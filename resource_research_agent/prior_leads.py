from __future__ import annotations

import re
from copy import deepcopy
from typing import Any, Iterable

from .optimization import (
    candidate_identity_key,
    canonicalize_discovery_url,
    sha256_json,
    validate_query_plan,
)


PRIOR_LEAD_MANIFEST_SCHEMA_VERSION = 1
PRIOR_LEAD_POLICY_VERSION = "prior-result-leads-v1"
PRIOR_LEAD_DISPOSITIONS = {
    "candidate",
    "routed",
    "rejected",
    "unresolved",
    "excluded-existing",
    "needs-review",
}
ALLOWED_LEAD_KEYS = {
    "leadKey",
    "organization",
    "program",
    "aliases",
    "urls",
    "historicalDisposition",
    "provenance",
}


def _text(value: Any, field: str) -> str:
    text = " ".join(str(value or "").split())
    if not text:
        raise ValueError(f"Prior-result lead manifest field {field} must not be blank")
    return text


def _text_list(value: Any, field: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"Prior-result lead manifest field {field} must be an array")
    result = []
    for item in value:
        text = _text(item, field)
        if text not in result:
            result.append(text)
    return result


def _lead_key(organization: str, program: str, aliases: list[str], urls: list[str]) -> str:
    if organization and program:
        return f"identity:{candidate_identity_key(organization, program)}"
    if urls:
        return f"url:{urls[0]}"
    if aliases:
        return f"alias:{aliases[0].casefold()}"
    raise ValueError("Prior-result lead needs an identity, URL, or alias")


def normalize_prior_lead_manifest(value: dict[str, Any]) -> dict[str, Any]:
    """Validate and canonicalize historical names/URLs without importing facts."""

    if not isinstance(value, dict) or value.get("schemaVersion") != 1:
        raise ValueError("Prior-result lead manifest schemaVersion must be 1")
    manifest_id = _text(value.get("manifestId"), "manifestId")
    category_id = _text(value.get("categoryId"), "categoryId")
    target_location = _text(value.get("targetLocation"), "targetLocation")
    created_at = _text(value.get("createdAt"), "createdAt")
    sources_value = value.get("sources")
    if not isinstance(sources_value, list) or not sources_value:
        raise ValueError("Prior-result lead manifest needs a non-empty sources array")
    sources: list[dict[str, Any]] = []
    source_ids: set[str] = set()
    for source in sources_value:
        if not isinstance(source, dict):
            raise ValueError("Prior-result lead manifest source must be an object")
        source_id = _text(source.get("id"), "sources.id")
        if source_id in source_ids:
            raise ValueError(f"Duplicate prior-result lead source id: {source_id}")
        source_ids.add(source_id)
        normalized_source = {
            "id": source_id,
            "kind": _text(source.get("kind"), "sources.kind"),
            "sourceRunId": _text(source.get("sourceRunId"), "sources.sourceRunId"),
            "sourceStageKey": _text(
                source.get("sourceStageKey"), "sources.sourceStageKey"
            ),
            "observedAt": _text(source.get("observedAt"), "sources.observedAt"),
        }
        if source.get("artifactSha256"):
            artifact_sha256 = _text(
                source["artifactSha256"], "sources.artifactSha256"
            )
            if not re.fullmatch(r"[0-9a-f]{64}", artifact_sha256):
                raise ValueError(
                    "Prior-result lead source artifactSha256 must be a SHA-256 digest"
                )
            normalized_source["artifactSha256"] = artifact_sha256
        sources.append(normalized_source)
    leads_value = value.get("leads")
    if not isinstance(leads_value, list) or not leads_value:
        raise ValueError("Prior-result lead manifest needs a non-empty leads array")
    leads: list[dict[str, Any]] = []
    lead_keys: set[str] = set()
    for raw in leads_value:
        if not isinstance(raw, dict):
            raise ValueError("Prior-result lead must be an object")
        forbidden = sorted(set(raw) - ALLOWED_LEAD_KEYS)
        if forbidden:
            raise ValueError(
                "Prior-result lead contains current factual fields: "
                + ", ".join(forbidden)
            )
        organization = " ".join(str(raw.get("organization") or "").split())
        program = " ".join(str(raw.get("program") or "").split())
        if bool(organization) != bool(program):
            raise ValueError(
                "Prior-result lead organization and program must appear together"
            )
        aliases = _text_list(raw.get("aliases"), "leads.aliases")
        try:
            urls = sorted(
                {
                    canonicalize_discovery_url(url)
                    for url in _text_list(raw.get("urls"), "leads.urls")
                }
            )
        except ValueError as error:
            raise ValueError(f"Prior-result lead URL is invalid: {error}") from error
        disposition = _text(
            raw.get("historicalDisposition"), "leads.historicalDisposition"
        )
        if disposition not in PRIOR_LEAD_DISPOSITIONS:
            raise ValueError(f"Unsupported historical lead disposition: {disposition}")
        lead_key = _lead_key(organization, program, aliases, urls)
        supplied_key = str(raw.get("leadKey") or "").strip()
        if supplied_key and supplied_key != lead_key:
            raise ValueError(f"Prior-result lead key is not canonical: {supplied_key}")
        if lead_key in lead_keys:
            raise ValueError(f"Duplicate prior-result lead key: {lead_key}")
        lead_keys.add(lead_key)
        provenance_value = raw.get("provenance")
        if not isinstance(provenance_value, list) or not provenance_value:
            raise ValueError("Prior-result lead needs provenance")
        provenance: list[dict[str, str]] = []
        for item in provenance_value:
            if not isinstance(item, dict):
                raise ValueError("Prior-result lead provenance must be an object")
            source_id = _text(item.get("sourceId"), "leads.provenance.sourceId")
            if source_id not in source_ids:
                raise ValueError(f"Unknown prior-result lead source id: {source_id}")
            record = {
                "sourceId": source_id,
                "sourceRunId": _text(
                    item.get("sourceRunId"), "leads.provenance.sourceRunId"
                ),
                "sourceStageKey": _text(
                    item.get("sourceStageKey"), "leads.provenance.sourceStageKey"
                ),
                "observedAt": _text(
                    item.get("observedAt"), "leads.provenance.observedAt"
                ),
                "historicalDisposition": (
                    _text(
                        item.get("historicalDisposition"),
                        "leads.provenance.historicalDisposition",
                    )
                    if item.get("historicalDisposition")
                    else disposition
                ),
            }
            if record["historicalDisposition"] not in PRIOR_LEAD_DISPOSITIONS:
                raise ValueError(
                    "Unsupported provenance historical disposition: "
                    + record["historicalDisposition"]
                )
            if record not in provenance:
                provenance.append(record)
        leads.append(
            {
                "leadKey": lead_key,
                "organization": organization,
                "program": program,
                "aliases": aliases,
                "urls": urls,
                "historicalDisposition": disposition,
                "provenance": provenance,
            }
        )
    normalized = {
        "schemaVersion": PRIOR_LEAD_MANIFEST_SCHEMA_VERSION,
        "policyVersion": PRIOR_LEAD_POLICY_VERSION,
        "manifestId": manifest_id,
        "categoryId": category_id,
        "targetLocation": target_location,
        "createdAt": created_at,
        "sources": sorted(sources, key=lambda item: item["id"]),
        "leads": sorted(leads, key=lambda item: item["leadKey"]),
    }
    normalized["manifestSha256"] = sha256_json(normalized)
    supplied_hash = str(value.get("manifestSha256") or "").strip()
    if supplied_hash and supplied_hash != normalized["manifestSha256"]:
        raise ValueError("Prior-result lead manifest SHA-256 does not match its content")
    return normalized


def build_prior_lead_manifest(
    *,
    manifest_id: str,
    category_id: str,
    target_location: str,
    created_at: str,
    sources: Iterable[dict[str, Any]],
    leads: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    return normalize_prior_lead_manifest(
        {
            "schemaVersion": PRIOR_LEAD_MANIFEST_SCHEMA_VERSION,
            "manifestId": manifest_id,
            "categoryId": category_id,
            "targetLocation": target_location,
            "createdAt": created_at,
            "sources": list(deepcopy(tuple(sources))),
            "leads": list(deepcopy(tuple(leads))),
        }
    )


def augment_query_plan_with_prior_leads(
    plan: dict[str, Any], manifest: dict[str, Any]
) -> dict[str, Any]:
    normalized = normalize_prior_lead_manifest(manifest)
    result = deepcopy(plan)
    if str(result.get("categoryId") or "") != normalized["categoryId"]:
        raise ValueError("Prior-result lead manifest belongs to another category")
    if str(result.get("targetLocation") or "").casefold() != str(
        normalized["targetLocation"]
    ).casefold():
        raise ValueError("Prior-result lead manifest belongs to another target location")
    if any(branch.get("key") == "prior-result-leads" for branch in result["branches"]):
        raise ValueError("Query plan already contains prior-result leads")
    if len(normalized["leads"]) > 1000:
        raise ValueError("Prior-result lead manifests support at most 1000 leads")
    purpose = (
        "Recheck preserved historical names and URLs under current identity, geography, "
        "actionability, package, status, and evidence gates."
    )
    queries = []
    for position, lead in enumerate(normalized["leads"], start=1):
        identity_text = (
            f'"{lead["organization"]}" "{lead["program"]}"'
            if lead["organization"] and lead["program"]
            else f'"{lead["aliases"][0]}"'
            if lead["aliases"]
            else lead["urls"][0]
        )
        queries.append(
            {
                "key": f"prior-result-{sha256_json(lead['leadKey'])[:16]}",
                "position": position,
                "purpose": purpose,
                "query": (
                    f"{identity_text} {result['targetLocation']} current service intake"
                ),
                "priorLeadKey": lead["leadKey"],
            }
        )
    count = len(queries)
    result["branches"].append(
        {
            "key": "prior-result-leads",
            "purpose": purpose,
            "required": True,
            "saturation": {
                "minimumQueries": count,
                "maximumQueries": count,
                "consecutiveNoNewIdentityQueries": count,
                "noveltyUnit": "currently qualified package-eligible identity",
            },
            "queries": queries,
        }
    )
    result["schemaVersion"] = max(5, int(result.get("schemaVersion") or 0))
    result["priorLeadPolicyVersion"] = PRIOR_LEAD_POLICY_VERSION
    result["priorResultLeadManifestSha256"] = normalized["manifestSha256"]
    validate_query_plan(result)
    return result
