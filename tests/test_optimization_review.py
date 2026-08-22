from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from resource_research_agent.optimization_review import (
    CachedSearchClient,
    apply_identity_review_patch,
    cache_housing_searches,
    identity_review_template,
    merge_identity_review,
    reviewed_identity_decisions,
    validate_identity_review,
)
from resource_research_agent.optimization_runtime import OptimizationRuntimeError


class OptimizationReviewTests(unittest.TestCase):
    def test_search_cache_resumes_and_review_requires_every_disposition(self) -> None:
        calls = []

        def search(query: str, _limit: int) -> list[dict]:
            calls.append(query)
            return [{"url": "https://example.org/help", "title": "Help", "snippet": query}]

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cache.json"
            first = cache_housing_searches(path, search=search)
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
                "identity": {"organization": "Example", "program": "Help"},
            }
        )
        validate_identity_review(first, review)
        self.assertEqual(
            "Help",
            reviewed_identity_decisions(review)["https://example.org/help"]["program"],
        )

        record.pop("identity")
        record["identities"] = [
            {
                "organization": "Example",
                "program": "Help Line",
                "evidenceExcerpt": "Call the Help Line.",
            },
            {
                "organization": "Example",
                "program": "Street Outreach",
                "evidenceExcerpt": "Street Outreach meets people outside.",
            },
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
                "identity": {"organization": "Example", "program": "Program"},
            }
        )
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
            "pending", merged["decisions"]["https://example.org/new"]["disposition"]
        )
        self.assertEqual("new", merged["searchCacheSha256"])

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
                    "identity": {"organization": "Example", "program": "Program"},
                },
                "https://example.org/junk": {
                    "disposition": "excluded",
                    "reason": "Unrelated result",
                },
            },
        }
        updated = apply_identity_review_patch(review, patch)
        self.assertEqual("candidate", updated["decisions"]["https://example.org/program"]["disposition"])
        self.assertEqual("excluded", updated["decisions"]["https://example.org/junk"]["disposition"])
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


if __name__ == "__main__":
    unittest.main()
