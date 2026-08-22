from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .optimization import (
    augment_housing_query_plan_with_status_checks,
    build_housing_urgent_query_plan,
    sha256_json,
)
from .optimization_pipeline import canonicalize_discovery_url
from .optimization_runtime import DDGSSearchClient, OptimizationRuntimeError


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def cache_housing_searches(
    path: Path,
    *,
    search: Callable[[str, int], list[dict[str, Any]]] | None = None,
    progress: Callable[[str], None] | None = None,
    minimum_queries: int = 2,
    maximum_queries: int = 6,
    saturation_queries: int = 2,
    results_per_query: int = 8,
    candidate_status_review: dict[str, Any] | None = None,
    previous_cache: dict[str, Any] | None = None,
) -> dict[str, Any]:
    plan = build_housing_urgent_query_plan(
        "Mesa",
        "Maricopa County and nearby areas",
        minimum_queries=minimum_queries,
        maximum_queries=maximum_queries,
        saturation_queries=saturation_queries,
    )
    if candidate_status_review is not None:
        identity_values: list[dict[str, Any]] = []
        for value in reviewed_identity_decisions(candidate_status_review).values():
            identity_values.extend(value if isinstance(value, list) else [value])
        plan = augment_housing_query_plan_with_status_checks(plan, identity_values)
    plan_hash = sha256_json(plan)
    if path.exists():
        value = json.loads(path.read_text(encoding="utf-8"))
        if value.get("queryPlanSha256") != plan_hash:
            raise OptimizationRuntimeError("Search cache belongs to a different query plan")
    else:
        value = {
            "schemaVersion": 1,
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "provider": "ddgs",
            "queryPlanSha256": plan_hash,
            "queryPolicy": {
                "minimumQueries": minimum_queries,
                "maximumQueries": maximum_queries,
                "consecutiveNoNewIdentityQueries": saturation_queries,
                "resultsPerQuery": results_per_query,
            },
            "queries": {},
        }
        if previous_cache is not None:
            prior_queries = previous_cache.get("queries", {})
            if not isinstance(prior_queries, dict):
                raise OptimizationRuntimeError("Previous search cache has no queries object")
            planned = {
                query["key"]: (branch["key"], query["query"])
                for branch in plan["branches"]
                for query in branch["queries"]
            }
            for key, (branch_key, query_text) in planned.items():
                prior = prior_queries.get(key)
                if not isinstance(prior, dict) or prior.get("query") != query_text:
                    continue
                carried = deepcopy(prior)
                carried["branchKey"] = branch_key
                value["queries"][key] = carried
            value["previousCacheSha256"] = previous_cache.get("cacheSha256") or sha256_json(
                prior_queries
            )
    provider = search or DDGSSearchClient()
    notify = progress or (lambda _message: None)
    for branch in plan["branches"]:
        for query in branch["queries"]:
            key = query["key"]
            if key in value["queries"]:
                continue
            sources = provider(query["query"], results_per_query)
            value["queries"][key] = {
                "branchKey": branch["key"],
                "query": query["query"],
                "sources": sources,
            }
            _write_json(path, value)
            notify(key)
    value["completedAt"] = datetime.now(timezone.utc).isoformat()
    value["cacheSha256"] = sha256_json(value["queries"])
    _write_json(path, value)
    return value


def identity_review_template(cache: dict[str, Any]) -> dict[str, Any]:
    records: dict[str, dict[str, Any]] = {}
    for key, query in cache.get("queries", {}).items():
        if not isinstance(query, dict):
            continue
        for source in query.get("sources", []):
            if not isinstance(source, dict):
                continue
            try:
                url = canonicalize_discovery_url(source.get("url"))
            except ValueError:
                continue
            record = records.setdefault(
                url,
                {
                    "disposition": "pending",
                    "reason": "",
                    "title": str(source.get("title") or ""),
                    "snippet": str(source.get("snippet") or ""),
                    "queryKeys": [],
                    "identity": None,
                },
            )
            if key not in record["queryKeys"]:
                record["queryKeys"].append(key)
    return {
        "schemaVersion": 1,
        "searchCacheSha256": cache.get("cacheSha256") or sha256_json(cache.get("queries", {})),
        "decisions": dict(sorted(records.items())),
    }


def merge_identity_review(
    cache: dict[str, Any], previous_review: dict[str, Any]
) -> dict[str, Any]:
    """Carry completed URL decisions into a new ledger without stale query metadata."""

    merged = identity_review_template(cache)
    previous_decisions = previous_review.get("decisions", {})
    if not isinstance(previous_decisions, dict):
        return merged
    for url, record in merged["decisions"].items():
        previous = previous_decisions.get(url)
        if not isinstance(previous, dict) or previous.get("disposition") not in {
            "candidate",
            "excluded",
        }:
            continue
        for key in ("disposition", "reason", "identity", "identities"):
            if key in previous:
                record[key] = json.loads(json.dumps(previous[key], ensure_ascii=False))
        if "identities" in record:
            record.pop("identity", None)
    return merged


def apply_identity_review_patch(
    review: dict[str, Any], patch: dict[str, Any]
) -> dict[str, Any]:
    """Apply a labeled, replay-safe set of human identity-review decisions."""

    decisions = review.get("decisions")
    if not isinstance(decisions, dict):
        raise OptimizationRuntimeError("Identity review has no decisions object")
    label = str(patch.get("label") or "").strip()
    patch_decisions = patch.get("decisions")
    if not label or not isinstance(patch_decisions, dict) or not patch_decisions:
        raise OptimizationRuntimeError(
            "Identity review patch needs a label and non-empty decisions object"
        )
    expected_cache = str(review.get("searchCacheSha256") or "")
    patch_cache = str(patch.get("searchCacheSha256") or "")
    if patch_cache and patch_cache != expected_cache:
        raise OptimizationRuntimeError("Identity review patch belongs to a different search cache")

    patch_digest = sha256_json(
        {
            "label": label,
            "searchCacheSha256": expected_cache,
            "decisions": patch_decisions,
        }
    )
    applications = review.get("reviewApplications", [])
    if applications is None:
        applications = []
    if not isinstance(applications, list):
        raise OptimizationRuntimeError("Identity review applications must be an array")
    if any(
        isinstance(application, dict)
        and application.get("patchSha256") == patch_digest
        for application in applications
    ):
        return deepcopy(review)

    result = deepcopy(review)
    for url, decision_patch in patch_decisions.items():
        if url not in decisions:
            raise OptimizationRuntimeError(f"Identity review patch URL was not discovered: {url}")
        if not isinstance(decision_patch, dict):
            raise OptimizationRuntimeError(f"Identity review patch decision is invalid: {url}")
        disposition = decision_patch.get("disposition")
        reason = str(decision_patch.get("reason") or "").strip()
        if disposition not in {"candidate", "excluded"} or not reason:
            raise OptimizationRuntimeError(
                f"Identity review patch decision needs a disposition and reason: {url}"
            )
        identity_value = decision_patch.get("identities", decision_patch.get("identity"))
        if disposition == "candidate":
            identities = (
                [identity_value]
                if isinstance(identity_value, dict)
                else identity_value
                if isinstance(identity_value, list)
                else []
            )
            if not identities or any(not isinstance(identity, dict) for identity in identities):
                raise OptimizationRuntimeError(
                    f"Candidate identity-review patch lacks an identity: {url}"
                )
            for identity in identities:
                if not str(identity.get("organization") or "").strip() or not str(
                    identity.get("program") or ""
                ).strip():
                    raise OptimizationRuntimeError(
                        f"Candidate identity-review patch is incomplete: {url}"
                    )
        elif identity_value is not None:
            raise OptimizationRuntimeError(
                f"Excluded identity-review patch must not contain an identity: {url}"
            )

        record = result["decisions"][url]
        record["disposition"] = disposition
        record["reason"] = reason
        record.pop("identity", None)
        record.pop("identities", None)
        if disposition == "candidate":
            key = "identities" if isinstance(identity_value, list) else "identity"
            record[key] = deepcopy(identity_value)

    result.setdefault("reviewApplications", []).append(
        {
            "label": label,
            "patchSha256": patch_digest,
            "decisionCount": len(patch_decisions),
        }
    )
    return result


def validate_identity_review(cache: dict[str, Any], review: dict[str, Any]) -> None:
    expected = cache.get("cacheSha256") or sha256_json(cache.get("queries", {}))
    if review.get("searchCacheSha256") != expected:
        raise OptimizationRuntimeError("Identity review belongs to a different search cache")
    decisions = review.get("decisions")
    if not isinstance(decisions, dict):
        raise OptimizationRuntimeError("Identity review has no decisions object")
    template = identity_review_template(cache)["decisions"]
    missing = sorted(set(template) - set(decisions))
    if missing:
        raise OptimizationRuntimeError(f"Identity review is missing {len(missing)} discovered URLs")
    for url in template:
        decision = decisions.get(url)
        if not isinstance(decision, dict):
            raise OptimizationRuntimeError(f"Identity review decision is invalid for {url}")
        disposition = decision.get("disposition")
        reason = str(decision.get("reason") or "").strip()
        if disposition == "excluded":
            if not reason:
                raise OptimizationRuntimeError(f"Excluded URL lacks a reason: {url}")
            continue
        if disposition != "candidate":
            raise OptimizationRuntimeError(f"Identity review is still pending for {url}")
        identity_value = decision.get("identities", decision.get("identity"))
        identities = (
            [identity_value]
            if isinstance(identity_value, dict)
            else identity_value
            if isinstance(identity_value, list)
            else []
        )
        if not identities or any(not isinstance(identity, dict) for identity in identities):
            raise OptimizationRuntimeError(f"Candidate URL lacks an identity: {url}")
        for identity in identities:
            if not str(identity.get("organization") or "").strip() or not str(
                identity.get("program") or ""
            ).strip():
                raise OptimizationRuntimeError(f"Candidate identity is incomplete: {url}")
            if "evidenceExcerpt" in identity and not str(
                identity.get("evidenceExcerpt") or ""
            ).strip():
                raise OptimizationRuntimeError(
                    f"Candidate evidence excerpt is blank: {url}"
                )


def reviewed_identity_decisions(
    review: dict[str, Any],
) -> dict[str, dict[str, Any] | list[dict[str, Any]]]:
    result = {}
    for url, record in review.get("decisions", {}).items():
        if isinstance(record, dict) and record.get("disposition") == "candidate":
            identity_value = record.get("identities", record.get("identity"))
            if isinstance(identity_value, dict):
                result[url] = identity_value
            elif isinstance(identity_value, list) and all(
                isinstance(identity, dict) for identity in identity_value
            ):
                result[url] = identity_value
    return result


class CachedSearchClient:
    def __init__(self, cache: dict[str, Any]) -> None:
        self.by_query = {
            str(record.get("query") or ""): record.get("sources", [])
            for record in cache.get("queries", {}).values()
            if isinstance(record, dict)
        }

    def __call__(self, query: str, max_results: int) -> list[dict[str, Any]]:
        if query not in self.by_query:
            raise OptimizationRuntimeError(f"Fixed search cache has no entry for query: {query}")
        sources = self.by_query[query]
        if not isinstance(sources, list):
            raise OptimizationRuntimeError("Fixed search cache contains an invalid source list")
        return [dict(source) for source in sources[:max_results] if isinstance(source, dict)]
