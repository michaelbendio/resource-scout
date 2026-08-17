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

    def package(self, data: object, member: str = "nested/resource-data.json") -> Path:
        path = self.root / "resource-package.zip"
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr(member, json.dumps(data))
            archive.writestr("assets/readme.txt", "not resource data")
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
        }
        path = self.package({"categories": [{"id": "housing", "label": "Housing"}], "resources": [full]})
        store = ResearchStore(self.root / "research.sqlite3")
        import_id = store.save_import(ResourcePackageImporter().read(path))
        seeds = store.list_seeds(import_id)
        self.assertEqual(seeds[0]["fullRecord"], full)
        self.assertFalse(seeds[0]["seedContext"]["isNewDiscovery"])
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


if __name__ == "__main__":
    unittest.main()

