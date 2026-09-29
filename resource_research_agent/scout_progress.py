from __future__ import annotations

import re
import json
from pathlib import Path
from typing import Any

from .storage import ResearchStore
from .scout_review_handoff import review_handoff
from .focused_research import CODEX_FIRST_EXPERIMENT_MODE
from .curation_eta import ACTIVE_PHASES, estimate_curation
from .review_progress import review_progress
from .review_eta import estimate_review


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


def prepared_delivery_context(store, import_id):
    """Use only the pipeline belonging to this exact database/import."""
    database = getattr(store, 'path', None)
    if not isinstance(database, (str, Path)):
        return None
    database = Path(database).resolve()
    path = database.parent / 'pipeline.json'
    if not path.is_file():
        return None
    config = json.loads(path.read_text())
    if (not config.get('preparedMode') or config.get('importId') != import_id
            or Path(config['database']).resolve() != database):
        return None
    state_path = path.parent / 'pipeline-status.json'
    state = json.loads(state_path.read_text()) if state_path.exists() else {}
    date_format = 'YY-MM-DD' if config.get('shortDeliveryDate') else 'YYYY-MM-DD'
    slug = config.get('officeSlug') or re.sub(r'[^a-z0-9]+', '-', config['officeName'].lower()).strip('-')
    artifact = state.get('delivery', {}).get('artifactFile')
    review_ids = config.get('reviewCategoryIds')
    seed_categories = json.loads(Path(config['sourceSeedPath']).read_text())['categories'] if config.get('sourceSeedPath') else []
    if review_ids is None and config.get('sourceSeedPath'):
        review_ids = [c['id'] for c in seed_categories if c['id'] != 'miscellaneous']
    review = review_progress(path.parent, review_ids, state) if review_ids else None
    if review:
        labels = {c['id']: c.get('label', c['id']) for c in seed_categories}
        for row in review['categories']:
            row['label'] = labels.get(row['categoryId'], row['categoryId'])
        review['estimate'] = estimate_review(path.parent, database, state.get('jobId'), review, state)
    return dict(kind='prepared-resources', filename=Path(artifact).name if artifact else
                f'scout-{slug}-prepared-resources-<{date_format}>.json',
                phase=state.get('phase'), automaticReview=bool(config.get('automaticReview')),
                artifactFile=artifact, artifactSha256=state.get('delivery', {}).get('artifactSha256'),
                counts=state.get('delivery', {}).get('counts', {}),
                pauseFinished=bool(state.get('pauseFinishedAt')),
                reviewProgress=review,
                readyForSave=state.get('phase') == 'prepared-delivery-complete')


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
    codex_jobs_by_category = {
        str(item["categoryId"]): item
        for item in focused_jobs
        if str(item.get("experimentMode") or "") == CODEX_FIRST_EXPERIMENT_MODE
    }
    codex_jobs = [
        codex_jobs_by_category[category_id]
        for category_id in category_labels
        if category_id in codex_jobs_by_category
    ]
    codex_plan_in_progress = bool(
        codex_jobs and any(item["status"] != "completed" for item in codex_jobs)
    )
    if codex_plan_in_progress:
        job = None
        curation_events = []
        curation_event = None
        current_event = workflow_event
    focused_job = next((
        item for item in focused_jobs
        if str(item.get("experimentMode") or "") != CODEX_FIRST_EXPERIMENT_MODE
    ), None)
    focused_active = bool(
        focused_job and focused_job.get("status") in {"pending", "in-progress"}
    )
    focused_is_newest = bool(
        focused_job
        and str(focused_job.get("updatedAt") or "")
        >= str((current_event or {}).get("createdAt") or "")
    )

    research_completed = len(completed_category_ids & set(category_labels))
    research_total = len(categories)
    if codex_jobs:
        research_completed = sum(item["status"] == "completed" for item in codex_jobs)
        research_total = len(codex_jobs)
    curation = (job or {}).get("progress") or {
        "completed": 0,
        "failed": 0,
        "total": research_total,
    }
    location_name = _location_name(summary)
    prepared = prepared_delivery_context(store, selected_import_id)
    target_filename = prepared['filename'] if prepared else _review_filename(location_name)

    # A completed research plan must not hide the newer curation/review phase.
    if codex_jobs and (codex_plan_in_progress or not job):
        completed_codex = sum(item["status"] == "completed" for item in codex_jobs)
        active_codex = next((item for item in codex_jobs if item["status"] != "completed"), None)
        phase = "codex-first-research" if active_codex else "codex-first-research-complete"
        category_id = str((active_codex or {}).get("categoryId") or "")
        if active_codex:
            assignments = store.list_codex_first_assignments(int(active_codex["id"]))
            completed_sources = sum(item["status"] == "completed" for item in assignments)
            message = (
                f"Codex-first research: {active_codex['categoryLabel']}. "
                f"{completed_codex} of {len(codex_jobs)} categories complete; "
                f"{active_codex['progress']['completed']} of {active_codex['progress']['total']} "
                f"Codex passes and {completed_sources} challenger or shadow responses complete."
            )
            updated_at = max(
                [str(active_codex.get("updatedAt") or "")]
                + [str(item.get("updatedAt") or "") for item in assignments]
            )
            heartbeat_event = (
                workflow_event
                if workflow_event
                and str(workflow_event.get("phase") or "") == "codex-first-heartbeat"
                and str(workflow_event.get("categoryId") or "") == category_id
                and str(workflow_event.get("createdAt") or "") >= str(updated_at or "")
                else None
            )
            if heartbeat_event:
                message = str(heartbeat_event.get("message") or message)
                updated_at = heartbeat_event.get("createdAt")
        else:
            message = (
                f"Codex-first research is complete for all {len(codex_jobs)} categories. "
                "Scout is ready for Codex-controlled curation."
            )
            updated_at = max(str(item.get("updatedAt") or "") for item in codex_jobs)
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
            else f"Curation is complete. {target_filename} is awaiting review."
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
    if job and job.get("status") == "completed" and not prepared:
        resource_ids = {
            str(resource.get("id") or "")
            for category in job.get("categories") or []
            for resource in (category.get("result") or {}).get("resources") or []
            if resource.get("id")
        }
        handoff = review_handoff(job, curation_events)
        review_file = {
            **handoff,
            "status": ("created" if review_event else "ready") if handoff["readyForSave"] else "awaiting-codex-review",
            "filename": _review_filename(location_name),
            "createdAt": review_event.get("createdAt") if review_event else None,
            "resourceCount": len(resource_ids),
            "categoryCount": int(curation.get("total") or 0),
            "downloadUrl": f"/api/scout-curation-jobs/{job['id']}/review-file",
        }

        if not handoff["readyForSave"]:
            from .scout_curation import ScoutCurationError
            from .scout_review_readiness import require_review_ready
            try:
                require_review_ready(store, job)
            except ScoutCurationError as exc:
                review_file["readinessIssue"] = str(exc)
            phase = "awaiting-codex-review"
            message = "Curation is complete. Start a Codex session and ask for a review. Save will be available when that review is complete."
            category_id = ""
        else:
            phase = "codex-review-completed"
            message = "Codex review is complete. The review HTML is ready to save."
            category_id = ""

    if prepared and prepared['phase'] == 'paused':
        phase = 'paused'
        message = ('Curation is paused at a saved checkpoint. Automatic review is paused.'
                   if prepared['pauseFinished'] else 'Pause requested: finishing the current category, then stopping.')

    curation_eta = (
        estimate_curation(job, curation_events)
        if job and phase in ACTIVE_PHASES else None
    )
    if curation_eta:
        message = f"{message.rstrip('. ')}, {curation_eta['label']}."

    if prepared and job and job.get('status') == 'completed':
        phase = prepared['phase'] or 'ready-for-codex-review'
        message = {
            'review': 'Curation is complete. Codex is reviewing the prepared resources.',
            'ready-review': 'Curation is complete. The authorized Codex review is starting.',
            'prepared-delivery-ready': 'The prepared JSON is generated and validated. Final registry checkpoint remains.',
            'prepared-delivery-complete': 'The prepared-resources JSON is complete and ready to save.',
            'needs-attention': 'Prepared delivery needs diagnosis. Saved research and review work are preserved.',
        }.get(phase, 'Curation is complete. Prepared-resource review remains.')
        if prepared['readyForSave']:
            review_file = dict(status='created', filename=target_filename, readyForSave=True,
                resourceCount=prepared['counts'].get('resources', 0),
                categoryCount=len(job['categories']), downloadUrl=f'/api/scout-prepared-resources?importId={selected_import_id}')

    return {
        "importId": selected_import_id,
        "sourceName": summary.get("sourceName"),
        "officeName": summary.get("officeName"),
        "locationName": location_name,
        "targetReviewFilename": target_filename,
        "workProduct": prepared,
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
            "estimate": curation_eta,
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
            if focused_job and not codex_jobs else None
        ),
        "codexFirstResearch": (
            {
                "status": "completed" if all(item["status"] == "completed" for item in codex_jobs) else "in-progress",
                "completedCategories": sum(item["status"] == "completed" for item in codex_jobs),
                "totalCategories": len(codex_jobs),
                "completedPasses": sum(
                    int(item["progress"]["completed"]) for item in codex_jobs
                ),
                "totalPasses": sum(
                    int(item["progress"]["total"]) for item in codex_jobs
                ),
                "leadCount": sum(
                    int(item["progress"]["leadCount"]) for item in codex_jobs
                ),
                "activeCategory": category_labels.get(category_id) or None,
            }
            if codex_jobs else None
        ),
    }
