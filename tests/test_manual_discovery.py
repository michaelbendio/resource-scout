from __future__ import annotations

import hashlib
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from resource_research_agent.manual_discovery import (
    MAX_MANUAL_CONTRIBUTION_BYTES,
    normalize_manual_identity,
    normalize_manual_url,
    parse_manual_contribution,
)
from resource_research_agent.storage import ResearchStore


FIXTURES = Path(__file__).parent / "fixtures" / "manual_discovery"


class ManualDiscoveryParserTests(unittest.TestCase):
    def test_pilot_contributions_parse_without_discarding_source_material(self) -> None:
        expected = json.loads((FIXTURES / "expected.json").read_text(encoding="utf-8"))
        total = 0
        for source in expected["sourceOrder"]:
            raw_text = (FIXTURES / expected["files"][source]).read_text(encoding="utf-8")
            parsed = parse_manual_contribution(raw_text)
            with self.subTest(source=source):
                self.assertEqual("parsed", parsed["status"])
                self.assertEqual("", parsed["error"])
                self.assertIsInstance(parsed["parsed"], dict)
                self.assertEqual(len(parsed["parsed"]["leads"]), len(parsed["leads"]))
                if source == "Perplexity":
                    self.assertTrue(parsed["trailingText"].strip())
                else:
                    self.assertEqual("", parsed["trailingText"].strip())
            total += len(parsed["leads"])
        self.assertEqual(expected["submittedRows"], total)

    def test_leading_prose_and_fences_are_tolerated_and_reported(self) -> None:
        raw_text = "Here is the result:\n```json\n{\"leads\": []}\n```\nSource note"
        parsed = parse_manual_contribution(raw_text)
        self.assertEqual("parsed", parsed["status"])
        self.assertEqual([], parsed["leads"])
        self.assertIn("Leading text", parsed["warnings"][0])
        self.assertIn("```", parsed["trailingText"])

    def test_invalid_payload_is_preserved_as_a_parse_error(self) -> None:
        parsed = parse_manual_contribution("A useful but non-JSON answer")
        self.assertEqual("error", parsed["status"])
        self.assertIsNone(parsed["parsed"])
        self.assertIn("No complete JSON object", parsed["error"])

        wrong_shape = parse_manual_contribution('{"leads": "not an array"}')
        self.assertEqual("error", wrong_shape["status"])
        self.assertEqual("The leads field must be an array", wrong_shape["error"])

    def test_incomplete_rows_are_retained_with_specific_warnings(self) -> None:
        parsed = parse_manual_contribution(
            '{"leads":[{"organization":"Example","website":7,"leadType":"mystery"},9]}'
        )
        self.assertEqual("parsed", parsed["status"])
        self.assertEqual(1, len(parsed["leads"]))
        warnings = " | ".join(parsed["leads"][0]["warnings"])
        self.assertIn("Missing fields", warnings)
        self.assertIn("Non-text fields: website", warnings)
        self.assertIn("Lead type is missing or unsupported", warnings)
        self.assertTrue(any("Lead 2 is not an object" in item for item in parsed["warnings"]))

    def test_urls_are_normalized_without_accepting_unsafe_values(self) -> None:
        self.assertEqual(
            ("https://example.org/path", ["Markdown link converted to a plain URL"]),
            normalize_manual_url("[Example](https://EXAMPLE.org/path#fragment)"),
        )
        self.assertEqual(
            ("https://example.org/", ["URL scheme defaulted to https"]),
            normalize_manual_url("example.org"),
        )
        for unsafe in (
            "javascript:alert(1)",
            "data:text/html,<script>alert(1)</script>",
            "<a href=https://example.org onclick=alert(1)>Example</a>",
            "https://user:secret@example.org",
        ):
            with self.subTest(unsafe=unsafe):
                normalized, warnings = normalize_manual_url(unsafe)
                self.assertEqual("", normalized)
                self.assertTrue(warnings)

    def test_identity_normalization_is_conservative(self) -> None:
        self.assertEqual(
            normalize_manual_identity("Community Bridges, Inc. (CBI)"),
            normalize_manual_identity("Community Bridges"),
        )
        self.assertNotEqual(
            normalize_manual_identity("Community Bridges East Valley Addiction Recovery Center"),
            normalize_manual_identity("Community Bridges"),
        )

    def test_contribution_size_is_bounded(self) -> None:
        with self.assertRaisesRegex(ValueError, "too large"):
            parse_manual_contribution("x" * (MAX_MANUAL_CONTRIBUTION_BYTES + 1))


class ManualDiscoveryStorageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.database = Path(self.temporary.name) / "research.sqlite3"
        self.store = ResearchStore(self.database)
        self.run_id = self.store.create_manual_discovery_run(
            assignment="Discover recovery resources in Mesa",
            prompt={"assignment": "Discover recovery resources in Mesa"},
            target_location="Mesa, Arizona",
            target_category_id="substance-use-recovery",
            target_category_label="Substance Use Recovery",
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def fixture(self, source: str) -> str:
        expected = json.loads((FIXTURES / "expected.json").read_text(encoding="utf-8"))
        return (FIXTURES / expected["files"][source]).read_text(encoding="utf-8")

    def test_manual_run_has_no_agent_stages_or_attempts(self) -> None:
        run = self.store.get_run(self.run_id)
        self.assertEqual("manual-discovery", run["runKind"])
        self.assertEqual("manual-chat", run["adapter"])
        self.assertEqual("running", run["status"])
        self.assertEqual([], run["stages"])
        with self.store.connect() as connection:
            attempts = connection.execute(
                "SELECT COUNT(*) FROM research_stage_attempts WHERE run_id = ?", (self.run_id,)
            ).fetchone()[0]
        self.assertEqual(0, attempts)

    def test_raw_provenance_and_parsed_leads_round_trip(self) -> None:
        raw_text = self.fixture("ChatGPT")
        saved = self.store.save_manual_contribution(
            self.run_id,
            "ChatGPT",
            raw_text,
            filename="../chatgpt-response.txt",
        )
        self.assertEqual(raw_text, saved["rawText"])
        self.assertEqual(hashlib.sha256(raw_text.encode()).hexdigest(), saved["rawSha256"])
        self.assertEqual("chatgpt-response.txt", saved["filename"])
        self.assertEqual("parsed", saved["parseStatus"])
        self.assertEqual(3, len(saved["leads"]))
        self.assertEqual([saved], self.store.list_manual_contributions(self.run_id))

        reopened = ResearchStore(self.database)
        self.assertEqual([saved], reopened.list_manual_contributions(self.run_id))

    def test_same_source_replaces_content_but_preserves_source_order(self) -> None:
        original = self.store.save_manual_contribution(
            self.run_id, "ChatGPT", self.fixture("ChatGPT")
        )
        second = self.store.save_manual_contribution(self.run_id, "Claude", self.fixture("Claude"))
        replacement_text = '{"leads":[]}'
        replacement = self.store.save_manual_contribution(
            self.run_id, "  chatgpt  ", replacement_text
        )
        self.assertEqual(original["id"], replacement["id"])
        self.assertEqual(1, replacement["sourcePosition"])
        self.assertEqual([], replacement["leads"])
        self.assertEqual(second["id"], self.store.list_manual_contributions(self.run_id)[1]["id"])

    def test_parse_errors_are_saved_instead_of_losing_the_submission(self) -> None:
        raw_text = "No JSON was returned"
        saved = self.store.save_manual_contribution(self.run_id, "Perplexity", raw_text)
        self.assertEqual("error", saved["parseStatus"])
        self.assertEqual(raw_text, saved["rawText"])
        self.assertTrue(saved["error"])
        self.assertEqual([], saved["leads"])

    def test_delete_cascades_leads_and_completed_run_is_immutable(self) -> None:
        saved = self.store.save_manual_contribution(
            self.run_id, "Grok", self.fixture("Grok")
        )
        self.assertTrue(self.store.delete_manual_contribution(self.run_id, saved["id"]))
        self.assertEqual([], self.store.list_manual_contributions(self.run_id))
        self.store.complete_run(self.run_id, "", {"summary": "closed"}, None)
        with self.assertRaisesRegex(ValueError, "while the run is open"):
            self.store.save_manual_contribution(self.run_id, "Claude", self.fixture("Claude"))
        with self.assertRaisesRegex(ValueError, "while the run is open"):
            self.store.delete_manual_contribution(self.run_id, saved["id"])

    def test_legacy_run_kind_defaults_to_agent_research(self) -> None:
        legacy_run = self.store.create_research_run(
            adapter="demo", assignment="Legacy", prompt={}
        )
        self.assertEqual("agent-research", self.store.get_run(legacy_run)["runKind"])

    def test_existing_database_gains_run_kind_and_manual_tables(self) -> None:
        old_database = Path(self.temporary.name) / "old.sqlite3"
        connection = sqlite3.connect(old_database)
        connection.execute(
            """CREATE TABLE research_runs (
                   id INTEGER PRIMARY KEY, created_at TEXT NOT NULL, started_at TEXT,
                   completed_at TEXT, status TEXT NOT NULL, adapter TEXT NOT NULL,
                   assignment TEXT NOT NULL, research_mode TEXT NOT NULL DEFAULT 'package',
                   target_location TEXT, regional_scope TEXT NOT NULL DEFAULT '',
                   target_category_id TEXT NOT NULL DEFAULT 'housing',
                   target_category_label TEXT NOT NULL DEFAULT 'Housing',
                   source_import_id INTEGER, seed_import_id INTEGER, seed_resource_id TEXT,
                   prompt_json TEXT NOT NULL, output_text TEXT NOT NULL DEFAULT '',
                   result_json TEXT, usage_json TEXT, error TEXT NOT NULL DEFAULT ''
               )"""
        )
        connection.execute(
            """INSERT INTO research_runs
               (created_at, status, adapter, assignment, prompt_json)
               VALUES ('then', 'completed', 'deepseek', 'Historical run', '{}')"""
        )
        connection.commit()
        connection.close()

        upgraded = ResearchStore(old_database)

        self.assertEqual("agent-research", upgraded.get_run(1)["runKind"])
        with upgraded.connect() as connection:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                ).fetchall()
            }
        self.assertIn("manual_discovery_contributions", tables)
        self.assertIn("manual_discovery_leads", tables)


if __name__ == "__main__":
    unittest.main()
