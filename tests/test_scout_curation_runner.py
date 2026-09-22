from __future__ import annotations

import json
import tempfile
import unittest
import argparse
import hashlib
import zipfile
from pathlib import Path
from unittest.mock import patch

from resource_research_agent.scout_curation_runner import (
    compact_assignment, execute_worker, validate_links, write_once,
    run, candidate_batches, read_worker_result, write_evidence_once, encode,
)
from resource_research_agent.storage import ResearchStore
from resource_research_agent.importer import ResourcePackageImporter
from resource_research_agent.duplicates import DuplicateIndex
from resource_research_agent.manual_consolidation import consolidate_manual_discovery, finish_manual_discovery


class CurationRunnerTests(unittest.TestCase):
    def test_reviewed_repair_preserves_raw_output_and_keeps_validation_required(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            original = {"assignmentSha256": "sealed", "categoryId": "education",
                        "scoutCurationResultSchemaVersion": 1,
                        "resources": [{"id": "real", "candidateIds": ["1"]},
                                      {"id": "stray", "candidateIds": ["1"]}],
                        "candidateDispositions": [{"candidateId": "1", "disposition": "curated", "resourceIds": ["real"]}]}
            raw = encode(original); (root / "result.json").write_text(raw)
            with self.assertRaisesRegex(ValueError, "Inconsistent"):
                validate_links({}, read_worker_result(root))
            corrected = {**original, "resources": original["resources"][:1]}
            repair = {"originalSha256": hashlib.sha256(raw.encode()).hexdigest(),
                      "resultSha256": hashlib.sha256(encode(corrected).encode()).hexdigest(),
                      "reviewer": "supervising-codex", "reviewedAt": "2026-09-19T20:00:00Z",
                      "reason": "Removed reviewed stray placeholder; retained the real entry and all decisions.",
                      "evidence": [{"removedResourceId": "stray", "retainedResourceId": "real"}],
                      "result": corrected}
            path = root / "reviewed-result-repair.json"; path.write_text(encode(repair))
            self.assertEqual(corrected, read_worker_result(root))
            validate_links({}, read_worker_result(root))
            self.assertEqual(raw, (root / "result.json").read_text())
            # An audited repair is not permission to bypass link validation.
            invalid = {**corrected, "resources": []}
            path.write_text(encode({**repair, "result": invalid,
                "resultSha256": hashlib.sha256(encode(invalid).encode()).hexdigest()}))
            with self.assertRaisesRegex(ValueError, "Inconsistent"):
                validate_links({}, read_worker_result(root))
            # Neither changed source bytes nor moving a correction to a different
            # sealed assignment can silently reuse the review.
            path.write_text(encode(repair)); (root / "result.json").write_text(raw + " ")
            with self.assertRaisesRegex(ValueError, "Invalid reviewed"):
                read_worker_result(root)
            (root / "result.json").write_text(raw)
            changed = {**corrected, "assignmentSha256": "different"}
            path.write_text(encode({**repair, "result": changed,
                "resultSha256": hashlib.sha256(encode(changed).encode()).hexdigest()}))
            with self.assertRaisesRegex(ValueError, "sealed identity"):
                read_worker_result(root)

    def test_readable_evidence_preserves_old_sealed_bytes_and_rejects_changed_values(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            value = [{"id": "a", "informationText": "First"}, {"id": "b", "informationText": "Second"}]
            old = root / "old.json"
            original = json.dumps(value, separators=(",", ":"))
            old.write_text(original)
            write_evidence_once(old, value)
            self.assertEqual(original, old.read_text())
            new = root / "new.json"
            write_evidence_once(new, value)
            self.assertEqual(value, json.loads(new.read_text()))
            self.assertGreater(len(new.read_text().splitlines()), 2)
            with self.assertRaisesRegex(ValueError, "sealed artifact"):
                write_evidence_once(new, [{"id": "changed"}])

    def test_category_resume_and_completed_export_do_not_repeat_worker(self):
        for batch_candidates, compact_prior_index in ((0, False), (1, False), (1, True)):
            with self.subTest(batch_candidates=batch_candidates, compact_prior_index=compact_prior_index):
                self.exercise_category_resume(batch_candidates, compact_prior_index)

    def exercise_category_resume(self, batch_candidates, compact_prior_index=False):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = root / "source.zip"
            with zipfile.ZipFile(package, "w") as archive:
                archive.writestr("tso-resources.json", json.dumps({
                    "resourcePackageSchemaVersion": 3, "packageVersion": 1,
                    "officeName": "Test TSO", "serviceArea": "Test",
                    "categories": [{"id": c, "name": c.title(), "filters": []} for c in ("food", "housing")],
                    "forGroups": [], "resources": [],
                }))
            store = ResearchStore(root / "research.sqlite3")
            import_id = store.save_import(ResourcePackageImporter(None).read(package))
            for category in ("food", "housing"):
                run_id = store.create_manual_discovery_run(
                    "Find help", {"researchContext": {"mode": "package"}}, import_id,
                    target_category_id=category, target_category_label=category.title(),
                )
                store.save_manual_contribution(run_id, "Codex", json.dumps({"leads": [{
                    "organization": f"Test {category}", "program": f"Direct {category} help",
                    "website": f"https://example.org/{category}", "phone": "555-555-5555",
                    "address": "1 Main Street", "leadType": "program", "locationOrServiceArea": "Test",
                    "whyRelevant": f"Provides direct {category} help.", "uncertainty": "Confirm hours",
                }, {"organization": f"Alternate {category} name", "program": f"Direct {category} help",
                    "website": f"https://example.org/alternate-{category}", "leadType": "program",
                    "whyRelevant": "Direct service", "locationOrServiceArea": "Test"}]}))
                consolidate_manual_discovery(store, run_id, DuplicateIndex(store))
                finish_manual_discovery(store, run_id)
            args = argparse.Namespace(database=str(store.path), output=str(root / "out"),
                                      import_id=import_id, source_audit=None, max_categories=1,
                                      codex_binary="never-call", model="test", timeout_seconds=60, effort="high", batch_candidates=batch_candidates, batch_chars=60000)
            args.compact_prior_index = compact_prior_index
            def worker(directory, **kwargs):
                if directory.name == "structural-repair-1":
                    self.assertFalse(kwargs["search"])
                    repaired = json.loads((directory / "original-result.json").read_text())
                    repaired["resources"] = [r for r in repaired["resources"] if r["id"] != "stray-placeholder"]
                    (directory / "result.json").write_text(json.dumps(repaired))
                    return
                assignment = json.loads((directory / "assignment.json").read_text())
                if compact_prior_index:
                    self.assertEqual("identity-v1", assignment["batch"]["priorIndexFormat"])
                    view = json.loads((directory / "view.json").read_text())
                    self.assertTrue(all("description" not in r for r in view["previousResourceIndex"]))
                category = assignment["category"]["id"]
                ids = [str(c["id"]) for c in assignment["candidates"]]
                prior_ids = [c for r in assignment["previouslyCuratedResources"] if r["id"] == category for c in r["candidateIds"]]
                result = {
                    "scoutCurationResultSchemaVersion": 1, "assignmentSha256": assignment["assignmentSha256"],
                    "categoryId": category,
                    "resources": [{"id": category, "name": f"Direct {category}", "categories": [category], "candidateIds": prior_ids + ids,
                                   "website": f"https://example.org/{category}"}],
                    "candidateDispositions": [{"candidateId": c, "disposition": "curated", "resourceIds": [category], "reason": ""} for c in ids],
                }
                if category == "food" and not prior_ids:
                    result["resources"].append({"id": "stray-placeholder", "candidateIds": ids,
                        "website": "https://example.org/food", "categories": [category],
                        "name": "Duplicate placeholder remove", "description": "Duplicate placeholder",
                        "informationText": "Duplicate placeholder remove"})
                (directory / "result.json").write_text(json.dumps(result))
            with patch("resource_research_agent.scout_curation_runner.execute_worker", side_effect=worker) as launch:
                first = run(args)
                self.assertEqual(3 if batch_candidates else 2, launch.call_count)
                self.assertEqual("in-progress", first["status"])
                self.assertEqual("curation-awaiting-effort-review",
                                 store.list_scout_curation_progress(first["jobId"])[-1]["phase"])
                run(args)
                self.assertEqual(3 if batch_candidates else 2, launch.call_count)
                args.max_categories = None
                completed = run(args)
                self.assertEqual(5 if batch_candidates else 3, launch.call_count)
                self.assertEqual("completed", completed["status"])
                self.assertEqual(2, completed["resourceCount"])
                self.assertTrue(Path(completed["reviewFile"]).exists())
                self.assertEqual(completed, run(args))
                self.assertEqual(5 if batch_candidates else 3, launch.call_count)
                Path(completed["reviewFile"]).write_text("Human edit")
                with self.assertRaisesRegex(ValueError, "Review artifact changed"):
                    run(args)
                self.assertEqual("Human edit", Path(completed["reviewFile"]).read_text())

    def test_only_identical_resource_duplicates_are_normalized_with_original_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            resource = {"id": "same", "name": "Same provider", "candidateIds": ["1"]}
            result = {"resources": [resource, dict(resource)], "candidateDispositions": []}
            original = json.dumps(result)
            (root / "result.json").write_text(original)
            repaired = read_worker_result(root)
            self.assertEqual([resource], repaired["resources"])
            self.assertEqual(original, (root / "result.json").read_text())
            self.assertEqual(["same"], json.loads((root / "result-normalization.json").read_text())["removedDuplicateIds"])
            self.assertEqual(repaired, read_worker_result(root))
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = {"resources": [resource, {**resource, "name": "Conflicting provider"}]}
            (root / "result.json").write_text(json.dumps(result))
            self.assertEqual(result, read_worker_result(root))
            self.assertFalse((root / "normalized-result.json").exists())

    def test_compact_index_preserves_all_identities_and_full_evidence(self):
        from copy import deepcopy
        from resource_research_agent.scout_curation import _assignment_sha256
        assignment = {"candidates": [], "batch": {"index": 1, "total": 1},
                      "previouslyCuratedResources": [
                          {"id": "a", "name": "Clinic", "website": "https://example.org/a",
                           "categories": ["medical"], "description": "Detailed eligibility " * 100,
                           "informationText": "Complete body"},
                          {"id": "b", "name": "Shelter", "website": "https://example.org/b",
                           "categories": ["housing"], "description": "Different access"}]}
        legacy = deepcopy(assignment)
        legacy_view = compact_assignment(assignment)
        assignment["batch"]["priorIndexFormat"] = "identity-v1"
        compact = compact_assignment(assignment)
        self.assertNotEqual(_assignment_sha256(legacy), _assignment_sha256(assignment))
        self.assertEqual(legacy["previouslyCuratedResources"], assignment["previouslyCuratedResources"])
        self.assertEqual(["a", "b"], [r["id"] for r in compact["previousResourceIndex"]])
        self.assertEqual([{k: v for k, v in r.items() if k != "description"}
                          for r in legacy_view["previousResourceIndex"]], compact["previousResourceIndex"])
        self.assertLess(len(encode(compact)), len(encode(legacy_view)))

    def test_projection_preserves_every_identity_original_and_manual_edit(self):
        original = {"submittedOrganization": "Clinic", "uncertainty": "Adults only?", "sourceLabel": "Saved Claude", "submittedWebsite": "https://example.org"}
        assignment = {
            "assignmentSha256": "sealed", "candidates": [
                {"id": 42, "name": "Clinic", "notes": "Phone checked by staff",
                 "resourceDraft": {"phone": "555"}, "knownResourceMatch": {"id": "r1"},
                 "candidate": {"manualDiscoveryProvenance": {"members": [original]}, "manualDiscoveryChecks": ["not a verification"]}},
                {"id": 43, "name": "Legacy", "candidate": {"uncertainties": ["Unresolved"]}},
            ], "sourceResponses": ["very large raw response"],
            "previouslyCuratedResources": [{"id": "r1", "name": "Clinic", "informationText": "Must preserve eligibility"}],
        }
        before = json.dumps(assignment)
        view = compact_assignment(assignment)
        self.assertEqual([row["id"] for row in view["candidates"]], ["42", "43"])
        self.assertEqual(view["candidates"][0]["originalSubmissions"], [original])
        self.assertEqual(view["candidates"][0]["resourceDraft"], {"phone": "555"})
        self.assertEqual(view["candidates"][0]["knownResourceMatch"], {"id": "r1"})
        self.assertEqual(view["candidates"][1]["candidate"], {"uncertainties": ["Unresolved"]})
        self.assertEqual(view["assignmentSha256"], "sealed")
        self.assertIn("prior-resources.json", view["evidenceFiles"])
        self.assertEqual(json.dumps(assignment), before)

    def test_sealed_files_cannot_be_replaced_on_resume(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "assignment.json"
            write_once(path, "first")
            write_once(path, "first")
            with self.assertRaisesRegex(ValueError, "Refusing to replace"):
                write_once(path, "second")
            self.assertEqual(path.read_text(), "first")

    def test_links_must_point_to_the_actual_containing_resource(self):
        result = {"resources": [{"id": "a", "candidateIds": ["1"]}, {"id": "b", "candidateIds": ["2"]}],
                  "candidateDispositions": [{"candidateId": "1", "disposition": "curated", "resourceIds": ["b"]}]}
        with self.assertRaisesRegex(ValueError, "Inconsistent"):
            validate_links({}, result)
        result["candidateDispositions"][0]["resourceIds"] = ["a"]
        validate_links({}, result)
        result["resources"][0]["forGroups"] = ["Invented"]
        with self.assertRaisesRegex(ValueError, "Unknown For group"):
            validate_links({"availableForGroups": []}, result)

    def test_omitted_candidates_cannot_keep_resource_links(self):
        result = {"resources": [{"id": "a", "candidateIds": ["1"]}],
                  "candidateDispositions": [{"candidateId": "1", "disposition": "omitted", "resourceIds": ["a"]}]}
        with self.assertRaises(ValueError):
            validate_links({}, result)

    def test_failed_worker_keeps_artifacts_and_is_not_retried(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "prompt.txt").write_text("sealed prompt")
            process = unittest.mock.Mock()
            process.pid = 12345
            process.wait.return_value = 7
            process.returncode = 7
            process.poll.return_value = 7
            with patch("resource_research_agent.scout_curation_runner.record_worker"), patch("resource_research_agent.scout_curation_runner.subprocess.Popen", return_value=process) as launch:
                with self.assertRaisesRegex(RuntimeError, "Codex exited 7"):
                    execute_worker(root, binary="codex", model="test", timeout=60, heartbeat=lambda _: None, effort="xhigh")
            self.assertEqual(launch.call_count, 1)
            self.assertIn('model_reasoning_effort="xhigh"', launch.call_args.args[0])
            self.assertTrue((root / "events.jsonl").exists())
            self.assertEqual(json.loads((root / "execution.json").read_text())["exitCode"], 7)
            with patch("resource_research_agent.scout_curation_runner.subprocess.Popen") as launch:
                with self.assertRaises(FileExistsError):
                    execute_worker(root, binary="codex", model="test", timeout=60, heartbeat=lambda _: None)
                launch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
