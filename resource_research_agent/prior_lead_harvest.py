from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Iterable

from .optimization import candidate_identity_key, canonicalize_discovery_url
from .prior_leads import build_prior_lead_manifest


DISPOSITION_PRIORITY = {
    "candidate": 6,
    "routed": 5,
    "needs-review": 4,
    "excluded-existing": 3,
    "rejected": 2,
    "unresolved": 1,
}


def _urls(values: Iterable[Any]) -> list[str]:
    result = set()
    for value in values:
        try:
            result.add(canonicalize_discovery_url(value))
        except ValueError:
            continue
    return sorted(result)


def _candidate_urls(candidate: dict[str, Any]) -> list[str]:
    values = [candidate.get("website"), candidate.get("url")]
    evidence = candidate.get("evidence")
    if isinstance(evidence, list):
        values.extend(
            item.get("url") for item in evidence if isinstance(item, dict)
        )
    return _urls(values)


def _merge_lead(
    records: dict[str, dict[str, Any]],
    *,
    organization: str = "",
    program: str = "",
    aliases: Iterable[str] = (),
    urls: Iterable[str] = (),
    disposition: str,
    provenance: dict[str, str],
) -> None:
    clean_organization = " ".join(str(organization or "").split())
    clean_program = " ".join(str(program or "").split())
    clean_aliases = sorted(
        {" ".join(str(alias or "").split()) for alias in aliases if str(alias or "").strip()}
    )
    clean_urls = _urls(urls)
    if clean_organization and clean_program:
        key = f"identity:{candidate_identity_key(clean_organization, clean_program)}"
    elif clean_urls:
        key = f"url:{clean_urls[0]}"
    elif clean_aliases:
        key = f"alias:{clean_aliases[0].casefold()}"
    else:
        return
    record = records.setdefault(
        key,
        {
            "organization": clean_organization,
            "program": clean_program,
            "aliases": [],
            "urls": [],
            "historicalDisposition": disposition,
            "provenance": [],
        },
    )
    record["aliases"] = sorted(set(record["aliases"]) | set(clean_aliases))
    record["urls"] = sorted(set(record["urls"]) | set(clean_urls))
    if DISPOSITION_PRIORITY[disposition] > DISPOSITION_PRIORITY[
        record["historicalDisposition"]
    ]:
        record["historicalDisposition"] = disposition
    provenance_record = {**provenance, "historicalDisposition": disposition}
    if provenance_record not in record["provenance"]:
        record["provenance"].append(provenance_record)


def harvest_prior_leads(
    database: Path,
    *,
    manifest_id: str,
    category_id: str,
    target_location: str,
    created_at: str,
    database_sha256: str,
    research_runs: Iterable[tuple[int, str]],
    optimization_discovery_run_ids: Iterable[int],
) -> dict[str, Any]:
    """Harvest historical identity hints without copying service facts."""

    connection = sqlite3.connect(database)
    connection.row_factory = sqlite3.Row
    sources: dict[str, dict[str, Any]] = {}
    records: dict[str, dict[str, Any]] = {}
    try:
        for run_id, kind in research_runs:
            run = connection.execute(
                """SELECT id, target_category_id, target_location, created_at,
                          completed_at, status
                   FROM research_runs WHERE id = ?""",
                (run_id,),
            ).fetchone()
            if not run:
                raise ValueError(f"Historical research run {run_id} was not found")
            if str(run["target_category_id"]) != category_id:
                raise ValueError(f"Historical research run {run_id} has another category")
            discoveries = connection.execute(
                """SELECT discovery.created_at, discovery.candidate_json,
                          COALESCE(stage.stage_key, 'unknown-stage') AS stage_key
                   FROM discoveries AS discovery
                   LEFT JOIN research_run_stages AS stage ON stage.id = discovery.stage_id
                   WHERE discovery.run_id = ? ORDER BY discovery.id""",
                (run_id,),
            ).fetchall()
            for discovery in discoveries:
                candidate = json.loads(discovery["candidate_json"])
                if not isinstance(candidate, dict):
                    continue
                stage_key = str(discovery["stage_key"])
                source_id = f"research-{kind}-run-{run_id}-stage-{stage_key}"
                observed_at = str(
                    run["completed_at"] or discovery["created_at"] or run["created_at"]
                )
                sources[source_id] = {
                    "id": source_id,
                    "kind": kind,
                    "sourceRunId": str(run_id),
                    "sourceStageKey": stage_key,
                    "observedAt": observed_at,
                    "artifactSha256": database_sha256,
                }
                name = " ".join(str(candidate.get("name") or "").split())
                organization = " ".join(
                    str(candidate.get("organization") or name).split()
                )
                program = " ".join(str(candidate.get("program") or name).split())
                aliases = [name] if name and name not in {organization, program} else []
                _merge_lead(
                    records,
                    organization=organization,
                    program=program,
                    aliases=aliases,
                    urls=_candidate_urls(candidate),
                    disposition="candidate",
                    provenance={
                        "sourceId": source_id,
                        "sourceRunId": str(run_id),
                        "sourceStageKey": stage_key,
                        "observedAt": observed_at,
                    },
                )

        for run_id in optimization_discovery_run_ids:
            run = connection.execute(
                """SELECT run.id, run.label, run.created_at, run.completed_at,
                          configuration.target_category_id, configuration.stage_key
                   FROM optimization_runs AS run
                   JOIN optimization_configurations AS configuration
                     ON configuration.id = run.configuration_id
                   WHERE run.id = ? AND run.run_kind = 'discovery'""",
                (run_id,),
            ).fetchone()
            if not run:
                raise ValueError(
                    f"Historical optimization discovery run {run_id} was not found"
                )
            if str(run["target_category_id"]) != category_id:
                raise ValueError(
                    f"Historical optimization run {run_id} has another category"
                )
            stage_key = str(run["stage_key"])
            source_id = f"optimization-qwen-run-{run_id}-stage-{stage_key}"
            observed_at = str(run["completed_at"] or run["created_at"])
            sources[source_id] = {
                "id": source_id,
                "kind": "qwen-optimization",
                "sourceRunId": str(run_id),
                "sourceStageKey": stage_key,
                "observedAt": observed_at,
                "artifactSha256": database_sha256,
            }
            identities = connection.execute(
                """SELECT identity.*
                   FROM optimization_candidate_identities AS identity
                   WHERE identity.run_id = ? ORDER BY identity.identity_key""",
                (run_id,),
            ).fetchall()
            for identity in identities:
                identity_leads = connection.execute(
                    """SELECT lead.canonical_url, lead.title
                       FROM optimization_identity_leads AS link
                       JOIN optimization_discovery_leads AS lead ON lead.id = link.lead_id
                       WHERE link.identity_id = ? ORDER BY lead.id""",
                    (identity["id"],),
                ).fetchall()
                disposition = (
                    "excluded-existing"
                    if identity["boundary_state"] == "excluded-existing"
                    else "routed"
                    if identity["target_stage_key"] != stage_key
                    else "candidate"
                    if identity["boundary_state"] == "resolved"
                    else "needs-review"
                )
                _merge_lead(
                    records,
                    organization=str(identity["organization"]),
                    program=str(identity["program"]),
                    aliases=[str(lead["title"] or "") for lead in identity_leads],
                    urls=[str(lead["canonical_url"] or "") for lead in identity_leads],
                    disposition=disposition,
                    provenance={
                        "sourceId": source_id,
                        "sourceRunId": str(run_id),
                        "sourceStageKey": str(identity["target_stage_key"] or stage_key),
                        "observedAt": observed_at,
                    },
                )
            unlinked = connection.execute(
                """SELECT lead.* FROM optimization_discovery_leads AS lead
                   LEFT JOIN optimization_identity_leads AS link ON link.lead_id = lead.id
                   WHERE lead.run_id = ? AND link.lead_id IS NULL ORDER BY lead.id""",
                (run_id,),
            ).fetchall()
            for lead in unlinked:
                disposition = (
                    "rejected"
                    if lead["fetch_status"] in {"rejected", "not-selected"}
                    else "unresolved"
                )
                _merge_lead(
                    records,
                    aliases=[str(lead["title"] or "")],
                    urls=[str(lead["canonical_url"] or "")],
                    disposition=disposition,
                    provenance={
                        "sourceId": source_id,
                        "sourceRunId": str(run_id),
                        "sourceStageKey": stage_key,
                        "observedAt": observed_at,
                    },
                )
    finally:
        connection.close()
    if not records:
        raise ValueError("Historical lead harvest produced no leads")
    return build_prior_lead_manifest(
        manifest_id=manifest_id,
        category_id=category_id,
        target_location=target_location,
        created_at=created_at,
        sources=sources.values(),
        leads=records.values(),
    )
