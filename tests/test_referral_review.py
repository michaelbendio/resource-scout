from __future__ import annotations

import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from resource_research_agent.optimization_pipeline import OptimizationDiscoveryPipeline
from resource_research_agent.referral_graph import (
    attach_referral_graph_to_query_plan,
    normalize_referral_graph,
)
from resource_research_agent.referral_review import (
    ReviewedReferralResolver,
    normalize_referral_review,
)
from resource_research_agent.storage import ResearchStore
from tests.test_qwen_discovery import FixtureProviders, qualified_identity


class ReferralReviewTests(unittest.TestCase):
    def graph(self) -> dict:
        return normalize_referral_graph(
            {
                "schemaVersion": 1,
                "graphId": "fixture-review-v1",
                "categoryId": "housing",
                "targetLocation": "Mesa",
                "createdAt": "2026-08-23T00:00:00+00:00",
                "sourceArtifactSha256": "a" * 64,
                "edges": [
                    {
                        "sourceUrl": "https://city.example/referrals",
                        "sourceTitle": "City referrals",
                        "sourceAuthority": "government-referral",
                        "destinationUrl": "https://provider.example/program",
                        "organization": "Provider",
                        "program": "Historical Program Name",
                        "stageKey": "urgent-access",
                        "relationship": "authoritative-referral",
                        "context": "The city links to the named program.",
                    }
                ],
            }
        )

    def review(self, graph: dict) -> dict:
        edge = graph["edges"][0]
        identity = qualified_identity(
            "Provider",
            "Current Program Name",
            stageKey="urgent-access",
            directDomains=["provider.example"],
        )
        identity["boundaryState"] = "resolved"
        identity["evidenceUrls"] = [edge["sourceUrl"], edge["destinationUrl"]]
        return {
            "schemaVersion": 1,
            "graphSha256": graph["graphSha256"],
            "decisions": {
                edge["edgeKey"]: {
                    "disposition": "candidate",
                    "reason": "Current provider evidence resolves the renamed program.",
                    "identityResolutionReason": "The provider now uses Current Program Name.",
                    "identity": identity,
                }
            },
        }

    def test_review_exactly_covers_graph_and_hashes_decisions(self) -> None:
        graph = self.graph()
        review = normalize_referral_review(graph, self.review(graph))
        self.assertEqual("reviewed-referral-destinations-v1", review["policyVersion"])
        self.assertEqual(64, len(review["reviewSha256"]))
        missing = self.review(graph)
        missing["decisions"] = {}
        with self.assertRaisesRegex(ValueError, "missing 1 edges"):
            normalize_referral_review(graph, missing)

    def test_changed_identity_requires_explicit_resolution_reason(self) -> None:
        graph = self.graph()
        review = self.review(graph)
        del review["decisions"][graph["edges"][0]["edgeKey"]][
            "identityResolutionReason"
        ]
        with self.assertRaisesRegex(ValueError, "identityResolutionReason"):
            normalize_referral_review(graph, review)

    def test_unresolved_edge_cannot_smuggle_an_identity(self) -> None:
        graph = self.graph()
        review = self.review(graph)
        decision = review["decisions"][graph["edges"][0]["edgeKey"]]
        decision["disposition"] = "unresolved"
        with self.assertRaisesRegex(ValueError, "cannot contain identities"):
            normalize_referral_review(graph, review)

    def test_candidate_evidence_requires_fresh_destination(self) -> None:
        graph = self.graph()
        review = self.review(graph)
        identity = review["decisions"][graph["edges"][0]["edgeKey"]]["identity"]
        identity["evidenceUrls"] = [graph["edges"][0]["sourceUrl"]]
        with self.assertRaisesRegex(ValueError, "freshly fetched destination"):
            normalize_referral_review(graph, review)

    def test_resolver_uses_edge_key_and_falls_back_for_search_results(self) -> None:
        graph = self.graph()
        review = self.review(graph)
        fallback_calls = []
        resolver = ReviewedReferralResolver(
            graph, review, lambda result: fallback_calls.append(result) or {"search": True}
        )
        decision = resolver(
            {"referralEdge": {"edgeKey": graph["edges"][0]["edgeKey"]}}
        )
        self.assertEqual("Current Program Name", decision["program"])
        self.assertEqual({"search": True}, resolver({"url": "https://search.example"}))
        self.assertEqual(1, len(fallback_calls))

    def test_candidate_qualification_is_required_and_category_neutral(self) -> None:
        graph = self.graph()
        graph.pop("graphSha256")
        graph["categoryId"] = "food"
        graph = normalize_referral_graph(graph)
        review = self.review(graph)
        edge = graph["edges"][0]
        review["decisions"] = {
            edge["edgeKey"]: next(iter(review["decisions"].values()))
        }
        identity = review["decisions"][edge["edgeKey"]]["identity"]
        identity["stageKey"] = edge["stageKey"]
        del identity["categoryState"]
        with self.assertRaisesRegex(ValueError, "categoryState"):
            normalize_referral_review(graph, review)

    def test_reviewed_resolver_integrates_with_discovery_pipeline(self) -> None:
        providers = FixtureProviders()
        graph = self.graph()
        normalized_graph = normalize_referral_graph(graph)
        review = self.review(normalized_graph)
        configuration = providers.configuration("fixture-reviewed-referral")
        configuration["queryPlan"] = attach_referral_graph_to_query_plan(
            configuration["queryPlan"], normalized_graph
        )
        destination = normalized_graph["edges"][0]["destinationUrl"]

        def fetch(url: str) -> dict:
            if url == destination:
                return {
                    "text": "Current provider page with an actionable intake path.",
                    "finalUrl": url,
                    "statusCode": 200,
                    "contentType": "text/html",
                }
            return providers.fetch(url)

        resolver = ReviewedReferralResolver(
            normalized_graph, review, providers.resolve
        )
        with tempfile.TemporaryDirectory() as directory:
            result = OptimizationDiscoveryPipeline(
                ResearchStore(Path(directory) / "research.sqlite3"),
                configuration,
                search=providers.search,
                fetch=fetch,
                resolve_identity=resolver,
                existing_resources=providers.fixture["existingResources"],
                referral_graph=normalized_graph,
            ).run()
        self.assertEqual(1, result.referral_edge_count)
        self.assertEqual(8, result.packet_count)


if __name__ == "__main__":
    unittest.main()
