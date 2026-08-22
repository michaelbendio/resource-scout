#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from resource_research_agent.optimization_review import (
    _write_json,
    build_identity_review_exclusion_patch,
)


parser = argparse.ArgumentParser(
    description="Build an exact-URL Qwen review patch from explicit exclusion rules"
)
parser.add_argument("--review", type=Path, required=True)
parser.add_argument("--policy", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
arguments = parser.parse_args()

review = json.loads(arguments.review.read_text(encoding="utf-8"))
policy = json.loads(arguments.policy.read_text(encoding="utf-8"))
patch = build_identity_review_exclusion_patch(review, policy)
_write_json(arguments.output, patch)
print(json.dumps({"decisionCount": len(patch["decisions"]), **patch["ruleCounts"]}, indent=2))
