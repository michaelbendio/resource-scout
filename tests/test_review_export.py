from __future__ import annotations

import json
import re
import tempfile
import threading
import unittest
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from resource_research_agent.duplicates import DuplicateIndex
from resource_research_agent.importer import ResourcePackageImporter
from resource_research_agent.review_export import ReviewCopyError, build_review_copy
from resource_research_agent.server import ResearchHTTPServer
from resource_research_agent.storage import ResearchStore


class ReviewCopyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.store = ResearchStore(self.root / "research.sqlite3")
        package_path = self.root / "provo-resource-package.zip"
        package = {
            "resourcePackageSchemaVersion": 3,
            "packageVersion": 43,
            "categories": [{"id": "housing", "name": "Housing"}],
            "resources": [{
                "id": "known-home",
                "name": "Known Home",
                "categories": ["housing"],
                "website": "https://known.example.org/program",
                "address": "1 Main Street, Provo, UT",
                "privateExtension": "full imported records must not be exported",
            }],
        }
        with zipfile.ZipFile(package_path, "w") as archive:
            archive.writestr("tso-resources.json", json.dumps(package))
        self.import_id = self.store.save_import(ResourcePackageImporter().read(package_path))

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def completed_run(self) -> int:
        run_id = self.store.create_research_run(
            "hermes",
            "Find practical Housing options",
            {"selectedSeed": None},
            self.import_id,
            None,
        )
        self.store.mark_run_running(run_id)
        candidate = {
            "name": "Known Home Assistance Program",
            "organization": "Known Home",
            "website": "https://known.example.org/assistance",
            "housingNeed": "Short-term rent assistance",
            "evidence": [{
                "url": "https://known.example.org/assistance",
                "title": "Official program page",
                "finding": "The program offers short-term help.",
                "sourceType": "official",
                "reliability": "high",
                "accessedAt": "2026-08-17",
            }],
        }
        match = DuplicateIndex(self.store).match(candidate, import_id=self.import_id, limit=1)[0]
        saved = self.store.save_discovery(candidate, match, run_id=run_id)
        self.store.review_discovery(
            saved["id"], "research-further", "Confirm funding before referral. <script>alert(1)</script>"
        )
        self.store.assess_discovery_match(saved["id"], "same-organization-different-program")
        self.store.save_lesson(
            "Verify time-varying funding.", rationale="Availability changes.",
            status="proposed", source="agent", run_id=run_id,
        )
        self.store.complete_run(
            run_id,
            "RAW-AGENT-OUTPUT-MUST-NOT-APPEAR",
            {"summary": "A concise completed summary with </script> text.", "candidates": [candidate]},
            {"provider": "private-provider-detail"},
        )
        self.assertEqual(self.import_id, self.store.get_run(run_id)["sourceImportId"])
        self.assertIsNone(self.store.get_run(run_id)["seedImportId"])
        return run_id

    @staticmethod
    def embedded_data(html: str) -> dict[str, object]:
        match = re.search(r'<script id="review-data" type="application/json">(.*?)</script>', html, re.DOTALL)
        if not match:
            raise AssertionError("embedded review data was not found")
        return json.loads(match.group(1))

    def test_completed_run_exports_portable_safe_review(self) -> None:
        run_id = self.completed_run()
        review = build_review_copy(
            self.store,
            run_id,
            exported_at=datetime(2026, 8, 17, 15, 30, tzinfo=timezone.utc),
        )
        html = review.html.decode("utf-8")
        data = self.embedded_data(html)

        self.assertEqual("broad-housing-research-review-2026-08-17.html", review.filename)
        self.assertEqual(1, data["reviewCopySchemaVersion"])
        self.assertEqual("A concise completed summary with </script> text.", data["run"]["summary"])
        self.assertEqual(1, data["run"]["candidateCount"])
        self.assertEqual("Known Home", data["candidates"][0]["knownResourceMatch"]["name"])
        self.assertTrue(data["candidates"][0]["knownResourceMatch"]["signals"])
        self.assertEqual("research-further", data["candidates"][0]["status"])
        self.assertEqual(
            "same-organization-different-program", data["candidates"][0]["matchAssessment"]
        )
        self.assertIn("Confirm funding", data["candidates"][0]["reviewFeedback"])
        self.assertEqual("Verify time-varying funding.", data["lessons"][0]["text"])
        self.assertNotIn("RAW-AGENT-OUTPUT-MUST-NOT-APPEAR", html)
        self.assertNotIn("private-provider-detail", html)
        self.assertNotIn("privateExtension", html)
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("\\u003cscript", html)
        self.assertIn("Content-Security-Policy", html)
        self.assertNotIn("__REVIEW_COPY_DATA__", html)

    def test_incomplete_run_cannot_be_exported(self) -> None:
        run_id = self.store.create_research_run(
            "hermes", "Still working", {"selectedSeed": None}, self.import_id, None
        )
        with self.assertRaisesRegex(ReviewCopyError, "Only completed"):
            build_review_copy(self.store, run_id)

    def test_match_assessment_requires_a_saved_match(self) -> None:
        saved = self.store.save_discovery({"name": "Unmatched candidate"})
        with self.assertRaisesRegex(ValueError, "does not have"):
            self.store.assess_discovery_match(saved["id"], "not-related")
        with self.assertRaisesRegex(ValueError, "Unsupported"):
            self.store.assess_discovery_match(saved["id"], "maybe")

    def test_http_endpoint_downloads_the_review_copy(self) -> None:
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
                self.assertEqual("text/html; charset=utf-8", response.headers.get_content_type() + "; charset=" + response.headers.get_content_charset())
                self.assertIn("attachment;", response.headers["Content-Disposition"])
                self.assertIn("broad-housing-research-review-2026-08-17.html", response.headers["Content-Disposition"])
                self.assertIn("Known Home Assistance Program", body)
            discoveries_url = f"http://127.0.0.1:{port}/api/discoveries"
            with urllib.request.urlopen(discoveries_url, timeout=5) as response:
                discoveries = json.loads(response.read())["discoveries"]
                self.assertEqual("Known Home", discoveries[0]["matchDetails"]["name"])
            assessment_request = urllib.request.Request(
                f"http://127.0.0.1:{port}/api/discoveries/{discoveries[0]['id']}/match-assessment",
                data=json.dumps({"assessment": "related-distinct"}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(assessment_request, timeout=5) as response:
                assessed = json.loads(response.read())["discovery"]
                self.assertEqual("related-distinct", assessed["matchAssessment"])
                self.assertEqual("Known Home", assessed["matchDetails"]["name"])
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
