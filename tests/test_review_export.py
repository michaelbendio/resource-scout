from __future__ import annotations

import json
import subprocess
import tempfile
import threading
import unittest
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from resource_research_agent import __version__
from resource_research_agent.duplicates import DuplicateIndex
from resource_research_agent.importer import ResourcePackageImporter
from resource_research_agent.manual_consolidation import consolidate_manual_discovery, finish_manual_discovery
from resource_research_agent.review_export import ReviewCopyError, build_review_copy
from resource_research_agent.server import ResearchHTTPServer
from resource_research_agent.storage import ResearchStore


class ReviewCopyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.store = ResearchStore(self.root / "research.sqlite3")
        package_path = self.root / "mesa-resource-package.zip"
        package = {
            "resourcePackageSchemaVersion": 3,
            "packageVersion": 43,
            "officeName": "Mesa TSO",
            "serviceArea": "Mesa, Arizona",
            "categories": [{"id": "housing", "name": "Housing", "filters": ["Shelter"]}],
            "forGroups": ["Veterans"],
            "resources": [{
                "id": "known-home", "name": "Known Home", "categories": ["housing"],
                "website": "https://known.example.org/program",
                "address": "1 Main Street, Mesa, AZ",
                "privateExtension": "must not be exported",
            }],
        }
        with zipfile.ZipFile(package_path, "w") as archive:
            archive.writestr("tso-resources.json", json.dumps(package))
        self.import_id = self.store.save_import(ResourcePackageImporter().read(package_path))

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def completed_run(
        self,
        *,
        package_backed: bool = True,
        location: str = "Mesa, Arizona",
        category_id: str = "housing",
        category_label: str = "Housing",
    ) -> int:
        package_id = self.import_id if package_backed else None
        mode = "package" if package_id else "standalone-location"
        run_id = self.store.create_manual_discovery_run(
            f"Discover {category_label} leads in {location}",
            {"researchContext": {"mode": mode, "serviceArea": location}},
            package_id,
            research_mode=mode,
            target_location=location if mode == "standalone-location" else None,
            regional_scope="Maricopa County",
            target_category_id=category_id,
            target_category_label=category_label,
        )
        response = {
            "leads": [{
                "organization": "Known Home",
                "program": "Known Home Assistance Program",
                "website": "https://known.example.org/assistance",
                "phone": "480-555-0100",
                "address": "2 Main Street, Mesa, AZ",
                "leadType": "program",
                "locationOrServiceArea": location,
                "whyRelevant": "Offers short-term housing assistance.",
                "uncertainty": "Confirm current funding.",
            }]
        }
        self.store.save_manual_contribution(run_id, "ChatGPT", json.dumps(response))
        consolidate_manual_discovery(self.store, run_id, DuplicateIndex(self.store))
        finish_manual_discovery(self.store, run_id)
        return run_id

    @staticmethod
    def embedded_data(html: str) -> dict[str, object]:
        import re
        match = re.search(
            r'<script id="review-data" type="application/json">(.*?)</script>',
            html,
            re.DOTALL,
        )
        if not match:
            raise AssertionError("embedded review data was not found")
        return json.loads(match.group(1))

    def test_completed_chat_discovery_exports_clean_portable_curator(self) -> None:
        run_id = self.completed_run()
        review = build_review_copy(
            self.store, run_id,
            exported_at=datetime(2026, 8, 26, 15, 30, tzinfo=timezone.utc),
        )
        html = review.html.decode("utf-8")
        data = self.embedded_data(html)
        self.assertEqual(14, data["reviewCopySchemaVersion"])
        self.assertEqual(1, data["curatorWorkSchemaVersion"])
        self.assertEqual("Housing research", data["title"])
        self.assertEqual(1, data["run"]["candidateCount"])
        self.assertNotIn("adapter", data["run"])
        self.assertNotIn("runKind", data["run"])
        self.assertNotIn("stages", data["run"])
        self.assertNotIn("lessons", data)
        self.assertNotIn("status", data["candidates"][0])
        self.assertNotIn("reviewFeedback", data["candidates"][0])
        self.assertEqual("Known Home", data["candidates"][0]["knownResourceMatch"]["name"])
        self.assertEqual(["housing"], data["candidates"][0]["resourceDraft"]["categories"])
        self.assertTrue(data["manualDiscovery"]["contributionSources"])
        self.assertTrue(data["sourcePackage"]["packageEligible"])
        self.assertNotIn("privateExtension", html)
        self.assertIn("Content-Security-Policy", html)
        self.assertIn("Resource Curator", html)
        self.assertIn("Editors", html)
        self.assertIn("Notes", html)
        self.assertNotIn("Candidate Research", html)
        self.assertNotIn("Research trail", html)
        self.assertNotIn("Teaching Loop", html)
        self.assertNotIn("Outcome", html)
        self.assertIn(f'<span class="workspace-version">v{__version__}</span>', html)

    def test_open_discovery_cannot_be_exported(self) -> None:
        run_id = self.store.create_manual_discovery_run(
            "Still collecting", {}, self.import_id,
            target_category_id="housing", target_category_label="Housing",
        )
        with self.assertRaisesRegex(ReviewCopyError, "Finish discovery"):
            build_review_copy(self.store, run_id)

    def test_standalone_export_has_no_package_or_resource_draft(self) -> None:
        run_id = self.completed_run(package_backed=False)
        data = build_review_copy(self.store, run_id).data
        self.assertEqual("standalone-location", data["run"]["researchMode"])
        self.assertEqual("Mesa, Arizona", data["run"]["targetLocation"])
        self.assertIsNone(data["sourcePackage"])
        self.assertIsNone(data["candidates"][0]["resourceDraft"])
        self.assertIn("not an official or comprehensive", data["notice"])

    def test_review_and_resource_ids_are_stable(self) -> None:
        run_id = self.completed_run()
        first = build_review_copy(self.store, run_id).data
        second = build_review_copy(self.store, run_id).data
        self.assertEqual(first["reviewId"], second["reviewId"])
        self.assertEqual(
            first["candidates"][0]["resourceDraft"]["id"],
            second["candidates"][0]["resourceDraft"]["id"],
        )

    def test_http_endpoint_downloads_curator(self) -> None:
        run_id = self.completed_run()
        web_dir = Path(__file__).resolve().parent.parent / "web"
        server = ResearchHTTPServer(("127.0.0.1", 0), self.store, web_dir)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            port = server.server_address[1]
            with urllib.request.urlopen(
                f"http://127.0.0.1:{port}/api/research-runs/{run_id}/review-copy", timeout=5
            ) as response:
                body = response.read().decode("utf-8")
                self.assertIn("attachment;", response.headers["Content-Disposition"])
                self.assertIn("Known Home Assistance Program", body)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    def test_curator_javascript_builds_an_additions_package(self) -> None:
        review = build_review_copy(self.store, self.completed_run()).data
        script = r"""
const fs = require('fs');
(0, eval)(fs.readFileSync('web/review-copy.js', 'utf8'));
const review = JSON.parse(fs.readFileSync(0, 'utf8'));
const state = ReviewAppCore.initialState(review);
const item = review.candidates[0];
state.candidates[item.id].packageStatus = 'ready';
state.candidates[item.id].matchAssessment = 'same-organization-different-program';
state.candidates[item.id].curatorNotes = '- [ ] Confirm hours';
state.candidates[item.id].curatorNotes = ReviewAppCore.toggleChecklistItem(state.candidates[item.id].curatorNotes, 0, true);
const built = ReviewAppCore.buildResourcePackage(review, state, '2026-08-26T12:00:00+00:00');
const archived = ReviewAppCore.archivePackagedCandidates(review, state, built, '2026-08-26T12:00:00+00:00');
const restored = ReviewAppCore.validateFeedback(review, JSON.parse(JSON.stringify(state)));
process.stdout.write(JSON.stringify({errors: built.errors, data: built.data, archived, notes: restored.candidates[item.id].curatorNotes, state: restored.candidates[item.id]}));
"""
        completed = subprocess.run(
            ["node", "-e", script], input=json.dumps(review), text=True,
            capture_output=True, check=True,
        )
        result = json.loads(completed.stdout)
        self.assertEqual([], result["errors"])
        self.assertEqual(1, result["archived"])
        self.assertIn("[x] Confirm hours", result["notes"])
        self.assertNotIn("disposition", result["state"])
        self.assertNotIn("outcomeHistory", result["state"])
        self.assertNotIn("sourceScoutStatus", result["state"])
        self.assertEqual("Known Home Assistance Program", result["data"]["resources"][0]["name"])


if __name__ == "__main__":
    unittest.main()
