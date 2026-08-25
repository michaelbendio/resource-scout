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

    def test_scout_service_uses_the_unmetered_tailscale_launcher(self) -> None:
        plist = self._render("com.michaelbendio.resource-research-agent.plist.template")

        self.assertEqual("com.michaelbendio.resource-research-agent", plist["Label"])
        self.assertEqual(
            ["/bin/sh", "/tmp/resource-research-agent/run-qwen-tailscale.sh"],
            plist["ProgramArguments"],
        )
        self.assertTrue(plist["RunAtLoad"])
        self.assertTrue(plist["KeepAlive"])
        self.assertEqual(
            "/opt/homebrew/bin/python3",
            plist["EnvironmentVariables"]["RESOURCE_RESEARCH_PYTHON"],
        )

    def test_qwen_service_is_separate_persistent_and_loopback_launcher_owned(self) -> None:
        plist = self._render("com.michaelbendio.resource-scout-local-qwen.plist.template")

        self.assertEqual("com.michaelbendio.resource-scout-local-qwen", plist["Label"])
        self.assertEqual(
            ["/bin/sh", "/tmp/resource-research-agent/run-local-qwen-service.sh"],
            plist["ProgramArguments"],
        )
        self.assertTrue(plist["RunAtLoad"])
        self.assertTrue(plist["KeepAlive"])
        self.assertIn("local-qwen-service.log", plist["StandardOutPath"])

        launcher = (ROOT / "run-local-qwen-service.sh").read_text()
        self.assertIn("serve --quantization 8-bit --validate", launcher)

    def test_production_launcher_enforces_unmetered_qwen_without_loading_a_key(self) -> None:
        launcher = (ROOT / "run-qwen-tailscale.sh").read_text()

        self.assertIn("RESOURCE_SCOUT_REQUIRE_UNMETERED=1", launcher)
        self.assertIn("unset DEEPSEEK_API_KEY", launcher)
        self.assertIn('exec ./run-tailscale.sh "$@"', launcher)
        self.assertNotIn("run-dsh.sh", launcher)

    def test_service_control_manages_both_services_and_preserves_data(self) -> None:
        control = (ROOT / "background-service.sh").read_text()

        self.assertIn("QWEN_PLIST=", control)
        self.assertIn('bootstrap_one "$QWEN_SERVICE" "$QWEN_PLIST"', control)
        self.assertNotIn("find-generic-password", control)
        self.assertNotIn('rm -rf "$REPOSITORY/data"', control)
        self.assertIn('rm -f "$APP_PLIST" "$QWEN_PLIST"', control)
        self.assertIn("model cache, credentials, and logs were left in place", control)


if __name__ == "__main__":
    unittest.main()
