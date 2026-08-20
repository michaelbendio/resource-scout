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
    "categories", "categoryFilters", "forGroups",
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
    for key in ("serviceNeed", "housingNeed", "description", "resourceType"):
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

    contact_details = []
    for address in _items(candidate.get("additionalAddresses")):
        contact_details.append(f"Additional address: {address}")
    for phone in _items(candidate.get("additionalPhoneNumbers")):
        contact_details.append(f"Additional phone: {phone}")
    sections.append(_section("Additional locations and contacts", contact_details))

    sections.append(_section("Services provided", _items(candidate.get("servicesProvided"))))

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

    sections.append(_section("Eligibility requirements", _items(candidate.get("eligibility"))))
    sections.append(_section("What to expect", _items(candidate.get("whatToExpect"))))
    sections.append(_section("How to best connect", _items(candidate.get("howToBestConnect"))))
    sections.append(_section("Additional notes", _items(candidate.get("additionalNotes"))))
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
    available_types: Iterable[str] = (),
    available_for_groups: Iterable[str] = (),
) -> dict[str, Any]:
    name = _inline(candidate.get("name") or candidate.get("title"))
    if not name:
        raise GeneratedResourceError("The candidate needs a name before it can become a resource")
    category_id = str(category_id or "").strip()
    if not category_id:
        raise GeneratedResourceError("The imported research category is missing an id")
    now = (timestamp or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat()
    type_labels = list(dict.fromkeys(str(value) for value in available_types))
    for_labels = list(dict.fromkeys(str(value) for value in available_for_groups))
    recommended_types = [
        value for value in _items(candidate.get("recommendedTypes")) if value in type_labels
    ]
    recommended_for = [
        value for value in _items(candidate.get("recommendedFor")) if value in for_labels
    ]
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
        "categoryFilters": {category_id: recommended_types} if recommended_types else {},
        "forGroups": recommended_for,
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
        elif field in {"categories", "forGroups"}:
            if not isinstance(value, list):
                raise GeneratedResourceError(f"{field} must be a list")
            next_resource[field] = list(dict.fromkeys(_inline(item) for item in value if _inline(item)))
        elif field == "categoryFilters":
            if not isinstance(value, dict):
                raise GeneratedResourceError("categoryFilters must be an object")
            next_resource[field] = {
                str(key): list(dict.fromkeys(_inline(item) for item in values if _inline(item)))
                for key, values in value.items() if isinstance(values, list)
            }
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
        category = self.store.import_category(
            int(import_id), run.get("targetCategoryId", "housing")
        )
        if not category:
            raise GeneratedResourceError("The research category was not found in the imported package")
        taxonomy = self.store.import_taxonomy(int(import_id))
        category_summary = next(
            (item for item in taxonomy["categories"] if item["id"] == str(category["id"])),
            {"types": []},
        )
        resource = candidate_to_resource(
            discovery["candidate"], str(category["id"]),
            available_types=category_summary.get("types", []),
            available_for_groups=taxonomy["forGroups"],
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
        self._validate_taxonomy(generated["sourceImportId"], resource)
        updated = self.store.update_generated_resource(discovery_id, resource)
        if not updated:
            raise GeneratedResourceError("Generated resource not found")
        return updated

    def taxonomy_for_discovery(self, discovery_id: int) -> dict[str, Any] | None:
        discovery = self.store.get_discovery(discovery_id)
        if not discovery or discovery.get("runId") is None:
            return None
        run = self.store.get_run(int(discovery["runId"]))
        if not run or run.get("sourceImportId") is None:
            return None
        taxonomy = self.store.import_taxonomy(int(run["sourceImportId"]))
        generated = self.store.get_generated_resource(discovery_id)
        warnings = self._taxonomy_warnings(
            generated["resource"] if generated else {}, taxonomy
        )
        return {**taxonomy, "warnings": warnings}

    @staticmethod
    def _taxonomy_warnings(resource: dict[str, Any], taxonomy: dict[str, Any]) -> list[str]:
        categories = {item["id"]: item for item in taxonomy["categories"]}
        warnings: list[str] = []
        for category_id in resource.get("categories", []):
            if category_id not in categories:
                warnings.append(f"Category {category_id!r} is not in the source package")
        for category_id, labels in (resource.get("categoryFilters") or {}).items():
            available = set(categories.get(category_id, {}).get("types", []))
            for label in labels if isinstance(labels, list) else []:
                if label not in available:
                    warnings.append(
                        f"Type {label!r} is no longer defined for {categories.get(category_id, {}).get('label', category_id)}"
                    )
        available_for = set(taxonomy.get("forGroups", []))
        for label in resource.get("forGroups", []):
            if label not in available_for:
                warnings.append(f"For label {label!r} is not in the source package")
        return warnings

    def _validate_taxonomy(self, import_id: int, resource: dict[str, Any]) -> None:
        taxonomy = self.store.import_taxonomy(int(import_id))
        warnings = self._taxonomy_warnings(resource, taxonomy)
        if warnings:
            raise GeneratedResourceError("; ".join(warnings))
        selected = set(resource.get("categories", []))
        if not selected:
            raise GeneratedResourceError("Select at least one category")
        extra_filter_categories = set((resource.get("categoryFilters") or {})) - selected
        if extra_filter_categories:
            raise GeneratedResourceError("Types can be selected only for assigned categories")

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
        package = self.store.import_summary(int(import_id))
        if not package:
            raise GeneratedResourceError("The source package is unavailable")
        if str(package["schema"].get("schemaVersion") or "") != str(
            RESOURCE_PACKAGE_SCHEMA_VERSION
        ):
            raise GeneratedResourceError(
                "Accepted-resource export currently supports source packages using schema 3"
            )

        exported = (exported_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
        resources = [item["resource"] for item in generated]
        for resource in resources:
            self._validate_taxonomy(int(import_id), resource)
        category_ids = list(dict.fromkeys(
            category_id
            for resource in resources
            for category_id in resource.get("categories", [])
        ))
        categories = []
        for category_id in category_ids:
            category = self.store.import_category(int(import_id), category_id)
            if not category:
                raise GeneratedResourceError(f"Category {category_id!r} is unavailable")
            categories.append(category)
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
            "categories": categories,
            "categoryMigrations": [],
            "forGroups": self.store.import_for_groups(int(import_id)),
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
        category_slug = re.sub(
            r"[^a-z0-9]+", "-", str(run.get("targetCategoryLabel") or "resources").casefold()
        ).strip("-") or "resources"
        filename = f"{source_slug}-{category_slug}-research-run-{run_id}-resource-package.zip"
        return ResourcePackageExport(filename=filename, content=target.getvalue(), data=data)
