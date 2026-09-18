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

    def test_worker_telemetry_summary_tracks_turns_failures_and_velocity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = root / "telemetry-resource-package.zip"
            with zipfile.ZipFile(package, "w") as archive:
                archive.writestr("tso-resources.json", json.dumps({
                    "resourcePackageSchemaVersion": 3,
                    "packageVersion": 1,
                    "officeName": "Test TSO",
                    "serviceArea": "Test County",
                    "categories": [
                        {"id": "food", "name": "Food", "filters": []},
                    ],
                    "forGroups": [],
                    "resources": [],
                }))
            store = ResearchStore(root / "telemetry.sqlite3")
            import_id = store.save_import(ResourcePackageImporter(None).read(package))
            store.record_worker_telemetry(
                import_id=import_id,
                profile="codex-grok",
                provider="Grok",
                role="challenger",
                category_id="food",
                category_label="Food",
                attempt=1,
                model="grok-test",
                outcome="completed",
                started_at="2026-09-18T00:00:00+00:00",
                completed_at="2026-09-18T00:01:00+00:00",
                elapsed_ms=60000,
                lead_count=3,
                response_bytes=500,
                usage={"numTurns": 7, "webSearchRequests": 4},
            )
            store.record_worker_telemetry(
                import_id=import_id,
                profile="codex-grok",
                provider="Grok",
                role="challenger",
                category_id="food",
                category_label="Food",
                attempt=2,
                model="grok-test",
                outcome="failed",
                started_at="2026-09-18T00:01:00+00:00",
                completed_at="2026-09-18T00:01:30+00:00",
                elapsed_ms=30000,
                error="test failure",
            )
            summary = store.worker_telemetry_summary(import_id)
            self.assertEqual(2, summary["attemptCount"])
            provider = summary["providers"][0]
            self.assertEqual("Grok", provider["provider"])
            self.assertEqual(2, provider["attempts"])
            self.assertEqual(1, provider["completedAttempts"])
            self.assertEqual(1, provider["failedAttempts"])
            self.assertIsNone(provider["turnCount"])
            self.assertIsNone(provider["webSearchRequests"])
            self.assertEqual(7, provider["observedTurnCount"])
            self.assertEqual(4, provider["observedWebSearchRequests"])
            self.assertEqual(1, provider["turnCountKnownAttempts"])
            self.assertEqual(1, provider["webSearchKnownAttempts"])
            self.assertEqual(3, provider["leadCount"])
            self.assertEqual(1.5, provider["elapsedMinutes"])
            self.assertEqual(1.0, provider["successfulElapsedMinutes"])
            self.assertEqual(0.5, provider["failedElapsedMinutes"])
            self.assertEqual(2.0, provider["rawLeadsPerWorkerMinute"])
            self.assertEqual(3.0, provider["rawLeadsPerSuccessfulWorkerMinute"])

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
