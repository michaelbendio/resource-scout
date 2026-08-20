from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from resource_research_agent.duplicates import DuplicateIndex
from resource_research_agent.importer import PackageImportError, ResourcePackageImporter
from resource_research_agent.storage import ResearchStore


class ImporterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def package(self, data: object, member: str = "nested/resource-data.json", assets: dict[str, bytes] | None = None) -> Path:
        path = self.root / "resource-package.zip"
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr(member, json.dumps(data))
            archive.writestr("assets/readme.txt", "not resource data")
            for asset_path, content in (assets or {}).items():
                archive.writestr(asset_path, content)
        return path

    @staticmethod
    def hash(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def test_discovers_nested_schema_and_multicategory_housing(self) -> None:
        marker = {"nested": [1, 2, 3], "important": "preserve me"}
        path = self.package({
            "schemaVersion": "custom-7",
            "data": {
                "categoryDefinitions": [
                    {"key": "need-housing", "name": "Housing"},
                    {"key": "food", "name": "Food"},
                ],
                "records": [
                    {"id": "one", "title": "One", "categoryIds": ["need-housing"], "extension": marker},
                    {"id": "two", "title": "Two", "categoryIds": ["food", "need-housing"]},
                    {"id": "three", "title": "Three", "categoryIds": ["food"]},
                ],
            },
        })
        before = self.hash(path)
        imported = ResourcePackageImporter().read(path)
        self.assertEqual(imported.target_category_id, "need-housing")
        self.assertEqual(len(imported.resources), 3)
        self.assertEqual(len(imported.target_resources), 2)
        self.assertEqual(imported.multicategory_target_count, 1)
        self.assertEqual(imported.target_resources[0]["extension"], marker)
        self.assertEqual(imported.schema.resource_path, ("data", "records"))
        self.assertEqual(self.hash(path), before, "the source ZIP must remain byte-for-byte unchanged")

    def test_categories_can_be_inferred_from_resource_records(self) -> None:
        path = self.package({"items": [
            {"id": "h", "name": "A Home", "categories": ["Housing"]},
            {"id": "f", "name": "A Pantry", "categories": ["Food"]},
        ]})
        imported = ResourcePackageImporter("housing").read(path)
        self.assertEqual([item["id"] for item in imported.target_resources], ["h"])
        self.assertIsNone(imported.schema.category_path)

    def test_package_identity_uses_metadata_then_known_filename_fallback(self) -> None:
        mesa = self.package({
            "categories": [{"id": "housing", "label": "Housing"}],
            "resources": [],
        })
        mesa_named = mesa.with_name("mesa-resource-package.zip")
        mesa.rename(mesa_named)
        imported = ResourcePackageImporter().read(mesa_named)
        self.assertEqual("Mesa TSO", imported.identity["officeName"])
        self.assertEqual(
            "Mesa and Maricopa County, Arizona", imported.identity["serviceArea"]
        )
        self.assertEqual("filename-fallback", imported.identity["identitySource"])

        explicit = self.package({
            "officeName": "East Valley TSO",
            "serviceArea": "East Valley, Arizona",
            "categories": [{"id": "housing", "label": "Housing"}],
            "resources": [],
        })
        explicit_import = ResourcePackageImporter().read(explicit)
        self.assertEqual("East Valley TSO", explicit_import.identity["officeName"])
        self.assertEqual("East Valley, Arizona", explicit_import.identity["serviceArea"])
        self.assertEqual("package-metadata", explicit_import.identity["identitySource"])

    def test_missing_target_category_is_explained(self) -> None:
        path = self.package({"resources": [{"id": "f", "name": "Food", "categories": ["food"]}]})
        with self.assertRaisesRegex(PackageImportError, "was not found"):
            ResourcePackageImporter().read(path)

    def test_rejects_unsafe_member_paths(self) -> None:
        path = self.package({"resources": [{"id": "h", "name": "Home", "categories": ["housing"]}]}, "../data.json")
        with self.assertRaisesRegex(PackageImportError, "Unsafe ZIP member"):
            ResourcePackageImporter().read(path)

    def test_full_records_seeds_and_discoveries_are_separate(self) -> None:
        full = {
            "id": "known", "name": "Known Housing", "categories": ["housing", "food"],
            "aliases": ["Known Home"], "website": "https://known.example/program",
            "address": "12 North Main Street", "privateExtension": {"keep": True},
            "pdfs": [{"name": "Housing guide.pdf", "path": "pdfs/known/guide.pdf"}],
        }
        path = self.package(
            {"categories": [{"id": "housing", "label": "Housing"}, {"id": "food", "label": "Food Assistance"}], "resources": [full]},
            assets={"pdfs/known/guide.pdf": b"%PDF-1.4 test attachment"},
        )
        store = ResearchStore(self.root / "research.sqlite3")
        import_id = store.save_import(ResourcePackageImporter().read(path))
        seeds = store.list_seeds(import_id)
        self.assertEqual(seeds[0]["fullRecord"], full)
        self.assertFalse(seeds[0]["seedContext"]["isNewDiscovery"])
        self.assertEqual(seeds[0]["categories"][1], {"id": "food", "label": "Food Assistance"})
        self.assertTrue(seeds[0]["attachments"][0]["available"])
        asset = store.seed_asset(import_id, "known", "pdfs/known/guide.pdf")
        self.assertEqual(asset["name"], "Housing guide.pdf")
        self.assertEqual(asset["mediaType"], "application/pdf")
        self.assertEqual(asset["content"], b"%PDF-1.4 test attachment")
        self.assertEqual(store.list_discoveries(), [])

        match = DuplicateIndex(store).match({"name": "Known Home", "website": "known.example/other"})[0]
        self.assertEqual(match["resourceId"], "known")
        self.assertEqual(match["classification"], "already-known")
        saved = store.save_discovery({"name": "Known Home"}, match)
        self.assertFalse(saved["isNewDiscovery"])
        self.assertEqual(saved["status"], "already-known")
        self.assertEqual(len(store.list_seeds()), 1)
        self.assertEqual(len(store.list_discoveries()), 1)

    def test_index_covers_all_resources_not_only_housing(self) -> None:
        path = self.package({
            "categories": [{"id": "housing", "label": "Housing"}, {"id": "health", "label": "Health"}],
            "resources": [
                {"id": "seed", "name": "Housing Seed", "categories": ["housing"]},
                {"id": "cross", "name": "Cross Category Agency", "categories": ["health"], "website": "cross.example"},
            ],
        })
        store = ResearchStore(self.root / "research.sqlite3")
        store.save_import(ResourcePackageImporter().read(path))
        match = DuplicateIndex(store).match({"name": "Cross Category Agency"})[0]
        self.assertEqual(match["resourceId"], "cross")
        self.assertFalse(match["isTargetCategory"])

    def test_package_taxonomy_and_all_category_seeds_are_preserved(self) -> None:
        path = self.package({
            "resourcePackageSchemaVersion": 3,
            "categories": [
                {"id": "housing", "name": "Housing", "filters": []},
                {"id": "food", "name": "Food", "filters": ["Meals", "Pantries"]},
                {"id": "employment", "name": "Employment", "filters": ["Temp Agencies"]},
                {"id": "legal", "name": "Legal", "filters": ["Pro bono"]},
            ],
            "forGroups": ["Families with children", "Veterans"],
            "resources": [
                {"id": "meal", "name": "Community Meal", "categories": ["food"]},
                {"id": "work", "name": "Job Center", "categories": ["employment", "legal"]},
                {"id": "law", "name": "Legal Aid", "categories": ["legal"]},
            ],
        })
        store = ResearchStore(self.root / "taxonomy.sqlite3")
        import_id = store.save_import(ResourcePackageImporter().read(path))
        summary = store.import_summary(import_id)
        categories = {item["id"]: item for item in summary["categories"]}
        self.assertEqual(["Meals", "Pantries"], categories["food"]["types"])
        self.assertTrue(categories["employment"]["supported"])
        self.assertTrue(categories["legal"]["supported"])
        self.assertEqual(["Families with children", "Veterans"], summary["forGroups"])
        self.assertEqual(["Community Meal"], [item["name"] for item in store.list_seeds(import_id, "food")])
        self.assertEqual(["Job Center"], [item["name"] for item in store.list_seeds(import_id, "employment")])
        self.assertEqual(
            ["Job Center", "Legal Aid"],
            [item["name"] for item in store.list_seeds(import_id, "legal")],
        )

    def test_existing_imports_gain_seeds_for_every_category_on_upgrade(self) -> None:
        path = self.package({
            "categories": [
                {"id": "housing", "name": "Housing"},
                {"id": "legal", "name": "Legal"},
            ],
            "resources": [
                {"id": "home", "name": "Known Home", "categories": ["housing"]},
                {"id": "law", "name": "Legal Aid", "categories": ["legal"]},
            ],
        })
        database = self.root / "upgrade.sqlite3"
        store = ResearchStore(database)
        import_id = store.save_import(ResourcePackageImporter().read(path))
        with store.connect() as connection:
            connection.execute(
                "DELETE FROM research_seeds WHERE import_id = ? AND resource_id = 'law'",
                (import_id,),
            )

        upgraded = ResearchStore(database)

        self.assertEqual(
            ["Legal Aid"],
            [item["name"] for item in upgraded.list_seeds(import_id, "legal")],
        )

    def test_reimport_backfills_for_groups_for_historical_runs(self) -> None:
        path = self.package({
            "resourcePackageSchemaVersion": 3,
            "categories": [{"id": "housing", "name": "Housing"}],
            "forGroups": ["Families with children", "Veterans"],
            "resources": [{"id": "home", "name": "Known Home", "categories": ["housing"]}],
        })
        store = ResearchStore(self.root / "for-upgrade.sqlite3")
        package = ResourcePackageImporter().read(path)
        historical_import_id = store.save_import(package)
        with store.connect() as connection:
            connection.execute(
                "UPDATE imports SET for_groups_json = '[]' WHERE id = ?",
                (historical_import_id,),
            )

        store.save_import(package)

        self.assertEqual(
            ["Families with children", "Veterans"],
            store.import_for_groups(historical_import_id),
        )


if __name__ == "__main__":
    unittest.main()
