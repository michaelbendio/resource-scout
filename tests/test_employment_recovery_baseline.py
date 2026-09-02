from __future__ import annotations

import json
import unittest
from pathlib import Path


BASELINE_PATH = (
    Path(__file__).parent.parent
    / "resource_research_agent"
    / "research_evidence"
    / "employment_recovery_baseline.json"
)
REPORT_PATH = (
    Path(__file__).parent.parent
    / "resource_research_agent"
    / "research_evidence"
    / "employment_v2_retrospective_report.json"
)


class EmploymentRecoveryBaselineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))

    def test_baseline_counts_are_fixed(self) -> None:
        self.assertEqual("resource-scout-0.43.1-build-9", self.baseline["baselineVersion"])
        self.assertEqual("chat-discovery-v1", self.baseline["playbookVersion"])
        self.assertEqual(
            {
                "mesa": (72, 63, 7, 54, 17),
                "provo": (63, 58, 3, 48, 15),
            },
            {
                location: (
                    value["submittedLeads"],
                    value["identityGroups"],
                    value["multiSourceGroups"],
                    value["curationCandidates"],
                    value["curatedResources"],
                )
                for location, value in self.baseline["locations"].items()
            },
        )

    def test_primary_and_secondary_targets_are_unique_and_complete(self) -> None:
        primary = self.baseline["primaryTargets"]
        secondary = self.baseline["secondaryTargets"]
        self.assertEqual(9, len(primary))
        self.assertEqual(2, len(secondary))
        self.assertEqual(6, sum(item["location"] == "Mesa" for item in primary))
        self.assertEqual(3, sum(item["location"] == "Provo" for item in primary))
        keys = [item["key"] for item in primary + secondary]
        self.assertEqual(len(keys), len(set(keys)))
        for target in primary + secondary:
            self.assertTrue(target["name"].strip())
            self.assertTrue(target["website"].startswith("https://"))
            self.assertTrue(target["branches"])

    def test_completed_retrospective_exceeds_the_approved_gate(self) -> None:
        report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
        self.assertEqual("complete", report["status"])
        self.assertEqual(
            {"available": 9, "met": True, "recovered": 9, "required": 8},
            report["threshold"],
        )
        self.assertEqual(
            {
                "ambiguous": 0,
                "credible-equivalent": 0,
                "exact": 11,
                "missed": 0,
                "parent-only": 0,
            },
            report["outcomeCounts"],
        )
        self.assertEqual(11, len(report["outcomes"]))
        self.assertEqual(
            {item["key"] for item in self.baseline["primaryTargets"]},
            {
                item["targetKey"]
                for item in report["outcomes"]
                if item["tier"] == "primary"
            },
        )
        for outcome in report["outcomes"]:
            self.assertEqual("exact", outcome["outcome"])
            self.assertTrue(outcome["candidateStableKey"].startswith("identity-"))
            self.assertTrue(outcome["researchFocusKeys"])
            self.assertTrue(outcome["evidence"])


if __name__ == "__main__":
    unittest.main()
