from __future__ import annotations

import hashlib
import json
import tempfile
import threading
import unittest
import urllib.request
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from resource_research_agent.autocurator import (
    AutoCuratorError,
    build_autocurator_seed,
    next_autocurator_assignment,
    prepare_autocurator_job,
    progress_heartbeat_due,
    save_autocurator_result,
    schedule_chatgpt_assignment,
)
from resource_research_agent.autocurator_generation import (
    build_autocurator_review_file,
)
from resource_research_agent.duplicates import DuplicateIndex
from resource_research_agent.importer import ResourcePackageImporter
from resource_research_agent.manual_consolidation import (
    consolidate_manual_discovery,
    finish_manual_discovery,
)
from resource_research_agent.server import ResearchHTTPServer
from resource_research_agent.storage import ResearchStore


def assignment_digest(assignment: dict) -> str:
    snapshot = dict(assignment)
    snapshot.pop("assignmentSha256", None)
    encoded = json.dumps(
        snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class FixedRandom:
    def __init__(self, value: int) -> None:
        self.value = value

    def randint(self, lower: int, upper: int) -> int:
        if not lower <= self.value <= upper:
            raise AssertionError("Fixed random value is outside the requested range")
        return self.value


class AutoCuratorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.store = ResearchStore(self.root / "research.sqlite3")
        package_path = self.root / "mesa-resource-package.zip"
        with zipfile.ZipFile(package_path, "w") as archive:
            archive.writestr("tso-resources.json", json.dumps({
                "resourcePackageSchemaVersion": 3,
                "packageVersion": 8,
                "officeName": "Mesa TSO",
                "serviceArea": "Mesa and Maricopa County, Arizona",
                "categories": [
                    {"id": "employment", "name": "Employment", "filters": []},
                    {"id": "food", "name": "Food", "filters": []},
                    {"id": "miscellaneous", "name": "Miscellaneous", "filters": []},
                ],
                "forGroups": ["Veterans"],
                "resources": [],
            }))
        self.import_id = self.store.save_import(
            ResourcePackageImporter("Employment").read(package_path)
        )
        self.old_employment_run = self.completed_run(
            "employment", "Employment", ["Earlier AI"]
        )
        self.employment_run = self.completed_run(
            "employment", "Employment", ["ChatGPT", "Claude"]
        )
        self.food_run = self.completed_run("food", "Food", ["Grok"])

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def completed_run(
        self, category_id: str, category_label: str, sources: list[str]
    ) -> int:
        run_id = self.store.create_manual_discovery_run(
            f"Find {category_label} resources",
            {"researchContext": {"mode": "package"}},
            self.import_id,
            target_category_id=category_id,
            target_category_label=category_label,
        )
        for position, source in enumerate(sources, start=1):
            self.store.save_manual_contribution(run_id, source, json.dumps({
                "leads": [{
                    "organization": f"{category_label} Provider {run_id}-{position}",
                    "program": f"{category_label} Program {run_id}-{position}",
                    "website": f"https://example.org/{category_id}/{run_id}/{position}",
                    "phone": f"480-555-{run_id:02d}{position:02d}",
                    "address": f"{run_id}{position} Main Street, Mesa, AZ",
                    "leadType": "program",
                    "locationOrServiceArea": "Mesa",
                    "whyRelevant": f"Provides {category_label.lower()} help.",
                    "uncertainty": "Confirm hours.",
                }]
            }))
        consolidate_manual_discovery(self.store, run_id, DuplicateIndex(self.store))
        finish_manual_discovery(self.store, run_id)
        return run_id

    def result_for(
        self,
        assignment: dict,
        *,
        resource_id: str,
        categories: list[str] | None = None,
        candidate_ids: list[str] | None = None,
    ) -> dict:
        current_ids = [str(item["id"]) for item in assignment["candidates"]]
        all_candidate_ids = candidate_ids or current_ids
        return {
            "autoCuratorResultSchemaVersion": 1,
            "assignmentSha256": assignment["assignmentSha256"],
            "categoryId": assignment["category"]["id"],
            "resources": [{
                "id": resource_id,
                "name": "Mesa Community Assistance",
                "description": "Connects Mesa residents with practical help.",
                "informationText": "Call or visit the website to confirm eligibility.",
                "categories": categories or [assignment["category"]["id"]],
                "categoryFilters": {},
                "forGroups": ["Veterans"],
                "candidateIds": all_candidate_ids,
            }],
            "candidateDispositions": [
                {
                    "candidateId": candidate_id,
                    "disposition": "curated",
                    "resourceIds": [resource_id],
                    "reason": "",
                }
                for candidate_id in current_ids
            ],
        }

    def test_prepares_resumable_job_and_uses_most_complete_category_run(self) -> None:
        job = prepare_autocurator_job(self.store, self.import_id)
        self.assertEqual(["employment", "food"], [
            item["categoryId"] for item in job["categories"]
        ])
        self.assertEqual(
            self.employment_run, job["categories"][0]["canonicalRunId"]
        )
        self.assertEqual(2, job["categories"][0]["candidateCount"])
        self.assertEqual(
            job["categories"][0]["assignmentSha256"],
            assignment_digest(job["categories"][0]["assignment"]),
        )
        self.assertEqual(
            job["candidatePackageSha256"],
            job["categories"][0]["assignment"]["candidatePackageSha256"],
        )
        self.assertEqual(
            ["employment", "food"],
            [
                item["id"]
                for item in job["categories"][0]["assignment"]["availableCategories"]
            ],
        )
        self.assertEqual(
            ["Veterans"],
            job["categories"][0]["assignment"]["availableForGroups"],
        )
        resumed = prepare_autocurator_job(self.store, self.import_id)
        self.assertEqual(job["id"], resumed["id"])
        self.assertEqual(1, len(self.store.list_autocurator_jobs(self.import_id)))

    def test_new_research_snapshot_creates_a_new_job_without_rewriting_the_old_one(self) -> None:
        original = prepare_autocurator_job(self.store, self.import_id)
        newer_run = self.completed_run(
            "employment", "Employment", ["ChatGPT", "Claude", "Grok"]
        )
        refreshed = prepare_autocurator_job(self.store, self.import_id)
        self.assertNotEqual(original["id"], refreshed["id"])
        self.assertNotEqual(
            original["candidatePackageSha256"], refreshed["candidatePackageSha256"]
        )
        self.assertEqual(newer_run, refreshed["categories"][0]["canonicalRunId"])
        preserved = self.store.get_autocurator_job(original["id"])
        self.assertEqual(
            self.employment_run, preserved["categories"][0]["canonicalRunId"]
        )

    def test_curates_one_category_at_a_time_and_builds_all_category_seed(self) -> None:
        job = prepare_autocurator_job(self.store, self.import_id)
        employment = next_autocurator_assignment(self.store, job["id"])
        self.assertEqual("employment", employment["category"]["id"])
        self.assertEqual(employment["assignmentSha256"], assignment_digest(employment))
        employment_result = self.result_for(employment, resource_id="mesa-help")
        saved = save_autocurator_result(
            self.store, job["id"], "employment", employment_result
        )
        self.assertEqual(1, saved["progress"]["completed"])

        food = next_autocurator_assignment(self.store, job["id"])
        self.assertEqual("food", food["category"]["id"])
        self.assertEqual(1, len(food["previouslyCuratedResources"]))
        old_candidate_ids = employment_result["resources"][0]["candidateIds"]
        food_candidate_ids = [str(item["id"]) for item in food["candidates"]]
        food_result = self.result_for(
            food,
            resource_id="mesa-help",
            categories=["employment", "food"],
            candidate_ids=old_candidate_ids + food_candidate_ids,
        )
        completed = save_autocurator_result(
            self.store, job["id"], "food", food_result
        )
        self.assertEqual("completed", completed["status"])
        self.assertIsNone(next_autocurator_assignment(self.store, job["id"]))

        seed = build_autocurator_seed(self.store, job["id"])
        self.assertEqual(["employment", "food"], [
            item["id"] for item in seed["categories"]
        ])
        self.assertEqual(1, len(seed["resources"]))
        self.assertEqual(["employment", "food"], seed["resources"][0]["categories"])
        self.assertNotIn("candidateIds", seed["resources"][0])
        self.assertEqual([], seed["deletions"])
        phases = [
            event["phase"] for event in self.store.list_autocurator_progress(job["id"])
        ]
        self.assertEqual(1, phases.count("curation-completed"))

    def test_rejects_a_result_that_does_not_cover_the_assignment(self) -> None:
        job = prepare_autocurator_job(self.store, self.import_id)
        assignment = next_autocurator_assignment(self.store, job["id"])
        result = self.result_for(assignment, resource_id="mesa-help")
        result["candidateDispositions"].pop()
        with self.assertRaisesRegex(AutoCuratorError, "missing candidate dispositions"):
            save_autocurator_result(
                self.store, job["id"], "employment", result
            )
        result = self.result_for(assignment, resource_id="mesa-help")
        result["assignmentSha256"] = "0" * 64
        with self.assertRaisesRegex(AutoCuratorError, "assigned curation snapshot"):
            save_autocurator_result(
                self.store, job["id"], "employment", result
            )
        result = self.result_for(assignment, resource_id="mesa-help")
        result["resources"][0]["candidateIds"].pop()
        with self.assertRaisesRegex(AutoCuratorError, "missing contributing candidate IDs"):
            save_autocurator_result(
                self.store, job["id"], "employment", result
            )

    def test_chatgpt_schedule_and_progress_reporting_policy(self) -> None:
        completed_at = datetime(2026, 8, 28, 18, 0, tzinfo=timezone.utc)
        schedule = schedule_chatgpt_assignment(
            completed_at,
            FixedRandom(14),
            adjustment_minutes=6,
            reason="Recent responses suggest lighter throttling is prudent.",
        )
        self.assertEqual(20, schedule.delay_minutes)
        self.assertEqual(completed_at + timedelta(minutes=20), schedule.scheduled_at)
        self.assertIn("wait 20 minutes", schedule.message)
        self.assertIn("lighter throttling", schedule.message)
        reset_at = completed_at + timedelta(minutes=37, seconds=30)
        reset_schedule = schedule_chatgpt_assignment(
            completed_at,
            FixedRandom(10),
            explicit_reset_at=reset_at,
        )
        self.assertEqual(38, reset_schedule.delay_minutes)
        self.assertEqual(reset_at, reset_schedule.scheduled_at)
        self.assertIn("explicit reset time", reset_schedule.message)
        self.assertFalse(progress_heartbeat_due(completed_at, completed_at + timedelta(minutes=14)))
        self.assertTrue(progress_heartbeat_due(completed_at, completed_at + timedelta(minutes=15)))

    def test_http_contract_exposes_durable_assignments_results_and_progress(self) -> None:
        web_dir = Path(__file__).resolve().parent.parent / "web"
        server = ResearchHTTPServer(("127.0.0.1", 0), self.store, web_dir)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_address[1]}"

        def post(path: str, value: dict) -> dict:
            request = urllib.request.Request(
                base + path,
                data=json.dumps(value).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=5) as response:
                return json.loads(response.read())

        try:
            job = post("/api/autocurator-jobs", {"importId": self.import_id})
            assignment = post(
                f"/api/autocurator-jobs/{job['id']}/next-assignment", {}
            )["assignment"]
            result = self.result_for(assignment, resource_id="mesa-help")
            saved = post(f"/api/autocurator-jobs/{job['id']}/results", {
                "categoryId": "employment",
                "result": result,
            })
            self.assertEqual(1, saved["progress"]["completed"])
            event = post(f"/api/autocurator-jobs/{job['id']}/progress", {
                "categoryId": "food",
                "phase": "curation-heartbeat",
                "message": "Food curation is still in progress.",
                "details": {"elapsedMinutes": 15},
            })
            self.assertEqual("curation-heartbeat", event["phase"])
            with urllib.request.urlopen(
                base + f"/api/autocurator-jobs/{job['id']}/progress", timeout=5
            ) as response:
                events = json.loads(response.read())["events"]
            self.assertEqual("curation-heartbeat", events[-1]["phase"])
            with urllib.request.urlopen(
                base + f"/api/autocurator-jobs?importId={self.import_id}", timeout=5
            ) as response:
                jobs = json.loads(response.read())["jobs"]
            self.assertEqual([job["id"]], [item["id"] for item in jobs])
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    def test_builds_versioned_review_file_through_resource_assistant(self) -> None:
        job = prepare_autocurator_job(self.store, self.import_id)
        employment = next_autocurator_assignment(self.store, job["id"])
        employment_result = self.result_for(employment, resource_id="mesa-help")
        save_autocurator_result(
            self.store, job["id"], "employment", employment_result
        )
        food = next_autocurator_assignment(self.store, job["id"])
        old_candidate_ids = employment_result["resources"][0]["candidateIds"]
        food_candidate_ids = [str(item["id"]) for item in food["candidates"]]
        save_autocurator_result(
            self.store,
            job["id"],
            "food",
            self.result_for(
                food,
                resource_id="mesa-help",
                categories=["employment", "food"],
                candidate_ids=old_candidate_ids + food_candidate_ids,
            ),
        )

        checkout = self.root / "resource-assistant"
        (checkout / "src").mkdir(parents=True)
        (checkout / "src" / "release.json").write_text(json.dumps({
            "version": "2.3.5",
            "build": 151,
        }), encoding="utf-8")
        (checkout / "make-autocurator").write_text(
            """import argparse, json, pathlib, zipfile
parser = argparse.ArgumentParser()
parser.add_argument('candidates')
parser.add_argument('--seed', required=True)
parser.add_argument('--output', required=True)
args = parser.parse_args()
with zipfile.ZipFile(args.candidates) as archive:
    candidate = json.loads(archive.read('scout-candidates.json'))
seed = json.loads(pathlib.Path(args.seed).read_text())
location = candidate['location']['name']
pathlib.Path(args.output).write_text(
    f'<meta name="autocurator-location-name" content="{location}">'
    f'<script id="seed-data" type="application/json">{json.dumps(seed)}</script>'
)
""",
            encoding="utf-8",
        )

        review_file = build_autocurator_review_file(
            self.store, job["id"], checkout
        )
        self.assertEqual("autoMesa.html", review_file.filename)
        self.assertEqual("2.3.5", review_file.resource_assistant_version)
        self.assertEqual(151, review_file.resource_assistant_build)
        self.assertIn(b'"employment", "food"', review_file.content)
        last_event = self.store.list_autocurator_progress(job["id"])[-1]
        self.assertEqual("review-file-built", last_event["phase"])
        self.assertEqual(151, last_event["details"]["resourceAssistantBuild"])


if __name__ == "__main__":
    unittest.main()
