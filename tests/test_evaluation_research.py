import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from resource_research_agent.evaluation.protocol import init_experiment,seal_protocol,EvaluationError,read
from resource_research_agent.evaluation.research import run_category,initialize_scratch,evaluation_lock
from resource_research_agent.evaluation.ledger import BudgetHold
from tests.evaluation_support import fixture,authorize
from tests.test_evaluation_deepseek import response,search_blocks,final


class ResearchTransport:
    is_live=False
    def __init__(self,interrupt_at=None):self.requests=[];self.interrupt_at=interrupt_at
    def __call__(self,payload,timeout):
        self.requests.append(json.loads(json.dumps(payload)))
        if self.interrupt_at==len(self.requests):raise KeyboardInterrupt('Synthetic process exit')
        i=len(self.requests)
        leads=[] if i>2 else [dict(organization='Shared Housing Agency',program='Shelter' if i==1 else 'Tenant Legal Help',
            website='https://shared.example.org',phone='480-555-0100',address='Mesa, AZ',leadType='program',
            locationOrServiceArea='Mesa, Arizona',whyRelevant='Direct shelter access' if i==1 else 'Direct tenant legal assistance',uncertainty='Confirm intake')]
        return response(search_blocks()+[dict(type='text',text=json.dumps({'leads':leads}))])


class ResearchTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.config,self.db=fixture(self.root)
        self.exp=self.root/'experiment';init_experiment(self.config,self.exp);seal_protocol(self.exp)
        self.network=patch('urllib.request.OpenerDirector.open',side_effect=AssertionError('No live requests in tests'));self.mock=self.network.start()
    def tearDown(self):self.mock.assert_not_called();self.network.stop();self.db.close();self.tmp.cleanup()
    def test_dry_run_without_authorization_and_default_has_no_dispatch(self):
        t=ResearchTransport();r=run_category(self.exp,'existing-policy','housing',transport=t)
        self.assertTrue(r['dryRun']);self.assertEqual([],t.requests)
        self.assertIn('Original Known Shelter',r['nextAssignment']['assignment'])
        self.assertNotIn('SECRET_REVIEWER_CANARY',json.dumps(r))
    def test_paid_flag_cannot_manufacture_authorization(self):
        t=ResearchTransport()
        with self.assertRaises(BudgetHold):run_category(self.exp,'existing-policy','housing',execute=True,transport=t)
        self.assertEqual([],t.requests)
    def test_scratch_symlink_and_hardlink_to_source_rejected(self):
        path=self.exp/'scratch/existing-policy.sqlite3';path.symlink_to(self.root/'source.sqlite3')
        with self.assertRaises(EvaluationError):initialize_scratch(self.exp,'existing-policy')
        path.unlink();import os;os.link(self.root/'source.sqlite3',path)
        with self.assertRaises(EvaluationError):initialize_scratch(self.exp,'existing-policy')
    def test_concurrent_invocation_is_rejected(self):
        with evaluation_lock(self.exp):
            with self.assertRaisesRegex(EvaluationError,'Another evaluation'):run_category(self.exp,'existing-policy','housing')
    def test_full_category_uses_own_discoveries_and_exactly_one_gap(self):
        authorize(self.exp);t=ResearchTransport();r=run_category(self.exp,'existing-policy','housing',execute=True,transport=t)
        self.assertEqual(1,sum(p['kind']=='gap' for p in r['passes']))
        self.assertEqual('completed-research-awaiting-source-audit',r['status'])
        self.assertFalse(r['importable']);self.assertIsNone(r['qualityJudgment'])
        self.assertNotIn('SECRET_REVIEWER_CANARY',json.dumps(t.requests))
        self.assertIn('Shared Housing Agency',json.dumps(t.requests[1]))
        self.assertEqual(2,sum(p['leadCount'] for p in r['passes']))
        before=len(t.requests);again=run_category(self.exp,'existing-policy','housing',execute=True,transport=t)
        self.assertEqual(before,len(t.requests));self.assertEqual(r,again)
        self.assertEqual(1,self.db.execute('SELECT count(*) FROM imports').fetchone()[0])
        self.assertEqual(1,self.db.execute('SELECT count(*) FROM focused_research_jobs').fetchone()[0])
    def test_policy_change_refuses_dispatch(self):
        t=ResearchTransport();authorize(self.exp)
        with patch('resource_research_agent.evaluation.research.policy_semantics',side_effect=[{'changed':1},{}]):
            with self.assertRaisesRegex(EvaluationError,'differs'):run_category(self.exp,'existing-policy','housing',execute=True,transport=t)
        self.assertEqual([],t.requests)


if __name__=='__main__':unittest.main()
