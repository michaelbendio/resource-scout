from __future__ import annotations

import unittest

from resource_research_agent.optimization_housing_calibration import (
    build_housing_urgent_query_plan,
)
from resource_research_agent.query_expansion import (
    augment_query_plan_with_targeted_branch,
)


class TargetedQueryExpansionTests(unittest.TestCase):
    @staticmethod
    def queries() -> list[dict]:
        return [
            {
                "key": f"referral-depth-{position}",
                "query": f"Mesa current referred program {position}",
                "referralSourceKey": f"source-{position}",
            }
            for position in range(1, 6)
        ]

    def test_appended_branch_preserves_base_and_stops_after_three_no_yield_queries(self) -> None:
        base = build_housing_urgent_query_plan(
            "Mesa", "Maricopa County and nearby areas"
        )
        expanded = augment_query_plan_with_targeted_branch(
            base,
            branch_key="coordinated-entry-referral-depth",
            purpose="Follow authoritative coordinated-entry referrals to named programs.",
            queries=self.queries(),
            parent_corpus_sha256="d" * 64,
        )
        self.assertEqual(9, len(base["branches"]))
        self.assertEqual(10, len(expanded["branches"]))
        branch = expanded["branches"][-1]
        self.assertEqual(3, branch["saturation"]["minimumQueries"])
        self.assertEqual(5, branch["saturation"]["maximumQueries"])
        self.assertEqual(3, branch["saturation"]["consecutiveNoNewIdentityQueries"])
        self.assertEqual(list(range(1, 6)), [query["position"] for query in branch["queries"]])
        self.assertEqual("d" * 64, expanded["parentCorpusSha256"])

    def test_expansion_is_category_neutral(self) -> None:
        plan = build_housing_urgent_query_plan(
            "Mesa", "Maricopa County and nearby areas"
        )
        plan["categoryId"] = "food"
        plan["stageKey"] = "immediate-food"
        expanded = augment_query_plan_with_targeted_branch(
            plan,
            branch_key="food-referral-depth",
            purpose="Follow current food-service referrals.",
            queries=self.queries(),
            parent_corpus_sha256="e" * 64,
        )
        self.assertEqual("food", expanded["categoryId"])
        self.assertEqual("immediate-food", expanded["stageKey"])
        self.assertEqual("food-referral-depth", expanded["branches"][-1]["key"])

    def test_duplicate_or_unbounded_expansion_fails_closed(self) -> None:
        plan = build_housing_urgent_query_plan(
            "Mesa", "Maricopa County and nearby areas"
        )
        duplicate = self.queries()
        duplicate[1]["query"] = duplicate[0]["query"]
        with self.assertRaisesRegex(ValueError, "unique"):
            augment_query_plan_with_targeted_branch(
                plan,
                branch_key="depth",
                purpose="Targeted depth",
                queries=duplicate,
                parent_corpus_sha256="f" * 64,
            )
        with self.assertRaisesRegex(ValueError, "exactly maximumQueries"):
            augment_query_plan_with_targeted_branch(
                plan,
                branch_key="depth",
                purpose="Targeted depth",
                queries=self.queries()[:4],
                parent_corpus_sha256="f" * 64,
            )
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            augment_query_plan_with_targeted_branch(
                plan,
                branch_key="depth",
                purpose="Targeted depth",
                queries=self.queries(),
                parent_corpus_sha256="z" * 64,
            )


if __name__ == "__main__":
    unittest.main()
