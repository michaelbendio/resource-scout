#!/usr/bin/env python3
"""Synthetic migration UI and actual office-reader compatibility QA."""
from __future__ import annotations
import argparse
import json
import sys
import threading
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from playwright.sync_api import sync_playwright
from tests.test_taxonomy_review import TaxonomyTests
from resource_research_agent.improvement_packages import read_package
from resource_research_agent.server import ResearchHTTPServer


def check(output, chrome, office_html):
    output.mkdir(parents=True,exist_ok=False)
    qa=TaxonomyTests();qa.setUp();qa.select_all();qa.finish();plan=qa.plan()
    server=ResearchHTTPServer(('127.0.0.1',0),qa.store,ROOT/'web')
    threading.Thread(target=server.serve_forever,daemon=True).start();errors=[]
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(executable_path=chrome,headless=True)
            context=browser.new_context(viewport={'width':1024,'height':1000},accept_downloads=True)
            page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
            page.goto(f'http://127.0.0.1:{server.server_port}/taxonomy-review?project={qa.pid}')
            page.locator('.migration-plan').wait_for();page.locator('#reviewer').fill('Synthetic browser QA; not Michael')
            assert page.locator('[data-export]').is_disabled()
            group=page.locator('.group-card').filter(has=page.locator('summary',has_text='Rare group ·'))
            group.locator('summary').first.click();form=group.locator('form')
            form.locator('[name=use]').fill('Find an essential specialist.')
            form.locator('[name=reason]').fill('A single documented member is useful; do not delete by count.')
            form.locator('[name=member0]').fill('Keep supported membership.')
            form.locator('button').click();page.wait_for_function("document.querySelector('#report').textContent.includes('Saved recommendation: retain')")
            for i in range(3):
                row=page.locator('.mapping').nth(i);row.locator('summary').first.click()
                row.locator('[name=note]').fill('QA supported service and group mapping; no actual provider claim.')
                row.locator('[name=type0]').fill('Retire old Type; preserve Food / Pantries.')
                row.locator('form button').click()
                page.wait_for_function('(n)=>document.querySelectorAll(".mapping > summary")[n].textContent.includes("mapping reviewed")',arg=i)
            approve=page.locator('form[data-kind=approve]');approve.locator('[name=note]').fill('QA checked all three resources.')
            approve.locator('button').click();page.wait_for_function('!document.querySelector("[data-export]").disabled')
            # Unsaved edits cannot export the previous approved state.
            row=page.locator('.mapping').first;row.locator('summary').first.click();row.locator('[name=note]').fill('Unsaved alternative')
            page.locator('[data-export]').click();page.wait_for_function("document.querySelector('#message').textContent.includes('edited review')")
            assert not qa.review.view(qa.pid)['plans'][0]['saved']
            row.locator('form button').click();page.wait_for_function('document.querySelector("[data-export]").disabled')
            assert qa.review.view(qa.pid)['plans'][0]['approval'] is None
            approve=page.locator('form[data-kind=approve]');approve.locator('[name=note]').fill('QA rechecked changed mapping.');approve.locator('button').click()
            page.wait_for_function('!document.querySelector("[data-export]").disabled')
            page.evaluate("()=>{window.showSaveFilePicker=async()=>{throw new DOMException('QA canceled','AbortError')}}")
            page.locator('[data-export]').click();page.wait_for_function("document.querySelector('#message').textContent.includes('cancelled')")
            assert all(not r['packaged'] for r in qa.flow.view(qa.pid)['resources'])
            page.evaluate('window.showSaveFilePicker=undefined')
            with page.expect_download() as dl:page.locator('[data-export]').click()
            saved=output/'migration.zip';dl.value.save_as(saved)
            page.locator('#confirm-saved').wait_for(state='visible')
            assert all(not r['packaged'] for r in qa.flow.view(qa.pid)['resources'])
            page.locator('#keep-review').click()
            for width in (1024,768,390):
                page.set_viewport_size({'width':width,'height':1000})
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),f'Overflow at {width}'
                page.screenshot(path=str(output/f'review-{width}.png'),full_page=True)
            package=read_package(saved.read_bytes());assert package['assets']==qa.assets
            office=context.new_page();office.goto(office_html.resolve().as_uri())
            merged=office.evaluate('''([current,incoming])=>{
              const old=processResourcePackageData(current,{sourceName:'Synthetic current'}).data;
              const next=processResourcePackageData(incoming,{sourceName:'Synthetic migration'}).data;
              const merged=mergeResourcePackages(old,next).mergedData;
              // Reopen and merge an older package again: retired labels must not return.
              return mergeResourcePackages(processResourcePackageData(merged,{sourceName:'Synthetic reopened'}).data,old).mergedData;
            }''',[qa.data,package['data']])
            assert not {'seniors','old-seniors','older-seniors'} & {c['id'] for c in merged['categories']}
            assert all(not m.get('toId') for m in merged['categoryMigrations'] if m['fromId'] in {'seniors','old-seniors','older-seniors'})
            byid={r['id']:r for r in merged['resources']};assert set(byid)=={'r1','r2','r3'}
            for rid,r in byid.items():
                assert 'seniors' not in r['categories'] and 'seniors' not in r['categoryFilters']
                for field in ('categories','categoryFilters','forGroups','description','informationText','phone','verifiedOn','pdfs'):
                    assert r[field]==package['resources'][rid][field],(rid,field,r[field])
            (output/'office-merge.json').write_text(json.dumps(merged,indent=2))
            # A captured compatibility limitation, not a successful alias migration.
            # Build this unsupported case in disposable browser memory only.
            alias_issue=office.evaluate('''([current,incoming])=>{
              current.categoryMigrations=[{fromId:'old-seniors',toId:'seniors'}];
              incoming.categoryMigrations.push({fromId:'old-seniors'});
              const first=mergeResourcePackages(current,incoming).mergedData;
              try{mergeResourcePackages(first,current);return null;}
              catch(e){return {message:e.message,details:e.details};}
            }''',[qa.data,package['data']])
            assert alias_issue and 'unknown target' in str(alias_issue),alias_issue
            (output/'blocked-alias-reader-case.json').write_text(json.dumps(alias_issue,indent=2))
            with page.expect_download() as dl:page.locator('[data-export]').click()
            dl.value.save_as(output/'retry.zip');assert saved.read_bytes()==(output/'retry.zip').read_bytes()
            page.locator('#confirm-saved').click();page.wait_for_function("document.querySelector('.migration-plan summary').textContent.includes('saved')")
            assert all(r['packaged'] for r in qa.flow.view(qa.pid)['resources'])
            assert not errors,errors
            browser.close()
    finally:server.shutdown();server.server_close();qa.doCleanups()
    (output/'result.json').write_text(json.dumps({'passed':True,'syntheticOnly':True,'browserErrors':errors,'officeHtml':str(office_html)},indent=2))
    print('Taxonomy browser and actual office merge QA passed:',output)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--chrome',default='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
    parser.add_argument('--office-html',type=Path,default=Path('/Users/michaelbendio/resource-assistant/provo.html'))
    a=parser.parse_args();check(a.output,a.chrome,a.office_html)
