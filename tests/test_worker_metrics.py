from __future__ import annotations

import json
import subprocess
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch

from resource_research_agent.pairwise_runner import (
    _run_grok_text, _run_claude_text, _run_codex_worker,
    _run_with_retries, WorkerLimitError,
)
from resource_research_agent.runner_lock import research_runner_lock
from resource_research_agent.worker_metrics import model_counter, observed_counter


class WorkerMetricsTests(unittest.TestCase):
    def test_duplicate_runner_is_refused_and_lock_releases_on_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.sqlite3"
            with self.assertRaisesRegex(ValueError, "test failure"):
                with research_runner_lock(path):
                    with self.assertRaisesRegex(RuntimeError, "already holds"):
                        with research_runner_lock(path):
                            self.fail("duplicate runner entered")
                    raise ValueError("test failure")
            with research_runner_lock(path):
                pass

    def test_timeouts_and_turn_limits_do_not_repeat_unchanged(self):
        for error in (WorkerLimitError("limit"), subprocess.TimeoutExpired("worker", 10)):
            with self.subTest(error=type(error).__name__), patch("resource_research_agent.pairwise_runner.time.sleep") as sleep:
                calls = []
                def action():
                    calls.append(True)
                    raise error
                records = []
                with self.assertRaises(type(error)):
                    _run_with_retries("test", action, retry_count=3, context={}, record_attempt=lambda **row: records.append(row))
                self.assertEqual(1, len(calls))
                self.assertEqual(1, len(records))
                self.assertEqual("failed", records[0]["outcome"])
                sleep.assert_not_called()

    def test_claude_turn_limit_is_classified_even_with_nonzero_exit(self):
        envelope = {"is_error": True, "subtype": "error_max_turns", "terminal_reason": "max_turns", "num_turns": 61}
        with patch("resource_research_agent.pairwise_runner.subprocess.run", return_value=subprocess.CompletedProcess([], 1, json.dumps(envelope), "")):
            with self.assertRaises(WorkerLimitError):
                _run_claude_text("test", claude_binary="claude", model="", timeout_seconds=10, max_turns=60)

    def test_codex_effort_is_explicit_and_empty_event_stream_is_unknown(self):
        commands = []
        def completed(command, **kwargs):
            commands.append(command)
            Path(command[command.index("--output-last-message") + 1]).write_text('{"leads": []}')
            return subprocess.CompletedProcess(command, 0, "", "")
        with patch("resource_research_agent.pairwise_runner.subprocess.run", side_effect=completed):
            result = _run_codex_worker("test", codex_binary="codex", model="test", timeout_seconds=10, reasoning_effort="high")
        self.assertIn('model_reasoning_effort="high"', commands[0])
        self.assertEqual("high", result["usage"]["requestedReasoningEffort"])
        self.assertIsNone(result["usage"]["webSearchRequests"])
        self.assertIsNone(result["usage"]["numTurns"])

    def test_absent_partial_and_explicit_zero_counters(self):
        self.assertIsNone(model_counter({}, "webSearchRequests"))
        self.assertIsNone(model_counter({"a": {"tokens": 1}}, "webSearchRequests"))
        self.assertIsNone(model_counter({"a": {"webSearchRequests": 2}, "b": {}}, "webSearchRequests"))
        self.assertEqual(0, model_counter({"a": {"webSearchRequests": 0}}, "webSearchRequests"))
        self.assertEqual(5, model_counter({"a": {"webSearchRequests": 2}, "b": {"webSearchRequests": 3}}, "webSearchRequests"))
        self.assertIsNone(observed_counter({"numTurns": 0}, "numTurns"))
        self.assertEqual(0, observed_counter({"numTurns": 0, "counterSchemaVersion": 2}, "numTurns"))
        self.assertEqual(7, observed_counter({"numTurns": 7}, "numTurns"))

    def test_grok_native_envelope_without_search_counter_stays_unknown(self):
        envelope = {"text": '{"leads": []}', "num_turns": 6, "usage": {"input_tokens": 100}}
        with patch("resource_research_agent.pairwise_runner.run_grok_process", return_value=subprocess.CompletedProcess([], 0, json.dumps(envelope), "")):
            result = _run_grok_text("test", grok_binary="grok", model="", timeout_seconds=10, return_metadata=True)
        self.assertEqual(6, result["usage"]["numTurns"])
        self.assertIsNone(result["usage"]["webSearchRequests"])
        self.assertEqual(2, result["usage"]["counterSchemaVersion"])

    def test_claude_explicit_zero_is_retained_and_missing_turns_stay_unknown(self):
        envelope = {"result": '{"leads": []}', "modelUsage": {"test": {"webSearchRequests": 0}}}
        with patch("resource_research_agent.pairwise_runner.subprocess.run", return_value=subprocess.CompletedProcess([], 0, json.dumps(envelope), "")):
            result = _run_claude_text("test", claude_binary="claude", model="", timeout_seconds=10, max_turns=60, return_metadata=True)
        self.assertEqual(0, result["usage"]["webSearchRequests"])
        self.assertIsNone(result["usage"]["numTurns"])
        self.assertIsNone(result["usage"]["durationApiMs"])


if __name__ == "__main__":
    unittest.main()
