from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .importer import ResourcePackageImporter, resource_id
from .optimization import canonical_json, optimization_resource_id, sha256_json
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


def _candidate_field(value: Any) -> Any:
    if isinstance(value, str):
        return value.strip()
    return value


def compare_optimization_run_to_package(
    store: ResearchStore,
    run_id: int,
    package_path: str | Path,
) -> OptimizationPackageOutcome:
    """Link verified candidates to phone-vetted resources by stable resource id."""

    with store.connect() as connection:
        run = connection.execute(
            """SELECT run.status, run.configuration_id, run.corpus_id,
                      configuration.configuration_hash,
                      configuration.source_package_sha256,
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

    package = ResourcePackageImporter("housing").read(package_path)
    final_resources = {resource_id(resource): resource for resource in package.resources}
    expected_ids: set[str] = set()
    outcomes = []
    for row in rows:
        packet_id = int(row["packet_id"])
        linked_resource_id = optimization_resource_id(
            str(run["configuration_hash"]), packet_id
        )
        expected_ids.add(linked_resource_id)
        dossier = json.loads(row["verified_dossier_json"])
        identity = dossier.get("candidateIdentity", {})
        fields = dossier.get("fields", {})
        final_resource = final_resources.get(linked_resource_id)
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
        outcomes.append(
            {
                "packetId": packet_id,
                "identityKey": row["identity_key"],
                "organization": identity.get("organization"),
                "program": identity.get("program"),
                "verificationStatus": row["status"],
                "verifiedDossierSha256": row["verified_dossier_sha256"],
                "resourceId": linked_resource_id,
                "outcome": "present-in-vetted-package" if final_resource else "not-present",
                "fieldChanges": field_changes,
            }
        )
    accepted_count = sum(
        outcome["outcome"] == "present-in-vetted-package" for outcome in outcomes
    )
    unlinked_ids = sorted(set(final_resources) - expected_ids)
    report = {
        "schemaVersion": 1,
        "runId": run_id,
        "configurationId": int(run["configuration_id"]),
        "configurationHash": run["configuration_hash"],
        "corpusId": int(run["corpus_id"]),
        "corpusSha256": run["corpus_sha256"],
        "sourcePackageSha256": run["source_package_sha256"],
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
    report_hash = sha256_json(report)
    now = datetime.now(timezone.utc).isoformat()
    with store.connect() as connection:
        existing = connection.execute(
            """SELECT report_json, report_sha256
               FROM optimization_package_outcomes
               WHERE run_id = ? AND final_package_sha256 = ?""",
            (run_id, package.sha256),
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
                       run_id, created_at, final_package_sha256,
                       report_json, report_sha256
                   ) VALUES (?, ?, ?, ?, ?)""",
                (run_id, now, package.sha256, canonical_json(report), report_hash),
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
