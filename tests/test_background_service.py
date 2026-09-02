from __future__ import annotations

import plistlib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class BackgroundServiceTests(unittest.TestCase):
    def _render(self, name: str) -> dict:
        template = (ROOT / "service" / name).read_text()
        rendered = template.replace("__REPOSITORY__", "/tmp/resource-research-agent").replace(
            "__PYTHON__", "/opt/homebrew/bin/python3"
        )
        return plistlib.loads(rendered.encode())

    def test_scout_service_uses_the_tailscale_launcher(self) -> None:
        plist = self._render("com.michaelbendio.resource-research-agent.plist.template")

        self.assertEqual("com.michaelbendio.resource-research-agent", plist["Label"])
        self.assertEqual(
            ["/bin/sh", "/tmp/resource-research-agent/run-tailscale.sh"],
            plist["ProgramArguments"],
        )
        self.assertTrue(plist["RunAtLoad"])
        self.assertTrue(plist["KeepAlive"])
        self.assertEqual(
            "/opt/homebrew/bin/python3",
            plist["EnvironmentVariables"]["RESOURCE_SCOUT_PYTHON"],
        )

    def test_service_control_manages_only_scout_and_preserves_data(self) -> None:
        control = (ROOT / "background-service.sh").read_text()

        self.assertNotIn("QWEN_", control)
        self.assertNotIn("DeepSeek", control)
        self.assertNotIn('rm -rf "$REPOSITORY/data"', control)
        self.assertIn('rm -f "$APP_PLIST"', control)
        self.assertIn("Research data and logs were left in place", control)


if __name__ == "__main__":
    unittest.main()
