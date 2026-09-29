"""Exercise the visible next step and location-specific save action."""
import json
import shutil
import subprocess
import unittest
from pathlib import Path


@unittest.skipUnless(shutil.which("node"), "Node required for UI behavior test")
class ScoutProgressUITests(unittest.TestCase):
    def test_waiting_active_paused_and_ready_states(self):
        source = (Path(__file__).resolve().parents[1] / "web/app.js").read_text()
        labels = source[source.index("function friendlyProgressPhase("):source.index("function researchStatusLabel(")]
        render = source[source.index("function renderScoutProgress("):source.index("async function loadScoutProgress(")]
        script = """
const assert = require('node:assert/strict');
const state = {};
const nodes = new Map();
const document = {querySelector(selector) {
  if (!nodes.has(selector)) nodes.set(selector, {hidden: true, dataset: {}});
  return nodes.get(selector);
}};
const formatWhen = value => value;
""" + labels + render + """
const base = {phase: 'codex-first-research-complete', research: {completed:21,total:21},
 curation:{completed:0,total:21}, targetReviewFilename:'autoWelfareSquare.html', message:'Research finished'};
renderScoutProgress(base);
assert.equal(nodes.get('#scout-progress-title').textContent, 'Research complete — ready to curate and consolidate');
assert.equal(nodes.get('#curation-next-step').hidden, false);
assert.match(nodes.get('#curation-next-step-detail').textContent, /Discuss curation effort/);
assert.equal(nodes.get('#review-file-ready').hidden, true);
renderScoutProgress({...base, phase:'codex-curation-active'});
assert.equal(nodes.get('#curation-next-step').hidden, true); // 0 completed can still be active
renderScoutProgress({...base, phase:'curation-awaiting-effort-review', curation:{completed:2,total:21}});
assert.equal(nodes.get('#curation-next-step').hidden, false);
assert.match(nodes.get('#scout-progress-title').textContent, /paused/);
renderScoutProgress({...base, phase:'codex-curation-stopped', curation:{completed:5,total:21}, message:'Inconsistent candidate/resource links: 1648'});
assert.equal(nodes.get('#curation-next-step').hidden, false);
assert.match(nodes.get('#scout-progress-title').textContent, /stopped/);
assert.match(nodes.get('#curation-next-step-detail').textContent, /1648/);
renderScoutProgress({...base, phase:'codex-curation-repair-active'});
assert.equal(nodes.get('#curation-next-step').hidden, true);
assert.equal(nodes.get('#scout-progress-phase').textContent, 'Correcting saved curation result');
renderScoutProgress({...base, phase:'review', workProduct:{reviewProgress:{stage:'selection', summary:'Choosing Food complements',
 checkpointAvailable:true, contentCompleted:22,taxonomyCompleted:20,selectionCompleted:9,totalCategories:22,
 identityStatus:'complete',validationStatus:'pending',updatedAt:'2026-09-29T07:00:00Z',session:2}}});
assert.equal(nodes.get('#scout-review-progress').hidden, false);
assert.match(nodes.get('#scout-review-stage').textContent, /Starters and complementary/);
assert.match(nodes.get('#scout-review-counts').textContent, /Selections 9\/22/);
assert.match(nodes.get('#scout-review-checkpoint').textContent, /Reviewer-reported/);
renderScoutProgress({...base, phase:'review', workProduct:{reviewProgress:{stage:'content', summary:'Checking Food',
 checkpointAvailable:true, contentCompleted:0,taxonomyCompleted:0,selectionCompleted:0,totalCategories:1,
 identityStatus:'pending',validationStatus:'pending',session:1,
 recordProgress:{categoryId:'food',resourcesReviewed:2,resourcesTotal:20,candidatesReviewed:3,candidatesTotal:30,currentTask:'Checking intake'},
 categories:[{categoryId:'food',content:'in-progress',taxonomy:'pending',selection:'pending'}],
 recentFindings:['<img src=x onerror=alert(1)>'],activity:{message:'Checking a public front door.',eventAgeSeconds:10}}}});
assert.match(nodes.get('#scout-review-records').textContent, /2 of 20 resource records/);
assert.match(nodes.get('#scout-review-categories').innerHTML, /In Progress/);
assert.match(nodes.get('#scout-review-findings').innerHTML, /&lt;img/);
assert.doesNotMatch(nodes.get('#scout-review-findings').innerHTML, /<img/);
assert.match(nodes.get('#scout-review-activity').textContent, /Activity does not count/);
renderScoutProgress({...base, phase:'awaiting-codex-review', reviewFile:{readyForSave:false,filename:'autoWelfareSquare.html'}});
assert.equal(nodes.get('#review-file-download').hidden, true);
assert.match(nodes.get('#scout-progress-title').textContent, /ready for Codex review/);
renderScoutProgress({...base, phase:'review-file', reviewFile:{filename:'autoWelfareSquare.html',
 downloadUrl:'/api/scout-curation-jobs/7/review-file', categoryCount:21,resourceCount:250}});
assert.equal(nodes.get('#curation-next-step').hidden, true);
assert.equal(nodes.get('#review-file-ready').hidden, false);
assert.equal(nodes.get('#review-file-download').hidden, false);
assert.equal(nodes.get('#review-file-download').textContent, 'Save autoWelfareSquare.html');
assert.equal(nodes.get('#review-file-download').download, 'autoWelfareSquare.html');
assert.equal(nodes.get('#review-file-download').href, '/api/scout-curation-jobs/7/review-file');
const jsonName = 'scout-welfare-square-prepared-resources-<YY-MM-DD>.json';
renderScoutProgress({...base, targetReviewFilename:jsonName,
 workProduct:{kind:'prepared-resources',automaticReview:true,readyForSave:false,phase:'waiting-research'}});
assert.equal(nodes.get('#scout-progress-title').textContent, `Creating ${jsonName}`);
assert.equal(nodes.get('#curation-next-step').hidden, true);
assert.equal(nodes.get('#review-file-ready').hidden, true);
renderScoutProgress({...base, phase:'prepared-delivery-complete', targetReviewFilename:jsonName,
 workProduct:{kind:'prepared-resources',readyForSave:true,phase:'prepared-delivery-complete'},
 reviewFile:{filename:'scout-welfare-square-prepared-resources-26-09-28.json', readyForSave:true,
 downloadUrl:'/api/scout-prepared-resources?importId=1',categoryCount:21,resourceCount:250}});
assert.equal(nodes.get('#review-file-download').download, 'scout-welfare-square-prepared-resources-26-09-28.json');
assert.equal(nodes.get('#review-file-download').href, '/api/scout-prepared-resources?importId=1');
renderScoutProgress({...base, phase:'paused', targetReviewFilename:jsonName,
 workProduct:{kind:'prepared-resources',phase:'paused',pauseFinished:true,readyForSave:false}});
assert.equal(nodes.get('#scout-progress-title').textContent, `Paused: ${jsonName}`);
assert.equal(nodes.get('#scout-progress-phase').textContent, 'Paused');
assert.equal(nodes.get('#curation-next-step').hidden, true);
"""
        result = subprocess.run(["node", "-e", script], capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stderr)
        html = (Path(__file__).resolve().parents[1] / "web/index.html").read_text()
        self.assertLess(html.index('id="review-file-ready"'), html.index('id="codex-progress-detail"'))
