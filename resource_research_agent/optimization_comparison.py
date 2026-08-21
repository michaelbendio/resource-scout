from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .optimization import canonical_json, sha256_json
from .storage import ResearchStore


class OptimizationComparisonError(RuntimeError):
    pass


@dataclass(frozen=True)
class ModelNeutralComparison:
    comparison_id: int
    corpus_id: int
    labels: dict[str, int]
    report: dict[str, Any]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run_record(store: ResearchStore, run_id: int) -> dict[str, Any]:
    with store.connect() as connection:
        row = connection.execute(
            """SELECT run.*, configuration.quantization
               FROM optimization_runs AS run
               JOIN optimization_configurations AS configuration
                 ON configuration.id = run.configuration_id
               WHERE run.id = ?""",
            (run_id,),
        ).fetchone()
    if not row:
        raise OptimizationComparisonError(f"Optimization run {run_id} does not exist")
    return dict(row)


def _packet_fingerprint(store: ResearchStore, corpus_id: int) -> list[tuple[str, str]]:
    with store.connect() as connection:
        rows = connection.execute(
            """SELECT identity_key, packet_sha256
               FROM optimization_evidence_packets
               WHERE corpus_id = ? ORDER BY identity_key""",
            (corpus_id,),
        ).fetchall()
    return [(str(row["identity_key"]), str(row["packet_sha256"])) for row in rows]


def _quality_metrics(store: ResearchStore, run_id: int) -> dict[str, Any]:
    with store.connect() as connection:
        rows = connection.execute(
            """SELECT verification.status, verification.verified_dossier_json,
                      verification.findings_json, packet.packet_json
               FROM optimization_verifications AS verification
               JOIN optimization_candidate_dossiers AS dossier
                 ON dossier.id = verification.dossier_id
               JOIN optimization_evidence_packets AS packet
                 ON packet.id = dossier.packet_id
               WHERE dossier.run_id = ? ORDER BY packet.identity_key""",
            (run_id,),
        ).fetchall()
    field_states = {"supported": 0, "conflicting": 0, "unknown": 0}
    source_ids: set[str] = set()
    source_domains: set[str] = set()
    authority_counts: dict[str, int] = {}
    finding_codes: dict[str, int] = {}
    passed = 0
    failed = 0
    usable = 0
    for row in rows:
        dossier = json.loads(row["verified_dossier_json"])
        packet = json.loads(row["packet_json"])
        if row["status"] == "passed":
            passed += 1
        else:
            failed += 1
        supported_here = 0
        for finding in dossier.get("fields", {}).values():
            if not isinstance(finding, dict):
                continue
            state = finding.get("status")
            if state in field_states:
                field_states[state] += 1
            if state == "supported":
                supported_here += 1
        if row["status"] == "passed" and dossier.get("sources") and supported_here:
            usable += 1
        findings = json.loads(row["findings_json"] or "{}")
        for finding in findings.get("finalDeterministicFindings", []):
            if isinstance(finding, dict):
                code = str(finding.get("code") or "unspecified")
                finding_codes[code] = finding_codes.get(code, 0) + 1
        for source in packet.get("sources", []):
            if not isinstance(source, dict):
                continue
            source_ids.add(str(source.get("id") or source.get("canonical_url") or ""))
            url = str(source.get("canonical_url") or "")
            domain = url.split("/", 3)[2].casefold() if "://" in url else ""
            if domain:
                source_domains.add(domain)
            authority = str(source.get("authority") or "unknown")
            authority_counts[authority] = authority_counts.get(authority, 0) + 1
    return {
        "priority1Accuracy": {
            "passedCandidates": passed,
            "failedCandidates": failed,
            "remainingDeterministicFindings": finding_codes,
            "gatePassed": failed == 0 and not finding_codes,
        },
        "priority2Completeness": {
            "fieldStates": field_states,
            "explicitFieldStateTotal": sum(field_states.values()),
        },
        "priority3Sources": {
            "frozenSourceCount": len(source_ids),
            "uniqueDomainCount": len(source_domains),
            "authorityCounts": dict(sorted(authority_counts.items())),
        },
        "priority4Candidates": {
            "verifiedCandidateCount": passed,
            "usableCandidateCount": usable,
        },
    }


def _quality_vector(metrics: dict[str, Any]) -> tuple[int, ...]:
    accuracy = metrics["priority1Accuracy"]
    completeness = metrics["priority2Completeness"]["fieldStates"]
    sources = metrics["priority3Sources"]
    candidates = metrics["priority4Candidates"]
    return (
        int(bool(accuracy["gatePassed"])),
        -int(accuracy["failedCandidates"]),
        -sum(int(value) for value in accuracy["remainingDeterministicFindings"].values()),
        int(completeness["supported"]),
        int(completeness["conflicting"]),
        -int(completeness["unknown"]),
        int(sources["frozenSourceCount"]),
        int(sources["uniqueDomainCount"]),
        int(candidates["usableCandidateCount"]),
        int(candidates["verifiedCandidateCount"]),
    )


def create_model_neutral_comparison(
    store: ResearchStore,
    *,
    label: str,
    four_bit_run_id: int,
    eight_bit_run_id: int,
) -> ModelNeutralComparison:
    four = _run_record(store, four_bit_run_id)
    eight = _run_record(store, eight_bit_run_id)
    if four["quantization"] != "4-bit" or eight["quantization"] != "8-bit":
        raise OptimizationComparisonError("Comparison inputs must be 4-bit and 8-bit runs")
    if four["status"] != "completed" or eight["status"] != "completed":
        raise OptimizationComparisonError("Both model evaluations must be completed")
    if four["corpus_id"] is None or four["corpus_id"] != eight["corpus_id"]:
        raise OptimizationComparisonError("Model evaluations do not share one frozen corpus")
    corpus_id = int(four["corpus_id"])
    fingerprint = _packet_fingerprint(store, corpus_id)
    if not fingerprint:
        raise OptimizationComparisonError("Frozen corpus has no evidence packets")
    # The label assignment is stable, opaque, and unrelated to run order or speed.
    swap = hashlib.sha256(f"{label}:{sha256_json(fingerprint)}".encode()).digest()[0] & 1
    labels = (
        {"A": eight_bit_run_id, "B": four_bit_run_id}
        if swap
        else {"A": four_bit_run_id, "B": eight_bit_run_id}
    )
    metrics_by_run = {
        four_bit_run_id: _quality_metrics(store, four_bit_run_id),
        eight_bit_run_id: _quality_metrics(store, eight_bit_run_id),
    }
    options = {key: metrics_by_run[run_id] for key, run_id in labels.items()}
    vectors = {key: _quality_vector(value) for key, value in options.items()}
    quality_winner = "tie" if vectors["A"] == vectors["B"] else max(vectors, key=vectors.get)
    report = {
        "schemaVersion": 1,
        "corpusPacketCount": len(fingerprint),
        "corpusPacketsSha256": sha256_json(fingerprint),
        "identicalFrozenPackets": True,
        "timingConcealed": True,
        "modelIdentityConcealed": True,
        "priorityOrder": ["accuracy", "completeness", "sources", "candidates"],
        "options": options,
        "qualityWinner": quality_winner,
    }
    with store.connect() as connection:
        existing = connection.execute(
            "SELECT * FROM optimization_comparisons WHERE label = ?", (label,)
        ).fetchone()
        if existing:
            if (
                int(existing["corpus_id"]) != corpus_id
                or int(existing["four_bit_run_id"]) != four_bit_run_id
                or int(existing["eight_bit_run_id"]) != eight_bit_run_id
            ):
                raise OptimizationComparisonError(
                    "Comparison label is already bound to different provenance"
                )
            comparison_id = int(existing["id"])
            persisted = json.loads(existing["priorities_one_through_four_json"])
            return ModelNeutralComparison(comparison_id, corpus_id, labels, persisted)
        comparison_id = int(
            connection.execute(
                """INSERT INTO optimization_comparisons (
                       created_at, label, corpus_id, four_bit_run_id, eight_bit_run_id,
                       status, priorities_one_through_four_json
                   ) VALUES (?, ?, ?, ?, ?, 'priorities-scored', ?)""",
                (
                    _now(), label, corpus_id, four_bit_run_id, eight_bit_run_id,
                    canonical_json(report),
                ),
            ).lastrowid
        )
    return ModelNeutralComparison(comparison_id, corpus_id, labels, report)


def reveal_timing_and_decide(store: ResearchStore, comparison_id: int) -> dict[str, Any]:
    with store.connect() as connection:
        row = connection.execute(
            "SELECT * FROM optimization_comparisons WHERE id = ?", (comparison_id,)
        ).fetchone()
    if not row:
        raise OptimizationComparisonError(f"Comparison {comparison_id} does not exist")
    if row["status"] not in {"priorities-scored", "revealed", "decided"}:
        raise OptimizationComparisonError("Quality priorities must be scored before timing is revealed")
    quality = json.loads(row["priorities_one_through_four_json"])
    run_ids = {
        "4-bit": int(row["four_bit_run_id"]),
        "8-bit": int(row["eight_bit_run_id"]),
    }
    timings: dict[str, Any] = {}
    for quantization, run_id in run_ids.items():
        run = _run_record(store, run_id)
        elapsed = None
        if run.get("started_at") and run.get("completed_at"):
            elapsed = (
                datetime.fromisoformat(run["completed_at"])
                - datetime.fromisoformat(run["started_at"])
            ).total_seconds()
        timings[quantization] = {"elapsedSeconds": elapsed}
    swap = hashlib.sha256(
        f"{row['label']}:{quality['corpusPacketsSha256']}".encode()
    ).digest()[0] & 1
    label_to_run = (
        {"A": run_ids["8-bit"], "B": run_ids["4-bit"]}
        if swap
        else {"A": run_ids["4-bit"], "B": run_ids["8-bit"]}
    )
    quality_winner = quality["qualityWinner"]
    if quality_winner == "tie":
        selected = "4-bit"
        rationale = "Priorities 1 through 4 are tied; the documented tie rule selects 4-bit."
    else:
        winning_run = label_to_run[quality_winner]
        selected = "4-bit" if winning_run == run_ids["4-bit"] else "8-bit"
        rationale = f"{selected} leads on the ordered quality priorities; time was not used."
    decision = {
        "selectedQuantization": selected,
        "qualityWinnerBeforeTiming": quality_winner,
        "rationale": rationale,
    }
    with store.connect() as connection:
        connection.execute(
            """UPDATE optimization_comparisons
               SET status = 'decided', timing_json = ?, decision_json = ? WHERE id = ?""",
            (canonical_json(timings), canonical_json(decision), comparison_id),
        )
    return {"quality": quality, "timing": timings, "decision": decision}
