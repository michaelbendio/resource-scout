from __future__ import annotations

import re
from typing import Any

from .storage import ResearchStore


def _effective_import_id(run: dict[str, Any]) -> int | None:
    reconciliation = run.get("reconciliation")
    if isinstance(reconciliation, dict) and reconciliation.get("targetImportId") is not None:
        return int(reconciliation["targetImportId"])
    value = run.get("sourceImportId") or run.get("seedImportId")
    return int(value) if value is not None else None


def _location_name(summary: dict[str, Any]) -> str:
    office_name = str(summary.get("officeName") or "").strip()
    without_suffix = re.sub(r"\s+TSO$", "", office_name, flags=re.IGNORECASE).strip()
    return without_suffix or str(summary.get("serviceArea") or "Location").strip()


def _review_filename(location_name: str) -> str:
    token = "".join(character for character in location_name if character.isalnum())
    return f"auto{token or 'Location'}.html"


def _newer_event(*events: dict[str, Any] | None) -> dict[str, Any] | None:
    available = [event for event in events if event]
    return max(available, key=lambda event: str(event.get("createdAt") or "")) if available else None


def build_scout_progress(
    store: ResearchStore,
    import_id: int | None = None,
) -> dict[str, Any]:
    selected_import_id = int(import_id or store.latest_import_id() or 0)
    if not selected_import_id:
        raise ValueError("Connect a resource package before viewing Scout progress")
    summary = store.import_summary(selected_import_id)
    if not summary:
        raise ValueError("Resource package snapshot not found")

    categories = [
        category
        for category in summary.get("categories") or []
        if str(category.get("id") or "").casefold() != "miscellaneous"
    ]
    category_labels = {
        str(category.get("id") or ""): str(category.get("label") or category.get("id") or "")
        for category in categories
    }
    runs = [
        run
        for run in store.list_runs(limit=100)
        if run.get("researchMode", "package") == "package"
        and _effective_import_id(run) == selected_import_id
    ]
    completed_category_ids = {
        str(run.get("targetCategoryId") or "")
        for run in runs
        if run.get("status") == "completed"
    }
    running = next((run for run in runs if run.get("status") == "running"), None)

    jobs = store.list_scout_curation_jobs(selected_import_id)
    job = jobs[0] if jobs else None
    curation_events = (
        store.list_scout_curation_progress(int(job["id"])) if job else []
    )
    curation_event = curation_events[-1] if curation_events else None
    workflow_events = store.list_scout_workflow_progress(selected_import_id, limit=1)
    workflow_event = workflow_events[0] if workflow_events else None
    current_event = _newer_event(workflow_event, curation_event)
    focused_jobs = store.list_focused_research_jobs(selected_import_id)
    focused_job = focused_jobs[0] if focused_jobs else None
    focused_active = bool(
        focused_job and focused_job.get("status") in {"pending", "in-progress"}
    )
    focused_is_newest = bool(
        focused_job
        and str(focused_job.get("updatedAt") or "")
        >= str((current_event or {}).get("createdAt") or "")
    )
    blind_studies = store.list_blind_comparison_studies()
    blind_study = blind_studies[0] if blind_studies else None
    blind_is_newest = bool(
        blind_study
        and str(blind_study.get("updatedAt") or "")
        >= max(
            str((current_event or {}).get("createdAt") or ""),
            str((focused_job or {}).get("updatedAt") or ""),
        )
    )

    research_completed = len(completed_category_ids & set(category_labels))
    research_total = len(categories)
    curation = (job or {}).get("progress") or {
        "completed": 0,
        "failed": 0,
        "total": research_total,
    }
    location_name = _location_name(summary)

    if blind_study and blind_is_newest:
        blind_status = str(blind_study.get("status") or "")
        blind_categories = blind_study.get("categories") or []
        completed_blind_categories = sum(
            str((item.get("focusedJob") or {}).get("status") or "") == "completed"
            for item in blind_categories
        )
        reviewed_blind_categories = sum(bool(item.get("reviewResult")) for item in blind_categories)
        active_blind_category = next((
            item for item in blind_categories
            if str((item.get("focusedJob") or {}).get("status") or "") != "completed"
        ), None)
        if blind_status == "researching":
            phase = "blind-research"
            category_id = str((active_blind_category or {}).get("categoryId") or "")
            message = (
                f"Blind comparison research: {(active_blind_category or {}).get('categoryLabel') or 'held-out categories'}. "
                f"{completed_blind_categories} of {len(blind_categories)} Codex category results are closed. "
                "Four-AI identities remain sealed."
            )
        elif blind_status == "codex-closed":
            phase = "blind-codex-closed"
            category_id = ""
            message = (
                "Every Codex held-out result is closed. Four-AI identities remain sealed "
                "and are ready for controlled reveal."
            )
        elif blind_status in {"revealed", "reviewing"}:
            phase = "blind-review"
            category_id = ""
            message = (
                f"Source-hidden comparison review: {reviewed_blind_categories} of "
                f"{len(blind_categories)} categories complete."
            )
        else:
            phase = "blind-comparison-complete"
            category_id = ""
            comparison = (blind_study.get("report") or {}).get("aggregateComparison") or {}
            message = (
                "Blind comparison is complete. "
                f"Codex contributed {comparison.get('codexCuratedCount', 0)} curated identities; "
                f"the four-AI union contributed {comparison.get('fourAiCuratedCount', 0)}."
            )
        updated_at = blind_study.get("updatedAt")
    elif focused_active or (focused_job and focused_is_newest):
        phase = (
            "focused-research" if focused_active else "focused-research-complete"
        )
        assigned_pass = next(
            (
                item for item in focused_job["passes"]
                if item.get("status") == "assigned"
            ),
            None,
        )
        next_pass = assigned_pass or next(
            (
                item for item in focused_job["passes"]
                if item.get("status") == "pending"
            ),
            None,
        )
        category_id = str(focused_job.get("categoryId") or "")
        progress = focused_job.get("progress") or {}
        if not focused_active:
            evaluation = focused_job.get("evaluation") or {}
            message = (
                f"Focused {focused_job.get('categoryLabel') or 'resource'} research "
                f"is complete for {focused_job.get('locationName')}. "
                f"Recovered {evaluation.get('locationPrimaryRecoveredCount', 0)} of "
                f"{evaluation.get('locationPrimaryTargetCount', 0)} primary retrospective targets."
            )
        elif next_pass:
            message = (
                f"Focused {focused_job.get('categoryLabel') or 'resource'} research: "
                f"{next_pass.get('focusLabel')}. "
                f"{progress.get('completed', 0)} of {progress.get('total', 0)} passes complete."
            )
        else:
            message = "Focused research passes are complete and ready for evaluation."
        updated_at = focused_job.get("updatedAt")
    elif current_event:
        phase = str(current_event.get("phase") or "Scout progress")
        message = str(current_event.get("message") or "Scout progress was updated.")
        category_id = str(current_event.get("categoryId") or "")
        updated_at = current_event.get("createdAt")
    elif running:
        phase = "research"
        category_id = str(running.get("targetCategoryId") or "")
        message = f"Researching {running.get('targetCategoryLabel') or category_labels.get(category_id) or 'resources'}."
        updated_at = running.get("startedAt") or running.get("createdAt")
    elif research_completed < research_total:
        phase = "research"
        category_id = ""
        message = f"Research is complete for {research_completed} of {research_total} categories."
        updated_at = runs[0].get("completedAt") if runs else summary.get("importedAt")
    elif not job:
        phase = "ready-for-curation"
        category_id = ""
        message = "Research is complete. Scout is ready for Codex-controlled curation."
        updated_at = runs[0].get("completedAt") if runs else summary.get("importedAt")
    else:
        phase = "curation" if job.get("status") != "completed" else "review-file"
        category_id = ""
        message = (
            "Codex-controlled curation is in progress."
            if job.get("status") != "completed"
            else f"Curation is complete. {_review_filename(location_name)} is ready."
        )
        updated_at = job.get("updatedAt")

    details = (
        (workflow_event or {}).get("details") or {}
        if current_event is workflow_event
        else {}
    )
    chatgpt_assignment = (
        store.latest_chatgpt_assignment_schedule(selected_import_id)
        if not (curation_event and current_event is curation_event)
        else None
    )
    next_chatgpt = (
        chatgpt_assignment
        if chatgpt_assignment
        and chatgpt_assignment.get("status") in {"scheduled", "due", "cooling-down"}
        else details.get("nextChatgpt")
    )
    if not isinstance(next_chatgpt, dict):
        next_chatgpt = None

    review_event = next(
        (event for event in reversed(curation_events) if event.get("phase") == "review-file-built"),
        None,
    )
    review_file = None
    if job and job.get("status") == "completed":
        resource_ids = {
            str(resource.get("id") or "")
            for category in job.get("categories") or []
            for resource in (category.get("result") or {}).get("resources") or []
            if resource.get("id")
        }
        review_file = {
            "status": "created" if review_event else "ready",
            "filename": _review_filename(location_name),
            "createdAt": review_event.get("createdAt") if review_event else None,
            "resourceCount": len(resource_ids),
            "categoryCount": int(curation.get("total") or 0),
            "downloadUrl": f"/api/scout-curation-jobs/{job['id']}/review-file",
        }

    return {
        "importId": selected_import_id,
        "sourceName": summary.get("sourceName"),
        "officeName": summary.get("officeName"),
        "locationName": location_name,
        "targetReviewFilename": _review_filename(location_name),
        "phase": phase,
        "message": message,
        "categoryId": category_id or None,
        "categoryLabel": category_labels.get(category_id) or None,
        "updatedAt": updated_at,
        "research": {
            "completed": research_completed,
            "total": research_total,
        },
        "curation": {
            "completed": int(curation.get("completed") or 0),
            "failed": int(curation.get("failed") or 0),
            "total": int(curation.get("total") or research_total),
        },
        "nextChatgpt": next_chatgpt,
        "chatgptAssignment": chatgpt_assignment,
        "reviewFile": review_file,
        "focusedResearch": (
            {
                "jobId": focused_job["id"],
                "status": focused_job["status"],
                "categoryId": focused_job["categoryId"],
                "categoryLabel": focused_job["categoryLabel"],
                "playbookVersion": focused_job["playbookVersion"],
                "completed": int(focused_job["progress"]["completed"]),
                "total": int(focused_job["progress"]["total"]),
                "leadCount": int(focused_job["progress"]["leadCount"]),
                "activeFocus": next((
                    item["focusLabel"] for item in focused_job["passes"]
                    if item["status"] == "assigned"
                ), None),
            }
            if focused_job and not (blind_study and blind_is_newest) else None
        ),
        "blindComparison": (
            {
                "studyId": int(blind_study["id"]),
                "status": str(blind_study["status"]),
                "completedCategories": sum(
                    str((item.get("focusedJob") or {}).get("status") or "") == "completed"
                    for item in blind_study.get("categories") or []
                ),
                "totalCategories": len(blind_study.get("categories") or []),
                "completedPasses": sum(
                    int(((item.get("focusedJob") or {}).get("progress") or {}).get("completed") or 0)
                    for item in blind_study.get("categories") or []
                ),
                "totalPasses": sum(
                    int(((item.get("focusedJob") or {}).get("progress") or {}).get("total") or 0)
                    for item in blind_study.get("categories") or []
                ),
                "leadCount": sum(
                    int(((item.get("focusedJob") or {}).get("progress") or {}).get("leadCount") or 0)
                    for item in blind_study.get("categories") or []
                ),
                "reviewedCategories": sum(
                    bool(item.get("reviewResult"))
                    for item in blind_study.get("categories") or []
                ),
                "shadowRevealed": str(blind_study.get("status") or "") in {
                    "revealed", "reviewing", "completed"
                },
                "reportSha256": str(blind_study.get("reportSha256") or ""),
            }
            if blind_study and blind_is_newest else None
        ),
    }
