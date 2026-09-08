"""Synthetic storage QA; no actual research or curator approval."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from resource_research_agent.improvement_packages import digest, write_package
from resource_research_agent.learning_evidence import EvidenceLedger
from resource_research_agent.project_state import decode_project_state, encode_project_state
from resource_research_agent.scout_maintenance import MaintenanceWorkflow
from resource_research_agent.storage import ResearchStore
from tests.test_scout_improvement import fixture_package
from tests.test_scout_maintenance import result_for


class ProjectStateTests(unittest.TestCase):
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
