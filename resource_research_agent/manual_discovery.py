from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from .importer import normalize_index_value


MANUAL_DISCOVERY_PARSER_VERSION = "manual-leads-v2"
MAX_MANUAL_CONTRIBUTION_BYTES = 2 * 1024 * 1024
LEAD_TYPES = {
    "program",
    "provider-organization",
    "access-point",
    "routing-source",
    "directory",
}
REQUIRED_LEAD_FIELDS = (
    "organization",
    "program",
    "website",
    "leadType",
    "locationOrServiceArea",
    "whyRelevant",
    "uncertainty",
)
MARKDOWN_LINK = re.compile(r"^\s*\[[^]]*\]\((https?://[^)]+)\)\s*$", re.IGNORECASE)
DOMAIN_ONLY = re.compile(r"^(?:www\.)?[a-z0-9.-]+\.[a-z]{2,}(?:[/?#].*)?$", re.IGNORECASE)


def build_manual_discovery_assignment(
    *,
    category_label: str,
    service_area: str,
    office_name: str = "",
    regional_scope: str = "",
    known_resources: list[dict[str, Any]] | None = None,
) -> str:
    category = " ".join(str(category_label).split())
    area = " ".join(str(service_area).split())
    if not category:
        raise ValueError("Category label is required")
    if not area:
        raise ValueError("Service area or research location is required")
    known_lines = []
    for resource in known_resources or []:
        resource_id = " ".join(str(resource.get("id") or resource.get("resourceId") or "").split())
        name = " ".join(str(resource.get("name") or "").split())
        if name:
            known_lines.append(f"- {resource_id}: {name}" if resource_id else f"- {name}")
    known_section = (
        "\n".join(known_lines)
        if known_lines
        else "- None are currently recorded for this category."
    )
    scope_lines = [f"Category: {category}", f"Service area: {area}"]
    if office_name.strip():
        scope_lines.append(f"Resource office: {' '.join(office_name.split())}")
    if regional_scope.strip():
        scope_lines.append(f"Nearby scope: {' '.join(regional_scope.split())}")
    schema = json.dumps(
        {
            "leads": [
                {
                    "organization": "",
                    "program": "",
                    "website": "",
                    "phone": "",
                    "address": "",
                    "leadType": "program | provider-organization | access-point | routing-source | directory",
                    "locationOrServiceArea": "",
                    "whyRelevant": "",
                    "uncertainty": "",
                }
            ]
        },
        indent=2,
        ensure_ascii=False,
    )
    return "\n".join(
        [
            f"Discover credible {category} resource leads that a Resource Specialist should investigate for {area}.",
            "This is discovery, not a complete resource dossier. Prioritize distinct providers, named programs, and actionable access points. Do not spend time filling every eligibility, hours, cost, openings, pet-policy, or intake detail.",
            "",
            *scope_lines,
            "",
            "Resources already in the package (avoid obvious repeats, but retain a renamed or materially distinct program with an uncertainty note):",
            known_section,
            "",
            "Return one JSON object in exactly this shape:",
            schema,
            "",
            "Safeguards:",
            "- Prefer an official organization or program URL and use a plain URL when known.",
            "- Include a public phone number or address when it is readily available; do not spend time completing every contact field.",
            "- Separate a named program only when its service, population, intake, or administration is materially distinct.",
            "- Do not split ordinary locations or access offices into separate services.",
            "- Label directories and routing systems rather than presenting them as providers.",
            f"- Do not claim service to {area} without a credible indication; state uncertainty instead.",
            "- Explicitly label historical, uncertain, planned, pilot, grant-funded, stale, or limited-access leads.",
            "- Do not invent missing facts. Blank strings are acceptable.",
            "- Return the JSON object first. You may put source notes after it.",
        ]
    )


def _first_leads_object(text: str) -> tuple[dict[str, Any], int, int]:
    decoder = json.JSONDecoder()
    for match in re.finditer(r"\{", text):
        start = match.start()
        try:
            value, length = decoder.raw_decode(text[start:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and "leads" in value:
            return value, start, start + length
    raise ValueError("No complete JSON object containing a leads array was found")


def normalize_manual_url(value: Any) -> tuple[str, list[str]]:
    raw = str(value or "").strip()
    if not raw:
        return "", []
    warnings: list[str] = []
    markdown = MARKDOWN_LINK.fullmatch(raw)
    if markdown:
        raw = markdown.group(1).strip()
        warnings.append("Markdown link converted to a plain URL")
    if DOMAIN_ONLY.fullmatch(raw):
        raw = "https://" + raw
        warnings.append("URL scheme defaulted to https")
    try:
        parts = urlsplit(raw)
    except ValueError:
        return "", ["Website value is not a valid URL"]
    if parts.scheme.casefold() not in {"http", "https"}:
        return "", ["Website uses an unsafe or unsupported URL scheme"]
    if parts.username or parts.password:
        return "", ["Website URL may not contain credentials"]
    host = (parts.hostname or "").casefold()
    if not host:
        return "", ["Website URL has no host"]
    try:
        port = f":{parts.port}" if parts.port is not None else ""
    except ValueError:
        return "", ["Website URL has an invalid port"]
    normalized = urlunsplit(
        (
            parts.scheme.casefold(),
            host + port,
            parts.path or "/",
            parts.query,
            "",
        )
    )
    return normalized, warnings


def normalize_manual_identity(value: Any) -> str:
    text = re.sub(r"\((?:[A-Za-z][A-Za-z0-9&.-]*\s*){1,5}\)", "", str(value or ""))
    text = re.sub(
        r"\b(?:incorporated|inc|llc|pllc|corp|corporation)\b\.?",
        "",
        text,
        flags=re.IGNORECASE,
    )
    return normalize_index_value("name", text)


def parse_manual_contribution(raw_text: str) -> dict[str, Any]:
    if not isinstance(raw_text, str):
        raise ValueError("Contribution text must be a string")
    byte_count = len(raw_text.encode("utf-8"))
    if byte_count > MAX_MANUAL_CONTRIBUTION_BYTES:
        raise ValueError(
            f"Contribution is too large; the limit is {MAX_MANUAL_CONTRIBUTION_BYTES} bytes"
        )
    result: dict[str, Any] = {
        "status": "error",
        "parserVersion": MANUAL_DISCOVERY_PARSER_VERSION,
        "parsed": None,
        "trailingText": "",
        "warnings": [],
        "error": "",
        "leads": [],
    }
    try:
        value, start, end = _first_leads_object(raw_text.lstrip("\ufeff"))
    except ValueError as error:
        result["error"] = str(error)
        return result
    if start:
        result["warnings"].append("Leading text before the JSON object was preserved")
    trailing = raw_text.lstrip("\ufeff")[end:]
    if trailing.strip():
        result["warnings"].append("Trailing text after the JSON object was preserved")
    result["parsed"] = value
    result["trailingText"] = trailing
    source_leads = value.get("leads")
    if not isinstance(source_leads, list):
        result["error"] = "The leads field must be an array"
        return result
    for ordinal, raw_lead in enumerate(source_leads, start=1):
        if not isinstance(raw_lead, dict):
            result["warnings"].append(f"Lead {ordinal} is not an object and was preserved only in parsed JSON")
            continue
        warnings: list[str] = []
        missing = [field for field in REQUIRED_LEAD_FIELDS if field not in raw_lead]
        if missing:
            warnings.append("Missing fields: " + ", ".join(missing))
        non_string = [
            field
            for field in REQUIRED_LEAD_FIELDS
            if field in raw_lead and not isinstance(raw_lead[field], str)
        ]
        if non_string:
            warnings.append("Non-text fields: " + ", ".join(non_string))

        def field(name: str) -> str:
            value = raw_lead.get(name, "")
            return value.strip() if isinstance(value, str) else ""

        organization = field("organization")
        program = field("program")
        website_raw = field("website")
        website, website_warnings = normalize_manual_url(website_raw)
        warnings.extend(website_warnings)
        lead_type = field("leadType")
        if not organization:
            warnings.append("Organization is blank")
        if lead_type not in LEAD_TYPES:
            warnings.append("Lead type is missing or unsupported")
        result["leads"].append(
            {
                "ordinal": ordinal,
                "raw": raw_lead,
                "organization": organization,
                "program": program,
                "websiteRaw": website_raw,
                "website": website,
                "phone": field("phone"),
                "address": field("address"),
                "leadType": lead_type,
                "locationOrServiceArea": field("locationOrServiceArea"),
                "whyRelevant": field("whyRelevant"),
                "uncertainty": field("uncertainty"),
                "normalizedOrganization": normalize_manual_identity(organization),
                "normalizedProgram": normalize_manual_identity(program),
                "warnings": warnings,
            }
        )
    result["status"] = "parsed"
    return result
