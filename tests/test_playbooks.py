from __future__ import annotations

import unittest

from resource_research_agent.playbooks import (
    PLAYBOOKS,
    PLAYBOOK_LIBRARY_VERSION,
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
        self.assertEqual("1.0.0", PLAYBOOK_LIBRARY_VERSION)
        self.assertEqual(EXPECTED_CATEGORIES, set(PLAYBOOKS))
        for category_id, playbook in PLAYBOOKS.items():
            with self.subTest(category=category_id):
                self.assertEqual(f"{category_id}.json", playbook.source)
                self.assertEqual(4, len(playbook.stages))
                self.assertTrue(playbook.scope)
                self.assertTrue(playbook.exclusions)
                self.assertTrue(playbook.verification_questions)
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


if __name__ == "__main__":
    unittest.main()
