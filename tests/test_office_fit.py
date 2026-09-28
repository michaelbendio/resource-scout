"""The four office-fit rules reach every researcher, the curator and the reviewer."""
import unittest

from resource_research_agent import office_pipeline, pairwise_runner, preparation_contract
from resource_research_agent.office_fit import OFFICE_FIT_RULES


class OfficeFitRuleTests(unittest.TestCase):
    def assert_all_rules(self, text):
        for rule in OFFICE_FIT_RULES:
            self.assertIn(rule, text)

    def test_every_researcher_gets_the_rules(self):
        for researcher, role in [("Codex", "primary"), ("DeepSeek", "challenger"), ("Grok", "challenger"),
                                 ("Claude", "challenger")]:
            with self.subTest(researcher=researcher):
                self.assert_all_rules(pairwise_runner._research_prompt("ASSIGNMENT", researcher, role))

    def test_the_rules_come_before_the_assignment(self):
        prompt = pairwise_runner._research_prompt("ASSIGNMENT", "Codex", "primary")
        self.assertLess(prompt.index(OFFICE_FIT_RULES[0]), prompt.index("ASSIGNMENT"))

    def test_curation_gets_the_rules(self):
        self.assert_all_rules("\n".join(preparation_contract.preparation_instructions()))

    def test_review_gets_the_rules(self):
        config = dict(runDirectory="/tmp/run", authorization="ok", repository="/repo", database="/db", importId=1)
        self.assert_all_rules(office_pipeline.review_prompt(config, 1, 1))

    def test_curation_no_longer_keeps_everything(self):
        text = "\n".join(preparation_contract.preparation_instructions())
        self.assertNotIn("Do not minimize the collection", text)
        self.assertNotIn("including useful reserve options", text)
        self.assertIn("Retain only", text)

    def test_review_keeps_curated_flags_but_not_every_resource(self):
        config = dict(runDirectory="/tmp/run", authorization="ok", repository="/repo", database="/db", importId=1)
        prompt = office_pipeline.review_prompt(config, 1, 1)
        self.assertNotIn("Preserve all resources", prompt)
        self.assertIn("human Curated flags", prompt)

    def test_the_rules_name_no_office(self):
        for rule in OFFICE_FIT_RULES:
            for place in ["Mesa", "Provo", "Las Vegas", "Albuquerque", "Arizona", "Utah"]:
                self.assertNotIn(place, rule)

    def test_the_research_prompt_version_changed(self):
        self.assertNotEqual(pairwise_runner.RESEARCH_PROMPT_VERSION, "scout-research-2026-09-18-v4")


if __name__ == "__main__":
    unittest.main()
