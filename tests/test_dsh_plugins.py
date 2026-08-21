from __future__ import annotations

import shutil
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DSHPluginTests(unittest.TestCase):
    def test_safe_fetch_cli_uses_the_installed_dsh_plugin(self) -> None:
        helper = (ROOT / "dsh-plugins" / "web-fetch-safe" / "fetch-cli.js").read_text()
        self.assertIn(
            "dsh-runtime/node_modules/@resource-scout/dsh-web-fetch-safe/index.js",
            helper,
        )

    def test_ddgs_provider_node_suite(self) -> None:
        node = shutil.which("node")
        installed = (
            ROOT
            / "dsh-runtime"
            / "node_modules"
            / "@resource-scout"
            / "dsh-web-search-ddgs"
            / "index.js"
        )
        if not node or not installed.is_file():
            self.skipTest("run ./install-dsh.sh for the DSH plugin integration tests")
        completed = subprocess.run(
            [node, "--test", str(ROOT / "tests" / "ddgs_provider.test.mjs")],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)

    def test_safe_fetch_provider_node_suite(self) -> None:
        node = shutil.which("node")
        installed = (
            ROOT
            / "dsh-runtime"
            / "node_modules"
            / "@resource-scout"
            / "dsh-web-fetch-safe"
            / "index.js"
        )
        if not node or not installed.is_file():
            self.skipTest("run ./install-local-qwen.sh for the DSH plugin integration tests")
        completed = subprocess.run(
            [node, "--test", str(ROOT / "tests" / "safe_fetch.test.mjs")],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)


if __name__ == "__main__":
    unittest.main()
