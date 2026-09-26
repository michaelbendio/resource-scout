"""Versioned WSRS-TSO exchange, semantic checks and deterministic snapshots.

This is a separate delivery mode from the legacy HTML workbench. Human office
state is consumer-owned; it is never inferred from AI preparation or selection.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import hashlib
import re
from urllib.parse import urlsplit

from .preparation_contract import information_sections
from .resource_identity import fingerprint, validate_registry


ARTIFACT_TYPE = "scout-prepared-resources"
CONTACT_FIELDS = ("phone", "address", "website", "email", "hours")
HUMAN_FIELDS = {"verifiedOn", "verifiedAt", "curated", "curatedAt", "deleted", "pinned", "clientNote"}


class PreparedResourceError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise PreparedResourceError(message)


def text(value):
    return isinstance(value, str) and bool(value.strip())


def valid_url(url):
    try:
        parsed = urlsplit(url)
        return parsed.scheme in ("https", "http") and bool(parsed.netloc) and not parsed.username
    except (TypeError, ValueError):
        return False


def source_id(url):
    require(valid_url(url), "Source URL must be an HTTP(S) page")
    return "src_" + hashlib.sha256(url.strip().encode()).hexdigest()[:24]


def revision(resource):
    return fingerprint({k: v for k, v in resource.items() if k != "revision"})


def content_fingerprint(artifact):
    # Packaging metadata is not content; human-state fields are prohibited below.
    return fingerprint({k: v for k, v in artifact.items() if k not in ("snapshot", "review", "changeSet")})


def source_catalog(entries):
    catalog = {}
    for entry in entries:
        url = entry["url"].strip()
        sid = source_id(url)
        catalog.setdefault(sid, dict(id=sid, url=url, title=entry.get("title") or url))
    return sorted(catalog.values(), key=lambda s: s["id"])


def keyed(rows, label):
    require(isinstance(rows, list), f"{label} must be a list")
    require(all(isinstance(r, dict) and text(r.get("id")) for r in rows), f"{label} needs IDs")
    result = {r["id"]: r for r in rows}
    require(len(result) == len(rows), f"Duplicate {label} IDs")
    return result


def validate_artifact(artifact, registry=None, *, office_category_ids=None):
    require(artifact.get("artifactType") == ARTIFACT_TYPE, "Not a prepared-resource artifact")
    require(type(artifact.get("schemaVersion")) is int and artifact["schemaVersion"] == 1,
            "Unsupported prepared-resource major version")
    require(not artifact.get("evaluationOnly"), "Evaluation artifacts cannot be imported")
    require(text(artifact.get("office", {}).get("slug")) and text(artifact["office"].get("name")), "Missing office identity")
    taxonomy = artifact.get("taxonomy", {})
    categories = keyed(taxonomy.get("categories"), "category")
    types = keyed(taxonomy.get("types"), "Type")
    groups = keyed(taxonomy.get("forGroups"), "For group")
    for row in [*categories.values(), *types.values(), *groups.values()]:
        require(text(row.get("label")), "Taxonomy label missing")
    if office_category_ids is not None:
        require(set(categories) == set(office_category_ids), "Office category IDs do not match; no label translation is permitted")
    for row in [*types.values(), *groups.values()]:
        require(text(row.get("definition")), "Taxonomy definition missing")
    for row in types.values():
        require(row.get("categoryId") in categories, "Type belongs to an unknown category")
    sources = keyed(artifact.get("sources"), "source")
    for row in sources.values():
        require(valid_url(row.get("url")) and text(row.get("title")), "Invalid source page")
    resources = keyed(artifact.get("resources"), "resource")
    require(all(re.fullmatch(r'sr_[a-f0-9]{32}', rid) for rid in resources), 'Resource IDs must be registry-assigned identities')
    if registry is not None:
        validate_registry(registry)
        require(set(resources) <= set(registry["resources"]), "A resource ID is not in the registry")
    scope = artifact.get("scope", {}).get("categoryIds", list(categories))
    require(isinstance(scope, list) and bool(scope) and all(text(c) for c in scope)
            and len(scope) == len(set(scope)) and set(scope) <= set(categories), "Invalid export scope")
    if 'scope' in artifact:
        require(all(type(artifact['scope'].get(k)) is bool for k in ('completeScope', 'completeOffice')), 'Scope completeness must be explicit')
    for rid, row in resources.items():
        require(not HUMAN_FIELDS.intersection(row), f"{rid}: Scout must not export office-owned approval or verification")
        require(row.get("state") in ("usable", "needs-resolution"), f"{rid}: non-importable preparation state")
        require(text(row.get("name")) and text(row.get("description")), f"{rid}: name/description missing")
        require(all(isinstance(row.get(key), str) for key in CONTACT_FIELDS), f"{rid}: contact fields must be strings")
        require("researchedAt" in row and (row["researchedAt"] is None or text(row["researchedAt"])), f"{rid}: research date must be explicit or null")
        if row.get("researchedAt"):
            try:
                datetime.fromisoformat(row["researchedAt"].replace("Z", "+00:00"))
            except ValueError as exc:
                raise PreparedResourceError(f"{rid}: invalid research date") from exc
        for key in ("categories", "types", "forGroups", "sourceIds"):
            require(isinstance(row.get(key), list) and all(text(x) for x in row[key])
                    and len(row[key]) == len(set(row[key])), f"{rid}: invalid {key}")
        require(row["categories"] and set(row["categories"]) <= set(scope), f"{rid}: wrong category scope")
        require(set(row["types"]) <= set(types) and set(row["forGroups"]) <= set(groups), f"{rid}: unknown taxonomy assignment")
        require(all(types[tid]["categoryId"] in row["categories"] for tid in row["types"]), f"{rid}: Type outside resource categories")
        require(row["sourceIds"] and set(row["sourceIds"]) <= set(sources), f"{rid}: missing/dangling source references")
        try:
            information_sections(row.get("informationText", ""))
        except ValueError as exc:
            raise PreparedResourceError(f"{rid}: {exc}") from exc
        if row["state"] == "usable":
            require(all(any(types[tid]["categoryId"] == cid for tid in row["types"]) for cid in row["categories"]), f"{rid}: category lacks a supported Type")
        else:
            require(text(row.get("resolutionReason")), f"{rid}: unresolved record needs an explanation")
        require(row.get("revision") == revision(row), f"{rid}: stale resource revision")
        from .resource_identity import canonical
        require(len(canonical(row).encode()) < 500_000, f"{rid}: oversized resource; reference evidence separately")
    seen = set()
    for starter in artifact.get("starterSets", []):
        cid = starter.get("categoryId")
        require(cid in scope and cid not in seen, "Unknown or duplicate starter category")
        seen.add(cid)
        require(text(starter.get("rationale")) and isinstance(starter.get("gaps"), str), "Starter rationale/gaps missing")
        members = starter.get("members", [])
        require(7 <= len(members) <= 10 or text(starter.get("sizeException")), "Starter size needs a justified exception")
        require(all(type(m.get('position')) is int for m in members)
                and [m.get("position") for m in members] == list(range(1, len(members) + 1)), "Starter positions must be unique and ordered")
        picks = [m.get("resourceId") for m in members]
        require(len(picks) == len(set(picks)), "Duplicate starter resource")
        for member in members:
            rid = member.get("resourceId")
            require(rid in resources and resources[rid]["state"] == "usable" and cid in resources[rid]["categories"], "Starter member is absent, unresolved or outside category")
            require(text(member.get("contribution")) and isinstance(member.get("limitation"), str), "Starter explanation missing")
    require(seen == set(scope), "Starter review must account for every exported category")
    if 'considerations' in artifact:
        selected = {(m['resourceId'], s['categoryId']) for s in artifact['starterSets'] for m in s['members']}
        expected = {(r['id'], cid) for r in resources.values() for cid in r['categories']} - selected
        considered = set()
        require(isinstance(artifact['considerations'], list), 'Considerations must be a list')
        for item in artifact['considerations']:
            pair = (item.get('resourceId'), item.get('categoryId'))
            require(pair in expected and pair not in considered, 'Invalid, selected or repeated consideration pair')
            require(text(item.get('reason')), 'Consideration needs a curator-facing reason')
            considered.add(pair)
        require(considered == expected, 'Every non-starter membership needs a consideration')
    snapshot = artifact.get("snapshot", {})
    require(text(snapshot.get("id")) and text(snapshot.get("generatedAt")), "Snapshot identity/time missing")
    require('predecessorId' in snapshot and (snapshot['predecessorId'] is None or text(snapshot['predecessorId'])), "Invalid predecessor ID")
    try:
        require(datetime.fromisoformat(snapshot['generatedAt'].replace('Z', '+00:00')).tzinfo is not None, 'Snapshot time needs a timezone')
    except (ValueError, TypeError) as exc:
        raise PreparedResourceError('Invalid snapshot time') from exc
    if "contentFingerprint" in snapshot:
        require(snapshot["contentFingerprint"] == content_fingerprint(artifact), "Stale snapshot fingerprint")
    for event in artifact.get("withdrawnEvents", []):
        require(text(event.get("resourceId")) and text(event.get("reason")) and event.get("sourceIds"), "Withdrawal needs identity, reason and evidence")
        require(set(event["sourceIds"]) <= set(sources), "Withdrawal has missing source evidence")
        require(event.get("action") == "admin-review", "Withdrawal must not automatically remove a resource")
        if registry is not None:
            require(event["resourceId"] in registry["resources"], "Withdrawal identity not registered")
    return dict(resources=len(resources), usable=sum(r["state"] == "usable" for r in resources.values()),
                needsResolution=sum(r["state"] == "needs-resolution" for r in resources.values()),
                considerations=len(artifact.get('considerations', [])),
                starterMemberships=sum(len(s["members"]) for s in artifact["starterSets"]),
                uniqueStarterResources=len({m["resourceId"] for s in artifact["starterSets"] for m in s["members"]}))


def compare_snapshots(previous, current):
    require(previous["office"]["slug"] == current["office"]["slug"], "Cannot compare different offices")
    old, new = {r["id"]: r for r in previous["resources"]}, {r["id"]: r for r in current["resources"]}
    same_scope = (previous.get('scope', {}).get('completeScope') is True
                  and current.get('scope', {}).get('completeScope') is True
                  and set(previous['scope']['categoryIds']) == set(current['scope']['categoryIds']))
    return dict(baselineSnapshotId=previous["snapshot"]["id"],
                added=sorted(set(new)-set(old)), changed=sorted(rid for rid in set(old)&set(new) if old[rid]["revision"] != new[rid]["revision"]),
                notObserved=sorted(set(old)-set(new)) if same_scope else [],
                comparisonScope="same-complete" if same_scope else "different-or-incomplete-no-disappearance-claims")


def build_snapshot(payload, *, generated_at, previous=None):
    artifact = deepcopy(payload)
    artifact.update(artifactType=ARTIFACT_TYPE, schemaVersion=1)
    for resource in artifact["resources"]:
        resource["revision"] = revision(resource)
    digest = content_fingerprint(artifact)
    artifact["snapshot"] = dict(id="ss_" + digest[:32],
        predecessorId=previous["snapshot"]["id"] if previous and previous["snapshot"].get("contentFingerprint") != digest else (previous["snapshot"].get("predecessorId") if previous else None),
        generatedAt=generated_at, contentFingerprint=digest)
    if previous and previous["snapshot"].get("contentFingerprint") == digest:
        artifact["snapshot"] = deepcopy(previous["snapshot"])
    elif previous:
        artifact["changeSet"] = compare_snapshots(previous, artifact)
    return artifact
