from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from resource_research_agent.challenger_routing import load_challenger_routing
from resource_research_agent.codex_first_research import (
    codex_first_view, load_researcher_profile, prepare_codex_first_plan, validate_researcher_roster,
)
from resource_research_agent.importer import ResourcePackageImporter
from resource_research_agent.pairwise_runner import run_pairwise
from resource_research_agent.storage import ResearchStore


def response(name):
    return json.dumps({"leads": [{
        "organization": name, "program": "Assistance", "website": "https://example.org",
        "phone": "", "address": "", "leadType": "program",
        "locationOrServiceArea": "Test County", "whyRelevant": "Direct assistance",
        "uncertainty": "Confirm intake",
    }]})


class ChallengerRoutingTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch.dict("resource_research_agent.worker_policy.DISABLED_WORKERS", {}, clear=True))

    def test_scoped_second_opinion_waits_for_grok_and_resume_keeps_completed_categories(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = root / "package.zip"
            with zipfile.ZipFile(package, "w") as archive:
                archive.writestr("tso-resources.json", json.dumps({
                    "resourcePackageSchemaVersion": 3, "packageVersion": 1,
                    "officeName": "Test TSO", "serviceArea": "Test County",
                    "categories": [{"id": "food", "name": "Food", "filters": []},
                                   {"id": "legal", "name": "Legal", "filters": []}],
                    "forGroups": [], "resources": [],
                }))
            store = ResearchStore(root / "research.sqlite3")
            import_id = store.save_import(ResourcePackageImporter(None).read(package))
            policy = root / "routing.json"
            policy.write_text(json.dumps({"schemaVersion": 1, "version": "test-routing-v1", "categories": {
                "legal": {"scope": "Administrative appeals and public-benefit legal help.",
                          "reason": "Test a bounded public-system gap review."},
            }}))
            routes = load_challenger_routing(policy)
            calls = []
            def worker(provider):
                def run(assignment, **kwargs):
                    calls.append((provider, assignment))
                    if provider == "Claude":
                        active = codex_first_view(store, import_id)["activeCategory"]
                        statuses = {r["name"]: r["status"] for r in active["researchers"]}
                        self.assertEqual("completed", statuses["Codex"])
                        self.assertEqual("completed", statuses["Grok"])
                        self.assertEqual("Grok", active["researchers"][-1]["after"])
                        self.assertIn("Grok legal addition", assignment)
                        self.assertIn("Administrative appeals", assignment)
                        self.assertIn("at most eight", assignment)
                        self.assertNotIn("Grok food addition", assignment)
                    name = provider + (" legal addition" if "Category: Legal" in assignment else " food addition")
                    return response(name)
                return run
            options = dict(
                profile="codex-grok", codex_binary="/usr/bin/true", codex_model="test",
                grok_binary="/usr/bin/true", grok_model="", claude_binary="/usr/bin/true", claude_model="",
                codex_timeout_seconds=10, grok_timeout_seconds=10, claude_timeout_seconds=10,
                claude_max_turns=60, retry_count=0, max_passes=None, preflight=False,
                category_rosters=routes,
            )
            with patch("resource_research_agent.pairwise_runner._run_codex_worker", side_effect=worker("Codex")), \
                 patch("resource_research_agent.pairwise_runner._run_grok_worker", side_effect=worker("Grok")), \
                 patch("resource_research_agent.pairwise_runner._run_claude_worker", side_effect=worker("Claude")):
                first = run_pairwise(store, import_id, max_categories=1, **options)
                self.assertEqual(1, first["completedCategories"])
                self.assertNotIn("Claude", [p for p, _ in calls])
                first_count = len(calls)
                finished = run_pairwise(ResearchStore(store.path), import_id, max_categories=2, **options)
                self.assertEqual(2, finished["completedCategories"])
                self.assertTrue(all("Category: Legal" in assignment for _, assignment in calls[first_count:]))
                self.assertEqual(["Grok", "Claude"], [p for p, _ in calls[first_count:] if p != "Codex"])
                count = len(calls)
                with patch("resource_research_agent.pairwise_runner._grok_preflight", side_effect=AssertionError("completed run should not probe")):
                    run_pairwise(store, import_id, max_categories=2, **{**options, "preflight": True})
                self.assertEqual(count, len(calls))

            legal = store.get_focused_research_job(finished["categories"][1]["jobId"])
            self.assertEqual("Test a bounded public-system gap review.", legal["plan"]["researcherRoster"]["researchers"][-1]["routingReason"])
            assignments = store.list_codex_first_assignments(legal["id"])
            self.assertEqual(["completed", "completed"], [a["status"] for a in assignments])
            old_hashes = [a["assignmentSha256"] for a in assignments]
            routes["legal"]["researchers"][-1]["scope"] = "Changed scope"
            with self.assertRaisesRegex(ValueError, "different sealed"):
                prepare_codex_first_plan(store, import_id, roster=load_researcher_profile("codex-grok"), category_rosters=routes)
            self.assertEqual(old_hashes, [a["assignmentSha256"] for a in store.list_codex_first_assignments(legal["id"])])
            self.assertEqual(2, len(store.list_focused_research_jobs(import_id)))

    def test_forward_or_disabled_dependency_is_rejected(self):
        for researchers in [
            [{"name": "Codex", "role": "primary"}, {"name": "Claude", "role": "challenger", "after": "Grok"}, {"name": "Grok", "role": "challenger"}],
            [{"name": "Codex", "role": "primary"}, {"name": "Grok", "role": "disabled"}, {"name": "Claude", "role": "challenger", "after": "Grok"}],
        ]:
            with self.assertRaisesRegex(RuntimeError, "earlier enabled"):
                validate_researcher_roster({"schemaVersion": 1, "researchers": researchers})


if __name__ == "__main__":
    unittest.main()
