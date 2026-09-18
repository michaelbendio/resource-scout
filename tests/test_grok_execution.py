from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from resource_research_agent.grok_execution import (
    GrokAuthenticationError, _AuthLog, run_grok_process,
)


class GrokExecutionTests(unittest.TestCase):
    def test_auth_stall_stops_and_does_not_disclose_raw_log(self):
        with tempfile.TemporaryDirectory() as directory:
            log = Path(directory) / "log.jsonl"
            command = [sys.executable, "-c", (
                "import os,json,time,pathlib; "
                f"p=pathlib.Path({str(log)!r}); "
                "p.write_text(json.dumps({'pid':os.getpid(), "
                "'msg':'shell.turn.inference_failed', "
                "'ctx':{'kind':'auth','message':'SECRET'}})+'\\n'); "
                "time.sleep(30)"
            )]
            with self.assertRaises(GrokAuthenticationError) as caught:
                run_grok_process(command, timeout_seconds=10, log_path=log)
            self.assertNotIn("SECRET", str(caught.exception))
            self.assertIn("grok login", str(caught.exception))

    def test_normal_output_without_log_and_real_timeout(self):
        with tempfile.TemporaryDirectory() as directory:
            log = Path(directory) / "missing"
            result = run_grok_process(
                [sys.executable, "-c", "print('ready')"],
                timeout_seconds=10, log_path=log,
            )
            self.assertEqual(0, result.returncode)
            self.assertEqual("ready\n", result.stdout)
            with self.assertRaises(subprocess.TimeoutExpired):
                run_grok_process(
                    [sys.executable, "-c", "import time; time.sleep(30)"],
                    timeout_seconds=1, log_path=log,
                )

    def test_only_new_auth_events_for_this_child_including_partial_lines(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "log"
            event = lambda pid, kind: json.dumps({
                "pid": pid, "msg": "shell.turn.inference_failed", "ctx": {"kind": kind},
            }) + "\n"
            path.write_text(event(1, "auth"))
            log = _AuthLog(path)
            with path.open("a") as stream:
                stream.write(event(2, "auth") + event(1, "network") + "malformed\n")
            self.assertFalse(log.failed(1))
            line = event(1, "auth")
            with path.open("a") as stream:
                stream.write(line[:15])
            self.assertFalse(log.failed(1))
            with path.open("a") as stream:
                stream.write(line[15:])
            self.assertTrue(log.failed(1))

    def test_log_rotation_is_seen(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "log"
            path.write_text("old log\n")
            log = _AuthLog(path)
            path.rename(path.with_suffix(".old"))
            path.write_text(json.dumps({
                "pid": 1, "msg": "shell.turn.inference_failed", "ctx": {"kind": "auth"},
            }) + "\n")
            self.assertTrue(log.failed(1))

    def test_auth_failure_records_once_and_is_not_retried(self):
        from resource_research_agent.pairwise_runner import _run_with_retries
        with patch("resource_research_agent.pairwise_runner.time.sleep") as sleep:
            with patch(__name__ + ".run_grok_process", side_effect=GrokAuthenticationError("sign in")) as action:
                records = []
                with self.assertRaises(GrokAuthenticationError):
                    _run_with_retries(
                        "Grok", action, retry_count=3, context={},
                        record_attempt=lambda **event: records.append(event),
                    )
                self.assertEqual(1, action.call_count)
                self.assertEqual(1, len(records))
                self.assertEqual("failed", records[0]["outcome"])
                sleep.assert_not_called()
