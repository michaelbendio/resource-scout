from __future__ import annotations

import re
from copy import deepcopy
from typing import Any

from .optimization import canonicalize_discovery_url, sha256_json


REFERRAL_GRAPH_SCHEMA_VERSION = 1
REFERRAL_GRAPH_POLICY_VERSION = "authoritative-one-hop-referrals-v1"
REFERRAL_SOURCE_AUTHORITIES = {
    "direct-provider",
    "government-referral",
    "reputable-secondary",
}
REFERRAL_RELATIONSHIPS = {
    "provides-program",
    "authoritative-referral",
    "coordinated-entry-referral",
}
MAX_REFERRAL_EDGES = 200
MAX_REFERRAL_EDGES_PER_SOURCE = 25


def _text(value: Any, field: str) -> str:
    text = " ".join(str(value or "").split())
    if not text:
        raise ValueError(f"Referral graph field {field} must not be blank")
    return text


def normalize_referral_graph(value: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("schemaVersion") != 1:
        raise ValueError("Referral graph schemaVersion must be 1")
    graph_id = _text(value.get("graphId"), "graphId")
    category_id = _text(value.get("categoryId"), "categoryId")
    target_location = _text(value.get("targetLocation"), "targetLocation")
    created_at = _text(value.get("createdAt"), "createdAt")
    source_artifact_sha256 = _text(
        value.get("sourceArtifactSha256"), "sourceArtifactSha256"
    )
    if not re.fullmatch(r"[0-9a-f]{64}", source_artifact_sha256):
        raise ValueError("Referral graph sourceArtifactSha256 must be a SHA-256 digest")
    edges_value = value.get("edges")
    if not isinstance(edges_value, list) or not edges_value:
        raise ValueError("Referral graph needs a non-empty edges array")
    if len(edges_value) > MAX_REFERRAL_EDGES:
        raise ValueError(f"Referral graph supports at most {MAX_REFERRAL_EDGES} edges")
    edges = []
    keys: set[str] = set()
    source_counts: dict[str, int] = {}
    for raw in edges_value:
        if not isinstance(raw, dict):
            raise ValueError("Referral edge must be an object")
        source_url = canonicalize_discovery_url(raw.get("sourceUrl"))
        destination_url = canonicalize_discovery_url(raw.get("destinationUrl"))
        if source_url == destination_url:
            raise ValueError("Referral graph rejects self-loop edges")
        source_authority = _text(raw.get("sourceAuthority"), "edges.sourceAuthority")
        if source_authority not in REFERRAL_SOURCE_AUTHORITIES:
            raise ValueError(
                "Referral edges require a direct, government, or reviewed authoritative source"
            )
        relationship = _text(raw.get("relationship"), "edges.relationship")
        if relationship not in REFERRAL_RELATIONSHIPS:
            raise ValueError(f"Unsupported referral relationship: {relationship}")
        organization = _text(raw.get("organization"), "edges.organization")
        program = _text(raw.get("program"), "edges.program")
        stage_key = _text(raw.get("stageKey"), "edges.stageKey")
        context = _text(raw.get("context"), "edges.context")
        if len(context) > 2000:
            raise ValueError("Referral edge context exceeds 2000 characters")
        edge_key = "edge:" + sha256_json(
            {
                "sourceUrl": source_url,
                "destinationUrl": destination_url,
                "organization": organization,
                "program": program,
            }
        )
        supplied_key = str(raw.get("edgeKey") or "").strip()
        if supplied_key and supplied_key != edge_key:
            raise ValueError(f"Referral edge key is not canonical: {supplied_key}")
        if edge_key in keys:
            raise ValueError(f"Duplicate referral edge: {edge_key}")
        keys.add(edge_key)
        source_counts[source_url] = source_counts.get(source_url, 0) + 1
        if source_counts[source_url] > MAX_REFERRAL_EDGES_PER_SOURCE:
            raise ValueError(
                f"Referral source exceeds {MAX_REFERRAL_EDGES_PER_SOURCE} edges"
            )
        edges.append(
            {
                "edgeKey": edge_key,
                "sourceUrl": source_url,
                "sourceTitle": _text(raw.get("sourceTitle"), "edges.sourceTitle"),
                "sourceAuthority": source_authority,
                "destinationUrl": destination_url,
                "organization": organization,
                "program": program,
                "stageKey": stage_key,
                "relationship": relationship,
                "context": context,
            }
        )
    normalized = {
        "schemaVersion": REFERRAL_GRAPH_SCHEMA_VERSION,
        "policyVersion": REFERRAL_GRAPH_POLICY_VERSION,
        "graphId": graph_id,
        "categoryId": category_id,
        "targetLocation": target_location,
        "createdAt": created_at,
        "sourceArtifactSha256": source_artifact_sha256,
        "edges": sorted(edges, key=lambda edge: edge["edgeKey"]),
    }
    normalized["graphSha256"] = sha256_json(normalized)
    supplied_hash = str(value.get("graphSha256") or "").strip()
    if supplied_hash and supplied_hash != normalized["graphSha256"]:
        raise ValueError("Referral graph SHA-256 does not match its content")
    return normalized


def attach_referral_graph_to_query_plan(
    plan: dict[str, Any], graph: dict[str, Any]
) -> dict[str, Any]:
    normalized = normalize_referral_graph(graph)
    result = deepcopy(plan)
    if result.get("categoryId") != normalized["categoryId"]:
        raise ValueError("Referral graph belongs to another category")
    if str(result.get("targetLocation") or "").casefold() != str(
        normalized["targetLocation"]
    ).casefold():
        raise ValueError("Referral graph belongs to another target location")
    if result.get("referralGraphSha256"):
        raise ValueError("Query plan already has a referral graph")
    result["schemaVersion"] = max(6, int(result.get("schemaVersion") or 0))
    result["referralGraphPolicyVersion"] = REFERRAL_GRAPH_POLICY_VERSION
    result["referralGraphSha256"] = normalized["graphSha256"]
    return result
