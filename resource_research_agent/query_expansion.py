from __future__ import annotations

from copy import deepcopy
from string import hexdigits
from typing import Any, Iterable

from .optimization import branch_stop_state, validate_query_plan


TARGETED_QUERY_EXPANSION_POLICY_VERSION = "targeted-saturation-branch-v1"


def augment_query_plan_with_targeted_branch(
    plan: dict[str, Any],
    *,
    branch_key: str,
    purpose: str,
    queries: Iterable[dict[str, Any]],
    parent_corpus_sha256: str,
    minimum_queries: int = 3,
    maximum_queries: int = 5,
    saturation_queries: int = 3,
) -> dict[str, Any]:
    """Append a bounded category-neutral branch to an immutable base plan."""

    clean_key = str(branch_key or "").strip()
    clean_purpose = " ".join(str(purpose or "").split())
    if not clean_key or not clean_purpose:
        raise ValueError("Targeted query expansion needs a branch key and purpose")
    if len(parent_corpus_sha256) != 64 or any(
        character not in hexdigits for character in parent_corpus_sha256
    ):
        raise ValueError("Targeted query expansion needs a parent corpus SHA-256")
    branch_stop_state(
        [],
        minimum_queries=minimum_queries,
        maximum_queries=maximum_queries,
        saturation_queries=saturation_queries,
    )
    if maximum_queries > 20:
        raise ValueError("A targeted query expansion supports at most 20 queries")
    values = list(deepcopy(tuple(queries)))
    if len(values) != maximum_queries:
        raise ValueError("Targeted expansion must persist exactly maximumQueries queries")
    normalized = []
    seen_keys = set()
    seen_queries = set()
    for position, value in enumerate(values, start=1):
        if not isinstance(value, dict):
            raise ValueError("Targeted expansion query must be an object")
        key = str(value.get("key") or "").strip()
        query = " ".join(str(value.get("query") or "").split())
        query_purpose = " ".join(
            str(value.get("purpose") or clean_purpose).split()
        )
        if not key or not query or not query_purpose:
            raise ValueError("Targeted expansion query is incomplete")
        if key in seen_keys or query.casefold() in seen_queries:
            raise ValueError("Targeted expansion queries must be unique")
        seen_keys.add(key)
        seen_queries.add(query.casefold())
        normalized.append(
            {
                "key": key,
                "position": position,
                "purpose": query_purpose,
                "query": query,
                **(
                    {"referralSourceKey": str(value["referralSourceKey"])}
                    if value.get("referralSourceKey")
                    else {}
                ),
            }
        )
    result = deepcopy(plan)
    if any(branch.get("key") == clean_key for branch in result["branches"]):
        raise ValueError(f"Query plan already contains branch {clean_key}")
    result["branches"].append(
        {
            "key": clean_key,
            "purpose": clean_purpose,
            "required": True,
            "saturation": {
                "minimumQueries": minimum_queries,
                "maximumQueries": maximum_queries,
                "consecutiveNoNewIdentityQueries": saturation_queries,
                "noveltyUnit": "currently qualified package-eligible identity",
            },
            "queries": normalized,
        }
    )
    result["schemaVersion"] = max(7, int(result.get("schemaVersion") or 0))
    result["targetedExpansionPolicyVersion"] = (
        TARGETED_QUERY_EXPANSION_POLICY_VERSION
    )
    result["parentCorpusSha256"] = parent_corpus_sha256
    validate_query_plan(result)
    return result
