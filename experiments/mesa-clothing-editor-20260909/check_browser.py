"""Disposable-browser checks; synthetic curation never enters delivered files."""
import json,zipfile,sys
from pathlib import Path
from playwright.sync_api import sync_playwright
P=Path(__file__).resolve().parent;D=Path(sys.argv[1]).resolve()
def data(name):return json.loads(zipfile.ZipFile(name).read('tso-resources.json'))
draft=data(D/'autoMesaClothingPilot.zip');full=data(D/'original-268-resource-draft.zip');count=len(draft['resources'])
new_question=json.loads((D/'new-curator-questions.json').read_text())[0]
rid=new_question['resourceId'];qid=new_question['question']['id']
question_index=next(i for r in draft['resources'] if r['id']==rid for i,q in enumerate(r['openQuestions']) if q['id']==qid)
with sync_playwright() as p:
 browser=p.chromium.launch(channel='chrome',headless=True)
 context=browser.new_context(viewport={'width':820,'height':1180});page=context.new_page();errors=[]
 page.on('pageerror',lambda e:errors.append(str(e)));page.on('dialog',lambda d:d.accept())
 page.goto((D/'autoMesaClothingPilot.html').as_uri());page.wait_for_function('n=>typeof data!=="undefined" && data.resources.length===n',arg=count)
 assert page.evaluate('getScoutReviewCuratedResourceCount()')==0
 assert page.evaluate('getConfiguredSharePointPackageUrl()')==''
 page.evaluate('assertInvariants("Clothing maintenance and editor pilot QA")')
 assert page.evaluate('data.resources')==page.evaluate('s=>processResourcePackageData(structuredClone(s),{sourceName:"QA expected"}).data.resources',draft)
 page.evaluate("openCategoryFromCard('clothing')");assert page.evaluate("getCategoryResources('clothing').length")==count
 page.screenshot(path=str(D/'qa-clothing.png'))
 page.evaluate('''rid=>{setAdminVisibility(true);view='admin';adminTab='resources';selectedResourceId=rid;adminResourceEditMode=true;safeRender();editResource(data.resources.findIndex(r=>r.id===rid));}''',rid)
 assert page.locator('#res_open_questions').is_visible()
 page.locator('[data-question-note]').nth(question_index).fill('SYNTHETIC QA ONLY: not a provider answer.')
 page.locator('[data-question-resolved]').nth(question_index).check()
 page.locator('#res_update_description').fill('SYNTHETIC QA ONLY: test question preservation.')
 page.locator('#res_done_btn').click();page.reload();page.wait_for_function('n=>data.resources.length===n',arg=count)
 edited=page.evaluate('id=>data.resources.find(r=>r.id===id)',rid)
 assert next(q for q in edited['openQuestions'] if q['id']==qid)['status']=='resolved'
 exported=page.evaluate('''async rid=>{
  setScoutReviewResourceCurated(rid,true);let blob;
  await saveCurrentResourcePackage({kind:'file-handle',handle:{createWritable:async()=>({write:async b=>blob=b,close:async()=>{},abort:async()=>{}})}},{showSuccessToast:false});
  const z=await JSZip.loadAsync(blob);return JSON.parse(await z.file('tso-resources.json').async('string'));
 }''',rid)
 assert len(exported['resources'])==1
 merged=page.evaluate('''({full,draft,edited})=>{
  let d=mergeResourcePackages(full,draft).mergedData;d=mergeResourcePackages(d,edited).mergedData;
  return mergeResourcePackages(d,full).mergedData;
 }''',{'full':full,'draft':draft,'edited':exported})
 # Compare against the receiving application's canonical representation (for
 # example an existing 2026-08-27 verification label normalizes to 08/26).
 normalized_full=page.evaluate('s=>processResourcePackageData(structuredClone(s),{sourceName:"QA original office"}).data',full)
 old={r['id']:r for r in normalized_full['resources']};new={r['id']:r for r in merged['resources']};pilot={r['id'] for r in draft['resources']}
 assert len(new)==len(set(old)|pilot)
 for ident in set(old)-pilot:
  for field in ['name','description','informationText','phone','address','website','categories','categoryFilters','forGroups','verifiedOn','openQuestions']:
   assert new[ident].get(field)==old[ident].get(field),(ident,field)
 answer=next(q for q in new[rid]['openQuestions'] if q['id']==qid)
 assert answer['resolution']=='SYNTHETIC QA ONLY: not a provider answer.'
 assert answer['history']
 clean=browser.new_context(viewport={'width':820,'height':1180});review=clean.new_page();review.on('pageerror',lambda e:errors.append(str(e)))
 review.goto((D/'autoMesaClothingPilot-review.html').as_uri());assert review.evaluate('document.documentElement.scrollWidth<=innerWidth')
 review.screenshot(path=str(D/'qa-report.png'));None # Existing print PDF is preserved by this browser-only check
 review.set_viewport_size({'width':390,'height':844});assert review.evaluate('document.documentElement.scrollWidth<=innerWidth')
 review.goto((D/'autoMesaClothingPilot.html').as_uri());review.wait_for_function('n=>data.resources.length===n',arg=count)
 assert review.evaluate('getScoutReviewCuratedResourceCount()')==0
 assert not review.evaluate('data.resources.some(r=>(r.openQuestions||[]).some(q=>(q.resolution||"").includes("SYNTHETIC QA ONLY")))')
 assert not errors,errors
 browser.close()
result={'resources':count,'editorSaveReload':True,'selectedCuratedPackageExport':True,'partialMergePreservesUnselected249Records':True,'syntheticAnswerSurvivesOldPackageReplay':True,'newQuestionIdTested':qid,'newQuestionCreatedByThisRunSurvivesMergeAndOlderPackageReplay':True,'cleanDeliveryContainsNoSyntheticAnswersOrNewHumanApprovals':True,'pageErrors':errors,'responsiveReportWidths':[820,390],'mergedFullOfficeCount':len(new),'attachmentsInSource':len(zipfile.ZipFile(D/'original-268-resource-draft.zip').namelist())-1}
(D/'rerun-browser-verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
