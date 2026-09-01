from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any

from .storage import ResearchStore
from .taxonomy_category_proposal import RETIRED_CATEGORY_IDS
from .taxonomy_study import TaxonomyStudyError


APPROVED_CATEGORY_RULES = {
    "parentingAndChildDevelopment": (
        "Keep Parenting & Child Development as one need Category. Child Care, Parenting "
        "Education, Early Intervention, Home Visiting, and similar distinctions may be Types."
    ),
    "independentLiving": (
        "Keep the familiar Independent Living label and explicitly include community "
        "participation, adaptive recreation, communication access, and self-advocacy."
    ),
    "caregivingOverlap": (
        "Adult-day and in-home programs may appear in both Independent Living and "
        "Caregiving when they genuinely address both needs."
    ),
    "categoryEvidence": (
        "Assign a Category when the provider directly delivers the service or operates a "
        "named, accountable navigation pathway for it. A vague referral promise is insufficient."
    ),
}

TYPE_REVIEW_RULES = {
    "definition": (
        "A Type describes the particular way a resource addresses the selected need."
    ),
    "placement": "Types are offered only after entering one Category.",
    "selection": "Multiple selected Types are ORed.",
    "optional": (
        "A resource/category relationship may legitimately need no Type. Never invent a "
        "Type merely to fill a blank."
    ),
    "dispositions": ["assigned-types", "no-type-needed", "unresolved"],
    "labels": (
        "Missionary-facing Type button labels must be concise; longer definitions and "
        "research guidance belong outside the button label."
    ),
}


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _category_filters(resource: dict[str, Any], category_id: str) -> list[str]:
    values = resource.get("categoryFilters")
    if not isinstance(values, dict):
        return []
    selected = values.get(category_id)
    if not isinstance(selected, list):
        return []
    result: list[str] = []
    for value in selected:
        label = str(value or "").strip()
        if label and label not in result:
            result.append(label)
    return result


def _latest_category_proposal(study: dict[str, Any]) -> dict[str, Any]:
    proposals = study.get("categoryRedistributionProposals") or []
    if not proposals:
        raise TaxonomyStudyError("The taxonomy study has no Category proposal")
    return proposals[-1]


def approve_categories_and_prepare_type_review(
    store: ResearchStore,
    study_id: int,
) -> dict[str, Any]:
    study = store.get_taxonomy_study(study_id)
    if study is None:
        raise TaxonomyStudyError("Taxonomy study not found")
    proposal_record = _latest_category_proposal(study)
    rules_sha256 = _sha256(APPROVED_CATEGORY_RULES)
    store.approve_taxonomy_category_proposal(
        study_id,
        proposal_record["proposalSha256"],
        APPROVED_CATEGORY_RULES,
        rules_sha256,
        source="michael-approved-category-foundation",
        note=(
            "Michael approved all four Category judgments before category-by-category "
            "Type design."
        ),
    )
    refreshed = store.get_taxonomy_study(study_id)
    if refreshed is None:  # pragma: no cover
        raise RuntimeError("Approved taxonomy study could not be read")
    packets = build_type_review_packets(refreshed)
    store.create_taxonomy_type_review_packets(
        study_id,
        packets,
        based_on_proposal_sha256=proposal_record["proposalSha256"],
    )
    saved_packets = store.list_taxonomy_type_review_packets(study_id)
    return {
        "studyId": int(study_id),
        "status": "types-review",
        "proposalSha256": proposal_record["proposalSha256"],
        "rulesSha256": rules_sha256,
        "categoryCount": len(saved_packets),
        "categories": [
            {
                "categoryId": item["categoryId"],
                "categoryLabel": item["categoryLabel"],
                "resourceCount": item["packet"]["resourceCount"],
                "status": item["status"],
                "packetSha256": item["packetSha256"],
            }
            for item in saved_packets
        ],
    }


def build_type_review_packets(study: dict[str, Any]) -> list[dict[str, Any]]:
    proposal_record = _latest_category_proposal(study)
    proposal = proposal_record["proposal"]
    approval = study.get("categoryApproval")
    if not approval or approval["proposalSha256"] != proposal_record["proposalSha256"]:
        raise TaxonomyStudyError("Approve the Category foundation before Types review")
    if approval["rules"] != APPROVED_CATEGORY_RULES:
        raise TaxonomyStudyError("The approved Category rules do not match this Types review")

    current_categories = {
        str(item["id"]): {
            "id": str(item["id"]),
            "label": str(item.get("label") or item["id"]),
            "currentTypes": list(item.get("types") or []),
            "origin": "connected-package",
        }
        for item in study["corpus"]["categories"]
        if str(item["id"]) not in RETIRED_CATEGORY_IDS
    }
    for item in proposal["proposedNeedCategories"]:
        current_categories[str(item["id"])] = {
            "id": str(item["id"]),
            "label": str(item["label"]),
            "currentTypes": [],
            "origin": "category-review-proposal",
            "definition": deepcopy(item),
        }
    assignment_by_resource = {
        str(item["resourceId"]): item for item in proposal["assignments"]
    }
    relations: dict[str, list[dict[str, Any]]] = {
        category_id: [] for category_id in current_categories
    }
    for item in study["corpus"]["resources"]:
        resource_id = str(item["resourceId"])
        assignment = assignment_by_resource.get(resource_id)
        category_ids = (
            list(assignment["proposedNeedCategories"])
            if assignment else list(item["categories"])
        )
        invalid = sorted(set(category_ids) - set(current_categories))
        if invalid:
            raise TaxonomyStudyError(
                f"Resource {resource_id} has Categories outside the approved foundation: "
                + ", ".join(invalid)
            )
        for category_id in category_ids:
            relations[category_id].append({
                "corpusKey": item["corpusKey"],
                "resourceId": resource_id,
                "name": item["name"],
                "origin": item["origin"],
                "priorCategoryIds": list(item["categories"]),
                "currentAssignedTypes": _category_filters(
                    item["resource"], category_id
                ),
                "requiredDisposition": (
                    "assigned-types | no-type-needed | unresolved"
                ),
                "resource": deepcopy(item["resource"]),
            })
    packets: list[dict[str, Any]] = []
    for category_id, category in current_categories.items():
        resources = sorted(
            relations[category_id],
            key=lambda item: (item["name"].casefold(), item["resourceId"]),
        )
        packet = {
            "schemaVersion": 1,
            "studyId": int(study["id"]),
            "corpusSha256": study["corpusSha256"],
            "categoryProposalSha256": proposal_record["proposalSha256"],
            "category": deepcopy(category),
            "resourceCount": len(resources),
            "typeReviewRules": deepcopy(TYPE_REVIEW_RULES),
            "resources": resources,
            "workedExamples": [
                {
                    "resource": "Online class that accommodates Spanish speakers",
                    "category": "Education",
                    "type": "Online",
                    "for": "Spanish-speaking",
                },
                {
                    "resource": "General clinic with no meaningful service-mode distinction",
                    "category": "Medical, Dental, Vision",
                    "typeDisposition": "no-type-needed",
                },
            ],
        }
        packets.append({
            "categoryId": category_id,
            "categoryLabel": category["label"],
            "packet": packet,
            "packetSha256": _sha256(packet),
        })
    packets.sort(key=lambda item: (item["categoryLabel"].casefold(), item["categoryId"]))
    if len(packets) != 19:
        raise TaxonomyStudyError(
            f"Expected 19 approved need Categories, found {len(packets)}"
        )
    return packets


def taxonomy_types_status(
    store: ResearchStore,
    study_id: int,
) -> dict[str, Any]:
    packets = store.list_taxonomy_type_review_packets(study_id)
    revisions = store.list_taxonomy_type_design_revisions(study_id)
    latest_by_category: dict[str, dict[str, Any]] = {}
    for revision in revisions:
        latest_by_category[revision["categoryId"]] = revision
    categories: list[dict[str, Any]] = []
    for packet in packets:
        design = latest_by_category.get(packet["categoryId"])
        categories.append({
            "categoryId": packet["categoryId"],
            "categoryLabel": packet["categoryLabel"],
            "status": packet["status"],
            "resourceCount": packet["packet"]["resourceCount"],
            "designRevision": design["revision"] if design else None,
            "typeCount": len(design["design"]["types"]) if design else 0,
            "noTypeNeededCount": (
                design["design"]["coverage"]["noTypeNeededCount"] if design else 0
            ),
            "unresolvedCount": (
                design["design"]["coverage"]["unresolvedCount"] if design else 0
            ),
        })
    return {
        "studyId": int(study_id),
        "categoryCount": len(categories),
        "designedCategoryCount": sum(
            item["status"] in ("designed", "reviewed") for item in categories
        ),
        "reviewedCategoryCount": sum(
            item["status"] == "reviewed" for item in categories
        ),
        "categories": categories,
    }
