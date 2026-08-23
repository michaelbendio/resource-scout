from __future__ import annotations

from copy import deepcopy
from typing import Any

from .optimization import (
    CANDIDATE_QUALIFICATION_POLICY_VERSION,
    candidate_identity_key,
    candidate_qualification,
    canonicalize_discovery_url,
    sha256_json,
)
from .optimization_runtime import OptimizationRuntimeError


IDENTITY_QUALIFICATION_MANIFEST_VERSION = 1
QUALIFICATION_FIELDS = (
    "candidateRole",
    "geographyState",
    "categoryState",
    "actionabilityState",
    "currentStatusState",
    "evidenceReadiness",
)


def _identity_values(record: dict[str, Any]) -> list[dict[str, Any]]:
    value = record.get("identities", record.get("identity"))
    if isinstance(value, dict):
        return [value]
    if isinstance(value, list) and all(isinstance(item, dict) for item in value):
        return value
    return []


def identity_qualification_template(review: dict[str, Any]) -> dict[str, Any]:
    """Build an explicitly incomplete, identity-deduplicated audit template."""

    identities: dict[str, dict[str, Any]] = {}
    for url, record in review.get("decisions", {}).items():
        if not isinstance(record, dict) or record.get("disposition") != "candidate":
            continue
        for identity in _identity_values(record):
            organization = str(identity.get("organization") or "").strip()
            program = str(identity.get("program") or "").strip()
            try:
                identity_key = candidate_identity_key(organization, program)
                evidence_url = canonicalize_discovery_url(url)
            except ValueError as error:
                raise OptimizationRuntimeError(
                    f"Candidate identity is incomplete: {url}"
                ) from error
            entry = identities.setdefault(
                identity_key,
                {
                    "organization": organization,
                    "program": program,
                    "boundaryState": str(
                        identity.get("boundaryState") or "resolved"
                    ),
                    **{field: "" for field in QUALIFICATION_FIELDS},
                    "reviewReason": "",
                    "evidenceUrls": [],
                },
            )
            if (
                entry["organization"] != organization
                or entry["program"] != program
            ):
                raise OptimizationRuntimeError(
                    f"Normalized identity collision requires review: {identity_key}"
                )
            if evidence_url not in entry["evidenceUrls"]:
                entry["evidenceUrls"].append(evidence_url)
    return {
        "schemaVersion": IDENTITY_QUALIFICATION_MANIFEST_VERSION,
        "candidateQualificationPolicyVersion": (
            CANDIDATE_QUALIFICATION_POLICY_VERSION
        ),
        "searchCacheSha256": review.get("searchCacheSha256"),
        "identities": dict(sorted(identities.items())),
    }


def apply_identity_qualification_manifest(
    review: dict[str, Any], manifest: dict[str, Any]
) -> dict[str, Any]:
    """Apply one audited qualification consistently to every occurrence of an identity."""

    if manifest.get("schemaVersion") != IDENTITY_QUALIFICATION_MANIFEST_VERSION:
        raise OptimizationRuntimeError("Unsupported identity qualification manifest")
    if (
        manifest.get("candidateQualificationPolicyVersion")
        != CANDIDATE_QUALIFICATION_POLICY_VERSION
    ):
        raise OptimizationRuntimeError(
            "Identity qualification manifest uses a different policy"
        )
    review_hash = str(review.get("searchCacheSha256") or "")
    if manifest.get("searchCacheSha256") != review_hash:
        raise OptimizationRuntimeError(
            "Identity qualification manifest belongs to a different review"
        )
    entries = manifest.get("identities")
    if not isinstance(entries, dict) or not entries:
        raise OptimizationRuntimeError(
            "Identity qualification manifest has no identity decisions"
        )

    occurrences: dict[str, list[tuple[str, int, dict[str, Any]]]] = {}
    for url, record in review.get("decisions", {}).items():
        if not isinstance(record, dict) or record.get("disposition") != "candidate":
            continue
        identities = _identity_values(record)
        if not identities:
            raise OptimizationRuntimeError(f"Candidate URL lacks an identity: {url}")
        for position, identity in enumerate(identities):
            try:
                identity_key = candidate_identity_key(
                    str(identity.get("organization") or ""),
                    str(identity.get("program") or ""),
                )
            except ValueError as error:
                raise OptimizationRuntimeError(
                    f"Candidate identity is incomplete: {url}"
                ) from error
            occurrences.setdefault(identity_key, []).append((url, position, identity))

    expected = set(occurrences)
    provided = set(entries)
    missing = sorted(expected - provided)
    extra = sorted(provided - expected)
    if missing or extra:
        details = []
        if missing:
            details.append(f"missing {len(missing)} identities")
        if extra:
            details.append(f"contains {len(extra)} undiscovered identities")
        raise OptimizationRuntimeError(
            "Identity qualification manifest does not exactly match the review: "
            + "; ".join(details)
        )

    result = deepcopy(review)
    for identity_key, source_occurrences in occurrences.items():
        entry = entries[identity_key]
        if not isinstance(entry, dict):
            raise OptimizationRuntimeError(
                f"Identity qualification decision is invalid: {identity_key}"
            )
        organization = str(entry.get("organization") or "").strip()
        program = str(entry.get("program") or "").strip()
        try:
            entry_key = candidate_identity_key(organization, program)
        except ValueError as error:
            raise OptimizationRuntimeError(
                f"Identity qualification decision is incomplete: {identity_key}"
            ) from error
        if entry_key != identity_key:
            raise OptimizationRuntimeError(
                f"Identity qualification key does not match its identity: {identity_key}"
            )
        review_reason = str(entry.get("reviewReason") or "").strip()
        evidence_urls = entry.get("evidenceUrls")
        if not review_reason or not isinstance(evidence_urls, list) or not evidence_urls:
            raise OptimizationRuntimeError(
                f"Identity qualification lacks reason or evidence: {identity_key}"
            )
        try:
            normalized_evidence = sorted(
                {canonicalize_discovery_url(url) for url in evidence_urls}
            )
        except ValueError as error:
            raise OptimizationRuntimeError(
                f"Identity qualification has invalid evidence: {identity_key}"
            ) from error
        qualification_values = {field: entry.get(field) for field in QUALIFICATION_FIELDS}
        boundary_state = str(entry.get("boundaryState") or "resolved").strip()
        candidate_qualification(
            qualification_values,
            boundary_state=boundary_state,
            package_match_state="not-matched",
        )

        for url, position, _identity in source_occurrences:
            record = result["decisions"][url]
            values = _identity_values(record)
            target = values[position]
            if (
                str(target.get("organization") or "").strip() != organization
                or str(target.get("program") or "").strip() != program
            ):
                raise OptimizationRuntimeError(
                    f"Identity qualification would alter reviewed identity: {identity_key}"
                )
            target.update(qualification_values)
            target["boundaryState"] = boundary_state
            target["decisionReason"] = review_reason
            target["qualificationEvidenceUrls"] = normalized_evidence

    digest = sha256_json(manifest)
    applications = result.setdefault("qualificationApplications", [])
    if not any(
        isinstance(application, dict)
        and application.get("manifestSha256") == digest
        for application in applications
    ):
        applications.append(
            {
                "policyVersion": CANDIDATE_QUALIFICATION_POLICY_VERSION,
                "manifestSha256": digest,
                "identityCount": len(entries),
            }
        )
    result["candidateQualificationPolicyVersion"] = (
        CANDIDATE_QUALIFICATION_POLICY_VERSION
    )
    return result
