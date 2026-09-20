"""Reviewed Types and For groups for a completed office workbench.

This adds finding aids to AI proposals without rewriting sealed assignments,
resource facts, category membership, or human approval. It calls no AI worker.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from typing import Any

from .scout_curation import ScoutCurationError, _completed_resources, _sha256, _canonical_json
from .scout_review_handoff import curation_fingerprint
from .storage import ResearchStore


def latest_navigation(store: ResearchStore, job_id: int) -> dict[str, Any] | None:
    with store.connect() as connection:
        row = connection.execute(
            "SELECT * FROM scout_review_navigation_revisions WHERE job_id=? ORDER BY id DESC LIMIT 1",
            (job_id,),
        ).fetchone()
    if not row:
        return None
    result = {"id": row["id"], "baseFingerprint": row["base_fingerprint"],
              "proposalSha256": row["proposal_sha256"], "proposal": json.loads(row["proposal_json"])}
    if _sha256(result["proposal"]) != result["proposalSha256"]:
        raise ScoutCurationError("Navigation proposal hash does not match its saved content")
    return result


def _definitions(values: Any, name: str, *, allow_empty: bool = False) -> dict[str, dict[str, Any]]:
    if not isinstance(values, list) or (not values and not allow_empty):
        raise ScoutCurationError(f"{name} must contain definitions")
    result = {}
    for item in values:
        label = item.get("label", "") if isinstance(item, dict) else ""
        if not isinstance(label, str) or not label.strip() or label != label.strip() or label.casefold() in result:
            raise ScoutCurationError(f"{name} has a blank or duplicate label")
        if not isinstance(item.get("definition"), str) or not item["definition"].strip():
            raise ScoutCurationError(f"{name} needs a definition for {label}")
        result[label.casefold()] = item
    return result


def validate_navigation(job: dict[str, Any], proposal: dict[str, Any]) -> None:
    if not isinstance(proposal, dict):
        raise ScoutCurationError("Navigation proposal must be an object")
    if job["status"] != "completed" or any(c["status"] != "completed" for c in job["categories"]):
        raise ScoutCurationError("Finish curation before assigning navigation")
    if proposal.get("schemaVersion") != 1 or proposal.get("baseFingerprint") != curation_fingerprint(job):
        raise ScoutCurationError("Navigation was prepared for different curation results")
    resources = {r["id"]: r for r in _completed_resources(job)}
    category_ids = {c["categoryId"] for c in job["categories"]}
    categories = proposal.get("categories")
    if not isinstance(categories, list) or len(categories) != len(category_ids) or any(not isinstance(c, dict) for c in categories) or {c.get("id") for c in categories} != category_ids:
        raise ScoutCurationError("Navigation must design exactly the completed Categories")
    types = {c["id"]: _definitions(c.get("types"), c["id"] + " Types") for c in categories}
    groups = _definitions(proposal.get("groups"), "For groups", allow_empty=True)
    if not groups and (not isinstance(proposal.get("noGroupCatalogReason"), str) or not proposal["noGroupCatalogReason"].strip()):
        raise ScoutCurationError("An empty For-group catalog needs an explicit review reason")
    assignments = proposal.get("assignments")
    if not isinstance(assignments, list) or len(assignments) != len(resources) or any(not isinstance(a, dict) for a in assignments) or {a.get("resourceId") for a in assignments} != set(resources):
        raise ScoutCurationError("Navigation must cover every resource exactly once")
    used_types = {c: set() for c in category_ids}
    used_groups = set()
    for assignment in assignments:
        resource = resources[assignment["resourceId"]]
        if not isinstance(assignment.get("types"), dict) or set(assignment.get("types", {})) != set(resource["categories"]):
            raise ScoutCurationError(f"Type assignments must cover exactly the Categories of {resource['id']}")
        if not isinstance(assignment.get("forGroups"), list) or any(not isinstance(g, dict) for g in assignment["forGroups"]):
            raise ScoutCurationError(f"For-group decisions must be a list on {resource['id']}")
        records = list(assignment["forGroups"])
        for category_id, choices in assignment["types"].items():
            if not isinstance(choices, list) or not choices or any(not isinstance(t, dict) for t in choices):
                raise ScoutCurationError(f"Resolve the {category_id} Type for {resource['id']}")
            labels = [x.get("label") for x in choices]
            if len(set(labels)) != len(labels) or any(str(x).casefold() not in types[category_id] for x in labels):
                raise ScoutCurationError(f"Unknown or duplicate Type on {resource['id']}")
            used_types[category_id].update(labels)
            records.extend(choices)
        labels = [x.get("label") for x in assignment.get("forGroups", [])]
        if len(labels) != len(set(labels)) or any(str(x).casefold() not in groups for x in labels):
            raise ScoutCurationError(f"Unknown or duplicate For group on {resource['id']}")
        used_groups.update(labels)
        if not labels and (not isinstance(assignment.get("noGroupReason"), str) or not assignment["noGroupReason"].strip()):
            raise ScoutCurationError(f"Record the no-group decision for {resource['id']}")
        for relation in records:
            evidence = relation.get("evidence") or {}
            if not isinstance(evidence, dict):
                raise ScoutCurationError(f"Navigation evidence must be an object on {resource['id']}")
            field, text = evidence.get("field"), evidence.get("text")
            if not isinstance(field, str) or field not in {"name", "description", "informationText", "hours", "address"} or not isinstance(text, str) or not text.strip() or text not in resource.get(field, ""):
                raise ScoutCurationError(f"Navigation evidence is not present in {resource['id']}")
    if used_groups != {v['label'] for v in groups.values()}:
        raise ScoutCurationError("Remove unused For-group definitions")
    for cid, definitions in types.items():
        if used_types[cid] != {v['label'] for v in definitions.values()}:
            raise ScoutCurationError(f"Remove unused {cid} Type definitions")


def save_navigation(store: ResearchStore, job_id: int, proposal: dict[str, Any], *, reason: str) -> dict[str, Any]:
    if not reason.strip():
        raise ScoutCurationError("Navigation needs a review reason")
    with store.connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        job = store.get_scout_curation_job(job_id)
        if not job:
            raise ScoutCurationError("Curation job not found")
        if store.latest_taxonomy_compilation_for_curation_job(job_id):
            raise ScoutCurationError("This workbench already has a taxonomy compilation; revise that study instead")
        validate_navigation(job, proposal)
        digest = _sha256(proposal)
        current = latest_navigation(store, job_id)
        if current and current["proposalSha256"] == digest:
            return current
        if connection.execute(
            "SELECT 1 FROM scout_review_navigation_revisions WHERE job_id=? AND proposal_sha256=?",
            (job_id, digest),
        ).fetchone():
            raise ScoutCurationError("This proposal is an older revision; create an explicitly revised proposal")
        now = datetime.now(timezone.utc).isoformat()
        connection.execute(
            "INSERT INTO scout_review_navigation_revisions (job_id,created_at,base_fingerprint,proposal_sha256,proposal_json,reason) VALUES (?,?,?,?,?,?)",
            (job_id, now, proposal["baseFingerprint"], digest, _canonical_json(proposal), reason.strip()),
        )
        connection.execute(
            "INSERT INTO scout_curation_progress_events (job_id,category_id,created_at,phase,message,details_json) VALUES (?,NULL,?,?,?,?)",
            (job_id, now, "review-navigation-proposed", "Types and For groups prepared for the review workbench.",
             _canonical_json({"proposalSha256": digest, "resourceCount": len(proposal["assignments"]), "humanApproved": False})),
        )
    return latest_navigation(store, job_id)


def apply_navigation(seed: dict[str, Any], job: dict[str, Any], navigation: dict[str, Any]) -> dict[str, Any]:
    proposal = navigation["proposal"]
    if navigation["proposalSha256"] != job.get("reviewNavigationSha256"):
        raise ScoutCurationError("Navigation changed while preparing the workbench")
    validate_navigation(job, proposal)
    result = deepcopy(seed)
    categories = {c["id"]: c for c in proposal["categories"]}
    for category in result["categories"]:
        category["filters"] = [t["label"] for t in categories[category["id"]]["types"]]
    result["forGroups"] = [g["label"] for g in proposal["groups"]]
    assignments = {a["resourceId"]: a for a in proposal["assignments"]}
    for resource in result["resources"]:
        a = assignments[resource["id"]]
        resource["categoryFilters"] = {c: [t["label"] for t in values] for c, values in a["types"].items()}
        resource["forGroups"] = [g["label"] for g in a["forGroups"]]
    return result


def main() -> int:
    import argparse
    from pathlib import Path
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', required=True)
    parser.add_argument('--job-id', type=int, required=True)
    parser.add_argument('--proposal', type=Path, required=True)
    parser.add_argument('--reason', required=True)
    args = parser.parse_args()
    revision = save_navigation(ResearchStore(Path(args.database)), args.job_id,
        json.loads(args.proposal.read_text()), reason=args.reason)
    print(json.dumps({k:v for k,v in revision.items() if k != 'proposal'}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
