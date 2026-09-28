import tempfile
import unittest
from pathlib import Path
from resource_research_agent.evaluation.protocol import init_experiment,EvaluationError,read
from resource_research_agent.evaluation.baseline import readonly
from tests.evaluation_support import fixture


class BaselineTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.config,self.db=fixture(self.root);self.exp=self.root/'experiment'
    def tearDown(self):self.db.close();self.tmp.cleanup()
    def test_consistent_wal_backup_and_no_source_writes(self):
        before=self.db.execute('SELECT count(*) FROM sqlite_master').fetchone()
        self.assertTrue(Path(str(self.root/'source.sqlite3')+'-wal').exists())
        init_experiment(self.config,self.exp)
        with readonly(self.exp/'reference/source.sqlite3') as snapshot:
            self.assertEqual(self.db.execute('SELECT count(*) FROM manual_discovery_contributions').fetchone()[0],snapshot.execute('SELECT count(*) FROM manual_discovery_contributions').fetchone()[0])
            with self.assertRaises(Exception):snapshot.execute('CREATE TABLE forbidden(x)')
        self.assertEqual(before,self.db.execute('SELECT count(*) FROM sqlite_master').fetchone())
        self.assertEqual(7,read(self.exp/'baseline.json')['originalImportId'])
    def test_current_package_cannot_replace_original(self):
        (self.root/'original.zip').write_bytes(b'current package differs')
        with self.assertRaisesRegex(EvaluationError,'Original package'):init_experiment(self.config,self.exp)
    def test_policy_redaction_and_missing_history_stop_comparison(self):
        self.config['baseline']['redactRecoveryTargets']=True
        with self.assertRaisesRegex(EvaluationError,'redaction'):init_experiment(self.config,self.exp)
        self.config['baseline']['redactRecoveryTargets']=False
        self.config['baseline']['playbookVersions']['housing']='another-policy'
        with self.assertRaisesRegex(EvaluationError,'policy/playbook'):init_experiment(self.config,self.root/'second')


if __name__=='__main__':unittest.main()
