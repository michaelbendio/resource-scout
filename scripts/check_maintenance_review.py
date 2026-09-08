#!/usr/bin/env python3
"""Inspect a generated review in disposable browser storage; never mark real work curated."""
import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('review',type=Path)
    parser.add_argument('summary',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();args.output.mkdir(exist_ok=True,parents=True)
    errors=[];checks={}
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless=True)
        page=browser.new_page(viewport={'width':768,'height':1024})
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.goto(args.review.resolve().as_uri())
        page.evaluate('async()=>await window.scoutPreviewAssetsReady')
        checks['resources']=page.evaluate('data.resources.length')
        assert page.evaluate('getScoutReviewCuratedResourceCount()')==0
        checks['initialCuratedCount']=0
        page.evaluate("()=>{setAdminVisibility(true);adminTab='resources';setView('admin');}")
        # All three actual editor tabs are available and operable.
        page.get_by_role('button',name='For',exact=True).click()
        assert page.evaluate("editing && editing.kind==='forGroups'")
        page.get_by_role('button',name='Resources',exact=True).click()
        page.get_by_role('button',name='Categories',exact=True).last.click()
        page.get_by_role('button',name='Resources',exact=True).click()
        checks['threeEditors']=True
        rid=page.evaluate("data.resources.find(r=>(r.openQuestions||[]).some(q=>q.status==='open')).id")
        page.locator('[data-resource-id="'+rid+'"]').click()
        page.get_by_role('button',name='Edit',exact=True).click()
        assert page.get_by_text('What did you find out?',exact=True).count()>0
        question=page.evaluate('id=>data.resources.find(r=>r.id===id).openQuestions[0].question',rid)
        page.screenshot(path=str(args.output/'resource-editor.png'),full_page=True)
        page.evaluate('printCurrentResource()')
        preview=page.locator('#printContent')
        assert preview.count()==1
        assert question not in preview.inner_text()
        assert 'What did you find out?' not in preview.inner_text()
        checks['curatorQuestionsExcludedFromHandout']=True
        page.screenshot(path=str(args.output/'patron-preview.png'),full_page=True)
        # Embedded PDFs survive reopening, and a replacement takes precedence.
        pdf=page.evaluate('data.resources.flatMap(r=>r.pdfs||[])[0]||null')
        if pdf:
            old=page.evaluate('async p=>(await getPDF(p)).size',pdf['path'])
            assert old>0
            page.evaluate("async p=>await savePDF(p,new Blob(['synthetic replacement PDF'],{type:'application/pdf'}))",pdf['path'])
            page.reload();page.evaluate('async()=>await window.scoutPreviewAssetsReady')
            assert page.evaluate('async p=>(await getPDF(p)).text()',pdf['path'])=='synthetic replacement PDF'
            checks['curatorPdfReplacementSurvivesReload']=True
        for width in [768,390]:
            page.set_viewport_size({'width':width,'height':1024})
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),width
        checks['mobileWidthFits']=True
        overview=browser.new_page(viewport={'width':768,'height':1024})
        overview.on('pageerror',lambda error:errors.append(str(error)))
        overview.goto(args.summary.resolve().as_uri())
        assert overview.locator('article').count()==checks['resources']
        assert overview.locator('article strong').count()>0
        overview.screenshot(path=str(args.output/'overview.png'),full_page=False)
        overview.emulate_media(media='print')
        assert overview.locator('article:visible').count()==0
        overview.pdf(path=str(args.output/'overview-print.pdf'),format='Letter',print_background=True)
        overview.evaluate("()=>{document.body.classList.add('print-one');document.querySelector('article').classList.add('print-target')}")
        assert overview.locator('article:visible').count()==1
        assert overview.locator('section:visible').count()==0
        checks['overviewAndSingleResourcePrinting']=True
        browser.close()
    assert not errors,errors
    checks['pageErrors']=errors
    (args.output/'verification.json').write_text(json.dumps(checks,indent=2)+'\n')


if __name__=='__main__':main()
