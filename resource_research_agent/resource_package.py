from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Any, Iterable

RESOURCE_PACKAGE_SCHEMA_VERSION = 3
class GeneratedResourceError(ValueError):
    """Raised when a candidate cannot become a Curator resource draft."""


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


def candidate_information(
    candidate: dict[str, Any],
    additional_fields: Iterable[tuple[str, str]] = (),
) -> str:
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
    for field, _description in additional_fields:
        if text := _inline(candidate.get(field)):
            sections.append(_section(_label(field), [text]))

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
