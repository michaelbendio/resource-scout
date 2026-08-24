from __future__ import annotations

import os
import runpy
import unittest
from pathlib import Path


class CoordinatorTests(unittest.TestCase):
    def test_coordinator_explicitly_removes_deepseek_key(self) -> None:
        source = (Path(__file__).parents[1] / "run-qwen-quantization-comparison.py").read_text()
        self.assertIn('environment.pop("DEEPSEEK_API_KEY", None)', source)
        self.assertNotIn("subprocess", source)
        self.assertNotIn("run-qwen-housing-model.py", source)
        self.assertIn("will not start inference under a newer policy", source)

    def test_corrected_comparison_uses_separate_v9_provenance(self) -> None:
        root = Path(__file__).parents[1]
        coordinator = (root / "run-qwen-quantization-comparison.py").read_text()
        runner = (root / "run-qwen-housing-model.py").read_text()
        self.assertIn("reviewed-corpus-v9", coordinator)
        self.assertIn("quantization-v9", coordinator)
        self.assertIn("verifier-patch-v10", runner)
        self.assertIn("verifier-decision-patch-v2", runner)
        self.assertIn('"modelMaxCompletionTokens": LOCAL_QWEN_MAX_COMPLETION_TOKENS', runner)
        self.assertIn('"localQwenProxyTimeoutSeconds": 7200', runner)

    def test_calibration_entrypoints_derive_category_and_stage_from_frozen_inputs(self) -> None:
        root = Path(__file__).parents[1]
        freezer = (root / "freeze-qwen-housing-corpus.py").read_text()
        runner = (root / "run-qwen-housing-model.py").read_text()
        self.assertNotIn('ResourcePackageImporter("housing")', freezer)
        self.assertNotIn('"stageKey": "urgent-access"', freezer)
        self.assertIn('category_id = str(plan["categoryId"])', freezer)
        self.assertIn("configuration['targetCategoryId']", runner)
        self.assertIn("configuration['stageKey']", runner)
        self.assertNotIn("mesa-housing-urgent-", runner)

    def test_comparison_recompute_uses_only_persisted_runs(self) -> None:
        source = (
            Path(__file__).parents[1] / "recompute-qwen-quantization-comparison.py"
        ).read_text()
        self.assertIn("create_model_neutral_comparison", source)
        self.assertIn("recomputedFromPersistedRuns", source)
        self.assertNotIn("run-qwen-housing-model.py", source)
        self.assertNotIn("mlx_lm", source)

    def test_verification_recompute_uses_only_persisted_outputs(self) -> None:
        source = (
            Path(__file__).parents[1] / "recompute-qwen-verifications.py"
        ).read_text()
        self.assertIn("recompute_persisted_verifications", source)
        self.assertIn('"modelInferenceCalls": result.model_inference_calls', source)
        self.assertIn('"searchCalls": 0', source)
        self.assertIn('"fetchCalls": 0', source)
        self.assertNotIn("LocalQwenJSONClient", source)
        self.assertNotIn("mlx_lm", source)


if __name__ == "__main__":
    unittest.main()
