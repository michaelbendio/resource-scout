import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from resource_research_agent.curation_recovery import INPUT_FILES, recover_result
from resource_research_agent.scout_curation_runner import file_index_view, compact_assignment


class ContextRecoveryTests(unittest.TestCase):
    def prepare(self, root):
        for name in INPUT_FILES:
            (root / name).write_text('{}')
        view = {'candidates': [{'id': 'one', 'name': 'Clinic'}],
                'previousResourceIndex': [{'id': 'prior', 'name': 'Clinic'}]}
        (root / 'view.json').write_text(json.dumps(view))
        (root / 'prompt.txt').write_text('Original large prompt ' * 100)
        (root / 'events.jsonl').write_text(json.dumps({'type': 'turn.failed', 'error': {'message': 'context window exceeded'}}))
        (root / 'execution.json').write_text('{"exitCode":1}')
        (root / 'reviewed-resources.json').write_text('{"resources":[]}')
        child = root / 'context-retry-1'; child.mkdir()
        for name in (*INPUT_FILES, 'reviewed-resources.json'):
            (child / name).write_bytes((root / name).read_bytes())
        bounded, index = file_index_view(view)
        (child / 'view.json').write_text(json.dumps(bounded))
        (child / 'prior-resource-index.json').write_text(json.dumps(index))
        (child / 'prompt.txt').write_text('Read the same complete evidence in bounded chunks.')
        self.seal(root, child)
        return child

    def seal(self, root, child):
        digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
        (root / 'reviewed-context-recovery.json').write_text(json.dumps({
            'schemaVersion': 1, 'maximumAttempts': 1, 'reviewer': 'root',
            'reason': 'Diagnosed oversized inline prior index; relocate without deleting evidence.',
            'originalHashes': {p.name: digest(p) for p in root.iterdir() if p.is_file() and p.name != 'reviewed-context-recovery.json'},
            'retryHashes': {p.name: digest(p) for p in child.iterdir() if p.is_file()},
        }))

    def call(self, root, worker):
        return recover_result(root, worker, heartbeat=lambda _: None, timeout=60, effort='high')

    def test_retry_preserves_evidence_effort_and_reuses_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); child = self.prepare(root)
            before = (root / 'events.jsonl').read_bytes()
            def execute(folder, **options):
                self.assertEqual(child, folder)
                self.assertEqual('high', options['effort'])
                (folder / 'result.json').write_text('{}')
            worker = Mock(side_effect=execute)
            self.assertEqual(child, self.call(root, worker))
            self.assertEqual(child, self.call(root, worker))
            self.assertEqual(1, worker.call_count)
            self.assertEqual(before, (root / 'events.jsonl').read_bytes())

    def test_failed_context_retry_is_not_relaunched(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); child = self.prepare(root)
            (child / 'events.jsonl').write_bytes((root / 'events.jsonl').read_bytes())
            (child / 'execution.json').write_text('{"exitCode":1}')
            worker = Mock()
            with self.assertRaisesRegex(RuntimeError, 'context'):
                self.call(root, worker)
            worker.assert_not_called()

    def test_tampered_input_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); child = self.prepare(root)
            (child / 'assignment.json').write_text('changed')
            with self.assertRaisesRegex(ValueError, 'sealed input changed'):
                self.call(root, Mock())

    def test_context_plan_does_not_grant_another_transport_attempt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); child = self.prepare(root)
            def fail(folder, **_):
                (folder / 'events.jsonl').write_text(json.dumps({'type': 'turn.failed', 'error': {'message': '503 temporarily unavailable'}}))
                (folder / 'execution.json').write_text('{"exitCode":1}')
                raise RuntimeError('503 temporarily unavailable')
            worker = Mock(side_effect=fail)
            for _ in range(2):
                with self.assertRaisesRegex(RuntimeError, 'retry exhausted'):
                    self.call(root, worker)
            self.assertEqual(1, worker.call_count)
            self.assertFalse((child / 'transport-retry-1').exists())

    def test_resealed_candidate_loss_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); child = self.prepare(root)
            view = json.loads((child / 'view.json').read_text()); view['candidates'] = []
            (child / 'view.json').write_text(json.dumps(view)); self.seal(root, child)
            with self.assertRaisesRegex(ValueError, 'preserve all candidates'):
                self.call(root, Mock())

    def test_full_prior_records_are_not_inlined(self):
        assignment = {'batch': {'priorIndexFormat': 'file-v1'}, 'candidates': [],
                      'previouslyCuratedResources': [{'id': 'a', 'name': 'A', 'description': 'long detail', 'informationText': 'complete facts'}]}
        view, index = file_index_view(compact_assignment(assignment))
        self.assertNotIn('previousResourceIndex', view)
        self.assertEqual(1, view['previousResourceCount'])
        self.assertNotIn('description', index[0])
        self.assertEqual('complete facts', assignment['previouslyCuratedResources'][0]['informationText'])


if __name__ == '__main__':
    unittest.main()
