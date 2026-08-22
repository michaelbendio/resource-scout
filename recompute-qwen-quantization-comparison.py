#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from resource_research_agent.optimization_comparison import (
    create_model_neutral_comparison,
    reveal_timing_and_decide,
)
from resource_research_agent.optimization_models import recompute_model_evaluation_audits
from resource_research_agent.storage import ResearchStore


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


parser = argparse.ArgumentParser(
    description="Recompute a Qwen comparison from completed persisted model runs"
)
parser.add_argument("--database", type=Path, required=True)
parser.add_argument("--four-bit-run-id", type=int, required=True)
parser.add_argument("--eight-bit-run-id", type=int, required=True)
parser.add_argument("--label", required=True)
parser.add_argument("--artifacts", type=Path, required=True)
arguments = parser.parse_args()

os.environ.pop("DEEPSEEK_API_KEY", None)
store = ResearchStore(arguments.database)
recompute_model_evaluation_audits(store, arguments.four_bit_run_id)
recompute_model_evaluation_audits(store, arguments.eight_bit_run_id)
comparison = create_model_neutral_comparison(
    store,
    label=arguments.label,
    four_bit_run_id=arguments.four_bit_run_id,
    eight_bit_run_id=arguments.eight_bit_run_id,
)
write_json(arguments.artifacts / "model-neutral-quality-report.json", comparison.report)
revealed = reveal_timing_and_decide(store, comparison.comparison_id)
write_json(arguments.artifacts / "quantization-decision.json", revealed)
write_json(
    arguments.artifacts / "comparison-status.json",
    {
        "comparisonId": comparison.comparison_id,
        "decision": revealed["decision"],
        "deepSeekKeyPresent": False,
        "phase": "completed",
        "recomputedFromPersistedRuns": {
            "4-bit": arguments.four_bit_run_id,
            "8-bit": arguments.eight_bit_run_id,
        },
        "updatedAt": datetime.now(timezone.utc).isoformat(),
    },
)
