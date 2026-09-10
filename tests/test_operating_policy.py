"""Synthetic policy transitions; these tests establish no research efficacy."""
from copy import deepcopy
import argparse,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from resource_research_agent.improvement_packages import ImprovementError,digest,write_package
from resource_research_agent.operating_policy import OperatingPolicyWorkbench,validate_policy
from resource_research_agent.policy_cli import add_policy_commands,run_policy_command
from resource_research_agent.storage import ResearchStore
from resource_research_agent.scout_maintenance import MaintenanceWorkflow
from tests.test_research_execution import settings,response
from tests.test_scout_improvement import fixture_package


class OperatingPolicyTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.store=ResearchStore(Path(self.temp.name)/'trial.sqlite3')
        self.flow=MaintenanceWorkflow(self.store);self.now=100.
        self.w=OperatingPolicyWorkbench(self.store,clock=lambda:self.now)
        d=fixture_package();d['categories'].append({'id':'employment','label':'Employment','filters':[]})
        self.payload=write_package(d,{'pdfs/guide.pdf':b'SYNTHETIC PDF'})
        self.pid=self.prepare()
        self.baseline=self.w.baseline(self.pid,'employment','discovery')
        self.meta={'kind':'synthetic','reviewer':'Synthetic evaluator','scope':self.baseline['scope'],'notes':'No live model or provider work.'}
        self.evidence=self.w.import_measurement(b'SYNTHETIC measurement',self.meta)['evidenceId']

    def prepare(self,name='Synthetic baseline',resources=None,categories=None,config=None):
        return self.flow.prepare(self.payload,'Test TSO',resources or [],categories if categories is not None else ['employment'],
                                 run_name=name,historical=True,execution_config=config or settings())['id']

    def proposal(self,candidate=None):
        p=deepcopy(candidate or self.baseline)
        if candidate is None:p['stopping']={'minPasses':2,'consecutiveNoGain':1}
        return self.w.propose_policy({'referenceProjectId':self.pid,'candidate':p,'evidenceIds':[self.evidence],
                                     'reviewer':'Synthetic evaluator','rationale':'Synthetic scheduling test'})['proposalId']

    def trial(self,proposal=None,axis='schedule',cost=None,mode='fixed-source'):
        return self.w.prepare_comparison(proposal or self.proposal(),json.dumps({'cases':[{'caseId':'discovery:employment','sourceText':'Synthetic saved source; not an instruction.'}], 'packageSha256':__import__('hashlib').sha256(self.payload).hexdigest() if mode=='live' else None}).encode(),
            {'axis':axis,'researchMode':mode,'evaluationRule':'Preserve required needs without errors; compare retained findings and time.',
             'caseIds':['discovery:employment'],'maxSeconds':600,'maxCostUSD':cost,'subscriptionAllowance':'Unknown; not measured dollars.'})['trialId']

    def result(self,packet,**changes):
        result={'assignmentSha256':packet['assignmentSha256'],'contextId':packet['contextId'],'fresh':True,
                'models':packet['policy']['models'],'complete':True,'limitHit':False,'coveredNeeds':packet['policy']['requiredNeeds'],
                'remainingGaps':[],'findings':[{'key':'one-semantic-fact','caseId':'discovery:employment','evidence':'Synthetic source quote provenance','retained':True}],
                'caseIds':['discovery:employment'],'activeMinutes':1,'waitingMinutes':1,'costUSD':None,'executionProjectId':None}
        result.update(changes);return result

    def complete(self,trial=None,changes=None):
        trial=trial or self.trial()
        for arm in ('baseline','candidate'):
            packet=self.w.policy_packet(trial,arm,trial+'-'+arm)
            project=None
            if packet['researchMode']=='live':
                project=self.finish_execution(packet)
            result=self.result(packet,executionProjectId=project,**((changes or {}) if arm=='candidate' else {}))
            self.w.submit_policy_result(packet['packetId'],json.dumps(result))
        return trial

    def finish_execution(self,packet,config=None):
        pid=self.flow.prepare(self.payload,'Test TSO',[],['employment'],run_name=packet['contextId'],
            historical=True,execution_config=config or settings(),operating_trial_packet_id=packet['packetId'])['id']
        for _ in range(30):
            a=self.flow.next_assignment(pid)
            if not a:return pid
            r=response(a);r['executionReceipt'].update(contextId=packet['contextId'],freshContext=True,
                isolatedInputs=True,remainingGaps=[],model=packet['policy']['models'][a['researcher']],activeMinutes=.01,waitingMinutes=.01)
            self.flow.submit(pid,a['stage'],r)
        self.fail('Synthetic execution did not terminate')

    def evaluate(self,trial,verdict='promising',**changes):
        a={'reviewer':'Synthetic independent evaluator','verdict':verdict,'rationale':'Synthetic state test, no real improvement claimed.','criticalErrors':[],'lostNeeds':[]}
        a.update(changes);return self.w.evaluate_policy(trial,a)

    def activate(self,proposal=None,axis='schedule'):
        trial=self.complete(self.trial(proposal,axis,mode='live'))
        evaluation=self.evaluate(trial)
        approval=self.w.approve_policy(evaluation['evaluationId'],'Synthetic authorized operator','Test only')['approvalId']
        old=self.w.policy_manifest()['manifestId']
        return old,self.w.activate_policy(approval,old)

    def state(self,pid):
        with self.store.connect() as c:return self.flow._load(c,pid)

    def pass_review(self,pid,keys,covered=None,**changes):
        a=self.flow.next_assignment(pid);self.assertTrue(a['stage'].startswith('pass:'))
        r=response(a);r['executionReceipt']['remainingGaps']=[]
        self.flow.submit(pid,a['stage'],r)
        doc={'reviewer':'Synthetic evaluator','resultSha256':digest(r),'retainedFindingKeys':keys,
             'coveredNeeds':self.baseline['requiredNeeds'] if covered is None else covered,'unresolvedNeeds':[],
             'limitHit':False,'reason':'Synthetic outcome accounting; no provider facts.'}
        doc.update(changes)
        self.flow.assess_pass(pid,self.flow.view(pid)['revision'],a['taskId'],a['stage'],doc)
        return a,doc

    def test_import_idempotent_provenance_and_no_activation(self):
        self.assertEqual(self.evidence,self.w.import_measurement(b'SYNTHETIC measurement',self.meta)['evidenceId'])
        report=self.w.policy_report();self.assertEqual(1,len(report['records']['operating-evidence']))
        self.assertEqual([],report['manifest']['entries'])

    def test_model_comparison_changes_only_models_and_seals_sources(self):
        candidate=deepcopy(self.baseline);candidate['models']['Codex']='Synthetic model v2'
        trial=self.trial(self.proposal(candidate),'models')
        a=self.w.policy_packet(trial,'baseline','a');b=self.w.policy_packet(trial,'candidate','b')
        self.assertEqual(a['sourceMaterial'],b['sourceMaterial'])
        self.assertNotEqual(a['policy']['models'],b['policy']['models'])
        self.assertEqual(a['policy']['passes'],b['policy']['passes'])
        with self.assertRaises(ImprovementError):self.trial(self.proposal(candidate),'schedule')

    def test_goals_cannot_be_smuggled_into_schedule_comparison(self):
        c=deepcopy(self.baseline);c['passes'][0]['direction']='A different goal'
        proposal=self.proposal(c)
        with self.assertRaises(ImprovementError):self.trial(proposal,'schedule')
        self.trial(proposal,'goals')

    def test_required_sparse_need_cannot_be_removed(self):
        c=deepcopy(self.baseline);c['requiredNeeds'].pop()
        with self.assertRaisesRegex(ImprovementError,'sparse'):self.proposal(c)
        c=deepcopy(self.baseline);c['passes']=c['passes'][:1]
        with self.assertRaises(ImprovementError):validate_policy(c)

    def test_fresh_context_no_reassignment_or_reuse(self):
        trial=self.trial();a=self.w.policy_packet(trial,'baseline','fresh-a')
        self.assertEqual(a,self.w.policy_packet(trial,'baseline','fresh-a'))
        with self.assertRaises(ImprovementError):self.w.policy_packet(trial,'candidate','fresh-a')
        with self.assertRaises(ImprovementError):self.w.policy_packet(trial,'baseline','replacement')
        bad=self.result(a,fresh=False)
        with self.assertRaises(ImprovementError):self.w.submit_policy_result(a['packetId'],json.dumps(bad))

    def test_malformed_deliveries_saved_and_accepted_results_immutable(self):
        a=self.w.policy_packet(self.trial(),'baseline','fresh-a')
        with self.assertRaises(json.JSONDecodeError):self.w.submit_policy_result(a['packetId'],'not JSON')
        with self.store.connect() as c:self.assertEqual(1,c.execute("SELECT count(*) FROM scout_learning_records WHERE kind='operating-delivery'").fetchone()[0])
        r=self.result(a);first=self.w.submit_policy_result(a['packetId'],json.dumps(r))
        self.assertEqual(first,self.w.submit_policy_result(a['packetId'],json.dumps(r)))
        r['activeMinutes']=3
        with self.assertRaisesRegex(ImprovementError,'immutable'):self.w.submit_policy_result(a['packetId'],json.dumps(r))

    def test_limits_incomplete_gaps_and_sparse_coverage_block_promising(self):
        # Use a separate trial ID for each fixture; accepted results are immutable.
        for i,changes in enumerate(({'complete':False},{'limitHit':True},{'remainingGaps':['Unexamined small need']},{'coveredNeeds':[]})):
            with self.subTest(changes=changes):
                candidate=deepcopy(self.baseline);candidate['stopping']={'minPasses':i+1,'consecutiveNoGain':1}
                trial=self.complete(self.trial(self.proposal(candidate)),changes)
                with self.assertRaises(ImprovementError):self.evaluate(trial)
                self.assertTrue(self.evaluate(trial,'inconclusive')['blockers'])

    def test_late_result_and_unknown_cost_not_evidence_of_coverage(self):
        trial=self.trial(cost=1)
        for arm in ('baseline','candidate'):
            p=self.w.policy_packet(trial,arm,arm);self.now+=601
            self.w.submit_policy_result(p['packetId'],json.dumps(self.result(p)))
        with self.assertRaises(ImprovementError):self.evaluate(trial)
        result=self.evaluate(trial,'inconclusive')
        self.assertTrue(any('cost cap' in b for b in result['blockers']))

    def test_duplicate_retained_keys_do_not_inflate_value(self):
        f={'key':'one-semantic-fact','caseId':'discovery:employment','evidence':'same fact from another page','retained':True}
        trial=self.complete(changes={'findings':[f,f,f]})
        self.assertEqual({'baseline':1,'candidate':1},self.evaluate(trial)['distinctRetainedFindings'])

    def test_errors_or_lost_needs_block_activation(self):
        trial=self.complete()
        with self.assertRaises(ImprovementError):self.evaluate(trial,criticalErrors=['Unsupported promise'])
        e=self.evaluate(trial,'worse',lostNeeds=['Sparse need omitted'])
        with self.assertRaises(ImprovementError):self.w.approve_policy(e['evaluationId'],'Reviewer','Not permitted')

    def test_review_required_atomic_stale_activation_and_rollback(self):
        trial=self.complete(self.trial(mode='live'));e=self.evaluate(trial)
        initial=self.w.policy_manifest()['manifestId']
        with self.assertRaises(ImprovementError):self.w.activate_policy(e['evaluationId'],initial)
        approval=self.w.approve_policy(e['evaluationId'],'Synthetic approver','Test only')['approvalId']
        with self.assertRaises(ImprovementError):self.w.activate_policy(approval,'wrong-head')
        active=self.w.activate_policy(approval,initial)
        with self.assertRaises(ImprovementError):self.w.activate_policy(approval,initial)
        rolled=self.w.rollback_policy(initial,active['manifestId'],'Synthetic approver','Test rollback')
        self.assertEqual([],rolled['entries']);self.assertEqual(active['manifestId'],rolled['parent'])

    def test_new_model_only_in_new_runs_old_run_remains_sealed(self):
        old=self.flow.next_assignment(self.pid)
        c=deepcopy(self.baseline);c['models']['Codex']='Synthetic v2';self.activate(self.proposal(c),'models')
        pid=self.prepare('After approval')
        new=self.flow.next_assignment(pid)
        self.assertEqual('Synthetic v2',new['configuredModel'])
        with self.assertRaisesRegex(ImprovementError,'model identity'):
            self.flow.submit(pid,new['stage'],response(new))
        self.assertEqual(old,self.flow.next_assignment(self.pid))
        self.assertIsNone(old['configuredModel'])

    def test_changed_guidance_blocks_new_policy_application(self):
        self.activate()
        from resource_research_agent.research_execution import playbook_for
        original=playbook_for('employment','Employment','Test County')
        with patch('resource_research_agent.research_execution.playbook_for',return_value=original):
            # An actual source snapshot change is detected even though policy is active.
            from dataclasses import replace
            changed=replace(original,scope=original.scope+('Synthetic new requirement',))
        with patch('resource_research_agent.research_execution.playbook_for',return_value=changed):
            with self.assertRaisesRegex(ImprovementError,'guidance changed'):self.prepare('Changed source')

    def test_stopping_deduplicates_value_preserves_synthesis_and_resume(self):
        self.activate();pid=self.prepare('Stop test')
        self.pass_review(pid,['same-finding']);self.pass_review(pid,['same-finding'])
        self.flow.stop_optional_passes(pid,self.flow.view(pid)['revision'],'discovery:employment','Synthetic editor','Duplicate-only tail; required needs examined.')
        self.flow=MaintenanceWorkflow(ResearchStore(self.store.path))
        a=self.flow.next_assignment(pid);self.assertEqual('primary',a['stage'])
        self.assertEqual(5,len(a['stoppingDecision']['basis']['skippedStages']))
        while a:
            self.flow.submit(pid,a['stage'],response(a));a=self.flow.next_assignment(pid)
        state=self.state(pid);task=state['tasks']['discovery:employment']
        self.assertIn('stoppingDecisionSha256',task['primaryFreeze'])
        self.assertEqual(2,len([s for s in task['results'] if s.startswith('pass:')]))

    def test_stopping_blocked_by_sparse_need_limit_or_new_value(self):
        self.activate()
        for name,covered,keys,extra in [('sparse',[],['same'],{}),('limit',None,['same'],{'limitHit':True}),('value',None,['new'],{})]:
            pid=self.prepare(name);self.pass_review(pid,['same'],covered)
            self.pass_review(pid,keys,covered,**extra)
            with self.assertRaises(ImprovementError):self.flow.stop_optional_passes(pid,self.flow.view(pid)['revision'],'discovery:employment','Evaluator','Test')

    def test_cannot_stop_dispatched_pass_or_mutate_assessment(self):
        self.activate();pid=self.prepare('Dispatched')
        a,doc=self.pass_review(pid,[]);self.pass_review(pid,[])
        self.flow.next_assignment(pid)
        with self.assertRaises(ImprovementError):self.flow.stop_optional_passes(pid,self.flow.view(pid)['revision'],a['taskId'],'Evaluator','Test')
        doc['reason']='Changed'
        with self.assertRaisesRegex(ImprovementError,'immutable'):self.flow.assess_pass(pid,self.flow.view(pid)['revision'],a['taskId'],a['stage'],doc)

    def test_overlapping_categories_count_one_outside_assignment(self):
        d=fixture_package();d['categories'].append({'id':'employment','label':'Employment','filters':[]})
        d['resources'][0]['categories'].append('employment');self.payload=write_package(d,{'pdfs/guide.pdf':b'SYNTHETIC PDF'})
        config=settings(rate=3)
        pid=self.prepare('Overlap',resources=['r1'],categories=[],config=config)
        from resource_research_agent.research_execution import execution_summary
        summary=execution_summary(self.state(pid))['outsideWorkload']
        self.assertEqual(1,summary['uniqueAssignments']);self.assertEqual(2,summary['categoryMemberships'])
        self.assertEqual({'random'},set(summary['assignments'][0]['reasons'].values()))

    def test_deliberate_and_targeted_checks_survive_zero_policy_sampling(self):
        self.activate();pid=self.prepare('Deliberate',config=settings(deliberate=['employment']))
        self.flow.request_challenge(pid,self.flow.view(pid)['revision'],'discovery:employment','Grok','Synthetic operator','Specific contradiction')
        from resource_research_agent.research_execution import execution_summary
        rows=execution_summary(self.state(pid))['outsideWorkload']['assignments']
        self.assertEqual(2,len(rows));self.assertEqual({'targeted','employment'},{k for r in rows for k in r['reasons']})
        self.assertIn('deliberate',[v for r in rows for v in r['reasons'].values()])

    def test_cli_manifest_report_and_capture_no_model_calls(self):
        parser=argparse.ArgumentParser();sub=parser.add_subparsers();add_policy_commands(sub)
        args=parser.parse_args(['policy','manifest'])
        self.assertEqual([],run_policy_command(self.store,args)['entries'])
        evidence=self.w.capture_execution(self.pid,'employment','discovery','Synthetic operator')
        self.assertIn('evidenceId',evidence)
        self.assertEqual(2,len(self.w.policy_report()['records']['operating-evidence']))

    def test_fixed_source_screen_cannot_approve_policy(self):
        e=self.evaluate(self.complete())
        with self.assertRaisesRegex(ImprovementError,'fixed-source'):
            self.w.approve_policy(e['evaluationId'],'Reviewer','Screen only')
        self.assertEqual([],self.w.policy_manifest()['entries'])

    def test_experiment_source_scope_and_incomplete_execution_are_guarded(self):
        trial=self.trial(mode='live')
        p=self.w.policy_packet(trial,'baseline','incomplete-baseline')
        with self.assertRaisesRegex(ImprovementError,'sealed source'):
            self.w.trial_policy_snapshot(p['packetId'],'wrong hash','Test TSO',['discovery:employment'],{})
        with self.assertRaisesRegex(ImprovementError,'scope'):
            self.w.trial_policy_snapshot(p['packetId'],__import__('hashlib').sha256(self.payload).hexdigest(),
                'Test TSO',['discovery:employment'],{'discovery:employment':{('housing','discovery')}})
        pid=self.flow.prepare(self.payload,'Test TSO',[],['employment'],run_name='Incomplete',historical=True,
            execution_config=settings(),operating_trial_packet_id=p['packetId'])['id']
        self.w.submit_policy_result(p['packetId'],json.dumps(self.result(p,executionProjectId=pid)))
        candidate=self.w.policy_packet(trial,'candidate','complete-candidate')
        pid=self.finish_execution(candidate)
        self.w.submit_policy_result(candidate['packetId'],json.dumps(self.result(candidate,executionProjectId=pid)))
        with self.assertRaisesRegex(ImprovementError,'execution incomplete'):self.evaluate(trial)
        self.assertEqual([],self.w.policy_manifest()['entries'])

    def test_synthetic_approval_cannot_govern_live_research(self):
        self.activate()
        with self.assertRaisesRegex(ImprovementError,'historical comparisons'):
            self.flow.prepare(self.payload,'Test TSO',[],['employment'],run_name='Operational',
                              historical=False,execution_config=settings())

    def test_activation_failure_rolls_back_manifest_record_and_head(self):
        e=self.evaluate(self.complete(self.trial(mode='live')))
        approval=self.w.approve_policy(e['evaluationId'],'Synthetic approver','Test only')['approvalId']
        original=self.w.policy_manifest()
        record=self.w._record
        def fail_after_record(c,kind,document):
            ident=record(c,kind,document)
            if kind=='operating-manifest':raise RuntimeError('Synthetic disk failure')
            return ident
        with patch.object(self.w,'_record',side_effect=fail_after_record):
            with self.assertRaises(RuntimeError):self.w.activate_policy(approval,original['manifestId'])
        self.assertEqual(original,self.w.policy_manifest())
        with self.store.connect() as c:
            self.assertEqual(1,c.execute("SELECT count(*) FROM scout_learning_records WHERE kind='operating-manifest'").fetchone()[0])

    def test_runtime_rejects_conflicting_profiles_for_overlap(self):
        from resource_research_agent.operating_runtime import apply_policies
        m=deepcopy(self.state(self.pid)['execution']['manifest'])
        m['playbooks']['other']=deepcopy(m['playbooks']['employment'])
        m['taskPlans']={'recheck:r1':{'categoryIds':['employment','other'],'passes':[],'comparisonReasons':{}}}
        entries=[]
        for category,model in [('employment','Model A'),('other','Model B')]:
            p=deepcopy(self.baseline);p['scope'].update(category=category,kind='recheck');p['passes']=[];p['models']['Codex']=model
            entries.append({'proposalId':category,'policy':p,'guidanceSha256':digest({'playbook':m['playbooks'][category],'learnedGuidance':m.get('learnedGuidance')})})
        with self.assertRaisesRegex(ImprovementError,'Conflicting model'):
            apply_policies(m,{'manifestId':'synthetic','policies':entries})

    def test_policy_sampler_keeps_baseline_selection(self):
        from resource_research_agent.operating_runtime import apply_policies
        from resource_research_agent.operating_policy import default_policy
        pid=self.prepare('Sample baseline',categories=['employment',fixture_package()['categories'][0]['id']],config=settings(rate=1))
        m=deepcopy(self.state(pid)['execution']['manifest']);before=deepcopy(m['taskPlans'])
        entries=[{'proposalId':cid,'policy':default_policy(m,cid,'discovery'),
                  'guidanceSha256':digest({'playbook':m['playbooks'][cid],'learnedGuidance':m.get('learnedGuidance')})} for cid in m['playbooks']]
        apply_policies(m,{'manifestId':'synthetic','policies':entries})
        self.assertEqual({tid:set(p['comparisonReasons']) for tid,p in before.items()},
                         {tid:set(p['comparisonReasons']) for tid,p in m['taskPlans'].items()})

    def test_unused_model_change_cannot_be_approved(self):
        candidate=deepcopy(self.baseline);candidate['models']['Claude']='Synthetic new Claude'
        trial=self.complete(self.trial(self.proposal(candidate),axis='models',mode='live'))
        with self.assertRaisesRegex(ImprovementError,'not exercised'):self.evaluate(trial)

    def test_live_arms_cannot_change_execution_settings(self):
        trial=self.trial(mode='live')
        for arm in ('baseline','candidate'):
            p=self.w.policy_packet(trial,arm,arm)
            config=settings()
            if arm=='candidate':config['sampling']['seed']='different seed'
            pid=self.finish_execution(p,config)
            self.w.submit_policy_result(p['packetId'],json.dumps(self.result(p,executionProjectId=pid)))
        with self.assertRaisesRegex(ImprovementError,'settings'):self.evaluate(trial)

    def test_experimental_arms_do_not_receive_each_others_prior_results(self):
        trial=self.trial(mode='live')
        baseline=self.w.policy_packet(trial,'baseline','isolated-baseline')
        baseline_pid=self.finish_execution(baseline)
        candidate=self.w.policy_packet(trial,'candidate','isolated-candidate')
        pid=self.flow.prepare(self.payload,'Test TSO',[],['employment'],run_name='Isolated candidate',historical=True,
            execution_config=settings(),operating_trial_packet_id=candidate['packetId'])['id']
        a=self.flow.next_assignment(pid)
        self.assertEqual([],a['priorChecks'])
        original=next(iter(self.state(baseline_pid)['tasks']['discovery:employment']['assignments'].values()))
        self.assertEqual(original['knownIdentities'],a['knownIdentities'])
        self.assertFalse(any('priorRunId' in r for r in a['knownIdentities']))
        ordinary=self.prepare('Ordinary after experiment')
        self.assertEqual([],self.flow.next_assignment(ordinary)['priorChecks'])
