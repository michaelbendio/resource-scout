from __future__ import annotations

import json
import re
import tempfile
import threading
import unittest
import urllib.request
import zipfile
from pathlib import Path

from resource_research_agent.importer import ResourcePackageImporter
from resource_research_agent.manual_consolidation import (
    consolidate_manual_discovery,
    finish_manual_discovery,
)
from resource_research_agent.reconciliation import reconcile_completed_run
from resource_research_agent.review_export import build_review_copy
from resource_research_agent.server import ResearchHTTPServer
from resource_research_agent.storage import ResearchStore


class CompletedRunReconciliationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.store = ResearchStore(self.root / "research.sqlite3")
        self.original_import_id = self.import_package("empty.zip", [])
        self.run_id = self.store.create_manual_discovery_run(
            "Discover Addiction resources in Mesa",
            {"researchContext": {"sourcePackage": {"sourceName": "empty.zip"}}},
            self.original_import_id,
            target_category_id="addiction",
            target_category_label="Addiction",
        )
        self.store.save_manual_contribution(
            self.run_id,
            "ChatGPT",
            json.dumps({
                "leads": [{
                    "organization": "Amelia Recovery Center",
                    "program": "",
                    "website": "https://amelia.example.org",
                    "leadType": "provider-organization",
                    "locationOrServiceArea": "Mesa",
                    "whyRelevant": "Provides addiction recovery support.",
                    "uncertainty": "Confirm intake details.",
                }, {
                    "organization": "Name Only Recovery",
                    "program": "",
                    "website": "",
                    "leadType": "provider-organization",
                    "locationOrServiceArea": "Mesa",
                    "whyRelevant": "Provides peer recovery support.",
                    "uncertainty": "Confirm identity and contact details.",
                }]
            }),
        )
        consolidate_manual_discovery(self.store, self.run_id)
        finish_manual_discovery(self.store, self.run_id)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def import_package(self, filename: str, resources: list[dict[str, object]]) -> int:
        path = self.root / filename
        package = {
            "resourcePackageSchemaVersion": 3,
            "packageVersion": len(resources) + 1,
            "officeName": "Mesa TSO",
            "serviceArea": "Mesa and Maricopa County, Arizona",
            "categories": [{"id": "addiction", "name": "Addiction"}],
            "resources": resources,
        }
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("tso-resources.json", json.dumps(package))
        return self.store.save_import(ResourcePackageImporter("addiction").read(path))

    @staticmethod
    def embedded_data(html: bytes) -> dict[str, object]:
        match = re.search(
            r'<script id="review-data" type="application/json">(.*?)</script>',
            html.decode("utf-8"),
            re.DOTALL,
        )
        if not match:
            raise AssertionError("embedded review data was not found")
        return json.loads(match.group(1))

    def test_reconciliation_preserves_original_basis_and_rebases_curator(self) -> None:
        replacement_import_id = self.import_package(
            "mesa-resource-package.zip",
            [{
                "id": "amelia-recovery",
                "name": "Amelia Recovery Center",
                "website": "https://amelia.example.org",
                "categories": ["addiction"],
            }, {
                "id": "name-only",
                "name": "Name Only Recovery",
                "categories": ["addiction"],
            }],
        )

        result = reconcile_completed_run(
            self.store, self.run_id, replacement_import_id
        )

        self.assertEqual(2, result["candidateCount"])
        self.assertEqual(1, result["alreadyKnownCount"])
        self.assertEqual(1, result["possibleRelationshipCount"])
        self.assertEqual(0, result["unmatchedCount"])
        run = self.store.get_run(self.run_id)
        self.assertEqual(self.original_import_id, run["sourceImportId"])
        self.assertEqual(replacement_import_id, run["reconciliation"]["targetImportId"])
        review = self.embedded_data(build_review_copy(self.store, self.run_id).html)
        self.assertEqual(
            self.store.import_summary(replacement_import_id)["sourceSha256"],
            review["sourcePackage"]["sourceSha256"],
        )
        self.assertEqual(
            1,
            review["run"]["candidateCount"],
        )
        self.assertEqual(
            "possible-duplicate",
            review["candidates"][0]["knownResourceMatch"]["classification"],
        )
        self.assertEqual(
            "already-in-package",
            next(iter(self.store.reconciliation_matches(
                run["reconciliation"]["id"]
            ).values()))["classification"],
        )

        updated_import_id = self.import_package(
            "mesa-updated-resource-package.zip",
            [{
                "id": "amelia-recovery",
                "name": "Amelia Recovery Center",
                "website": "https://amelia.example.org",
                "categories": ["addiction"],
            }, {
                "id": "second-resource",
                "name": "Second Recovery Resource",
                "categories": ["addiction"],
            }, {
                "id": "name-only",
                "name": "Name Only Recovery",
                "categories": ["addiction"],
            }],
        )
        reconcile_completed_run(self.store, self.run_id, updated_import_id)
        with self.store.connect() as connection:
            count = connection.execute(
                "SELECT COUNT(*) AS count FROM research_run_reconciliations WHERE run_id = ?",
                (self.run_id,),
            ).fetchone()["count"]
        self.assertEqual(2, count)

    def test_same_package_content_is_not_offered_twice(self) -> None:
        replacement_import_id = self.import_package(
            "mesa-resource-package.zip",
            [{
                "id": "amelia-recovery",
                "name": "Amelia Recovery Center",
                "website": "https://amelia.example.org",
                "categories": ["addiction"],
            }],
        )
        reconcile_completed_run(self.store, self.run_id, replacement_import_id)

        same_content_import_id = self.import_package(
            "renamed-resource-package.zip",
            [{
                "id": "amelia-recovery",
                "name": "Amelia Recovery Center",
                "website": "https://amelia.example.org",
                "categories": ["addiction"],
            }],
        )
        self.assertNotEqual(replacement_import_id, same_content_import_id)
        self.assertEqual(
            self.store.import_summary(replacement_import_id)["contentSha256"],
            self.store.import_summary(same_content_import_id)["contentSha256"],
        )

        with self.assertRaisesRegex(ValueError, "already uses the connected package"):
            reconcile_completed_run(self.store, self.run_id, same_content_import_id)

    def test_http_endpoint_reconciles_and_returns_refreshed_discoveries(self) -> None:
        replacement_import_id = self.import_package(
            "mesa-resource-package.zip",
            [{
                "id": "amelia-recovery",
                "name": "Amelia Recovery Center",
                "website": "https://amelia.example.org",
                "categories": ["addiction"],
            }],
        )
        web_dir = Path(__file__).resolve().parent.parent / "web"
        server = ResearchHTTPServer(("127.0.0.1", 0), self.store, web_dir)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_address[1]}"
        try:
            request = urllib.request.Request(
                base + f"/api/research-runs/{self.run_id}/reconcile",
                data=json.dumps({"importId": replacement_import_id}).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=5) as response:
                result = json.loads(response.read())
            self.assertEqual(self.run_id, result["runId"])
            with urllib.request.urlopen(base + "/api/research-runs", timeout=5) as response:
                runs = json.loads(response.read())["runs"]
            self.assertEqual(
                replacement_import_id,
                runs[0]["reconciliation"]["targetImportId"],
            )
            with urllib.request.urlopen(base + "/api/discoveries", timeout=5) as response:
                discoveries = json.loads(response.read())["discoveries"]
            amelia = next(item for item in discoveries if item["name"] == "Amelia Recovery Center")
            self.assertEqual(
                "already-in-package", amelia["matchDetails"]["classification"]
            )
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
