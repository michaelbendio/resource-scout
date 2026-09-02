from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path


class ScoutReviewPersistenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.template_path = (
            Path(__file__).resolve().parent.parent
            / "resource_research_agent"
            / "scout_review_template.html"
        )
        cls.template = cls.template_path.read_text(encoding="utf-8")

    def test_review_mode_uses_artifact_scoped_compact_storage(self) -> None:
        self.assertIn('name="scout-review-artifact-id"', self.template)
        self.assertIn("ScoutReviewV3:${SCOUT_REVIEW_ARTIFACT_ID}", self.template)
        self.assertIn("SCOUT_REVIEW_V2_STORAGE_KEY", self.template)
        self.assertIn("resourceOverrides", self.template)
        self.assertIn("addedResources", self.template)
        self.assertIn("deletedResourceIds", self.template)
        self.assertIn("resourceIds:resources.map", self.template)
        self.assertNotIn("resources:batch.resources.map", self.template)

        persist_start = self.template.index("function persist(){")
        persist_end = self.template.index("function openAssetsDB()", persist_start)
        persist_source = self.template[persist_start:persist_end]
        self.assertIn("persistScoutReviewState(scoutReviewState)", persist_source)
        self.assertIn("if(isScoutReviewMode())", persist_source)

    def test_compact_overlay_round_trips_under_a_small_storage_limit(self) -> None:
        segment_start = self.template.index("let scoutReviewStorageError = null;")
        segment_end = self.template.index(
            "// Main persisted app data snapshot", segment_start
        )
        functions = self.template[segment_start:segment_end]
        script = f"""
const assert = require('assert');
const SCOUT_REVIEW_ARTIFACT_ID = 'artifact-a';
const SCOUT_REVIEW_STORAGE_KEY = 'review-v3-artifact-a';
const SCOUT_REVIEW_V2_STORAGE_KEY = 'review-v2-artifact-a';
const SCOUT_REVIEW_LEGACY_STORAGE_KEY = 'review-v1';
const DATA_STORAGE_KEY = 'review-data';
let scoutReviewBaseData = null;
function isScoutReviewMode() {{ return true; }}
const values = new Map([
  [DATA_STORAGE_KEY, 'legacy-full-copy'],
  [SCOUT_REVIEW_LEGACY_STORAGE_KEY, 'legacy-review-copy']
]);
const localStorage = {{
  getItem(key) {{ return values.has(key) ? values.get(key) : null; }},
  removeItem(key) {{ values.delete(key); }},
  setItem(key, value) {{
    if(String(value).length > 50000) throw new Error('QuotaExceededError');
    values.set(key, String(value));
  }}
}};
{functions}

const resources = Array.from({{length:430}}, (_, index) => ({{
  id:`resource-${{index}}`,
  name:`Resource ${{index}}`,
  description:'x'.repeat(1000),
  informationText:'',
  categories:['employment'],
  categoryFilters:{{}},
  forGroups:[],
  pdfs:[]
}}));
scoutReviewBaseData = {{
  packageVersion:43,
  officeName:'AutoProvo',
  categories:[{{id:'employment', label:'Employment', active:true}}],
  forGroups:['Veterans'],
  resources,
  changes:[],
  deletionRequests:[],
  deletions:[]
}};
const current = cloneScoutReviewValue(scoutReviewBaseData);
current.resources[0].description = 'Reviewer edit';
current.resources = current.resources.filter(resource => !['resource-1', 'resource-2'].includes(resource.id));
current.resources.push({{
  id:'reviewer-added', name:'Reviewer added', description:'Added locally',
  informationText:'', categories:['employment'], categoryFilters:{{}},
  forGroups:[], pdfs:[]
}});
const previous = normalizeScoutReviewState({{
  curatedResourceIds:['resource-0', 'reviewer-added'],
  readyResourceIds:['resource-3'],
  packagedBatches:[{{
    id:'batch-1', savedAt:'2026-08-29T00:00:00Z', packageVersion:44,
    fileName:'provo-resource-package.zip', resourceIds:['resource-1']
  }}],
  resourceOverrides:[{{...resources[1], description:'Packaged reviewer edit'}}]
}});
const compact = buildCompactScoutReviewState(current, previous);
const serialized = JSON.stringify(compact);
assert(JSON.stringify(scoutReviewBaseData).length > 50000);
assert(serialized.length < 50000);
assert.strictEqual(compact.packagedBatches[0].resources, undefined);
assert.deepStrictEqual(compact.packagedBatches[0].resourceIds, ['resource-1']);
assert(compact.deletedResourceIds.includes('resource-2'));
assert(!compact.deletedResourceIds.includes('resource-1'));
assert(compact.addedResources.some(resource => resource.id === 'reviewer-added'));
assert(compact.resourceOverrides.some(resource => resource.id === 'resource-0'));
assert(compact.resourceOverrides.some(resource => resource.id === 'resource-1'));
assert.deepStrictEqual(compact.curatedResourceIds.sort(), ['resource-0', 'reviewer-added']);
assert(!compact.curatedResourceIds.includes('resource-3'));
assert.strictEqual(writeCompactScoutReviewState(compact), true);
assert.strictEqual(values.has(DATA_STORAGE_KEY), false);
assert.strictEqual(values.has(SCOUT_REVIEW_LEGACY_STORAGE_KEY), false);
assert.strictEqual(values.get(SCOUT_REVIEW_STORAGE_KEY), serialized);

const restored = applyScoutReviewState(scoutReviewBaseData, compact);
const restoredIds = new Set(restored.resources.map(resource => resource.id));
assert(restoredIds.has('resource-0'));
assert(restoredIds.has('reviewer-added'));
assert(!restoredIds.has('resource-1'));
assert(!restoredIds.has('resource-2'));
assert.strictEqual(restored.resources.find(resource => resource.id === 'resource-0').description, 'Reviewer edit');
process.stdout.write(JSON.stringify({{full:JSON.stringify(scoutReviewBaseData).length, compact:serialized.length}}));
"""
        completed = subprocess.run(
            ["node", "-e", script],
            text=True,
            capture_output=True,
            check=True,
        )
        sizes = json.loads(completed.stdout)
        self.assertGreater(sizes["full"], sizes["compact"] * 10)

    def test_curated_workflow_replaces_ready_without_inheriting_ready_marks(self) -> None:
        self.assertIn(
            "Curate resources in Admin. Save a resource package of the curated resources.",
            self.template,
        )
        self.assertIn("Save a package of ${count} curated resources", self.template)
        self.assertIn(">Curate Resource</h3>", self.template)
        self.assertIn('id="res_curated_btn"', self.template)
        self.assertIn('id="res_print_btn"', self.template)
        self.assertIn('id="res_website_link"', self.template)
        self.assertIn("function updateResourceWebsiteLink()", self.template)
        self.assertIn("function printCurrentResource()", self.template)
        self.assertIn("const draft = resourceEditorDraft();", self.template)
        self.assertIn("<summary>Curate</summary>", self.template)
        self.assertIn("scout-review-curated-indicator", self.template)
        self.assertIn('${scoutReview ? "" : `', self.template)
        self.assertIn(
            'modal.querySelectorAll(".admin-publishing-help").forEach(section => section.remove())',
            self.template,
        )
        self.assertNotIn("scout-review-ready-checkbox", self.template)
        self.assertNotIn("Ready to package", self.template)

        normalize_start = self.template.index("function normalizeScoutReviewState(")
        normalize_end = self.template.index("function loadScoutReviewState(", normalize_start)
        normalize_source = self.template[normalize_start:normalize_end]
        self.assertIn("source.curatedResourceIds", normalize_source)
        self.assertNotIn("source.readyResourceIds", normalize_source)

        curated_toggle_start = self.template.index(
            "function toggleCurrentResourceCurated()"
        )
        curated_toggle_end = self.template.index(
            "function cancelResourceEditor()", curated_toggle_start
        )
        curated_toggle_source = self.template[curated_toggle_start:curated_toggle_end]
        self.assertIn("pendingResourceCuratedToggle = true", curated_toggle_source)
        self.assertIn("commitPendingEditsIfChanged()", curated_toggle_source)


if __name__ == "__main__":
    unittest.main()
