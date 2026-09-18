from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from resource_research_agent.importer import ResourcePackageImporter
from resource_research_agent.pairwise_supervisor import _monitor_specs, clone_import_baseline
from resource_research_agent.storage import ResearchStore


class PairwiseSupervisorTests(unittest.TestCase):
    def test_monitor_specs_assign_one_port_per_profile(self) -> None:
        specs = _monitor_specs(Path("/tmp/pairwise"), 8766)
        self.assertEqual(8766, specs["codex-grok"]["port"])
        self.assertEqual("http://127.0.0.1:8766", specs["codex-grok"]["url"])
        self.assertEqual(8767, specs["codex-claude"]["port"])
        self.assertEqual("http://127.0.0.1:8767", specs["codex-claude"]["url"])
        self.assertEqual(8768, specs["claude-grok"]["port"])
        self.assertEqual("http://127.0.0.1:8768", specs["claude-grok"]["url"])

    def test_clone_import_baseline_preserves_clean_package_order(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = root / "st-george-resource-package.zip"
            with zipfile.ZipFile(package, "w") as archive:
                archive.writestr("tso-resources.json", json.dumps({
                    "resourcePackageSchemaVersion": 3,
                    "packageVersion": 1,
                    "officeName": "St George TSO",
                    "serviceArea": "St George",
                    "categories": [
                        {"id": "addiction", "name": "Addiction", "filters": []},
                        {"id": "education", "name": "Education", "filters": []},
                        {"id": "employment", "name": "Employment", "filters": []},
                    ],
                    "forGroups": [],
                    "resources": [],
                }))
            source_path = root / "source.sqlite3"
            source = ResearchStore(source_path)
            import_id = source.save_import(ResourcePackageImporter(None).read(package))

            destination_path = root / "destination.sqlite3"
            cloned_id = clone_import_baseline(
                source_path,
                import_id,
                destination_path,
            )
            self.assertEqual(import_id, cloned_id)

            destination = ResearchStore(destination_path)
            source_summary = source.import_summary(import_id)
            destination_summary = destination.import_summary(cloned_id)
            self.assertIsNotNone(source_summary)
            self.assertIsNotNone(destination_summary)
            self.assertEqual(
                source_summary["sourceSha256"],
                destination_summary["sourceSha256"],
            )
            self.assertEqual(
                ["addiction", "education", "employment"],
                [item["id"] for item in destination_summary["categories"]],
            )
            self.assertEqual([], destination.list_focused_research_jobs(cloned_id))


if __name__ == "__main__":
    unittest.main()
