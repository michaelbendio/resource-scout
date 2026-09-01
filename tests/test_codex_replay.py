from __future__ import annotations

import json
import tempfile
import threading
import unittest
import urllib.request
import zipfile
from pathlib import Path

from resource_research_agent.codex_first_research import (
    next_codex_first_assignment,
    prepare_codex_first_plan,
    save_codex_first_external_result,
    save_codex_first_primary_result,
)
from resource_research_agent.codex_replay import (
    codex_replay_view,
    next_codex_replay_assignment,
    prepare_codex_replay_study,
    reveal_and_complete_codex_replay,
    save_codex_replay_result,
)
from resource_research_agent.importer import ResourcePackageImporter
from resource_research_agent.server import ResearchHTTPServer
from resource_research_agent.storage import ResearchStore


def response(organization: str, program: str, website: str) -> str:
    return json.dumps({"leads": [{
        "organization": organization,
        "program": program,
        "website": website,
        "phone": "480-555-0100",
        "address": "100 Main Street, Mesa, AZ",
        "leadType": "program",
        "locationOrServiceArea": "Mesa and Maricopa County, Arizona",
        "whyRelevant": "A community program provides direct food and benefits navigation.",
        "uncertainty": "Confirm eligibility, intake, availability, and current funding.",
    }]})


class CodexReplayTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        package = root / "mesa-resource-package.zip"
        with zipfile.ZipFile(package, "w") as archive:
            archive.writestr("tso-resources.json", json.dumps({
                "resourcePackageSchemaVersion": 3,
                "packageVersion": 2,
                "officeName": "Mesa TSO",
                "serviceArea": "Mesa and Maricopa County, Arizona",
                "categories": [
                    {"id": "food", "name": "Food", "filters": ["Pantry", "Meals"]},
                    {"id": "miscellaneous", "name": "Miscellaneous", "filters": []},
                ],
                "forGroups": ["Families with children"],
                "resources": [{
                    "id": "known-food",
                    "name": "Known Food Provider",
                    "description": "Known program",
                    "website": "https://known.example.org/food",
                    "categories": ["food"],
                    "categoryFilters": {"food": ["Pantry"]},
                    "forGroups": [],
                    "informationText": "",
                }],
            }))
        self.store = ResearchStore(root / "research.sqlite3")
        self.import_id = self.store.save_import(
            ResourcePackageImporter(None).read(package)
        )
        roster = {
            "schemaVersion": 1,
            "version": "replay-test-roster-v1",
            "researchers": [
                {"name": "Codex", "role": "primary"},
                {"name": "Provider Alpha", "role": "challenger"},
                {"name": "Provider Beta", "role": "challenger"},
                {"name": "Provider Gamma", "role": "challenger"},
                {"name": "Provider Delta", "role": "shadow"},
            ],
        }
        plan = prepare_codex_first_plan(self.store, self.import_id, roster=roster)
        self.v1_job_id = int(plan["categories"][0]["jobId"])
        index = 0
        while True:
            assignment = next_codex_first_assignment(
                self.store, self.import_id, "Codex"
            )
            if assignment and assignment["researchPass"]:
                research_pass = assignment["researchPass"]
                save_codex_first_primary_result(
                    self.store,
                    self.v1_job_id,
                    research_pass["focusKey"],
                    response(
                        "V1 Food Network",
                        f"V1 Food Program {index}",
                        f"https://v1-{index}.example.org/food",
                    ),
                )
                index += 1
                continue
            break
        assignments = self.store.list_codex_first_assignments(self.v1_job_id)
        for assignment in assignments:
            if assignment["role"] != "challenger":
                continue
            save_codex_first_external_result(
                self.store,
                int(assignment["id"]),
                response(
                    "Hidden Food Network",
                    f"Mobile Pantry {assignment['researcher']}",
                    "https://hidden.example.org/mobile-pantry",
                ),
            )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_study_seals_identity_holdouts_and_builds_exact_v2_proposal(self) -> None:
        study = prepare_codex_replay_study(self.store, self.import_id)
        repeated = prepare_codex_replay_study(self.store, self.import_id)
        self.assertEqual(study["id"], repeated["id"])
        self.assertEqual("sealed", study["status"])
        self.assertFalse(study["holdoutsRevealed"])
        self.assertIsNone(study["categories"][0]["v1Snapshot"])
        self.assertIsNone(study["categories"][0]["sealedHoldout"])
        self.assertNotIn("Hidden Food Network", json.dumps(study))
        self.assertNotIn("hidden.example.org", json.dumps(study))
        serialized_lessons = json.dumps(study["categories"][0]["lessonEvidence"])
        self.assertNotIn("Hidden Food Network", serialized_lessons)
        self.assertNotIn("hidden.example.org", serialized_lessons)
        self.assertEqual(
            "codex-first-v2-proposal",
            study["categories"][0]["v2Plan"]["playbookLibraryVersion"],
        )
        self.assertEqual(
            study["packageFixtureSha256"], repeated["packageFixtureSha256"]
        )

    def test_fresh_v2_work_cannot_see_holdout_then_reveals_comparison(self) -> None:
        study = prepare_codex_replay_study(self.store, self.import_id)
        study_id = int(study["id"])
        index = 0
        while True:
            assignment = next_codex_replay_assignment(self.store, study_id)
            if assignment is None:
                break
            text = assignment["researchPass"]["assignment"]
            if index == 0:
                self.assertNotIn("Hidden Food Network", text)
                self.assertNotIn("hidden.example.org", text)
            else:
                self.assertIn("hidden.example.org", text)
            raw = (
                response(
                    "Hidden Food Network",
                    "Mobile Pantry Provider Alpha",
                    "https://hidden.example.org/mobile-pantry",
                )
                if index == 0
                else response(
                    "V1 Food Network",
                    "V1 Food Program 0",
                    "https://v1-0.example.org/food",
                )
            )
            save_codex_replay_result(
                self.store,
                study_id,
                int(assignment["jobId"]),
                str(assignment["researchPass"]["focusKey"]),
                raw,
            )
            index += 1
        closed = codex_replay_view(self.store, study_id)
        self.assertEqual("codex-closed", closed["status"])
        self.assertFalse(closed["holdoutsRevealed"])
        completed = reveal_and_complete_codex_replay(self.store, study_id)
        self.assertEqual("completed", completed["status"])
        self.assertTrue(completed["holdoutsRevealed"])
        self.assertIsNotNone(completed["categories"][0]["v1Snapshot"])
        metrics = completed["categories"][0]["metrics"]
        self.assertGreaterEqual(metrics["recovery"]["v2RecoveredCount"], 1)
        self.assertGreaterEqual(metrics["retention"]["retainedByV2Count"], 1)
        self.assertIn("v1Plan", metrics["beforeAfter"])
        self.assertIn("v2Plan", metrics["beforeAfter"])
        self.assertEqual(
            "proposal-only; no active playbook was changed",
            completed["report"]["activationDecision"],
        )

    def test_http_contract_hides_evidence_and_resumes_assignment(self) -> None:
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
            with urllib.request.urlopen(req, timeout=5) as response_value:
                return json.loads(response_value.read())

        try:
            prepared = request("/api/codex-replays", "POST", {
                "importId": self.import_id,
            })
            study_id = int(prepared["id"])
            self.assertIsNone(prepared["categories"][0]["v1Snapshot"])
            self.assertIsNone(prepared["categories"][0]["sealedHoldout"])
            assigned = request(
                f"/api/codex-replays/{study_id}/next-assignment", "POST", {}
            )["assignment"]
            resumed = request(
                f"/api/codex-replays/{study_id}/next-assignment", "POST", {}
            )["assignment"]
            self.assertEqual(
                assigned["researchPass"]["assignmentSha256"],
                resumed["researchPass"]["assignmentSha256"],
            )
            view = request(f"/api/codex-replays/{study_id}")
            self.assertEqual("running", view["status"])
            self.assertIsNone(view["categories"][0]["v1Snapshot"])
            self.assertIsNone(view["categories"][0]["sealedHoldout"])
            listed = request(f"/api/codex-replays?importId={self.import_id}")
            self.assertEqual(study_id, listed["studies"][0]["id"])
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
