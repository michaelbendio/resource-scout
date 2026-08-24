from __future__ import annotations

import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

from resource_research_agent.importer import ResourcePackageImporter
from resource_research_agent.resource_package import (
    GeneratedResourceError,
    candidate_to_resource,
)
from resource_research_agent.review_export import build_review_copy
from resource_research_agent.server import ResearchHTTPServer
from resource_research_agent.storage import ResearchStore


class ResourceDraftAndRemovedScoutPathTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.store = ResearchStore(self.root / "research.sqlite3")
        package_path = self.root / "provo-resource-package.zip"
        package = {
            "resourcePackageSchemaVersion": 3,
            "packageVersion": 43,
            "categories": [
                {
                    "id": "housing",
                    "name": "Housing",
                    "filters": ["Shelter", "Rent help"],
                },
                {"id": "food", "name": "Food", "filters": ["Meals", "Pantries"]},
            ],
            "forGroups": ["Families with children", "Veterans"],
            "resources": [
                {
                    "id": "known-home",
                    "name": "Known Home",
                    "categories": ["housing"],
                }
            ],
        }
        with zipfile.ZipFile(package_path, "w") as archive:
            archive.writestr("tso-resources.json", json.dumps(package))
        self.import_id = self.store.save_import(
            ResourcePackageImporter().read(package_path)
        )
        self.run_id = self.store.create_research_run(
            "hermes",
            "Find Housing resources",
            {"selectedSeed": None},
            self.import_id,
            None,
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    @staticmethod
    def candidate(name: str = "New Resource") -> dict[str, object]:
        return {
            "name": name,
            "organization": "Helpful Organization",
            "program": "Direct Service",
            "phone": "801-555-0100",
            "address": "10 Center Street, Provo, UT",
            "website": "https://helpful.example.org/program",
            "hours": "Monday-Friday, 9-5",
            "serviceNeed": "Helps people meet an urgent need.",
            "description": "A longer researcher explanation.",
            "geography": "Utah County",
            "recommendedTypes": ["Shelter", "Not a package type"],
            "recommendedFor": ["Veterans", "Not a package For label"],
            "petPolicy": "Ask during intake.",
            "unknowns": ["Current appointment wait"],
            "evidence": [
                {
                    "title": "Official page",
                    "url": "https://helpful.example.org/program",
                    "finding": "Describes direct help.",
                    "sourceType": "official",
                    "reliability": "high",
                }
            ],
        }

    def test_curator_drafts_are_category_neutral_and_playbook_driven(self) -> None:
        candidate = self.candidate()
        housing = candidate_to_resource(
            candidate,
            "housing",
            resource_id="housing-draft",
            available_types=["Shelter"],
            available_for_groups=["Veterans"],
        )
        self.assertEqual("housing-draft", housing["id"])
        self.assertEqual(["housing"], housing["categories"])
        self.assertEqual({"housing": ["Shelter"]}, housing["categoryFilters"])
        self.assertEqual(["Veterans"], housing["forGroups"])
        self.assertIn("**Pet Policy**", housing["informationText"])
        self.assertIn("**Verify before referral**", housing["informationText"])

        food = candidate_to_resource(
            candidate,
            "food",
            resource_id="food-draft",
            available_types=["Meals"],
            available_for_groups=["Veterans"],
        )
        self.assertEqual(["food"], food["categories"])
        self.assertNotIn("Pet Policy", food["informationText"])
        with self.assertRaisesRegex(GeneratedResourceError, "needs a name"):
            candidate_to_resource({}, "food")

    def test_historical_generated_draft_remains_readable_in_curator_export(self) -> None:
        saved = self.store.save_discovery(
            self.candidate("Legacy edited draft"), run_id=self.run_id
        )
        legacy_resource = candidate_to_resource(
            self.candidate("Legacy edited draft"),
            "housing",
            resource_id="legacy-generated-id",
        )
        legacy_resource["phone"] = "801-555-0199"
        with self.store.connect() as connection:
            connection.execute(
                """INSERT INTO generated_resources (
                       discovery_id, run_id, source_import_id, resource_id,
                       created_at, updated_at, resource_json
                   ) VALUES (?, ?, ?, ?, 'legacy', 'legacy', ?)""",
                (
                    saved["id"],
                    self.run_id,
                    self.import_id,
                    legacy_resource["id"],
                    json.dumps(legacy_resource),
                ),
            )
        self.store.mark_run_running(self.run_id)
        self.store.complete_run(
            self.run_id,
            "raw",
            {"summary": "Complete", "candidates": [self.candidate()]},
            None,
        )
        review = build_review_copy(self.store, self.run_id)
        self.assertEqual(
            "legacy-generated-id", review.data["candidates"][0]["resourceDraft"]["id"]
        )
        self.assertEqual(
            "801-555-0199", review.data["candidates"][0]["resourceDraft"]["phone"]
        )

    def test_migration_recovers_source_package_for_older_package_backed_run(self) -> None:
        with self.store.connect() as connection:
            connection.execute(
                "UPDATE research_runs SET source_import_id = NULL WHERE id = ?",
                (self.run_id,),
            )
        reopened = ResearchStore(self.store.path)
        self.assertEqual(self.import_id, reopened.get_run(self.run_id)["sourceImportId"])

    def test_scout_http_does_not_expose_human_curation_or_package_routes(self) -> None:
        saved = self.store.save_discovery(self.candidate(), run_id=self.run_id)
        web_dir = Path(__file__).resolve().parent.parent / "web"
        server = ResearchHTTPServer(("127.0.0.1", 0), self.store, web_dir)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base = f"http://127.0.0.1:{server.server_address[1]}"
            for path, method, payload in (
                (
                    f"/api/discoveries/{saved['id']}/review",
                    "POST",
                    {"status": "accepted"},
                ),
                (
                    f"/api/discoveries/{saved['id']}/generated-resource",
                    "POST",
                    {"resource": {"name": "Edited"}},
                ),
                (
                    f"/api/discoveries/{saved['id']}/match-assessment",
                    "POST",
                    {"assessment": "same-resource"},
                ),
                (f"/api/research-runs/{self.run_id}/resource-package", "GET", None),
            ):
                request = urllib.request.Request(
                    f"{base}{path}",
                    data=(
                        json.dumps(payload).encode() if payload is not None else None
                    ),
                    headers=(
                        {"Content-Type": "application/json"}
                        if payload is not None
                        else {}
                    ),
                    method=method,
                )
                with self.assertRaises(urllib.error.HTTPError) as raised:
                    urllib.request.urlopen(request, timeout=5)
                self.assertEqual(404, raised.exception.code)
                raised.exception.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
