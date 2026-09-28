"""Read-only post-run audit of real comparison inputs and web transport counts."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from resource_research_agent.storage import ResearchStore
from resource_research_agent.scout_maintenance import MaintenanceWorkflow
from resource_research_agent.operating_policy import OperatingPolicyWorkbench
from resource_research_agent.research_execution import execution_stages
P=Path(__file__).resolve().parent;OUT=ROOT/'output/operating-real-20260909'


def run():
    store=ResearchStore(OUT/'comparison.sqlite3');flow=MaintenanceWorkflow(store);arms={}
    expected=json.loads((P/'prepared.json').read_text())['initialManifest']
    for arm in ('baseline','candidate'):
        folder=OUT/arm;project=json.loads((folder/'project.json').read_text())
        with store.connect() as c:state=flow._load(c,project['projectId'])
        records=[]
        for path in sorted(folder.glob('web-*.json')):
            doc=json.loads(path.read_text());args=doc.get('args',doc.get('arguments'))
            if args is None:raise AssertionError('Missing exact web arguments')
            queries=len(args.get('search_query',[]));opens=len(args.get('open',[]))+len(args.get('click',[]))
            assert queries==doc.get('queries',doc.get('queryCount')),path.name
            assert opens==doc.get('opens',doc.get('openCount')),path.name
            records.append({'file':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                            'queries':queries,'pageOpens':opens,'fileTimestampUnix':path.stat().st_mtime,
                            'toolSeconds':doc.get('elapsedSeconds',doc.get('elapsedToolSeconds'))})
        remaining=[];assigned=[];result_hashes={};minutes={'activeMinutes':0.,'waitingMinutes':0.}
        for tid,task in state['tasks'].items():
            for stage,researcher in execution_stages(state,task):
                if stage not in task['results']:remaining.append(stage);continue
                a=task['assignments'][stage];r=task['results'][stage]
                assert a.get('priorChecks',[])==[],(arm,stage,'Cross-run research exposed')
                assert r['executionReceipt']['contextId']==project['contextId']
                assert r['executionReceipt']['model']=='gpt-6-astra'
                assigned.append(stage)
                from resource_research_agent.improvement_packages import digest
                result_hashes[stage]=digest(r)
                for key in minutes:minutes[key]+=r['executionReceipt'][key]
        per_pass=[]
        for tid,task in state['tasks'].items():
            for stage in task['results']:
                if not stage.startswith('pass:'):continue
                stem=stage.replace(':','--')
                start=(folder/(stem+'-assignment.json')).stat().st_mtime
                deliveries=[f for f in folder.glob(stem+'-*-delivery.json') if json.loads(f.read_text())==task['results'][stage]]
                assert len(deliveries)==1
                end=deliveries[0].stat().st_mtime
                calls=[r for r in records if start<=r['fileTimestampUnix']<=end]
                totals={'stage':stage,'webCalls':len(calls),'queries':sum(r['queries'] for r in calls),'pageOpens':sum(r['pageOpens'] for r in calls)}
                assert totals['webCalls']<=3 and totals['queries']<=2 and totals['pageOpens']<=4
                per_pass.append(totals)
        arms[arm]={'perPassUsage':per_pass,'projectId':project['projectId'],'manifestSha256':state['execution']['manifestSha256'],
                   'historical':state['historical'],'contextId':project['contextId'],'completedStages':assigned,
                   'remainingStages':remaining,'resultHashes':result_hashes,'originalReceiptMinutes':minutes,
                   'webCalls':len(records),'queries':sum(r['queries'] for r in records),
                   'pageOpens':sum(r['pageOpens'] for r in records),'webToolSeconds':sum(r['toolSeconds'] for r in records),
                   'transportRecords':records,'settings':state['execution']['manifest']['settings']}
        arms[arm]['withinTotalSourceAllowance']=arms[arm]['webCalls']<=16 and arms[arm]['queries']<=8 and arms[arm]['pageOpens']<=16
    assert arms['baseline']['settings']==arms['candidate']['settings']
    assert arms['baseline']['contextId']!=arms['candidate']['contextId']
    manifest=OperatingPolicyWorkbench(store).policy_manifest();assert manifest==expected
    report={'arms':arms,'activeManifest':manifest,'productionActivation':False,
            'note':'Raw web logs remain in local output and are hashed here. Counts are explicit tool requests, not all pages exposed in search results. Receipt minutes are original attributed estimates, not measured model compute time.'}
    (P/'execution-audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({a:{k:d[k] for k in ['completedStages','remainingStages','webCalls','queries','pageOpens','withinTotalSourceAllowance']} for a,d in arms.items()},indent=2))
    return report

if __name__=='__main__':run()
