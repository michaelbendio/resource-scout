from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from resource_research_agent.importer import ResourcePackageImporter
from resource_research_agent.manual_consolidation import (
    consolidate_manual_discovery,
    finish_manual_discovery,
    leave_pending_manual_identities_unresolved,
    record_manual_identity_decision,
)
from resource_research_agent.review_export import build_review_copy
from resource_research_agent.storage import ResearchStore


FIXTURES = Path(__file__).parent / "fixtures" / "manual_discovery"


def payload(*leads: dict[str, str]) -> str:
    return json.dumps({"leads": list(leads)})


def lead(
    organization: str,
    program: str = "",
    *,
    website: str = "",
    lead_type: str = "provider-organization",
    location: str = "Mesa, Arizona",
    why: str = "Relevant lead",
    uncertainty: str = "Confirm details",
    phone: str = "",
    address: str = "",
) -> dict[str, str]:
    return {
        "organization": organization,
        "program": program,
        "website": website,
        "phone": phone,
        "address": address,
        "leadType": lead_type,
        "locationOrServiceArea": location,
        "whyRelevant": why,
        "uncertainty": uncertainty,
    }


class ManualConsolidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.store = ResearchStore(self.root / "research.sqlite3")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def create_run(self, store: ResearchStore | None = None) -> int:
        active_store = store or self.store
        return active_store.create_manual_discovery_run(
            "Discover leads",
            {},
            target_location="Mesa, Arizona",
            target_category_id="addiction",
            target_category_label="Addiction",
        )

    def save_pilot(self, run_id: int, store: ResearchStore | None = None, reverse: bool = False) -> None:
        active_store = store or self.store
        expected = json.loads((FIXTURES / "expected.json").read_text())
        sources = list(expected["sourceOrder"])
        if reverse:
            sources.reverse()
        for source in sources:
            active_store.save_manual_contribution(
                run_id,
                source,
                (FIXTURES / expected["files"][source]).read_text(),
            )

    def test_four_source_pilot_has_an_honest_noninflated_funnel(self) -> None:
        run_id = self.create_run()
        self.save_pilot(run_id)
        result = consolidate_manual_discovery(self.store, run_id)
        self.assertEqual(
            {
                "submittedRows": 14,
                "parsedLeads": 14,
                "exactDuplicateRows": 3,
                "consolidatedIdentities": 11,
                "possiblePackageDuplicates": 0,
                "providerProgramIdentities": 7,
                "accessPointIdentities": 0,
                "routingDirectoryIdentities": 3,
                "outreachInitiatives": 1,
                "unresolvedIdentities": 0,
                "candidateIdentities": 7,
                "pendingIdentityDecisions": 2,
                "sameIdentityDecisions": 0,
                "separateIdentityDecisions": 0,
                "unresolvedIdentityDecisions": 0,
            },
            result["funnel"],
        )
        roles = {group["program"] or group["organization"]: group["routedRole"] for group in result["groups"]}
        self.assertEqual("directory", roles["Opioid treatment locator"])
        self.assertEqual("routing-source", roles["988 Suicide & Crisis Lifeline"])
        self.assertEqual("outreach-initiative", roles["Overdose prevention outreach"])
        self.assertEqual(2, len(result["suggestions"]))

    def test_identity_review_merges_or_separates_without_written_justification(self) -> None:
        run_id = self.create_run()
        self.store.save_manual_contribution(
            run_id,
            "ChatGPT",
            payload(lead("Example Services", "Recovery Program", lead_type="program")),
        )
        self.store.save_manual_contribution(
            run_id,
            "Claude",
            payload(lead("Example Services")),
        )
        first = consolidate_manual_discovery(self.store, run_id)
        suggestion = first["suggestions"][0]
        separated = record_manual_identity_decision(
            self.store,
            run_id,
            suggestion["leftKey"],
            suggestion["rightKey"],
            "separate",
        )
        self.assertEqual(2, separated["funnel"]["consolidatedIdentities"])
        self.assertEqual(0, separated["funnel"]["pendingIdentityDecisions"])
        self.assertTrue(
            all(group["consolidationState"] == "reviewed-separate" for group in separated["groups"])
        )
        merged = record_manual_identity_decision(
            self.store,
            run_id,
            suggestion["leftKey"],
            suggestion["rightKey"],
            "same",
        )
        self.assertEqual(1, merged["funnel"]["consolidatedIdentities"])
        self.assertEqual("program", merged["groups"][0]["routedRole"])
        self.assertEqual("reviewed-merge", merged["groups"][0]["consolidationState"])
        self.assertEqual(2, len(merged["groups"][0]["members"]))

    def test_distinct_programs_stay_separate_while_locations_do_not_multiply_one_program(self) -> None:
        run_id = self.create_run()
        self.store.save_manual_contribution(
            run_id,
            "ChatGPT",
            payload(
                lead("One Organization", "Program A", lead_type="program", location="Mesa"),
                lead("One Organization", "Program B", lead_type="program", location="Mesa"),
            ),
        )
        self.store.save_manual_contribution(
            run_id,
            "Grok",
            payload(lead("One Organization", "Program A", lead_type="program", location="Tempe")),
        )
        result = consolidate_manual_discovery(self.store, run_id)
        self.assertEqual(2, result["funnel"]["consolidatedIdentities"])
        self.assertEqual(1, result["funnel"]["exactDuplicateRows"])
        self.assertEqual([], result["suggestions"])
        self.assertEqual(
            {"One Organization · Program A", "One Organization · Program B"},
            {group["displayName"] for group in result["groups"]},
        )

    def test_two_chat_votes_do_not_turn_a_weak_lead_into_verified_truth(self) -> None:
        run_id = self.create_run()
        weak = lead(
            "Unconfirmed Center",
            website="",
            location="Possibly Mesa",
            why="A chat recalled this name",
            uncertainty="No current source or access path",
        )
        self.store.save_manual_contribution(run_id, "ChatGPT", payload(weak))
        self.store.save_manual_contribution(run_id, "Grok", payload(weak))
        result = consolidate_manual_discovery(self.store, run_id)
        self.assertEqual(1, result["funnel"]["consolidatedIdentities"])
        group = result["groups"][0]
        self.assertEqual(2, len(group["members"]))
        self.assertNotIn("verified", json.dumps(group).casefold())
        self.assertEqual("provider-organization", group["routedRole"])

    def test_access_points_and_directories_do_not_collapse_into_a_provider(self) -> None:
        run_id = self.create_run()
        shared = dict(organization="Shared Organization", website="https://shared.example.org")
        self.store.save_manual_contribution(
            run_id,
            "ChatGPT",
            payload(
                lead(**shared, lead_type="provider-organization"),
                lead(**shared, lead_type="access-point", why="Public intake desk"),
                lead(**shared, lead_type="directory", why="Searchable directory"),
            ),
        )
        result = consolidate_manual_discovery(self.store, run_id)
        self.assertEqual(3, result["funnel"]["consolidatedIdentities"])
        self.assertEqual(
            {"provider-organization", "access-point", "directory"},
            {group["routedRole"] for group in result["groups"]},
        )
        self.assertEqual([], result["suggestions"])

    def test_parent_organization_cannot_bridge_two_distinct_named_programs(self) -> None:
        run_id = self.create_run()
        self.store.save_manual_contribution(
            run_id,
            "ChatGPT",
            payload(
                lead("Parent Organization"),
                lead("Parent Organization", "Program A", lead_type="program"),
                lead("Parent Organization", "Program B", lead_type="program"),
            ),
        )
        result = consolidate_manual_discovery(self.store, run_id)
        self.assertEqual(2, len(result["suggestions"]))
        first, second = result["suggestions"]
        record_manual_identity_decision(
            self.store,
            run_id,
            first["leftKey"],
            first["rightKey"],
            "same",
        )
        with self.assertRaisesRegex(ValueError, "distinct named programs"):
            record_manual_identity_decision(
                self.store,
                run_id,
                second["leftKey"],
                second["rightKey"],
                "same",
            )

    def test_grouping_is_repeatable_when_source_import_order_changes(self) -> None:
        first_run = self.create_run()
        self.save_pilot(first_run)
        first = consolidate_manual_discovery(self.store, first_run)
        other_store = ResearchStore(self.root / "other.sqlite3")
        second_run = self.create_run(other_store)
        self.save_pilot(second_run, other_store, reverse=True)
        second = consolidate_manual_discovery(other_store, second_run)
        self.assertEqual(first["funnel"], second["funnel"])
        self.assertEqual(
            [group["stableKey"] for group in first["groups"]],
            [group["stableKey"] for group in second["groups"]],
        )

    def test_replacing_a_response_invalidates_groups_and_identity_decisions(self) -> None:
        run_id = self.create_run()
        self.store.save_manual_contribution(
            run_id,
            "ChatGPT",
            payload(lead("Example", "Program", lead_type="program")),
        )
        self.store.save_manual_contribution(run_id, "Claude", payload(lead("Example")))
        result = consolidate_manual_discovery(self.store, run_id)
        suggestion = result["suggestions"][0]
        record_manual_identity_decision(
            self.store, run_id, suggestion["leftKey"], suggestion["rightKey"], "same"
        )
        self.store.save_manual_contribution(run_id, "Claude", payload(lead("Different")))
        self.assertIsNone(self.store.manual_consolidation_snapshot(run_id))
        self.assertEqual([], self.store.manual_identity_decisions(run_id))

    def test_saving_an_unchanged_response_preserves_consolidation_and_decisions(self) -> None:
        run_id = self.create_run()
        first = payload(lead("Example", "Program", lead_type="program"))
        second = payload(lead("Example"))
        self.store.save_manual_contribution(run_id, "ChatGPT", first)
        original = self.store.save_manual_contribution(run_id, "Claude", second)
        result = consolidate_manual_discovery(self.store, run_id)
        suggestion = result["suggestions"][0]
        decided = record_manual_identity_decision(
            self.store, run_id, suggestion["leftKey"], suggestion["rightKey"], "separate"
        )
        snapshot = self.store.manual_consolidation_snapshot(run_id)

        unchanged = self.store.save_manual_contribution(run_id, "Claude", second)

        self.assertEqual(original, unchanged)
        self.assertEqual(snapshot, self.store.manual_consolidation_snapshot(run_id))
        self.assertEqual(decided["funnel"], snapshot["funnel"])
        self.assertEqual("separate", self.store.manual_identity_decisions(run_id)[0]["decision"])

    def test_parse_error_must_be_corrected_or_deleted_before_consolidation(self) -> None:
        run_id = self.create_run()
        self.store.save_manual_contribution(run_id, "Grok", "not json")
        with self.assertRaisesRegex(ValueError, "parse errors"):
            consolidate_manual_discovery(self.store, run_id)

    def test_supplementary_unknowns_never_block_an_uncertain_candidate(self) -> None:
        run_id = self.create_run()
        self.store.save_manual_contribution(
            run_id,
            "Claude",
            payload(
                lead(
                    "Uncertain Provider",
                    website="",
                    location="Possibly Mesa; confirm service area",
                    why="Provides relevant recovery support",
                    uncertainty="Pet policy, hours, payment, eligibility, and current openings are unknown",
                )
            ),
        )
        consolidated = consolidate_manual_discovery(self.store, run_id)
        checks = consolidated["groups"][0]["checks"]
        self.assertEqual("present", checks["identity"]["state"])
        self.assertEqual("uncertain", checks["geography"]["state"])
        self.assertEqual("present", checks["categoryRelevance"]["state"])
        self.assertEqual("uncertain", checks["currentSignal"]["state"])
        self.assertEqual("uncertain", checks["publicAccess"]["state"])
        finished = finish_manual_discovery(self.store, run_id)
        self.assertEqual(1, finished["result"]["candidateCount"])

    def test_package_duplicate_signals_are_visible_but_do_not_erase_the_group(self) -> None:
        package_path = self.root / "mesa-resource-package.zip"
        with zipfile.ZipFile(package_path, "w") as archive:
            archive.writestr(
                "tso-resources.json",
                json.dumps(
                    {
                        "officeName": "Mesa TSO",
                        "serviceArea": "Mesa, Arizona",
                        "categories": [{"id": "addiction", "name": "Addiction"}],
                        "resources": [
                            {
                                "id": "known-center",
                                "name": "Known Recovery Center",
                                "categories": ["addiction"],
                                "website": "https://known.example.org",
                            }
                        ],
                    }
                ),
            )
        import_id = self.store.save_import(
            ResourcePackageImporter("addiction").read(package_path)
        )
        run_id = self.store.create_manual_discovery_run(
            "Discover leads",
            {},
            import_id,
            target_category_id="addiction",
            target_category_label="Addiction",
        )
        self.store.save_manual_contribution(
            run_id,
            "Claude",
            payload(lead("Known Recovery Center", website="https://known.example.org")),
        )
        result = consolidate_manual_discovery(self.store, run_id)
        self.assertEqual(1, result["funnel"]["possiblePackageDuplicates"])
        self.assertEqual("known-center", result["groups"][0]["duplicateMatches"][0]["resourceId"])

    def test_finish_keeps_pending_relationships_separate_and_creates_only_direct_candidates(self) -> None:
        run_id = self.create_run()
        self.save_pilot(run_id)
        result = consolidate_manual_discovery(self.store, run_id)
        finished = finish_manual_discovery(self.store, run_id)
        self.assertEqual("completed", finished["status"])
        self.assertEqual(7, finished["result"]["candidateCount"])
        discoveries = self.store.list_discoveries(run_id)
        self.assertEqual(7, len(discoveries))
        self.assertTrue(
            all(
                discovery["candidate"]["resourceType"]
                in {"program", "provider-organization", "access-point"}
                for discovery in discoveries
            )
        )
        self.assertTrue(
            all(discovery["candidate"]["manualDiscoveryProvenance"]["members"] for discovery in discoveries)
        )
        related = [
            discovery for discovery in discoveries
            if discovery["candidate"]["possibleRelatedSubmissions"]
        ]
        self.assertTrue(related)
        self.assertTrue(
            all(
                relationship["reviewState"] == "pending"
                for discovery in related
                for relationship in discovery["candidate"]["possibleRelatedSubmissions"]
            )
        )
        ids = [discovery["id"] for discovery in discoveries]
        with self.assertRaisesRegex(ValueError, "already closed"):
            finish_manual_discovery(self.store, run_id)
        self.assertEqual(ids, [discovery["id"] for discovery in self.store.list_discoveries(run_id)])

    def test_pending_identity_pairs_can_be_left_unresolved_atomically(self) -> None:
        run_id = self.create_run()
        self.save_pilot(run_id)
        result = consolidate_manual_discovery(self.store, run_id)
        self.assertEqual(2, result["funnel"]["pendingIdentityDecisions"])
        result = leave_pending_manual_identities_unresolved(self.store, run_id)
        self.assertEqual(0, result["funnel"]["pendingIdentityDecisions"])
        self.assertEqual(2, result["funnel"]["unresolvedIdentityDecisions"])
        self.assertTrue(all(item["status"] == "unresolved" for item in result["suggestions"]))
        self.assertEqual(7, finish_manual_discovery(self.store, run_id)["result"]["candidateCount"])

    def test_manual_curator_export_is_minimal_safe_and_preserves_source_only_records(self) -> None:
        package_path = self.root / "mesa-resource-package.zip"
        with zipfile.ZipFile(package_path, "w") as archive:
            archive.writestr(
                "tso-resources.json",
                json.dumps(
                    {
                        "resourcePackageSchemaVersion": 3,
                        "packageVersion": "1",
                        "officeName": "Mesa TSO",
                        "serviceArea": "Mesa and Maricopa County, Arizona",
                        "categories": [{"id": "addiction", "name": "Addiction"}],
                        "forGroups": ["Veterans"],
                        "resources": [],
                    }
                ),
            )
        import_id = self.store.save_import(
            ResourcePackageImporter("addiction").read(package_path)
        )
        run_id = self.store.create_manual_discovery_run(
            "Discover Addiction leads",
            {
                "researchContext": {
                    "sourcePackage": {
                        "officeName": "Mesa TSO",
                        "serviceArea": "Mesa and Maricopa County, Arizona",
                    }
                }
            },
            import_id,
            target_category_id="addiction",
            target_category_label="Addiction",
        )
        hostile = "Relevant lead </script><img src=x onerror=alert(1)>"
        self.store.save_manual_contribution(
            run_id,
            "ChatGPT </script>",
            payload(
                lead(
                    "Minimal Recovery Provider",
                    website="https://minimal.example.org",
                    phone="480-555-0100",
                    address="123 Main St, Mesa, AZ",
                    why=hostile,
                    uncertainty="Confirm identity, service area, and access",
                ),
                lead(
                    "State Directory",
                    website="https://directory.example.org",
                    lead_type="directory",
                    why="Routes people to providers",
                ),
            ),
        )
        consolidate_manual_discovery(self.store, run_id)
        finish_manual_discovery(self.store, run_id)

        review = build_review_copy(self.store, run_id)

        self.assertEqual(13, review.data["reviewCopySchemaVersion"])
        self.assertEqual(1, review.data["run"]["candidateCount"])
        self.assertEqual("manual-discovery", review.data["run"]["runKind"])
        self.assertEqual(1, len(review.data["manualDiscovery"]["sourceOnlyRecords"]))
        self.assertEqual("directory", review.data["manualDiscovery"]["sourceOnlyRecords"][0]["routedRole"])
        item = review.data["candidates"][0]
        self.assertEqual("candidate", item["status"])
        self.assertIsNone(item["reviewedAt"])
        self.assertEqual("", item["reviewFeedback"])
        self.assertEqual("480-555-0100", item["resourceDraft"]["phone"])
        self.assertEqual("123 Main St, Mesa, AZ", item["resourceDraft"]["address"])
        self.assertEqual("", item["resourceDraft"]["hours"])
        self.assertIsNone(item["resourceDraft"]["verifiedOn"])
        self.assertTrue(item["candidate"]["manualDiscoveryProvenance"]["members"])
        self.assertIn("manualDiscoveryChecks", item["candidate"])
        self.assertNotIn(b"</script><img", review.html)
        self.assertNotIn(b"agent_settings", review.html)
        self.assertNotIn(b"raw_json", review.html)


if __name__ == "__main__":
    unittest.main()
