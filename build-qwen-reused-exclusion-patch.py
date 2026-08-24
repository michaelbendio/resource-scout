#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from resource_research_agent.optimization_review import (
    _write_json,
    build_exact_reused_exclusion_patch,
)


parser = argparse.ArgumentParser(
    description="Build an exact-result exclusion patch from a previous reviewed ledger"
)
parser.add_argument("--review", type=Path, required=True)
parser.add_argument("--previous-review", type=Path, required=True)
parser.add_argument("--label", required=True)
parser.add_argument("--output", type=Path, required=True)
arguments = parser.parse_args()

review = json.loads(arguments.review.read_text(encoding="utf-8"))
previous_review = json.loads(arguments.previous_review.read_text(encoding="utf-8"))
patch = build_exact_reused_exclusion_patch(
    review,
    previous_review,
    label=arguments.label,
)
_write_json(arguments.output, patch)
print(
    json.dumps(
        {
            "decisionCount": len(patch["decisions"]),
            "matchPolicy": patch["matchPolicy"],
            "previousReviewSha256": patch["previousReviewSha256"],
        },
        indent=2,
        sort_keys=True,
    )
)
