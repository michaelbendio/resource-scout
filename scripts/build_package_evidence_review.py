#!/usr/bin/env python3
"""Compare two explicitly selected real packages without inventing attribution."""
import argparse
from collections import Counter, defaultdict
import html
import json
from pathlib import Path

from resource_research_agent.improvement_packages import read_package
from resource_research_agent.learning_evidence import EvidenceLedger
from resource_research_agent.storage import ResearchStore


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('before', type=Path)
    parser.add_argument('after', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--office', required=True)
    parser.add_argument('--collection', required=True)
    parser.add_argument('--lineage-note', required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    ledger = EvidenceLedger(ResearchStore(args.output / 'evidence.sqlite3'))
    records, packages, sources = [], [], []
    for path in (args.before, args.after):
        payload = path.read_bytes()
        package = read_package(payload, evidence_legacy_version=True)
        record = ledger.import_package(args.collection, args.office, payload, scope='unknown', historical=True)
        records.append(record)
        packages.append(package)
        sources.append({'path': str(path.resolve()), 'evidence': record,
                        'createdAt': package['data'].get('packageCreatedAt'),
                        'resourceCount': len(package['resources'])})
    comparison = ledger.compare(records[0]['id'], records[1]['id'], reviewer='Scout operator',
                                lineage_note=args.lineage_note)
    report = ledger.report(comparison['id'])
    counts = Counter(e['field'] for e in report['events'])
    result = {'sources': sources, 'fieldCounts': dict(counts), 'report': report}
    (args.output / 'pilot.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    esc = lambda value: html.escape(str(value), quote=True)
    def display(value):
        return esc(value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2))
    grouped = defaultdict(list)
    for event in report['events']:
        grouped[event['resourceId']].append(event)
    cards = []
    for rid, events in grouped.items():
        resource = packages[1]['resources'].get(rid, packages[0]['resources'].get(rid, {}))
        title = resource.get('name', rid)
        rows = ''.join('<h3>' + esc(e['field']) + '</h3><div class="pair"><div><h4>Before</h4><pre>'
                       + display(e['before']) + '</pre></div><div><h4>After</h4><pre>'
                       + display(e['after']) + '</pre></div></div>' for e in events)
        cards.append('<details class="resource"><summary>' + esc(title) + ' · '
                     + esc(', '.join(e['field'] for e in events)) + '</summary>' + rows + '</details>')
    source_html = ''.join('<li>' + esc(Path(s['path']).name) + ': ' + str(s['resourceCount'])
                         + ' resources; saved ' + esc(s['createdAt']) + '</li>' for s in sources)
    warnings = ''.join('<p>' + esc(w) + '</p>' for r in records for w in r['intakeWarnings'])
    page = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Scout · Real package evidence</title><style>
*{box-sizing:border-box}body{margin:0;background:#f3f6f7;color:#203139;font:18px/1.5 system-ui;overflow-wrap:anywhere}main{max-width:1100px;margin:auto;padding:24px}h1{font-size:1.8rem}h2{font-size:1.35rem}section,details.resource{background:white;border:1px solid #ccd6da;border-radius:10px;padding:18px;margin:16px 0}summary,button{cursor:pointer}summary{font-weight:600}.notice{background:#fff2cf}.pair{display:grid;grid-template-columns:1fr 1fr;gap:24px}.pair>div{min-width:0}pre{white-space:pre-wrap;font:inherit}button{padding:10px;font:inherit}h4{margin-bottom:0}@media(max-width:650px){.pair{display:block}main{padding:12px}}@media print{body{background:white;font:11pt/1.35 Arial}main{padding:0}.resource,button,.screen-only{display:none!important}section{border:0;padding:0}}
</style><main><h1>Scout · Real package evidence</h1><p>What Scout checked: two saved Mesa packages, compared by resource ID and exact field values.</p>
<button onclick="window.print()">Print overview</button><section class="notice"><h2>Real changes; limited attribution</h2>
<p>These are actual saved resource packages, not invented examples. This historical comparison does not establish who made each change, whether a curator accepted a particular proposal, or whether a provider confirmed the information. No individual proposal receipts or verification notes were supplied.</p>
<p>All changes remain observations. Linked proposal adoptions: 0. Explicit field verifications: 0. Inferred whole-resource vetting: 0. Lessons activated: 0.</p></section>'''
    page += '<section><h2>What changed</h2><p>' + str(len(grouped)) + ' resource or catalog records; ' + str(len(report['events'])) + ' field/history observations.</p><ul>'
    page += ''.join('<li>' + esc(field) + ': ' + str(count) + '</li>' for field, count in sorted(counts.items())) + '</ul></section>'
    page += '<section><h2>Sources and limits</h2><ul>' + source_html + '</ul><p>' + esc(args.lineage_note) + '</p>' + warnings
    page += '<p>Original ZIP bytes and hashes are retained in the ledger. Package completeness is unconfirmed. Dates, names and matching IDs support this selected comparison; they do not prove a complete editing history.</p></section>'
    page += '<section><h2>Questions to settle</h2><p>For future final packages, can we retain the delivered Scout proposal and the curator’s decision alongside the changed field? When a provider confirms a fact, which field was checked, by whom, when and how?</p><p>Stephanie’s approved writing instructions are direct guidance. Repeating an editorial change across many resources does not turn it into many independent examples of successful research.</p><p>Next in the grand plan: connect evidence capture to routine package intake, preserving these distinctions. Research-method lessons and adaptive category assignments follow attributable vetting outcomes and a readiness review.</p></section>'
    page += '<div class="screen-only"><h2>Inspect the exact changes</h2><p>Changes are bold; removed text is crossed out in Before. Open a resource to compare its fields. Printing includes the overview only.</p></div>' + ''.join(cards) + '</main></html>'
    highlighter = (Path(__file__).resolve().parents[1] / 'web/comparison.js').read_text()
    page += '<script>' + highlighter + "\nfor(const pair of document.querySelectorAll('.pair')){const [a,b]=pair.querySelectorAll('pre');const d=highlightComparison(a.innerHTML,b.innerHTML);a.innerHTML=d.before;b.innerHTML=d.after;}" + '</script>'
    target = args.output / 'autoMesaEvidencePilot.html'
    target.write_text(page)
    print(json.dumps({'output': str(target), 'fieldCounts': dict(counts), 'summary': report['summary']}, indent=2))


if __name__ == '__main__':
    main()
