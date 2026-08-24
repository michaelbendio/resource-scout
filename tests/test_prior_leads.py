from __future__ import annotations

import unittest
import tempfile
from pathlib import Path

from resource_research_agent.optimization_housing_calibration import (
    build_housing_urgent_query_plan,
)
from resource_research_agent.prior_leads import (
    augment_query_plan_with_prior_leads,
    build_prior_lead_manifest,
    normalize_prior_lead_manifest,
)
from resource_research_agent.prior_lead_harvest import harvest_prior_leads
from resource_research_agent.optimization_pipeline import OptimizationDiscoveryPipeline
from resource_research_agent.storage import ResearchStore
from tests.test_qwen_discovery import FixtureProviders, qualified_identity


class PriorResultLeadManifestTests(unittest.TestCase):
    @staticmethod
    def manifest() -> dict:
        return build_prior_lead_manifest(
            manifest_id="mesa-housing-preserved-v1",
            category_id="housing",
            target_location="Mesa",
            created_at="2026-08-23T00:00:00+00:00",
            sources=[
                {
                    "id": "deepseek-run-1-stage-1",
                    "kind": "deepseek",
                    "sourceRunId": "1",
                    "sourceStageKey": "urgent-access",
                    "observedAt": "2026-08-20T04:38:22+00:00",
                    "artifactSha256": "a" * 64,
                },
                {
                    "id": "qwen-run-23-stage-1",
                    "kind": "qwen",
                    "sourceRunId": "23",
                    "sourceStageKey": "urgent-access",
                    "observedAt": "2026-08-21T18:24:56+00:00",
                },
            ],
            leads=[
                {
                    "organization": "Example Provider",
                    "program": "Shelter Program",
                    "aliases": ["Old Shelter Name"],
                    "urls": [
                        "HTTPS://Example.org:443/program/?utm_source=old#intake"
                    ],
                    "historicalDisposition": "candidate",
                    "provenance": [
                        {
                            "sourceId": "deepseek-run-1-stage-1",
                            "sourceRunId": "1",
                            "sourceStageKey": "urgent-access",
                            "observedAt": "2026-08-20T04:38:22+00:00",
                        }
                    ],
                },
                {
                    "aliases": ["Unresolved provider lead"],
                    "urls": ["https://leads.example.net/listing"],
                    "historicalDisposition": "unresolved",
                    "provenance": [
                        {
                            "sourceId": "qwen-run-23-stage-1",
                            "sourceRunId": "23",
                            "sourceStageKey": "urgent-access",
                            "observedAt": "2026-08-21T18:24:56+00:00",
                        }
                    ],
                },
            ],
        )

    def test_manifest_keeps_only_names_urls_and_historical_provenance(self) -> None:
        manifest = self.manifest()
        self.assertEqual("prior-result-leads-v1", manifest["policyVersion"])
        self.assertEqual(64, len(manifest["manifestSha256"]))
        identity = next(
            lead for lead in manifest["leads"] if lead["organization"]
        )
        self.assertEqual(["https://example.org/program"], identity["urls"])
        self.assertEqual(
            "identity:example provider::shelter program", identity["leadKey"]
        )
        self.assertNotIn("phone", identity)
        self.assertNotIn("eligibility", identity)

    def test_current_factual_claims_and_unknown_sources_are_rejected(self) -> None:
        manifest = self.manifest()
        with self.assertRaisesRegex(ValueError, "current factual fields"):
            normalize_prior_lead_manifest(
                {
                    **manifest,
                    "leads": [
                        {
                            **manifest["leads"][0],
                            "phone": "480-555-0100",
                        }
                    ],
                }
            )
        invalid_source = {
            **manifest,
            "leads": [
                {
                    **manifest["leads"][0],
                    "provenance": [
                        {
                            "sourceId": "missing-source",
                            "sourceRunId": "1",
                            "sourceStageKey": "urgent-access",
                            "observedAt": "2026-08-20T04:38:22+00:00",
                        }
                    ],
                }
            ],
        }
        with self.assertRaisesRegex(ValueError, "Unknown prior-result lead source"):
            normalize_prior_lead_manifest(invalid_source)

    def test_every_historical_lead_gets_a_current_search_without_early_saturation(self) -> None:
        plan = augment_query_plan_with_prior_leads(
            build_housing_urgent_query_plan(
                "Mesa", "Maricopa County and nearby areas"
            ),
            self.manifest(),
        )
        branch = plan["branches"][-1]
        self.assertEqual("prior-result-leads", branch["key"])
        self.assertEqual(2, branch["saturation"]["minimumQueries"])
        self.assertEqual(2, branch["saturation"]["maximumQueries"])
        self.assertEqual(2, len(branch["queries"]))
        self.assertTrue(all(query.get("priorLeadKey") for query in branch["queries"]))
        self.assertEqual(
            self.manifest()["manifestSha256"],
            plan["priorResultLeadManifestSha256"],
        )

    def test_manifest_category_and_location_must_match_the_query_plan(self) -> None:
        plan = build_housing_urgent_query_plan(
            "Mesa", "Maricopa County and nearby areas"
        )
        manifest = self.manifest()
        with self.assertRaisesRegex(ValueError, "another category"):
            augment_query_plan_with_prior_leads(
                plan, {**manifest, "categoryId": "food", "manifestSha256": ""}
            )
        with self.assertRaisesRegex(ValueError, "another target location"):
            augment_query_plan_with_prior_leads(
                plan, {**manifest, "targetLocation": "Phoenix", "manifestSha256": ""}
            )

    def test_pipeline_persists_manifest_but_counts_only_current_search_results(self) -> None:
        providers = FixtureProviders()
        manifest = self.manifest()
        configuration = providers.configuration("fixture-prior-result-leads")
        configuration["queryPlan"] = augment_query_plan_with_prior_leads(
            configuration["queryPlan"], manifest
        )
        current_url = "https://example.org/current-shelter"

        def search(query: str, maximum: int) -> list[dict]:
            if "current service intake" not in query:
                return providers.search(query, maximum)
            if '"Example Provider" "Shelter Program"' in query:
                return [
                    {
                        "url": current_url,
                        "title": "Current shelter program",
                        "identity": qualified_identity(
                            "Example Provider",
                            "Shelter Program",
                            directDomains=["example.org"],
                        ),
                    }
                ]
            return []

        def fetch(url: str) -> dict:
            if url == current_url:
                return {
                    "text": "The current program page confirms a Mesa intake path.",
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
                search=search,
                fetch=fetch,
                resolve_identity=providers.resolve,
                existing_resources=providers.fixture["existingResources"],
                prior_lead_manifest=manifest,
            ).run()
            self.assertEqual(2, result.prior_lead_count)
            self.assertEqual(27, result.query_count)
            self.assertEqual(8, result.eligible_identity_count)
            self.assertEqual(8, result.packet_count)
            with store.connect() as connection:
                self.assertEqual(
                    2,
                    connection.execute(
                        "SELECT COUNT(*) FROM optimization_prior_leads"
                    ).fetchone()[0],
                )
                self.assertEqual(
                    2,
                    connection.execute(
                        """SELECT COUNT(*) FROM optimization_queries
                           WHERE prior_lead_key != ''"""
                    ).fetchone()[0],
                )
                self.assertEqual(
                    1,
                    connection.execute(
                        """SELECT COUNT(*) FROM optimization_candidate_identities
                           WHERE organization = 'Example Provider'
                             AND program = 'Shelter Program'"""
                    ).fetchone()[0],
                )

    def test_harvest_imports_names_and_urls_but_not_historical_claims(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "research.sqlite3"
            store = ResearchStore(database)
            run_id = store.create_research_run(
                "dsh",
                "Historical fixture",
                {},
                research_mode="package",
                target_location="Mesa",
                regional_scope="Maricopa County",
                target_category_id="housing",
                target_category_label="Housing",
                stages=[
                    {
                        "key": "urgent-access",
                        "title": "Urgent",
                        "instruction": "Find urgent programs",
                    }
                ],
            )
            stage_id = store.list_run_stages(run_id)[0]["id"]
            store.save_discovery(
                {
                    "name": "Historical Shelter",
                    "organization": "Example Provider",
                    "program": "Shelter Program",
                    "website": "https://example.org/shelter?utm_source=old",
                    "phone": "480-555-0199",
                    "eligibility": ["Historical claim must not be imported"],
                    "evidence": [
                        {
                            "url": "https://example.org/evidence",
                            "finding": "Historical service claim",
                        }
                    ],
                },
                run_id=run_id,
                stage_id=stage_id,
            )
            manifest = harvest_prior_leads(
                database,
                manifest_id="fixture-harvest-v1",
                category_id="housing",
                target_location="Mesa",
                created_at="2026-08-23T00:00:00+00:00",
                database_sha256="b" * 64,
                research_runs=[(run_id, "deepseek")],
                optimization_discovery_run_ids=[],
            )
        self.assertEqual(1, len(manifest["leads"]))
        lead = manifest["leads"][0]
        self.assertEqual("Example Provider", lead["organization"])
        self.assertEqual("Shelter Program", lead["program"])
        self.assertEqual(
            ["https://example.org/evidence", "https://example.org/shelter"],
            lead["urls"],
        )
        self.assertNotIn("phone", lead)
        self.assertNotIn("eligibility", lead)
        self.assertNotIn("finding", lead)


if __name__ == "__main__":
    unittest.main()
