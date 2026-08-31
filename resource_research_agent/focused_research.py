from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .manual_discovery import build_manual_discovery_assignment, normalize_manual_identity
from .manual_consolidation import (
    consolidate_manual_discovery,
    finish_manual_discovery,
    leave_pending_manual_identities_unresolved,
)
from .playbooks import CategoryPlaybook, ResearchFocus, playbook_for
from .storage import ResearchStore


EVIDENCE_PATH = Path(__file__).with_name("research_evidence") / "employment_recovery_baseline.json"
FOCUSED_RESEARCH_EXPERIMENT_MODE = "employment-retrospective-v1"


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def json_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def text_sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def load_employment_recovery_baseline() -> dict[str, Any]:
    value = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("Employment recovery evidence must be one JSON object")
    return value


def _location_name(office_name: str, service_area: str) -> str:
    value = re.sub(r"\s+TSO$", "", str(office_name or ""), flags=re.IGNORECASE).strip()
    if value:
        return value
    return str(service_area or "Location").split(",", 1)[0].strip() or "Location"


def _focus_dict(focus: ResearchFocus) -> dict[str, Any]:
    return {
        "key": focus.key,
        "label": focus.label,
        "direction": focus.direction,
        "coverage": list(focus.coverage),
        "vocabulary": list(focus.vocabulary),
        "sourceChannels": list(focus.source_channels),
    }


def build_focused_plan(
    playbook: CategoryPlaybook,
    *,
    import_id: int,
    category_id: str,
    category_label: str,
    office_name: str,
    service_area: str,
) -> dict[str, Any]:
    focused = playbook.focused_research
    if focused is None:
        raise ValueError(f"{category_label} does not have focused research guidance")
    return {
        "schemaVersion": 1,
        "experimentMode": FOCUSED_RESEARCH_EXPERIMENT_MODE,
        "importId": int(import_id),
        "locationName": _location_name(office_name, service_area),
        "officeName": office_name,
        "serviceArea": service_area,
        "category": {"id": category_id, "label": category_label},
        "playbookVersion": focused.version,
        "playbookLibraryVersion": playbook.library_version,
        "playbookSource": playbook.source,
        "alternativeVocabulary": list(focused.alternative_vocabulary),
        "sourceChannels": list(focused.source_channels),
        "include": list(playbook.scope),
        "exclude": list(playbook.exclusions),
        "focuses": [_focus_dict(focus) for focus in focused.focuses],
        "gapPass": {
            "key": "gap",
            "label": "Coverage gap follow-up",
            "kind": "gap",
        },
    }


def _target_terms(location_name: str) -> tuple[set[str], set[str]]:
    baseline = load_employment_recovery_baseline()
    names: set[str] = set()
    hosts: set[str] = set()
    for target in baseline["primaryTargets"] + baseline["secondaryTargets"]:
        if str(target.get("location") or "").casefold() != location_name.casefold():
            continue
        names.add(normalize_manual_identity(target.get("name")))
        host = (urlsplit(str(target.get("website") or "")).hostname or "").casefold()
        if host:
            hosts.add(host.removeprefix("www."))
    return names, hosts


def _contains_target(value: dict[str, Any], location_name: str) -> bool:
    target_names, target_hosts = _target_terms(location_name)
    normalized_name = normalize_manual_identity(value.get("name") or value.get("organization"))
    if normalized_name and any(
        normalized_name == target or normalized_name in target or target in normalized_name
        for target in target_names
    ):
        return True
    host = (urlsplit(str(value.get("website") or "")).hostname or "").casefold()
    return bool(host and host.removeprefix("www.") in target_hosts)


def build_known_resource_manifest(
    store: ResearchStore,
    import_id: int,
    category_id: str,
    location_name: str,
    *,
    redact_recovery_targets: bool = True,
) -> list[dict[str, str]]:
    resources = [
        {
            "id": str(seed.get("resourceId") or ""),
            "name": str(seed.get("name") or ""),
            "website": str((seed.get("fullRecord") or {}).get("website") or ""),
        }
        for seed in store.list_seeds(import_id, category_id)
    ]
    if redact_recovery_targets:
        resources = [item for item in resources if not _contains_target(item, location_name)]
    return sorted(resources, key=lambda item: (item["name"].casefold(), item["id"]))


def build_candidate_manifest(store: ResearchStore, run_id: int) -> list[dict[str, str]]:
    identities: dict[tuple[str, str, str], dict[str, str]] = {}
    for lead in store.manual_leads_for_consolidation(run_id):
        key = (
            str(lead.get("normalizedOrganization") or ""),
            str(lead.get("normalizedProgram") or ""),
            str(lead.get("website") or ""),
        )
        if not any(key):
            continue
        identities.setdefault(key, {
            "organization": str(lead.get("organization") or ""),
            "program": str(lead.get("program") or ""),
            "website": str(lead.get("website") or ""),
        })
    return sorted(
        identities.values(),
        key=lambda item: (
            item["organization"].casefold(),
            item["program"].casefold(),
            item["website"],
        ),
    )


def _manifest_lines(values: list[dict[str, str]], *, known: bool) -> list[str]:
    if not values:
        return ["- None."]
    lines: list[str] = []
    for value in values:
        if known:
            label = value["name"]
        else:
            label = " · ".join(
                item for item in (value["organization"], value["program"]) if item
            ) or value["website"]
        suffix = f" — {value['website']}" if value.get("website") else ""
        lines.append(f"- {label}{suffix}")
    return lines


def build_focus_assignment(
    plan: dict[str, Any],
    focus: dict[str, Any],
    known_resources: list[dict[str, str]],
    candidates: list[dict[str, str]],
) -> str:
    base = build_manual_discovery_assignment(
        category_label=plan["category"]["label"],
        service_area=plan["serviceArea"],
        office_name=plan["officeName"],
        known_resources=[],
        include=plan["include"],
        exclude=plan["exclude"],
    )
    return "\n".join([
        f"Resource Scout focused research pass: {focus['label']}",
        f"Focus key: {focus['key']}",
        str(focus["direction"]),
        "",
        "Coverage to seek:",
        *[f"- {item}" for item in focus.get("coverage") or []],
        "",
        "Useful alternative vocabulary:",
        *[f"- {item}" for item in (
            list(plan.get("alternativeVocabulary") or [])
            + list(focus.get("vocabulary") or [])
        )],
        "",
        "Source channels to search deliberately:",
        *[f"- {item}" for item in (
            list(plan.get("sourceChannels") or [])
            + list(focus.get("sourceChannels") or [])
        )],
        "",
        "Resources already in the connected package; do not return obvious repeats:",
        *_manifest_lines(known_resources, known=True),
        "",
        "Candidate identities already found in earlier focused passes; do not return obvious repeats:",
        *_manifest_lines(candidates, known=False),
        "",
        base,
        "",
        "This is a focused pass. Do not broaden it into another general Employment list.",
    ])


def prepare_focused_research_job(
    store: ResearchStore,
    import_id: int | None = None,
    category_id: str = "employment",
) -> dict[str, Any]:
    selected_import_id = int(import_id or store.latest_import_id() or 0)
    if not selected_import_id:
        raise ValueError("Connect a resource package before focused research")
    summary = store.import_summary(selected_import_id)
    category = store.import_category(selected_import_id, category_id)
    if not summary or not category:
        raise ValueError("The focused research category is not in the connected package")
    playbook = playbook_for(
        str(category["id"]),
        str(category["label"]),
        str(summary.get("serviceArea") or ""),
    )
    plan = build_focused_plan(
        playbook,
        import_id=selected_import_id,
        category_id=str(category["id"]),
        category_label=str(category["label"]),
        office_name=str(summary.get("officeName") or ""),
        service_area=str(summary.get("serviceArea") or ""),
    )
    plan_sha = json_sha256(plan)
    existing = store.find_focused_research_job(
        selected_import_id,
        str(category["id"]),
        plan["playbookVersion"],
        plan_sha,
        FOCUSED_RESEARCH_EXPERIMENT_MODE,
    )
    if existing:
        return existing
    location_name = str(plan["locationName"])
    known_resources = build_known_resource_manifest(
        store, selected_import_id, str(category["id"]), location_name
    )
    baseline_sha = json_sha256(known_resources)
    assignment = (
        f"Complete the versioned {plan['playbookVersion']} focused research plan "
        f"for {category['label']} in {summary.get('serviceArea')}."
    )
    run_id = store.create_manual_discovery_run(
        assignment,
        {
            "assignment": assignment,
            "focusedResearchPlan": plan,
            "planSha256": plan_sha,
            "researchContext": {
                "mode": "package",
                "sourcePackage": {
                    "importId": selected_import_id,
                    "sourceName": summary.get("sourceName"),
                    "sourceSha256": summary.get("sourceSha256"),
                    "contentSha256": summary.get("contentSha256"),
                },
            },
        },
        selected_import_id,
        target_location=str(summary.get("serviceArea") or ""),
        target_category_id=str(category["id"]),
        target_category_label=str(category["label"]),
    )
    try:
        return store.create_focused_research_job(
            run_id=run_id,
            import_id=selected_import_id,
            category_id=str(category["id"]),
            category_label=str(category["label"]),
            location_name=location_name,
            service_area=str(summary.get("serviceArea") or ""),
            playbook_version=plan["playbookVersion"],
            experiment_mode=FOCUSED_RESEARCH_EXPERIMENT_MODE,
            plan=plan,
            plan_sha256=plan_sha,
            baseline_manifest_sha256=baseline_sha,
            passes=plan["focuses"],
        )
    except Exception:
        store.delete_empty_manual_discovery_run(run_id)
        raise


def next_focused_research_assignment(
    store: ResearchStore,
    job_id: int,
) -> dict[str, Any] | None:
    job = store.get_focused_research_job(job_id)
    if not job:
        raise ValueError("Focused research job not found")
    current = next(
        (item for item in job["passes"] if item["status"] == "assigned"), None
    )
    if current:
        return current
    research_pass = next(
        (item for item in job["passes"] if item["status"] == "pending"), None
    )
    if not research_pass:
        return None
    known = build_known_resource_manifest(
        store,
        int(job["importId"]),
        str(job["categoryId"]),
        str(job["locationName"]),
    )
    candidates = build_candidate_manifest(store, int(job["runId"]))
    manifest_sha = json_sha256({"known": known, "candidates": candidates})
    assignment = build_focus_assignment(
        job["plan"], research_pass["definition"], known, candidates
    )
    return store.assign_focused_research_pass(
        job_id,
        str(research_pass["focusKey"]),
        assignment,
        text_sha256(assignment),
        manifest_sha,
    )


def save_focused_research_result(
    store: ResearchStore,
    job_id: int,
    focus_key: str,
    raw_text: str,
) -> dict[str, Any]:
    job = store.get_focused_research_job(job_id)
    if not job:
        raise ValueError("Focused research job not found")
    research_pass = next(
        (item for item in job["passes"] if item["focusKey"] == focus_key), None
    )
    if not research_pass:
        raise ValueError("Focused research pass not found")
    if research_pass["status"] == "completed":
        contribution = store.get_manual_contribution(
            int(job["runId"]), int(research_pass["contributionId"])
        )
        if contribution and contribution["rawText"] == raw_text:
            return research_pass
        raise ValueError("Completed focused research pass is immutable")
    if research_pass["status"] != "assigned":
        raise ValueError("Read the focused research assignment before submitting a result")
    source_label = f"Codex · {research_pass['focusLabel']}"
    contribution = store.save_manual_contribution(
        int(job["runId"]), source_label, raw_text
    )
    if contribution["parseStatus"] != "parsed":
        raise ValueError(
            "Correct the focused research response before completing the pass: "
            + str(contribution.get("parseError") or "invalid response")
        )
    return store.complete_focused_research_pass(
        job_id,
        focus_key,
        int(contribution["id"]),
        len(contribution["leads"]),
        {"coverage": research_pass["definition"].get("coverage") or []},
    )


def prepare_focused_gap_pass(
    store: ResearchStore,
    job_id: int,
) -> dict[str, Any]:
    job = store.get_focused_research_job(job_id)
    if not job:
        raise ValueError("Focused research job not found")
    existing = next(
        (item for item in job["passes"] if item["focusKey"] == "gap"), None
    )
    if existing:
        return existing
    fixed = [item for item in job["passes"] if item["passKind"] == "focus"]
    if any(item["status"] != "completed" for item in fixed):
        raise ValueError("Complete every fixed focus before creating the gap pass")

    snapshot = consolidate_manual_discovery(store, int(job["runId"]))
    missing = [item["focusLabel"] for item in fixed if int(item["leadCount"]) == 0]
    low_yield = [
        item["focusLabel"] for item in fixed if 0 < int(item["leadCount"]) <= 1
    ]
    candidate_count = int(snapshot["funnel"]["candidateIdentities"])
    identity_count = int(snapshot["funnel"]["consolidatedIdentities"])
    if missing:
        direction = (
            "Search only the remaining zero-yield coverage areas, using different "
            "vocabulary and source channels from the fixed passes."
        )
    elif low_yield:
        direction = (
            "Search the lowest-yield coverage areas for overlooked direct-service "
            "programs, using different vocabulary and source channels."
        )
    else:
        direction = (
            "Make one final adversarial search for direct-service Employment programs "
            "that the fixed passes and current candidate manifest may have missed."
        )
    definition = {
        "key": "gap",
        "label": "Coverage gap follow-up",
        "kind": "gap",
        "direction": direction,
        "coverage": missing or low_yield or [
            "non-obvious direct-service programs absent from the current candidate manifest"
        ],
        "vocabulary": [
            "use synonyms not already dominant in the current candidates",
            "search by service pathway, population, provider type, and referral route",
        ],
        "sourceChannels": [
            "official provider and government pages not represented in earlier passes",
            "credible referral partners that identify the operating provider",
        ],
        "gapAnalysis": {
            "fixedPassLeadCounts": {
                item["focusKey"]: int(item["leadCount"]) for item in fixed
            },
            "missingFocusLabels": missing,
            "lowYieldFocusLabels": low_yield,
            "consolidatedIdentityCount": identity_count,
            "candidateIdentityCount": candidate_count,
        },
    }
    return store.add_focused_gap_pass(job_id, definition)


def _url_identity(value: str) -> tuple[str, str]:
    parsed = urlsplit(str(value or ""))
    host = (parsed.hostname or "").casefold().removeprefix("www.")
    path = re.sub(r"/+$", "", parsed.path.casefold()) or "/"
    return host, path


def _identity_tokens(value: str) -> set[str]:
    return {
        token for token in normalize_manual_identity(value).split()
        if len(token) >= 3 and token not in {"and", "for", "the", "services", "program"}
    }


def _automatic_target_match(
    target: dict[str, Any], groups: list[dict[str, Any]]
) -> dict[str, Any] | None:
    target_host, target_path = _url_identity(str(target.get("website") or ""))
    target_tokens = _identity_tokens(str(target.get("name") or ""))
    ranked: list[tuple[tuple[int, int, int], dict[str, Any], list[str]]] = []
    for group in groups:
        group_host, group_path = _url_identity(str(group.get("website") or ""))
        group_tokens = _identity_tokens(" ".join([
            str(group.get("displayName") or ""),
            str(group.get("organization") or ""),
            str(group.get("program") or ""),
        ]))
        shared = target_tokens & group_tokens
        coverage = len(shared) / max(1, min(len(target_tokens), len(group_tokens)))
        exact_url = bool(
            target_host and group_host == target_host
            and (target_path == group_path or target_path == "/" or group_path == "/")
        )
        organization_domain = bool(
            target_host and group_host == target_host and coverage >= 0.34
        )
        strong_name = bool(coverage >= 0.72 and len(shared) >= 2)
        if not (exact_url or organization_domain or strong_name):
            continue
        signals = []
        if exact_url:
            signals.append("same normalized official URL")
        elif organization_domain:
            signals.append("same official domain with matching identity terms")
        if strong_name:
            signals.append("strong normalized organization or program identity")
        ranked.append((
            (int(exact_url), int(organization_domain), len(shared)),
            group,
            signals,
        ))
    if not ranked:
        return None
    _score, group, signals = max(ranked, key=lambda item: item[0])
    return {
        "candidateStableKey": group["stableKey"],
        "candidateName": group["displayName"],
        "candidateWebsite": group["website"],
        "evidence": signals,
        "researchFocusKeys": sorted({
            str(member.get("researchFocusKey") or "")
            for member in group["members"]
            if member.get("researchFocusKey")
        }),
        "sourceLabels": sorted({
            str(member.get("sourceLabel") or "")
            for member in group["members"]
            if member.get("sourceLabel")
        }, key=str.casefold),
    }


def evaluate_focused_research_job(
    store: ResearchStore,
    job_id: int,
    adjudications: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    job = store.get_focused_research_job(job_id)
    if not job:
        raise ValueError("Focused research job not found")
    if job["status"] == "completed":
        return job
    if not any(item["passKind"] == "gap" for item in job["passes"]):
        raise ValueError("Create and complete the coverage gap pass before evaluation")
    if any(item["status"] != "completed" for item in job["passes"]):
        raise ValueError("Complete every focused research pass before evaluation")

    snapshot = consolidate_manual_discovery(store, int(job["runId"]))
    if any(item["status"] == "pending" for item in snapshot["suggestions"]):
        snapshot = leave_pending_manual_identities_unresolved(
            store, int(job["runId"])
        )
    groups = snapshot["groups"]
    groups_by_key = {str(group["stableKey"]): group for group in groups}
    overrides: dict[str, dict[str, Any]] = {}
    for item in adjudications or []:
        if not isinstance(item, dict):
            raise ValueError("Each recovery adjudication must be one object")
        key = str(item.get("targetKey") or "")
        outcome = str(item.get("outcome") or "")
        evidence = item.get("evidence") or []
        if outcome not in {
            "credible-equivalent", "parent-only", "ambiguous", "missed"
        }:
            raise ValueError(
                "Adjudications may mark credible-equivalent, parent-only, ambiguous, or missed"
            )
        if outcome != "missed" and (
            not str(item.get("candidateStableKey") or "")
            or not isinstance(evidence, list)
            or not any(str(value).strip() for value in evidence)
            or not str(item.get("note") or "").strip()
        ):
            raise ValueError("A recovery adjudication needs a candidate, note, and evidence")
        overrides[key] = item

    baseline = load_employment_recovery_baseline()
    location = str(job["locationName"])
    targets = [
        {**target, "tier": tier}
        for tier, values in (
            ("primary", baseline["primaryTargets"]),
            ("secondary", baseline["secondaryTargets"]),
        )
        for target in values
        if str(target.get("location") or "").casefold() == location.casefold()
    ]
    target_keys = {str(target["key"]) for target in targets}
    unknown_adjudications = sorted(set(overrides) - target_keys)
    if unknown_adjudications:
        raise ValueError(
            "Recovery adjudication target not found: " + ", ".join(unknown_adjudications)
        )
    outcomes = []
    for target in targets:
        automatic = _automatic_target_match(target, groups)
        override = overrides.get(str(target["key"]))
        if automatic:
            outcome = "exact"
            match = automatic
        elif override and override["outcome"] != "missed":
            candidate_key = str(override["candidateStableKey"])
            candidate = groups_by_key.get(candidate_key)
            if not candidate:
                raise ValueError(f"Recovery adjudication candidate not found: {candidate_key}")
            outcome = str(override["outcome"])
            match = {
                "candidateStableKey": candidate_key,
                "candidateName": candidate["displayName"],
                "candidateWebsite": candidate["website"],
                "evidence": [str(value) for value in override["evidence"]],
                "note": str(override.get("note") or ""),
                "researchFocusKeys": sorted({
                    str(member.get("researchFocusKey") or "")
                    for member in candidate["members"]
                    if member.get("researchFocusKey")
                }),
                "sourceLabels": sorted({
                    str(member.get("sourceLabel") or "")
                    for member in candidate["members"]
                    if member.get("sourceLabel")
                }, key=str.casefold),
            }
        else:
            outcome = "missed"
            match = {
                "evidence": [str(value) for value in (override or {}).get("evidence") or []],
                "note": str((override or {}).get("note") or ""),
            }
        outcomes.append({
            "targetKey": target["key"],
            "tier": target["tier"],
            "name": target["name"],
            "website": target["website"],
            "branches": target["branches"],
            "outcome": outcome,
            "match": match,
        })

    primary = [item for item in outcomes if item["tier"] == "primary"]
    recovered = [
        item for item in primary
        if item["outcome"] in {"exact", "credible-equivalent"}
    ]
    branch_names = sorted({branch for item in primary for branch in item["branches"]})
    evaluation = {
        "schemaVersion": 1,
        "experimentMode": job["experimentMode"],
        "locationName": location,
        "playbookVersion": job["playbookVersion"],
        "threshold": {"required": 8, "available": 9},
        "locationPrimaryTargetCount": len(primary),
        "locationPrimaryRecoveredCount": len(recovered),
        "combinedThresholdPending": True,
        "candidateIdentityCount": int(snapshot["funnel"]["candidateIdentities"]),
        "consolidatedIdentityCount": int(snapshot["funnel"]["consolidatedIdentities"]),
        "branchCoverage": {
            branch: {
                "targets": sum(branch in item["branches"] for item in primary),
                "recovered": sum(
                    branch in item["branches"]
                    and item["outcome"] in {"exact", "credible-equivalent"}
                    for item in primary
                ),
            }
            for branch in branch_names
        },
        "outcomes": outcomes,
        "funnel": {
            "submittedRows": int(snapshot["funnel"]["submittedRows"]),
            "exactDuplicateRows": int(snapshot["funnel"]["exactDuplicateRows"]),
            "possiblePackageDuplicates": int(
                snapshot["funnel"]["possiblePackageDuplicates"]
            ),
        },
        "proposedLessons": [
            {
                "status": "inactive",
                "branch": branch,
                "reason": "A primary recovery target in this branch was not rediscovered.",
            }
            for branch in sorted({
                branch
                for item in primary
                if item["outcome"] not in {"exact", "credible-equivalent"}
                for branch in item["branches"]
            })
        ],
    }
    final_manifest_sha = json_sha256([
        {
            "stableKey": group["stableKey"],
            "displayName": group["displayName"],
            "website": group["website"],
            "memberLeadIds": sorted(member["id"] for member in group["members"]),
        }
        for group in groups
    ])
    finish_manual_discovery(store, int(job["runId"]))
    return store.complete_focused_research_job(
        job_id,
        final_manifest_sha,
        evaluation,
        json_sha256(evaluation),
    )


def employment_retrospective_report(store: ResearchStore) -> dict[str, Any]:
    completed_by_location: dict[str, dict[str, Any]] = {}
    for job in store.list_focused_research_jobs():
        if (
            job["experimentMode"] == FOCUSED_RESEARCH_EXPERIMENT_MODE
            and job["categoryId"] == "employment"
            and job["status"] == "completed"
            and job.get("evaluation")
        ):
            completed_by_location.setdefault(str(job["locationName"]), job)
    required_locations = ["Mesa", "Provo"]
    missing = [name for name in required_locations if name not in completed_by_location]
    evaluations = [
        completed_by_location[name]["evaluation"]
        for name in required_locations if name in completed_by_location
    ]
    outcomes = [item for value in evaluations for item in value["outcomes"]]
    primary = [item for item in outcomes if item["tier"] == "primary"]
    recovered = [
        item for item in primary
        if item["outcome"] in {"exact", "credible-equivalent"}
    ]
    outcome_counts = {
        outcome: sum(item["outcome"] == outcome for item in outcomes)
        for outcome in (
            "exact", "credible-equivalent", "parent-only", "ambiguous", "missed"
        )
    }
    report = {
        "schemaVersion": 1,
        "experimentMode": FOCUSED_RESEARCH_EXPERIMENT_MODE,
        "status": "complete" if not missing else "waiting",
        "missingLocations": missing,
        "locations": [
            {
                "locationName": name,
                "jobId": completed_by_location[name]["id"],
                "evaluationSha256": completed_by_location[name]["evaluationSha256"],
                "primaryRecovered": completed_by_location[name]["evaluation"][
                    "locationPrimaryRecoveredCount"
                ],
                "primaryTargets": completed_by_location[name]["evaluation"][
                    "locationPrimaryTargetCount"
                ],
            }
            for name in required_locations if name in completed_by_location
        ],
        "threshold": {
            "required": 8,
            "available": 9,
            "recovered": len(recovered),
            "met": len(recovered) >= 8 if not missing else None,
        },
        "outcomeCounts": outcome_counts,
        "outcomes": outcomes,
        "proposedLessons": [
            {"status": "inactive", "branch": branch, "reason": reason}
            for branch, reason in sorted({
                (item["branch"], item["reason"])
                for value in evaluations
                for item in value["proposedLessons"]
            })
        ],
    }
    report["reportSha256"] = json_sha256(report)
    return report
