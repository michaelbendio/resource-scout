from __future__ import annotations

import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from resource_research_agent.optimization import canonical_json, sha256_json
from resource_research_agent.optimization_comparison import (
    OptimizationComparisonError,
    _quality_metrics,
    _quality_vector,
    create_model_neutral_comparison,
    reveal_timing_and_decide,
)
from resource_research_agent.optimization_models import (
    OptimizationModelPipeline,
    recompute_model_evaluation_audits,
)
from resource_research_agent.optimization_pipeline import OptimizationDiscoveryPipeline
from resource_research_agent.storage import ResearchStore
from tests.test_qwen_discovery import FixtureProviders
from tests.test_qwen_models import SeededFixtureModels, model_configuration


def quantized_configuration(providers: FixtureProviders, label: str, quantization: str) -> dict:
    value = model_configuration(providers, label)
    value["quantization"] = quantization
    value["modelArtifact"] = f"mlx-community/Qwen3.8-27B-{quantization.replace('-', '')}"
    return value


class QuantizationComparisonTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.store = ResearchStore(Path(self.temporary.name) / "research.sqlite3")
        self.providers = FixtureProviders()
        self.corpus = OptimizationDiscoveryPipeline(
            self.store,
            self.providers.configuration("comparison-fixture-discovery"),
            search=self.providers.search,
            fetch=self.providers.fetch,
            resolve_identity=self.providers.resolve,
            existing_resources=self.providers.fixture["existingResources"],
        ).run()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def run_model(self, quantization: str) -> int:
        models = SeededFixtureModels()
        return OptimizationModelPipeline(
            self.store,
            quantized_configuration(
                self.providers, f"comparison-{quantization}", quantization
            ),
            self.corpus.corpus_id,
            extract=models.extract,
            verify=models.verify,
        ).run().run_id

    def test_model_neutral_report_precedes_timing_and_tie_selects_four_bit(self) -> None:
        four_run = self.run_model("4-bit")
        eight_run = self.run_model("8-bit")
        comparison = create_model_neutral_comparison(
            self.store,
            label="fixture-fair-comparison",
            four_bit_run_id=four_run,
            eight_bit_run_id=eight_run,
        )

        encoded = json.dumps(comparison.report)
        self.assertTrue(comparison.report["identicalFrozenPackets"])
        self.assertTrue(comparison.report["timingConcealed"])
        self.assertTrue(comparison.report["modelIdentityConcealed"])
        self.assertEqual("tie", comparison.report["qualityWinner"])
        self.assertNotIn("4-bit", encoded)
        self.assertNotIn("8-bit", encoded)
        self.assertNotIn("elapsed", encoded.casefold())

        revealed = reveal_timing_and_decide(self.store, comparison.comparison_id)
        self.assertEqual("4-bit", revealed["decision"]["selectedQuantization"])
        self.assertIn("tie rule", revealed["decision"]["rationale"])
        with self.store.connect() as connection:
            row = connection.execute(
                "SELECT * FROM optimization_comparisons WHERE id = ?",
                (comparison.comparison_id,),
            ).fetchone()
        self.assertEqual("decided", row["status"])
        self.assertTrue(json.loads(row["timing_json"]))
        self.assertEqual(
            comparison.report, json.loads(row["priorities_one_through_four_json"])
        )

    def test_comparison_rejects_noncompleted_or_mismatched_provenance(self) -> None:
        four_run = self.run_model("4-bit")
        with self.store.connect() as connection:
            configuration = quantized_configuration(
                self.providers, "other-eight-bit", "8-bit"
            )
            configuration_id = self.store.save_optimization_configuration(configuration)
            other_run = int(
                connection.execute(
                    """INSERT INTO optimization_runs (
                           created_at, label, configuration_id, corpus_id, run_kind,
                           status, current_phase
                       ) VALUES ('now', 'incomplete-eight', ?, ?, 'model-evaluation',
                                 'running', 'extract')""",
                    (configuration_id, self.corpus.corpus_id),
                ).lastrowid
            )
        with self.assertRaisesRegex(OptimizationComparisonError, "completed"):
            create_model_neutral_comparison(
                self.store,
                label="invalid-comparison",
                four_bit_run_id=four_run,
                eight_bit_run_id=other_run,
            )

    def test_needs_review_is_not_an_accuracy_failure_and_remains_usable(self) -> None:
        four_run = self.run_model("4-bit")
        eight_run = self.run_model("8-bit")
        with self.store.connect() as connection:
            verification = connection.execute(
                """SELECT verification.dossier_id, verification.verified_dossier_json
                   FROM optimization_verifications AS verification
                   JOIN optimization_candidate_dossiers AS dossier
                     ON dossier.id = verification.dossier_id
                   WHERE dossier.run_id = ? ORDER BY dossier.packet_id LIMIT 1""",
                (four_run,),
            ).fetchone()
            dossier_id = int(verification["dossier_id"])
            dossier = json.loads(verification["verified_dossier_json"])
            dossier["fields"]["description"] = {
                "status": "supported",
                "value": "Fixture candidate",
                "evidenceIds": [dossier["sources"][0]["id"]],
            }
            connection.execute(
                """UPDATE optimization_verifications
                   SET status = 'needs-review', verified_dossier_json = ?,
                       verified_dossier_sha256 = ? WHERE dossier_id = ?""",
                (canonical_json(dossier), sha256_json(dossier), dossier_id),
            )
        recompute_model_evaluation_audits(self.store, four_run)

        four = _quality_metrics(self.store, four_run)
        eight = _quality_metrics(self.store, eight_run)
        self.assertTrue(four["priority1Accuracy"]["gatePassed"])
        self.assertEqual(0, four["priority1Accuracy"]["failedCandidates"])
        self.assertEqual(3, four["priority1Accuracy"]["needsReviewCandidates"])
        self.assertEqual(4, four["priority1Accuracy"]["passedCandidates"])
        self.assertEqual(
            _quality_vector(four)[:3],
            _quality_vector(eight)[:3],
            "needs-review must not affect the accuracy axis",
        )
        self.assertEqual(1, four["priority4Candidates"]["usableCandidateCount"])
        self.assertEqual(1, four["priority4Candidates"]["usableWithReviewFlagCount"])
        with self.store.connect() as connection:
            quality = json.loads(
                connection.execute(
                    """SELECT report_json FROM optimization_audits
                       WHERE run_id = ? AND audit_type = 'quality-gate'""",
                    (four_run,),
                ).fetchone()["report_json"]
            )
        self.assertTrue(quality["passed"])
        self.assertEqual(0, quality["verificationFailures"])
        self.assertEqual(3, quality["verificationNeedsReview"])

    def test_persisted_comparison_label_cannot_change_provenance(self) -> None:
        four_run = self.run_model("4-bit")
        eight_run = self.run_model("8-bit")
        first = create_model_neutral_comparison(
            self.store,
            label="immutable-comparison-label",
            four_bit_run_id=four_run,
            eight_bit_run_id=eight_run,
        )
        repeated = create_model_neutral_comparison(
            self.store,
            label="immutable-comparison-label",
            four_bit_run_id=four_run,
            eight_bit_run_id=eight_run,
        )
        self.assertEqual(first.comparison_id, repeated.comparison_id)


if __name__ == "__main__":
    unittest.main()
