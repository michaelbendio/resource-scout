from __future__ import annotations

import re
import unittest
from pathlib import Path

from resource_research_agent import __version__


class ScoutLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        web = Path(__file__).resolve().parent.parent / "web"
        cls.html = (web / "index.html").read_text(encoding="utf-8")
        cls.css = (web / "app.css").read_text(encoding="utf-8")
        cls.javascript = (web / "app.js").read_text(encoding="utf-8")

    def test_progress_precedes_resource_candidates_and_recent_runs_are_removed(self) -> None:
        self.assertLess(
            self.html.index('id="scout-progress-panel"'),
            self.html.index('class="panel candidates-panel"'),
        )
        self.assertNotIn('class="panel runs-panel"', self.html)
        self.assertNotIn('id="run-list"', self.html)
        self.assertNotIn("Recent runs", self.html)

    def test_top_bar_uses_resource_scout_name(self) -> None:
        self.assertIn("<title>Resource Scout</title>", self.html)
        self.assertIn("<h1>Resource Scout</h1>", self.html)
        self.assertIn(
            "Research, consolidate, and curate resources for human review.",
            self.html,
        )

    def test_codex_shepherded_research_removes_manual_setup_ui(self) -> None:
        self.assertNotIn('class="panel category-panel"', self.html)
        self.assertNotIn('class="panel research-panel"', self.html)
        self.assertNotIn('id="standalone-mode"', self.html)
        self.assertNotIn('id="research-location-mode"', self.html)
        self.assertNotIn(">Research a location</button>", self.html)
        self.assertNotIn(">Set up discovery</button>", self.html)
        self.assertIn('id="scout-progress-panel"', self.html)

    def test_version_is_in_the_green_header(self) -> None:
        header = self.html[self.html.index("<header>"):self.html.index("</header>")]
        self.assertIn('class="header-version" id="app-version"', header)
        self.assertIn(f'>v{__version__}</span>', header)
        self.assertNotIn('class="app-footer"', self.html)
        self.assertIn(".header-version { position: absolute;", self.css)

    def test_candidate_package_export_is_not_in_the_visible_ui(self) -> None:
        self.assertNotIn("Save Candidate Package", self.html)
        self.assertNotIn('id="candidate-package-export"', self.html)

    def test_progress_shows_counts_chatgpt_delay_and_review_file(self) -> None:
        for element_id in (
            "scout-research-progress",
            "scout-curation-progress",
            "next-chatgpt-delay",
            "next-chatgpt-time",
            "review-file-ready",
            "review-file-download",
        ):
            self.assertIn(f'id="{element_id}"', self.html)
        self.assertIn("Scheduled assignment", self.html)
        self.assertIn("/api/scout-progress?importId=", self.javascript)
        self.assertIn("next.delayMinutes", self.javascript)
        self.assertIn("curationFailures", self.javascript)
        self.assertIn("need attention", self.javascript)
        self.assertIn("review.downloadUrl", self.javascript)
        self.assertIn("}, 15000);", self.javascript)

    def test_resource_candidates_are_section_three_and_package_scoped(self) -> None:
        self.assertIn("03 · Resource candidates", self.html)
        self.assertIn('id="candidate-run-filter"', self.html)
        self.assertIn('id="candidate-list"', self.html)
        self.assertIn("Category research run", self.html)
        self.assertIn("?importId=${state.latestImport.id}", self.javascript)
        self.assertIn("request(`/api/research-runs${scope}`)", self.javascript)
        self.assertIn("request(`/api/discoveries${scope}`)", self.javascript)
        self.assertNotIn("05 · Research records", self.html)
        self.assertNotIn("Research candidates", self.html)
        self.assertIn("Scout curation", self.html)
        self.assertIn("Codex-controlled curation", self.html)
        self.assertNotIn("Resource Curator", self.html)

    def test_ipad_access_is_one_compact_clickable_line(self) -> None:
        start = self.html.index('<section class="ipad-access"')
        end = self.html.index("</section>", start)
        access = self.html[start:end]
        self.assertIn("<strong>iPad access:</strong>", access)
        self.assertIn('id="private-access-url"', access)
        self.assertNotIn("button", access)
        self.assertNotIn("PRIVATE IPAD ACCESS", access)

    def test_package_import_refreshes_records_and_progress(self) -> None:
        import_start = self.javascript.index("async function importSelectedPackage()")
        import_end = self.javascript.index(
            "document.querySelector('#package-input').addEventListener", import_start
        )
        import_javascript = self.javascript[import_start:import_end]
        self.assertIn(
            "await Promise.all([loadResearchData(), loadScoutProgress()]);",
            import_javascript,
        )
        self.assertIn("state.candidateRunSelectionInitialized = false", self.javascript)
        self.assertIn(
            "Scout read a private copy and did not change your ZIP",
            import_javascript,
        )

    def test_every_direct_event_listener_targets_an_existing_element(self) -> None:
        ids = re.findall(
            r"document\.querySelector\('#([^']+)'\)\.addEventListener",
            self.javascript,
        )
        self.assertTrue(ids)
        for element_id in ids:
            with self.subTest(element_id=element_id):
                self.assertIn(f'id="{element_id}"', self.html)


if __name__ == "__main__":
    unittest.main()
