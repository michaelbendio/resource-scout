"""Disposable browser QA; synthetic curation never enters the delivery."""
import json,zipfile,sys
from pathlib import Path
from playwright.sync_api import sync_playwright
p=Path('output/discovery-pilot-20260909');p.mkdir(parents=True,exist_ok=True);d=Path(sys.argv[1]) if len(sys.argv)>1 else p/'delivery'
with zipfile.ZipFile(d/'resource-package.zip') as z: source=json.loads(z.read('tso-resources.json'))
with sync_playwright() as pw:
 b=pw.chromium.launch(channel='chrome',headless=True);ctx=b.new_context(viewport={'width':1024,'height':900});page=ctx.new_page();errors=[]
 page.on('pageerror',lambda e:errors.append(str(e)));page.on('dialog',lambda dialog:dialog.accept())
 page.goto((d/'autoWelfareSquareEmploymentPilot.html').resolve().as_uri());page.wait_for_function('typeof data!=="undefined" && data.resources.length===5')
 page.evaluate('assertInvariants("bounded discovery pilot QA")')
 assert page.evaluate('getScoutReviewCuratedResourceCount()')==0
 assert page.evaluate('data.categories[0].filters')==['Job Search','Staffing']
 assert page.evaluate('data.forGroups')==[]
 coverage=page.evaluate('data.scoutDiscoveryCoverage || null')
 assert coverage==source['scoutDiscoveryCoverage'], 'coverage lost during HTML import'
 page.evaluate("openCategoryFromCard('employment')")
 assert page.evaluate("getCategoryResources('employment').length")==5
 page.screenshot(path=str(p/'qa-category.png'),full_page=True)
 rid=next(r['id'] for r in source['resources'] if r.get('openQuestions'))
 page.evaluate("rid=>{setAdminVisibility(true);view='admin';adminTab='resources';selectedResourceId=rid;adminResourceEditMode=true;safeRender();editResource(data.resources.findIndex(r=>r.id===rid));}",rid)
 assert page.locator('#res_name').is_visible()
 assert page.locator('#res_open_questions').is_visible()
 page.screenshot(path=str(p/'qa-editor.png'),full_page=True)
 note=page.locator('[data-question-note]').first
 note.fill('SYNTHETIC QA ONLY: answer persistence check; no provider called.')
 page.locator('[data-question-resolved]').first.check()
 page.locator('#res_update_description').fill('SYNTHETIC QA ONLY: test a curator answer.')
 page.locator('#res_done_btn').click()
 saved=page.evaluate('id=>data.resources.find(r=>r.id===id)',rid)
 assert saved['openQuestions'][0]['status']=='resolved'
 exported=page.evaluate('''async rid=>{setScoutReviewResourceCurated(rid,true);let blob;await saveCurrentResourcePackage({kind:'file-handle',handle:{createWritable:async()=>({write:async b=>blob=b,close:async()=>{},abort:async()=>{}})}},{showSuccessToast:false});const zip=await JSZip.loadAsync(blob);return JSON.parse(await zip.file('tso-resources.json').async('string'));}''',rid)
 assert len(exported['resources'])==1
 assert exported.get('scoutDiscoveryCoverage')==source['scoutDiscoveryCoverage'],'coverage lost on save'
 assert exported['resources'][0]['openQuestions']==saved['openQuestions']
 merged=page.evaluate('({a,b})=>mergeResourcePackages(a,b).mergedData',{'a':source,'b':exported})
 assert len(merged['resources'])==5
 assert next(r for r in merged['resources'] if r['id']==rid)['openQuestions']==saved['openQuestions']
 assert merged.get('scoutDiscoveryCoverage')==source['scoutDiscoveryCoverage'],'coverage lost on merge'
 assert not errors, errors
 result={'fixture':'real pilot output with synthetic edits in disposable context only','resources':5,'categoryNavigation':True,'editor':True,'questionResolutionSaveAndMerge':True,'coverageRoundTrip':True,'humanApprovalsInDelivery':0,'runtimeErrors':errors}
 (p/'browser-result.json').write_text(json.dumps(result,indent=2)+'\n');b.close()
print('HTML, navigation, editor, coverage and question save/merge checks passed.')
