from __future__ import annotations

import os
import runpy
import unittest
from pathlib import Path


class CoordinatorTests(unittest.TestCase):
    def test_coordinator_explicitly_removes_deepseek_key(self) -> None:
        source = (Path(__file__).parents[1] / "run-qwen-quantization-comparison.py").read_text()
        self.assertIn('environment.pop("DEEPSEEK_API_KEY", None)', source)
        self.assertEqual(["4-bit", "8-bit"], list(__import__(
            "resource_research_agent.optimization_runtime", fromlist=["PINNED_MODELS"]
        ).PINNED_MODELS))


if __name__ == "__main__":
    unittest.main()
