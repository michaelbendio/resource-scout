import io
import json
import tempfile
import unittest
import warnings
from pathlib import Path
from unittest.mock import patch
from resource_research_agent.performance import capture_timings, measured, timing_session, summarize_timings
from resource_research_agent.storage import ResearchStore


class PerformanceTests(unittest.TestCase):
    def test_disabled_and_content_free_nested_error_timing(self):
        with measured('disabled') as c:c['secret']='not serialized'
        with capture_timings() as events:
            with self.assertRaisesRegex(ValueError,'private'):
                with measured('outer') as c:
                    c.update(inputBytes=4,secret='private payload')
                    with measured('inner'):raise ValueError('private error')
        self.assertEqual(['inner','outer'],[x['phase'] for x in events])
        self.assertTrue(all(x['status']=='error' and x['seconds']>=0 for x in events))
        self.assertNotIn('private',json.dumps(events));self.assertNotIn('secret',json.dumps(events))
        self.assertEqual({'inputBytes':4},events[1]['counters'])

    def test_file_failure_does_not_prevent_commit_or_rollback(self):
        with tempfile.TemporaryDirectory() as tmp:
            store=ResearchStore(Path(tmp)/'qa.db')
            with warnings.catch_warnings(record=True) as alerts:
                with timing_session(tmp):
                    with store.connect() as c:c.execute('CREATE TABLE timing_qa(value INTEGER)')
                self.assertTrue(alerts)
            with capture_timings() as events:
                with self.assertRaises(ValueError):
                    with store.connect() as c:
                        c.execute('INSERT INTO timing_qa VALUES(1)');raise ValueError('private')
            self.assertIn('database.rollback',[e['phase'] for e in events])
            with store.connect() as c:self.assertEqual(0,c.execute('SELECT count(*) FROM timing_qa').fetchone()[0])
            path=Path(tmp)/'timing.jsonl'
            with timing_session(path):
                with store.connect() as c:c.execute('INSERT INTO timing_qa VALUES(2)')
            self.assertEqual(1,summarize_timings(path)['phases']['database.commit']['count'])

    def test_write_failure_preserves_work(self):
        class Broken(io.StringIO):
            def write(self,text):raise OSError('private disk issue')
        with patch('pathlib.Path.open',return_value=Broken()),warnings.catch_warnings(record=True) as alerts:
            with timing_session('/tmp/qa-no-write'):
                with measured('test'):pass
            self.assertTrue(alerts)
