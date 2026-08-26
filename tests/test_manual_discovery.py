from __future__ import annotations

import hashlib
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

from resource_research_agent.importer import ResourcePackageImporter
from resource_research_agent.manual_discovery import (
    MAX_MANUAL_CONTRIBUTION_BYTES,
    build_manual_discovery_assignment,
    normalize_manual_identity,
    normalize_manual_url,
    parse_manual_contribution,
)
from resource_research_agent.server import ResearchHTTPServer
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

    def test_assignment_uses_supplied_category_area_and_known_resources(self) -> None:
        food = build_manual_discovery_assignment(
            category_label="Food",
            service_area="Mesa, Arizona",
            known_resources=[{"id": "pantry-1", "name": "Known Pantry"}],
        )
        legal = build_manual_discovery_assignment(
            category_label="Legal",
            service_area="Mesa, Arizona",
            known_resources=[],
        )
        self.assertIn("credible Food resource leads", food)
        self.assertIn("pantry-1: Known Pantry", food)
        self.assertNotIn("Known Pantry", legal)
        for assignment in (food, legal):
            self.assertNotIn("Housing", assignment)
            self.assertNotIn("Addiction", assignment)
            self.assertIn('"leadType"', assignment)
            self.assertIn('"phone"', assignment)
            self.assertIn('"address"', assignment)
            self.assertIn("readily available", assignment)

    def test_optional_phone_and_address_are_preserved(self) -> None:
        raw = json.dumps({"leads": [{
            "organization": "Example Center", "program": "Recovery",
            "website": "https://example.org", "phone": "480-555-0100",
            "address": "123 Main St, Mesa, AZ", "leadType": "program",
            "locationOrServiceArea": "Mesa", "whyRelevant": "Recovery support",
            "uncertainty": "Confirm hours",
        }]})
        lead = parse_manual_contribution(raw)["leads"][0]
        self.assertEqual("480-555-0100", lead["phone"])
        self.assertEqual("123 Main St, Mesa, AZ", lead["address"])


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

    def test_discovery_run_starts_open_without_stage_machinery(self) -> None:
        run = self.store.get_run(self.run_id)
        self.assertNotIn("runKind", run)
        self.assertNotIn("adapter", run)
        self.assertEqual("running", run["status"])
        with self.store.connect() as connection:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
        self.assertNotIn("research_run_stages", tables)
        self.assertNotIn("research_stage_attempts", tables)

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

        reopened = ResearchStore(self.database, recover_interrupted=True)
        self.assertEqual([saved], reopened.list_manual_contributions(self.run_id))
        self.assertEqual("running", reopened.get_run(self.run_id)["status"])

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
        with self.store.connect() as connection:
            connection.execute(
                "UPDATE research_runs SET status = 'completed' WHERE id = ?",
                (self.run_id,),
            )
        with self.assertRaisesRegex(ValueError, "while the run is open"):
            self.store.save_manual_contribution(self.run_id, "Claude", self.fixture("Claude"))
        with self.assertRaisesRegex(ValueError, "while the run is open"):
            self.store.delete_manual_contribution(self.run_id, saved["id"])
        with self.store.connect() as connection:
            tables = {
                row["name"]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
        self.assertIn("manual_discovery_identity_members", tables)
        self.assertIn("manual_discovery_identity_decisions", tables)
        self.assertIn("discovery_contact_lookups", tables)


class ManualDiscoveryHTTPTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.package_path = self.root / "mesa-resource-package.zip"
        package = {
            "resourcePackageSchemaVersion": 3,
            "officeName": "Mesa TSO",
            "serviceArea": "Mesa and Maricopa County, Arizona",
            "categories": [
                {"id": "food", "name": "Food"},
                {"id": "legal", "name": "Legal"},
            ],
            "resources": [
                {"id": "known-pantry", "name": "Known Pantry", "categories": ["food"]},
                {"id": "known-legal", "name": "Known Legal Aid", "categories": ["legal"]},
            ],
        }
        with zipfile.ZipFile(self.package_path, "w") as archive:
            archive.writestr("tso-resources.json", json.dumps(package))
        self.package_hash = hashlib.sha256(self.package_path.read_bytes()).hexdigest()
        self.store = ResearchStore(self.root / "research.sqlite3")
        self.import_id = self.store.save_import(ResourcePackageImporter("food").read(self.package_path))
        web_dir = Path(__file__).resolve().parent.parent / "web"
        self.server = ResearchHTTPServer(("127.0.0.1", 0), self.store, web_dir)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self.temporary.cleanup()

    def request(self, path: str, method: str = "GET", payload: dict | None = None) -> dict:
        data = json.dumps(payload).encode() if payload is not None else None
        request = urllib.request.Request(
            self.base + path,
            data=data,
            headers={"Content-Type": "application/json"} if data is not None else {},
            method=method,
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            return json.loads(response.read())

    def test_package_assignment_and_manual_run_lifecycle_use_no_agent(self) -> None:
        assignment_result = self.request(
            "/api/manual-discovery-assignment",
            "POST",
            {
                "researchMode": "package",
                "sourceImportId": self.import_id,
                "categoryId": "food",
            },
        )
        assignment = assignment_result["assignment"]
        self.assertIn("Food", assignment)
        self.assertIn("Mesa and Maricopa County", assignment)
        self.assertIn("known-pantry: Known Pantry", assignment)
        self.assertNotIn("Known Legal Aid", assignment)
        self.assertEqual(self.package_hash, hashlib.sha256(self.package_path.read_bytes()).hexdigest())

        run = self.request(
            "/api/manual-discovery-runs",
            "POST",
            {
                "assignment": assignment,
                "researchMode": "package",
                "sourceImportId": self.import_id,
                "categoryId": "food",
            },
        )
        self.assertNotIn("runKind", run)
        self.assertEqual("running", run["status"])
        contribution = self.request(
            f"/api/manual-discovery-runs/{run['id']}/contributions",
            "POST",
            {
                "sourceLabel": "ChatGPT",
                "rawText": '{"leads":[]}',
                "filename": "response.json",
            },
        )
        snapshot = self.request(
            f"/api/manual-discovery-runs/{run['id']}/contributions"
        )
        self.assertEqual([contribution], snapshot["contributions"])
        self.assertEqual(1, snapshot["run"]["manualProgress"]["contributionCount"])
        deleted = self.request(
            f"/api/manual-discovery-runs/{run['id']}/contributions/{contribution['id']}",
            "DELETE",
        )
        self.assertTrue(deleted["ok"])
        self.request(
            f"/api/manual-discovery-runs/{run['id']}/contributions",
            "POST",
            {"sourceLabel": "Claude", "rawText": '{"leads":[]}'},
        )
        consolidated = self.request(
            f"/api/manual-discovery-runs/{run['id']}/consolidate", "POST", {}
        )
        self.assertEqual(0, consolidated["funnel"]["candidateIdentities"])
        finished = self.request(
            f"/api/manual-discovery-runs/{run['id']}/finish", "POST", {}
        )
        self.assertEqual("completed", finished["status"])
        with self.assertRaises(urllib.error.HTTPError) as raised:
            self.request(
                f"/api/manual-discovery-runs/{run['id']}/contributions",
                "POST",
                {"sourceLabel": "Grok", "rawText": '{"leads":[]}'},
            )
        self.assertEqual(400, raised.exception.code)
        raised.exception.close()

    def test_standalone_assignment_uses_the_selected_category(self) -> None:
        result = self.request(
            "/api/manual-discovery-assignment",
            "POST",
            {
                "researchMode": "standalone-location",
                "categoryId": "food",
                "categoryLabel": "Food",
                "targetLocation": "Flagstaff, Arizona",
            },
        )
        self.assertEqual("food", result["context"]["categoryId"])
        self.assertEqual("Food", result["context"]["categoryLabel"])
        self.assertIn("credible Food resource leads", result["assignment"])
        self.assertIn("Flagstaff, Arizona", result["assignment"])
        self.assertNotIn("Housing", result["assignment"])

    def test_manual_workspace_is_served_as_the_recommended_touch_usable_path(self) -> None:
        with urllib.request.urlopen(self.base + "/", timeout=5) as response:
            html = response.read().decode()
        with urllib.request.urlopen(self.base + "/app.js", timeout=5) as response:
            javascript = response.read().decode()
        with urllib.request.urlopen(self.base + "/app.css", timeout=5) as response:
            css = response.read().decode()
        self.assertNotIn("Research agent", html)
        self.assertNotIn('id="research-method"', html)
        self.assertNotIn("Research context", html)
        self.assertNotIn('id="research-context-note"', html)
        self.assertIn('id="standalone-mode"', html)
        self.assertIn("Research a location without a package", html)
        self.assertIn(">Start discovery</button>", html)
        self.assertIn("status.playbookCategories", javascript)
        self.assertNotIn("categoryId: researchMode === 'package' ? state.activeCategoryId : 'housing'", javascript)
        self.assertIn("copy-manual-assignment", html)
        self.assertIn("manual-source-list", html)
        self.assertIn("['ChatGPT', 'Grok', 'Claude', 'Perplexity']", javascript)
        self.assertIn("Choose text or JSON file", javascript)
        self.assertIn("window.confirm", javascript)
        self.assertNotIn("Finish discovery and lock", javascript)
        finish_block = javascript[
            javascript.index("document.querySelector('#finish-manual-discovery').addEventListener"):
            javascript.index("document.querySelector('#copy-private-url').addEventListener")
        ]
        self.assertNotIn("openManualDiscoveryRun", finish_block)
        self.assertIn("manual-discovery-dialog').close()", finish_block)
        self.assertIn("textContent = contribution.trailingText", javascript)
        self.assertIn("Consolidate leads", html)
        self.assertIn('id="manual-next-step"', html)
        self.assertIn("Next: Select Consolidate leads.", javascript)
        self.assertIn("#finish-manual-discovery:disabled { cursor: not-allowed; }", css)
        self.assertIn("Lead and identity presentation", html)
        self.assertIn("Same identity", javascript)
        self.assertIn("Keep separate", javascript)
        self.assertIn("Leave unresolved", javascript)
        self.assertIn("Leave all ${pendingSuggestions.length} pending pairs unresolved", javascript)
        self.assertIn("Possible relationships retained", javascript)
        self.assertIn("No further action is required here.", javascript)
        self.assertIn("if (!locked) card.append(actions);", javascript)
        self.assertIn("Review responses and leads", javascript)
        self.assertIn("Collect responses", javascript)
        self.assertIn("function manualRunActionLabel(run)", javascript)
        self.assertIn("openManual.textContent = manualRunActionLabel(run)", javascript)
        self.assertIn("if (run.status === 'running')", javascript)
        self.assertNotIn("View responses and leads", javascript)
        self.assertIn("document.createElement('details')", javascript)
        self.assertIn("summary.className = 'run-summary'", javascript)
        self.assertIn("separator.textContent = '·'", javascript)
        self.assertIn("expandedRunIds: new Set()", javascript)
        self.assertIn("item.open = state.expandedRunIds.has(run.id)", javascript)
        self.assertIn(".run[open] > .run-summary::before", css)
        self.assertIn("Export website lookup", javascript)
        self.assertIn("Import website results", javascript)
        self.assertIn("runActionMessages", javascript)
        self.assertIn("was not imported", javascript)
        self.assertIn("file.name", javascript)
        self.assertIn(".run-actions button, .run-actions .review-export", css)
        self.assertIn(".run-action-status.error", css)
        self.assertIn('class="category-list" id="category-grid"', html)
        self.assertIn("types.className = 'category-types'", javascript)
        self.assertNotIn("category.resourceCount", javascript)
        self.assertIn(".category-row + .category-row", css)
        self.assertIn("excluded lead", javascript)
        self.assertIn("'unavailable', 'unreachable'", javascript)
        self.assertIn(".excluded-leads", css)
        self.assertIn("#manual-consolidation').scrollIntoView", javascript)
        self.assertIn("manual-reviewed-identities", css)
        self.assertIn("@media (max-width: 800px)", css)
        self.assertIn(".manual-source-list { grid-template-columns: 1fr; }", css)

    def test_contact_lookup_request_and_results_round_trip_through_http(self) -> None:
        run = self.request(
            "/api/manual-discovery-runs",
            "POST",
            {
                "researchMode": "package",
                "sourceImportId": self.import_id,
                "categoryId": "food",
            },
        )
        raw_text = json.dumps(
            {
                "leads": [
                    {
                        "organization": "Contactless Pantry",
                        "program": "Food boxes",
                        "website": "",
                        "phone": "",
                        "address": "",
                        "leadType": "program",
                        "locationOrServiceArea": "Mesa, Arizona",
                        "whyRelevant": "Offers emergency groceries.",
                        "uncertainty": "Confirm contact information.",
                    }
                ]
            }
        )
        self.request(
            f"/api/manual-discovery-runs/{run['id']}/contributions",
            "POST",
            {"sourceLabel": "ChatGPT", "rawText": raw_text},
        )
        self.request(f"/api/manual-discovery-runs/{run['id']}/consolidate", "POST", {})
        self.request(f"/api/manual-discovery-runs/{run['id']}/finish", "POST", {})
        with urllib.request.urlopen(
            self.base + f"/api/research-runs/{run['id']}/contact-lookup", timeout=5
        ) as response:
            request_document = json.loads(response.read())
            self.assertIn("attachment", response.headers["Content-Disposition"])
        self.assertEqual(1, len(request_document["candidates"]))
        candidate_id = request_document["candidates"][0]["candidateId"]
        applied = self.request(
            f"/api/research-runs/{run['id']}/contact-lookup",
            "POST",
            {
                "schemaVersion": 1,
                "kind": "resource-scout-contact-lookup-results",
                "runId": run["id"],
                "results": [
                    {
                        "candidateId": candidate_id,
                        "status": "verified-contact",
                        "website": "https://contactless.example.org",
                        "sourceUrl": "https://contactless.example.org/contact",
                    }
                ],
            },
        )
        self.assertEqual(1, applied["verifiedContactCount"])
        discoveries = self.request("/api/discoveries")["discoveries"]
        saved = next(item for item in discoveries if item["id"] == candidate_id)
        self.assertEqual("https://contactless.example.org", saved["candidate"]["website"])

    def test_pending_identity_relationships_do_not_gate_finished_candidates(self) -> None:
        run = self.request(
            "/api/manual-discovery-runs",
            "POST",
            {
                "researchMode": "package",
                "sourceImportId": self.import_id,
                "categoryId": "food",
            },
        )
        organization = {
            "organization": "Example Food Network",
            "program": "",
            "website": "https://example.org",
            "leadType": "provider-organization",
            "locationOrServiceArea": "Mesa",
            "whyRelevant": "Food provider",
            "uncertainty": "Confirm access",
        }
        program = dict(organization, program="Fresh Food Program", leadType="program")
        for source, submitted in (("ChatGPT", organization), ("Claude", program)):
            self.request(
                f"/api/manual-discovery-runs/{run['id']}/contributions",
                "POST",
                {"sourceLabel": source, "rawText": json.dumps({"leads": [submitted]})},
            )
        consolidated = self.request(
            f"/api/manual-discovery-runs/{run['id']}/consolidate", "POST", {}
        )
        self.assertEqual(1, consolidated["funnel"]["pendingIdentityDecisions"])
        finished = self.request(
            f"/api/manual-discovery-runs/{run['id']}/finish", "POST", {}
        )
        self.assertEqual(2, finished["result"]["candidateCount"])
        discoveries = self.request("/api/discoveries")["discoveries"]
        candidates = [item for item in discoveries if item["runId"] == run["id"]]
        program_candidate = next(
            item for item in candidates if item["candidate"]["programName"] == "Fresh Food Program"
        )
        self.assertEqual("Fresh Food Program", program_candidate["name"])
        self.assertEqual(
            "Example Food Network · Fresh Food Program",
            program_candidate["candidate"]["presentationName"],
        )
        self.assertEqual(1, len(program_candidate["candidate"]["possibleRelatedSubmissions"]))
        self.assertEqual(
            "Example Food Network",
            program_candidate["candidate"]["possibleRelatedSubmissions"][0]["displayName"],
        )

    def test_bulk_unresolved_endpoint_keeps_ambiguous_candidates_separate(self) -> None:
        run = self.request(
            "/api/manual-discovery-runs",
            "POST",
            {
                "researchMode": "package",
                "sourceImportId": self.import_id,
                "categoryId": "food",
            },
        )
        organization = {
            "organization": "Example Food Network",
            "program": "",
            "website": "https://example.org",
            "leadType": "provider-organization",
            "locationOrServiceArea": "Mesa",
            "whyRelevant": "Food provider",
            "uncertainty": "Confirm access",
        }
        program = dict(organization, program="Fresh Food Program", leadType="program")
        for source, submitted in (("ChatGPT", organization), ("Claude", program)):
            self.request(
                f"/api/manual-discovery-runs/{run['id']}/contributions",
                "POST",
                {"sourceLabel": source, "rawText": json.dumps({"leads": [submitted]})},
            )
        self.request(f"/api/manual-discovery-runs/{run['id']}/consolidate", "POST", {})
        resolved = self.request(
            f"/api/manual-discovery-runs/{run['id']}/leave-pending-unresolved",
            "POST",
            {},
        )
        self.assertEqual(0, resolved["funnel"]["pendingIdentityDecisions"])
        self.assertEqual(1, resolved["funnel"]["unresolvedIdentityDecisions"])
        finished = self.request(
            f"/api/manual-discovery-runs/{run['id']}/finish", "POST", {}
        )
        self.assertEqual(2, finished["result"]["candidateCount"])


if __name__ == "__main__":
    unittest.main()
