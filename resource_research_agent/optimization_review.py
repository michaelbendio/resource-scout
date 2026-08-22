from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .optimization import build_housing_urgent_query_plan, sha256_json
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
) -> dict[str, Any]:
    plan = build_housing_urgent_query_plan(
        "Mesa",
        "Maricopa County and nearby areas",
        minimum_queries=minimum_queries,
        maximum_queries=maximum_queries,
        saturation_queries=saturation_queries,
    )
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
