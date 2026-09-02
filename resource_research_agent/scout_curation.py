from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .candidate_package import build_candidate_package
from .storage import ResearchStore
from .focused_research import CODEX_FIRST_EXPERIMENT_MODE


SCOUT_CURATION_ASSIGNMENT_VERSION = "codex-curation-v2-direct-service"
SCOUT_CURATION_RESULT_SCHEMA_VERSION = 1


class ScoutCurationError(ValueError):
    """Raised when a curation job or Codex result violates its durable contract."""


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _assignment_sha256(assignment: dict[str, Any]) -> str:
    """Fingerprint an assignment without making its fingerprint self-referential."""
    fingerprinted = deepcopy(assignment)
    fingerprinted.pop("assignmentSha256", None)
    return _sha256(fingerprinted)


def _text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _unique_text(values: Any) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values if isinstance(values, list) else []:
        text = _text(value)
        key = text.casefold()
        if text and key not in seen:
            seen.add(key)
            result.append(text)
    return result


def _canonical_run(run_payloads: list[dict[str, Any]]) -> dict[str, Any]:
    if not run_payloads:
        raise ScoutCurationError("A researched category has no completed Scout run")
    return max(
        run_payloads,
        key=lambda item: (
            len(item.get("sourceResponses") or []),
            int((item.get("run") or {}).get("id") or 0),
        ),
    )


def _durable_run_payloads(run_payloads: Any) -> list[dict[str, Any]]:
    """Remove export-time presentation fields from Scout's research snapshot."""
    durable = deepcopy(run_payloads if isinstance(run_payloads, list) else [])
    for run_payload in durable:
        for candidate in run_payload.get("candidates") or []:
            resource_draft = candidate.get("resourceDraft")
            if isinstance(resource_draft, dict):
                resource_draft.pop("lastModified", None)
    return durable


def _assignment(
    candidate_package: dict[str, Any],
    category: dict[str, Any],
    run_payload: dict[str, Any],
) -> dict[str, Any]:
    run = run_payload["run"]
    durable_run = _durable_run_payloads([run_payload])[0]
    candidates = durable_run.get("candidates") or []
    return {
        "assignmentSchemaVersion": 1,
        "assignmentVersion": SCOUT_CURATION_ASSIGNMENT_VERSION,
        "role": "Codex-controlled Resource Scout curation",
        "location": deepcopy(candidate_package["location"]),
        "sourcePackage": deepcopy(candidate_package["sourcePackage"]),
        "availableCategories": [
            deepcopy(item)
            for item in candidate_package.get("categories") or []
            if str(item.get("id") or "") != "miscellaneous"
        ],
        "availableForGroups": deepcopy(candidate_package.get("forGroups") or []),
        "category": {
            "id": category["id"],
            "label": category["label"],
            "definition": deepcopy(category),
            "canonicalRunId": run["id"],
        },
        "candidates": deepcopy(candidates),
        "excludedCandidates": deepcopy(durable_run.get("excludedCandidates") or []),
        "sourceOnlyRecords": deepcopy(durable_run.get("sourceOnlyRecords") or []),
        "sourceResponses": deepcopy(durable_run.get("sourceResponses") or []),
        "previouslyCuratedResources": [],
        "curationPolicy": {
            "objective": (
                "Build the smallest high-confidence set of distinct, currently actionable "
                "resources that directly serve this category. Completeness is candidate "
                "disposition coverage, not proposal volume."
            ),
            "directServiceTest": (
                "Keep a proposal in a category only when the named program itself directly "
                "provides a substantial service that a person would reasonably seek under "
                "that category."
            ),
            "crossCategoryTest": (
                "Add another category only when the same named program independently passes "
                "that category's direct-service test. Do not add a category merely because "
                "the service removes a barrier, supports a later outcome, supplies a referral, "
                "or serves people who may also need that category."
            ),
            "portfolioGuidance": (
                "Prefer fewer strong additions over broad coverage. Do not keep a marginal "
                "candidate to meet a quota."
            ),
            "forGroupPolicy": (
                "Apply only an existing For group when current evidence clearly identifies "
                "that population. Never create or suggest a missing For group in this pass."
            ),
        },
        "instructions": [
            "Curate every candidate or explicitly omit it with a reason.",
            "Treat candidate coverage as an audit requirement, not an instruction to propose every candidate.",
            "Propose only distinct, current, actionable programs or providers that directly deliver the current category's service.",
            "Omit generic employer career pages, general school catalogs, broad directories, referral-only pages, and programs whose connection to the category is only an indirect barrier or downstream outcome.",
            "Prefer one actionable program or provider per resource; consolidate aliases and duplicate program descriptions, and do not split ordinary locations.",
            "Preserve uncertainty in plain language and do not invent facts.",
            "A broken page alone does not prove closure; use current official or primary evidence before omitting a candidate as closed or inaccessible.",
            "Reuse and extend a previously curated resource when it is the same program.",
            "Every new resource must include the current category and contributing candidate IDs.",
            "Assign another category only when the same named program directly and independently provides a substantial service in that category; barrier removal, referrals, and likely client overlap are not enough.",
            "Apply only clearly evidenced existing For groups. Do not create or suggest a missing For group.",
            "Prefer the smallest high-confidence proposal set; there is no target count or coverage quota.",
            "Return only one JSON object matching outputContract.",
        ],
        "outputContract": {
            "scoutCurationResultSchemaVersion": SCOUT_CURATION_RESULT_SCHEMA_VERSION,
            "assignmentSha256": "Copy from this assignment's assignmentSha256 field.",
            "categoryId": category["id"],
            "resources": [{
                "id": "stable generated resource ID",
                "name": "",
                "phone": "",
                "address": "",
                "website": "",
                "hours": "",
                "description": "",
                "informationText": "",
                "verifiedOn": None,
                "categories": [category["id"]],
                "categoryFilters": {},
                "forGroups": [],
                "pdfs": [],
                "candidateIds": ["candidate ID"],
            }],
            "candidateDispositions": [{
                "candidateId": "candidate ID",
                "disposition": "curated | merged | omitted",
                "resourceIds": ["generated resource ID"],
                "reason": "Required when omitted",
            }],
        },
    }


def prepare_scout_curation_job(
    store: ResearchStore,
    import_id: int | None = None,
) -> dict[str, Any]:
    selected_import_id = import_id or store.latest_import_id()
    if selected_import_id is None:
        raise ScoutCurationError("Connect a resource package before starting Resource Scout curation")
    codex_first_jobs = [
        job for job in store.list_focused_research_jobs(int(selected_import_id))
        if str(job.get("experimentMode") or "") == CODEX_FIRST_EXPERIMENT_MODE
    ]
    incomplete_codex_first = [
        str(job.get("categoryLabel") or job.get("categoryId") or "unnamed category")
        for job in codex_first_jobs
        if job.get("status") != "completed"
    ]
    if incomplete_codex_first:
        raise ScoutCurationError(
            "Finish the configured Codex-first research plan before curation. Remaining categories: "
            + ", ".join(f"'{label}'" for label in incomplete_codex_first)
        )
    candidate_package = build_candidate_package(store, int(selected_import_id))
    package_data = candidate_package.data
    incomplete_categories = [
        str(item.get("label") or item.get("id") or "unnamed category")
        for item in package_data.get("categoryManifest") or []
        if str(item.get("id") or "") != "miscellaneous"
        and item.get("researchStatus") != "completed"
    ]
    if incomplete_categories:
        raise ScoutCurationError(
            "Finish Scout research before starting Resource Scout curation. Remaining categories: "
            + ", ".join(f"'{label}'" for label in incomplete_categories)
        )
    package_fingerprint = {
        key: package_data[key]
        for key in (
            "candidatePackageSchemaVersion",
            "scoutVersion",
            "location",
            "sourcePackage",
            "categories",
            "forGroups",
            "categoryManifest",
        )
    }
    package_fingerprint["runs"] = _durable_run_payloads(package_data.get("runs"))
    candidate_package_sha256 = _sha256(package_fingerprint)
    existing = next((
        job for job in store.list_scout_curation_jobs(int(selected_import_id))
        if job["assignmentVersion"] == SCOUT_CURATION_ASSIGNMENT_VERSION
        and job["candidatePackageSha256"] == candidate_package_sha256
    ), None)
    if existing:
        return existing
    run_by_category: dict[str, list[dict[str, Any]]] = {}
    for run_payload in package_data.get("runs") or []:
        category_id = str((run_payload.get("run") or {}).get("targetCategoryId") or "")
        if category_id:
            run_by_category.setdefault(category_id, []).append(run_payload)

    category_rows: list[dict[str, Any]] = []
    for category in package_data.get("categories") or []:
        category_id = str(category.get("id") or "")
        if not category_id or category_id == "miscellaneous":
            continue
        runs = run_by_category.get(category_id, [])
        if not runs:
            continue
        canonical = _canonical_run(runs)
        assignment = _assignment(package_data, category, canonical)
        assignment["candidatePackageSha256"] = candidate_package_sha256
        assignment_sha256 = _assignment_sha256(assignment)
        assignment["assignmentSha256"] = assignment_sha256
        category_rows.append({
            "categoryId": category_id,
            "categoryLabel": str(category.get("label") or category_id),
            "canonicalRunId": int(canonical["run"]["id"]),
            "candidateCount": len(canonical.get("candidates") or []),
            "assignment": assignment,
            "assignmentSha256": assignment_sha256,
        })

    job_id = store.create_scout_curation_job(
        {
            "importId": int(selected_import_id),
            "assignmentVersion": SCOUT_CURATION_ASSIGNMENT_VERSION,
            "candidatePackageSha256": candidate_package_sha256,
            "locationName": package_data["location"]["name"],
            "officeName": package_data["location"].get("officeName") or "",
            "serviceArea": package_data["location"].get("serviceArea") or "",
            "sourcePackageSha256": package_data["sourcePackage"]["sourceSha256"],
            "sourcePackageContentSha256": package_data["sourcePackage"]["contentSha256"],
            "sourcePackageVersion": package_data["sourcePackage"].get("packageVersion") or "",
        },
        category_rows,
    )
    job = store.get_scout_curation_job(job_id)
    if job is None:  # pragma: no cover - guarded by the insert above
        raise RuntimeError("Created Resource Scout curation job could not be read")
    return job


def _completed_resources(job: dict[str, Any]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for category in job["categories"]:
        result = category.get("result") or {}
        for resource in result.get("resources") or []:
            resource_id = str(resource.get("id") or "")
            if not resource_id:
                continue
            if resource_id not in merged:
                order.append(resource_id)
                merged[resource_id] = deepcopy(resource)
                continue
            previous = merged[resource_id]
            next_resource = deepcopy(resource)
            next_resource["categories"] = _unique_text(
                (previous.get("categories") or []) + (resource.get("categories") or [])
            )
            next_resource["forGroups"] = _unique_text(
                (previous.get("forGroups") or []) + (resource.get("forGroups") or [])
            )
            filters = deepcopy(previous.get("categoryFilters") or {})
            filters.update(deepcopy(resource.get("categoryFilters") or {}))
            next_resource["categoryFilters"] = filters
            next_resource["candidateIds"] = _unique_text(
                (previous.get("candidateIds") or []) + (resource.get("candidateIds") or [])
            )
            merged[resource_id] = next_resource
    return [merged[resource_id] for resource_id in order]


def completed_scout_curation_resources(job: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the stable merged resource set produced by a completed curation job."""
    if job.get("status") != "completed":
        raise ScoutCurationError(
            "Finish every Resource Scout curation category before reading its resource set"
        )
    return _completed_resources(job)


def next_scout_curation_assignment(store: ResearchStore, job_id: int) -> dict[str, Any] | None:
    job = store.get_scout_curation_job(job_id)
    if not job:
        raise ScoutCurationError("Resource Scout curation job not found")
    category = next(
        (item for item in job["categories"] if item["status"] == "assigned"),
        None,
    )
    if category is None:
        category = next(
            (item for item in job["categories"] if item["status"] in {"pending", "failed"}),
            None,
        )
    if category is None:
        return None
    if category["status"] != "assigned":
        assignment = deepcopy(category["assignment"])
        assignment["previouslyCuratedResources"] = _completed_resources(job)
        digest = _assignment_sha256(assignment)
        assignment["assignmentSha256"] = digest
        store.update_scout_curation_category_assignment(
            job_id, category["categoryId"], assignment, digest
        )
        category = store.mark_scout_curation_category_assigned(
            job_id, category["categoryId"]
        )
    return category["assignment"]


def _normalize_resource(
    resource: Any,
    *,
    category_id: str,
    valid_category_ids: set[str],
    now: str,
) -> dict[str, Any]:
    if not isinstance(resource, dict):
        raise ScoutCurationError("Every curated resource must be an object")
    resource_id = _text(resource.get("id"))
    name = _text(resource.get("name"))
    if not resource_id or not name:
        raise ScoutCurationError("Every curated resource needs a stable ID and name")
    categories = _unique_text(resource.get("categories"))
    if category_id not in categories:
        raise ScoutCurationError(f"Resource '{name}' is missing category '{category_id}'")
    unknown_categories = set(categories) - valid_category_ids
    if unknown_categories:
        raise ScoutCurationError(
            f"Resource '{name}' uses unknown categories: {', '.join(sorted(unknown_categories))}"
        )
    candidate_ids = _unique_text(resource.get("candidateIds"))
    if not candidate_ids:
        raise ScoutCurationError(f"Resource '{name}' has no contributing candidate IDs")
    filters = resource.get("categoryFilters") or {}
    if not isinstance(filters, dict):
        raise ScoutCurationError(f"Resource '{name}' categoryFilters must be an object")
    normalized_filters = {
        str(key): _unique_text(value)
        for key, value in filters.items()
        if str(key) in categories and _unique_text(value)
    }
    return {
        "id": resource_id,
        "name": name,
        "phone": _text(resource.get("phone")),
        "address": _text(resource.get("address")),
        "website": _text(resource.get("website")),
        "hours": _text(resource.get("hours")),
        "description": str(resource.get("description") or "").strip(),
        "informationText": str(resource.get("informationText") or "").strip(),
        "verifiedOn": resource.get("verifiedOn") or None,
        "categories": categories,
        "categoryFilters": normalized_filters,
        "forGroups": _unique_text(resource.get("forGroups")),
        "pdfs": deepcopy(resource.get("pdfs") if isinstance(resource.get("pdfs"), list) else []),
        "candidateIds": candidate_ids,
        "lastModified": _text(resource.get("lastModified")) or now,
    }


def save_scout_curation_result(
    store: ResearchStore,
    job_id: int,
    category_id: str,
    result: dict[str, Any],
) -> dict[str, Any]:
    job = store.get_scout_curation_job(job_id)
    if not job:
        raise ScoutCurationError("Resource Scout curation job not found")
    category = next(
        (item for item in job["categories"] if item["categoryId"] == category_id),
        None,
    )
    if not category:
        raise ScoutCurationError("Resource Scout curation category not found")
    if category["status"] != "assigned":
        raise ScoutCurationError("Assign this category to Codex before saving its result")
    if not isinstance(result, dict):
        raise ScoutCurationError("Codex curation result must be one JSON object")
    if result.get("scoutCurationResultSchemaVersion") != SCOUT_CURATION_RESULT_SCHEMA_VERSION:
        raise ScoutCurationError("Unsupported Resource Scout curation result schema version")
    if str(result.get("assignmentSha256") or "") != category["assignmentSha256"]:
        raise ScoutCurationError("Codex result does not match the assigned curation snapshot")
    if str(result.get("categoryId") or "") != category_id:
        raise ScoutCurationError("Codex result belongs to another category")

    assignment_candidates = category["assignment"].get("candidates") or []
    expected_candidate_ids = {str(item.get("id")) for item in assignment_candidates}
    valid_category_ids = {item["categoryId"] for item in job["categories"]}
    now = datetime.now(timezone.utc).isoformat()
    resources = [
        _normalize_resource(
            resource,
            category_id=category_id,
            valid_category_ids=valid_category_ids,
            now=now,
        )
        for resource in result.get("resources") or []
    ]
    resource_ids = [resource["id"] for resource in resources]
    if len(resource_ids) != len(set(resource_ids)):
        raise ScoutCurationError("Codex result contains duplicate resource IDs")
    prior_resource_ids = {resource["id"] for resource in _completed_resources(job)}
    known_resource_ids = set(resource_ids) | prior_resource_ids

    dispositions = result.get("candidateDispositions")
    if not isinstance(dispositions, list):
        raise ScoutCurationError("Codex result needs candidateDispositions")
    seen_candidate_ids: set[str] = set()
    normalized_dispositions: list[dict[str, Any]] = []
    allowed = {"curated", "merged", "omitted"}
    for disposition in dispositions:
        if not isinstance(disposition, dict):
            raise ScoutCurationError("Every candidate disposition must be an object")
        candidate_id = str(disposition.get("candidateId") or "")
        state = str(disposition.get("disposition") or "")
        linked_resources = _unique_text(disposition.get("resourceIds"))
        reason = str(disposition.get("reason") or "").strip()
        if candidate_id not in expected_candidate_ids:
            raise ScoutCurationError(f"Unknown candidate disposition: {candidate_id}")
        if candidate_id in seen_candidate_ids:
            raise ScoutCurationError(f"Candidate {candidate_id} has more than one disposition")
        if state not in allowed:
            raise ScoutCurationError(f"Candidate {candidate_id} has an invalid disposition")
        if state == "omitted" and not reason:
            raise ScoutCurationError(f"Omitted candidate {candidate_id} needs a reason")
        if state != "omitted" and not linked_resources:
            raise ScoutCurationError(f"Candidate {candidate_id} needs a resource link")
        unknown_resource_ids = set(linked_resources) - known_resource_ids
        if unknown_resource_ids:
            raise ScoutCurationError(
                f"Candidate {candidate_id} links unknown resources: "
                + ", ".join(sorted(unknown_resource_ids))
            )
        seen_candidate_ids.add(candidate_id)
        normalized_dispositions.append({
            "candidateId": candidate_id,
            "disposition": state,
            "resourceIds": linked_resources,
            "reason": reason,
        })
    missing = expected_candidate_ids - seen_candidate_ids
    if missing:
        raise ScoutCurationError(
            "Codex result is missing candidate dispositions: " + ", ".join(sorted(missing))
        )
    known_candidate_ids = expected_candidate_ids | {
        candidate_id
        for resource in category["assignment"].get("previouslyCuratedResources") or []
        for candidate_id in _unique_text(resource.get("candidateIds"))
    }
    covered_by_resources = {
        candidate_id
        for resource in resources
        for candidate_id in resource["candidateIds"]
    }
    unknown_resource_candidates = covered_by_resources - known_candidate_ids
    if unknown_resource_candidates:
        raise ScoutCurationError(
            "Curated resources contain unknown candidate IDs: "
            + ", ".join(sorted(unknown_resource_candidates))
        )
    required_resource_candidates = {
        item["candidateId"]
        for item in normalized_dispositions
        if item["disposition"] != "omitted"
    }
    missing_resource_candidates = required_resource_candidates - covered_by_resources
    if missing_resource_candidates:
        raise ScoutCurationError(
            "Curated resources are missing contributing candidate IDs: "
            + ", ".join(sorted(missing_resource_candidates))
        )
    omitted_resource_candidates = {
        item["candidateId"]
        for item in normalized_dispositions
        if item["disposition"] == "omitted"
    } & covered_by_resources
    if omitted_resource_candidates:
        raise ScoutCurationError(
            "Omitted candidates appear in curated resources: "
            + ", ".join(sorted(omitted_resource_candidates))
        )

    normalized = {
        "scoutCurationResultSchemaVersion": SCOUT_CURATION_RESULT_SCHEMA_VERSION,
        "assignmentSha256": category["assignmentSha256"],
        "categoryId": category_id,
        "resources": resources,
        "candidateDispositions": normalized_dispositions,
    }
    return store.save_scout_curation_category_result(
        job_id,
        category_id,
        normalized,
        _sha256(normalized),
        len(resources),
    )


def build_scout_review_seed(store: ResearchStore, job_id: int) -> dict[str, Any]:
    job = store.get_scout_curation_job(job_id)
    if not job:
        raise ScoutCurationError("Resource Scout curation job not found")
    if job["status"] != "completed":
        raise ScoutCurationError("Finish every Resource Scout curation category before building HTML")
    summary = store.import_summary(job["importId"])
    if not summary:
        raise ScoutCurationError("Resource Scout curation source package snapshot is missing")
    resources = _completed_resources(job)
    for resource in resources:
        resource.pop("candidateIds", None)
    categories = [
        deepcopy(category)
        for category in summary["categories"]
        if category["id"] != "miscellaneous"
    ]
    return {
        "resourcePackageSchemaVersion": 3,
        "packageVersion": summary["schema"]["packageVersion"],
        "officeName": f"Auto{job['locationName'].replace(' ', '')}",
        "serviceArea": job["serviceArea"],
        "categories": categories,
        "categoryMigrations": [],
        "forGroups": summary["forGroups"],
        "resources": resources,
        "changes": [],
        "deletionRequests": [],
        "deletions": [],
        "packageCreatedAt": datetime.now(timezone.utc).isoformat(),
        "lastModified": datetime.now(timezone.utc).isoformat(),
    }


@dataclass(frozen=True)
class ChatGPTSchedule:
    delay_minutes: int
    scheduled_at: datetime
    reason: str

    @property
    def message(self) -> str:
        clock = self.scheduled_at.astimezone().strftime("%I:%M %p").lstrip("0")
        suffix = f" {self.reason}" if self.reason else ""
        return (
            f"I will wait {self.delay_minutes} minutes before the next ChatGPT "
            f"research assignment and send it at {clock}.{suffix}"
        )


def schedule_chatgpt_assignment(
    completed_at: datetime,
    random_source: Any,
    *,
    adjustment_minutes: int = 0,
    reason: str = "",
    explicit_reset_at: datetime | None = None,
    previous_sent_at: datetime | None = None,
) -> ChatGPTSchedule:
    if explicit_reset_at and explicit_reset_at > completed_at:
        import math

        delay = math.ceil((explicit_reset_at - completed_at).total_seconds() / 60)
        return ChatGPTSchedule(
            delay_minutes=delay,
            scheduled_at=explicit_reset_at,
            reason=_text(reason) or "ChatGPT supplied an explicit reset time.",
        )
    baseline = int(random_source.randint(5, 10))
    adjustment = max(0, int(adjustment_minutes))
    spacing = baseline + adjustment
    from datetime import timedelta

    spacing_anchor = previous_sent_at or completed_at
    scheduled_at = max(
        completed_at,
        spacing_anchor + timedelta(minutes=spacing),
    )
    import math

    delay = max(
        0,
        math.ceil((scheduled_at - completed_at).total_seconds() / 60),
    )

    return ChatGPTSchedule(
        delay_minutes=delay,
        scheduled_at=scheduled_at,
        reason=_text(reason),
    )


def progress_heartbeat_due(last_reported_at: datetime, now: datetime) -> bool:
    return (now - last_reported_at).total_seconds() >= 15 * 60
