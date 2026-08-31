from __future__ import annotations

import json
import tempfile
import threading
import unittest
import urllib.request
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from resource_research_agent.codex_first_research import (
    codex_first_view,
    next_codex_first_assignment,
    prepare_codex_first_plan,
    save_codex_first_external_result,
    save_codex_first_primary_result,
)
from resource_research_agent.importer import ResourcePackageImporter
from resource_research_agent.scout_curation import ScoutCurationError, prepare_scout_curation_job
from resource_research_agent.storage import ResearchStore
from resource_research_agent.playbooks import PLAYBOOKS
from resource_research_agent.scout_progress import build_scout_progress
from resource_research_agent.server import ResearchHTTPServer


class FixedRandom:
    def __init__(self, value: int) -> None:
        self.value = value

    def randint(self, lower: int, upper: int) -> int:
        if not lower <= self.value <= upper:
            raise AssertionError("Fixed random value is outside the requested range")
        return self.value


def response(name: str) -> str:
    return json.dumps({"leads": [{
        "organization": name,
        "program": f"{name} Program",
        "website": f"https://{name.casefold().replace(' ', '-')}.example.org",
        "phone": "801-555-0100",
        "address": "100 Main Street, Provo, UT",
        "leadType": "program",
        "locationOrServiceArea": "Utah County, Utah",
        "whyRelevant": "Provides direct food assistance.",
        "uncertainty": "Confirm current intake.",
    }]})


class CodexFirstResearchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        package = root / "provo-resource-package.zip"
        with zipfile.ZipFile(package, "w") as archive:
            archive.writestr("tso-resources.json", json.dumps({
                "resourcePackageSchemaVersion": 3,
                "packageVersion": 1,
                "officeName": "Provo TSO",
                "serviceArea": "Utah County, Utah",
                "categories": [
                    {"id": "food", "name": "Food", "filters": []},
                    {"id": "miscellaneous", "name": "Miscellaneous", "filters": []},
                ],
                "forGroups": [],
                "resources": [],
            }))
        self.store = ResearchStore(root / "research.sqlite3")
        self.import_id = self.store.save_import(ResourcePackageImporter(None).read(package))

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_whole_office_plan_is_durable_and_excludes_miscellaneous(self) -> None:
        plan = prepare_codex_first_plan(self.store, self.import_id)
        repeated = prepare_codex_first_plan(self.store, self.import_id)
        self.assertEqual(1, plan["totalCategories"])
        self.assertEqual(["food"], [item["categoryId"] for item in plan["categories"]])
        self.assertEqual(
            [item["jobId"] for item in plan["categories"]],
            [item["jobId"] for item in repeated["categories"]],
        )
        job = self.store.get_focused_research_job(plan["categories"][0]["jobId"])
        self.assertEqual("researcher-roster-v1", job["plan"]["researcherRoster"]["version"])
        with self.assertRaisesRegex(ScoutCurationError, "Codex-first research plan"):
            prepare_scout_curation_job(self.store, self.import_id)
        progress = build_scout_progress(self.store, self.import_id)
        self.assertEqual("codex-first-research", progress["phase"])
        self.assertEqual({"completed": 0, "total": 1}, progress["research"])
        self.assertIsNone(progress["reviewFile"])
        self.assertEqual(0, progress["curation"]["completed"])

    def test_challengers_shadow_disabled_and_chatgpt_pacing(self) -> None:
        roster = {
            "schemaVersion": 1,
            "version": "test-roster-v1",
            "researchers": [
                {"name": "Codex", "role": "primary"},
                {"name": "ChatGPT", "role": "challenger"},
                {"name": "Grok", "role": "challenger"},
                {"name": "Claude", "role": "shadow"},
                {"name": "Perplexity", "role": "disabled"},
            ],
        }
        plan = prepare_codex_first_plan(self.store, self.import_id, roster=roster)
        job_id = plan["categories"][0]["jobId"]
        index = 0
        while True:
            assignment = next_codex_first_assignment(
                self.store, self.import_id, "Codex",
                random_source=FixedRandom(7),
                now=datetime(2026, 8, 31, 18, 0, tzinfo=timezone.utc),
            )
            if assignment is None:
                break
            research_pass = assignment["researchPass"]
            save_codex_first_primary_result(
                self.store, job_id, research_pass["focusKey"], response(f"Codex Food {index}")
            )
            index += 1

        assignments = self.store.list_codex_first_assignments(job_id)
        self.assertEqual(
            {"ChatGPT", "Grok", "Claude"},
            {item["researcher"] for item in assignments},
        )
        self.assertNotIn("Perplexity", {item["researcher"] for item in assignments})
        chatgpt = next(item for item in assignments if item["researcher"] == "ChatGPT")
        schedule = self.store.get_chatgpt_assignment_schedule(chatgpt["chatgptScheduleId"])
        self.assertEqual(7, schedule["delayMinutes"])
        self.assertEqual("Random 5-10 minute research interval.", schedule["reason"])
        self.assertIsNone(next_codex_first_assignment(
            ResearchStore(self.store.path), self.import_id, "Codex",
            random_source=FixedRandom(9),
            now=datetime(2026, 8, 31, 18, 1, tzinfo=timezone.utc),
        ))
        self.assertEqual(
            schedule["id"],
            self.store.latest_chatgpt_assignment_schedule(self.import_id)["id"],
        )

        with self.assertRaisesRegex(ValueError, "Mark the ChatGPT assignment sent"):
            save_codex_first_external_result(self.store, chatgpt["id"], response("ChatGPT Food"))
        due_time = datetime.fromisoformat(schedule["scheduledAt"])
        self.store.mark_chatgpt_assignment_sent(chatgpt["chatgptScheduleId"], sent_at=due_time)
        save_codex_first_external_result(self.store, chatgpt["id"], response("ChatGPT Food"))
        grok = next(item for item in assignments if item["researcher"] == "Grok")
        save_codex_first_external_result(self.store, grok["id"], response("Grok Food"))

        completed = codex_first_view(self.store, self.import_id)
        self.assertEqual("completed", completed["status"])
        self.assertEqual(1, completed["completedCategories"])
        job = self.store.get_focused_research_job(job_id)
        self.assertEqual(index + 2, job["evaluation"]["submittedLeadCount"])
        self.assertEqual(index + 2, job["evaluation"]["sourceResponseCount"])

        claude = next(item for item in assignments if item["researcher"] == "Claude")
        save_codex_first_external_result(self.store, claude["id"], response("Claude Food"))
        self.assertEqual(
            index + 2,
            self.store.manual_discovery_progress(job["runId"])["leadCount"],
        )

    def test_whole_office_codex_only_cycle_completes_without_chatgpt_pacing(self) -> None:
        root = Path(self.temporary.name)
        package = root / "whole-office-resource-package.zip"
        with zipfile.ZipFile(package, "w") as archive:
            archive.writestr("tso-resources.json", json.dumps({
                "resourcePackageSchemaVersion": 3,
                "packageVersion": 1,
                "officeName": "Test TSO",
                "serviceArea": "Test County",
                "categories": [
                    {"id": category_id, "name": playbook.label, "filters": []}
                    for category_id, playbook in PLAYBOOKS.items()
                ] + [{"id": "miscellaneous", "name": "Miscellaneous", "filters": []}],
                "forGroups": [],
                "resources": [],
            }))
        import_id = self.store.save_import(ResourcePackageImporter(None).read(package))
        roster = {
            "schemaVersion": 1,
            "version": "codex-only-test-v1",
            "researchers": [
                {"name": "Codex", "role": "primary"},
                {"name": "ChatGPT", "role": "disabled"},
                {"name": "Grok", "role": "disabled"},
                {"name": "Claude", "role": "disabled"},
                {"name": "Perplexity", "role": "disabled"},
            ],
        }
        plan = prepare_codex_first_plan(self.store, import_id, roster=roster)
        self.assertEqual(20, plan["totalCategories"])
        result_index = 0
        while codex_first_view(self.store, import_id)["status"] != "completed":
            assignment = next_codex_first_assignment(
                self.store, import_id, "Codex", random_source=FixedRandom(5)
            )
            if assignment is None:
                continue
            research_pass = assignment["researchPass"]
            save_codex_first_primary_result(
                self.store,
                assignment["job"]["id"],
                research_pass["focusKey"],
                response(f"Whole Office {result_index}"),
            )
            result_index += 1
        completed = codex_first_view(self.store, import_id)
        self.assertEqual(20, completed["completedCategories"])
        self.assertEqual([], self.store.due_chatgpt_assignment_schedules(import_id))
        self.assertIsNotNone(prepare_scout_curation_job(self.store, import_id))

    def test_http_contract_prepares_and_resumes_primary_work(self) -> None:
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
            prepared = request("/api/codex-first-research", "POST", {
                "importId": self.import_id,
            })
            self.assertEqual(1, prepared["totalCategories"])
            assigned = request("/api/codex-first-research/next-assignment", "POST", {
                "importId": self.import_id,
                "researcher": "Codex",
            })["assignment"]
            self.assertEqual("primary", assigned["kind"])
            resumed = request("/api/codex-first-research/next-assignment", "POST", {
                "importId": self.import_id,
                "researcher": "Codex",
            })["assignment"]
            self.assertEqual(
                assigned["researchPass"]["assignmentSha256"],
                resumed["researchPass"]["assignmentSha256"],
            )
            view = request(f"/api/codex-first-research?importId={self.import_id}")
            self.assertEqual("food", view["activeCategory"]["categoryId"])
            progress = request(f"/api/scout-progress?importId={self.import_id}")
            self.assertEqual("codex-first-research", progress["phase"])
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
