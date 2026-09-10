"""Isolated synthetic scheduler acceptance plus attributed saved pilot intake.

Run from the repository root. Uses only a temporary database; no model calls.
"""
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from tests.test_operating_policy import OperatingPolicyTests
from tests.test_research_execution import settings,response
from resource_research_agent.improvement_packages import digest
from resource_research_agent.research_execution import execution_summary


def run():
    fixture=OperatingPolicyTests();fixture.setUp()
    try:
        w,flow=fixture.w,fixture.flow
        source=ROOT/'experiments/mesa-maintenance-editor-20260909/tool-measurements.json'
        raw=source.read_bytes();measurements=json.loads(raw)
        scoped={'sourcePath':str(source.relative_to(ROOT)),'sourceSha256':hashlib.sha256(raw).hexdigest(),
                'calls':[c for c in measurements['calls'] if c['group']=='employment'],
                'note':'One employment tool batch from a manual pilot; not a complete category benchmark or independent model experiment.'}
        manual=w.import_measurement(json.dumps(scoped,sort_keys=True).encode(),{
            'kind':'manual-pilot','reviewer':'Astra: attributed saved pilot intake',
            'scope':{'office':'Mesa','category':'employment','kind':'recheck'},'notes':scoped['note']})
        initial=w.policy_manifest();trial=fixture.trial(mode='live');arms={}
        for arm in ('baseline','candidate'):
            packet=w.policy_packet(trial,arm,'synthetic-acceptance-'+arm)
            pid=flow.prepare(fixture.payload,'Test TSO',[],['employment'],run_name=packet['contextId'],
                historical=True,execution_config=settings(),operating_trial_packet_id=packet['packetId'])['id']
            completed=0
            for _ in range(30):
                assignment=flow.next_assignment(pid)
                if not assignment:break
                result=response(assignment)
                result['executionReceipt'].update(contextId=packet['contextId'],freshContext=True,
                    isolatedInputs=True,remainingGaps=[],activeMinutes=.01,waitingMinutes=.01)
                flow.submit(pid,assignment['stage'],result)
                if assignment['stage'].startswith('pass:'):
                    completed+=1
                    flow.assess_pass(pid,flow.view(pid)['revision'],assignment['taskId'],assignment['stage'],{
                        'reviewer':'Synthetic acceptance evaluator','resultSha256':digest(result),
                        'retainedFindingKeys':['synthetic-same-fact'],'coveredNeeds':packet['policy']['requiredNeeds'],
                        'unresolvedNeeds':[],'limitHit':False,'reason':'Synthetic repeated finding and complete declared need coverage.'})
                    if arm=='candidate' and completed==2:
                        flow.stop_optional_passes(pid,flow.view(pid)['revision'],assignment['taskId'],
                            'Synthetic evaluator','Synthetic no-new-value test; not a real research judgment.')
            else:raise AssertionError('Synthetic run did not terminate')
            submitted=w.submit_policy_result(packet['packetId'],json.dumps(fixture.result(packet,executionProjectId=pid)))
            summary=execution_summary(fixture.state(pid))
            arms[arm]={'projectId':pid,'completedPasses':completed,'resultId':submitted['resultId'],
                       'executionEvidence':submitted['executionEvidence'],'workload':summary}
        evaluation=fixture.evaluate(trial)
        approval=w.approve_policy(evaluation['evaluationId'],'Synthetic test operator','Historical fixture only')['approvalId']
        active=w.activate_policy(approval,initial['manifestId'])
        rolled=w.rollback_policy(initial['manifestId'],active['manifestId'],'Synthetic test operator','Acceptance cleanup')
        assert rolled['entries']==[]
        report={'kind':'synthetic-acceptance','outsideModelCalls':0,'productionPoliciesActivated':0,
                'manualEvidence':{**manual,**scoped},'trialId':trial,'arms':arms,'evaluation':evaluation,
                'historicalOnlyApproval':approval,'isolatedManifestAfterRollback':rolled,
                'conclusion':'Actual scheduler and immutable policy transitions exercised with synthetic responses. Seven versus two passes is fixture behavior, not a measured real research speedup or proof of equal quality. Saved Mesa measurements triggered no policy change.'}
        (Path(__file__).parent/'acceptance.json').write_text(json.dumps(report,indent=2)+'\n')
        print('Acceptance saved: baseline 7 passes; candidate 2 plus 5 intentional omissions; zero outside calls; temporary policy rolled back.')
    finally:fixture.doCleanups()


if __name__=='__main__':run()
