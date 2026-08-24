from __future__ import annotations

import unittest
from pathlib import Path


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

    def test_dsh_offers_explicit_local_and_metered_configurations(self) -> None:
        self.assertIn('id="dsh-configuration"', self.html)
        self.assertIn("Local Qwen — no metered services", self.html)
        self.assertIn("DeepSeek — metered", self.html)
        self.assertNotIn("DeepSeek Harness (experimental)", self.html)
        self.assertIn(
            "dshConfiguration: document.querySelector('#dsh-configuration').value",
            self.javascript,
        )
        self.assertIn('data-dsh-configuration-only="deepseek"', self.html)

    def test_version_is_in_the_green_header(self) -> None:
        header = self.html[self.html.index("<header>"):self.html.index("</header>")]
        self.assertIn('class="header-version" id="app-version"', header)
        self.assertNotIn('class="app-footer"', self.html)
        self.assertIn(".header-version { position: absolute;", self.css)

    def test_divider_supports_pointer_keyboard_and_responsive_layouts(self) -> None:
        self.assertIn("divider.addEventListener('pointerdown'", self.javascript)
        self.assertIn("divider.addEventListener('pointermove'", self.javascript)
        self.assertIn("divider.addEventListener('keydown'", self.javascript)
        self.assertIn("setupResearchPaneResizer();", self.javascript)
        self.assertIn("grid-template-columns: minmax(280px, var(--runs-pane-width)) 16px minmax(360px, 1fr)", self.css)
        self.assertIn(".research-divider { display: none; }", self.css)

    def test_run_findings_render_as_expandable_stage_sections_and_lists(self) -> None:
        self.assertIn("function renderRunFindings(run)", self.javascript)
        self.assertIn("function renderStageSummary(stage)", self.javascript)
        self.assertIn("document.createElement('ol')", self.javascript)
        self.assertIn("Show full findings", self.javascript)
        self.assertIn("stage-summary-card", self.css)
        self.assertNotIn("summary.textContent = run.result.summary", self.javascript)

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
        self.assertIn("duplicate signals", self.html)
        self.assertIn("Curator and human vetting", self.html)
        self.assertNotIn("duplicate decisions", self.html)
        self.assertIn("human vetting, optional outcomes, resource editing, printing, and package preparation", self.html)
        self.assertIn("portable vetting and package workspace", self.javascript)
        self.assertNotIn('id="review-actions"', self.html)
        self.assertNotIn('id="generated-resource-form"', self.html)
        self.assertNotIn('id="save-match-assessment"', self.html)
        self.assertNotIn("/api/discoveries/${state.currentCandidate.id}/review", self.javascript)
        self.assertNotIn("/api/discoveries/${state.currentCandidate.id}/generated-resource", self.javascript)
        self.assertNotIn("/api/discoveries/${state.currentCandidate.id}/match-assessment", self.javascript)
        self.assertNotIn("Export resource package", self.javascript)


if __name__ == "__main__":
    unittest.main()
