from __future__ import annotations

import json
import tempfile
import threading
import unittest
import urllib.request
import zipfile
from pathlib import Path

from resource_research_agent.focused_research import (
    build_candidate_manifest,
    evaluate_focused_research_job,
    next_focused_research_assignment,
    prepare_focused_gap_pass,
    prepare_focused_research_job,
    save_focused_research_result,
)
from resource_research_agent.importer import ResourcePackageImporter
from resource_research_agent.storage import ResearchStore
from resource_research_agent.server import ResearchHTTPServer


def response_for(organization: str, program: str, website: str) -> str:
    return json.dumps({"leads": [{
        "organization": organization,
        "program": program,
        "website": website,
        "phone": "480-555-0100",
        "address": "100 Main Street, Mesa, AZ",
        "leadType": "program",
        "locationOrServiceArea": "Mesa and Maricopa County, Arizona",
        "whyRelevant": "Provides direct employment help.",
        "uncertainty": "Confirm current intake.",
    }]})


class FocusedResearchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.database = self.root / "research.sqlite3"
        package_path = self.root / "mesa-resource-package.zip"
        with zipfile.ZipFile(package_path, "w") as archive:
            archive.writestr("tso-resources.json", json.dumps({
                "resourcePackageSchemaVersion": 3,
                "packageVersion": 2,
                "officeName": "Mesa TSO",
                "serviceArea": "Mesa and Maricopa County, Arizona",
                "categories": [
                    {"id": "employment", "name": "Employment", "filters": []},
                    {"id": "miscellaneous", "name": "Miscellaneous", "filters": []},
                ],
                "forGroups": [],
                "resources": [{
                    "id": "known-workforce",
                    "name": "Known Workforce Center",
                    "description": "Known program",
                    "website": "https://known.example.org",
                    "categories": ["employment"],
                    "categoryFilters": {},
                    "forGroups": [],
                    "informationText": "",
                }, {
                    "id": "hidden-recovery-target",
                    "name": "Arouet Foundation Employment Readiness",
                    "description": "Must not leak into the retrospective assignment",
                    "website": "https://arouetfoundation.org/",
                    "categories": ["employment"],
                    "categoryFilters": {},
                    "forGroups": [],
                    "informationText": "",
                }],
            }))
        self.store = ResearchStore(self.database)
        self.import_id = self.store.save_import(
            ResourcePackageImporter("employment").read(package_path)
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_prepares_resumable_job_and_redacts_recovery_targets(self) -> None:
        job = prepare_focused_research_job(self.store, self.import_id)
        resumed = prepare_focused_research_job(self.store, self.import_id)
        self.assertEqual(job["id"], resumed["id"])
        self.assertEqual("employment-focused-v2", job["playbookVersion"])
        self.assertEqual(7, len(job["passes"]))
        self.assertEqual("pending", job["status"])

        research_pass = next_focused_research_assignment(self.store, job["id"])
        self.assertEqual("public-workforce", research_pass["focusKey"])
        self.assertEqual("assigned", research_pass["status"])
        self.assertIn("Known Workforce Center", research_pass["assignment"])
        self.assertNotIn("Arouet", research_pass["assignment"])
        self.assertNotIn("arouetfoundation.org", research_pass["assignment"])
        same = next_focused_research_assignment(self.store, job["id"])
        self.assertEqual(research_pass["assignmentSha256"], same["assignmentSha256"])

    def test_result_is_idempotent_and_next_pass_sees_prior_candidate(self) -> None:
        job = prepare_focused_research_job(self.store, self.import_id)
        first = next_focused_research_assignment(self.store, job["id"])
        raw = response_for(
            "Mesa Skills Collaborative", "Public Workforce Navigation",
            "https://skills.example.org/workforce",
        )
        completed = save_focused_research_result(
            self.store, job["id"], first["focusKey"], raw
        )
        repeated = save_focused_research_result(
            self.store, job["id"], first["focusKey"], raw
        )
        self.assertEqual(completed["contributionId"], repeated["contributionId"])
        self.assertEqual(1, completed["leadCount"])
        self.assertEqual(1, len(build_candidate_manifest(self.store, job["runId"])))

        second = next_focused_research_assignment(self.store, job["id"])
        self.assertEqual("immediate-employment", second["focusKey"])
        self.assertIn("Mesa Skills Collaborative", second["assignment"])
        self.assertEqual(1, len(self.store.list_manual_contributions(job["runId"])))

    def test_reopen_preserves_assigned_pass(self) -> None:
        job = prepare_focused_research_job(self.store, self.import_id)
        assigned = next_focused_research_assignment(self.store, job["id"])
        reopened = ResearchStore(self.database)
        resumed = next_focused_research_assignment(reopened, job["id"])
        self.assertEqual(assigned["id"], resumed["id"])
        self.assertEqual(assigned["assignment"], resumed["assignment"])

    def test_gap_pass_requires_fixed_pass_completion(self) -> None:
        job = prepare_focused_research_job(self.store, self.import_id)
        with self.assertRaisesRegex(ValueError, "Complete every fixed focus"):
            self.store.add_focused_gap_pass(job["id"], {"key": "gap"})

    def test_gap_pass_uses_completed_pass_counts_and_preserves_focus_provenance(self) -> None:
        job = prepare_focused_research_job(self.store, self.import_id)
        for ordinal in range(7):
            research_pass = next_focused_research_assignment(self.store, job["id"])
            raw = response_for(
                f"Mesa Employment Provider {ordinal}",
                f"Employment Program {ordinal}",
                f"https://provider-{ordinal}.example.org/employment",
            )
            save_focused_research_result(
                self.store, job["id"], research_pass["focusKey"], raw
            )

        gap = prepare_focused_gap_pass(self.store, job["id"])
        repeated = prepare_focused_gap_pass(self.store, job["id"])
        self.assertEqual(gap["id"], repeated["id"])
        self.assertEqual("gap", gap["passKind"])
        self.assertEqual(7, len(gap["definition"]["gapAnalysis"]["lowYieldFocusLabels"]))
        assigned = next_focused_research_assignment(self.store, job["id"])
        self.assertEqual("gap", assigned["focusKey"])
        self.assertIn("lowest-yield", assigned["assignment"])

        from resource_research_agent.manual_consolidation import consolidate_manual_discovery

        snapshot = consolidate_manual_discovery(self.store, job["runId"])
        members = [
            member for group in snapshot["groups"] for member in group["members"]
        ]
        self.assertEqual(7, len(members))
        self.assertTrue(all(member["researchFocusKey"] for member in members))
        self.assertTrue(all(member["researchPassKind"] == "focus" for member in members))

    def test_http_contract_and_scout_progress_expose_active_focus(self) -> None:
        web_dir = Path(__file__).resolve().parent.parent / "web"
        server = ResearchHTTPServer(("127.0.0.1", 0), self.store, web_dir)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_address[1]}"

        def request(path: str, method: str = "GET", payload: dict | None = None) -> dict:
            data = json.dumps(payload).encode("utf-8") if payload is not None else None
            req = urllib.request.Request(
                base + path,
                data=data,
                headers={"Content-Type": "application/json"} if data else {},
                method=method,
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                return json.loads(response.read())

        try:
            job = request("/api/focused-research-jobs", "POST", {
                "importId": self.import_id,
                "categoryId": "employment",
            })
            assigned = request(
                f"/api/focused-research-jobs/{job['id']}/next-assignment",
                "POST",
                {},
            )["assignment"]
            self.assertEqual("public-workforce", assigned["focusKey"])
            progress = request(f"/api/scout-progress?importId={self.import_id}")
            self.assertEqual("focused-research", progress["phase"])
            self.assertEqual("Public workforce infrastructure", progress["focusedResearch"]["activeFocus"])
            self.assertEqual(0, progress["focusedResearch"]["completed"])

            result = request(
                f"/api/focused-research-jobs/{job['id']}/results",
                "POST",
                {
                    "focusKey": assigned["focusKey"],
                    "rawText": response_for(
                        "Mesa Public Workforce", "Employment Navigation",
                        "https://public-workforce.example.org",
                    ),
                },
            )
            self.assertEqual("completed", result["status"])
            listed = request(
                f"/api/focused-research-jobs?importId={self.import_id}"
            )["jobs"]
            self.assertEqual([job["id"]], [item["id"] for item in listed])
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    def test_evaluation_unseals_targets_only_after_gap_is_complete(self) -> None:
        job = prepare_focused_research_job(self.store, self.import_id)
        self.assertNotIn("mesa-arouet", json.dumps(job).casefold())
        for ordinal in range(7):
            research_pass = next_focused_research_assignment(self.store, job["id"])
            if ordinal == 0:
                raw = response_for(
                    "Arouet Foundation", "Employment Readiness and Reentry Support",
                    "https://arouetfoundation.org/",
                )
            else:
                raw = response_for(
                    f"Mesa Provider {ordinal}", f"Program {ordinal}",
                    f"https://mesa-provider-{ordinal}.example.org",
                )
            save_focused_research_result(
                self.store, job["id"], research_pass["focusKey"], raw
            )
        prepare_focused_gap_pass(self.store, job["id"])
        gap = next_focused_research_assignment(self.store, job["id"])
        save_focused_research_result(
            self.store, job["id"], gap["focusKey"], '{"leads":[]}'
        )

        completed = evaluate_focused_research_job(self.store, job["id"])
        self.assertEqual("completed", completed["status"])
        evaluation = completed["evaluation"]
        self.assertEqual(6, evaluation["locationPrimaryTargetCount"])
        self.assertEqual(1, evaluation["locationPrimaryRecoveredCount"])
        arouet = next(
            item for item in evaluation["outcomes"]
            if item["targetKey"] == "mesa-arouet-employment-reentry"
        )
        self.assertEqual("exact", arouet["outcome"])
        self.assertIn("same normalized official URL", arouet["match"]["evidence"])
        repeated = evaluate_focused_research_job(self.store, job["id"])
        self.assertEqual(completed["evaluationSha256"], repeated["evaluationSha256"])


if __name__ == "__main__":
    unittest.main()
