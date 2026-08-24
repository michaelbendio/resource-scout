from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from .optimization import (
    CANDIDATE_ROLES,
    COUNTABLE_CANDIDATE_ROLES,
    SOURCE_AUTHORITIES,
    sha256_json,
    validate_query_plan,
)
from .playbooks import PLAYBOOK_LIBRARY_DIR, CategoryPlaybook


PLAYBOOK_AUDIT_SCHEMA_VERSION = 2
PLAYBOOK_AUDIT_POLICY_VERSION = "optimization-playbook-audit-v2"
PLAYBOOK_AUDIT_POLICIES = {
    1: "optimization-playbook-audit-v1",
    2: PLAYBOOK_AUDIT_POLICY_VERSION,
}


def _text(value: Any, field: str) -> str:
    result = " ".join(str(value or "").split())
    if not result:
        raise ValueError(f"Optimization playbook audit field {field} must not be blank")
    return result


def _text_list(value: Any, field: str, *, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list) or (not value and not allow_empty):
        suffix = "an array" if allow_empty else "a non-empty array"
        raise ValueError(f"Optimization playbook audit field {field} must be {suffix}")
    result = [_text(item, field) for item in value]
    if len(set(result)) != len(result):
        raise ValueError(f"Optimization playbook audit field {field} has duplicates")
    return result


def _sha256(value: Any, field: str) -> str:
    result = _text(value, field)
    if not re.fullmatch(r"[0-9a-f]{64}", result):
        raise ValueError(f"Optimization playbook audit field {field} must be SHA-256")
    return result


def _optional_sha256(value: Any, field: str) -> str | None:
    if value is None or str(value).strip().casefold() in {"", "none"}:
        return None
    return _sha256(value, field)


def _coverage_needs(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value:
        raise ValueError("Optimization playbook audit needs requiredCoverageNeeds")
    result = []
    keys: set[str] = set()
    for item in value:
        if not isinstance(item, dict):
            raise ValueError("Optimization required coverage need must be an object")
        key = _text(item.get("key"), "requiredCoverageNeeds.key")
        if key in keys:
            raise ValueError("Optimization required coverage need keys must be unique")
        keys.add(key)
        normalized: dict[str, Any] = {
            "key": key,
            "label": _text(item.get("label"), "requiredCoverageNeeds.label"),
            "query": _text(item.get("query"), "requiredCoverageNeeds.query"),
        }
        any_tags = item.get("satisfiedByAnyTags")
        all_tags = item.get("satisfiedByAllTags")
        if any_tags is not None and all_tags is not None:
            raise ValueError(
                "Optimization required coverage need cannot combine any-tag and all-tag matching"
            )
        if any_tags is not None:
            normalized["satisfiedByAnyTags"] = _text_list(
                any_tags, "requiredCoverageNeeds.satisfiedByAnyTags"
            )
        if all_tags is not None:
            normalized["satisfiedByAllTags"] = _text_list(
                all_tags, "requiredCoverageNeeds.satisfiedByAllTags"
            )
        if "candidateGap" in item:
            if not isinstance(item["candidateGap"], bool):
                raise ValueError(
                    "Optimization required coverage need candidateGap must be boolean"
                )
            normalized["candidateGap"] = item["candidateGap"]
        result.append(normalized)
    return result


def playbook_source_receipt(playbook: CategoryPlaybook) -> dict[str, str]:
    base_path = PLAYBOOK_LIBRARY_DIR / "base.json"
    category_path = PLAYBOOK_LIBRARY_DIR / playbook.source
    return {
        "libraryVersion": playbook.library_version,
        "baseSource": base_path.name,
        "baseSourceSha256": sha256_json(
            json.loads(base_path.read_text(encoding="utf-8"))
        ),
        "categorySource": category_path.name,
        "categorySourceSha256": sha256_json(
            json.loads(category_path.read_text(encoding="utf-8"))
        ),
    }


def coverage_plan_sha256(
    query_plan: dict[str, Any], coverage_branch_keys: list[str]
) -> str:
    selected = set(coverage_branch_keys)
    return sha256_json(
        {
            "candidateQualificationPolicyVersion": query_plan.get(
                "candidateQualificationPolicyVersion"
            ),
            "categoryId": query_plan.get("categoryId"),
            "stageKey": query_plan.get("stageKey"),
            "targetLocation": query_plan.get("targetLocation"),
            "regionalScope": query_plan.get("regionalScope"),
            "branches": [
                deepcopy(branch)
                for branch in query_plan["branches"]
                if branch.get("key") in selected
            ],
        }
    )


def normalize_optimization_playbook_audit(
    value: dict[str, Any],
    *,
    query_plan: dict[str, Any],
    playbook: CategoryPlaybook,
    referral_graph_sha256: str | None = None,
    referral_review_sha256: str | None = None,
) -> dict[str, Any]:
    if (
        not isinstance(value, dict)
        or value.get("schemaVersion") not in PLAYBOOK_AUDIT_POLICIES
    ):
        raise ValueError("Optimization playbook audit schemaVersion must be 1 or 2")
    schema_version = int(value["schemaVersion"])
    policy_version = PLAYBOOK_AUDIT_POLICIES[schema_version]
    if value.get("policyVersion") != policy_version:
        raise ValueError(
            "Optimization playbook audit policyVersion must be "
            f"{policy_version}"
        )
    validate_query_plan(query_plan)
    referral_graph_sha256 = _optional_sha256(
        referral_graph_sha256,
        "referralGraphSha256",
    )
    referral_review_sha256 = _optional_sha256(
        referral_review_sha256,
        "referralReviewSha256",
    )
    if bool(referral_graph_sha256) != bool(referral_review_sha256):
        raise ValueError("Referral graph and review hashes must be supplied together")

    category_id = _text(value.get("categoryId"), "categoryId")
    stage_key = _text(value.get("stageKey"), "stageKey")
    target_location = _text(value.get("targetLocation"), "targetLocation")
    regional_scope = _text(value.get("regionalScope"), "regionalScope")
    if category_id != playbook.category_id or category_id != query_plan.get("categoryId"):
        raise ValueError("Optimization playbook audit belongs to another category")
    if stage_key != query_plan.get("stageKey") or stage_key not in {
        stage["key"] for stage in playbook.stages
    }:
        raise ValueError("Optimization playbook audit belongs to another stage")
    if target_location.casefold() != str(query_plan.get("targetLocation") or "").casefold():
        raise ValueError("Optimization playbook audit belongs to another target location")
    if regional_scope.casefold() != str(query_plan.get("regionalScope") or "").casefold():
        raise ValueError("Optimization playbook audit has another regional scope")

    receipt = playbook_source_receipt(playbook)
    supplied_receipt = value.get("playbook")
    if supplied_receipt != receipt:
        raise ValueError("Optimization playbook audit playbook receipt is stale")

    coverage_branch_keys = _text_list(
        value.get("coverageBranchKeys"), "coverageBranchKeys"
    )
    operational_branch_keys = _text_list(
        value.get("operationalBranchKeys"),
        "operationalBranchKeys",
        allow_empty=True,
    )
    if set(coverage_branch_keys) & set(operational_branch_keys):
        raise ValueError("Optimization playbook audit branch classes overlap")
    plan_branches = {
        str(branch.get("key") or ""): branch for branch in query_plan["branches"]
    }
    if set(coverage_branch_keys) | set(operational_branch_keys) != set(plan_branches):
        raise ValueError("Optimization playbook audit must classify every query branch")
    if any(not plan_branches[key].get("required") for key in coverage_branch_keys):
        raise ValueError("Optimization playbook audit coverage branches must be required")
    coverage_sha256 = _sha256(
        value.get("coveragePlanSha256"), "coveragePlanSha256"
    )
    if coverage_sha256 != coverage_plan_sha256(query_plan, coverage_branch_keys):
        raise ValueError("Optimization playbook audit belongs to another coverage plan")

    role_policy = value.get("candidateRolePolicy")
    if not isinstance(role_policy, dict):
        raise ValueError("Optimization playbook audit needs candidateRolePolicy")
    eligible_roles = _text_list(role_policy.get("eligible"), "candidateRolePolicy.eligible")
    preserved_roles = _text_list(
        role_policy.get("preservedNoncandidate"),
        "candidateRolePolicy.preservedNoncandidate",
    )
    if set(eligible_roles) != COUNTABLE_CANDIDATE_ROLES:
        raise ValueError("Optimization playbook audit has the wrong eligible roles")
    if set(preserved_roles) != CANDIDATE_ROLES - COUNTABLE_CANDIDATE_ROLES:
        raise ValueError("Optimization playbook audit has the wrong noncandidate roles")

    required_fields = _text_list(
        value.get("requiredFactualFields"), "requiredFactualFields"
    )
    supplementary_fields = _text_list(
        value.get("supplementaryFields"), "supplementaryFields"
    )
    access_critical_fields = _text_list(
        value.get("accessCriticalFields"), "accessCriticalFields"
    )
    expected_supplementary = set(playbook.supplementary_fields)
    expected_required = set(playbook.factual_fields) - expected_supplementary
    if set(required_fields) != expected_required:
        raise ValueError("Optimization playbook audit factual-field contract is stale")
    if set(supplementary_fields) != expected_supplementary:
        raise ValueError("Optimization playbook audit supplementary-field contract is stale")
    if not set(access_critical_fields) <= expected_required:
        raise ValueError("Access-critical fields must be required factual fields")

    source_families_value = value.get("authoritativeSourceFamilies")
    if not isinstance(source_families_value, list) or not source_families_value:
        raise ValueError("Optimization playbook audit needs authoritativeSourceFamilies")
    source_families = []
    source_keys: set[str] = set()
    authorities: set[str] = set()
    for item in source_families_value:
        if not isinstance(item, dict):
            raise ValueError("Optimization source family must be an object")
        key = _text(item.get("key"), "authoritativeSourceFamilies.key")
        authority = _text(
            item.get("authority"), "authoritativeSourceFamilies.authority"
        )
        if key in source_keys:
            raise ValueError("Optimization source family keys must be unique")
        if authority not in SOURCE_AUTHORITIES:
            raise ValueError(f"Unsupported source authority: {authority}")
        source_keys.add(key)
        authorities.add(authority)
        source_families.append(
            {
                "key": key,
                "authority": authority,
                "use": _text(item.get("use"), "authoritativeSourceFamilies.use"),
            }
        )
    if not {"direct-provider", "government-referral"} <= authorities:
        raise ValueError("Optimization audit needs direct and government source families")

    components = value.get("corpusComponents")
    if not isinstance(components, dict):
        raise ValueError("Optimization playbook audit needs corpusComponents")
    if schema_version == 1:
        normalized_components = {
            "referralGraphSha256": _sha256(
                components.get("referralGraphSha256"),
                "corpusComponents.referralGraphSha256",
            ),
            "referralReviewSha256": _sha256(
                components.get("referralReviewSha256"),
                "corpusComponents.referralReviewSha256",
            ),
        }
    else:
        normalized_components = {
            "referralGraphSha256": _optional_sha256(
                components.get("referralGraphSha256"),
                "corpusComponents.referralGraphSha256",
            ),
            "referralReviewSha256": _optional_sha256(
                components.get("referralReviewSha256"),
                "corpusComponents.referralReviewSha256",
            ),
        }
        if bool(normalized_components["referralGraphSha256"]) != bool(
            normalized_components["referralReviewSha256"]
        ):
            raise ValueError(
                "Optimization playbook audit referral components must appear together"
            )
    if (
        referral_graph_sha256
        and normalized_components["referralGraphSha256"] != referral_graph_sha256
    ):
        raise ValueError("Optimization playbook audit belongs to another referral graph")
    if (
        referral_review_sha256
        and normalized_components["referralReviewSha256"] != referral_review_sha256
    ):
        raise ValueError("Optimization playbook audit belongs to another referral review")

    normalized = {
        "schemaVersion": schema_version,
        "policyVersion": policy_version,
        "auditId": _text(value.get("auditId"), "auditId"),
        "categoryId": category_id,
        "stageKey": stage_key,
        "targetLocation": target_location,
        "regionalScope": regional_scope,
        "coveragePlanSha256": coverage_sha256,
        "playbook": receipt,
        "coverageBranchKeys": coverage_branch_keys,
        "operationalBranchKeys": operational_branch_keys,
        "serviceNeeds": _text_list(value.get("serviceNeeds"), "serviceNeeds"),
        "populations": _text_list(value.get("populations"), "populations"),
        "barriers": _text_list(value.get("barriers"), "barriers"),
        "authoritativeSourceFamilies": source_families,
        "geographyRules": _text_list(value.get("geographyRules"), "geographyRules"),
        "candidateRolePolicy": {
            "eligible": eligible_roles,
            "preservedNoncandidate": preserved_roles,
        },
        "requiredFactualFields": required_fields,
        "accessCriticalFields": access_critical_fields,
        "supplementaryFields": supplementary_fields,
        "requiredCoverageNeeds": _coverage_needs(
            value.get("requiredCoverageNeeds")
        ),
        "gapSearchTerms": _text_list(value.get("gapSearchTerms"), "gapSearchTerms"),
        "currentStatusSignals": _text_list(
            value.get("currentStatusSignals"), "currentStatusSignals"
        ),
        "corpusComponents": normalized_components,
        "reviewDecision": _text(value.get("reviewDecision"), "reviewDecision"),
    }
    normalized["auditSha256"] = sha256_json(normalized)
    supplied_hash = str(value.get("auditSha256") or "").strip()
    if supplied_hash and supplied_hash != normalized["auditSha256"]:
        raise ValueError("Optimization playbook audit SHA-256 does not match its content")
    return normalized
