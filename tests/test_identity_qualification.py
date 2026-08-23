from __future__ import annotations

import unittest

from resource_research_agent.identity_qualification import (
    apply_identity_qualification_manifest,
    identity_qualification_template,
)
from resource_research_agent.optimization import candidate_identity_key
from resource_research_agent.optimization_runtime import OptimizationRuntimeError


class IdentityQualificationManifestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.identity = {
            "organization": "Example Provider",
            "program": "Example Shelter",
            "stageKey": "urgent-access",
        }
        self.key = candidate_identity_key(
            self.identity["organization"], self.identity["program"]
        )
        self.review = {
            "schemaVersion": 2,
            "searchCacheSha256": "a" * 64,
            "decisions": {
                "https://example.org/program": {
                    "disposition": "candidate",
                    "reason": "Direct page",
                    "identity": dict(self.identity),
                },
                "https://example.gov/referral": {
                    "disposition": "candidate",
                    "reason": "Authoritative referral",
                    "identity": dict(self.identity),
                },
            },
        }
        self.manifest = {
            "schemaVersion": 1,
            "candidateQualificationPolicyVersion": "candidate-qualification-gates-v2",
            "searchCacheSha256": "a" * 64,
            "identities": {
                self.key: {
                    "organization": "Example Provider",
                    "program": "Example Shelter",
                    "boundaryState": "resolved",
                    "candidateRole": "direct-program",
                    "geographyState": "confirmed-target",
                    "categoryState": "confirmed",
                    "actionabilityState": "actionable",
                    "currentStatusState": "current",
                    "evidenceReadiness": "current-corroborated",
                    "reviewReason": "Current direct and government evidence agree.",
                    "evidenceUrls": [
                        "https://example.org/program/",
                        "https://example.gov/referral",
                    ],
                }
            },
        }

    def test_one_decision_is_applied_to_every_identity_occurrence(self) -> None:
        result = apply_identity_qualification_manifest(self.review, self.manifest)
        values = [
            record["identity"] for record in result["decisions"].values()
        ]
        self.assertEqual({"direct-program"}, {value["candidateRole"] for value in values})
        self.assertEqual({"confirmed"}, {value["categoryState"] for value in values})
        self.assertEqual(
            ["https://example.gov/referral", "https://example.org/program"],
            values[0]["qualificationEvidenceUrls"],
        )
        replay = apply_identity_qualification_manifest(result, self.manifest)
        self.assertEqual(1, len(replay["qualificationApplications"]))

    def test_template_deduplicates_identity_and_remains_explicitly_incomplete(self) -> None:
        template = identity_qualification_template(self.review)
        self.assertEqual([self.key], list(template["identities"]))
        entry = template["identities"][self.key]
        self.assertEqual("", entry["candidateRole"])
        self.assertEqual(
            ["https://example.org/program", "https://example.gov/referral"],
            entry["evidenceUrls"],
        )
        with self.assertRaisesRegex(OptimizationRuntimeError, "lacks reason or evidence"):
            apply_identity_qualification_manifest(self.review, template)

    def test_manifest_must_exactly_cover_reviewed_identities(self) -> None:
        self.manifest["identities"] = {}
        with self.assertRaisesRegex(OptimizationRuntimeError, "no identity decisions"):
            apply_identity_qualification_manifest(self.review, self.manifest)

    def test_manifest_cannot_relabel_an_identity(self) -> None:
        self.manifest["identities"][self.key]["program"] = "Different Program"
        with self.assertRaisesRegex(OptimizationRuntimeError, "key does not match"):
            apply_identity_qualification_manifest(self.review, self.manifest)

    def test_unknown_pet_policy_is_not_part_of_qualification_manifest(self) -> None:
        result = apply_identity_qualification_manifest(self.review, self.manifest)
        self.assertNotIn(
            "petPolicy",
            result["decisions"]["https://example.org/program"]["identity"],
        )


if __name__ == "__main__":
    unittest.main()
