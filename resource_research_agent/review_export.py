from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .duplicates import DuplicateIndex
from .resource_package import RESOURCE_PACKAGE_SCHEMA_VERSION, candidate_to_resource
from .storage import ResearchStore


REVIEW_COPY_SCHEMA_VERSION = 6
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TEMPLATE = PROJECT_ROOT / "web" / "review-copy.html"
DEFAULT_SCRIPT = PROJECT_ROOT / "web" / "review-copy.js"


class ReviewCopyError(ValueError):
    """Raised when a research run cannot be exported as a review copy."""


@dataclass(frozen=True)
class ReviewCopy:
    filename: str
    html: bytes
    data: dict[str, Any]


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return cleaned[:70] or "housing"


def _embedded_json(value: dict[str, Any]) -> str:
    """Serialize data without allowing it to close the inert script element."""
    return (
        json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        .replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def _run_title(run: dict[str, Any]) -> str:
    category = str(run.get("targetCategoryLabel") or "Housing")
    if run.get("researchMode") == "standalone-location" and run.get("targetLocation"):
        return f"{category} research for {run['targetLocation']}"
    selected_seed = run.get("prompt", {}).get("selectedSeed")
    if isinstance(selected_seed, dict) and selected_seed.get("name"):
        return f"{category} research from {selected_seed['name']}"
    return f"{category} research"


def _known_resource_match(
    index: DuplicateIndex, discovery: dict[str, Any]
) -> dict[str, Any] | None:
    explained = index.explain_saved_match(discovery)
    if not explained:
        return None
    return {
        "resourceId": explained["resourceId"],
        "name": explained["name"],
        "isTargetCategoryResource": explained["isTargetCategory"],
        "score": explained["score"],
        "classification": explained["classification"],
        "signals": explained["signals"],
    }


def build_review_copy(
    store: ResearchStore,
    run_id: int,
    *,
    template_path: str | Path = DEFAULT_TEMPLATE,
    script_path: str | Path = DEFAULT_SCRIPT,
    exported_at: datetime | None = None,
) -> ReviewCopy:
    run = store.get_run(run_id)
    if not run:
        raise ReviewCopyError("Research run not found")
    if run["status"] not in {"completed", "partial"} or not isinstance(run.get("result"), dict):
        raise ReviewCopyError("Only completed or partially completed research runs can be exported")

    discoveries = list(reversed(store.list_discoveries(run_id=run_id)))
    lessons = [lesson for lesson in reversed(store.list_lessons()) if lesson.get("runId") == run_id]
    import_id = run.get("sourceImportId") or run.get("seedImportId")
    if import_id is None:
        matched_imports = {
            int(discovery["match"]["importId"])
            for discovery in discoveries
            if discovery.get("match")
        }
        if len(matched_imports) == 1:
            import_id = matched_imports.pop()
        elif run.get("researchMode", "package") == "package":
            # Older package-backed runs predate explicit source provenance.
            import_id = store.latest_import_id()
    package = store.import_summary(int(import_id)) if import_id is not None else None
    taxonomy = store.import_taxonomy(int(import_id)) if import_id is not None else {
        "categories": [], "forGroups": []
    }
    category_definitions = [
        category
        for item in taxonomy["categories"]
        if (category := store.import_category(int(import_id), item["id"])) is not None
    ] if import_id is not None else []
    exported = exported_at or datetime.now(timezone.utc)
    completed_date = str(run.get("completedAt") or run.get("createdAt") or exported.isoformat())[:10]
    title = _run_title(run)
    source_identity = package["sourceSha256"] if package else "standalone"
    review_id = uuid.uuid5(
        uuid.NAMESPACE_URL, f"resource-research-review:{source_identity}:{run_id}"
    ).hex
    package_eligible = bool(
        package
        and run.get("researchMode", "package") == "package"
        and str(package["schema"].get("schemaVersion") or "")
        == str(RESOURCE_PACKAGE_SCHEMA_VERSION)
    )
    index = DuplicateIndex(store)
    candidates = []
    target_category_id = str(run.get("targetCategoryId") or "housing")
    category_summary = next(
        (item for item in taxonomy["categories"] if item["id"] == target_category_id),
        {"types": []},
    )
    for discovery in discoveries:
        generated = store.get_generated_resource(discovery["id"])
        resource_draft = generated["resource"] if generated else None
        if package_eligible and resource_draft is None:
            resource_draft = candidate_to_resource(
                discovery["candidate"],
                target_category_id,
                resource_id=uuid.uuid5(
                    uuid.NAMESPACE_URL,
                    f"resource-research-resource:{source_identity}:{run_id}:{discovery['id']}",
                ).hex,
                timestamp=exported,
                available_types=category_summary.get("types", []),
                available_for_groups=taxonomy["forGroups"],
            )
        candidates.append({
            "id": discovery["id"],
            "name": discovery["name"],
            "status": discovery["status"],
            "origin": discovery["origin"],
            "createdAt": discovery["createdAt"],
            "updatedAt": discovery["updatedAt"],
            "reviewedAt": discovery["reviewedAt"],
            "reviewFeedback": discovery["reviewFeedback"],
            "useForFutureResearch": False,
            "matchAssessment": discovery["matchAssessment"],
            "matchAssessedAt": discovery["matchAssessedAt"],
            "notes": discovery["notes"],
            "candidate": discovery["candidate"],
            "knownResourceMatch": _known_resource_match(index, discovery),
            "resourceDraft": resource_draft,
        })

    data = {
        "reviewCopySchemaVersion": REVIEW_COPY_SCHEMA_VERSION,
        "reviewFeedbackSchemaVersion": 1,
        "reviewId": review_id,
        "exportedAt": exported.astimezone(timezone.utc).isoformat(),
        "title": title,
        "notice": (
            (
                f"This research run stopped after {run['progress']['completed']} of {run['progress']['total']} stages. "
                "The completed-stage findings remain available for review, but the research is incomplete. "
            )
            if run["status"] == "partial" else ""
        ) + (
            "Portable exploratory location research for human review; it is not an official or comprehensive "
            "TSO Resources inventory. Availability, eligibility, and other facts may change; verify important "
            "details before assisting a client. Review decisions and feedback can be saved, but standalone "
            "research cannot create a resource package."
            if run.get("researchMode") == "standalone-location"
            else "Portable research for human review. Availability, eligibility, and other facts may change; "
            "verify important details before assisting a client or adding an accepted resource to TSO Resources."
        ),
        "run": {
            "id": run["id"],
            "createdAt": run["createdAt"],
            "startedAt": run["startedAt"],
            "completedAt": run["completedAt"],
            "status": run["status"],
            "adapter": run["adapter"],
            "assignment": run["assignment"],
            "researchMode": run.get("researchMode", "package"),
            "targetLocation": run.get("targetLocation"),
            "regionalScope": run.get("regionalScope", ""),
            "targetCategoryId": run.get("targetCategoryId", "housing"),
            "targetCategoryLabel": run.get("targetCategoryLabel", "Housing"),
            "summary": str(run["result"].get("summary") or ""),
            "candidateCount": len(candidates),
            "progress": run.get("progress", {"total": 0, "completed": 0, "failed": 0}),
            "stages": [
                {
                    "title": stage["title"],
                    "position": stage["position"],
                    "status": stage["status"],
                    "completedAt": stage["completedAt"],
                    "error": stage["error"],
                }
                for stage in run.get("stages", [])
            ],
        },
        "sourcePackage": (
            {
                "sourceName": package["sourceName"],
                "sourceSha256": package["sourceSha256"],
                "schemaVersion": package["schema"]["schemaVersion"],
                "packageVersion": package["schema"]["packageVersion"],
                "resourcePackageSchemaVersion": RESOURCE_PACKAGE_SCHEMA_VERSION,
                "packageEligible": package_eligible,
                "categories": category_definitions,
                "categorySummaries": taxonomy["categories"],
                "forGroups": store.import_for_groups(int(import_id)),
                "category": {
                    "id": run.get("targetCategoryId", "housing"),
                    "label": run.get("targetCategoryLabel", "Housing"),
                },
            }
            if package
            else None
        ),
        "candidates": candidates,
        "lessons": [
            {
                "scope": lesson["scope"],
                "text": lesson["text"],
                "rationale": lesson["rationale"],
                "status": lesson["status"],
                "source": lesson["source"],
                "researchMode": lesson.get("researchMode", "package"),
                "targetLocation": lesson.get("targetLocation"),
            }
            for lesson in lessons
        ],
    }

    template = Path(template_path).read_text(encoding="utf-8")
    data_marker = "__REVIEW_COPY_DATA__"
    script_marker = "__REVIEW_COPY_SCRIPT__"
    if template.count(data_marker) != 1:
        raise RuntimeError("Review-copy template must contain exactly one data marker")
    if template.count(script_marker) != 1:
        raise RuntimeError("Review-copy template must contain exactly one script marker")
    script = Path(script_path).read_text(encoding="utf-8")
    if "</script" in script.casefold():
        raise RuntimeError("Review-copy script may not contain a closing script tag")
    html = template.replace(data_marker, _embedded_json(data)).replace(script_marker, script)
    html = html.encode("utf-8")
    filename = f"{_slug(title)}-curator-{completed_date}.html"
    return ReviewCopy(filename=filename, html=html, data=data)
