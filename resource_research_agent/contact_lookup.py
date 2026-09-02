from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .storage import ResearchStore


CONTACT_LOOKUP_SCHEMA_VERSION = 1
REQUEST_KIND = "resource-scout-contact-lookup-request"
RESULTS_KIND = "resource-scout-contact-lookup-results"


@dataclass(frozen=True)
class ContactLookupRequest:
    filename: str
    content: bytes
    data: dict[str, Any]


def _text(value: Any) -> str:
    return str(value or "").strip()


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return cleaned[:70] or "research"


def _candidate_name(candidate: dict[str, Any], fallback: str) -> str:
    return _text(candidate.get("presentationName") or candidate.get("name") or fallback)


def _suggested_searches(name: str, category: str) -> list[str]:
    quoted = f'"{name}"'
    return [
        f"{quoted} Mesa {category}",
        f'{quoted} "Maricopa County" {category}',
        f"{quoted} Arizona official contact",
    ]


def build_contact_lookup_request(
    store: ResearchStore,
    run_id: int,
    *,
    exported_at: datetime | None = None,
) -> ContactLookupRequest:
    run = store.get_run(run_id)
    if not run:
        raise ValueError("Research run not found")
    if run["status"] not in {"completed", "partial"}:
        raise ValueError("Contact lookup is available after research is finished")
    category = _text(run.get("targetCategoryLabel")) or "Resource"
    service_area = _text(
        run.get("sourceServiceArea") or run.get("targetLocation") or run.get("regionalScope")
    )
    candidates = []
    for discovery in reversed(store.list_discoveries(run_id=run_id)):
        candidate = discovery["candidate"]
        if discovery["status"] in {"unavailable", "unreachable"}:
            continue
        if _text(candidate.get("website") or candidate.get("url")):
            continue
        name = _candidate_name(candidate, discovery["name"])
        candidates.append(
            {
                "candidateId": discovery["id"],
                "name": name,
                "organization": _text(
                    candidate.get("organizationName") or candidate.get("organization")
                ),
                "program": _text(candidate.get("programName") or candidate.get("program")),
                "category": category,
                "serviceArea": service_area,
                "suggestedSearches": _suggested_searches(name, category),
            }
        )
    exported = exported_at or datetime.now(timezone.utc)
    data = {
        "schemaVersion": CONTACT_LOOKUP_SCHEMA_VERSION,
        "kind": REQUEST_KIND,
        "runId": run_id,
        "category": category,
        "serviceArea": service_area,
        "exportedAt": exported.isoformat(),
        "instructions": {
            "purpose": "Find an official website for each candidate; include useful phone or address details when readily available.",
            "returnKind": RESULTS_KIND,
            "allowedStatuses": [
                "verified-contact",
                "unavailable",
                "unreachable",
                "unresolved",
            ],
            "rules": [
                "Use verified-contact only when an official website is supported by the cited source.",
                "Use unavailable only with credible evidence that the organization or program closed or ended; a missing or broken page alone is not proof.",
                "Use unreachable when a known official website is dead and the suggested searches find no replacement website or current public phone. This means the lead is not actionable now, not that the organization legally closed.",
                "Use unresolved when the search is inconclusive, explain what remains uncertain, and provide concrete suggestedNextSteps for the Resource Specialist's checklist.",
                "Preserve candidateId exactly so Scout can apply the result to the correct candidate.",
            ],
            "resultShape": {
                "schemaVersion": CONTACT_LOOKUP_SCHEMA_VERSION,
                "kind": RESULTS_KIND,
                "runId": run_id,
                "results": [
                    {
                        "candidateId": "integer from this request",
                        "status": "verified-contact | unavailable | unreachable | unresolved",
                        "website": "",
                        "phone": "",
                        "address": "",
                        "sourceUrl": "",
                        "checkedAt": "ISO-8601 timestamp",
                        "note": "",
                        "suggestedNextSteps": ["specific follow-up search or call"],
                    }
                ],
            },
        },
        "candidates": candidates,
    }
    filename = f"{_slug(category)}-contact-lookup-run-{run_id}.json"
    content = (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    return ContactLookupRequest(filename=filename, content=content, data=data)


def apply_contact_lookup_results(
    store: ResearchStore, run_id: int, payload: Any
) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Contact lookup results must be a JSON object")
    if payload.get("schemaVersion") != CONTACT_LOOKUP_SCHEMA_VERSION:
        raise ValueError("Unsupported contact lookup results schema")
    if payload.get("kind") != RESULTS_KIND:
        raise ValueError("This is not a Resource Scout contact lookup results file")
    try:
        payload_run_id = int(payload.get("runId"))
    except (TypeError, ValueError) as error:
        raise ValueError("Contact lookup results must identify their research run") from error
    if payload_run_id != run_id:
        raise ValueError("These contact lookup results belong to a different research run")
    results = payload.get("results")
    if not isinstance(results, list) or not results:
        raise ValueError("Contact lookup results must contain at least one result")
    return store.apply_contact_lookup_results(run_id, results)
