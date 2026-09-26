import unittest
from resource_research_agent.preparation_contract import (
    INFORMATION_HEADINGS, information_sections, migrate_reviewed_information, preparation_instructions,
)


class PreparationContractTests(unittest.TestCase):
    def test_migration_preserves_every_existing_section_and_adds_authored_text(self):
        resource = {"informationText": "**Eligibility Requirements**\n\nEligible applicants.\n\n**How to Best Connect**\n\nCall intake.\n\n**Access**\n\nTuesday only; confirm access.\n\n**Important Information to Know**\n\nFunding uncertain. https://example.org/"}
        result = migrate_reviewed_information(resource, services="Prepared meals.", population="The saved evidence identifies older adults.")
        sections = information_sections(result)
        self.assertEqual(tuple(sections), INFORMATION_HEADINGS)
        for value in ("Eligible applicants.", "Call intake.", "Tuesday only; confirm access.", "Funding uncertain. https://example.org/"):
            self.assertIn(value, result)
        self.assertIn("Tuesday only", sections["How to Best Connect"])
        self.assertNotIn("**Access**", result)

    def test_reject_empty_misordered_or_inline_headings(self):
        for text in ("**Services Offered** inline", "", "**Population Served**\n\nAll people."):
            with self.assertRaises(ValueError): information_sections(text)

    def test_policy_preserves_reserve_and_disallows_ai_verification(self):
        instructions = " ".join(preparation_instructions())
        self.assertIn("including useful reserve options", instructions)
        self.assertIn("verifiedOn must be null", instructions)
        self.assertIn("registry", instructions)


if __name__ == "__main__": unittest.main()
