from __future__ import annotations

import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from resource_research_agent.optimization_pipeline import (
    OptimizationDiscoveryPipeline,
    OptimizationPipelineError,
)
from resource_research_agent.referral_graph import (
    attach_referral_graph_to_query_plan,
    normalize_referral_graph,
)
from resource_research_agent.storage import ResearchStore
from tests.test_qwen_discovery import FixtureProviders, qualified_identity


class ReferralGraphTests(unittest.TestCase):
    @staticmethod
    def graph(**edge_values) -> dict:
        edge = {
            "sourceUrl": "https://mesaaz.gov/housing/resources",
            "sourceTitle": "City housing resources",
            "sourceAuthority": "government-referral",
            "destinationUrl": "https://provider.example/current-program",
            "organization": "Referral Provider",
            "program": "Current Program",
            "stageKey": "urgent-access",
            "relationship": "authoritative-referral",
            "context": "The city names Current Program and links to its provider page.",
        }
        edge.update(edge_values)
        return {
            "schemaVersion": 1,
            "graphId": "fixture-referrals-v1",
            "categoryId": "housing",
            "targetLocation": "Mesa",
            "createdAt": "2026-08-23T00:00:00+00:00",
            "sourceArtifactSha256": "c" * 64,
            "edges": [edge],
        }

    def test_graph_is_canonical_bounded_and_rejects_non_authoritative_sources(self) -> None:
        graph = normalize_referral_graph(self.graph())
        self.assertEqual("authoritative-one-hop-referrals-v1", graph["policyVersion"])
        self.assertEqual(64, len(graph["graphSha256"]))
        self.assertTrue(graph["edges"][0]["edgeKey"].startswith("edge:"))
        with self.assertRaisesRegex(ValueError, "self-loop"):
            normalize_referral_graph(
                self.graph(destinationUrl="https://mesaaz.gov/housing/resources")
            )
        with self.assertRaisesRegex(ValueError, "authoritative source"):
            normalize_referral_graph(self.graph(sourceAuthority="directory-lead"))
        duplicate = self.graph()
        duplicate["edges"].append(deepcopy(duplicate["edges"][0]))
        with self.assertRaisesRegex(ValueError, "Duplicate referral edge"):
            normalize_referral_graph(duplicate)

    def test_graph_category_and_location_must_match(self) -> None:
        providers = FixtureProviders()
        with self.assertRaisesRegex(ValueError, "another category"):
            attach_referral_graph_to_query_plan(
                providers.plan, {**self.graph(), "categoryId": "food"}
            )
        with self.assertRaisesRegex(ValueError, "another target location"):
            attach_referral_graph_to_query_plan(
                providers.plan, {**self.graph(), "targetLocation": "Phoenix"}
            )
        invalid_stage = normalize_referral_graph(self.graph(stageKey="housing-only-stage"))
        configuration = providers.configuration("fixture-invalid-referral-stage")
        configuration["queryPlan"] = attach_referral_graph_to_query_plan(
            configuration["queryPlan"], invalid_stage
        )
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(
                OptimizationPipelineError, "outside the selected playbook"
            ):
                OptimizationDiscoveryPipeline(
                    ResearchStore(Path(directory) / "research.sqlite3"),
                    configuration,
                    search=providers.search,
                    fetch=providers.fetch,
                    resolve_identity=providers.resolve,
                    referral_graph=invalid_stage,
                )

    def test_pipeline_fetches_destination_and_counts_only_qualified_program(self) -> None:
        providers = FixtureProviders()
        graph = normalize_referral_graph(self.graph())
        configuration = providers.configuration("fixture-referral-graph")
        configuration["queryPlan"] = attach_referral_graph_to_query_plan(
            configuration["queryPlan"], graph
        )
        destination = graph["edges"][0]["destinationUrl"]

        def resolve(result: dict):
            if result.get("url") == destination:
                return qualified_identity(
                    "Referral Provider",
                    "Current Program",
                    directDomains=["provider.example"],
                )
            return providers.resolve(result)

        def fetch(url: str) -> dict:
            if url == destination:
                return {
                    "text": "Current provider page with a direct Mesa intake path.",
                    "finalUrl": url,
                    "statusCode": 200,
                    "contentType": "text/html",
                }
            return providers.fetch(url)

        with tempfile.TemporaryDirectory() as directory:
            store = ResearchStore(Path(directory) / "research.sqlite3")
            result = OptimizationDiscoveryPipeline(
                store,
                configuration,
                search=providers.search,
                fetch=fetch,
                resolve_identity=resolve,
                existing_resources=providers.fixture["existingResources"],
                referral_graph=graph,
            ).run()
            self.assertEqual(1, result.referral_edge_count)
            self.assertEqual(25, result.query_count)
            self.assertEqual(8, result.eligible_identity_count)
            self.assertEqual(8, result.packet_count)
            with store.connect() as connection:
                edge = connection.execute(
                    "SELECT status, lead_id, context FROM optimization_referral_edges"
                ).fetchone()
                self.assertEqual("expanded", edge["status"])
                lead = connection.execute(
                    """SELECT origin_type, origin_key, fetch_status
                       FROM optimization_discovery_leads WHERE id = ?""",
                    (edge["lead_id"],),
                ).fetchone()
                self.assertEqual("referral-edge", lead["origin_type"])
                self.assertEqual("fetched", lead["fetch_status"])
                packet = json.loads(
                    connection.execute(
                        """SELECT packet_json FROM optimization_evidence_packets
                           WHERE identity_key = 'referral provider::current program'"""
                    ).fetchone()["packet_json"]
                )
            self.assertEqual(
                "Current provider page with a direct Mesa intake path.",
                packet["sources"][0]["extract"]["text"],
            )
            self.assertNotIn(edge["context"], packet["sources"][0]["extract"]["text"])

    def test_referral_expansion_resume_does_not_repeat_completed_edge(self) -> None:
        providers = FixtureProviders()
        graph = normalize_referral_graph(self.graph())
        configuration = providers.configuration("fixture-referral-resume")
        configuration["queryPlan"] = attach_referral_graph_to_query_plan(
            configuration["queryPlan"], graph
        )
        destination = graph["edges"][0]["destinationUrl"]
        resolution_count = 0
        interrupted = False

        def resolve(result: dict):
            nonlocal resolution_count
            if result.get("url") == destination:
                resolution_count += 1
                return qualified_identity(
                    "Referral Provider",
                    "Current Program",
                    directDomains=["provider.example"],
                )
            return providers.resolve(result)

        def progress(event: dict) -> None:
            nonlocal interrupted
            if event["phase"] == "referral-expansion" and not interrupted:
                interrupted = True
                raise RuntimeError("fixture referral interruption")

        def pipeline(store: ResearchStore, callback=None) -> OptimizationDiscoveryPipeline:
            return OptimizationDiscoveryPipeline(
                store,
                configuration,
                search=providers.search,
                fetch=lambda url: {
                    "text": "Current provider page",
                    "finalUrl": url,
                    "statusCode": 200,
                    "contentType": "text/html",
                }
                if url == destination
                else providers.fetch(url),
                resolve_identity=resolve,
                existing_resources=providers.fixture["existingResources"],
                referral_graph=graph,
                progress=callback,
            )

        with tempfile.TemporaryDirectory() as directory:
            store = ResearchStore(Path(directory) / "research.sqlite3")
            with self.assertRaisesRegex(OptimizationPipelineError, "interruption"):
                pipeline(store, progress).run()
            result = pipeline(store).run()
            self.assertEqual(8, result.packet_count)
            self.assertEqual(1, resolution_count)

    def test_referral_graph_uses_a_non_housing_playbook_stage(self) -> None:
        providers = FixtureProviders()
        graph_value = self.graph(
            sourceUrl="https://county.example/food/resources",
            sourceTitle="County food resources",
            destinationUrl="https://pantry.example/current-program",
            organization="Example Pantry",
            program="Food Box Program",
            stageKey="immediate-food",
        )
        graph_value["categoryId"] = "food"
        graph = normalize_referral_graph(graph_value)
        configuration = providers.configuration("fixture-food-referral")
        configuration["targetCategoryId"] = "food"
        configuration["stageKey"] = "immediate-food"
        configuration["queryPlan"] = {
            "schemaVersion": 4,
            "candidateQualificationPolicyVersion": "candidate-qualification-gates-v2",
            "categoryId": "food",
            "stageKey": "immediate-food",
            "targetLocation": "Mesa",
            "regionalScope": "Maricopa County and nearby areas",
            "branches": [
                {
                    "key": "direct-food",
                    "purpose": "Current direct food access",
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
                            "purpose": "Current direct food access",
                            "query": "Mesa current food box",
                        }
                    ],
                }
            ],
        }
        configuration["queryPlan"] = attach_referral_graph_to_query_plan(
            configuration["queryPlan"], graph
        )
        destination = graph["edges"][0]["destinationUrl"]
        with tempfile.TemporaryDirectory() as directory:
            result = OptimizationDiscoveryPipeline(
                ResearchStore(Path(directory) / "research.sqlite3"),
                configuration,
                search=lambda _query, _maximum: [],
                fetch=lambda url: {
                    "text": "Current direct food-box intake details.",
                    "finalUrl": url,
                    "statusCode": 200,
                    "contentType": "text/html",
                },
                resolve_identity=lambda result: qualified_identity(
                    "Example Pantry",
                    "Food Box Program",
                    directDomains=["pantry.example"],
                )
                if result.get("url") == destination
                else None,
                referral_graph=graph,
            ).run()
        self.assertEqual(1, result.referral_edge_count)
        self.assertEqual(1, result.packet_count)


if __name__ == "__main__":
    unittest.main()
