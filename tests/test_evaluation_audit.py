import tempfile
import unittest
from pathlib import Path
from resource_research_agent.evaluation.protocol import init_experiment,seal_protocol,read,digest,EvaluationError
from resource_research_agent.evaluation.research import run_category
from resource_research_agent.evaluation.audit import build_audit_packet,record_stage_decision
from resource_research_agent.evaluation.cost_report import write_actuals
from tests.evaluation_support import fixture,authorize
from tests.test_evaluation_research import ResearchTransport

class AuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.config,self.db=fixture(self.root)
        self.db.execute('ALTER TABLE manual_discovery_contributions ADD COLUMN parsed_json TEXT')
        self.db.execute('UPDATE manual_discovery_contributions SET parsed_json=?',('{"leads":[]}',));self.db.commit()
        self.exp=self.root/'experiment';init_experiment(self.config,self.exp);seal_protocol(self.exp);authorize(self.exp)
    def tearDown(self):self.db.close();self.tmp.cleanup()
    def complete(self):
        run_category(self.exp,'existing-policy','housing',execute=True,transport=ResearchTransport())
        return build_audit_packet(self.exp)
    def judgment(self,packet):
        return dict(packetSha256=digest(packet),decision='advance',reviewer='Synthetic reviewer',reviewedAt='2026-09-27',
            reasons='Synthetic acceptance evidence',recognitionDisclosure='Synthetic fixture only',
            essentialAssessments=[dict(need='emergency shelter',outcome='supported',reason='A usable route exists',
                evidence=[dict(url='https://example.org/shelter',checkedAt='2026-09-27',finding='Synthetic intake evidence')])],
            consequentialErrorsResolved=True,remainingCodexWorkReduced=True,repeatedConsequentialErrors=False,uniqueAdditionsAuditComplete=True)
    def test_incomplete_research_cannot_be_scored(self):
        with self.assertRaisesRegex(EvaluationError,'Completed'):build_audit_packet(self.exp)
    def test_packet_deterministic_reveal_separate_and_no_dispatch(self):
        packet=self.complete();self.assertEqual(packet,build_audit_packet(self.exp))
        self.assertEqual({'A','B'},set(packet['collections']))
        self.assertNotIn('deepseek-existing-policy',str(packet))
        self.assertTrue((self.exp/'reference/housing-audit-reveal.json').exists())
        report=write_actuals(self.exp);self.assertIsNone(report['usage']['knownBilledUsd'])
        self.assertIn('Unmeasured',(self.exp/'reports/initial-projection.md').read_text())
    def test_missing_or_unsupported_essential_cannot_advance(self):
        packet=self.complete();j=self.judgment(packet)
        j['essentialAssessments'][0]['outcome']='miss'
        with self.assertRaisesRegex(EvaluationError,'Unresolved'):record_stage_decision(self.exp,'housing',j)
        j['essentialAssessments']=[]
        with self.assertRaisesRegex(EvaluationError,'every frozen'):record_stage_decision(self.exp,'housing',j)
    def test_repeated_errors_require_retest_and_valid_decision_is_immutable(self):
        packet=self.complete();j=self.judgment(packet);j['repeatedConsequentialErrors']=True
        with self.assertRaisesRegex(EvaluationError,'Repeated'):record_stage_decision(self.exp,'housing',j)
        j['decision']='targeted-retest';record_stage_decision(self.exp,'housing',j)
        j['reasons']='Changed after freeze'
        with self.assertRaises(EvaluationError):record_stage_decision(self.exp,'housing',j)

if __name__=='__main__':unittest.main()
