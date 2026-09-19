"""Evidence-backed corrections with immutable history of each curation result."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .scout_curation import ScoutCurationError, _canonical_json, _sha256, validate_scout_curation_result
from .scout_curation_runner import validate_links
from .storage import ResearchStore


def revise_scout_curation_result(
    store: ResearchStore, job_id: int, category_id: str, result: dict[str, Any], *,
    expected_result_sha256: str, reason: str, evidence: list[dict[str, Any]],
) -> dict[str, Any]:
    """Revise a completed result, preserving its assignment and original output.

    No worker is called. Existing in-flight assignments remain sealed; later
    categories receive the revised resources. Final audit must also check any
    earlier in-flight assignment that reused the previous resource version.
    """
    if not reason.strip() or not evidence:
        raise ScoutCurationError("A curation revision requires a reason and evidence")
    job = store.get_scout_curation_job(job_id)
    normalized = validate_scout_curation_result(job, category_id, result, required_status="completed")
    category = next(c for c in job["categories"] if c["categoryId"] == category_id)
    validate_links(category["assignment"], normalized)
    now = datetime.now(timezone.utc).isoformat()
    digest = _sha256(normalized)
    with store.connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        previous = connection.execute(
            "SELECT * FROM scout_curation_categories WHERE job_id = ? AND category_id = ?",
            (job_id, category_id),
        ).fetchone()
        if previous["status"] != "completed" or previous["result_sha256"] != expected_result_sha256:
            raise ScoutCurationError("Curation result changed since this revision was prepared")
        if digest == previous["result_sha256"]:
            raise ScoutCurationError("Curation revision contains no change")
        cursor = connection.execute(
            """INSERT INTO scout_curation_result_revisions
               (job_id,category_id,created_at,reason,evidence_json,previous_result_json,
                previous_result_sha256,result_json,result_sha256)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (job_id, category_id, now, reason.strip(), _canonical_json(evidence),
             previous["result_json"], previous["result_sha256"], _canonical_json(normalized), digest),
        )
        connection.execute(
            """UPDATE scout_curation_categories SET result_json=?,result_sha256=?,
               resource_count=?,updated_at=? WHERE job_id=? AND category_id=?""",
            (_canonical_json(normalized), digest, len(normalized["resources"]), now, job_id, category_id),
        )
        connection.execute("UPDATE scout_curation_jobs SET updated_at=? WHERE id=?", (now, job_id))
        connection.execute(
            """INSERT INTO scout_curation_progress_events
               (job_id,category_id,created_at,phase,message,details_json) VALUES (?,?,?,?,?,?)""",
            (job_id, category_id, now, "curation-audit-correction", reason.strip(),
             _canonical_json({"revisionId": cursor.lastrowid, "previousResultSha256": previous["result_sha256"],
                              "resultSha256": digest, "resourceCount": len(normalized["resources"])})),
        )
    return store.get_scout_curation_job(job_id)
