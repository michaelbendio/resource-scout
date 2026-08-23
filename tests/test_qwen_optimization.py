from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from resource_research_agent.optimization import (
    branch_stop_state,
    build_housing_urgent_query_plan,
    candidate_qualification,
    candidate_identity_key,
    configuration_snapshot,
    coverage_branch_complete,
    package_exclusion_state,
    validate_candidate_dossier,
)
from resource_research_agent.playbooks import playbook_for
from resource_research_agent.storage import ResearchStore


FIXTURE_DIRECTORY = Path(__file__).parent / "fixtures" / "housing_qwen"
HOUSING_FACTUAL_FIELDS = playbook_for("housing").factual_fields


def optimization_configuration(quantization: str = "4-bit") -> dict:
    plan = build_housing_urgent_query_plan("Mesa", "Maricopa County and nearby areas")
    return {
        "label": f"housing-urgent-{quantization}",
        "modelArtifact": f"mlx-community/Qwen3.8-27B-{quantization.replace('-', '')}",
        "quantization": quantization,
        "modelProvider": "qwen-local",
        "modelEndpoint": "http://127.0.0.1:8080/v1",
        "mlxVersion": "pinned-at-run-start",
        "dshVersion": "0.1.0-rc.6",
        "searchProvider": "ddgs",
        "fetchProvider": "safe-http",
        "searchPluginVersion": "checkpoint-a-v1",
        "fetchPluginVersion": "checkpoint-a-v1",
        "promptPolicyVersion": "schema-playbook-dossier-v1",
        "playbookVersion": "1.2.0",
        "sourcePackageSha256": "c7a2251d7d638472f90207c24a28ec71c24515ea5d1aafced68a38fdce3d30f8",
        "sourcePackageVersion": "frozen-mesa-package",
        "targetLocation": "Mesa",
        "regionalScope": "Maricopa County and nearby areas",
        "targetCategoryId": "housing",
        "stageKey": "urgent-access",
        "limits": {
            "modelFallbacks": [],
            "searchFallbacks": [],
            "fetchMaxBytes": 200000,
            "fetchMaxRedirects": 5,
        },
        "stoppingRules": {
            "branchPolicy": "two consecutive queries with no new normalized identities",
            "coverageRequiresEveryBranch": True,
        },
        "queryPlan": plan,
    }


class OptimizationPersistenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.store = ResearchStore(Path(self.temporary.name) / "research.sqlite3")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_migration_creates_inspectable_pipeline_records(self) -> None:
        expected = {
            "optimization_configurations",
            "optimization_runs",
            "optimization_checkpoints",
            "optimization_coverage_branches",
            "optimization_queries",
            "optimization_query_attempts",
            "optimization_discovery_leads",
            "optimization_fetch_attempts",
            "optimization_lead_queries",
            "optimization_candidate_identities",
            "optimization_identity_leads",
            "optimization_evidence_sources",
            "optimization_corpora",
            "optimization_evidence_packets",
            "optimization_model_attempts",
            "optimization_candidate_dossiers",
            "optimization_verifications",
            "optimization_gap_queries",
            "optimization_comparisons",
            "optimization_audits",
            "optimization_package_outcomes",
        }
        with self.store.connect() as connection:
            actual = {
                row["name"]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            self.assertEqual("ok", connection.execute("PRAGMA integrity_check").fetchone()[0])
        self.assertTrue(expected.issubset(actual))
        with self.store.connect() as connection:
            query_columns = {
                row["name"]
                for row in connection.execute(
                    "PRAGMA table_info(optimization_queries)"
                )
            }
            branch_columns = {
                row["name"]
                for row in connection.execute(
                    "PRAGMA table_info(optimization_coverage_branches)"
                )
            }
        self.assertIn("new_eligible_identity_count", query_columns)
        self.assertIn("new_eligible_identity_count", branch_columns)
        self.assertIn("consecutive_no_new_eligible_identities", branch_columns)
        with self.store.connect() as connection:
            identity_columns = {
                row["name"]
                for row in connection.execute(
                    "PRAGMA table_info(optimization_candidate_identities)"
                )
            }
        self.assertIn("target_stage_key", identity_columns)

    def test_quantization_and_policy_changes_cannot_share_a_configuration(self) -> None:
        four_bit = optimization_configuration("4-bit")
        eight_bit = optimization_configuration("8-bit")
        four_bit_id = self.store.save_optimization_configuration(four_bit)
        eight_bit_id = self.store.save_optimization_configuration(eight_bit)
        self.assertNotEqual(four_bit_id, eight_bit_id)
        self.assertNotEqual(
            self.store.optimization_configuration(four_bit_id)["configurationHash"],
            self.store.optimization_configuration(eight_bit_id)["configurationHash"],
        )

        changed_policy = deepcopy(four_bit)
        changed_policy["label"] = "housing-urgent-4-bit-policy-2"
        changed_policy["promptPolicyVersion"] = "schema-playbook-dossier-v2"
        changed_policy_id = self.store.save_optimization_configuration(changed_policy)
        self.assertNotIn(changed_policy_id, {four_bit_id, eight_bit_id})

    def test_identical_snapshot_is_deduplicated_and_immutable(self) -> None:
        value = optimization_configuration()
        configuration_id = self.store.save_optimization_configuration(value)
        relabeled = deepcopy(value)
        relabeled["label"] = "display-label-does-not-change-provenance"
        self.assertEqual(
            configuration_id, self.store.save_optimization_configuration(relabeled)
        )
        with self.assertRaisesRegex(sqlite3.IntegrityError, "immutable"):
            with self.store.connect() as connection:
                connection.execute(
                    "UPDATE optimization_configurations SET quantization = '8-bit' WHERE id = ?",
                    (configuration_id,),
                )

    def test_metered_or_fallback_configuration_fails_closed(self) -> None:
        cloud = optimization_configuration()
        cloud["modelProvider"] = "deepseek-official"
        cloud["modelEndpoint"] = "https://api.deepseek.com"
        with self.assertRaisesRegex(ValueError, "loopback"):
            configuration_snapshot(cloud)

        fallback = optimization_configuration()
        fallback["limits"]["modelFallbacks"] = ["deepseek-official"]
        with self.assertRaisesRegex(ValueError, "fallback"):
            configuration_snapshot(fallback)

    def test_model_attempt_cannot_use_a_packet_from_another_frozen_corpus(self) -> None:
        configuration_id = self.store.save_optimization_configuration(
            optimization_configuration()
        )
        digest = "0" * 64
        with self.store.connect() as connection:
            discovery_run_id = connection.execute(
                """INSERT INTO optimization_runs (
                       created_at, label, configuration_id, run_kind, status, current_phase
                   ) VALUES ('now', 'discovery', ?, 'discovery', 'completed', 'freeze')""",
                (configuration_id,),
            ).lastrowid
            corpus_ids = []
            for suffix in ("1", "2"):
                corpus_ids.append(
                    connection.execute(
                        """INSERT INTO optimization_corpora (
                               discovery_run_id, created_at, frozen_at, status,
                               ledger_sha256, identities_sha256, sources_sha256,
                               packets_sha256, corpus_sha256
                           ) VALUES (?, 'now', NULL, 'building', ?, ?, ?, ?, ?)""",
                        (discovery_run_id, digest, digest, digest, digest, suffix * 64),
                    ).lastrowid
                )
            packet_id = connection.execute(
                """INSERT INTO optimization_evidence_packets (
                       corpus_id, identity_key, packet_json, packet_sha256
                   ) VALUES (?, 'provider::program', '{}', ?)""",
                (corpus_ids[1], "2" * 64),
            ).lastrowid
            connection.execute(
                "UPDATE optimization_corpora SET status = 'frozen', frozen_at = 'now'"
            )
            run_id = connection.execute(
                """INSERT INTO optimization_runs (
                       created_at, label, configuration_id, corpus_id, run_kind,
                       status, current_phase
                   ) VALUES ('now', 'four-bit-evaluation', ?, ?,
                             'model-evaluation', 'running', 'extract')""",
                (configuration_id, corpus_ids[0]),
            ).lastrowid
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    """INSERT INTO optimization_model_attempts (
                           run_id, packet_id, corpus_id, operation, attempt_number,
                           started_at, status, prompt_sha256
                       ) VALUES (?, ?, ?, 'extract', 1, 'now', 'running', ?)""",
                    (run_id, packet_id, corpus_ids[1], digest),
                )
            with self.assertRaisesRegex(sqlite3.IntegrityError, "immutable"):
                connection.execute(
                    "UPDATE optimization_evidence_packets SET packet_json = '{\"changed\":true}' WHERE id = ?",
                    (packet_id,),
                )

        eight_bit_configuration_id = self.store.save_optimization_configuration(
            optimization_configuration("8-bit")
        )
        with self.store.connect() as connection:
            eight_bit_other_corpus_run = connection.execute(
                """INSERT INTO optimization_runs (
                       created_at, label, configuration_id, corpus_id, run_kind,
                       status, current_phase
                   ) VALUES ('now', 'eight-bit-other-corpus', ?, ?,
                             'model-evaluation', 'completed', 'audit')""",
                (eight_bit_configuration_id, corpus_ids[1]),
            ).lastrowid
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    """INSERT INTO optimization_comparisons (
                           created_at, label, corpus_id, four_bit_run_id,
                           eight_bit_run_id, status
                       ) VALUES ('now', 'unfair-comparison', ?, ?, ?, 'planned')""",
                    (corpus_ids[0], run_id, eight_bit_other_corpus_run),
                )
            eight_bit_same_corpus_run = connection.execute(
                """INSERT INTO optimization_runs (
                       created_at, label, configuration_id, corpus_id, run_kind,
                       status, current_phase
                   ) VALUES ('now', 'eight-bit-same-corpus', ?, ?,
                             'model-evaluation', 'completed', 'audit')""",
                (eight_bit_configuration_id, corpus_ids[0]),
            ).lastrowid
            comparison_id = connection.execute(
                """INSERT INTO optimization_comparisons (
                       created_at, label, corpus_id, four_bit_run_id,
                       eight_bit_run_id, status
                   ) VALUES ('now', 'fair-comparison', ?, ?, ?, 'planned')""",
                (corpus_ids[0], run_id, eight_bit_same_corpus_run),
            ).lastrowid
            self.assertGreater(comparison_id, 0)


class CoverageAndSaturationTests(unittest.TestCase):
    def test_first_housing_stage_has_persistable_required_coverage(self) -> None:
        plan = build_housing_urgent_query_plan("Mesa", "Maricopa County and nearby areas")
        self.assertEqual("urgent-access", plan["stageKey"])
        self.assertEqual(9, len(plan["branches"]))
        self.assertTrue(all(branch["required"] for branch in plan["branches"]))
        self.assertTrue(all(len(branch["queries"]) == 6 for branch in plan["branches"]))
        self.assertEqual(
            {
                "official-city",
                "official-county",
                "official-state",
                "coordinated-entry-and-211",
                "direct-providers",
                "specialized-safety",
                "temporary-lodging",
                "regional-serving-target",
                "access-barriers",
            },
            {branch["key"] for branch in plan["branches"]},
        )

    def test_expanded_plan_has_versioned_depth_and_package_eligible_saturation(self) -> None:
        plan = build_housing_urgent_query_plan(
            "Mesa",
            "Maricopa County and nearby areas",
            minimum_queries=4,
            maximum_queries=10,
            saturation_queries=3,
        )
        self.assertEqual(4, plan["schemaVersion"])
        self.assertEqual(
            "candidate-role-gates-v1",
            plan["candidateQualificationPolicyVersion"],
        )
        self.assertTrue(all(len(branch["queries"]) == 10 for branch in plan["branches"]))
        queries = {
            query["key"]: query["query"]
            for branch in plan["branches"]
            for query in branch["queries"]
        }
        self.assertEqual(
            'Maricopa Regional Continuum of Care "Mesa" coordinated entry get help',
            queries["coordinated-entry-and-211-10"],
        )
        self.assertEqual(
            '"Mesa" senior older adults medically vulnerable homeless day center shelter',
            queries["specialized-safety-4"],
        )
        self.assertEqual(
            '"Mesa" medical respite homeless housing',
            queries["specialized-safety-10"],
        )
        self.assertEqual(
            '"Mesa" Salvation Army Phoenix emergency family shelter intake',
            queries["temporary-lodging-4"],
        )
        self.assertTrue(
            all(
                branch["saturation"]["minimumQueries"] == 4
                and branch["saturation"]["consecutiveNoNewIdentityQueries"] == 3
                and branch["saturation"]["noveltyUnit"].startswith("package-eligible")
                for branch in plan["branches"]
            )
        )
        with self.assertRaisesRegex(ValueError, "at most ten"):
            build_housing_urgent_query_plan(
                "Mesa",
                "Maricopa County and nearby areas",
                maximum_queries=11,
            )

    def test_branch_stops_only_at_recorded_saturation_or_maximum(self) -> None:
        policy = {
            "minimum_queries": 2,
            "maximum_queries": 6,
            "saturation_queries": 2,
        }
        self.assertEqual("continue", branch_stop_state([0], **policy))
        self.assertEqual("continue", branch_stop_state([2, 0], **policy))
        self.assertEqual("saturated", branch_stop_state([2, 0, 0], **policy))
        self.assertEqual("maximum-reached", branch_stop_state([1, 1, 1, 1, 1, 1], **policy))
        with self.assertRaisesRegex(ValueError, "exceed"):
            branch_stop_state([1, 1, 1, 1, 1, 1, 1], **policy)

    def test_not_applicable_branch_requires_an_explicit_reason(self) -> None:
        self.assertFalse(coverage_branch_complete({"status": "not-applicable"}))
        self.assertTrue(
            coverage_branch_complete(
                {"status": "not-applicable", "notApplicableReason": "No state program exists for this stage"}
            )
        )


class CandidateQualificationTests(unittest.TestCase):
    @staticmethod
    def decision(**values) -> dict:
        decision = {
            "candidateRole": "direct-program",
            "geographyState": "confirmed-target",
            "actionabilityState": "actionable",
            "currentStatusState": "current",
            "evidenceReadiness": "current-authoritative",
        }
        decision.update(values)
        return decision

    def test_only_program_and_actionable_assessment_roles_are_countable(self) -> None:
        for role in ("direct-program", "access-assessment-service"):
            with self.subTest(role=role):
                result = candidate_qualification(
                    self.decision(candidateRole=role),
                    boundary_state="resolved",
                    package_match_state="not-matched",
                )
                self.assertEqual("eligible", result["state"])
        for role in (
            "service-location",
            "referral-system",
            "directory",
            "organization-only",
            "unresolved-lead",
        ):
            with self.subTest(role=role):
                result = candidate_qualification(
                    self.decision(candidateRole=role),
                    boundary_state="resolved",
                    package_match_state="not-matched",
                )
                self.assertEqual("noncandidate", result["state"])

    def test_uncertain_or_lead_only_identity_is_preserved_for_review(self) -> None:
        for field, value in (
            ("geographyState", "unknown"),
            ("actionabilityState", "uncertain"),
            ("currentStatusState", "uncertain"),
            ("evidenceReadiness", "lead-only"),
        ):
            with self.subTest(field=field):
                result = candidate_qualification(
                    self.decision(**{field: value}),
                    boundary_state="resolved",
                    package_match_state="not-matched",
                )
                self.assertEqual("review-required", result["state"])

    def test_same_program_and_nonactionable_record_do_not_count(self) -> None:
        package_duplicate = candidate_qualification(
            self.decision(),
            boundary_state="excluded-existing",
            package_match_state="same-program",
        )
        informational = candidate_qualification(
            self.decision(actionabilityState="informational-only"),
            boundary_state="resolved",
            package_match_state="not-matched",
        )
        self.assertEqual("excluded-existing", package_duplicate["state"])
        self.assertEqual("noncandidate", informational["state"])

    def test_missing_role_contract_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "candidateRole"):
            candidate_qualification(
                {
                    "geographyState": "confirmed-target",
                    "actionabilityState": "actionable",
                    "currentStatusState": "current",
                    "evidenceReadiness": "current-authoritative",
                },
                boundary_state="resolved",
                package_match_state="not-matched",
            )


class HousingQualityGateTests(unittest.TestCase):
    def test_every_regression_fixture_is_rejected_for_its_named_failure(self) -> None:
        fixture_paths = sorted(FIXTURE_DIRECTORY.glob("*.json"))
        self.assertEqual(6, len(fixture_paths))
        for path in fixture_paths:
            with self.subTest(fixture=path.name):
                fixture = json.loads(path.read_text(encoding="utf-8"))
                for source in fixture["dossier"].get("sources", []):
                    self.assertTrue(source.get("url"))
                    self.assertTrue(source.get("extract"))
                issues = validate_candidate_dossier(
                    fixture["dossier"], required_fields=fixture["requiredFields"]
                )
                codes = {issue["code"] for issue in issues}
                self.assertTrue(
                    set(fixture["expectedIssueCodes"]).issubset(codes),
                    f"{path.name} produced {issues}",
                )

    def test_every_factual_field_must_be_supported_conflicting_or_unknown(self) -> None:
        identity_key = candidate_identity_key("Example Provider", "Housing Program")
        dossier = {
            "candidateIdentity": {
                "organization": "Example Provider",
                "program": "Housing Program",
                "identityKey": identity_key,
                "componentIdentityKeys": [identity_key],
            },
            "sources": [],
            "fields": {
                field: {"status": "unknown", "reason": "Not found in the frozen evidence packet"}
                for field in HOUSING_FACTUAL_FIELDS
            },
        }
        self.assertEqual(
            [],
            validate_candidate_dossier(
                dossier, required_fields=HOUSING_FACTUAL_FIELDS
            ),
        )
        del dossier["fields"]["eligibility"]
        issues = validate_candidate_dossier(
            dossier, required_fields=HOUSING_FACTUAL_FIELDS
        )
        self.assertIn("missing-field-state", {issue["code"] for issue in issues})

    def test_explicit_evidenced_conflict_is_allowed(self) -> None:
        identity_key = candidate_identity_key("Example Provider", "Housing Program")
        dossier = {
            "candidateIdentity": {
                "organization": "Example Provider",
                "program": "Housing Program",
                "identityKey": identity_key,
                "componentIdentityKeys": [identity_key],
            },
            "sources": [
                {
                    "id": "official-a",
                    "url": "https://fixture.invalid/example/official-a",
                    "extract": "Fixture extract: the program publishes 480-000-0300.",
                    "authority": "direct-provider",
                    "pageIdentityKey": identity_key,
                    "pageOrganizationKey": "example provider",
                    "supports": [{"field": "phone", "value": "480-000-0300", "scope": "program"}],
                },
                {
                    "id": "official-b",
                    "url": "https://fixture.invalid/example/official-b",
                    "extract": "Fixture extract: the referral system publishes 480-000-0399.",
                    "authority": "government-referral",
                    "pageIdentityKey": identity_key,
                    "pageOrganizationKey": "example provider",
                    "supports": [{"field": "phone", "value": "480-000-0399", "scope": "program"}],
                },
            ],
            "fields": {
                "phone": {
                    "status": "conflicting",
                    "alternatives": [
                        {"value": "480-000-0300", "evidenceIds": ["official-a"]},
                        {"value": "480-000-0399", "evidenceIds": ["official-b"]},
                    ],
                }
            },
        }
        self.assertEqual([], validate_candidate_dossier(dossier, required_fields=["phone"]))

    def test_package_exclusion_uses_organization_plus_program(self) -> None:
        self.assertEqual(
            "same-program",
            package_exclusion_state("A New Leaf", "Rapid Re-Housing", "A New Leaf", "Rapid Re-Housing"),
        )
        self.assertEqual(
            "different-program",
            package_exclusion_state("A New Leaf", "Rapid Re-Housing", "A New Leaf", "MesaCAN"),
        )


if __name__ == "__main__":
    unittest.main()
