"""Offline end-to-end evidence, interruption and category-limit checks."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from resource_research_agent.evaluation.protocol import init_experiment,seal_protocol,read
from resource_research_agent.evaluation.ledger import Ledger,BudgetHold
from resource_research_agent.evaluation.research import run_category
from tests.evaluation_support import fixture,authorize
from tests.test_evaluation_research import ResearchTransport
from tests.test_evaluation_deepseek import FakeTransport,response,search_blocks,final


class OfflineTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.config,self.db=fixture(self.root)
        self.network=patch('urllib.request.OpenerDirector.open',side_effect=AssertionError('No network permitted'));self.mock=self.network.start()
    def tearDown(self):self.mock.assert_not_called();self.network.stop();self.db.close();self.tmp.cleanup()
    def experiment(self,name):
        exp=self.root/name;init_experiment(self.config,exp);seal_protocol(exp);authorize(exp);return exp
    def test_whole_category_resume_equals_uninterrupted_results_and_charges(self):
        straight=self.experiment('straight');t1=ResearchTransport()
        expected=run_category(straight,'existing-policy','housing',execute=True,transport=t1)
        resumed=self.experiment('resumed');t2=ResearchTransport();original=Ledger.record_response;calls=0
        def interrupted(ledger,aid,body):
            nonlocal calls
            calls+=1
            if calls==3:raise KeyboardInterrupt('Crash after saving third native response')
            return original(ledger,aid,body)
        with patch.object(Ledger,'record_response',interrupted):
            with self.assertRaises(KeyboardInterrupt):run_category(resumed,'existing-policy','housing',execute=True,transport=t2)
        actual=run_category(resumed,'existing-policy','housing',execute=True,transport=t2)
        self.assertEqual(expected['passes'],actual['passes'])
        self.assertEqual(expected['candidates'],actual['candidates'])
        for field in ['attempts','states','exposureUsd','calculatedUsd','outstandingReservedUsd']:
            self.assertEqual(expected['usage'][field],actual['usage'][field],field)
        self.assertEqual(len(t1.requests),len(t2.requests))
    def test_zero_lead_category_and_gap_are_valid_research_not_quality_approval(self):
        exp=self.experiment('zero');t=FakeTransport([response(search_blocks()+[final()]) for _ in range(20)])
        result=run_category(exp,'existing-policy','housing',execute=True,transport=t)
        self.assertEqual([],result['candidates']);self.assertIsNone(result['qualityJudgment'])
        self.assertEqual(1,sum(p['kind']=='gap' for p in result['passes']))
    def test_category_cap_is_shared_across_passes(self):
        self.config['limits']['callsPerCategory']=1;exp=self.experiment('capped');t=ResearchTransport()
        with self.assertRaisesRegex(BudgetHold,'call cap'):run_category(exp,'existing-policy','housing',execute=True,transport=t)
        self.assertEqual(1,len(t.requests))
        self.assertEqual(1,Ledger(exp,simulation=True).summarize_usage()['attempts'])
        self.assertFalse((exp/'results/existing-policy/housing/summary.json').exists())
    def test_invalid_result_stays_original_evidence_and_does_not_complete_pass(self):
        exp=self.experiment('invalid');t=FakeTransport([response(search_blocks()+[dict(type='text',text='{"leads": [{"madeUp": true}]}')])])
        with self.assertRaises(ValueError):run_category(exp,'existing-policy','housing',execute=True,transport=t)
        self.assertTrue(list((exp/'attempts').rglob('response.raw')))
        self.assertFalse(list((exp/'results').rglob('*-original.json')))
        self.assertFalse((exp/'results/existing-policy/housing/summary.json').exists())


if __name__=='__main__':unittest.main()
