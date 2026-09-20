"""Explicit Codex review handoff, bound to the exact saved curation results.

No AI worker is called. Completing this handoff records the reviewing assistant's
report; it is not human approval or telephone verification of the resources.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .scout_curation import ScoutCurationError, _canonical_json, _sha256
from .storage import ResearchStore

REVIEW_CONTRACT_VERSION = 2

def curation_fingerprint(job: dict[str, Any]) -> str:
    return _sha256({
        **{key: job.get(key) for key in (
            "id", "importId", "status", "candidatePackageSha256", "sourcePackageContentSha256",
            "officeName", "serviceArea",
        )},
        "categories": [{key: c.get(key) for key in ("categoryId", "status", "assignmentSha256", "resultSha256")}
                       for c in job["categories"]],
    })


def review_fingerprint(job: dict[str, Any]) -> str:
    digest = curation_fingerprint(job)
    navigation = job.get("reviewNavigationSha256")
    taxonomy = job.get("reviewTaxonomySeedSha256")
    return _sha256({"curation": digest, "navigation": navigation, "taxonomy": taxonomy}) if navigation or taxonomy else digest


def review_handoff(job: dict[str, Any], events: list[dict[str, Any]]) -> dict[str, Any]:
    digest = review_fingerprint(job)
    completed = job.get("status") == "completed" and all(c["status"] == "completed" for c in job["categories"])
    review = next((e for e in reversed(events)
                   if e["phase"] == "codex-review-completed"
                   and e.get("details", {}).get("reviewContractVersion") == REVIEW_CONTRACT_VERSION
                   and e.get("details", {}).get("resultFingerprint") == digest), None) if completed else None
    return {"status": "reviewed" if review else "awaiting-codex-review" if completed else "curating",
            "readyForSave": bool(review), "resultFingerprint": digest,
            "reviewedAt": review["createdAt"] if review else None}


def complete_codex_review(store: ResearchStore, job_id: int, *, expected_fingerprint: str,
                          report_path: Path) -> dict[str, Any]:
    report = report_path.read_text(encoding="utf-8")
    if not report.strip():
        raise ScoutCurationError("A completed Codex review requires a saved review report")
    # Hold the write reservation across the final snapshot check and review record.
    with store.connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        job = store.get_scout_curation_job(job_id)
        if not job or job["status"] != "completed" or any(c["status"] != "completed" for c in job["categories"]):
            raise ScoutCurationError("Complete curation before recording the Codex review")
        digest = review_fingerprint(job)
        if digest != expected_fingerprint:
            raise ScoutCurationError("Curation changed since the review; inspect the changed results first")
        from .scout_review_readiness import require_review_ready
        readiness = require_review_ready(store, job)
        details = {"resultFingerprint": digest, "reportPath": str(report_path.resolve()),
                   "reportSha256": hashlib.sha256(report.encode()).hexdigest(), "reportText": report,
                   "humanApproved": False, "phoneVerified": False,
                   "reviewContractVersion": REVIEW_CONTRACT_VERSION, "readiness": readiness}
        connection.execute(
            """INSERT INTO scout_curation_progress_events
               (job_id,category_id,created_at,phase,message,details_json) VALUES (?,?,?,?,?,?)""",
            (job_id, None, datetime.now(timezone.utc).isoformat(), "codex-review-completed",
             "Codex review is complete. The review HTML is ready to save.", _canonical_json(details)),
        )
    return review_handoff(job, store.list_scout_curation_progress(job_id))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", required=True)
    parser.add_argument("--job-id", required=True, type=int)
    parser.add_argument("--complete", action="store_true", help="Record an actually completed Codex review; does not perform one")
    parser.add_argument("--expected-fingerprint")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    store = ResearchStore(Path(args.database))
    if args.complete:
        if not args.expected_fingerprint or not args.report:
            parser.error("--complete requires --expected-fingerprint and --report")
        status = complete_codex_review(store, args.job_id, expected_fingerprint=args.expected_fingerprint, report_path=args.report)
    else:
        job = store.get_scout_curation_job(args.job_id)
        if not job:
            parser.error("Curation job not found")
        status = review_handoff(job, store.list_scout_curation_progress(args.job_id))
    print(json.dumps(status, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
