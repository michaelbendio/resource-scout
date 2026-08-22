from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from copy import deepcopy
from typing import Any, Iterable
from urllib.parse import urlsplit


CONFIGURATION_FIELDS = (
    "modelArtifact",
    "quantization",
    "modelProvider",
    "modelEndpoint",
    "mlxVersion",
    "dshVersion",
    "searchProvider",
    "fetchProvider",
    "searchPluginVersion",
    "fetchPluginVersion",
    "promptPolicyVersion",
    "playbookVersion",
    "sourcePackageSha256",
    "sourcePackageVersion",
    "targetLocation",
    "regionalScope",
    "targetCategoryId",
    "stageKey",
    "limits",
    "stoppingRules",
    "queryPlan",
)

HOUSING_FACTUAL_FIELDS = (
    "name",
    "organization",
    "program",
    "website",
    "address",
    "additionalAddresses",
    "phone",
    "additionalPhoneNumbers",
    "hours",
    "geography",
    "resourceType",
    "serviceNeed",
    "accessTimeline",
    "description",
    "servicesProvided",
    "eligibility",
    "whatToExpect",
    "howToBestConnect",
    "additionalNotes",
    "barriers",
    "availability",
    "petPolicy",
    "experienceAssessment",
)

FIELD_STATES = {"supported", "conflicting", "unknown"}
SOURCE_AUTHORITIES = {
    "direct-provider",
    "government-referral",
    "reputable-secondary",
    "directory-lead",
}
LEAD_ONLY_SENSITIVE_FIELDS = {
    "address",
    "additionalAddresses",
    "phone",
    "additionalPhoneNumbers",
    "hours",
    "geography",
    "eligibility",
    "whatToExpect",
    "howToBestConnect",
    "barriers",
    "availability",
    "petPolicy",
}


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _identity_part(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", str(value or "")).casefold()
    return " ".join(re.findall(r"[a-z0-9]+", normalized))


def organization_key(organization: str) -> str:
    key = _identity_part(organization)
    if not key:
        raise ValueError("Candidate organization must not be blank")
    return key


def candidate_identity_key(organization: str, program: str) -> str:
    organization_part = organization_key(organization)
    program_part = _identity_part(program)
    if not program_part:
        raise ValueError("Candidate program must not be blank")
    return f"{organization_part}::{program_part}"


def package_exclusion_state(
    candidate_organization: str,
    candidate_program: str,
    existing_organization: str,
    existing_program: str,
) -> str:
    candidate_key = candidate_identity_key(candidate_organization, candidate_program)
    existing_key = candidate_identity_key(existing_organization, existing_program)
    if candidate_key == existing_key:
        return "same-program"
    if organization_key(candidate_organization) == organization_key(existing_organization):
        return "different-program"
    return "not-matched"


def configuration_snapshot(value: dict[str, Any]) -> dict[str, Any]:
    missing = [field for field in ("label", *CONFIGURATION_FIELDS) if field not in value]
    if missing:
        raise ValueError(f"Optimization configuration is missing: {', '.join(missing)}")
    label = str(value["label"] or "").strip()
    if not label:
        raise ValueError("Optimization configuration label must not be blank")
    snapshot = {field: deepcopy(value[field]) for field in CONFIGURATION_FIELDS}
    for field in CONFIGURATION_FIELDS[:-3]:
        if isinstance(snapshot[field], str) and not snapshot[field].strip():
            raise ValueError(f"Optimization configuration field {field} must not be blank")
    if snapshot["quantization"] not in {"4-bit", "8-bit", "none"}:
        raise ValueError("Optimization quantization must be 4-bit, 8-bit, or none")
    if snapshot["searchProvider"] != "ddgs":
        raise ValueError("Optimization search provider must be the unmetered DDGS provider")
    if snapshot["fetchProvider"] != "safe-http":
        raise ValueError("Optimization fetch provider must be the safe local fetcher")
    if not isinstance(snapshot["limits"], dict) or not snapshot["limits"]:
        raise ValueError("Optimization limits must be a non-empty object")
    if not isinstance(snapshot["stoppingRules"], dict) or not snapshot["stoppingRules"]:
        raise ValueError("Optimization stoppingRules must be a non-empty object")
    if snapshot["limits"].get("modelFallbacks") or snapshot["limits"].get("searchFallbacks"):
        raise ValueError("Optimization configuration must not contain provider fallbacks")
    if snapshot["quantization"] == "none":
        if snapshot["modelProvider"] != "none" or snapshot["modelArtifact"] != "none":
            raise ValueError("A model-free discovery configuration must use the none provider and artifact")
    else:
        endpoint = urlsplit(snapshot["modelEndpoint"])
        if endpoint.scheme != "http" or endpoint.hostname not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("Optimization model endpoint must be loopback HTTP")
        if snapshot["modelProvider"] != "qwen-local":
            raise ValueError("Optimization model provider must be qwen-local")
        artifact = str(snapshot["modelArtifact"]).casefold()
        if not artifact.endswith(snapshot["quantization"].replace("-", "")):
            raise ValueError("Model artifact and quantization do not agree")
    package_hash = str(snapshot["sourcePackageSha256"])
    if not re.fullmatch(r"[0-9a-f]{64}", package_hash):
        raise ValueError("sourcePackageSha256 must be a lowercase SHA-256 digest")
    validate_query_plan(snapshot["queryPlan"])
    return {
        "label": label,
        "configurationHash": sha256_json(snapshot),
        "snapshot": snapshot,
    }


def branch_stop_state(
    new_identity_counts: Iterable[int],
    *,
    minimum_queries: int,
    maximum_queries: int,
    saturation_queries: int,
) -> str:
    counts = list(new_identity_counts)
    if (
        any(
            not isinstance(value, int) or isinstance(value, bool)
            for value in (minimum_queries, maximum_queries, saturation_queries)
        )
        or minimum_queries <= 0
        or saturation_queries <= 0
        or maximum_queries < minimum_queries
    ):
        raise ValueError("Invalid deterministic saturation policy")
    if any(not isinstance(count, int) or isinstance(count, bool) or count < 0 for count in counts):
        raise ValueError("New identity counts must be non-negative integers")
    if len(counts) > maximum_queries:
        raise ValueError("Executed queries exceed the deterministic maximum")
    if len(counts) < minimum_queries:
        return "continue"
    if len(counts) >= maximum_queries:
        return "maximum-reached"
    if len(counts) >= saturation_queries and all(
        count == 0 for count in counts[-saturation_queries:]
    ):
        return "saturated"
    return "continue"


def coverage_branch_complete(branch: dict[str, Any]) -> bool:
    status = branch.get("status")
    if status in {"saturated", "maximum-reached"}:
        return True
    if status == "not-applicable":
        return bool(str(branch.get("notApplicableReason") or "").strip())
    return False


def validate_query_plan(plan: Any) -> None:
    if not isinstance(plan, dict) or not isinstance(plan.get("branches"), list):
        raise ValueError("Query plan must contain a branches array")
    branches = plan["branches"]
    if not branches:
        raise ValueError("Query plan must contain at least one coverage branch")
    keys: set[str] = set()
    for branch in branches:
        if not isinstance(branch, dict):
            raise ValueError("Each coverage branch must be an object")
        key = str(branch.get("key") or "").strip()
        purpose = str(branch.get("purpose") or "").strip()
        queries = branch.get("queries")
        if not key or not purpose or not isinstance(queries, list) or not queries:
            raise ValueError("Each coverage branch needs a key, purpose, and planned queries")
        if key in keys:
            raise ValueError(f"Duplicate coverage branch: {key}")
        keys.add(key)
        policy = branch.get("saturation")
        if not isinstance(policy, dict):
            raise ValueError(f"Coverage branch {key} lacks a saturation policy")
        minimum = policy.get("minimumQueries")
        maximum = policy.get("maximumQueries")
        saturation = policy.get("consecutiveNoNewIdentityQueries")
        branch_stop_state(
            [],
            minimum_queries=minimum,
            maximum_queries=maximum,
            saturation_queries=saturation,
        )
        if len(queries) != maximum:
            raise ValueError(
                f"Coverage branch {key} must persist exactly maximumQueries planned queries"
            )
        query_keys = [str(query.get("key") or "") for query in queries if isinstance(query, dict)]
        if len(query_keys) != len(queries) or any(not key for key in query_keys):
            raise ValueError(f"Coverage branch {key} has an invalid planned query")
        if len(set(query_keys)) != len(query_keys):
            raise ValueError(f"Coverage branch {key} has duplicate planned query keys")


def build_housing_urgent_query_plan(
    target_location: str,
    regional_scope: str,
) -> dict[str, Any]:
    location = " ".join(str(target_location or "").split())
    region = " ".join(str(regional_scope or "").split())
    if not location or not region:
        raise ValueError("Housing query planning requires a target location and regional scope")
    policy = {
        "minimumQueries": 2,
        "maximumQueries": 6,
        "consecutiveNoNewIdentityQueries": 2,
        "noveltyUnit": "package-eligible normalized organization-plus-program identity",
    }
    specifications = (
        (
            "official-city",
            "Find city-run access points, programs, funding, jurisdiction rules, and official referrals.",
            (
                f'site:mesaaz.gov "{location}" emergency shelter homeless',
                f'site:mesaaz.gov "{location}" housing crisis assistance',
                f'site:mesaaz.gov "{location}" motel voucher temporary lodging',
                f'site:mesaaz.gov "{location}" coordinated entry homeless',
                f'site:mesaaz.gov "{location}" family youth shelter',
                f'site:mesaaz.gov "{location}" pets shelter transportation homeless',
            ),
        ),
        (
            "official-county",
            "Find county programs and record whether their jurisdiction includes the target city.",
            (
                f'site:maricopa.gov "{location}" emergency housing',
                f'site:maricopa.gov "{location}" homeless shelter',
                f'site:maricopa.gov "{location}" coordinated entry',
                f'site:maricopa.gov "{location}" motel voucher',
                f'site:maricopa.gov "{location}" family shelter',
                f'site:maricopa.gov "{location}" housing authority service area',
            ),
        ),
        (
            "official-state",
            "Find state-administered programs and authoritative statewide referral paths serving the target.",
            (
                f'site:az.gov "{location}" emergency housing homeless',
                f'site:az.gov "{location}" shelter services',
                f'site:az.gov "{location}" domestic violence shelter housing',
                f'site:az.gov "{location}" youth shelter',
                f'site:az.gov "{location}" veteran emergency housing',
                f'site:az.gov "{location}" temporary lodging assistance',
            ),
        ),
        (
            "coordinated-entry-and-211",
            "Trace coordinated entry and authoritative referral results to specific named programs.",
            (
                f'211 Arizona "{location}" emergency shelter',
                f'"{location}" coordinated entry homeless access point',
                f'211 Arizona "{location}" family shelter',
                f'211 Arizona "{location}" domestic violence shelter',
                f'211 Arizona "{location}" youth shelter',
                f'211 Arizona "{location}" motel voucher',
            ),
        ),
        (
            "direct-providers",
            "Find direct providers and specific emergency programs with an actionable intake path.",
            (
                f'"{location}" emergency shelter intake',
                f'"{location}" homeless shelter program apply',
                f'"{location}" temporary housing direct provider',
                f'"{location}" emergency lodging homeless program',
                f'"{location}" shelter hotline intake hours',
                f'"{location}" crisis housing nonprofit',
            ),
        ),
        (
            "specialized-safety",
            "Cover domestic-violence, family, youth, medically vulnerable, and other specialized safety paths.",
            (
                f'"{location}" domestic violence emergency shelter',
                f'"{location}" family emergency shelter children',
                f'"{location}" youth emergency shelter',
                f'"{location}" medical respite homeless housing',
                f'"{location}" veteran emergency shelter',
                f'"{location}" disability accessible emergency housing',
            ),
        ),
        (
            "temporary-lodging",
            "Identify voucher issuers and the specific temporary lodging or bridge programs they use.",
            (
                f'"{location}" motel voucher homeless',
                f'"{location}" hotel voucher emergency housing',
                f'"{location}" emergency lodging voucher program',
                f'"{location}" bridge housing temporary lodging',
                f'"{location}" family motel assistance',
                f'"{location}" shelter overflow hotel program',
            ),
        ),
        (
            "regional-serving-target",
            "Find adjacent regional programs only when a source explicitly states that they serve the target.",
            (
                f'"serves {location}" emergency shelter',
                f'"{location} residents" homeless housing program',
                f'"{location}" "{region}" emergency housing',
                f'"{location}" regional shelter intake',
                f'"{location}" Phoenix shelter transportation',
                f'"{location}" East Valley emergency shelter',
            ),
        ),
        (
            "access-barriers",
            "Verify transportation, pet, documentation, family-composition, sobriety, and referral barriers.",
            (
                f'"{location}" homeless shelter pets',
                f'"{location}" shelter transportation intake',
                f'"{location}" low barrier shelter identification',
                f'"{location}" family shelter eligibility referral',
                f'"{location}" shelter sobriety requirements',
                f'"{location}" service animals emergency shelter',
            ),
        ),
    )
    branches = []
    for branch_key, purpose, query_texts in specifications:
        branches.append(
            {
                "key": branch_key,
                "purpose": purpose,
                "required": True,
                "saturation": deepcopy(policy),
                "queries": [
                    {
                        "key": f"{branch_key}-{position}",
                        "position": position,
                        "purpose": purpose,
                        "query": query,
                    }
                    for position, query in enumerate(query_texts, start=1)
                ],
            }
        )
    plan = {
        "schemaVersion": 1,
        "categoryId": "housing",
        "stageKey": "urgent-access",
        "targetLocation": location,
        "regionalScope": region,
        "branches": branches,
    }
    validate_query_plan(plan)
    return plan


def _issue(code: str, message: str, *, field: str | None = None) -> dict[str, str]:
    issue = {"code": code, "message": message}
    if field:
        issue["field"] = field
    return issue


def _binding_matches(binding: dict[str, Any], field: str, value: Any) -> bool:
    return binding.get("field") == field and canonical_json(binding.get("value")) == canonical_json(value)


def validate_candidate_dossier(
    dossier: dict[str, Any],
    *,
    required_fields: Iterable[str] = HOUSING_FACTUAL_FIELDS,
) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    identity = dossier.get("candidateIdentity")
    if not isinstance(identity, dict):
        return [_issue("missing-identity", "Candidate dossier has no resolved identity")]
    try:
        expected_identity_key = candidate_identity_key(
            str(identity.get("organization") or ""), str(identity.get("program") or "")
        )
    except ValueError as error:
        return [_issue("invalid-identity", str(error))]
    identity_key = str(identity.get("identityKey") or "")
    if identity_key != expected_identity_key:
        issues.append(_issue("identity-key-mismatch", "Candidate identity key is not canonical"))
    components = identity.get("componentIdentityKeys", [identity_key])
    if not isinstance(components, list) or set(components) != {identity_key}:
        issues.append(
            _issue(
                "multiple-program-identities",
                "One dossier combines more than one organization-plus-program identity",
            )
        )

    sources_value = dossier.get("sources")
    sources = sources_value if isinstance(sources_value, list) else []
    source_by_id: dict[str, dict[str, Any]] = {}
    for source in sources:
        if not isinstance(source, dict) or not str(source.get("id") or ""):
            issues.append(_issue("invalid-source", "Evidence source lacks a stable id"))
            continue
        source_id = str(source["id"])
        if source_id in source_by_id:
            issues.append(_issue("duplicate-source-id", f"Evidence source id {source_id} is duplicated"))
            continue
        source_by_id[source_id] = source
        if not str(source.get("url") or "").strip():
            issues.append(_issue("source-without-url", f"Evidence source {source_id} has no URL"))
        if not str(source.get("extract") or "").strip():
            issues.append(_issue("source-without-extract", f"Evidence source {source_id} has no bounded extract"))
        if source.get("authority") not in SOURCE_AUTHORITIES:
            issues.append(_issue("invalid-source-authority", f"Evidence source {source_id} has an invalid authority"))

    fields = dossier.get("fields")
    if not isinstance(fields, dict):
        return issues + [_issue("missing-fields", "Candidate dossier has no field findings")]
    required = tuple(required_fields)
    for field in required:
        finding = fields.get(field)
        if not isinstance(finding, dict):
            issues.append(_issue("missing-field-state", "Required field has no finding", field=field))
            continue
        status = finding.get("status")
        if status not in FIELD_STATES:
            issues.append(
                _issue(
                    "invalid-field-state",
                    "Field must be supported, conflicting, or unknown",
                    field=field,
                )
            )
            continue
        if status == "unknown":
            if "value" in finding or finding.get("evidenceIds"):
                issues.append(_issue("unknown-has-claim", "Unknown field contains a factual claim", field=field))
            if not str(finding.get("reason") or "").strip():
                issues.append(_issue("unknown-without-reason", "Unknown field needs a reason", field=field))
            continue
        if status == "conflicting":
            alternatives = finding.get("alternatives")
            if not isinstance(alternatives, list) or len(alternatives) < 2:
                issues.append(_issue("invalid-conflict", "Conflicting field needs at least two alternatives", field=field))
                continue
            if len({canonical_json(item.get("value")) for item in alternatives if isinstance(item, dict)}) < 2:
                issues.append(_issue("invalid-conflict", "Conflicting field alternatives must differ", field=field))
            for alternative in alternatives:
                if not isinstance(alternative, dict):
                    issues.append(_issue("invalid-conflict", "Conflict alternative is not an object", field=field))
                    continue
                issues.extend(
                    _validate_supported_value(
                        field,
                        alternative.get("value"),
                        alternative.get("evidenceIds"),
                        identity_key,
                        identity,
                        source_by_id,
                    )
                )
            continue
        if "value" not in finding:
            issues.append(_issue("supported-without-value", "Supported field has no value", field=field))
            continue
        issues.extend(
            _validate_supported_value(
                field,
                finding["value"],
                finding.get("evidenceIds"),
                identity_key,
                identity,
                source_by_id,
            )
        )
        observed_values = {
            canonical_json(binding.get("value"))
            for source in sources
            for binding in source.get("supports", [])
            if isinstance(binding, dict)
            and binding.get("field") == field
            and source.get("authority") != "directory-lead"
        }
        selected_value = canonical_json(finding["value"])
        if len(observed_values) > 1 or (observed_values and selected_value not in observed_values):
            issues.append(
                _issue(
                    "unresolved-conflict",
                    "Field is marked supported despite conflicting authoritative evidence",
                    field=field,
                )
            )
        if any(
            _binding_matches(binding, field, finding["value"])
            for source in sources
            for binding in source.get("contradicts", [])
            if isinstance(binding, dict)
        ):
            issues.append(
                _issue(
                    "contradicted-field",
                    "A retained field value is contradicted by captured evidence",
                    field=field,
                )
            )
    return issues


def _validate_supported_value(
    field: str,
    value: Any,
    evidence_ids: Any,
    identity_key: str,
    identity: dict[str, Any],
    source_by_id: dict[str, dict[str, Any]],
) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    if not isinstance(evidence_ids, list) or not evidence_ids:
        return [_issue("missing-evidence", "Supported value has no evidence binding", field=field)]
    supporting_sources: list[dict[str, Any]] = []
    for raw_source_id in evidence_ids:
        source_id = str(raw_source_id)
        source = source_by_id.get(source_id)
        if source is None:
            issues.append(_issue("unknown-evidence", f"Evidence source {source_id} does not exist", field=field))
            continue
        matching_bindings = [
            binding
            for binding in source.get("supports", [])
            if isinstance(binding, dict) and _binding_matches(binding, field, value)
        ]
        if not matching_bindings:
            issues.append(
                _issue(
                    "source-does-not-support-field",
                    f"Evidence source {source_id} does not support the retained value",
                    field=field,
                )
            )
            continue
        supporting_sources.append(source)
        for binding in matching_bindings:
            scope = binding.get("scope", "program")
            if scope == "program" and source.get("pageIdentityKey") != identity_key:
                issues.append(
                    _issue(
                        "cross-program-evidence",
                        f"Evidence source {source_id} describes a different program",
                        field=field,
                    )
                )
            elif scope == "organization":
                if source.get("pageOrganizationKey") != organization_key(
                    str(identity.get("organization") or "")
                ):
                    issues.append(
                        _issue(
                            "cross-organization-evidence",
                            f"Evidence source {source_id} describes a different organization",
                            field=field,
                        )
                    )
            elif scope not in {"program", "organization"}:
                issues.append(_issue("invalid-evidence-scope", f"Evidence source {source_id} has invalid scope", field=field))
    if (
        field in LEAD_ONLY_SENSITIVE_FIELDS
        and supporting_sources
        and all(source.get("authority") == "directory-lead" for source in supporting_sources)
    ):
        issues.append(
            _issue(
                "lead-only-sensitive-field",
                "A directory or aggregator cannot be the sole support for this field",
                field=field,
            )
        )
    return issues
