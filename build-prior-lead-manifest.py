#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from resource_research_agent.prior_lead_harvest import harvest_prior_leads


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


parser = argparse.ArgumentParser(
    description="Build a names-and-URLs-only prior-result lead manifest"
)
parser.add_argument("--database", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
parser.add_argument("--manifest-id", required=True)
parser.add_argument("--category-id", required=True)
parser.add_argument("--target-location", required=True)
parser.add_argument(
    "--created-at",
    default=datetime.now(timezone.utc).isoformat(),
    help="Manifest creation timestamp; pin this for a reproducible preserved harvest",
)
parser.add_argument(
    "--research-run",
    action="append",
    default=[],
    metavar="ID:KIND",
    help="Historical research run and explicit source kind; repeat as needed",
)
parser.add_argument(
    "--optimization-discovery-run",
    action="append",
    type=int,
    default=[],
    help="Historical optimization discovery run id; repeat as needed",
)
arguments = parser.parse_args()

research_runs = []
for value in arguments.research_run:
    run_id, separator, kind = value.partition(":")
    if not separator or not run_id.isdigit() or not kind.strip():
        parser.error("--research-run must use ID:KIND")
    research_runs.append((int(run_id), kind.strip()))
if not research_runs and not arguments.optimization_discovery_run:
    parser.error("At least one historical run is required")

manifest = harvest_prior_leads(
    arguments.database,
    manifest_id=arguments.manifest_id,
    category_id=arguments.category_id,
    target_location=arguments.target_location,
    created_at=arguments.created_at,
    database_sha256=file_sha256(arguments.database),
    research_runs=research_runs,
    optimization_discovery_run_ids=arguments.optimization_discovery_run,
)
write_json(arguments.output, manifest)
print(
    json.dumps(
        {
            "output": str(arguments.output),
            "leadCount": len(manifest["leads"]),
            "sourceCount": len(manifest["sources"]),
            "manifestSha256": manifest["manifestSha256"],
        },
        indent=2,
        sort_keys=True,
    )
)
