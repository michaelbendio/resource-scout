from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from resource_research_agent.candidate_package import build_candidate_package
from resource_research_agent.importer import ResourcePackageImporter
from resource_research_agent.pairwise_runner import run_pairwise
from resource_research_agent.pairwise_supervisor import clone_import_baseline
from resource_research_agent.production_prep import PROFILES, prepare_production_copy
from resource_research_agent.scout_curation import _canonical_run
from resource_research_agent.storage import ResearchStore
from tests.test_challenger_routing import response


class ProductionPreparationTests(unittest.TestCase):
    def test_promotion_preserves_sources_reuses_completed_and_keeps_all_evidence_for_curation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = root / "package.zip"
            with zipfile.ZipFile(package, "w") as archive:
                archive.writestr("tso-resources.json", json.dumps({
                    "resourcePackageSchemaVersion": 3, "packageVersion": 1,
                    "officeName": "Test TSO", "serviceArea": "Test County",
                    "categories": [{"id": c, "name": c.title(), "filters": []} for c in ("food", "legal", "education")],
                    "forGroups": [], "resources": [],
                }))
            source = ResearchStore(root / "codex-grok.sqlite3")
            source.save_import(ResourcePackageImporter(None).read(package))
            for profile in PROFILES[1:]:
                clone_import_baseline(source.path, 1, root / (profile + ".sqlite3"))
            review = root / "review.md"
            review.write_text("Completed test review")
            destination = root / "production.sqlite3"
            with self.assertRaisesRegex(ValueError, "incomplete"):
                prepare_production_copy(root, destination, review_path=review, completed_count=2)
            self.assertFalse(destination.exists())

            for profile in PROFILES:
                store = ResearchStore(root / (profile + ".sqlite3"))
                with patch("resource_research_agent.pairwise_runner._run_provider", side_effect=lambda provider, assignment, **kw: {"rawText": response(provider + " " + profile), "usage": {}}):
                    run_pairwise(store, 1, profile=profile,
                        codex_binary="/usr/bin/true", codex_model="test", grok_binary="/usr/bin/true", grok_model="",
                        claude_binary="/usr/bin/true", claude_model="", codex_timeout_seconds=10,
                        grok_timeout_seconds=10, claude_timeout_seconds=10, claude_max_turns=60,
                        retry_count=0, max_passes=None, max_categories=2, preflight=False)
            hashes = {p: hashlib.sha256((root / (p + ".sqlite3")).read_bytes()).hexdigest() for p in PROFILES}
            manifest = prepare_production_copy(root, destination, review_path=review, completed_count=2)
            self.assertEqual("ready", manifest["status"])
            self.assertFalse(manifest["launched"])
            self.assertEqual(2, manifest["completedCategories"])
            self.assertEqual(["education"], manifest["pendingCategories"])
            self.assertEqual(1, len(manifest["retiredEmptyPlans"]))
            self.assertEqual(hashes, {p: hashlib.sha256((root / (p + ".sqlite3")).read_bytes()).hexdigest() for p in PROFILES})
            production = ResearchStore(destination)
            self.assertEqual(3, len(production.list_focused_research_jobs(1)))
            package_data = build_candidate_package(production, 1).data
            for union in manifest["curationUnions"]:
                runs = [r for r in package_data["runs"] if r["run"]["targetCategoryId"] == union["categoryId"]]
                self.assertEqual(union["runId"], _canonical_run(runs)["run"]["id"])
                self.assertEqual(set(PROFILES), {c["profile"] for c in union["contributions"]})
                self.assertEqual({"primary", "challenger"}, {c["sourceRole"] for c in union["contributions"]})
                for contribution in union["contributions"]:
                    saved = production.get_manual_contribution(union["runId"], contribution["newContributionId"])
                    self.assertEqual(contribution["rawSha256"], saved["rawSha256"])
            with source.connect() as original, production.connect() as copied:
                for table in ("focused_research_passes", "codex_first_research_assignments"):
                    before = [tuple(r) for r in original.execute(f"SELECT * FROM {table} WHERE job_id IN (1,2) ORDER BY id")]
                    after = [tuple(r) for r in copied.execute(f"SELECT * FROM {table} WHERE job_id IN (1,2) ORDER BY id")]
                    self.assertEqual(before, after)
            with self.assertRaisesRegex(ValueError, "already exists"):
                prepare_production_copy(root, destination, review_path=review, completed_count=2)


if __name__ == "__main__":
    unittest.main()
