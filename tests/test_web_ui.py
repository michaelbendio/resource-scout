from __future__ import annotations

import unittest
import re
from pathlib import Path

from resource_research_agent import __version__


class ScoutLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        web = Path(__file__).resolve().parent.parent / "web"
        cls.html = (web / "index.html").read_text(encoding="utf-8")
        cls.css = (web / "app.css").read_text(encoding="utf-8")
        cls.javascript = (web / "app.js").read_text(encoding="utf-8")

    def test_recent_runs_and_candidate_inbox_have_an_accessible_divider(self) -> None:
        self.assertIn('id="research-divider"', self.html)
        self.assertIn('role="separator"', self.html)
        self.assertIn('aria-orientation="vertical"', self.html)
        self.assertLess(self.html.index('class="panel runs-panel"'), self.html.index('id="research-divider"'))
        self.assertLess(self.html.index('id="research-divider"'), self.html.index('class="panel candidates-panel"'))

    def test_top_bar_uses_resource_scout_name(self) -> None:
        self.assertIn("<title>Resource Scout</title>", self.html)
        self.assertIn("<h1>Resource Scout</h1>", self.html)

    def test_chat_discovery_is_the_only_product_research_path(self) -> None:
        self.assertNotIn("Research agent", self.html)
        self.assertNotIn('id="research-method"', self.html)
        self.assertNotIn('id="agent-adapter"', self.html)
        self.assertNotIn('id="dsh-configuration"', self.html)
        self.assertIn('id="standalone-mode"', self.html)
        self.assertIn("Research a location without a package", self.html)
        self.assertIn(">Set up discovery</button>", self.html)
        self.assertNotIn("selectedResearchMethod", self.javascript)
        self.assertNotIn("No chat API or paid fallback is used", self.html)
        self.assertNotIn("Teaching Loop", self.html)
        self.assertNotIn("Research lessons", self.html)

    def test_version_is_in_the_green_header(self) -> None:
        header = self.html[self.html.index("<header>"):self.html.index("</header>")]
        self.assertIn('class="header-version" id="app-version"', header)
        self.assertIn(f'>v{__version__}</span>', header)
        self.assertNotIn('class="app-footer"', self.html)
        self.assertIn(".header-version { position: absolute;", self.css)

    def test_divider_supports_pointer_keyboard_and_responsive_layouts(self) -> None:
        self.assertIn("divider.addEventListener('pointerdown'", self.javascript)
        self.assertIn("divider.addEventListener('pointermove'", self.javascript)
        self.assertIn("divider.addEventListener('keydown'", self.javascript)
        self.assertIn("setupResearchPaneResizer();", self.javascript)
        self.assertIn("grid-template-columns: minmax(280px, var(--runs-pane-width)) 16px minmax(360px, 1fr)", self.css)
        self.assertIn(".research-divider { display: none; }", self.css)

    def test_recent_runs_have_no_agent_stage_or_resume_controls(self) -> None:
        self.assertNotIn("renderRunFindings", self.javascript)
        self.assertNotIn("renderStageSummary", self.javascript)
        self.assertNotIn("Show full findings", self.javascript)
        self.assertNotIn("stage-summary-card", self.css)
        self.assertNotIn("Resume research", self.javascript)

    def test_runs_show_place_duration_and_candidate_context(self) -> None:
        self.assertIn("function formatDuration(run)", self.javascript)
        self.assertIn("function runPlace(run)", self.javascript)
        self.assertIn("` · Duration ${duration}`", self.javascript)
        self.assertIn("run.sourceOfficeName || run.sourceServiceArea", self.javascript)
        self.assertIn("const importChanged = state.latestImport?.id !== summary.id", self.javascript)
        self.assertIn("summary.serviceArea", self.javascript)

    def test_human_curation_is_exported_instead_of_performed_in_scout(self) -> None:
        self.assertIn("05 · Research records", self.html)
        self.assertIn("Continue in Resource Curator", self.html)
        self.assertIn("human vetting", self.html)
        self.assertIn("Curator and human vetting", self.html)
        self.assertNotIn("duplicate decisions", self.html)
        self.assertIn("human vetting, resource editing, printing, and package preparation", self.html)
        self.assertNotIn('id="review-actions"', self.html)
        self.assertNotIn('id="generated-resource-form"', self.html)
        self.assertNotIn('id="save-match-assessment"', self.html)
        self.assertNotIn("/api/discoveries/${state.currentCandidate.id}/review", self.javascript)
        self.assertNotIn("/api/discoveries/${state.currentCandidate.id}/generated-resource", self.javascript)
        self.assertNotIn("/api/discoveries/${state.currentCandidate.id}/match-assessment", self.javascript)
        self.assertNotIn("Export resource package", self.javascript)

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
