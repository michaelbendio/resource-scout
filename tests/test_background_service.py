from __future__ import annotations

import plistlib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class BackgroundServiceTests(unittest.TestCase):
    def test_launch_agent_template_has_persistent_private_launcher(self) -> None:
        template = (ROOT / "service/com.michaelbendio.resource-research-agent.plist.template").read_text()
        rendered = template.replace("__REPOSITORY__", "/tmp/resource-research-agent").replace(
            "__PYTHON__", "/opt/homebrew/bin/python3"
        )
        plist = plistlib.loads(rendered.encode())

        self.assertEqual("com.michaelbendio.resource-research-agent", plist["Label"])
        self.assertEqual(
            ["/bin/sh", "/tmp/resource-research-agent/run-dsh-tailscale.sh"],
            plist["ProgramArguments"],
        )
        self.assertTrue(plist["RunAtLoad"])
        self.assertTrue(plist["KeepAlive"])
        self.assertEqual("/opt/homebrew/bin/python3", plist["EnvironmentVariables"]["RESOURCE_RESEARCH_PYTHON"])

    def test_background_launcher_requires_saved_key_and_uses_tailscale(self) -> None:
        launcher = (ROOT / "run-dsh-tailscale.sh").read_text()

        self.assertIn("RESOURCE_RESEARCH_RUNNER=./run-tailscale.sh", launcher)
        self.assertIn("RESOURCE_RESEARCH_KEYCHAIN_ONLY=1", launcher)
        self.assertIn('exec ./run-dsh.sh "$@"', launcher)

    def test_service_control_preserves_data_when_uninstalled(self) -> None:
        control = (ROOT / "background-service.sh").read_text()

        self.assertNotIn('rm -rf "$REPOSITORY/data"', control)
        self.assertIn('rm -f "$PLIST"', control)
        self.assertIn("Research data and logs were left in place.", control)


if __name__ == "__main__":
    unittest.main()
