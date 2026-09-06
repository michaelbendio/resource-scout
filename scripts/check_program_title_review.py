#!/usr/bin/env python3
"""Check pilot provenance, unchanged originals, responsive UI and print choices."""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from playwright.sync_api import sync_playwright

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('review',type=Path)
parser.add_argument('source',type=Path)
parser.add_argument('report',type=Path)
parser.add_argument('output',type=Path)
a=parser.parse_args();a.output.mkdir(parents=True,exist_ok=True)
d=json.loads(a.review.read_text())
assert hashlib.sha256(a.source.read_bytes()).hexdigest()==d['source']['sha256']
seed=json.loads(re.search(r'<script id="seed-data" type="application/json">(.*?)</script>',a.source.read_text(),re.S).group(1))
originals={r['id']:r for r in seed['resources']}
assert len(originals)==d['source']['resourceCount']==333
assert len(d['items'])==5
assert len({r['id'] for r in d['items']})==5
assert sum(r['status']=='Title proposed' for r in d['items'])==3
assert sum(r['status'].startswith('Conditional') for r in d['items'])==1
assert sum(r['proposedName'] is None for r in d['items'])==1
for row in d['items']:assert row['current']==originals[row['id']]
for row in d['relatedResources']:assert row==originals[row['id']]
assert d['independentAudits']==[] and d['humanReviewDecisions']==d['exports']==0
results=[];errors=[]
with sync_playwright() as pw:
 browser=pw.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless=True)
 page=browser.new_page(viewport={'width':768,'height':1024});page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto(a.report.resolve().as_uri())
 assert page.locator('section.resource').count()==5
 page.locator('details.original').first.locator('summary').click()
 assert page.locator('details.original').first.evaluate('(el)=>el.open')
 main=page.locator('main').inner_html()
 page.locator('#print-report').click();page.locator('#cancel-print').click()
 assert not page.locator('#print-options').is_visible()
 assert page.locator('#print-report').evaluate('(el)=>el===document.activeElement')
 ids=['overview']+[r['id'] for r in d['items']]
 for i,selected in enumerate(ids):
  for notes in ([False] if selected=='overview' else [False,True]):
   page.locator('#print-report').click();page.locator('#print-choice').select_option(selected)
   assert page.locator('#notes-option').is_hidden()==(selected=='overview')
   if selected!='overview':page.locator('#include-notes').set_checked(notes)
   page.evaluate('() => {window.printCalls=0;window.print=()=>{window.printCalls++};}')
   page.locator('#confirm-print').click();assert page.evaluate('window.printCalls')==1
   assert page.locator('#print-copy .original').count()==0
   assert page.locator('#print-copy .research').count()==int(notes)
   label=f'{i}-'+('research' if notes else 'working')
   pdf=a.output/(label+'.pdf')
   page.pdf(path=str(pdf),prefer_css_page_size=True,display_header_footer=True,header_template='<span></span>',footer_template='<div style="font-size:8px;width:100%;text-align:center">Mesa title pilot · <span class="pageNumber"></span>/<span class="totalPages"></span></div>')
   text=subprocess.check_output(['pdftotext','-layout',str(pdf),'-'],text=True)
   pages=[p for p in text.split('\f') if p.strip()]
   assert all(len(p.strip())>100 for p in pages),label
   assert len(pages)<=(1 if selected=='overview' else 3 if notes else 2),(label,len(pages))
   assert text.count('Questions to settle')==int(selected!='overview')
   if selected!='overview':
    row=next(r for r in d['items'] if r['id']==selected)
    flattened=' '.join(text.split())
    for q in row['questions']:assert ' '.join(q.split()) in flattened,q
   assert page.locator('main').inner_html()==main
   results.append({'id':selected,'notes':notes,'pages':len(pages),'proof':pdf.name})
 for width,height in [(390,844),(768,1024)]:
  page.set_viewport_size({'width':width,'height':height})
  page.evaluate('window.scrollTo(0,0)')
  assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
  page.screenshot(path=str(a.output/f'screen-{width}.png'))
  page.locator('#print-report').click()
  assert page.locator('#print-options').evaluate('(el)=>el.scrollWidth<=el.clientWidth')
  page.screenshot(path=str(a.output/f'print-{width}.png'))
  page.keyboard.press('Escape');assert not page.locator('#print-options').is_visible()
 assert not errors,errors
 browser.close()
verification={'sourceUnchanged':True,'originalRecordsExact':True,'screenUnchangedAfterPrint':True,'narrowScreenChecks':[390,768],'cancelAndEscape':True,'pageErrors':errors,'handouts':results}
(a.output/'verification.json').write_text(json.dumps(verification,indent=2)+'\n')
print(json.dumps(verification,indent=2))
