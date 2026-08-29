from __future__ import annotations

import io
import json
import tempfile
import threading
import unittest
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from resource_research_agent.candidate_package import (
    CANDIDATE_PACKAGE_MEMBER,
    build_candidate_package,
)
from resource_research_agent.duplicates import DuplicateIndex
from resource_research_agent.importer import ResourcePackageImporter
from resource_research_agent.manual_consolidation import (
    consolidate_manual_discovery,
    finish_manual_discovery,
)
from resource_research_agent.server import ResearchHTTPServer
from resource_research_agent.scout_progress import build_scout_progress
from resource_research_agent.storage import ResearchStore


class CandidatePackageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.store = ResearchStore(self.root / "research.sqlite3")
        package_path = self.root / "mesa-resource-package.zip"
        with zipfile.ZipFile(package_path, "w") as archive:
            archive.writestr("tso-resources.json", json.dumps({
                "resourcePackageSchemaVersion": 3,
                "packageVersion": 2,
                "officeName": "Mesa TSO",
                "serviceArea": "Mesa and Maricopa County, Arizona",
                "categories": [
                    {"id": "employment", "name": "Employment", "filters": []},
                    {"id": "food", "name": "Food", "filters": []},
                ],
                "forGroups": ["Veterans"],
                "resources": [],
            }))
        self.import_id = self.store.save_import(
            ResourcePackageImporter("Employment").read(package_path)
        )
        self.run_id = self.store.create_manual_discovery_run(
            "Find Employment resources",
            {"researchContext": {"mode": "package"}},
            self.import_id,
            target_category_id="employment",
            target_category_label="Employment",
        )
        self.store.save_manual_contribution(self.run_id, "ChatGPT", json.dumps({
            "leads": [{
                "organization": "Mesa Work Help",
                "program": "Career Center",
                "website": "https://example.org/work",
                "phone": "480-555-0100",
                "address": "1 Main Street, Mesa, AZ",
                "leadType": "program",
                "locationOrServiceArea": "Mesa",
                "whyRelevant": "Provides employment assistance.",
                "uncertainty": "Confirm hours.",
            }]
        }))
        consolidate_manual_discovery(self.store, self.run_id, DuplicateIndex(self.store))
        finish_manual_discovery(self.store, self.run_id)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_packages_all_completed_runs_for_one_location(self) -> None:
        package = build_candidate_package(
            self.store,
            self.import_id,
            exported_at=datetime(2026, 8, 28, 18, 0, tzinfo=timezone.utc),
        )
        self.assertEqual("mesa-candidates.zip", package.filename)
        self.assertEqual(1, package.data["candidatePackageSchemaVersion"])
        self.assertEqual("Mesa", package.data["location"]["name"])
        self.assertEqual([self.run_id], package.data["categoryManifest"][0]["runIds"])
        self.assertEqual("not-researched", package.data["categoryManifest"][1]["researchStatus"])
        self.assertEqual(1, len(package.data["runs"]))
        self.assertEqual(1, len(package.data["runs"][0]["candidates"]))
        self.assertEqual("ChatGPT", package.data["runs"][0]["sourceResponses"][0]["sourceLabel"])
        with zipfile.ZipFile(io.BytesIO(package.content)) as archive:
            self.assertEqual([CANDIDATE_PACKAGE_MEMBER], archive.namelist())
            embedded = json.loads(archive.read(CANDIDATE_PACKAGE_MEMBER))
        self.assertEqual(package.data["sourcePackage"], embedded["sourcePackage"])

    def test_http_endpoint_downloads_location_named_zip(self) -> None:
        web_dir = Path(__file__).resolve().parent.parent / "web"
        server = ResearchHTTPServer(("127.0.0.1", 0), self.store, web_dir)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            url = (
                f"http://127.0.0.1:{server.server_address[1]}"
                f"/api/candidate-package?importId={self.import_id}"
            )
            with urllib.request.urlopen(url, timeout=5) as response:
                self.assertEqual("application/zip", response.headers["Content-Type"])
                self.assertIn("mesa-candidates.zip", response.headers["Content-Disposition"])
                content = response.read()
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                self.assertIn(CANDIDATE_PACKAGE_MEMBER, archive.namelist())
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    def test_scout_progress_combines_research_counts_and_chatgpt_schedule(self) -> None:
        initial = build_scout_progress(self.store, self.import_id)
        self.assertEqual({"completed": 1, "total": 2}, initial["research"])
        self.assertEqual("autoMesa.html", initial["targetReviewFilename"])
        self.assertEqual("research", initial["phase"])
        self.assertIsNone(initial["nextChatgpt"])

        event = self.store.record_scout_workflow_progress(
            self.import_id,
            "research",
            "Employment research is complete; Food is next.",
            category_id="food",
            details={
                "nextChatgpt": {
                    "categoryId": "food",
                    "categoryLabel": "Food",
                    "delayMinutes": 17,
                    "scheduledAt": "2026-08-28T22:17:00+00:00",
                    "reason": "Random 10-20 minute research interval.",
                }
            },
        )
        self.assertEqual("food", event["categoryId"])
        progress = build_scout_progress(self.store, self.import_id)
        self.assertEqual("Employment research is complete; Food is next.", progress["message"])
        self.assertEqual(17, progress["nextChatgpt"]["delayMinutes"])
        self.assertEqual("Food", progress["nextChatgpt"]["categoryLabel"])

    def test_http_progress_records_and_returns_delay_duration(self) -> None:
        web_dir = Path(__file__).resolve().parent.parent / "web"
        server = ResearchHTTPServer(("127.0.0.1", 0), self.store, web_dir)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_address[1]}"
        payload = {
            "importId": self.import_id,
            "phase": "research",
            "categoryId": "food",
            "message": "Food research is scheduled.",
            "details": {
                "nextChatgpt": {
                    "categoryId": "food",
                    "categoryLabel": "Food",
                    "delayMinutes": 14,
                    "scheduledAt": "2026-08-28T22:14:00+00:00",
                }
            },
        }
        try:
            request = urllib.request.Request(
                base + "/api/scout-progress",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=5) as response:
                response_status = response.status
                saved = json.loads(response.read())
            self.assertEqual(201, response_status)
            self.assertEqual(14, saved["progress"]["nextChatgpt"]["delayMinutes"])
            with urllib.request.urlopen(
                base + f"/api/scout-progress?importId={self.import_id}", timeout=5
            ) as response:
                progress = json.loads(response.read())
            self.assertEqual("Food research is scheduled.", progress["message"])
            self.assertEqual("2026-08-28T22:14:00+00:00", progress["nextChatgpt"]["scheduledAt"])
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    def test_http_candidate_views_are_scoped_to_one_office_package(self) -> None:
        package_path = self.root / "provo-resource-package.zip"
        with zipfile.ZipFile(package_path, "w") as archive:
            archive.writestr("tso-resources.json", json.dumps({
                "resourcePackageSchemaVersion": 3,
                "packageVersion": 9,
                "officeName": "Provo TSO",
                "serviceArea": "Utah County, Utah",
                "categories": [
                    {"id": "education", "name": "Education", "filters": []},
                ],
                "resources": [],
            }))
        provo_import_id = self.store.save_import(
            ResourcePackageImporter("Education").read(package_path)
        )
        provo_run_id = self.store.create_manual_discovery_run(
            "Find Education resources",
            {"researchContext": {"mode": "package"}},
            provo_import_id,
            target_category_id="education",
            target_category_label="Education",
        )
        self.store.save_manual_contribution(
            provo_run_id,
            "ChatGPT",
            json.dumps({
                "leads": [{
                    "organization": "Provo Learning Center",
                    "program": "Adult Education",
                    "website": "https://example.org/provo-learning",
                    "phone": "801-555-0100",
                    "address": "1 Center Street, Provo, UT",
                    "leadType": "program",
                    "locationOrServiceArea": "Provo",
                    "whyRelevant": "Provides adult education.",
                    "uncertainty": "Confirm enrollment dates.",
                }]
            }),
        )
        consolidate_manual_discovery(
            self.store, provo_run_id, DuplicateIndex(self.store)
        )
        finish_manual_discovery(self.store, provo_run_id)

        web_dir = Path(__file__).resolve().parent.parent / "web"
        server = ResearchHTTPServer(("127.0.0.1", 0), self.store, web_dir)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_address[1]}"
        try:
            with urllib.request.urlopen(
                base + f"/api/research-runs?importId={provo_import_id}",
                timeout=5,
            ) as response:
                runs = json.loads(response.read())["runs"]
            self.assertEqual([provo_run_id], [run["id"] for run in runs])
            self.assertEqual(["Provo TSO"], [run["sourceOfficeName"] for run in runs])

            with urllib.request.urlopen(
                base + f"/api/discoveries?importId={provo_import_id}",
                timeout=5,
            ) as response:
                discoveries = json.loads(response.read())["discoveries"]
            self.assertEqual({provo_run_id}, {
                discovery["runId"] for discovery in discoveries
            })

            with urllib.request.urlopen(
                base + f"/api/research-runs?importId={self.import_id}",
                timeout=5,
            ) as response:
                mesa_runs = json.loads(response.read())["runs"]
            self.assertEqual([self.run_id], [run["id"] for run in mesa_runs])
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
