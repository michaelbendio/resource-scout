from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .codex_first_research import load_researcher_roster
from .storage import ResearchStore


SCOUT_ENRICHMENT_VERSION = "scout-enrichment-v1-stephanie-template"
SCOUT_ENRICHMENT_RESULT_SCHEMA_VERSION = "1"
SCOUT_ENRICHMENT_AUDIT_SCHEMA_VERSION = "1"
SCOUT_ENRICHMENT_RECONCILIATION_VERSION = "codex-reconciliation-v1"

SERVICES_GUIDANCE = (
    "Describe what the organization offers. Be specific—types of assistance, "
    "programs, or resources available."
)
ELIGIBILITY_GUIDANCE = (
    "Who qualifies for services? Include age, income, geographic boundaries, "
    "documentation needed, referral requirements, etc."
)
CONNECT_GUIDANCE = (
    "Tips for success—whether appointments are required, walk-in availability, "
    "online application links"
)

_SEED_RE = re.compile(
    r'(<script\s+id=["\']seed-data["\'][^>]*>)(.*?)(</script>)',
    re.IGNORECASE | re.DOTALL,
)
_ARTIFACT_RE = re.compile(
    r'(<meta\s+name=["\']scout-review-artifact-id["\']\s+content=["\'])'
    r'([^"\']*)(["\'][^>]*>)',
    re.IGNORECASE,
)


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def extract_scout_seed(html: str) -> dict[str, Any]:
    match = _SEED_RE.search(html)
    if not match:
        raise ValueError("The HTML does not contain a seed-data JSON script")
    try:
        seed = json.loads(match.group(2))
    except json.JSONDecodeError as error:
        raise ValueError("The seed-data script does not contain valid JSON") from error
    if not isinstance(seed, dict) or not isinstance(seed.get("resources"), list):
        raise ValueError("The seed-data JSON does not contain a resources array")
    return seed


def _artifact_id(html: str) -> str:
    match = _ARTIFACT_RE.search(html)
    if not match:
        raise ValueError("The HTML has no scout-review-artifact-id meta tag")
    return match.group(2)


def _resource_id(resource: dict[str, Any], ordinal: int) -> str:
    value = str(resource.get("id") or "").strip()
    if not value:
        raise ValueError(f"Resource {ordinal + 1} has no id")
    return value


def _assignment(
    *, project_key: str, resource: dict[str, Any], ordinal: int,
    location_name: str, office_name: str, service_area: str,
) -> tuple[dict[str, Any], str]:
    resource_id = _resource_id(resource, ordinal)
    assignment = {
        "assignmentVersion": SCOUT_ENRICHMENT_VERSION,
        "resultSchemaVersion": SCOUT_ENRICHMENT_RESULT_SCHEMA_VERSION,
        "projectKey": project_key,
        "resourceId": resource_id,
        "resourceName": str(resource.get("name") or "").strip(),
        "locationName": location_name,
        "officeName": office_name,
        "serviceArea": service_area,
        "resource": deepcopy(resource),
        "informationSections": [
            {"key": "servicesProvided", "heading": "Services Provided",
             "guidance": SERVICES_GUIDANCE},
            {"key": "eligibilityRequirements", "heading": "Eligibility Requirements",
             "guidance": ELIGIBILITY_GUIDANCE},
            {"key": "howToBestConnect", "heading": "How to Best Connect",
             "guidance": CONNECT_GUIDANCE},
        ],
        "preservation": {
            "heading": "Scout Findings",
            "originalInformationText": str(resource.get("informationText") or ""),
            "instruction": "Preserve this text verbatim; do not summarize or rewrite it.",
        },
        "researchRules": [
            "Use current public sources and prefer the organization's official website.",
            "Answer every section specifically for this resource.",
            "State when a detail could not be confirmed; never invent a fact.",
            "Return evidence source URLs in evidenceSources.",
            "Do not rewrite Scout Findings; it is appended mechanically after validation.",
        ],
    }
    assignment_sha256 = _sha256_text(_json(assignment))
    assignment["assignmentSha256"] = assignment_sha256
    return assignment, assignment_sha256


def prepare_scout_enrichment_project(
    store: ResearchStore, source_path: str | Path
) -> dict[str, Any]:
    path = Path(source_path).expanduser().resolve()
    html = path.read_text(encoding="utf-8")
    seed = extract_scout_seed(html)
    resources = seed["resources"]
    if not resources:
        raise ValueError("The source artifact contains no resources")
    source_sha256 = _sha256_text(html)
    project_key = source_sha256[:24]
    location_name = path.stem[4:] if path.stem.lower().startswith("auto") else path.stem
    office_name = str(seed.get("officeName") or "").strip()
    service_area = str(seed.get("serviceArea") or "").strip()
    prepared = []
    seen_ids: set[str] = set()
    for ordinal, raw_resource in enumerate(resources):
        if not isinstance(raw_resource, dict):
            raise ValueError(f"Resource {ordinal + 1} is not an object")
        resource_id = _resource_id(raw_resource, ordinal)
        if resource_id in seen_ids:
            raise ValueError(f"Duplicate resource id: {resource_id}")
        seen_ids.add(resource_id)
        assignment, assignment_sha256 = _assignment(
            project_key=project_key, resource=raw_resource, ordinal=ordinal,
            location_name=location_name, office_name=office_name,
            service_area=service_area,
        )
        prepared.append({
            "ordinal": ordinal,
            "resourceId": resource_id,
            "resourceName": str(raw_resource.get("name") or "").strip(),
            "originalResource": raw_resource,
            "originalResourceSha256": _sha256_text(_json(raw_resource)),
            "originalInformationText": str(raw_resource.get("informationText") or ""),
            "assignment": assignment,
            "assignmentSha256": assignment_sha256,
        })
    seed_sha256 = _sha256_text(_json(seed))
    project_id = store.create_scout_enrichment_project({
        "enrichmentVersion": SCOUT_ENRICHMENT_VERSION,
        "resultSchemaVersion": SCOUT_ENRICHMENT_RESULT_SCHEMA_VERSION,
        "sourcePath": str(path), "sourceHtml": html,
        "sourceSha256": source_sha256, "sourceArtifactId": _artifact_id(html),
        "sourceSeed": seed, "sourceSeedSha256": seed_sha256,
        "locationName": location_name, "officeName": office_name,
        "serviceArea": service_area,
    }, prepared)
    value = store.get_scout_enrichment_project(project_id)
    if value is None:
        raise ValueError("Scout enrichment project was not saved")
    return enrichment_project_summary(value)


def enrichment_project_summary(project: dict[str, Any]) -> dict[str, Any]:
    return {
        key: project[key] for key in (
            "id", "createdAt", "updatedAt", "status", "enrichmentVersion",
            "resultSchemaVersion", "sourcePath", "sourceSha256",
            "sourceArtifactId", "sourceSeedSha256", "locationName",
            "officeName", "serviceArea", "resourceCount", "progress",
        )
    }


def next_scout_enrichment_assignment(
    store: ResearchStore, project_id: int
) -> dict[str, Any] | None:
    return store.next_scout_enrichment_assignment(project_id)


def _nonempty_text(result: dict[str, Any], key: str, label: str) -> str:
    value = result.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a nonempty string")
    return value.strip()


def validate_scout_enrichment_result(
    assignment: dict[str, Any], result: dict[str, Any]
) -> dict[str, Any]:
    if not isinstance(result, dict):
        raise ValueError("Enrichment result must be a JSON object")
    if str(result.get("resourceId") or "") != assignment["resourceId"]:
        raise ValueError("Result resourceId does not match the assignment")
    if str(result.get("assignmentSha256") or "") != assignment["assignmentSha256"]:
        raise ValueError("Result assignmentSha256 does not match the assignment")
    return {
        "resourceId": assignment["resourceId"],
        "assignmentSha256": assignment["assignmentSha256"],
        "servicesProvided": _nonempty_text(result, "servicesProvided", "Services Provided"),
        "eligibilityRequirements": _nonempty_text(
            result, "eligibilityRequirements", "Eligibility Requirements"
        ),
        "howToBestConnect": _nonempty_text(
            result, "howToBestConnect", "How to Best Connect"
        ),
        "evidenceSources": _normalize_evidence_sources(result.get("evidenceSources")),
    }


def save_scout_enrichment_result(
    store: ResearchStore, project_id: int, raw_result: str | dict[str, Any]
) -> dict[str, Any]:
    result = json.loads(raw_result) if isinstance(raw_result, str) else raw_result
    project = store.get_scout_enrichment_project(project_id)
    if project is None:
        raise ValueError("Scout enrichment project not found")
    resource_id = str(result.get("resourceId") or "") if isinstance(result, dict) else ""
    resource = next(
        (item for item in project["resources"] if item["resourceId"] == resource_id), None
    )
    if resource is None:
        raise ValueError("Result resourceId is not part of this project")
    normalized = validate_scout_enrichment_result(resource["assignment"], result)
    result_sha256 = _sha256_text(_json(normalized))
    store.save_scout_enrichment_result(
        project_id, resource_id, normalized, result_sha256
    )
    ensure_scout_enrichment_audits(store, project_id)
    updated = store.get_scout_enrichment_project(project_id)
    if updated is None:
        raise ValueError("Scout enrichment project not found")
    return enrichment_project_summary(updated)


_UNCERTAINTY_PATTERNS = (
    "not confirmed", "could not confirm", "unable to confirm",
    "cannot confirm", "not publicly available", "not published",
    "unclear", "contact the organization to confirm", "verify with",
)
_SAFETY_SENSITIVE_TERMS = (
    "crisis", "suicide", "overdose", "detox", "withdrawal",
    "domestic violence", "emergency shelter", "legal aid", "medical",
    "mental health", "behavioral health",
)
_CONNECT_TERMS = (
    "call", "phone", "online", "apply", "appointment", "walk-in",
    "walk in", "email", "visit", "intake", "website", "referral",
)


def enrichment_audit_risk(
    resource: dict[str, Any], result: dict[str, Any]
) -> dict[str, Any]:
    reasons: list[str] = []
    all_text = " ".join(str(result.get(key) or "") for key in (
        "servicesProvided", "eligibilityRequirements", "howToBestConnect"
    )).lower()
    uncertainty = sorted({
        phrase for phrase in _UNCERTAINTY_PATTERNS if phrase in all_text
    })
    if uncertainty:
        reasons.append("Primary result contains unresolved or unconfirmed details")
    source_urls = [
        str(item.get("url") or "").strip()
        for item in result.get("evidenceSources") or [] if isinstance(item, dict)
    ]
    if not any(urlparse(url).scheme in {"http", "https"} for url in source_urls):
        reasons.append("Primary result has no usable evidence URL")
    if not str(resource.get("website") or "").strip() and not str(
        resource.get("phone") or ""
    ).strip():
        reasons.append("Source record has neither a website nor a phone number")
    connect_text = str(result.get("howToBestConnect") or "").lower()
    if not any(term in connect_text for term in _CONNECT_TERMS):
        reasons.append("Connection guidance has no concrete contact or intake action")
    identity_text = " ".join(str(resource.get(key) or "") for key in (
        "name", "description", "informationText"
    )).lower()
    sensitive = sorted({term for term in _SAFETY_SENSITIVE_TERMS if term in identity_text})
    if sensitive:
        reasons.append("Safety-sensitive service warrants an independent audit")
    return {
        "required": bool(reasons), "reasons": reasons,
        "uncertaintySignals": uncertainty, "safetySignals": sensitive,
    }


def _external_auditors() -> list[dict[str, str]]:
    roster = load_researcher_roster()
    return [
        item for item in roster["researchers"]
        if item["name"] != "Codex" and item["role"] != "disabled"
    ]


def _audit_assignment(
    project: dict[str, Any], resource: dict[str, Any], risk: dict[str, Any],
    researcher: dict[str, str],
) -> tuple[dict[str, Any], str]:
    assignment = {
        "assignmentVersion": SCOUT_ENRICHMENT_VERSION,
        "auditSchemaVersion": SCOUT_ENRICHMENT_AUDIT_SCHEMA_VERSION,
        "role": "targeted-independent-audit",
        "projectId": project["id"], "resourceId": resource["resourceId"],
        "resourceName": resource["resourceName"],
        "researcher": researcher["name"], "rosterRole": researcher["role"],
        "risk": risk, "resource": resource["originalResource"],
        "primaryResult": resource["result"],
        "instructions": [
            "Independently verify the three enriched Information sections.",
            "Focus on the listed risk reasons and current operational accuracy.",
            "Prefer official sources and cite every evidence URL used.",
            "Identify exact corrections; do not rewrite Scout Findings.",
            "Return only the required audit JSON object.",
        ],
    }
    digest = _sha256_text(_json(assignment))
    assignment["assignmentSha256"] = digest
    return assignment, digest


def ensure_scout_enrichment_audits(
    store: ResearchStore, project_id: int
) -> dict[str, Any]:
    project = store.get_scout_enrichment_project(project_id)
    if project is None:
        raise ValueError("Scout enrichment project not found")
    auditors = _external_auditors()
    if not auditors:
        raise ValueError("The researcher roster has no external enrichment auditors")
    for resource in project["resources"]:
        if resource["status"] != "completed" or resource["audit"] is not None:
            continue
        risk = enrichment_audit_risk(resource["originalResource"], resource["result"])
        if not risk["required"]:
            continue
        researcher = auditors[int(resource["ordinal"]) % len(auditors)]
        assignment, digest = _audit_assignment(
            project, resource, risk, researcher
        )
        store.create_scout_enrichment_audit(
            project_id, resource["resourceId"], researcher=researcher["name"],
            roster_role=researcher["role"], risk=risk, assignment=assignment,
            assignment_sha256=digest,
        )
    updated = store.get_scout_enrichment_project(project_id)
    if updated is None:
        raise ValueError("Scout enrichment project not found")
    return updated


def next_scout_enrichment_audit(
    store: ResearchStore, project_id: int, researcher: str | None = None
) -> dict[str, Any] | None:
    ensure_scout_enrichment_audits(store, project_id)
    audit = store.next_scout_enrichment_audit(project_id, researcher)
    return audit["assignment"] if audit else None


def _normalize_evidence_sources(sources: Any) -> list[dict[str, str]]:
    if not isinstance(sources, list):
        raise ValueError("evidenceSources must be an array")
    normalized = []
    for source in sources:
        if not isinstance(source, dict):
            raise ValueError("Every evidence source must be an object")
        url = str(source.get("url") or "").strip()
        if url and not re.match(r"^https?://", url, re.IGNORECASE):
            raise ValueError("Evidence source URLs must start with http:// or https://")
        normalized.append({
            "title": str(source.get("title") or "").strip(), "url": url,
            "supports": str(source.get("supports") or "").strip(),
            "accessedOn": str(source.get("accessedOn") or "").strip(),
        })
    return normalized


def validate_scout_enrichment_audit_result(
    assignment: dict[str, Any], result: dict[str, Any]
) -> dict[str, Any]:
    if not isinstance(result, dict):
        raise ValueError("Audit result must be a JSON object")
    for key in ("resourceId", "researcher", "assignmentSha256"):
        if str(result.get(key) or "") != str(assignment[key]):
            raise ValueError(f"Audit {key} does not match the assignment")
    verdict = str(result.get("verdict") or "").strip()
    if verdict not in {"confirmed", "revisions-needed"}:
        raise ValueError("Audit verdict must be confirmed or revisions-needed")
    issues = result.get("issues")
    if not isinstance(issues, list) or any(not isinstance(item, str) for item in issues):
        raise ValueError("Audit issues must be an array of strings")
    replacements = result.get("suggestedReplacements")
    if not isinstance(replacements, dict):
        raise ValueError("suggestedReplacements must be an object")
    return {
        "resourceId": assignment["resourceId"],
        "researcher": assignment["researcher"],
        "assignmentSha256": assignment["assignmentSha256"],
        "verdict": verdict, "issues": [item.strip() for item in issues if item.strip()],
        "suggestedReplacements": {
            key: str(replacements.get(key) or "").strip() for key in (
                "servicesProvided", "eligibilityRequirements", "howToBestConnect"
            )
        },
        "evidenceSources": _normalize_evidence_sources(result.get("evidenceSources")),
    }


def _reconciliation_assignment(
    audit: dict[str, Any], resource: dict[str, Any], audit_result: dict[str, Any]
) -> tuple[dict[str, Any], str]:
    assignment = {
        "assignmentVersion": SCOUT_ENRICHMENT_RECONCILIATION_VERSION,
        "resultSchemaVersion": SCOUT_ENRICHMENT_RESULT_SCHEMA_VERSION,
        "role": "codex-audit-reconciliation", "auditId": audit["id"],
        "resourceId": resource["resourceId"],
        "resourceName": resource["resourceName"],
        "resource": resource["originalResource"], "risk": audit["risk"],
        "primaryResult": resource["result"], "independentAudit": audit_result,
        "instructions": [
            "Reconcile the primary enrichment with the independent audit.",
            "Use evidence, not deference, to decide every correction.",
            "Return complete final text for all three sections and combined evidence.",
            "State unconfirmed details plainly; never invent a fact.",
            "Scout Findings is appended mechanically and must not be rewritten.",
        ],
    }
    digest = _sha256_text(_json(assignment))
    assignment["assignmentSha256"] = digest
    return assignment, digest


def save_scout_enrichment_audit_result(
    store: ResearchStore, project_id: int, raw_result: str | dict[str, Any]
) -> dict[str, Any]:
    result = json.loads(raw_result) if isinstance(raw_result, str) else raw_result
    project = ensure_scout_enrichment_audits(store, project_id)
    digest = str(result.get("assignmentSha256") or "") if isinstance(result, dict) else ""
    audit = next((item for item in project["audits"] if item["assignmentSha256"] == digest), None)
    if audit is None:
        raise ValueError("Audit assignmentSha256 is not part of this project")
    normalized = validate_scout_enrichment_audit_result(audit["assignment"], result)
    resource = next(
        item for item in project["resources"] if item["resourceId"] == audit["resourceId"]
    )
    reconciliation, reconciliation_digest = _reconciliation_assignment(
        audit, resource, normalized
    )
    store.save_scout_enrichment_audit_result(
        audit["id"], normalized, _sha256_text(_json(normalized)),
        reconciliation, reconciliation_digest,
    )
    updated = store.get_scout_enrichment_project(project_id)
    if updated is None:
        raise ValueError("Scout enrichment project not found")
    return enrichment_project_summary(updated)


def next_scout_enrichment_reconciliation(
    store: ResearchStore, project_id: int
) -> dict[str, Any] | None:
    ensure_scout_enrichment_audits(store, project_id)
    return store.next_scout_enrichment_reconciliation(project_id)


def save_scout_enrichment_reconciliation_result(
    store: ResearchStore, project_id: int, raw_result: str | dict[str, Any]
) -> dict[str, Any]:
    result = json.loads(raw_result) if isinstance(raw_result, str) else raw_result
    project = store.get_scout_enrichment_project(project_id)
    if project is None:
        raise ValueError("Scout enrichment project not found")
    digest = str(result.get("assignmentSha256") or "") if isinstance(result, dict) else ""
    audit = next((
        item for item in project["audits"]
        if item["reconciliationAssignmentSha256"] == digest
    ), None)
    if audit is None or audit["reconciliationAssignment"] is None:
        raise ValueError("Reconciliation assignmentSha256 is not part of this project")
    normalized = validate_scout_enrichment_result(
        audit["reconciliationAssignment"], result
    )
    store.save_scout_enrichment_reconciliation_result(
        audit["id"], normalized, _sha256_text(_json(normalized))
    )
    updated = store.get_scout_enrichment_project(project_id)
    if updated is None:
        raise ValueError("Scout enrichment project not found")
    return enrichment_project_summary(updated)


def compose_information_text(result: dict[str, Any], scout_findings: str) -> str:
    sections = [
        "**Services Provided**\n" + result["servicesProvided"].strip(),
        "**Eligibility Requirements**\n" + result["eligibilityRequirements"].strip(),
        "**How to Best Connect**\n" + result["howToBestConnect"].strip(),
        "**Scout Findings**\n" + scout_findings,
    ]
    return "\n\n".join(sections)


def build_scout_enriched_html(store: ResearchStore, project_id: int) -> bytes:
    ensure_scout_enrichment_audits(store, project_id)
    project = store.get_scout_enrichment_project(project_id, include_source=True)
    if project is None:
        raise ValueError("Scout enrichment project not found")
    if project["status"] != "completed":
        progress = project["progress"]
        raise ValueError(
            f"Enrichment is incomplete: {progress['completed']} of {progress['total']} resources"
        )
    seed = deepcopy(project["sourceSeed"])
    originals = seed["resources"]
    rows = project["resources"]
    if len(originals) != len(rows):
        raise ValueError("Stored resource count no longer matches the source seed")
    enriched_resources = []
    for ordinal, (original, row) in enumerate(zip(originals, rows)):
        if _sha256_text(_json(original)) != row["originalResourceSha256"]:
            raise ValueError(f"Source resource {ordinal + 1} failed its integrity check")
        if row["result"] is None:
            raise ValueError(f"Resource {row['resourceId']} has no enrichment result")
        final_result = row["result"]
        if row["audit"] is not None:
            if row["audit"]["status"] != "reconciled":
                raise ValueError(f"Resource {row['resourceId']} has an incomplete audit")
            final_result = row["audit"]["reconciliationResult"]
        enriched = deepcopy(original)
        enriched["informationText"] = compose_information_text(
            final_result, row["originalInformationText"]
        )
        for key, value in original.items():
            if key != "informationText" and enriched.get(key) != value:
                raise ValueError(f"Enrichment changed protected field {key}")
        enriched_resources.append(enriched)
    seed["resources"] = enriched_resources
    seed_json = json.dumps(seed, ensure_ascii=False, indent=2).replace("</", "<\\/")
    html = project["sourceHtml"]
    html, seed_count = _SEED_RE.subn(
        lambda match: match.group(1) + "\n" + seed_json + "\n" + match.group(3),
        html, count=1,
    )
    if seed_count != 1:
        raise ValueError("Could not replace the source seed-data script")
    artifact_id = "scout-enriched-" + _sha256_text(
        project["sourceSha256"] + SCOUT_ENRICHMENT_VERSION
    )[:24]
    html, artifact_count = _ARTIFACT_RE.subn(
        lambda match: match.group(1) + artifact_id + match.group(3), html, count=1
    )
    if artifact_count != 1:
        raise ValueError("Could not replace the source artifact id")
    return html.encode("utf-8")


def default_enriched_filename(project: dict[str, Any]) -> str:
    location = re.sub(r"[^A-Za-z0-9]+", "", str(project["locationName"])) or "Location"
    return f"auto{location}-enriched.html"
