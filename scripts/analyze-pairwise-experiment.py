#!/usr/bin/env python3
"""Read-only evidence export. Counts candidates, never claims curated acceptance."""
from __future__ import annotations
import argparse
import collections
import csv
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import sys
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from resource_research_agent.worker_metrics import observed_counter

PROFILES = ('codex-grok', 'codex-claude', 'claude-grok')

def counter_observation(usages, key):
    values = [observed_counter(usage, key) for usage in usages]
    known = [value for value in values if value is not None]
    return {'observedSum': sum(known) if known else None,
            'knownAttempts': len(known), 'attempts': len(values),
            'completeSum': sum(known) if values and len(known) == len(values) else None}

def seconds(start, end):
    return (dt.datetime.fromisoformat(end)-dt.datetime.fromisoformat(start)).total_seconds() if start and end else None

def normalize(value):
    return ' '.join(re.findall(r'[a-z0-9]+', (value or '').casefold()))

def legacy_failures(path):
    """Recover counters from original logs without printing provider transcripts."""
    result=[]
    if not path.exists():
        return result
    for line_number,line in enumerate(path.read_text().splitlines(),1):
        try:
            event=json.loads(line)
        except ValueError:
            continue
        if event.get('event') not in ('worker-retry','worker-failed'):
            continue
        match=re.search(r'\{.*\}',event.get('error',''))
        try:
            envelope=json.loads(match[0]) if match else {}
        except ValueError:
            envelope={}
        usage=envelope.get('modelUsage') or {}
        result.append({'file':path.name,'line':line_number,'event':event['event'],
          'provider':event.get('worker'),'category':event.get('category'),'attempt':event.get('attempt'),
          'terminalReason':envelope.get('terminal_reason'), 'reportedDurationMs':envelope.get('duration_ms'),
          'reportedTurns':envelope.get('num_turns'),
          'reportedSearches':sum(v['webSearchRequests'] for v in usage.values())
            if usage and all(isinstance(v,dict) and 'webSearchRequests' in v for v in usage.values()) else None})
    return result

def read_condition(path, limit):
    db=sqlite3.connect(path.resolve().as_uri()+'?mode=ro', uri=True)
    db.row_factory=sqlite3.Row
    db.execute('BEGIN')
    tables={r[0] for r in db.execute("select name from sqlite_master where type='table'")}
    rows=lambda query,args=(): [dict(r) for r in db.execute(query,args)]
    jobs=rows('select * from focused_research_jobs order by id limit ?', (limit,))
    categories=[]; all_leads=[]
    for job in jobs:
        jid=job['id']; run=job['run_id']
        passes=rows('select * from focused_research_passes where job_id=? order by ordinal',(jid,))
        assignments=rows('select * from codex_first_research_assignments where job_id=?',(jid,))
        telemetry=rows('select * from research_worker_telemetry where job_id=? order by id',(jid,)) if 'research_worker_telemetry' in tables else []
        leads=rows('''select l.*,m.source_label,m.created_at from manual_discovery_leads l
          join manual_discovery_contributions m on m.id=l.contribution_id where m.run_id=? order by l.id''',(run,))
        challenger_ids={a['contribution_id'] for a in assignments}
        for lead in leads:
            lead.update(profile=path.stem, category=job['category_label'],role='challenger' if lead['contribution_id'] in challenger_ids else 'primary')
            lead['exact_name_key']=normalize(lead['organization'])+'|'+normalize(lead['program'])
            lead['host']=urlsplit(lead['website_normalized'] or lead['website_raw']).hostname or ''
        primary=[l for l in leads if l['role']=='primary']; challenger=[l for l in leads if l['role']=='challenger']
        primary_names={l['exact_name_key'] for l in primary}; primary_orgs={normalize(l['organization']) for l in primary}
        counts={'primary':len(primary),'challenger':len(challenger),'total':len(leads),
          'exactNamePairs':len({l['exact_name_key'] for l in leads}),
          'challengerExactNamePairAdditions':len({l['exact_name_key'] for l in challenger}-primary_names),
          'challengerSameOrganizationRows':sum(normalize(l['organization']) in primary_orgs for l in challenger),
          'missingWebsiteRows':sum(not l['website_raw'].strip() for l in leads),
          'uncertaintyRows':sum(bool(l['uncertainty'].strip()) for l in leads),
          'sourceHosts':len({l['host'] for l in leads if l['host']})}
        starts=[p['assigned_at'] for p in passes if p['assigned_at']]
        pass_windows=[seconds(p['assigned_at'],p['completed_at']) for p in passes if p['completed_at']]
        ext_windows=[seconds(a['created_at'],a['completed_at']) for a in assignments if a['completed_at']]
        known_success=[t for t in telemetry if t['outcome']=='completed']
        usage=[json.loads(t['usage_json']) for t in known_success]
        provider_metrics={}
        for provider in sorted({t['provider'] for t in telemetry}):
            attempts=[t for t in telemetry if t['provider']==provider]
            successful=[t for t in attempts if t['outcome']=='completed']
            counters=[json.loads(t['usage_json']) for t in successful]
            turns=counter_observation(counters, 'numTurns')
            searches=counter_observation(counters, 'webSearchRequests')
            provider_metrics[provider]={
              'successfulAttempts':len(successful),'failedAttempts':len(attempts)-len(successful),
              'successfulWorkerSeconds':sum(t['elapsed_ms'] for t in successful)/1000,
              'failedWorkerSeconds':sum(t['elapsed_ms'] for t in attempts if t['outcome']=='failed')/1000,
              'observedTurns':turns['observedSum'],
              'positiveSearchCountLowerBound':searches['observedSum'],
              'counterCoverage':{'numTurns':turns,'webSearchRequests':searches},
              'successfulModelUsage':[u.get('modelUsage') for u in counters if u.get('modelUsage')]}
        # Legacy extraction converted absent counters to zero. A positive counter is observed;
        # zero cannot establish absence of tools without the underlying provider envelope.
        turns=counter_observation(usage, 'numTurns')
        searches=counter_observation(usage, 'webSearchRequests')
        categories.append({'category':job['category_label'],'status':job['status'],'counts':counts,
          'firstPassAssignedAt':min(starts) if starts else None,'completedAt':job['completed_at'],
          'categoryElapsedSeconds':seconds(min(starts),job['completed_at']) if starts else None,
          'primaryAssignmentWindowSeconds':sum(pass_windows),'challengerAssignmentWindowSeconds':sum(ext_windows),
          'completedPrimaryPasses':sum(p['status']=='completed' for p in passes),
          'completedChallengerAssignments':sum(a['status']=='completed' for a in assignments),
          'telemetrySuccessfulAttempts':len(known_success),'telemetryFailedAttempts':sum(t['outcome']=='failed' for t in telemetry),
          'telemetrySuccessfulSeconds':sum(t['elapsed_ms'] for t in known_success)/1000,
          'telemetryFailedSeconds':sum(t['elapsed_ms'] for t in telemetry if t['outcome']=='failed')/1000,
          'reportedTurns':turns['observedSum'],
          'reportedPositiveSearchCountLowerBound':searches['observedSum'],
          'counterCoverage':{'numTurns':turns,'webSearchRequests':searches},
          'acceptedUniqueIdentities':None,'acceptedIdentitiesPerActiveMinute':None,
          'marginalAcceptedIdentitiesPerAdditionalMinute':None,'curatorMinutes':None,
          'passes':[{k:p[k] for k in ['id','focus_key','pass_kind','status','assigned_at','completed_at','lead_count']} for p in passes],
          'challengers':[{**{k:a[k] for k in ['id','researcher','status','created_at','completed_at','lead_count','assignment_sha256']},
                          'assignmentCharacters':len(a['assignment'])} for a in assignments],
          'telemetry':telemetry})
        categories[-1]['providerMetrics']=provider_metrics
        all_leads.extend(leads)
    source_import=rows('select * from imports order by id limit 1')[0]
    baseline={t:rows('select * from '+t+' order by rowid') for t in ('imports','categories','imported_resources','known_terms','research_seeds')}
    fingerprint=hashlib.sha256(json.dumps(baseline,sort_keys=True).encode()).hexdigest()
    result={'profile':path.stem,'database':str(path.resolve()),'baselineLogicalSha256':fingerprint,
      'sourcePackageSha256':source_import['source_sha256'],'importedResourceCount':len(baseline['imported_resources']),
      'curationJobCount':db.execute('select count(*) from scout_curation_jobs').fetchone()[0],
      'allSelectedCategoriesComplete':len(categories)==limit and all(c['status']=='completed' for c in categories),
      'originalLogFailures':legacy_failures(path.with_suffix('.log')),
      'categories':categories}
    db.close()
    return result,all_leads

def main():
    p=argparse.ArgumentParser();p.add_argument('experiment',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--require-complete',action='store_true');a=p.parse_args()
    conditions=[];leads=[]
    for profile in PROFILES:
        condition,rows=read_condition(a.experiment/(profile+'.sqlite3'),6);conditions.append(condition);leads.extend(rows)
    if a.require_complete and not all(c['allSelectedCategoriesComplete'] for c in conditions):raise SystemExit('Six-category conditions still incomplete; refusing final report')
    a.output.mkdir(parents=True,exist_ok=True)
    result={'generatedAt':dt.datetime.now(dt.timezone.utc).isoformat(),'conditions':conditions,'limits':[
      'No completed curation: accepted identities and accepted-rate metrics are unknown.',
      'Exact name pairs are candidate string fingerprints, not resolved service identities.',
      'Shared organization does not imply duplicate program. Shared domain does not imply duplicate provider.',
      'Assignment time windows include pauses/retries; not interchangeable with active inference time.',
      'Missing telemetry is unknown, not zero. Legacy zero search counters may represent missing metadata.',
      'Comparison includes different primary results, wrapper ceilings, authentication failures and staggered restarts.']}
    (a.output/'metrics.json').write_text(json.dumps(result,indent=2))
    (a.output/'leads.json').write_text(json.dumps(leads,indent=2))
    fields=['profile','category','id','role','organization','program','website_raw','phone','address','lead_type','location_or_service_area','why_relevant','uncertainty']
    with (a.output/'leads.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');writer.writeheader();writer.writerows(leads)
    print(json.dumps([{'profile':c['profile'],'complete':c['allSelectedCategoriesComplete'],'baseline':c['baselineLogicalSha256'],'categories':[{'category':r['category'],'primary':r['counts']['primary'],'challenger':r['counts']['challenger'],'elapsedMinutes':round(r['categoryElapsedSeconds']/60,1) if r['categoryElapsedSeconds'] is not None else None} for r in c['categories']]} for c in conditions],indent=2))

if __name__=='__main__':main()
