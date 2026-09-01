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
    NEW_CATEGORY_TYPE_DESIGNS,
    build_type_design,
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
            "children-pregnancy", "disability", "reentry-support",
            "miscellaneous", "seniors", "veterans",
        }
        self.assertTrue(RESOURCE_TARGETS)
        for resource_id, targets in RESOURCE_TARGETS.items():
            with self.subTest(resource_id=resource_id):
                self.assertTrue(targets)
                self.assertEqual(len(targets), len(set(targets)))
                self.assertFalse(retired.intersection(targets))

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
                ],
            },
        }
        proposal = build_mesa_category_redistribution_proposal(study)
        assignments = proposal["assignments"]
        self.assertEqual(len(RESOURCE_TARGETS), len(assignments))
        self.assertEqual(
            set(RESOURCE_TARGETS),
            {item["resourceId"] for item in assignments},
        )
        self.assertEqual(0, proposal["coverage"]["unassignedCount"])
        self.assertEqual(20, proposal["coverage"]["targetCategoryCounts"][
            "parenting-child-development"
        ])
        self.assertEqual(18, proposal["coverage"]["targetCategoryCounts"][
            "independent-living"
        ])
        self.assertEqual(10, proposal["coverage"]["targetCategoryCounts"][
            "caregiving"
        ])

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

    def test_new_category_type_designs_have_compact_unique_labels(self) -> None:
        for category_id, specification in NEW_CATEGORY_TYPE_DESIGNS.items():
            labels = [item["label"] for item in specification["types"]]
            with self.subTest(category_id=category_id):
                self.assertEqual(len(labels), len(set(labels)))
                self.assertTrue(all(len(label) <= 24 for label in labels))

    def test_new_category_type_designs_cover_redistributed_resources(self) -> None:
        for category_id in (
            "parenting-child-development",
            "independent-living",
            "caregiving",
        ):
            specification = NEW_CATEGORY_TYPE_DESIGNS[category_id]
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
        housing = NEW_CATEGORY_TYPE_DESIGNS["housing"]
        housing_labels = {item["label"] for item in housing["types"]}
        self.assertIn("Emergency Shelter", housing_labels)
        self.assertIn("Rapid Rehousing", housing_labels)
        self.assertIn("Rental Assistance", housing_labels)
        self.assertNotIn("Veterans", housing_labels)
        self.assertNotIn("Seniors", housing_labels)

        homeless = NEW_CATEGORY_TYPE_DESIGNS["homeless-services"]
        self.assertEqual(
            homeless["assignments"]["0df6bb236d8c7bf168ce4867dc83360e"],
            "no-type-needed",
        )
        self.assertIn(
            "Street Outreach",
            homeless["assignments"]["91d5cdd19b42853fb4bbe8e57f325be0"],
        )

        financial = NEW_CATEGORY_TYPE_DESIGNS["financial-assistance"]
        self.assertIn(
            "Disability Income",
            financial["assignments"]["8d70eda15ed4d365bd3ffb2577c8653e"],
        )
        self.assertIn(
            "Benefits Navigation",
            financial["assignments"]["c6862828db3631873bf2eb1f4ff99bea"],
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


if __name__ == "__main__":
    unittest.main()
