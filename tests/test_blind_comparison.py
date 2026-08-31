from __future__ import annotations

import hashlib
import json
import tempfile
import threading
import unittest
import urllib.request
import zipfile
from pathlib import Path
from unittest.mock import patch

from resource_research_agent.blind_comparison import (
    blind_comparison_view,
    build_blind_review_assignment,
    close_blind_codex_arm,
    complete_blind_comparison,
    prepare_blind_comparison,
    reveal_blind_shadows,
    save_blind_review_result,
)
from resource_research_agent.focused_research import (
    next_focused_research_assignment,
    prepare_focused_gap_pass,
    save_focused_research_result,
)
from resource_research_agent.importer import ResourcePackageImporter
from resource_research_agent.manual_consolidation import (
    consolidate_manual_discovery,
    finish_manual_discovery,
)
from resource_research_agent.scout_curation import (
    next_scout_curation_assignment,
    prepare_scout_curation_job,
    save_scout_curation_result,
)
from resource_research_agent.server import ResearchHTTPServer
from resource_research_agent.storage import ResearchStore


def assignment_sha(value: dict) -> str:
    copied = dict(value)
    copied.pop("assignmentSha256", None)
    return hashlib.sha256(json.dumps(
        copied, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")).hexdigest()


class BlindComparisonTests(unittest.TestCase):
    categories = (
        ("housing", "Housing"),
        ("medical-dental-vision", "Medical, Dental, Vision"),
        ("transportation", "Transportation"),
    )

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.store = ResearchStore(self.root / "research.sqlite3")
        package = self.root / "provo-resource-package.zip"
        with zipfile.ZipFile(package, "w") as archive:
            archive.writestr("tso-resources.json", json.dumps({
                "resourcePackageSchemaVersion": 3,
                "packageVersion": 1,
                "officeName": "Provo TSO",
                "serviceArea": "Utah County, Utah",
                "categories": [
                    {"id": category_id, "name": label, "filters": []}
                    for category_id, label in self.categories
                ] + [{"id": "miscellaneous", "name": "Miscellaneous", "filters": []}],
                "forGroups": [],
                "resources": [],
            }))
        imported = ResourcePackageImporter("Housing").read(package)
        self.import_id = self.store.save_import(imported)
        self.shadow_runs = {
            category_id: self.completed_shadow_run(category_id, label)
            for category_id, label in self.categories
        }
        curation = prepare_scout_curation_job(self.store, self.import_id)
        while assignment := next_scout_curation_assignment(self.store, curation["id"]):
            candidate_ids = [str(item["id"]) for item in assignment["candidates"]]
            resource_id = "curated-" + assignment["category"]["id"]
            result = {
                "scoutCurationResultSchemaVersion": 1,
                "assignmentSha256": assignment["assignmentSha256"],
                "categoryId": assignment["category"]["id"],
                "resources": [{
                    "id": resource_id,
                    "name": assignment["category"]["label"] + " Resource",
                    "description": "Direct practical service.",
                    "informationText": "Verify access before visiting.",
                    "categories": [assignment["category"]["id"]],
                    "categoryFilters": {},
                    "forGroups": [],
                    "candidateIds": candidate_ids,
                }],
                "candidateDispositions": [
                    {
                        "candidateId": candidate_id,
                        "disposition": "curated",
                        "resourceIds": [resource_id],
                        "reason": "",
                    }
                    for candidate_id in candidate_ids
                ],
            }
            save_scout_curation_result(
                self.store, curation["id"], assignment["category"]["id"], result
            )
        curation = self.store.get_scout_curation_job(curation["id"])
        summary = self.store.import_summary(self.import_id)
        self.fixture = {
            "schemaVersion": 1,
            "experimentMode": "blind-comparison-v1",
            "location": {
                "importId": self.import_id,
                "officeName": summary["officeName"],
                "serviceArea": summary["serviceArea"],
                "sourceName": summary["sourceName"],
                "sourceSha256": summary["sourceSha256"],
                "contentSha256": summary["contentSha256"],
            },
            "curation": {
                "jobId": curation["id"],
                "assignmentVersion": curation["assignmentVersion"],
            },
            "subscriptionContext": {
                source: {"monthlyUsd": 20, "decisionRole": "test"}
                for source in ("ChatGPT", "Grok", "Claude", "Perplexity")
            },
            "heldOutCategories": [],
        }
        for category_id, label in self.categories:
            category = next(
                item for item in curation["categories"]
                if item["categoryId"] == category_id
            )
            seal = self.store.manual_contribution_seal(self.shadow_runs[category_id])
            self.fixture["heldOutCategories"].append({
                "categoryId": category_id,
                "categoryLabel": label,
                "researchCharacteristic": "test characteristic",
                "shadowRunId": self.shadow_runs[category_id],
                "curationResultSha256": category["resultSha256"],
                "contributions": [{
                    "id": item["id"],
                    "source": item["source"],
                    "leadCount": item["leadCount"],
                    "rawSha256": item["rawSha256"],
                } for item in seal],
            })
        self.fixture_path = self.root / "blind-fixture.json"
        self.fixture_path.write_text(json.dumps(self.fixture), encoding="utf-8")
        self.fixture_patch = patch(
            "resource_research_agent.blind_comparison.BLIND_FIXTURE_PATH",
            self.fixture_path,
        )
        self.fixture_patch.start()

    def tearDown(self) -> None:
        self.fixture_patch.stop()
        self.temporary.cleanup()

    def completed_shadow_run(self, category_id: str, label: str) -> int:
        run_id = self.store.create_manual_discovery_run(
            f"Find {label}",
            {"researchContext": {"mode": "package"}},
            self.import_id,
            target_category_id=category_id,
            target_category_label=label,
        )
        for position, source in enumerate(("ChatGPT", "Grok", "Claude", "Perplexity"), 1):
            self.store.save_manual_contribution(run_id, source, json.dumps({
                "leads": [{
                    "organization": f"Shadow {label} {source}",
                    "program": f"Shadow program {position}",
                    "website": f"https://shadow-{category_id}-{position}.example.org/program",
                    "phone": "801-555-0100",
                    "address": "1 Main Street, Provo, UT",
                    "leadType": "program",
                    "locationOrServiceArea": "Utah County",
                    "whyRelevant": f"Direct {label} help.",
                    "uncertainty": "Confirm hours.",
                }]
            }))
        consolidate_manual_discovery(self.store, run_id)
        finish_manual_discovery(self.store, run_id)
        return run_id

    def complete_codex_arm(self, study: dict) -> dict:
        for category in study["categories"]:
            job_id = category["focusedJobId"]
            pass_number = 0
            while assignment := next_focused_research_assignment(self.store, job_id):
                pass_number += 1
                self.assertNotIn("Shadow ", assignment["assignment"])
                save_focused_research_result(
                    self.store,
                    job_id,
                    assignment["focusKey"],
                    json.dumps({"leads": [{
                        "organization": f"Codex {category['categoryLabel']} {pass_number}",
                        "program": "Direct program",
                        "website": f"https://codex-{category['categoryId']}-{pass_number}.example.org/program",
                        "phone": "801-555-0199",
                        "address": "2 Center Street, Provo, UT",
                        "leadType": "program",
                        "locationOrServiceArea": "Utah County",
                        "whyRelevant": "Direct practical service.",
                        "uncertainty": "Confirm schedule.",
                    }]}),
                )
                job = self.store.get_focused_research_job(job_id)
                if all(item["status"] == "completed" for item in job["passes"]):
                    break
            prepare_focused_gap_pass(self.store, job_id)
            gap = next_focused_research_assignment(self.store, job_id)
            save_focused_research_result(
                self.store,
                job_id,
                gap["focusKey"],
                json.dumps({"leads": []}),
            )
        return close_blind_codex_arm(self.store, study["id"])

    def test_shadows_remain_sealed_until_every_codex_category_closes(self) -> None:
        study = prepare_blind_comparison(self.store)
        self.assertEqual("researching", study["status"])
        self.assertTrue(all(item["shadow"]["sealed"] for item in study["categories"]))
        self.assertTrue(all(not item["shadow"]["revealed"] for item in study["categories"]))
        self.assertNotIn("fixture", study)
        encoded = json.dumps(study)
        self.assertNotIn("Shadow Housing", encoded)
        with self.assertRaisesRegex(ValueError, "Close every Codex"):
            reveal_blind_shadows(self.store, study["id"])

        closed = self.complete_codex_arm(study)
        self.assertEqual("codex-closed", closed["status"])
        revealed = reveal_blind_shadows(self.store, study["id"])
        self.assertEqual("revealed", revealed["status"])
        self.assertTrue(all(item["shadow"]["revealed"] for item in revealed["categories"]))

    def test_reveal_rejects_changed_shadow_response(self) -> None:
        study = prepare_blind_comparison(self.store)
        self.complete_codex_arm(study)
        contribution_id = self.fixture["heldOutCategories"][0]["contributions"][0]["id"]
        with self.store.connect() as connection:
            connection.execute(
                "UPDATE manual_discovery_contributions SET raw_sha256 = ? WHERE id = ?",
                ("0" * 64, contribution_id),
            )
        with self.assertRaisesRegex(ValueError, "responses changed"):
            reveal_blind_shadows(self.store, study["id"])

    def test_source_hidden_review_and_report_are_deterministic(self) -> None:
        study = prepare_blind_comparison(self.store)
        self.complete_codex_arm(study)
        reveal_blind_shadows(self.store, study["id"])
        for category_id, _label in self.categories:
            assignment = build_blind_review_assignment(
                self.store, study["id"], category_id
            )
            self.assertTrue(assignment["sourceAttributionHidden"])
            self.assertEqual(assignment["assignmentSha256"], assignment_sha(assignment))
            self.assertFalse(any("sources" in item for item in assignment["candidates"]))
            result = {
                "assignmentSha256": assignment["assignmentSha256"],
                "categoryId": category_id,
                "dispositions": [
                    {
                        "candidateId": item["id"],
                        "outcome": "curated",
                        "duplicateOf": "",
                        "reason": "",
                        "evidence": ["Direct service in the test fixture."],
                    }
                    for item in assignment["candidates"]
                ],
                "reviewEffort": {
                    "durationSeconds": 60,
                    "editCount": 0,
                    "adjudicationCount": 0,
                },
            }
            save_blind_review_result(
                self.store, study["id"], category_id, result
            )
        completed = complete_blind_comparison(self.store, study["id"])
        self.assertEqual("completed", completed["status"])
        self.assertEqual(3, completed["report"]["heldOutCategoryCount"])
        self.assertGreater(
            completed["report"]["aggregateComparison"]["curatedUnionCount"], 0
        )
        self.assertNotIn("reportSha256", completed["report"])
        self.assertEqual(completed["reportSha256"], hashlib.sha256(json.dumps(
            completed["report"],
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")).hexdigest())
        repeated = complete_blind_comparison(self.store, study["id"])
        self.assertEqual(completed["reportSha256"], repeated["reportSha256"])

    def test_rejects_incomplete_or_mismatched_review_results(self) -> None:
        study = prepare_blind_comparison(self.store)
        self.complete_codex_arm(study)
        reveal_blind_shadows(self.store, study["id"])
        assignment = build_blind_review_assignment(self.store, study["id"], "housing")
        with self.assertRaisesRegex(ValueError, "cover every candidate"):
            save_blind_review_result(self.store, study["id"], "housing", {
                "assignmentSha256": assignment["assignmentSha256"],
                "categoryId": "housing",
                "dispositions": [],
                "reviewEffort": {},
            })
        dispositions = [
            {
                "candidateId": item["id"],
                "outcome": "curated",
                "reason": "",
                "evidence": [],
            }
            for item in assignment["candidates"]
        ]
        dispositions[0]["outcome"] = "duplicate"
        dispositions[0]["reason"] = "Same program."
        with self.assertRaisesRegex(ValueError, "needs another candidate"):
            save_blind_review_result(self.store, study["id"], "housing", {
                "assignmentSha256": assignment["assignmentSha256"],
                "categoryId": "housing",
                "dispositions": dispositions,
                "reviewEffort": {},
            })

    def test_http_contract_runs_the_sealed_comparison_to_report(self) -> None:
        web_dir = Path(__file__).resolve().parent.parent / "web"
        server = ResearchHTTPServer(("127.0.0.1", 0), self.store, web_dir)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_address[1]}"

        def request(path: str, method: str = "GET", payload: dict | None = None) -> dict:
            data = json.dumps(payload).encode("utf-8") if payload is not None else None
            req = urllib.request.Request(
                base + path,
                data=data,
                headers={"Content-Type": "application/json"} if data else {},
                method=method,
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                return json.loads(response.read())

        try:
            study = request("/api/blind-comparisons", "POST", {})
            self.assertEqual("researching", study["status"])
            self.complete_codex_arm(study)
            revealed = request(
                f"/api/blind-comparisons/{study['id']}/reveal", "POST", {}
            )
            self.assertEqual("revealed", revealed["status"])
            for category_id, _label in self.categories:
                assignment = request(
                    f"/api/blind-comparisons/{study['id']}/review-assignment",
                    "POST",
                    {"categoryId": category_id},
                )
                request(
                    f"/api/blind-comparisons/{study['id']}/review-result",
                    "POST",
                    {
                        "categoryId": category_id,
                        "result": {
                            "assignmentSha256": assignment["assignmentSha256"],
                            "categoryId": category_id,
                            "dispositions": [{
                                "candidateId": item["id"],
                                "outcome": "curated",
                                "reason": "",
                                "evidence": ["Direct test service."],
                            } for item in assignment["candidates"]],
                            "reviewEffort": {
                                "durationSeconds": 1,
                                "editCount": 0,
                                "adjudicationCount": 0,
                            },
                        },
                    },
                )
            completed = request(
                f"/api/blind-comparisons/{study['id']}/report", "POST", {}
            )
            self.assertEqual("completed", completed["status"])
            listed = request("/api/blind-comparisons")["studies"]
            self.assertEqual([study["id"]], [item["id"] for item in listed])
            detailed = request(f"/api/blind-comparisons/{study['id']}")
            self.assertEqual(completed["reportSha256"], detailed["reportSha256"])
            progress = request(f"/api/scout-progress?importId={self.import_id}")
            self.assertEqual("blind-comparison-complete", progress["phase"])
            self.assertEqual(3, progress["blindComparison"]["reviewedCategories"])
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
