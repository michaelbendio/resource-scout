import subprocess
import unittest
from pathlib import Path


class ScoutPriorityUITests(unittest.TestCase):
    def test_open_for_curation_shows_admin_shell_and_preserves_pending_edits_gate(self):
        template = (Path(__file__).parents[1] / 'resource_research_agent/scout_review_template.html').read_text()
        note = template[template.index('function buildScoutPriorityNote('):template.index('function setupScoutPriorityEditor(')]
        shell = template[template.index('function prepareRenderShell('):template.index('function renderCategoryReminder(')]
        script = """
const assert = require('node:assert/strict');
const resource = {id:'one', name:'One', categories:['food']};
const data = {resources:[resource], categories:[{id:'food',label:'Food'}]};
const scoutReviewBaseData = null;
const SCOUT_PRIORITY_LABELS = {start:'Start here', specialized:'Important specialized help', additional:'Additional options'};
const getScoutPriority = () => ({tier:'start',reason:'Local intake'});
const isScoutReviewResourceCurated = () => false;
const elements = [];
const document = {createElement(tag) {
  const element = {tag, dataset:{}, children:[], setAttribute(){}, addEventListener(){}, appendChild(child){this.children.push(child)}};
  elements.push(element); return element;
}};
let view='category', isAdminVisible=false, editing=null, editorSnapshot='';
let allowCommit=true, selectedId=null, editorOpened=false;
const appView = {hidden:false, classList:{toggle(_,value){appView.hidden=value}}};
const adminView = {hidden:true, classList:{toggle(_,value){adminView.hidden=value}}};
const tabFavorites=null, tabAdmin={style:{}};
const updatePrintSelectionIndicator=()=>{}, syncSearchPanel=()=>{};
const commitPendingEditsIfChanged=()=>allowCommit;
const setAdminVisibility=value=>{isAdminVisible=value};
const safeRender=()=>prepareRenderShell();
const openAdminCategoryResourceById=id=>{selectedId=id;editorOpened=true};
""" + shell + note + """
buildScoutPriorityNote(resource,'food');
const button=elements.find(e=>e.tag==='button' && e.textContent==='Open for curation');
assert(button);
allowCommit=false;button.onclick();
assert.equal(view,'category');assert.equal(adminView.hidden,true);assert.equal(editorOpened,false);
allowCommit=true;button.onclick();
assert.equal(view,'admin');assert.equal(isAdminVisible,true);
assert.equal(adminView.hidden,false);assert.equal(appView.hidden,true);
assert.equal(selectedId,'one');assert.equal(editorOpened,true);
assert.equal(isScoutReviewResourceCurated('one'),false);
"""
        result = subprocess.run(['node','-e',script],capture_output=True,text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_personal_choices_preserve_ai_proposal_facts_and_approval(self):
        template=(Path(__file__).parents[1]/'resource_research_agent/scout_review_template.html').read_text()
        source=template[template.index('const SCOUT_PRIORITY_LABELS'):template.index('function buildScoutPriorityNote')]
        export=template[template.index('function buildResourcePackageData('):template.index('function buildScoutReviewSelectionPackageData(')]
        script="""
const assert=require('node:assert/strict');
const original={id:'one',name:'One',categories:['housing','food'],informationText:'Canonical facts',forGroups:['Seniors'],forGroupReview:{decision:'groups',contentKey:'unchanged'}};
let data={resources:[original],categories:[{id:'housing',label:'Housing'},{id:'food',label:'Food'}],forGroups:['Seniors'],changes:[],deletions:[],deletionRequests:[],categoryMigrations:[],scoutReviewPriorities:{assignments:[{resourceId:'one',categoryId:'housing',tier:'start',reason:'Local intake'},{resourceId:'one',categoryId:'food',tier:'additional',reason:'Extra option'}]}};
let scoutReviewState={curatedResourceIds:['one']};let durable=null,fail=false;
const cloneScoutReviewValue=x=>x===undefined?undefined:JSON.parse(JSON.stringify(x));
const isScoutReviewMode=()=>true,nowISO=()=> '2026-09-20';
const buildCompactScoutReviewState=(d,s)=>({...s,topLevelOverrides:{scoutReviewPriorityOverrides:cloneScoutReviewValue(d.scoutReviewPriorityOverrides)}});
const writeCompactScoutReviewState=s=>{if(fail)return false;durable=cloneScoutReviewValue(s);return true};
const alert=()=>{};
const processResourcePackageData=x=>({data:x});
const RESOURCE_PACKAGE_SCHEMA_VERSION=3,APP_VERSION='test',APP_CHANGE_LOG=[];
"""+source+export+"""
const originalJSON=JSON.stringify(data.resources),proposal=JSON.stringify(data.scoutReviewPriorities);
assert.equal(getScoutPriorityTier('one','housing'),'start');
assert.equal(getScoutPriorityTier('one','food'),'additional');
assert.equal(getScoutPriorityTier('new','food'),'unassigned');
assert.equal(changeScoutPriority('one','housing','specialized'),true);
assert.equal(getScoutPriorityTier('one','housing'),'specialized');
assert.equal(getScoutPriorityTier('one','food'),'additional');
assert.equal(durable.topLevelOverrides.scoutReviewPriorityOverrides.housing.one.tier,'specialized');
assert.deepEqual(scoutReviewState.curatedResourceIds,['one']);
assert.equal(JSON.stringify(data.resources),originalJSON);
assert.equal(JSON.stringify(data.scoutReviewPriorities),proposal);
fail=true;assert.equal(changeScoutPriority('one','housing','start'),false);
assert.equal(getScoutPriorityTier('one','housing'),'specialized');
fail=false;assert.equal(changeScoutPriority('one','housing',''),true);
assert.equal(getScoutPriorityTier('one','housing'),'start');
assert.equal(changeScoutPriority('one','unknown','start'),false);
assert.equal(changeScoutPriority('unknown','housing','start'),false);
assert.equal(changeScoutPriority('one','housing','approved'),false);
const packet=buildResourcePackageData(data);
assert(!Object.hasOwn(packet,'scoutReviewPriorities'));
assert(!Object.hasOwn(packet,'scoutReviewPriorityOverrides'));
assert.equal(JSON.stringify(packet.resources),originalJSON);
assert.equal(JSON.stringify(data.scoutReviewPriorities),proposal);
"""
        subprocess.run(['node','-e',script],check=True,capture_output=True,text=True)


if __name__=='__main__':unittest.main()
