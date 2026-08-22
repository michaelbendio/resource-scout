#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from resource_research_agent.review_export import build_optimization_review_copy
from resource_research_agent.storage import ResearchStore


parser = argparse.ArgumentParser(
    description="Export one completed Qwen optimization run as an isolated Resource Curator"
)
parser.add_argument("--database", type=Path, required=True)
parser.add_argument("--run-id", type=int, required=True)
parser.add_argument("--output", type=Path, required=True)
arguments = parser.parse_args()

review = build_optimization_review_copy(
    ResearchStore(arguments.database), arguments.run_id
)
output = arguments.output
if output.exists() and output.is_dir():
    output = output / review.filename
elif not output.suffix:
    output.mkdir(parents=True, exist_ok=True)
    output = output / review.filename
else:
    output.parent.mkdir(parents=True, exist_ok=True)
output.write_bytes(review.html)
print(output.resolve())
