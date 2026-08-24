#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from resource_research_agent.prior_lead_harvest import harvest_routed_stage_leads


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


parser = argparse.ArgumentParser(
    description="Export one discovery run's routed identities as non-candidate lead hints"
)
parser.add_argument("--database", type=Path, required=True)
parser.add_argument("--source-run-id", type=int, required=True)
parser.add_argument("--target-stage-key", required=True)
parser.add_argument("--manifest-id", required=True)
parser.add_argument("--output", type=Path, required=True)
arguments = parser.parse_args()

manifest = harvest_routed_stage_leads(
    arguments.database,
    source_run_id=arguments.source_run_id,
    target_stage_key=arguments.target_stage_key,
    manifest_id=arguments.manifest_id,
    created_at=datetime.now(timezone.utc).isoformat(),
    database_sha256=file_sha256(arguments.database),
)
arguments.output.parent.mkdir(parents=True, exist_ok=True)
arguments.output.write_text(
    json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
print(
    json.dumps(
        {
            "leadCount": len(manifest["leads"]),
            "manifestSha256": manifest["manifestSha256"],
            "output": str(arguments.output),
        },
        indent=2,
        sort_keys=True,
    )
)
