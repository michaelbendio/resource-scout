#!/usr/bin/env python3
"""Create a portable read-only review using a copy of a classification database.

This inventories evidence and creates optional unapproved migration drafts.
It never changes the source database, runs researchers, or grants approval.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import sqlite3
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from resource_research_agent.storage import ResearchStore
from resource_research_agent.scout_classification import ClassificationWorkflow
from resource_research_agent.taxonomy_review import TaxonomyReview


def build(database,project,output,retire):
    output.mkdir(parents=True,exist_ok=False)
    copied=output/'review.sqlite3'
    with sqlite3.connect(f'file:{database.resolve()}?mode=ro',uri=True) as source,sqlite3.connect(copied) as target:
        source.backup(target)
    review=TaxonomyReview(ClassificationWorkflow(ResearchStore(copied)))
    report=review.view(project)
    if retire:
        report=review.create_plan(project,report['revision'],retire,
            'Review every resource before replacing population categories with service categories and supported groups. Draft only; no retirement approved.')
    serialized=json.dumps(report,ensure_ascii=False,indent=2)
    (output/'review-snapshot.json').write_text(serialized,encoding='utf-8')
    html=(ROOT/'web/taxonomy-review.html').read_text()
    html=html.replace('<link rel="stylesheet" href="/improvements.css">','<style>'+(ROOT/'web/improvements.css').read_text()+'</style>')
    embedded=serialized.replace('<','\\u003c').replace('\u2028','\\u2028').replace('\u2029','\\u2029')
    html=html.replace('<script src="/taxonomy-review.js"></script>',f'<script>window.SCOUT_TAXONOMY_SNAPSHOT={embedded};</script><script>'+(ROOT/'web/taxonomy-review.js').read_text()+'</script>')
    artifact=output/'autoProvoGroupReview.html' if report['office'].lower().startswith('provo') else output/'autoScoutGroupReview.html'
    artifact.write_text(html,encoding='utf-8')
    manifest={'sourceDatabase':str(database.resolve()),'projectId':project,'sourcePackageSha256':report['packageSha256'],
        'htmlSha256':hashlib.sha256(artifact.read_bytes()).hexdigest(),'readOnly':True,
        'historicalDevelopmentOnly':report['historical'],'officeResourceCount':report['officeResourceCount'],
        'researchedResourceCount':report['researchedResourceCount'],'groupCount':len(report['groups']),
        'newApprovals':False,'productionPackageChanged':False,'realResearchRun':False}
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'artifact':str(artifact),'manifest':manifest,'plans':[{'id':p['id'],'affected':len(p['affectedIds']),'researched':sum(r['researchComplete'] for r in p['rows']),'ready':p['ready']} for p in report['plans']]},indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--database',type=Path,required=True);p.add_argument('--project',type=int,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--retire',nargs='*',default=[])
    a=p.parse_args();build(a.database,a.project,a.output,a.retire)
