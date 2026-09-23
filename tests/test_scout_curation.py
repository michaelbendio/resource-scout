from __future__ import annotations

import hashlib
import json
import re
import tempfile
import threading
import unittest
import urllib.request
import zipfile
from unittest.mock import patch
from datetime import datetime, timedelta, timezone
from pathlib import Path

from resource_research_agent import __build__, __version__
from resource_research_agent.scout_curation import (
    ScoutCurationError,
    build_scout_review_seed,
    next_scout_curation_assignment,
    prepare_scout_curation_job,
    progress_heartbeat_due,
    save_scout_curation_result,
    schedule_chatgpt_assignment,
)
from resource_research_agent.scout_review import (
    build_scout_review_file,
)
from resource_research_agent.scout_curation_revision import revise_scout_curation_result
from resource_research_agent.scout_review_handoff import complete_codex_review, review_fingerprint, review_handoff
from resource_research_agent.scout_progress import build_scout_progress
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


class ScoutCurationTests(unittest.TestCase):
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

    def complete_test_review(self, job_id):
        from resource_research_agent.scout_curation import _completed_resources
        from resource_research_agent.scout_navigation import save_navigation
        from resource_research_agent.scout_review_handoff import curation_fingerprint
        job = self.store.get_scout_curation_job(job_id)
        resources = _completed_resources(job)
        proposal = {'schemaVersion':1, 'baseFingerprint':curation_fingerprint(job),
            'categories':[{'id':c['categoryId'],'types':[{'label':'Direct help','definition':'Practical assistance in this category'}]} for c in job['categories']],
            'groups':[{'label':'Veterans','definition':'Programs serving veterans'}],
            'assignments':[{'resourceId':r['id'],
                'types':{c:[{'label':'Direct help','evidence':{'field':'description','text':r['description']}}] for c in r['categories']},
                'forGroups':[{'label':'Veterans','evidence':{'field':'informationText','text':'Veterans'}}]} for r in resources]}
        if job['status'] == 'completed':
            save_navigation(self.store, job_id, proposal, reason='Reviewed test fixture navigation')
            self.save_test_priorities(job_id)
        report = self.root / "review-report.md"
        report.write_text("Test fixture review: checked identities, sources, omissions and consolidation.")
        return complete_codex_review(self.store, job_id,
            expected_fingerprint=review_fingerprint(self.store.get_scout_curation_job(job_id)), report_path=report)

    def save_test_priorities(self, job_id):
        from resource_research_agent.scout_review_priorities import save_priorities, priority_source_seed
        from resource_research_agent.scout_review_handoff import priority_base_fingerprint
        job = self.store.get_scout_curation_job(job_id)
        seed = priority_source_seed(self.store, job)
        proposal = {'schemaVersion':1, 'baseFingerprint':priority_base_fingerprint(job),
            'assignments':[{'resourceId':r['id'],'categoryId':cid,'tier':'start',
                'reason':'Establish this direct local intake route first.',
                'question':'What is the current intake process?',
                'evidence':{'field':'description','text':r['description']}}
                for r in seed['resources'] for cid in r['categories']]}
        return save_priorities(self.store,job_id,proposal,reason='Reviewed priority fixture')

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
            "scoutCurationResultSchemaVersion": 1,
            "assignmentSha256": assignment["assignmentSha256"],
            "categoryId": assignment["category"]["id"],
            "resources": [{
                "id": resource_id,
                "name": "Mesa Community Assistance",
                "description": "Connects Mesa residents with practical help.",
                "informationText": "**Eligibility Requirements**\n\nVeterans in Mesa.\n\n**How to Best Connect**\n\nCall to apply.\n\n**Access**\n\nConfirm appointment hours.\n\n**Important Information to Know**\n\nConfirm availability.",
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

    def test_completed_codex_plan_does_not_mask_curation_or_review(self) -> None:
        job = prepare_scout_curation_job(self.store, self.import_id)
        completed_plan = [{
            "categoryId": category, "status": "completed",
            "experimentMode": "codex-first", "updatedAt": "2020-01-01T00:00:00Z",
            "progress": {"completed": 4, "total": 4, "leadCount": 4},
        } for category in ("employment", "food")]
        from resource_research_agent.focused_research import CODEX_FIRST_EXPERIMENT_MODE
        for item in completed_plan:
            item["experimentMode"] = CODEX_FIRST_EXPERIMENT_MODE
        with patch.object(self.store, "list_focused_research_jobs", return_value=completed_plan):
            assignment = next_scout_curation_assignment(self.store, job["id"])
            self.store.record_scout_curation_progress(
                job["id"], "codex-curation-active", "Curating Employment",
                category_id="employment",
            )
            progress = build_scout_progress(self.store, self.import_id)
            self.assertEqual("codex-curation-active", progress["phase"])
            self.assertEqual("employment", progress["categoryId"])
            self.assertEqual({"completed": 2, "total": 2}, progress["research"])
            save_scout_curation_result(self.store, job["id"], "employment",
                                      self.result_for(assignment, resource_id="work"))
            self.assertEqual(1, build_scout_progress(self.store, self.import_id)["curation"]["completed"])
            assignment = next_scout_curation_assignment(self.store, job["id"])
            save_scout_curation_result(self.store, job["id"], "food",
                                      self.result_for(assignment, resource_id="food"))
            build_scout_review_file(self.store, job["id"])
            progress = build_scout_progress(self.store, self.import_id)
            self.assertEqual("awaiting-codex-review", progress["phase"])
            self.assertFalse(progress["reviewFile"]["readyForSave"])
            self.complete_test_review(job["id"])
            progress = build_scout_progress(self.store, self.import_id)
            self.assertEqual("codex-review-completed", progress["phase"])
            self.assertEqual(2, progress["curation"]["completed"])
            self.assertEqual("created", progress["reviewFile"]["status"])

    def test_review_is_bound_to_exact_results_and_cannot_approve_incomplete_curation(self):
        job = prepare_scout_curation_job(self.store, self.import_id)
        with self.assertRaisesRegex(ScoutCurationError, "Complete curation"):
            self.complete_test_review(job["id"])
        for category in ("employment", "food"):
            assignment = next_scout_curation_assignment(self.store, job["id"])
            save_scout_curation_result(self.store, job["id"], category,
                                      self.result_for(assignment, resource_id=category))
        self.assertTrue(self.complete_test_review(job["id"])["readyForSave"])
        job = self.store.get_scout_curation_job(job["id"])
        original_fingerprint = review_fingerprint(job)
        category = job["categories"][0]
        result = json.loads(json.dumps(category["result"]))
        result["resources"][0]["informationText"] = result["resources"][0]["informationText"].replace("Veterans in Mesa.", "Veterans in Mesa; eligibility corrected from source evidence.")
        revised = revise_scout_curation_result(self.store, job["id"], category["categoryId"], result,
            expected_result_sha256=category["resultSha256"], reason="Correct eligibility",
            evidence=[{"url":"https://example.org/eligibility"}])
        self.assertFalse(review_handoff(revised, self.store.list_scout_curation_progress(job["id"]))["readyForSave"])
        with self.assertRaisesRegex(ScoutCurationError, "changed since the review"):
            complete_codex_review(self.store, job["id"], expected_fingerprint=original_fingerprint,
                                 report_path=self.root / "review-report.md")
        with self.assertRaisesRegex(ScoutCurationError, "different curation results"):
            build_scout_review_seed(self.store, job["id"])
        self.assertTrue(self.complete_test_review(job["id"])["readyForSave"])

    def completed_review_fixture(self):
        job = prepare_scout_curation_job(self.store, self.import_id)
        for category in ("employment", "food"):
            assignment = next_scout_curation_assignment(self.store, job["id"])
            save_scout_curation_result(self.store, job["id"], category,
                                      self.result_for(assignment, resource_id=category))
        return self.store.get_scout_curation_job(job["id"])

    def test_handoff_rejects_missing_navigation_and_monitor_explains_it(self):
        job = self.completed_review_fixture()
        report = self.root / "report.md"
        report.write_text("Source review alone is insufficient.")
        with self.assertRaisesRegex(ScoutCurationError, "Types and For-group review"):
            complete_codex_review(self.store, job['id'],
                expected_fingerprint=review_fingerprint(job), report_path=report)
        progress = build_scout_progress(self.store, self.import_id)
        self.assertFalse(progress['reviewFile']['readyForSave'])
        self.assertIn('For-group review', progress['reviewFile']['readinessIssue'])
        # A legacy approval of exactly the same results is insufficient.
        legacy = [{'phase':'codex-review-completed','createdAt':'earlier',
                   'details':{'resultFingerprint':review_fingerprint(job)}}]
        self.assertFalse(review_handoff(job, legacy)['readyForSave'])

    def test_information_sections_and_type_coverage_are_release_requirements(self):
        from resource_research_agent.scout_review_readiness import validate_ready_seed
        job = self.completed_review_fixture()
        self.complete_test_review(job['id'])
        seed = build_scout_review_seed(self.store, job['id'])
        self.assertEqual(2, validate_ready_seed(seed)['resources'])
        for bad in ('Eligibility: Veterans. Connect: Call. Access: Varies. Important: Confirm.',
                    seed['resources'][0]['informationText'].replace('Call to apply.', '')):
            broken = json.loads(json.dumps(seed))
            broken['resources'][0]['informationText'] = bad
            with self.assertRaisesRegex(ScoutCurationError, 'Information'):
                validate_ready_seed(broken)
        seed['resources'][0]['categoryFilters'] = {}
        with self.assertRaisesRegex(ScoutCurationError, 'Types'):
            validate_ready_seed(seed)

    def test_navigation_requires_approved_disability_parents_and_exports_definitions(self):
        from resource_research_agent.scout_navigation import latest_navigation, save_navigation
        job = self.completed_review_fixture()
        self.complete_test_review(job['id'])
        proposal = latest_navigation(self.store, job['id'])['proposal']
        proposal['groups'] = [
            {'label':'Deaf & hard of hearing','definition':'Hearing-specific services'},
            {'label':'People with disabilities','definition':'Disability-specific services'},
        ]
        for assignment in proposal['assignments']:
            # Synthetic evidence exercises structure, not a real population judgment.
            evidence = assignment['forGroups'][0]['evidence']
            assignment['forGroups'] = [{'label':'Deaf & hard of hearing','evidence':evidence}]
        with self.assertRaisesRegex(ScoutCurationError, 'also requires People with disabilities'):
            save_navigation(self.store, job['id'], proposal, reason='Invalid missing parent fixture')
        for assignment in proposal['assignments']:
            assignment['forGroups'].append({'label':'People with disabilities','evidence':assignment['forGroups'][0]['evidence']})
        saved = save_navigation(self.store, job['id'], proposal, reason='Approved parent fixture')
        seed = build_scout_review_seed(self.store, job['id'])
        self.assertEqual({'description':'Hearing-specific services','lastModified':saved['createdAt']},
                         seed['forGroupDefinitions']['Deaf & hard of hearing'])
        self.assertTrue(all('forGroupReview' not in r for r in seed['resources']))

    def test_navigation_is_evidenced_complete_and_invalidates_saved_review(self):
        from resource_research_agent.scout_navigation import latest_navigation, save_navigation
        job = self.completed_review_fixture()
        before = build_scout_review_seed(self.store, job['id'])
        self.complete_test_review(job['id'])
        navigation = latest_navigation(self.store, job['id'])
        proposal = navigation['proposal']
        for mutation, message in (
            (lambda p:p['assignments'].pop(), 'every resource'),
            (lambda p:p['assignments'][0]['forGroups'].clear(), 'no-group decision'),
            (lambda p:p['assignments'][0]['types'].clear(), 'exactly the Categories'),
            (lambda p:p['assignments'][0]['forGroups'][0]['evidence'].update(text='Invented population'), 'evidence'),
        ):
            broken = json.loads(json.dumps(proposal)); mutation(broken)
            with self.assertRaisesRegex(ScoutCurationError, message):
                save_navigation(self.store, job['id'], broken, reason='Invalid fixture')
        proposal['assignments'][0]['forGroups'] = []
        proposal['assignments'][0]['noGroupReason'] = None
        with self.assertRaisesRegex(ScoutCurationError, 'no-group decision'):
            save_navigation(self.store, job['id'], proposal, reason='Null reason is not review')
        proposal['assignments'][0]['noGroupReason'] = 'Reviewed as broadly available.'
        saved = save_navigation(self.store, job['id'], proposal, reason='Revise population decision')
        self.assertEqual(saved['id'], save_navigation(self.store, job['id'], proposal, reason='Idempotent')['id'])
        after = build_scout_review_seed(self.store, job['id'])
        for old,new in zip(before['resources'],after['resources']):
            for key in old:
                if key not in {'categoryFilters','forGroups'}:
                    self.assertEqual(old[key],new[key])
        job = self.store.get_scout_curation_job(job['id'])
        self.assertFalse(review_handoff(job, self.store.list_scout_curation_progress(job['id']))['readyForSave'])
        self.assertEqual([],after['resources'][0]['forGroups'])
        # A deliberate all-ungrouped design differs from silently skipping review.
        proposal['groups'] = []
        for assignment in proposal['assignments']:
            assignment['forGroups'] = []
            assignment['noGroupReason'] = 'Reviewed as broadly available.'
        with self.assertRaisesRegex(ScoutCurationError, 'catalog needs'):
            save_navigation(self.store, job['id'], proposal, reason='Empty catalog')
        proposal['noGroupCatalogReason'] = 'This fixture has only broad services.'
        save_navigation(self.store, job['id'], proposal, reason='Explicit catalog conclusion')
        from resource_research_agent.scout_review_readiness import require_review_ready
        with self.assertRaisesRegex(ScoutCurationError, 'different curation or navigation'):
            require_review_ready(self.store, self.store.get_scout_curation_job(job['id']))
        self.save_test_priorities(job['id'])
        self.assertEqual(0, require_review_ready(self.store, self.store.get_scout_curation_job(job['id']))['resourcesWithGroups'])

    def test_audit_revision_preserves_original_and_rejects_stale_or_incomplete_updates(self) -> None:
        job = prepare_scout_curation_job(self.store, self.import_id)
        assignment = next_scout_curation_assignment(self.store, job["id"])
        saved = save_scout_curation_result(self.store, job["id"], "employment",
                                          self.result_for(assignment, resource_id="work"))
        before = saved["categories"][0]
        corrected = json.loads(json.dumps(before["result"]))
        corrected["resources"][0]["description"] = "Corrected direct employment service."
        revised = revise_scout_curation_result(
            self.store, job["id"], "employment", corrected,
            expected_result_sha256=before["resultSha256"], reason="Provider source corrected scope",
            evidence=[{"url": "https://example.org/official"}],
        )
        after = revised["categories"][0]
        self.assertEqual(before["assignmentSha256"], after["assignmentSha256"])
        self.assertEqual(before["completedAt"], after["completedAt"])
        self.assertEqual(1, revised["progress"]["completed"])
        with self.store.connect() as connection:
            revision = connection.execute("SELECT * FROM scout_curation_result_revisions").fetchone()
            self.assertEqual(before["result"], json.loads(revision["previous_result_json"]))
            self.assertEqual(after["result"], json.loads(revision["result_json"]))
        with self.assertRaisesRegex(ScoutCurationError, "changed since"):
            revise_scout_curation_result(
                self.store, job["id"], "employment", corrected,
                expected_result_sha256=before["resultSha256"], reason="Stale edit",
                evidence=[{"url": "https://example.org/official"}],
            )
        corrected["candidateDispositions"] = []
        with self.assertRaisesRegex(ScoutCurationError, "missing candidate dispositions"):
            revise_scout_curation_result(
                self.store, job["id"], "employment", corrected,
                expected_result_sha256=after["resultSha256"], reason="Incomplete edit",
                evidence=[{"url": "https://example.org/official"}],
            )
        with self.store.connect() as connection:
            self.assertEqual(1, connection.execute("SELECT COUNT(*) FROM scout_curation_result_revisions").fetchone()[0])
        next_assignment = next_scout_curation_assignment(self.store, job["id"])
        self.assertEqual("Corrected direct employment service.", next_assignment["previouslyCuratedResources"][0]["description"])

    def test_review_can_remove_discovery_membership_without_losing_sole_resource(self) -> None:
        from copy import deepcopy
        from resource_research_agent.scout_curation import validate_scout_curation_result
        job = prepare_scout_curation_job(self.store, self.import_id)
        assignment = next_scout_curation_assignment(self.store, job["id"])
        worker_result = self.result_for(assignment, resource_id="sole-resource", categories=["food"])
        with self.assertRaisesRegex(ScoutCurationError, "missing category"):
            save_scout_curation_result(self.store, job["id"], "employment", worker_result)
        with self.assertRaisesRegex(ScoutCurationError, "completed job"):
            validate_scout_curation_result(self.store.get_scout_curation_job(job["id"]), "employment", worker_result,
                reviewed_category_removals={"sole-resource"})
        worker_result["resources"][0]["categories"] = ["employment", "food"]
        saved = save_scout_curation_result(self.store, job["id"], "employment", worker_result)
        before = saved["categories"][0]
        corrected = deepcopy(before["result"])
        corrected["resources"][0]["categories"] = ["food"]
        revision_args = dict(expected_result_sha256=before["resultSha256"],
            reason="Source establishes food assistance only; retain discovery provenance.",
            evidence=[{"source": "https://example.org/official"}],
            reviewed_category_removals={"sole-resource"})
        with self.assertRaisesRegex(ScoutCurationError, "completed job"):
            revise_scout_curation_result(self.store, job["id"], "employment", corrected, **revision_args)
        assignment = next_scout_curation_assignment(self.store, job["id"])
        completed = save_scout_curation_result(self.store, job["id"], "food",
            self.result_for(assignment, resource_id="other-food-resource"))
        old_fingerprint = review_fingerprint(completed)
        for field, value in [("description", "Changed fact"), ("candidateIds", []),
                             ("categories", []), ("categories", ["unknown"])]:
            invalid = deepcopy(corrected)
            invalid["resources"][0][field] = value
            with self.assertRaisesRegex(ScoutCurationError, "only remove that membership"):
                revise_scout_curation_result(self.store, job["id"], "employment", invalid, **revision_args)
        invalid = deepcopy(corrected)
        invalid["candidateDispositions"][0]["reason"] = "Changed disposition"
        with self.assertRaisesRegex(ScoutCurationError, "preserve candidate dispositions"):
            revise_scout_curation_result(self.store, job["id"], "employment", invalid, **revision_args)
        with self.assertRaisesRegex(ScoutCurationError, "existing resource"):
            revise_scout_curation_result(self.store, job["id"], "employment", corrected,
                **{**revision_args, "reviewed_category_removals": {"unrelated"}})
        with self.assertRaisesRegex(ScoutCurationError, "missing category"):
            revise_scout_curation_result(self.store, job["id"], "employment", corrected,
                **{k: v for k, v in revision_args.items() if k != "reviewed_category_removals"})
        revised = revise_scout_curation_result(self.store, job["id"], "employment", corrected, **revision_args)
        after = revised["categories"][0]
        self.assertNotEqual(old_fingerprint, review_fingerprint(revised))
        self.assertEqual(before["assignment"], after["assignment"])
        self.assertEqual(before["result"]["candidateDispositions"], after["result"]["candidateDispositions"])
        self.assertEqual(after["result"], validate_scout_curation_result(
            revised, "employment", after["result"], required_status="completed"))
        seed = build_scout_review_seed(self.store, job["id"])
        self.assertEqual(2, len(seed["resources"]))
        self.assertEqual(["food"], next(r for r in seed["resources"] if r["id"] == "sole-resource")["categories"])
        with self.store.connect() as connection:
            row = connection.execute("SELECT * FROM scout_curation_result_revisions").fetchone()
            self.assertEqual(before["result"], json.loads(row["previous_result_json"]))
            self.assertEqual(["sole-resource"], json.loads(row["evidence_json"])[-1]["resourceIds"])
        # A later fact correction must remain possible without restoring the rejected category.
        subsequent = deepcopy(after["result"])
        subsequent["resources"][0]["hours"] = "New verified hours"
        revise_scout_curation_result(self.store, job["id"], "employment", subsequent,
            expected_result_sha256=after["resultSha256"], reason="Updated hours",
            evidence=[{"source": "https://example.org/hours"}])

    def test_prepares_resumable_job_and_uses_most_complete_category_run(self) -> None:
        job = prepare_scout_curation_job(self.store, self.import_id)
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
        assignment = job["categories"][0]["assignment"]
        self.assertEqual(
            "codex-curation-v2-direct-service",
            assignment["assignmentVersion"],
        )
        self.assertIn(
            "smallest high-confidence set",
            assignment["curationPolicy"]["objective"],
        )
        self.assertIn(
            "barrier",
            assignment["curationPolicy"]["crossCategoryTest"],
        )
        self.assertTrue(any(
            "no target count" in instruction
            for instruction in assignment["instructions"]
        ))
        resumed = prepare_scout_curation_job(self.store, self.import_id)
        self.assertEqual(job["id"], resumed["id"])
        self.assertEqual(1, len(self.store.list_scout_curation_jobs(self.import_id)))

    def test_new_research_snapshot_creates_a_new_job_without_rewriting_the_old_one(self) -> None:
        original = prepare_scout_curation_job(self.store, self.import_id)
        newer_run = self.completed_run(
            "employment", "Employment", ["ChatGPT", "Claude", "Grok"]
        )
        refreshed = prepare_scout_curation_job(self.store, self.import_id)
        self.assertNotEqual(original["id"], refreshed["id"])
        self.assertNotEqual(
            original["candidatePackageSha256"], refreshed["candidatePackageSha256"]
        )
        self.assertEqual(newer_run, refreshed["categories"][0]["canonicalRunId"])
        preserved = self.store.get_scout_curation_job(original["id"])
        self.assertEqual(
            self.employment_run, preserved["categories"][0]["canonicalRunId"]
        )

    def test_migrates_short_lived_v041_curation_table_names(self) -> None:
        original = prepare_scout_curation_job(self.store, self.import_id)
        legacy_prefix = "auto" + "curator"
        with self.store.connect() as connection:
            connection.execute(
                f"ALTER TABLE scout_curation_jobs RENAME TO {legacy_prefix}_jobs"
            )
            connection.execute(
                "ALTER TABLE scout_curation_categories "
                f"RENAME TO {legacy_prefix}_categories"
            )
            connection.execute(
                "ALTER TABLE scout_curation_progress_events "
                f"RENAME TO {legacy_prefix}_progress_events"
            )

        migrated_store = ResearchStore(self.store.path)
        migrated = migrated_store.get_scout_curation_job(original["id"])
        self.assertIsNotNone(migrated)
        self.assertEqual(original["candidatePackageSha256"], migrated["candidatePackageSha256"])
        self.assertEqual(
            ["employment", "food"],
            [item["categoryId"] for item in migrated["categories"]],
        )
        with migrated_store.connect() as connection:
            tables = {
                str(row["name"])
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
        self.assertFalse(any(name.startswith(legacy_prefix) for name in tables))

    def test_curates_one_category_at_a_time_and_builds_all_category_seed(self) -> None:
        job = prepare_scout_curation_job(self.store, self.import_id)
        employment = next_scout_curation_assignment(self.store, job["id"])
        self.assertEqual("employment", employment["category"]["id"])
        self.assertEqual(employment["assignmentSha256"], assignment_digest(employment))
        employment_result = self.result_for(employment, resource_id="mesa-help")
        saved = save_scout_curation_result(
            self.store, job["id"], "employment", employment_result
        )
        self.assertEqual(1, saved["progress"]["completed"])

        food = next_scout_curation_assignment(self.store, job["id"])
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
        completed = save_scout_curation_result(
            self.store, job["id"], "food", food_result
        )
        self.assertEqual("completed", completed["status"])
        self.assertIsNone(next_scout_curation_assignment(self.store, job["id"]))

        seed = build_scout_review_seed(self.store, job["id"])
        self.assertEqual(["employment", "food"], [
            item["id"] for item in seed["categories"]
        ])
        self.assertEqual(1, len(seed["resources"]))
        self.assertEqual(["employment", "food"], seed["resources"][0]["categories"])
        self.assertNotIn("candidateIds", seed["resources"][0])
        self.assertEqual([], seed["deletions"])
        phases = [
            event["phase"] for event in self.store.list_scout_curation_progress(job["id"])
        ]
        self.assertEqual(1, phases.count("curation-completed"))

    def test_rejects_a_result_that_does_not_cover_the_assignment(self) -> None:
        job = prepare_scout_curation_job(self.store, self.import_id)
        assignment = next_scout_curation_assignment(self.store, job["id"])
        result = self.result_for(assignment, resource_id="mesa-help")
        result["candidateDispositions"].pop()
        with self.assertRaisesRegex(ScoutCurationError, "missing candidate dispositions"):
            save_scout_curation_result(
                self.store, job["id"], "employment", result
            )
        result = self.result_for(assignment, resource_id="mesa-help")
        result["assignmentSha256"] = "0" * 64
        with self.assertRaisesRegex(ScoutCurationError, "assigned curation snapshot"):
            save_scout_curation_result(
                self.store, job["id"], "employment", result
            )
        result = self.result_for(assignment, resource_id="mesa-help")
        result["resources"][0]["candidateIds"].pop()
        with self.assertRaisesRegex(ScoutCurationError, "missing contributing candidate IDs"):
            save_scout_curation_result(
                self.store, job["id"], "employment", result
            )

    def test_chatgpt_schedule_and_progress_reporting_policy(self) -> None:
        completed_at = datetime(2026, 8, 28, 18, 0, tzinfo=timezone.utc)
        schedule = schedule_chatgpt_assignment(
            completed_at,
            FixedRandom(8),
            adjustment_minutes=6,
            reason="Recent responses suggest lighter throttling is prudent.",
        )
        self.assertEqual(14, schedule.delay_minutes)
        self.assertEqual(completed_at + timedelta(minutes=14), schedule.scheduled_at)
        self.assertIn("wait 14 minutes", schedule.message)
        self.assertIn("lighter throttling", schedule.message)
        recent_send = schedule_chatgpt_assignment(
            completed_at,
            FixedRandom(8),
            previous_sent_at=completed_at - timedelta(minutes=4),
        )
        self.assertEqual(4, recent_send.delay_minutes)
        self.assertEqual(completed_at + timedelta(minutes=4), recent_send.scheduled_at)
        elapsed_send = schedule_chatgpt_assignment(
            completed_at,
            FixedRandom(10),
            previous_sent_at=completed_at - timedelta(minutes=18),
        )
        self.assertEqual(0, elapsed_send.delay_minutes)
        self.assertEqual(completed_at, elapsed_send.scheduled_at)
        reset_at = completed_at + timedelta(minutes=37, seconds=30)
        reset_schedule = schedule_chatgpt_assignment(
            completed_at,
            FixedRandom(5),
            explicit_reset_at=reset_at,
        )
        self.assertEqual(38, reset_schedule.delay_minutes)
        self.assertEqual(reset_at, reset_schedule.scheduled_at)
        self.assertIn("explicit reset time", reset_schedule.message)
        self.assertFalse(progress_heartbeat_due(completed_at, completed_at + timedelta(minutes=14)))
        self.assertTrue(progress_heartbeat_due(completed_at, completed_at + timedelta(minutes=15)))

    def test_curation_start_clears_an_old_chatgpt_schedule(self) -> None:
        self.store.record_scout_workflow_progress(
            self.import_id,
            "research",
            "All research is complete.",
            details={
                "nextChatgpt": {
                    "categoryId": "food",
                    "categoryLabel": "Food",
                    "delayMinutes": 15,
                    "scheduledAt": "2026-08-28T22:15:00+00:00",
                }
            },
        )
        prepare_scout_curation_job(self.store, self.import_id)
        progress = build_scout_progress(self.store, self.import_id)
        self.assertEqual("curation-start", progress["phase"])
        self.assertIsNone(progress["nextChatgpt"])

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
            job = post("/api/scout-curation-jobs", {"importId": self.import_id})
            assignment = post(
                f"/api/scout-curation-jobs/{job['id']}/next-assignment", {}
            )["assignment"]
            result = self.result_for(assignment, resource_id="mesa-help")
            saved = post(f"/api/scout-curation-jobs/{job['id']}/results", {
                "categoryId": "employment",
                "result": result,
            })
            self.assertEqual(1, saved["progress"]["completed"])
            event = post(f"/api/scout-curation-jobs/{job['id']}/progress", {
                "categoryId": "food",
                "phase": "curation-heartbeat",
                "message": "Food curation is still in progress.",
                "details": {"elapsedMinutes": 15},
            })
            self.assertEqual("curation-heartbeat", event["phase"])
            with urllib.request.urlopen(
                base + f"/api/scout-curation-jobs/{job['id']}/progress", timeout=5
            ) as response:
                events = json.loads(response.read())["events"]
            self.assertEqual("curation-heartbeat", events[-1]["phase"])
            with urllib.request.urlopen(
                base + f"/api/scout-curation-jobs?importId={self.import_id}", timeout=5
            ) as response:
                jobs = json.loads(response.read())["jobs"]
            self.assertEqual([job["id"]], [item["id"] for item in jobs])

            food = post(
                f"/api/scout-curation-jobs/{job['id']}/next-assignment", {}
            )["assignment"]
            post(f"/api/scout-curation-jobs/{job['id']}/results", {
                "categoryId": "food",
                "result": self.result_for(food, resource_id="mesa-food"),
            })
            with self.assertRaises(urllib.error.HTTPError) as blocked:
                urllib.request.urlopen(base + f"/api/scout-curation-jobs/{job['id']}/review-file", timeout=5)
            self.assertEqual(400, blocked.exception.code)
            self.complete_test_review(job["id"])
            with urllib.request.urlopen(
                base + f"/api/scout-curation-jobs/{job['id']}/review-file",
                timeout=5,
            ) as response:
                review_file = response.read()
                disposition = response.headers.get("Content-Disposition", "")
            self.assertIn('filename="autoMesa.html"', disposition)
            self.assertIn(b"AutoMesa TSO Resources", review_file)
            self.assertIn(b"Resource Scout", review_file)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    def test_resource_scout_builds_its_versioned_auto_office_review_file(self) -> None:
        job = prepare_scout_curation_job(self.store, self.import_id)
        employment = next_scout_curation_assignment(self.store, job["id"])
        employment_result = self.result_for(employment, resource_id="mesa-help")
        save_scout_curation_result(
            self.store, job["id"], "employment", employment_result
        )
        food = next_scout_curation_assignment(self.store, job["id"])
        old_candidate_ids = employment_result["resources"][0]["candidateIds"]
        food_candidate_ids = [str(item["id"]) for item in food["candidates"]]
        save_scout_curation_result(
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

        review_file = build_scout_review_file(self.store, job["id"])
        self.assertEqual("autoMesa.html", review_file.filename)
        self.assertEqual(__version__, review_file.scout_version)
        self.assertEqual(__build__, review_file.scout_build)
        self.assertIn(
            b'<meta name="tso-storage-id" content="scout-review-mesa">',
            review_file.content,
        )
        self.assertIn(
            b'<meta name="scout-review-location-name" content="Mesa">',
            review_file.content,
        )
        self.assertNotIn(b"Auto" + b"Curator", review_file.content)
        self.assertIn(
            b'<meta name="scout-review-curated-category-ids" content="employment,food">',
            review_file.content,
        )
        self.assertIn(
            b"Apply reviewed need Categories, Types, and comprehensive For groups",
            review_file.content,
        )
        artifact_match = re.search(
            rb'<meta name="scout-review-artifact-id" content="(scout-review-[0-9a-f]{24})">',
            review_file.content,
        )
        self.assertIsNotNone(artifact_match)
        repeated = build_scout_review_file(self.store, job["id"])
        self.assertIn(artifact_match.group(0), repeated.content)
        last_event = self.store.list_scout_curation_progress(job["id"])[-1]
        self.assertEqual("review-file-built", last_event["phase"])
        self.assertEqual(__build__, last_event["details"]["scoutBuild"])
        progress = build_scout_progress(self.store, self.import_id)
        self.assertEqual("awaiting-codex-review", progress["reviewFile"]["status"])
        self.complete_test_review(job["id"])
        progress = build_scout_progress(self.store, self.import_id)
        self.assertTrue(progress["reviewFile"]["readyForSave"])
        self.assertEqual("autoMesa.html", progress["targetReviewFilename"])
        self.assertEqual("autoMesa.html", progress["reviewFile"]["filename"])
        self.assertEqual(1, progress["reviewFile"]["resourceCount"])
        self.assertEqual(
            f"/api/scout-curation-jobs/{job['id']}/review-file",
            progress["reviewFile"]["downloadUrl"],
        )


if __name__ == "__main__":
    unittest.main()
