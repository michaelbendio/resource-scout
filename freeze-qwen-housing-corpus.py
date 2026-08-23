#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from copy import deepcopy
from pathlib import Path

from resource_research_agent.importer import ResourcePackageImporter
from resource_research_agent.optimization import sha256_json, validate_query_plan
from resource_research_agent.optimization_pipeline import OptimizationDiscoveryPipeline
from resource_research_agent.optimization_review import (
    CachedSearchClient,
    reviewed_identity_decisions,
    validate_identity_review,
)
from resource_research_agent.optimization_runtime import ReviewedIdentityResolver, SafeFetchClient
from resource_research_agent.playbooks import playbook_for
from resource_research_agent.storage import ResearchStore


parser = argparse.ArgumentParser(description="Freeze the reviewed first-stage Housing corpus")
parser.add_argument("--database", type=Path, required=True)
parser.add_argument("--package", type=Path, required=True)
parser.add_argument("--cache", type=Path, required=True)
parser.add_argument("--review", type=Path, required=True)
arguments = parser.parse_args()

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
configuration = {
    "label": (
        "mesa-housing-urgent-reviewed-ddgs-v10-qualified-2026-08-23-"
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
    "playbookVersion": playbook.version,
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
        "referralEvidenceContextCharacters": 2000,
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
    name = str(resource.get("name") or resource.get("title") or "").strip()
    organization = str(resource.get("organization") or resource.get("provider") or name).strip()
    program = str(resource.get("program") or name).strip()
    existing.append(
        {
            "organization": organization,
            "program": program,
            "resourceId": resource.get("id"),
        }
    )
result = OptimizationDiscoveryPipeline(
    ResearchStore(arguments.database, recover_interrupted=True),
    configuration,
    search=CachedSearchClient(cache),
    fetch=SafeFetchClient(),
    resolve_identity=ReviewedIdentityResolver(reviewed_identity_decisions(review)),
    existing_resources=existing,
    progress=lambda event: print(json.dumps(event, sort_keys=True), flush=True),
).run()
print(json.dumps(result.__dict__, indent=2, sort_keys=True))
