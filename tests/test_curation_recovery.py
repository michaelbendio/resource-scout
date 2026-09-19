import json
import tempfile
import unittest
import subprocess
import sys
import time
from pathlib import Path
from unittest.mock import Mock, patch

from resource_research_agent.curation_recovery import INPUT_FILES, recover_result
from resource_research_agent.worker_lifecycle import await_orphan, record_worker


class CurationRecoveryTests(unittest.TestCase):
    def test_real_surviving_process_is_adopted_without_duplicate_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); self.inputs(root)
            (root / 'events.jsonl').write_text('{"type":"turn.started"}\n')
            script = 'import pathlib,sys,time; time.sleep(.25); pathlib.Path(sys.argv[1]).write_text("{}")'
            command = [sys.executable, '-c', script, str(root / 'result.json')]
            process = subprocess.Popen(command, start_new_session=True)
            try:
                # macOS Homebrew's Python launcher execs the framework binary.
                # Record the established worker, not that transient launcher.
                time.sleep(.05)
                record_worker(root, process.pid, command)
                def adopt(folder, timeout, heartbeat):
                    return await_orphan(folder, timeout, heartbeat, pause=lambda _: time.sleep(.01))
                worker = Mock()
                with patch('resource_research_agent.curation_recovery.await_orphan', side_effect=adopt):
                    self.assertEqual(root, self.call(root, worker))
                worker.assert_not_called()
                self.assertEqual('{}', (root / 'result.json').read_text())
                self.assertEqual(0, process.wait(timeout=5))
                receipt = json.loads((root / 'orphan-recovery.json').read_text())
                self.assertEqual(process.pid, receipt['workerPid'])
                self.assertIsNone(receipt['exitCode'])
                with patch('resource_research_agent.curation_recovery.await_orphan') as adopt_again:
                    self.assertEqual(root, self.call(root, worker))
                adopt_again.assert_not_called()
            finally:
                if process.poll() is None:
                    process.terminate()
                process.wait(timeout=5)

    def inputs(self, root):
        for name in INPUT_FILES:
            (root / name).write_text('sealed ' + name)

    def failed(self, root, message):
        (root / 'events.jsonl').write_text(json.dumps({
            'type': 'turn.failed', 'error': {'message': message}}) + '\n')

    def call(self, root, execute):
        return recover_result(root, execute, heartbeat=lambda _: None,
                              timeout=60, effort='high')

    def test_one_transport_retry_preserves_inputs_and_reuses_result_on_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); self.inputs(root)
            calls = []
            def execute(folder, **options):
                calls.append(folder)
                self.assertEqual('high', options['effort'])
                if folder == root:
                    self.failed(folder, 'stream disconnected: connection reset')
                    raise RuntimeError('native transport failure')
                for name in INPUT_FILES:
                    self.assertEqual((root / name).read_bytes(), (folder / name).read_bytes())
                (folder / 'result.json').write_text('{"resources":[]}')
            with patch('resource_research_agent.curation_recovery.await_orphan'):
                result = self.call(root, execute)
                self.assertEqual(root / 'transport-retry-1', result)
                self.assertEqual(result, self.call(root, execute))
            self.assertEqual(2, len(calls))
            self.assertIn('connection reset', (root / 'events.jsonl').read_text())
            self.assertTrue((root / 'recovery-result.json').exists())

    def test_retry_budget_survives_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); self.inputs(root)
            def execute(folder, **_):
                self.failed(folder, '503 temporarily unavailable')
                raise RuntimeError('503')
            worker = Mock(side_effect=execute)
            with patch('resource_research_agent.curation_recovery.await_orphan'):
                for _ in range(2):
                    with self.assertRaisesRegex(RuntimeError, 'retry exhausted'):
                        self.call(root, worker)
            self.assertEqual(2, worker.call_count)

    def test_auth_usage_context_and_unknown_do_not_repeat_paid_work(self):
        for message in ('401 unauthorized', 'usage limit reached',
                        'context window exceeded', 'unrecognized failure'):
            with self.subTest(message=message), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp); self.inputs(root); self.failed(root, message)
                worker = Mock()
                with patch('resource_research_agent.curation_recovery.await_orphan'):
                    with self.assertRaises(RuntimeError):
                        self.call(root, worker)
                worker.assert_not_called()
                self.assertFalse((root / 'transport-retry-1').exists())

    def test_live_orphan_finishes_before_result_is_read_without_new_worker(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); self.inputs(root)
            (root / 'events.jsonl').write_text('{"type":"turn.started"}\n')
            def finish(*_):
                (root / 'result.json').write_text('{"resources":[]}')
            worker = Mock()
            with patch('resource_research_agent.curation_recovery.await_orphan', side_effect=finish) as adopt:
                self.assertEqual(root, self.call(root, worker))
            adopt.assert_called_once()
            worker.assert_not_called()

    def test_invalid_result_is_preserved_for_validation_without_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); self.inputs(root)
            (root / 'result.json').write_text('invalid output')
            worker = Mock()
            self.assertEqual(root, self.call(root, worker))
            worker.assert_not_called()
            self.assertEqual('invalid output', (root / 'result.json').read_text())

    def test_finished_attempt_does_not_inspect_a_potentially_reused_pid(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); self.inputs(root)
            (root / 'events.jsonl').write_text('{"type":"turn.completed"}\n')
            (root / 'execution.json').write_text('{"exitCode":0}')
            (root / 'result.json').write_text('{}')
            worker = Mock()
            with patch('resource_research_agent.curation_recovery.await_orphan') as adopt:
                self.assertEqual(root, self.call(root, worker))
            adopt.assert_not_called()
            worker.assert_not_called()

    def test_timeout_is_not_mistaken_for_prior_transient_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); self.inputs(root)
            def execute(folder, **_):
                self.failed(folder, 'stream disconnected')
                raise TimeoutError('deadline exceeded')
            with self.assertRaises(TimeoutError):
                self.call(root, execute)
            self.assertFalse((root / 'transport-retry-1').exists())
            worker = Mock()
            with patch('resource_research_agent.curation_recovery.await_orphan'):
                with self.assertRaisesRegex(RuntimeError, 'timeout'):
                    self.call(root, worker)
            worker.assert_not_called()

    def test_changed_retry_input_stops_before_launch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); self.inputs(root); self.failed(root, '503')
            retry = root / 'transport-retry-1'; retry.mkdir()
            (retry / 'assignment.json').write_text('tampered')
            worker = Mock()
            with patch('resource_research_agent.curation_recovery.await_orphan'):
                with self.assertRaisesRegex(ValueError, 'sealed input changed'):
                    self.call(root, worker)
            worker.assert_not_called()


if __name__ == '__main__':
    unittest.main()
