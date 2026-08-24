from __future__ import annotations

import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from resource_research_agent.optimization_review import (
    CachedSearchClient,
    apply_identity_review_patch,
    build_identity_review_exclusion_patch,
    build_reviewed_housing_query_plan,
    cache_optimization_searches,
    cache_housing_searches,
    identity_review_template,
    merge_identity_review,
    reviewed_identity_decisions,
    validate_identity_review,
)
from resource_research_agent.optimization_runtime import OptimizationRuntimeError
from resource_research_agent.optimization import (
    augment_query_plan_with_identity_status_checks,
    sha256_json,
)
from resource_research_agent.optimization_housing_calibration import (
    HOUSING_STAGE_KEYS,
    build_housing_stage_query_plan,
    build_housing_urgent_query_plan,
)
from resource_research_agent.query_expansion import augment_query_plan_with_targeted_branch
from resource_research_agent.prior_leads import (
    augment_query_plan_with_prior_leads,
    build_prior_lead_manifest,
)


def qualified_identity(organization: str, program: str, **values) -> dict:
    identity = {
        "organization": organization,
        "program": program,
        "candidateRole": "direct-program",
        "geographyState": "confirmed-target",
        "categoryState": "confirmed",
        "actionabilityState": "actionable",
        "currentStatusState": "current",
        "evidenceReadiness": "current-authoritative",
    }
    identity.update(values)
    return identity


class OptimizationReviewTests(unittest.TestCase):
    def test_housing_calibration_has_distinct_valid_plans_for_all_four_stages(self) -> None:
        plans = {
            stage_key: build_housing_stage_query_plan(
                "Mesa",
                "Maricopa County and nearby areas",
                stage_key=stage_key,
            )
            for stage_key in HOUSING_STAGE_KEYS
        }
        self.assertEqual(set(HOUSING_STAGE_KEYS), set(plans))
        self.assertEqual(
            build_housing_urgent_query_plan(
                "Mesa", "Maricopa County and nearby areas"
            ),
            plans["urgent-access"],
        )
        branch_sets = {
            stage_key: {branch["key"] for branch in plan["branches"]}
            for stage_key, plan in plans.items()
        }
        self.assertNotEqual(
            branch_sets["stabilization"], branch_sets["specialized-housing"]
        )
        self.assertNotEqual(
            branch_sets["specialized-housing"], branch_sets["long-term-and-gaps"]
        )
        self.assertNotIn("official-city", branch_sets["stabilization"])

    def test_generic_cache_uses_non_housing_plan_without_hidden_defaults(self) -> None:
        plan = {
            "schemaVersion": 4,
            "candidateQualificationPolicyVersion": "candidate-qualification-gates-v2",
            "categoryId": "food",
            "stageKey": "immediate-food",
            "targetLocation": "Provo",
            "regionalScope": "Utah County",
            "branches": [
                {
                    "key": "direct-food",
                    "purpose": "Find direct food access.",
                    "required": True,
                    "saturation": {
                        "minimumQueries": 1,
                        "maximumQueries": 1,
                        "consecutiveNoNewIdentityQueries": 1,
                        "noveltyUnit": "package-eligible identity",
                    },
                    "queries": [
                        {
                            "key": "direct-food-1",
                            "position": 1,
                            "purpose": "Find direct food access.",
                            "query": "Provo current food pantry intake",
                        }
                    ],
                }
            ],
        }
        calls = []
        with tempfile.TemporaryDirectory() as directory:
            cache = cache_optimization_searches(
                Path(directory) / "food.json",
                query_plan=plan,
                search=lambda query, _limit: calls.append(query) or [],
                minimum_queries=1,
                maximum_queries=1,
                saturation_queries=1,
            )
        self.assertEqual(["Provo current food pantry intake"], calls)
        self.assertEqual("food", cache["queryPlan"]["categoryId"])
        self.assertEqual("immediate-food", cache["queryPlan"]["stageKey"])

    def test_reviewed_query_plan_includes_every_urgent_status_check(self) -> None:
        review = {
            "decisions": {
                "https://example.org/urgent": {
                    "disposition": "candidate",
                    "identity": qualified_identity(
                        "Urgent Provider", "Urgent Program"
                    ),
                },
                "https://example.org/routed": {
                    "disposition": "candidate",
                    "identity": qualified_identity(
                        "Routed Provider",
                        "Routed Program",
                        stageKey="stabilization",
                    ),
                },
            }
        }
        plan = build_reviewed_housing_query_plan(
            minimum_queries=4,
            maximum_queries=10,
            saturation_queries=3,
            candidate_status_review=review,
        )
        status = plan["branches"][-1]
        self.assertEqual("candidate-current-status", status["key"])
        self.assertEqual(1, len(status["queries"]))
        self.assertEqual(1, status["saturation"]["minimumQueries"])
        self.assertIn('"Urgent Provider" "Urgent Program"', status["queries"][0]["query"])

    def test_status_sweep_is_category_neutral(self) -> None:
        plan = build_housing_urgent_query_plan("Mesa", "Maricopa County")
        plan["categoryId"] = "food"
        plan["stageKey"] = "immediate-food"
        expanded = augment_query_plan_with_identity_status_checks(
            plan,
            [qualified_identity("Food Provider", "Pantry", stageKey="immediate-food")],
        )
        self.assertEqual("food", expanded["categoryId"])
        self.assertEqual("immediate-food", expanded["stageKey"])
        self.assertIn("reviewed food identity", expanded["branches"][-1]["purpose"])

    def test_reviewed_query_plan_can_include_routed_status_checks(self) -> None:
        review = {
            "decisions": {
                "https://example.org/routed": {
                    "disposition": "candidate",
                    "identity": qualified_identity(
                        "Routed Provider",
                        "Routed Program",
                        stageKey="stabilization",
                    ),
                }
            }
        }
        plan = build_reviewed_housing_query_plan(
            minimum_queries=4,
            maximum_queries=10,
            saturation_queries=3,
            candidate_status_review=review,
            include_routed_status=True,
        )
        self.assertEqual("identity-current-status-v2", plan["candidateStatusPolicyVersion"])
        self.assertTrue(plan["candidateStatusIncludesRoutedIdentities"])
        self.assertIn(
            '"Routed Provider" "Routed Program"',
            plan["branches"][-1]["queries"][0]["query"],
        )

    def test_search_cache_resumes_and_review_requires_every_disposition(self) -> None:
        calls = []

        def search(query: str, _limit: int) -> list[dict]:
            calls.append(query)
            return [{"url": "https://example.org/help", "title": "Help", "snippet": query}]

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cache.json"
            first = cache_housing_searches(path, search=search)
            self.assertEqual(2, first["schemaVersion"])
            self.assertEqual(first["queryPlanSha256"], sha256_json(first["queryPlan"]))
            self.assertEqual(54, len(first["queries"]))
            self.assertEqual(54, len(calls))
            second = cache_housing_searches(path, search=search)
            self.assertEqual(first["cacheSha256"], second["cacheSha256"])
            self.assertEqual(54, len(calls))

        review = identity_review_template(first)
        self.assertEqual(1, len(review["decisions"]))
        with self.assertRaisesRegex(OptimizationRuntimeError, "pending"):
            validate_identity_review(first, review)
        record = review["decisions"]["https://example.org/help"]
        record.update(
            {
                "disposition": "candidate",
                "reason": "Official provider program page",
                "identity": qualified_identity("Example", "Help"),
            }
        )
        validate_identity_review(first, review)
        self.assertEqual(
            "Help",
            reviewed_identity_decisions(review)["https://example.org/help"]["program"],
        )

        record.pop("identity")
        record["identities"] = [
            qualified_identity(
                "Example", "Help Line", evidenceExcerpt="Call the Help Line."
            ),
            qualified_identity(
                "Example",
                "Street Outreach",
                evidenceExcerpt="Street Outreach meets people outside.",
            ),
        ]
        validate_identity_review(first, review)
        decisions = reviewed_identity_decisions(review)["https://example.org/help"]
        self.assertEqual(["Help Line", "Street Outreach"], [item["program"] for item in decisions])

    def test_exclusion_requires_a_reason(self) -> None:
        cache = {
            "queries": {
                "q": {
                    "sources": [{"url": "https://example.org/", "title": "Directory"}]
                }
            }
        }
        cache["cacheSha256"] = __import__(
            "resource_research_agent.optimization", fromlist=["sha256_json"]
        ).sha256_json(cache["queries"])
        review = identity_review_template(cache)
        review["decisions"]["https://example.org/"]["disposition"] = "excluded"
        with self.assertRaisesRegex(OptimizationRuntimeError, "lacks a reason"):
            validate_identity_review(cache, review)

    def test_candidate_review_without_role_contract_fails_closed(self) -> None:
        cache = {
            "queries": {
                "q": {
                    "sources": [
                        {"url": "https://example.org/program", "title": "Program"}
                    ]
                }
            }
        }
        cache["cacheSha256"] = __import__(
            "resource_research_agent.optimization", fromlist=["sha256_json"]
        ).sha256_json(cache["queries"])
        review = identity_review_template(cache)
        review["decisions"]["https://example.org/program"].update(
            {
                "disposition": "candidate",
                "reason": "Named page without completed qualification review",
                "identity": {"organization": "Example", "program": "Program"},
            }
        )
        with self.assertRaisesRegex(OptimizationRuntimeError, "lacks qualification"):
            validate_identity_review(cache, review)

    def test_cached_search_is_exact_and_bounded(self) -> None:
        client = CachedSearchClient(
            {
                "queries": {
                    "q": {
                        "query": "exact query",
                        "sources": [{"url": f"https://example.org/{index}"} for index in range(3)],
                    }
                }
            }
        )
        self.assertEqual(2, len(client("exact query", 2)))
        with self.assertRaisesRegex(OptimizationRuntimeError, "no entry"):
            client("changed query", 8)

    def test_review_merge_carries_decisions_but_refreshes_query_provenance(self) -> None:
        old_cache = {
            "cacheSha256": "old",
            "queries": {
                "old-query": {
                    "sources": [
                        {
                            "url": "https://example.org/program",
                            "title": "Old title",
                        }
                    ]
                }
            },
        }
        previous = identity_review_template(old_cache)
        previous["decisions"]["https://example.org/program"].update(
            {
                "disposition": "candidate",
                "reason": "Reviewed program",
                "identity": qualified_identity("Example", "Program"),
                "reviewEvidence": [
                    {
                        "url": "https://example.org/status",
                        "excerpt": "The reviewed program remains open.",
                    }
                ],
            }
        )
        previous["reviewApplications"] = [
            {"label": "batch-1", "patchSha256": "a" * 64, "decisionCount": 1}
        ]
        new_cache = {
            "cacheSha256": "new",
            "queries": {
                "new-query": {
                    "sources": [
                        {
                            "url": "https://example.org/program",
                            "title": "New title",
                        },
                        {"url": "https://example.org/new", "title": "New lead"},
                    ]
                }
            },
        }
        merged = merge_identity_review(new_cache, previous)
        carried = merged["decisions"]["https://example.org/program"]
        self.assertEqual("candidate", carried["disposition"])
        self.assertEqual("New title", carried["title"])
        self.assertEqual(["new-query"], carried["queryKeys"])
        self.assertEqual(
            previous["decisions"]["https://example.org/program"]["reviewEvidence"],
            carried["reviewEvidence"],
        )
        self.assertEqual(
            "pending", merged["decisions"]["https://example.org/new"]["disposition"]
        )
        self.assertEqual("new", merged["searchCacheSha256"])
        self.assertEqual(previous["reviewApplications"], merged["reviewApplications"])

    def test_labeled_review_patch_is_validated_and_replay_safe(self) -> None:
        cache = {
            "cacheSha256": "cache",
            "queries": {
                "q": {
                    "sources": [
                        {"url": "https://example.org/program", "title": "Program"},
                        {"url": "https://example.org/junk", "title": "Junk"},
                    ]
                }
            },
        }
        review = identity_review_template(cache)
        patch = {
            "label": "review-batch-1",
            "searchCacheSha256": "cache",
            "decisions": {
                "https://example.org/program": {
                    "disposition": "candidate",
                    "reason": "Direct program page",
                    "identity": qualified_identity("Example", "Program"),
                },
                "https://example.org/junk": {
                    "disposition": "excluded",
                    "reason": "Unrelated result",
                    "reviewEvidence": [
                        {
                            "url": "https://example.org/status",
                            "excerpt": "The program closed.",
                        }
                    ],
                },
            },
        }
        updated = apply_identity_review_patch(review, patch)
        self.assertEqual("candidate", updated["decisions"]["https://example.org/program"]["disposition"])
        self.assertEqual("excluded", updated["decisions"]["https://example.org/junk"]["disposition"])
        self.assertEqual(
            "The program closed.",
            updated["decisions"]["https://example.org/junk"]["reviewEvidence"][0]["excerpt"],
        )
        self.assertEqual(1, len(updated["reviewApplications"]))
        replayed = apply_identity_review_patch(updated, patch)
        self.assertEqual(updated, replayed)

        changed_cache = dict(patch, searchCacheSha256="other")
        with self.assertRaisesRegex(OptimizationRuntimeError, "different search cache"):
            apply_identity_review_patch(review, changed_cache)

        unknown_url = dict(patch)
        unknown_url["decisions"] = {
            "https://other.example/": {
                "disposition": "excluded",
                "reason": "Not present",
            }
        }
        with self.assertRaisesRegex(OptimizationRuntimeError, "was not discovered"):
            apply_identity_review_patch(review, unknown_url)

        invalid_evidence = deepcopy(patch)
        invalid_evidence["decisions"] = {
            "https://example.org/junk": {
                "disposition": "excluded",
                "reason": "Unrelated result",
                "reviewEvidence": [{"url": "file:///tmp/status", "excerpt": "Closed"}],
            }
        }
        with self.assertRaisesRegex(OptimizationRuntimeError, "evidence URL is invalid"):
            apply_identity_review_patch(review, invalid_evidence)

    def test_status_sweep_reuses_base_cache_and_queries_each_urgent_identity(self) -> None:
        calls = []

        def search(query: str, _limit: int) -> list[dict]:
            calls.append(query)
            return [{"url": f"https://example.org/{len(calls)}", "title": "Result"}]

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            base = cache_housing_searches(
                root / "base.json",
                search=search,
                minimum_queries=2,
                maximum_queries=2,
                saturation_queries=2,
            )
            self.assertEqual(18, len(calls))
            review = identity_review_template(base)
            first = next(iter(review["decisions"].values()))
            first.update(
                {
                    "disposition": "candidate",
                    "reason": "Resolved program",
                    "identity": qualified_identity(
                        "Example", "Emergency Shelter"
                    ),
                }
            )
            expanded = cache_housing_searches(
                root / "expanded.json",
                search=search,
                minimum_queries=2,
                maximum_queries=2,
                saturation_queries=2,
                candidate_status_review=review,
                previous_cache=base,
            )
            self.assertEqual(19, len(calls))
            self.assertEqual(19, len(expanded["queries"]))
            self.assertEqual(base["cacheSha256"], expanded["previousCacheSha256"])
            status = next(
                record
                for key, record in expanded["queries"].items()
                if key.startswith("candidate-current-status-")
            )
            self.assertEqual("candidate-current-status", status["branchKey"])
            self.assertIn('"Emergency Shelter"', status["query"])

    def test_targeted_branch_reuses_every_frozen_base_response(self) -> None:
        calls = []

        def search(query: str, _limit: int) -> list[dict]:
            calls.append(query)
            return []

        targeted = [
            {"key": f"depth-{position}", "query": f"targeted referral {position}"}
            for position in range(1, 6)
        ]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            base = cache_housing_searches(
                root / "base.json",
                search=search,
                minimum_queries=2,
                maximum_queries=2,
                saturation_queries=2,
            )
            self.assertEqual(18, len(calls))
            plan = augment_query_plan_with_targeted_branch(
                build_housing_urgent_query_plan(
                    "Mesa",
                    "Maricopa County and nearby areas",
                    minimum_queries=2,
                    maximum_queries=2,
                    saturation_queries=2,
                ),
                branch_key="referral-depth",
                purpose="Follow reviewed referrals.",
                queries=targeted,
                parent_corpus_sha256="d" * 64,
            )
            expanded = cache_housing_searches(
                root / "expanded.json",
                search=search,
                minimum_queries=2,
                maximum_queries=2,
                saturation_queries=2,
                previous_cache=base,
                query_plan=plan,
            )
        self.assertEqual(23, len(calls))
        self.assertEqual(23, len(expanded["queries"]))
        self.assertEqual(base["cacheSha256"], expanded["previousCacheSha256"])

    def test_review_merge_preserves_identity_and_qualification_receipts(self) -> None:
        cache = {
            "cacheSha256": "new-cache",
            "queries": {
                "q1": {
                    "sources": [
                        {"url": "https://example.org/program", "title": "Program"}
                    ]
                }
            },
        }
        previous = {
            "reviewApplications": [{"patchSha256": "a" * 64}],
            "qualificationApplications": [{"manifestSha256": "b" * 64}],
            "decisions": {
                "https://example.org/program": {
                    "disposition": "excluded",
                    "reason": "Reviewed",
                }
            },
        }
        merged = merge_identity_review(cache, previous)
        self.assertEqual(previous["reviewApplications"], merged["reviewApplications"])
        self.assertEqual(
            previous["qualificationApplications"],
            merged["qualificationApplications"],
        )

    def test_prior_lead_branch_reuses_the_qualified_cache(self) -> None:
        calls = []

        def search(query: str, _limit: int) -> list[dict]:
            calls.append(query)
            return []

        manifest = build_prior_lead_manifest(
            manifest_id="fixture-history",
            category_id="housing",
            target_location="Mesa",
            created_at="2026-08-23T00:00:00+00:00",
            sources=[
                {
                    "id": "fixture",
                    "kind": "fixture",
                    "sourceRunId": "1",
                    "sourceStageKey": "urgent-access",
                    "observedAt": "2026-08-20T00:00:00+00:00",
                }
            ],
            leads=[
                {
                    "organization": "Historical Provider",
                    "program": "Historical Program",
                    "historicalDisposition": "candidate",
                    "provenance": [
                        {
                            "sourceId": "fixture",
                            "sourceRunId": "1",
                            "sourceStageKey": "urgent-access",
                            "observedAt": "2026-08-20T00:00:00+00:00",
                            "historicalDisposition": "candidate",
                        }
                    ],
                }
            ],
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            base = cache_housing_searches(
                root / "base.json",
                search=search,
                minimum_queries=2,
                maximum_queries=2,
                saturation_queries=2,
            )
            plan = augment_query_plan_with_prior_leads(
                build_housing_urgent_query_plan(
                    "Mesa",
                    "Maricopa County",
                    minimum_queries=2,
                    maximum_queries=2,
                    saturation_queries=2,
                ),
                manifest,
            )
            expanded = cache_housing_searches(
                root / "expanded.json",
                search=search,
                minimum_queries=2,
                maximum_queries=2,
                saturation_queries=2,
                previous_cache=base,
                query_plan=plan,
            )
        self.assertEqual(19, len(calls))
        self.assertEqual(19, len(expanded["queries"]))
        self.assertEqual(base["cacheSha256"], expanded["previousCacheSha256"])
        self.assertEqual(
            manifest["manifestSha256"],
            expanded["queryPlan"]["priorResultLeadManifestSha256"],
        )

    def test_exclusion_policy_builds_exact_pending_only_patch(self) -> None:
        review = {
            "searchCacheSha256": "cache",
            "decisions": {
                "https://maps.example/social": {
                    "disposition": "pending",
                    "title": "Map",
                    "snippet": "",
                },
                "https://provider.example/program": {
                    "disposition": "candidate",
                    "title": "Costa Mesa name in retained candidate",
                    "snippet": "",
                },
                "https://other.example/wrong": {
                    "disposition": "pending",
                    "title": "Costa Mesa shelter",
                    "snippet": "California",
                },
            },
        }
        policy = {
            "label": "obvious-v1",
            "rules": [
                {
                    "key": "platform",
                    "reason": "Not evidence",
                    "hosts": ["maps.example"],
                },
                {
                    "key": "wrong-place",
                    "reason": "Wrong location",
                    "textContains": ["Costa Mesa"],
                },
            ],
        }
        patch = build_identity_review_exclusion_patch(review, policy)
        self.assertEqual(2, len(patch["decisions"]))
        self.assertNotIn("https://provider.example/program", patch["decisions"])
        self.assertEqual({"platform": 1, "wrong-place": 1}, patch["ruleCounts"])
        self.assertEqual("cache", patch["searchCacheSha256"])


if __name__ == "__main__":
    unittest.main()
