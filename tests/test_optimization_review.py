from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from resource_research_agent.optimization_review import (
    cache_housing_searches,
    identity_review_template,
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


if __name__ == "__main__":
    unittest.main()
