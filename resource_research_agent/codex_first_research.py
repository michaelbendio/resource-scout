from __future__ import annotations

import json
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .focused_research import (
    CODEX_FIRST_EXPERIMENT_MODE,
    build_candidate_manifest,
    close_focused_research_job,
    json_sha256,
    next_focused_research_assignment,
    prepare_focused_gap_pass,
    prepare_focused_research_job,
    save_focused_research_result,
    text_sha256,
)
from .manual_discovery import parse_manual_contribution
from .playbooks import playbook_for
from .scout_curation import schedule_chatgpt_assignment
from .storage import ResearchStore


ROSTER_PATH = Path(__file__).with_name("researcher_roster.json")


def load_researcher_roster(path: Path = ROSTER_PATH) -> dict[str, Any]:
    return validate_researcher_roster(json.loads(path.read_text(encoding="utf-8")))


def validate_researcher_roster(value: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("schemaVersion") != 1:
        raise RuntimeError("Researcher roster must use schema version 1")
    researchers = value.get("researchers")
    if not isinstance(researchers, list) or not researchers:
        raise RuntimeError("Researcher roster must list researchers")
    allowed = {"primary", "challenger", "shadow", "disabled"}
    names: set[str] = set()
    primary = 0
    normalized: list[dict[str, str]] = []
    for item in researchers:
        if not isinstance(item, dict):
            raise RuntimeError("Every researcher roster entry must be an object")
        name = str(item.get("name") or "").strip()
        role = str(item.get("role") or "").strip()
        if not name or name.casefold() in names or role not in allowed:
            raise RuntimeError("Researcher roster names must be unique and roles valid")
        names.add(name.casefold())
        primary += role == "primary"
        normalized.append({"name": name, "role": role})
    if primary != 1:
        raise RuntimeError("Researcher roster must have exactly one primary")
    return {
        "schemaVersion": 1,
        "version": str(value.get("version") or "").strip(),
        "researchers": normalized,
    }


def _codex_jobs(store: ResearchStore, import_id: int) -> list[dict[str, Any]]:
    by_category = {
        str(job["categoryId"]): job
        for job in store.list_focused_research_jobs(import_id)
        if str(job.get("experimentMode") or "") == CODEX_FIRST_EXPERIMENT_MODE
    }
    return [
        by_category[str(category["id"])]
        for category in store.list_import_categories(import_id)
        if str(category.get("id") or "").casefold() != "miscellaneous"
        and str(category["id"]) in by_category
    ]


def prepare_codex_first_plan(
    store: ResearchStore,
    import_id: int | None = None,
    *,
    roster: dict[str, Any] | None = None,
) -> dict[str, Any]:
    selected = int(import_id or store.latest_import_id() or 0)
    if not selected:
        raise ValueError("Connect a resource package before Codex-first research")
    roster_value = validate_researcher_roster(roster) if roster is not None else load_researcher_roster()
    enabled = [
        item for item in roster_value["researchers"] if item["role"] != "disabled"
    ]
    if not any(item["role"] == "primary" and item["name"] == "Codex" for item in enabled):
        raise ValueError("The first Codex-first release requires Codex as primary")
    categories = [
        category for category in store.list_import_categories(selected)
        if str(category.get("id") or "").casefold() != "miscellaneous"
    ]
    missing = [
        str(category.get("label") or category.get("id"))
        for category in categories
        if playbook_for(
            str(category["id"]), str(category["label"]),
            str((store.import_summary(selected) or {}).get("serviceArea") or ""),
        ).focused_research is None
    ]
    if missing:
        raise ValueError("Focused research guidance is missing for: " + ", ".join(missing))
    for category in categories:
        prepare_focused_research_job(
            store,
            selected,
            str(category["id"]),
            experiment_mode=CODEX_FIRST_EXPERIMENT_MODE,
            redact_recovery_targets=False,
            researcher_roster=roster_value,
        )
    return codex_first_view(store, selected)


def _external_researchers(job: dict[str, Any]) -> list[dict[str, str]]:
    roster = (job.get("plan") or {}).get("researcherRoster") or {}
    return [
        item for item in roster.get("researchers") or []
        if item.get("role") in {"challenger", "shadow"}
    ]


def _build_challenger_assignment(
    job: dict[str, Any], researcher: str, candidates: list[dict[str, str]]
) -> str:
    candidate_lines = [
        "- " + (" · ".join(filter(None, (item["organization"], item["program"]))) or item["website"])
        + (f" — {item['website']}" if item["website"] else "")
        for item in candidates
    ] or ["- None."]
    plan = job["plan"]
    return "\n".join([
        f"Resource Scout adversarial challenger assignment for {researcher}.",
        f"Category: {job['categoryLabel']}",
        f"Service area: {job['serviceArea']}",
        "",
        "Codex has completed the category playbook and a coverage-gap pass.",
        "Find credible, direct-service candidates it still missed. Do not repeat the identities below.",
        "Search different vocabulary, provider ecosystems, referral pathways, public records, grants, contracts, registries, and primary-source PDFs.",
        "Return only candidates that credibly serve the stated area. A broken page alone does not prove closure.",
        "",
        "Include:",
        *[f"- {item}" for item in plan.get("include") or []],
        "",
        "Exclude:",
        *[f"- {item}" for item in plan.get("exclude") or []],
        "",
        "Already found; do not repeat obvious aliases:",
        *candidate_lines,
        "",
        "Return one JSON object with a leads array. Each lead must contain organization, program, website, phone, address, leadType, locationOrServiceArea, whyRelevant, and uncertainty as text fields.",
    ])


def prepare_codex_first_challenges(
    store: ResearchStore,
    job_id: int,
    *,
    random_source: Any = random,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    job = store.get_focused_research_job(job_id)
    if not job or str(job.get("experimentMode") or "") != CODEX_FIRST_EXPERIMENT_MODE:
        raise ValueError("Codex-first research job not found")
    if not any(item["passKind"] == "gap" for item in job["passes"]):
        raise ValueError("Complete the Codex gap pass before assigning challengers")
    if any(item["status"] != "completed" for item in job["passes"]):
        raise ValueError("Complete every Codex research pass before assigning challengers")
    candidates = build_candidate_manifest(store, int(job["runId"]))
    manifest_sha = json_sha256(candidates)
    existing = {item["researcher"]: item for item in store.list_codex_first_assignments(job_id)}
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    for researcher in _external_researchers(job):
        name = str(researcher["name"])
        assignment_text = _build_challenger_assignment(job, name, candidates)
        saved = existing.get(name) or store.create_codex_first_assignment(
            job_id=job_id,
            researcher=name,
            role=str(researcher["role"]),
            assignment=assignment_text,
            assignment_sha256=text_sha256(assignment_text),
            candidate_manifest_sha256=manifest_sha,
        )
        if name.casefold() == "chatgpt" and saved["chatgptScheduleId"] is None:
            latest = store.latest_chatgpt_assignment_schedule(int(job["importId"]))
            if latest and latest["assignment"] == assignment_text:
                stored_schedule = latest
            else:
                previous_sent_at = (
                    datetime.fromisoformat(str(latest["sentAt"]))
                    if latest and latest.get("sentAt")
                    else None
                )
                schedule = schedule_chatgpt_assignment(
                    current,
                    random_source,
                    reason=(
                        "Random 5-10 minute research interval measured from "
                        "the previous ChatGPT send."
                    ),
                    previous_sent_at=previous_sent_at,
                )
                stored_schedule = store.create_chatgpt_assignment_schedule(
                    int(job["importId"]), str(job["categoryId"]),
                    str(job["categoryLabel"]), assignment_text,
                    schedule.delay_minutes, schedule.scheduled_at,
                    reason=schedule.reason, now=current,
                )
            store.attach_codex_first_chatgpt_schedule(saved["id"], stored_schedule["id"])
    return store.list_codex_first_assignments(job_id)


def save_codex_first_external_result(
    store: ResearchStore, assignment_id: int, raw_text: str
) -> dict[str, Any]:
    assignment = store.get_codex_first_assignment(assignment_id)
    if not assignment:
        raise ValueError("Codex-first assignment not found")
    digest = text_sha256(raw_text)
    if assignment["status"] == "completed":
        if assignment["rawSha256"] == digest:
            return assignment
        raise ValueError("Completed Codex-first result is immutable")
    job = store.get_focused_research_job(int(assignment["jobId"]))
    if not job:
        raise ValueError("Codex-first research job not found")
    if assignment["chatgptScheduleId"] is not None:
        schedule = store.get_chatgpt_assignment_schedule(
            int(assignment["chatgptScheduleId"])
        )
        if not schedule or schedule["status"] != "sent":
            raise ValueError("Mark the ChatGPT assignment sent before saving its result")
    parsed = parse_manual_contribution(raw_text)
    if parsed["status"] != "parsed":
        raise ValueError("Correct the research response before saving it: " + str(parsed["error"]))
    contribution_id = None
    if assignment["role"] == "challenger":
        contribution = store.save_manual_contribution(
            int(job["runId"]), str(assignment["researcher"]), raw_text
        )
        if contribution["parseStatus"] != "parsed":  # pragma: no cover
            raise ValueError(str(contribution.get("error") or "Invalid response"))
        contribution_id = int(contribution["id"])
    completed = store.complete_codex_first_assignment(
        assignment_id,
        raw_text=raw_text,
        raw_sha256=digest,
        parsed=parsed["parsed"],
        lead_count=len(parsed["leads"]),
        contribution_id=contribution_id,
    )
    _close_if_ready(store, int(assignment["jobId"]))
    return completed


def _close_if_ready(store: ResearchStore, job_id: int) -> dict[str, Any] | None:
    job = store.get_focused_research_job(job_id)
    if not job or job["status"] == "completed":
        return job
    assignments = store.list_codex_first_assignments(job_id)
    expected = {
        item["name"] for item in _external_researchers(job)
        if item["role"] == "challenger"
    }
    completed = {
        item["researcher"] for item in assignments
        if item["role"] == "challenger" and item["status"] == "completed"
    }
    if expected == completed:
        return close_focused_research_job(store, job_id)
    return None


def next_codex_first_assignment(
    store: ResearchStore,
    import_id: int,
    researcher: str,
    *,
    random_source: Any = random,
    now: datetime | None = None,
) -> dict[str, Any] | None:
    jobs = _codex_jobs(store, int(import_id))
    if not jobs:
        raise ValueError("Prepare Codex-first research before requesting assignments")
    wanted = str(researcher or "").strip()
    if wanted == "Codex":
        for job in jobs:
            if job["status"] == "completed":
                continue
            if all(item["status"] == "completed" for item in job["passes"]):
                if not any(item["passKind"] == "gap" for item in job["passes"]):
                    prepare_focused_gap_pass(store, int(job["id"]))
                    job = store.get_focused_research_job(int(job["id"])) or job
                else:
                    prepare_codex_first_challenges(
                        store, int(job["id"]), random_source=random_source, now=now
                    )
                    _close_if_ready(store, int(job["id"]))
                    continue
            research_pass = next_focused_research_assignment(store, int(job["id"]))
            return {"kind": "primary", "job": job, "researchPass": research_pass}
        return None
    for job in jobs:
        match = next((
            item for item in store.list_codex_first_assignments(int(job["id"]))
            if item["researcher"] == wanted and item["status"] != "completed"
        ), None)
        if match:
            return {"kind": match["role"], "job": job, "externalAssignment": match}
    return None


def save_codex_first_primary_result(
    store: ResearchStore, job_id: int, focus_key: str, raw_text: str
) -> dict[str, Any]:
    return save_focused_research_result(store, job_id, focus_key, raw_text)


def codex_first_view(store: ResearchStore, import_id: int) -> dict[str, Any]:
    jobs = _codex_jobs(store, int(import_id))
    categories: list[dict[str, Any]] = []
    for job in jobs:
        assignments = store.list_codex_first_assignments(int(job["id"]))
        assignments_by_researcher = {
            str(item["researcher"]): item for item in assignments
        }
        run_id = int(job["runId"])
        contribution_progress = store.manual_discovery_progress(run_id)
        funnel = store.manual_consolidation_funnel(run_id) or {}
        contact_progress = store.discovery_contact_lookup_progress(run_id)
        categories.append({
            "jobId": int(job["id"]),
            "categoryId": str(job["categoryId"]),
            "categoryLabel": str(job["categoryLabel"]),
            "status": str(job["status"]),
            "primary": {
                **dict(job["progress"]),
                "passes": [
                    {
                        "ordinal": int(item["ordinal"]),
                        "focusKey": str(item["focusKey"]),
                        "focusLabel": str(item["focusLabel"]),
                        "passKind": str(item["passKind"]),
                        "status": str(item["status"]),
                        "leadCount": int(item["leadCount"]),
                    }
                    for item in job["passes"]
                ],
            },
            "funnel": {
                "submittedLeads": int(contribution_progress["leadCount"]),
                "sourceResponses": int(contribution_progress["parsedContributionCount"]),
                "consolidatedIdentities": int(funnel.get("consolidatedIdentities") or 0),
                "candidateIdentities": int(funnel.get("candidateIdentities") or 0),
                "verifiedContacts": int(contact_progress["verifiedContactCount"]),
                "contactResults": int(contact_progress["resultCount"]),
            },
            "researchers": [
                {
                    "name": item["name"],
                    "role": item["role"],
                    "status": (
                        "completed" if item["name"] == "Codex" and job["status"] == "completed"
                        else "in-progress" if item["name"] == "Codex" and job["status"] == "in-progress"
                        else "pending" if item["name"] == "Codex"
                        else (assignments_by_researcher.get(item["name"]) or {}).get("status", "pending")
                    ),
                    "leadCount": int(
                        (assignments_by_researcher.get(item["name"]) or {}).get("leadCount") or 0
                    ) if item["name"] != "Codex" else int(job["progress"]["leadCount"]),
                }
                for item in (job["plan"].get("researcherRoster") or {}).get("researchers") or []
                if item["role"] != "disabled"
            ],
        })
    completed = sum(item["status"] == "completed" for item in categories)
    return {
        "schemaVersion": 1,
        "experimentMode": CODEX_FIRST_EXPERIMENT_MODE,
        "importId": int(import_id),
        "status": "completed" if categories and completed == len(categories) else "in-progress",
        "completedCategories": completed,
        "totalCategories": len(categories),
        "activeCategory": next((item for item in categories if item["status"] != "completed"), None),
        "categories": categories,
    }
