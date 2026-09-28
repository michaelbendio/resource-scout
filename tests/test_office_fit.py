"""The four office-fit rules reach every researcher, the curator and the reviewer."""
import unittest

from pathlib import Path

from resource_research_agent import (office_pipeline, pairwise_challenge, pairwise_runner, preparation_contract,
                                     scout_curation, scout_curation_runner)
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

    def test_phone_and_online_resources_count(self):
        # Michael, 28 September 2026: "Phone and online resources count."
        self.assertIn("phone or online", OFFICE_FIT_RULES[0])
        self.assertIn("passes", OFFICE_FIT_RULES[0].split("phone or online", 1)[1][:200])

    def test_default_curation_gets_the_rules(self):
        # The schema-2 writing contract, used by office_pipeline and the server.
        self.assert_all_rules("\n".join(scout_curation.curation_instructions()))

    def test_old_curation_jobs_are_not_reused_without_the_rules(self):
        self.assertIn("office-fit", scout_curation.SCOUT_CURATION_ASSIGNMENT_VERSION)
        self.assertIn("office-fit", preparation_contract.ASSIGNMENT_VERSION)
        self.assertIn(preparation_contract.ASSIGNMENT_VERSION, preparation_contract.PREPARED_ASSIGNMENT_VERSIONS)

    def test_prepared_curation_no_longer_aims_to_prepare_everything(self):
        prepared = preparation_contract.prepared_assignment({"outputContract": {"resources": [{}]}})
        objective = prepared["curationPolicy"]["objective"]
        self.assertNotIn("every distinct supported resource", objective)
        self.assertIn("office-fit", objective)
        instructions = "\n".join(prepared["instructions"])
        self.assertNotIn("Keep useful unresolved leads for administrators", instructions)

    def test_curation_worker_does_not_invite_keeping_more(self):
        source = Path(scout_curation_runner.__file__).read_text()
        self.assertNotIn("unresolved useful leads may be retained", source)
        self.assertNotIn("do not omit a duplicate when it contributes", source)

    def test_review_no_longer_preserves_every_result(self):
        config = dict(runDirectory="/tmp/run", authorization="ok", repository="/repo", database="/db", importId=1)
        prompt = office_pipeline.review_prompt(config, 1, 1)
        self.assertNotIn("Preserve every source, resource identity, provenance and original result", prompt)

    def test_challengers_are_not_sent_looking_for_referral_pathways(self):
        from resource_research_agent import codex_first_research
        self.assertNotIn("referral pathways", Path(codex_first_research.__file__).read_text())

    def test_the_manual_challenger_gets_the_rules(self):
        self.assert_all_rules(pairwise_challenge.with_office_fit("ASSIGNMENT"))
        self.assertTrue(pairwise_challenge.with_office_fit("ASSIGNMENT").rstrip().endswith("ASSIGNMENT"))

    def test_the_rules_name_no_office(self):
        for rule in OFFICE_FIT_RULES:
            for place in ["Mesa", "Provo", "Las Vegas", "Albuquerque", "Arizona", "Utah"]:
                self.assertNotIn(place, rule)

    def test_the_research_prompt_version_changed(self):
        self.assertNotEqual(pairwise_runner.RESEARCH_PROMPT_VERSION, "scout-research-2026-09-18-v4")


if __name__ == "__main__":
    unittest.main()
