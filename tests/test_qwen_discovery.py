from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from resource_research_agent.optimization import build_housing_urgent_query_plan
from resource_research_agent.optimization_pipeline import (
    OptimizationDiscoveryPipeline,
    OptimizationPipelineError,
    canonicalize_discovery_url,
    source_authority,
)
from resource_research_agent.storage import ResearchStore


FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "housing_qwen" / "stage1"


class FixtureProviders:
    def __init__(self) -> None:
        self.fixture = json.loads((FIXTURE_ROOT / "manifest.json").read_text(encoding="utf-8"))
        self.plan = build_housing_urgent_query_plan(
            "Mesa", "Maricopa County and nearby areas"
        )
        self.query_keys = {
            query["query"]: query["key"]
            for branch in self.plan["branches"]
            for query in branch["queries"]
        }
        self.search_calls: list[str] = []
        self.search_result_limits: list[int] = []
        self.fetch_calls: list[str] = []

    def search(self, query: str, max_results: int) -> list[dict]:
        key = self.query_keys[query]
        self.search_calls.append(key)
        self.search_result_limits.append(max_results)
        return deepcopy(self.fixture["searchResults"].get(key, []))

    def fetch(self, url: str) -> dict:
        canonical = canonicalize_discovery_url(url)
        self.fetch_calls.append(canonical)
        record = deepcopy(self.fixture["fetches"][canonical])
        record["text"] = (FIXTURE_ROOT / record.pop("pageFile")).read_text(encoding="utf-8")
        record["finalUrl"] = canonical
        record["truncated"] = False
        return record

    @staticmethod
    def resolve(result: dict) -> dict | None:
        identity = result.get("identity")
        return deepcopy(identity) if isinstance(identity, dict) else None

    def configuration(self, label: str) -> dict:
        return {
            "label": label,
            "modelArtifact": "none",
            "quantization": "none",
            "modelProvider": "none",
            "modelEndpoint": "none",
            "mlxVersion": "not-used",
            "dshVersion": "not-used",
            "searchProvider": "ddgs",
            "fetchProvider": "safe-http",
            "searchPluginVersion": "fixture-v1",
            "fetchPluginVersion": "fixture-v1",
            "promptPolicyVersion": "no-model-discovery-v1",
            "playbookVersion": "1.1.0",
            "sourcePackageSha256": "c7a2251d7d638472f90207c24a28ec71c24515ea5d1aafced68a38fdce3d30f8",
            "sourcePackageVersion": "fixture",
            "targetLocation": "Mesa",
            "regionalScope": "Maricopa County and nearby areas",
            "targetCategoryId": "housing",
            "stageKey": "urgent-access",
            "limits": {
                "modelFallbacks": [],
                "searchFallbacks": [],
                "searchResultsPerQuery": 11,
                "fetchMaxBytes": 200000,
            },
            "stoppingRules": {
                "minimumQueries": 2,
                "maximumQueries": 6,
                "consecutiveNoNewIdentityQueries": 2,
            },
            "queryPlan": self.plan,
        }


class DiscoveryPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.store = ResearchStore(Path(self.temporary.name) / "research.sqlite3")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def pipeline(
        self,
        providers: FixtureProviders,
        label: str,
        *,
        progress=None,
    ) -> OptimizationDiscoveryPipeline:
        return OptimizationDiscoveryPipeline(
            self.store,
            providers.configuration(label),
            search=providers.search,
            fetch=providers.fetch,
            resolve_identity=providers.resolve,
            existing_resources=providers.fixture["existingResources"],
            progress=progress,
        )

    def test_fixture_stage_builds_complete_inspectable_corpus_without_qwen(self) -> None:
        providers = FixtureProviders()
        result = self.pipeline(providers, "fixture-housing-stage").run()

        self.assertEqual(9, result.branch_count)
        self.assertEqual(26, result.query_count)
        self.assertEqual(9, result.lead_count)
        self.assertEqual(9, result.identity_count)
        self.assertEqual(8, result.eligible_identity_count)
        self.assertEqual(1, result.excluded_identity_count)
        self.assertEqual(8, result.source_count)
        self.assertEqual(8, result.packet_count)
        self.assertEqual(26, len(providers.search_calls))
        self.assertEqual({11}, set(providers.search_result_limits))
        self.assertEqual(8, len(providers.fetch_calls))

        with self.store.connect() as connection:
            configuration = connection.execute(
                "SELECT * FROM optimization_configurations WHERE id = ?",
                (result.configuration_id,),
            ).fetchone()
            self.assertEqual("none", configuration["model_artifact"])
            self.assertEqual("none", configuration["quantization"])
            self.assertEqual(
                {"saturated"},
                {
                    row["status"]
                    for row in connection.execute(
                        "SELECT status FROM optimization_coverage_branches WHERE run_id = ?",
                        (result.run_id,),
                    ).fetchall()
                },
            )
            self.assertEqual(
                26,
                connection.execute(
                    "SELECT COUNT(*) FROM optimization_query_attempts"
                ).fetchone()[0],
            )
            self.assertEqual(
                8,
                connection.execute(
                    "SELECT COUNT(*) FROM optimization_fetch_attempts"
                ).fetchone()[0],
            )
            authorities = {
                row["authority"]: row["count"]
                for row in connection.execute(
                    """SELECT authority, COUNT(*) AS count
                       FROM optimization_evidence_sources GROUP BY authority"""
                ).fetchall()
            }
            self.assertEqual(
                {"direct-provider": 6, "government-referral": 2}, authorities
            )
            rapid = connection.execute(
                """SELECT package_match_state, boundary_state
                   FROM optimization_candidate_identities
                   WHERE identity_key = 'a new leaf::rapid re housing'"""
            ).fetchone()
            self.assertEqual("different-program", rapid["package_match_state"])
            self.assertEqual("resolved", rapid["boundary_state"])
            excluded = connection.execute(
                """SELECT package_match_state, boundary_state
                   FROM optimization_candidate_identities
                   WHERE identity_key = 'housing authority of maricopa county::housing choice voucher'"""
            ).fetchone()
            self.assertEqual("same-program", excluded["package_match_state"])
            self.assertEqual("excluded-existing", excluded["boundary_state"])
            county = connection.execute(
                """SELECT executed_query_count, new_lead_count,
                          new_eligible_identity_count,
                          consecutive_no_new_eligible_identities
                   FROM optimization_coverage_branches
                   WHERE run_id = ? AND branch_key = 'official-county'""",
                (result.run_id,),
            ).fetchone()
            self.assertEqual(2, county["executed_query_count"])
            self.assertEqual(1, county["new_lead_count"])
            self.assertEqual(0, county["new_eligible_identity_count"])
            self.assertEqual(2, county["consecutive_no_new_eligible_identities"])
            packets = connection.execute(
                "SELECT packet_json FROM optimization_evidence_packets WHERE corpus_id = ?",
                (result.corpus_id,),
            ).fetchall()
            self.assertTrue(
                all(json.loads(row["packet_json"])["sources"] for row in packets)
            )
            corpus = connection.execute(
                "SELECT status FROM optimization_corpora WHERE id = ?", (result.corpus_id,)
            ).fetchone()
            self.assertEqual("frozen", corpus["status"])
            with self.assertRaisesRegex(sqlite3.IntegrityError, "immutable"):
                connection.execute(
                    "UPDATE optimization_corpora SET corpus_sha256 = ? WHERE id = ?",
                    ("f" * 64, result.corpus_id),
                )

    def test_resume_after_discovery_interruption_does_not_repeat_completed_query(self) -> None:
        providers = FixtureProviders()
        interrupted = False

        def stop_after_first_query(event: dict) -> None:
            nonlocal interrupted
            if event["phase"] == "discovery" and not interrupted:
                interrupted = True
                raise RuntimeError("fixture discovery interruption")

        with self.assertRaisesRegex(OptimizationPipelineError, "interruption"):
            self.pipeline(
                providers, "fixture-discovery-resume", progress=stop_after_first_query
            ).run()
        self.assertEqual(["official-city-1"], providers.search_calls)

        result = self.pipeline(providers, "fixture-discovery-resume").run()
        self.assertEqual(26, result.query_count)
        self.assertEqual(1, providers.search_calls.count("official-city-1"))
        with self.store.connect() as connection:
            attempt_count = connection.execute(
                """SELECT COUNT(*) FROM optimization_query_attempts AS attempt
                   JOIN optimization_queries AS query ON query.id = attempt.query_id
                   WHERE query.query_key = 'official-city-1'"""
            ).fetchone()[0]
        self.assertEqual(1, attempt_count)

    def test_resume_after_fetch_interruption_does_not_repeat_completed_fetch(self) -> None:
        providers = FixtureProviders()
        interrupted = False

        def stop_after_first_fetch(event: dict) -> None:
            nonlocal interrupted
            if event["phase"] == "fetch" and not interrupted:
                interrupted = True
                raise RuntimeError("fixture fetch interruption")

        with self.assertRaisesRegex(OptimizationPipelineError, "interruption"):
            self.pipeline(
                providers, "fixture-fetch-resume", progress=stop_after_first_fetch
            ).run()
        first_url = providers.fetch_calls[0]

        result = self.pipeline(providers, "fixture-fetch-resume").run()
        self.assertEqual(8, result.packet_count)
        self.assertEqual(1, providers.fetch_calls.count(first_url))
        self.assertEqual(8, len(providers.fetch_calls))

    def test_restart_marks_inflight_attempt_failed_and_retries_only_that_query(self) -> None:
        providers = FixtureProviders()

        def crash_during_query(_query: str, _max_results: int) -> list[dict]:
            raise KeyboardInterrupt("fixture process stop")

        pipeline = OptimizationDiscoveryPipeline(
            self.store,
            providers.configuration("fixture-process-restart"),
            search=crash_during_query,
            fetch=providers.fetch,
            resolve_identity=providers.resolve,
            existing_resources=providers.fixture["existingResources"],
        )
        with self.assertRaises(KeyboardInterrupt):
            pipeline.run()

        self.store = ResearchStore(self.store.path)
        result = self.pipeline(providers, "fixture-process-restart").run()
        self.assertEqual(8, result.packet_count)
        with self.store.connect() as connection:
            attempts = connection.execute(
                """SELECT attempt.status FROM optimization_query_attempts AS attempt
                   JOIN optimization_queries AS query ON query.id = attempt.query_id
                   WHERE query.query_key = 'official-city-1'
                   ORDER BY attempt.attempt_number"""
            ).fetchall()
        self.assertEqual(["failed", "completed"], [row["status"] for row in attempts])


class DiscoveryPolicyTests(unittest.TestCase):
    def test_url_canonicalization_collapses_tracking_and_fragments(self) -> None:
        self.assertEqual(
            "https://example.org/help?a=1&b=2",
            canonicalize_discovery_url(
                "HTTPS://Example.org:443/help/?b=2&utm_source=test&a=1#hours"
            ),
        )

    def test_authority_requires_direct_domain_or_known_authoritative_host(self) -> None:
        self.assertEqual(
            "direct-provider",
            source_authority(
                "https://program.example/intake", direct_domains=["program.example"]
            ),
        )
        self.assertEqual(
            "government-referral", source_authority("https://housing.az.gov/help")
        )
        self.assertEqual(
            "directory-lead", source_authority("https://directory.example/listing")
        )


if __name__ == "__main__":
    unittest.main()
