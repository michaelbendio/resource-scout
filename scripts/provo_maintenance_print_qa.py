#!/usr/bin/env python3
"""Check that printing creates small handouts without changing the full report."""
import argparse,json,subprocess
from pathlib import Path
from playwright.sync_api import sync_playwright
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('report',type=Path)
parser.add_argument('output',type=Path)
args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
results=[]
with sync_playwright() as w:
 browser=w.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless=True)
 page=browser.new_page(viewport={'width':768,'height':1024});errors=[]
 page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto(args.report.resolve().as_uri())
 page.locator('main details').first.locator('summary').click()
 before=page.locator('main details').evaluate_all('(els)=>els.map(e=>e.open)')
 original=page.locator('main').inner_html()
 page.get_by_role('button',name='Print report',exact=True).click()
 assert page.locator('#print-options').is_visible()
 page.get_by_role('button',name='Cancel',exact=True).click()
 assert not page.locator('#print-options').is_visible()
 assert page.locator('main').inner_html()==original
 assert page.locator('#print-report').evaluate('(el)=>el===document.activeElement')
 ids=['overview','casfb','facc','pantry-to-porch-utah-county']
 for selected,audit in [(x,False) for x in ids]+[(x,True) for x in ids[1:]]:
  page.get_by_role('button',name='Print report',exact=True).click()
  page.locator('#print-choice').select_option(selected)
  assert page.locator('#audit-option').is_hidden()==(selected=='overview')
  if selected!='overview':page.locator('#include-audit').set_checked(audit)
  # Exercise the button without opening the native print sheet, then render
  # through Chromium's print lifecycle (including beforeprint/afterprint).
  page.evaluate('window.print = () => { window.printRequested = (window.printRequested || 0) + 1; }')
  page.get_by_role('button',name='Print handout',exact=True).click()
  assert not page.locator('#print-options').is_visible()
  assert page.locator('#print-copy .original-notes').count()==0
  assert page.locator('#print-copy .audit').count()==({'casfb':10,'facc':10,'pantry-to-porch-utah-county':11}[selected] if audit else 0)
  pdf=args.output/(selected+('-audit' if audit else '')+'.pdf')
  page.pdf(path=str(pdf),prefer_css_page_size=True,display_header_footer=True,header_template='<span></span>',footer_template='<div style="font-size:9px;width:100%;text-align:center">Scout maintenance · <span class="pageNumber"></span> / <span class="totalPages"></span></div>')
  text=subprocess.check_output(['pdftotext','-layout',str(pdf),'-']).decode()
  pages=[p for p in text.split('\f') if p.strip()]
  assert all(len(p.strip())>100 for p in pages),'Blank page'
  assert text.count('Auditor finding:')==({'casfb':10,'facc':10,'pantry-to-porch-utah-county':11}[selected] if audit else 0)
  assert text.count('Scout decision')==({'casfb':10,'facc':10,'pantry-to-porch-utah-county':11}[selected] if audit else 0)
  assert text.count('Questions to settle')==(0 if selected=='overview' else 1)
  if selected=='overview':assert len(pages)==1
  elif not audit:assert len(pages)<=2,(selected,len(pages))
  if selected=='casfb':assert 'Other unresolved local details' in text
  assert page.locator('main').inner_html()==original
  assert page.locator('main details').evaluate_all('(els)=>els.map(e=>e.open)')==before
  assert page.locator('main .audit').count()==31
  results.append({'handout':selected,'audit':audit,'pages':len(pages)})
 for width,height in [(768,1024),(390,844)]:
  page.set_viewport_size({'width':width,'height':height})
  page.get_by_role('button',name='Print report',exact=True).click()
  assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
  assert page.locator('#print-options').evaluate('(el)=>el.scrollWidth<=el.clientWidth')
  page.screenshot(path=str(args.output/f'print-choices-{width}.png'))
  page.keyboard.press('Escape');assert not page.locator('#print-options').is_visible()
 assert not errors
 browser.close()
verification={'handouts':results,'fullReportUnchanged':True,'cancelAndEscapeCloseDialog':True,'noScreenOverflow':True,'pageErrors':errors}
(args.output/'verification.json').write_text(json.dumps(verification,indent=2));print(json.dumps(verification))
