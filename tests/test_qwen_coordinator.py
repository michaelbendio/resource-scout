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
        self.assertIn("verifier-decision-patch-v1", runner)
        self.assertIn('"modelMaxCompletionTokens": LOCAL_QWEN_MAX_COMPLETION_TOKENS', runner)
        self.assertIn('"localQwenProxyTimeoutSeconds": 7200', runner)

    def test_comparison_recompute_uses_only_persisted_runs(self) -> None:
        source = (
            Path(__file__).parents[1] / "recompute-qwen-quantization-comparison.py"
        ).read_text()
        self.assertIn("create_model_neutral_comparison", source)
        self.assertIn("recomputedFromPersistedRuns", source)
        self.assertNotIn("run-qwen-housing-model.py", source)
        self.assertNotIn("mlx_lm", source)


if __name__ == "__main__":
    unittest.main()
