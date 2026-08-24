#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from resource_research_agent.optimization_models import (
    VERIFICATION_DERIVATION_POLICY_VERSION,
    recompute_persisted_verifications,
)
from resource_research_agent.storage import ResearchStore


parser = argparse.ArgumentParser(
    description=(
        "Recompute derived verification status from persisted dossiers and completed "
        "verifier outputs without search, fetching, or model inference."
    )
)
parser.add_argument("--database", required=True)
parser.add_argument("--run-id", type=int, required=True)
parser.add_argument("--report")
arguments = parser.parse_args()

database_path = Path(arguments.database).expanduser().resolve()
if not database_path.is_file():
    raise SystemExit(f"Benchmark database does not exist: {database_path}")

result = recompute_persisted_verifications(
    ResearchStore(database_path),
    arguments.run_id,
    policy_version=VERIFICATION_DERIVATION_POLICY_VERSION,
)
report = {
    "schemaVersion": 1,
    "runId": result.run_id,
    "policyVersion": result.policy_version,
    "revisionId": result.revision_id,
    "sourceSnapshotSha256": result.source_snapshot_sha256,
    "derivedSnapshotSha256": result.derived_snapshot_sha256,
    "before": result.before,
    "after": result.after,
    "modelInferenceCalls": result.model_inference_calls,
    "searchCalls": 0,
    "fetchCalls": 0,
}
rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
if arguments.report:
    report_path = Path(arguments.report).expanduser().resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(rendered, encoding="utf-8")
print(rendered, end="")
