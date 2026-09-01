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
from resource_research_agent.taxonomy_study import (
    TaxonomyStudyError,
    prepare_taxonomy_study,
    taxonomy_study_summary,
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


if __name__ == "__main__":
    unittest.main()
