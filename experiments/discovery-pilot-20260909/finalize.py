"""Apply the actual final editorial choices and export the reviewable pilot."""
import json
from pathlib import Path
from resource_research_agent.frontier_editor import FrontierEditorWorkflow
from resource_research_agent.storage import ResearchStore
from resource_research_agent.performance import timing_session
P=Path(__file__).parent;O=Path('output/discovery-pilot-20260909');D=O/'delivery';D.mkdir(exist_ok=True)
load=lambda n:json.loads((P/n).read_text())
def save(n,x): (P/n).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
f=FrontierEditorWorkflow(ResearchStore(O/'pilot.sqlite3'));pid=load('project.json')['id'];a=f.packet(pid,'final')
decisions=[]
for r in a['package']['resources']:
 reserve='uteta.org' in r.get('website','')
 reason=('Reserve this researched option for a patron specifically seeking electrical training who can meet its travel and entry requirements. Statewide assignments, a license, school prerequisites, uncertain initial costs and an unconfirmed start delay make it a poor default referral for this small collection. Paid training itself is useful; the multi-year duration is not the reason for reserving it. Preserve the facts and question in the evidence package.' if reserve else
 'Retain as a distinct practical route. '+{
 'welfare-employment-sugarhouse':'Personal adviser help, walk-ins and remote support offer a useful way to start without requiring Church membership.',
 'welfare-employment-peopleready':'A local staffed application route to actual paid assignments complements job-search advice; no shift is promised.',
 'scout-lead:disc-usor-vr-20260909':'Disability-specific eligibility and support differ from ordinary DWS help. Preserve restrictions while keeping the named route useful for eligible patrons.',
 'scout-lead:disc-uca-workforce-20260909':'Free adult job help and education support have direct intake, broad income eligibility and useful local reach.'
 }.get(r['id'],'Public job tools and a training-application route remain useful. Use the statewide service title and keep the local-office question visible instead of printing an unconfirmed address.'))
 decisions.append({'resourceId':r['id'],'disposition':'reserve' if reserve else 'retain',
  'targetResourceIds':[] if reserve else [r['id']],'reason':reason,
  'evidence':[r.get('website',''), 'Reconciled official-source research and its documented uncertainty.'],
  'fields':{},'questions':[]})
reply={'assignmentSha256':a['assignmentSha256'],'decisions':decisions};save('final-response.json',reply)
with timing_session(P/'workflow-timings.jsonl'):
 f.submit(pid,'final',json.dumps(reply,ensure_ascii=False),load('editor-receipt.json'))
 exported=f.export(pid)
(D/exported['filename']).write_bytes(exported['html']);(D/'resource-package.zip').write_bytes(exported['package'])
save('export-manifest.json',exported['manifest']);(D/'manifest.json').write_text(json.dumps(exported['manifest'],indent=2)+'\n')
# Preserve all six researched entries as a separate evidence snapshot, not as
# the default collection or a tombstone-driven office deletion package.
from resource_research_agent.improvement_packages import write_package
(D/'all-researched-candidates.zip').write_bytes(write_package(a['package'],{}))
print('Final pilot exported:',exported['filename'],exported['manifest']['resources'],'retained, 1 reserved; no human approvals.')
