from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Iterable

from .optimization import (
    canonical_json,
    configuration_snapshot,
    EVIDENCE_PREPARATION_POLICY_VERSION,
    IDENTITY_SUPPORT_RELATIONSHIPS,
    sha256_json,
    validate_candidate_dossier,
)
from .playbooks import playbook_for
from .storage import ResearchStore


ModelCallback = Callable[[dict[str, Any]], "ModelInvocation | dict[str, Any]"]
ProgressCallback = Callable[[dict[str, Any]], None]

VERIFICATION_FIELD_ACTIONS = {
    "keep",
    "downgrade-to-unknown",
    "mark-conflicting",
    "flag-review",
}
VERIFICATION_MATERIAL_DEFECTS = {
    "identity-conflation",
    "wrong-category",
    "wrong-geography",
    "altered-or-invented-source",
    "unsupported-safety-critical-claim",
    "candidate-not-credible",
}
VERIFICATION_DERIVATION_POLICY_VERSION = "verifier-candidate-salvage-v2"
VERIFIER_RESOLVED_ACTIONS = {"removed", "downgraded", "separated", "resolved"}
SEMANTICALLY_RESOLVABLE_ISSUES = {
    "contradicted-field",
    "cross-organization-evidence",
    "cross-program-evidence",
    "lead-only-field",
    "source-does-not-support-field",
    "unresolved-conflict",
}
CANDIDATE_FATAL_DEFECTS = {
    "identity-conflation",
    "wrong-category",
    "wrong-geography",
    "candidate-not-credible",
}


class OptimizationModelError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        raw_output: str = "",
        usage: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.raw_output = raw_output
        self.usage = usage


@dataclass(frozen=True)
class ModelInvocation:
    result: dict[str, Any]
    raw_output: str = ""
    usage: dict[str, Any] | None = None


@dataclass(frozen=True)
class ModelEvaluationResult:
    run_id: int
    configuration_id: int
    corpus_id: int
    packet_count: int
    passed_count: int
    needs_review_count: int
    failed_count: int
    supported_field_count: int
    conflicting_field_count: int
    unknown_field_count: int
    gap_count: int
    quality_gate_passed: bool


@dataclass(frozen=True)
class VerificationRecomputeResult:
    run_id: int
    policy_version: str
    revision_id: int
    source_snapshot_sha256: str
    derived_snapshot_sha256: str
    before: dict[str, Any]
    after: dict[str, Any]
    model_inference_calls: int = 0


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _invocation(value: ModelInvocation | dict[str, Any]) -> ModelInvocation:
    if isinstance(value, ModelInvocation):
        if not isinstance(value.result, dict):
            raise OptimizationModelError("Model invocation result must be an object")
        return value
    if not isinstance(value, dict):
        raise OptimizationModelError("Model callback must return an object")
    return ModelInvocation(result=value, raw_output=canonical_json(value), usage=None)


def verified_dossier_to_candidate(
    dossier: dict[str, Any],
    *,
    verification_status: str = "passed",
    verification_findings: dict[str, Any] | None = None,
) -> dict[str, Any]:
    identity = dossier["candidateIdentity"]
    candidate: dict[str, Any] = {
        "name": str(identity.get("program") or identity.get("organization") or "Unnamed candidate"),
        "organization": str(identity.get("organization") or ""),
        "program": str(identity.get("program") or ""),
        "unknowns": [],
        "conflicts": [],
        "evidence": [],
        "verificationStatus": verification_status,
        "verificationFindings": verification_findings or {},
    }
    for field, finding in dossier.get("fields", {}).items():
        if not isinstance(finding, dict):
            continue
        if finding.get("status") == "supported":
            candidate[field] = finding.get("value")
        elif finding.get("status") == "conflicting":
            candidate["conflicts"].append(
                {"field": field, "alternatives": finding.get("alternatives", [])}
            )
        elif finding.get("status") == "unknown":
            candidate["unknowns"].append(
                f"{field}: {str(finding.get('reason') or 'Not found')}"
            )
    for source in dossier.get("sources", []):
        if not isinstance(source, dict):
            continue
        candidate["evidence"].append(
            {
                "url": source.get("url"),
                "title": source.get("title", ""),
                "sourceType": {
                    "direct-provider": "official",
                    "government-referral": "government",
                    "reputable-secondary": "news",
                    "directory-lead": "other",
                }.get(source.get("authority"), "other"),
                "finding": source.get("extract", ""),
                "reliability": (
                    "lead-only" if source.get("authority") == "directory-lead" else "high"
                ),
            }
        )
    return candidate


def _summarize_verification_rows(rows: Iterable[Any]) -> dict[str, Any]:
    state_counts = {"supported": 0, "conflicting": 0, "unknown": 0}
    coverage_tags: set[str] = set()
    status_counts = {"passed": 0, "needs-review": 0, "failed": 0}
    row_count = 0
    for row in rows:
        row_count += 1
        dossier = json.loads(row["verified_dossier_json"])
        packet = json.loads(row["packet_json"])
        coverage_tags.update(packet["candidateIdentity"].get("coverageTags", []))
        status = str(row["status"])
        status_counts[status if status in status_counts else "failed"] += 1
        for finding in dossier.get("fields", {}).values():
            if isinstance(finding, dict) and finding.get("status") in state_counts:
                state_counts[finding["status"]] += 1
    return {
        "packetCount": row_count,
        "statusCounts": status_counts,
        "fieldStates": state_counts,
        "coverageTags": sorted(coverage_tags),
    }


def _persist_model_evaluation_audits(
    store: ResearchStore,
    run_id: int,
    summary: dict[str, Any],
    gaps: list[dict[str, str]],
) -> None:
    reports = _model_evaluation_audit_reports(summary, gaps)
    with store.connect() as connection:
        _write_model_evaluation_audits(connection, run_id, reports)


def _model_evaluation_audit_reports(
    summary: dict[str, Any], gaps: list[dict[str, str]]
) -> dict[str, dict[str, Any]]:
    counts = summary["statusCounts"]
    return {
        "candidate-completeness": {
            "packetCount": summary["packetCount"],
            "passedCount": counts["passed"],
            "needsReviewCount": counts["needs-review"],
            "failedCount": counts["failed"],
            "fieldStates": summary["fieldStates"],
        },
        "quality-gate": {
            "passed": counts["failed"] == 0,
            "verificationFailures": counts["failed"],
            "verificationNeedsReview": counts["needs-review"],
            "coverageTags": summary["coverageTags"],
            "coverageGaps": gaps,
        },
    }


def _write_model_evaluation_audits(
    connection: Any,
    run_id: int,
    reports: dict[str, dict[str, Any]],
) -> None:
    for audit_type, report in reports.items():
        connection.execute(
            """INSERT OR REPLACE INTO optimization_audits (
                   run_id, audit_type, created_at, report_json, report_sha256
               ) VALUES (?, ?, ?, ?, ?)""",
            (run_id, audit_type, _now(), canonical_json(report), sha256_json(report)),
        )


def recompute_model_evaluation_audits(store: ResearchStore, run_id: int) -> None:
    with store.connect() as connection:
        rows = connection.execute(
            """SELECT verification.status, verification.verified_dossier_json,
                      packet.packet_json
               FROM optimization_verifications AS verification
               JOIN optimization_candidate_dossiers AS dossier
                 ON dossier.id = verification.dossier_id
               JOIN optimization_evidence_packets AS packet
                 ON packet.id = dossier.packet_id
               WHERE dossier.run_id = ? ORDER BY dossier.packet_id""",
            (run_id,),
        ).fetchall()
        gap_rows = connection.execute(
            """SELECT need_key, need_label, query_text, reason
               FROM optimization_gap_queries WHERE run_id = ? ORDER BY need_key""",
            (run_id,),
        ).fetchall()
    if not rows:
        raise OptimizationModelError(f"Optimization run {run_id} has no verifications")
    gaps = [
        {
            "key": str(row["need_key"]),
            "label": str(row["need_label"]),
            "query": str(row["query_text"]),
            "reason": str(row["reason"]),
        }
        for row in gap_rows
    ]
    _persist_model_evaluation_audits(
        store, run_id, _summarize_verification_rows(rows), gaps
    )


def _persisted_verification_rows(store: ResearchStore, run_id: int) -> list[Any]:
    with store.connect() as connection:
        return connection.execute(
            """SELECT verification.id AS verification_id,
                      verification.dossier_id,
                      verification.verification_attempt_id,
                      verification.status,
                      verification.verified_dossier_json,
                      verification.verified_dossier_sha256,
                      verification.findings_json,
                      dossier.packet_id, dossier.dossier_json,
                      dossier.dossier_sha256,
                      packet.packet_json, packet.packet_sha256,
                      attempt.status AS attempt_status,
                      attempt.prompt_sha256, attempt.raw_output,
                      attempt.parsed_json
               FROM optimization_verifications AS verification
               JOIN optimization_candidate_dossiers AS dossier
                 ON dossier.id = verification.dossier_id
               JOIN optimization_evidence_packets AS packet
                 ON packet.id = dossier.packet_id
               JOIN optimization_model_attempts AS attempt
                 ON attempt.id = verification.verification_attempt_id
               WHERE dossier.run_id = ? ORDER BY dossier.packet_id""",
            (run_id,),
        ).fetchall()


def _gap_reports(store: ResearchStore, run_id: int) -> list[dict[str, str]]:
    with store.connect() as connection:
        rows = connection.execute(
            """SELECT need_key, need_label, query_text, reason
               FROM optimization_gap_queries WHERE run_id = ? ORDER BY need_key""",
            (run_id,),
        ).fetchall()
    return [
        {
            "key": str(row["need_key"]),
            "label": str(row["need_label"]),
            "query": str(row["query_text"]),
            "reason": str(row["reason"]),
        }
        for row in rows
    ]


def _verification_snapshot(
    rows: Iterable[Any], reports: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    row_list = list(rows)
    raw_evidence = [
        {
            "packetId": int(row["packet_id"]),
            "packetSha256": str(row["packet_sha256"]),
            "dossierSha256": str(row["dossier_sha256"]),
            "verificationAttemptId": int(row["verification_attempt_id"]),
            "verificationPromptSha256": str(row["prompt_sha256"]),
            "verificationRawOutput": str(row["raw_output"] or ""),
            "verificationParsedJson": str(row["parsed_json"] or ""),
        }
        for row in row_list
    ]
    return {
        "rawEvidenceSha256": sha256_json(raw_evidence),
        "summary": _summarize_verification_rows(row_list),
        "verifications": [
            {
                "verificationId": int(row["verification_id"]),
                "dossierId": int(row["dossier_id"]),
                "verificationAttemptId": int(row["verification_attempt_id"]),
                "status": str(row["status"]),
                "verifiedDossierJson": str(row["verified_dossier_json"]),
                "verifiedDossierSha256": str(row["verified_dossier_sha256"]),
                "findingsJson": str(row["findings_json"]),
            }
            for row in row_list
        ],
        "audits": reports,
    }


def _stored_audit_reports(store: ResearchStore, run_id: int) -> dict[str, dict[str, Any]]:
    with store.connect() as connection:
        rows = connection.execute(
            """SELECT audit_type, report_json FROM optimization_audits
               WHERE run_id = ? AND audit_type IN ('candidate-completeness', 'quality-gate')
               ORDER BY audit_type""",
            (run_id,),
        ).fetchall()
    return {str(row["audit_type"]): json.loads(row["report_json"]) for row in rows}


def recompute_persisted_verifications(
    store: ResearchStore,
    run_id: int,
    *,
    policy_version: str = VERIFICATION_DERIVATION_POLICY_VERSION,
) -> VerificationRecomputeResult:
    if policy_version != VERIFICATION_DERIVATION_POLICY_VERSION:
        raise OptimizationModelError(
            f"Unsupported verification derivation policy {policy_version!r}"
        )
    with store.connect() as connection:
        run = connection.execute(
            """SELECT run.status, configuration.snapshot_json
               FROM optimization_runs AS run
               JOIN optimization_configurations AS configuration
                 ON configuration.id = run.configuration_id
               WHERE run.id = ?""",
            (run_id,),
        ).fetchone()
        existing_revision = connection.execute(
            """SELECT id, source_snapshot_json, source_snapshot_sha256,
                      derived_snapshot_json, derived_snapshot_sha256
               FROM optimization_verification_revisions
               WHERE run_id = ? AND policy_version = ?""",
            (run_id, policy_version),
        ).fetchone()
    if run is None or str(run["status"]) != "completed":
        raise OptimizationModelError(
            f"Optimization run {run_id} must be completed before verification recomputation"
        )
    rows = _persisted_verification_rows(store, run_id)
    if not rows or any(str(row["attempt_status"]) != "completed" for row in rows):
        raise OptimizationModelError(
            f"Optimization run {run_id} has incomplete persisted verification attempts"
        )
    current_snapshot = _verification_snapshot(
        rows, _stored_audit_reports(store, run_id)
    )
    current_sha256 = sha256_json(current_snapshot)
    if existing_revision is not None:
        if current_sha256 != str(existing_revision["derived_snapshot_sha256"]):
            raise OptimizationModelError(
                "Persisted verification state drifted after this immutable policy revision"
            )
        source_snapshot = json.loads(existing_revision["source_snapshot_json"])
        derived_snapshot = json.loads(existing_revision["derived_snapshot_json"])
        return VerificationRecomputeResult(
            run_id=run_id,
            policy_version=policy_version,
            revision_id=int(existing_revision["id"]),
            source_snapshot_sha256=str(existing_revision["source_snapshot_sha256"]),
            derived_snapshot_sha256=str(existing_revision["derived_snapshot_sha256"]),
            before=source_snapshot["summary"],
            after=derived_snapshot["summary"],
        )

    snapshot = json.loads(run["snapshot_json"])
    playbook = playbook_for(str(snapshot["targetCategoryId"]))
    derived_rows: list[dict[str, Any]] = []
    for row in rows:
        response = json.loads(row["parsed_json"])
        status, verified, findings = derive_verification_from_response(
            json.loads(row["dossier_json"]),
            json.loads(row["packet_json"]),
            response,
            playbook.factual_fields,
            playbook.supplementary_fields,
        )
        derived_rows.append(
            {
                **dict(row),
                "status": status,
                "verified_dossier_json": canonical_json(verified),
                "verified_dossier_sha256": sha256_json(verified),
                "findings_json": canonical_json(findings),
            }
        )
    gaps = _gap_reports(store, run_id)
    summary = _summarize_verification_rows(derived_rows)
    reports = _model_evaluation_audit_reports(summary, gaps)
    derived_snapshot = _verification_snapshot(derived_rows, reports)
    derived_sha256 = sha256_json(derived_snapshot)

    with store.connect() as connection:
        current_hashes = connection.execute(
            """SELECT verification.id, verification.verified_dossier_sha256
               FROM optimization_verifications AS verification
               JOIN optimization_candidate_dossiers AS dossier
                 ON dossier.id = verification.dossier_id
               WHERE dossier.run_id = ? ORDER BY dossier.packet_id""",
            (run_id,),
        ).fetchall()
        expected_hashes = [
            (int(row["verification_id"]), str(row["verified_dossier_sha256"]))
            for row in rows
        ]
        if [
            (int(row["id"]), str(row["verified_dossier_sha256"]))
            for row in current_hashes
        ] != expected_hashes:
            raise OptimizationModelError(
                "Persisted verification state changed during recomputation"
            )
        revision_id = int(
            connection.execute(
                """INSERT INTO optimization_verification_revisions (
                       run_id, created_at, policy_version,
                       source_snapshot_json, source_snapshot_sha256,
                       derived_snapshot_json, derived_snapshot_sha256
                   ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    run_id,
                    _now(),
                    policy_version,
                    canonical_json(current_snapshot),
                    current_sha256,
                    canonical_json(derived_snapshot),
                    derived_sha256,
                ),
            ).lastrowid
        )
        for row in derived_rows:
            connection.execute(
                """UPDATE optimization_verifications
                   SET status = ?, verified_dossier_json = ?,
                       verified_dossier_sha256 = ?, findings_json = ?
                   WHERE id = ?""",
                (
                    row["status"],
                    row["verified_dossier_json"],
                    row["verified_dossier_sha256"],
                    row["findings_json"],
                    row["verification_id"],
                ),
            )
        _write_model_evaluation_audits(connection, run_id, reports)
    return VerificationRecomputeResult(
        run_id=run_id,
        policy_version=policy_version,
        revision_id=revision_id,
        source_snapshot_sha256=current_sha256,
        derived_snapshot_sha256=derived_sha256,
        before=current_snapshot["summary"],
        after=derived_snapshot["summary"],
    )


def validate_dossier_for_packet(
    dossier: dict[str, Any],
    packet: dict[str, Any],
    required_fields: Iterable[str],
) -> list[dict[str, str]]:
    dossier = restore_reviewed_identity_bindings(dossier, packet)
    issues = validate_candidate_dossier(dossier, required_fields=required_fields)
    dossier_identity = dossier.get("candidateIdentity", {})
    packet_identity = packet.get("candidateIdentity", {})
    if dossier_identity.get("identityKey") != packet_identity.get("identityKey"):
        issues.append(
            {
                "code": "packet-identity-mismatch",
                "message": "Dossier identity differs from the frozen evidence packet identity",
            }
        )
    packet_sources = {
        str(source.get("id")): source
        for source in packet.get("sources", [])
        if isinstance(source, dict) and source.get("id") is not None
    }
    for source in dossier.get("sources", []):
        if not isinstance(source, dict):
            continue
        source_id = str(source.get("id") or "")
        packet_source = packet_sources.get(source_id)
        if packet_source is None:
            issues.append(
                {
                    "code": "invented-source",
                    "message": f"Dossier source {source_id or '(blank)'} is not in the frozen packet",
                }
            )
            continue
        expected = {
            "url": packet_source.get("canonical_url"),
            "extract": packet_source.get("extract", {}).get("text"),
            "authority": packet_source.get("authority"),
            "pageIdentityKey": packet_source.get("page_identity_key"),
        }
        for field, expected_value in expected.items():
            if source.get(field) != expected_value:
                issues.append(
                    {
                        "code": "altered-source",
                        "field": field,
                        "message": f"Dossier changed frozen source {source_id} field {field}",
                    }
                )
    return issues


def restore_frozen_source_envelopes(
    dossier: dict[str, Any], packet: dict[str, Any]
) -> dict[str, Any]:
    restored = json.loads(canonical_json(dossier))
    packet_sources = {
        str(source.get("id")): source
        for source in packet.get("sources", [])
        if isinstance(source, dict) and source.get("id") is not None
    }
    sources = []
    for source in restored.get("sources", []):
        if not isinstance(source, dict):
            sources.append(source)
            continue
        frozen = packet_sources.get(str(source.get("id") or ""))
        if frozen is None:
            sources.append(source)
            continue
        page_identity_key = str(frozen.get("page_identity_key") or "")
        sources.append(
            {
                **source,
                "url": frozen.get("canonical_url"),
                "title": frozen.get("extract", {}).get("title", ""),
                "extract": frozen.get("extract", {}).get("text"),
                "authority": frozen.get("authority"),
                "pageIdentityKey": page_identity_key,
                "pageOrganizationKey": page_identity_key.split("::", 1)[0],
            }
        )
    restored["sources"] = sources
    return restored


def restore_reviewed_identity_bindings(
    dossier: dict[str, Any], packet: dict[str, Any]
) -> dict[str, Any]:
    """Bind reviewed identity receipts without extending them to ordinary facts."""

    restored = json.loads(canonical_json(dossier))
    identity = packet.get("candidateIdentity")
    fields = restored.get("fields")
    if not isinstance(identity, dict) or not isinstance(fields, dict):
        return restored
    identity_key = str(identity.get("identityKey") or "")
    packet_sources = {
        str(source.get("id")): source
        for source in packet.get("sources", [])
        if isinstance(source, dict) and source.get("id") is not None
    }
    dossier_sources = {
        str(source.get("id")): source
        for source in restored.get("sources", [])
        if isinstance(source, dict) and source.get("id") is not None
    }
    for field, scope in (("organization", "organization"), ("program", "program")):
        finding = fields.get(field)
        expected_value = str(identity.get(field) or "").strip()
        if (
            not isinstance(finding, dict)
            or finding.get("status") != "supported"
            or " ".join(str(finding.get("value") or "").split()).casefold()
            != " ".join(expected_value.split()).casefold()
        ):
            continue
        evidence_ids = finding.get("evidenceIds")
        if not isinstance(evidence_ids, list):
            continue
        for raw_source_id in evidence_ids:
            source_id = str(raw_source_id)
            packet_source = packet_sources.get(source_id)
            dossier_source = dossier_sources.get(source_id)
            if packet_source is None or dossier_source is None:
                continue
            extract = packet_source.get("extract")
            if not isinstance(extract, dict):
                continue
            selection = extract.get("selection")
            support = extract.get("identitySupport")
            receipt = support.get(field) if isinstance(support, dict) else None
            if (
                packet_source.get("page_identity_key") != identity_key
                or not isinstance(selection, dict)
                or selection.get("policyVersion")
                != EVIDENCE_PREPARATION_POLICY_VERSION
                or not isinstance(receipt, dict)
                or receipt.get("relationship") not in IDENTITY_SUPPORT_RELATIONSHIPS
            ):
                continue
            source_label = str(receipt.get("sourceLabel") or "").strip()
            excerpt = str(receipt.get("evidenceExcerpt") or "").strip()
            source_text = str(extract.get("text") or "")
            if not source_label or not excerpt or excerpt not in source_text:
                continue
            if source_label.casefold() not in excerpt.casefold():
                continue
            relationship = str(receipt.get("relationship") or "")
            if relationship == "exact-label" and (
                source_label.casefold() != expected_value.casefold()
            ):
                continue
            if relationship == "reviewed-alias" and not str(
                receipt.get("reason") or ""
            ).strip():
                continue
            binding = {"field": field, "value": expected_value, "scope": scope}
            supports = dossier_source.setdefault("supports", [])
            if not isinstance(supports, list):
                continue
            if not any(
                isinstance(existing, dict)
                and existing.get("field") == field
                and canonical_json(existing.get("value"))
                == canonical_json(expected_value)
                for existing in supports
            ):
                supports.append(binding)
    return restored


def compact_source_bindings(dossier: dict[str, Any]) -> dict[str, Any]:
    """Remove immutable source-envelope copies while preserving model-owned bindings."""
    compacted = json.loads(canonical_json(dossier))
    compacted["sources"] = [
        {
            key: source[key]
            for key in ("id", "supports", "contradicts")
            if key in source
        }
        if isinstance(source, dict)
        else source
        for source in compacted.get("sources", [])
    ]
    return compacted


def restore_frozen_candidate_identity(
    dossier: dict[str, Any], packet: dict[str, Any]
) -> dict[str, Any]:
    """Restore the immutable corpus identity without dropping model review metadata."""
    restored = json.loads(canonical_json(dossier))
    frozen = packet.get("candidateIdentity")
    if not isinstance(frozen, dict):
        return restored
    model_identity = restored.get("candidateIdentity")
    identity = dict(model_identity) if isinstance(model_identity, dict) else {}
    identity_key = str(frozen.get("identityKey") or "")
    identity.update(
        {
            "organization": frozen.get("organization"),
            "program": frozen.get("program"),
            "identityKey": identity_key,
            "componentIdentityKeys": [identity_key],
        }
    )
    restored["candidateIdentity"] = identity
    return restored


def remediate_invalid_factual_fields(
    dossier: dict[str, Any],
    issues: Iterable[dict[str, str]],
    required_fields: Iterable[str],
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    """Remove residual factual claims that Scout's validator cannot substantiate.

    This is deliberately narrower than repairing an arbitrary invalid dossier. It may
    only replace a schema-required factual-field finding with an explicit unknown. Identity,
    source-envelope, and other structural defects remain failures for human diagnosis.
    """

    remediated = json.loads(canonical_json(dossier))
    fields = remediated.setdefault("fields", {})
    if not isinstance(fields, dict):
        return remediated, []
    required = tuple(required_fields)
    required_set = set(required)
    codes_by_field: dict[str, set[str]] = {}
    for issue in issues:
        field = str(issue.get("field") or "")
        code = str(issue.get("code") or "")
        if field not in required_set or not code:
            continue
        codes_by_field.setdefault(field, set()).add(code)
    findings = []
    for field in required:
        codes = sorted(codes_by_field.get(field, ()))
        if not codes:
            continue
        fields[field] = {
            "status": "unknown",
            "reason": (
                "Scout removed a residual claim that did not pass deterministic "
                f"evidence validation ({', '.join(codes)})."
            ),
        }
        findings.append(
            {
                "code": "deterministic-field-downgrade",
                "field": field,
                "action": "downgraded",
                "reason": (
                    "The verifier left a factual-field claim with deterministic "
                    f"validation findings: {', '.join(codes)}"
                ),
            }
        )
    return remediated, findings


def _rewrite_conflict_bindings(
    dossier: dict[str, Any], field: str, alternatives: Any
) -> str:
    if not isinstance(alternatives, list) or len(alternatives) < 2:
        return "A conflicting decision requires at least two source-bound alternatives."
    source_by_id = {
        str(source.get("id")): source
        for source in dossier.get("sources", [])
        if isinstance(source, dict) and source.get("id") is not None
    }
    values: set[str] = set()
    replacements: list[tuple[dict[str, Any], Any]] = []
    for alternative in alternatives:
        if not isinstance(alternative, dict) or "value" not in alternative:
            return "Every conflicting alternative requires a value and evidence ids."
        evidence_ids = alternative.get("evidenceIds")
        if not isinstance(evidence_ids, list) or not evidence_ids:
            return "Every conflicting alternative requires a value and evidence ids."
        values.add(canonical_json(alternative["value"]))
        for evidence_id in evidence_ids:
            source = source_by_id.get(str(evidence_id))
            if source is None:
                return f"Conflicting alternative cites unknown source {evidence_id}."
            replacements.append((source, alternative["value"]))
    if len(values) < 2:
        return "Conflicting alternatives must contain different values."
    for source in source_by_id.values():
        source["supports"] = [
            binding
            for binding in source.get("supports", [])
            if not isinstance(binding, dict) or binding.get("field") != field
        ]
        source["contradicts"] = [
            binding
            for binding in source.get("contradicts", [])
            if not isinstance(binding, dict) or binding.get("field") != field
        ]
    for source, value in replacements:
        source.setdefault("supports", []).append(
            {"field": field, "value": json.loads(canonical_json(value)), "scope": "program"}
        )
    return ""


def _quarantine_field(
    fields: dict[str, Any], field: str, code: str, reason: str
) -> tuple[str, str]:
    finding = fields.get(field)
    if isinstance(finding, dict) and finding.get("status") == "unknown":
        return "quarantined", reason
    if isinstance(finding, dict) and finding.get("status") == "conflicting":
        return (
            "preserved-conflict",
            "Scout retained the source-bound conflict and requires human review: " + reason,
        )
    fields[field] = {
        "status": "unknown",
        "reason": f"Scout quarantined this field after verifier defect {code}: {reason}",
    }
    return "quarantined", reason


def apply_verification_decisions(
    dossier: dict[str, Any],
    response: dict[str, Any],
    required_fields: Iterable[str],
    non_blocking_fields: Iterable[str] = (),
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    """Apply a verifier's constrained decisions without accepting dossier rewrites.

    Missing or invalid field decisions preserve the validated extraction field and
    create a review finding. Material defects are reported separately and never
    mutate the dossier.
    """

    verified = json.loads(canonical_json(dossier))
    fields = verified.setdefault("fields", {})
    if not isinstance(fields, dict):
        fields = {}
        verified["fields"] = fields
    required = tuple(required_fields)
    required_set = set(required)
    non_blocking_set = set(non_blocking_fields)
    decisions = response.get("fieldDecisions")
    if not isinstance(decisions, dict):
        decisions = {}
    decision_findings: list[dict[str, Any]] = []
    forbidden_rewrites = sorted(
        {"verifiedDossier", "candidateIdentity", "fields", "sources"} & set(response)
    )
    if forbidden_rewrites:
        decision_findings.append(
            {
                "code": "forbidden-verifier-rewrite",
                "action": "ignored",
                "reason": (
                    "Verifier attempted to replace Scout-owned data: "
                    + ", ".join(forbidden_rewrites)
                ),
            }
        )

    for field in required:
        decision = decisions.get(field)
        if not isinstance(decision, dict):
            decision_findings.append(
                {
                    "code": "verification-incomplete",
                    "field": field,
                    "action": "preserved",
                    "reason": "Verifier returned no decision for this required field.",
                }
            )
            continue
        action = str(decision.get("action") or "")
        reason = str(decision.get("reason") or "").strip()
        if action not in VERIFICATION_FIELD_ACTIONS:
            decision_findings.append(
                {
                    "code": "invalid-verifier-decision",
                    "field": field,
                    "action": "preserved",
                    "reason": f"Unsupported verifier action {action or '(blank)'!r}.",
                }
            )
            continue
        if action == "keep":
            continue
        if not reason:
            decision_findings.append(
                {
                    "code": "invalid-verifier-decision",
                    "field": field,
                    "action": "preserved",
                    "reason": f"Verifier action {action!r} requires an evidence-based reason.",
                }
            )
            continue
        if action == "downgrade-to-unknown":
            fields[field] = {"status": "unknown", "reason": reason}
            decision_findings.append(
                {
                    "code": "verifier-field-downgrade",
                    "field": field,
                    "action": "downgraded",
                    "reason": reason,
                }
            )
        elif action == "mark-conflicting":
            alternatives = decision.get("alternatives")
            binding_error = _rewrite_conflict_bindings(verified, field, alternatives)
            if binding_error:
                decision_findings.append(
                    {
                        "code": "invalid-verifier-decision",
                        "field": field,
                        "action": "preserved",
                        "reason": binding_error,
                    }
                )
                continue
            fields[field] = {
                "status": "conflicting",
                "alternatives": json.loads(canonical_json(alternatives)),
            }
            decision_findings.append(
                {
                    "code": "verifier-field-conflict",
                    "field": field,
                    "action": "marked-conflicting",
                    "reason": reason,
                }
            )
        else:
            decision_findings.append(
                {
                    "code": "verifier-review-flag",
                    "field": field,
                    "action": "flagged",
                    "reason": reason,
                }
            )

    for field in sorted(set(decisions) - required_set):
        decision_findings.append(
            {
                "code": "invalid-verifier-decision-field",
                "field": str(field),
                "action": "ignored",
                "reason": "Verifier returned a decision for a field outside this playbook contract.",
            }
        )

    material_defects: list[dict[str, Any]] = []
    raw_material_defects = response.get("materialDefects", [])
    if not isinstance(raw_material_defects, list):
        raw_material_defects = [
            {
                "code": "invalid-material-defect",
                "reason": "Verifier materialDefects must be an array.",
            }
        ]
    for raw_defect in raw_material_defects:
        if not isinstance(raw_defect, dict):
            decision_findings.append(
                {
                    "code": "invalid-material-defect",
                    "action": "ignored",
                    "reason": "Verifier material defect was not an object.",
                }
            )
            continue
        code = str(raw_defect.get("code") or "")
        reason = str(raw_defect.get("reason") or "").strip()
        field = str(raw_defect.get("field") or "")
        candidate_viability = str(raw_defect.get("candidateViability") or "").strip()
        if (
            code not in VERIFICATION_MATERIAL_DEFECTS
            or not reason
            or candidate_viability not in {"", "candidate-fatal", "field-quarantinable"}
            or (
                code == "unsupported-safety-critical-claim"
                and field not in required_set
            )
        ):
            decision_findings.append(
                {
                    "code": "invalid-material-defect",
                    "field": str(raw_defect.get("field") or ""),
                    "action": "ignored",
                    "reason": "Verifier material defect used an unsupported code or lacked a reason.",
                }
            )
            continue
        if field:
            if field not in required_set:
                decision_findings.append(
                    {
                        "code": "invalid-material-defect",
                        "field": field,
                        "action": "ignored",
                        "reason": "Verifier material defect named a field outside this playbook contract.",
                    }
                )
                continue
            if candidate_viability == "candidate-fatal" and code in CANDIDATE_FATAL_DEFECTS:
                material_defects.append(
                    {
                        "code": code,
                        "reason": reason,
                        "field": field,
                        "candidateViability": candidate_viability,
                    }
                )
                continue
            action, quarantine_reason = _quarantine_field(fields, field, code, reason)
            decision_findings.append(
                {
                    "code": (
                        "supplementary-field-material-defect"
                        if field in non_blocking_set
                        else "field-material-defect"
                    ),
                    "field": field,
                    "action": action,
                    "reason": quarantine_reason,
                }
            )
            continue
        material_defects.append(
            {
                "code": code,
                "reason": reason,
                "candidateViability": candidate_viability or "candidate-fatal",
            }
        )
    return verified, decision_findings, material_defects


def _finding_requires_review(finding: Any) -> bool:
    if not isinstance(finding, dict):
        return True
    return str(finding.get("action") or "") not in VERIFIER_RESOLVED_ACTIONS


def _resolved_false_positive_finding(
    finding: Any, final_issues: Iterable[dict[str, Any]]
) -> bool:
    if not isinstance(finding, dict):
        return False
    field = str(finding.get("field") or "")
    if (
        str(finding.get("code") or "") != "deterministic-finding-resolved"
        or not field
        or "false positive" not in str(finding.get("reason") or "").casefold()
    ):
        return False
    return not any(
        isinstance(issue, dict) and str(issue.get("field") or "") == field
        for issue in final_issues
    )


def _resolve_semantic_deterministic_findings(
    issues: Iterable[dict[str, Any]],
    verifier_findings: Iterable[Any],
    field_decisions: Any,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    decisions = field_decisions if isinstance(field_decisions, dict) else {}
    findings = [finding for finding in verifier_findings if isinstance(finding, dict)]
    unresolved: list[dict[str, Any]] = []
    resolutions: list[dict[str, Any]] = []
    for issue in issues:
        issue_code = str(issue.get("code") or "")
        field = str(issue.get("field") or "")
        if issue_code not in SEMANTICALLY_RESOLVABLE_ISSUES or not field:
            unresolved.append(issue)
            continue
        decision = decisions.get(field)
        decision_action = (
            str(decision.get("action") or "") if isinstance(decision, dict) else ""
        )
        resolution = (
            {
                "reason": str(decision.get("reason") or "Verifier supplied a source-bound conflict.")
            }
            if decision_action == "mark-conflicting"
            else None
        )
        for finding in findings:
            if resolution is not None:
                break
            if str(finding.get("field") or "") != field:
                continue
            finding_code = str(finding.get("code") or "").lower()
            action = str(finding.get("action") or "")
            explicitly_resolved = (
                action in VERIFIER_RESOLVED_ACTIONS
                or "false-positive" in finding_code
                or "erroneous" in finding_code
                or (
                    issue_code in {"cross-program-evidence", "cross-organization-evidence"}
                    and finding_code == issue_code
                    and decision_action == "keep"
                )
            )
            if explicitly_resolved:
                resolution = finding
                break
        if resolution is None:
            unresolved.append(issue)
            continue
        resolutions.append(
            {
                "code": "semantic-verifier-resolution",
                "field": field,
                "action": "resolved",
                "deterministicCode": issue_code,
                "reason": str(resolution.get("reason") or "Verifier resolved the finding."),
            }
        )
    return unresolved, resolutions


def derive_verification_from_response(
    dossier: dict[str, Any],
    packet: dict[str, Any],
    response: dict[str, Any],
    required_fields: Iterable[str],
    non_blocking_fields: Iterable[str] = (),
) -> tuple[str, dict[str, Any], dict[str, Any]]:
    dossier = restore_reviewed_identity_bindings(dossier, packet)
    required = tuple(required_fields)
    initial_findings = validate_dossier_for_packet(dossier, packet, required)
    verifier_findings = response.get("findings", [])
    if not isinstance(verifier_findings, list):
        raise OptimizationModelError("Verifier findings must be an array")
    verified, decision_findings, material_defects = apply_verification_decisions(
        dossier, response, required, non_blocking_fields
    )
    post_verifier_findings = validate_dossier_for_packet(verified, packet, required)
    unresolved_post, semantic_resolutions = _resolve_semantic_deterministic_findings(
        post_verifier_findings, verifier_findings, response.get("fieldDecisions")
    )
    verified, deterministic_remediation = remediate_invalid_factual_fields(
        verified, unresolved_post, required
    )
    raw_final_findings = validate_dossier_for_packet(verified, packet, required)
    final_findings, final_resolutions = _resolve_semantic_deterministic_findings(
        raw_final_findings, verifier_findings, response.get("fieldDecisions")
    )
    seen_resolutions = {
        (item.get("field"), item.get("deterministicCode"))
        for item in semantic_resolutions
    }
    semantic_resolutions.extend(
        item
        for item in final_resolutions
        if (item.get("field"), item.get("deterministicCode")) not in seen_resolutions
    )
    resolved_false_positives = [
        finding
        for finding in verifier_findings
        if _resolved_false_positive_finding(finding, final_findings)
    ]
    semantic_resolutions.extend(
        {
            "code": "obsolete-deterministic-finding-resolution",
            "field": str(finding.get("field") or ""),
            "action": "resolved",
            "reason": (
                "The current deterministic policy accepts this field, so the verifier's "
                "recorded false-positive finding requires no human review."
            ),
        }
        for finding in resolved_false_positives
    )
    review_findings = [
        finding
        for finding in (
            *decision_findings,
            *deterministic_remediation,
            *(
                finding
                for finding in verifier_findings
                if finding not in resolved_false_positives
            ),
        )
        if _finding_requires_review(finding)
    ]
    requested_status = str(response.get("status") or "passed")
    status = verification_status(
        final_issues=final_findings,
        material_defects=material_defects,
        review_findings=review_findings,
        requested_status=requested_status,
    )
    findings = {
        "derivationPolicyVersion": VERIFICATION_DERIVATION_POLICY_VERSION,
        "initialDeterministicFindings": initial_findings,
        "verifierFindings": verifier_findings,
        "verifierDecisionFindings": decision_findings,
        "materialDefects": material_defects,
        "postVerifierDeterministicFindings": post_verifier_findings,
        "semanticResolutionFindings": semantic_resolutions,
        "deterministicRemediationFindings": deterministic_remediation,
        "rawFinalDeterministicFindings": raw_final_findings,
        "finalDeterministicFindings": final_findings,
    }
    return status, verified, findings


def verification_status(
    *,
    final_issues: Iterable[dict[str, Any]],
    material_defects: Iterable[dict[str, Any]],
    review_findings: Iterable[dict[str, Any]],
    requested_status: str,
) -> str:
    if tuple(final_issues) or tuple(material_defects):
        return "failed"
    if tuple(review_findings) or requested_status != "passed":
        return "needs-review"
    return "passed"


class OptimizationModelPipeline:
    def __init__(
        self,
        store: ResearchStore,
        configuration: dict[str, Any],
        corpus_id: int,
        *,
        extract: ModelCallback,
        verify: ModelCallback,
        required_coverage_needs: Iterable[dict[str, Any]] = (),
        progress: ProgressCallback | None = None,
    ) -> None:
        self.store = store
        self.configuration = configuration
        self.configuration_record = configuration_snapshot(configuration)
        snapshot = self.configuration_record["snapshot"]
        if snapshot["quantization"] not in {"4-bit", "8-bit"}:
            raise ValueError("Candidate extraction requires a 4-bit or 8-bit configuration")
        self.playbook = playbook_for(str(snapshot["targetCategoryId"]))
        self.required_fields = self.playbook.factual_fields
        self.corpus_id = int(corpus_id)
        self.extract = extract
        self.verify = verify
        self.required_coverage_needs = tuple(required_coverage_needs)
        self.progress = progress or (lambda _event: None)

    def run(self) -> ModelEvaluationResult:
        configuration_id = self.store.save_optimization_configuration(self.configuration)
        self._validate_corpus(configuration_id)
        run_id = self._ensure_run(configuration_id)
        self._mark_run(run_id, status="running", phase="candidate-extraction")
        try:
            for packet_id, packet in self._packets():
                dossier_id, dossier = self._ensure_dossier(run_id, packet_id, packet)
                self._ensure_verification(run_id, packet_id, dossier_id, packet, dossier)
            self._mark_run(run_id, status="running", phase="completeness-audit")
            result = self._audit(run_id, configuration_id)
        except Exception as error:
            self._mark_run(run_id, status="partial", phase="resume-required", error=str(error))
            if isinstance(error, OptimizationModelError):
                raise
            raise OptimizationModelError(str(error)) from error
        self._mark_run(run_id, status="completed", phase="complete")
        return result

    def verified_candidates(self, run_id: int) -> list[dict[str, Any]]:
        with self.store.connect() as connection:
            rows = connection.execute(
                """SELECT verification.status, verification.verified_dossier_json,
                          verification.findings_json
                   FROM optimization_verifications AS verification
                   JOIN optimization_candidate_dossiers AS dossier
                     ON dossier.id = verification.dossier_id
                   WHERE dossier.run_id = ?
                     AND verification.status IN ('passed', 'needs-review')
                   ORDER BY dossier.packet_id""",
                (run_id,),
            ).fetchall()
        return [
            verified_dossier_to_candidate(
                json.loads(row["verified_dossier_json"]),
                verification_status=str(row["status"]),
                verification_findings=json.loads(row["findings_json"] or "{}"),
            )
            for row in rows
        ]

    def _validate_corpus(self, configuration_id: int) -> None:
        snapshot = self.configuration_record["snapshot"]
        with self.store.connect() as connection:
            row = connection.execute(
                """SELECT corpus.status, discovery_configuration.snapshot_json
                   FROM optimization_corpora AS corpus
                   JOIN optimization_runs AS discovery_run
                     ON discovery_run.id = corpus.discovery_run_id
                   JOIN optimization_configurations AS discovery_configuration
                     ON discovery_configuration.id = discovery_run.configuration_id
                   WHERE corpus.id = ?""",
                (self.corpus_id,),
            ).fetchone()
        if not row or row["status"] != "frozen":
            raise OptimizationModelError("Model evaluation requires a frozen evidence corpus")
        discovery_snapshot = json.loads(row["snapshot_json"])
        for field in (
            "sourcePackageSha256",
            "sourcePackageVersion",
            "targetLocation",
            "regionalScope",
            "targetCategoryId",
            "stageKey",
            "queryPlan",
        ):
            if discovery_snapshot[field] != snapshot[field]:
                raise OptimizationModelError(
                    f"Model configuration does not match frozen corpus field {field}"
                )

    def _ensure_run(self, configuration_id: int) -> int:
        with self.store.connect() as connection:
            corpus = connection.execute(
                "SELECT corpus_sha256 FROM optimization_corpora WHERE id = ?",
                (self.corpus_id,),
            ).fetchone()
            label = (
                f"{self.configuration_record['label']}-"
                f"{str(corpus['corpus_sha256'])[:12]}"
            )
            existing = connection.execute(
                "SELECT id, configuration_id, corpus_id FROM optimization_runs WHERE label = ?",
                (label,),
            ).fetchone()
            if existing:
                if (
                    int(existing["configuration_id"]) != configuration_id
                    or int(existing["corpus_id"]) != self.corpus_id
                ):
                    raise OptimizationModelError(
                        "A model-evaluation label cannot be resumed with different provenance"
                    )
                return int(existing["id"])
            cursor = connection.execute(
                """INSERT INTO optimization_runs (
                       created_at, label, configuration_id, corpus_id, run_kind,
                       status, current_phase
                   ) VALUES (?, ?, ?, ?, 'model-evaluation', 'queued', 'candidate-extraction')""",
                (_now(), label, configuration_id, self.corpus_id),
            )
        return int(cursor.lastrowid)

    def _packets(self) -> list[tuple[int, dict[str, Any]]]:
        with self.store.connect() as connection:
            rows = connection.execute(
                """SELECT id, packet_json FROM optimization_evidence_packets
                   WHERE corpus_id = ? ORDER BY identity_key""",
                (self.corpus_id,),
            ).fetchall()
        return [(int(row["id"]), json.loads(row["packet_json"])) for row in rows]

    def _ensure_dossier(
        self,
        run_id: int,
        packet_id: int,
        packet: dict[str, Any],
    ) -> tuple[int, dict[str, Any]]:
        with self.store.connect() as connection:
            existing = connection.execute(
                """SELECT id, dossier_json FROM optimization_candidate_dossiers
                   WHERE run_id = ? AND packet_id = ?""",
                (run_id, packet_id),
            ).fetchone()
        if existing:
            return int(existing["id"]), json.loads(existing["dossier_json"])
        prompt = {
            "operation": "extract-candidate-dossier",
            "instructions": [
                "Use only the supplied frozen evidence packet.",
                "Return one organization-plus-program candidate dossier.",
                "Bind every supported or conflicting field value to exact source ids.",
                "Each retained value must exactly equal the JSON value in every cited source support binding.",
                "Use only program or organization as an evidence-binding scope.",
                "Use conflicting only for two or more genuinely incompatible values, not complementary details.",
                "Return unknown with a reason instead of inferring a missing fact.",
                "Do not transfer facts between programs in the same organization.",
                (
                    "Respect contact types: phone and additionalPhoneNumbers may contain only "
                    "callable or text-capable phone numbers, never fax numbers or email addresses."
                ),
                (
                    "Treat access points, properties, partners, subprograms, and named examples "
                    "as separate entities; do not promote their facts to the candidate unless "
                    "the source explicitly states that the fact applies candidate-wide."
                ),
                (
                    "Addresses and service geography need an explicit candidate-level service, "
                    "location, or intake link. Do not turn a site footer, headquarters, admin "
                    "office, organization-wide contact, or another program's address into the "
                    "candidate address or service area."
                ),
                (
                    "For the website field, a direct-provider source canonical URL whose "
                    "pageIdentityKey exactly matches the candidate is explicit program-page "
                    "evidence even when that URL is not printed inside the page text."
                ),
            ],
            "requiredFields": list(self.required_fields),
            "outputContract": {
                "candidateIdentity": {
                    "organization": "copy from evidencePacket.candidateIdentity",
                    "program": "copy from evidencePacket.candidateIdentity",
                    "identityKey": "copy exactly",
                    "componentIdentityKeys": ["the one exact identityKey"],
                },
                "sources": (
                    "Return each used source as an object with only id, supports, and contradicts. "
                    "Scout restores immutable URL, title, extract, authority, pageIdentityKey, "
                    "and pageOrganizationKey from the frozen evidence packet after this response. "
                    "Every supports or contradicts item has field, value, and scope; scope must "
                    "be exactly program or organization, and value must be the exact JSON value "
                    "retained for that field or conflict alternative."
                ),
                "fields": {
                    "supported": {
                        "status": "supported",
                        "value": "exact supported value",
                        "evidenceIds": ["source id"],
                    },
                    "conflicting": {
                        "status": "conflicting",
                        "alternatives": [
                            {"value": "one source value", "evidenceIds": ["source id"]}
                        ],
                    },
                    "unknown": {"status": "unknown", "reason": "specific reason"},
                },
                "rules": [
                    "Return every requiredFields key exactly once under fields.",
                    "Do not add factual values outside fields or sources.",
                    "Do not use markdown fences or commentary outside the JSON object.",
                ],
            },
            "evidencePacket": packet,
        }
        attempt_id = self._start_attempt(run_id, packet_id, "extract", prompt)
        try:
            invocation = _invocation(self.extract(prompt))
            dossier = invocation.result
            if not isinstance(dossier.get("candidateIdentity"), dict):
                raise OptimizationModelError("Extractor returned no candidate identity")
            dossier = restore_frozen_candidate_identity(dossier, packet)
            dossier = restore_frozen_source_envelopes(dossier, packet)
            dossier = restore_reviewed_identity_bindings(dossier, packet)
        except BaseException as error:
            self._fail_attempt(
                attempt_id,
                str(error),
                raw_output=getattr(error, "raw_output", ""),
                usage=getattr(error, "usage", None),
            )
            raise
        with self.store.connect() as connection:
            raw = invocation.raw_output or canonical_json(invocation.result)
            connection.execute(
                """UPDATE optimization_model_attempts
                   SET completed_at = ?, status = 'completed', raw_output = ?,
                       parsed_json = ?, usage_json = ?, error = '' WHERE id = ?""",
                (
                    _now(),
                    raw,
                    canonical_json(invocation.result),
                    canonical_json(invocation.usage) if invocation.usage else None,
                    attempt_id,
                ),
            )
            dossier_id = int(
                connection.execute(
                    """INSERT INTO optimization_candidate_dossiers (
                           run_id, packet_id, extraction_attempt_id, dossier_json, dossier_sha256
                       ) VALUES (?, ?, ?, ?, ?)""",
                    (
                        run_id,
                        packet_id,
                        attempt_id,
                        canonical_json(dossier),
                        sha256_json(dossier),
                    ),
                ).lastrowid
            )
        self.progress(
            {
                "phase": "extraction",
                "packetId": packet_id,
                "identityKey": packet["candidateIdentity"]["identityKey"],
            }
        )
        return dossier_id, dossier

    def _ensure_verification(
        self,
        run_id: int,
        packet_id: int,
        dossier_id: int,
        packet: dict[str, Any],
        dossier: dict[str, Any],
    ) -> None:
        with self.store.connect() as connection:
            existing = connection.execute(
                "SELECT id FROM optimization_verifications WHERE dossier_id = ?",
                (dossier_id,),
            ).fetchone()
        if existing:
            return
        deterministic_findings = validate_dossier_for_packet(
            dossier, packet, self.required_fields
        )
        prompt = {
            "operation": "verify-candidate-dossier-decision-patch-fresh-context",
            "instructions": [
                "Check the dossier independently against only the supplied identity and sources.",
                "Return one explicit decision for every required factual field.",
                "Use keep when the validated extraction field is supported as written.",
                "Use downgrade-to-unknown for an unsupported or misattributed claim.",
                "Use mark-conflicting only for source-bound incompatible values.",
                "Use flag-review when the field is usable but needs human attention.",
                "Report material identity, category, geography, source, safety, or credibility defects separately.",
                "A field defect is field-quarantinable when removing that field leaves a truthful candidate.",
                "Use candidate-fatal only when core identity, current service, relevant geography, or credible existence cannot remain truthful after unsafe fields are removed.",
                "Do not invent replacement facts.",
                "Do not return or rewrite the dossier, identity, or source envelopes.",
            ],
            "candidateIdentity": packet["candidateIdentity"],
            "sources": packet["sources"],
            "dossier": compact_source_bindings(dossier),
            "requiredFields": list(self.required_fields),
            "deterministicFindings": deterministic_findings,
            "checklist": [
                "source-to-field attribution",
                "organization and program boundaries",
                "jurisdiction and service area",
                "conflicting contact or intake information",
                "speculative restrictions",
                "duplicate or fragmented identity",
                "access-point, property, partner, subprogram, and system attribution",
                "footer, headquarters, admin-office, and service-geography attribution",
                "exact-identity direct-provider URL evidence for the website field",
                "missing required fields",
            ],
            "outputContract": {
                "status": "passed or needs-review",
                "fieldDecisions": {
                    "each exact required field": {
                        "action": (
                            "keep, downgrade-to-unknown, mark-conflicting, or flag-review"
                        ),
                        "reason": "required for every action except keep",
                        "alternatives": (
                            "required only for mark-conflicting; each item has exact value and evidenceIds"
                        ),
                    }
                },
                "materialDefects": [
                    {
                        "code": (
                            "identity-conflation, wrong-category, wrong-geography, "
                            "altered-or-invented-source, unsupported-safety-critical-claim, "
                            "or candidate-not-credible"
                        ),
                        "field": "field name when applicable",
                        "candidateViability": "field-quarantinable or candidate-fatal",
                        "reason": "evidence-based explanation",
                    }
                ],
                "findings": [
                    {
                        "code": "short finding code",
                        "field": "field name when applicable",
                        "action": "removed, downgraded, separated, or flagged",
                        "reason": "evidence-based explanation",
                    }
                ],
                "rules": [
                    "Return every required field exactly once under fieldDecisions.",
                    "Never return verifiedDossier, candidateIdentity, fields, or sources as replacements.",
                    "Do not add replacement facts or source ids.",
                    "Do not use markdown fences or commentary outside the JSON object.",
                ],
            },
        }
        attempt_id = self._start_attempt(run_id, packet_id, "verify", prompt)
        try:
            invocation = _invocation(self.verify(prompt))
            status, verified, findings = derive_verification_from_response(
                dossier,
                packet,
                invocation.result,
                self.required_fields,
                self.playbook.supplementary_fields,
            )
        except BaseException as error:
            self._fail_attempt(
                attempt_id,
                str(error),
                raw_output=getattr(error, "raw_output", ""),
                usage=getattr(error, "usage", None),
            )
            raise
        with self.store.connect() as connection:
            raw = invocation.raw_output or canonical_json(invocation.result)
            connection.execute(
                """UPDATE optimization_model_attempts
                   SET completed_at = ?, status = 'completed', raw_output = ?,
                       parsed_json = ?, usage_json = ?, error = '' WHERE id = ?""",
                (
                    _now(),
                    raw,
                    canonical_json(invocation.result),
                    canonical_json(invocation.usage) if invocation.usage else None,
                    attempt_id,
                ),
            )
            connection.execute(
                """INSERT INTO optimization_verifications (
                       dossier_id, verification_attempt_id, status,
                       verified_dossier_json, verified_dossier_sha256, findings_json
                   ) VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    dossier_id,
                    attempt_id,
                    status,
                    canonical_json(verified),
                    sha256_json(verified),
                    canonical_json(findings),
                ),
            )
        self.progress(
            {
                "phase": "verification",
                "packetId": packet_id,
                "status": status,
                "initialFindingCount": len(deterministic_findings),
                "finalFindingCount": len(findings["finalDeterministicFindings"]),
            }
        )

    def _start_attempt(
        self, run_id: int, packet_id: int, operation: str, prompt: dict[str, Any]
    ) -> int:
        with self.store.connect() as connection:
            attempt_number = int(
                connection.execute(
                    """SELECT COALESCE(MAX(attempt_number), 0) + 1 AS value
                       FROM optimization_model_attempts
                       WHERE run_id = ? AND packet_id = ? AND operation = ?""",
                    (run_id, packet_id, operation),
                ).fetchone()["value"]
            )
            cursor = connection.execute(
                """INSERT INTO optimization_model_attempts (
                       run_id, packet_id, corpus_id, operation, attempt_number,
                       started_at, status, prompt_sha256
                   ) VALUES (?, ?, ?, ?, ?, ?, 'running', ?)""",
                (
                    run_id,
                    packet_id,
                    self.corpus_id,
                    operation,
                    attempt_number,
                    _now(),
                    sha256_json(prompt),
                ),
            )
        return int(cursor.lastrowid)

    def _fail_attempt(
        self,
        attempt_id: int,
        error: str,
        *,
        raw_output: str = "",
        usage: dict[str, Any] | None = None,
    ) -> None:
        with self.store.connect() as connection:
            connection.execute(
                """UPDATE optimization_model_attempts
                   SET completed_at = ?, status = 'failed', raw_output = ?,
                       usage_json = ?, error = ? WHERE id = ?""",
                (
                    _now(),
                    raw_output,
                    canonical_json(usage) if usage else None,
                    error,
                    attempt_id,
                ),
            )

    def _audit(self, run_id: int, configuration_id: int) -> ModelEvaluationResult:
        with self.store.connect() as connection:
            rows = connection.execute(
                """SELECT verification.status, verification.verified_dossier_json,
                          packet.packet_json
                   FROM optimization_verifications AS verification
                   JOIN optimization_candidate_dossiers AS dossier
                     ON dossier.id = verification.dossier_id
                   JOIN optimization_evidence_packets AS packet
                     ON packet.id = dossier.packet_id
                   WHERE dossier.run_id = ? ORDER BY dossier.packet_id""",
                (run_id,),
            ).fetchall()
        summary = _summarize_verification_rows(rows)
        state_counts = summary["fieldStates"]
        coverage_tags = set(summary["coverageTags"])
        passed = summary["statusCounts"]["passed"]
        needs_review = summary["statusCounts"]["needs-review"]
        failed = summary["statusCounts"]["failed"]
        gaps = []
        with self.store.connect() as connection:
            for need in self.required_coverage_needs:
                key = str(need.get("key") or "").strip()
                label = str(need.get("label") or key).strip()
                query = str(need.get("query") or "").strip()
                if not key or not query:
                    raise OptimizationModelError("Coverage needs require key and query")
                if need.get("candidateGap") is False:
                    continue
                any_tags = {
                    str(tag).strip()
                    for tag in need.get("satisfiedByAnyTags", [])
                    if str(tag).strip()
                }
                all_tags = {
                    str(tag).strip()
                    for tag in need.get("satisfiedByAllTags", [])
                    if str(tag).strip()
                }
                if any_tags and all_tags:
                    raise OptimizationModelError(
                        "Coverage needs cannot combine any-tag and all-tag matching"
                    )
                if any_tags:
                    satisfied = bool(any_tags & coverage_tags)
                    expected_tags = sorted(any_tags)
                    match_description = "one of"
                elif all_tags:
                    satisfied = all_tags <= coverage_tags
                    expected_tags = sorted(all_tags)
                    match_description = "all of"
                else:
                    satisfied = key in coverage_tags
                    expected_tags = [key]
                    match_description = ""
                if satisfied:
                    continue
                tag_text = ", ".join(expected_tags)
                reason = (
                    "No frozen evidence packet coverage satisfies required tag"
                    + (f" set ({match_description} {tag_text})" if match_description else f" {tag_text}")
                )
                gaps.append({"key": key, "label": label, "query": query, "reason": reason})
                connection.execute(
                    """INSERT OR REPLACE INTO optimization_gap_queries (
                           run_id, corpus_id, need_key, need_label, reason,
                           query_text, status
                       ) VALUES (?, ?, ?, ?, ?, ?, 'planned')""",
                    (run_id, self.corpus_id, key, label, reason, query),
                )
        _persist_model_evaluation_audits(self.store, run_id, summary, gaps)
        self.progress(
            {
                "phase": "gap-audit",
                "gapCount": len(gaps),
                "verificationFailureCount": failed,
                "verificationNeedsReviewCount": needs_review,
            }
        )
        return ModelEvaluationResult(
            run_id=run_id,
            configuration_id=configuration_id,
            corpus_id=self.corpus_id,
            packet_count=len(rows),
            passed_count=passed,
            needs_review_count=needs_review,
            failed_count=failed,
            supported_field_count=state_counts["supported"],
            conflicting_field_count=state_counts["conflicting"],
            unknown_field_count=state_counts["unknown"],
            gap_count=len(gaps),
            quality_gate_passed=failed == 0,
        )

    def _mark_run(
        self, run_id: int, *, status: str, phase: str, error: str = ""
    ) -> None:
        now = _now()
        with self.store.connect() as connection:
            connection.execute(
                """UPDATE optimization_runs
                   SET status = ?, current_phase = ?, error = ?,
                       started_at = COALESCE(started_at, ?),
                       completed_at = CASE WHEN ? IN ('completed', 'failed', 'cancelled')
                                           THEN ? ELSE NULL END
                   WHERE id = ?""",
                (status, phase, error, now, status, now, run_id),
            )
