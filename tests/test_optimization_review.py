from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from resource_research_agent.optimization_review import (
    CachedSearchClient,
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


if __name__ == "__main__":
    unittest.main()
