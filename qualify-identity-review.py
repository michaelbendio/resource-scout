#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from resource_research_agent.identity_qualification import (
    apply_identity_qualification_manifest,
    identity_qualification_template,
)
from resource_research_agent.optimization_review import _write_json


parser = argparse.ArgumentParser(
    description="Build or apply a category-neutral identity qualification manifest"
)
parser.add_argument("--review", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
parser.add_argument("--manifest", type=Path)
arguments = parser.parse_args()

review = json.loads(arguments.review.read_text(encoding="utf-8"))
if arguments.manifest:
    manifest = json.loads(arguments.manifest.read_text(encoding="utf-8"))
    value = apply_identity_qualification_manifest(review, manifest)
else:
    value = identity_qualification_template(review)
_write_json(arguments.output, value)
print(
    json.dumps(
        {
            "mode": "apply" if arguments.manifest else "template",
            "identityCount": len(manifest["identities"])
            if arguments.manifest
            else len(value["identities"]),
            "output": str(arguments.output),
        },
        indent=2,
    )
)
