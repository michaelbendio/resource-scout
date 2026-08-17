from __future__ import annotations

import os
import unittest
from pathlib import Path

from resource_research_agent.importer import ResourcePackageImporter, resource_category_ids


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


if __name__ == "__main__":
    unittest.main()

