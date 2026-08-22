#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from resource_research_agent.optimization_review import (
    _write_json,
    cache_housing_searches,
    identity_review_template,
    merge_identity_review,
)


parser = argparse.ArgumentParser(description="Cache the fixed Housing-stage DDGS ledger")
parser.add_argument("--cache", type=Path, required=True)
parser.add_argument("--review", type=Path, required=True)
parser.add_argument("--minimum-queries", type=int, default=2)
parser.add_argument("--maximum-queries", type=int, default=6)
parser.add_argument("--saturation-queries", type=int, default=2)
parser.add_argument("--results-per-query", type=int, default=8)
parser.add_argument("--previous-review", type=Path)
arguments = parser.parse_args()

cache = cache_housing_searches(
    arguments.cache,
    progress=lambda key: print(f"completed {key}", flush=True),
    minimum_queries=arguments.minimum_queries,
    maximum_queries=arguments.maximum_queries,
    saturation_queries=arguments.saturation_queries,
    results_per_query=arguments.results_per_query,
)
if arguments.previous_review:
    previous = json.loads(arguments.previous_review.read_text(encoding="utf-8"))
    review = merge_identity_review(cache, previous)
    _write_json(arguments.review, review)
elif arguments.review.exists():
    review = json.loads(arguments.review.read_text(encoding="utf-8"))
else:
    review = identity_review_template(cache)
    _write_json(arguments.review, review)
print(json.dumps({"queryCount": len(cache["queries"]), "reviewCount": len(review["decisions"])}, indent=2))
