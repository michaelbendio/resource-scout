from __future__ import annotations

import subprocess
import unittest
from pathlib import Path


class ScoutReviewEditorActionsTests(unittest.TestCase):
    def test_done_and_curated_require_explicit_review_without_losing_edits(self) -> None:
        template = (Path(__file__).resolve().parents[1] / 'resource_research_agent/scout_review_template.html').read_text()
        names = (
            'snapshotResourceEditor', 'requireResourceEditorForGroupReview',
            'requireDraftForGroupReview', 'commitPendingEditsIfChanged',
            'closeResourceEditor', 'toggleCurrentResourceCurated',
            'refreshCurrentResourceCuratedButton', 'setScoutReviewResourceCurated',
            'getScoutReviewCuratedResourceIds', 'isScoutReviewResourceCurated',
            'populateResourceBrowseOptions',
        )
        # Function declarations in this template begin at column zero.
        functions = '\n'.join(template[template.index(f'function {name}('):].split('\n}\n', 1)[0] + '\n}' for name in names)
        script = r'''
const assert = require('node:assert/strict');
function element(tag='div') {
  const classes = new Set();
  return { tagName:tag.toUpperCase(), dataset:{}, children:[], textContent:'',
    attributes:{}, classList:{add(x){classes.add(x)}, toggle(x,on){on?classes.add(x):classes.delete(x)}, contains(x){return classes.has(x)}},
    setAttribute(k,v){this.attributes[k]=v}, removeAttribute(k){delete this.attributes[k]},
    append(...xs){this.children.push(...xs)}, appendChild(x){this.children.push(x)},
    set innerHTML(x){this.children=[]}, scrollIntoView(){this.scrolled=true}, focus(){this.focused=true} };
}
const checkbox=element(), button=element('button'), list=element();
const label=element(); label.textContent='I reviewed all applicable For groups.';
const elements={res_for_groups_reviewed:checkbox,res_for_groups_review_label:label,res_curated_btn:button};
const document={getElementById(id){return elements[id] || null},createElement:element};
let alerts=[], writes=0, renders=0, persistedIds=[];
function alert(message){alerts.push(message)}
let data={resources:[{id:'r1',name:'Test resource'}]};
let scoutReviewState={curatedResourceIds:[]};
function isScoutReviewMode(){return true}
function persistScoutReviewState(next){scoutReviewState=next;persistedIds=[...next.curatedResourceIds]}
let selectedResourceId='r1', editing={kind:'resource',idx:0}, adminResourceEditMode=true;
let pendingResourceCuratedToggle=false, newResourceIds=new Set(), adminShowVerifiedDates=false;
let draft={name:'Test resource',verifiedOn:'09/26',forGroupReviewConfirmed:false,updateDescription:'Test update'};
function resourceEditorDraft(){return draft}
function validateResourceName(){return {valid:true}}
function validateVerifiedOnInput(){return {valid:true}}
function showResourceNameWarning(){}
function showResourceVerifiedWarning(){}
let descriptionAllowed=true;
function confirmBlankUpdateDescription(){return descriptionAllowed}
function applyResourceDraft(idx,d){data.resources[idx]={...data.resources[idx],...d};setScoutReviewResourceCurated('r1',false)}
function persist(){writes++}
function addChangeEntry(){}
function createChangeEntry(){}
function setupScoutPriorityEditor(){}
function getAdminResourceBrowseList(){return data.resources}
function isValidMMYY(){return false}
function hasDeletionRequest(){return false}
function setResourceBrowseSelection(el,id){el.dataset.selectedResourceId=id}
function safeRenderAdmin(){renders++;populateResourceBrowseOptions(list,selectedResourceId)}
'''+functions+r'''
let editorSnapshot=snapshotResourceEditor();
// An unchanged resource closes without making the user certify a review.
closeResourceEditor();
assert.equal(adminResourceEditMode,false); assert.equal(editing,null);
assert.equal(writes,0); assert.equal(alerts.length,0);
function reopen(){editing={kind:'resource',idx:0};adminResourceEditMode=true;editorSnapshot=snapshotResourceEditor()}
reopen();draft.name='Edited resource';
closeResourceEditor();
assert.equal(adminResourceEditMode,true);assert.equal(writes,0);
assert.equal(draft.name,'Edited resource');assert.equal(data.resources[0].name,'Test resource');
assert.match(alerts.at(-1),/Before saving changes or marking this resource Curated/);
assert.match(alerts.at(-1),/I reviewed all applicable For groups/);
assert.equal(checkbox.focused,true);assert.equal(checkbox.scrolled,true);
toggleCurrentResourceCurated();
assert.equal(isScoutReviewResourceCurated('r1'),false);assert.equal(writes,0);
// Use the visible no-group label too, so the instruction matches either decision.
label.textContent='I reviewed the groups; none apply to this resource.';
toggleCurrentResourceCurated();assert.ok(alerts.at(-1).includes(label.textContent));
// The separate description prompt still blocks until explicitly resolved.
draft.forGroupReviewConfirmed=true;descriptionAllowed=false;
elements.blankUpdateDescriptionPrompt=element();toggleCurrentResourceCurated();
assert.equal(pendingResourceCuratedToggle,true);assert.equal(writes,0);
delete elements.blankUpdateDescriptionPrompt;descriptionAllowed=true;
toggleCurrentResourceCurated();
assert.equal(writes,1);assert.equal(data.resources[0].name,'Edited resource');
assert.deepEqual(persistedIds,['r1']);assert.equal(button.classList.contains('primary'),true);
assert.equal(button.attributes['aria-pressed'],'true');assert.equal(adminResourceEditMode,true);
closeResourceEditor();
assert.equal(adminResourceEditMode,false);assert.equal(writes,1);
assert.equal(list.children[0].children[0].textContent,'✓');
assert.equal(list.children[0].classList.contains('scout-review-resource-curated'),true);
// Clearing Curated also persists and removes its marker when returning to the list.
reopen();toggleCurrentResourceCurated();closeResourceEditor();
assert.deepEqual(persistedIds,[]);assert.equal(button.attributes['aria-pressed'],'false');
assert.equal(list.children[0].children[0].textContent,'');
// Done saves a confirmed edit and closes, without marking it Curated automatically.
reopen();draft.name='Another edit';closeResourceEditor();
assert.equal(data.resources[0].name,'Another edit');assert.equal(writes,2);
assert.equal(adminResourceEditMode,false);assert.deepEqual(persistedIds,[]);
'''
        result = subprocess.run(['node', '-e', script], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
