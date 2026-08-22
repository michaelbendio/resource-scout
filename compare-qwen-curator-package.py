#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from resource_research_agent.optimization_outcomes import (
    compare_optimization_run_to_package,
)
from resource_research_agent.storage import ResearchStore


parser = argparse.ArgumentParser(
    description="Compare a completed Qwen run with a phone-vetted Curator package"
)
parser.add_argument("--database", type=Path, required=True)
parser.add_argument("--run-id", type=int, required=True)
parser.add_argument("--package", type=Path, required=True)
parser.add_argument("--report", type=Path)
arguments = parser.parse_args()

outcome = compare_optimization_run_to_package(
    ResearchStore(arguments.database), arguments.run_id, arguments.package
)
rendered = json.dumps(outcome.report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
if arguments.report:
    arguments.report.parent.mkdir(parents=True, exist_ok=True)
    arguments.report.write_text(rendered, encoding="utf-8")
print(rendered, end="")
