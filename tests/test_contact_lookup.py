from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from resource_research_agent.contact_lookup import (
    RESULTS_KIND,
    apply_contact_lookup_results,
    build_contact_lookup_request,
)
from resource_research_agent.manual_consolidation import (
    consolidate_manual_discovery,
    finish_manual_discovery,
)
from resource_research_agent.review_export import build_review_copy
from resource_research_agent.storage import ResearchStore


def lead(name: str, *, website: str = "", phone: str = "") -> dict[str, str]:
    return {
        "organization": name,
        "program": "Food assistance",
        "website": website,
        "phone": phone,
        "address": "",
        "leadType": "program",
        "locationOrServiceArea": "Mesa and Maricopa County, Arizona",
        "whyRelevant": f"{name} provides food assistance.",
        "uncertainty": "Confirm current contact information.",
    }


class ContactLookupTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.store = ResearchStore(Path(self.temporary.name) / "research.sqlite3")
        self.run_id = self.store.create_manual_discovery_run(
            "Discover food resources",
            {},
            target_location="Mesa and Maricopa County, Arizona",
            target_category_id="food",
            target_category_label="Food",
        )
        self.store.save_manual_contribution(
            self.run_id,
            "ChatGPT",
            json.dumps(
                {
                    "leads": [
                        lead("Needs Contact"),
                        lead("Closed Program"),
                        lead("Phone Only", phone="480-555-0199"),
                        lead("Already Reachable", website="https://reachable.example.org"),
                    ]
                }
            ),
        )
        consolidate_manual_discovery(self.store, self.run_id)
        finish_manual_discovery(self.store, self.run_id)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def discoveries_by_name(self) -> dict[str, dict]:
        return {
            item["candidate"]["organizationName"]: item
            for item in self.store.list_discoveries(run_id=self.run_id)
        }

    def result_document(self, results: list[dict]) -> dict:
        return {
            "schemaVersion": 1,
            "kind": RESULTS_KIND,
            "runId": self.run_id,
            "results": results,
        }

    def test_request_contains_every_candidate_missing_a_website(self) -> None:
        request = build_contact_lookup_request(
            self.store,
            self.run_id,
            exported_at=datetime(2026, 8, 26, 16, 0, tzinfo=timezone.utc),
        )
        self.assertEqual("food-contact-lookup-run-1.json", request.filename)
        self.assertEqual(
            {
                "Needs Contact · Food assistance",
                "Closed Program · Food assistance",
                "Phone Only · Food assistance",
            },
            {item["name"] for item in request.data["candidates"]},
        )
        first = request.data["candidates"][0]
        self.assertEqual(3, len(first["suggestedSearches"]))
        self.assertTrue(any("Mesa Food" in query for query in first["suggestedSearches"]))
        self.assertTrue(any("Maricopa County" in query for query in first["suggestedSearches"]))
        self.assertIn("missing or broken page alone is not proof", request.content.decode())
        self.assertIn("not actionable now", request.content.decode())
        phone_only = next(
            item
            for item in request.data["candidates"]
            if item["name"] == "Phone Only · Food assistance"
        )
        self.assertEqual("Phone Only", phone_only["organization"])

    def test_verified_contact_requires_an_official_website(self) -> None:
        candidate = self.discoveries_by_name()["Phone Only"]
        with self.assertRaisesRegex(ValueError, "needs a website"):
            apply_contact_lookup_results(
                self.store,
                self.run_id,
                self.result_document(
                    [
                        {
                            "candidateId": candidate["id"],
                            "status": "verified-contact",
                            "phone": "480-555-0199",
                            "sourceUrl": "https://directory.example.org/phone-only",
                        }
                    ]
                ),
            )

    def test_results_enrich_verified_contact_and_exclude_confirmed_unavailable(self) -> None:
        before = self.discoveries_by_name()
        result = apply_contact_lookup_results(
            self.store,
            self.run_id,
            self.result_document(
                [
                    {
                        "candidateId": before["Needs Contact"]["id"],
                        "status": "verified-contact",
                        "website": "https://needs-contact.example.org",
                        "phone": "480-555-0100",
                        "address": "1 Main St, Mesa, AZ",
                        "sourceUrl": "https://needs-contact.example.org/contact",
                        "checkedAt": "2026-08-26T16:05:00+00:00",
                        "note": "Official contact page.",
                    },
                    {
                        "candidateId": before["Closed Program"]["id"],
                        "status": "unavailable",
                        "website": "",
                        "phone": "",
                        "address": "",
                        "sourceUrl": "https://example.gov/closure-notice",
                        "checkedAt": "2026-08-26T16:06:00+00:00",
                        "note": "The administering agency says the program ended in 2025.",
                    },
                ]
            ),
        )
        self.assertEqual(1, result["verifiedContactCount"])
        self.assertEqual(1, result["unavailableCount"])
        after = self.discoveries_by_name()
        enriched = after["Needs Contact"]
        self.assertEqual("https://needs-contact.example.org", enriched["candidate"]["website"])
        self.assertEqual("480-555-0100", enriched["candidate"]["phone"])
        self.assertEqual("candidate", enriched["status"])
        unavailable = after["Closed Program"]
        self.assertEqual("unavailable", unavailable["status"])
        self.assertIn("program ended", unavailable["candidate"]["contactLookup"]["note"])

        review = build_review_copy(self.store, self.run_id)
        review_names = {item["candidate"]["organizationName"] for item in review.data["candidates"]}
        self.assertIn("Needs Contact", review_names)
        self.assertNotIn("Closed Program", review_names)
        exported = next(
            item for item in review.data["candidates"]
            if item["candidate"]["organizationName"] == "Needs Contact"
        )
        self.assertEqual(
            "https://needs-contact.example.org", exported["candidate"]["website"]
        )

    def test_unavailable_requires_positive_evidence_not_a_failed_search(self) -> None:
        candidate = self.discoveries_by_name()["Closed Program"]
        with self.assertRaisesRegex(ValueError, "cited source URL"):
            apply_contact_lookup_results(
                self.store,
                self.run_id,
                self.result_document(
                    [
                        {
                            "candidateId": candidate["id"],
                            "status": "unavailable",
                            "sourceUrl": "",
                            "note": "I could not find it.",
                        }
                    ]
                ),
            )
        self.assertEqual("candidate", self.store.get_discovery(candidate["id"])["status"])

    def test_unreachable_dead_site_is_audited_and_excluded_from_curator(self) -> None:
        candidate = self.discoveries_by_name()["Needs Contact"]
        result = apply_contact_lookup_results(
            self.store,
            self.run_id,
            self.result_document(
                [
                    {
                        "candidateId": candidate["id"],
                        "status": "unreachable",
                        "sourceUrl": "https://dead.example.org",
                        "note": (
                            "The known official website is dead, and the prescribed searches "
                            "found no replacement website or current public phone."
                        ),
                    }
                ]
            ),
        )
        self.assertEqual(1, result["unreachableCount"])
        saved = self.store.get_discovery(candidate["id"])
        self.assertEqual("unreachable", saved["status"])
        self.assertEqual("unreachable", saved["candidate"]["contactLookup"]["status"])
        request = build_contact_lookup_request(self.store, self.run_id)
        self.assertNotIn(
            candidate["id"],
            {item["candidateId"] for item in request.data["candidates"]},
        )
        review = build_review_copy(self.store, self.run_id)
        review_names = {
            item["candidate"]["organizationName"] for item in review.data["candidates"]
        }
        self.assertNotIn("Needs Contact", review_names)

    def test_unreachable_requires_dead_site_source_and_explanation(self) -> None:
        candidate = self.discoveries_by_name()["Needs Contact"]
        with self.assertRaisesRegex(ValueError, "cited source URL"):
            apply_contact_lookup_results(
                self.store,
                self.run_id,
                self.result_document(
                    [
                        {
                            "candidateId": candidate["id"],
                            "status": "unreachable",
                            "sourceUrl": "",
                            "note": "The known official website is dead.",
                        }
                    ]
                ),
            )
        with self.assertRaisesRegex(ValueError, "note explaining"):
            apply_contact_lookup_results(
                self.store,
                self.run_id,
                self.result_document(
                    [
                        {
                            "candidateId": candidate["id"],
                            "status": "unreachable",
                            "sourceUrl": "https://dead.example.org",
                            "note": "",
                        }
                    ]
                ),
            )

    def test_unresolved_lookup_is_not_removed_from_candidates(self) -> None:
        candidate = self.discoveries_by_name()["Needs Contact"]
        result = apply_contact_lookup_results(
            self.store,
            self.run_id,
            self.result_document(
                [
                    {
                        "candidateId": candidate["id"],
                        "status": "unresolved",
                        "sourceUrl": "",
                        "note": "Search results did not establish a current official contact.",
                        "suggestedNextSteps": [
                            "Call the county referral line to confirm the current program name.",
                            "Search the administering organization's program directory.",
                        ],
                    }
                ]
            ),
        )
        self.assertEqual(1, result["unresolvedCount"])
        saved = self.store.get_discovery(candidate["id"])
        self.assertEqual("candidate", saved["status"])
        self.assertEqual("unresolved", saved["candidate"]["contactLookup"]["status"])
        review = build_review_copy(self.store, self.run_id)
        exported = next(
            item for item in review.data["candidates"]
            if item["candidate"]["organizationName"] == "Needs Contact"
        )
        self.assertIn("- [ ] Resolve the inconclusive contact search", exported["notes"])
        self.assertIn("- [ ] Call the county referral line", exported["notes"])


if __name__ == "__main__":
    unittest.main()
