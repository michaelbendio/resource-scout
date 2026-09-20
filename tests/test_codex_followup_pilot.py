import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from resource_research_agent import codex_followup_pilot as pilot


class FollowupPilotTests(unittest.TestCase):
    def setup_pilot(self, root):
        source = root / "historical.sqlite3"
        source.write_bytes(b"sealed historical evidence")
        categories = []
        for category in pilot.CATEGORIES:
            folder = root / "workers" / category
            folder.mkdir(parents=True)
            (folder / "prompt.txt").write_text("sealed prompt")
            (folder / "schema.json").write_bytes(pilot.SCHEMA.read_bytes())
            categories.append({"categoryId": category, "workerDirectory": str(folder),
                               "promptSha256": pilot.digest(folder / "prompt.txt"),
                               "schemaSha256": pilot.digest(folder / "schema.json")})
        manifest = {"sourceDatabase": str(source), "sourceSha256": pilot.digest(source),
                    "categories": categories, "maximumWorkerCalls": 2, "effort": "high",
                    "automaticRetries": 0, "timeoutSecondsPerWorker": 900,
                    "maximumLeadsPerWorker": 20, "model": "test-model"}
        (root / "pilot-manifest.json").write_text(json.dumps(manifest))
        return manifest

    def test_prompt_preserves_scope_and_identity_exclusions(self):
        old = "Old model instructions\nInclude:\n- direct help\nExclude:\n- brokers\n\nAlready found; do not repeat obvious aliases:\n- Known Program — https://example.org\n\nReturn one JSON object with a leads array."
        prompt = pilot.followup_prompt("Category", "St George", old)
        self.assertIn("Include:\n- direct help\nExclude:\n- brokers", prompt)
        self.assertIn("- Known Program — https://example.org", prompt)
        self.assertNotIn("Old model instructions", prompt)
        self.assertIn("fresh-context", prompt)
        with self.assertRaises(ValueError):
            pilot.followup_prompt("Category", "St George", "unrecognized")

    def test_resume_reuses_results_without_calls_or_source_changes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = self.setup_pilot(root)
            def worker(folder, **kwargs):
                self.assertEqual("high", kwargs["effort"])
                (folder / "result.json").write_text('{"leads": []}')
                (folder / "execution.json").write_text('{"exitCode": 0, "elapsedSeconds": 1}')
            with patch.object(pilot, "execute_worker", side_effect=worker) as run:
                self.assertTrue(pilot.run(root)["sourceUnchanged"])
                original_summary = (root / "pilot-summary.json").read_bytes()
                pilot.run(root)
                self.assertEqual(2, run.call_count)
                self.assertEqual(original_summary, (root / "pilot-summary.json").read_bytes())
            self.assertEqual(manifest["sourceSha256"], pilot.digest(Path(manifest["sourceDatabase"])))

    def test_failed_launch_never_retries_and_changed_inputs_never_launch(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.setup_pilot(root)
            with patch.object(pilot, "execute_worker", side_effect=RuntimeError("launch failed")) as run:
                with self.assertRaisesRegex(RuntimeError, "launch failed"):
                    pilot.run(root)
                with self.assertRaisesRegex(RuntimeError, "incomplete pilot"):
                    pilot.run(root)
                self.assertEqual(1, run.call_count)
            (root / "workers/addiction/prompt.txt").write_text("changed")
            with patch.object(pilot, "execute_worker") as run:
                with self.assertRaisesRegex(ValueError, "input changed"):
                    pilot.run(root)
                run.assert_not_called()

    def test_lead_validation_rejects_overflow_and_wrong_fields(self):
        pilot.validate_result({"leads": []}, 20)
        for result in ({"leads": [{}] * 21}, {"leads": [{}]}, {"other": []}):
            with self.assertRaises(ValueError):
                pilot.validate_result(result, 20)


if __name__ == "__main__":
    unittest.main()
