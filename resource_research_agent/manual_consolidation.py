from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from typing import Any
from urllib.parse import urlsplit

from .duplicates import DuplicateIndex
from .storage import ResearchStore


DIRECT_ROLES = {"program", "provider-organization", "access-point"}
PRESERVED_ROLES = {"routing-source", "directory", "outreach-initiative", "unresolved"}


def _sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _identity_key(lead: dict[str, Any]) -> tuple[str, str]:
    organization = lead["normalizedOrganization"]
    program = lead["normalizedProgram"]
    website = lead["website"]
    role_family = {
        "program": "service",
        "provider-organization": "service",
        "access-point": "access-point",
        "routing-source": "routing-source",
        "directory": "directory",
    }.get(lead["leadType"], "unresolved")
    if organization and program:
        return f"{role_family}|organization-program|{organization}|{program}", "exact normalized organization and program with compatible role"
    if program:
        return f"{role_family}|program|{program}|{website}", "exact normalized program with compatible role"
    if organization:
        return f"{role_family}|organization|{organization}", "exact normalized organization with compatible role"
    if website:
        return f"{role_family}|website|{website}", "exact normalized official URL with compatible role"
    return (
        f"source-row|{lead['sourceLabel'].casefold()}|{lead['rawSha256']}|{lead['sourceOrdinal']}",
        "source row has no usable identity",
    )


def _choose_text(values: list[str]) -> str:
    candidates = {value.strip() for value in values if value and value.strip()}
    if not candidates:
        return ""
    return sorted(
        candidates,
        key=lambda value: (-len(value.split()), -len(value), value.casefold(), value),
    )[0]


def _choose_url(values: list[str]) -> str:
    candidates = {value for value in values if value}
    if not candidates:
        return ""
    return sorted(
        candidates,
        key=lambda value: (
            0 if value.startswith("https://") else 1,
            1 if urlsplit(value).query else 0,
            len(urlsplit(value).path),
            len(value),
            value,
        ),
    )[0]


def _route_role(members: list[dict[str, Any]], program: str, organization: str) -> str:
    declared = {member["leadType"] for member in members}
    if not organization and not program:
        return "unresolved"
    if not declared or not declared <= (DIRECT_ROLES | {"routing-source", "directory"}):
        return "unresolved"
    if declared <= {"directory", "routing-source"}:
        return "directory" if declared == {"directory"} else "routing-source"
    if declared & {"directory", "routing-source"}:
        return "unresolved"
    if declared <= {"program", "provider-organization"}:
        role = "program" if program else "provider-organization"
    elif declared == {"access-point"}:
        role = "access-point"
    elif len(declared) == 1:
        role = next(iter(declared))
    else:
        return "unresolved"
    combined = " ".join(
        member["program"] + " " + member["whyRelevant"] + " " + member["uncertainty"]
        for member in members
    ).casefold()
    has_limited_initiative_signal = bool(
        re.search(r"\b(?:pilot|planned|grant[- ]funded|initiative)\b", combined)
    )
    has_public_path = any(member["website"] for member in members) or bool(
        re.search(r"\b(?:intake|apply|application|enroll|appointment|call|referral|walk-in)\b", combined)
    )
    if has_limited_initiative_signal and not has_public_path:
        return "outreach-initiative"
    return role


def _candidate_shape(group: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": group["displayName"],
        "organizationName": group["organization"],
        "programName": group["program"],
        "website": group["website"],
    }


def _preliminary_groups(leads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[str, list[tuple[dict[str, Any], str]]] = defaultdict(list)
    for lead in leads:
        identity, reason = _identity_key(lead)
        buckets[identity].append((lead, reason))
    result = []
    for identity in sorted(buckets):
        entries = buckets[identity]
        members = [entry[0] for entry in entries]
        stable_key = "identity-" + _sha256(identity)[:20]
        result.append(
            {
                "stableKey": stable_key,
                "identitySignal": identity,
                "members": members,
                "memberReasons": {member["id"]: reason for member, reason in entries},
                "organization": _choose_text([member["organization"] for member in members]),
                "program": _choose_text([member["program"] for member in members]),
                "website": _choose_url([member["website"] for member in members]),
                "normalizedOrganizations": {
                    member["normalizedOrganization"] for member in members
                    if member["normalizedOrganization"]
                },
                "normalizedPrograms": {
                    member["normalizedProgram"] for member in members
                    if member["normalizedProgram"]
                },
                "roleFamilies": {
                    _identity_key(member)[0].split("|", 1)[0] for member in members
                },
            }
        )
    return result


def _suggestions(
    groups: list[dict[str, Any]], decisions: dict[tuple[str, str], str]
) -> list[dict[str, Any]]:
    result = []
    for index, left in enumerate(groups):
        for right in groups[index + 1 :]:
            reason = ""
            if left["roleFamilies"] != right["roleFamilies"]:
                continue
            same_organization = bool(
                left["normalizedOrganizations"] & right["normalizedOrganizations"]
            )
            same_program = bool(left["normalizedPrograms"] & right["normalizedPrograms"])
            if same_organization and bool(left["program"]) != bool(right["program"]):
                reason = "Same organization; one response names a program and the other names only the organization."
            elif same_program and left["normalizedOrganizations"] != right["normalizedOrganizations"]:
                reason = "Same normalized program name with different or missing organization identity."
            elif left["website"] and left["website"] == right["website"]:
                reason = "Same normalized official URL but different submitted identity text."
            if not reason:
                continue
            pair = tuple(sorted((left["stableKey"], right["stableKey"])))
            result.append(
                {
                    "leftKey": pair[0],
                    "rightKey": pair[1],
                    "left": {
                        "displayName": left["program"] or left["organization"] or left["website"],
                        "organization": left["organization"],
                        "program": left["program"],
                        "sources": sorted({member["sourceLabel"] for member in left["members"]}),
                    },
                    "right": {
                        "displayName": right["program"] or right["organization"] or right["website"],
                        "organization": right["organization"],
                        "program": right["program"],
                        "sources": sorted({member["sourceLabel"] for member in right["members"]}),
                    },
                    "reason": reason,
                    "status": decisions.get(pair, "pending"),
                }
            )
    return result


def _merged_groups(
    preliminary: list[dict[str, Any]],
    suggestions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    parent = {group["stableKey"]: group["stableKey"] for group in preliminary}

    def find(key: str) -> str:
        while parent[key] != key:
            parent[key] = parent[parent[key]]
            key = parent[key]
        return key

    def union(left: str, right: str) -> None:
        left_root, right_root = find(left), find(right)
        if left_root != right_root:
            first, second = sorted((left_root, right_root))
            parent[second] = first

    for suggestion in suggestions:
        if suggestion["status"] == "same":
            union(suggestion["leftKey"], suggestion["rightKey"])
    components: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for group in preliminary:
        components[find(group["stableKey"])].append(group)
    decisions_by_key: dict[str, set[str]] = defaultdict(set)
    for suggestion in suggestions:
        decisions_by_key[suggestion["leftKey"]].add(suggestion["status"])
        decisions_by_key[suggestion["rightKey"]].add(suggestion["status"])
    result = []
    for groups in components.values():
        preliminary_keys = sorted(group["stableKey"] for group in groups)
        members = [member for group in groups for member in group["members"]]
        members.sort(
            key=lambda member: (
                member["sourceLabel"].casefold(),
                member["sourceOrdinal"],
                member["normalizedOrganization"],
                member["normalizedProgram"],
            )
        )
        organization = _choose_text([member["organization"] for member in members])
        program = _choose_text([member["program"] for member in members])
        website = _choose_url([member["website"] for member in members])
        statuses = {status for key in preliminary_keys for status in decisions_by_key[key]}
        if len(groups) > 1:
            consolidation_state = "reviewed-merge"
            stable_key = "merged-" + _sha256(preliminary_keys)[:20]
        elif "separate" in statuses:
            consolidation_state = "reviewed-separate"
            stable_key = preliminary_keys[0]
        elif statuses & {"pending", "unresolved"}:
            consolidation_state = "unresolved"
            stable_key = preliminary_keys[0]
        else:
            consolidation_state = "exact"
            stable_key = preliminary_keys[0]
        reasons = {}
        signals = {}
        for group in groups:
            for member in group["members"]:
                reasons[member["id"]] = (
                    "human-reviewed same identity"
                    if len(groups) > 1
                    else group["memberReasons"][member["id"]]
                )
                signals[member["id"]] = group["identitySignal"]
        result.append(
            {
                "stableKey": stable_key,
                "preliminaryKeys": preliminary_keys,
                "displayName": program or organization or website or "Unresolved lead",
                "organization": organization,
                "program": program,
                "website": website,
                "routedRole": _route_role(members, program, organization),
                "consolidationState": consolidation_state,
                "members": [
                    {
                        **member,
                        "membershipReason": reasons[member["id"]],
                        "deterministicSignal": signals[member["id"]],
                    }
                    for member in members
                ],
            }
        )
    return sorted(result, key=lambda group: group["stableKey"])


def _validate_identity_decisions(
    preliminary: list[dict[str, Any]], suggestions: list[dict[str, Any]]
) -> None:
    parent = {group["stableKey"]: group["stableKey"] for group in preliminary}

    def find(key: str) -> str:
        while parent[key] != key:
            parent[key] = parent[parent[key]]
            key = parent[key]
        return key

    def union(left: str, right: str) -> None:
        left_root, right_root = find(left), find(right)
        if left_root != right_root:
            first, second = sorted((left_root, right_root))
            parent[second] = first

    for suggestion in suggestions:
        if suggestion["status"] == "same":
            union(suggestion["leftKey"], suggestion["rightKey"])
    for suggestion in suggestions:
        if suggestion["status"] == "separate" and find(suggestion["leftKey"]) == find(suggestion["rightKey"]):
            raise ValueError("Identity decisions conflict: one pair is both merged and kept separate")
    program_names: dict[str, set[str]] = defaultdict(set)
    for group in preliminary:
        program_names[find(group["stableKey"])].update(group["normalizedPrograms"])
    if any(len(names) > 1 for names in program_names.values()):
        raise ValueError("Identity decision would merge two distinct named programs")


def consolidate_manual_discovery(
    store: ResearchStore, run_id: int, duplicate_index: DuplicateIndex | None = None
) -> dict[str, Any]:
    run = store.get_run(run_id)
    if not run or run["runKind"] != "manual-discovery":
        raise ValueError("Manual discovery run not found")
    if run["status"] != "running":
        snapshot = store.manual_consolidation_snapshot(run_id)
        if snapshot is None:
            raise ValueError("Finished manual discovery has no consolidation snapshot")
        snapshot["suggestions"] = []
        return snapshot
    contributions = store.list_manual_contributions(run_id)
    if not contributions:
        raise ValueError("Add at least one contribution before consolidating leads")
    if any(item["parseStatus"] == "error" for item in contributions):
        raise ValueError("Correct or delete responses with parse errors before consolidating leads")
    leads = store.manual_leads_for_consolidation(run_id)
    preliminary = _preliminary_groups(leads)
    decision_rows = store.manual_identity_decisions(run_id)
    decisions = {
        (row["leftKey"], row["rightKey"]): row["decision"] for row in decision_rows
    }
    suggestions = _suggestions(preliminary, decisions)
    _validate_identity_decisions(preliminary, suggestions)
    groups = _merged_groups(preliminary, suggestions)
    matcher = duplicate_index or DuplicateIndex(store)
    for group in groups:
        group["duplicateMatches"] = matcher.match(
            _candidate_shape(group), import_id=run["sourceImportId"], limit=3
        ) if run["sourceImportId"] else []
    role_counts = Counter(group["routedRole"] for group in groups)
    submitted_rows = sum(
        len(item["parsed"].get("leads", []))
        for item in contributions
        if isinstance(item.get("parsed"), dict) and isinstance(item["parsed"].get("leads"), list)
    )
    funnel = {
        "submittedRows": submitted_rows,
        "parsedLeads": len(leads),
        "exactDuplicateRows": max(0, len(leads) - len(preliminary)),
        "consolidatedIdentities": len(groups),
        "possiblePackageDuplicates": sum(bool(group["duplicateMatches"]) for group in groups),
        "providerProgramIdentities": role_counts["program"] + role_counts["provider-organization"],
        "accessPointIdentities": role_counts["access-point"],
        "routingDirectoryIdentities": role_counts["routing-source"] + role_counts["directory"],
        "outreachInitiatives": role_counts["outreach-initiative"],
        "unresolvedIdentities": role_counts["unresolved"],
        "candidateIdentities": sum(group["routedRole"] in DIRECT_ROLES for group in groups),
        "pendingIdentityDecisions": sum(item["status"] == "pending" for item in suggestions),
    }
    input_sha256 = _sha256(
        [
            {
                "source": item["sourceLabel"],
                "position": item["sourcePosition"],
                "sha256": item["rawSha256"],
                "parserVersion": item["parserVersion"],
            }
            for item in contributions
        ]
    )
    store.replace_manual_consolidation(run_id, input_sha256, groups, funnel)
    snapshot = manual_consolidation_view(store, run_id)
    if snapshot is None:  # pragma: no cover - guarded by replacement above
        raise RuntimeError("Consolidation snapshot could not be read")
    return snapshot


def manual_consolidation_view(
    store: ResearchStore, run_id: int
) -> dict[str, Any] | None:
    snapshot = store.manual_consolidation_snapshot(run_id)
    if snapshot is None:
        return None
    preliminary = _preliminary_groups(store.manual_leads_for_consolidation(run_id))
    decisions = {
        (row["leftKey"], row["rightKey"]): row["decision"]
        for row in store.manual_identity_decisions(run_id)
    }
    snapshot["suggestions"] = _suggestions(preliminary, decisions)
    return snapshot


def record_manual_identity_decision(
    store: ResearchStore,
    run_id: int,
    left_key: str,
    right_key: str,
    decision: str,
    duplicate_index: DuplicateIndex | None = None,
) -> dict[str, Any]:
    current = consolidate_manual_discovery(store, run_id, duplicate_index)
    pair = tuple(sorted((str(left_key), str(right_key))))
    if not any(
        (item["leftKey"], item["rightKey"]) == pair for item in current["suggestions"]
    ):
        raise ValueError("Identity suggestion is no longer current")
    proposed = []
    for item in current["suggestions"]:
        value = dict(item)
        if (value["leftKey"], value["rightKey"]) == pair:
            value["status"] = decision
        proposed.append(value)
    _validate_identity_decisions(
        _preliminary_groups(store.manual_leads_for_consolidation(run_id)), proposed
    )
    store.save_manual_identity_decision(run_id, pair[0], pair[1], decision)
    return consolidate_manual_discovery(store, run_id, duplicate_index)


def _candidate_from_snapshot_group(group: dict[str, Any]) -> dict[str, Any]:
    members = group["members"]
    locations = sorted(
        {member["locationOrServiceArea"] for member in members if member["locationOrServiceArea"]},
        key=str.casefold,
    )
    relevance = sorted(
        {
            (member["sourceLabel"], member["whyRelevant"])
            for member in members
            if member["whyRelevant"]
        },
        key=lambda value: (value[0].casefold(), value[1].casefold()),
    )
    uncertainty = sorted(
        {
            (member["sourceLabel"], member["uncertainty"])
            for member in members
            if member["uncertainty"]
        },
        key=lambda value: (value[0].casefold(), value[1].casefold()),
    )
    return {
        "name": group["displayName"],
        "organizationName": group["organization"],
        "programName": group["program"],
        "website": group["website"],
        "resourceType": group["routedRole"],
        "geography": locations[0] if len(locations) == 1 else locations,
        "serviceNeed": relevance[0][1] if relevance else "",
        "uncertainties": [value for _source, value in uncertainty],
        "sources": [
            {
                "source": member["sourceLabel"],
                "url": member["website"],
                "note": member["whyRelevant"],
            }
            for member in members
            if member["website"]
        ],
        "manualDiscoveryProvenance": {
            "groupKey": group["stableKey"],
            "consolidationState": group["consolidationState"],
            "routedRole": group["routedRole"],
            "sourceCount": len({member["sourceLabel"] for member in members}),
            "members": [
                {
                    "leadId": member["id"],
                    "sourceLabel": member["sourceLabel"],
                    "sourceOrdinal": member["sourceOrdinal"],
                    "submittedOrganization": member["organization"],
                    "submittedProgram": member["program"],
                    "submittedWebsite": member["website"],
                    "declaredLeadType": member["leadType"],
                    "locationOrServiceArea": member["locationOrServiceArea"],
                    "whyRelevant": member["whyRelevant"],
                    "uncertainty": member["uncertainty"],
                    "membershipReason": member["membershipReason"],
                    "deterministicSignal": member["deterministicSignal"],
                }
                for member in members
            ],
            "relevanceAlternatives": [
                {"sourceLabel": source, "value": value} for source, value in relevance
            ],
            "uncertaintyAlternatives": [
                {"sourceLabel": source, "value": value} for source, value in uncertainty
            ],
            "duplicateMatches": group["duplicateMatches"],
        },
    }


def finish_manual_discovery(store: ResearchStore, run_id: int) -> dict[str, Any]:
    result = manual_consolidation_view(store, run_id)
    if result is None:
        raise ValueError("Consolidate the current responses before finishing discovery")
    if result["funnel"]["pendingIdentityDecisions"]:
        raise ValueError("Review each ambiguous identity before finishing discovery")
    candidates = []
    for group in result["groups"]:
        if group["routedRole"] not in DIRECT_ROLES:
            continue
        candidates.append(
            {
                "candidate": _candidate_from_snapshot_group(group),
                "match": group["duplicateMatches"][0] if group["duplicateMatches"] else None,
            }
        )
    return store.finish_manual_consolidated_run(run_id, candidates, result["funnel"])
