#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from resource_research_agent.optimization_review import (
    _write_json,
    apply_identity_review_patch,
)


parser = argparse.ArgumentParser(
    description="Apply a labeled, replay-safe decision patch to a Qwen identity review"
)
parser.add_argument("--review", type=Path, required=True)
parser.add_argument("--patch", type=Path, required=True)
arguments = parser.parse_args()

review = json.loads(arguments.review.read_text(encoding="utf-8"))
patch = json.loads(arguments.patch.read_text(encoding="utf-8"))
updated = apply_identity_review_patch(review, patch)
_write_json(arguments.review, updated)
print(
    json.dumps(
        {
            "review": str(arguments.review),
            "application": updated.get("reviewApplications", [])[-1],
        },
        indent=2,
    )
)
