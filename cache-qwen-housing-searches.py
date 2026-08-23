#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from resource_research_agent.optimization_review import (
    build_reviewed_housing_query_plan,
    _write_json,
    cache_housing_searches,
    identity_review_template,
    merge_identity_review,
)
from resource_research_agent.query_expansion import augment_query_plan_with_targeted_branch
from resource_research_agent.prior_leads import augment_query_plan_with_prior_leads


parser = argparse.ArgumentParser(description="Cache the fixed Housing-stage DDGS ledger")
parser.add_argument("--cache", type=Path, required=True)
parser.add_argument("--review", type=Path, required=True)
parser.add_argument("--minimum-queries", type=int, default=2)
parser.add_argument("--maximum-queries", type=int, default=6)
parser.add_argument("--saturation-queries", type=int, default=2)
parser.add_argument("--results-per-query", type=int, default=8)
parser.add_argument("--previous-review", type=Path)
parser.add_argument("--candidate-status-review", type=Path)
parser.add_argument("--previous-cache", type=Path)
parser.add_argument("--targeted-expansion", type=Path)
parser.add_argument("--prior-lead-manifest", type=Path)
parser.add_argument(
    "--all-identity-status",
    action="store_true",
    help="Append status checks for identities routed to every playbook stage",
)
arguments = parser.parse_args()

candidate_status_review = (
    json.loads(arguments.candidate_status_review.read_text(encoding="utf-8"))
    if arguments.candidate_status_review
    else None
)
previous_cache = (
    json.loads(arguments.previous_cache.read_text(encoding="utf-8"))
    if arguments.previous_cache
    else None
)
query_plan = None
if arguments.targeted_expansion or arguments.prior_lead_manifest:
    query_plan = build_reviewed_housing_query_plan(
        minimum_queries=arguments.minimum_queries,
        maximum_queries=arguments.maximum_queries,
        saturation_queries=arguments.saturation_queries,
        candidate_status_review=candidate_status_review,
        include_routed_status=arguments.all_identity_status,
    )
if arguments.targeted_expansion:
    expansion = json.loads(arguments.targeted_expansion.read_text(encoding="utf-8"))
    query_plan = augment_query_plan_with_targeted_branch(
        query_plan,
        branch_key=str(expansion["branchKey"]),
        purpose=str(expansion["purpose"]),
        queries=expansion["queries"],
        parent_corpus_sha256=str(expansion["parentCorpusSha256"]),
        minimum_queries=int(expansion["saturation"]["minimumQueries"]),
        maximum_queries=int(expansion["saturation"]["maximumQueries"]),
        saturation_queries=int(
            expansion["saturation"]["consecutiveNoNewIdentityQueries"]
        ),
    )
if arguments.prior_lead_manifest:
    prior_manifest = json.loads(
        arguments.prior_lead_manifest.read_text(encoding="utf-8")
    )
    query_plan = augment_query_plan_with_prior_leads(query_plan, prior_manifest)

cache = cache_housing_searches(
    arguments.cache,
    progress=lambda key: print(f"completed {key}", flush=True),
    minimum_queries=arguments.minimum_queries,
    maximum_queries=arguments.maximum_queries,
    saturation_queries=arguments.saturation_queries,
    results_per_query=arguments.results_per_query,
    candidate_status_review=candidate_status_review,
    include_routed_status=arguments.all_identity_status,
    previous_cache=previous_cache,
    query_plan=query_plan,
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
