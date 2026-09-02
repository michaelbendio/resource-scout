from __future__ import annotations

import copy
import re
from collections import Counter
from datetime import datetime
from typing import Any
from urllib.parse import urlsplit

from .focused_research import (
    CODEX_FIRST_EXPERIMENT_MODE,
    build_known_resource_manifest,
    close_focused_research_job,
    json_sha256,
    next_focused_research_assignment,
    prepare_focused_gap_pass,
    save_focused_research_result,
)
from .manual_discovery import normalize_manual_identity
from .storage import ResearchStore


REPLAY_VERSION = "source-hidden-codex-first-v1-v2"
V2_EXPERIMENT_MODE = "codex-first-replay-v2"
V2_PLAYBOOK_LIBRARY_VERSION = "codex-first-v2-proposal"

PATHWAY_SIGNALS = {
    "benefits-navigation": ("benefit", "navigation", "case management"),
    "community-embedded": ("community", "nonprofit", "faith", "church"),
    "crisis-response": ("crisis", "emergency", "hotline", "shelter"),
    "direct-program": ("program", "clinic", "center", "service"),
    "government-system": ("government", "county", "city", "state", "public"),
    "population-specific": (
        "veteran", "senior", "women", "family", "children", "disability",
        "spanish", "immigrant", "refugee", "reentry",
    ),
}

ACCESS_SIGNALS = {
    "availability-and-capacity": ("availability", "capacity", "waitlist", "openings"),
    "cost-and-funding": ("cost", "fee", "funding", "insurance", "medicaid"),
    "currentness": ("current", "stale", "closed", "confirm", "verify"),
    "documentation": ("document", "identification", "proof"),
    "eligibility": ("eligible", "eligibility", "criteria", "qualify"),
    "intake-and-referral": ("intake", "referral", "appointment", "apply", "enroll"),
    "language-and-accessibility": (
        "language", "spanish", "accessible", "accommodation", "disability",
    ),
    "service-area": ("service area", "resident", "county", "city limits"),
    "transportation": ("transportation", "transit", "ride", "distance"),
}

SOURCE_GUIDANCE = {
    "government": "Government program, registry, contract, and grant pages",
    "education": "School, college, and education-system program pages",
    "health-system": "Health-system and public-health program pages",
    "other-official": "Official provider and named-program pages",
}


def _lead_identity(lead: dict[str, Any]) -> dict[str, str]:
    website = str(lead.get("website") or lead.get("websiteRaw") or "").strip()
    parts = urlsplit(website) if website else None
    host = (parts.hostname or "").casefold().removeprefix("www.") if parts else ""
    path = re.sub(r"/+$", "", parts.path or "").casefold() if parts else ""
    organization = str(lead.get("organization") or "").strip()
    program = str(lead.get("program") or "").strip()
    normalized_organization = normalize_manual_identity(organization)
    normalized_program = normalize_manual_identity(program)
    key = (
        f"url:{host}{path}"
        if host and path and path != "/"
        else f"name:{normalized_organization}|{normalized_program}"
    )
    return {
        "key": key,
        "organization": organization,
        "program": program,
        "website": website,
        "host": host,
        "normalizedOrganization": normalized_organization,
        "normalizedProgram": normalized_program,
        "leadType": str(lead.get("leadType") or ""),
        "locationOrServiceArea": str(lead.get("locationOrServiceArea") or ""),
        "whyRelevant": str(lead.get("whyRelevant") or ""),
        "uncertainty": str(lead.get("uncertainty") or ""),
    }


def _source_class(website: str) -> str:
    host = (urlsplit(website).hostname or "").casefold() if website else ""
    if host.endswith(".gov") or ".gov." in host:
        return "government"
    if host.endswith(".edu"):
        return "education"
    if any(value in host for value in ("health", "hospital", "clinic", "medical")):
        return "health-system"
    return "other-official"


def _signal_counts(leads: list[dict[str, Any]], signals: dict[str, tuple[str, ...]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for lead in leads:
        text = " ".join(
            str(lead.get(field) or "")
            for field in ("leadType", "whyRelevant", "uncertainty", "locationOrServiceArea")
        ).casefold()
        for label, terms in signals.items():
            if any(term in text for term in terms):
                counts[label] += 1
    return {label: int(counts.get(label, 0)) for label in sorted(signals)}


def _provider_holdout(store: ResearchStore, job: dict[str, Any]) -> dict[str, Any]:
    submissions: list[dict[str, Any]] = []
    all_identities: list[dict[str, str]] = []
    for assignment in store.list_codex_first_assignments(int(job["id"])):
        if assignment["status"] != "completed":
            submissions.append({
                "researcher": assignment["researcher"],
                "role": assignment["role"],
                "status": assignment["status"],
                "assignmentSha256": assignment["assignmentSha256"],
                "rawSha256": "",
                "identities": [],
            })
            continue
        parsed = assignment.get("parsed") or {}
        identities = [_lead_identity(lead) for lead in parsed.get("leads") or []]
        all_identities.extend(identities)
        submissions.append({
            "researcher": assignment["researcher"],
            "role": assignment["role"],
            "status": assignment["status"],
            "assignmentSha256": assignment["assignmentSha256"],
            "rawSha256": assignment["rawSha256"],
            "identities": identities,
        })
    unique = {identity["key"]: identity for identity in all_identities if identity["key"]}
    return {
        "schemaVersion": 1,
        "categoryId": job["categoryId"],
        "submissions": submissions,
        "identityManifest": sorted(unique.values(), key=lambda item: item["key"]),
        "rawIdentityCount": len(all_identities),
        "uniqueIdentityCount": len(unique),
    }


def _strict_baseline_match(candidate: dict[str, str], known: dict[str, str]) -> bool:
    if candidate["host"] and candidate["host"] == known["host"]:
        candidate_path = urlsplit(candidate["website"]).path.rstrip("/").casefold()
        known_path = urlsplit(known["website"]).path.rstrip("/").casefold()
        if candidate_path and known_path and candidate_path == known_path:
            return True
    if (
        candidate["normalizedOrganization"]
        and candidate["normalizedOrganization"] == known["normalizedOrganization"]
    ):
        return (
            not candidate["normalizedProgram"]
            or candidate["normalizedProgram"] == known["normalizedProgram"]
        )
    return False


def _remove_known_and_v1_identities(
    holdout: dict[str, Any],
    known_identities: list[dict[str, str]],
    v1_identities: list[dict[str, str]],
) -> dict[str, Any]:
    value = copy.deepcopy(holdout)
    removed = 0
    kept: dict[str, dict[str, str]] = {}
    for submission in value["submissions"]:
        filtered = []
        for identity in submission["identities"]:
            known = any(_strict_baseline_match(identity, item) for item in known_identities)
            already_v1 = any(_matches(identity, item) for item in v1_identities)
            if known or already_v1:
                removed += 1
                continue
            filtered.append(identity)
            kept.setdefault(identity["key"], identity)
        submission["identities"] = filtered
    value["identityManifest"] = sorted(kept.values(), key=lambda item: item["key"])
    value["rawIdentityCount"] = sum(
        len(item["identities"]) for item in value["submissions"]
    )
    value["uniqueIdentityCount"] = len(kept)
    value["excludedKnownOrV1IdentityCount"] = removed
    return value


def build_generalized_lesson_evidence(holdout: dict[str, Any]) -> dict[str, Any]:
    leads = [
        identity
        for submission in holdout["submissions"]
        for identity in submission["identities"]
    ]
    key_sources: dict[str, set[str]] = {}
    provider_lead_counts: dict[str, int] = {}
    provider_status: dict[str, str] = {}
    for submission in holdout["submissions"]:
        provider = str(submission["researcher"])
        provider_status[provider] = str(submission["status"])
        provider_lead_counts[provider] = len(submission["identities"])
        for identity in submission["identities"]:
            key_sources.setdefault(identity["key"], set()).add(provider)
    allowed_lead_types = {
        "program", "provider-organization", "access-point", "routing-source", "directory"
    }
    lead_types = Counter(
        value if value in allowed_lead_types else "unspecified"
        for lead in leads
        for value in [str(lead.get("leadType") or "unspecified").strip().casefold()]
    )
    source_classes = Counter(_source_class(str(lead.get("website") or "")) for lead in leads)
    evidence = {
        "schemaVersion": 1,
        "categoryId": str(holdout["categoryId"]),
        "providerCoverage": {
            "status": provider_status,
            "leadCounts": provider_lead_counts,
            "completedCount": sum(value == "completed" for value in provider_status.values()),
            "expectedCount": len(provider_status),
        },
        "identityShape": {
            "submittedLeadCount": len(leads),
            "anonymousUniqueIdentityCount": len(key_sources),
            "anonymousRepeatedIdentityCount": sum(len(value) > 1 for value in key_sources.values()),
            "leadTypeCounts": dict(sorted(lead_types.items())),
        },
        "sourceClassCounts": dict(sorted(source_classes.items())),
        "pathwaySignalCounts": _signal_counts(leads, PATHWAY_SIGNALS),
        "accessConcernCounts": _signal_counts(leads, ACCESS_SIGNALS),
    }
    _assert_identity_free(evidence, holdout)
    return evidence


def _assert_identity_free(evidence: dict[str, Any], holdout: dict[str, Any]) -> None:
    text = str(evidence).casefold()
    if "http://" in text or "https://" in text or re.search(r"\b\d{3}[-.) ]\d{3}", text):
        raise ValueError("Generalized replay lessons contain direct identity details")
    for identity in holdout["identityManifest"]:
        for field in ("organization", "program", "host"):
            value = str(identity.get(field) or "").strip().casefold()
            if len(value) >= 8 and value in text:
                raise ValueError("Generalized replay lessons contain a sealed identity")


def build_v2_plan(v1_plan: dict[str, Any], lessons: dict[str, Any]) -> dict[str, Any]:
    plan = copy.deepcopy(v1_plan)
    plan["schemaVersion"] = 2
    plan["experimentMode"] = V2_EXPERIMENT_MODE
    plan["playbookVersion"] = f"{v1_plan['playbookVersion']}-replay-v2"
    plan["playbookLibraryVersion"] = V2_PLAYBOOK_LIBRARY_VERSION
    plan["playbookSource"] = f"{v1_plan.get('playbookSource') or 'category playbook'} + anonymous lessons"
    plan.pop("researcherRoster", None)

    pathway_counts = lessons["pathwaySignalCounts"]
    access_counts = lessons["accessConcernCounts"]
    source_counts = lessons["sourceClassCounts"]
    top_pathways = [
        label for label, count in sorted(
            pathway_counts.items(), key=lambda item: (-int(item[1]), item[0])
        ) if int(count) > 0
    ][:3]
    top_access = [
        label for label, count in sorted(
            access_counts.items(), key=lambda item: (-int(item[1]), item[0])
        ) if int(count) > 0
    ][:3]
    source_guidance = [
        SOURCE_GUIDANCE[label]
        for label, count in sorted(source_counts.items(), key=lambda item: (-int(item[1]), item[0]))
        if int(count) > 0 and label in SOURCE_GUIDANCE
    ]
    learned_coverage = [f"Anonymous provider evidence emphasized {label.replace('-', ' ')}" for label in top_pathways]
    learned_access = [f"verify {label.replace('-', ' ')}" for label in top_access]

    for focus in plan.get("focuses") or []:
        focus["direction"] = (
            str(focus.get("direction") or "").rstrip()
            + " Apply the sealed study's anonymous pattern evidence without searching for or inferring any held-out identity."
        )
        focus["coverage"] = list(dict.fromkeys(
            list(focus.get("coverage") or []) + learned_coverage
        ))
        focus["sourceChannels"] = list(dict.fromkeys(
            list(focus.get("sourceChannels") or []) + source_guidance
        ))
        focus["vocabulary"] = list(dict.fromkeys(
            list(focus.get("vocabulary") or []) + learned_access
        ))
    plan["anonymousLessonEvidence"] = {
        "sha256": json_sha256(lessons),
        "topPathwaySignals": top_pathways,
        "topAccessConcerns": top_access,
        "sourceClasses": [label for label, count in source_counts.items() if int(count) > 0],
        "providerCoverage": lessons["providerCoverage"],
        "identityShape": lessons["identityShape"],
    }
    return plan


def _v1_snapshot(store: ResearchStore, job: dict[str, Any]) -> dict[str, Any]:
    return {
        "jobId": int(job["id"]),
        "runId": int(job["runId"]),
        "plan": job["plan"],
        "planSha256": job["planSha256"],
        "finalManifestSha256": job["finalManifestSha256"],
        "evaluation": job["evaluation"],
        "passes": [
            {
                "ordinal": item["ordinal"],
                "focusKey": item["focusKey"],
                "focusLabel": item["focusLabel"],
                "passKind": item["passKind"],
                "definition": item["definition"],
                "assignment": item["assignment"],
                "assignmentSha256": item["assignmentSha256"],
                "leadCount": item["leadCount"],
                "assignedAt": item["assignedAt"],
                "completedAt": item["completedAt"],
            }
            for item in job["passes"]
        ],
    }


def _prepare_v2_job(
    store: ResearchStore, import_id: int, summary: dict[str, Any], plan: dict[str, Any]
) -> dict[str, Any]:
    plan_sha = json_sha256(plan)
    category = plan["category"]
    existing = store.find_focused_research_job(
        import_id, category["id"], plan["playbookVersion"], plan_sha, V2_EXPERIMENT_MODE
    )
    if existing:
        return existing
    known = build_known_resource_manifest(
        store, import_id, category["id"], plan["locationName"], redact_recovery_targets=False
    )
    assignment = (
        f"Run the source-hidden Codex-first v2 proposal for {category['label']} "
        f"in {summary['serviceArea']}."
    )
    run_id = store.create_manual_discovery_run(
        assignment,
        {
            "assignment": assignment,
            "focusedResearchPlan": plan,
            "planSha256": plan_sha,
            "sourceHiddenReplay": True,
            "researchContext": {
                "mode": "package",
                "sourcePackage": {
                    "importId": import_id,
                    "sourceName": summary["sourceName"],
                    "sourceSha256": summary["sourceSha256"],
                    "contentSha256": summary["contentSha256"],
                },
            },
        },
        import_id,
        target_location=summary["serviceArea"],
        target_category_id=category["id"],
        target_category_label=category["label"],
    )
    try:
        return store.create_focused_research_job(
            run_id=run_id,
            import_id=import_id,
            category_id=category["id"],
            category_label=category["label"],
            location_name=plan["locationName"],
            service_area=summary["serviceArea"],
            playbook_version=plan["playbookVersion"],
            experiment_mode=V2_EXPERIMENT_MODE,
            plan=plan,
            plan_sha256=plan_sha,
            baseline_manifest_sha256=json_sha256(known),
            passes=plan["focuses"],
        )
    except Exception:
        store.delete_empty_manual_discovery_run(run_id)
        raise


def prepare_codex_replay_study(
    store: ResearchStore, import_id: int | None = None
) -> dict[str, Any]:
    selected = int(import_id or store.latest_import_id() or 0)
    summary = store.import_summary(selected)
    if not summary:
        raise ValueError("Connect the immutable package baseline before preparing replay")
    categories = [
        item for item in summary["categories"] if item["id"] != "miscellaneous"
    ]
    fixture = {
        "schemaVersion": 1,
        "importId": selected,
        "sourceName": summary["sourceName"],
        "sourceSha256": summary["sourceSha256"],
        "contentSha256": summary["contentSha256"],
        "officeName": summary["officeName"],
        "serviceArea": summary["serviceArea"],
        "categories": [{"id": item["id"], "label": item["label"]} for item in categories],
        "knownResources": [
            {
                "id": seed["resourceId"],
                "name": seed["name"],
                "categories": [item["id"] for item in seed["categories"]],
                "website": str(seed["fullRecord"].get("website") or ""),
            }
            for category in categories
            for seed in store.list_seeds(selected, category["id"])
        ],
    }
    fixture["knownResources"] = list({
        item["id"]: item for item in fixture["knownResources"]
    }.values())
    fixture_sha = json_sha256(fixture)
    existing = store.find_codex_replay_study(selected, REPLAY_VERSION, fixture_sha)
    if existing:
        return codex_replay_view(store, int(existing["id"]))

    jobs = {
        str(job["categoryId"]): job
        for job in store.list_focused_research_jobs(selected)
        if job["experimentMode"] == CODEX_FIRST_EXPERIMENT_MODE
        and job["status"] == "completed"
    }
    missing = [item["label"] for item in categories if item["id"] not in jobs]
    if missing:
        raise ValueError("Complete Codex-first v1 before replay: " + ", ".join(missing))

    study_categories: list[dict[str, Any]] = []
    for category in categories:
        v1_job = jobs[category["id"]]
        holdout = _provider_holdout(store, v1_job)
        known_identities = [
            _lead_identity({
                "organization": seed["name"],
                "program": "",
                "website": str(seed["fullRecord"].get("website") or ""),
            })
            for seed in store.list_seeds(selected, category["id"])
        ]
        holdout = _remove_known_and_v1_identities(
            holdout, known_identities, _codex_identities(store, int(v1_job["id"]))
        )
        completed_challengers = sum(
            item["role"] == "challenger" and item["status"] == "completed"
            for item in holdout["submissions"]
        )
        if completed_challengers < 1:
            raise ValueError(f"{category['label']} has no completed provider holdout")
        lessons = build_generalized_lesson_evidence(holdout)
        v2_plan = build_v2_plan(v1_job["plan"], lessons)
        v2_job = _prepare_v2_job(store, selected, summary, v2_plan)
        snapshot = _v1_snapshot(store, v1_job)
        study_categories.append({
            "categoryId": category["id"],
            "categoryLabel": category["label"],
            "v1JobId": v1_job["id"],
            "v2JobId": v2_job["id"],
            "v1Snapshot": snapshot,
            "v1SnapshotSha256": json_sha256(snapshot),
            "lessonEvidence": lessons,
            "lessonEvidenceSha256": json_sha256(lessons),
            "sealedHoldout": holdout,
            "sealedHoldoutSha256": json_sha256(holdout),
            "v2Plan": v2_plan,
            "v2PlanSha256": json_sha256(v2_plan),
        })
    study = store.create_codex_replay_study(
        import_id=selected,
        replay_version=REPLAY_VERSION,
        package_fixture=fixture,
        package_fixture_sha256=fixture_sha,
        categories=study_categories,
    )
    return codex_replay_view(store, int(study["id"]))


def _visible_category(category: dict[str, Any], *, revealed: bool) -> dict[str, Any]:
    value = {
        key: category[key]
        for key in (
            "ordinal", "categoryId", "categoryLabel", "v1JobId", "v2JobId",
            "v1SnapshotSha256", "lessonEvidence",
            "lessonEvidenceSha256", "sealedHoldoutSha256", "v2Plan",
            "v2PlanSha256", "metrics", "metricsSha256", "updatedAt",
        )
    }
    if revealed:
        value["v1Snapshot"] = category["v1Snapshot"]
        value["sealedHoldout"] = category["sealedHoldout"]
    else:
        value["v1Snapshot"] = None
        value["sealedHoldout"] = None
    return value


def codex_replay_view(store: ResearchStore, study_id: int) -> dict[str, Any]:
    study = store.get_codex_replay_study(study_id)
    if not study:
        raise ValueError("Codex replay study not found")
    revealed = study["status"] in {"revealed", "completed"}
    categories = []
    for category in study["categories"]:
        value = _visible_category(category, revealed=revealed)
        value["v2Job"] = store.get_focused_research_job(int(category["v2JobId"]))
        categories.append(value)
    completed = sum((item["v2Job"] or {}).get("status") == "completed" for item in categories)
    return {
        key: study[key]
        for key in (
            "id", "importId", "replayVersion", "status", "packageFixture",
            "packageFixtureSha256", "report", "reportSha256", "createdAt",
            "updatedAt", "codexClosedAt", "revealedAt", "completedAt",
        )
    } | {
        "categories": categories,
        "progress": {"completedCategories": completed, "totalCategories": len(categories)},
        "holdoutsRevealed": revealed,
    }


def next_codex_replay_assignment(store: ResearchStore, study_id: int) -> dict[str, Any] | None:
    study = store.get_codex_replay_study(study_id)
    if not study:
        raise ValueError("Codex replay study not found")
    if study["status"] in {"codex-closed", "revealed", "completed"}:
        return None
    if study["status"] == "sealed":
        store.transition_codex_replay_study(
            study_id, allowed_statuses={"sealed"}, status="running"
        )
    for category in study["categories"]:
        job = store.get_focused_research_job(int(category["v2JobId"]))
        if not job:
            raise ValueError("Codex replay v2 job not found")
        if job["status"] == "completed":
            continue
        assignment = next_focused_research_assignment(store, int(job["id"]))
        if assignment is None:
            if not any(item["passKind"] == "gap" for item in job["passes"]):
                prepare_focused_gap_pass(store, int(job["id"]))
                assignment = next_focused_research_assignment(store, int(job["id"]))
            else:
                close_focused_research_job(store, int(job["id"]))
                continue
        return {
            "studyId": study_id,
            "categoryId": category["categoryId"],
            "categoryLabel": category["categoryLabel"],
            "jobId": job["id"],
            "researchPass": assignment,
        }
    store.transition_codex_replay_study(
        study_id, allowed_statuses={"running", "sealed"}, status="codex-closed"
    )
    return None


def save_codex_replay_result(
    store: ResearchStore, study_id: int, job_id: int, focus_key: str, raw_text: str
) -> dict[str, Any]:
    study = store.get_codex_replay_study(study_id)
    if not study or study["status"] not in {"sealed", "running"}:
        raise ValueError("Codex replay is not accepting v2 results")
    if job_id not in {int(item["v2JobId"]) for item in study["categories"]}:
        raise ValueError("Focused job does not belong to this replay")
    return save_focused_research_result(store, job_id, focus_key, raw_text)


def _codex_identities(store: ResearchStore, job_id: int) -> list[dict[str, str]]:
    job = store.get_focused_research_job(job_id)
    if not job:
        return []
    contribution_ids = {
        int(item["contributionId"])
        for item in job["passes"] if item.get("contributionId") is not None
    }
    identities: list[dict[str, str]] = []
    for contribution in store.list_manual_contributions(int(job["runId"])):
        if int(contribution["id"]) in contribution_ids:
            identities.extend(_lead_identity(lead) for lead in contribution["leads"])
    return identities


def _matches(left: dict[str, str], right: dict[str, str]) -> bool:
    if left["host"] and left["host"] == right["host"]:
        left_path = urlsplit(left["website"]).path.rstrip("/").casefold()
        right_path = urlsplit(right["website"]).path.rstrip("/").casefold()
        if not left_path or not right_path or left_path == right_path:
            return True
    left_org, right_org = left["normalizedOrganization"], right["normalizedOrganization"]
    if left_org and right_org and left_org == right_org:
        left_program, right_program = left["normalizedProgram"], right["normalizedProgram"]
        return not left_program or not right_program or (
            left_program == right_program
            or left_program in right_program
            or right_program in left_program
        )
    return False


def _duration_seconds(job: dict[str, Any]) -> int:
    total = 0.0
    for item in job["passes"]:
        if not item.get("assignedAt") or not item.get("completedAt"):
            continue
        total += (
            datetime.fromisoformat(item["completedAt"])
            - datetime.fromisoformat(item["assignedAt"])
        ).total_seconds()
    return max(0, round(total))


def calculate_category_metrics(
    store: ResearchStore, category: dict[str, Any]
) -> dict[str, Any]:
    v1 = _codex_identities(store, int(category["v1JobId"]))
    v2 = _codex_identities(store, int(category["v2JobId"]))
    holdout = category["sealedHoldout"]["identityManifest"]
    v1_unique = {item["key"]: item for item in v1 if item["key"]}
    v2_unique = {item["key"]: item for item in v2 if item["key"]}
    recovered = [target for target in holdout if any(_matches(candidate, target) for candidate in v2_unique.values())]
    v1_holdout = [target for target in holdout if any(_matches(candidate, target) for candidate in v1_unique.values())]
    retained = [target for target in v1_unique.values() if any(_matches(candidate, target) for candidate in v2_unique.values())]
    novel = [
        candidate for candidate in v2_unique.values()
        if not any(_matches(candidate, target) for target in holdout)
        and not any(_matches(candidate, target) for target in v1_unique.values())
    ]
    v1_job = store.get_focused_research_job(int(category["v1JobId"]))
    v2_job = store.get_focused_research_job(int(category["v2JobId"]))
    assert v1_job is not None and v2_job is not None
    return {
        "schemaVersion": 1,
        "categoryId": category["categoryId"],
        "recovery": {
            "holdoutIdentityCount": len(holdout),
            "v1RecoveredCount": len(v1_holdout),
            "v2RecoveredCount": len(recovered),
            "v2RecoveryRate": round(len(recovered) / len(holdout), 4) if holdout else None,
        },
        "retention": {
            "v1IdentityCount": len(v1_unique),
            "retainedByV2Count": len(retained),
            "rate": round(len(retained) / len(v1_unique), 4) if v1_unique else None,
        },
        "novelty": {"v2NovelIdentityCount": len(novel)},
        "duplicates": {
            "v1SubmittedLeadCount": len(v1),
            "v1UniqueIdentityCount": len(v1_unique),
            "v2SubmittedLeadCount": len(v2),
            "v2UniqueIdentityCount": len(v2_unique),
            "v2DuplicateCount": max(0, len(v2) - len(v2_unique)),
        },
        "uncertainty": {
            "v1WithUncertaintyCount": sum(bool(item["uncertainty"].strip()) for item in v1),
            "v2WithUncertaintyCount": sum(bool(item["uncertainty"].strip()) for item in v2),
        },
        "sourceCoverage": {
            "v1HostCount": len({item["host"] for item in v1 if item["host"]}),
            "v2HostCount": len({item["host"] for item in v2 if item["host"]}),
            "holdoutProviderCoverage": category["lessonEvidence"]["providerCoverage"],
        },
        "time": {
            "v1ResearchSeconds": _duration_seconds(v1_job),
            "v2ResearchSeconds": _duration_seconds(v2_job),
        },
        "beforeAfter": {
            "v1Plan": category["v1Snapshot"]["plan"],
            "v2Plan": category["v2Plan"],
            "v1Assignments": [item["assignment"] for item in category["v1Snapshot"]["passes"]],
            "v2Assignments": [item["assignment"] for item in v2_job["passes"]],
        },
    }


def reveal_and_complete_codex_replay(store: ResearchStore, study_id: int) -> dict[str, Any]:
    study = store.get_codex_replay_study(study_id)
    if not study:
        raise ValueError("Codex replay study not found")
    if study["status"] == "completed":
        return codex_replay_view(store, study_id)
    if study["status"] != "codex-closed":
        raise ValueError("Complete and close every v2 category before revealing holdouts")
    store.transition_codex_replay_study(
        study_id, allowed_statuses={"codex-closed"}, status="revealed"
    )
    category_metrics = []
    for category in study["categories"]:
        metrics = calculate_category_metrics(store, category)
        store.save_codex_replay_metrics(
            study_id, category["categoryId"], metrics, json_sha256(metrics)
        )
        category_metrics.append(metrics)
    aggregate = {
        "holdoutIdentityCount": sum(item["recovery"]["holdoutIdentityCount"] for item in category_metrics),
        "v2RecoveredCount": sum(item["recovery"]["v2RecoveredCount"] for item in category_metrics),
        "v1IdentityCount": sum(item["retention"]["v1IdentityCount"] for item in category_metrics),
        "retainedByV2Count": sum(item["retention"]["retainedByV2Count"] for item in category_metrics),
        "v2NovelIdentityCount": sum(item["novelty"]["v2NovelIdentityCount"] for item in category_metrics),
        "v2DuplicateCount": sum(item["duplicates"]["v2DuplicateCount"] for item in category_metrics),
        "v1ResearchSeconds": sum(item["time"]["v1ResearchSeconds"] for item in category_metrics),
        "v2ResearchSeconds": sum(item["time"]["v2ResearchSeconds"] for item in category_metrics),
    }
    aggregate["v2RecoveryRate"] = round(
        aggregate["v2RecoveredCount"] / aggregate["holdoutIdentityCount"], 4
    ) if aggregate["holdoutIdentityCount"] else None
    aggregate["v2RetentionRate"] = round(
        aggregate["retainedByV2Count"] / aggregate["v1IdentityCount"], 4
    ) if aggregate["v1IdentityCount"] else None
    report = {
        "schemaVersion": 1,
        "replayVersion": study["replayVersion"],
        "packageFixtureSha256": study["packageFixtureSha256"],
        "aggregate": aggregate,
        "categories": category_metrics,
        "activationDecision": "proposal-only; no active playbook was changed",
    }
    store.complete_codex_replay_study(study_id, report, json_sha256(report))
    return codex_replay_view(store, study_id)
