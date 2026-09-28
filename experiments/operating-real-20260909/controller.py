"""Transport-neutral operator bridge for the prepared real comparison.

Each respondent uses only its own arm. Does not call models or activate policy.
"""
import argparse,hashlib,json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from resource_research_agent.storage import ResearchStore
from resource_research_agent.scout_maintenance import MaintenanceWorkflow
from resource_research_agent.operating_policy import OperatingPolicyWorkbench
from resource_research_agent.research_execution import execution_summary
P=Path(__file__).resolve().parent;OUT=ROOT/'output/operating-real-20260909'


def save(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')


def command(action,arm,response_path=None):
    work=OUT/arm;work.mkdir(parents=True,exist_ok=True)
    store=ResearchStore(OUT/'comparison.sqlite3');flow=MaintenanceWorkflow(store);w=OperatingPolicyWorkbench(store)
    marker=work/'project.json'
    if action=='start':
        if marker.exists():return json.loads(marker.read_text())
        packet=w.policy_packet(json.loads((P/'prepared.json').read_text())['trialId'],arm,'astra-clothing-20260909-'+arm)
        save(work/'policy-packet.json',packet)
        project=flow.prepare((P/'source-package.zip').read_bytes(),'Mesa',[],['clothing'],
            run_name='Real Clothing comparison '+arm,execution_config=json.loads((P/'execution-configuration.json').read_text()),
            operating_trial_packet_id=packet['packetId'])
        doc={'projectId':project['id'],'packetId':packet['packetId'],'contextId':packet['contextId'],
             'startedAtUnix':packet['dispatchedAt'],'deadlineUnix':packet['dispatchedAt']+1800,
             'arm':arm,'historical':False,'model':'gpt-6-astra'}
        save(marker,doc);return doc
    doc=json.loads(marker.read_text());pid=doc['projectId']
    if action=='next':
        if time.time()>doc['deadlineUnix']:raise RuntimeError('Arm time allowance exhausted; preserve partial work and stop.')
        assignment=flow.next_assignment(pid)
        if not assignment:
            return {'complete':True,'projectId':pid,'statusPath':str(work/'status.json')}
        name=assignment['stage'].replace(':','--')+'-assignment.json';path=work/name
        if path.exists() and json.loads(path.read_text())!=assignment:raise RuntimeError('Sealed assignment changed')
        save(path,assignment)
        return {'stage':assignment['stage'],'assignmentPath':str(path),'contextId':doc['contextId'],
                'deadlineUnix':doc['deadlineUnix'],'commonInstructions':str(P/'common-research-instructions.json')}
    if action=='submit':
        path=Path(response_path).resolve()
        if work.resolve() not in path.parents:raise RuntimeError('Read only this arm response files')
        raw=path.read_bytes();result=json.loads(raw)
        assignment=flow.next_assignment(pid)
        if not assignment:raise RuntimeError('No pending assignment')
        stage=assignment['stage'];delivery=work/(stage.replace(':','--')+'-'+hashlib.sha256(raw).hexdigest()[:12]+'-delivery.json')
        if not delivery.exists():delivery.write_bytes(raw)
        status=flow.submit(pid,stage,result);save(work/'status.json',status)
        return {'accepted':True,'stage':stage,'projectId':pid,'revision':status['revision']}
    if action=='status':
        with store.connect() as c:state=flow._load(c,pid)
        summary=execution_summary(state);save(work/'execution-summary.json',summary)
        completed={tid:list(task['results']) for tid,task in state['tasks'].items()}
        return {'projectId':pid,'completedStages':completed,'summaryPath':str(work/'execution-summary.json')}
    raise ValueError(action)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['start','next','submit','status']);p.add_argument('arm',choices=['baseline','candidate']);p.add_argument('response',nargs='?')
    a=p.parse_args();print(json.dumps(command(a.action,a.arm,a.response),indent=2))
