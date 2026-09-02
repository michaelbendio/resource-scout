from __future__ import annotations

import unittest

from resource_research_agent.taxonomy_compile import _compile_seed


FINAL_CATEGORY_IDS = [
    "addiction",
    "caregiving",
    "clothing",
    "domestic-violence",
    "education",
    "employment",
    "financial-assistance",
    "food",
    "homeless-services",
    "housing",
    "household-essentials",
    "id-recovery",
    "immigration",
    "independent-living",
    "legal",
    "medical-dental-vision",
    "mental-health",
    "parenting-child-development",
    "transportation",
    "utilities-phone-internet",
]


class TaxonomyCompilationTests(unittest.TestCase):
    def test_compiles_full_audit_but_outputs_only_curated_proposals(self) -> None:
        categories = [
            {"id": category_id, "label": category_id.replace("-", " ").title()}
            for category_id in FINAL_CATEGORY_IDS
        ]
        resources = [
            {
                "corpusKey": "connected-package:known",
                "origin": "connected-package",
                "resourceId": "known",
                "categories": ["transportation"],
                "resource": {"id": "known", "name": "Known Ride"},
            },
            {
                "corpusKey": "automesa-curated:new",
                "origin": "automesa-curated",
                "resourceId": "new",
                "categories": ["transportation"],
                "resource": {"id": "new", "name": "New Ride"},
            },
        ]
        type_revisions = []
        for category in categories:
            category_id = category["id"]
            assignments = []
            if category_id == "transportation":
                assignments = [
                    {
                        "resourceId": "known",
                        "disposition": "assigned-types",
                        "types": ["Transit"],
                    },
                    {
                        "resourceId": "new",
                        "disposition": "assigned-types",
                        "types": ["Transit"],
                    },
                ]
            type_revisions.append({
                "categoryId": category_id,
                "revision": 1,
                "designSha256": category_id.ljust(64, "0")[:64],
                "design": {
                    "categoryLabel": category["label"],
                    "types": [{"label": "Transit"}] if assignments else [],
                    "assignments": assignments,
                },
            })
        group_assignments = [
            {
                "corpusKey": item["corpusKey"],
                "reviewStatus": "ready",
                "groups": [{"label": "Seniors", "relationship": "accommodates"}],
            }
            for item in resources
        ]
        seed, manifest = _compile_seed(
            {"officeName": "Mesa TSO", "resources": []},
            {"corpus": {"categories": categories, "resources": resources}},
            {
                "proposal": {
                    "assignments": [],
                    "proposedNeedCategories": [],
                }
            },
            type_revisions,
            {
                "proposal": {
                    "assignments": group_assignments,
                    "catalog": [{"label": "Seniors"}],
                }
            },
            compiled_at="2026-09-01T00:00:00+00:00",
        )

        self.assertEqual(20, len(seed["categories"]))
        transportation = next(
            item for item in seed["categories"] if item["id"] == "transportation"
        )
        self.assertEqual(["Transit"], transportation["filters"])
        self.assertNotIn("types", transportation)
        self.assertEqual(["new"], [item["id"] for item in seed["resources"]])
        self.assertEqual(
            {"transportation": ["Transit"]},
            seed["resources"][0]["categoryFilters"],
        )
        self.assertEqual(["Seniors"], seed["resources"][0]["forGroups"])
        self.assertEqual(20, len(manifest))


if __name__ == "__main__":
    unittest.main()
