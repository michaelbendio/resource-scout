"""Synthetic lifecycle tests; approvals here authorize fixtures, never real guidance."""
from copy import deepcopy
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from tests import test_learning_workbench as fixtures
from tests.test_scout_improvement import fixture_package
from tests.test_research_execution import settings, response
from resource_research_agent.learning_workbench import LearningWorkbench, ARMS
from resource_research_agent.learning_evidence import EvidenceLedger
from resource_research_agent.improvement_packages import ImprovementError, write_package
from resource_research_agent.scout_maintenance import MaintenanceWorkflow
from resource_research_agent.frontier_editor import FrontierEditorWorkflow


class ActivationTests(unittest.TestCase):
    reply = fixtures.WorkbenchTests.reply
    assessment = fixtures.WorkbenchTests.assessment

    def setUp(self):
        fixtures.WorkbenchTests.setUp(self)
        self.baseline = Path(self.tmp.name)/'baseline.md'
        self.baseline.write_text(self.proposal['baseline']['text'])
        self.proposal['baseline']['path'] = str(self.baseline)
        self.lesson = self.work.propose(self.proposal)['lessonId']
        self.trial = self.work.prepare_trial(self.lesson, self.spec)['trialId']
        self.initial = self.work.manifest()['manifestId']

    def evaluate(self, conclusion='promising'):
        for arm in ARMS:
            result, receipt = self.reply(arm)
            self.work.submit(self.trial, arm, json.dumps(result), receipt)
        assessment = self.assessment(); assessment['conclusion'] = conclusion
        return self.work.assess(self.trial, assessment)

    def review(self, **changes):
        doc = {'reviewer':'Synthetic authorized reviewer', 'decision':'activate',
               'rationale':'Synthetic fixture only', 'trialIds':[self.trial], 'supersedes':[]}
        doc.update(changes)
        return self.work.review_guidance(self.lesson, doc)

    def activate(self):
        review = self.review()
        return self.work.activate(review['reviewId'], review['expectedManifestId'])

    def test_lifecycle_scoped_use_rollback_restart_and_history(self):
        self.assertEqual(self.work.lesson_status(self.lesson), 'experiment')
        self.evaluate()
        self.assertEqual(self.work.lesson_status(self.lesson), 'evaluated')
        active = self.activate()
        self.assertEqual(self.work.lesson_status(self.lesson), 'active')
        self.assertEqual(self.work.inbox()['activeLessons'], 1)
        self.assertEqual(len(self.work.resolve_guidance('test tso', ['food'], 'editorial')['lessons']), 1)
        for office, cats, stage in [('Other', ['food'], 'editorial'), ('Test TSO',['jobs'],'editorial'),('Test TSO',['food'],'research')]:
            self.assertEqual(self.work.resolve_guidance(office,cats,stage)['lessons'], [])
        old = deepcopy(self.work.inspect(active['manifestId']))
        self.work = LearningWorkbench(self.store)
        back = self.work.rollback(self.initial, expected_manifest_id=active['manifestId'], reviewer='QA', reason='Synthetic rollback')
        self.assertEqual(back['entries'], [])
        self.assertEqual(self.work.inspect(active['manifestId']),old)
        self.assertEqual(self.work.lesson_status(self.lesson),'superseded')
        self.review(decision='reject',trialIds=[])
        self.assertEqual(self.work.lesson_status(self.lesson),'rejected')
        with self.assertRaisesRegex(ImprovementError,'rejection'):
            self.work.rollback(active['manifestId'],expected_manifest_id=back['manifestId'],reviewer='QA',reason='Invalid restore')

    def test_activation_requires_review_applicable_evaluation_and_unchanged_baseline(self):
        with self.assertRaisesRegex(ImprovementError,'promising'):
            self.review()
        self.evaluate('no-clear-benefit')
        with self.assertRaisesRegex(ImprovementError,'promising'):
            self.review()
        self.assertEqual(self.work.manifest()['manifestId'],self.initial)

    def test_late_result_cannot_activate(self):
        for arm in ARMS:
            self.reply(arm)
        self.now += 31
        self.evaluate()
        with self.assertRaisesRegex(ImprovementError,'over-budget'):
            self.review()

    def test_stale_reviews_baseline_changes_and_atomic_failure(self):
        self.evaluate(); review = self.review()
        original = self.work._record
        def broken(c,kind,doc):
            result = original(c,kind,doc)
            if kind == 'guidance-manifest':raise RuntimeError('Simulated crash after manifest write, before head update')
            return result
        with patch.object(self.work,'_record',side_effect=broken),self.assertRaises(RuntimeError):
            self.work.activate(review['reviewId'],self.initial)
        self.assertEqual(self.work.manifest()['manifestId'],self.initial)
        self.baseline.write_text('Changed baseline')
        with self.assertRaisesRegex(ImprovementError,'Baseline guidance changed'):
            self.work.activate(review['reviewId'],self.initial)
        self.baseline.write_text(self.proposal['baseline']['text'])
        self.review(decision='defer',trialIds=[])
        with self.assertRaisesRegex(ImprovementError,'superseded'):
            self.work.activate(review['reviewId'],self.initial)
        active = self.activate()
        with self.assertRaisesRegex(ImprovementError,'manifest changed'):
            self.work.activate(review['reviewId'],self.initial)
        with self.assertRaisesRegex(ImprovementError,'manifest changed'):
            self.work.rollback(self.initial,expected_manifest_id=self.initial,reviewer='QA',reason='Stale')
        self.assertEqual(self.work.manifest()['manifestId'],active['manifestId'])

    def test_scope_conflict_requires_explicit_supersession(self):
        self.evaluate(); first=self.lesson; active=self.activate()
        self.proposal['addition']='Synthetic replacement amendment'
        self.lesson=self.work.propose(self.proposal)['lessonId']
        self.trial=self.work.prepare_trial(self.lesson,{**self.spec,'name':'Replacement'})['trialId']
        sealed = self.work.inspect(self.trial)
        self.assertEqual(sealed['guidanceContext']['baselineLessonIds'], [first])
        self.assertIn('Preserve usable referrals.', sealed['baselineGuidance'])
        self.assertNotIn('Preserve usable referrals.', sealed['candidateGuidance'])
        # Fresh contexts must also be unique across trials.
        for arm in ARMS:
            packet=self.work.packet(self.trial,arm,'replacement-'+arm,fresh=True)
            result={'assignmentSha256':packet['assignmentSha256'],'complete':True,'cases':[
                {'caseId':c['caseId'],'decision':'retain','reason':'Synthetic','criticalDetails':[],'openQuestions':[]} for c in packet['cases']]}
            receipt={'contextId':packet['contextId'],'fresh':True,'modelConfig':self.spec['modelConfig'], 'incrementalCostUSD':None,'interventions':0,'notes':'Synthetic'}
            self.work.submit(self.trial,arm,json.dumps(result),receipt)
        assessment=self.assessment();assessment['conclusion']='promising';self.work.assess(self.trial,assessment)
        review=self.review()
        with self.assertRaisesRegex(ImprovementError,'Conflicting active scope'):
            self.work.activate(review['reviewId'],active['manifestId'])
        review=self.review(supersedes=[first])
        self.work.activate(review['reviewId'],active['manifestId'])
        self.assertEqual(self.work.lesson_status(first),'superseded')

    def test_wrong_scope_or_saved_case_stage_rejected(self):
        for scope in ({'office':'Other','category':'food','stage':'editorial'},
                      {'office':'Test TSO','category':'jobs','stage':'editorial'},
                      {'office':'Test TSO','category':'food','stage':'research'}):
            self.proposal['scope']=scope; self.lesson=self.work.propose(self.proposal)['lessonId']
            self.trial=self.work.prepare_trial(self.lesson,self.spec)['trialId']
            # The validation can be exercised after a copied complete synthetic evaluation.
            for arm in ARMS:
                p=self.work.packet(self.trial,arm,self.lesson+arm,fresh=True)
                r={'assignmentSha256':p['assignmentSha256'],'complete':True,'cases':[{'caseId':x['caseId'],'decision':'retain','reason':'Synthetic','criticalDetails':[],'openQuestions':[]} for x in p['cases']]}
                self.work.submit(self.trial,arm,json.dumps(r),{'contextId':p['contextId'],'fresh':True,'modelConfig':self.spec['modelConfig'],'incrementalCostUSD':None,'interventions':0,'notes':'Synthetic'})
            a=self.assessment();a['conclusion']='promising';self.work.assess(self.trial,a)
            with self.assertRaises(ImprovementError): self.review()

    def test_editor_seals_guidance_and_old_packets_survive_activation_and_rollback(self):
        flow=FrontierEditorWorkflow(self.store)
        config={'name':'Synthetic editor','editor':'QA','model':None,'settings':{},'sourceScope':'full','categoryIds':['food'],'authorityNote':'Synthetic only'}
        before=flow.prepare(self.package,'Test TSO',config)['id']
        old=flow.packet(before,'early')
        self.evaluate();active=self.activate()
        after=flow.prepare(self.package,'Test TSO',config)['id']
        new=flow.packet(after,'early')
        self.assertNotEqual(before,after)
        self.assertEqual(new['learnedGuidance']['lessons'][0]['addition'],self.proposal['addition'])
        self.work.rollback(self.initial,expected_manifest_id=active['manifestId'],reviewer='QA',reason='Synthetic')
        self.assertEqual(flow.packet(before,'early'),old)
        self.assertEqual(flow.packet(after,'early'),new)

    def test_research_protocol_neutrality_and_sealed_assignment_integration(self):
        self.proposal['scope']['stage']='research';self.lesson=self.work.propose(self.proposal)['lessonId']
        self.spec['researchProtocol']={'version':2,'maxSourcePages':8,'maxWebCalls':8}
        self.trial=self.work.prepare_trial(self.lesson,self.spec)['trialId']
        baseline=self.work.packet(self.trial,'baseline','context-baseline',fresh=True)
        candidate=self.work.packet(self.trial,'candidate','context-candidate',fresh=True)
        self.assertEqual(baseline['instructions'],candidate['instructions'])
        self.assertNotIn('usable named referrals',baseline['instructions'])
        self.assertEqual(set(baseline['cases'][0]['resource']),{'name','website'})
        self.assertNotIn('ANSWER KEY',json.dumps(baseline))
        flow=MaintenanceWorkflow(self.store)
        before=flow.prepare(self.package,'Test TSO',['r1'],[],run_name='Before',historical=True,execution_config=settings(1))['id']
        old=flow.next_assignment(before)
        self.evaluate();active=self.activate()
        after=flow.prepare(self.package,'Test TSO',['r1'],[],run_name='After',historical=True,execution_config=settings(1))['id']
        new=flow.next_assignment(after)
        self.assertIn('learnedGuidance',new)
        self.assertEqual(flow.next_assignment(before),old)
        flow.submit(after,new['stage'],response(new))
        freeze=flow.next_assignment(after);flow.submit(after,freeze['stage'],response(freeze))
        flow.record_provider(after,flow.view(after)['revision'],'Claude','available','QA','Synthetic','qa-claude')
        blind=flow.next_assignment(after,researcher='Claude')
        self.assertNotIn('learnedGuidance',blind)
        self.assertNotIn(self.proposal['addition'],json.dumps(blind))
        self.work.rollback(self.initial,expected_manifest_id=active['manifestId'],reviewer='QA',reason='Synthetic')
        self.assertEqual(flow.next_assignment(before),old)

    def test_feedback_deduplicates_versions_preserves_questions_absence_and_distillation(self):
        ledger=EvidenceLedger(self.store)
        data=fixture_package();data['resources'][0]['openQuestions']=[{'id':'q','question':'Where to apply?', 'explanation':'Synthetic conflicting routes', 'status':'open','resolution':''}]
        a=ledger.import_package('feedback','Test TSO',write_package(data,{'pdfs/guide.pdf':b'%PDF synthetic'}),scope='full')
        data['resources'][0]['openQuestions'][0].update(status='resolved',resolution='Curator says call county directly')
        b=ledger.import_package('feedback','Test TSO',write_package(data,{'pdfs/guide.pdf':b'%PDF synthetic'}),scope='partial')
        comp=ledger.compare(a['id'],b['id'],reviewer='QA',lineage_note='Same office package')
        self.work.collect_comparisons(); first=self.work.feedback_queue()
        self.work.import_comparison(comp['id']);second=self.work.feedback_queue()
        self.assertEqual(first,second)
        qgroup=next(g for g in second['groups'] if g['topic']=='openQuestions')
        self.assertEqual(qgroup['distinctEventCount'],1)
        ids=[x['observationId'] for x in qgroup['observations']]
        raw=json.dumps(qgroup)
        self.assertIn('Curator says call county directly',raw)
        self.assertFalse(qgroup['observations'][0]['evidence']['providerVerificationInferred'])
        data['resources'][0]['openQuestions'][0].update(status='open',resolution='Conflicting later answer')
        data['resources'].pop()
        c=ledger.import_package('feedback','Test TSO',write_package(data,{'pdfs/guide.pdf':b'%PDF synthetic'}),scope='partial')
        ledger.compare(b['id'],c['id'],reviewer='QA',lineage_note='Later partial update')
        groups=self.work.feedback_queue()['groups']
        self.assertIn('Conflicting later answer',json.dumps(groups))
        self.assertTrue(any('not evidence' in str(g['cautions']) for g in groups))
        document={'reviewer':'Synthetic editor','observationIds':ids,'counterevidenceIds':[], 'kind':'resource-fact','interpretation':'A fact update, cause not established','proposal':None}
        saved=self.work.distill(document)
        self.assertIsNone(saved['lessonId'])
        self.assertEqual(saved,self.work.distill(document))
        proposal=deepcopy(self.proposal);proposal['supportIds']=ids
        document.update(kind='method',interpretation='Potential transferable method, not provider verification',proposal=proposal)
        method=self.work.distill(document)
        self.assertEqual(self.work.lesson_status(method['lessonId']),'proposed')
        document['kind']='policy'
        with self.assertRaisesRegex(ImprovementError,'Only method'):
            self.work.distill(document)


if __name__=='__main__':unittest.main()

class FeedbackEdgeTests(unittest.TestCase):
    setUp = ActivationTests.setUp
    reply = ActivationTests.reply
    assessment = ActivationTests.assessment
    review = ActivationTests.review

    def test_restored_exclusion_is_linked_as_candidate_not_assumed_correction(self):
        editorial=deepcopy(self.ledger)
        editorial['decisions'][1].update(disposition='exclude',targetResourceIds=[],reason='Synthetic unsuitable route')
        editorial['output']['finalUniqueResources']=2
        imported=self.work.import_editorial(self.package,json.dumps(editorial).encode())
        ledger=EvidenceLedger(self.store);data=fixture_package();data['resources'].pop()
        before=ledger.import_package('restore','Test TSO',write_package(data,{'pdfs/guide.pdf':b'%PDF'}),scope='partial')
        after=ledger.import_package('restore','Test TSO',write_package(fixture_package(),{'pdfs/guide.pdf':b'%PDF'}),scope='partial')
        ledger.compare(before['id'],after['id'],reviewer='QA',lineage_note='Curator supplied later package; author of addition is not proved')
        groups=self.work.feedback_queue()['groups']
        restored=next(g for g in groups if g.get('possibleEditorialReversals'))
        self.assertEqual(restored['possibleEditorialReversals'],[imported['observationIds'][1]])
        self.assertTrue(restored['editorialReversalRequiresLineageReview'])
        self.assertEqual(self.work.manifest()['entries'],[])

    def test_event_evidence_versions_are_one_event_and_keep_conflicts(self):
        ledger=EvidenceLedger(self.store);data=fixture_package()
        before=ledger.import_package('versions','Test TSO',write_package(data,{'pdfs/guide.pdf':b'%PDF'}),scope='full')
        data['resources'][0]['phone']='555-9999'
        after=ledger.import_package('versions','Test TSO',write_package(data,{'pdfs/guide.pdf':b'%PDF'}),scope='full')
        comp=ledger.compare(before['id'],after['id'],reviewer='QA',lineage_note='Same source chain')
        self.work.collect_comparisons()
        args={'reviewer':'Synthetic curator','method':'phone','note':'Synthetic field confirmation','source':'Fixture call record'}
        ledger.attest(comp['id'],comp['events'][0]['eventId'],**args)
        self.work.collect_comparisons()
        ledger.attest(comp['id'],comp['events'][0]['eventId'],**{**args,'note':'Competing synthetic note'})
        group=next(g for g in self.work.feedback_queue()['groups'] if g['topic']=='phone')
        self.assertEqual(group['distinctEventCount'],1)
        self.assertEqual(len(group['observations']),3)
        self.assertIn('verificationAmbiguity',json.dumps(group))

    def test_question_transition_labels_do_not_invent_resolution_on_removal(self):
        from resource_research_agent.learning_activation import question_changes
        old={'id':'q','status':'resolved','resolution':'One answer'}
        e={'field':'openQuestions','before':[old],'after':[{**old,'status':'open'}]}
        self.assertEqual(question_changes(e)[0]['transition'],'reopened')
        e['after']=[{**old,'resolution':'Contradiction'}]
        self.assertEqual(question_changes(e)[0]['transition'],'answer-changed-review-for-conflict')
        e['after']=[]
        self.assertEqual(question_changes(e)[0]['transition'],'removed-not-proof-of-resolution')

    def test_positive_label_does_not_override_new_critical_error(self):
        for arm in ARMS:
            result,receipt=self.reply(arm);self.work.submit(self.trial,arm,json.dumps(result),receipt)
        a=self.assessment();a['conclusion']='promising';a['caseJudgments'][0]['candidate']['unsupportedPromise']=True
        self.work.assess(self.trial,a)
        with self.assertRaisesRegex(ImprovementError,'unsupported promises'):
            self.review()

    def test_counterevidence_is_excluded_from_new_trial_and_distillation_is_atomic(self):
        ids=[self.imported['observationIds'][2]]
        proposal=deepcopy(self.proposal);proposal['title']='Counterexample test'
        doc={'reviewer':'Synthetic editor','observationIds':ids,'counterevidenceIds':[self.imported['observationIds'][0]],
             'kind':'method','interpretation':'Counterexample is not independent test evidence','proposal':proposal}
        original=self.work._record
        with self.store.connect() as c:before=c.execute('SELECT count(*) FROM scout_learning_records').fetchone()[0]
        def fail(c,kind,document):
            value=original(c,kind,document)
            if kind=='distillation':raise RuntimeError('Synthetic transaction failure')
            return value
        with patch.object(self.work,'_record',side_effect=fail),self.assertRaises(RuntimeError):self.work.distill(doc)
        with self.store.connect() as c:self.assertEqual(before,c.execute('SELECT count(*) FROM scout_learning_records').fetchone()[0])
        lesson=self.work.distill(doc)['lessonId']
        with self.assertRaisesRegex(ImprovementError,'separate from lesson examples'):
            self.work.prepare_trial(lesson,self.spec)

    def test_operator_cli_can_display_feedback_and_record_a_nonactivating_review(self):
        import io
        from contextlib import redirect_stdout
        from resource_research_agent.cli import main
        path=Path(self.tmp.name)/'review.json'
        path.write_text(json.dumps({'reviewer':'Synthetic reviewer','decision':'defer','rationale':'Need an applicable result', 'trialIds':[],'supersedes':[]}))
        for args in [['learning','feedback'],['learning','manifest'],['learning','review',self.lesson,str(path)],['learning','inbox']]:
            stdout=io.StringIO()
            with redirect_stdout(stdout):code=main(['--database',str(self.store.path),*args])
            self.assertEqual(code,0)
            self.assertIsInstance(json.loads(stdout.getvalue()),dict)
        self.assertEqual(self.work.manifest()['entries'],[])
