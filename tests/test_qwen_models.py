from __future__ import annotations

import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from resource_research_agent.optimization import HOUSING_FACTUAL_FIELDS
from resource_research_agent.optimization_models import (
    OptimizationModelError,
    OptimizationModelPipeline,
    remediate_invalid_factual_fields,
    restore_frozen_source_envelopes,
)
from resource_research_agent.optimization_pipeline import OptimizationDiscoveryPipeline
from resource_research_agent.review_export import build_optimization_review_copy
from resource_research_agent.storage import ResearchStore
from tests.test_qwen_discovery import FixtureProviders


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
            "promptPolicyVersion": "candidate-dossier-and-verifier-v1",
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
            for field in HOUSING_FACTUAL_FIELDS
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
        elif program == "Brian Garcia Welcome Center":
            components = [
                identity_key,
                "central arizona shelter services::emergency shelter",
            ]
        elif program == "Halle Women's Center":
            components = [
                identity_key,
                "umom new day centers::family shelter",
            ]
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
        elif program == "State Shelter Referral":
            identity_key = "arizona housing directory::state shelter referral"
            identity = {
                **identity,
                "organization": "Arizona Housing Directory",
                "identityKey": identity_key,
            }
            components = [identity_key]
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
        verified = deepcopy(prompt["dossier"])
        identity = prompt["candidateIdentity"]
        verified["candidateIdentity"] = {
            "organization": identity["organization"],
            "program": identity["program"],
            "identityKey": identity["identityKey"],
            "componentIdentityKeys": [identity["identityKey"]],
        }
        verified["sources"] = source_records({"sources": prompt["sources"]})
        for finding in prompt["deterministicFindings"]:
            field = finding.get("field")
            if field in verified["fields"]:
                verified["fields"][field] = {
                    "status": "unknown",
                    "reason": f"Removed by verifier: {finding['code']}",
                }
        return {
            "status": "passed",
            "verifiedDossier": verified,
            "findings": [
                {
                    "code": finding["code"],
                    "action": "removed-or-separated",
                }
                for finding in prompt["deterministicFindings"]
            ],
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
        )
        self.assertEqual("unknown", remediated["fields"]["phone"]["status"])
        self.assertEqual("deterministic-field-downgrade", findings[0]["code"])
        self.assertEqual("phone", findings[0]["field"])
        self.assertEqual({"status": "supported", "value": "480-555-0100"}, dossier["fields"]["phone"])

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
        self.assertEqual(8, result.passed_count)
        self.assertEqual(0, result.needs_review_count)
        self.assertEqual(0, result.failed_count)
        self.assertEqual(8 * len(HOUSING_FACTUAL_FIELDS), result.unknown_field_count)
        self.assertEqual(1, result.gap_count)
        self.assertEqual(8, len(models.extract_prompts))
        self.assertEqual(8, len(models.verify_prompts))
        self.assertTrue(
            all(prompt["operation"] == "extract-candidate-dossier" for prompt in models.extract_prompts)
        )
        self.assertTrue(all(prompt.get("outputContract") for prompt in models.extract_prompts))
        self.assertTrue(
            all(
                "Use only program or organization as an evidence-binding scope."
                in prompt["instructions"]
                for prompt in models.extract_prompts
            )
        )
        self.assertTrue(
            all(
                prompt["operation"] == "verify-candidate-dossier-fresh-context"
                for prompt in models.verify_prompts
            )
        )
        self.assertTrue(all(prompt.get("outputContract") for prompt in models.verify_prompts))
        detected_codes = {
            finding["code"]
            for prompt in models.verify_prompts
            for finding in prompt["deterministicFindings"]
        }
        self.assertTrue(
            {
                "cross-program-evidence",
                "multiple-program-identities",
                "source-does-not-support-field",
                "contradicted-field",
                "missing-evidence",
                "packet-identity-mismatch",
                "altered-source",
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
        self.assertTrue(all(len(candidate["unknowns"]) == len(HOUSING_FACTUAL_FIELDS) for candidate in candidates))

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
                result["verifiedDossier"]["candidateIdentity"]["identityKey"] = "wrong::program"
            return result

        mixed_pipeline = self.pipeline(
            mixed_models,
            "model-fixture-mixed-verification-statuses",
            verify=mixed_statuses,
        )
        mixed_result = mixed_pipeline.run()
        self.assertFalse(mixed_result.quality_gate_passed)
        self.assertEqual(6, mixed_result.passed_count)
        self.assertEqual(1, mixed_result.needs_review_count)
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
        self.assertEqual(1, completeness["needsReviewCount"])
        self.assertEqual(1, completeness["failedCount"])
        self.assertEqual(1, quality["verificationNeedsReview"])
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

    def test_residual_invalid_field_is_removed_and_requires_review(self) -> None:
        models = SeededFixtureModels()

        def leave_unsupported_phone(prompt: dict) -> dict:
            result = models.verify(prompt)
            if prompt["candidateIdentity"]["program"] == "Rapid Re-Housing":
                source_id = result["verifiedDossier"]["sources"][0]["id"]
                result["verifiedDossier"]["fields"]["phone"] = {
                    "status": "supported",
                    "value": "480-555-0199",
                    "evidenceIds": [source_id],
                }
            return result

        pipeline = self.pipeline(
            models,
            "model-fixture-residual-field-remediation",
            verify=leave_unsupported_phone,
        )
        result = pipeline.run()
        self.assertTrue(result.quality_gate_passed)
        self.assertEqual(7, result.passed_count)
        self.assertEqual(1, result.needs_review_count)
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
