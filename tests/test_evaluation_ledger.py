from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
import tempfile
import unittest
from pathlib import Path
from resource_research_agent.evaluation.protocol import init_experiment,seal_protocol,read
from resource_research_agent.evaluation.ledger import Ledger,BudgetHold,maximum_charge,normalize_usage
from tests.evaluation_support import fixture,authorize


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.config,self.source=fixture(self.root);self.exp=self.root/'experiment'
        init_experiment(self.config,self.exp);seal_protocol(self.exp)
        self.bound=maximum_charge(self.config['provider'],self.config['pricing'])
    def tearDown(self):self.source.close();self.tmp.cleanup()
    def ledger(self,cap='10',simulation=True):
        authorize(self.exp,total=cap,stage=cap);return Ledger(self.exp,simulation=simulation)
    def reserve(self,l,aid='attempt-1',**extra):
        return l.reserve_attempt(aid,condition='existing-policy',category='housing',stage='housing-research',pass_key='shelter',request={'model':'deepseek-flash'},timeout_seconds=1,**extra)
    def response(self,l,aid='attempt-1',usage=None):
        l.mark_sent(aid)
        body=dict(model='deepseek-flash',usage=usage or dict(input_tokens=100,cache_read_input_tokens=10,cache_creation_input_tokens=5,output_tokens=20,server_tool_use={'web_search_requests':1}))
        l.record_response(aid,body);return body
    def test_exact_boundary_and_reservation_race(self):
        l=self.ledger(str(self.bound))
        def reserve(n):
            try:self.reserve(l,f'attempt-{n}');return True
            except BudgetHold:return False
        with ThreadPoolExecutor(max_workers=2) as pool:self.assertEqual([False,True],sorted(pool.map(reserve,[1,2])))
        self.assertEqual(str(self.bound),l.summarize_usage()['exposureUsd'])
    def test_cap_and_authorization_rejected_before_dispatch(self):
        l=self.ledger(str(self.bound-Decimal('.0001')))
        with self.assertRaises(BudgetHold):self.reserve(l)
        self.assertEqual(0,l.summarize_usage()['attempts'])
        live=Ledger(self.exp,simulation=False)
        with self.assertRaisesRegex(BudgetHold,'Simulation'):self.reserve(live)
    def test_unknown_outcome_does_not_release_or_replay(self):
        l=self.ledger();self.reserve(l);l.mark_sent('attempt-1');l.record_failure('attempt-1',diagnosis='Timed out after send')
        with self.assertRaises(BudgetHold):self.reserve(l,'attempt-2')
        with self.assertRaises(BudgetHold):l.mark_sent('attempt-1')
        self.assertEqual(str(self.bound),l.summarize_usage()['outstandingReservedUsd'])
    def test_response_adopted_once_after_interruption(self):
        l=self.ledger();self.reserve(l);body=self.response(l);before=l.summarize_usage()
        l.record_response('attempt-1',body)
        self.assertEqual(before,l.summarize_usage())
        self.assertEqual(1,before['attempts']);self.assertEqual('0',before['outstandingReservedUsd'])
    def test_missing_usage_remains_reserved(self):
        l=self.ledger();self.reserve(l);self.response(l,usage={'input_tokens':1})
        summary=l.summarize_usage();self.assertEqual(1,summary['unknownUsageAttempts'])
        self.assertEqual(str(self.bound),summary['exposureUsd'])
        self.assertIsNone(summary['knownBilledUsd'])
    def test_exclusive_cache_and_reasoning_not_double_charged(self):
        pricing=self.config['pricing'];usage=dict(input_tokens=100,cache_read_input_tokens=200,cache_creation_input_tokens=50,
            output_tokens=30,reasoning_tokens=20,server_tool_use={'web_search_requests':2})
        counters,cost=normalize_usage(usage,pricing)
        self.assertEqual(Decimal('.020230'),cost)
        pricing={**pricing,'inputAccounting':'totalIncludesCached'};usage['input_tokens']=350
        self.assertEqual(cost,normalize_usage(usage,pricing)[1])
        self.assertEqual(20,counters['reasoning'])
    def test_unknown_tool_price_and_changed_rate_hold(self):
        pricing={**self.config['pricing'],'searchPerUse':None}
        with self.assertRaises(BudgetHold):maximum_charge(self.config['provider'],pricing)
        l=self.ledger();p=self.exp/'inputs/pricing.json';p.write_text('{}')
        with self.assertRaises(BudgetHold):self.reserve(l)
    def test_diagnosed_not_sent_failure_releases_only_unused_reservation(self):
        l=self.ledger();self.reserve(l);l.record_failure('attempt-1',not_sent=True,diagnosis='Local credential preflight failed before transport')
        self.assertEqual('0',l.summarize_usage()['exposureUsd'])
        self.reserve(l,'attempt-2',recovery_of='attempt-1',diagnosis='Local preflight corrected')
        l.mark_sent('attempt-2')
        with self.assertRaises(BudgetHold):l.record_failure('attempt-2',not_sent=True,diagnosis='Cannot claim unused after send')
    def test_observed_charge_over_bound_stops_all_future_calls(self):
        l=self.ledger();self.reserve(l)
        with self.assertRaises(BudgetHold):self.response(l,usage=dict(input_tokens=100000000,cache_read_input_tokens=0,cache_creation_input_tokens=0,output_tokens=0,server_tool_use={'web_search_requests':0}))
        with self.assertRaisesRegex(BudgetHold,'Accounting'):self.reserve(l,'attempt-2')


if __name__=='__main__':unittest.main()
