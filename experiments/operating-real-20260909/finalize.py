"""Preserve completed real responses and the coordinator's evaluation. No activation."""
import hashlib,json,shutil,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from resource_research_agent.storage import ResearchStore
from resource_research_agent.operating_policy import OperatingPolicyWorkbench
from resource_research_agent.scout_maintenance import MaintenanceWorkflow
P=Path(__file__).resolve().parent;OUT=ROOT/'output/operating-real-20260909'


def save(path,value):
    text=json.dumps(value,ensure_ascii=False,indent=2)+'\n'
    if path.exists() and path.read_text()!=text:raise RuntimeError('Refuse to change preserved '+str(path))
    path.write_text(text)


def run():
    store=ResearchStore(OUT/'comparison.sqlite3');w=OperatingPolicyWorkbench(store);flow=MaintenanceWorkflow(store)
    audit=json.loads((P/'execution-audit.json').read_text());review=json.loads((P/'quality-review.json').read_text())
    prepared=json.loads((P/'prepared.json').read_text());results={};summary={}
    for arm in ('baseline','candidate'):
        src=OUT/arm;dest=P/arm;dest.mkdir(exist_ok=True)
        project=json.loads((src/'project.json').read_text());packet=json.loads((src/'policy-packet.json').read_text())
        outcome=json.loads((src/'outcome.json').read_text());measurement=json.loads((src/'transport-measurements.json').read_text())
        aa=audit['arms'][arm];assert not aa['remainingStages'];assert aa['withinTotalSourceAllowance']
        with store.connect() as c:state=flow._load(c,project['projectId'])
        task=state['tasks']['discovery:clothing']
        for stage,response in task['results'].items():
            save(dest/(stage.replace(':','--')+'-result.json'),response)
            save(dest/(stage.replace(':','--')+'-assignment.json'),task['assignments'][stage])
        for name in ('outcome.json','transport-measurements.json','policy-packet.json','project.json'):
            target=dest/name
            if target.exists() and target.read_bytes()!=(src/name).read_bytes():raise RuntimeError('Archive changed')
            shutil.copyfile(src/name,target)
        # Keep the actual rejected response and exact accepted replacement.
        if arm=='baseline':
            for name in ('response-05-primary.json','response-05-primary-contract-corrected.json'):
                shutil.copyfile(src/name,dest/name)
        findings=[{'key':unit['key'],'caseId':'discovery:clothing','evidence':unit['finding']+' Sources: '+'; '.join(unit['sources']),'retained':True}
                  for unit in review['commonRetainedUnits']]
        raw_minutes=aa['originalReceiptMinutes']
        active=outcome.get('activeMinutes',outcome.get('estimatedActiveMinutes'))
        waiting=outcome.get('waitingMinutes',outcome.get('estimatedWaitingMinutes'))
        result={'assignmentSha256':packet['assignmentSha256'],'contextId':project['contextId'],'fresh':True,
            'models':packet['policy']['models'],'complete':True,'limitHit':bool(outcome['limitHit']),
            'coveredNeeds':outcome['coveredNeeds'],'remainingGaps':outcome['remainingGaps'],
            'findings':findings,'caseIds':packet['caseIds'],
            # Preserve original estimates and corrected timing separately. The workbench
            # summary conservatively includes at least the accepted stage estimates.
            'activeMinutes':max(active,raw_minutes['activeMinutes']),
            'waitingMinutes':max(waiting,raw_minutes['waitingMinutes']),
            'costUSD':None,'executionProjectId':project['projectId']}
        save(dest/'comparison-result.json',result)
        accepted=w.submit_policy_result(packet['packetId'],json.dumps(result,ensure_ascii=False))
        save(dest/'accepted-comparison-result.json',accepted);results[arm]=accepted['resultId']
        completion=next(src.glob('reconcile-*-delivery.json')).stat().st_mtime
        total=measurement.get('elapsedSeconds',measurement.get('elapsedMinutesIncludingAccounting',0)*60)
        summary[arm]={'completedStages':len(task['results']),'completedPasses':sum(s.startswith('pass:') for s in task['results']),
            'writtenLeads':len(task['results']['reconcile']['items']),'matchedUsefulUnits':len(findings),
            'webCalls':aa['webCalls'],'searchQueries':aa['queries'],'pageOpens':aa['pageOpens'],
            'webToolSeconds':aa['webToolSeconds'],'elapsedSecondsThroughFinalDelivery':completion-project['startedAtUnix'],
            'elapsedSecondsIncludingRespondentAccounting':total,'incrementalCostUSD':None,
            'timingNote':'Measured controller dispatch-to-final-delivery and respondent accounting timestamps. Normalized policy-result effort preserves the larger original estimate where corrected estimates were lower; do not use it to rank speed.'}
    assessment={'reviewer':'Astra coordinator, post-freeze source verification; not blinded',
        'verdict':'inconclusive','rationale':review['conclusion']+' '+review['recommendedNextStep'],
        'criticalErrors':review['criticalErrorsInVerifiedDraftClaims'],'lostNeeds':review['lostSelectedPrograms']}
    evaluation=w.evaluate_policy(prepared['trialId'],assessment)
    save(P/'assessment.json',assessment);save(P/'evaluation.json',evaluation)
    assert w.policy_manifest()==prepared['initialManifest']
    save(P/'comparison-summary.json',{'results':results,'evaluationId':evaluation['evaluationId'],'arms':summary,
        'verdict':'inconclusive','activeManifest':w.policy_manifest(),'productionActivation':False,
        'findingsProvenance':'Coordinator normalized only the ten matched program/issue groups in the final drafts after checking primary sources; original agent finding lists remain intact.'})
    print(json.dumps({'verdict':'inconclusive','arms':summary,'policyChanged':False},indent=2))


if __name__=='__main__':run()
