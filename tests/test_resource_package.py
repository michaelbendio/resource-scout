from __future__ import annotations

import io
import json
import tempfile
import threading
import unittest
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from resource_research_agent.importer import ResourcePackageImporter
from resource_research_agent.resource_package import (
    AcceptedResourceManager,
    GeneratedResourceError,
)
from resource_research_agent.server import ResearchHTTPServer
from resource_research_agent.storage import ResearchStore


class AcceptedResourcePackageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.store = ResearchStore(self.root / "research.sqlite3")
        self.package_path = self.root / "provo-resource-package.zip"
        package = {
            "resourcePackageSchemaVersion": 3,
            "packageVersion": 43,
            "categories": [
                {"id": "housing", "name": "Housing", "filters": ["Shelter", "Rent help"]},
                {"id": "food", "name": "Food", "filters": ["Meals", "Pantries"]},
            ],
            "forGroups": ["Families with children", "Veterans"],
            "resources": [{
                "id": "known-home",
                "name": "Known Home",
                "categories": ["housing"],
                "pdfs": [{"filename": "known-home-guide.pdf"}],
                "privateExtension": "must remain in the imported snapshot only",
            }],
        }
        with zipfile.ZipFile(self.package_path, "w", compression=zipfile.ZIP_STORED) as archive:
            archive.writestr("tso-resources.json", json.dumps(package))
            archive.writestr("pdfs/known-home-guide.pdf", b"x" * (1024 * 1024))
        self.import_id = self.store.save_import(
            ResourcePackageImporter().read(self.package_path)
        )
        self.run_id = self.store.create_research_run(
            "hermes", "Find Housing resources", {"selectedSeed": None}, self.import_id, None
        )
        self.manager = AcceptedResourceManager(self.store)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    @staticmethod
    def candidate(name: str = "New Housing Program") -> dict[str, object]:
        return {
            "name": name,
            "organization": "Helpful Organization",
            "program": "Housing Navigation",
            "phone": "801-555-0100",
            "address": "10 Center Street, Provo, UT",
            "website": "https://helpful.example.org/housing",
            "hours": "Monday-Friday, 9-5",
            "resourceType": "Housing navigation",
            "housingNeed": "Helps people locate and apply for stable housing.",
            "description": "A longer researcher explanation for the Information field.",
            "geography": "Utah County",
            "accessTimeline": "Call for an intake appointment.",
            "eligibility": ["Adults experiencing homelessness", "Utah County resident"],
            "barriers": ["Photo identification may be requested"],
            "availability": {
                "status": "Accepting referrals",
                "asOf": "2026-08-17",
                "evidence": "Confirmed on the program page",
            },
            "petPolicy": "Ask during intake.",
            "experienceAssessment": {"privacy": "Private appointments are available"},
            "unknowns": ["Current appointment wait"],
            "followUpBranches": ["Confirm Spanish-language availability"],
            "evidence": [{
                "title": "Official housing page",
                "url": "https://helpful.example.org/housing",
                "finding": "Describes navigation and application help.",
                "sourceType": "official",
                "reliability": "high",
                "accessedAt": "2026-08-17",
            }],
        }

    def save_candidate(self, name: str = "New Housing Program") -> dict[str, object]:
        saved = self.store.save_discovery(self.candidate(name), run_id=self.run_id)
        discovery = self.store.get_discovery(saved["id"])
        assert discovery is not None
        return discovery

    def test_accept_creates_editable_tso_resource_with_requested_field_mapping(self) -> None:
        discovery = self.save_candidate()
        reviewed = self.manager.review_candidate(discovery["id"], "accepted")
        generated = self.store.get_generated_resource(discovery["id"])

        self.assertEqual("accepted", reviewed["status"])
        self.assertIsNotNone(generated)
        resource = generated["resource"]
        self.assertEqual("New Housing Program", resource["name"])
        self.assertEqual("801-555-0100", resource["phone"])
        self.assertEqual("10 Center Street, Provo, UT", resource["address"])
        self.assertEqual("https://helpful.example.org/housing", resource["website"])
        self.assertEqual("Monday-Friday, 9-5", resource["hours"])
        self.assertEqual(
            "Helps people locate and apply for stable housing.", resource["description"]
        )
        self.assertIsNone(resource["verifiedOn"])
        self.assertEqual(["housing"], resource["categories"])
        self.assertEqual([], resource["pdfs"])
        self.assertIn("**Resource details**", resource["informationText"])
        self.assertIn("* Research description: A longer researcher explanation", resource["informationText"])
        self.assertIn("**Verify before referral**", resource["informationText"])
        self.assertIn("---", resource["informationText"])
        self.assertIn("https://helpful.example.org/housing", resource["informationText"])

    def test_resource_id_survives_review_changes_and_human_edits(self) -> None:
        discovery = self.save_candidate()
        self.manager.review_candidate(discovery["id"], "accepted")
        first = self.store.get_generated_resource(discovery["id"])["resource"]
        self.manager.review_candidate(discovery["id"], "research-further")
        self.manager.review_candidate(discovery["id"], "accepted")
        second = self.store.get_generated_resource(discovery["id"])["resource"]
        self.assertEqual(first["id"], second["id"])

        updated = self.manager.update_resource(discovery["id"], {
            "name": "Reviewer-corrected name",
            "verifiedOn": "08/26",
            "informationText": "**Call first**\n\n* Ask about availability",
        })["resource"]
        self.assertEqual(first["id"], updated["id"])
        self.assertEqual("Reviewer-corrected name", updated["name"])
        self.assertEqual("08/26", updated["verifiedOn"])
        self.assertEqual(["housing"], updated["categories"])
        with self.assertRaisesRegex(GeneratedResourceError, "MM/YY"):
            self.manager.update_resource(discovery["id"], {"verifiedOn": "August 2026"})

    def test_export_is_cumulative_run_scoped_and_contains_no_baseline_or_assets(self) -> None:
        first = self.save_candidate("First accepted resource")
        second = self.save_candidate("Second accepted resource")
        self.manager.review_candidate(first["id"], "accepted")
        initial = self.manager.build_package(
            self.run_id, exported_at=datetime(2026, 8, 17, tzinfo=timezone.utc)
        )
        self.assertEqual(1, initial.resource_count)

        self.manager.review_candidate(second["id"], "accepted")
        cumulative = self.manager.build_package(self.run_id)
        with zipfile.ZipFile(io.BytesIO(cumulative.content)) as archive:
            self.assertEqual(["tso-resources.json"], archive.namelist())
            data = json.loads(archive.read("tso-resources.json"))

        self.assertEqual(3, data["resourcePackageSchemaVersion"])
        self.assertEqual(43, data["packageVersion"])
        self.assertEqual(["housing"], [category["id"] for category in data["categories"]])
        self.assertEqual(
            ["First accepted resource", "Second accepted resource"],
            [resource["name"] for resource in data["resources"]],
        )
        exported_json = json.dumps(data)
        self.assertNotIn("Known Home", exported_json)
        self.assertNotIn("known-home-guide.pdf", exported_json)
        self.assertNotIn("privateExtension", exported_json)
        self.assertLess(len(cumulative.content), len(self.package_path.read_bytes()) // 10)

        other_run = self.store.create_research_run(
            "hermes", "Other run", {"selectedSeed": None}, self.import_id, None
        )
        other = self.store.save_discovery(self.candidate("Other run resource"), run_id=other_run)
        self.manager.review_candidate(other["id"], "accepted")
        self.assertNotIn(
            "Other run resource", json.dumps(self.manager.build_package(self.run_id).data)
        )

        self.manager.review_candidate(first["id"], "rejected")
        after_rejection = self.manager.build_package(self.run_id).data
        self.assertEqual(["Second accepted resource"], [item["name"] for item in after_rejection["resources"]])

    def test_food_export_preserves_package_types_for_groups_and_multicategory_review(self) -> None:
        run_id = self.store.create_research_run(
            "hermes", "Find food resources", {"selectedSeed": None}, self.import_id, None,
            target_category_id="food", target_category_label="Food",
        )
        candidate = self.candidate("Family meal program")
        candidate.update({
            "serviceNeed": "Provides a dependable evening meal for families.",
            "recommendedTypes": ["Meals", "Not a package Type"],
            "recommendedFor": ["Families with children", "Not a package For label"],
        })
        saved = self.store.save_discovery(candidate, run_id=run_id)
        self.manager.review_candidate(saved["id"], "accepted")
        generated = self.store.get_generated_resource(saved["id"])["resource"]
        self.assertEqual(["food"], generated["categories"])
        self.assertEqual({"food": ["Meals"]}, generated["categoryFilters"])
        self.assertEqual(["Families with children"], generated["forGroups"])

        self.manager.update_resource(saved["id"], {
            "categories": ["food", "housing"],
            "categoryFilters": {"food": ["Meals"], "housing": ["Shelter"]},
            "forGroups": ["Families with children", "Veterans"],
        })
        data = self.manager.build_package(run_id).data
        self.assertEqual(["food", "housing"], [item["id"] for item in data["categories"]])
        self.assertEqual(["Families with children", "Veterans"], data["forGroups"])
        self.assertEqual(
            {"food": ["Meals"], "housing": ["Shelter"]},
            data["resources"][0]["categoryFilters"],
        )
        self.assertIn("food-research-run", self.manager.build_package(run_id).filename)

        with self.assertRaisesRegex(GeneratedResourceError, "no longer defined"):
            self.manager.update_resource(saved["id"], {
                "categories": ["food"], "categoryFilters": {"food": ["Renamed label"]},
            })

    def test_standalone_review_stays_review_only(self) -> None:
        run_id = self.store.create_research_run(
            "hermes", "Research Mesa", {"selectedSeed": None},
            research_mode="standalone-location", target_location="Mesa, Arizona",
        )
        saved = self.store.save_discovery(self.candidate("Mesa lead"), run_id=run_id)
        reviewed = self.manager.review_candidate(saved["id"], "accepted")
        self.assertEqual("accepted", reviewed["status"])
        self.assertIsNone(self.store.get_generated_resource(saved["id"]))
        with self.assertRaisesRegex(GeneratedResourceError, "package-backed"):
            self.manager.build_package(run_id)

    def test_export_refuses_to_mislabel_an_older_source_schema(self) -> None:
        discovery = self.save_candidate()
        self.manager.review_candidate(discovery["id"], "accepted")
        with self.store.connect() as connection:
            connection.execute(
                "UPDATE imports SET schema_version = '2' WHERE id = ?",
                (self.import_id,),
            )
        with self.assertRaisesRegex(GeneratedResourceError, "schema 3"):
            self.manager.build_package(self.run_id)

    def test_migration_recovers_source_package_for_older_package_backed_run(self) -> None:
        with self.store.connect() as connection:
            connection.execute(
                "UPDATE research_runs SET source_import_id = NULL WHERE id = ?",
                (self.run_id,),
            )
        reopened = ResearchStore(self.store.path)
        self.assertEqual(self.import_id, reopened.get_run(self.run_id)["sourceImportId"])

    def test_http_review_edit_and_download_flow(self) -> None:
        discovery = self.save_candidate()
        web_dir = Path(__file__).resolve().parent.parent / "web"
        server = ResearchHTTPServer(("127.0.0.1", 0), self.store, web_dir)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base = f"http://127.0.0.1:{server.server_address[1]}"
            review_request = urllib.request.Request(
                f"{base}/api/discoveries/{discovery['id']}/review",
                data=json.dumps({"status": "accepted"}).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(review_request, timeout=5) as response:
                accepted = json.loads(response.read())["discovery"]
            self.assertEqual("accepted", accepted["status"])
            self.assertEqual(
                "New Housing Program", accepted["generatedResource"]["resource"]["name"]
            )

            edit_request = urllib.request.Request(
                f"{base}/api/discoveries/{discovery['id']}/generated-resource",
                data=json.dumps({"resource": {
                    "name": "Reviewer-corrected resource",
                    "verifiedOn": "08/26",
                }}).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(edit_request, timeout=5) as response:
                edited = json.loads(response.read())
            self.assertEqual(
                "Reviewer-corrected resource", edited["generatedResource"]["resource"]["name"]
            )

            with urllib.request.urlopen(
                f"{base}/api/research-runs/{self.run_id}/resource-package", timeout=5
            ) as response:
                content = response.read()
                self.assertEqual("application/zip", response.headers.get_content_type())
                self.assertIn("attachment;", response.headers["Content-Disposition"])
                self.assertIn("research-run-1-resource-package.zip", response.headers["Content-Disposition"])
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                package = json.loads(archive.read("tso-resources.json"))
            self.assertEqual(
                ["Reviewer-corrected resource"], [item["name"] for item in package["resources"]]
            )
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
