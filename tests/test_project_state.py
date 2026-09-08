"""Synthetic storage QA; no actual research or curator approval."""
import base64
import json
import tempfile
import unittest
import zlib
from pathlib import Path
from unittest.mock import patch

from resource_research_agent.improvement_packages import digest, write_package
from resource_research_agent.learning_evidence import EvidenceLedger
from resource_research_agent.project_state import decode_project_state, encode_project_state
from resource_research_agent.scout_maintenance import MaintenanceWorkflow
from resource_research_agent.storage import ResearchStore
from tests.test_scout_improvement import fixture_package
from tests.test_scout_maintenance import result_for
from tests.test_research_execution import response, settings


class ProjectStateTests(unittest.TestCase):
    @staticmethod
    def legacy_compressed(state):
        # The previous release wrote the same envelope with zlib's default
        # compression level. Keep this fixture independent of the new encoder.
        return json.dumps({'_scoutStateEncoding': 'scout-project-json-zlib-v1',
                           'payload': base64.b64encode(zlib.compress(
                               json.dumps(state, ensure_ascii=False).encode('utf-8'))).decode('ascii')})

    def test_lossless_legacy_and_compressed_hashes(self):
        state = {'office': 'Mésa', 'notes': 'a\n"b" · 🏠', 'null': None,
                 'decisions': [{'resolved': True, 'note': 'Keep my words.'}],
                 'assignments': {'sealed': {'assignmentSha256': 'unchanged'}}}
        plain = encode_project_state(state)
        self.assertEqual(json.loads(plain), state)
        with patch('resource_research_agent.project_state.COMPRESSION_THRESHOLD', 1):
            packed = encode_project_state(state)
        self.assertEqual(decode_project_state(packed), state)
        self.assertEqual(digest(decode_project_state(packed)), digest(state))
        self.assertEqual(decode_project_state(plain), state)

    def test_fast_and_previous_compression_are_bidirectionally_compatible(self):
        state = {'notes': 'Mésa · 🏠\n' * 1000,
                 'questions': [{'resolved': True, 'resolution': 'Keep the curator’s exact words.'}]}
        self.assertEqual(decode_project_state(self.legacy_compressed(state)), state)
        with patch('resource_research_agent.project_state.COMPRESSION_THRESHOLD', 1):
            encoded = encode_project_state(state)
        # A reader from the previous release needs no migration or new codec.
        envelope = json.loads(encoded)
        self.assertEqual(envelope['_scoutStateEncoding'], 'scout-project-json-zlib-v1')
        old_reader = json.loads(zlib.decompress(base64.b64decode(envelope['payload'], validate=True)))
        self.assertEqual(old_reader, state)

    def test_legacy_blind_checkpoint_resumes_without_resealing_research(self):
        with tempfile.TemporaryDirectory() as folder, patch(
                'resource_research_agent.project_state.COMPRESSION_THRESHOLD', 1):
            store = ResearchStore(Path(folder) / 'qa.sqlite3')
            flow = MaintenanceWorkflow(store)
            data = fixture_package()
            data['resources'][0]['openQuestions'] = [
                {'id': 'q', 'question': 'Which office?', 'explanation': 'Synthetic question',
                 'status': 'resolved', 'resolution': 'Curator confirmed the Mesa office.'}]
            payload = write_package(data, {'pdfs/guide.pdf': b'%PDF synthetic exact bytes'})
            pid = flow.prepare(payload, 'Test TSO', ['r1'], [],
                               run_name='Legacy blind checkpoint QA', historical=True,
                               execution_config=settings(deliberate=['food']))['id']
            for stage in ('primary', 'freeze'):
                a = flow.next_assignment(pid, researcher='Codex')
                self.assertEqual(a['stage'], stage)
                flow.submit(pid, stage, response(a))
            flow.record_provider(pid, flow.view(pid)['revision'], 'Claude', 'available',
                                 'Synthetic operator', 'Synthetic availability', 'synthetic-blind')
            blind = flow.next_assignment(pid, researcher='Claude')
            with store.connect() as c:
                raw = c.execute('SELECT state_json FROM scout_improvement_projects WHERE id=?', (pid,)).fetchone()[0]
                before = decode_project_state(raw)
                c.execute('UPDATE scout_improvement_projects SET state_json=? WHERE id=?',
                          (self.legacy_compressed(before), pid))
            restarted = MaintenanceWorkflow(ResearchStore(store.path))
            self.assertEqual(restarted.next_assignment(pid, researcher='Claude'), blind)
            restarted.submit(pid, 'blind:Claude', response(blind))
            restarted = MaintenanceWorkflow(ResearchStore(store.path))
            reconcile = restarted.next_assignment(pid, researcher='Codex')
            self.assertEqual(reconcile['stage'], 'reconcile')
            restarted.submit(pid, 'reconcile', response(reconcile))
            with store.connect() as c:
                after = restarted._load(c, pid)  # Includes all sealed-hash validation.
                self.assertEqual(restarted._package(c, after['baseSha256'])['data'], data)
                self.assertEqual(c.execute('SELECT payload FROM scout_improvement_packages WHERE sha256=?',
                                          (after['baseSha256'],)).fetchone()[0], payload)
            self.assertEqual(after['execution'], before['execution'])
            old_task = before['tasks']['recheck:r1']
            new_task = after['tasks']['recheck:r1']
            self.assertEqual(new_task['primaryFreeze'], old_task['primaryFreeze'])
            for stage, assignment in old_task['assignments'].items():
                self.assertEqual(new_task['assignments'][stage], assignment)
            for stage, result in old_task['results'].items():
                self.assertEqual(new_task['results'][stage], result)
            self.assertEqual(restarted.view(pid)['coverage']['recheck']['completed'], 1)

    def test_corrupt_or_future_encoding_is_rejected(self):
        for value in ({'_scoutStateEncoding': 'future', 'payload': ''},
                      {'_scoutStateEncoding': 'scout-project-json-zlib-v1', 'payload': 'not base64'}):
            with self.assertRaises(ValueError):
                decode_project_state(json.dumps(value))

    def test_compressed_project_resumes_and_preserves_history_and_evidence(self):
        with tempfile.TemporaryDirectory() as folder, patch(
                'resource_research_agent.project_state.COMPRESSION_THRESHOLD', 1):
            store = ResearchStore(Path(folder) / 'qa.sqlite3')
            flow = MaintenanceWorkflow(store)
            payload = write_package(fixture_package(), {'pdfs/guide.pdf': b'%PDF synthetic'})
            pid = flow.prepare(payload, 'Test TSO', ['r1'], ['food'],
                               run_name='Compressed QA', historical=True)['id']
            a = flow.next_assignment(pid)
            restarted = MaintenanceWorkflow(store)
            self.assertEqual(restarted.next_assignment(pid), a)
            while a := restarted.next_assignment(pid):
                restarted.submit(pid, a['stage'], result_for(a))
            with store.connect() as c:
                raw = c.execute('SELECT state_json FROM scout_improvement_projects WHERE id=?', (pid,)).fetchone()[0]
                self.assertIn('_scoutStateEncoding', json.loads(raw))
                before = decode_project_state(raw)
            self.assertEqual(restarted.list_projects(), [{'id': pid, 'office': 'Test TSO'}])
            ledger = EvidenceLedger(store)
            ledger.import_package('qa', 'Test TSO', payload, scope='full', historical=True)
            captured = ledger.capture_project('qa', pid)
            self.assertEqual(captured['state'], before)
            # A second execution must still see the first run's exact observations.
            second = restarted.prepare(payload, 'Test TSO', ['r1'], [],
                                       run_name='Next compressed QA', historical=True)['id']
            followup = restarted.next_assignment(second)
            self.assertTrue(followup['priorChecks'])
            self.assertEqual(followup['priorChecks'][0]['result'],
                             before['tasks']['recheck:r1']['results']['reconcile'])
