from __future__ import annotations

import json
import tempfile
import threading
import unittest
import urllib.request
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from resource_research_agent.importer import ResourcePackageImporter
from resource_research_agent.server import ResearchHTTPServer
from resource_research_agent.storage import ResearchStore


class ChatGPTAssignmentScheduleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.database = self.root / "research.sqlite3"
        self.store = ResearchStore(self.database)
        package_path = self.root / "provo-resource-package.zip"
        with zipfile.ZipFile(package_path, "w") as archive:
            archive.writestr("tso-resources.json", json.dumps({
                "resourcePackageSchemaVersion": 3,
                "packageVersion": 1,
                "officeName": "Provo TSO",
                "serviceArea": "Utah County, Utah",
                "categories": [
                    {"id": "housing", "name": "Housing", "filters": []},
                ],
                "resources": [],
            }))
        self.import_id = self.store.save_import(
            ResourcePackageImporter(None).read(package_path)
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_schedule_becomes_due_after_restart_without_a_new_delay(self) -> None:
        started = datetime(2026, 8, 29, 16, 0, tzinfo=timezone.utc)
        schedule = self.store.create_chatgpt_assignment_schedule(
            self.import_id,
            "housing",
            "Housing",
            "Research Housing",
            15,
            started + timedelta(minutes=15),
            reason="Random 5-10 minute research interval.",
            now=started,
        )
        self.assertEqual("scheduled", schedule["status"])

        restarted_store = ResearchStore(self.database)
        due = restarted_store.due_chatgpt_assignment_schedules(
            self.import_id,
            now=started + timedelta(hours=2),
        )
        self.assertEqual([schedule["id"]], [item["id"] for item in due])
        self.assertEqual("due", due[0]["status"])
        self.assertEqual(
            (started + timedelta(minutes=15)).isoformat(),
            due[0]["scheduledAt"],
        )

    def test_due_assignment_can_cool_down_and_then_be_sent(self) -> None:
        started = datetime(2026, 8, 29, 16, 0, tzinfo=timezone.utc)
        schedule = self.store.create_chatgpt_assignment_schedule(
            self.import_id,
            "housing",
            "Housing",
            "Research Housing",
            0,
            started,
            now=started,
        )
        self.assertEqual("due", schedule["status"])

        retry_at = started + timedelta(minutes=30)
        cooling = self.store.cool_down_chatgpt_assignment(
            schedule["id"],
            retry_at,
            note="Indirect throttle signal.",
            now=started,
        )
        self.assertEqual("cooling-down", cooling["status"])
        self.assertEqual(retry_at.isoformat(), cooling["cooldownUntil"])
        self.assertEqual(
            [],
            self.store.due_chatgpt_assignment_schedules(
                self.import_id, now=started + timedelta(minutes=29)
            ),
        )

        due = self.store.due_chatgpt_assignment_schedules(
            self.import_id, now=retry_at
        )
        self.assertEqual("due", due[0]["status"])
        sent = self.store.mark_chatgpt_assignment_sent(
            schedule["id"], sent_at=retry_at
        )
        self.assertEqual("sent", sent["status"])
        self.assertEqual(retry_at.isoformat(), sent["sentAt"])

    def test_http_due_and_sent_contract(self) -> None:
        web_dir = Path(__file__).resolve().parent.parent / "web"
        server = ResearchHTTPServer(("127.0.0.1", 0), self.store, web_dir)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_address[1]}"

        def post(path: str, value: dict) -> tuple[int, dict]:
            request = urllib.request.Request(
                base + path,
                data=json.dumps(value).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=5) as response:
                return response.status, json.loads(response.read())

        try:
            status, created = post("/api/chatgpt-assignments", {
                "importId": self.import_id,
                "categoryId": "housing",
                "categoryLabel": "Housing",
                "assignment": "Research Housing",
                "delayMinutes": 0,
                "scheduledAt": "2026-08-29T16:00:00+00:00",
            })
            self.assertEqual(201, status)
            self.assertEqual("due", created["assignment"]["status"])
            schedule_id = created["assignment"]["id"]

            with urllib.request.urlopen(
                base + f"/api/chatgpt-assignments/due?importId={self.import_id}",
                timeout=5,
            ) as response:
                due = json.loads(response.read())
            self.assertEqual([schedule_id], [item["id"] for item in due["assignments"]])
            self.assertEqual("Research Housing", due["assignments"][0]["assignment"])

            status, sent = post(
                f"/api/chatgpt-assignments/{schedule_id}/sent",
                {"message": "ChatGPT received Housing."},
            )
            self.assertEqual(200, status)
            self.assertEqual("sent", sent["assignment"]["status"])
            self.assertEqual("sent", sent["progress"]["chatgptAssignment"]["status"])
            self.assertIsNone(sent["progress"]["nextChatgpt"])
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
