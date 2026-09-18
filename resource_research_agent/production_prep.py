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
from .worker_policy import assert_worker_enabled
from .focused_research import save_focused_research_result


PROFILES = ("codex-grok", "codex-claude", "claude-grok")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _baseline(db: sqlite3.Connection, *, ignore_import_time: bool = False) -> dict[str, Any]:
    result = {table: [dict(row) for row in db.execute(f"SELECT * FROM {table} ORDER BY rowid")]
              for table in ("imports", "categories", "imported_resources", "known_terms", "research_seeds")}
    if ignore_import_time:
        for row in result["imports"]:
            row.pop("imported_at", None)
    return result


def _reuse_completed_primary(store: ResearchStore, db: sqlite3.Connection,
                            source_jobs: list[dict[str, Any]], import_id: int) -> list[dict[str, Any]]:
    """Copy sealed completed passes, retaining their clocks and provenance."""
    targets = {job["categoryId"]: job for job in store.list_focused_research_jobs(import_id)}
    reused = []
    for job in source_jobs:
        target = targets.get(job["category_id"])
        if not target or target["status"] == "completed":
            raise ValueError("Legacy partial work has no unfinished destination category")
        for row in db.execute("SELECT * FROM focused_research_passes WHERE job_id=? AND status='completed' ORDER BY ordinal", (job["id"],)):
            source_pass = dict(row)
            definition = json.loads(source_pass["definition_json"])
            if source_pass["pass_kind"] == "gap":
                store.add_focused_gap_pass(target["id"], definition)
            current = store.get_focused_research_job(target["id"])
            target_pass = next((p for p in current["passes"] if p["focusKey"] == source_pass["focus_key"]), None)
            if not target_pass or target_pass["status"] != "pending" or target_pass["definition"] != definition:
                raise ValueError("Legacy completed focus differs from the production plan")
            contribution = db.execute("SELECT * FROM manual_discovery_contributions WHERE id=?", (source_pass["contribution_id"],)).fetchone()
            if not contribution or contribution["run_id"] != job["run_id"] or contribution["parse_status"] != "parsed":
                raise ValueError("Legacy completed primary evidence is missing or invalid")
            if hashlib.sha256(source_pass["assignment"].encode()).hexdigest() != source_pass["assignment_sha256"]:
                raise ValueError("Legacy assignment hash mismatch")
            store.assign_focused_research_pass(target["id"], source_pass["focus_key"], source_pass["assignment"],
                                               source_pass["assignment_sha256"], source_pass["candidate_manifest_sha256"])
            saved = save_focused_research_result(store, target["id"], source_pass["focus_key"], contribution["raw_text"])
            saved_contribution = store.get_manual_contribution(target["runId"], saved["contributionId"])
            if saved["leadCount"] != source_pass["lead_count"] or saved_contribution["rawSha256"] != contribution["raw_sha256"]:
                raise ValueError("Legacy evidence changed during promotion")
            with store.connect() as copied:
                copied.execute("""UPDATE focused_research_passes SET assigned_at=?, completed_at=?,
                                  created_at=?, updated_at=?, coverage_json=? WHERE id=?""",
                               tuple(source_pass[k] for k in ("assigned_at", "completed_at", "created_at", "updated_at", "coverage_json")) + (saved["id"],))
                copied.execute("UPDATE manual_discovery_contributions SET created_at=?, updated_at=? WHERE id=?",
                               (contribution["created_at"], contribution["updated_at"], saved["contributionId"]))
            reused.append({"categoryId": job["category_id"], "sourceJobId": job["id"],
                           "sourcePassId": source_pass["id"], "focusKey": source_pass["focus_key"],
                           "sourceAssignmentSha256": source_pass["assignment_sha256"],
                           "rawSha256": contribution["raw_sha256"], "leadCount": saved["leadCount"],
                           "jobId": target["id"], "passId": saved["id"], "contributionId": saved["contributionId"]})
    return reused


def prepare_production_copy(
    experiment: Path,
    destination: Path,
    *,
    review_path: Path,
    category_rosters: dict[str, dict[str, Any]] | None = None,
    completed_count: int = 6,
    legacy_baseline: Path | None = None,
) -> dict[str, Any]:
    """Reuse completed categories and a provenance-preserving union for curation.

    Original condition databases are opened read-only. A fresh copy keeps their
    completed assignments intact. Only empty, unissued future jobs in that new
    copy are replaced by the reviewed production plan. Separate finished manual
    runs hold the candidate union; no accepted-identity decisions are invented.
    """
    if completed_count < 1:
        raise ValueError("At least one completed category is required")
    for roster in (category_rosters or {}).values():
        for researcher in roster["researchers"]:
            if researcher["role"] != "disabled":
                assert_worker_enabled(researcher["name"])
    destination = destination.expanduser().resolve()
    experiment = experiment.expanduser().resolve()
    review_path = review_path.expanduser().resolve()
    if destination.exists():
        raise ValueError("Production destination already exists; refusing to replace it")
    if not review_path.is_file() or not review_path.read_text().strip():
        raise ValueError("A completed architecture review artifact is required")
    source_paths = {profile: experiment / (profile + ".sqlite3") for profile in PROFILES}
    if legacy_baseline is not None:
        source_paths["five-worker-baseline"] = legacy_baseline.expanduser().resolve()
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
        for profile in PROFILES:
            path = source_paths[profile]
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
            baselines.append(_baseline(db))
        if any(baseline != baselines[0] for baseline in baselines[1:]):
            raise ValueError("Experiment conditions do not share the same import baseline")
        reference_jobs = jobs_by_profile["codex-grok"]
        selected_ids = [job["category_id"] for job in reference_jobs[:completed_count]]
        if any([job["category_id"] for job in jobs[:completed_count]] != selected_ids for jobs in jobs_by_profile.values()):
            raise ValueError("Experiment category order differs between conditions")
        if legacy_baseline is not None:
            db = sqlite3.connect(source_paths["five-worker-baseline"].as_uri() + "?mode=ro", uri=True)
            stack.callback(db.close)
            db.row_factory = sqlite3.Row
            db.execute("BEGIN")
            if _baseline(db, ignore_import_time=True) != _baseline(sources["codex-grok"], ignore_import_time=True):
                raise ValueError("Legacy baseline differs from the experiment import")
            legacy_jobs = [dict(row) for row in db.execute("SELECT * FROM focused_research_jobs ORDER BY id")]
            if [j["category_id"] for j in legacy_jobs[:completed_count]] != selected_ids or any(j["status"] != "completed" for j in legacy_jobs[:completed_count]):
                raise ValueError("Legacy baseline lacks the same completed categories")
            # Do not silently discard additional completed categories/challengers.
            for job in legacy_jobs[completed_count:]:
                external = db.execute("SELECT 1 FROM codex_first_research_assignments WHERE job_id=? AND (status='completed' OR raw_text!='')", (job["id"],)).fetchone()
                if job["status"] == "completed" or external:
                    raise ValueError("Legacy work beyond the review includes completed external evidence; explicit migration required")
            sources["five-worker-baseline"] = db
            jobs_by_profile["five-worker-baseline"] = legacy_jobs
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
        manifest["reusedLegacyPrimaryPasses"] = _reuse_completed_primary(
            store, sources["five-worker-baseline"], jobs_by_profile["five-worker-baseline"][completed_count:], import_id,
        ) if legacy_baseline is not None else []
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
            for profile, db in sources.items():
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
                for shadow in db.execute("SELECT * FROM codex_first_research_assignments WHERE job_id=? AND role='shadow'", (job["id"],)):
                    if shadow["status"] != "completed" or shadow["contribution_id"] is not None:
                        raise ValueError("Shadow evidence incomplete or already merged; inspect before promotion")
                    saved = store.save_manual_contribution(run_id, f"{profile} shadow #{shadow['id']} / {shadow['researcher']}"[:100], shadow["raw_text"])
                    if saved["parseStatus"] != "parsed" or len(saved["leads"]) != shadow["lead_count"] or saved["rawSha256"] != shadow["raw_sha256"]:
                        raise ValueError("Shadow evidence changed during promotion")
                    union["contributions"].append({
                        "profile": profile, "sourceRunId": job["run_id"], "sourceAssignmentId": shadow["id"],
                        "sourceLabel": shadow["researcher"], "sourceRole": "shadow",
                        "sourceAssignmentSha256": shadow["assignment_sha256"],
                        "rawSha256": shadow["raw_sha256"], "newContributionId": saved["id"],
                    })
            snapshot = consolidate_manual_discovery(store, run_id)
            if any(item["status"] == "pending" for item in snapshot["suggestions"]):
                leave_pending_manual_identities_unresolved(store, run_id)
            finish_manual_discovery(store, run_id)
            union["leadCount"] = store.manual_discovery_progress(run_id)["leadCount"]
            manifest["curationUnions"].append(union)
        if any(_sha(path) != source_hashes[profile] for profile, path in source_paths.items()):
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
    parser.add_argument("--legacy-baseline", type=Path)
    args = parser.parse_args(argv)
    result = prepare_production_copy(
        args.experiment, args.destination, review_path=args.review,
        category_rosters=load_challenger_routing(args.routing_policy) if args.routing_policy else None,
        legacy_baseline=args.legacy_baseline,
    )
    print(json.dumps({key: result[key] for key in (
        "status", "launched", "database", "completedCategories", "totalCategories", "pendingCategories",
    )}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
