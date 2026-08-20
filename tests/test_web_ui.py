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

    def test_divider_supports_pointer_keyboard_and_responsive_layouts(self) -> None:
        self.assertIn("divider.addEventListener('pointerdown'", self.javascript)
        self.assertIn("divider.addEventListener('pointermove'", self.javascript)
        self.assertIn("divider.addEventListener('keydown'", self.javascript)
        self.assertIn("setupResearchPaneResizer();", self.javascript)
        self.assertIn("grid-template-columns: minmax(280px, var(--runs-pane-width)) 16px minmax(360px, 1fr)", self.css)
        self.assertIn(".research-divider { display: none; }", self.css)


if __name__ == "__main__":
    unittest.main()
