#!/usr/bin/env python3
"""Create a portable read-only review of explicitly synthetic maintenance cases."""
import argparse
import html
import json
from pathlib import Path

p=argparse.ArgumentParser();p.add_argument('snapshot',type=Path);p.add_argument('output',type=Path);args=p.parse_args()
v=json.loads(args.snapshot.read_text())
if not v['historical'] or not v['runName'].startswith('Synthetic maintenance examples'):
    raise SystemExit('This demonstration builder accepts only the labeled synthetic QA snapshot')
esc=lambda x:html.escape(str(x))
labels={'informationText':'Information','informationSections':'Information','forGroups':'Groups','categoryFilters':'Types','categories':'Categories'}
def value(x):
    if isinstance(x,dict):return '<br>'.join('<strong>'+esc(labels.get(k,k))+':</strong> '+value(v) for k,v in x.items())
    if isinstance(x,list):return ', '.join(esc(v) for v in x) or '(none)'
    return esc(x if x is not None else '(not recorded)')
actions={'moved':'Review the new address; retain the existing identity.', 'paused':'Review the temporary-availability note; keep the resource.',
'possibly-closed':'Review the explicit notice and independent checks. If accepted, send a pending deletion request to the office. The resource remains until office deletion review.',
'inconclusive':'Keep the resource and follow up by phone. A failed website is not a closure finding.',
'current':'Keep the observation. Do not advance the human verification date.',
'renamed':'Confirm it is the same program, then update the existing name.',
'reopened':'Confirm resumed service and update the existing record. Do not create a duplicate.',
'identity':'Resolve the program boundary before changing the record.',
'new':'Review the identity matches, service category, and five Information sections before adding it.'}
parts=[]
for r in v['items']:
    comparison=''.join(f'<tr><th>{esc(labels.get(k,k.title()))}</th><td>{value(c["current"])}</td><td>{value(c["proposed"])}</td></tr>' for k,c in r['comparison'].items())
    if comparison:comparison='<table><thead><tr><th>Field</th><th>Current office value</th><th>Proposed value</th></tr></thead><tbody>'+comparison+'</tbody></table>'
    elif not r['current']:comparison=''.join(f'<h4>{esc(labels.get(k,k.title()))}</h4><p>{value(x)}</p>' for k,x in r['fields'].items())
    else:comparison='<p>No field changes proposed.</p>'
    parts.append(f'<section><h2>{esc(r["current"]["name"] if r["current"] else r["program"])} <small>{esc(r["status"])}</small></h2><p>{esc(r["summary"])}</p><p><strong>Review action:</strong> {esc(actions[r["status"]])}</p><details><summary>Inspect current and proposed information</summary>{comparison}<p>Last human verification: {esc((r["current"] or {}).get("verifiedOn","not recorded"))}. Research does not change this date.</p><p>Suggested next check: {esc(r["nextCheckOn"] or "not proposed")}</p></details><details><summary>Evidence and follow-up</summary><p>These notices and research stages are simulated test data, not findings from real research services.</p>'+''.join('<p>'+esc(s['accessedOn'])+' — '+esc(s['excerpt'])+'</p>' for s in r['sources'])+''.join('<p><strong>Follow-up:</strong> '+esc(q)+'</p>' for q in r['questions'])+'</details></section>')
c=v['coverage']
body='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Scout Maintenance Review — Demonstration</title><style>
body{font:18px/1.5 system-ui,sans-serif;color:#17334a;background:#f3f6f8;margin:0}main{max-width:980px;margin:auto;padding:20px}header{background:#07365e;color:white;padding:20px}header div{max-width:980px;margin:auto}section{background:white;border:1px solid #cbd5df;border-radius:8px;padding:18px;margin:20px 0}h1{font-size:1.7em}h2{font-size:1.25em}small{display:block;color:#536575;font-size:.85em}.notice{background:#fff0c6;padding:16px;border-left:5px solid #a26a00}summary{padding:12px 0;cursor:pointer;font-weight:bold}details{margin:8px 0}table{border-collapse:collapse;width:100%;table-layout:fixed}td,th{text-align:left;vertical-align:top;padding:10px;border:1px solid #d5dfe7;overflow-wrap:anywhere}p{overflow-wrap:anywhere}@media(max-width:600px){main{padding:12px}body{font-size:17px}td,th{padding:6px}section{padding:12px}}:focus-visible{outline:3px solid #155ea0;outline-offset:3px}
</style></head><body><header><div><h1>Scout maintenance review</h1><p>Software demonstration — invented programs and notices</p></div></header><main><p class="notice">This is a read-only demonstration. No real Provo resource has been checked, no research service supplied these test results, and this file cannot change an office package.</p>'''
body+=f'<section><h2>Two separate workstreams</h2><p><strong>Known resources:</strong> {c["recheck"]["completed"]} checked in the simulation, {c["officeResources"]} in the example office. One remains unchecked.</p><p><strong>Addition searches:</strong> {c["discovery"]["completed"]} category searched in the simulation, {c["officeCategories"]} in the example office. One category remains unsearched.</p><p>Reviewed updates and additions can be saved while other checks await research or a phone call. Canceled downloads leave reviews available.</p></section>'
body+=''.join(parts)+'<section><h2>What to assess</h2><p>Are the proposed actions clear? Does Scout distinguish a move, a temporary pause, a closed program, and an unsuccessful check? Is the current/proposed comparison sufficient for review?</p><p>After this software review, the next step is a small real maintenance pilot. The grand plan then proceeds to proposed lessons from human-vetted changes, followed later by adaptive research assignments.</p></section></main></body></html>'
args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(body)
print(args.output)
