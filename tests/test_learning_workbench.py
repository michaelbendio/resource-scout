"""Synthetic contract tests; none of these judgments are research or human vetting."""
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch
from resource_research_agent.cli import main
from resource_research_agent.improvement_packages import ImprovementError, write_package
from resource_research_agent.learning_evidence import EvidenceLedger
from resource_research_agent.learning_workbench import LearningWorkbench, ARMS, METRICS
from resource_research_agent.storage import ResearchStore
from tests.test_scout_improvement import fixture_package


class WorkbenchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.store = ResearchStore(Path(self.tmp.name) / 'test.db')
        self.now = 1000
        self.work = LearningWorkbench(self.store, clock=lambda: self.now)
        data = fixture_package()
        extra = deepcopy(data['resources'][0]); extra['id'] = 'support'; data['resources'].append(extra)
        for r in data['resources']:
            r['scoutEditorial'] = {'secret': 'ANSWER KEY'}
            r['openQuestions'] = [{'id': 'q', 'question': 'ANSWER KEY', 'explanation': 'Synthetic secret', 'status': 'open', 'resolution': ''}]
        self.package = write_package(data, {'pdfs/guide.pdf': b'%PDF exact bytes'})
        self.ledger = {'formatVersion': 1, 'run': {'sourceSha256': hashlib.sha256(self.package).hexdigest(),
                        'sourceRecordCount': 3, 'editor': 'Synthetic tester'},
                       'decisions': [{'resourceId': rid, 'disposition': 'retain', 'targetResourceIds': [rid],
                                      'reason': 'Synthetic decision'} for rid in ('r1','r2','support')],
                       'newOutputResources': [], 'output': {'finalUniqueResources': 3}}
        self.imported = self.work.import_editorial(self.package, json.dumps(self.ledger).encode())
        text = 'Synthetic baseline guidance'
        self.proposal = {'title': 'Synthetic lesson', 'supportIds': [self.imported['observationIds'][2]],
                         'scope': {'office': 'Test TSO', 'category': 'food', 'stage': 'editorial'},
                         'hypothesis': 'Named routes help', 'alternativeExplanation': 'Model variation',
                         'counterexample': 'A useful named referral',
                         'baseline': {'path': 'fixture.md', 'text': text, 'sha256': hashlib.sha256(text.encode()).hexdigest()},
                         'addition': 'Preserve usable referrals.', 'evaluationQuestion': 'Did useful programs survive?'}
        self.lesson = self.work.propose(self.proposal)['lessonId']
        self.spec = {'name': 'Synthetic paired test', 'operator': 'Synthetic operator', 'reason': 'Contract QA',
                     'modelConfig': {'provider': 'Synthetic', 'model': None, 'settings': {}},
                     'sourceSha256': self.imported['sourceSha256'],
                     'cases': [{'caseId': rid, 'resourceId': rid} for rid in ('r1','r2')],
                     'maxAssignments': 2, 'maxSeconds': 30, 'evaluationBasis': 'Synthetic fixture assertions'}
        self.trial = self.work.prepare_trial(self.lesson, self.spec)['trialId']

    def reply(self, arm, complete=True):
        packet = self.work.packet(self.trial, arm, 'context-' + arm, fresh=True)
        result = {'assignmentSha256': packet['assignmentSha256'], 'complete': complete,
                  'cases': [{'caseId': c['caseId'], 'decision': 'retain', 'reason': 'Synthetic reason',
                             'criticalDetails': ['Bring ID'], 'openQuestions': []} for c in packet['cases']]}
        receipt = {'contextId': packet['contextId'], 'fresh': True, 'modelConfig': self.spec['modelConfig'],
                   'incrementalCostUSD': None, 'interventions': 0, 'notes': 'Synthetic receipt'}
        return result, receipt

    def assessment(self):
        return {'reviewer': 'Synthetic QA', 'method': 'Fixture comparison', 'conclusion': 'no-clear-benefit',
                'limitations': 'Synthetic only', 'caseJudgments': [
                    {'caseId': rid, 'evidence': 'Exact fixture text', **{arm: {**{k: False for k in METRICS},
                     'reason': 'Synthetic parity'} for arm in ARMS}} for rid in ('r1','r2')]}

    def test_complete_cycle_restart_idempotence_no_activation(self):
        self.assertEqual(self.imported, self.work.import_editorial(self.package, json.dumps(self.ledger).encode()))
        for arm in ARMS:
            result, receipt = self.reply(arm)
            saved = self.work.submit(self.trial, arm, json.dumps(result), receipt)
            self.now += 2
            self.assertEqual(saved, self.work.submit(self.trial, arm, json.dumps(result), receipt))
        self.work = LearningWorkbench(ResearchStore(self.store.path), clock=lambda: self.now)
        report = self.work.assess(self.trial, self.assessment())
        self.assertEqual('evaluated', report['status']); self.assertFalse(report['active'])
        self.assertEqual(2, report['dispatches']); self.assertIsNone(report['responses']['baseline']['incrementalCostUSD'])
        self.assertEqual(0, report['quality']['candidate']['casesWithAnyFlag'])
        self.assertEqual(report, self.work.assess(self.trial, self.assessment()))
        self.assertFalse(report['assessment']['providerVerificationInferred'])
        with self.store.connect() as c:
            self.assertEqual(self.package, self.work._bytes(c, self.imported['sourceSha256'], 'resource-package'))
            self.assertEqual(0, c.execute("SELECT count(*) FROM sqlite_master WHERE name='scout_improvement_projects'").fetchone()[0])

    def test_invalid_imports_are_atomic(self):
        for mutate in (lambda x: x['decisions'].pop(),
                       lambda x: x['run'].update(sourceSha256='wrong'),
                       lambda x: x['decisions'][0].update(targetResourceIds=['missing']),
                       lambda x: x['decisions'][0].update(disposition='combine',targetResourceIds=['r1'])):
            bad = deepcopy(self.ledger); mutate(bad)
            with self.assertRaises(ImprovementError): self.work.import_editorial(self.package, json.dumps(bad).encode())
        with patch.object(self.work, '_record', side_effect=RuntimeError('injected')):
            bad = deepcopy(self.ledger); bad['run']['editor'] = 'Other synthetic editor'
            with self.assertRaises(RuntimeError): self.work.import_editorial(self.package, json.dumps(bad).encode())
        with self.store.connect() as c:
            self.assertEqual(2,c.execute('SELECT count(*) FROM scout_learning_artifacts').fetchone()[0])
            self.assertEqual(3,c.execute("SELECT count(*) FROM scout_learning_records WHERE kind='observation'").fetchone()[0])

    def test_packets_seal_guidance_omit_answers_and_enforce_context_and_examples(self):
        a = self.work.packet(self.trial, 'baseline', 'one', fresh=True)
        b = self.work.packet(self.trial, 'candidate', 'two', fresh=True)
        self.assertEqual(a['cases'],b['cases']); self.assertEqual(a['modelConfig'],b['modelConfig'])
        self.assertNotEqual(a['guidance'],b['guidance']); self.assertNotIn('ANSWER KEY',json.dumps(a))
        for arm,context,fresh in [('baseline','wrong',True),('candidate','one',True),('bad','new',True),('baseline','one',False)]:
            with self.assertRaises(ImprovementError): self.work.packet(self.trial,arm,context,fresh=fresh)
        spec=deepcopy(self.spec);spec['cases'][0]['resourceId']='support'
        with self.assertRaises(ImprovementError): self.work.prepare_trial(self.lesson,spec)
        proposal=deepcopy(self.proposal);proposal['baseline']['text']='tampered'
        with self.assertRaises(ImprovementError): self.work.propose(proposal)

    def test_deadline_and_late_capture_persist_after_restart(self):
        result,receipt=self.reply('baseline');self.now+=31
        self.work=LearningWorkbench(self.store,clock=lambda:self.now)
        with self.assertRaises(ImprovementError):self.work.packet(self.trial,'candidate','context-candidate',fresh=True)
        self.assertTrue(self.work.submit(self.trial,'baseline',json.dumps(result),receipt)['late'])
        self.assertEqual('incomplete',self.work.report(self.trial)['status'])

    def test_bad_complete_responses_and_receipts_rejected(self):
        result,receipt=self.reply('baseline')
        for mutate in (lambda x:x['cases'].pop(),lambda x:x['cases'].append(x['cases'][0]),
                       lambda x:x.update(assignmentSha256='bad'),lambda x:x['cases'][0].update(decision='invented')):
            bad=deepcopy(result);mutate(bad)
            with self.assertRaises(ImprovementError):self.work.submit(self.trial,'baseline',json.dumps(bad),receipt)
        for changes in ({'contextId':'bad'},{'fresh':False},{'incrementalCostUSD':-1},{'incrementalCostUSD':float('nan')},
                        {'modelConfig':{'provider':'Other','model':None,'settings':{}}}):
            with self.assertRaises(ImprovementError):self.work.submit(self.trial,'baseline',json.dumps(result),{**receipt,**changes})
        result['complete']=False;result['cases'].pop()
        self.work.submit(self.trial,'baseline',json.dumps(result),receipt)
        with self.assertRaises(ImprovementError):self.work.assess(self.trial,self.assessment())
        self.assertEqual('incomplete',self.work.report(self.trial)['status'])

    def test_tampered_assignment_and_immutable_history(self):
        result,receipt=self.reply('baseline')
        with self.store.connect() as c:
            p=json.loads(c.execute('SELECT packet FROM scout_learning_runs').fetchone()[0]);p['guidance']='changed'
            c.execute('UPDATE scout_learning_runs SET packet=?',(json.dumps(p),))
        with self.assertRaises(ImprovementError):self.work.submit(self.trial,'baseline',json.dumps(result),receipt)

    def test_package_changes_keep_original_evidence_strength(self):
        ledger=EvidenceLedger(self.store);data=fixture_package()
        before=ledger.import_package('test','Test TSO',write_package(data,{'pdfs/guide.pdf': b'%PDF synthetic'}),scope='full',historical=True)
        data['resources'][0]['name']='Observed change'
        after=ledger.import_package('test','Test TSO',write_package(data,{'pdfs/guide.pdf': b'%PDF synthetic'}),scope='full',historical=True)
        comparison=ledger.compare(before['id'],after['id'],reviewer='Synthetic',lineage_note='Explicit QA predecessor')
        imp=self.work.import_comparison(comparison['id'])
        self.assertEqual(imp,self.work.import_comparison(comparison['id']))
        obs=self.work.inspect(imp['observationIds'][0]);self.assertEqual('observed-change',obs['event']['level'])
        self.assertFalse(obs['providerVerificationInferred']);self.assertEqual(['r1'],obs['resourceIds'])

    def test_cli_roundtrip_and_timing(self):
        path=Path(self.tmp.name)/'source.zip';path.write_bytes(self.package)
        with redirect_stdout(io.StringIO()) as out:
            code=main(['--database',str(self.store.path),'--timings',str(Path(self.tmp.name)/'timings.jsonl'),
                       'learning','register-package',str(path)])
        self.assertEqual(0,code);self.assertEqual(3,json.loads(out.getvalue())['resources'])

    def test_rejected_raw_delivery_is_kept_without_completing_trial(self):
        self.reply('baseline')
        with self.assertRaisesRegex(ImprovementError,'raw delivery was preserved'):
            self.work.submit(self.trial,'baseline','{"incomplete raw',self.reply('baseline')[1])
        with self.store.connect() as c:
            docs=[json.loads(row[0]) for row in c.execute("SELECT document FROM scout_learning_records WHERE kind='trial-submission'")]
        self.assertEqual('{"incomplete raw',docs[0]['raw'])
        self.assertEqual('incomplete',self.work.report(self.trial)['status'])

    def test_ordinary_feedback_collection_is_idempotent_and_not_activation(self):
        self.test_package_changes_keep_original_evidence_strength()
        self.assertEqual(0,self.work.collect_comparisons()['newObservationVersions'])
        inbox=self.work.inbox();self.assertEqual(0,inbox['activeLessons']);self.assertEqual(1,len(inbox['lessons']))
