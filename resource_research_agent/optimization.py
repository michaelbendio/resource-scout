from __future__ import annotations

import hashlib
import json
import re
import unicodedata
import uuid
from copy import deepcopy
from typing import Any, Iterable
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


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

FIELD_STATES = {"supported", "conflicting", "unknown"}
SOURCE_AUTHORITIES = {
    "direct-provider",
    "government-referral",
    "reputable-secondary",
    "directory-lead",
}

CANDIDATE_ROLES = {
    "direct-program",
    "access-assessment-service",
    "service-location",
    "referral-system",
    "directory",
    "organization-only",
    "unresolved-lead",
}
COUNTABLE_CANDIDATE_ROLES = {
    "direct-program",
    "access-assessment-service",
}
CANDIDATE_GEOGRAPHY_STATES = {
    "confirmed-target",
    "confirmed-serves-target",
    "unknown",
    "outside-target",
}
CANDIDATE_CATEGORY_STATES = {
    "confirmed",
    "adjacent-support",
    "unknown",
    "wrong-category",
}
CANDIDATE_ACTIONABILITY_STATES = {
    "actionable",
    "uncertain",
    "informational-only",
}
CANDIDATE_CURRENT_STATUS_STATES = {
    "current",
    "uncertain",
    "inactive",
    "successor",
}
CANDIDATE_EVIDENCE_READINESS_STATES = {
    "current-authoritative",
    "current-corroborated",
    "lead-only",
    "stale",
}
CANDIDATE_QUALIFICATION_POLICY_VERSION = "candidate-qualification-gates-v2"


def candidate_qualification(
    decision: dict[str, Any],
    *,
    boundary_state: str,
    package_match_state: str,
) -> dict[str, Any]:
    """Classify a resolved identity without letting a named lead become a candidate.

    The reviewed decision owns the role and gate observations. Scout owns the
    deterministic promotion result. Missing or unfamiliar observations fail closed.
    """

    values = {
        "candidateRole": (
            str(decision.get("candidateRole") or "").strip(),
            CANDIDATE_ROLES,
        ),
        "geographyState": (
            str(decision.get("geographyState") or "").strip(),
            CANDIDATE_GEOGRAPHY_STATES,
        ),
        "categoryState": (
            str(decision.get("categoryState") or "").strip(),
            CANDIDATE_CATEGORY_STATES,
        ),
        "actionabilityState": (
            str(decision.get("actionabilityState") or "").strip(),
            CANDIDATE_ACTIONABILITY_STATES,
        ),
        "currentStatusState": (
            str(decision.get("currentStatusState") or "").strip(),
            CANDIDATE_CURRENT_STATUS_STATES,
        ),
        "evidenceReadiness": (
            str(decision.get("evidenceReadiness") or "").strip(),
            CANDIDATE_EVIDENCE_READINESS_STATES,
        ),
    }
    invalid = [name for name, (value, allowed) in values.items() if value not in allowed]
    if invalid:
        raise ValueError(
            "Candidate qualification is missing or invalid: " + ", ".join(invalid)
        )

    role = values["candidateRole"][0]
    geography = values["geographyState"][0]
    category = values["categoryState"][0]
    actionability = values["actionabilityState"][0]
    current_status = values["currentStatusState"][0]
    evidence = values["evidenceReadiness"][0]
    reasons: list[str] = []
    terminal_noncandidate = False

    if package_match_state == "same-program" or boundary_state == "excluded-existing":
        reasons.append("same program is already represented in the source package")
        terminal_noncandidate = True
    if role not in COUNTABLE_CANDIDATE_ROLES:
        reasons.append(f"role {role} is retained as a noncandidate lead")
        terminal_noncandidate = True
    if geography == "outside-target":
        reasons.append("service geography is outside the target")
        terminal_noncandidate = True
    elif geography == "unknown":
        reasons.append("service geography is unresolved")
    if category in {"adjacent-support", "wrong-category"}:
        reasons.append(f"category state {category} is not a target-category candidate")
        terminal_noncandidate = True
    elif category == "unknown":
        reasons.append("category fit is unresolved")
    if actionability == "informational-only":
        reasons.append("record has no independently actionable access function")
        terminal_noncandidate = True
    elif actionability == "uncertain":
        reasons.append("access path is unresolved")
    if current_status == "inactive":
        reasons.append("current evidence says the program is inactive")
        terminal_noncandidate = True
    elif current_status == "successor":
        reasons.append("possible successor or renamed program requires identity review")
    elif current_status == "uncertain":
        reasons.append("current program status is unresolved")
    if evidence == "lead-only":
        reasons.append("only lead-level evidence is available")
    elif evidence == "stale":
        reasons.append("available evidence is stale")
    if boundary_state != "resolved" and boundary_state != "excluded-existing":
        reasons.append(f"identity boundary is {boundary_state}")

    all_promotable = (
        boundary_state == "resolved"
        and package_match_state != "same-program"
        and role in COUNTABLE_CANDIDATE_ROLES
        and geography in {"confirmed-target", "confirmed-serves-target"}
        and category == "confirmed"
        and actionability == "actionable"
        and current_status == "current"
        and evidence in {"current-authoritative", "current-corroborated"}
    )
    state = (
        "excluded-existing"
        if package_match_state == "same-program" or boundary_state == "excluded-existing"
        else "eligible"
        if all_promotable
        else "noncandidate"
        if terminal_noncandidate
        else "review-required"
    )
    return {
        "state": state,
        "reasons": reasons,
        **{name: value for name, (value, _allowed) in values.items()},
    }


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def canonicalize_discovery_url(value: Any) -> str:
    text = str(value or "").strip()
    try:
        parsed = urlsplit(text)
        port = parsed.port
    except ValueError as error:
        raise ValueError(f"Invalid discovery URL: {text}") from error
    scheme = parsed.scheme.casefold()
    if scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError(f"Unsupported discovery URL: {text}")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("Discovery URLs containing credentials are not allowed")
    hostname = parsed.hostname.casefold()
    rendered_host = f"[{hostname}]" if ":" in hostname else hostname
    if port is not None and not (
        (scheme == "http" and port == 80) or (scheme == "https" and port == 443)
    ):
        rendered_host = f"{rendered_host}:{port}"
    ignored_parameters = {"fbclid", "gclid", "mc_cid", "mc_eid"}
    query = [
        (key, query_value)
        for key, query_value in parse_qsl(parsed.query, keep_blank_values=True)
        if key.casefold() not in ignored_parameters
        and not key.casefold().startswith("utm_")
    ]
    path = parsed.path or "/"
    if path != "/":
        path = path.rstrip("/") or "/"
    return urlunsplit((scheme, rendered_host, path, urlencode(sorted(query)), ""))


def _optimization_linkage_key(
    configuration_hash: str, packet_reference: int | str
) -> str:
    if not re.fullmatch(r"[0-9a-f]{64}", str(configuration_hash)):
        raise ValueError("Optimization resource linkage requires a configuration hash")
    if isinstance(packet_reference, int) and not isinstance(packet_reference, bool):
        if packet_reference <= 0:
            raise ValueError("Optimization resource linkage requires a positive packet id")
        return str(packet_reference)
    packet_sha256 = str(packet_reference or "").strip().casefold()
    if not re.fullmatch(r"[0-9a-f]{64}", packet_sha256):
        raise ValueError(
            "Optimization resource linkage requires a positive packet id or packet hash"
        )
    return f"packet-sha256:{packet_sha256}"


def optimization_resource_id(
    configuration_hash: str, packet_reference: int | str
) -> str:
    linkage_key = _optimization_linkage_key(configuration_hash, packet_reference)
    return uuid.uuid5(
        uuid.NAMESPACE_URL,
        f"resource-research-optimization:{configuration_hash}:{linkage_key}",
    ).hex


def optimization_candidate_id(configuration_hash: str, packet_sha256: str) -> str:
    linkage_key = _optimization_linkage_key(configuration_hash, packet_sha256)
    return "optimization-" + uuid.uuid5(
        uuid.NAMESPACE_URL,
        f"resource-research-optimization-candidate:{configuration_hash}:{linkage_key}",
    ).hex


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


def augment_query_plan_with_identity_status_checks(
    plan: dict[str, Any],
    identities: Iterable[dict[str, Any]],
    *,
    include_routed: bool = False,
) -> dict[str, Any]:
    """Add one deterministic currency/status query per reviewed identity."""

    result = deepcopy(plan)
    category_id = str(result.get("categoryId") or "").strip()
    active_stage = str(result.get("stageKey") or "").strip()
    target_location = str(result.get("targetLocation") or "").strip()
    if not category_id or not active_stage or not target_location:
        raise ValueError(
            "Candidate status checks require category, stage, and target location"
        )
    resolved: dict[str, tuple[str, str]] = {}
    for identity in identities:
        if not isinstance(identity, dict):
            continue
        stage_key = str(identity.get("stageKey") or active_stage).strip()
        if not include_routed and stage_key != active_stage:
            continue
        organization = str(identity.get("organization") or "").strip()
        program = str(identity.get("program") or "").strip()
        identity_key = candidate_identity_key(organization, program)
        resolved[identity_key] = (organization, program)
    if not resolved:
        return result
    if len(resolved) > 100:
        raise ValueError("Candidate status sweep supports at most 100 identities")

    existing_keys = {str(branch.get("key") or "") for branch in result["branches"]}
    if "candidate-current-status" in existing_keys:
        raise ValueError("Query plan already contains candidate current-status checks")
    ordered = sorted(resolved.items())
    count = len(ordered)
    purpose = (
        f"Find current evidence that each reviewed {category_id} identity remains active "
        "or has closed, moved, changed intake, or been succeeded."
    )
    result["branches"].append(
        {
            "key": "candidate-current-status",
            "purpose": purpose,
            "required": True,
            "saturation": {
                "minimumQueries": count,
                "maximumQueries": count,
                "consecutiveNoNewIdentityQueries": count,
                "noveltyUnit": (
                    "package-eligible normalized organization-plus-program identity"
                ),
            },
            "queries": [
                {
                    "key": f"candidate-current-status-{sha256_json(identity_key)[:12]}",
                    "position": position,
                    "purpose": purpose,
                    "identityKey": identity_key,
                    "query": (
                        f'"{organization}" "{program}" '
                        f'{target_location} current intake closure'
                    ),
                }
                for position, (identity_key, (organization, program)) in enumerate(
                    ordered, start=1
                )
            ],
        }
    )
    result["schemaVersion"] = max(8, int(result.get("schemaVersion") or 0))
    result["candidateStatusPolicyVersion"] = "identity-current-status-v2"
    result["candidateStatusIncludesRoutedIdentities"] = bool(include_routed)
    validate_query_plan(result)
    return result


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
    required_fields: Iterable[str],
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
    if supporting_sources and all(
        source.get("authority") == "directory-lead" for source in supporting_sources
    ):
        issues.append(
            _issue(
                "lead-only-field",
                "A directory or aggregator cannot be the sole support for a factual field",
                field=field,
            )
        )
    return issues
