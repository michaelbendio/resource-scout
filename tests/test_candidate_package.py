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


if __name__ == "__main__":
    unittest.main()
