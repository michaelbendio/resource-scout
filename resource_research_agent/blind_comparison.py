from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .focused_research import (
    BLIND_COMPARISON_EXPERIMENT_MODE,
    close_focused_research_job,
    json_sha256,
    prepare_focused_research_job,
)
from .manual_discovery import normalize_manual_identity
from .scout_curation import SCOUT_CURATION_ASSIGNMENT_VERSION
from .storage import ResearchStore


BLIND_FIXTURE_PATH = (
    Path(__file__).with_name("research_evidence") / "blind_comparison_v1.json"
)
BLIND_REVIEW_SCHEMA_VERSION = 1
SHADOW_SOURCES = ("ChatGPT", "Grok", "Claude", "Perplexity")
ALL_SOURCES = ("Codex", *SHADOW_SOURCES)


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def load_blind_comparison_fixture() -> dict[str, Any]:
    value = json.loads(BLIND_FIXTURE_PATH.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("Blind comparison fixture must be one JSON object")
    return value


def _fixture_category(fixture: dict[str, Any], category_id: str) -> dict[str, Any]:
    found = next(
        (
            item for item in fixture.get("heldOutCategories") or []
            if str(item.get("categoryId") or "") == category_id
        ),
        None,
    )
    if not found:
        raise ValueError(f"Blind comparison category not in fixture: {category_id}")
    return found


def _expected_seal(category: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "id": int(item["id"]),
            "source": str(item["source"]),
            "rawSha256": str(item["rawSha256"]),
            "leadCount": int(item["leadCount"]),
        }
        for item in category.get("contributions") or []
    ]


def _actual_seal(store: ResearchStore, run_id: int) -> list[dict[str, Any]]:
    return [
        {
            "id": int(item["id"]),
            "source": str(item["source"]),
            "rawSha256": str(item["rawSha256"]),
            "leadCount": int(item["leadCount"]),
        }
        for item in store.manual_contribution_seal(run_id)
    ]


def _validate_fixture(store: ResearchStore, fixture: dict[str, Any]) -> None:
    if int(fixture.get("schemaVersion") or 0) != 1:
        raise ValueError("Unsupported blind comparison fixture schema")
    if str(fixture.get("experimentMode") or "") != BLIND_COMPARISON_EXPERIMENT_MODE:
        raise ValueError("Blind comparison fixture mode does not match this release")
    location = fixture.get("location") or {}
    import_id = int(location.get("importId") or 0)
    summary = store.import_summary(import_id)
    if not summary:
        raise ValueError("Blind comparison package snapshot is unavailable")
    for field in ("sourceName", "sourceSha256", "contentSha256", "officeName", "serviceArea"):
        if str(summary.get(field) or "") != str(location.get(field) or ""):
            raise ValueError(f"Blind comparison package {field} changed")
    categories = fixture.get("heldOutCategories") or []
    ids = [str(item.get("categoryId") or "") for item in categories]
    if len(ids) < 3 or len(set(ids)) != len(ids) or any(not value for value in ids):
        raise ValueError("Blind comparison needs several unique held-out categories")
    curation = fixture.get("curation") or {}
    if str(curation.get("assignmentVersion") or "") != SCOUT_CURATION_ASSIGNMENT_VERSION:
        raise ValueError("Blind comparison curation policy changed")
    curation_job_id = int(curation.get("jobId") or 0)
    curation_job = store.get_scout_curation_job(curation_job_id)
    if not curation_job or curation_job.get("status") != "completed":
        raise ValueError("Blind comparison curation snapshot is unavailable")
    if int(curation_job.get("importId") or 0) != import_id:
        raise ValueError("Blind comparison curation package changed")
    for category in categories:
        category_id = str(category["categoryId"])
        run_id = int(category.get("shadowRunId") or 0)
        run = store.get_run(run_id)
        if not run or run.get("status") != "completed":
            raise ValueError(f"Held-out {category_id} shadow run is unavailable")
        if int(run.get("sourceImportId") or 0) != import_id:
            raise ValueError(f"Held-out {category_id} shadow package changed")
        if str(run.get("targetCategoryId") or "") != category_id:
            raise ValueError(f"Held-out {category_id} shadow category changed")
        expected = _expected_seal(category)
        actual = _actual_seal(store, run_id)
        if expected != actual:
            raise ValueError(f"Held-out {category_id} shadow responses changed")
        if {item["source"] for item in actual} != set(SHADOW_SOURCES):
            raise ValueError(f"Held-out {category_id} does not contain all shadow sources")
        curation_category = next(
            (
                item for item in curation_job.get("categories") or []
                if item.get("categoryId") == category_id
            ),
            None,
        )
        if not curation_category or curation_category.get("status") != "completed":
            raise ValueError(f"Held-out {category_id} curation result is unavailable")
        if str(curation_category.get("resultSha256") or "") != str(
            category.get("curationResultSha256") or ""
        ):
            raise ValueError(f"Held-out {category_id} curation result changed")


def prepare_blind_comparison(store: ResearchStore) -> dict[str, Any]:
    fixture = load_blind_comparison_fixture()
    _validate_fixture(store, fixture)
    fixture_sha = json_sha256(fixture)
    existing = store.find_blind_comparison_study(
        BLIND_COMPARISON_EXPERIMENT_MODE, fixture_sha
    )
    if existing:
        return blind_comparison_view(existing)
    import_id = int(fixture["location"]["importId"])
    category_rows = []
    for category in fixture["heldOutCategories"]:
        focused = prepare_focused_research_job(
            store,
            import_id,
            str(category["categoryId"]),
            experiment_mode=BLIND_COMPARISON_EXPERIMENT_MODE,
            redact_recovery_targets=False,
        )
        category_rows.append({
            "importId": import_id,
            "categoryId": str(category["categoryId"]),
            "categoryLabel": str(category["categoryLabel"]),
            "shadowRunId": int(category["shadowRunId"]),
            "shadowSealSha256": _sha(_expected_seal(category)),
            "focusedJobId": int(focused["id"]),
        })
    study = store.create_blind_comparison_study(
        experiment_mode=BLIND_COMPARISON_EXPERIMENT_MODE,
        fixture=fixture,
        fixture_sha256=fixture_sha,
        curation_assignment_version=SCOUT_CURATION_ASSIGNMENT_VERSION,
        categories=category_rows,
    )
    store.transition_blind_comparison_study(
        int(study["id"]), allowed_statuses={"sealed"}, status="researching"
    )
    return blind_comparison_view(store.get_blind_comparison_study(int(study["id"])))


def blind_comparison_view(study: dict[str, Any] | None) -> dict[str, Any]:
    if not study:
        raise ValueError("Blind comparison study not found")
    revealed = study.get("status") in {"revealed", "reviewing", "completed"}
    return {
        "id": int(study["id"]),
        "experimentMode": str(study["experimentMode"]),
        "status": str(study["status"]),
        "fixtureSha256": str(study["fixtureSha256"]),
        "curationAssignmentVersion": str(study["curationAssignmentVersion"]),
        "createdAt": study.get("createdAt"),
        "updatedAt": study.get("updatedAt"),
        "codexClosedAt": study.get("codexClosedAt"),
        "revealedAt": study.get("revealedAt"),
        "completedAt": study.get("completedAt"),
        "report": study.get("report"),
        "reportSha256": str(study.get("reportSha256") or ""),
        "categories": [
            {
                "ordinal": int(item["ordinal"]),
                "categoryId": str(item["categoryId"]),
                "categoryLabel": str(item["categoryLabel"]),
                "researchCharacteristic": str(
                    _fixture_category(study["fixture"], str(item["categoryId"]))[
                        "researchCharacteristic"
                    ]
                ),
                "focusedJobId": int(item["focusedJobId"]),
                "focusedJob": item.get("focusedJob"),
                "shadow": {
                    "sealed": True,
                    "revealed": revealed,
                    "responseCount": len(
                        _fixture_category(study["fixture"], str(item["categoryId"]))[
                            "contributions"
                        ]
                    ),
                    "leadCount": sum(
                        int(value["leadCount"])
                        for value in _fixture_category(
                            study["fixture"], str(item["categoryId"])
                        )["contributions"]
                    ),
                    "sealSha256": str(item["shadowSealSha256"]),
                },
                "reviewAssignment": item.get("reviewAssignment") if revealed else None,
                "reviewAssignmentSha256": (
                    str(item.get("reviewAssignmentSha256") or "") if revealed else ""
                ),
                "reviewResult": item.get("reviewResult") if revealed else None,
                "reviewResultSha256": (
                    str(item.get("reviewResultSha256") or "") if revealed else ""
                ),
            }
            for item in study["categories"]
        ],
    }


def close_blind_codex_arm(store: ResearchStore, study_id: int) -> dict[str, Any]:
    study = store.get_blind_comparison_study(study_id)
    if not study:
        raise ValueError("Blind comparison study not found")
    if study["status"] in {"codex-closed", "revealed", "reviewing", "completed"}:
        return blind_comparison_view(study)
    if study["status"] != "researching":
        raise ValueError("Blind comparison is not collecting Codex research")
    for category in study["categories"]:
        close_focused_research_job(store, int(category["focusedJobId"]))
    study = store.transition_blind_comparison_study(
        study_id, allowed_statuses={"researching"}, status="codex-closed"
    )
    return blind_comparison_view(study)


def reveal_blind_shadows(store: ResearchStore, study_id: int) -> dict[str, Any]:
    study = store.get_blind_comparison_study(study_id)
    if not study:
        raise ValueError("Blind comparison study not found")
    if study["status"] in {"revealed", "reviewing", "completed"}:
        return blind_comparison_view(study)
    if study["status"] != "codex-closed":
        raise ValueError("Close every Codex result before revealing shadow results")
    _validate_fixture(store, study["fixture"])
    for category in study["categories"]:
        actual_sha = _sha(_actual_seal(store, int(category["shadowRunId"])))
        if actual_sha != str(category["shadowSealSha256"]):
            raise ValueError(
                f"Held-out {category['categoryId']} shadow seal no longer matches"
            )
    study = store.transition_blind_comparison_study(
        study_id, allowed_statuses={"codex-closed"}, status="revealed"
    )
    return blind_comparison_view(study)


def _url_identity(value: str) -> tuple[str, str]:
    parsed = urlsplit(str(value or ""))
    return (
        (parsed.hostname or "").casefold().removeprefix("www."),
        re.sub(r"/+$", "", parsed.path.casefold()) or "/",
    )


def _tokens(value: str) -> set[str]:
    ignored = {"and", "for", "the", "services", "service", "program", "center"}
    return {
        item for item in normalize_manual_identity(value).split()
        if len(item) >= 3 and item not in ignored
    }


def _coverage(left: set[str], right: set[str]) -> float:
    return len(left & right) / max(1, min(len(left), len(right)))


def _same_identity(left: dict[str, Any], right: dict[str, Any]) -> bool:
    left_host, left_path = _url_identity(left.get("website") or "")
    right_host, right_path = _url_identity(right.get("website") or "")
    left_name = _tokens(left.get("displayName") or "")
    right_name = _tokens(right.get("displayName") or "")
    left_org = _tokens(left.get("organization") or "")
    right_org = _tokens(right.get("organization") or "")
    left_program = _tokens(left.get("program") or "")
    right_program = _tokens(right.get("program") or "")
    same_url = bool(
        left_host and left_host == right_host
        and left_path == right_path
    )
    same_org_site = bool(
        left_host and left_host == right_host
        and _coverage(left_org or left_name, right_org or right_name) >= 0.6
        and (
            not left_program or not right_program
            or _coverage(left_program, right_program) >= 0.5
        )
    )
    strong_name = bool(
        len(left_name & right_name) >= 2 and _coverage(left_name, right_name) >= 0.82
    )
    return same_url or same_org_site or strong_name


def _group_record(group: dict[str, Any], arm: str) -> dict[str, Any]:
    members = group.get("members") or []
    source_names = (
        {"Codex"}
        if arm == "Codex"
        else {
            str(item.get("sourceLabel") or "") for item in members
            if str(item.get("sourceLabel") or "") in SHADOW_SOURCES
        }
    )
    def first(field: str) -> str:
        return next(
            (str(item.get(field) or "").strip() for item in members if item.get(field)),
            "",
        )
    return {
        "stableKey": str(group.get("stableKey") or ""),
        "displayName": str(group.get("displayName") or ""),
        "organization": str(group.get("organization") or ""),
        "program": str(group.get("program") or ""),
        "website": str(group.get("website") or ""),
        "phone": first("phone"),
        "address": first("address"),
        "locationOrServiceArea": first("locationOrServiceArea"),
        "whyRelevant": sorted({
            str(item.get("whyRelevant") or "").strip()
            for item in members if str(item.get("whyRelevant") or "").strip()
        }, key=str.casefold),
        "uncertainty": sorted({
            str(item.get("uncertainty") or "").strip()
            for item in members if str(item.get("uncertainty") or "").strip()
        }, key=str.casefold),
        "sources": source_names,
        "members": [{"arm": arm, "stableKey": str(group.get("stableKey") or "")}],
    }


def _comparison_candidates(
    store: ResearchStore, study: dict[str, Any], category: dict[str, Any]
) -> list[dict[str, Any]]:
    focused = category.get("focusedJob") or store.get_focused_research_job(
        int(category["focusedJobId"])
    )
    codex_snapshot = store.manual_consolidation_snapshot(int(focused["runId"]))
    shadow_snapshot = store.manual_consolidation_snapshot(int(category["shadowRunId"]))
    if not codex_snapshot or not shadow_snapshot:
        raise ValueError("Blind comparison needs both consolidated result sets")
    records = [
        *[_group_record(item, "Codex") for item in codex_snapshot["groups"]],
        *[_group_record(item, "shadow") for item in shadow_snapshot["groups"]],
    ]
    unions: list[dict[str, Any]] = []
    for record in records:
        owner = next((item for item in unions if _same_identity(item, record)), None)
        if owner is None:
            unions.append(record)
            continue
        owner["sources"].update(record["sources"])
        owner["members"].extend(record["members"])
        owner["whyRelevant"] = sorted(
            set(owner["whyRelevant"]) | set(record["whyRelevant"]), key=str.casefold
        )
        owner["uncertainty"] = sorted(
            set(owner["uncertainty"]) | set(record["uncertainty"]), key=str.casefold
        )
        for field in ("website", "phone", "address", "locationOrServiceArea"):
            if not owner.get(field) and record.get(field):
                owner[field] = record[field]
        if len(str(record.get("displayName") or "")) > len(str(owner.get("displayName") or "")):
            owner["displayName"] = record["displayName"]
    for item in unions:
        identity_basis = sorted(
            f"{member['arm']}:{member['stableKey']}" for member in item["members"]
        )
        item["id"] = "comparison-" + hashlib.sha256(
            (str(category["categoryId"]) + "\n" + "\n".join(identity_basis)).encode("utf-8")
        ).hexdigest()[:20]
        item["sources"] = sorted(item["sources"], key=str.casefold)
        item["members"] = sorted(
            item["members"], key=lambda value: (value["arm"], value["stableKey"])
        )
    return sorted(unions, key=lambda item: (item["displayName"].casefold(), item["id"]))


def build_blind_review_assignment(
    store: ResearchStore, study_id: int, category_id: str
) -> dict[str, Any]:
    study = store.get_blind_comparison_study(study_id)
    if not study:
        raise ValueError("Blind comparison study not found")
    if study["status"] not in {"revealed", "reviewing", "completed"}:
        raise ValueError("Shadow results remain sealed until Codex closes")
    category = next(
        (item for item in study["categories"] if item["categoryId"] == category_id),
        None,
    )
    if not category:
        raise ValueError("Blind comparison category not found")
    if category.get("reviewAssignment"):
        return category["reviewAssignment"]
    comparison = _comparison_candidates(store, study, category)
    known = [
        {
            "id": str(item.get("resourceId") or ""),
            "name": str(item.get("name") or ""),
            "website": str((item.get("fullRecord") or {}).get("website") or ""),
        }
        for item in store.list_seeds(int(category["importId"]), category_id)
    ]
    assignment = {
        "blindReviewSchemaVersion": BLIND_REVIEW_SCHEMA_VERSION,
        "studyId": study_id,
        "categoryId": category_id,
        "categoryLabel": str(category["categoryLabel"]),
        "serviceArea": str(study["fixture"]["location"]["serviceArea"]),
        "curationAssignmentVersion": SCOUT_CURATION_ASSIGNMENT_VERSION,
        "sourceAttributionHidden": True,
        "knownResources": sorted(known, key=lambda item: item["name"].casefold()),
        "candidates": [
            {
                "id": item["id"],
                "name": item["displayName"],
                "organization": item["organization"],
                "program": item["program"],
                "website": item["website"],
                "phone": item["phone"],
                "address": item["address"],
                "locationOrServiceArea": item["locationOrServiceArea"],
                "whyRelevant": item["whyRelevant"],
                "uncertainty": item["uncertainty"],
            }
            for item in comparison
        ],
        "curationPolicy": {
            "objective": "Keep the smallest high-confidence set of distinct, current, actionable direct services.",
            "directServiceTest": "The named program itself must directly provide a substantial service that a person would seek in this category.",
            "portfolioGuidance": "Prefer fewer strong additions; do not keep a marginal candidate to meet a quota.",
            "evidenceRule": "A broken page alone does not prove closure; preserve uncertainty and use current official or primary evidence.",
        },
        "instructions": [
            "Review every source-hidden candidate under the same policy.",
            "Mark curated only when the candidate is distinct, current, actionable, geographically relevant, and passes the direct-service test.",
            "Mark already-known when the connected package already represents the same program.",
            "Mark duplicate only when another candidate in this assignment represents the same program, and identify that candidate.",
            "Use needs-research rather than guessing when evidence is genuinely insufficient.",
            "Do not infer a model or source from writing style, ordering, or candidate detail.",
        ],
        "outputContract": {
            "assignmentSha256": "Copy from this assignment.",
            "categoryId": category_id,
            "dispositions": [{
                "candidateId": "every candidate exactly once",
                "outcome": "curated | omit | already-known | needs-research | duplicate",
                "duplicateOf": "required only for duplicate",
                "reason": "required except for curated",
                "evidence": ["brief evidence or decision basis"],
            }],
            "reviewEffort": {
                "durationSeconds": "non-negative integer",
                "editCount": "non-negative integer",
                "adjudicationCount": "non-negative integer",
            },
        },
    }
    assignment["assignmentSha256"] = _sha(assignment)
    store.save_blind_review_assignment(
        study_id, category_id, assignment, assignment["assignmentSha256"]
    )
    return assignment


def save_blind_review_result(
    store: ResearchStore,
    study_id: int,
    category_id: str,
    result: dict[str, Any],
) -> dict[str, Any]:
    study = store.get_blind_comparison_study(study_id)
    if not study:
        raise ValueError("Blind comparison study not found")
    category = next(
        (item for item in study["categories"] if item["categoryId"] == category_id),
        None,
    )
    if not category or not category.get("reviewAssignment"):
        raise ValueError("Read the blind review assignment before submitting results")
    assignment = category["reviewAssignment"]
    if str(result.get("assignmentSha256") or "") != str(
        assignment["assignmentSha256"]
    ):
        raise ValueError("Blind review result does not match its sealed assignment")
    if str(result.get("categoryId") or "") != category_id:
        raise ValueError("Blind review result category changed")
    dispositions = result.get("dispositions")
    if not isinstance(dispositions, list):
        raise ValueError("Blind review dispositions must be an array")
    candidate_ids = {str(item["id"]) for item in assignment["candidates"]}
    submitted_ids = [str(item.get("candidateId") or "") for item in dispositions]
    if set(submitted_ids) != candidate_ids or len(submitted_ids) != len(candidate_ids):
        raise ValueError("Blind review must cover every candidate exactly once")
    allowed = {"curated", "omit", "already-known", "needs-research", "duplicate"}
    by_id = {str(item["candidateId"]): item for item in dispositions}
    for candidate_id, item in by_id.items():
        outcome = str(item.get("outcome") or "")
        if outcome not in allowed:
            raise ValueError(f"Unsupported blind review outcome: {outcome}")
        reason = str(item.get("reason") or "").strip()
        evidence = item.get("evidence") or []
        if outcome != "curated" and not reason:
            raise ValueError("Non-curated blind outcomes need a reason")
        if not isinstance(evidence, list):
            raise ValueError("Blind review evidence must be an array")
        if outcome == "duplicate":
            duplicate_of = str(item.get("duplicateOf") or "")
            if duplicate_of not in candidate_ids or duplicate_of == candidate_id:
                raise ValueError("Blind duplicate outcome needs another candidate")
            if str(by_id[duplicate_of].get("outcome") or "") == "duplicate":
                raise ValueError("Blind duplicate chains are not supported")
        elif item.get("duplicateOf"):
            raise ValueError("duplicateOf is only valid for duplicate outcomes")
    effort = result.get("reviewEffort") or {}
    if not isinstance(effort, dict):
        raise ValueError("Blind review effort must be an object")
    for field in ("durationSeconds", "editCount", "adjudicationCount"):
        try:
            value = int(effort.get(field, 0))
        except (TypeError, ValueError) as error:
            raise ValueError(f"Blind review {field} must be an integer") from error
        if value < 0:
            raise ValueError(f"Blind review {field} must not be negative")
        effort[field] = value
    normalized = {
        "assignmentSha256": str(result["assignmentSha256"]),
        "categoryId": category_id,
        "dispositions": dispositions,
        "reviewEffort": effort,
    }
    saved = store.save_blind_review_result(
        study_id, category_id, normalized, _sha(normalized)
    )
    return saved["reviewResult"]


def _parse_time(value: Any) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value)) if value else None
    except ValueError:
        return None


def _duration(start: Any, end: Any) -> int | None:
    left, right = _parse_time(start), _parse_time(end)
    return max(0, int((right - left).total_seconds())) if left and right else None


def _category_report(
    store: ResearchStore,
    study: dict[str, Any],
    category: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, set[str]]]:
    comparison = _comparison_candidates(store, study, category)
    assignment = category["reviewAssignment"]
    result = category["reviewResult"]
    if not assignment or not result:
        raise ValueError("Complete every blind category review first")
    outcomes = {
        str(item["candidateId"]): item for item in result["dispositions"]
    }
    representatives = {
        candidate_id: (
            str(item.get("duplicateOf") or candidate_id)
            if str(item.get("outcome") or "") == "duplicate" else candidate_id
        )
        for candidate_id, item in outcomes.items()
    }
    comparison_by_id = {str(item["id"]): item for item in comparison}
    source_ids = {source: set() for source in ALL_SOURCES}
    contributors: dict[str, set[str]] = {}
    for candidate_id, item in comparison_by_id.items():
        representative = representatives[candidate_id]
        contributors.setdefault(representative, set()).update(item["sources"])
        for source in item["sources"]:
            source_ids[source].add(representative)
    curated = {
        candidate_id for candidate_id, item in outcomes.items()
        if str(item.get("outcome") or "") == "curated"
    }
    source_metrics = {}
    fixture_category = _fixture_category(study["fixture"], str(category["categoryId"]))
    codex_leads = int(
        (category["focusedJob"].get("evaluation") or {}).get("submittedLeadCount") or 0
    )
    shadow_leads = {
        str(item["source"]): int(item["leadCount"])
        for item in fixture_category["contributions"]
    }
    for source in ALL_SOURCES:
        identities = source_ids[source]
        survived = identities & curated
        marginal = {
            identity for identity in survived if contributors.get(identity) == {source}
        }
        source_metrics[source] = {
            "submittedLeadCount": codex_leads if source == "Codex" else shadow_leads[source],
            "duplicateAdjustedIdentityCount": len(identities),
            "curatedIdentityCount": len(survived),
            "curationSurvivalRate": (
                round(len(survived) / len(identities), 4) if identities else None
            ),
            "marginalCuratedIdentityCount": len(marginal),
        }
    four_ai = set().union(*(source_ids[source] for source in SHADOW_SOURCES))
    codex = source_ids["Codex"]
    effort = result["reviewEffort"]
    focused = category["focusedJob"]
    shadow_run = store.get_run(int(category["shadowRunId"])) or {}
    report = {
        "categoryId": str(category["categoryId"]),
        "categoryLabel": str(category["categoryLabel"]),
        "researchCharacteristic": str(fixture_category["researchCharacteristic"]),
        "sourceMetrics": source_metrics,
        "comparison": {
            "duplicateAdjustedUnionCount": len(set(representatives.values())),
            "curatedUnionCount": len(curated),
            "codexCuratedCount": len(codex & curated),
            "fourAiCuratedCount": len(four_ai & curated),
            "sharedCuratedCount": len(codex & four_ai & curated),
            "codexOnlyCuratedCount": len((codex - four_ai) & curated),
            "fourAiOnlyCuratedCount": len((four_ai - codex) & curated),
            "needsResearchCount": sum(
                str(item.get("outcome") or "") == "needs-research"
                for item in outcomes.values()
            ),
        },
        "reviewerEffort": {
            "decisionCount": len(outcomes),
            "durationSeconds": int(effort.get("durationSeconds") or 0),
            "editCount": int(effort.get("editCount") or 0),
            "adjudicationCount": int(effort.get("adjudicationCount") or 0),
        },
        "observedResearchTime": {
            "CodexSeconds": _duration(focused.get("createdAt"), focused.get("completedAt")),
            "fourAiCollectionSeconds": _duration(
                shadow_run.get("createdAt"), shadow_run.get("completedAt")
            ),
            "note": "Historical four-AI time includes collection and pacing and is not a controlled per-model latency measure.",
        },
    }
    return report, source_ids


def complete_blind_comparison(store: ResearchStore, study_id: int) -> dict[str, Any]:
    study = store.get_blind_comparison_study(study_id)
    if not study:
        raise ValueError("Blind comparison study not found")
    if study["status"] == "completed":
        return blind_comparison_view(study)
    if study["status"] != "reviewing":
        raise ValueError("Complete the revealed source-hidden reviews before reporting")
    category_reports = []
    aggregate_ids = {source: set() for source in ALL_SOURCES}
    for category in study["categories"]:
        report, source_ids = _category_report(store, study, category)
        category_reports.append(report)
        prefix = str(category["categoryId"]) + ":"
        for source, identities in source_ids.items():
            aggregate_ids[source].update(prefix + identity for identity in identities)
    aggregate_source_metrics = {}
    for source in ALL_SOURCES:
        submitted = sum(
            int(category["sourceMetrics"][source]["submittedLeadCount"])
            for category in category_reports
        )
        identities = sum(
            int(category["sourceMetrics"][source]["duplicateAdjustedIdentityCount"])
            for category in category_reports
        )
        curated = sum(
            int(category["sourceMetrics"][source]["curatedIdentityCount"])
            for category in category_reports
        )
        marginal = sum(
            int(category["sourceMetrics"][source]["marginalCuratedIdentityCount"])
            for category in category_reports
        )
        aggregate_source_metrics[source] = {
            "submittedLeadCount": submitted,
            "duplicateAdjustedIdentityCount": identities,
            "curatedIdentityCount": curated,
            "curationSurvivalRate": round(curated / identities, 4) if identities else None,
            "marginalCuratedIdentityCount": marginal,
        }
    costs = study["fixture"].get("subscriptionContext") or {}
    subscription_evidence = {}
    for source in SHADOW_SOURCES:
        monthly = int((costs.get(source) or {}).get("monthlyUsd") or 0)
        marginal = int(aggregate_source_metrics[source]["marginalCuratedIdentityCount"])
        subscription_evidence[source] = {
            "monthlyUsd": monthly,
            "decisionRole": str((costs.get(source) or {}).get("decisionRole") or ""),
            "curatedIdentityCount": int(
                aggregate_source_metrics[source]["curatedIdentityCount"]
            ),
            "marginalCuratedIdentityCount": marginal,
            "monthlyUsdPerMarginalCuratedIdentity": (
                round(monthly / marginal, 2) if monthly and marginal else None
            ),
        }
    report = {
        "schemaVersion": 1,
        "experimentMode": BLIND_COMPARISON_EXPERIMENT_MODE,
        "status": "complete",
        "fixtureSha256": str(study["fixtureSha256"]),
        "curationAssignmentVersion": str(study["curationAssignmentVersion"]),
        "location": study["fixture"]["location"],
        "heldOutCategoryCount": len(category_reports),
        "categories": category_reports,
        "aggregateSourceMetrics": aggregate_source_metrics,
        "aggregateComparison": {
            key: sum(int(category["comparison"][key]) for category in category_reports)
            for key in (
                "duplicateAdjustedUnionCount", "curatedUnionCount",
                "codexCuratedCount", "fourAiCuratedCount", "sharedCuratedCount",
                "codexOnlyCuratedCount", "fourAiOnlyCuratedCount", "needsResearchCount",
            )
        },
        "reviewerEffort": {
            key: sum(int(category["reviewerEffort"][key]) for category in category_reports)
            for key in ("decisionCount", "durationSeconds", "editCount", "adjudicationCount")
        },
        "subscriptionEvidence": subscription_evidence,
        "interpretationBoundary": (
            "This one-location, four-category blind comparison is evidence for the "
            "subscription decision, not automatic authority to disable a researcher."
        ),
    }
    report_sha = _sha(report)
    completed = store.complete_blind_comparison_study(study_id, report, report_sha)
    return blind_comparison_view(completed)
