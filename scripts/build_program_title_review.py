#!/usr/bin/env python3
"""Render a read-only, source-linked program-title pilot with selective printing."""
import argparse
import html
import json
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('review', type=Path)
parser.add_argument('output', type=Path)
args = parser.parse_args()
data = json.loads(args.review.read_text())
esc = lambda value: html.escape(str(value), quote=True)
paragraph = lambda value: '<p>' + esc(value) + '</p>'
bullets = lambda values: '<ul>' + ''.join('<li>' + esc(v) + '</li>' for v in values) + '</ul>'
records = {r['id']: r for r in data['relatedResources']}
records.update({r['id']: r['current'] for r in data['items']})
sources = {s['id']: s for s in data['sources']}
parts = []
for row in data['items']:
    current = row['current']
    block = f'<section class="resource" id="{esc(row["id"])}"><h2>{esc(row["label"])}</h2>'
    block += '<p class="status">' + esc(row['status']) + '</p>'
    block += '<div class="comparison"><div><h3>Current title</h3>' + paragraph(current['name']) + '</div>'
    block += '<div><h3>' + ('Conditional title' if row['status'].startswith('Conditional') else 'Proposed title') + '</h3>'
    block += paragraph(row['proposedName'] or 'No title change yet — program unresolved') + '</div></div>'
    block += '<h3>Scout decision</h3>' + paragraph(row['reason'])
    if row.get('serviceAssessment'):
        block += '<h3>What a patron can receive</h3>'
        for service in row['serviceAssessment']:
            block += '<div class="service-assessment"><h4>' + esc(service['type']) + ' · ' + esc(service['status']) + '</h4>'
            block += paragraph(service['help']) + paragraph(service['access']) + '</div>'
    block += '<h3>Questions to settle</h3>' + bullets(row['questions'])
    block += '<details class="research"><summary>Research notes and sources</summary>' + bullets(row['observations'])
    for sid in row['sources']:
        source = sources[sid]
        block += '<div class="source"><h4><a href="' + esc(source['url']) + '">' + esc(source['title']) + '</a></h4>'
        block += paragraph(source['observation']) + '<p class="source-url">' + esc(source['url']) + '</p></div>'
    block += '<p class="muted">Sources checked ' + esc(data['researchDate']) + '. Observations are paraphrases. No provider contact or independent AI audit.</p></details>'
    block += '<details class="original"><summary>Current resource — unchanged</summary><h3>Description</h3>' + paragraph(current['description'])
    block += '<h3>Information</h3><div class="original-text">' + esc(current.get('informationText', '')) + '</div>'
    block += '<h3>Other recorded fields</h3><pre>' + esc(json.dumps({k:v for k,v in current.items() if k not in ('description','informationText')},indent=2,ensure_ascii=False)) + '</pre></details>'
    block += '<details class="original"><summary>Related records in this file</summary>'
    for rid in row['related']:
        r = records[rid]
        block += '<h3>' + esc(r['name']) + '</h3>' + paragraph(r['description']) + '<p class="muted">Resource ID: ' + esc(rid) + '</p>'
    block += '</details><p class="muted record-id">Existing resource ID: ' + esc(row['id']) + '</p></section>'
    parts.append(block)

overview = '''<section id="overview"><h2>What Scout checked</h2>
<p>Five entries titled A New Leaf in the saved Mesa review file. Scout checked their program identities against provider and City pages, then searched all 333 records for related services and overlap.</p>
<p><strong>Three title proposals, one conditional title, and the requested three-service title with access questions.</strong> These are review suggestions; no resource has changed.</p>
<p>This is a focused Codex review. Independent ChatGPT, Grok, and Perplexity audits were not performed because the browser connection was unavailable. It is not a completed four-AI maintenance run.</p>
<h3>Title decisions at a glance</h3><ul class="decisions">'''
for row in data['items']:
    overview += '<li><strong>' + esc(row['proposedName'] or 'Clothing and household items — title held') + '</strong><br>' + esc(row['status']) + '</li>'
overview += '</ul><p>Start with clothing, furniture and household essentials and the Workforce Center overlap. The full current records remain available below.</p></section>'
options = '<option value="overview">Overview</option>' + ''.join('<option value="'+esc(r['id'])+'">'+esc(r['label'])+'</option>' for r in data['items'])
page = '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Mesa program-title pilot</title><style>
*{box-sizing:border-box}body{margin:0;background:#f3f6f7;color:#1d2934;font:18px/1.5 system-ui,sans-serif;overflow-wrap:anywhere}header{background:#163f42;color:white;padding:28px 20px}header>div,main{max-width:980px;margin:auto}main{padding:20px}h1{font-size:1.85rem;margin:0}h2{font-size:1.45rem;margin:0 0 8px}h3{font-size:1.05rem;margin:18px 0 6px}h4{font-size:1rem;margin:12px 0 4px}p{margin:10px 0}section{background:white;border:1px solid #ccd6da;border-radius:10px;padding:22px;margin:18px 0}.status{font-weight:700;color:#654912}.comparison{display:grid;grid-template-columns:1fr 1fr;gap:12px}.comparison>div{background:#f1f6f5;border-left:4px solid #497d74;padding:0 12px 8px}.comparison p{font-weight:600}li{margin:9px 0}details{border-top:1px solid #d7dfe3;padding:12px 0;margin-top:12px}summary{cursor:pointer;font-weight:600}a{color:#125970}.original-text,pre{white-space:pre-wrap;font:inherit}pre{font-size:.85rem}.muted{font-size:.85rem;color:#52606d}.notice{padding:14px;background:#fff5d9;border-left:4px solid #b8862d}.source{padding:0 0 12px}.source-url{font-size:.8rem;word-break:break-all}.record-id{margin-top:16px}button,select{font:inherit;padding:10px 14px;border:1px solid #668082;border-radius:6px;cursor:pointer}button{background:#e4f2ed;color:#153f3c}button:focus-visible,select:focus-visible{outline:3px solid #bd791d;outline-offset:3px}dialog{width:min(560px,calc(100% - 24px));max-height:90vh;overflow:auto;border:1px solid #73878d;border-radius:12px;padding:24px;color:#1d2934}dialog::backdrop{background:#17292b99}label{display:block;margin:16px 0 6px}select{width:100%;min-width:0}input{width:20px;height:20px;vertical-align:middle}.actions{display:flex;gap:12px;justify-content:flex-end;margin-top:22px}#print-copy{display:none}[hidden]{display:none!important}@media(max-width:600px){.comparison{grid-template-columns:1fr}main{padding:12px}section{padding:16px}h1{font-size:1.5rem}}
@page{size:letter;margin:.65in}@media print{body{background:white;color:black;font:11pt/1.35 Arial,sans-serif}body>header,body>main,body>dialog{display:none}#print-copy{display:block}#print-copy>h1{font-size:17pt;margin-bottom:8px}section{border:0;margin:0;padding:0}h2{font-size:14pt;margin-top:14px}h3{font-size:11pt;margin:12px 0 4px}h4{font-size:11pt}p,li{margin:6px 0;widows:3;orphans:3}h2,h3,h4,summary{break-after:avoid}.comparison{display:block}.comparison>div{background:white;border-left:2px solid #aaa;padding:0 10px 4px;margin:8px 0}.original,.record-id{display:none}details{border:0}a{color:black}.source{break-inside:avoid}.source-url{font-size:9pt}.muted{font-size:9pt}.status{color:black}.decisions li{break-inside:avoid}}
</style></head><body><header><div><h1>Mesa program-title pilot</h1><p>Five A New Leaf entries · September 6, 2026</p><button id="print-report" type="button">Print report</button><p>Print the overview or one resource. Research notes and sources are optional.</p></div></header><main>
<p class="notice">For your review. The source HTML and all resource data remain unchanged. This page cannot edit or export an office package.</p>'''
page += overview + ''.join(parts)
page += '<section><h2>What this pilot taught us</h2><p>Titles can briefly list several meaningful service types. Scout assesses each from the patron’s side: useful help, eligible recipient, and a supported access route. The mixed entry retains an interview-clothing lead while furniture and household essentials remain unestablished. Clear labels must not hide uncertainty or make duplicate records look distinct. Checking the whole file exposed the shared Workforce Center. Comparing service schedules exposed a closing-time conflict.</p><p>Next, discuss these decisions and whether the labels work for missionaries. Research-method learning and adaptive category runs remain in the grand plan; this review is not phone-vetted evidence for automatic lesson activation.</p><details><summary>Scope and provenance</summary>'
page += paragraph(data['scope']) + bullets(data['limitations']) + paragraph('Source HTML SHA-256: ' + data['source']['sha256'])
page += '<p>Initial review: plain-language-v2 and maintenance-v2. Patron-usefulness follow-up: plain-language-v3 and maintenance-v3. Independent audits: 0. Human review decisions: 0. Exports: 0.</p></details></section></main>'
page += '<dialog id="print-options" aria-labelledby="print-title"><h2 id="print-title">What would you like to print?</h2><label for="print-choice">Choose a handout</label><select id="print-choice">' + options + '</select><p id="chosen-resource"></p><label id="notes-option" hidden><input type="checkbox" id="include-notes"> Include this resource’s research notes and sources</label><p>The working copy includes the title decision and all questions. Full original records remain on screen.</p><div class="actions"><button id="cancel-print">Cancel</button><button id="confirm-print">Print handout</button></div></dialog><div id="print-copy" aria-hidden="true"></div>'
page += '''<script>
const dialog=document.getElementById('print-options'),choice=document.getElementById('print-choice'),include=document.getElementById('include-notes'),copy=document.getElementById('print-copy'),printButton=document.getElementById('print-report');
function describe(){document.getElementById('notes-option').hidden=choice.value==='overview';document.getElementById('chosen-resource').textContent=choice.selectedOptions[0].textContent;}
function build(){copy.replaceChildren();let title=document.createElement('h1');title.textContent='Mesa program-title pilot';copy.append(title);let note=document.createElement('p');note.className='muted';note.textContent='September 6, 2026 · Codex review suggestions · no resource changes';copy.append(note);let part=document.getElementById(choice.value).cloneNode(true);part.removeAttribute('id');part.querySelectorAll('[id]').forEach(e=>e.removeAttribute('id'));part.querySelectorAll('.original,.record-id').forEach(e=>e.remove());if(!include.checked)part.querySelectorAll('.research').forEach(e=>e.remove());part.querySelectorAll('details').forEach(e=>e.open=true);copy.append(part);}
printButton.addEventListener('click',()=>{describe();dialog.showModal();});choice.addEventListener('change',describe);document.getElementById('cancel-print').addEventListener('click',()=>dialog.close());dialog.addEventListener('close',()=>printButton.focus());document.getElementById('confirm-print').addEventListener('click',()=>{dialog.close();build();window.print();});window.addEventListener('beforeprint',build);window.addEventListener('afterprint',()=>copy.replaceChildren());
</script></body></html>'''
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(page)
print(args.output)
