#!/usr/bin/env python3
"""Render a short overview of a working package, with optional exact comparisons."""
import argparse
from collections import defaultdict
import html
import json
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('directory', type=Path)
args = parser.parse_args()
p = args.directory
m = json.loads((p / 'manifest.json').read_text())
esc = lambda x: html.escape(str(x), quote=True)
labels = {'description': 'Description', 'informationText': 'Information', 'categories': 'Categories',
          'categoryFilters': 'Types', 'forGroups': 'Groups'}
groups = defaultdict(list)
for change in m['changes']:
    groups[change['resourceId']].append(change)
def value(v):
    return esc(v if isinstance(v, str) else json.dumps(v, ensure_ascii=False, indent=2))
cards = ''
for changes in groups.values():
    cards += '<li><strong>' + esc(changes[0]['name']) + '</strong>: ' + ', '.join(labels[e['field']] for e in changes) + '.</li>'
examples = ''
# One brief example; complete comparisons remain optional.
sample = next(e for e in m['changes'] if e['field'] == 'description' and 'Financial' in e['name'])
examples += '<h3>' + esc(sample['name']) + '</h3><div class="pair"><div><h4>Before</h4><pre>' + value(sample['before']) + '</pre></div><div><h4>Working copy</h4><pre>' + value(sample['after']) + '</pre></div></div>'
details = ''
for changes in groups.values():
    details += '<details><summary>' + esc(changes[0]['name']) + '</summary>'
    for e in changes:
        details += '<h3>' + labels[e['field']] + '</h3><div class="pair"><div><h4>Before</h4><pre>' + value(e['before']) + '</pre></div><div><h4>Working copy</h4><pre>' + value(e['after']) + '</pre></div></div>'
    details += '</details>'
page = '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Provo · First working batch</title><style>
*{box-sizing:border-box}body{margin:0;background:#f3f6f7;color:#203139;font:18px/1.5 system-ui;overflow-wrap:anywhere}main{max-width:1000px;margin:auto;padding:24px}h1{font-size:1.8rem}h2{font-size:1.35rem}h3{font-size:1.1rem}section{background:white;border:1px solid #ccd6da;border-radius:10px;padding:20px;margin:18px 0}.pair{display:grid;grid-template-columns:1fr 1fr;gap:20px}.pair>div{min-width:0}pre{white-space:pre-wrap;font:inherit}button{font:inherit;padding:10px;cursor:pointer}summary{cursor:pointer;font-weight:600}details{margin:16px 0}li{margin:8px 0}.notice{background:#fff2cf;padding:14px}@media(max-width:650px){main{padding:12px}.pair{display:block}}@media print{body{font:10.5pt/1.3 Arial;background:white}main{padding:0}button,.optional,.links{display:none}section{border:0;margin:10px 0;padding:0}h1{font-size:18pt}h2{font-size:13pt}.pair{display:block}.example{display:none}}
</style></head><body><main><h1>Provo · First working batch</h1><p class="notice">August 12 baseline. Five resources updated using previously accepted research. All 183 resources and 93 PDFs retained. This separate working copy has not been merged into the live office.</p>
<p class="links"><a href="autoProvoWorkingResources.html">Browse the working resources</a> · <a href="provo-scout-working-resource-package.zip">Working package ZIP</a></p><button onclick="window.print()">Print short summary</button>
<section><h2>What is ready</h2><ul>''' + cards + '''</ul><p>These changes reuse the completed four-AI pilots and your recorded acceptance. They are not new research or provider verification. The other 178 resource records remain unchanged.</p></section>
<section><h2>What still needs a curator decision</h2><ul>
<li><strong>Housing Authority:</strong> which residency and household rules apply to each housing list? Existing Information and the Addiction category remain unchanged.</li>
<li><strong>Financial Learning:</strong> confirm the separate website link and current class childcare/language arrangements. Writing includes a program link and call-to-confirm wording; group additions are deferred.</li>
<li><strong>DWS:</strong> confirm the county housing handoff and the local veteran reentry pathway. Existing Housing is retained; Veteran Services changes are deferred.</li>
</ul><p>Category retirement and the maintenance proposals remain separate pending work. They have not been silently applied here.</p></section>
<section class="example"><h2>One example</h2><p>Changes are bold; removed wording is crossed out in Before.</p>''' + examples + '''</section>
<section class="optional"><h2>Exact changes, if useful</h2><p>No need to review every field again. The full comparisons are available here.</p>''' + details + '''</section>
<section><h2>Next in the plan</h2><p>This is the first usable batch, not completion of the whole Provo collection. Continue improving the remaining resources while the curator settles the outstanding questions. Routine use now captures evidence for increment 5; research lessons and adaptive assignments follow sufficient attributable outcomes.</p></section></main>'''
script = (Path(__file__).resolve().parents[1] / 'web/comparison.js').read_text()
page += '<script>' + script + "\nfor(const pair of document.querySelectorAll('.pair')){const [a,b]=pair.querySelectorAll('pre');const d=highlightComparison(a.innerHTML,b.innerHTML);a.innerHTML=d.before;b.innerHTML=d.after;}" + '</script></body></html>'
(p / 'autoProvoWorkingSummary.html').write_text(page)
print(p / 'autoProvoWorkingSummary.html')
