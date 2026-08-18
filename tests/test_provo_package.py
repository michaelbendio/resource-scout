from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from resource_research_agent.importer import ResourcePackageImporter, resource_category_ids
from resource_research_agent.storage import ResearchStore


class ProvoPackageIntegrationTest(unittest.TestCase):
    @unittest.skipUnless(os.environ.get("PROVO_RESOURCE_PACKAGE"), "set PROVO_RESOURCE_PACKAGE for the live-package test")
    def test_current_provo_package(self) -> None:
        path = Path(os.environ["PROVO_RESOURCE_PACKAGE"])
        imported = ResourcePackageImporter().read(path)
        self.assertGreater(imported.schema.schema_version, 0)
        self.assertGreater(len(imported.categories), 1)
        self.assertGreater(len(imported.resources), 1)
        self.assertGreater(len(imported.target_resources), 1)
        self.assertTrue(any(len(resource_category_ids(item)) > 1 for item in imported.target_resources))
        self.assertTrue(all(item for item in imported.target_resources))
        with tempfile.TemporaryDirectory() as directory:
            store = ResearchStore(Path(directory) / "research.sqlite3")
            import_id = store.save_import(imported)
            categories = store.list_import_categories(import_id)
            self.assertTrue(categories)
            self.assertTrue(all(category["supported"] for category in categories))
            for category in categories:
                self.assertEqual(
                    category["resourceCount"],
                    len(store.list_seeds(import_id, category["id"])),
                    category["label"],
                )


if __name__ == "__main__":
    unittest.main()
