from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DSHCompositionTests(unittest.TestCase):
    def test_local_qwen_patch_resolves_with_ddgs_and_without_deepseek(self) -> None:
        dsh = ROOT / "dsh-runtime" / "node_modules" / ".bin" / "dsh"
        if not dsh.is_file():
            self.skipTest("run ./install-dsh.sh for the composition integration test")
        with tempfile.TemporaryDirectory() as directory:
            completed = subprocess.run(
                [
                    str(dsh),
                    "--profile",
                    "headless",
                    "--patch",
                    str(ROOT / "dsh-research.patch.yml"),
                    "--patch",
                    str(ROOT / "dsh-local-qwen.patch.yml"),
                    "--dump-config",
                ],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
                env={**os.environ, "DSH_HOME": directory, "NO_COLOR": "1"},
            )
        self.assertEqual(0, completed.returncode, completed.stderr)
        output = completed.stdout
        self.assertIn("provider: qwen-local", output)
        self.assertIn("model: mlx-community/Qwen3.8-27B-4bit", output)
        self.assertIn("baseURL: http://127.0.0.1:8080/v1", output)
        self.assertIn("apiKeyEnv: RESOURCE_SCOUT_LOCAL_QWEN_TOKEN", output)
        self.assertIn("thinkingFormat: openai", output)
        self.assertIn("supportsReasoningEffort: true", output)
        self.assertIn("searchProvider: ddgs", output)
        self.assertIn("fetchProvider: safe-http", output)
        self.assertIn("name: '@resource-scout/dsh-web-search-ddgs'", output)
        self.assertIn("name: '@resource-scout/dsh-web-fetch-safe'", output)
        self.assertRegex(output, r"id: web-search-deepseek[\s\S]*?disabled: true")
        self.assertRegex(output, r"id: tool-web[\s\S]*?fetch: true")
        self.assertIn("fetchMaxOutputChars: 30000", output)
        self.assertRegex(output, r"maxCalls: 2")
        self.assertRegex(output, r"maxCalls: 5")
        self.assertRegex(output, r"use no more than two targeted web\s+searches")

    def test_local_qwen_plugins_mount_in_the_headless_profile(self) -> None:
        dsh = ROOT / "dsh-runtime" / "node_modules" / ".bin" / "dsh"
        ddgs_python = ROOT / "dsh-runtime" / ".venv-ddgs" / "bin" / "python"
        if not dsh.is_file() or not ddgs_python.is_file():
            self.skipTest("run ./install-local-qwen.sh for the live composition test")
        with tempfile.TemporaryDirectory() as directory:
            completed = subprocess.run(
                [
                    str(dsh),
                    "--profile",
                    "headless",
                    "--patch",
                    str(ROOT / "dsh-research.patch.yml"),
                    "--patch",
                    str(ROOT / "dsh-local-qwen.patch.yml"),
                    "--help",
                ],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
                env={
                    **os.environ,
                    "DSH_HOME": directory,
                    "DSH_TOOLS_MODE": "native",
                    "RESOURCE_SCOUT_DDGS_PYTHON": str(ddgs_python),
                    "NO_COLOR": "1",
                },
            )
        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertIn("Answer one task", completed.stdout)


if __name__ == "__main__":
    unittest.main()
