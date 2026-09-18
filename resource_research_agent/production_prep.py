"""Promote completed evidence into a separate, unstarted production workspace."""
from __future__ import annotations

import hashlib
import argparse
import json
import sqlite3
from contextlib import ExitStack, closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .codex_first_research import (
    codex_first_view, load_researcher_profile, prepare_codex_first_plan,
)
from .manual_consolidation import (
    consolidate_manual_discovery, finish_manual_discovery,
    leave_pending_manual_identities_unresolved,
)
from .storage import ResearchStore
from .challenger_routing import load_challenger_routing


PROFILES = ("codex-grok", "codex-claude", "claude-grok")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare_production_copy(
    experiment: Path,
    destination: Path,
    *,
    review_path: Path,
    category_rosters: dict[str, dict[str, Any]] | None = None,
    completed_count: int = 6,
) -> dict[str, Any]:
    """Reuse completed categories and a provenance-preserving union for curation.

    Original condition databases are opened read-only. A fresh copy keeps their
    completed assignments intact. Only empty, unissued future jobs in that new
    copy are replaced by the reviewed production plan. Separate finished manual
    runs hold the candidate union; no accepted-identity decisions are invented.
    """
    if completed_count < 1:
        raise ValueError("At least one completed category is required")
    destination = destination.expanduser().resolve()
    experiment = experiment.expanduser().resolve()
    review_path = review_path.expanduser().resolve()
    if destination.exists():
        raise ValueError("Production destination already exists; refusing to replace it")
    if not review_path.is_file() or not review_path.read_text().strip():
        raise ValueError("A completed architecture review artifact is required")
    source_paths = {profile: experiment / (profile + ".sqlite3") for profile in PROFILES}
    source_hashes = {profile: _sha(path) for profile, path in source_paths.items()}
    manifest: dict[str, Any] = {
        "schemaVersion": 1, "status": "preparing", "launched": False,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "database": str(destination), "sourceDirectory": str(experiment),
        "sourceDatabaseSha256": source_hashes,
        "reviewPath": str(review_path), "reviewSha256": _sha(review_path),
        "categoryRosters": category_rosters or {},
        "reusedResearchCategories": [], "retiredEmptyPlans": [], "curationUnions": [],
    }
    manifest_path = destination.with_suffix(".preparation.json")
    if manifest_path.exists():
        raise ValueError("Production preparation manifest already exists")
    with ExitStack() as stack:
        sources = {}
        jobs_by_profile = {}
        baselines = []
        for profile, path in source_paths.items():
            db = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
            stack.callback(db.close)
            db.row_factory = sqlite3.Row
            db.execute("BEGIN")
            sources[profile] = db
            jobs = [dict(row) for row in db.execute(
                "SELECT * FROM focused_research_jobs ORDER BY id"
            )]
            if len(jobs) < completed_count or any(job["status"] != "completed" for job in jobs[:completed_count]):
                raise ValueError(f"{profile}: selected experiment categories are incomplete")
            if any(job["status"] != "pending" for job in jobs[completed_count:]):
                raise ValueError(f"{profile}: research exists beyond the reviewed categories")
            jobs_by_profile[profile] = jobs
            baseline = {
                table: [dict(row) for row in db.execute(f"SELECT * FROM {table} ORDER BY rowid")]
                for table in ("imports", "categories", "imported_resources", "known_terms", "research_seeds")
            }
            baselines.append(baseline)
        if any(baseline != baselines[0] for baseline in baselines[1:]):
            raise ValueError("Experiment conditions do not share the same import baseline")
        reference_jobs = jobs_by_profile["codex-grok"]
        selected_ids = [job["category_id"] for job in reference_jobs[:completed_count]]
        if any([job["category_id"] for job in jobs[:completed_count]] != selected_ids for jobs in jobs_by_profile.values()):
            raise ValueError("Experiment category order differs between conditions")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.touch(exist_ok=False)
        with closing(sqlite3.connect(destination)) as copied:
            sources["codex-grok"].backup(copied)
        manifest_path.write_text(json.dumps(manifest, indent=2))
        store = ResearchStore(destination)
        import_id = int(reference_jobs[0]["import_id"])
        # This transaction can only discard untouched placeholders in our fresh
        # copy. Completed or assigned work, contributions and telemetry are vetoes.
        with store.connect() as copied:
            for job in reference_jobs[completed_count:]:
                active_pass = copied.execute(
                    "SELECT 1 FROM focused_research_passes WHERE job_id=? AND (status!='pending' OR assignment!='') LIMIT 1",
                    (job["id"],),
                ).fetchone()
                contributions = copied.execute("SELECT 1 FROM manual_discovery_contributions WHERE run_id=? LIMIT 1", (job["run_id"],)).fetchone()
                assignments = copied.execute("SELECT 1 FROM codex_first_research_assignments WHERE job_id=? LIMIT 1", (job["id"],)).fetchone()
                attempts = copied.execute("SELECT 1 FROM research_worker_telemetry WHERE job_id=? LIMIT 1", (job["id"],)).fetchone()
                if active_pass or contributions or assignments or attempts:
                    raise ValueError(f"{job['category_label']}: future work is not an empty placeholder")
                manifest["retiredEmptyPlans"].append({
                    "jobId": job["id"], "categoryId": job["category_id"], "planSha256": job["plan_sha256"],
                })
                copied.execute("DELETE FROM research_runs WHERE id=?", (job["run_id"],))

        prepare_codex_first_plan(
            store, import_id, roster=load_researcher_profile("codex-grok"),
            category_rosters=category_rosters, preserve_completed=True,
        )
        summary = store.import_summary(import_id) or {}
        for index, source_job in enumerate(reference_jobs[:completed_count]):
            manifest["reusedResearchCategories"].append({
                "categoryId": source_job["category_id"], "jobId": source_job["id"],
                "sourceProfile": "codex-grok", "sourceRunId": source_job["run_id"],
            })
            run_id = store.create_manual_discovery_run(
                "Consolidate the completed experiment evidence; no new research performed.",
                {"productionPromotion": True, "sourceDatabaseSha256": source_hashes,
                 "reviewSha256": manifest["reviewSha256"]},
                import_id, target_location=str(summary.get("serviceArea") or ""),
                target_category_id=source_job["category_id"], target_category_label=source_job["category_label"],
            )
            union: dict[str, Any] = {"categoryId": source_job["category_id"], "runId": run_id, "contributions": []}
            for profile in PROFILES:
                db = sources[profile]
                job = jobs_by_profile[profile][index]
                contributions = db.execute("""
                    SELECT * FROM manual_discovery_contributions WHERE id IN (
                        SELECT contribution_id FROM focused_research_passes WHERE job_id=? AND status='completed'
                        UNION SELECT contribution_id FROM codex_first_research_assignments
                          WHERE job_id=? AND status='completed' AND role='challenger'
                    ) ORDER BY id
                """, (job["id"], job["id"])).fetchall()
                for contribution in contributions:
                    if contribution["parse_status"] != "parsed":
                        raise ValueError("A completed source contribution is not parsed")
                    primary_pass = db.execute(
                        "SELECT focus_key, assignment_sha256 FROM focused_research_passes WHERE contribution_id=?",
                        (contribution["id"],),
                    ).fetchone()
                    external = db.execute(
                        "SELECT assignment_sha256 FROM codex_first_research_assignments WHERE contribution_id=?",
                        (contribution["id"],),
                    ).fetchone()
                    role = "primary" if primary_pass else "challenger"
                    label = f"{profile} {role} #{contribution['id']} / {contribution['source_label']}"[:100]
                    saved = store.save_manual_contribution(run_id, label, contribution["raw_text"])
                    union["contributions"].append({
                        "profile": profile, "sourceRunId": job["run_id"],
                        "sourceContributionId": contribution["id"], "sourceLabel": contribution["source_label"],
                        "sourceRole": role, "sourceFocusKey": primary_pass["focus_key"] if primary_pass else "",
                        "sourceAssignmentSha256": (primary_pass or external)["assignment_sha256"],
                        "rawSha256": contribution["raw_sha256"], "newContributionId": saved["id"],
                    })
            snapshot = consolidate_manual_discovery(store, run_id)
            if any(item["status"] == "pending" for item in snapshot["suggestions"]):
                leave_pending_manual_identities_unresolved(store, run_id)
            finish_manual_discovery(store, run_id)
            union["leadCount"] = store.manual_discovery_progress(run_id)["leadCount"]
            manifest["curationUnions"].append(union)
        if any(_sha(source_paths[profile]) != source_hashes[profile] for profile in PROFILES):
            raise RuntimeError("A source database changed during preparation; inspect before using the copy")
        view = codex_first_view(store, import_id)
        manifest.update(status="ready", importId=import_id,
                        completedCategories=view["completedCategories"], totalCategories=view["totalCategories"],
                        pendingCategories=[c["categoryId"] for c in view["categories"] if c["status"] != "completed"])
        manifest_path.write_text(json.dumps(manifest, indent=2))
        return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--routing-policy", type=Path)
    args = parser.parse_args(argv)
    result = prepare_production_copy(
        args.experiment, args.destination, review_path=args.review,
        category_rosters=load_challenger_routing(args.routing_policy) if args.routing_policy else None,
    )
    print(json.dumps({key: result[key] for key in (
        "status", "launched", "database", "completedCategories", "totalCategories", "pendingCategories",
    )}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
