from __future__ import annotations

import json
import os
import tempfile
import time
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from resource_research_agent.agents import HermesCLIAdapter
from resource_research_agent.importer import ResourcePackageImporter
from resource_research_agent.research import ResearchCoordinator
from resource_research_agent.storage import ResearchStore


class ResearchWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.store = ResearchStore(self.root / "research.sqlite3")
        package_path = self.root / "resources.zip"
        package = {
            "schemaVersion": 3,
            "categories": [{"id": "housing", "name": "Housing"}],
            "resources": [{
                "id": "known-home", "name": "Known Home", "categories": ["housing"],
                "website": "https://known.example.org", "address": "1 Main St, Provo, UT",
            }],
        }
        with zipfile.ZipFile(package_path, "w") as archive:
            archive.writestr("tso-resources.json", json.dumps(package))
        self.store.save_import(ResourcePackageImporter().read(package_path))

    def tearDown(self) -> None:
        self.directory.cleanup()

    def test_demo_research_run_creates_separate_candidate_and_review_lesson(self) -> None:
        self.store.save_settings({"adapter": "demo"})
        coordinator = ResearchCoordinator(self.store)
        run = coordinator.start("Find a transitional housing option", "known-home")
        for _ in range(200):
            current = self.store.get_run(run["id"])
            if current and current["status"] in {"completed", "failed"}:
                break
            time.sleep(0.01)
        self.assertEqual("completed", current["status"])
        discoveries = self.store.list_discoveries()
        self.assertEqual(1, len(discoveries))
        self.assertEqual("candidate", discoveries[0]["status"])
        self.assertEqual(run["id"], discoveries[0]["runId"])
        reviewed = self.store.review_discovery(discoveries[0]["id"], "research-further", "Verify pet policy")
        self.assertEqual("research-further", reviewed["status"])
        lesson = self.store.save_lesson(
            "Verify pet policy", source="human-feedback", discovery_id=discoveries[0]["id"]
        )
        self.assertEqual("active", lesson["status"])
        self.assertEqual(1, len(self.store.list_lessons(active_only=True)))
        self.assertIsNotNone(self.store.full_resource(1, "known-home"))

    def test_hermes_cli_adapter_uses_oneshot_and_parses_json(self) -> None:
        fake = self.root / "fake_hermes.py"
        fake.write_text(
            "import json, pathlib, sys\n"
            "if '--version' in sys.argv:\n"
            "    print('Hermes 0.test')\n"
            "    raise SystemExit(0)\n"
            "usage = pathlib.Path(sys.argv[sys.argv.index('--usage-file') + 1])\n"
            "usage.write_text(json.dumps({'provider': 'fake', 'completed': True}))\n"
            "print(json.dumps({'summary':'done','candidates':[{'name':'New Place'}],'lessons':['Prefer direct services']}))\n",
            encoding="utf-8",
        )
        hermes_home = self.root / "hermes-home"
        hermes_home.mkdir()
        (hermes_home / "config.yaml").write_text("model:\n  default: fake\n", encoding="utf-8")
        (hermes_home / ".env").write_text("FAKE_API_KEY=present\n", encoding="utf-8")
        settings = {"command": f"{os.sys.executable} {fake}", "timeoutSeconds": 30}
        with patch.dict(os.environ, {"HERMES_HOME": str(hermes_home)}):
            adapter = HermesCLIAdapter(settings)
            self.assertTrue(adapter.status()["ready"])
            result = adapter.run("Research Housing")
        self.assertEqual("New Place", result.result["candidates"][0]["name"])
        self.assertEqual("Prefer direct services", result.result["lessons"][0]["text"])
        self.assertEqual("fake", result.usage["provider"])


if __name__ == "__main__":
    unittest.main()
