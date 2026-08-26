from __future__ import annotations

import unittest

from resource_research_agent.manual_discovery import build_manual_discovery_assignment
from resource_research_agent.playbooks import PLAYBOOKS, PLAYBOOK_LIBRARY_VERSION, playbook_for


EXPECTED_CATEGORIES = {
    "addiction", "children-pregnancy", "clothing-household", "disability",
    "domestic-violence", "education", "employment", "financial-assistance",
    "reentry-support", "food", "medical-dental-vision", "homeless-services",
    "housing", "id-recovery", "legal", "mental-health", "seniors",
    "transportation", "utilities-phone-internet", "veterans",
}


class DiscoveryGuidanceTests(unittest.TestCase):
    def test_every_category_has_compact_discovery_guidance(self) -> None:
        self.assertEqual("chat-discovery-v1", PLAYBOOK_LIBRARY_VERSION)
        self.assertEqual(EXPECTED_CATEGORIES, set(PLAYBOOKS))
        for category_id, playbook in PLAYBOOKS.items():
            with self.subTest(category=category_id):
                self.assertEqual(f"{category_id}.json", playbook.source)
                self.assertTrue(playbook.scope)
                self.assertTrue(playbook.exclusions)
                self.assertIn("Utah County", playbook.default_assignment)
                self.assertFalse(hasattr(playbook, "stages"))
                self.assertFalse(hasattr(playbook, "factual_fields"))

    def test_service_area_changes_without_changing_category_scope(self) -> None:
        original = playbook_for("food", "Food")
        mesa = playbook_for("food", "Food", service_area="Mesa, Arizona")
        self.assertIn("Mesa, Arizona", mesa.default_assignment)
        self.assertNotIn("Utah County", mesa.default_assignment)
        self.assertEqual(original.scope, mesa.scope)
        self.assertEqual(original.exclusions, mesa.exclusions)

    def test_unknown_category_has_safe_generic_guidance(self) -> None:
        playbook = playbook_for("pet-support", "Pet Support")
        self.assertEqual("generated fallback", playbook.source)
        self.assertTrue(playbook.scope)
        self.assertTrue(playbook.exclusions)

    def test_guidance_is_included_in_the_chat_assignment(self) -> None:
        playbook = playbook_for("clothing-household", "Clothing/Household", "Mesa")
        assignment = build_manual_discovery_assignment(
            category_label=playbook.label,
            service_area="Mesa",
            include=playbook.scope,
            exclude=playbook.exclusions,
        )
        self.assertIn("Include:", assignment)
        self.assertIn("Do not treat these as candidates:", assignment)
        self.assertIn(playbook.scope[0], assignment)
        self.assertIn(playbook.exclusions[0], assignment)


if __name__ == "__main__":
    unittest.main()
