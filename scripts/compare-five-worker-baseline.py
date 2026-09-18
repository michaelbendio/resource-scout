#!/usr/bin/env python3
"""Compare saved submissions, including nonblocking shadow evidence; no workers."""
from __future__ import annotations

import argparse
import collections
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import statistics

spec = importlib.util.spec_from_file_location("pairwise_metrics", Path(__file__).with_name("analyze-pairwise-experiment.py"))
metrics = importlib.util.module_from_spec(spec)
spec.loader.exec_module(metrics)


def read(path: Path, include_shadow: bool):
    result, leads = metrics.read_condition(path, 6)
    if not result["allSelectedCategoriesComplete"]:
        raise ValueError("All six selected categories must be complete")
    db = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    try:
        jobs = list(db.execute("SELECT * FROM focused_research_jobs ORDER BY id LIMIT 6"))
        for job, category in zip(jobs, result["categories"]):
            assignments = list(db.execute("SELECT * FROM codex_first_research_assignments WHERE job_id=?", (job["id"],)))
            if include_shadow:
                for assignment in assignments:
                    if assignment["role"] != "shadow":
                        continue
                    if assignment["status"] != "completed":
                        raise ValueError("A selected shadow assignment is incomplete")
                    if assignment["contribution_id"] is not None:
                        raise ValueError("Shadow already in contributions; inspect before counting twice")
                    parsed = json.loads(assignment["parsed_json"])
                    if len(parsed["leads"]) != assignment["lead_count"]:
                        raise ValueError("Shadow count disagrees with saved response")
                    for ordinal, lead in enumerate(parsed["leads"], 1):
                        record = {key: lead.get(key, "") for key in ("organization", "program", "phone", "address", "uncertainty")}
                        record.update(id=f"shadow-{assignment['id']}-{ordinal}", category=job["category_label"],
                                      source_label=assignment["researcher"] + " shadow", role="shadow",
                                      assignment_id=assignment["id"], assignment_sha256=assignment["assignment_sha256"])
                        for old, new in (("website", "website_raw"), ("whyRelevant", "why_relevant"),
                                         ("locationOrServiceArea", "location_or_service_area"), ("leadType", "lead_type")):
                            record[new] = lead.get(old, "")
                        leads.append(record)
            rows = [lead for lead in leads if lead["category"] == job["category_label"]]
            category["includingShadowRows"] = len(rows)
            category["bySource"] = dict(collections.Counter(lead["source_label"].split(" · ")[0] for lead in rows))
            latest = max([job["completed_at"]] + [a["completed_at"] for a in assignments if a["completed_at"]])
            category["elapsedThroughShadowSeconds"] = metrics.seconds(category["firstPassAssignedAt"], latest)
        baseline = {table: [dict(row) for row in db.execute(f"SELECT * FROM {table} ORDER BY rowid")]
                    for table in ("imports", "categories", "imported_resources", "known_terms", "research_seeds")}
        # Re-importing the identical package changes this operational timestamp.
        for row in baseline["imports"]:
            row.pop("imported_at", None)
        result["semanticBaselineSha256"] = hashlib.sha256(json.dumps(baseline, sort_keys=True).encode()).hexdigest()
        words = [len((lead["why_relevant"] + " " + lead["uncertainty"]).split()) for lead in leads]
        result["submissionRowsIncludingShadow"] = len(leads)
        result["narrativeWords"] = sum(words)
        result["medianNarrativeWords"] = statistics.median(words)
        result["databaseSha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    finally:
        db.close()
    return result, leads


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--codex-grok", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    old, old_leads = read(args.baseline, True)
    new, _ = read(args.codex_grok, False)
    if old["semanticBaselineSha256"] != new["semanticBaselineSha256"]:
        raise ValueError("Semantic import baselines differ")
    if [c["category"] for c in old["categories"]] != [c["category"] for c in new["categories"]]:
        raise ValueError("Selected categories differ")
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "five-worker-baseline-leads.json").write_text(json.dumps(old_leads, indent=2))
    output = {"fiveWorker": old, "codexGrok": new, "limits": [
        "Counts are submitted rows, not accepted identities or recall.",
        "Claude shadow submissions were excluded from the old canonical run but are included here.",
        "Category windows include scheduling and human handoff; they are not active model time.",
        "Separate primary executions and incomplete historical telemetry prevent causal model comparisons."]}
    (args.output / "five-worker-comparison.json").write_text(json.dumps(output, indent=2))
    for result in (old, new):
        print(json.dumps({key: result[key] for key in ("database", "submissionRowsIncludingShadow", "narrativeWords", "semanticBaselineSha256")}))


if __name__ == "__main__":
    main()
