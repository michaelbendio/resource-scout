import copy
import json
import unittest

from resource_research_agent.starter_trial import (
    ARTIFACT_TYPE, compile_trial, digest, render_html, safe_url,
)


class StarterTrialTests(unittest.TestCase):
    def setUp(self):
        self.seed = {
            "categories": [{"id": c, "label": c.title()} for c in ("a", "b", "c")],
            "resources": [dict(id=f"resource-{i:04}", name=f"Provider {i}",
                               description="Documented local assistance.", informationText="Saved information.",
                               website="https://example.org/", categories=["a", "b", "c"])
                          for i in range(8)],
        }
        self.state = {"resourceOverrides": [], "addedResources": [], "deletedResourceIds": []}
        self.seed_bytes = json.dumps(self.seed).encode()
        self.state_bytes = json.dumps(self.state).encode()
        self.proposal = dict(schemaVersion=1, evaluationOnly=True,
                             seedSha256=digest(self.seed_bytes), stateSha256=digest(self.state_bytes),
                             office={"slug": "test"}, notes=["Evaluation only"], categories=[])
        for cid in ("a", "b", "c"):
            self.proposal["categories"].append(dict(
                categoryId=cid, rationale="Distinct access routes", gaps="Capacity uncertain",
                members=[dict(ref=f"resource-{i:04}", label=f"Provider {i}",
                              contribution="Adds documented help", limitation="Confirm intake",
                              evidence={"field": "description", "text": "local assistance"})
                         for i in range(7)],
                notSelected={"resource-0007": "Another alternative remains available."}))

    def compile(self):
        return compile_trial(self.seed_bytes, self.state_bytes, self.proposal)

    def test_complete_evaluation_reuses_ids_without_mutation_or_approval(self):
        before = copy.deepcopy(self.proposal)
        result = self.compile()
        self.assertEqual(result["artifactType"], ARTIFACT_TYPE)
        self.assertNotEqual(result["artifactType"], "scout-prepared-resources")
        self.assertTrue(result["evaluationOnly"])
        self.assertEqual((result["uniqueResources"], result["categoryEntries"], result["assessedMemberships"]), (7, 21, 24))
        self.assertEqual(result["starterSets"][0]["members"][0]["resourceId"], "resource-0000")
        self.assertEqual(self.proposal, before)
        self.assertNotIn("curated", result["starterSets"][0]["members"][0]["resource"])
        self.assertEqual(result, self.compile())

    def test_changed_source_or_browser_state_requires_new_assessment(self):
        for seed, state in ((self.seed_bytes + b" ", self.state_bytes),
                            (self.seed_bytes, self.state_bytes + b" ")):
            with self.assertRaisesRegex(ValueError, "Stale trial"):
                compile_trial(seed, state, self.proposal)

    def test_suppressed_resource_cannot_be_selected(self):
        self.state["deletedResourceIds"] = ["resource-0000"]
        self.state_bytes = json.dumps(self.state).encode()
        self.proposal["stateSha256"] = digest(self.state_bytes)
        with self.assertRaisesRegex(ValueError, "suppressed"):
            self.compile()

    def test_evidence_is_checked_after_browser_override(self):
        self.state["resourceOverrides"] = [{"id": "resource-0000", "description": "Human corrected this service."}]
        self.state_bytes = json.dumps(self.state).encode()
        self.proposal["stateSha256"] = digest(self.state_bytes)
        with self.assertRaisesRegex(ValueError, "Evidence does not occur"):
            self.compile()

    def test_duplicate_and_unassessed_memberships_are_rejected(self):
        original = copy.deepcopy(self.proposal)
        self.proposal["categories"][0]["members"][1] = self.proposal["categories"][0]["members"][0]
        with self.assertRaisesRegex(ValueError, "repeated selection"):
            self.compile()
        self.proposal = original
        self.proposal["categories"][0]["notSelected"] = {}
        with self.assertRaisesRegex(ValueError, "Incomplete assessment"):
            self.compile()

    def test_out_of_category_selection_is_rejected(self):
        self.seed["resources"][0]["categories"] = ["b", "c"]
        self.seed_bytes = json.dumps(self.seed).encode()
        self.proposal["seedSha256"] = digest(self.seed_bytes)
        with self.assertRaisesRegex(ValueError, "Invalid"):
            self.compile()

    def test_ambiguous_short_reference_is_rejected(self):
        self.proposal["categories"][0]["members"][0]["ref"] = "resource"
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            self.compile()

    def test_human_removed_category_is_not_resurrected(self):
        self.state["categoriesOverride"] = self.seed["categories"][1:]
        self.state_bytes = json.dumps(self.state).encode()
        self.proposal["stateSha256"] = digest(self.state_bytes)
        with self.assertRaisesRegex(ValueError, "Unknown or duplicate category"):
            self.compile()

    def test_unassessed_browser_additions_block_compilation(self):
        self.state["addedResources"] = [{"id": "new-human-record"}]
        self.state_bytes = json.dumps(self.state).encode()
        self.proposal["stateSha256"] = digest(self.state_bytes)
        with self.assertRaisesRegex(ValueError, "Review added browser resources"):
            self.compile()

    def test_html_escapes_source_content_and_blocks_executable_links(self):
        result = self.compile()
        member = result["starterSets"][0]["members"][0]
        member["resource"]["informationText"] = "<script>alert('source')</script>"
        member["resource"]["website"] = "javascript:alert(1)"
        html = render_html(result)
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertNotIn("javascript:", html)
        self.assertEqual(safe_url("file:///private/file"), "")


if __name__ == "__main__":
    unittest.main()
