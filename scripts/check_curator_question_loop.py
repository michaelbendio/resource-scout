#!/usr/bin/env python3
"""Verify real ZIP transfers between isolated review and office app instances.

Use disposable, seeded HTML copies only. Synthetic answers never reach an office.
"""
import argparse
import base64
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
from resource_research_agent.improvement_packages import read_package, write_package
from resource_research_agent.learning_evidence import EvidenceLedger
from resource_research_agent.storage import ResearchStore

EXPORT = """async()=>{
 let blob;
 await saveCurrentResourcePackage({kind:'file-handle',handle:{createWritable:async()=>({
   write:async b=>blob=b,close:async()=>{},abort:async()=>{}
 })}},{showSuccessToast:false});
 if(!blob) throw Error('Package was not saved');
 return await new Promise((resolve,reject)=>{const reader=new FileReader();
   reader.onload=()=>resolve(reader.result.split(',')[1]);reader.onerror=reject;
   reader.readAsDataURL(blob);});
}"""
IMPORT = """async encoded=>{
 const file=new File([Uint8Array.from(atob(encoded),c=>c.charCodeAt(0))],
   'synthetic-question-qa.zip',{type:'application/zip'});
 const warnings=[];
 await mergeImportPackage({target:{files:[file],remove(){}}},
   {silent:true,onWarnings:values=>warnings.push(...values)});
 return warnings;
}"""

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('review_html',type=Path)
    parser.add_argument('office_html',type=Path)
    parser.add_argument('--resource-id',default='provo-city-housing-authority')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    errors=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless=True)
        review=browser.new_page(viewport={'width':768,'height':1024})
        office=browser.new_page(viewport={'width':768,'height':1024})
        assert review.context != office.context
        for page,path in [(review,args.review_html),(office,args.office_html)]:
            page.on('pageerror',lambda e:errors.append(str(e)))
            page.on('dialog',lambda dialog:(errors.append(dialog.message),dialog.dismiss()))
            page.goto(path.resolve().as_uri())
            page.evaluate('async()=>await window.scoutPreviewAssetsReady')
        resource=lambda page:page.evaluate('id=>structuredClone(data.resources.find(r=>r.id===id))',args.resource_id)
        baseline=base64.b64decode(review.evaluate(EXPORT))
        before=resource(review);qid=before['openQuestions'][0]['id']
        review.evaluate("()=>{setAdminVisibility(true);adminTab='resources';setView('admin');}")
        review.locator('[data-resource-id="'+args.resource_id+'"]').click()
        review.get_by_role('button',name='Edit',exact=True).click()
        row=review.locator('[data-question-id="'+qid+'"]')
        answer='Synthetic QA: staff confirmed the intake route on September 8. Not a real provider contact.'
        row.locator('[data-question-note]').fill(answer)
        row.locator('[data-question-resolved]').check()
        review.locator('#res_update_description').fill('Synthetic QA resolution')
        review.locator('#res_done_btn').click()
        resolved=resource(review);expected=resolved['openQuestions']
        assert expected[0]['status']=='resolved' and expected[0]['resolution']==answer
        for key in ('question','explanation','source','id'):
            assert expected[0][key]==before['openQuestions'][0][key]
        assert expected[0]['history'][-1]['changedAt']
        exported=base64.b64decode(review.evaluate(EXPORT))
        assert read_package(exported)['resources'][args.resource_id]['openQuestions']==expected
        assert resource(office)['openQuestions']==before['openQuestions']
        for payload in [exported,exported,baseline]:
            assert not office.evaluate(IMPORT,base64.b64encode(payload).decode())
            assert resource(office)['openQuestions']==expected
        # A later contact edit made by an older editor cannot erase the answer.
        legacy=read_package(baseline);legacy_resource=legacy['resources'][args.resource_id]
        legacy_resource.pop('openQuestions');legacy_resource['phone']='Synthetic updated phone'
        legacy_resource['lastModified']='2099-01-01T00:00:00Z'
        payload=write_package(legacy['data'],legacy['assets'])
        assert not office.evaluate(IMPORT,base64.b64encode(payload).decode())
        assert resource(office)['phone']=='Synthetic updated phone'
        assert resource(office)['openQuestions']==expected
        office.reload();office.wait_for_function('typeof data === "object"')
        assert resource(office)['openQuestions']==expected
        office_payload=base64.b64decode(office.evaluate(EXPORT))
        final=read_package(office_payload)
        assert final['resources'][args.resource_id]['openQuestions']==expected
        assert final['assetHashes']==read_package(baseline)['assetHashes']
        assert not errors,errors
        browser.close()
    for name,payload in [('baseline.zip',baseline),('review-export.zip',exported),('office-export.zip',office_payload)]:
        (args.output/name).write_bytes(payload)
    ledger=EvidenceLedger(ResearchStore(args.output/'synthetic-evidence.sqlite3'))
    identity={'scope':'full','historical':True,'office_confirmation':'Explicit synthetic QA copies; no real office import.'}
    first=ledger.import_package('question-loop-qa','Synthetic QA',baseline,**identity)
    last=ledger.import_package('question-loop-qa','Synthetic QA',office_payload,**identity)
    repeated=ledger.import_package('question-loop-qa','Synthetic QA',office_payload,**identity)
    assert repeated['id']==last['id']
    comp=ledger.compare(first['id'],last['id'],reviewer='Synthetic QA',lineage_note='Isolated application ZIP roundtrip')
    report=ledger.report(comp['id'])
    question_events=[e for e in report['events'] if e['field']=='openQuestions']
    assert len(question_events)==1 and question_events[0]['level']=='observed-change'
    assert report['summary']['explicitFieldVerifications']==0
    assert report['summary']['activeLessons']==0
    (args.output/'scout-evidence.json').write_text(json.dumps(report,indent=2)+'\n')
    (args.output/'verification.json').write_text(json.dumps({
        'isolatedInstances':True,'ordinaryZipExportImport':True,'questionAndHistoryPreserved':True,
        'repeatImportPreserved':True,'olderOpenQuestionPreserved':True,'newerLegacyEditPreserved':True,
        'officeReloadPreserved':True,'pdfHashesPreserved':True,'scoutObservedDecision':True,
        'noAutomaticVerificationOrActiveLesson':True,'pageErrors':errors},indent=2)+'\n')
    print('Curator question ZIP loop passed, including Scout evidence intake.')

if __name__=='__main__':main()
