from __future__ import annotations

import hashlib
import json
from collections import Counter
from copy import deepcopy
from typing import Any

from .storage import ResearchStore
from .taxonomy_study import TaxonomyStudyError


NEW_CATEGORY_TYPE_DESIGNS: dict[str, dict[str, Any]] = {
    "parenting-child-development": {
        "types": [
            {
                "label": "Parenting Education",
                "definition": "Classes, coaching, or practical education for parents and caregivers.",
            },
            {
                "label": "Home Visiting",
                "definition": "Family support delivered through planned visits in the home.",
            },
            {
                "label": "Early Intervention",
                "definition": "Developmental evaluation or intervention for infants and young children.",
            },
            {
                "label": "Child Care",
                "definition": "Supervised care that enables work, school, safety, or family stability.",
            },
            {
                "label": "Early Learning",
                "definition": "Early-childhood learning and school-readiness programming.",
            },
            {
                "label": "Family Resource Center",
                "definition": "A multi-service family hub with activities, education, and navigation.",
            },
            {
                "label": "Family Reunification",
                "definition": "Support for restoring or strengthening parent-child relationships.",
            },
        ],
        "assignments": {
            "33b8cbd29cf68ac3a07e0fd8d984771b": ["Parenting Education"],
            "b48b75beadedb73dd0606ffb3dcc568d": ["Child Care", "Early Intervention"],
            "90ef7bed032bcd935b0f82e65f664917": ["Early Intervention"],
            "eb94f24384f8e51a2b237d7d8c507948": ["Early Intervention"],
            "067d28b529da7122c5d8c50ff1874faf": ["Early Intervention"],
            "193621d2449346f5eb4f3fe57535ad47": ["Family Reunification"],
            "1ed84b657420da445ac082991959b3f8": [
                "Parenting Education", "Early Learning", "Family Resource Center",
            ],
            "ed9cec6557722e44984887fb41637d6e": ["Parenting Education"],
            "2822ad624344c1ae4686dbbb665c3700": [
                "Parenting Education", "Early Learning", "Family Resource Center",
            ],
            "313775a628d6ace7912cbbd7fe30a8a3": [
                "Parenting Education", "Early Learning", "Family Resource Center",
            ],
            "38629d0e712141f7531b4cff4b0bfd53": "no-type-needed",
            "528e3dad283cd117ea2ff80b3bec333c": [
                "Parenting Education", "Family Reunification",
            ],
            "ba6cab830d60bb25c2039ae996392523": [
                "Parenting Education", "Child Care", "Early Learning",
            ],
            "a6043035dfbf51e34bad108416bca340": [
                "Parenting Education", "Early Learning", "Family Resource Center",
            ],
            "0df6bb236d8c7bf168ce4867dc83360e": ["Parenting Education"],
            "ec74c1192ef14f1debb3a31c912a1bbc": [
                "Parenting Education", "Home Visiting", "Early Intervention",
            ],
            "c44c60fb8e5cd640a4e7725286380d5c": ["Child Care", "Early Learning"],
            "220a1f02f8cd1658a7e7cd4b8e2906aa": [
                "Parenting Education", "Home Visiting", "Early Intervention",
            ],
            "029031368b1b87b942199b97cb2ac47f": [
                "Parenting Education", "Home Visiting",
            ],
            "aee416211643d092d52e82a4470df12b": ["Parenting Education"],
        },
        "boundary": (
            "Pregnancy medical care remains Medical; material aid remains Food or "
            "Clothing/Household; population descriptions remain For groups."
        ),
    },
    "independent-living": {
        "types": [
            {
                "label": "In-home Support",
                "definition": "Personal, homemaking, habilitation, or other support in the home.",
            },
            {
                "label": "Adult Day",
                "definition": "Structured daytime care, health, skill, or activity programs.",
            },
            {
                "label": "Assistive Technology",
                "definition": "Devices, software, evaluation, loans, or training that improve access.",
            },
            {
                "label": "Communication Access",
                "definition": "Tools or services enabling accessible communication.",
            },
            {
                "label": "Living Skills",
                "definition": "Training and support for managing daily life more independently.",
            },
            {
                "label": "Case Management",
                "definition": "Assessment, planning, coordination, and follow-through across supports.",
            },
            {
                "label": "Adaptive Recreation",
                "definition": "Sports, recreation, clubs, or activities adapted for participation.",
            },
            {
                "label": "Self-Advocacy",
                "definition": "Peer or professional support for expressing choices and protecting access.",
            },
            {
                "label": "Vision Rehabilitation",
                "definition": "Specialized rehabilitation and skills for blindness or low vision.",
            },
            {
                "label": "Long-Term Care",
                "definition": "Eligibility or service pathways for sustained home or community-based care.",
            },
        ],
        "assignments": {
            "a121b7ac06dc9b9ef503e462d5cffdd8": [
                "Living Skills", "Adaptive Recreation", "Self-Advocacy",
            ],
            "debb9e4a689060f00162da9ac2f8063b": ["Adult Day"],
            "5f72f3c9e07e90867dc016da33c05457": [
                "In-home Support", "Adult Day", "Case Management",
            ],
            "8db24b98270f7864dadcb0f97b901a53": [
                "Vision Rehabilitation", "Assistive Technology", "Living Skills",
            ],
            "ee67d6c2ce1b1b7f9dbf0b2ef86ef972": [
                "Communication Access", "Assistive Technology", "Self-Advocacy",
            ],
            "c30d34b41e5260bdd10a194738ec8df2": ["Adaptive Recreation"],
            "a246f47cd18fc8d7b1bfa520a0451300": ["Long-Term Care"],
            "6be73b6539fd16b3a6c84ffad77aace8": [
                "Assistive Technology", "Living Skills",
            ],
            "4ac8a5df1279284d2d5e64df54b5c1dd": ["Assistive Technology"],
            "00cca473db91285a4a393f5ba53add8f": [
                "Adult Day", "Living Skills", "Case Management",
            ],
            "f4bd5e83655dc1a2a573dc362204a505": ["Adaptive Recreation"],
            "0904081bbb9ee06085267ef392cd071f": [
                "Vision Rehabilitation", "Living Skills",
            ],
            "1bd2fb5b4587feef40252e0630c6c94c": [
                "In-home Support", "Case Management",
            ],
            "133e5f492400dff139f2cafa0b8f67c2": [
                "In-home Support", "Adult Day", "Living Skills",
            ],
            "df1db0951c8ad7dd0bcc0ec05a41b169": [
                "In-home Support", "Adult Day", "Case Management",
            ],
            "b41ef2cfadba3f4bedf490af52f17362": ["Adult Day"],
            "1a4c80c30adcb0f1df1846f7f84c3489": ["Self-Advocacy"],
            "b8c4699661c4d07b777efdab9ccb9d68": [
                "Communication Access", "Case Management", "Self-Advocacy",
            ],
        },
        "boundary": (
            "Employment, Housing, Transportation, Education, and Medical remain separate "
            "needs even when the same resource also supports independent living."
        ),
    },
    "caregiving": {
        "types": [
            {
                "label": "Respite",
                "definition": "Temporary relief or substitute care for an unpaid caregiver.",
            },
            {
                "label": "Support Groups",
                "definition": "Peer or facilitated emotional and practical caregiver support.",
            },
            {
                "label": "Caregiver Training",
                "definition": "Education and skills specifically for caregivers.",
            },
            {
                "label": "Care Coordination",
                "definition": "Assessment and arrangement of services supporting caregiver and recipient.",
            },
            {
                "label": "Adult Day",
                "definition": "Daytime programs that also provide caregiver relief.",
            },
            {
                "label": "In-home Support",
                "definition": "Care delivered in the home that reduces caregiver burden.",
            },
        ],
        "assignments": {
            "debb9e4a689060f00162da9ac2f8063b": ["Adult Day", "Respite"],
            "5f72f3c9e07e90867dc016da33c05457": [
                "Respite", "Adult Day", "In-home Support", "Care Coordination",
            ],
            "b21220ad00416ac580741d14ba3a1e7d": ["Respite"],
            "b47b61d084512681adb9c7ccacf2268c": ["Respite", "Support Groups"],
            "38629d0e712141f7531b4cff4b0bfd53": [
                "Respite", "Support Groups", "Care Coordination",
            ],
            "1bd2fb5b4587feef40252e0630c6c94c": [
                "In-home Support", "Care Coordination",
            ],
            "133e5f492400dff139f2cafa0b8f67c2": ["Adult Day", "In-home Support"],
            "df1db0951c8ad7dd0bcc0ec05a41b169": [
                "Adult Day", "In-home Support", "Care Coordination",
            ],
            "b41ef2cfadba3f4bedf490af52f17362": ["Adult Day", "Respite"],
            "948dd967fb329f7e5f04c0814a113889": [
                "Respite", "Support Groups", "Caregiver Training", "Care Coordination",
            ],
        },
        "boundary": (
            "The care recipient may also appear in Independent Living or Medical; this "
            "Category describes the unpaid caregiver's distinct need."
        ),
    },
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


def build_type_design(
    packet_record: dict[str, Any],
    specification: dict[str, Any],
) -> dict[str, Any]:
    packet = packet_record["packet"]
    category_id = str(packet_record["categoryId"])
    type_labels = [str(item["label"]) for item in specification["types"]]
    if len(type_labels) != len(set(type_labels)):
        raise TaxonomyStudyError(f"{category_id} has duplicate Type labels")
    expected_ids = {str(item["resourceId"]) for item in packet["resources"]}
    assignments = specification["assignments"]
    if expected_ids != set(assignments):
        raise TaxonomyStudyError(
            f"{category_id} Type coverage mismatch; "
            f"missing={sorted(expected_ids - set(assignments))}, "
            f"extra={sorted(set(assignments) - expected_ids)}"
        )
    resource_by_id = {
        str(item["resourceId"]): item for item in packet["resources"]
    }
    rows: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    disposition_counts: Counter[str] = Counter()
    for resource_id, selected in assignments.items():
        resource = resource_by_id[resource_id]
        if selected in ("no-type-needed", "unresolved"):
            disposition = str(selected)
            selected_types: list[str] = []
            disposition_counts.update([disposition])
            rows.append({
                "resourceId": resource_id,
                "name": resource["name"],
                "disposition": disposition,
                "types": [],
            })
            continue
        if not isinstance(selected, list) or not selected or len(selected) != len(set(selected)):
            raise TaxonomyStudyError(
                f"{category_id}/{resource_id} needs Types, no-type-needed, or unresolved"
            )
        selected_types = selected
        unknown = sorted(set(selected_types) - set(type_labels))
        if unknown:
            raise TaxonomyStudyError(
                f"{category_id}/{resource_id} has unknown Types: {unknown}"
            )
        counts.update(selected_types)
        disposition_counts.update(["assigned-types"])
        rows.append({
            "resourceId": resource_id,
            "name": resource["name"],
            "disposition": "assigned-types",
            "types": list(selected_types),
        })
    rows.sort(key=lambda item: (item["name"].casefold(), item["resourceId"]))
    design = {
        "schemaVersion": 1,
        "status": "proposal-only",
        "studyId": int(packet_record["studyId"]),
        "categoryId": category_id,
        "categoryLabel": packet_record["categoryLabel"],
        "packetSha256": packet_record["packetSha256"],
        "definition": packet["typeReviewRules"]["definition"],
        "types": deepcopy(specification["types"]),
        "boundary": str(specification["boundary"]),
        "assignments": rows,
        "coverage": {
            "resourceCount": len(expected_ids),
            "assignedTypesCount": disposition_counts["assigned-types"],
            "noTypeNeededCount": disposition_counts["no-type-needed"],
            "unresolvedCount": disposition_counts["unresolved"],
            "typeCounts": dict(sorted(counts.items())),
        },
    }
    return design


def save_new_category_type_designs(
    store: ResearchStore,
    study_id: int,
) -> dict[str, Any]:
    saved: list[dict[str, Any]] = []
    for category_id, specification in NEW_CATEGORY_TYPE_DESIGNS.items():
        packets = store.list_taxonomy_type_review_packets(study_id, category_id)
        if not packets:
            raise TaxonomyStudyError(f"Type review packet not found: {category_id}")
        packet = packets[0]
        design = build_type_design(packet, specification)
        design_sha256 = _sha256(design)
        revision = store.save_taxonomy_type_design_revision(
            study_id,
            category_id,
            design,
            design_sha256,
            based_on_packet_sha256=packet["packetSha256"],
            source="codex-category-by-category-type-design",
            note="Initial Type design for Michael's review; no resource package changed.",
        )
        saved.append({
            "categoryId": category_id,
            "categoryLabel": packet["categoryLabel"],
            "revision": revision,
            "designSha256": design_sha256,
            "typeCount": len(design["types"]),
            "resourceCount": design["coverage"]["resourceCount"],
            "unresolvedCount": design["coverage"]["unresolvedCount"],
            "types": [item["label"] for item in design["types"]],
        })
    return {
        "studyId": int(study_id),
        "designedCategoryCount": len(saved),
        "categories": saved,
    }
