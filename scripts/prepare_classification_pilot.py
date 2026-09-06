#!/usr/bin/env python3
"""Prepare the authorized historical six-resource pilot without claiming approval or research."""
from __future__ import annotations
import argparse
import hashlib
import html
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from resource_research_agent.improvement_packages import digest, read_package
from resource_research_agent.scout_classification import ClassificationWorkflow
from resource_research_agent.storage import ResearchStore

RESOURCE_IDS=['83cef4c7ca6a62e9bf4ab6d694f78bd9','provo-city-housing-authority',
              '4e2aee885b2126ae255d187c8496758b','ddd37652117d3f75952de587aa414ffd',
              'be263f34ffef82d605bccabb5a29bec3','facc']
EXPECTED_SHA='dc883d19eff7a30e78d33df580ea8408a50788eade33647c40ec6a23f0201a49'


def prepare(package_path, previous_pilot, output):
    payload=package_path.read_bytes();package=read_package(payload)
    if package['sha256']!=EXPECTED_SHA:raise ValueError('This pilot script expects the explicitly authorized historical Provo v41 package')
    acceptance=json.loads((previous_pilot/'pilot-acceptance.json').read_text())
    review=json.loads((previous_pilot/'review-snapshot.json').read_text())
    if acceptance['baseSha256']!=EXPECTED_SHA or review['baseSha256']!=EXPECTED_SHA:raise ValueError('Prior writing pilot source mismatch')
    if hashlib.sha256((previous_pilot/'autoProvoPilot.html').read_bytes()).hexdigest()!=acceptance['reviewHtmlSha256']:raise ValueError('Accepted writing review HTML changed')
    accepted={r['resourceId']:r['sourceResultSha256'] for r in acceptance['proposals']}
    linked={}
    for row in review['resources']:
        result=row['evidence']['reconcile'];rid=row['id']
        if accepted.get(rid)!=digest(result) or row['proposal']['sourceResultSha256']!=digest(result):raise ValueError('Prior accepted result mismatch')
        content={'sourcePackageSha256':EXPECTED_SHA,'acceptedWritingProposal':row['proposal'],
                 'reconciledResearch':result,'priorFindings':row['findings'],'acceptance':acceptance,
                 'limitations':['Acceptance concerns writing and reconciliation, not classification or production export.',
                                'Provider questions remain unresolved.',
                                'External auditors received supplied observations of scanned PDFs, not the PDF binaries.']}
        linked[rid]=[{'label':'Accepted increment 2 writing and reconciliation; classification remains to be researched',
                      'sha256':digest(content),'content':content}]
    guidance=json.loads((ROOT/'examples/provo-classification-pilot-definitions.json').read_text())
    output.mkdir(parents=True,exist_ok=True)
    flow=ClassificationWorkflow(ResearchStore(output/'pilot.sqlite3'))
    view=flow.prepare(payload,'Provo TSO',RESOURCE_IDS,source_name=package_path.name,historical=True,
                      guidance=guidance,linked_evidence=linked)
    (output/'project.json').write_text(json.dumps(view,ensure_ascii=False,indent=2)+'\n')
    (output/'definitions.json').write_text(json.dumps(view['guidance'],ensure_ascii=False,indent=2)+'\n')
    (output/'events.json').write_text(json.dumps(flow.events(view['id']),ensure_ascii=False,indent=2)+'\n')
    # A standalone readable artifact can be opened on Mac or through the iPad viewer.
    esc=html.escape
    body='<h1>Provo classification pilot</h1><p class="notice">Definition review only · historical August 12 package · no classification research or office update has been approved by this page.</p>'
    body+='<p>Scout proposes categories for the need, Types for the particular service, and groups for people explicitly served or meaningfully accommodated. Generic availability does not justify a group.</p>'
    body+='<h2>The six-resource pilot</h2><ul>'+''.join('<li>'+esc(r['original']['name'])+'</li>' for r in view['resources'])+'</ul>'
    body+='<p>The three accepted writing proposals are preserved as linked evidence. This pilot keeps the source records and PDFs unchanged.</p>'
    for field,title in [('forGroups','Groups'),('categories','Categories'),('categoryFilters','Types proposed for this pilot')]:
        body+='<h2>'+title+'</h2>'
        for t in guidance['terms']:
            if t['field']!=field or (field=='categoryFilters' and not t['definition']):continue
            label=t['label']+(' ('+t['categoryId']+')' if field=='categoryFilters' else '')
            definition=t['definition'] or 'Leave pending: the office needs to clarify which health risks or accommodations qualify.'
            body+='<section><h3>'+esc(label)+'</h3><p>'+esc(definition)+'</p></section>'
    body+='<p>All other Types stay pending. Existing unconfirmed assignments are retained. Seniors and Veterans category memberships cannot be removed in this slice; that requires a complete migration review.</p>'
    body+='<p><strong>Review decision:</strong> Use these definitions for the historical pilot, or discuss changes first. Approval of definitions does not approve any resource classifications or production export.</p>'
    document='<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Provo classification pilot definitions</title><style>body{font:18px/1.55 system-ui,sans-serif;max-width:850px;margin:auto;padding:24px;color:#203547;background:#f5f8fb}section{background:white;border:1px solid #cedbe6;border-radius:8px;padding:0 18px;margin:12px 0}h1,h2,h3{line-height:1.25}.notice{background:#fff1c9;padding:16px;border-left:4px solid #ad7b00}h2{margin-top:2em} @media print{body{background:white;font-size:12pt}section{break-inside:avoid}}</style>'+body+'</html>'
    (output/'autoProvoClassificationDefinitions.html').write_text(document)
    print(json.dumps({'projectId':view['id'],'database':str(output/'pilot.sqlite3'),'resources':len(view['resources']),
                      'linkedAcceptedWritingResources':len(linked),'historical':True,'definitionsApproved':False,
                      'reviewHtml':str(output/'autoProvoClassificationDefinitions.html')},indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--package',type=Path,required=True)
    p.add_argument('--previous-pilot',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();prepare(a.package,a.previous_pilot,a.output)
