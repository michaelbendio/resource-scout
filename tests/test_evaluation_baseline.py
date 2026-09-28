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


class ReconstructedOriginalTests(unittest.TestCase):
    def setUp(self):
        from resource_research_agent.storage import ResearchStore
        from resource_research_agent.importer import ResourcePackageImporter
        from resource_research_agent.focused_research import (prepare_focused_research_job,next_focused_research_assignment,
            save_focused_research_result,prepare_focused_gap_pass,close_focused_research_job)
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.config,old=fixture(self.root);old.close()
        self.source=self.root/'real-source.sqlite3';self.store=ResearchStore(self.source)
        imported=ResourcePackageImporter('housing').read(self.root/'original.zip');iid=self.store.save_import(imported)
        job=prepare_focused_research_job(self.store,iid,category_id='housing',experiment_mode='codex-first-v1',redact_recovery_targets=False)
        while (assignment:=next_focused_research_assignment(self.store,job['id'])):
            save_focused_research_result(self.store,job['id'],assignment['focusKey'],'{"leads": []}')
        prepare_focused_gap_pass(self.store,job['id']);assignment=next_focused_research_assignment(self.store,job['id'])
        save_focused_research_result(self.store,job['id'],assignment['focusKey'],'{"leads": []}');close_focused_research_job(self.store,job['id'])
        self.config['baseline'].update(sourceDb=str(self.source),originalPackage=None,importId=iid,jobIds={'housing':job['id']},
            reconstructOriginalSnapshot=True,expectedContentSha256=imported.content_sha256)
        self.exp=self.root/'reconstructed'
    def tearDown(self):self.tmp.cleanup()
    def test_repacked_content_and_original_known_manifest_match(self):
        from resource_research_agent.evaluation.protocol import seal_protocol
        from resource_research_agent.evaluation.research import run_category
        init_experiment(self.config,self.exp);seal_protocol(self.exp)
        metadata=read(self.exp/'baseline.json')
        self.assertNotEqual(metadata['originalPackageSha256'],metadata['frozenPackageSha256'])
        self.assertEqual(self.config['baseline']['expectedContentSha256'],metadata['inputReconstruction']['canonicalContentSha256'])
        self.assertTrue(run_category(self.exp,'existing-policy','housing')['dryRun'])
    def test_changed_raw_resource_cannot_pass_as_original(self):
        with self.store.connect() as db:db.execute("UPDATE imported_resources SET raw_json='{}'")
        with self.assertRaisesRegex(EvaluationError,'cannot be established'):init_experiment(self.config,self.exp)
    def test_original_assignment_baseline_is_an_independent_gate(self):
        from resource_research_agent.evaluation.protocol import seal_protocol
        from resource_research_agent.evaluation.research import run_category
        with self.store.connect() as db:db.execute("UPDATE focused_research_jobs SET baseline_manifest_sha256=?",('0'*64,))
        init_experiment(self.config,self.exp);seal_protocol(self.exp)
        with self.assertRaisesRegex(EvaluationError,'known resources differ'):run_category(self.exp,'existing-policy','housing')


if __name__=='__main__':unittest.main()
