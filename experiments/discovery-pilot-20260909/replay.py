"""Validate/replay preserved evidence only. No model calls or active lessons."""
import hashlib
import json
from pathlib import Path
import tempfile
from resource_research_agent.storage import ResearchStore
from resource_research_agent.improvement_packages import digest,read_package
from resource_research_agent.frontier_editor import FrontierEditorWorkflow
from resource_research_agent.research_execution import validate_execution,execution_stages,validate_receipt
from resource_research_agent.learning_workbench import LearningWorkbench
P=Path(__file__).parent;OLD=P.parent/'learning-pilot-20260909'
load=lambda n:json.loads((P/n).read_text())
for n,h in load('artifact-hashes.json').items():assert hashlib.sha256((P/n).read_bytes()).hexdigest()==h,n
state=load('research-state.json');validate_execution(state)
count=0
for task in state['tasks'].values():
 for stage,_ in execution_stages(state,task):
  a=task['assignments'][stage];r=task['results'][stage]
  assert r['assignmentSha256']==a['assignmentSha256'];validate_receipt(r,a);count+=1
assert count==19
for stage in ('early','final'):
 a=load(stage+'-packet.json');assert digest({k:v for k,v in a.items() if k!='assignmentSha256'})==a['assignmentSha256']
with tempfile.TemporaryDirectory() as tmp:
 store=ResearchStore(Path(tmp)/'replay.sqlite3');f=FrontierEditorWorkflow(store)
 final=read_package((P/'final-resource-package.zip').read_bytes())['data']
 replay=f._apply(load('editor-project-snapshot.json'),load('final-packet.json'),load('final-response.json'),final['packageCreatedAt'])
 assert replay==final
 assert len(final['resources'])==5 and len(final['scoutDiscoveryCoverage']['assignments'])==19
 assert not final['deletions'] and not final['deletionRequests']
 assert sum(len(r.get('openQuestions',[])) for r in final['resources'])==1
 w=LearningWorkbench(store)
 w.import_editorial((OLD/'source-package.zip').read_bytes(),(OLD/'editorial-decisions.json').read_bytes())
 lesson=w.propose(load('employment-lesson-proposal.json'));trial=w.prepare_trial(lesson['lessonId'],load('employment-trial-specification.json'))
 assert trial==load('employment-trial-receipt.json')
 for arm in ('baseline','candidate'):
  receipt=load('employment-'+arm+'-receipt.json')
  assert w.packet(trial['trialId'],arm,receipt['contextId'],fresh=True)==load('employment-'+arm+'-packet.json')
  w.submit(trial['trialId'],arm,(P/('employment-'+arm+'-response.json')).read_text(),receipt)
 report=w.assess(trial['trialId'],load('employment-assessment.json'))
 assert report['quality']==load('employment-report.json')['quality'] and not report['active']
print('19 sealed research results, exact final editing and paired learning evidence replayed; no model calls or active lessons.')
