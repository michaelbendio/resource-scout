from __future__ import annotations

import json
import base64
import io
import re
import subprocess
import tempfile
import threading
import time
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
            "categories": [{"id": "housing", "name": "Housing", "filters": ["Shelter"]}],
            "forGroups": ["Veterans"],
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
            "recommendedTypes": ["Shelter"],
            "recommendedFor": ["Veterans"],
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

        completed_date = data["run"]["completedAt"][:10]
        self.assertEqual(f"housing-research-curator-{completed_date}.html", review.filename)
        self.assertEqual(8, data["reviewCopySchemaVersion"])
        self.assertEqual(1, data["reviewFeedbackSchemaVersion"])
        self.assertTrue(data["reviewId"])
        self.assertEqual("A concise completed summary with </script> text.", data["run"]["summary"])
        self.assertEqual(1, data["run"]["candidateCount"])
        self.assertEqual("Known Home", data["candidates"][0]["knownResourceMatch"]["name"])
        self.assertTrue(data["candidates"][0]["knownResourceMatch"]["signals"])
        self.assertEqual("research-further", data["candidates"][0]["status"])
        self.assertEqual(
            "same-organization-different-program", data["candidates"][0]["matchAssessment"]
        )
        self.assertIn("Confirm funding", data["candidates"][0]["reviewFeedback"])
        self.assertTrue(data["candidates"][0]["resourceDraft"]["id"])
        self.assertEqual(["housing"], data["candidates"][0]["resourceDraft"]["categories"])
        self.assertEqual(
            {"housing": ["Shelter"]},
            data["candidates"][0]["resourceDraft"]["categoryFilters"],
        )
        self.assertEqual(["Veterans"], data["candidates"][0]["resourceDraft"]["forGroups"])
        self.assertEqual(["Veterans"], data["sourcePackage"]["forGroups"])
        self.assertTrue(data["sourcePackage"]["packageEligible"])
        self.assertEqual(3, data["sourcePackage"]["resourcePackageSchemaVersion"])
        self.assertEqual("Verify time-varying funding.", data["lessons"][0]["text"])
        self.assertNotIn("RAW-AGENT-OUTPUT-MUST-NOT-APPEAR", html)
        self.assertNotIn("private-provider-detail", html)
        self.assertNotIn("privateExtension", html)
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("\\u003cscript", html)
        self.assertIn("Content-Security-Policy", html)
        self.assertNotIn("__REVIEW_COPY_DATA__", html)
        self.assertNotIn("__REVIEW_COPY_SCRIPT__", html)
        self.assertIn("Save work", html)
        self.assertIn("Save a resource package", html)
        self.assertIn("Your saved-work JSON matters", html)
        self.assertIn("The HTML does not update itself", html)
        self.assertIn("send the JSON back", html)
        self.assertIn("it is not a backup of all review work", html)
        self.assertIn("Candidate Research", html)
        self.assertIn("Resource Editors", html)
        self.assertIn("Notes", html)
        self.assertIn("Formatting: - [ ] checklist", html)
        self.assertNotIn("Research progress", html)
        self.assertNotIn("Stage progress", html)
        self.assertNotIn('id="stages-panel"', html)

    def test_run_history_is_compact_but_individual_run_keeps_full_details(self) -> None:
        run_id = self.completed_run()

        history_run = next(run for run in self.store.list_runs() if run["id"] == run_id)
        full_run = self.store.get_run(run_id)

        self.assertEqual("", history_run["output"])
        self.assertIsNone(history_run["usage"])
        self.assertEqual(
            {
                "summary": "A concise completed summary with </script> text.",
                "stageSummaries": [],
                "isPartial": False,
            },
            history_run["result"],
        )
        self.assertEqual({"selectedSeed": None}, history_run["prompt"])
        self.assertEqual("RAW-AGENT-OUTPUT-MUST-NOT-APPEAR", full_run["output"])
        self.assertEqual("Known Home Assistance Program", full_run["result"]["candidates"][0]["name"])
        self.assertEqual("private-provider-detail", full_run["usage"]["provider"])

    def test_package_category_is_preserved_in_review_title_and_data(self) -> None:
        run_id = self.store.create_research_run(
            "hermes", "Find practical food resources", {"selectedSeed": None},
            self.import_id, None, target_category_id="food", target_category_label="Food",
        )
        self.store.mark_run_running(run_id)
        self.store.save_discovery(
            {"name": "Community Meal", "serviceNeed": "A meal available tonight"},
            run_id=run_id,
        )
        self.store.complete_run(run_id, "raw", {"summary": "Food research complete"}, None)
        review = build_review_copy(
            self.store, run_id,
            exported_at=datetime(2026, 8, 17, 15, 30, tzinfo=timezone.utc),
        )
        self.assertEqual("Food research", review.data["title"])
        self.assertEqual("Food", review.data["run"]["targetCategoryLabel"])
        completed_date = review.data["run"]["completedAt"][:10]
        self.assertEqual(f"food-research-curator-{completed_date}.html", review.filename)

    def test_review_copy_is_scoped_to_its_associated_run(self) -> None:
        first_run_id = self.completed_run()
        second_run_id = self.store.create_research_run(
            "hermes",
            "Research a different place",
            {"selectedSeed": None},
            research_mode="standalone-location",
            target_location="Mesa, Arizona",
        )
        self.store.mark_run_running(second_run_id)
        self.store.save_discovery(
            {"name": "Mesa Run Only", "geography": "Mesa, Arizona"},
            run_id=second_run_id,
        )
        self.store.complete_run(
            second_run_id,
            "second raw output",
            {"summary": "Mesa-only summary", "candidates": []},
            None,
        )

        first_html = build_review_copy(self.store, first_run_id).html.decode("utf-8")
        second_html = build_review_copy(self.store, second_run_id).html.decode("utf-8")

        self.assertIn("Known Home Assistance Program", first_html)
        self.assertNotIn("Mesa Run Only", first_html)
        self.assertIn("Mesa Run Only", second_html)
        self.assertNotIn("Known Home Assistance Program", second_html)

    def test_standalone_location_export_has_explicit_provenance_and_no_package(self) -> None:
        run_id = self.store.create_research_run(
            "hermes",
            "Research practical Housing options in Mesa",
            {
                "researchContext": {
                    "mode": "standalone-location",
                    "targetLocation": "Mesa, Arizona",
                    "regionalScope": "Maricopa County",
                    "sourcePackage": None,
                },
                "selectedSeed": None,
            },
            research_mode="standalone-location",
            target_location="Mesa, Arizona",
            regional_scope="Maricopa County",
        )
        self.store.mark_run_running(run_id)
        saved = self.store.save_discovery(
            {"name": "Mesa Housing Lead", "geography": "Mesa, Arizona"},
            run_id=run_id,
        )
        self.store.save_lesson(
            "Confirm service areas",
            status="proposed",
            source="agent",
            run_id=run_id,
            research_mode="standalone-location",
            target_location="Mesa, Arizona",
        )
        self.store.complete_run(
            run_id,
            "raw output",
            {"summary": "Exploratory Mesa findings", "candidates": [saved]},
            None,
        )

        review = build_review_copy(
            self.store,
            run_id,
            exported_at=datetime(2026, 8, 18, 6, 0, tzinfo=timezone.utc),
        )
        data = self.embedded_data(review.html.decode("utf-8"))
        self.assertEqual(
            f"housing-research-for-mesa-arizona-curator-{data['run']['completedAt'][:10]}.html",
            review.filename,
        )
        self.assertEqual("Housing research for Mesa, Arizona", data["title"])
        self.assertEqual("standalone-location", data["run"]["researchMode"])
        self.assertEqual("Mesa, Arizona", data["run"]["targetLocation"])
        self.assertEqual("Maricopa County", data["run"]["regionalScope"])
        self.assertIsNone(data["sourcePackage"])
        self.assertIsNone(data["candidates"][0]["resourceDraft"])
        self.assertIn("not an official or comprehensive", data["notice"])
        self.assertIsNone(data["candidates"][0]["knownResourceMatch"])
        self.assertEqual("Mesa, Arizona", data["lessons"][0]["targetLocation"])

    def test_partial_staged_run_can_be_exported_with_progress_and_failure_context(self) -> None:
        run_id = self.store.create_research_run(
            "hermes",
            "Research Mesa Housing",
            {"selectedSeed": None},
            research_mode="standalone-location",
            target_location="Mesa, Arizona",
            stages=[
                {"key": "urgent", "title": "Urgent access", "instruction": "Find urgent options"},
                {"key": "long-term", "title": "Long-term paths", "instruction": "Find long-term options"},
            ],
        )
        self.store.mark_run_running(run_id)
        stages = self.store.list_run_stages(run_id)
        self.store.mark_stage_running(stages[0]["id"])
        self.store.save_discovery(
            {"name": "Mesa Emergency Lead", "geography": "Mesa, Arizona"},
            run_id=run_id,
            stage_id=stages[0]["id"],
        )
        self.store.complete_stage(
            stages[0]["id"], "stage output", {"summary": "Urgent findings"}, None
        )
        self.store.mark_stage_running(stages[1]["id"])
        self.store.fail_stage(
            stages[1]["id"], "Hermes research exceeded the 900-second limit", "partial output"
        )
        result = {
            "summary": "Completed 1 of 2 research stages.\n\nUrgent access: Urgent findings",
            "isPartial": True,
        }
        self.store.partial_run(
            run_id,
            "Hermes research exceeded the 900-second limit",
            "stage output",
            result,
            None,
        )

        review = build_review_copy(self.store, run_id)
        data = self.embedded_data(review.html.decode("utf-8"))
        self.assertEqual("partial", data["run"]["status"])
        self.assertEqual({"total": 2, "completed": 1, "failed": 1}, data["run"]["progress"])
        self.assertEqual(["completed", "failed"], [stage["status"] for stage in data["run"]["stages"]])
        self.assertIn("stopped after 1 of 2 stages", data["notice"])
        self.assertIn("900-second limit", data["run"]["stages"][1]["error"])
        self.assertEqual("Mesa Emergency Lead", data["candidates"][0]["name"])

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
                completed_date = self.store.get_run(run_id)["completedAt"][:10]
                self.assertIn(
                    f"housing-research-curator-{completed_date}.html",
                    response.headers["Content-Disposition"],
                )
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

    def test_review_resource_ids_are_stable_across_exports(self) -> None:
        run_id = self.completed_run()
        first = build_review_copy(
            self.store, run_id,
            exported_at=datetime(2026, 8, 17, 15, 30, tzinfo=timezone.utc),
        ).data
        second = build_review_copy(
            self.store, run_id,
            exported_at=datetime(2026, 8, 18, 15, 30, tzinfo=timezone.utc),
        ).data
        self.assertEqual(first["reviewId"], second["reviewId"])
        self.assertEqual(
            first["candidates"][0]["resourceDraft"]["id"],
            second["candidates"][0]["resourceDraft"]["id"],
        )

    def test_review_javascript_builds_openable_additions_only_package(self) -> None:
        review = build_review_copy(self.store, self.completed_run()).data
        script = r"""
const fs = require('fs');
(0, eval)(fs.readFileSync('web/review-copy.js', 'utf8'));
const review = JSON.parse(fs.readFileSync(0, 'utf8'));
const state = ReviewAppCore.initialState(review);
const item = review.candidates[0];
const secondItem = JSON.parse(JSON.stringify(item));
secondItem.id = `${item.id}-second`;
secondItem.resourceDraft.id = `${item.resourceDraft.id}-second`;
const twoCandidateReview = Object.assign({}, review, { candidates: [item, secondItem] });
const twoCandidateState = ReviewAppCore.initialState(twoCandidateReview);
twoCandidateState.candidates[item.id].curatorNotes = 'Notes for the first candidate only';
const independentNotes = {
  first: twoCandidateState.candidates[item.id].curatorNotes,
  second: twoCandidateState.candidates[secondItem.id].curatorNotes,
};
state.candidates[item.id].curatorNotes = '**Interview**\n- [ ] Confirm hours\n- [x] Confirm service area';
const checklistBefore = ReviewAppCore.checklistItems(state.candidates[item.id].curatorNotes);
state.candidates[item.id].curatorNotes = ReviewAppCore.toggleChecklistItem(state.candidates[item.id].curatorNotes, 1, true);
const checklistAfter = ReviewAppCore.checklistItems(state.candidates[item.id].curatorNotes);
state.candidates[item.id].decision = 'accepted';
state.taxonomyDraft.categoryTypes.housing.push('Bridge housing');
state.taxonomyDraft.forGroups.push('Young adults');
state.taxonomyDraft.modifiedCategoryIds.push('housing');
state.taxonomyDraft.updatedAt = '2026-08-18T11:30:00+00:00';
state.candidates[item.id].resourceDraft.categoryFilters.housing = ['Bridge housing'];
state.candidates[item.id].resourceDraft.forGroups = ['Young adults'];
const pdfPath = `pdfs/${state.candidates[item.id].resourceDraft.id}/guide-test.pdf`;
state.candidates[item.id].resourceDraft.pdfs = [{ id: 'guide', name: 'Guide.pdf', path: pdfPath }];
state.candidates[item.id].pdfAssets[pdfPath] = { name: 'Guide.pdf', type: 'application/pdf', data: Buffer.from('%PDF curator test').toString('base64') };
const built = ReviewAppCore.buildResourcePackage(review, state, '2026-08-18T12:00:00+00:00');
const zip = built.errors.length ? null : ReviewAppCore.createZipArchive([
  { name: 'tso-resources.json', content: JSON.stringify(built.data, null, 2) },
  { name: pdfPath, content: ReviewAppCore.base64ToBytes(built.pdfAssets[pdfPath].data) },
]);
process.stdout.write(JSON.stringify({ errors: built.errors, emptyErrors: ReviewAppCore.buildResourcePackage(review, ReviewAppCore.initialState(review)).errors, independentNotes, checklistBefore, checklistAfter, savedNotes: state.candidates[item.id].curatorNotes, pdfPath, zip: zip && Buffer.from(zip).toString('base64') }));
"""
        completed = subprocess.run(
            ["node", "-e", script], input=json.dumps(review), text=True,
            capture_output=True, check=True,
        )
        result = json.loads(completed.stdout)
        self.assertEqual([], result["errors"])
        self.assertTrue(any("Ready for package" in error for error in result["emptyErrors"]))
        self.assertEqual("Notes for the first candidate only", result["independentNotes"]["first"])
        self.assertEqual("", result["independentNotes"]["second"])
        self.assertEqual([False, True], [item["checked"] for item in result["checklistBefore"]])
        self.assertEqual([True, True], [item["checked"] for item in result["checklistAfter"]])
        self.assertIn("- [x] Confirm hours", result["savedNotes"])
        with zipfile.ZipFile(io.BytesIO(base64.b64decode(result["zip"]))) as archive:
            self.assertEqual(["tso-resources.json", result["pdfPath"]], archive.namelist())
            package = json.loads(archive.read("tso-resources.json"))
            self.assertEqual(b"%PDF curator test", archive.read(result["pdfPath"]))
        self.assertEqual(3, package["resourcePackageSchemaVersion"])
        self.assertEqual(43, package["packageVersion"])
        self.assertEqual(1, len(package["resources"]))
        self.assertEqual("Known Home Assistance Program", package["resources"][0]["name"])
        self.assertEqual(["housing"], package["resources"][0]["categories"])
        self.assertEqual(["Veterans", "Young adults"], package["forGroups"])
        self.assertEqual(
            ["Shelter", "Bridge housing"], package["categories"][0]["filters"]
        )
        self.assertEqual(
            {"housing": ["Bridge housing"]}, package["resources"][0]["categoryFilters"]
        )
        self.assertEqual(["Young adults"], package["resources"][0]["forGroups"])
        self.assertEqual([], package["deletionRequests"])
        self.assertEqual(
            [{"id": "guide", "name": "Guide.pdf", "path": result["pdfPath"]}],
            package["resources"][0]["pdfs"],
        )

    def test_http_starts_explicit_standalone_location_without_using_latest_import(self) -> None:
        self.store.save_settings({"adapter": "demo"})
        web_dir = Path(__file__).resolve().parent.parent / "web"
        server = ResearchHTTPServer(("127.0.0.1", 0), self.store, web_dir)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            port = server.server_address[1]
            request = urllib.request.Request(
                f"http://127.0.0.1:{port}/api/research-runs",
                data=json.dumps({
                    "researchMode": "standalone-location",
                    "targetLocation": "Mesa, Arizona",
                    "regionalScope": "Maricopa County",
                    "assignment": "Research Housing in Mesa",
                }).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=5) as response:
                self.assertEqual(202, response.status)
                run = json.loads(response.read())
            self.assertEqual("standalone-location", run["researchMode"])
            self.assertEqual("Mesa, Arizona", run["targetLocation"])
            self.assertIsNone(run["sourceImportId"])
            for _ in range(200):
                completed = self.store.get_run(run["id"])
                if completed and completed["status"] in {"completed", "failed"}:
                    break
                time.sleep(0.01)
            self.assertEqual("completed", completed["status"])
            discoveries = self.store.list_discoveries(run_id=run["id"])
            self.assertTrue(discoveries)
            self.assertTrue(all(discovery["match"] is None for discovery in discoveries))
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
