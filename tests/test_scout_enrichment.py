from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from resource_research_agent.scout_enrichment import (
    CONNECT_GUIDANCE,
    ELIGIBILITY_GUIDANCE,
    SERVICES_GUIDANCE,
    build_scout_enriched_html,
    compose_information_text,
    extract_scout_seed,
    next_scout_enrichment_assignment,
    next_scout_enrichment_audit,
    next_scout_enrichment_reconciliation,
    prepare_scout_enrichment_project,
    save_scout_enrichment_result,
    save_scout_enrichment_audit_result,
    save_scout_enrichment_reconciliation_result,
)
from resource_research_agent.scout_enrichment_checkpoint import (
    export_scout_enrichment_checkpoint,
    import_scout_enrichment_checkpoint,
)
from resource_research_agent.storage import ResearchStore


class ScoutEnrichmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.store = ResearchStore(self.root / "research.sqlite3")
        self.resources = [
            {
                "id": "one", "name": "One Center", "description": "Original summary.",
                "informationText": "**Programs and services**\n- Food boxes\n\n  Keep spacing.",
                "website": "https://one.example", "categoryIds": ["food"],
                "types": ["Pantry"], "for": ["Families"],
            },
            {
                "id": "two", "name": "Two Center", "description": "Second summary.",
                "informationText": "**Access**\n- Area served: Mesa",
                "website": "https://two.example", "categoryIds": ["housing"],
                "types": ["Navigation"], "for": [],
            },
        ]
        seed = {
            "officeName": "Mesa TSO",
            "serviceArea": "Mesa and Maricopa County, Arizona",
            "categories": [{"id": "food", "name": "Food"}],
            "forGroups": ["Families"], "resources": self.resources,
        }
        self.source = self.root / "autoMesa.html"
        self.source.write_text(
            '<!doctype html>\n<meta name="scout-review-artifact-id" '
            'content="scout-review-original">\n'
            '<script id="seed-data" type="application/json">\n'
            + json.dumps(seed, ensure_ascii=False, indent=2)
            + "\n</script>\n<script>const untouched = true;</script>\n",
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _result(self, assignment: dict, suffix: str = "") -> dict:
        return {
            "resourceId": assignment["resourceId"],
            "assignmentSha256": assignment["assignmentSha256"],
            "servicesProvided": "Offers specific services" + suffix,
            "eligibilityRequirements": "Eligibility is confirmed" + suffix,
            "howToBestConnect": "Apply online or call first" + suffix,
            "evidenceSources": [{
                "title": "Official site", "url": "https://example.org/resource",
                "supports": "All three sections", "accessedOn": "2026-09-02",
            }],
        }

    def test_prepare_is_durable_and_contains_exact_template_guidance(self) -> None:
        first = prepare_scout_enrichment_project(self.store, self.source)
        second = prepare_scout_enrichment_project(self.store, self.source)
        self.assertEqual(first["id"], second["id"])
        self.assertEqual(first["resourceCount"], 2)
        self.assertEqual(first["progress"]["pending"], 2)

        assignment = next_scout_enrichment_assignment(self.store, first["id"])
        self.assertEqual(assignment["resourceId"], "one")
        self.assertEqual(
            [section["guidance"] for section in assignment["informationSections"]],
            [SERVICES_GUIDANCE, ELIGIBILITY_GUIDANCE, CONNECT_GUIDANCE],
        )
        self.assertEqual(
            assignment["preservation"]["originalInformationText"],
            self.resources[0]["informationText"],
        )

    def test_build_requires_completion_and_preserves_all_original_fields(self) -> None:
        summary = prepare_scout_enrichment_project(self.store, self.source)
        project_id = summary["id"]
        with self.assertRaisesRegex(ValueError, "incomplete"):
            build_scout_enriched_html(self.store, project_id)

        for suffix in (" one", " two"):
            assignment = next_scout_enrichment_assignment(self.store, project_id)
            save_scout_enrichment_result(
                self.store, project_id, self._result(assignment, suffix)
            )

        content = build_scout_enriched_html(self.store, project_id).decode("utf-8")
        enriched = extract_scout_seed(content)
        for original, resource, suffix in zip(
            self.resources, enriched["resources"], (" one", " two")
        ):
            for key, value in original.items():
                if key != "informationText":
                    self.assertEqual(resource[key], value)
            expected = compose_information_text({
                "servicesProvided": "Offers specific services" + suffix,
                "eligibilityRequirements": "Eligibility is confirmed" + suffix,
                "howToBestConnect": "Apply online or call first" + suffix,
            }, original["informationText"])
            self.assertEqual(resource["informationText"], expected)
            self.assertTrue(resource["informationText"].endswith(original["informationText"]))
        self.assertIn('content="scout-enriched-', content)
        self.assertNotIn('content="scout-review-original"', content)
        self.assertIn("const untouched = true", content)

    def test_validation_rejects_mismatched_or_empty_results(self) -> None:
        project = prepare_scout_enrichment_project(self.store, self.source)
        assignment = next_scout_enrichment_assignment(self.store, project["id"])
        result = self._result(assignment)
        result["assignmentSha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "assignmentSha256"):
            save_scout_enrichment_result(self.store, project["id"], result)
        result = self._result(assignment)
        result["servicesProvided"] = " "
        with self.assertRaisesRegex(ValueError, "Services Provided"):
            save_scout_enrichment_result(self.store, project["id"], result)

    def test_hybrid_rotates_four_ais_and_requires_codex_reconciliation(self) -> None:
        seed = extract_scout_seed(self.source.read_text(encoding="utf-8"))
        seed["resources"] = []
        for ordinal in range(4):
            resource = dict(self.resources[ordinal % 2])
            resource["id"] = f"crisis-{ordinal}"
            resource["name"] = f"Crisis Service {ordinal}"
            resource["informationText"] = f"Original finding {ordinal}"
            seed["resources"].append(resource)
        hybrid_source = self.root / "autoMesaHybrid.html"
        hybrid_source.write_text(
            '<meta name="scout-review-artifact-id" content="hybrid">\n'
            '<script id="seed-data" type="application/json">\n'
            + json.dumps(seed, ensure_ascii=False)
            + "\n</script>", encoding="utf-8",
        )
        project_id = prepare_scout_enrichment_project(
            self.store, hybrid_source
        )["id"]
        for ordinal in range(4):
            assignment = next_scout_enrichment_assignment(self.store, project_id)
            save_scout_enrichment_result(
                self.store, project_id, self._result(assignment, f" primary-{ordinal}")
            )
        project = self.store.get_scout_enrichment_project(project_id)
        self.assertEqual(
            [audit["researcher"] for audit in project["audits"]],
            ["ChatGPT", "Grok", "Perplexity", "Claude"],
        )
        self.assertEqual(project["status"], "in-progress")
        self.assertEqual(project["progress"]["auditsRequired"], 4)
        with self.assertRaisesRegex(ValueError, "incomplete"):
            build_scout_enriched_html(self.store, project_id)

        for researcher in ("ChatGPT", "Grok", "Perplexity", "Claude"):
            assignment = next_scout_enrichment_audit(
                self.store, project_id, researcher
            )
            self.assertEqual(assignment["researcher"], researcher)
            save_scout_enrichment_audit_result(self.store, project_id, {
                "resourceId": assignment["resourceId"], "researcher": researcher,
                "assignmentSha256": assignment["assignmentSha256"],
                "verdict": "revisions-needed", "issues": ["Clarify intake"],
                "suggestedReplacements": {
                    "servicesProvided": "Audited services",
                    "eligibilityRequirements": "Audited eligibility",
                    "howToBestConnect": "Audited intake",
                },
                "evidenceSources": [{
                    "title": "Audit source", "url": "https://audit.example",
                    "supports": "Correction", "accessedOn": "2026-09-02",
                }],
            })

        for ordinal in range(4):
            assignment = next_scout_enrichment_reconciliation(self.store, project_id)
            self.assertEqual(assignment["role"], "codex-audit-reconciliation")
            save_scout_enrichment_reconciliation_result(self.store, project_id, {
                "resourceId": assignment["resourceId"],
                "assignmentSha256": assignment["assignmentSha256"],
                "servicesProvided": f"Final services {ordinal}",
                "eligibilityRequirements": f"Final eligibility {ordinal}",
                "howToBestConnect": f"Final connection {ordinal}",
                "evidenceSources": assignment["primaryResult"]["evidenceSources"],
            })
        project = self.store.get_scout_enrichment_project(project_id)
        self.assertEqual(project["status"], "completed")
        self.assertEqual(project["progress"]["reconciled"], 4)
        enriched = extract_scout_seed(
            build_scout_enriched_html(self.store, project_id).decode("utf-8")
        )
        for ordinal, resource in enumerate(enriched["resources"]):
            self.assertIn(f"Final services {ordinal}", resource["informationText"])
            self.assertTrue(resource["informationText"].endswith(
                f"Original finding {ordinal}"
            ))

    def test_checkpoint_round_trip_preserves_project_without_source_file(self) -> None:
        project = prepare_scout_enrichment_project(self.store, self.source)
        checkpoint = self.root / "mesa-checkpoint.zip"
        exported = export_scout_enrichment_checkpoint(
            self.store, project["id"], checkpoint
        )
        self.assertTrue(checkpoint.exists())
        self.assertEqual(exported["projectId"], project["id"])
        self.source.unlink()
        imported_database = self.root / "mac" / "research-agent.sqlite3"
        imported = import_scout_enrichment_checkpoint(checkpoint, imported_database)
        self.assertEqual(imported["project"]["sourceSha256"], project["sourceSha256"])
        imported_store = ResearchStore(imported_database)
        restored = imported_store.get_scout_enrichment_project(
            project["id"], include_source=True
        )
        self.assertEqual(restored["resourceCount"], 2)
        self.assertIn("seed-data", restored["sourceHtml"])
        with self.assertRaisesRegex(ValueError, "refuses to overwrite"):
            import_scout_enrichment_checkpoint(checkpoint, imported_database)


if __name__ == "__main__":
    unittest.main()
