#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from copy import deepcopy
from pathlib import Path

from resource_research_agent.importer import (
    ResourcePackageImporter,
    resource_program_identity,
)
from resource_research_agent.optimization import sha256_json, validate_query_plan
from resource_research_agent.optimization_pipeline import OptimizationDiscoveryPipeline
from resource_research_agent.optimization_review import (
    CachedSearchClient,
    reviewed_identity_decisions,
    validate_identity_review,
)
from resource_research_agent.optimization_runtime import ReviewedIdentityResolver, SafeFetchClient
from resource_research_agent.optimization_playbook_audit import (
    normalize_optimization_playbook_audit,
)
from resource_research_agent.playbooks import playbook_for
from resource_research_agent.referral_graph import (
    attach_referral_graph_to_query_plan,
    normalize_referral_graph,
)
from resource_research_agent.referral_review import (
    ReviewedReferralResolver,
    normalize_referral_review,
)
from resource_research_agent.storage import ResearchStore


parser = argparse.ArgumentParser(description="Freeze the reviewed first-stage Housing corpus")
parser.add_argument("--database", type=Path, required=True)
parser.add_argument("--package", type=Path, required=True)
parser.add_argument("--cache", type=Path, required=True)
parser.add_argument("--review", type=Path, required=True)
parser.add_argument("--playbook-audit", type=Path, required=True)
parser.add_argument("--referral-graph", type=Path)
parser.add_argument("--referral-review", type=Path)
arguments = parser.parse_args()

if bool(arguments.referral_graph) != bool(arguments.referral_review):
    raise SystemExit("--referral-graph and --referral-review must be supplied together")

cache = json.loads(arguments.cache.read_text(encoding="utf-8"))
review = json.loads(arguments.review.read_text(encoding="utf-8"))
validate_identity_review(cache, review)
package = ResourcePackageImporter("housing").read(arguments.package)
query_policy = cache.get("queryPolicy") or {
    "minimumQueries": 2,
    "maximumQueries": 6,
    "consecutiveNoNewIdentityQueries": 2,
    "resultsPerQuery": 8,
}
plan = deepcopy(cache.get("queryPlan"))
if not isinstance(plan, dict):
    raise SystemExit("Search cache lacks its exact query plan; rebuild the cache")
validate_query_plan(plan)
if sha256_json(plan) != cache.get("queryPlanSha256"):
    raise SystemExit("Search cache query-plan hash does not match its snapshot")
playbook = playbook_for("housing")
referral_graph = None
referral_review = None
if arguments.referral_graph:
    referral_graph = normalize_referral_graph(
        json.loads(arguments.referral_graph.read_text(encoding="utf-8"))
    )
    referral_review = normalize_referral_review(
        referral_graph,
        json.loads(arguments.referral_review.read_text(encoding="utf-8")),
    )
playbook_audit = normalize_optimization_playbook_audit(
    json.loads(arguments.playbook_audit.read_text(encoding="utf-8")),
    query_plan=plan,
    playbook=playbook,
    referral_graph_sha256=(
        referral_graph["graphSha256"] if referral_graph else None
    ),
    referral_review_sha256=(
        referral_review["reviewSha256"] if referral_review else None
    ),
)
if not referral_graph:
    raise SystemExit("The audited revised corpus requires its referral graph and review")
if (
    playbook_audit["corpusComponents"]["referralGraphSha256"]
    != referral_graph["graphSha256"]
    or playbook_audit["corpusComponents"]["referralReviewSha256"]
    != referral_review["reviewSha256"]
):
    raise SystemExit("Playbook audit referral components do not match the supplied files")
if referral_graph:
    plan = attach_referral_graph_to_query_plan(plan, referral_graph)
configuration = {
    "label": (
        "mesa-housing-urgent-reviewed-ddgs-v11"
        f"{'-referral' if referral_graph else ''}-2026-08-23-"
        f"{sha256_json(review)[:12]}"
    ),
    "modelArtifact": "none",
    "quantization": "none",
    "modelProvider": "none",
    "modelEndpoint": "none",
    "mlxVersion": "not-used",
    "dshVersion": "not-used",
    "searchProvider": "ddgs",
    "fetchProvider": "safe-http",
    "searchPluginVersion": "resource-scout-ddgs-v1",
    "fetchPluginVersion": "resource-scout-safe-http-v1",
    "promptPolicyVersion": "human-reviewed-identity-qualification-v2",
    "playbookVersion": playbook.library_version,
    "sourcePackageSha256": package.sha256,
    "sourcePackageVersion": str(package.schema.package_version),
    "targetLocation": "Mesa",
    "regionalScope": "Maricopa County and nearby areas",
    "targetCategoryId": "housing",
    "stageKey": "urgent-access",
    "limits": {
        "modelFallbacks": [],
        "searchFallbacks": [],
        "searchResultsPerQuery": int(query_policy["resultsPerQuery"]),
        "fetchMaxBytes": 500000,
        "evidenceExtractMaxChars": 30000,
        "searchCacheSha256": cache["cacheSha256"],
        "identityReviewSha256": sha256_json(review),
        "playbookAuditSha256": playbook_audit["auditSha256"],
        "playbookBaseSourceSha256": playbook_audit["playbook"][
            "baseSourceSha256"
        ],
        "playbookCategorySourceSha256": playbook_audit["playbook"][
            "categorySourceSha256"
        ],
        "referralEvidenceContextCharacters": 2000,
        "referralGraphSha256": (
            referral_graph["graphSha256"] if referral_graph else "none"
        ),
        "referralReviewSha256": (
            referral_review["reviewSha256"] if referral_review else "none"
        ),
    },
    "stoppingRules": {
        "minimumQueries": int(query_policy["minimumQueries"]),
        "maximumQueries": int(query_policy["maximumQueries"]),
        "consecutiveNoNewIdentityQueries": int(
            query_policy["consecutiveNoNewIdentityQueries"]
        ),
    },
    "queryPlan": plan,
}
existing = []
for resource in package.resources:
    organization, program = resource_program_identity(resource)
    existing.append(
        {
            "organization": organization,
            "program": program,
            "resourceId": resource.get("id"),
        }
    )
base_resolver = ReviewedIdentityResolver(reviewed_identity_decisions(review))
resolver = (
    ReviewedReferralResolver(referral_graph, referral_review, base_resolver)
    if referral_graph and referral_review
    else base_resolver
)
result = OptimizationDiscoveryPipeline(
    ResearchStore(arguments.database, recover_interrupted=True),
    configuration,
    search=CachedSearchClient(cache),
    fetch=SafeFetchClient(),
    resolve_identity=resolver,
    existing_resources=existing,
    referral_graph=referral_graph,
    progress=lambda event: print(json.dumps(event, sort_keys=True), flush=True),
).run()
print(json.dumps(result.__dict__, indent=2, sort_keys=True))
