"""Frozen pre-merge roster for synthetic historical-workflow tests only."""
from pathlib import Path
from unittest.mock import patch
from resource_research_agent.codex_first_research import load_researcher_roster


def install_legacy_roster(test):
    fixture = Path(__file__).with_name("fixtures") / "legacy-researcher-roster.json"
    def load(path=None):
        return load_researcher_roster(fixture if path is None else path)
    for module in ("scout_improvement", "scout_maintenance"):
        mocked = patch(f"resource_research_agent.{module}.load_researcher_roster", side_effect=load)
        mocked.start()
        test.addCleanup(mocked.stop)
