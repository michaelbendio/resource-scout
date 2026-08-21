from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Iterable

from .optimization import (
    HOUSING_FACTUAL_FIELDS,
    canonical_json,
    configuration_snapshot,
    sha256_json,
    validate_candidate_dossier,
)
from .storage import ResearchStore


ModelCallback = Callable[[dict[str, Any]], "ModelInvocation | dict[str, Any]"]
ProgressCallback = Callable[[dict[str, Any]], None]


class OptimizationModelError(RuntimeError):
    pass


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


def verified_dossier_to_candidate(dossier: dict[str, Any]) -> dict[str, Any]:
    identity = dossier["candidateIdentity"]
    candidate: dict[str, Any] = {
        "name": str(identity.get("program") or identity.get("organization") or "Unnamed candidate"),
        "organization": str(identity.get("organization") or ""),
        "program": str(identity.get("program") or ""),
        "unknowns": [],
        "conflicts": [],
        "evidence": [],
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


def validate_dossier_for_packet(
    dossier: dict[str, Any], packet: dict[str, Any]
) -> list[dict[str, str]]:
    issues = validate_candidate_dossier(dossier)
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
        if self.configuration_record["snapshot"]["quantization"] not in {"4-bit", "8-bit"}:
            raise ValueError("Candidate extraction requires a 4-bit or 8-bit configuration")
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
                """SELECT verification.verified_dossier_json
                   FROM optimization_verifications AS verification
                   JOIN optimization_candidate_dossiers AS dossier
                     ON dossier.id = verification.dossier_id
                   WHERE dossier.run_id = ? AND verification.status = 'passed'
                   ORDER BY dossier.packet_id""",
                (run_id,),
            ).fetchall()
        return [
            verified_dossier_to_candidate(json.loads(row["verified_dossier_json"]))
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
                "Return unknown with a reason instead of inferring a missing fact.",
                "Do not transfer facts between programs in the same organization.",
            ],
            "requiredFields": list(HOUSING_FACTUAL_FIELDS),
            "evidencePacket": packet,
        }
        attempt_id = self._start_attempt(run_id, packet_id, "extract", prompt)
        try:
            invocation = _invocation(self.extract(prompt))
            dossier = invocation.result
            if not isinstance(dossier.get("candidateIdentity"), dict):
                raise OptimizationModelError("Extractor returned no candidate identity")
        except BaseException as error:
            self._fail_attempt(attempt_id, str(error))
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
        deterministic_findings = validate_dossier_for_packet(dossier, packet)
        prompt = {
            "operation": "verify-candidate-dossier-fresh-context",
            "instructions": [
                "Check the dossier independently against only the supplied identity and sources.",
                "Remove, downgrade, or flag unsupported or misattributed claims.",
                "Do not invent replacement facts.",
                "Every factual field must finish supported, conflicting, or unknown.",
            ],
            "candidateIdentity": packet["candidateIdentity"],
            "sources": packet["sources"],
            "dossier": dossier,
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
        }
        attempt_id = self._start_attempt(run_id, packet_id, "verify", prompt)
        try:
            invocation = _invocation(self.verify(prompt))
            verified = invocation.result.get("verifiedDossier")
            if not isinstance(verified, dict):
                raise OptimizationModelError("Verifier returned no verifiedDossier object")
            verifier_findings = invocation.result.get("findings", [])
            if not isinstance(verifier_findings, list):
                raise OptimizationModelError("Verifier findings must be an array")
            final_issues = validate_dossier_for_packet(verified, packet)
        except BaseException as error:
            self._fail_attempt(attempt_id, str(error))
            raise
        requested_status = str(invocation.result.get("status") or "passed")
        status = (
            "failed"
            if final_issues
            else requested_status
            if requested_status in {"passed", "needs-review"}
            else "failed"
        )
        findings = {
            "initialDeterministicFindings": deterministic_findings,
            "verifierFindings": verifier_findings,
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

    def _fail_attempt(self, attempt_id: int, error: str) -> None:
        with self.store.connect() as connection:
            connection.execute(
                """UPDATE optimization_model_attempts
                   SET completed_at = ?, status = 'failed', error = ? WHERE id = ?""",
                (_now(), error, attempt_id),
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
        state_counts = {"supported": 0, "conflicting": 0, "unknown": 0}
        coverage_tags: set[str] = set()
        passed = 0
        failed = 0
        for row in rows:
            dossier = json.loads(row["verified_dossier_json"])
            packet = json.loads(row["packet_json"])
            coverage_tags.update(packet["candidateIdentity"].get("coverageTags", []))
            if row["status"] == "passed":
                passed += 1
            else:
                failed += 1
            for finding in dossier.get("fields", {}).values():
                if isinstance(finding, dict) and finding.get("status") in state_counts:
                    state_counts[finding["status"]] += 1
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
            completeness = {
                "packetCount": len(rows),
                "passedCount": passed,
                "failedCount": failed,
                "fieldStates": state_counts,
            }
            quality = {
                "passed": failed == 0,
                "verificationFailures": failed,
                "coverageTags": sorted(coverage_tags),
                "coverageGaps": gaps,
            }
            for audit_type, report in (
                ("candidate-completeness", completeness),
                ("quality-gate", quality),
            ):
                connection.execute(
                    """INSERT OR REPLACE INTO optimization_audits (
                           run_id, audit_type, created_at, report_json, report_sha256
                       ) VALUES (?, ?, ?, ?, ?)""",
                    (
                        run_id,
                        audit_type,
                        _now(),
                        canonical_json(report),
                        sha256_json(report),
                    ),
                )
        self.progress(
            {
                "phase": "gap-audit",
                "gapCount": len(gaps),
                "verificationFailureCount": failed,
            }
        )
        return ModelEvaluationResult(
            run_id=run_id,
            configuration_id=configuration_id,
            corpus_id=self.corpus_id,
            packet_count=len(rows),
            passed_count=passed,
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
