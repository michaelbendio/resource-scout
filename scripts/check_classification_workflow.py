#!/usr/bin/env python3
"""Synthetic browser QA; never a claim of real research or Michael's approval."""
from __future__ import annotations
import argparse
import json
import sys
import threading
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from playwright.sync_api import sync_playwright
from tests.test_scout_improvement import fixture_package
from tests.test_scout_classification import classification_result
from resource_research_agent.improvement_packages import read_package,write_package
from resource_research_agent.scout_classification import ClassificationWorkflow
from resource_research_agent.server import ResearchHTTPServer
from resource_research_agent.storage import ResearchStore


def check(output, chrome, office_html):
    output.mkdir(parents=True,exist_ok=False)
    store=ResearchStore(output/'qa.sqlite3');flow=ClassificationWorkflow(store)
    data=fixture_package();data['forGroups'].append('Spanish speaking')
    assets={'pdfs/guide.pdf':b'%PDF-1.4 Synthetic QA attachment bytes'}
    source=output/'source.zip';source.write_bytes(write_package(data,assets))
    server=ResearchHTTPServer(('127.0.0.1',0),store,ROOT/'web')
    threading.Thread(target=server.serve_forever,daemon=True).start()
    errors=[]
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(executable_path=chrome,headless=True)
            context=browser.new_context(viewport={'width':1024,'height':1000},accept_downloads=True)
            page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
            base=f'http://127.0.0.1:{server.server_port}'
            page.goto(base+'/classifications')
            page.locator('#new-project summary').click();page.locator('#source').set_input_files(str(source))
            page.locator('#resource-selection input').first.wait_for();page.locator('#resource-selection input').first.check()
            page.locator('#historical').check();page.locator('#prepare').click()
            page.locator('#project-title').wait_for(state='visible')
            pid=int(page.url.split('project=')[1]);assert '/classifications?' in page.url
            assert not page.locator('[data-action=curated]').count()
            page.locator('#reviewer').fill('Synthetic browser QA; not Michael')
            page.locator('#definitions summary').click()
            for row in page.locator('[data-term]').all():
                row.locator('[data-definition]').fill('Synthetic QA definition; review this term based on explicit evidence.')
                row.locator('[data-approve]').check()
            page.locator('#save-definitions').click()
            page.wait_for_function("document.getElementById('message').textContent.startsWith('Definitions saved')")
            assert all(t['approvedBy']=='Synthetic browser QA; not Michael' for t in flow.view(pid)['guidance']['terms'])
            page.locator('#definitions summary').click()
            while a:=flow.next_assignment(pid):flow.submit(pid,a['stage'],classification_result(a))
            page.locator('#refresh').click();page.locator('[data-action=curated]').wait_for()
            assert page.locator('[data-action=curated]').is_disabled()
            page.locator('#latest').set_input_files(str(source))
            page.wait_for_function("!document.querySelector('[data-action=curated]').disabled")
            assert 'Spanish speaking' in page.locator('#resources').inner_text()
            page.locator('summary',has_text='Resource information and attachments').click()
            for a in page.locator('#resources a[href*="attachment?"]').all():
                r=context.request.get(base+a.get_attribute('href'));assert r.ok and r.body()==assets['pdfs/guide.pdf']
            page.locator('[data-action=curated]').click()
            page.wait_for_function("document.querySelector('[data-review-state]').textContent.includes('✓ Curated')")
            page.screenshot(path=str(output/'comparison-ipad.png'),full_page=True)
            page.locator('summary',has_text='Edit proposed classifications and reasons').click()
            edit=json.loads(page.locator('[data-edit]').input_value());edit['reviewNotes']=['Synthetic browser edit']
            page.locator('[data-edit]').fill(json.dumps(edit))
            page.wait_for_function('invalidating.size === 0')
            assert flow.view(pid)['resources'][0]['review'] is None
            assert page.locator('#export').is_disabled()
            page.locator('[data-action=edit]').click()
            page.wait_for_function("document.getElementById('message').textContent.startsWith('Edits saved')")
            page.locator('[data-action=curated]').click()
            page.wait_for_function("document.querySelector('[data-review-state]').textContent.includes('✓ Curated')")
            page.evaluate("()=>{window.showSaveFilePicker=async()=>{throw new DOMException('QA canceled','AbortError')}}")
            page.locator('#export').click();assert not flow.view(pid)['resources'][0]['packaged']
            page.evaluate('window.showSaveFilePicker=undefined')
            with page.expect_download() as download:page.locator('#export').click()
            saved=output/'updates.zip';download.value.save_as(saved)
            page.locator('#confirm-saved').wait_for(state='visible');assert not flow.view(pid)['resources'][0]['packaged']
            page.locator('#keep-review').click()
            page.evaluate('()=>{window.print=()=>{}}');page.locator('[data-action=print]').click()
            assert data['resources'][0]['description'] in page.locator('#print-content').inner_text()
            assert data['resources'][0]['informationText'] in page.locator('#print-content').inner_text()
            assert 'Synthetic decision' not in page.locator('#print-content').inner_text()
            for width in (768,390):
                page.set_viewport_size({'width':width,'height':1000})
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),f'Overflow at {width}'
                page.screenshot(path=str(output/f'review-{width}.png'),full_page=True)
            package=read_package(saved.read_bytes());assert package['assets']==assets
            office=context.new_page();office.goto(office_html.resolve().as_uri())
            merged=office.evaluate('''([current,incoming])=>{
              const old=processResourcePackageData(current,{sourceName:'Synthetic current'}).data;
              const next=processResourcePackageData(incoming,{sourceName:'Synthetic update'}).data;
              return mergeResourcePackages(old,next);
            }''',[data,package['data']])['mergedData']
            by_id={r['id']:r for r in merged['resources']}
            assert len(by_id)==2
            for field in ('categories','categoryFilters','forGroups','description','informationText','phone','verifiedOn','pdfs'):
                assert by_id['r1'][field]==package['resources']['r1'][field],field
            assert by_id['r2']['forGroups']==data['resources'][1]['forGroups']
            (output/'office-merge.json').write_text(json.dumps(merged,indent=2))
            with page.expect_download() as download:page.locator('#export').click()
            download.value.save_as(output/'retry.zip')
            assert saved.read_bytes()==(output/'retry.zip').read_bytes()
            page.locator('#confirm-saved').click()
            page.wait_for_function("document.getElementById('message').textContent.startsWith('Saved package recorded')")
            assert flow.view(pid)['resources'][0]['packaged']
            assert not errors,errors
            browser.close()
    finally:server.shutdown();server.server_close()
    (output/'result.json').write_text(json.dumps({'passed':True,'syntheticOnly':True,'browserErrors':errors,'officeHtml':str(office_html)},indent=2))
    print('Classification browser and office-merge QA passed:',output)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--chrome',default='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
    parser.add_argument('--office-html',type=Path,default=Path('/Users/michaelbendio/resource-assistant/provo.html'))
    a=parser.parse_args();check(a.output,a.chrome,a.office_html)
