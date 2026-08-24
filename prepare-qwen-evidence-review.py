#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from resource_research_agent.optimization_review import (
    _write_json,
    apply_evidence_preparation_manifest,
)


parser = argparse.ArgumentParser(
    description="Apply an exact evidence-preparation manifest to a Qwen identity review"
)
parser.add_argument("--cache", type=Path, required=True)
parser.add_argument("--review", type=Path, required=True)
parser.add_argument("--manifest", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
arguments = parser.parse_args()

cache = json.loads(arguments.cache.read_text(encoding="utf-8"))
review = json.loads(arguments.review.read_text(encoding="utf-8"))
manifest = json.loads(arguments.manifest.read_text(encoding="utf-8"))
prepared = apply_evidence_preparation_manifest(cache, review, manifest)
_write_json(arguments.output, prepared)
print(
    json.dumps(
        {
            "output": str(arguments.output),
            "evidencePreparationPolicyVersion": prepared[
                "evidencePreparationPolicyVersion"
            ],
            "application": prepared["reviewApplications"][-1],
        },
        indent=2,
    )
)
