from __future__ import annotations

import io
import json
import re
import uuid
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable

from .storage import ResearchStore


RESOURCE_PACKAGE_SCHEMA_VERSION = 3
EDITABLE_RESOURCE_FIELDS = (
    "name", "phone", "address", "website", "hours",
    "verifiedOn", "description", "informationText",
)


class GeneratedResourceError(ValueError):
    """Raised when an accepted candidate cannot become a mergeable resource."""


@dataclass(frozen=True)
class ResourcePackageExport:
    filename: str
    content: bytes
    data: dict[str, Any]

    @property
    def resource_count(self) -> int:
        return len(self.data["resources"])


def _inline(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, (str, int, float)):
        return re.sub(r"\s+", " ", str(value)).strip()
    if isinstance(value, list):
        return "; ".join(part for item in value if (part := _inline(item)))
    if isinstance(value, dict):
        return "; ".join(
            f"{_label(key)}: {text}"
            for key, item in value.items()
            if (text := _inline(item))
        )
    return re.sub(r"\s+", " ", str(value)).strip()


def _items(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [text for item in value if (text := _inline(item))]
    text = _inline(value)
    return [text] if text else []


def _label(value: Any) -> str:
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", str(value or ""))
    text = text.replace("_", " ").replace("-", " ").strip()
    return text[:1].upper() + text[1:] if text else "Detail"


def candidate_description(candidate: dict[str, Any]) -> str:
    for key in ("housingNeed", "description", "resourceType"):
        text = _inline(candidate.get(key))
        if text:
            return text
    return ""


def _section(title: str, items: Iterable[str]) -> list[str]:
    clean = [item for item in items if item]
    if not clean:
        return []
    return [f"**{title}**", *[f"* {item}" for item in clean]]


def candidate_information(candidate: dict[str, Any]) -> str:
    sections: list[list[str]] = []
    description = candidate_description(candidate)
    research_description = _inline(candidate.get("description"))
    details = []
    for key, label in (
        ("organization", "Organization"),
        ("program", "Program"),
        ("resourceType", "Resource type"),
        ("geography", "Area served"),
    ):
        if text := _inline(candidate.get(key)):
            details.append(f"{label}: {text}")
    if research_description and research_description != description:
        details.append(f"Research description: {research_description}")
    sections.append(_section("Resource details", details))

    access = []
    if text := _inline(candidate.get("accessTimeline")):
        access.append(f"Access timeline: {text}")
    availability = candidate.get("availability")
    if isinstance(availability, dict):
        if text := _inline(availability.get("status")):
            access.append(f"Availability: {text}")
        if text := _inline(availability.get("asOf")):
            access.append(f"Availability checked: {text}")
        if text := _inline(availability.get("evidence")):
            access.append(f"Availability detail: {text}")
    elif text := _inline(availability):
        access.append(f"Availability: {text}")
    sections.append(_section("Access and availability", access))

    sections.append(_section("Eligibility", _items(candidate.get("eligibility"))))
    sections.append(_section("Barriers and restrictions", _items(candidate.get("barriers"))))
    if text := _inline(candidate.get("petPolicy")):
        sections.append(_section("Pet and service-animal information", [text]))

    experience = candidate.get("experienceAssessment")
    if isinstance(experience, dict):
        experience_items = [
            f"{_label(key)}: {text}"
            for key, value in experience.items()
            if (text := _inline(value))
        ]
    else:
        experience_items = _items(experience)
    sections.append(_section("Conditions and experience", experience_items))

    verify = [f"Unknown: {item}" for item in _items(candidate.get("unknowns"))]
    verify.extend(
        f"Follow up: {item}" for item in _items(candidate.get("followUpBranches"))
    )
    if verify:
        sections.append(["---", *_section("Verify before referral", verify)])

    evidence_items = []
    evidence = candidate.get("evidence")
    for source in evidence if isinstance(evidence, list) else []:
        if not isinstance(source, dict):
            if text := _inline(source):
                evidence_items.append(text)
            continue
        title = _inline(source.get("title")) or "Research source"
        metadata = ", ".join(
            item for item in (
                _inline(source.get("sourceType")),
                _inline(source.get("reliability")),
                f"accessed {_inline(source.get('accessedAt'))}"
                if _inline(source.get("accessedAt")) else "",
                f"published {_inline(source.get('publishedAt'))}"
                if _inline(source.get("publishedAt")) else "",
                "firsthand" if source.get("firsthand") else "",
            ) if item
        )
        finding = _inline(source.get("finding") or source.get("quoteOrFinding"))
        url = _inline(source.get("url"))
        parts = [title + (f" ({metadata})" if metadata else ""), finding, url]
        evidence_items.append(" — ".join(part for part in parts if part))
    if evidence_items:
        sections.append(["---", *_section("Research sources", evidence_items)])

    return "\n\n".join("\n".join(section) for section in sections if section).strip()


def candidate_to_resource(
    candidate: dict[str, Any],
    category_id: str,
    *,
    resource_id: str | None = None,
    timestamp: datetime | None = None,
) -> dict[str, Any]:
    name = _inline(candidate.get("name") or candidate.get("title"))
    if not name:
        raise GeneratedResourceError("The candidate needs a name before it can become a resource")
    category_id = str(category_id or "").strip()
    if not category_id:
        raise GeneratedResourceError("The imported Housing category is missing an id")
    now = (timestamp or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat()
    return {
        "id": resource_id or uuid.uuid4().hex,
        "name": name,
        "phone": _inline(candidate.get("phone")),
        "address": _inline(candidate.get("address")),
        "website": _inline(candidate.get("website") or candidate.get("url")),
        "hours": _inline(candidate.get("hours")),
        "description": candidate_description(candidate),
        "informationText": candidate_information(candidate),
        "verifiedOn": None,
        "categories": [category_id],
        "categoryFilters": {},
        "forGroups": [],
        "pdfs": [],
        "lastModified": now,
    }


def _normalized_resource_update(
    existing: dict[str, Any], updates: dict[str, Any], timestamp: datetime | None = None
) -> dict[str, Any]:
    next_resource = dict(existing)
    for field in EDITABLE_RESOURCE_FIELDS:
        if field not in updates:
            continue
        value = updates[field]
        if field == "verifiedOn":
            text = _inline(value)
            if text and not re.fullmatch(r"(?:0[1-9]|1[0-2])/\d{2}", text):
                raise GeneratedResourceError("Verified must use MM/YY or remain blank")
            next_resource[field] = text or None
        elif field in {"description", "informationText"}:
            next_resource[field] = str(value or "").strip()
        else:
            next_resource[field] = _inline(value)
    if not str(next_resource.get("name") or "").strip():
        raise GeneratedResourceError("Resource name is required")
    comparable_before = {key: existing.get(key) for key in EDITABLE_RESOURCE_FIELDS}
    comparable_after = {key: next_resource.get(key) for key in EDITABLE_RESOURCE_FIELDS}
    if comparable_before != comparable_after:
        changed = timestamp or datetime.now(timezone.utc)
        next_resource["lastModified"] = changed.astimezone(timezone.utc).isoformat()
    return next_resource


class AcceptedResourceManager:
    def __init__(self, store: ResearchStore) -> None:
        self.store = store

    def ensure_generated_resource(self, discovery_id: int) -> dict[str, Any] | None:
        existing = self.store.get_generated_resource(discovery_id)
        if existing:
            return existing
        discovery = self.store.get_discovery(discovery_id)
        if not discovery:
            raise GeneratedResourceError("Candidate not found")
        if discovery.get("runId") is None:
            return None
        run = self.store.get_run(int(discovery["runId"]))
        if not run:
            raise GeneratedResourceError("The candidate's research run was not found")
        if run.get("researchMode") != "package":
            return None
        import_id = run.get("sourceImportId")
        if import_id is None:
            raise GeneratedResourceError(
                "This package-backed run does not identify its source package"
            )
        category = self.store.import_target_category(int(import_id))
        if not category:
            raise GeneratedResourceError("The imported Housing category was not found")
        resource = candidate_to_resource(
            discovery["candidate"], str(category["id"])
        )
        return self.store.create_generated_resource(
            discovery_id, int(run["id"]), int(import_id), resource
        )

    def review_candidate(
        self, discovery_id: int, status: str, feedback: str = ""
    ) -> dict[str, Any] | None:
        if status == "accepted":
            self.ensure_generated_resource(discovery_id)
        return self.store.review_discovery(discovery_id, status, feedback)

    def update_resource(
        self, discovery_id: int, updates: dict[str, Any]
    ) -> dict[str, Any]:
        generated = self.store.get_generated_resource(discovery_id)
        if not generated:
            raise GeneratedResourceError("Accept this candidate before editing its resource")
        resource = _normalized_resource_update(generated["resource"], updates)
        updated = self.store.update_generated_resource(discovery_id, resource)
        if not updated:
            raise GeneratedResourceError("Generated resource not found")
        return updated

    def build_package(
        self, run_id: int, *, exported_at: datetime | None = None
    ) -> ResourcePackageExport:
        run = self.store.get_run(run_id)
        if not run:
            raise GeneratedResourceError("Research run not found")
        if run.get("researchMode") != "package":
            raise GeneratedResourceError(
                "Resource packages are available only for package-backed research runs"
            )
        import_id = run.get("sourceImportId")
        if import_id is None:
            raise GeneratedResourceError("The research run does not identify a source package")
        generated = self.store.list_generated_resources(run_id, accepted_only=True)
        if not generated:
            raise GeneratedResourceError("Accept at least one candidate before exporting a resource package")
        category = self.store.import_target_category(int(import_id))
        package = self.store.import_summary(int(import_id))
        if not category or not package:
            raise GeneratedResourceError("The source package or Housing category is unavailable")
        if str(package["schema"].get("schemaVersion") or "") != str(
            RESOURCE_PACKAGE_SCHEMA_VERSION
        ):
            raise GeneratedResourceError(
                "Accepted-resource export currently supports source packages using schema 3"
            )

        exported = (exported_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
        resources = [item["resource"] for item in generated]
        package_version_text = str(package["schema"].get("packageVersion") or "Unknown")
        package_version: int | str = (
            int(package_version_text) if package_version_text.isdigit() else package_version_text
        )
        data = {
            "resourcePackageSchemaVersion": RESOURCE_PACKAGE_SCHEMA_VERSION,
            "packageVersion": package_version,
            "packageCreatedAt": exported.isoformat(),
            "lastModified": max(
                (str(resource.get("lastModified") or "") for resource in resources),
                default=exported.isoformat(),
            ) or exported.isoformat(),
            "categories": [category],
            "categoryMigrations": [],
            "forGroups": [],
            "resources": resources,
            "changes": [],
            "deletionRequests": [],
            "deletions": [],
        }
        json_bytes = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        target = io.BytesIO()
        with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            archive.writestr("tso-resources.json", json_bytes)
        source_slug = re.sub(
            r"(?:-resource-package)?\.zip$", "", str(package["sourceName"]), flags=re.IGNORECASE
        )
        source_slug = re.sub(r"[^a-z0-9]+", "-", source_slug.casefold()).strip("-") or "tso"
        filename = f"{source_slug}-housing-research-run-{run_id}-resource-package.zip"
        return ResourcePackageExport(filename=filename, content=target.getvalue(), data=data)
