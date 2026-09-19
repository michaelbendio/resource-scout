import json
import tempfile
import unittest
from pathlib import Path
from resource_research_agent.worker_failures import classify_worker_failure, native_error


class WorkerFailureTests(unittest.TestCase):
    def test_budget_and_auth_are_not_unchanged_retries(self):
        for message, kind in [
            ('429 insufficient_quota', 'usage'),
            ('401 token expired while waiting; timeout', 'authentication'),
            ("Codex ran out of room in the model's context window", 'context'),
            ('worker timed out', 'timeout'),
        ]:
            failure = classify_worker_failure(message)
            self.assertEqual(kind, failure.kind)
            self.assertFalse(failure.retryable)
        self.assertTrue(classify_worker_failure('503 temporarily unavailable').retryable)
        self.assertFalse(classify_worker_failure('Unknown program failure').retryable)

    def test_native_json_error_survives_truncated_last_line_and_empty_stderr(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'stderr.log').write_text('')
            (root / 'events.jsonl').write_text(json.dumps({'type': 'turn.failed', 'error': {'message': 'context window exceeded'}}) + '\n{"partial')
            self.assertEqual('context window exceeded', native_error(root))

    def test_stderr_tail_fallback_is_bounded(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'stderr.log').write_text('x' * 10000 + ' authentication failed')
            self.assertLessEqual(len(native_error(root)), 4000)
            self.assertEqual('authentication', classify_worker_failure(native_error(root)).kind)
