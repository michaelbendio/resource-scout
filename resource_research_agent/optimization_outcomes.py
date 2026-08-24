from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .importer import ResourcePackageImporter, resource_id
from .optimization import (
    canonical_json,
    optimization_candidate_id,
    optimization_resource_id,
    sha256_json,
)
from .storage import ResearchStore


class OptimizationOutcomeError(ValueError):
    pass


@dataclass(frozen=True)
class OptimizationPackageOutcome:
    run_id: int
    final_package_sha256: str
    report_sha256: str
    candidate_count: int
    accepted_count: int
    not_present_count: int
    report: dict[str, Any]


@dataclass(frozen=True)
class CuratorWork:
    sha256: str
    states: dict[str, dict[str, Any]]


def _candidate_field(value: Any) -> Any:
    if isinstance(value, str):
        return value.strip()
    return value


CURATOR_DISPOSITIONS = {
    "research-further",
    "duplicate",
    "wrong-category",
    "rejected",
}


def _read_curator_work(
    path: str | Path,
    *,
    run_id: int,
    configuration_hash: str,
    corpus_sha256: str,
    source_package_sha256: str,
    target_category_id: str,
    expected_candidate_ids: set[str],
) -> CuratorWork:
    try:
        work = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise OptimizationOutcomeError(f"Cannot read Curator work: {error}") from error
    if not isinstance(work, dict) or work.get("reviewFeedbackSchemaVersion") != 2:
        raise OptimizationOutcomeError("Curator work schema 2 is required")
    curator_run = work.get("run")
    if not isinstance(curator_run, dict) or str(curator_run.get("id")) != str(
        run_id
    ):
        raise OptimizationOutcomeError("Curator work belongs to a different run")
    if str(curator_run.get("categoryId") or "") != target_category_id:
        raise OptimizationOutcomeError("Curator work belongs to a different category")
    work_source_sha256 = work.get("sourceSha256")
    if work_source_sha256 not in (None, "", source_package_sha256):
        raise OptimizationOutcomeError("Curator work source package does not match the run")
    expected_review_id = uuid.uuid5(
        uuid.NAMESPACE_URL,
        f"resource-research-optimization-review:{configuration_hash}:{corpus_sha256}",
    ).hex
    if str(work.get("reviewId") or "") != expected_review_id:
        raise OptimizationOutcomeError("Curator work review identity does not match the run")
    candidates = work.get("candidates")
    if (
        not isinstance(candidates, dict)
        or set(map(str, candidates)) != expected_candidate_ids
    ):
        raise OptimizationOutcomeError("Curator work candidate set does not match the run")
    normalized: dict[str, dict[str, Any]] = {}
    raw_packaged_ids = work.get("packagedCandidateIds")
    if not isinstance(raw_packaged_ids, list):
        raise OptimizationOutcomeError("Curator work packaged candidate IDs must be a list")
    packaged_ids = {str(value) for value in raw_packaged_ids}
    if not packaged_ids.issubset(expected_candidate_ids):
        raise OptimizationOutcomeError("Curator work contains an unknown packaged candidate")
    state_packaged_ids: set[str] = set()
    for candidate_id, raw in candidates.items():
        if not isinstance(raw, dict):
            raise OptimizationOutcomeError("Curator candidate state must be an object")
        package_status = str(raw.get("packageStatus") or "pending")
        disposition = str(raw.get("disposition") or "")
        if package_status not in {"pending", "ready", "packaged"}:
            raise OptimizationOutcomeError("Curator candidate has an invalid package status")
        if disposition and disposition not in CURATOR_DISPOSITIONS:
            raise OptimizationOutcomeError("Curator candidate has an invalid disposition")
        if package_status in {"ready", "packaged"} and disposition:
            raise OptimizationOutcomeError(
                "Ready or packaged Curator state cannot also have a disposition"
            )
        if package_status == "packaged":
            state_packaged_ids.add(str(candidate_id))
        outcome_history = raw.get("outcomeHistory")
        package_history = raw.get("packageHistory")
        if not isinstance(outcome_history, list) or not isinstance(package_history, list):
            raise OptimizationOutcomeError("Curator candidate history must be a list")
        normalized[str(candidate_id)] = {
            "packageStatus": package_status,
            "disposition": disposition,
            "outcomeHistory": outcome_history,
            "packageHistory": package_history,
            "reviewedAt": raw.get("reviewedAt"),
            "updatedAt": raw.get("updatedAt"),
        }
    if state_packaged_ids != packaged_ids:
        raise OptimizationOutcomeError(
            "Curator packaged candidate IDs do not match candidate state"
        )
    return CuratorWork(sha256=sha256_json(work), states=normalized)


def _curator_outcome(state: dict[str, Any] | None) -> str:
    if not state:
        return "not-provided"
    if state["packageStatus"] == "packaged":
        return "entered-package"
    if state["packageStatus"] == "ready":
        return "ready-for-package"
    return str(state["disposition"] or "pending")


def compare_optimization_run_to_package(
    store: ResearchStore,
    run_id: int,
    package_path: str | Path,
    *,
    curator_work_path: str | Path | None = None,
) -> OptimizationPackageOutcome:
    """Link verified candidates to phone-vetted resources by stable resource id."""

    with store.connect() as connection:
        run = connection.execute(
            """SELECT run.status, run.configuration_id, run.corpus_id,
                      configuration.configuration_hash,
                      configuration.source_package_sha256,
                      configuration.target_category_id,
                      corpus.corpus_sha256
               FROM optimization_runs AS run
               JOIN optimization_configurations AS configuration
                 ON configuration.id = run.configuration_id
               JOIN optimization_corpora AS corpus ON corpus.id = run.corpus_id
               WHERE run.id = ? AND run.run_kind = 'model-evaluation'""",
            (run_id,),
        ).fetchone()
        rows = connection.execute(
            """SELECT packet.id AS packet_id, packet.identity_key,
                      packet.packet_sha256,
                      verification.status, verification.verified_dossier_json,
                      verification.verified_dossier_sha256
               FROM optimization_verifications AS verification
               JOIN optimization_candidate_dossiers AS dossier
                 ON dossier.id = verification.dossier_id
               JOIN optimization_evidence_packets AS packet
                 ON packet.id = dossier.packet_id
               WHERE dossier.run_id = ?
                 AND verification.status IN ('passed', 'needs-review')
               ORDER BY packet.identity_key""",
            (run_id,),
        ).fetchall()
    if not run or run["status"] != "completed":
        raise OptimizationOutcomeError("A completed optimization model run is required")
    if not rows:
        raise OptimizationOutcomeError("Optimization run has no exportable candidates")

    target_category_id = str(run["target_category_id"])
    package = ResourcePackageImporter(target_category_id).read(package_path)
    final_resources = {resource_id(resource): resource for resource in package.resources}
    expected_ids: set[str] = set()
    expected_candidate_ids = {
        optimization_candidate_id(
            str(run["configuration_hash"]), str(row["packet_sha256"])
        )
        for row in rows
    }
    curator_work = (
        _read_curator_work(
            curator_work_path,
            run_id=run_id,
            configuration_hash=str(run["configuration_hash"]),
            corpus_sha256=str(run["corpus_sha256"]),
            source_package_sha256=str(run["source_package_sha256"]),
            target_category_id=target_category_id,
            expected_candidate_ids=expected_candidate_ids,
        )
        if curator_work_path is not None
        else None
    )
    curator_states = curator_work.states if curator_work else {}
    outcomes = []
    for row in rows:
        packet_id = int(row["packet_id"])
        linked_resource_id = optimization_resource_id(
            str(run["configuration_hash"]), str(row["packet_sha256"])
        )
        legacy_resource_id = optimization_resource_id(
            str(run["configuration_hash"]), packet_id
        )
        expected_ids.update((linked_resource_id, legacy_resource_id))
        dossier = json.loads(row["verified_dossier_json"])
        candidate_id = optimization_candidate_id(
            str(run["configuration_hash"]), str(row["packet_sha256"])
        )
        curator_state = curator_states.get(candidate_id)
        curator_outcome = _curator_outcome(curator_state)
        identity = dossier.get("candidateIdentity", {})
        fields = dossier.get("fields", {})
        matched_resource_id = next(
            (
                resource_id_value
                for resource_id_value in (linked_resource_id, legacy_resource_id)
                if resource_id_value in final_resources
            ),
            None,
        )
        final_resource = (
            final_resources[matched_resource_id] if matched_resource_id else None
        )
        field_changes = []
        if final_resource:
            for candidate_field, resource_field in (
                ("name", "name"),
                ("phone", "phone"),
                ("address", "address"),
                ("website", "website"),
                ("hours", "hours"),
            ):
                finding = fields.get(candidate_field, {})
                original = (
                    finding.get("value")
                    if isinstance(finding, dict) and finding.get("status") == "supported"
                    else None
                )
                final = final_resource.get(resource_field)
                if _candidate_field(original) != _candidate_field(final):
                    field_changes.append(
                        {
                            "field": resource_field,
                            "scoutValue": original,
                            "vettedValue": final,
                        }
                    )
        final_outcome = (
            "present-in-vetted-package" if final_resource else "not-present"
        )
        outcome = {
            "packetId": packet_id,
            "packetSha256": row["packet_sha256"],
            "identityKey": row["identity_key"],
            "organization": identity.get("organization"),
            "program": identity.get("program"),
            "verificationStatus": row["status"],
            "verifiedDossierSha256": row["verified_dossier_sha256"],
            "resourceId": linked_resource_id,
            "matchedResourceId": matched_resource_id,
            "legacyResourceId": legacy_resource_id,
            "outcome": final_outcome,
            "fieldChanges": field_changes,
        }
        if curator_work:
            outcome.update(
                {
                    "candidateId": candidate_id,
                    "outcome": (
                        "present-in-vetted-package"
                        if final_resource
                        else {
                            "entered-package": "packaged-not-in-supplied-package",
                            "ready-for-package": "ready-not-in-supplied-package",
                        }.get(curator_outcome, curator_outcome)
                    ),
                    "curatorOutcome": curator_outcome,
                    "curatorOutcomeHistory": curator_state["outcomeHistory"],
                    "curatorPackageHistory": curator_state["packageHistory"],
                    "curatorReviewedAt": curator_state["reviewedAt"],
                    "curatorUpdatedAt": curator_state["updatedAt"],
                }
            )
        outcomes.append(outcome)
    accepted_count = sum(
        outcome["outcome"] == "present-in-vetted-package" for outcome in outcomes
    )
    unlinked_ids = sorted(set(final_resources) - expected_ids)
    report = {
        "schemaVersion": 2,
        "runId": run_id,
        "configurationId": int(run["configuration_id"]),
        "configurationHash": run["configuration_hash"],
        "corpusId": int(run["corpus_id"]),
        "corpusSha256": run["corpus_sha256"],
        "sourcePackageSha256": run["source_package_sha256"],
        "targetCategoryId": target_category_id,
        "finalPackageSha256": package.sha256,
        "candidateCount": len(outcomes),
        "presentInVettedPackageCount": accepted_count,
        "notPresentCount": len(outcomes) - accepted_count,
        "unlinkedFinalResourceCount": len(unlinked_ids),
        "unlinkedFinalResourceIds": unlinked_ids,
        "interpretation": (
            "Presence under the deterministic resource id proves candidate-to-final linkage. "
            "Absence is not automatically a rejection; the candidate may still be pending."
        ),
        "outcomes": outcomes,
    }
    curator_work_sha256 = ""
    if curator_work:
        curator_work_sha256 = curator_work.sha256
        terminal_outcomes = {
            "present-in-vetted-package",
            "duplicate",
            "wrong-category",
            "rejected",
        }
        terminal_count = sum(
            outcome["outcome"] in terminal_outcomes for outcome in outcomes
        )
        explicit_disposition_count = sum(
            outcome["curatorOutcome"] in CURATOR_DISPOSITIONS
            for outcome in outcomes
        )
        outcome_counts = {
            name: sum(outcome["outcome"] == name for outcome in outcomes)
            for name in sorted({outcome["outcome"] for outcome in outcomes})
        }
        report.update(
            {
                "schemaVersion": 3,
                "curatorWorkSha256": curator_work_sha256,
                "terminalHumanOutcomeCount": terminal_count,
                "explicitCuratorDispositionCount": explicit_disposition_count,
                "acceptedAmongTerminalOutcomeRate": (
                    accepted_count / terminal_count if terminal_count else None
                ),
                "outcomeCounts": outcome_counts,
                "interpretation": (
                    "Presence under the deterministic resource id proves candidate-to-final "
                    "linkage and takes precedence over an older Curator state. Curator optional "
                    "outcomes are used only when explicitly recorded. Absence from the supplied "
                    "package remains pending unless Curator records a terminal outcome."
                ),
            }
        )
    report_hash = sha256_json(report)
    now = datetime.now(timezone.utc).isoformat()
    with store.connect() as connection:
        existing = connection.execute(
            """SELECT report_json, report_sha256
               FROM optimization_package_outcomes
               WHERE run_id = ? AND final_package_sha256 = ?
                 AND curator_work_sha256 = ?""",
            (run_id, package.sha256, curator_work_sha256),
        ).fetchone()
        if existing:
            if existing["report_sha256"] != report_hash or json.loads(
                existing["report_json"]
            ) != report:
                raise OptimizationOutcomeError(
                    "A different outcome report already exists for this run and package"
                )
        else:
            connection.execute(
                """INSERT INTO optimization_package_outcomes (
                       run_id, created_at, final_package_sha256, curator_work_sha256,
                       report_json, report_sha256
                   ) VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    run_id,
                    now,
                    package.sha256,
                    curator_work_sha256,
                    canonical_json(report),
                    report_hash,
                ),
            )
    return OptimizationPackageOutcome(
        run_id=run_id,
        final_package_sha256=package.sha256,
        report_sha256=report_hash,
        candidate_count=len(outcomes),
        accepted_count=accepted_count,
        not_present_count=len(outcomes) - accepted_count,
        report=report,
    )
