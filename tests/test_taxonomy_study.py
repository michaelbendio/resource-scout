from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from resource_research_agent.importer import ResourcePackageImporter
from resource_research_agent.storage import ResearchStore
from resource_research_agent.taxonomy_category_proposal import (
    MESA_TAXONOMY_CORPUS_SHA256,
    PROPOSED_NEED_CATEGORIES,
    RESOURCE_CATEGORY_ADDITIONS,
    RESOURCE_TARGETS,
    RETIRED_CATEGORY_IDS,
    build_mesa_category_redistribution_proposal,
)
from resource_research_agent.taxonomy_study import (
    TaxonomyStudyError,
    prepare_taxonomy_study,
    record_mesa_category_directions,
    taxonomy_study_summary,
)
from resource_research_agent.taxonomy_types import (
    APPROVED_CATEGORY_RULES,
    TYPE_REVIEW_RULES,
    build_type_review_packets,
)
from resource_research_agent.taxonomy_type_design import (
    CATEGORY_TYPE_DESIGNS,
    TAXONOMY_APPLICATION_CLEANUP_FLAGS,
    build_type_design,
)
from resource_research_agent.taxonomy_groups import (
    GROUP_CATALOG,
    GROUP_REVIEW_RULES,
    group_browse_category_rows,
    infer_group_proposal,
    matches_category_filter,
    matches_type_and_group_filters,
)


def digest(value: object) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class TaxonomyStudyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        package_path = self.root / "mesa-resource-package.zip"
        with zipfile.ZipFile(package_path, "w") as archive:
            archive.writestr("tso-resources.json", json.dumps({
                "resourcePackageSchemaVersion": 3,
                "packageVersion": 8,
                "officeName": "Mesa TSO",
                "serviceArea": "Mesa and Maricopa County, Arizona",
                "categories": [
                    {
                        "id": "transportation",
                        "name": "Transportation",
                        "filters": ["Bus passes"],
                    },
                    {"id": "seniors", "name": "Seniors", "filters": []},
                    {"id": "miscellaneous", "name": "Miscellaneous", "filters": []},
                ],
                "forGroups": ["Seniors"],
                "resources": [{
                    "id": "known-ride",
                    "name": "Known Ride",
                    "categories": ["transportation"],
                    "categoryFilters": {"transportation": ["Bus passes"]},
                    "forGroups": ["Seniors"],
                    "informationText": "Preserve this exact Information text.",
                }],
            }))
        self.store = ResearchStore(self.root / "research.sqlite3")
        self.import_id = self.store.save_import(
            ResourcePackageImporter(None).read(package_path)
        )
        self.curation_job_id = self._completed_curation_job()
        self.replay_study_id = self._completed_replay_study()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _completed_curation_job(self) -> int:
        assignment = {"category": {"id": "transportation"}}
        assignment_sha = digest(assignment)
        job_id = self.store.create_scout_curation_job({
            "importId": self.import_id,
            "assignmentVersion": "taxonomy-test-curation",
            "candidatePackageSha256": "1" * 64,
            "locationName": "Mesa",
            "officeName": "Mesa TSO",
            "serviceArea": "Mesa and Maricopa County, Arizona",
            "sourcePackageSha256": "2" * 64,
            "sourcePackageContentSha256": self.store.import_summary(
                self.import_id
            )["contentSha256"],
            "sourcePackageVersion": "8",
        }, [{
            "categoryId": "transportation",
            "categoryLabel": "Transportation",
            "canonicalRunId": None,
            "candidateCount": 1,
            "assignment": assignment,
            "assignmentSha256": assignment_sha,
        }])
        result = {
            "resources": [{
                "id": "curated-senior-ride",
                "name": "Senior Ride",
                "categories": ["transportation", "seniors"],
                "categoryFilters": {"transportation": ["Bus passes"]},
                "forGroups": ["Seniors"],
                "informationText": "Curated Information remains unchanged.",
            }],
            "candidateDispositions": [],
        }
        self.store.save_scout_curation_category_result(
            job_id,
            "transportation",
            result,
            digest(result),
            1,
        )
        return job_id

    def _completed_replay_study(self) -> int:
        now = datetime.now(timezone.utc).isoformat()
        report = {"schemaVersion": 1, "aggregate": {"v2RecoveredCount": 1}}
        with self.store.connect() as connection:
            cursor = connection.execute(
                """INSERT INTO codex_replay_studies (
                       import_id, replay_version, status, package_fixture_json,
                       package_fixture_sha256, report_json, report_sha256,
                       created_at, updated_at, codex_closed_at, revealed_at,
                       completed_at
                   ) VALUES (?, 'taxonomy-test-replay', 'completed', ?, ?, ?, ?,
                             ?, ?, ?, ?, ?)""",
                (
                    self.import_id,
                    json.dumps({"importId": self.import_id}),
                    "3" * 64,
                    json.dumps(report),
                    digest(report),
                    now,
                    now,
                    now,
                    now,
                    now,
                ),
            )
        return int(cursor.lastrowid)

    def test_freezes_exact_connected_and_automesa_resource_sets(self) -> None:
        study = prepare_taxonomy_study(
            self.store,
            self.import_id,
            curation_job_id=self.curation_job_id,
            replay_study_id=self.replay_study_id,
        )
        summary = taxonomy_study_summary(study)
        self.assertEqual("category-review", summary["status"])
        self.assertEqual({
            "connectedPackage": 1,
            "autoMesaCurated": 1,
            "total": 2,
        }, summary["resourceCounts"])
        self.assertEqual(3, summary["categoryCount"])
        keys = [item["corpusKey"] for item in study["corpus"]["resources"]]
        self.assertEqual([
            "connected-package:known-ride",
            "automesa-curated:curated-senior-ride",
        ], keys)
        known = study["corpus"]["resources"][0]["resource"]
        curated = study["corpus"]["resources"][1]["resource"]
        self.assertEqual(
            "Preserve this exact Information text.", known["informationText"]
        )
        self.assertEqual(
            "Curated Information remains unchanged.", curated["informationText"]
        )

    def test_category_review_uses_plain_tests_and_flags_population_heading(self) -> None:
        study = prepare_taxonomy_study(
            self.store,
            self.import_id,
            curation_job_id=self.curation_job_id,
            replay_study_id=self.replay_study_id,
        )
        review = study["categoryReview"]
        self.assertEqual(3, len(review["categoryTest"]))
        seniors = next(
            item for item in review["categories"]
            if item["categoryId"] == "seniors"
        )
        transportation = next(
            item for item in review["categories"]
            if item["categoryId"] == "transportation"
        )
        self.assertEqual("population-shaped", seniors["attention"]["kind"])
        self.assertIsNone(transportation["attention"])
        self.assertIsNone(seniors["decision"])
        self.assertEqual("pending", seniors["reviewStatus"])
        example = review["workedExamples"][0]
        self.assertEqual("transportation", example["expectedCategory"])
        self.assertEqual(["Seniors"], example["expectedFor"])

    def test_repeating_exact_study_returns_same_durable_record(self) -> None:
        first = prepare_taxonomy_study(
            self.store,
            self.import_id,
            curation_job_id=self.curation_job_id,
            replay_study_id=self.replay_study_id,
        )
        second = prepare_taxonomy_study(
            self.store,
            self.import_id,
            curation_job_id=self.curation_job_id,
            replay_study_id=self.replay_study_id,
        )
        self.assertEqual(first["id"], second["id"])
        self.assertEqual(first["corpusSha256"], second["corpusSha256"])
        self.assertEqual(
            first["categoryReviewSha256"], second["categoryReviewSha256"]
        )

    def test_approved_directions_create_revision_without_losing_initial_review(self) -> None:
        with self.store.connect() as connection:
            rows = [
                ("children-pregnancy", "Children/Pregnancy"),
                ("clothing-household", "Clothing/Household"),
                ("disability", "Disability"),
                ("reentry-support", "Reentry Support"),
                ("veterans", "Veterans"),
            ]
            connection.executemany(
                """INSERT INTO categories (import_id, category_id, label, raw_json)
                   VALUES (?, ?, ?, '{}')""",
                [(self.import_id, category_id, label) for category_id, label in rows],
            )
        study = prepare_taxonomy_study(
            self.store,
            self.import_id,
            curation_job_id=self.curation_job_id,
            replay_study_id=self.replay_study_id,
        )
        original_sha = study["categoryReviewSha256"]
        updated = record_mesa_category_directions(self.store, study["id"])
        self.assertEqual(1, updated["categoryReviewRevision"])
        self.assertNotEqual(original_sha, updated["categoryReviewSha256"])
        self.assertEqual(2, len(updated["categoryReviewRevisions"]))
        self.assertEqual(
            original_sha,
            updated["categoryReviewRevisions"][0]["reviewSha256"],
        )
        seniors = next(
            item for item in updated["categoryReview"]["categories"]
            if item["categoryId"] == "seniors"
        )
        disability = next(
            item for item in updated["categoryReview"]["categories"]
            if item["categoryId"] == "disability"
        )
        self.assertEqual("reclassify-for", seniors["decision"])
        self.assertEqual(["Seniors"], seniors["targetFor"])
        self.assertEqual("direction-approved", seniors["reviewStatus"])
        self.assertIsNone(disability["decision"])
        self.assertEqual("analysis-required", disability["reviewStatus"])

    def test_requires_completed_revealed_replay(self) -> None:
        with self.store.connect() as connection:
            connection.execute(
                """UPDATE codex_replay_studies
                   SET status = 'running', report_json = NULL, report_sha256 = ''
                   WHERE id = ?""",
                (self.replay_study_id,),
            )
        with self.assertRaisesRegex(TaxonomyStudyError, "Finish and reveal"):
            prepare_taxonomy_study(
                self.store,
                self.import_id,
                curation_job_id=self.curation_job_id,
                replay_study_id=self.replay_study_id,
            )

    def test_mesa_proposal_refuses_another_frozen_corpus(self) -> None:
        study = prepare_taxonomy_study(
            self.store,
            self.import_id,
            curation_job_id=self.curation_job_id,
            replay_study_id=self.replay_study_id,
        )
        self.assertNotEqual(MESA_TAXONOMY_CORPUS_SHA256, study["corpusSha256"])
        with self.assertRaisesRegex(TaxonomyStudyError, "another frozen corpus"):
            build_mesa_category_redistribution_proposal(study)

    def test_mesa_resource_targets_never_use_retired_headings(self) -> None:
        retired = {
            "children-pregnancy", "clothing-household", "disability", "reentry-support",
            "miscellaneous", "seniors", "veterans",
        }
        self.assertTrue(RESOURCE_TARGETS)
        for resource_id, targets in RESOURCE_TARGETS.items():
            with self.subTest(resource_id=resource_id):
                self.assertTrue(targets)
                self.assertEqual(len(targets), len(set(targets)))
                self.assertFalse(retired.intersection(targets))
        self.assertTrue(RESOURCE_CATEGORY_ADDITIONS)
        for resource_id, additions in RESOURCE_CATEGORY_ADDITIONS.items():
            with self.subTest(resource_id=resource_id):
                self.assertTrue(additions)
                self.assertEqual(len(additions), len(set(additions)))
                self.assertFalse(retired.intersection(additions))

    def test_mesa_proposal_covers_each_affected_resource_exactly_once(self) -> None:
        target_ids = {
            category_id
            for targets in RESOURCE_TARGETS.values()
            for category_id in targets
        }
        current_ids = sorted(
            (target_ids - {item["id"] for item in PROPOSED_NEED_CATEGORIES})
            | RETIRED_CATEGORY_IDS
        )
        study = {
            "id": 1,
            "corpusSha256": MESA_TAXONOMY_CORPUS_SHA256,
            "categoryReviewSha256": "4" * 64,
            "corpus": {
                "categories": [
                    {"id": category_id, "label": category_id}
                    for category_id in current_ids
                ],
                "resources": [
                    {
                        "corpusKey": f"automesa-curated:{resource_id}",
                        "origin": "automesa-curated",
                        "resourceId": resource_id,
                        "name": f"Resource {resource_id}",
                        "categories": ["seniors"],
                        "resource": {"id": resource_id},
                    }
                    for resource_id in RESOURCE_TARGETS
                ] + [
                    {
                        "corpusKey": f"connected-package:{resource_id}",
                        "origin": "connected-package",
                        "resourceId": resource_id,
                        "name": f"Resource {resource_id}",
                        "categories": ["addiction"],
                        "resource": {"id": resource_id},
                    }
                    for resource_id in (
                        set(RESOURCE_CATEGORY_ADDITIONS) - set(RESOURCE_TARGETS)
                    )
                ],
            },
        }
        proposal = build_mesa_category_redistribution_proposal(study)
        assignments = proposal["assignments"]
        expected_assignment_ids = (
            set(RESOURCE_TARGETS) | set(RESOURCE_CATEGORY_ADDITIONS)
        )
        self.assertEqual(len(expected_assignment_ids), len(assignments))
        self.assertEqual(
            expected_assignment_ids,
            {item["resourceId"] for item in assignments},
        )
        self.assertEqual(
            len(RESOURCE_CATEGORY_ADDITIONS),
            proposal["coverage"]["fullCorpusAdditionResourceCount"],
        )
        self.assertEqual(0, proposal["coverage"]["unassignedCount"])
        self.assertEqual(
            "Parenting",
            next(
                item["label"]
                for item in proposal["proposedNeedCategories"]
                if item["id"] == "parenting-child-development"
            ),
        )
        self.assertEqual(20, proposal["coverage"]["targetCategoryCounts"][
            "parenting-child-development"
        ])
        self.assertEqual(19, proposal["coverage"]["targetCategoryCounts"][
            "independent-living"
        ])
        self.assertEqual(11, proposal["coverage"]["targetCategoryCounts"][
            "caregiving"
        ])
        assignment_by_id = {
            item["resourceId"]: item for item in assignments
        }
        self.assertEqual(
            ["legal"],
            assignment_by_id["ce14bd1aa42c212343ff01bdda80381e"][
                "proposedNeedCategories"
            ],
        )
        self.assertEqual(
            ["caregiving", "legal", "financial-assistance"],
            assignment_by_id["b47b61d084512681adb9c7ccacf2268c"][
                "proposedNeedCategories"
            ],
        )
        self.assertEqual(
            ["addiction", "housing"],
            assignment_by_id["a21c310d2a515339bb648af71577d74d"][
                "proposedNeedCategories"
            ],
        )
        self.assertEqual(
            [],
            assignment_by_id["a21c310d2a515339bb648af71577d74d"][
                "removeCategories"
            ],
        )
        self.assertIn(
            "housing",
            assignment_by_id["fb402105bec44e0623b4ccf8d7064802"][
                "proposedNeedCategories"
            ],
        )

    def test_type_packets_require_the_approved_category_rules(self) -> None:
        study = {
            "id": 1,
            "corpusSha256": MESA_TAXONOMY_CORPUS_SHA256,
            "corpus": {"categories": [], "resources": []},
            "categoryRedistributionProposals": [{
                "proposalSha256": "5" * 64,
                "proposal": {
                    "proposedNeedCategories": [],
                    "assignments": [],
                },
            }],
            "categoryApproval": None,
        }
        with self.assertRaisesRegex(TaxonomyStudyError, "Approve the Category"):
            build_type_review_packets(study)
        study["categoryApproval"] = {
            "proposalSha256": "5" * 64,
            "rules": {"different": "rules"},
        }
        with self.assertRaisesRegex(TaxonomyStudyError, "rules do not match"):
            build_type_review_packets(study)

    def test_type_review_rules_allow_legitimate_no_type_disposition(self) -> None:
        self.assertIn("no-type-needed", TYPE_REVIEW_RULES["dispositions"])
        self.assertIn("Never invent", TYPE_REVIEW_RULES["optional"])
        self.assertIn(
            "named, accountable navigation pathway",
            APPROVED_CATEGORY_RULES["categoryEvidence"],
        )

    def test_all_approved_categories_have_compact_unique_type_labels(self) -> None:
        self.assertEqual(
            set(CATEGORY_TYPE_DESIGNS),
            {
                "addiction",
                "caregiving",
                "clothing",
                "domestic-violence",
                "education",
                "employment",
                "financial-assistance",
                "food",
                "homeless-services",
                "housing",
                "household-essentials",
                "id-recovery",
                "immigration",
                "independent-living",
                "legal",
                "medical-dental-vision",
                "mental-health",
                "parenting-child-development",
                "transportation",
                "utilities-phone-internet",
            },
        )
        for category_id, specification in CATEGORY_TYPE_DESIGNS.items():
            labels = [item["label"] for item in specification["types"]]
            with self.subTest(category_id=category_id):
                self.assertEqual(len(labels), len(set(labels)))
                self.assertTrue(all(len(label) <= 24 for label in labels))

    def test_new_categories_cover_redistributed_resources(self) -> None:
        for category_id in (
            "clothing",
            "household-essentials",
            "parenting-child-development",
            "independent-living",
            "caregiving",
        ):
            specification = CATEGORY_TYPE_DESIGNS[category_id]
            with self.subTest(category_id=category_id):
                self.assertEqual(
                    set(specification["assignments"]),
                    {
                        resource_id
                        for resource_id, targets in RESOURCE_TARGETS.items()
                        if category_id in targets
                    },
                )

    def test_need_type_designs_preserve_method_boundaries(self) -> None:
        food = CATEGORY_TYPE_DESIGNS["food"]
        self.assertIn(
            "Gov't Benefits",
            food["assignments"]["cd0fd35209b8684c1b85d3a08afb1f4d"],
        )
        self.assertEqual(
            ["Infant Formula"],
            food["assignments"]["a6043035dfbf51e34bad108416bca340"],
        )
        self.assertNotIn(
            "Food Benefits",
            {item["label"] for item in food["types"]},
        )

        housing = CATEGORY_TYPE_DESIGNS["housing"]
        housing_labels = {item["label"] for item in housing["types"]}
        self.assertIn("Emergency Shelter", housing_labels)
        self.assertIn("Rapid Rehousing", housing_labels)
        self.assertIn("Rental Assistance", housing_labels)
        self.assertIn("Recovery Housing", housing_labels)
        self.assertIn("Eviction Prevention", housing_labels)
        self.assertIn("Eviction Legal Help", housing_labels)
        self.assertNotIn("Veterans", housing_labels)
        self.assertNotIn("Seniors", housing_labels)

        homeless = CATEGORY_TYPE_DESIGNS["homeless-services"]
        self.assertNotIn(
            "homeless-services",
            RESOURCE_TARGETS["0df6bb236d8c7bf168ce4867dc83360e"],
        )
        self.assertNotIn(
            "homeless-services",
            RESOURCE_TARGETS["a3782d71fb0f13f124d33c95dadd779c"],
        )
        self.assertIn(
            "Street Outreach",
            homeless["assignments"]["91d5cdd19b42853fb4bbe8e57f325be0"],
        )
        self.assertIn(
            "Overnight Lodging",
            homeless["assignments"]["78410d1265bcc4f89c056a7d624434f8"],
        )
        self.assertEqual(
            ["Overnight Lodging", "Homeless Navigation"],
            homeless["assignments"]["773f0771a3cca46a7a57189d17a58a01"],
        )
        self.assertEqual(
            ["Street Outreach", "Homeless Navigation"],
            homeless["assignments"]["6aa599e3a9f6ce52dd0a27bc6e625fd2"],
        )
        self.assertEqual(
            ["ID & Documents", "Mail & Storage"],
            homeless["assignments"]["5bfda48463f45755a59145fa7d226906"],
        )
        self.assertEqual(
            ["Homeless Navigation"],
            homeless["assignments"]["e81a4666fa9fdf3874524e595834798c"],
        )
        self.assertNotIn(
            "948dd967fb329f7e5f04c0814a113889",
            housing["assignments"],
        )
        self.assertNotIn(
            "948dd967fb329f7e5f04c0814a113889",
            RESOURCE_CATEGORY_ADDITIONS,
        )
        self.assertEqual(
            ["homeless-services", "financial-assistance"],
            RESOURCE_CATEGORY_ADDITIONS["e81a4666fa9fdf3874524e595834798c"],
        )

        financial = CATEGORY_TYPE_DESIGNS["financial-assistance"]
        financial_labels = {item["label"] for item in financial["types"]}
        self.assertEqual(17, len(financial_labels))
        self.assertEqual(58, len(financial["assignments"]))
        self.assertIn("Cash Assistance", financial_labels)
        self.assertNotIn("Cash Benefits", financial_labels)
        self.assertIn("Housing Subsidies", financial_labels)
        self.assertIn("Child Care Aid", financial_labels)
        self.assertIn("Education Aid", financial_labels)
        self.assertIn("Medical Cost Aid", financial_labels)
        self.assertIn("Caregiver Aid", financial_labels)
        self.assertIn(
            "Disability Income",
            financial["assignments"]["8d70eda15ed4d365bd3ffb2577c8653e"],
        )
        self.assertIn(
            "Benefits Navigation",
            financial["assignments"]["c6862828db3631873bf2eb1f4ff99bea"],
        )
        self.assertEqual(
            ["Child Care Aid", "Benefits Navigation"],
            financial["assignments"]["b48b75beadedb73dd0606ffb3dcc568d"],
        )
        self.assertIn(
            "Tax Preparation",
            financial["assignments"]["106d516390d810b1989b53d59ae806c9"],
        )
        self.assertEqual(
            ["Housing Subsidies", "Deposit Assistance"],
            financial["assignments"]["51cfce1c2944ef0453c793aba1923e08"],
        )
        self.assertEqual(
            ["Education Aid"],
            financial["assignments"]["84f48c34515e9e8aa0bce9ff7796631c"],
        )
        self.assertEqual(
            ["Medical Cost Aid"],
            financial["assignments"]["4ae8876a9b82a7f0a606939254d87bb8"],
        )
        self.assertNotIn(
            "193621d2449346f5eb4f3fe57535ad47",
            financial["assignments"],
        )
        self.assertNotIn(
            "financial-assistance",
            RESOURCE_TARGETS["193621d2449346f5eb4f3fe57535ad47"],
        )
        self.assertNotIn(
            "financial-assistance",
            RESOURCE_TARGETS["33b8cbd29cf68ac3a07e0fd8d984771b"],
        )
        self.assertEqual(
            ["financial-assistance"],
            RESOURCE_CATEGORY_ADDITIONS["bd13f813cdf1a52f4297b41d93bea46b"],
        )
        for free_or_discounted_service_id in (
            "9c6c63b5207dc97a65b6d8ca95c544e9",
            "111bbc8293126891b0ecef093e94874c",
            "4ff2225ddc559a033efe06a6b6ce3659",
        ):
            self.assertNotIn(
                "financial-assistance",
                RESOURCE_CATEGORY_ADDITIONS.get(free_or_discounted_service_id, []),
            )
        self.assertIn(
            "Free or sliding-fee service",
            financial["boundary"],
        )

        transportation = CATEGORY_TYPE_DESIGNS["transportation"]
        self.assertNotIn(
            "00cca473db91285a4a393f5ba53add8f",
            transportation["assignments"],
        )
        self.assertNotIn(
            "transportation",
            RESOURCE_TARGETS["00cca473db91285a4a393f5ba53add8f"],
        )
        self.assertIn(
            "independent-living",
            RESOURCE_TARGETS["00cca473db91285a4a393f5ba53add8f"],
        )
        self.assertNotIn(
            "Mobility Management",
            {item["label"] for item in transportation["types"]},
        )

        utilities = CATEGORY_TYPE_DESIGNS["utilities-phone-internet"]
        self.assertEqual(
            ["Heating/Cooling Repair"],
            utilities["assignments"]["774e5a59b471ceacca5d0fe7cc5e787b"],
        )
        self.assertEqual(
            ["Communication Equipment", "Relay Service"],
            utilities["assignments"]["ee67d6c2ce1b1b7f9dbf0b2ef86ef972"],
        )

        id_recovery = CATEGORY_TYPE_DESIGNS["id-recovery"]
        self.assertIn(
            "Mail Service",
            id_recovery["assignments"]["5bfda48463f45755a59145fa7d226906"],
        )
        self.assertIn(
            "Mail Service",
            id_recovery["assignments"]["fb14c6d3b942c86033ad23bf8b60fb48"],
        )

        housing = CATEGORY_TYPE_DESIGNS["housing"]
        self.assertEqual(
            ["Emergency Shelter", "Transitional Housing", "Rental Assistance"],
            housing["assignments"]["d0eeddd67746f3a298eaf4969b6e9bd1"],
        )
        self.assertEqual(
            ["Emergency Shelter", "Rapid Rehousing", "Housing Navigation"],
            housing["assignments"]["15b833547484fe110411244b99712ca9"],
        )
        self.assertEqual(
            ["Recovery Housing"],
            housing["assignments"]["a21c310d2a515339bb648af71577d74d"],
        )
        self.assertEqual(
            ["Treatment Housing"],
            housing["assignments"]["14d40b4e4bdd71c67e009326f3716119"],
        )
        self.assertIn(
            "Eviction Prevention",
            housing["assignments"]["773f0771a3cca46a7a57189d17a58a01"],
        )
        self.assertEqual(
            ["Eviction Legal Help"],
            housing["assignments"]["a75559d019132060ea10e3390d9106ab"],
        )
        self.assertNotIn(
            "6f857637fa2be0cd00ed6fc1671bded3",
            housing["assignments"],
        )
        family_hub_flag = next(
            item for item in TAXONOMY_APPLICATION_CLEANUP_FLAGS
            if item["proposedIdentity"].startswith("Family Housing Hub")
        )
        self.assertEqual(
            {
                "0e36c87d7889979a6cf7f4debff3bed7",
                "eadaaf197b67dc1d520ae55c2dc28a19",
            },
            set(family_hub_flag["resourceIds"]),
        )
        sister_place_flag = next(
            item for item in TAXONOMY_APPLICATION_CLEANUP_FLAGS
            if item["proposedIdentity"].startswith("My Sister's Place")
        )
        self.assertEqual(
            {
                "bd8d70a1ed5b94634c74d90a66d1ea64",
                "ea694e1df9c5ce31796e579520312da9",
            },
            set(sister_place_flag["resourceIds"]),
        )
        separate_resources = {
            item["proposedIdentity"]: item
            for item in TAXONOMY_APPLICATION_CLEANUP_FLAGS
            if item["kind"] == "separate-resource-required"
        }
        self.assertEqual(
            ["Transitional Housing"],
            separate_resources["House of Refuge — Transitional Housing"][
                "proposedTypes"
            ],
        )
        self.assertEqual(
            ["Recovery Housing", "Transitional Housing"],
            separate_resources["The Mesa House — Sober and Transitional Housing"][
                "proposedTypes"
            ],
        )
        consolidation_flags = {
            item["proposedIdentity"]: item
            for item in TAXONOMY_APPLICATION_CLEANUP_FLAGS
            if item["kind"] == "consolidation-candidate"
        }
        self.assertEqual(
            {
                "c9a6d961fc20217b2875637b5fef2cb6",
                "3460a40faf90d00f895061b117f1d9cc",
                "8c7a5e3631418ce97d934b37a67fbd61",
            },
            set(consolidation_flags[
                "Keys to Change — Key Campus Welcome Center"
            ]["resourceIds"]),
        )
        self.assertEqual(
            {
                "577e54a943c0cb1d97e003e0e6ba6623",
                "5bfda48463f45755a59145fa7d226906",
            },
            set(consolidation_flags[
                "La Mesa Ministries — Resource Center"
            ]["resourceIds"]),
        )
        va_transfer = next(
            item for item in TAXONOMY_APPLICATION_CLEANUP_FLAGS
            if item["kind"] == "content-transfer-required"
        )
        self.assertEqual(
            "e81a4666fa9fdf3874524e595834798c",
            va_transfer["destinationResourceId"],
        )

        education = CATEGORY_TYPE_DESIGNS["education"]
        online_ged = education["assignments"][
            "cce4f2f7537a93ea0f58d524dc2dd818"
        ]
        self.assertIn("Online Education", online_ged)
        self.assertIn("GED/HSE", online_ged)
        self.assertEqual(
            ["School Supplies"],
            education["assignments"]["ebac95249761b88323fc73b4e26259fd"],
        )
        education_labels = {item["label"] for item in education["types"]}
        self.assertEqual(15, len(education_labels))
        self.assertEqual(34, len(education["assignments"]))
        self.assertIn("Apprenticeships", education_labels)
        self.assertEqual(
            ["Education Navigation"],
            education["assignments"]["70ea356cba96bcc304b79ca2a5469f9c"],
        )
        self.assertEqual(
            ["Early Learning"],
            education["assignments"]["1ed84b657420da445ac082991959b3f8"],
        )
        self.assertEqual(
            ["Early Intervention", "Education Navigation"],
            education["assignments"]["90ef7bed032bcd935b0f82e65f664917"],
        )
        self.assertEqual(
            ["Career Training", "Apprenticeships", "Education Navigation"],
            education["assignments"]["f95aad04c5e72f66f324d9875d7caffd"],
        )
        self.assertEqual(
            ["Digital Literacy", "Career Training"],
            education["assignments"]["d72b099aea9d25b5ed7f4eafa274da78"],
        )
        self.assertNotIn(
            "5b3220f8a547f64ec5b3171b0af3217e",
            education["assignments"],
        )
        self.assertIn(
            "education",
            RESOURCE_TARGETS["b48b75beadedb73dd0606ffb3dcc568d"],
        )
        self.assertIn(
            "education",
            RESOURCE_TARGETS["f5956fe09395d25458ca9fda67d737c9"],
        )
        self.assertEqual(
            ["education"],
            RESOURCE_CATEGORY_ADDITIONS["31c5097bb2e3cc1075a6851e27fb88ec"],
        )

        education_consolidations = {
            item["proposedIdentity"]: item
            for item in TAXONOMY_APPLICATION_CLEANUP_FLAGS
            if item["kind"] == "consolidation-candidate"
            and "education" in item.get("proposedCategories", [])
        }
        self.assertEqual(
            {
                "b48b75beadedb73dd0606ffb3dcc568d",
                "90ef7bed032bcd935b0f82e65f664917",
                "eb94f24384f8e51a2b237d7d8c507948",
            },
            set(education_consolidations[
                "Arizona Early Intervention Program (AzEIP)"
            ]["resourceIds"]),
        )
        self.assertEqual(
            {
                "61a8d9d4eafa58537df9904250187968",
                "d633e161d87ac6cf94df2a2a6b877ab1",
            },
            set(education_consolidations[
                "Frank X. Gordon Adult Education Center"
            ]["resourceIds"]),
        )
        self.assertEqual(
            {
                "7f314bc451d77d01f553d4527407d06d",
                "c3ab0f1578b4ec24df452d8eee4c9ce6",
                "f95aad04c5e72f66f324d9875d7caffd",
            },
            set(education_consolidations["Workforce Center @ Mesa"]["resourceIds"]),
        )

        employment = CATEGORY_TYPE_DESIGNS["employment"]
        self.assertEqual(13, len(employment["types"]))
        self.assertEqual(42, len(employment["assignments"]))
        self.assertFalse(any(
            value == "no-type-needed"
            for value in employment["assignments"].values()
        ))
        self.assertEqual(
            ["Career Planning", "Job Readiness", "Job Search & Placement"],
            employment["assignments"]["2af79fdd0101ee3a198c732086f9bfc6"],
        )
        self.assertEqual(
            ["Career Planning", "Job Readiness"],
            employment["assignments"]["a90b957439ba736a20a0eb129322891e"],
        )
        self.assertEqual(
            ["Skills Training", "Credentials"],
            employment["assignments"]["e0bfbea73949f1e8965c6c1ad4eeb1ff"],
        )
        self.assertEqual(
            ["Job Readiness", "Skills Training"],
            employment["assignments"]["ac9f801d1000fcddb2531ecbf84d8b12"],
        )
        self.assertNotIn(
            "528e3dad283cd117ea2ff80b3bec333c",
            employment["assignments"],
        )
        self.assertNotIn(
            "01a9e5b0c362df7fad3f6577a423f91a",
            employment["assignments"],
        )
        self.assertNotIn(
            "employment",
            RESOURCE_TARGETS["528e3dad283cd117ea2ff80b3bec333c"],
        )
        self.assertNotIn(
            "employment",
            RESOURCE_TARGETS["01a9e5b0c362df7fad3f6577a423f91a"],
        )
        self.assertIn(
            "employment",
            RESOURCE_CATEGORY_ADDITIONS["e0bfbea73949f1e8965c6c1ad4eeb1ff"],
        )
        self.assertIn("Incidental employment assistance", employment["boundary"])

        arouet_flag = next(
            item for item in TAXONOMY_APPLICATION_CLEANUP_FLAGS
            if item.get("proposedIdentity", "").startswith("Arouet Foundation")
        )
        self.assertEqual(
            {
                "193621d2449346f5eb4f3fe57535ad47",
                "a9d82c588239bf51cb761861ce2ef062",
            },
            set(arouet_flag["resourceIds"]),
        )
        vr_transfer = next(
            item for item in TAXONOMY_APPLICATION_CLEANUP_FLAGS
            if item.get("destinationResourceId")
            == "6be73b6539fd16b3a6c84ffad77aace8"
        )
        self.assertEqual(
            ["08a7877a32a11b9f8531fa95f2a64ade"],
            vr_transfer["sourceResourceIds"],
        )

        addiction = CATEGORY_TYPE_DESIGNS["addiction"]
        addiction_labels = {item["label"] for item in addiction["types"]}
        self.assertEqual(14, len(addiction_labels))
        self.assertIn("Residential Recovery", addiction_labels)
        self.assertIn("Support Groups", addiction_labels)
        self.assertIn("Peer Support", addiction_labels)
        self.assertIn("Overdose/Crisis Line", addiction_labels)
        self.assertNotIn("Peer Recovery", addiction_labels)
        self.assertNotIn("Crisis/Overdose Line", addiction_labels)
        self.assertEqual(36, len(addiction["assignments"]))
        self.assertEqual(
            ["Detox/Withdrawal", "Intensive Outpatient", "Co-occurring Treatment"],
            addiction["assignments"]["ea77fba8e182ba83a7f60438bece546b"],
        )
        self.assertEqual(
            ["Outpatient Treatment", "Recovery Housing", "Peer Support"],
            addiction["assignments"]["86255417090cba31f14b0d7e9334d157"],
        )
        self.assertEqual(
            ["Outpatient Treatment"],
            addiction["assignments"]["18462adf6dd0d47ac76fba2161b70dfc"],
        )
        for residential_recovery_id in (
            "edc5a63f8239da2c402f528da2718669",
            "34bce41d6bcc0b3799d9636d6e0dff8b",
        ):
            self.assertEqual(
                ["Residential Recovery"],
                addiction["assignments"][residential_recovery_id],
            )
        self.assertEqual(
            "no-type-needed",
            addiction["assignments"]["b9affc7e4a6b284ed2bdae319aaa486a"],
        )
        self.assertEqual(
            "no-type-needed",
            addiction["assignments"]["87c3e010d39aad60d9640f059b834c21"],
        )
        self.assertIn("are distinct", addiction["boundary"])

        terros_flag = next(
            item for item in TAXONOMY_APPLICATION_CLEANUP_FLAGS
            if item.get("proposedIdentity", "").startswith("Terros Health")
        )
        self.assertEqual(
            {
                "6b2d7fcadeec59dea6cd835e732ef55f",
                "446d7aeaa7a45f7bab5d72f34d1b10e3",
                "9b72f8059923e0a5e6d1dca60a9dd708",
            },
            set(terros_flag["resourceIds"]),
        )

        medical = CATEGORY_TYPE_DESIGNS["medical-dental-vision"]
        medical_labels = {item["label"] for item in medical["types"]}
        self.assertEqual(20, len(medical_labels))
        self.assertIn("Physical Rehabilitation", medical_labels)
        self.assertIn("Vision Rehabilitation", medical_labels)
        self.assertIn("Reproductive Health", medical_labels)
        self.assertIn("Medical Equipment", medical_labels)
        self.assertNotIn("Rehabilitation", medical_labels)
        self.assertEqual(30, len(medical["assignments"]))
        self.assertEqual(
            ["Vision Care", "Vision Rehabilitation"],
            medical["assignments"]["8db24b98270f7864dadcb0f97b901a53"],
        )
        self.assertEqual(
            ["Primary Care", "Medical Respite", "Physical Rehabilitation"],
            medical["assignments"]["69bc2e9938b04722b0c8cdc1d67dadc8"],
        )
        self.assertIn(
            "Reproductive Health",
            medical["assignments"]["1d36ae0a82e6d1f6c264334db09e578c"],
        )
        self.assertFalse(any(
            "Medical Equipment" in value
            for value in medical["assignments"].values()
            if isinstance(value, list)
        ))
        self.assertIn("Pediatrics and Prenatal/Postpartum", medical["boundary"])

        medical_consolidations = {
            item["proposedIdentity"]: item
            for item in TAXONOMY_APPLICATION_CLEANUP_FLAGS
            if item.get("proposedIdentity") in {
                "Adelante Healthcare — Mesa",
                "Health-e-Arizona Plus — Benefits Enrollment Portal",
                "Mountain Park Health Center",
                "Valleywise Health — Mesa and Countywide Care",
            }
        }
        self.assertEqual(4, len(medical_consolidations))
        self.assertEqual(
            {
                "33b8cbd29cf68ac3a07e0fd8d984771b",
                "bd13f813cdf1a52f4297b41d93bea46b",
            },
            set(medical_consolidations["Adelante Healthcare — Mesa"]["resourceIds"]),
        )
        self.assertEqual(
            {
                "10c59c16ac8288d92ae7a7626edf06ab",
                "2a530b4a56b21439a952af2ac753f12f",
            },
            set(medical_consolidations[
                "Health-e-Arizona Plus — Benefits Enrollment Portal"
            ]["resourceIds"]),
        )
        availability_flag = next(
            item for item in TAXONOMY_APPLICATION_CLEANUP_FLAGS
            if item.get("kind") == "availability-verification-required"
        )
        self.assertEqual(
            ["363ba896bb14a4dc850081cd818533c7"],
            availability_flag["resourceIds"],
        )

        mental_health = CATEGORY_TYPE_DESIGNS["mental-health"]
        mental_health_labels = {
            item["label"] for item in mental_health["types"]
        }
        self.assertEqual(17, len(mental_health_labels))
        self.assertIn("Intensive Outpatient", mental_health_labels)
        self.assertIn("Partial Hospitalization", mental_health_labels)
        self.assertIn("Post-discharge Support", mental_health_labels)
        self.assertNotIn("Post-discharge Followup", mental_health_labels)
        self.assertEqual(29, len(mental_health["assignments"]))
        self.assertFalse(any(
            value == "no-type-needed"
            for value in mental_health["assignments"].values()
        ))
        self.assertEqual(
            ["Outpatient Counseling"],
            mental_health["assignments"]["18462adf6dd0d47ac76fba2161b70dfc"],
        )
        self.assertEqual(
            ["Outpatient Counseling", "Peer Support", "Case Management"],
            mental_health["assignments"]["815148d4fe10fdbf28f981c14050256c"],
        )
        self.assertEqual(
            [
                "Outpatient Counseling", "Psychiatry/Medication",
                "Case Management", "Telehealth", "Care Navigation",
            ],
            mental_health["assignments"]["b0d2eba21896a98631e48b8982248936"],
        )
        self.assertNotIn(
            "0474f03b486642977ecad2860ffac719",
            mental_health["assignments"],
        )
        self.assertNotIn(
            "df171bb522d8c9a10c10b5c20e52cc1b",
            mental_health["assignments"],
        )
        self.assertNotIn(
            "mental-health",
            RESOURCE_TARGETS["0474f03b486642977ecad2860ffac719"],
        )
        self.assertNotIn(
            "mental-health",
            RESOURCE_TARGETS["df171bb522d8c9a10c10b5c20e52cc1b"],
        )
        self.assertIn("incidental or vague referral", mental_health["boundary"])

        cbi_flag = next(
            item for item in TAXONOMY_APPLICATION_CLEANUP_FLAGS
            if item.get("proposedIdentity")
            == "Community Bridges, Inc. — Integrated Care"
        )
        self.assertEqual(
            {
                "5b415ee3078420f7b8081b605d1d087a",
                "20cf2620b396a3fc5a0d270ade9af911",
            },
            set(cbi_flag["resourceIds"]),
        )
        banner_transfer = next(
            item for item in TAXONOMY_APPLICATION_CLEANUP_FLAGS
            if item.get("destinationResourceId")
            == "34dc7c352ceb97ec5831aaa7cb4d3904"
        )
        self.assertEqual(
            ["0474f03b486642977ecad2860ffac719"],
            banner_transfer["sourceResourceIds"],
        )

        legal = CATEGORY_TYPE_DESIGNS["legal"]
        legal_labels = {item["label"] for item in legal["types"]}
        self.assertEqual(20, len(legal_labels))
        self.assertIn("General Civil Legal Help", legal_labels)
        self.assertNotIn("General Civil Legal Aid", legal_labels)
        for expected_gap in (
            "Debt/Bankruptcy", "Benefits Appeals", "Employment Law",
        ):
            self.assertIn(expected_gap, legal_labels)
            self.assertFalse(any(
                expected_gap in value
                for value in legal["assignments"].values()
                if isinstance(value, list)
            ))
        self.assertEqual(19, len(legal["assignments"]))
        self.assertEqual(
            ["Family Law", "Guardianship"],
            legal["assignments"]["38629d0e712141f7531b4cff4b0bfd53"],
        )
        self.assertEqual(
            ["Protective Orders", "Family Law"],
            legal["assignments"]["c8f5de50d9d41ce30ec0b8b6ef45b249"],
        )
        self.assertIn(
            "Wills/Probate",
            legal["assignments"]["6d4803e545580ed7abc3cd8bb87b1314"],
        )
        self.assertIn(
            "Criminal Defense",
            legal["assignments"]["6d4803e545580ed7abc3cd8bb87b1314"],
        )
        self.assertIn("population eligibility alone", legal["boundary"])

        court_identity_flag = next(
            item for item in TAXONOMY_APPLICATION_CLEANUP_FLAGS
            if item.get("proposedIdentity")
            == "Maricopa County Court Self-Service Center"
        )
        self.assertEqual(
            ["1191caa6a627cab7f478d5fe36466e0a"],
            court_identity_flag["resourceIds"],
        )
        veterans_clinic_flag = next(
            item for item in TAXONOMY_APPLICATION_CLEANUP_FLAGS
            if item.get("kind") == "service-area-verification-required"
        )
        self.assertEqual(
            ["1c01cd6b13aaf41619e7cdc09b4c6725"],
            veterans_clinic_flag["resourceIds"],
        )

        parenting = CATEGORY_TYPE_DESIGNS["parenting-child-development"]
        parenting_labels = {item["label"] for item in parenting["types"]}
        self.assertEqual(7, len(parenting_labels))
        self.assertNotIn("Kinship Parenting", parenting_labels)
        self.assertEqual(
            "no-type-needed",
            parenting["assignments"]["38629d0e712141f7531b4cff4b0bfd53"],
        )

        clothing = CATEGORY_TYPE_DESIGNS["clothing"]
        clothing_labels = {item["label"] for item in clothing["types"]}
        self.assertEqual(
            {"General Clothing", "Dress Clothing", "Work Clothing", "School Clothing"},
            clothing_labels,
        )
        self.assertEqual(
            ["Dress Clothing"],
            clothing["assignments"]["3367433d5c6845b44636936a2902a3bb"],
        )
        self.assertEqual(
            ["General Clothing"],
            clothing["assignments"]["7bacf0bff58c51dc50d9c02ccd69eac4"],
        )
        self.assertEqual(
            ["Work Clothing"],
            clothing["assignments"]["70ea356cba96bcc304b79ca2a5469f9c"],
        )
        self.assertNotIn("Medical Equipment", clothing_labels)

        household = CATEGORY_TYPE_DESIGNS["household-essentials"]
        self.assertEqual(
            {"Furniture", "Household Goods", "Hygiene Supplies", "Baby Supplies"},
            {item["label"] for item in household["types"]},
        )
        self.assertEqual(
            ["Baby Supplies"],
            household["assignments"]["7bacf0bff58c51dc50d9c02ccd69eac4"],
        )
        self.assertEqual(
            ["Baby Supplies"],
            household["assignments"]["337e91d961e84d96ee124c6c891045eb"],
        )
        self.assertEqual(
            "no-type-needed",
            household["assignments"]["669bd738b302f2f17f9caa6163dd35ed"],
        )

        independent_living = CATEGORY_TYPE_DESIGNS["independent-living"]
        self.assertEqual(
            ["Assistive Technology"],
            independent_living["assignments"]["d6de881b1d1c0d17801cfcc7e6614ffd"],
        )

        employment = CATEGORY_TYPE_DESIGNS["employment"]
        self.assertEqual(
            employment["assignments"]["ffb70295ec3f1e3256fc1955ec7ad5c0"],
            ["Staffing/Temp Work", "Job Search & Placement"],
        )

        addiction = CATEGORY_TYPE_DESIGNS["addiction"]
        self.assertEqual(
            addiction["assignments"]["56082a4920ef5e52ae645088882ab65d"],
            ["Harm Reduction"],
        )

        medical = CATEGORY_TYPE_DESIGNS["medical-dental-vision"]
        self.assertIn(
            "Medical Respite",
            medical["assignments"]["69bc2e9938b04722b0c8cdc1d67dadc8"],
        )

        mental_health = CATEGORY_TYPE_DESIGNS["mental-health"]
        self.assertIn(
            "Post-discharge Support",
            mental_health["assignments"]["f6b55e24c78fb7889c9767c7527512ea"],
        )

        legal = CATEGORY_TYPE_DESIGNS["legal"]
        self.assertIn(
            "Housing/Eviction Law",
            legal["assignments"]["a75559d019132060ea10e3390d9106ab"],
        )

        immigration = CATEGORY_TYPE_DESIGNS["immigration"]
        immigration_labels = {item["label"] for item in immigration["types"]}
        self.assertEqual(17, len(immigration_labels))
        self.assertTrue({
            "Green Cards", "Work Permits", "Temporary Protection",
            "Immigration Detention", "Refugee/Asylee Status",
            "Travel Documents", "Immigration Records", "Waivers",
        }.issubset(immigration_labels))
        self.assertFalse({
            "Green Card/Adjustment", "Work Authorization",
            "Detention Representation", "Refugee/Asylee Filings",
        } & immigration_labels)
        self.assertIn(
            "Work Permits",
            immigration["assignments"]["3695184e8d514e52029ab65c18e53728"],
        )
        self.assertEqual(
            [
                "Citizenship", "Family Petitions", "Green Cards",
                "Document Replacement", "Refugee/Asylee Status",
                "Travel Documents",
            ],
            immigration["assignments"]["8b325c40eea9d85f2dd5afccb96f5993"],
        )
        self.assertTrue({
            "DACA", "Asylum", "Temporary Protection", "Travel Documents",
            "Immigration Records", "Waivers",
        }.issubset(
            immigration["assignments"]["b9950394defba173a07461ac5fa19e67"]
        ))
        self.assertEqual(
            immigration["assignments"]["dca1d74f147af392005268006630b3ce"],
            ["Case Status/Biometrics"],
        )
        catholic_immigration = next(
            item for item in TAXONOMY_APPLICATION_CLEANUP_FLAGS
            if item.get("proposedIdentity")
            == "Catholic Charities Community Services — Immigration Legal Services"
        )
        self.assertEqual(
            {
                "511ba569ec22349728cb875494668f20",
                "89b9bdda24c8a5abd783f15e99dba056",
            },
            set(catholic_immigration["resourceIds"]),
        )

        domestic_violence = CATEGORY_TYPE_DESIGNS["domestic-violence"]
        domestic_labels = {item["label"] for item in domestic_violence["types"]}
        self.assertEqual(16, len(domestic_labels))
        self.assertIn("Victim Advocacy", domestic_labels)
        self.assertNotIn("Protective Services", domestic_labels)
        self.assertTrue({
            "Crisis Hotline", "Protective Orders", "Court Advocacy",
            "Victim Advocacy",
        }.issubset(
            domestic_violence["assignments"][
                "db2e8f3b8772791cf254fb9cc04b9838"
            ]
        ))
        self.assertEqual(
            ["Victim Advocacy"],
            domestic_violence["assignments"][
                "141b0ffaf944535bcc958d1d62ff4adc"
            ],
        )
        self.assertTrue({
            "Emergency Shelter", "Transitional Housing", "Court Advocacy",
        }.issubset(
            domestic_violence["assignments"][
                "626aab0a5b4c6dcd7811605470690fc3"
            ]
        ))
        self.assertEqual(
            domestic_violence["assignments"]["85a5b070658ea4afa6c89b604340e53e"],
            ["Address Confidentiality"],
        )
        self.assertNotIn(
            "ce14bd1aa42c212343ff01bdda80381e",
            domestic_violence["assignments"],
        )
        self.assertNotIn(
            "b47b61d084512681adb9c7ccacf2268c",
            domestic_violence["assignments"],
        )
        domestic_flags = {
            item.get("proposedIdentity"): item
            for item in TAXONOMY_APPLICATION_CLEANUP_FLAGS
        }
        self.assertEqual(
            "availability-verification-required",
            domestic_flags[
                "Arizona Coalition to End Sexual and Domestic Violence — "
                "Survivor Emergency Relief Fund"
            ]["kind"],
        )
        self.assertEqual(
            {
                "962a15177e75cb7770115e0b18c9cfa8",
                "0f7c45b87848334794e5e2f98a15f2fc",
            },
            set(domestic_flags[
                "Maricopa County Southeast Regional Protective Order Center "
                "and Domestic Violence Advocates"
            ]["resourceIds"]),
        )

    def test_type_design_requires_coverage_but_allows_no_type_needed(self) -> None:
        packet = {
            "studyId": 1,
            "categoryId": "caregiving",
            "categoryLabel": "Caregiving",
            "packetSha256": "6" * 64,
            "packet": {
                "typeReviewRules": {"definition": "A Type explains how."},
                "resources": [{"resourceId": "one", "name": "One"}],
            },
        }
        specification = {
            "types": [{"label": "Respite", "definition": "Relief."}],
            "assignments": {},
            "boundary": "Test boundary.",
        }
        with self.assertRaisesRegex(TaxonomyStudyError, "coverage mismatch"):
            build_type_design(packet, specification)
        specification["assignments"] = {"one": "no-type-needed"}
        design = build_type_design(packet, specification)
        self.assertEqual(1, design["coverage"]["noTypeNeededCount"])
        self.assertEqual("no-type-needed", design["assignments"][0]["disposition"])

    def test_group_inference_distinguishes_target_from_accommodation(self) -> None:
        packet = {
            "studyId": 1,
            "packetSha256": "7" * 64,
            "packet": {
                "rules": GROUP_REVIEW_RULES,
                "catalog": [
                    ({**item, "label": "Spanish-speaking"}
                     if item["id"] == "spanish-speaking" else item)
                    for item in GROUP_CATALOG
                ],
                "resources": [
                    {
                        "corpusKey": "automesa-curated:spanish-class",
                        "resourceId": "spanish-class",
                        "name": "Community Class",
                        "priorCategoryIds": ["education"],
                        "proposedCategoryIds": ["education"],
                        "priorForGroups": [],
                        "resource": {
                            "name": "Community Class",
                            "description": "Online GED classes with Spanish-language enrollment help.",
                            "informationText": "",
                        },
                    },
                    {
                        "corpusKey": "automesa-curated:veteran-job",
                        "resourceId": "veteran-job",
                        "name": "Veteran Job Program",
                        "priorCategoryIds": ["employment"],
                        "proposedCategoryIds": ["employment"],
                        "priorForGroups": ["Veterans"],
                        "resource": {
                            "name": "Veteran Job Program",
                            "description": "Career services for veterans.",
                            "informationText": "",
                        },
                    },
                ],
            },
        }
        proposal = infer_group_proposal(packet)
        spanish = proposal["assignments"][0]["groups"]
        self.assertEqual(["Spanish"], [item["label"] for item in spanish])
        self.assertEqual("accommodate", spanish[0]["mode"])
        self.assertNotIn("Hispanic/Latino", [item["label"] for item in spanish])
        veteran = proposal["assignments"][1]["groups"]
        self.assertEqual("target", veteran[0]["mode"])

    def test_specific_disability_evidence_uses_only_disabled_group(self) -> None:
        packet = {
            "studyId": 1,
            "packetSha256": "8" * 64,
            "packet": {
                "rules": GROUP_REVIEW_RULES,
                "catalog": GROUP_CATALOG,
                "resources": [{
                    "corpusKey": "connected-package:vision",
                    "resourceId": "vision",
                    "name": "Vision Service",
                    "priorCategoryIds": ["medical-dental-vision"],
                    "proposedCategoryIds": ["medical-dental-vision"],
                    "priorForGroups": [],
                    "resource": {
                        "name": "Vision Service",
                        "description": "Rehabilitation for blind or low vision adults.",
                        "informationText": "",
                    },
                }],
            },
        }
        labels = {
            item["label"]
            for item in infer_group_proposal(packet)["assignments"][0]["groups"]
        }
        self.assertEqual({"Disabled"}, labels)

    def test_reviewed_spanish_services_are_targets_not_only_accommodations(self) -> None:
        packet = {
            "studyId": 1,
            "packetSha256": "9" * 64,
            "packet": {
                "rules": GROUP_REVIEW_RULES,
                "catalog": GROUP_CATALOG,
                "resources": [
                    {
                        "corpusKey": "automesa-curated:f76b64043d73b489d7067d9f9d856b42",
                        "resourceId": "de-colores",
                        "name": "De Colores",
                        "priorCategoryIds": ["domestic-violence"],
                        "proposedCategoryIds": ["domestic-violence"],
                        "priorForGroups": [],
                        "resource": {
                            "name": "De Colores",
                            "description": "Domestic-violence shelter and Spanish-language services.",
                            "informationText": "",
                        },
                    },
                    {
                        "corpusKey": "automesa-curated:38629d0e712141f7531b4cff4b0bfd53",
                        "resourceId": "duet",
                        "name": "Duet",
                        "priorCategoryIds": ["seniors"],
                        "proposedCategoryIds": ["seniors"],
                        "priorForGroups": [],
                        "resource": {
                            "name": "Duet",
                            "description": "A dedicated Spanish caregiver support group.",
                            "informationText": "",
                        },
                    },
                ],
            },
        }
        assignments = infer_group_proposal(packet)["assignments"]
        for assignment in assignments:
            spanish = next(
                item for item in assignment["groups"] if item["label"] == "Spanish"
            )
            self.assertEqual("target", spanish["mode"])

    def test_chrysalis_uses_family_pathway_not_women_group(self) -> None:
        packet = {
            "studyId": 1,
            "packetSha256": "5" * 64,
            "packet": {
                "rules": GROUP_REVIEW_RULES,
                "catalog": GROUP_CATALOG,
                "resources": [{
                    "corpusKey": "automesa-curated:b666b49c655c08750bdf54de800e82af",
                    "resourceId": "chrysalis",
                    "name": "Chrysalis",
                    "priorCategoryIds": ["domestic-violence"],
                    "proposedCategoryIds": ["domestic-violence"],
                    "priorForGroups": ["Women"],
                    "resource": {
                        "name": "Chrysalis",
                        "description": (
                            "Family shelter and child services documented for women, "
                            "children, and men."
                        ),
                        "informationText": "",
                    },
                }],
            },
        }
        groups = {
            item["label"]: item
            for item in infer_group_proposal(packet)["assignments"][0]["groups"]
        }
        self.assertEqual("target", groups["Families"]["mode"])
        self.assertEqual("target", groups["Domestic violence survivors"]["mode"])
        self.assertNotIn("Women", groups)

    def test_reviewed_domestic_violence_assignments_remove_unsupported_and_accommodate_furniture_bank(self) -> None:
        packet = {
            "studyId": 1,
            "packetSha256": "a" * 64,
            "packet": {
                "rules": GROUP_REVIEW_RULES,
                "catalog": GROUP_CATALOG,
                "resources": [
                    {
                        "corpusKey": "automesa-curated:ce14bd1aa42c212343ff01bdda80381e",
                        "resourceId": "elder-affairs",
                        "name": "Elder Affairs",
                        "priorCategoryIds": ["seniors"],
                        "proposedCategoryIds": ["seniors", "domestic-violence"],
                        "priorForGroups": [],
                        "resource": {
                            "name": "Elder Affairs",
                            "description": "Help with elder abuse, exploitation, scams, and fraud.",
                            "informationText": "",
                        },
                    },
                    {
                        "corpusKey": "automesa-curated:b47b61d084512681adb9c7ccacf2268c",
                        "resourceId": "adult-protective-services",
                        "name": "Adult Protective Services",
                        "priorCategoryIds": ["seniors"],
                        "proposedCategoryIds": ["seniors", "domestic-violence"],
                        "priorForGroups": [],
                        "resource": {
                            "name": "Adult Protective Services",
                            "description": "Reports of vulnerable-adult abuse or unsafe caregiving.",
                            "informationText": "",
                        },
                    },
                    {
                        "corpusKey": "automesa-curated:442b7ced0e864db023bebfb05ecc9870",
                        "resourceId": "bridging-az",
                        "name": "Bridging AZ",
                        "priorCategoryIds": ["clothing-household"],
                        "proposedCategoryIds": ["clothing-household"],
                        "priorForGroups": [],
                        "resource": {
                            "name": "Bridging AZ",
                            "description": "Furniture referrals for people moving from homelessness, domestic violence, treatment, or other crises.",
                            "informationText": "",
                        },
                    },
                ],
            },
        }
        assignments = {
            item["resourceId"]: item
            for item in infer_group_proposal(packet)["assignments"]
        }
        for resource_id in ("elder-affairs", "adult-protective-services"):
            self.assertNotIn(
                "Domestic violence survivors",
                [item["label"] for item in assignments[resource_id]["groups"]],
            )
        bridging_group = next(
            item for item in assignments["bridging-az"]["groups"]
            if item["label"] == "Domestic violence survivors"
        )
        self.assertEqual("accommodate", bridging_group["mode"])

    def test_reviewed_all_age_resources_accommodate_youth(self) -> None:
        reviewed_resources = [
            (
                "automesa-curated:ea77fba8e182ba83a7f60438bece546b",
                "agave-ridge",
                "Addiction treatment serving adolescents and adults.",
            ),
            (
                "automesa-curated:7de41696b045cd6fdb9bb5c25cf7c53f",
                "common-ground",
                "Reentry services for youth and adults.",
            ),
            (
                "automesa-curated:00cca473db91285a4a393f5ba53add8f",
                "chandler-gilbert-arc",
                "Adult disability services that also include adolescents.",
            ),
            (
                "automesa-curated:9630eddb85bca6d59fb0dc70da0935a8",
                "mind-24-7",
                "Walk-in mental-health care for adults and youth.",
            ),
            (
                "automesa-curated:03c08ccec6ec7f669d5594a7c8499d06",
                "wecycle",
                "Refurbished bicycles for adults and youth.",
            ),
        ]
        packet = {
            "studyId": 1,
            "packetSha256": "b" * 64,
            "packet": {
                "rules": GROUP_REVIEW_RULES,
                "catalog": GROUP_CATALOG,
                "resources": [
                    {
                        "corpusKey": corpus_key,
                        "resourceId": resource_id,
                        "name": resource_id,
                        "priorCategoryIds": ["test-category"],
                        "proposedCategoryIds": ["test-category"],
                        "priorForGroups": [],
                        "resource": {
                            "name": resource_id,
                            "description": description,
                            "informationText": "",
                        },
                    }
                    for corpus_key, resource_id, description in reviewed_resources
                ],
            },
        }
        assignments = infer_group_proposal(packet)["assignments"]
        self.assertEqual(len(reviewed_resources), len(assignments))
        for assignment in assignments:
            youth = next(
                item for item in assignment["groups"] if item["label"] == "Youth"
            )
            self.assertEqual("accommodate", youth["mode"])

    def test_group_catalog_matches_michaels_reviewed_vocabulary(self) -> None:
        self.assertEqual({
            "Seniors", "Veterans", "Re-entry", "Pregnant/postpartum",
            "Families", "Disabled", "Youth", "Women", "Men",
            "LGBTQ+", "Spanish", "Immigrants", "Native American", "Homeless",
            "Domestic violence survivors", "Low-income households",
            "Uninsured/underinsured", "Pet owners", "Medically vulnerable",
        }, {item["label"] for item in GROUP_CATALOG})

    def test_caregiving_is_a_need_category_not_a_for_group(self) -> None:
        self.assertNotIn("Caregivers", {item["label"] for item in GROUP_CATALOG})
        self.assertIn(
            "caregiving",
            RESOURCE_TARGETS["eb94f24384f8e51a2b237d7d8c507948"],
        )
        self.assertEqual(
            ["Respite", "Care Coordination"],
            CATEGORY_TYPE_DESIGNS["caregiving"]["assignments"][
                "eb94f24384f8e51a2b237d7d8c507948"
            ],
        )

        packet = {
            "studyId": 1,
            "packetSha256": "d" * 64,
            "packet": {
                "rules": GROUP_REVIEW_RULES,
                "catalog": GROUP_CATALOG,
                "resources": [{
                    "corpusKey": "automesa-curated:foster",
                    "resourceId": "foster",
                    "name": "Foster essentials",
                    "priorCategoryIds": ["clothing-household"],
                    "proposedCategoryIds": ["clothing-household"],
                    "priorForGroups": [],
                    "resource": {
                        "name": "Foster essentials",
                        "description": "Supplies for foster and kinship caregivers.",
                        "informationText": "",
                    },
                }],
            },
        }
        labels = {
            item["label"]
            for item in infer_group_proposal(packet)["assignments"][0]["groups"]
        }
        self.assertEqual({"Families"}, labels)

    def test_need_category_supplies_population_evidence(self) -> None:
        packet = {
            "studyId": 1,
            "packetSha256": "9" * 64,
            "packet": {
                "rules": GROUP_REVIEW_RULES,
                "catalog": GROUP_CATALOG,
                "resources": [{
                    "corpusKey": "automesa-curated:safe-shelter",
                    "resourceId": "safe-shelter",
                    "name": "Safe Shelter",
                    "priorCategoryIds": [],
                    "proposedCategoryIds": ["domestic-violence"],
                    "priorForGroups": [],
                    "resource": {
                        "name": "Safe Shelter",
                        "description": "Emergency shelter and advocacy.",
                        "informationText": "",
                    },
                }],
            },
        }
        assignment = infer_group_proposal(packet)["assignments"][0]
        self.assertEqual(
            ["Domestic violence survivors"],
            [item["label"] for item in assignment["groups"]],
        )
        self.assertEqual(
            "approved-need-category",
            assignment["groups"][0]["evidence"][0]["source"],
        )

    def test_inherited_group_without_support_is_flagged_for_review(self) -> None:
        packet = {
            "studyId": 1,
            "packetSha256": "a" * 64,
            "packet": {
                "rules": GROUP_REVIEW_RULES,
                "catalog": GROUP_CATALOG,
                "resources": [{
                    "corpusKey": "connected-package:generic",
                    "resourceId": "generic",
                    "name": "Generic Service",
                    "priorCategoryIds": ["employment"],
                    "proposedCategoryIds": ["employment"],
                    "priorForGroups": ["Veterans"],
                    "resource": {
                        "name": "Generic Service",
                        "description": "General employment help.",
                        "informationText": "",
                    },
                }],
            },
        }
        assignment = infer_group_proposal(packet)["assignments"][0]
        self.assertEqual("review-existing-only", assignment["reviewStatus"])
        self.assertEqual("existing-only", assignment["groups"][0]["evidenceStatus"])

    def test_full_corpus_review_rejects_false_matches_and_sets_accommodations(self) -> None:
        packet = {
            "studyId": 1,
            "packetSha256": "b" * 64,
            "packet": {
                "rules": GROUP_REVIEW_RULES,
                "catalog": GROUP_CATALOG,
                "resources": [
                    {
                        "corpusKey": "automesa-curated:1bd2fb5b4587feef40252e0630c6c94c",
                        "resourceId": "fsl",
                        "name": "Foundation for Senior Living",
                        "priorCategoryIds": ["independent-living"],
                        "proposedCategoryIds": ["independent-living"],
                        "priorForGroups": [],
                        "resource": {
                            "name": "Foundation for Senior Living",
                            "description": "Adult Foster Care and services for older adults.",
                            "informationText": "",
                        },
                    },
                    {
                        "corpusKey": "automesa-curated:b684b97f8e67ea1cb39778d953a2c4cf",
                        "resourceId": "mvd",
                        "name": "Arizona MVD",
                        "priorCategoryIds": ["id-recovery"],
                        "proposedCategoryIds": ["id-recovery"],
                        "priorForGroups": ["Seniors"],
                        "resource": {
                            "name": "Arizona MVD",
                            "description": (
                                "Free ID cards for people age 65 or older, qualifying "
                                "SSI recipients, youth in DCS custody, and homeless veterans."
                            ),
                            "informationText": "",
                        },
                    },
                    {
                        "corpusKey": "connected-package:6b2d7fcadeec59dea6cd835e732ef55f",
                        "resourceId": "lifewell",
                        "name": "Lifewell Behavioral Wellness / Terros",
                        "priorCategoryIds": ["mental-health"],
                        "proposedCategoryIds": ["mental-health"],
                        "priorForGroups": ["Medically vulnerable"],
                        "resource": {
                            "name": "Lifewell Behavioral Wellness / Terros",
                            "description": "Integrated treatment for serious mental illness.",
                            "informationText": "",
                        },
                    },
                    {
                        "corpusKey": "automesa-curated:8b0cbd343a20dc0118ec3fa8c9a17d1f",
                        "resourceId": "srp",
                        "name": "Salt River Project",
                        "priorCategoryIds": ["utilities-phone-internet"],
                        "proposedCategoryIds": ["utilities-phone-internet"],
                        "priorForGroups": ["Medically vulnerable"],
                        "resource": {
                            "name": "Salt River Project",
                            "description": "A specialized pathway for medically vulnerable utility customers.",
                            "informationText": "",
                        },
                    },
                    {
                        "corpusKey": "automesa-curated:f76b64043d73b489d7067d9f9d856b42",
                        "resourceId": "de-colores",
                        "name": "De Colores",
                        "priorCategoryIds": ["domestic-violence"],
                        "proposedCategoryIds": ["domestic-violence"],
                        "priorForGroups": [],
                        "resource": {
                            "name": "De Colores",
                            "description": "Verify services for men and LGBTQ+ survivors.",
                            "informationText": "",
                        },
                    },
                ],
            },
        }
        assignments = infer_group_proposal(packet)["assignments"]
        self.assertNotIn(
            "Foster youth",
            [item["label"] for item in assignments[0]["groups"]],
        )
        mvd_groups = {item["label"]: item for item in assignments[1]["groups"]}
        self.assertEqual({
            "Homeless",
            "Disabled",
            "Seniors",
            "Veterans",
            "Youth",
        }, set(mvd_groups))
        self.assertTrue(all(
            mvd_groups[label]["mode"] == "accommodate"
            for label in (
                "Homeless", "Disabled", "Seniors", "Veterans", "Youth",
            )
        ))
        self.assertNotIn(
            "Medically vulnerable",
            [item["label"] for item in assignments[2]["groups"]],
        )
        srp_groups = {item["label"]: item for item in assignments[3]["groups"]}
        self.assertEqual("accommodate", srp_groups["Medically vulnerable"]["mode"])
        de_colores_labels = {
            item["label"] for item in assignments[4]["groups"]
        }
        self.assertNotIn("LGBTQ+", de_colores_labels)
        self.assertNotIn("Men", de_colores_labels)

    def test_type_and_group_filtering_ors_within_and_ands_across(self) -> None:
        selected_types = {"Online Education", "GED/HSE"}
        selected_groups = {"Spanish", "Veterans"}
        self.assertTrue(matches_type_and_group_filters(
            resource_types={"Online Education"},
            resource_groups={"Spanish"},
            selected_types=selected_types,
            selected_groups=selected_groups,
        ))
        self.assertTrue(matches_type_and_group_filters(
            resource_types={"GED/HSE"},
            resource_groups={"Veterans"},
            selected_types=selected_types,
            selected_groups=selected_groups,
        ))
        self.assertFalse(matches_type_and_group_filters(
            resource_types={"Online Education"},
            resource_groups={"Youth"},
            selected_types=selected_types,
            selected_groups=selected_groups,
        ))
        self.assertFalse(matches_type_and_group_filters(
            resource_types={"Financial aid"},
            resource_groups={"Veterans"},
            selected_types=selected_types,
            selected_groups=selected_groups,
        ))

    def test_native_review_distinguishes_targets_from_accommodations(self) -> None:
        packet = {
            "studyId": 1,
            "packetSha256": "c" * 64,
            "packet": {
                "rules": GROUP_REVIEW_RULES,
                "catalog": GROUP_CATALOG,
                "resources": [
                    {
                        "corpusKey": "automesa-curated:7edc59ef2bb7bef8e25a7d32fd382159",
                        "resourceId": "eves-place",
                        "name": "Eve's Place Mobile Advocacy",
                        "priorCategoryIds": ["domestic-violence"],
                        "proposedCategoryIds": ["domestic-violence"],
                        "priorForGroups": [],
                        "resource": {
                            "name": "Eve's Place Mobile Advocacy",
                            "description": "Mobile advocacy serving rural and tribal communities.",
                            "informationText": "",
                        },
                    },
                    {
                        "corpusKey": "automesa-curated:5add8558737e9cfc392878fce4cca308",
                        "resourceId": "native-health-wic",
                        "name": "NATIVE HEALTH food pantry and WIC",
                        "priorCategoryIds": ["food"],
                        "proposedCategoryIds": ["food"],
                        "priorForGroups": [],
                        "resource": {
                            "name": "NATIVE HEALTH food pantry and WIC",
                            "description": "Broadly available services administered by an urban Indian health center.",
                            "informationText": "",
                        },
                    },
                    {
                        "corpusKey": "automesa-curated:cfddfe7aec2aa52de1a56c0d3d797d9e",
                        "resourceId": "native-connections",
                        "name": "Native American Connections",
                        "priorCategoryIds": ["addiction"],
                        "proposedCategoryIds": ["addiction"],
                        "priorForGroups": [],
                        "resource": {
                            "name": "Native American Connections",
                            "description": "Traditional healing and dedicated residential programs for two-spirit adults.",
                            "informationText": "",
                        },
                    },
                ],
            },
        }
        assignments = infer_group_proposal(packet)["assignments"]
        eves_groups = {item["label"]: item for item in assignments[0]["groups"]}
        self.assertEqual("accommodate", eves_groups["Native American"]["mode"])
        wic_groups = {item["label"]: item for item in assignments[1]["groups"]}
        self.assertEqual("accommodate", wic_groups["Native American"]["mode"])
        connections_groups = {
            item["label"]: item for item in assignments[2]["groups"]
        }
        self.assertEqual("target", connections_groups["Native American"]["mode"])
        self.assertEqual("target", connections_groups["LGBTQ+"]["mode"])

    def test_reentry_aware_public_education_is_an_accommodation(self) -> None:
        packet = {
            "studyId": 1,
            "packetSha256": "e" * 64,
            "packet": {
                "rules": GROUP_REVIEW_RULES,
                "catalog": GROUP_CATALOG,
                "resources": [{
                    "corpusKey": "automesa-curated:d633e161d87ac6cf94df2a2a6b877ab1",
                    "resourceId": "fxg",
                    "name": "Frank X. Gordon Adult Education",
                    "priorCategoryIds": ["education"],
                    "proposedCategoryIds": ["education"],
                    "priorForGroups": ["Exiting corrections"],
                    "resource": {
                        "name": "Frank X. Gordon Adult Education",
                        "description": (
                            "Reentry-aware GED and ESOL classes open to probationers "
                            "and the general public."
                        ),
                        "informationText": "",
                    },
                }],
            },
        }
        groups = {
            item["label"]: item
            for item in infer_group_proposal(packet)["assignments"][0]["groups"]
        }
        self.assertEqual("accommodate", groups["Re-entry"]["mode"])

    def test_homeless_group_requires_current_homeless_service_evidence(self) -> None:
        self.assertNotIn(
            "homeless-services",
            RESOURCE_TARGETS["617d4be1951f67468b5ddffdb2f670f5"],
        )
        self.assertNotIn(
            "617d4be1951f67468b5ddffdb2f670f5",
            CATEGORY_TYPE_DESIGNS["homeless-services"]["assignments"],
        )

        packet = {
            "studyId": 1,
            "packetSha256": "f" * 64,
            "packet": {
                "rules": GROUP_REVIEW_RULES,
                "catalog": GROUP_CATALOG,
                "resources": [
                    {
                        "corpusKey": "automesa-curated:212ecd27650ff9a74102bc122a331934",
                        "resourceId": "plan",
                        "name": "Phoenix Legal Action Network",
                        "priorCategoryIds": ["immigration"],
                        "proposedCategoryIds": ["immigration"],
                        "priorForGroups": [],
                        "resource": {
                            "name": "Phoenix Legal Action Network",
                            "description": "Immigration help prioritizing people experiencing homelessness.",
                            "informationText": "",
                        },
                    },
                    {
                        "corpusKey": "automesa-curated:15507c56e359f505d8f574491c7962ac",
                        "resourceId": "rsm",
                        "name": "Resurrection Street Ministry",
                        "priorCategoryIds": ["food"],
                        "proposedCategoryIds": ["food"],
                        "priorForGroups": [],
                        "resource": {
                            "name": "Resurrection Street Ministry",
                            "description": (
                                "An access listing mentions people experiencing homelessness, "
                                "but pantry eligibility is uncertain."
                            ),
                            "informationText": "",
                        },
                    },
                ],
            },
        }
        assignments = infer_group_proposal(packet)["assignments"]
        plan_groups = {item["label"]: item for item in assignments[0]["groups"]}
        self.assertEqual("target", plan_groups["Homeless"]["mode"])
        self.assertNotIn(
            "Homeless",
            {item["label"] for item in assignments[1]["groups"]},
        )

    def test_immigration_group_review_corrects_population_evidence(self) -> None:
        packet = {
            "studyId": 1,
            "packetSha256": "6" * 64,
            "packet": {
                "rules": GROUP_REVIEW_RULES,
                "catalog": GROUP_CATALOG,
                "resources": [
                    {
                        "corpusKey": "automesa-curated:4b42cc9c9bed01788a1fdbfe29248adf",
                        "resourceId": "always",
                        "name": "ALWAYS",
                        "priorCategoryIds": ["immigration"],
                        "proposedCategoryIds": ["immigration"],
                        "priorForGroups": [],
                        "resource": {
                            "name": "ALWAYS",
                            "description": "VAWA services and humanitarian representation for youth.",
                            "informationText": "",
                        },
                    },
                    {
                        "corpusKey": "automesa-curated:370e7f0a4f6a63fedd476ff9cc1bfb32",
                        "resourceId": "florence",
                        "name": "Florence Project",
                        "priorCategoryIds": ["immigration"],
                        "proposedCategoryIds": ["immigration"],
                        "priorForGroups": [],
                        "resource": {
                            "name": "Florence Project",
                            "description": "Dedicated Children's Program for unaccompanied immigrant children.",
                            "informationText": "",
                        },
                    },
                    {
                        "corpusKey": "automesa-curated:34603fb44974ece7329a1a2d8ca51f35",
                        "resourceId": "irc",
                        "name": "International Rescue Committee",
                        "priorCategoryIds": ["immigration"],
                        "proposedCategoryIds": ["immigration"],
                        "priorForGroups": [],
                        "resource": {
                            "name": "International Rescue Committee",
                            "description": "Not a general low-income court-defense clinic.",
                            "informationText": "",
                        },
                    },
                ],
            },
        }
        assignments = {
            item["resourceId"]: {
                group["label"]: group for group in item["groups"]
            }
            for item in infer_group_proposal(packet)["assignments"]
        }
        self.assertEqual(
            "target", assignments["always"]["Domestic violence survivors"]["mode"]
        )
        self.assertEqual("target", assignments["always"]["Youth"]["mode"])
        self.assertEqual("target", assignments["florence"]["Youth"]["mode"])
        self.assertNotIn("Low-income households", assignments["irc"])

    def test_senior_review_distinguishes_pathways_from_division_names(self) -> None:
        packet = {
            "studyId": 1,
            "packetSha256": "1" * 64,
            "packet": {
                "rules": GROUP_REVIEW_RULES,
                "catalog": GROUP_CATALOG,
                "resources": [
                    {
                        "corpusKey": "automesa-curated:33560faa0e326f7d9f179cfc8f356488",
                        "resourceId": "allthrive-rides",
                        "name": "AllThrive Transportation",
                        "priorCategoryIds": ["transportation"],
                        "proposedCategoryIds": ["transportation"],
                        "priorForGroups": ["Seniors"],
                        "resource": {
                            "name": "AllThrive Transportation",
                            "description": "Volunteer rides for older adults and other community members.",
                            "informationText": "",
                        },
                    },
                    {
                        "corpusKey": "automesa-curated:fa0719b16ad0843652d8175fb792ca87",
                        "resourceId": "mesa-utilities",
                        "name": "City of Mesa Utilities",
                        "priorCategoryIds": ["utilities-phone-internet"],
                        "proposedCategoryIds": ["utilities-phone-internet"],
                        "priorForGroups": ["Seniors"],
                        "resource": {
                            "name": "City of Mesa Utilities",
                            "description": "Limited-income senior water-rate discount.",
                            "informationText": "",
                        },
                    },
                    {
                        "corpusKey": "automesa-curated:bcc694b6232b6b88cd40c57d3052f4ca",
                        "resourceId": "county-cap",
                        "name": "Maricopa County Human Services",
                        "priorCategoryIds": ["financial-assistance"],
                        "proposedCategoryIds": ["financial-assistance"],
                        "priorForGroups": ["Seniors"],
                        "resource": {
                            "name": "Maricopa County Human Services",
                            "description": "General aid administered by the Senior Services and Community Resilience Division.",
                            "informationText": "",
                        },
                    },
                ],
            },
        }
        assignments = infer_group_proposal(packet)["assignments"]
        for index in (0, 1):
            groups = {item["label"]: item for item in assignments[index]["groups"]}
            self.assertEqual("accommodate", groups["Seniors"]["mode"])
        self.assertNotIn(
            "Seniors",
            {item["label"] for item in assignments[2]["groups"]},
        )

    def test_general_legal_clinic_accommodates_veterans(self) -> None:
        packet = {
            "studyId": 1,
            "packetSha256": "2" * 64,
            "packet": {
                "rules": GROUP_REVIEW_RULES,
                "catalog": GROUP_CATALOG,
                "resources": [{
                    "corpusKey": "automesa-curated:138a8c6f2c950488f75f8766e2ef6252",
                    "resourceId": "legal-center",
                    "name": "Arizona Legal Center",
                    "priorCategoryIds": ["legal"],
                    "proposedCategoryIds": ["legal"],
                    "priorForGroups": ["Veterans"],
                    "resource": {
                        "name": "Arizona Legal Center",
                        "description": "General legal consultations include veterans issues.",
                        "informationText": "",
                    },
                }],
            },
        }
        groups = {
            item["label"]: item
            for item in infer_group_proposal(packet)["assignments"][0]["groups"]
        }
        self.assertEqual("accommodate", groups["Veterans"]["mode"])

    def test_multiple_categories_are_ored(self) -> None:
        self.assertTrue(matches_category_filter(
            resource_categories={"education", "employment"},
            selected_categories={"housing", "education"},
        ))
        self.assertFalse(matches_category_filter(
            resource_categories={"education"},
            selected_categories={"housing", "food"},
        ))

    def test_group_browse_deduplicates_within_each_need_heading(self) -> None:
        resources = [
            {
                "corpusKey": "resource:one",
                "categoryIds": ["education", "employment"],
                "groupIds": ["spanish-speaking", "veterans"],
            },
            {
                "corpusKey": "resource:two",
                "categoryIds": ["education"],
                "groupIds": ["youth-young-adults"],
            },
        ]
        rows = group_browse_category_rows(
            resources,
            selected_groups={"spanish-speaking", "veterans"},
        )
        self.assertEqual({
            "education": ["resource:one"],
            "employment": ["resource:one"],
        }, rows)


if __name__ == "__main__":
    unittest.main()
