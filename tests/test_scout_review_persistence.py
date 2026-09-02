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
resources[0].categories = ['employment', 'housing'];
resources[0].categoryFilters = {{housing:['Emergency shelter']}};
scoutReviewBaseData = {{
  packageVersion:43,
  officeName:'AutoProvo',
  categories:[
    {{id:'employment', label:'Employment', active:true}},
    {{id:'housing', label:'Housing', active:true, filters:['Emergency shelter']}}
  ],
  forGroups:['Veterans'],
  resources,
  changes:[],
  deletionRequests:[],
  deletions:[]
}};
const current = cloneScoutReviewValue(scoutReviewBaseData);
current.resources[0].description = 'Reviewer edit';
current.categories = current.categories.filter(category => category.id !== 'housing');
current.resources[0].categories = ['employment'];
delete current.resources[0].categoryFilters.housing;
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
assert.deepStrictEqual(compact.categoriesOverride.map(category => category.id), ['employment']);
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
assert.deepStrictEqual(restored.categories.map(category => category.id), ['employment']);
assert.deepStrictEqual(restored.resources.find(resource => resource.id === 'resource-0').categories, ['employment']);
assert.strictEqual(restored.resources.find(resource => resource.id === 'resource-0').categoryFilters.housing, undefined);
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

    def test_review_resources_and_categories_delete_without_tags(self) -> None:
        self.assertIn(
            "Delete the proposed resource '${name}' from this Scout review copy?",
            self.template,
        )
        self.assertIn(
            "Delete the proposed category '${name}' from this Scout review copy?",
            self.template,
        )
        self.assertIn("function deleteScoutReviewCategory(categoryId)", self.template)
        self.assertIn(
            "The resources themselves will remain.",
            self.template,
        )

        category_delete_start = self.template.index("function deleteCategory()")
        category_delete_end = self.template.index(
            "function closeCategoryEditor()", category_delete_start
        )
        category_delete_source = self.template[
            category_delete_start:category_delete_end
        ]
        self.assertIn("if(isScoutReviewMode())", category_delete_source)
        self.assertIn("deleteScoutReviewCategory(cat.id)", category_delete_source)
        self.assertIn("return;", category_delete_source)
        self.assertIn("promptCategoryDeleteDescription", category_delete_source)

        direct_category_start = self.template.index(
            "function deleteScoutReviewCategory(categoryId)"
        )
        direct_category_end = self.template.index(
            "function deleteCategory()", direct_category_start
        )
        direct_category_source = self.template[
            direct_category_start:direct_category_end
        ]
        self.assertIn("applyDeletionTombstones(data", direct_category_source)
        self.assertNotIn("tagDeletionRequests", direct_category_source)

        resource_delete_start = self.template.index("function deleteResource()")
        resource_delete_end = self.template.index(
            "function openResourceEditor()", resource_delete_start
        )
        resource_delete_source = self.template[
            resource_delete_start:resource_delete_end
        ]
        self.assertIn("if(isScoutReviewMode())", resource_delete_source)
        self.assertIn("data.resources.splice(idx, 1)", resource_delete_source)

    def test_direct_category_delete_removes_assignments_and_persists(self) -> None:
        deletion_core_start = self.template.index("const DELETION_KINDS")
        deletion_core_end = self.template.index(
            "// Source: src/js/27-package-pipeline.js", deletion_core_start
        )
        deletion_core = self.template[deletion_core_start:deletion_core_end]
        direct_delete_start = self.template.index(
            "function deleteScoutReviewCategory(categoryId)"
        )
        direct_delete_end = self.template.index(
            "function deleteCategory()", direct_delete_start
        )
        direct_delete = self.template[direct_delete_start:direct_delete_end]
        script = f"""
const assert = require('assert');
function nowISO() {{ return '2026-09-02T12:00:00Z'; }}
function normalizeCategoryFilters(values) {{ return Array.isArray(values) ? values : []; }}
function normalizeTaxonomyLabels(values) {{ return Array.isArray(values) ? values : []; }}
{deletion_core}

let data = {{
  categories:[
    {{id:'category-a', label:'Alpha', filters:['One']}},
    {{id:'category-b', label:'Beta', filters:[]}}
  ],
  resources:[
    {{id:'resource-1', name:'One', categories:['category-a', 'category-b'], categoryFilters:{{'category-a':['One']}}}},
    {{id:'resource-2', name:'Two', categories:['category-b'], categoryFilters:{{}}}}
  ],
  forGroups:[],
  deletionRequests:[
    {{kind:'category', targetId:'category-a', label:'Alpha', requestedAt:'2026-09-01T12:00:00Z'}},
    {{kind:'type', categoryId:'category-b', label:'Keep me', requestedAt:'2026-09-01T12:00:00Z'}}
  ],
  deletions:[]
}};
let selectedCategoryIndex = '0';
let editing = {{kind:'category', idx:0}};
let editorSnapshot = 'before';
let curatedIds = new Set(['resource-1', 'resource-2']);
const newCategoryIds = new Set(['category-a']);
const selectedCategoryFilters = {{'category-a':['One']}};
let persistCount = 0;
let renderCount = 0;
let toast = '';
function getAlphabeticalCategoryPairs() {{
  return data.categories.map((c, i) => ({{c, i}})).sort((a, b) => a.c.label.localeCompare(b.c.label));
}}
function getCategoryIndexById(id) {{ return data.categories.findIndex(category => category.id === id); }}
function getDeletionImpact(request) {{
  return {{
    affectedResources:data.resources.filter(resource =>
      resource.categories.includes(request.targetId)
      || Object.prototype.hasOwnProperty.call(resource.categoryFilters, request.targetId)
    )
  }};
}}
function clearScoutReviewResourceCurated(id) {{ curatedIds.delete(id); }}
function persist() {{ persistCount += 1; }}
function safeRender() {{ renderCount += 1; }}
function safeRenderAdmin() {{ renderCount += 1; }}
function showToast(message) {{ toast = message; }}
function formatResourceCount(count) {{ return `${{count}} ${{count === 1 ? 'resource' : 'resources'}}`; }}
{direct_delete}

deleteScoutReviewCategory('category-a');
assert.deepStrictEqual(data.categories.map(category => category.id), ['category-b']);
assert.deepStrictEqual(data.resources[0].categories, ['category-b']);
assert.strictEqual(data.resources[0].categoryFilters['category-a'], undefined);
assert.deepStrictEqual(data.resources[1].categories, ['category-b']);
assert(!curatedIds.has('resource-1'));
assert(curatedIds.has('resource-2'));
assert(!newCategoryIds.has('category-a'));
assert.strictEqual(selectedCategoryFilters['category-a'], undefined);
assert.strictEqual(data.deletionRequests.length, 1);
assert.strictEqual(data.deletionRequests[0].kind, 'type');
assert.deepStrictEqual(data.deletions, []);
assert.strictEqual(selectedCategoryIndex, '0');
assert.strictEqual(editing, null);
assert.strictEqual(editorSnapshot, '');
assert.strictEqual(persistCount, 1);
assert.strictEqual(renderCount, 2);
assert(toast.includes('Deleted proposed category'));
"""
        subprocess.run(
            ["node", "-e", script],
            text=True,
            capture_output=True,
            check=True,
        )


if __name__ == "__main__":
    unittest.main()
