from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path


TEMPLATE = (
    Path(__file__).resolve().parents[1]
    / "resource_research_agent"
    / "scout_review_template.html"
)


class ScoutReviewTaxonomyUITests(unittest.TestCase):
    @staticmethod
    def _function(source: str, name: str) -> str:
        start = source.index(f"function {name}(")
        brace = source.index("{", start)
        depth = 0
        for index in range(brace, len(source)):
            if source[index] == "{":
                depth += 1
            elif source[index] == "}":
                depth -= 1
                if depth == 0:
                    return source[start:index + 1]
        raise AssertionError(f"Could not extract {name}")

    def test_offers_need_and_group_browsing(self) -> None:
        source = TEMPLATE.read_text(encoding="utf-8")
        self.assertIn('label:"Browse by need"', source)
        self.assertIn('label:"Find resources for"', source)
        self.assertIn("Choose one or more groups", source)
        self.assertIn("organized below by the needs they address", source)
        self.assertIn("openCategoryFromGroupBrowse", source)
        self.assertIn('typeof container.appendChild === "function"', source)

    def test_types_or_groups_and_by_default_with_optional_any(self) -> None:
        source = TEMPLATE.read_text(encoding="utf-8")
        functions = "\n".join(
            self._function(source, name)
            for name in (
                "canonicalizeTaxonomyLabel",
                "normalizeTaxonomyLabels",
                "normalizeCategoryFilters",
                "makeCategorySpecificFilterKey",
                "makeForGroupFilterKey",
                "getResourceCategoryFilterKeys",
                "getResourceForGroupFilterKeys",
                "selectedCategoryFilterDimensions",
                "resourceMatchesSelectedCategoryFilters",
            )
        )
        module_start = source.index("/* ---------- For-group matching and explicit editor review")
        module_end = source.index("function makeCategorySpecificFilterKey", module_start)
        functions += "\n" + source[module_start:module_end]
        cases = [
            {
                "name": "type and group both match",
                "selected": ["filter:ged", "for:veterans"],
                "expected": True,
            },
            {
                "name": "type matches but group does not",
                "selected": ["filter:ged", "for:spanish"],
                "expected": False,
            },
            {
                "name": "types are ORed",
                "selected": ["filter:ged", "filter:online education", "for:veterans"],
                "expected": True,
            },
            {
                "name": "groups are ANDed by default",
                "selected": ["filter:ged", "for:spanish", "for:veterans"],
                "expected": False,
            },
        ]
        script = f"""
{functions}
const data = {{forGroups:["Veterans","Spanish","Deaf & hard of hearing","People with disabilities"]}};
const resource = {{
  categoryFilters: {{ education: ["GED"] }},
  forGroups: ["Veterans"]
}};
const cases = {json.dumps(cases)};
for (const item of cases) {{
  const actual = resourceMatchesSelectedCategoryFilters(
    resource, "education", item.selected
  );
  if (actual !== item.expected) {{
    throw new Error(`${{item.name}}: expected ${{item.expected}}, received ${{actual}}`);
  }}
}}
"""
        script += """
forGroupMatchMode="any";
if(!resourceMatchesSelectedCategoryFilters(resource,"education",["for:spanish","for:veterans"])) throw Error("Optional ANY must allow either group");
forGroupMatchMode="all";
const child={name:"Hearing aid program",categories:["education"],forGroups:["Deaf & hard of hearing"]};
if(!matchesSelectedForGroupKeys(child,["for:deaf & hard of hearing","for:people with disabilities"])) throw Error("Approved parent missing from search");
const nowISO=()=>"2026-09-20T10:00:00Z";
if(hasCurrentForGroupReview(child,data.forGroups)) throw Error("Unreviewed child appears reviewed");
recordForGroupReview(child,data.forGroups);
if(!child.forGroups.includes("People with disabilities") || !hasCurrentForGroupReview(child,data.forGroups)) throw Error("Confirmed review missing");
for(const changes of [{description:"Changed"},{informationText:"New eligibility"},{categories:["food"]},{forGroups:[]},{categoryFilters:{education:["GED"]}}]){
  if(hasCurrentForGroupReview({...child,...changes},data.forGroups)) throw Error("Stale review survived a relevant edit");
}
if(!hasCurrentForGroupReview({...child,phone:"555-1234"},data.forGroups)) throw Error("Contact edit invalidated review");
if(hasCurrentForGroupReview(child,[...data.forGroups,"Children"])) throw Error("New group option not reviewed");
if(effectiveForGroups(["Deaf & hard of hearing"],["Deaf & hard of hearing"]).length!==1) throw Error("Created a group outside catalog");
"""
        completed = subprocess.run(
            ["node", "-e", script],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(0, completed.returncode, completed.stderr)


    def test_curated_export_requires_current_review_and_preserves_review_date(self):
        source = TEMPLATE.read_text(encoding="utf-8")
        start = source.index("/* ---------- For-group matching and explicit editor review")
        end = source.index("function makeCategorySpecificFilterKey", start)
        functions = source[start:end] + "\n" + "\n".join(self._function(source, name) for name in (
            "canonicalizeTaxonomyLabel", "normalizeTaxonomyLabels", "buildScoutReviewSelectionPackageData"))
        script = functions + """
const assert=require('assert');
const nowISO=()=>"2026-09-20T10:00:00Z";
const cloneDataObject=x=>JSON.parse(JSON.stringify(x));
const processResourcePackageData=x=>({data:cloneDataObject(x)});
const buildResourcePackageData=x=>cloneDataObject(x);
const source={categories:[{id:'medical'},{id:'food'}],forGroups:['Deaf & hard of hearing','People with disabilities','Veterans'],
 resources:[{id:'hearing',name:'Hearing program',categories:['medical'],forGroups:['Deaf & hard of hearing']}],changes:[]};
assert.throws(()=>buildScoutReviewSelectionPackageData(source,['hearing']),/Review For groups/);
recordForGroupReview(source.resources[0],source.forGroups);
const reviewedAt=source.resources[0].forGroupReview.reviewedAt;
const packet=buildScoutReviewSelectionPackageData(source,['hearing']);
assert.strictEqual(packet.resources.length,1);
assert.strictEqual(packet.forGroups.length,2);
assert(hasCurrentForGroupReview(packet.resources[0],packet.forGroups));
assert.strictEqual(packet.resources[0].forGroupReview.reviewedAt,reviewedAt);
assert(hasCurrentForGroupReview(source.resources[0],source.forGroups)); // export did not mutate source stamp
packet.resources[0].informationText='Changed eligibility';
assert.throws(()=>buildScoutReviewSelectionPackageData(packet,['hearing']),/Review For groups/);
"""
        result = subprocess.run(["node", "-e", script], text=True, capture_output=True)
        self.assertEqual(0, result.returncode, result.stderr)


if __name__ == "__main__":
    unittest.main()
