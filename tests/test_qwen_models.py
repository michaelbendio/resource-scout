from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from copy import deepcopy
from pathlib import Path

from resource_research_agent.optimization import optimization_resource_id
from resource_research_agent.optimization_models import (
    apply_verification_decisions,
    compact_source_bindings,
    OptimizationModelError,
    OptimizationModelPipeline,
    remediate_invalid_factual_fields,
    restore_frozen_candidate_identity,
    restore_frozen_source_envelopes,
    verification_status,
)
from resource_research_agent.playbooks import playbook_for
from resource_research_agent.optimization_pipeline import OptimizationDiscoveryPipeline
from resource_research_agent.optimization_outcomes import compare_optimization_run_to_package
from resource_research_agent.review_export import build_optimization_review_copy
from resource_research_agent.storage import ResearchStore
from tests.test_qwen_discovery import FixtureProviders


HOUSING_FACTUAL_FIELDS = playbook_for("housing").factual_fields


def model_configuration(providers: FixtureProviders, label: str) -> dict:
    value = providers.configuration(label)
    value.update(
        {
            "modelArtifact": "mlx-community/Qwen3.8-27B-4bit",
            "quantization": "4-bit",
            "modelProvider": "qwen-local",
            "modelEndpoint": "http://127.0.0.1:8080/v1",
            "mlxVersion": "fixture-runtime",
            "dshVersion": "0.1.0-rc.6",
            "promptPolicyVersion": "schema-playbook-dossier-v1-and-verifier-decision-patch-v1",
        }
    )
    return value


def source_records(packet: dict) -> list[dict]:
    result = []
    for source in packet["sources"]:
        result.append(
            {
                "id": str(source["id"]),
                "url": source["canonical_url"],
                "title": source["extract"]["title"],
                "extract": source["extract"]["text"],
                "authority": source["authority"],
                "pageIdentityKey": source["page_identity_key"],
                "pageOrganizationKey": source["page_identity_key"].split("::", 1)[0],
                "supports": [],
                "contradicts": [],
            }
        )
    return result


class SeededFixtureModels:
    def __init__(self) -> None:
        self.extract_prompts: list[dict] = []
        self.verify_prompts: list[dict] = []

    def extract(self, prompt: dict) -> dict:
        self.extract_prompts.append(deepcopy(prompt))
        packet = prompt["evidencePacket"]
        identity = packet["candidateIdentity"]
        identity_key = identity["identityKey"]
        sources = source_records(packet)
        fields = {
            field: {
                "status": "unknown",
                "reason": "Not found in the frozen fixture evidence packet",
            }
            for field in prompt["requiredFields"]
        }
        program = identity["program"]
        components = [identity_key]
        if program == "Rapid Re-Housing":
            sources[0]["pageIdentityKey"] = "a new leaf::mesacan"
            sources[0]["supports"] = [
                {
                    "field": "phone",
                    "value": "480-000-0100",
                    "scope": "program",
                }
            ]
            fields["phone"] = {
                "status": "supported",
                "value": "480-000-0100",
                "evidenceIds": [sources[0]["id"]],
            }
        elif program == "Off the Streets":
            sources[0]["supports"] = [
                {
                    "field": "geography",
                    "value": "Maricopa County outside Mesa",
                    "scope": "program",
                }
            ]
            sources[0]["contradicts"] = [
                {"field": "geography", "value": "Mesa"}
            ]
            fields["geography"] = {
                "status": "supported",
                "value": "Mesa",
                "evidenceIds": [sources[0]["id"]],
            }
        elif program == "Emergency Lodging Program":
            fields["barriers"] = {
                "status": "supported",
                "value": ["Must be sober"],
                "evidenceIds": [],
            }
        return {
            "candidateIdentity": {
                "organization": identity["organization"],
                "program": program,
                "identityKey": identity_key,
                "componentIdentityKeys": components,
            },
            "sources": sources,
            "fields": fields,
        }

    def verify(self, prompt: dict) -> dict:
        self.verify_prompts.append(deepcopy(prompt))
        decisions = {
            field: {"action": "keep"} for field in prompt["requiredFields"]
        }
        for finding in prompt["deterministicFindings"]:
            field = finding.get("field")
            if field in decisions:
                decisions[field] = {
                    "action": "downgrade-to-unknown",
                    "reason": f"Removed by verifier: {finding['code']}",
                }
        return {
            "status": "passed",
            "fieldDecisions": decisions,
            "materialDefects": [],
            "findings": [],
        }


class ModelPipelineTests(unittest.TestCase):
    def test_deterministic_remediation_only_downgrades_factual_fields(self) -> None:
        dossier = {
            "fields": {
                "phone": {"status": "supported", "value": "480-555-0100"},
            }
        }
        remediated, findings = remediate_invalid_factual_fields(
            dossier,
            [
                {"code": "missing-evidence", "field": "phone", "message": "bad"},
                {
                    "code": "altered-source",
                    "field": "url",
                    "message": "structural defect",
                },
            ],
            ["phone"],
        )
        self.assertEqual("unknown", remediated["fields"]["phone"]["status"])
        self.assertEqual("deterministic-field-downgrade", findings[0]["code"])
        self.assertEqual("phone", findings[0]["field"])
        self.assertEqual({"status": "supported", "value": "480-555-0100"}, dossier["fields"]["phone"])

    def test_actual_verifier_omissions_preserve_extraction_and_never_fail_candidate(
        self,
    ) -> None:
        cases = json.loads(
            (
                Path(__file__).parent
                / "fixtures"
                / "verification_omission_regressions.json"
            ).read_text(encoding="utf-8")
        )
        for case in cases:
            with self.subTest(program=case["program"], field=case["field"]):
                dossier = {
                    "candidateIdentity": {
                        "organization": case["organization"],
                        "program": case["program"],
                    },
                    "sources": [{"id": "preserved-source"}],
                    "fields": {
                        field: {
                            "status": "unknown",
                            "reason": "Not found in regression fixture",
                        }
                        for field in HOUSING_FACTUAL_FIELDS
                    },
                }
                dossier["fields"][case["field"]] = case["extractedFinding"]
                response = {
                    "status": "passed",
                    "fieldDecisions": {
                        field: {"action": "keep"}
                        for field in HOUSING_FACTUAL_FIELDS
                        if field != case["field"]
                    },
                    "materialDefects": [],
                }

                verified, findings, material_defects = apply_verification_decisions(
                    dossier, response, HOUSING_FACTUAL_FIELDS
                )
                self.assertEqual(
                    case["extractedFinding"], verified["fields"][case["field"]]
                )
                self.assertEqual(dossier["candidateIdentity"], verified["candidateIdentity"])
                self.assertEqual(dossier["sources"], verified["sources"])
                self.assertEqual([], material_defects)
                self.assertEqual(
                    [("verification-incomplete", case["field"])],
                    [
                        (finding["code"], finding.get("field"))
                        for finding in findings
                    ],
                )
                self.assertEqual(
                    "needs-review",
                    verification_status(
                        final_issues=[],
                        material_defects=material_defects,
                        review_findings=findings,
                        requested_status="passed",
                    ),
                )

    def test_pet_policy_cannot_be_promoted_to_candidate_blocking_defect(self) -> None:
        dossier = {
            "candidateIdentity": {"organization": "Example", "program": "Shelter"},
            "sources": [],
            "fields": {
                field: {"status": "unknown", "reason": "Not found"}
                for field in HOUSING_FACTUAL_FIELDS
            },
        }
        verified, findings, defects = apply_verification_decisions(
            dossier,
            {
                "status": "passed",
                "fieldDecisions": {
                    field: {"action": "keep"} for field in HOUSING_FACTUAL_FIELDS
                },
                "materialDefects": [
                    {
                        "code": "unsupported-safety-critical-claim",
                        "field": "petPolicy",
                        "reason": "The pet policy is not known.",
                    }
                ],
            },
            HOUSING_FACTUAL_FIELDS,
            playbook_for("housing").supplementary_fields,
        )
        self.assertEqual(dossier["fields"]["petPolicy"], verified["fields"]["petPolicy"])
        self.assertEqual([], defects)
        self.assertIn(
            "nonblocking-field-material-defect",
            {finding["code"] for finding in findings},
        )
        self.assertEqual(
            "needs-review",
            verification_status(
                final_issues=[],
                material_defects=defects,
                review_findings=findings,
                requested_status="passed",
            ),
        )

    def test_invented_field_cannot_become_safety_critical_blocking_defect(self) -> None:
        dossier = {
            "candidateIdentity": {"organization": "Example", "program": "Shelter"},
            "sources": [],
            "fields": {
                field: {"status": "unknown", "reason": "Not found"}
                for field in HOUSING_FACTUAL_FIELDS
            },
        }
        _verified, findings, defects = apply_verification_decisions(
            dossier,
            {
                "status": "passed",
                "fieldDecisions": {
                    field: {"action": "keep"} for field in HOUSING_FACTUAL_FIELDS
                },
                "materialDefects": [
                    {
                        "code": "unsupported-safety-critical-claim",
                        "field": "petsAllowed",
                        "reason": "The verifier invented an out-of-contract field.",
                    }
                ],
            },
            HOUSING_FACTUAL_FIELDS,
            playbook_for("housing").supplementary_fields,
        )
        self.assertEqual([], defects)
        self.assertIn("invalid-material-defect", {finding["code"] for finding in findings})

    def test_verifier_patch_cannot_mutate_identity_sources_or_unlisted_fields(self) -> None:
        dossier = {
            "candidateIdentity": {"organization": "Example", "program": "Food Box"},
            "sources": [{"id": "source-1", "url": "https://example.org"}],
            "fields": {
                "phone": {"status": "supported", "value": "480-555-0100"},
                "hours": {"status": "unknown", "reason": "Not published"},
            },
        }
        verified, findings, defects = apply_verification_decisions(
            dossier,
            {
                "fieldDecisions": {
                    "phone": {
                        "action": "downgrade-to-unknown",
                        "reason": "The cited source describes another program.",
                    },
                    "hours": {
                        "action": "mark-conflicting",
                        "reason": "Two current official schedules conflict.",
                        "alternatives": [
                            {"value": "Weekdays", "evidenceIds": ["source-1"]},
                            {"value": "Daily", "evidenceIds": ["source-2"]},
                        ],
                    },
                    "inventedField": {"action": "keep"},
                },
                "candidateIdentity": {"organization": "Mutated"},
                "sources": [],
                "materialDefects": [],
            },
            ["phone", "hours"],
        )
        self.assertEqual(dossier["candidateIdentity"], verified["candidateIdentity"])
        self.assertEqual(dossier["sources"], verified["sources"])
        self.assertEqual("unknown", verified["fields"]["phone"]["status"])
        self.assertEqual("conflicting", verified["fields"]["hours"]["status"])
        self.assertNotIn("inventedField", verified["fields"])
        self.assertEqual([], defects)
        self.assertIn(
            "invalid-verifier-decision-field",
            {finding["code"] for finding in findings},
        )
        self.assertIn(
            "forbidden-verifier-rewrite",
            {finding["code"] for finding in findings},
        )

    def test_frozen_source_envelope_is_restored_without_hiding_invented_ids(self) -> None:
        packet = {
            "sources": [
                {
                    "id": 7,
                    "canonical_url": "https://example.org/program",
                    "authority": "direct-provider",
                    "page_identity_key": "example::program",
                    "extract": {"title": "Program", "text": "Frozen exact text"},
                }
            ]
        }
        dossier = {
            "sources": [
                {"id": "7", "extract": "model summary", "supports": []},
                {"id": "invented", "extract": "made up", "supports": []},
            ]
        }
        restored = restore_frozen_source_envelopes(dossier, packet)
        self.assertEqual("Frozen exact text", restored["sources"][0]["extract"])
        self.assertEqual("made up", restored["sources"][1]["extract"])

    def test_source_binding_compaction_preserves_only_model_owned_fields(self) -> None:
        dossier = {
            "sources": [
                {
                    "id": 7,
                    "url": "https://example.org/program",
                    "extract": "immutable text",
                    "authority": "direct-provider",
                    "supports": [{"field": "phone", "value": "211"}],
                    "contradicts": [],
                }
            ],
            "fields": {"phone": {"status": "supported", "value": "211"}},
        }
        compacted = compact_source_bindings(dossier)

        self.assertEqual(
            [{"id": 7, "supports": [{"field": "phone", "value": "211"}], "contradicts": []}],
            compacted["sources"],
        )
        self.assertEqual(dossier["fields"], compacted["fields"])
        self.assertIn("url", dossier["sources"][0])

    def test_frozen_candidate_identity_is_restored_without_dropping_review_metadata(self) -> None:
        packet = {
            "candidateIdentity": {
                "organization": "A New Leaf",
                "program": "Community Alliance Against Family Abuse Shelter",
                "identityKey": "a new leaf::community alliance against family abuse shelter",
            }
        }
        dossier = {
            "candidateIdentity": {
                "organization": "A New Leaf",
                "program": "Community Alliance Against Family Abuse (CAAFA)",
                "identityKey": "a new leaf::community alliance against family abuse shelter",
                "boundaryState": "resolved",
                "coverageTags": ["domestic-violence"],
            }
        }
        restored = restore_frozen_candidate_identity(dossier, packet)

        self.assertEqual(
            packet["candidateIdentity"]["program"],
            restored["candidateIdentity"]["program"],
        )
        self.assertEqual(
            [packet["candidateIdentity"]["identityKey"]],
            restored["candidateIdentity"]["componentIdentityKeys"],
        )
        self.assertEqual("resolved", restored["candidateIdentity"]["boundaryState"])
        self.assertEqual(
            ["domestic-violence"], restored["candidateIdentity"]["coverageTags"]
        )

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.store = ResearchStore(Path(self.temporary.name) / "research.sqlite3")
        self.providers = FixtureProviders()
        discovery = OptimizationDiscoveryPipeline(
            self.store,
            self.providers.configuration("model-fixture-discovery"),
            search=self.providers.search,
            fetch=self.providers.fetch,
            resolve_identity=self.providers.resolve,
            existing_resources=self.providers.fixture["existingResources"],
        )
        self.corpus = discovery.run()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def pipeline(
        self,
        models: SeededFixtureModels,
        label: str,
        *,
        progress=None,
        extract=None,
        verify=None,
    ) -> OptimizationModelPipeline:
        return OptimizationModelPipeline(
            self.store,
            model_configuration(self.providers, label),
            self.corpus.corpus_id,
            extract=extract or models.extract,
            verify=verify or models.verify,
            required_coverage_needs=(
                {
                    "key": "emergency-adult",
                    "label": "Adult emergency access",
                    "query": '"Mesa" adult emergency shelter intake',
                },
                {
                    "key": "medical-respite",
                    "label": "Medical respite",
                    "query": '"Mesa" medical respite homeless program',
                },
            ),
            progress=progress,
        )

    def test_fresh_verifier_catches_seeded_defects_and_gap_audit_plans_query(self) -> None:
        models = SeededFixtureModels()
        pipeline = self.pipeline(models, "model-fixture-four-bit")
        result = pipeline.run()

        self.assertTrue(result.quality_gate_passed)
        self.assertEqual(8, result.packet_count)
        self.assertEqual(6, result.passed_count)
        self.assertEqual(2, result.needs_review_count)
        self.assertEqual(0, result.failed_count)
        self.assertEqual(1, result.supported_field_count)
        self.assertEqual(8 * len(HOUSING_FACTUAL_FIELDS) - 1, result.unknown_field_count)
        self.assertEqual(1, result.gap_count)
        self.assertEqual(8, len(models.extract_prompts))
        self.assertEqual(8, len(models.verify_prompts))
        self.assertTrue(
            all(prompt["operation"] == "extract-candidate-dossier" for prompt in models.extract_prompts)
        )
        self.assertTrue(all(prompt.get("outputContract") for prompt in models.extract_prompts))
        self.assertTrue(
            all(
                "only id, supports, and contradicts"
                in prompt["outputContract"]["sources"]
                for prompt in models.extract_prompts
            )
        )
        self.assertTrue(
            all(
                "Use only program or organization as an evidence-binding scope."
                in prompt["instructions"]
                for prompt in models.extract_prompts
            )
        )
        self.assertTrue(
            all(
                prompt["operation"]
                == "verify-candidate-dossier-decision-patch-fresh-context"
                for prompt in models.verify_prompts
            )
        )
        self.assertTrue(all(prompt.get("outputContract") for prompt in models.verify_prompts))
        self.assertTrue(
            all(
                all(
                    set(source) <= {"id", "supports", "contradicts"}
                    for source in prompt["dossier"]["sources"]
                )
                for prompt in models.verify_prompts
            )
        )
        detected_codes = {
            finding["code"]
            for prompt in models.verify_prompts
            for finding in prompt["deterministicFindings"]
        }
        self.assertTrue(
            {
                "source-does-not-support-field",
                "contradicted-field",
                "missing-evidence",
            }.issubset(detected_codes)
        )

        with self.store.connect() as connection:
            final_findings = [
                json.loads(row["findings_json"])["finalDeterministicFindings"]
                for row in connection.execute(
                    "SELECT findings_json FROM optimization_verifications"
                ).fetchall()
            ]
            self.assertTrue(all(not findings for findings in final_findings))
            gaps = connection.execute(
                "SELECT need_key, query_text, status FROM optimization_gap_queries"
            ).fetchall()
            self.assertEqual(
                [("medical-respite", '"Mesa" medical respite homeless program', "planned")],
                [(row["need_key"], row["query_text"], row["status"]) for row in gaps],
            )

        candidates = pipeline.verified_candidates(result.run_id)
        self.assertEqual(8, len(candidates))
        self.assertTrue(all(candidate["name"] for candidate in candidates))
        self.assertTrue(all(candidate["evidence"] for candidate in candidates))
        self.assertEqual(
            8 * len(HOUSING_FACTUAL_FIELDS) - 1,
            sum(len(candidate["unknowns"]) for candidate in candidates),
        )
        self.assertTrue(any(candidate.get("phone") == "480-000-0100" for candidate in candidates))

    def test_non_housing_pipeline_uses_the_selected_playbook_field_contract(self) -> None:
        store = ResearchStore(Path(self.temporary.name) / "food.sqlite3")
        providers = FixtureProviders()
        discovery_configuration = providers.configuration("food-fixture-discovery")
        discovery_configuration["targetCategoryId"] = "food"
        discovery_configuration["stageKey"] = "immediate-food"
        discovery_configuration["queryPlan"] = deepcopy(
            discovery_configuration["queryPlan"]
        )
        discovery_configuration["queryPlan"]["categoryId"] = "food"
        discovery_configuration["queryPlan"]["stageKey"] = "immediate-food"

        def resolve_food(result: dict) -> dict | list[dict] | None:
            resolved = providers.resolve(result)
            if isinstance(resolved, list):
                retained = [
                    {**item, "stageKey": "immediate-food"}
                    for item in resolved
                    if item.get("stageKey", "urgent-access") == "urgent-access"
                ]
                return retained or None
            if isinstance(resolved, dict):
                if resolved.get("stageKey", "urgent-access") != "urgent-access":
                    return None
                return {**resolved, "stageKey": "immediate-food"}
            return None

        corpus = OptimizationDiscoveryPipeline(
            store,
            discovery_configuration,
            search=providers.search,
            fetch=providers.fetch,
            resolve_identity=resolve_food,
            existing_resources=providers.fixture["existingResources"],
        ).run()
        configuration = model_configuration(providers, "food-fixture-model")
        for field in ("targetCategoryId", "stageKey", "queryPlan"):
            configuration[field] = deepcopy(discovery_configuration[field])
        models = SeededFixtureModels()
        result = OptimizationModelPipeline(
            store,
            configuration,
            corpus.corpus_id,
            extract=models.extract,
            verify=models.verify,
        ).run()

        food_fields = playbook_for("food").factual_fields
        self.assertNotIn("petPolicy", food_fields)
        self.assertTrue(
            all(prompt["requiredFields"] == list(food_fields) for prompt in models.extract_prompts)
        )
        self.assertTrue(
            all(prompt["requiredFields"] == list(food_fields) for prompt in models.verify_prompts)
        )
        self.assertEqual(result.packet_count * len(food_fields), result.supported_field_count + result.conflicting_field_count + result.unknown_field_count)
        with store.connect() as connection:
            dossiers = connection.execute(
                "SELECT verified_dossier_json FROM optimization_verifications"
            ).fetchall()
        self.assertTrue(
            all(
                "petPolicy" not in json.loads(row["verified_dossier_json"])["fields"]
                for row in dossiers
            )
        )

    def test_inspection_open_does_not_recover_an_active_model_attempt(self) -> None:
        configuration_id = self.store.save_optimization_configuration(
            model_configuration(self.providers, "active-model-inspection")
        )
        with self.store.connect() as connection:
            run_id = int(
                connection.execute(
                    """INSERT INTO optimization_runs (
                           created_at, label, configuration_id, corpus_id, run_kind,
                           status, current_phase
                       ) VALUES ('now', 'active-model-inspection', ?, ?,
                                 'model-evaluation', 'running', 'candidate-extraction')""",
                    (configuration_id, self.corpus.corpus_id),
                ).lastrowid
            )
            packet_id = int(
                connection.execute(
                    """SELECT id FROM optimization_evidence_packets
                       WHERE corpus_id = ? ORDER BY id LIMIT 1""",
                    (self.corpus.corpus_id,),
                ).fetchone()["id"]
            )
            attempt_id = int(
                connection.execute(
                    """INSERT INTO optimization_model_attempts (
                           run_id, packet_id, corpus_id, operation, attempt_number,
                           started_at, status, prompt_sha256
                       ) VALUES (?, ?, ?, 'extract', 1, 'now', 'running', ?)""",
                    (run_id, packet_id, self.corpus.corpus_id, "0" * 64),
                ).lastrowid
            )

        inspected = ResearchStore(self.store.path)
        with inspected.connect() as connection:
            self.assertEqual(
                "running",
                connection.execute(
                    "SELECT status FROM optimization_model_attempts WHERE id = ?",
                    (attempt_id,),
                ).fetchone()["status"],
            )
            self.assertEqual(
                "running",
                connection.execute(
                    "SELECT status FROM optimization_runs WHERE id = ?", (run_id,)
                ).fetchone()["status"],
            )

        recovered = ResearchStore(self.store.path, recover_interrupted=True)
        with recovered.connect() as connection:
            self.assertEqual(
                "failed",
                connection.execute(
                    "SELECT status FROM optimization_model_attempts WHERE id = ?",
                    (attempt_id,),
                ).fetchone()["status"],
            )
            self.assertEqual(
                "partial",
                connection.execute(
                    "SELECT status FROM optimization_runs WHERE id = ?", (run_id,)
                ).fetchone()["status"],
            )

    def test_needs_review_is_reported_separately_and_reaches_candidate_output(self) -> None:
        review_models = SeededFixtureModels()

        def needs_review(prompt: dict) -> dict:
            result = review_models.verify(prompt)
            return {**result, "status": "needs-review"}

        review_pipeline = self.pipeline(
            review_models,
            "model-fixture-needs-review",
            verify=needs_review,
        )
        review_result = review_pipeline.run()
        self.assertTrue(review_result.quality_gate_passed)
        self.assertEqual(0, review_result.passed_count)
        self.assertEqual(8, review_result.needs_review_count)
        self.assertEqual(0, review_result.failed_count)
        review_candidates = review_pipeline.verified_candidates(review_result.run_id)
        self.assertEqual(8, len(review_candidates))
        self.assertTrue(
            all(
                candidate["verificationStatus"] == "needs-review"
                for candidate in review_candidates
            )
        )
        self.assertTrue(
            all(
                "verifierFindings" in candidate["verificationFindings"]
                for candidate in review_candidates
            )
        )

        mixed_models = SeededFixtureModels()

        def mixed_statuses(prompt: dict) -> dict:
            result = mixed_models.verify(prompt)
            program = prompt["candidateIdentity"]["program"]
            if program == "Rapid Re-Housing":
                return {**result, "status": "needs-review"}
            if program == "Brian Garcia Welcome Center":
                result["materialDefects"].append(
                    {
                        "code": "identity-conflation",
                        "reason": "Fixture material identity defect",
                    }
                )
            return result

        mixed_pipeline = self.pipeline(
            mixed_models,
            "model-fixture-mixed-verification-statuses",
            verify=mixed_statuses,
        )
        mixed_result = mixed_pipeline.run()
        self.assertFalse(mixed_result.quality_gate_passed)
        self.assertEqual(4, mixed_result.passed_count)
        self.assertEqual(3, mixed_result.needs_review_count)
        self.assertEqual(1, mixed_result.failed_count)
        self.assertEqual(7, len(mixed_pipeline.verified_candidates(mixed_result.run_id)))
        with self.store.connect() as connection:
            completeness = json.loads(
                connection.execute(
                    """SELECT report_json FROM optimization_audits
                       WHERE run_id = ? AND audit_type = 'candidate-completeness'""",
                    (mixed_result.run_id,),
                ).fetchone()["report_json"]
            )
            quality = json.loads(
                connection.execute(
                    """SELECT report_json FROM optimization_audits
                       WHERE run_id = ? AND audit_type = 'quality-gate'""",
                    (mixed_result.run_id,),
                ).fetchone()["report_json"]
            )
        self.assertEqual(3, completeness["needsReviewCount"])
        self.assertEqual(1, completeness["failedCount"])
        self.assertEqual(3, quality["verificationNeedsReview"])
        self.assertEqual(1, quality["verificationFailures"])
        review = build_optimization_review_copy(
            self.store,
            mixed_result.run_id,
        )
        self.assertEqual(7, len(review.data["candidates"]))
        self.assertEqual(
            {"passed", "needs-review"},
            {
                item["candidate"]["verificationStatus"]
                for item in review.data["candidates"]
            },
        )
        self.assertTrue(
            all(
                item["candidate"]["optimizationProvenance"]["runId"]
                == mixed_result.run_id
                for item in review.data["candidates"]
            )
        )
        self.assertTrue(
            all(
                "verifierFindings" in item["candidate"]["verificationFindings"]
                for item in review.data["candidates"]
            )
        )
        self.assertNotIn("wrong::program", review.html.decode("utf-8"))
        package_path = Path(self.temporary.name) / "phone-vetted-resource-package.zip"
        accepted_candidates = review.data["candidates"][:2]
        resources = []
        for item in accepted_candidates:
            provenance = item["candidate"]["optimizationProvenance"]
            resources.append(
                {
                    "id": optimization_resource_id(
                        provenance["configurationHash"], provenance["packetId"]
                    ),
                    "name": item["name"],
                    "phone": "480-555-0100",
                    "categories": ["housing"],
                }
            )
        with zipfile.ZipFile(package_path, "w") as archive:
            archive.writestr(
                "tso-resources.json",
                json.dumps(
                    {
                        "resourcePackageSchemaVersion": 3,
                        "packageVersion": 2,
                        "categories": [{"id": "housing", "label": "Housing"}],
                        "resources": resources,
                    }
                ),
            )
        outcome = compare_optimization_run_to_package(
            self.store, mixed_result.run_id, package_path
        )
        self.assertEqual(7, outcome.candidate_count)
        self.assertEqual(2, outcome.accepted_count)
        self.assertEqual(5, outcome.not_present_count)
        self.assertEqual(
            outcome.report_sha256,
            compare_optimization_run_to_package(
                self.store, mixed_result.run_id, package_path
            ).report_sha256,
        )
        with self.store.connect() as connection:
            self.assertEqual(
                1,
                connection.execute(
                    "SELECT COUNT(*) FROM optimization_package_outcomes"
                ).fetchone()[0],
            )

    def test_residual_invalid_field_is_removed_and_requires_review(self) -> None:
        models = SeededFixtureModels()

        def leave_unsupported_phone(prompt: dict) -> dict:
            result = models.verify(prompt)
            if prompt["candidateIdentity"]["program"] == "Rapid Re-Housing":
                result["fieldDecisions"]["phone"] = {
                    "action": "mark-conflicting",
                    "reason": "Fixture returns an invalid one-value conflict",
                    "alternatives": [
                        {"value": "480-555-0199", "evidenceIds": ["1"]}
                    ],
                }
            return result

        pipeline = self.pipeline(
            models,
            "model-fixture-residual-field-remediation",
            verify=leave_unsupported_phone,
        )
        result = pipeline.run()
        self.assertTrue(result.quality_gate_passed)
        self.assertEqual(5, result.passed_count)
        self.assertEqual(3, result.needs_review_count)
        self.assertEqual(0, result.failed_count)
        with self.store.connect() as connection:
            row = connection.execute(
                """SELECT verification.verified_dossier_json, verification.findings_json
                   FROM optimization_verifications AS verification
                   JOIN optimization_candidate_dossiers AS dossier
                     ON dossier.id = verification.dossier_id
                   JOIN optimization_evidence_packets AS packet
                     ON packet.id = dossier.packet_id
                   WHERE dossier.run_id = ?
                     AND packet.identity_key = 'a new leaf::rapid re housing'""",
                (result.run_id,),
            ).fetchone()
        verified = json.loads(row["verified_dossier_json"])
        findings = json.loads(row["findings_json"])
        self.assertEqual("unknown", verified["fields"]["phone"]["status"])
        self.assertEqual([], findings["finalDeterministicFindings"])
        self.assertEqual(
            "deterministic-field-downgrade",
            findings["deterministicRemediationFindings"][0]["code"],
        )

    def test_verifier_failure_resumes_without_repeating_extraction(self) -> None:
        models = SeededFixtureModels()
        failures = 0

        def fail_first_verification(prompt: dict) -> dict:
            nonlocal failures
            if failures == 0:
                failures += 1
                raise RuntimeError("fixture verifier failure")
            return models.verify(prompt)

        with self.assertRaisesRegex(OptimizationModelError, "fixture verifier failure"):
            self.pipeline(
                models,
                "model-fixture-resume",
                verify=fail_first_verification,
            ).run()
        self.assertEqual(1, len(models.extract_prompts))

        result = self.pipeline(models, "model-fixture-resume").run()
        self.assertTrue(result.quality_gate_passed)
        self.assertEqual(8, len(models.extract_prompts))
        with self.store.connect() as connection:
            first_packet_attempts = connection.execute(
                """SELECT operation, status FROM optimization_model_attempts
                   WHERE run_id = ? ORDER BY id LIMIT 3""",
                (result.run_id,),
            ).fetchall()
        self.assertEqual(
            [("extract", "completed"), ("verify", "failed"), ("verify", "completed")],
            [(row["operation"], row["status"]) for row in first_packet_attempts],
        )

    def test_extractor_failure_is_retained_and_retried(self) -> None:
        models = SeededFixtureModels()
        failures = 0

        def fail_first_extraction(prompt: dict) -> dict:
            nonlocal failures
            if failures == 0:
                failures += 1
                raise RuntimeError("fixture extractor failure")
            return models.extract(prompt)

        with self.assertRaisesRegex(OptimizationModelError, "fixture extractor failure"):
            self.pipeline(
                models,
                "model-fixture-extractor-resume",
                extract=fail_first_extraction,
            ).run()
        result = self.pipeline(models, "model-fixture-extractor-resume").run()
        self.assertTrue(result.quality_gate_passed)
        with self.store.connect() as connection:
            attempts = connection.execute(
                """SELECT operation, status FROM optimization_model_attempts
                   WHERE run_id = ? ORDER BY id LIMIT 3""",
                (result.run_id,),
            ).fetchall()
        self.assertEqual(
            [("extract", "failed"), ("extract", "completed"), ("verify", "completed")],
            [(row["operation"], row["status"]) for row in attempts],
        )

    def test_extractor_may_return_sparse_source_bindings_and_scout_restores_envelopes(
        self,
    ) -> None:
        models = SeededFixtureModels()

        def sparse_extract(prompt: dict) -> dict:
            dossier = models.extract(prompt)
            dossier["sources"] = [
                {
                    key: deepcopy(source[key])
                    for key in ("id", "supports", "contradicts")
                }
                for source in dossier["sources"]
            ]
            return dossier

        result = self.pipeline(
            models,
            "model-fixture-sparse-source-bindings",
            extract=sparse_extract,
        ).run()
        self.assertTrue(result.quality_gate_passed)

        with self.store.connect() as connection:
            dossiers = connection.execute(
                """SELECT dossier_json FROM optimization_candidate_dossiers
                   WHERE run_id = ? ORDER BY packet_id""",
                (result.run_id,),
            ).fetchall()
        for row in dossiers:
            for source in json.loads(row["dossier_json"])["sources"]:
                self.assertTrue(source["url"].startswith("https://"))
                self.assertIn("extract", source)
                self.assertIn("authority", source)
                self.assertIn("pageIdentityKey", source)

    def test_failed_model_output_and_usage_are_retained_for_diagnosis(self) -> None:
        models = SeededFixtureModels()

        def fail_with_raw_output(_prompt: dict) -> dict:
            raise OptimizationModelError(
                "fixture parse failure",
                raw_output="unfinished fixture output",
                usage={"completion_tokens": 99, "metered": False},
            )

        with self.assertRaisesRegex(OptimizationModelError, "fixture parse failure"):
            self.pipeline(
                models,
                "model-fixture-raw-failure",
                extract=fail_with_raw_output,
            ).run()

        with self.store.connect() as connection:
            attempt = connection.execute(
                """SELECT status, raw_output, usage_json, error
                   FROM optimization_model_attempts
                   WHERE operation = 'extract' ORDER BY id DESC LIMIT 1"""
            ).fetchone()
        self.assertEqual("failed", attempt["status"])
        self.assertEqual("unfinished fixture output", attempt["raw_output"])
        self.assertEqual(99, json.loads(attempt["usage_json"])["completion_tokens"])
        self.assertEqual("fixture parse failure", attempt["error"])

    def test_gap_audit_resume_does_not_repeat_model_work(self) -> None:
        models = SeededFixtureModels()
        interrupted = False

        def stop_after_gap_audit(event: dict) -> None:
            nonlocal interrupted
            if event["phase"] == "gap-audit" and not interrupted:
                interrupted = True
                raise RuntimeError("fixture gap audit interruption")

        with self.assertRaisesRegex(OptimizationModelError, "gap audit interruption"):
            self.pipeline(
                models,
                "model-fixture-gap-resume",
                progress=stop_after_gap_audit,
            ).run()
        self.assertEqual(8, len(models.extract_prompts))
        self.assertEqual(8, len(models.verify_prompts))

        result = self.pipeline(models, "model-fixture-gap-resume").run()
        self.assertEqual(1, result.gap_count)
        self.assertEqual(8, len(models.extract_prompts))
        self.assertEqual(8, len(models.verify_prompts))


if __name__ == "__main__":
    unittest.main()
