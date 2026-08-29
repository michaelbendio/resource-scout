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

    research_completed = len(completed_category_ids & set(category_labels))
    research_total = len(categories)
    curation = (job or {}).get("progress") or {
        "completed": 0,
        "failed": 0,
        "total": research_total,
    }
    location_name = _location_name(summary)

    if current_event:
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
    next_chatgpt = details.get("nextChatgpt")
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
        "reviewFile": review_file,
    }
