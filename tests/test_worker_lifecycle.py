import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
from resource_research_agent.worker_lifecycle import atomic_json, await_orphan, record_worker


class WorkerLifecycleTests(unittest.TestCase):
    def make_worker(self, root, age=0):
        atomic_json(root / "worker.json", {"pid": 12345, "identity": "original worker",
            "startedAt": (datetime.now(timezone.utc) - timedelta(seconds=age)).isoformat()})

    def test_restarted_coordinator_waits_for_matching_live_worker(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); self.make_worker(root)
            beats, pauses = [], []
            with patch("resource_research_agent.worker_lifecycle.process_identity", side_effect=[
                {"state": "Ss", "identity": "original worker"}, None]), patch("os.killpg") as kill:
                await_orphan(root, 60, beats.append, pause=pauses.append)
            self.assertEqual(1, len(beats))
            self.assertEqual(1, len(pauses))
            kill.assert_not_called()

    def test_reused_pid_is_never_signaled(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); self.make_worker(root, age=100)
            with patch("resource_research_agent.worker_lifecycle.process_identity", return_value={
                "state": "Ss", "identity": "unrelated worker"}), patch("os.killpg") as kill:
                with self.assertRaisesRegex(RuntimeError, "identity changed"):
                    await_orphan(root, 60, lambda _: None)
            kill.assert_not_called()

    def test_exiting_process_command_change_is_rechecked_without_signaling(self):
        for finished in (None, {"state": "Z", "identity": "defunct"}):
            with self.subTest(finished=finished), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary); self.make_worker(root, age=100)
                pauses = []
                with patch("resource_research_agent.worker_lifecycle.process_identity", side_effect=[
                    {"state": "Rs", "identity": "(python3.12)"}, finished]), patch("os.killpg") as kill:
                    await_orphan(root, 60, lambda _: None, pause=pauses.append)
                self.assertEqual([0.05], pauses)
                kill.assert_not_called()

    def test_termination_exit_race_does_not_escalate_to_sigkill(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); self.make_worker(root, age=100)
            with patch("resource_research_agent.worker_lifecycle.process_identity", side_effect=[
                {"state": "Ss", "identity": "original worker"},
                {"state": "Rs", "identity": "(python3.12)"},
                {"state": "Z", "identity": "defunct"}]), patch("os.killpg") as kill:
                with self.assertRaises(TimeoutError):
                    await_orphan(root, 60, lambda _: None, pause=lambda _: None)
            self.assertEqual(1, kill.call_count)

    def test_timed_out_matching_orphan_is_terminated(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); self.make_worker(root, age=100)
            with patch("resource_research_agent.worker_lifecycle.process_identity", side_effect=[
                {"state": "Ss", "identity": "original worker"}, None]), patch("os.killpg") as kill:
                with self.assertRaises(TimeoutError):
                    await_orphan(root, 60, lambda _: None, pause=lambda _: None)
            self.assertEqual(1, kill.call_count)
            self.assertEqual(12345, kill.call_args.args[0])

    def test_identity_record_is_durable_and_no_temporary_file_remains(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch("resource_research_agent.worker_lifecycle.process_identity", return_value={
                "state": "Ss", "identity": "original worker"}):
                record_worker(root, 12345, ["fake-worker"])
            saved = json.loads((root / "worker.json").read_text())
            self.assertEqual("original worker", saved["identity"])
            self.assertEqual(["fake-worker"], saved["command"])
            self.assertFalse((root / "worker.json.tmp").exists())
