#!/usr/bin/env python3
"""Build an explicitly synthetic, reproducible evidence-ledger demonstration."""
import argparse
import html
import json
import hashlib
from copy import deepcopy
from pathlib import Path
from resource_research_agent.storage import ResearchStore
from resource_research_agent.learning_evidence import EvidenceLedger
from resource_research_agent.improvement_packages import write_package
from resource_research_agent.scout_maintenance import MaintenanceWorkflow
from tests.test_scout_improvement import fixture_package
from tests.test_scout_maintenance import result_for

parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('output',type=Path);args=parser.parse_args()
p=args.output;p.mkdir(parents=True,exist_ok=True)
store=ResearchStore(p/'evidence.sqlite3');ledger=EvidenceLedger(store)
data=fixture_package();assets={'pdfs/guide.pdf':b'%PDF-1.4 synthetic evidence pilot'}
def imp(value,scope='full'):
 return ledger.import_package('synthetic-evidence-pilot','Test TSO',write_package(value,assets),scope=scope,historical=True)
def compare(before,after,**kwargs):
 return ledger.compare(before['id'],after['id'],reviewer='Synthetic operator',lineage_note='Explicit synthetic predecessor',**kwargs)
base=imp(data);changed=deepcopy(data);changed['resources'][0]['name']='Example organization · Food pantry';later=imp(changed)
cases=[]
def case(title,comparison,explanation):
 report=ledger.report(comparison['id']);cases.append({'title':title,'explanation':explanation,'report':report})
case('1. A title changed in a later package',compare(base,later),'Scout records the exact old and new title. With no proposal link, it does not assume who changed it, why, or whether any service was verified.')
artifact=p/'synthetic-review.html';artifact.write_text('<h1>Synthetic proposal</h1><p>Example organization · Food pantry</p>')
manual=ledger.record_manual_proposal('synthetic-evidence-pilot',base['id'],resource_id='r1',fields={'name':changed['resources'][0]['name']},artifact={'path':str(artifact.resolve()),'sha256':hashlib.sha256(artifact.read_bytes()).hexdigest(),'deliveredAt':'2026-09-06T12:00:00Z'},configuration={'policy':'synthetic-example-v1','researcher':'Synthetic QA'})
case('2. The package uses Scout’s delivered title',compare(base,later,captures=[manual['id']]),'The matching field and baseline support adoption of a delivered proposal. This says nothing about a provider call or the resource’s eligibility and access details.')
flow=MaintenanceWorkflow(store)
pid=flow.prepare(write_package(data,assets),'Test TSO',['r1'],[],run_name='Synthetic evidence demo',historical=True)['id']
while a:=flow.next_assignment(pid):
 r=result_for(a,'changed')
 if not a['stage'].startswith('audit:'):
  r['items'][0]['fields']={'name':'Example organization · Food pantry'};r['items'][0]['questions']=['Synthetic unresolved access question.']
 flow.submit(pid,a['stage'],r)
if not flow.view(pid)['items'][0]['saved']:
 flow.connect_latest(pid,flow.view(pid)['revision'],write_package(data,assets),'Test TSO')
 flow.review(pid,flow.view(pid)['revision'],'recheck:r1','r1','accept',{'name':'proposed'},'Synthetic curator','Title approved; access question remains unresolved.')
 export=flow.prepare_export(pid,flow.view(pid)['revision'])
 flow.acknowledge_export(pid,flow.view(pid)['revision'],export['exportId'],export['manifest']['packageSha256'])
capture=ledger.capture_project('synthetic-evidence-pilot',pid)
case('3. The curator approves only the title',compare(base,later,captures=[capture['id']]),'The captured workflow contains the title-only decision and saved export receipt. The later matching package establishes adoption; the unresolved access question remains in the research history. No service verification is inferred.')
phone=deepcopy(data);phone['resources'][0]['phone']='555-0199';comp=compare(base,imp(phone));event=comp['events'][0]
ledger.attest(comp['id'],event['eventId'],reviewer='Synthetic curator',method='phone',note='Synthetic confirmation of this phone field only.',source='Synthetic call note — no actual call occurred')
case('4. A specific phone correction has explicit evidence',comp,'This synthetic call note verifies only the changed phone field. It does not verify the whole resource. The entire demonstration is marked development-only and supplies no real vetting outcomes.')
subset=deepcopy(data);subset['resources']=subset['resources'][:1]
case('5. A resource is missing from a partial package',compare(base,imp(subset,'partial')),'Scout records an absence. It does not label the resource closed, deleted, rejected, or a research failure.')
(p/'pilot.json').write_text(json.dumps(cases,indent=2,ensure_ascii=False)+'\n')
esc=lambda x:html.escape(str(x),quote=True)
labels={'observed-change':'Observed change','linked-adoption':'Linked proposal adoption','explicit-vetted-outcome':'Explicit verification of this field'}
body=''
for item in cases:
 report=item['report'];body+='<section><h2>'+esc(item['title'])+'</h2><p>'+esc(item['explanation'])+'</p>'
 for event in report['events']:
  body+='<p class="level">'+esc(labels[event['level']])+'</p><p><strong>Field:</strong> '+esc('Whole record' if event['field']=='*' else event['field'])+'</p>'
  if event['field']!='*':body+='<dl><dt>Before</dt><dd>'+esc(event['before'])+'</dd><dt>After</dt><dd>'+esc(event['after'])+'</dd></dl>'
 summary=report['summary']
 body+='<details><summary>What was recorded</summary><ul>'
 for label,key in [('Changes observed','observedChanges'),('Linked proposal adoptions','linkedAdoptions'),('Fields with explicit verification','explicitFieldVerifications')]:
  body+='<li>'+label+': '+str(summary[key])+'</li>'
 body+='</ul><p>No whole-resource verification was inferred. No research lessons were activated. Learning readiness is not assessed from these synthetic examples.</p></details></section>'
page='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Scout evidence pilot</title><style>
*{box-sizing:border-box}body{margin:0;background:#f3f6f7;color:#203139;font:18px/1.5 system-ui,sans-serif;overflow-wrap:anywhere}header{background:#163f42;color:white;padding:24px}header>div,main{max-width:900px;margin:auto}main{padding:20px}h1{font-size:1.8rem;margin:0}h2{font-size:1.3rem}section{background:white;border:1px solid #ccd6da;border-radius:10px;padding:20px;margin:18px 0}.notice{background:#fff2cf;padding:16px}.level{font-weight:bold;color:#185b49}dt{font-weight:bold}dd{margin:4px 0 12px}summary{cursor:pointer;font-weight:600}pre{white-space:pre-wrap;font:14px/1.4 monospace}@media(max-width:500px){main{padding:12px}section{padding:16px}}@media print{body{background:white;font:11pt/1.35 Arial}header{background:white;color:black;padding:0}main{padding:0}section{border:0;break-inside:avoid}details{display:none}}
</style></head><body><header><div><h1>Scout evidence pilot</h1><p>What can Scout learn from a curator’s decisions?</p></div></header><main><p class="notice"><strong>Synthetic demonstration.</strong> These are invented QA examples, not Mesa or Provo resources, real calls, human approvals, or independent AI research. No office package changes. No lessons activated.</p><p>The ledger keeps a record of what changed, what came from Scout, and what was explicitly verified. These are separate kinds of evidence.</p>'''+body+'''<section><h2>What to discuss next</h2><p>Do these distinctions reflect what the curator actually decided? Title approval should not certify services. A missing resource should not imply closure.</p><p>Next in the grand plan: try evidence capture with attributable office outcomes, discuss any uncertain links, and only then evaluate readiness for research-method learning. Adaptive category assignments come later.</p></section></main></body></html>'''
(p/'autoScoutEvidencePilot.html').write_text(page)
assert all(c['report']['historical'] for c in cases)
print(json.dumps({'output':str(p/'autoScoutEvidencePilot.html'),'cases':len(cases),'levels':[c['report']['events'][0]['level'] for c in cases],'activeLessons':0},indent=2))
