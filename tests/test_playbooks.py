from __future__ import annotations

import unittest

from resource_research_agent.playbooks import (
    PLAYBOOKS,
    PLAYBOOK_LIBRARY_VERSION,
    output_schema,
    playbook_for,
)


EXPECTED_CATEGORIES = {
    "addiction",
    "children-pregnancy",
    "clothing-household",
    "disability",
    "domestic-violence",
    "education",
    "employment",
    "financial-assistance",
    "reentry-support",
    "food",
    "medical-dental-vision",
    "homeless-services",
    "housing",
    "id-recovery",
    "legal",
    "mental-health",
    "seniors",
    "transportation",
    "utilities-phone-internet",
    "veterans",
}


class PlaybookLibraryTests(unittest.TestCase):
    def test_every_package_category_has_a_human_reviewable_playbook(self) -> None:
        self.assertEqual("1.2.0", PLAYBOOK_LIBRARY_VERSION)
        self.assertEqual(EXPECTED_CATEGORIES, set(PLAYBOOKS))
        for category_id, playbook in PLAYBOOKS.items():
            with self.subTest(category=category_id):
                self.assertEqual(f"{category_id}.json", playbook.source)
                self.assertEqual(4, len(playbook.stages))
                self.assertTrue(playbook.scope)
                self.assertTrue(playbook.exclusions)
                self.assertTrue(playbook.verification_questions)
                self.assertIn("geography", playbook.factual_fields)
                self.assertEqual(len(set(playbook.factual_fields)), len(playbook.factual_fields))
                self.assertEqual(
                    [
                        "identity-and-contact", "services-provided",
                        "eligibility-requirements", "what-to-expect",
                        "how-to-best-connect", "additional-notes",
                    ],
                    [item["key"] for item in playbook.resource_gathering_requirements],
                )
                self.assertIn("Utah County", playbook.default_assignment)

    def test_clothing_playbook_rejects_ordinary_retail_search_results(self) -> None:
        playbook = playbook_for("clothing-household", "Clothing/Household")
        self.assertIn("ordinary retail", playbook.default_assignment.lower())
        self.assertTrue(any("ordinary clothing" in item.lower() for item in playbook.exclusions))
        self.assertEqual("clothing-access", playbook.stages[0]["key"])
        self.assertEqual("household-goods", playbook.stages[1]["key"])

    def test_service_area_can_be_rendered_without_rewriting_category_guidance(self) -> None:
        playbook = playbook_for("food", "Food", service_area="Bernalillo County")
        self.assertIn("Bernalillo County", playbook.default_assignment)
        self.assertNotIn("Utah County", playbook.default_assignment)
        self.assertEqual(PLAYBOOKS["food"].stages, playbook.stages)

    def test_unknown_category_retains_a_safe_generated_fallback(self) -> None:
        playbook = playbook_for("pet-support", "Pet Support")
        self.assertEqual("generated fallback", playbook.source)
        self.assertEqual(4, len(playbook.stages))
        self.assertTrue(playbook.exclusions)
        self.assertEqual(
            PLAYBOOKS["housing"].resource_gathering_requirements,
            playbook.resource_gathering_requirements,
        )

    def test_output_schema_has_curator_ready_gathering_fields(self) -> None:
        candidate = output_schema("Food")["candidates"][0]
        for field in (
            "additionalAddresses", "additionalPhoneNumbers", "servicesProvided",
            "eligibility", "whatToExpect", "howToBestConnect", "additionalNotes",
        ):
            self.assertIn(field, candidate)

    def test_category_specific_factual_fields_are_playbook_data(self) -> None:
        housing = playbook_for("housing")
        food = playbook_for("food")
        self.assertIn("petPolicy", housing.factual_fields)
        self.assertNotIn("petPolicy", food.factual_fields)
        self.assertIn("petPolicy", housing.supplementary_fields)
        self.assertNotIn("petPolicy", food.supplementary_fields)
        self.assertIn("petPolicy", output_schema("Housing")["candidates"][0])
        self.assertNotIn("petPolicy", output_schema("Food")["candidates"][0])
        self.assertEqual(
            set(housing.factual_fields) - {"petPolicy"}, set(food.factual_fields)
        )


if __name__ == "__main__":
    unittest.main()
