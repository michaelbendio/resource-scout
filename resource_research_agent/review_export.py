from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .duplicates import DuplicateIndex
from .importer import resource_name
from .storage import ResearchStore


REVIEW_COPY_SCHEMA_VERSION = 1
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TEMPLATE = PROJECT_ROOT / "web" / "review-copy.html"


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
    selected_seed = run.get("prompt", {}).get("selectedSeed")
    if isinstance(selected_seed, dict) and selected_seed.get("name"):
        return f"Housing research from {selected_seed['name']}"
    return "Broad Housing research"


def _known_resource_match(
    store: ResearchStore, index: DuplicateIndex, discovery: dict[str, Any]
) -> dict[str, Any] | None:
    stored = discovery.get("match")
    if not stored:
        return None
    import_id = int(stored["importId"])
    resource_id = str(stored["resourceId"])
    recomputed = next(
        (
            match
            for match in index.match(discovery.get("candidate", {}), import_id=import_id, limit=100)
            if match["resourceId"] == resource_id
        ),
        None,
    )
    if recomputed:
        return {
            "resourceId": resource_id,
            "name": recomputed["name"],
            "isHousingResource": recomputed["isTargetCategory"],
            "score": recomputed["score"],
            "classification": recomputed["classification"],
            "signals": recomputed["signals"],
        }
    record = store.full_resource(import_id, resource_id)
    return {
        "resourceId": resource_id,
        "name": resource_name(record or {}) or resource_id,
        "isHousingResource": None,
        "score": stored.get("score"),
        "classification": "historical-signal",
        "signals": [],
    }


def build_review_copy(
    store: ResearchStore,
    run_id: int,
    *,
    template_path: str | Path = DEFAULT_TEMPLATE,
    exported_at: datetime | None = None,
) -> ReviewCopy:
    run = store.get_run(run_id)
    if not run:
        raise ReviewCopyError("Research run not found")
    if run["status"] != "completed" or not isinstance(run.get("result"), dict):
        raise ReviewCopyError("Only completed research runs can be exported")

    discoveries = list(reversed(store.list_discoveries(run_id=run_id)))
    lessons = [lesson for lesson in reversed(store.list_lessons()) if lesson.get("runId") == run_id]
    index = DuplicateIndex(store)
    candidates = []
    for discovery in discoveries:
        candidates.append({
            "name": discovery["name"],
            "status": discovery["status"],
            "origin": discovery["origin"],
            "createdAt": discovery["createdAt"],
            "reviewedAt": discovery["reviewedAt"],
            "reviewFeedback": discovery["reviewFeedback"],
            "notes": discovery["notes"],
            "candidate": discovery["candidate"],
            "knownResourceMatch": _known_resource_match(store, index, discovery),
        })

    import_id = run.get("sourceImportId") or run.get("seedImportId")
    if import_id is None:
        matched_imports = {
            int(discovery["match"]["importId"])
            for discovery in discoveries
            if discovery.get("match")
        }
        import_id = matched_imports.pop() if len(matched_imports) == 1 else store.latest_import_id()
    package = store.import_summary(int(import_id)) if import_id is not None else None
    exported = exported_at or datetime.now(timezone.utc)
    completed_date = str(run.get("completedAt") or run.get("createdAt") or exported.isoformat())[:10]
    title = _run_title(run)

    data = {
        "reviewCopySchemaVersion": REVIEW_COPY_SCHEMA_VERSION,
        "exportedAt": exported.astimezone(timezone.utc).isoformat(),
        "title": title,
        "notice": (
            "Read-only research for human review. Availability, eligibility, and other facts may change; "
            "verify important details before assisting a client or adding a resource to TSO Resources."
        ),
        "run": {
            "createdAt": run["createdAt"],
            "startedAt": run["startedAt"],
            "completedAt": run["completedAt"],
            "adapter": run["adapter"],
            "assignment": run["assignment"],
            "summary": str(run["result"].get("summary") or ""),
            "candidateCount": len(candidates),
        },
        "sourcePackage": (
            {
                "sourceName": package["sourceName"],
                "sourceSha256": package["sourceSha256"],
                "schemaVersion": package["schema"]["schemaVersion"],
                "packageVersion": package["schema"]["packageVersion"],
                "category": package["category"],
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
            }
            for lesson in lessons
        ],
    }

    template = Path(template_path).read_text(encoding="utf-8")
    marker = "__REVIEW_COPY_DATA__"
    if template.count(marker) != 1:
        raise RuntimeError("Review-copy template must contain exactly one data marker")
    html = template.replace(marker, _embedded_json(data)).encode("utf-8")
    filename = f"{_slug(title)}-review-{completed_date}.html"
    return ReviewCopy(filename=filename, html=html, data=data)
