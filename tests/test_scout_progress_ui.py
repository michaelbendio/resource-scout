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
renderScoutProgress({...base, phase:'review-file', reviewFile:{filename:'autoWelfareSquare.html',
 downloadUrl:'/api/scout-curation-jobs/7/review-file', categoryCount:21,resourceCount:250}});
assert.equal(nodes.get('#curation-next-step').hidden, true);
assert.equal(nodes.get('#review-file-ready').hidden, false);
assert.equal(nodes.get('#review-file-download').textContent, 'Save autoWelfareSquare.html');
assert.equal(nodes.get('#review-file-download').download, 'autoWelfareSquare.html');
assert.equal(nodes.get('#review-file-download').href, '/api/scout-curation-jobs/7/review-file');
"""
        result = subprocess.run(["node", "-e", script], capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stderr)
        html = (Path(__file__).resolve().parents[1] / "web/index.html").read_text()
        self.assertLess(html.index('id="review-file-ready"'), html.index('id="codex-progress-detail"'))
