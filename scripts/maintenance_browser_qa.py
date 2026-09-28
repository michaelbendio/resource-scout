#!/usr/bin/env python3
"""Build explicitly synthetic review cases and test a disposable maintenance server."""
import argparse
import json
import sys
import threading
from copy import deepcopy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from resource_research_agent.improvement_packages import write_package,read_package
from resource_research_agent.scout_maintenance import MaintenanceWorkflow
from resource_research_agent.server import ResearchHTTPServer
from resource_research_agent.storage import ResearchStore
from tests.test_scout_improvement import fixture_package
from tests.test_scout_maintenance import result_for
from playwright.sync_api import sync_playwright


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    database=args.output/'synthetic.sqlite3'
    if database.exists():raise SystemExit('Choose a fresh QA output directory')
    store=ResearchStore(database);flow=MaintenanceWorkflow(store);data=fixture_package();data['officeName']='Demonstration TSO'
    statuses={'r1':'moved','r2':'paused','r3':'possibly-closed','r4':'inconclusive','r5':'current','r6':'renamed','r7':'reopened','r8':'identity'}
    names={'r1':'Community Pantry (example)','r2':'Evening Meals (example)','r3':'Weekend Food Boxes (example)','r4':'Home Delivery (example)','r5':'Neighborhood Pantry (example)','r6':'Food Cupboard (example)','r7':'Seasonal Meals (example)','r8':'Community Kitchen Referral (example)','unchecked':'Other Pantry (not checked)'}
    data['resources']=[{**deepcopy(data['resources'][0]),'id':rid,'name':names[rid],'address':'Old address'} for rid in [*statuses,'unchecked']]
    data['categories'].append({'id':'housing','label':'Housing','filters':[]})
    assets={'pdfs/guide.pdf':b'%PDF-1.4 Synthetic attachment; not a client handout'}
    source=write_package(data,assets);(args.output/'synthetic-source.zip').write_bytes(source)
    pid=flow.prepare(source,'Demonstration TSO',list(statuses),['food'],run_name='Synthetic maintenance examples — not real research',historical=True)['id']
    while a:=flow.next_assignment(pid):
        r=result_for(a,statuses.get(a['target']['id'],'moved'))
        if 'items' in r and a['scope']=='recheck':
            item=r['items'][0]
            summaries={'moved':'The pantry reports a new address. Services and eligibility appear unchanged.',
              'paused':'Evening meals are temporarily paused. Confirm when they will resume.',
              'possibly-closed':'An explicit notice says this food-box program has ended. The parent organization still operates.',
              'inconclusive':'The old website failed, and current operation could not be verified. A phone call is needed.',
              'current':'Current provider information supports continued service. No change is proposed.',
              'renamed':'The same program uses a new name. Confirm identity before updating its existing record.',
              'reopened':'Seasonal meals have resumed. Update the existing resource rather than creating a duplicate.',
              'identity':'The website describes referrals, while the office record may describe direct service. Confirm the program boundary.'}
            item['summary']=summaries[item['status']]
            if item['status'] in ('inconclusive','identity'):item['lastEvidenceOfOperationOn']=''
            if item['status']=='renamed':item['fields']={'name':'Community Food Cupboard (example)'}
            if item['status']=='reopened':item['fields']={'hours':'Tuesday evening meals have resumed. Call for current hours.'}
            if item['status']=='paused':item['fields']={'informationSections':{'programsAndServices':'Evening meals are temporarily paused.','eligibilityRequirements':'Open to community members.','howToBestConnect':'Call the provider to ask when meals will resume.','access':'Test County.','importantInformationToKnow':'Do not travel to this meal service until reopening is confirmed.'}}
        if a['target']['id']=='r1':
            if a['stage']=='audit:ChatGPT':r['findings']=[{'id':'intake','summary':'Confirm intake hours and whether group targeting changed.','severity':'material'}]
            if a['stage']=='reconcile':r['resolutions']=[{'findingId':'ChatGPT:intake','status':'needs-review','reason':'Human follow-up needed.'}]
        flow.submit(pid,a['stage'],r)
    flow.connect_latest(pid,flow.view(pid)['revision'],source,'Demonstration TSO')
    snapshot=flow.view(pid);(args.output/'review-snapshot.json').write_text(json.dumps(snapshot,indent=2))
    server=ResearchHTTPServer(('127.0.0.1',0),store,ROOT/'web');thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    base=f'http://127.0.0.1:{server.server_port}'
    try:
        with sync_playwright() as pw:
            browser=pw.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless=True)
            context=browser.new_context(viewport={'width':768,'height':1024},has_touch=True,accept_downloads=True)
            page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
            page.goto(base+'/maintenance');page.select_option('#projects',str(pid));page.wait_for_selector('[data-item-id="r1"]')
            assert '8 completed, 8 selected, 9 in office' in page.locator('#coverage').inner_text()
            assert '1 completed, 1 selected, 2 office categories' in page.locator('#coverage').inner_text()
            page.screenshot(path=str(args.output/'maintenance-ipad.png'),full_page=True)
            page.fill('#reviewer','Synthetic QA reviewer; not Michael')
            card=page.locator('[data-item-id="r1"]');card.locator('[data-field="address"]').select_option('proposed');card.locator('.decision').select_option('accept');card.locator('.note').fill('QA: confirmed the new address; classifications remain appropriate.')
            card.locator('.save').click();page.wait_for_function("document.getElementById('message').textContent.includes('Human resolution')")
            card.locator('[data-finding]').fill('Synthetic human follow-up: intake and targeting confirmed.');card.locator('.save').click();page.wait_for_function("state.items.find(r=>r.id==='r1').review?.decision==='accept'")
            closed=page.locator('[data-item-id="r3"]');closed.locator('.decision').select_option('retire');closed.locator('.note').fill('Synthetic QA: independently corroborated named-program closure notice; request office deletion review.');closed.locator('.save').click();page.wait_for_function("state.items.find(r=>r.id==='r3').review?.decision==='retire'")
            new=page.locator('[data-item-id="new-pantry"]');new.locator('.decision').select_option('accept');new.locator('.note').fill('Synthetic QA: distinct new program; service category and access reviewed.');new.locator('.save').click();page.wait_for_function("state.items.find(r=>r.id==='new-pantry').review?.decision==='accept'")
            # Use the iPad-style download path. Cancellation must not mark anything saved.
            page.evaluate('window.showSaveFilePicker=undefined')
            with page.expect_download() as download:page.click('#export')
            first=download.value;first.save_as(args.output/'reviewed.zip')
            page.wait_for_selector('#pending-save:not([hidden])');page.click('#cancel-saved')
            assert not any(r['saved'] for r in flow.view(pid)['items'])
            with page.expect_download() as download:page.click('#export')
            second=download.value;second.save_as(args.output/'retry.zip')
            assert (args.output/'reviewed.zip').read_bytes()==(args.output/'retry.zip').read_bytes()
            page.click('#confirm-saved');page.wait_for_function("state.requiresReconnection===true")
            out=read_package((args.output/'reviewed.zip').read_bytes())
            assert len(out['resources'])==10
            assert out['resources']['r1']['address']=='New address'
            assert out['resources']['r3']==data['resources'][2]
            assert out['data']['deletions']==[] and out['data']['deletionRequests'][0]['targetId']=='r3'
            assert out['assets']==assets and out['resources']['r1']['verifiedOn']==data['resources'][0]['verifiedOn']
            page.set_viewport_size({'width':390,'height':844})
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            page.screenshot(path=str(args.output/'maintenance-narrow.png'),full_page=True)
            assert not errors,errors
            (args.output/'verification.json').write_text(json.dumps({'syntheticOnly':True,'coverage':snapshot['coverage'],'browserErrors':errors,'downloadCancellationPreservedReview':True,'repeatBytesIdentical':True,'humanResolutionRequired':True,'retirementIsPendingRequestOnly':True,'exactPDFBytes':True,'humanVerificationPreserved':True,'viewportWidths':[768,390]},indent=2))
            browser.close()
        print('MAINTENANCE BROWSER QA PASSED: '+str(args.output))
    finally:server.shutdown();server.server_close();thread.join()

if __name__=='__main__':main()
