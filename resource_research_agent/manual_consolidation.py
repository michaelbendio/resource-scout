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
PROGRAM_TOKEN_STOPWORDS = {"a", "an", "and", "for", "of", "the", "to"}
PHONE_LETTERS = str.maketrans(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
    "2223334445556667777888999922233344455566677778889999",
)


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


def _presentation_name(organization: str, program: str, website: str = "") -> str:
    if organization and program:
        return f"{organization} · {program}"
    return program or organization or website or "Unresolved lead"


def _organization_group_name(members: list[dict[str, Any]], fallback: str) -> str:
    names = {member["organization"].strip() for member in members if member["organization"].strip()}
    if not names:
        return fallback
    return sorted(names, key=lambda value: (len(value.split()), len(value), value.casefold()))[0]


def _identity_tokens(value: str) -> tuple[str, ...]:
    return tuple(token for token in value.split() if token)


def _significant_program_tokens(value: str) -> set[str]:
    return {
        token for token in _identity_tokens(value)
        if token not in PROGRAM_TOKEN_STOPWORDS
    }


def _phone_keys(group: dict[str, Any]) -> set[str]:
    result: set[str] = set()
    for member in group["members"]:
        for chunk in re.findall(r"[+()A-Za-z0-9.-]{7,}", member["phone"] or ""):
            if not any(character.isdigit() for character in chunk):
                continue
            digits = re.sub(r"\D", "", chunk.translate(PHONE_LETTERS))
            if len(digits) == 11 and digits.startswith("1"):
                digits = digits[1:]
            if len(digits) == 10:
                result.add(digits)
    return result


def _organization_family_matches(left: dict[str, Any], right: dict[str, Any]) -> bool:
    for left_name in left["normalizedOrganizations"]:
        left_tokens = _identity_tokens(left_name)
        for right_name in right["normalizedOrganizations"]:
            right_tokens = _identity_tokens(right_name)
            if left_name == right_name:
                return True
            shorter, longer = sorted((left_tokens, right_tokens), key=len)
            if len(shorter) >= 2 and longer[:len(shorter)] == shorter:
                return True
    return False


def _program_alias_reason(left: dict[str, Any], right: dict[str, Any]) -> str:
    if not _organization_family_matches(left, right):
        return ""
    left_programs = sorted(left["normalizedPrograms"])
    right_programs = sorted(right["normalizedPrograms"])
    if not left_programs or not right_programs:
        return ""
    if left["roleFamilies"] == right["roleFamilies"] == {"access-point"}:
        if _phone_keys(left) & _phone_keys(right):
            return "Same organization and access-point phone number."
    for left_program in left_programs:
        left_tokens = _identity_tokens(left_program)
        left_significant = _significant_program_tokens(left_program)
        for right_program in right_programs:
            right_tokens = _identity_tokens(right_program)
            right_significant = _significant_program_tokens(right_program)
            shorter, longer = sorted((left_tokens, right_tokens), key=len)
            if len(shorter) >= 2 and longer[:len(shorter)] == shorter:
                return "Same organization and one program name extends the other with descriptive wording."
            if left_significant and right_significant:
                similarity = len(left_significant & right_significant) / len(
                    left_significant | right_significant
                )
                if min(len(left_significant), len(right_significant)) >= 2 and similarity >= 0.75:
                    return "Same organization and strongly overlapping program names."
            left_initialism = "".join(token[0] for token in left_tokens if token)
            right_initialism = "".join(token[0] for token in right_tokens if token)
            if len(left_initialism) >= 4 and left_initialism in right_tokens:
                return "Same organization and acronym/expanded program name."
            if len(right_initialism) >= 4 and right_initialism in left_tokens:
                return "Same organization and acronym/expanded program name."
    return ""


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
        "organization": group["organization"],
        "program": group["program"],
        "organizationName": group["organization"],
        "programName": group["program"],
        "website": group["website"],
    }


def _check_result(
    state: str, note: str, members: list[dict[str, Any]]
) -> dict[str, Any]:
    return {
        "state": state,
        "note": note,
        "sources": [
            {"leadId": member["id"], "sourceLabel": member["sourceLabel"]}
            for member in members
        ],
    }


def _lightweight_checks(
    group: dict[str, Any], run: dict[str, Any]
) -> dict[str, dict[str, Any]]:
    members = group["members"]
    identity_state = "present" if group["organization"] or group["program"] else "uncertain"
    identity_note = (
        "At least one chat response supplied an organization or program name."
        if identity_state == "present"
        else "Confirm the organization or program name."
    )

    geography_values = [member["locationOrServiceArea"] for member in members if member["locationOrServiceArea"]]
    geography_text = " ".join(geography_values).casefold()
    geography_negative = bool(
        re.search(r"\b(?:does not serve|not serving|outside (?:the )?(?:service area|target area)|wrong (?:city|state))\b", geography_text)
    )
    geography_tentative = bool(
        re.search(r"\b(?:possibly|may serve|uncertain|unknown|confirm|appears to serve)\b", geography_text)
    )
    if geography_negative:
        geography_state = "conflicting"
        geography_note = "The chat responses disagree about whether this resource serves the area."
    elif not geography_values or geography_tentative:
        geography_state = "uncertain"
        geography_note = "Confirm that this resource serves the area."
    else:
        geography_state = "present"
        geography_note = "At least one chat response says this resource may serve the area."

    relevance_values = [member["whyRelevant"] for member in members if member["whyRelevant"]]
    relevance_text = " ".join(relevance_values).casefold()
    relevance_negative = bool(
        re.search(r"\b(?:wrong category|unrelated|not (?:a |an )?(?:provider|service|program))\b", relevance_text)
    )
    relevance_tentative = bool(
        re.search(r"\b(?:possibly|uncertain|unknown|may be|confirm relevance)\b", relevance_text)
    )
    if relevance_negative:
        category_state = "conflicting"
        category_note = "The chat responses disagree about whether this resource fits the category."
    elif not relevance_values or relevance_tentative:
        category_state = "uncertain"
        category_note = "Confirm that this resource fits the category."
    else:
        category_state = "present"
        category_note = f"At least one chat response connects this resource with {run['targetCategoryLabel']}."

    all_text = " ".join(
        member["whyRelevant"] + " " + member["uncertainty"] for member in members
    ).casefold()
    stale_signal = bool(
        re.search(r"\b(?:closed|defunct|historical|formerly|stale|ended|discontinued)\b", all_text)
    )
    current_signal = bool(group["website"]) or bool(
        re.search(
            r"\b(?:currently (?:open|operating|offers|provides|serves)|official (?:site|website)|active program|202[4-9])\b",
            all_text,
        )
    )
    if stale_signal and current_signal:
        current_state = "conflicting"
        current_note = "The chat responses conflict about whether this resource is still operating."
    elif stale_signal or not current_signal:
        current_state = "uncertain"
        current_note = "Confirm that the organization is still operating and currently offers this service."
    else:
        current_state = "present"
        current_note = "A chat response supplied a website or said the service is currently available."

    access_signal = bool(group["website"]) or bool(
        re.search(r"\b(?:intake|apply|application|enroll|appointment|call|referral|walk-in|locator|directory)\b", all_text)
    )
    no_access_signal = bool(
        re.search(r"\b(?:no public (?:intake|access)|no access path|not open to (?:the )?public)\b", all_text)
    )
    if group["routedRole"] == "outreach-initiative":
        access_state = "not-applicable"
        access_note = "This appears to be a limited initiative rather than a service people contact directly."
    elif access_signal and no_access_signal:
        access_state = "conflicting"
        access_note = "The chat responses conflict about whether people can contact this service directly."
    elif access_signal:
        access_state = "present"
        access_note = "A chat response supplied a website or a possible way to contact or apply."
    else:
        access_state = "uncertain"
        access_note = "Confirm how someone contacts, applies for, or is referred to this service."

    return {
        "identity": _check_result(identity_state, identity_note, members),
        "geography": _check_result(geography_state, geography_note, members),
        "categoryRelevance": _check_result(category_state, category_note, members),
        "currentSignal": _check_result(current_state, current_note, members),
        "publicAccess": _check_result(access_state, access_note, members),
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
            automatic_reason = _program_alias_reason(left, right)
            if automatic_reason:
                reason = automatic_reason
            elif same_organization and bool(left["program"]) != bool(right["program"]):
                reason = "Same organization; one response names a program and the other names only the organization."
            elif same_program and left["normalizedOrganizations"] != right["normalizedOrganizations"]:
                reason = "Same normalized program name with different or missing organization identity."
            if not reason:
                continue
            pair = tuple(sorted((left["stableKey"], right["stableKey"])))
            result.append(
                {
                    "leftKey": pair[0],
                    "rightKey": pair[1],
                    "left": {
                        "displayName": _presentation_name(
                            left["organization"], left["program"], left["website"]
                        ),
                        "organization": left["organization"],
                        "program": left["program"],
                        "sources": sorted({member["sourceLabel"] for member in left["members"]}),
                    },
                    "right": {
                        "displayName": _presentation_name(
                            right["organization"], right["program"], right["website"]
                        ),
                        "organization": right["organization"],
                        "program": right["program"],
                        "sources": sorted({member["sourceLabel"] for member in right["members"]}),
                    },
                    "reason": reason,
                    "status": "same" if automatic_reason else decisions.get(pair, "pending"),
                    "automatic": bool(automatic_reason),
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
        if suggestion["status"] == "same" and suggestion.get("automatic"):
            union(suggestion["leftKey"], suggestion["rightKey"])
    for suggestion in suggestions:
        if suggestion["status"] == "same" and not suggestion.get("automatic"):
            union(suggestion["leftKey"], suggestion["rightKey"])
    components: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for group in preliminary:
        components[find(group["stableKey"])].append(group)
    decisions_by_key: dict[str, set[str]] = defaultdict(set)
    manual_same_pairs: set[tuple[str, str]] = set()
    for suggestion in suggestions:
        decisions_by_key[suggestion["leftKey"]].add(suggestion["status"])
        decisions_by_key[suggestion["rightKey"]].add(suggestion["status"])
        if suggestion["status"] == "same" and not suggestion.get("automatic"):
            manual_same_pairs.add((suggestion["leftKey"], suggestion["rightKey"]))
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
        has_manual_merge = any(
            left in preliminary_keys and right in preliminary_keys
            for left, right in manual_same_pairs
        )
        if len(groups) > 1:
            consolidation_state = "reviewed-merge" if has_manual_merge else "exact"
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
                    (
                        "human-reviewed same identity"
                        if has_manual_merge
                        else "automatic same-program alias consolidation"
                    )
                    if len(groups) > 1
                    else group["memberReasons"][member["id"]]
                )
                signals[member["id"]] = group["identitySignal"]
        result.append(
            {
                "stableKey": stable_key,
                "preliminaryKeys": preliminary_keys,
                "displayName": _presentation_name(organization, program, website),
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
        if suggestion["status"] == "same" and suggestion.get("automatic"):
            union(suggestion["leftKey"], suggestion["rightKey"])
    automatic_program_families = {
        group["stableKey"]: find(group["stableKey"])
        for group in preliminary
        if group["normalizedPrograms"]
    }
    for suggestion in suggestions:
        if suggestion["status"] == "same" and not suggestion.get("automatic"):
            union(suggestion["leftKey"], suggestion["rightKey"])
    for suggestion in suggestions:
        if suggestion["status"] == "separate" and find(suggestion["leftKey"]) == find(suggestion["rightKey"]):
            raise ValueError("Identity decisions conflict: one pair is both merged and kept separate")
    program_families: dict[str, set[str]] = defaultdict(set)
    for group in preliminary:
        family = automatic_program_families.get(group["stableKey"])
        if family:
            program_families[find(group["stableKey"])].add(family)
    if any(len(families) > 1 for families in program_families.values()):
        raise ValueError("Identity decision would merge two distinct named programs")


def consolidate_manual_discovery(
    store: ResearchStore, run_id: int, duplicate_index: DuplicateIndex | None = None
) -> dict[str, Any]:
    run = store.get_run(run_id)
    if not run:
        raise ValueError("Discovery run not found")
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
        group["checks"] = _lightweight_checks(group, run)
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
        "sameIdentityDecisions": sum(item["status"] == "same" for item in suggestions),
        "separateIdentityDecisions": sum(item["status"] == "separate" for item in suggestions),
        "unresolvedIdentityDecisions": sum(item["status"] == "unresolved" for item in suggestions),
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
    preliminary_key_by_lead = {
        member["id"]: group["stableKey"]
        for group in preliminary
        for member in group["members"]
    }
    for group in snapshot["groups"]:
        group["preliminaryKeys"] = sorted(
            {
                preliminary_key_by_lead[member["id"]]
                for member in group["members"]
            }
        )
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
    current = manual_consolidation_view(store, run_id)
    if current is None:
        raise ValueError("Consolidate the manual discovery responses before reviewing identities")
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


def leave_pending_manual_identities_unresolved(
    store: ResearchStore,
    run_id: int,
    duplicate_index: DuplicateIndex | None = None,
) -> dict[str, Any]:
    current = consolidate_manual_discovery(store, run_id, duplicate_index)
    pending = [
        {
            "leftKey": item["leftKey"],
            "rightKey": item["rightKey"],
            "decision": "unresolved",
        }
        for item in current["suggestions"]
        if item["status"] == "pending"
    ]
    if not pending:
        raise ValueError("No pending identity pairs remain")
    store.save_manual_identity_decisions(run_id, pending)
    return consolidate_manual_discovery(store, run_id, duplicate_index)


def _candidate_from_snapshot_group(
    group: dict[str, Any], possible_relationships: list[dict[str, Any]]
) -> dict[str, Any]:
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
    phones = sorted({member["phone"] for member in members if member["phone"]}, key=str.casefold)
    addresses = sorted(
        {member["address"] for member in members if member["address"]}, key=str.casefold
    )
    follow_up_questions = {
        "identity": "Confirm the organization or program name.",
        "geography": "Confirm that this resource serves the area.",
        "categoryRelevance": "Confirm that this resource fits the category.",
        "currentSignal": "Confirm that the organization is still operating and currently offers this service.",
        "publicAccess": "Confirm how someone contacts, applies for, or is referred to this service.",
    }
    return {
        "name": group["program"] or group["organization"] or group["displayName"],
        "presentationName": group["displayName"],
        "organizationName": group["organization"],
        "organizationGroupName": _organization_group_name(members, group["organization"]),
        "programName": group["program"],
        "website": group["website"],
        "phone": phones[0] if phones else "",
        "additionalPhoneNumbers": phones[1:],
        "address": addresses[0] if addresses else "",
        "additionalAddresses": addresses[1:],
        "resourceType": group["routedRole"],
        "geography": locations[0] if len(locations) == 1 else locations,
        "serviceNeed": relevance[0][1] if relevance else "",
        "uncertainties": [value for _source, value in uncertainty],
        "unknowns": [
            follow_up_questions[name]
            for name, check in group["checks"].items()
            if check["state"] in {"uncertain", "conflicting"}
        ],
        "possibleRelatedSubmissions": possible_relationships,
        "manualDiscoveryChecks": group["checks"],
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
                    "researchFocusKey": member.get("researchFocusKey") or "",
                    "researchFocusLabel": member.get("researchFocusLabel") or "",
                    "researchPassKind": member.get("researchPassKind") or "",
                    "sourceOrdinal": member["sourceOrdinal"],
                    "submittedOrganization": member["organization"],
                    "submittedProgram": member["program"],
                    "submittedWebsite": member["website"],
                    "submittedPhone": member["phone"],
                    "submittedAddress": member["address"],
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
            "checks": group["checks"],
            "possibleRelatedSubmissions": possible_relationships,
        },
    }


def finish_manual_discovery(store: ResearchStore, run_id: int) -> dict[str, Any]:
    result = manual_consolidation_view(store, run_id)
    if result is None:
        raise ValueError("Consolidate the current responses before finishing discovery")
    possible_by_key: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for suggestion in result["suggestions"]:
        if suggestion["status"] not in {"pending", "unresolved"}:
            continue
        for own_key, other_key, other in (
            (suggestion["leftKey"], suggestion["rightKey"], suggestion["right"]),
            (suggestion["rightKey"], suggestion["leftKey"], suggestion["left"]),
        ):
            possible_by_key[own_key].append(
                {
                    "identityKeys": [other_key],
                    "displayName": other["displayName"],
                    "organization": other["organization"],
                    "program": other["program"],
                    "sources": other["sources"],
                    "reason": suggestion["reason"],
                    "reasons": [suggestion["reason"]],
                    "reviewState": suggestion["status"],
                }
            )
    candidates = []
    for group in result["groups"]:
        if group["routedRole"] not in DIRECT_ROLES:
            continue
        relationships_by_label: dict[str, dict[str, Any]] = {}
        for key in group["preliminaryKeys"]:
            for item in possible_by_key[key]:
                relationship_key = item["displayName"]
                existing = relationships_by_label.get(relationship_key)
                if existing is None:
                    relationships_by_label[relationship_key] = dict(item)
                else:
                    existing["identityKeys"] = sorted(
                        set(existing["identityKeys"]) | set(item["identityKeys"])
                    )
                    existing["sources"] = sorted(
                        set(existing["sources"]) | set(item["sources"]), key=str.casefold
                    )
                    existing["reasons"] = sorted(
                        set(existing["reasons"]) | set(item["reasons"]), key=str.casefold
                    )
        possible_relationships = sorted(
            relationships_by_label.values(),
            key=lambda item: (item["displayName"].casefold(), item["identityKeys"]),
        )
        candidates.append(
            {
                "candidate": _candidate_from_snapshot_group(group, possible_relationships),
                "match": group["duplicateMatches"][0] if group["duplicateMatches"] else None,
            }
        )
    return store.finish_manual_consolidated_run(run_id, candidates, result["funnel"])
