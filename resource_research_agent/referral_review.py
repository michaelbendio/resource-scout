from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable

from .optimization import (
    EVIDENCE_PREPARATION_POLICY_VERSION,
    candidate_identity_key,
    candidate_qualification,
    canonicalize_discovery_url,
    reviewed_source_metadata,
    sha256_json,
)
from .referral_graph import normalize_referral_graph


REFERRAL_REVIEW_SCHEMA_VERSION = 1
REFERRAL_REVIEW_POLICY_VERSION = "reviewed-referral-destinations-v1"
REFERRAL_REVIEW_DISPOSITIONS = {"candidate", "unresolved", "excluded"}


def _text(value: Any, field: str) -> str:
    text = " ".join(str(value or "").split())
    if not text:
        raise ValueError(f"Referral review field {field} must not be blank")
    return text


def _identity_values(record: dict[str, Any]) -> list[dict[str, Any]]:
    value = record.get("identities", record.get("identity"))
    if isinstance(value, dict):
        return [value]
    if isinstance(value, list) and value and all(isinstance(item, dict) for item in value):
        return value
    raise ValueError("Candidate referral review needs an identity or identities array")


def normalize_referral_review(
    graph_value: dict[str, Any],
    review_value: dict[str, Any],
    *,
    evidence_preparation_policy_version: str = "",
) -> dict[str, Any]:
    graph = normalize_referral_graph(graph_value)
    if not isinstance(review_value, dict) or review_value.get("schemaVersion") != 1:
        raise ValueError("Referral review schemaVersion must be 1")
    if review_value.get("graphSha256") != graph["graphSha256"]:
        raise ValueError("Referral review belongs to a different referral graph")
    requested_evidence_policy = str(
        evidence_preparation_policy_version
        or review_value.get("evidencePreparationPolicyVersion")
        or ""
    ).strip()
    if requested_evidence_policy and (
        requested_evidence_policy != EVIDENCE_PREPARATION_POLICY_VERSION
    ):
        raise ValueError("Referral review requests an unsupported evidence-preparation policy")
    if evidence_preparation_policy_version and (
        review_value.get("evidencePreparationPolicyVersion")
        != EVIDENCE_PREPARATION_POLICY_VERSION
    ):
        raise ValueError("Referral review lacks the current evidence-preparation policy")
    decisions_value = review_value.get("decisions")
    if not isinstance(decisions_value, dict):
        raise ValueError("Referral review needs a decisions object")
    edges = {edge["edgeKey"]: edge for edge in graph["edges"]}
    missing = sorted(set(edges) - set(decisions_value))
    extra = sorted(set(decisions_value) - set(edges))
    if missing or extra:
        details = []
        if missing:
            details.append(f"missing {len(missing)} edges")
        if extra:
            details.append(f"contains {len(extra)} unknown edges")
        raise ValueError("Referral review must exactly cover the graph: " + ", ".join(details))

    decisions: dict[str, dict[str, Any]] = {}
    for edge_key, raw in decisions_value.items():
        if not isinstance(raw, dict):
            raise ValueError(f"Referral review decision must be an object: {edge_key}")
        edge = edges[edge_key]
        disposition = _text(raw.get("disposition"), "decisions.disposition")
        if disposition not in REFERRAL_REVIEW_DISPOSITIONS:
            raise ValueError(f"Unsupported referral review disposition: {disposition}")
        record: dict[str, Any] = {
            "disposition": disposition,
            "reason": _text(raw.get("reason"), "decisions.reason"),
        }
        if disposition != "candidate":
            if raw.get("identity") is not None or raw.get("identities") is not None:
                raise ValueError("Noncandidate referral review cannot contain identities")
            decisions[edge_key] = record
            continue

        identities = []
        edge_identity_key = candidate_identity_key(edge["organization"], edge["program"])
        resolution_reason = " ".join(
            str(raw.get("identityResolutionReason") or "").split()
        )
        for identity_value in _identity_values(raw):
            identity = deepcopy(identity_value)
            organization = _text(identity.get("organization"), "identity.organization")
            program = _text(identity.get("program"), "identity.program")
            identity["organization"] = organization
            identity["program"] = program
            identity["boundaryState"] = _text(
                identity.get("boundaryState"), "identity.boundaryState"
            )
            identity["stageKey"] = _text(identity.get("stageKey"), "identity.stageKey")
            if identity["stageKey"] != edge["stageKey"]:
                raise ValueError("Referral review identity stage disagrees with its edge")
            qualification = candidate_qualification(
                identity,
                boundary_state=identity["boundaryState"],
                package_match_state="not-matched",
            )
            if requested_evidence_policy and qualification["state"] == "eligible":
                try:
                    reviewed_source_metadata(
                        identity,
                        require_current_contract=True,
                    )
                except ValueError as error:
                    raise ValueError(
                        f"Referral candidate evidence receipt is invalid: {edge_key}: {error}"
                    ) from error
            evidence_urls = identity.get("evidenceUrls")
            if not isinstance(evidence_urls, list) or not evidence_urls:
                raise ValueError("Candidate referral review identity needs evidenceUrls")
            identity["evidenceUrls"] = sorted(
                {canonicalize_discovery_url(url) for url in evidence_urls}
            )
            if edge["destinationUrl"] not in identity["evidenceUrls"]:
                raise ValueError(
                    "Referral review evidence must include the freshly fetched destination URL"
                )
            identity_key = candidate_identity_key(organization, program)
            if identity_key != edge_identity_key and not resolution_reason:
                raise ValueError(
                    "Changed referral identity needs identityResolutionReason"
                )
            identities.append(identity)
        identity_keys = {
            candidate_identity_key(item["organization"], item["program"])
            for item in identities
        }
        if len(identity_keys) != len(identities):
            raise ValueError("Referral review candidate identities must be unique")
        record["identities"] = identities
        if resolution_reason:
            record["identityResolutionReason"] = resolution_reason
        decisions[edge_key] = record

    normalized = {
        "schemaVersion": REFERRAL_REVIEW_SCHEMA_VERSION,
        "policyVersion": REFERRAL_REVIEW_POLICY_VERSION,
        "graphSha256": graph["graphSha256"],
        "decisions": dict(sorted(decisions.items())),
    }
    if requested_evidence_policy:
        normalized["evidencePreparationPolicyVersion"] = requested_evidence_policy
    normalized["reviewSha256"] = sha256_json(normalized)
    supplied_hash = str(review_value.get("reviewSha256") or "").strip()
    if supplied_hash and supplied_hash != normalized["reviewSha256"]:
        raise ValueError("Referral review SHA-256 does not match its content")
    return normalized


class ReviewedReferralResolver:
    def __init__(
        self,
        graph: dict[str, Any],
        review: dict[str, Any],
        fallback: Callable[[dict[str, Any]], Any],
    ) -> None:
        self.review = normalize_referral_review(graph, review)
        self.fallback = fallback

    def __call__(self, result: dict[str, Any]) -> Any:
        referral = result.get("referralEdge")
        if not isinstance(referral, dict) or not referral.get("edgeKey"):
            return self.fallback(result)
        record = self.review["decisions"].get(str(referral["edgeKey"]))
        if not isinstance(record, dict) or record["disposition"] != "candidate":
            return None
        identities = deepcopy(record["identities"])
        return identities[0] if len(identities) == 1 else identities
