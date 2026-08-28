from __future__ import annotations

import io
import json
import re
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from . import __version__
from .review_export import build_review_copy
from .storage import ResearchStore


CANDIDATE_PACKAGE_SCHEMA_VERSION = 1
CANDIDATE_PACKAGE_MEMBER = "scout-candidates.json"


class CandidatePackageError(ValueError):
    """Raised when Scout cannot create a location candidate package."""


@dataclass(frozen=True)
class CandidatePackage:
    filename: str
    content: bytes
    data: dict[str, Any]


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return cleaned[:70] or "location"


def _location_name(package: dict[str, Any]) -> str:
    office_name = str(package.get("officeName") or "").strip()
    without_suffix = re.sub(r"\s+TSO$", "", office_name, flags=re.IGNORECASE).strip()
    return without_suffix or str(package.get("serviceArea") or "Location").strip()


def _effective_import_id(run: dict[str, Any]) -> int | None:
    reconciliation = run.get("reconciliation")
    if isinstance(reconciliation, dict) and reconciliation.get("targetImportId") is not None:
        return int(reconciliation["targetImportId"])
    value = run.get("sourceImportId") or run.get("seedImportId")
    return int(value) if value is not None else None


def _excluded_candidates(store: ResearchStore, run_id: int) -> list[dict[str, Any]]:
    return [
        {
            "id": discovery["id"],
            "name": discovery["name"],
            "status": discovery["status"],
            "candidate": discovery["candidate"],
            "notes": discovery.get("notes", ""),
        }
        for discovery in reversed(store.list_discoveries(run_id=run_id))
        if discovery["status"] in {"unavailable", "unreachable"}
    ]


def build_candidate_package(
    store: ResearchStore,
    import_id: int | None = None,
    *,
    exported_at: datetime | None = None,
) -> CandidatePackage:
    selected_import_id = import_id or store.latest_import_id()
    if selected_import_id is None:
        raise CandidatePackageError("Connect a resource package before saving candidates")
    package = store.import_summary(int(selected_import_id))
    if not package:
        raise CandidatePackageError("Connected resource package not found")

    exported = exported_at or datetime.now(timezone.utc)
    completed_runs = [
        run for run in reversed(store.list_runs())
        if run.get("status") == "completed"
        and run.get("researchMode", "package") == "package"
        and _effective_import_id(run) == int(selected_import_id)
    ]
    run_payloads = []
    for run in completed_runs:
        review = build_review_copy(store, int(run["id"]), exported_at=exported).data
        manual = review.get("manualDiscovery") or {}
        contributions = store.list_manual_contributions(int(run["id"]))
        run_payloads.append({
            "run": review["run"],
            "candidates": review["candidates"],
            "excludedCandidates": _excluded_candidates(store, int(run["id"])),
            "sourceOnlyRecords": manual.get("sourceOnlyRecords", []),
            "sourceResponses": [
                {
                    "sourceLabel": contribution["sourceLabel"],
                    "sourcePosition": contribution["sourcePosition"],
                    "rawSha256": contribution["rawSha256"],
                    "rawText": contribution["rawText"],
                    "parseStatus": contribution["parseStatus"],
                    "leadCount": len(contribution["leads"]),
                }
                for contribution in contributions
            ],
        })

    category_manifest = []
    for category in package.get("categories", []):
        category_runs = [
            item for item in run_payloads
            if item["run"]["targetCategoryId"] == category["id"]
        ]
        category_manifest.append({
            "id": category["id"],
            "label": category["label"],
            "runIds": [item["run"]["id"] for item in category_runs],
            "candidateCount": sum(len(item["candidates"]) for item in category_runs),
            "excludedCandidateCount": sum(
                len(item["excludedCandidates"]) for item in category_runs
            ),
            "researchStatus": "completed" if category_runs else "not-researched",
        })

    location_name = _location_name(package)
    data = {
        "candidatePackageSchemaVersion": CANDIDATE_PACKAGE_SCHEMA_VERSION,
        "scoutVersion": __version__,
        "exportedAt": exported.astimezone(timezone.utc).isoformat(),
        "location": {
            "name": location_name,
            "officeName": package.get("officeName", ""),
            "serviceArea": package.get("serviceArea", ""),
        },
        "sourcePackage": {
            "importId": int(selected_import_id),
            "sourceName": package["sourceName"],
            "sourceSha256": package["sourceSha256"],
            "contentSha256": package["contentSha256"],
            "schemaVersion": package["schema"]["schemaVersion"],
            "packageVersion": package["schema"]["packageVersion"],
        },
        "categories": package.get("categories", []),
        "forGroups": package.get("forGroups", []),
        "categoryManifest": category_manifest,
        "runs": run_payloads,
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            CANDIDATE_PACKAGE_MEMBER,
            json.dumps(data, ensure_ascii=False, indent=2),
        )
    return CandidatePackage(
        filename=f"{_slug(location_name)}-candidates.zip",
        content=buffer.getvalue(),
        data=data,
    )
