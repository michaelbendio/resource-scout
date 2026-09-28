"""Disposable-browser QA: actual editor, package export, merge and old-package replay."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
P=Path(__file__).resolve().parent;ROOT=P.parents[1];OUT=ROOT/'output/mesa-maintenance-editor-20260909'
draft=json.loads((P/'draft-resources.json').read_text())
full=json.loads((ROOT/'output/autoMesa-editorial-20260909/tso-resources.json').read_text())
rid='73dfadc219f93cdde3c2e07d3e1045b4'
with sync_playwright() as p:
 browser=p.chromium.launch(channel='chrome',headless=True)
 context=browser.new_context(viewport={'width':820,'height':1180})
 page=context.new_page();errors=[]
 page.on('pageerror',lambda e:errors.append(str(e)))
 page.on('dialog',lambda d:d.accept())
 page.goto((OUT/'autoMesaMaintenancePilot.html').as_uri())
 page.wait_for_function('typeof data!=="undefined" && data.resources.length===12')
 assert page.evaluate('getScoutReviewCuratedResourceCount()')==0
 assert page.evaluate('getConfiguredSharePointPackageUrl()')==''
 assert page.evaluate('data.resources')==page.evaluate('s=>processResourcePackageData(structuredClone(s),{sourceName:"QA expected"}).data.resources',draft)
 page.evaluate('assertInvariants("maintenance pilot QA")')
 page.evaluate("openCategoryFromCard('clothing')")
 assert page.evaluate("getCategoryResources('clothing').length")>=4
 page.evaluate('''rid=>{setAdminVisibility(true);view='admin';adminTab='resources';selectedResourceId=rid;adminResourceEditMode=true;safeRender();editResource(data.resources.findIndex(r=>r.id===rid));}''',rid)
 assert page.locator('#res_open_questions').is_visible()
 assert page.locator('[data-question-note]').count()==1
 page.screenshot(path=str(OUT/'qa-resource-editor.png'))
 page.locator('[data-question-note]').fill('SYNTHETIC QA ONLY: not a provider answer.')
 page.locator('[data-question-resolved]').check()
 page.locator('#res_update_description').fill('SYNTHETIC QA ONLY: exercise question preservation.')
 page.locator('#res_done_btn').click()
 page.reload();page.wait_for_function('data.resources.length===12')
 saved=page.evaluate('id=>data.resources.find(r=>r.id===id)',rid)
 assert saved['openQuestions'][0]['status']=='resolved'
 assert saved['openQuestions'][0]['history']
 exported=page.evaluate('''async rid=>{
  setScoutReviewResourceCurated(rid,true);
  let blob;await saveCurrentResourcePackage({kind:'file-handle',handle:{createWritable:async()=>({write:async b=>blob=b,close:async()=>{},abort:async()=>{}})}},{showSuccessToast:false});
  const z=await JSZip.loadAsync(blob);return JSON.parse(await z.file('tso-resources.json').async('string'));
 }''',rid)
 assert len(exported['resources'])==1
 office=context.new_page();office.on('pageerror',lambda e:errors.append(str(e)))
 office.on('dialog',lambda d:d.accept())
 office.goto((ROOT/'output/meeting-final-qa-20260909/mesa-import-demo.html').as_uri())
 office.wait_for_function('typeof mergeResourcePackages==="function"')
 merged=office.evaluate('''({full,draft,edited})=>{
  let d=mergeResourcePackages(full,draft).mergedData;
  d=mergeResourcePackages(d,edited).mergedData;
  return mergeResourcePackages(d,full).mergedData;
 }''',{'full':full,'draft':draft,'edited':exported})
 assert len(merged['resources'])==268
 selected=next(r for r in merged['resources'] if r['id']==rid)
 assert selected['openQuestions'][0]['status']=='resolved'
 assert selected['openQuestions'][0]['resolution']=='SYNTHETIC QA ONLY: not a provider answer.'
 assert selected['openQuestions'][0]['history']
 worker=next(r for r in merged['resources'] if r['id']=='08497e5f8c33c372d57430bc722bb639')
 assert worker['informationText']==next(r for r in draft['resources'] if r['id']==worker['id'])['informationText']
 assert len(worker['openQuestions'])==2
 clean=browser.new_context(viewport={'width':820,'height':1180})
 report=clean.new_page();report.goto((OUT/'mesa-maintenance-editor-review.html').as_uri())
 assert report.locator('details').count()==3
 report.locator('summary').first.click()
 assert report.locator('details[open] strong').count()>0
 assert report.evaluate('document.documentElement.scrollWidth<=innerWidth')
 report.screenshot(path=str(OUT/'qa-review.png'))
 report.pdf(path=str(OUT/'mesa-maintenance-editor-review.pdf'),format='Letter',print_background=True)
 report.set_viewport_size({'width':390,'height':844})
 assert report.evaluate('document.documentElement.scrollWidth<=innerWidth')
 report.goto((OUT/'autoMesaMaintenancePilot.html').as_uri())
 report.wait_for_function('data.resources.length===12')
 assert report.evaluate('getScoutReviewCuratedResourceCount()')==0
 assert not report.evaluate('data.resources.some(r=>(r.openQuestions||[]).some(q=>q.status==="resolved"))')
 assert not errors,errors
 browser.close()
(P/'browser-verification.json').write_text(json.dumps({'actualEditorSaveReload':True,'curatedSelectionExport':True,'partialMergeRetains268Resources':True,'newQuestionsAndEditsSurviveOlderPackageMerge':True,'syntheticAnswerSurvivesMerge':True,'cleanDraftHasNoHumanApprovals':True,'reviewExactChangesExpandable':True,'horizontalOverflowAt820And390':False,'pageErrors':errors,'syntheticTestsNeverWrittenToDelivery':True},indent=2)+'\n')
print('Passed browser editor/save/export, full-office merge plus older package, question history, clean draft and responsive review.')
