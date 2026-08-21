#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from resource_research_agent.optimization_review import (
    _write_json,
    cache_housing_searches,
    identity_review_template,
)


parser = argparse.ArgumentParser(description="Cache the fixed Housing-stage DDGS ledger")
parser.add_argument("--cache", type=Path, required=True)
parser.add_argument("--review", type=Path, required=True)
arguments = parser.parse_args()

cache = cache_housing_searches(
    arguments.cache,
    progress=lambda key: print(f"completed {key}", flush=True),
)
if arguments.review.exists():
    review = json.loads(arguments.review.read_text(encoding="utf-8"))
else:
    review = identity_review_template(cache)
    _write_json(arguments.review, review)
print(json.dumps({"queryCount": len(cache["queries"]), "reviewCount": len(review["decisions"])}, indent=2))
