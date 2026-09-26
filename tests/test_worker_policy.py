from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from resource_research_agent.pairwise_runner import _claude_preflight, _grok_preflight, main
from resource_research_agent.codex_first_research import load_researcher_roster
from resource_research_agent.worker_policy import WorkerDisabledError, assert_worker_enabled


class WorkerPolicyTests(unittest.TestCase):
    def test_claude_preflight_is_blocked_before_any_subprocess(self):
        with patch("resource_research_agent.pairwise_runner.subprocess.run") as run:
            with self.assertRaisesRegex(WorkerDisabledError, "Anthropic charges"):
                _claude_preflight(claude_binary="claude", model="", timeout_seconds=10, max_turns=5)
            run.assert_not_called()

    def test_disabled_profile_does_not_even_create_a_database(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "must-not-exist.sqlite3"
            with self.assertRaises(WorkerDisabledError):
                main(["--database", str(database), "--profile", "codex-claude", "--skip-preflight"])
            self.assertFalse(database.exists())

    def test_authorized_workers_remain_enabled(self):
        assert_worker_enabled("Codex")
        assert_worker_enabled("DeepSeek")
        with self.assertRaises(WorkerDisabledError):
            assert_worker_enabled("  CLAUDE  ")

    def test_only_deepseek_is_selected_for_new_plans(self):
        researchers = load_researcher_roster()["researchers"]
        self.assertEqual(["DeepSeek"], [r["name"] for r in researchers if r["role"] == "challenger"])
        self.assertFalse(any(r["role"] == "shadow" for r in researchers))
        for name in ("Grok", "ChatGPT", "Perplexity"):
            with self.subTest(name=name), self.assertRaisesRegex(WorkerDisabledError, "only challenger"):
                assert_worker_enabled(name)

    def test_grok_probe_is_blocked_before_any_process(self):
        with patch("resource_research_agent.pairwise_runner.run_grok_process") as run:
            with self.assertRaises(WorkerDisabledError):
                _grok_preflight(grok_binary="grok", model="", timeout_seconds=10)
            run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
