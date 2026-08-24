from __future__ import annotations

import ast
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FREEZE_SCRIPT = ROOT / "freeze-qwen-housing-corpus.py"


class FreezeQwenHousingCliTests(unittest.TestCase):
    def test_cli_accepts_and_passes_the_prior_lead_manifest(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(FREEZE_SCRIPT), "--help"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertIn("--prior-lead-manifest", completed.stdout)

        module = ast.parse(FREEZE_SCRIPT.read_text(encoding="utf-8"))
        pipeline_calls = [
            node
            for node in ast.walk(module)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "OptimizationDiscoveryPipeline"
        ]
        self.assertEqual(1, len(pipeline_calls))
        keyword_values = {
            keyword.arg: keyword.value for keyword in pipeline_calls[0].keywords
        }
        self.assertIn("prior_lead_manifest", keyword_values)
        self.assertIsInstance(keyword_values["prior_lead_manifest"], ast.Name)
        self.assertEqual(
            "prior_lead_manifest",
            keyword_values["prior_lead_manifest"].id,
        )


if __name__ == "__main__":
    unittest.main()
