from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from resource_research_agent.optimization import (
    canonicalize_discovery_url,
    EVIDENCE_PREPARATION_POLICY_VERSION,
)
from resource_research_agent.optimization_housing_calibration import (
    build_housing_urgent_query_plan,
)
from resource_research_agent.optimization_pipeline import (
    OptimizationDiscoveryPipeline,
    OptimizationPipelineError,
    source_authority,
)
from resource_research_agent.storage import ResearchStore


FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "housing_qwen" / "stage1"


def qualified_identity(
    organization: str,
    program: str,
    **values,
) -> dict:
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
        if not isinstance(identity, dict):
            return None
        resolved = qualified_identity(
            str(identity.get("organization") or ""),
            str(identity.get("program") or ""),
            **{
                key: deepcopy(value)
                for key, value in identity.items()
                if key not in {"organization", "program"}
            },
        )
        if resolved["program"] == "State Shelter Referral":
            resolved.update(
                {
                    "candidateRole": "referral-system",
                    "actionabilityState": "informational-only",
                }
            )
        elif resolved["program"] == "Brian Garcia Welcome Center":
            resolved["candidateRole"] = "access-assessment-service"
        return resolved

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
            "playbookVersion": "1.2.0",
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
        self.assertEqual(25, result.query_count)
        self.assertEqual(10, result.lead_count)
        self.assertEqual(10, result.identity_count)
        self.assertEqual(7, result.eligible_identity_count)
        self.assertEqual(1, result.noncandidate_identity_count)
        self.assertEqual(0, result.review_required_identity_count)
        self.assertEqual(1, result.routed_identity_count)
        self.assertEqual(1, result.excluded_identity_count)
        self.assertEqual(7, result.source_count)
        self.assertEqual(7, result.packet_count)
        self.assertEqual(25, len(providers.search_calls))
        self.assertEqual({11}, set(providers.search_result_limits))
        self.assertEqual(7, len(providers.fetch_calls))

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
                25,
                connection.execute(
                    "SELECT COUNT(*) FROM optimization_query_attempts"
                ).fetchone()[0],
            )
            self.assertEqual(
                7,
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
                {"direct-provider": 6, "government-referral": 1}, authorities
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
            referral = connection.execute(
                """SELECT candidate_role, promotion_state
                   FROM optimization_candidate_identities
                   WHERE identity_key = 'arizona department of housing::state shelter referral'"""
            ).fetchone()
            self.assertEqual("referral-system", referral["candidate_role"])
            self.assertEqual("noncandidate", referral["promotion_state"])
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
            routed = connection.execute(
                """SELECT target_stage_key, boundary_state
                   FROM optimization_candidate_identities
                   WHERE identity_key = 'city of mesa::eviction prevention program'"""
            ).fetchone()
            self.assertEqual("stabilization", routed["target_stage_key"])
            self.assertEqual("resolved", routed["boundary_state"])
            self.assertNotIn(
                "https://mesaaz.gov/housing/eviction-prevention",
                providers.fetch_calls,
            )
            self.assertNotIn(
                "https://housing.az.gov/emergency/shelter-referral",
                providers.fetch_calls,
            )
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

    def test_reviewed_referral_page_can_create_separate_bounded_program_packets(self) -> None:
        providers = FixtureProviders()
        configuration = providers.configuration("fixture-referral-expansion")
        configuration["limits"]["referralEvidenceContextCharacters"] = 12
        referral_url = "https://mesaaz.gov/housing/homeless-resources"

        def search(query: str, _maximum: int) -> list[dict]:
            if providers.query_keys[query] != "official-city-1":
                return []
            return [
                {
                    "url": referral_url,
                    "title": "Homeless Resources",
                    "identities": [
                        qualified_identity(
                            "City of Mesa",
                            "Homeless Resource Line",
                            directDomains=["mesaaz.gov"],
                            evidenceExcerpt="Homeless Resource Line 480-644-HOPE",
                        ),
                        qualified_identity(
                            "City of Mesa",
                            "Street Outreach Services",
                            directDomains=["mesaaz.gov"],
                            evidenceExcerpt="Street Outreach Services 602-346-3361",
                        ),
                    ],
                }
            ]

        fetch_calls = []

        def fetch(url: str) -> dict:
            fetch_calls.append(url)
            return {
                "text": (
                    "prefix Homeless Resource Line 480-644-HOPE "
                    + "unrelated " * 40
                    + "Street Outreach Services 602-346-3361 suffix"
                ),
                "finalUrl": url,
                "statusCode": 200,
                "contentType": "text/html",
                "truncated": False,
            }

        pipeline = OptimizationDiscoveryPipeline(
            self.store,
            configuration,
            search=search,
            fetch=fetch,
            resolve_identity=lambda result: result.get("identities"),
        )
        result = pipeline.run()
        self.assertEqual(2, result.identity_count)
        self.assertEqual(2, result.packet_count)
        self.assertEqual(2, result.source_count)
        self.assertEqual([referral_url], fetch_calls)
        with self.store.connect() as connection:
            packets = [
                json.loads(row["packet_json"])
                for row in connection.execute(
                    """SELECT packet_json FROM optimization_evidence_packets
                       WHERE corpus_id = ? ORDER BY identity_key""",
                    (result.corpus_id,),
                ).fetchall()
            ]
        extracts = [packet["sources"][0]["extract"] for packet in packets]
        self.assertTrue(
            all(
                extract["selection"]["method"] == "reviewed-exact-excerpt"
                for extract in extracts
            )
        )
        self.assertNotEqual(extracts[0]["text"], extracts[1]["text"])
        self.assertTrue(all(len(extract["text"]) < 80 for extract in extracts))

    def test_current_policy_keeps_complete_bounded_direct_provider_page(self) -> None:
        providers = FixtureProviders()
        configuration = providers.configuration("fixture-complete-direct-evidence")
        configuration["limits"]["evidencePreparationPolicyVersion"] = (
            EVIDENCE_PREPARATION_POLICY_VERSION
        )
        direct_url = "https://provider.example.org/program"
        identity = qualified_identity(
            "Example Provider",
            "Example Program",
            reviewedAuthority="direct-provider",
            evidenceSelection={"mode": "full-page"},
            identitySupport={
                "organization": {
                    "relationship": "exact-label",
                    "sourceLabel": "Example Provider",
                    "evidenceExcerpt": "Example Provider",
                },
                "program": {
                    "relationship": "exact-label",
                    "sourceLabel": "Example Program",
                    "evidenceExcerpt": "Example Program",
                },
            },
        )

        def search(query: str, _maximum: int) -> list[dict]:
            if providers.query_keys[query] != "official-city-1":
                return []
            return [{"url": direct_url, "title": "Example Program", "identity": identity}]

        complete_text = (
            "Example Provider\nExample Program\n"
            + ("Program description. " * 260)
            + "Complete final eligibility requirement."
        )

        result = OptimizationDiscoveryPipeline(
            self.store,
            configuration,
            search=search,
            fetch=lambda url: {
                "text": complete_text,
                "finalUrl": url,
                "statusCode": 200,
                "contentType": "text/html",
                "truncated": False,
            },
            resolve_identity=lambda value: value.get("identity"),
        ).run()
        with self.store.connect() as connection:
            packet = json.loads(
                connection.execute(
                    "SELECT packet_json FROM optimization_evidence_packets WHERE corpus_id = ?",
                    (result.corpus_id,),
                ).fetchone()["packet_json"]
            )
        extract = packet["sources"][0]["extract"]
        self.assertEqual(complete_text, extract["text"])
        self.assertEqual("reviewed-full-page", extract["selection"]["method"])
        self.assertIn("Complete final eligibility requirement.", extract["text"])
        self.assertEqual(identity["identitySupport"], extract["identitySupport"])

    def test_current_policy_uses_exact_non_housing_section_without_sibling_facts(
        self,
    ) -> None:
        providers = FixtureProviders()
        configuration = providers.configuration("fixture-food-reviewed-section")
        configuration.update(
            {
                "targetCategoryId": "food",
                "stageKey": "immediate-food",
                "targetLocation": "Provo",
                "regionalScope": "Utah County",
                "queryPlan": {
                    "schemaVersion": 4,
                    "candidateQualificationPolicyVersion": (
                        "candidate-qualification-gates-v2"
                    ),
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
                },
            }
        )
        configuration["limits"]["evidencePreparationPolicyVersion"] = (
            EVIDENCE_PREPARATION_POLICY_VERSION
        )
        url = "https://county.example.gov/food-directory"
        identity = qualified_identity(
            "Community Pantry",
            "Weekly Food Distribution",
            stageKey="immediate-food",
            reviewedAuthority="government-referral",
            evidenceSelection={
                "mode": "reviewed-section",
                "startExcerpt": "Community Pantry — Weekly Food Distribution",
                "endExcerpt": "Call 555-0100 to arrange pickup.",
            },
            identitySupport={
                "organization": {
                    "relationship": "exact-label",
                    "sourceLabel": "Community Pantry",
                    "evidenceExcerpt": "Community Pantry — Weekly Food Distribution",
                },
                "program": {
                    "relationship": "exact-label",
                    "sourceLabel": "Weekly Food Distribution",
                    "evidenceExcerpt": "Community Pantry — Weekly Food Distribution",
                },
            },
        )
        page = (
            "County food directory\n"
            "Community Pantry — Weekly Food Distribution\n"
            "Fresh food is available Tuesdays. Call 555-0100 to arrange pickup.\n"
            "Sibling Pantry — Senior Delivery\n"
            "Only adults age 65+ may call 555-9999."
        )
        result = OptimizationDiscoveryPipeline(
            self.store,
            configuration,
            search=lambda query, _maximum: (
                [
                    {
                        "url": url,
                        "title": "Stale result title concatenated with a sibling",
                        "identity": identity,
                    }
                ]
                if query == "Provo current food pantry intake"
                else []
            ),
            fetch=lambda value: {
                "text": page,
                "finalUrl": value,
                "statusCode": 200,
                "contentType": "text/html",
                "truncated": False,
            },
            resolve_identity=lambda value: value.get("identity"),
        ).run()
        with self.store.connect() as connection:
            packet = json.loads(
                connection.execute(
                    "SELECT packet_json FROM optimization_evidence_packets WHERE corpus_id = ?",
                    (result.corpus_id,),
                ).fetchone()["packet_json"]
            )
        source = packet["sources"][0]
        self.assertEqual("government-referral", source["authority"])
        self.assertEqual("County food directory", source["extract"]["title"])
        self.assertEqual("reviewed-exact-section", source["extract"]["selection"]["method"])
        self.assertNotIn("Sibling Pantry", source["extract"]["text"])
        self.assertNotIn("555-9999", source["extract"]["text"])

    def test_current_policy_rejects_identity_receipt_absent_from_selected_evidence(
        self,
    ) -> None:
        providers = FixtureProviders()
        configuration = providers.configuration("fixture-unsupported-identity-label")
        configuration["limits"]["evidencePreparationPolicyVersion"] = (
            EVIDENCE_PREPARATION_POLICY_VERSION
        )
        url = "https://provider.example.org/intake"
        identity = qualified_identity(
            "Example Provider",
            "Invented Canonical Program Name",
            reviewedAuthority="direct-provider",
            evidenceSelection={"mode": "full-page"},
            identitySupport={
                "organization": {
                    "relationship": "exact-label",
                    "sourceLabel": "Example Provider",
                    "evidenceExcerpt": "Example Provider",
                },
                "program": {
                    "relationship": "reviewed-alias",
                    "sourceLabel": "Published Program Name",
                    "evidenceExcerpt": "Published Program Name",
                    "reason": "Reviewer asserted a canonical alias.",
                },
            },
        )

        with self.assertRaisesRegex(
            OptimizationPipelineError, "program identity evidence is absent"
        ):
            OptimizationDiscoveryPipeline(
                self.store,
                configuration,
                search=lambda query, _maximum: (
                    [{"url": url, "title": "Intake", "identity": identity}]
                    if providers.query_keys[query] == "official-city-1"
                    else []
                ),
                fetch=lambda value: {
                    "text": "Example Provider offers current intake.",
                    "finalUrl": value,
                    "statusCode": 200,
                    "contentType": "text/html",
                    "truncated": False,
                },
                resolve_identity=lambda value: value.get("identity"),
            ).run()

    def test_current_policy_combines_ordered_sections_without_middle_entity(self) -> None:
        providers = FixtureProviders()
        configuration = providers.configuration("fixture-multiple-reviewed-sections")
        configuration["limits"]["evidencePreparationPolicyVersion"] = (
            EVIDENCE_PREPARATION_POLICY_VERSION
        )
        url = "https://provider.example.org/program-and-properties"
        identity = qualified_identity(
            "Example Provider",
            "Example Program",
            reviewedAuthority="direct-provider",
            evidenceSelection={
                "mode": "reviewed-sections",
                "sections": [
                    {
                        "startExcerpt": "Example Provider — Example Program",
                        "endExcerpt": "Candidate-wide supportive services are available.",
                    },
                    {
                        "startExcerpt": "How to apply to Example Program",
                        "endExcerpt": "Call the central intake line at 555-0100.",
                    },
                ],
            },
            identitySupport={
                "organization": {
                    "relationship": "exact-label",
                    "sourceLabel": "Example Provider",
                    "evidenceExcerpt": "Example Provider — Example Program",
                },
                "program": {
                    "relationship": "exact-label",
                    "sourceLabel": "Example Program",
                    "evidenceExcerpt": "Example Provider — Example Program",
                },
            },
        )
        page = (
            "Example Provider — Example Program\n"
            "Candidate-wide supportive services are available.\n"
            "Property Alpha\nOnly veterans at this property may call 555-9999.\n"
            "How to apply to Example Program\n"
            "Call the central intake line at 555-0100."
        )
        result = OptimizationDiscoveryPipeline(
            self.store,
            configuration,
            search=lambda query, _maximum: (
                [{"url": url, "title": "Program and properties", "identity": identity}]
                if providers.query_keys[query] == "official-city-1"
                else []
            ),
            fetch=lambda value: {
                "text": page,
                "finalUrl": value,
                "statusCode": 200,
                "contentType": "text/html",
                "truncated": False,
            },
            resolve_identity=lambda value: value.get("identity"),
        ).run()
        with self.store.connect() as connection:
            packet = json.loads(
                connection.execute(
                    "SELECT packet_json FROM optimization_evidence_packets WHERE corpus_id = ?",
                    (result.corpus_id,),
                ).fetchone()["packet_json"]
            )
        extract = packet["sources"][0]["extract"]
        self.assertEqual("reviewed-exact-sections", extract["selection"]["method"])
        self.assertEqual(2, len(extract["selection"]["sections"]))
        self.assertIn("Candidate-wide supportive services", extract["text"])
        self.assertIn("central intake line", extract["text"])
        self.assertNotIn("Property Alpha", extract["text"])
        self.assertNotIn("555-9999", extract["text"])

        reversed_identity = deepcopy(identity)
        reversed_identity["evidenceSelection"]["sections"].reverse()
        reversed_configuration = deepcopy(configuration)
        reversed_configuration["label"] = "fixture-reversed-reviewed-sections"
        with self.assertRaisesRegex(
            OptimizationPipelineError, "overlap or are out of order"
        ):
            OptimizationDiscoveryPipeline(
                self.store,
                reversed_configuration,
                search=lambda query, _maximum: (
                    [
                        {
                            "url": url,
                            "title": "Program and properties",
                            "identity": reversed_identity,
                        }
                    ]
                    if providers.query_keys[query] == "official-city-1"
                    else []
                ),
                fetch=lambda value: {
                    "text": page,
                    "finalUrl": value,
                    "statusCode": 200,
                    "contentType": "text/html",
                    "truncated": False,
                },
                resolve_identity=lambda value: value.get("identity"),
            ).run()

    def test_current_policy_requires_sections_for_multi_identity_page(self) -> None:
        providers = FixtureProviders()
        configuration = providers.configuration("fixture-multi-identity-full-page")
        configuration["limits"]["evidencePreparationPolicyVersion"] = (
            EVIDENCE_PREPARATION_POLICY_VERSION
        )
        url = "https://referrer.example.org/programs"

        def identity(organization: str, program: str) -> dict:
            return qualified_identity(
                organization,
                program,
                reviewedAuthority="government-referral",
                evidenceSelection={"mode": "full-page"},
                identitySupport={
                    "organization": {
                        "relationship": "exact-label",
                        "sourceLabel": organization,
                        "evidenceExcerpt": organization,
                    },
                    "program": {
                        "relationship": "exact-label",
                        "sourceLabel": program,
                        "evidenceExcerpt": program,
                    },
                },
            )

        fetch_calls: list[str] = []
        with self.assertRaisesRegex(
            OptimizationPipelineError, "requires exact reviewed sections"
        ):
            OptimizationDiscoveryPipeline(
                self.store,
                configuration,
                search=lambda query, _maximum: (
                    [
                        {
                            "url": url,
                            "title": "Programs",
                            "identities": [
                                identity("Provider One", "Program One"),
                                identity("Provider Two", "Program Two"),
                            ],
                        }
                    ]
                    if providers.query_keys[query] == "official-city-1"
                    else []
                ),
                fetch=lambda value: fetch_calls.append(value) or {},
                resolve_identity=lambda value: value.get("identities"),
            ).run()
        self.assertEqual([], fetch_calls)

    def test_reviewed_excerpt_and_authority_are_bound_to_each_source(self) -> None:
        providers = FixtureProviders()
        configuration = providers.configuration("fixture-source-specific-review")
        direct_url = "https://provider.example.org/program"
        supporting_url = "https://news.example.net/report"

        def search(query: str, _maximum: int) -> list[dict]:
            key = providers.query_keys[query]
            if key == "official-city-1":
                return [
                    {
                        "url": direct_url,
                        "title": "Direct program page",
                        "identity": qualified_identity(
                            "Example Provider",
                            "Example Program",
                            directDomains=["example.org"],
                            evidenceExcerpt="Primary program evidence",
                        ),
                    }
                ]
            if key == "official-city-2":
                return [
                    {
                        "url": supporting_url,
                        "title": "Supporting report",
                        "identity": qualified_identity(
                            "Example Provider",
                            "Example Program",
                            reviewedAuthority="reputable-secondary",
                            evidenceExcerpt="Independent supporting evidence",
                        ),
                    }
                ]
            return []

        def fetch(url: str) -> dict:
            text = (
                "Primary program evidence and current intake details."
                if url == direct_url
                else "Independent supporting evidence about the same program."
            )
            return {
                "text": text,
                "finalUrl": url,
                "statusCode": 200,
                "contentType": "text/html",
                "truncated": False,
            }

        result = OptimizationDiscoveryPipeline(
            self.store,
            configuration,
            search=search,
            fetch=fetch,
            resolve_identity=lambda result: result.get("identity"),
        ).run()
        self.assertEqual(1, result.identity_count)
        self.assertEqual(2, result.source_count)
        with self.store.connect() as connection:
            sources = [
                dict(row)
                for row in connection.execute(
                    """SELECT canonical_url, authority, extract_json
                       FROM optimization_evidence_sources ORDER BY canonical_url"""
                ).fetchall()
            ]
            link_metadata = [
                json.loads(row["metadata_json"])
                for row in connection.execute(
                    """SELECT link.metadata_json
                       FROM optimization_identity_leads AS link
                       JOIN optimization_discovery_leads AS lead ON lead.id = link.lead_id
                       ORDER BY lead.canonical_url"""
                ).fetchall()
            ]
        self.assertEqual(
            ["reputable-secondary", "direct-provider"],
            [source["authority"] for source in sources],
        )
        self.assertEqual(
            ["Independent supporting evidence", "Primary program evidence"],
            [
                json.loads(source["extract_json"])["selection"]["excerpt"]
                for source in sources
            ],
        )
        self.assertEqual(
            ["Independent supporting evidence", "Primary program evidence"],
            [metadata["evidenceExcerpt"] for metadata in link_metadata],
        )

    def test_referral_page_preserves_its_own_identity(self) -> None:
        providers = FixtureProviders()
        configuration = providers.configuration("fixture-referral-page-identity")
        referral_url = "https://referrer.example.gov/access-points"

        def search(query: str, _maximum: int) -> list[dict]:
            if providers.query_keys[query] != "official-city-1":
                return []
            return [
                {
                    "url": referral_url,
                    "title": "Current access points",
                    "identity": qualified_identity(
                        "Referred Provider",
                        "Housing Assessment",
                        candidateRole="access-assessment-service",
                        reviewedAuthority="government-referral",
                        pageOrganization="Regional Housing Authority",
                        pageProgram="Access Point Directory",
                        evidenceExcerpt="Referred Provider offers housing assessment",
                    ),
                }
            ]

        def fetch(url: str) -> dict:
            return {
                "text": "Referred Provider offers housing assessment across the county.",
                "finalUrl": url,
                "statusCode": 200,
                "contentType": "text/html",
                "truncated": False,
            }

        result = OptimizationDiscoveryPipeline(
            self.store,
            configuration,
            search=search,
            fetch=fetch,
            resolve_identity=lambda result: result.get("identity"),
        ).run()
        self.assertEqual(1, result.packet_count)
        with self.store.connect() as connection:
            source = connection.execute(
                "SELECT page_identity_key, authority FROM optimization_evidence_sources"
            ).fetchone()
            metadata = json.loads(
                connection.execute(
                    "SELECT metadata_json FROM optimization_identity_leads"
                ).fetchone()["metadata_json"]
            )
        self.assertEqual(
            "regional housing authority::access point directory",
            source["page_identity_key"],
        )
        self.assertEqual("government-referral", source["authority"])
        self.assertEqual("Regional Housing Authority", metadata["pageOrganization"])
        self.assertEqual("Access Point Directory", metadata["pageProgram"])

    def test_partial_referral_page_identity_fails_closed(self) -> None:
        providers = FixtureProviders()
        configuration = providers.configuration("fixture-partial-page-identity")

        def resolve(result: dict) -> dict | None:
            identity = providers.resolve(result)
            if identity:
                identity["pageOrganization"] = "Referrer"
            return identity

        with self.assertRaisesRegex(
            OptimizationPipelineError, "needs both organization and program"
        ):
            OptimizationDiscoveryPipeline(
                self.store,
                configuration,
                search=providers.search,
                fetch=providers.fetch,
                resolve_identity=resolve,
                existing_resources=providers.fixture["existingResources"],
            ).run()

    def test_directory_only_named_program_cannot_freeze_a_candidate_packet(self) -> None:
        providers = FixtureProviders()
        configuration = providers.configuration("fixture-directory-only-program")
        query = {
            "key": "one-query",
            "position": 1,
            "purpose": "Fixture candidate qualification",
            "query": "fixture directory-only program",
        }
        configuration["queryPlan"] = {
            "schemaVersion": 4,
            "candidateQualificationPolicyVersion": "candidate-qualification-gates-v2",
            "categoryId": "housing",
            "stageKey": "urgent-access",
            "targetLocation": "Mesa",
            "regionalScope": "Maricopa County and nearby areas",
            "branches": [
                {
                    "key": "fixture",
                    "purpose": query["purpose"],
                    "required": True,
                    "saturation": {
                        "minimumQueries": 1,
                        "maximumQueries": 1,
                        "consecutiveNoNewIdentityQueries": 1,
                        "noveltyUnit": "package-eligible identity",
                    },
                    "queries": [query],
                }
            ],
        }
        url = "https://directory.example/program-name"
        with self.assertRaisesRegex(OptimizationPipelineError, "only directory evidence"):
            OptimizationDiscoveryPipeline(
                self.store,
                configuration,
                search=lambda _query, _maximum: [
                    {"url": url, "title": "Named program lead"}
                ],
                fetch=lambda _url: {
                    "text": "A directory names a program but is not program evidence.",
                    "finalUrl": url,
                    "statusCode": 200,
                    "contentType": "text/html",
                },
                resolve_identity=lambda _result: qualified_identity(
                    "Example Provider", "Example Program"
                ),
            ).run()

    def test_conflicting_role_reviews_for_one_identity_fail_closed(self) -> None:
        providers = FixtureProviders()
        configuration = providers.configuration("fixture-conflicting-roles")
        queries = [
            {
                "key": f"role-{position}",
                "position": position,
                "purpose": "Fixture identity-role consistency",
                "query": f"fixture role {position}",
            }
            for position in (1, 2)
        ]
        configuration["queryPlan"] = {
            "schemaVersion": 4,
            "candidateQualificationPolicyVersion": "candidate-qualification-gates-v2",
            "categoryId": "housing",
            "stageKey": "urgent-access",
            "targetLocation": "Mesa",
            "regionalScope": "Maricopa County and nearby areas",
            "branches": [
                {
                    "key": "fixture",
                    "purpose": "Fixture identity-role consistency",
                    "required": True,
                    "saturation": {
                        "minimumQueries": 2,
                        "maximumQueries": 2,
                        "consecutiveNoNewIdentityQueries": 2,
                        "noveltyUnit": "package-eligible identity",
                    },
                    "queries": queries,
                }
            ],
        }
        call_count = 0

        def resolve(_result: dict) -> dict:
            nonlocal call_count
            call_count += 1
            return qualified_identity(
                "Example Provider",
                "Example Program",
                candidateRole=(
                    "direct-program" if call_count == 1 else "service-location"
                ),
            )

        with self.assertRaisesRegex(
            OptimizationPipelineError, "Conflicting reviewed qualification"
        ):
            OptimizationDiscoveryPipeline(
                self.store,
                configuration,
                search=lambda query, _maximum: [
                    {
                        "url": f"https://provider.example/{query.rsplit(' ', 1)[-1]}",
                        "title": "Program",
                    }
                ],
                fetch=lambda _url: {},
                resolve_identity=resolve,
            ).run()

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
        self.assertEqual(25, result.query_count)
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
        self.assertEqual(7, result.packet_count)
        self.assertEqual(1, providers.fetch_calls.count(first_url))
        self.assertEqual(7, len(providers.fetch_calls))

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

        inspected = ResearchStore(self.store.path)
        with inspected.connect() as connection:
            attempt = connection.execute(
                "SELECT status FROM optimization_query_attempts ORDER BY id DESC LIMIT 1"
            ).fetchone()
            run = connection.execute(
                "SELECT status FROM optimization_runs ORDER BY id DESC LIMIT 1"
            ).fetchone()
        self.assertEqual("running", attempt["status"])
        self.assertEqual("running", run["status"])

        self.store = ResearchStore(self.store.path, recover_interrupted=True)
        result = self.pipeline(providers, "fixture-process-restart").run()
        self.assertEqual(7, result.packet_count)
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
        self.assertEqual(
            "government-referral",
            source_authority(
                "https://provider.example/access-points",
                direct_domains=["provider.example"],
                reviewed_authority="government-referral",
                reviewed_authority_precedence=True,
            ),
        )
        self.assertEqual(
            "direct-provider",
            source_authority(
                "https://provider.example/access-points",
                direct_domains=["provider.example"],
                reviewed_authority="government-referral",
            ),
        )
        with self.assertRaisesRegex(ValueError, "Invalid reviewed source authority"):
            source_authority(
                "https://provider.example/program",
                reviewed_authority="unreviewed",
                reviewed_authority_precedence=True,
            )


if __name__ == "__main__":
    unittest.main()
