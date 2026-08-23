from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Iterable

from .optimization import (
    canonical_json,
    configuration_snapshot,
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
    counts = summary["statusCounts"]
    reports = {
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
    with store.connect() as connection:
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


def validate_dossier_for_packet(
    dossier: dict[str, Any],
    packet: dict[str, Any],
    required_fields: Iterable[str],
) -> list[dict[str, str]]:
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
            if not isinstance(alternatives, list):
                decision_findings.append(
                    {
                        "code": "invalid-verifier-decision",
                        "field": field,
                        "action": "preserved",
                        "reason": "A conflicting decision requires source-bound alternatives.",
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
        if (
            code not in VERIFICATION_MATERIAL_DEFECTS
            or not reason
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
        if field and field in non_blocking_set:
            decision_findings.append(
                {
                    "code": "nonblocking-field-material-defect",
                    "field": field,
                    "action": "ignored",
                    "reason": (
                        "This playbook classifies the field as supplementary; "
                        "downgrade or flag it without rejecting the candidate."
                    ),
                }
            )
            continue
        material_defects.append(
            {
                "code": code,
                "reason": reason,
                **(
                    {"field": field}
                    if field
                    else {}
                ),
            }
        )
    return verified, decision_findings, material_defects


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
        required_coverage_needs: Iterable[dict[str, str]] = (),
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
            verifier_findings = invocation.result.get("findings", [])
            if not isinstance(verifier_findings, list):
                raise OptimizationModelError("Verifier findings must be an array")
            verified, decision_findings, material_defects = apply_verification_decisions(
                dossier,
                invocation.result,
                self.required_fields,
                self.playbook.supplementary_fields,
            )
            post_verifier_issues = validate_dossier_for_packet(
                verified, packet, self.required_fields
            )
            verified, deterministic_remediation = remediate_invalid_factual_fields(
                verified, post_verifier_issues, self.required_fields
            )
            final_issues = validate_dossier_for_packet(
                verified, packet, self.required_fields
            )
        except BaseException as error:
            self._fail_attempt(
                attempt_id,
                str(error),
                raw_output=getattr(error, "raw_output", ""),
                usage=getattr(error, "usage", None),
            )
            raise
        requested_status = str(invocation.result.get("status") or "passed")
        status = verification_status(
            final_issues=final_issues,
            material_defects=material_defects,
            review_findings=(
                *decision_findings,
                *deterministic_remediation,
                *verifier_findings,
            ),
            requested_status=requested_status,
        )
        findings = {
            "initialDeterministicFindings": deterministic_findings,
            "verifierFindings": verifier_findings,
            "verifierDecisionFindings": decision_findings,
            "materialDefects": material_defects,
            "postVerifierDeterministicFindings": post_verifier_issues,
            "deterministicRemediationFindings": deterministic_remediation,
            "finalDeterministicFindings": final_issues,
        }
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
                "finalFindingCount": len(final_issues),
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
                if key in coverage_tags:
                    continue
                reason = f"No frozen evidence packet carries required coverage tag {key}"
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
