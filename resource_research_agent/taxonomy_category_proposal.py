from __future__ import annotations

import hashlib
import json
from collections import Counter
from copy import deepcopy
from typing import Any

from .storage import ResearchStore
from .taxonomy_study import TaxonomyStudyError


MESA_TAXONOMY_CORPUS_SHA256 = (
    "cb4d2567052aaf9e67ecc4df45f5d73afb28db628bf962c5a1a4b27704916394"
)

RETIRED_CATEGORY_IDS = {
    "children-pregnancy",
    "disability",
    "reentry-support",
    "miscellaneous",
    "seniors",
    "veterans",
}

PROPOSED_NEED_CATEGORIES = [
    {
        "id": "parenting-child-development",
        "label": "Parenting & Child Development",
        "interviewerQuestion": (
            "Does this family need help caring for, parenting, or supporting the "
            "development of a child?"
        ),
        "includes": [
            "parenting education and coaching",
            "early intervention and developmental support",
            "home visiting and family resource centers",
            "child care and early-childhood family support",
        ],
        "boundary": (
            "Pregnancy medical care remains Medical; early education may also appear "
            "in Education; material aid appears in Clothing/Household or Food."
        ),
        "reviewQuestion": (
            "Is this one coherent need Category, or should Child Care become a separate need?"
        ),
    },
    {
        "id": "independent-living",
        "label": "Independent Living",
        "interviewerQuestion": (
            "Does this person need tools, skills, assistance, or accommodations to live "
            "and participate as independently as possible?"
        ),
        "includes": [
            "assistive technology and communication access",
            "in-home and adult-day support",
            "independent-living skills and case management",
            "adaptive recreation, mobility, self-advocacy, and community participation",
        ],
        "boundary": (
            "Employment, Housing, Transportation, Education, and Medical remain separate "
            "needs when the resource directly addresses them."
        ),
        "reviewQuestion": (
            "Does Independent Living clearly include community participation, adaptive "
            "recreation, and self-advocacy, or should that need be named separately?"
        ),
    },
    {
        "id": "caregiving",
        "label": "Caregiving",
        "interviewerQuestion": (
            "Does an unpaid caregiver need respite, training, support, or help arranging care?"
        ),
        "includes": [
            "respite and caregiver relief",
            "caregiver support groups and training",
            "care coordination where caregiver support is a direct service",
            "adult-day services that provide caregiver respite",
        ],
        "boundary": (
            "The care recipient's need may also appear in Independent Living or Medical; "
            "Caregiving is the caregiver's distinct need."
        ),
        "reviewQuestion": (
            "Should adult-day and in-home services appear in both Caregiving and "
            "Independent Living when they directly serve both needs?"
        ),
    },
]


RESOURCE_TARGETS: dict[str, list[str]] = {
    # Children/Pregnancy
    "33b8cbd29cf68ac3a07e0fd8d984771b": [
        "medical-dental-vision", "food", "financial-assistance",
        "parenting-child-development",
    ],
    "b48b75beadedb73dd0606ffb3dcc568d": [
        "parenting-child-development", "financial-assistance",
    ],
    "90ef7bed032bcd935b0f82e65f664917": ["parenting-child-development"],
    "855aea5e0d3d3b07f11e7bb81212e4d2": [
        "medical-dental-vision", "financial-assistance", "transportation",
    ],
    "34dc7c352ceb97ec5831aaa7cb4d3904": ["mental-health"],
    "0474f03b486642977ecad2860ffac719": [
        "medical-dental-vision", "mental-health",
    ],
    "18462adf6dd0d47ac76fba2161b70dfc": [
        "medical-dental-vision", "mental-health", "addiction",
    ],
    "1ed84b657420da445ac082991959b3f8": [
        "parenting-child-development", "education", "clothing-household",
    ],
    "ed9cec6557722e44984887fb41637d6e": [
        "medical-dental-vision", "parenting-child-development",
        "clothing-household",
    ],
    "2822ad624344c1ae4686dbbb665c3700": ["parenting-child-development"],
    "313775a628d6ace7912cbbd7fe30a8a3": ["parenting-child-development"],
    "ba6cab830d60bb25c2039ae996392523": [
        "housing", "education", "parenting-child-development",
    ],
    "220a1f02f8cd1658a7e7cd4b8e2906aa": ["parenting-child-development"],
    "8f5bf98773af65b68a2a025cff1b0d59": ["mental-health"],
    "a6043035dfbf51e34bad108416bca340": [
        "parenting-child-development", "clothing-household", "food",
    ],
    "ce0a9cdfa73bbb3fdafb2603d8099f40": ["mental-health"],
    "0df6bb236d8c7bf168ce4867dc83360e": [
        "housing", "homeless-services", "parenting-child-development",
        "clothing-household",
    ],
    "ec74c1192ef14f1debb3a31c912a1bbc": [
        "medical-dental-vision", "parenting-child-development", "mental-health",
    ],
    "c44c60fb8e5cd640a4e7725286380d5c": [
        "education", "parenting-child-development",
    ],
    "111bbc8293126891b0ecef093e94874c": ["medical-dental-vision"],
    "029031368b1b87b942199b97cb2ac47f": [
        "medical-dental-vision", "parenting-child-development",
    ],
    "aee416211643d092d52e82a4470df12b": [
        "medical-dental-vision", "parenting-child-development",
    ],
    "1d36ae0a82e6d1f6c264334db09e578c": [
        "medical-dental-vision", "mental-health",
    ],
    # Disability
    "a121b7ac06dc9b9ef503e462d5cffdd8": ["employment", "independent-living"],
    "5f72f3c9e07e90867dc016da33c05457": [
        "independent-living", "caregiving", "food", "financial-assistance",
    ],
    "b21220ad00416ac580741d14ba3a1e7d": ["caregiving"],
    "8db24b98270f7864dadcb0f97b901a53": [
        "independent-living", "employment", "medical-dental-vision",
    ],
    "ee67d6c2ce1b1b7f9dbf0b2ef86ef972": [
        "independent-living", "utilities-phone-internet",
    ],
    "eb94f24384f8e51a2b237d7d8c507948": [
        "parenting-child-development", "caregiving",
    ],
    "4ac8a5df1279284d2d5e64df54b5c1dd": ["independent-living", "education"],
    "c30d34b41e5260bdd10a194738ec8df2": ["independent-living"],
    "a246f47cd18fc8d7b1bfa520a0451300": [
        "medical-dental-vision", "independent-living",
    ],
    "6be73b6539fd16b3a6c84ffad77aace8": ["employment", "independent-living"],
    "067d28b529da7122c5d8c50ff1874faf": [
        "parenting-child-development", "education",
    ],
    "00cca473db91285a4a393f5ba53add8f": [
        "employment", "independent-living", "housing", "transportation",
    ],
    "f4bd5e83655dc1a2a573dc362204a505": ["independent-living"],
    "0904081bbb9ee06085267ef392cd071f": [
        "independent-living", "education", "medical-dental-vision",
    ],
    "133e5f492400dff139f2cafa0b8f67c2": [
        "independent-living", "caregiving", "employment",
    ],
    "df1db0951c8ad7dd0bcc0ec05a41b169": ["independent-living", "caregiving"],
    "1a4c80c30adcb0f1df1846f7f84c3489": ["independent-living"],
    "eac51d2e41cab50d1711a49e1f926ff0": ["employment"],
    "b8c4699661c4d07b777efdab9ccb9d68": ["independent-living", "employment"],
    # Reentry Support
    "08a7877a32a11b9f8531fa95f2a64ade": ["employment"],
    "f95aad04c5e72f66f324d9875d7caffd": ["employment"],
    "7de41696b045cd6fdb9bb5c25cf7c53f": ["employment"],
    "a90b957439ba736a20a0eb129322891e": [
        "id-recovery", "housing", "employment", "medical-dental-vision",
        "mental-health",
    ],
    "193621d2449346f5eb4f3fe57535ad47": [
        "employment", "financial-assistance", "parenting-child-development",
    ],
    "f2e69a8b2402313065411a32eaa02190": [
        "addiction", "mental-health", "housing",
    ],
    "df171bb522d8c9a10c10b5c20e52cc1b": [
        "employment", "clothing-household", "transportation", "mental-health",
        "housing",
    ],
    "528e3dad283cd117ea2ff80b3bec333c": [
        "parenting-child-development", "legal", "id-recovery", "food",
        "clothing-household", "transportation", "employment",
    ],
    "f5956fe09395d25458ca9fda67d737c9": ["employment", "transportation"],
    "8228b3327c959acccf53469fa50397a9": ["employment", "housing"],
    "01a9e5b0c362df7fad3f6577a423f91a": ["education", "employment"],
    "a4e45e62c0b9cb505d5b4874340871fb": [
        "id-recovery", "housing", "employment",
    ],
    "815148d4fe10fdbf28f981c14050256c": [
        "addiction", "mental-health", "housing",
    ],
    "617d4be1951f67468b5ddffdb2f670f5": [
        "addiction", "housing", "legal",
    ],
    "2888d7f802c66d6db7f0cdfc3d5f1b36": ["mental-health"],
    # Seniors (two shared records are listed under Disability above)
    "78ae362f464eb9c81519fc00a43f21ba": ["food"],
    "debb9e4a689060f00162da9ac2f8063b": [
        "independent-living", "caregiving", "medical-dental-vision",
    ],
    "ce14bd1aa42c212343ff01bdda80381e": ["legal"],
    "b47b61d084512681adb9c7ccacf2268c": [
        "caregiving", "legal",
    ],
    "38629d0e712141f7531b4cff4b0bfd53": [
        "caregiving", "parenting-child-development", "legal",
        "financial-assistance",
    ],
    "1bd2fb5b4587feef40252e0630c6c94c": [
        "independent-living", "caregiving", "housing",
    ],
    "b41ef2cfadba3f4bedf490af52f17362": ["independent-living", "caregiving"],
    # Veterans
    "fb402105bec44e0623b4ccf8d7064802": [
        "financial-assistance", "legal", "id-recovery",
    ],
    "70ea356cba96bcc304b79ca2a5469f9c": [
        "employment", "education", "clothing-household",
    ],
    "f0e0dca057e2ec54e46f72a3bdadd85e": ["mental-health"],
    "aa9a90d7f959067cb0447b4e06a5cb13": [
        "legal", "mental-health", "addiction",
    ],
    "c24a862cda664d0144ec0ae39b3e8f1f": ["id-recovery"],
    "a3782d71fb0f13f124d33c95dadd779c": [
        "housing", "homeless-services", "financial-assistance",
    ],
    "63094d56f92faa642ec6143be4d44d60": ["legal"],
    "2af79fdd0101ee3a198c732086f9bfc6": [
        "housing", "homeless-services", "employment", "mental-health", "addiction",
    ],
    "1c01cd6b13aaf41619e7cdc09b4c6725": ["legal"],
    "948dd967fb329f7e5f04c0814a113889": ["caregiving", "medical-dental-vision"],
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


def build_mesa_category_redistribution_proposal(
    study: dict[str, Any],
) -> dict[str, Any]:
    if study["corpusSha256"] != MESA_TAXONOMY_CORPUS_SHA256:
        raise TaxonomyStudyError(
            "This Mesa redistribution proposal belongs to another frozen corpus"
        )
    affected = [
        item
        for item in study["corpus"]["resources"]
        if RETIRED_CATEGORY_IDS.intersection(item["categories"])
    ]
    by_resource_id = {item["resourceId"]: item for item in affected}
    expected_ids = set(by_resource_id)
    actual_ids = set(RESOURCE_TARGETS)
    if expected_ids != actual_ids:
        missing = sorted(expected_ids - actual_ids)
        extra = sorted(actual_ids - expected_ids)
        raise TaxonomyStudyError(
            f"Redistribution coverage mismatch; missing={missing}, extra={extra}"
        )
    current_ids = {item["id"] for item in study["corpus"]["categories"]}
    proposed_ids = {item["id"] for item in PROPOSED_NEED_CATEGORIES}
    allowed_ids = (current_ids - RETIRED_CATEGORY_IDS) | proposed_ids
    assignments: list[dict[str, Any]] = []
    target_counts: Counter[str] = Counter()
    for resource_id, targets in RESOURCE_TARGETS.items():
        if not targets or len(targets) != len(set(targets)):
            raise TaxonomyStudyError(
                f"Resource {resource_id} needs distinct non-empty target Categories"
            )
        unknown = sorted(set(targets) - allowed_ids)
        if unknown:
            raise TaxonomyStudyError(
                f"Resource {resource_id} has unknown target Categories: {unknown}"
            )
        item = by_resource_id[resource_id]
        removed = sorted(RETIRED_CATEGORY_IDS.intersection(item["categories"]))
        target_counts.update(targets)
        assignments.append({
            "corpusKey": item["corpusKey"],
            "resourceId": resource_id,
            "name": item["name"],
            "removeCategories": removed,
            "proposedNeedCategories": list(targets),
            "status": "proposal-only",
        })
    assignments.sort(key=lambda item: (item["name"].casefold(), item["resourceId"]))
    return {
        "schemaVersion": 1,
        "status": "proposal-only",
        "studyId": int(study["id"]),
        "corpusSha256": study["corpusSha256"],
        "basedOnCategoryReviewSha256": study["categoryReviewSha256"],
        "principle": (
            "Categories organize resources by the needs they address; population, "
            "circumstance, and accommodation belong in For groups."
        ),
        "retireCategoryIds": sorted(RETIRED_CATEGORY_IDS),
        "proposedNeedCategories": deepcopy(PROPOSED_NEED_CATEGORIES),
        "recommendedForGroups": [
            "Seniors",
            "Veterans",
            "Exiting corrections",
            "Pregnant/postpartum",
            "Families with children",
            "People with disabilities",
        ],
        "assignments": assignments,
        "coverage": {
            "affectedResourceCount": len(affected),
            "uniqueAffectedResourceCount": len(by_resource_id),
            "assignmentCount": len(assignments),
            "unassignedCount": 0,
            "targetCategoryCounts": dict(sorted(target_counts.items())),
        },
        "reviewQuestions": [
            item["reviewQuestion"] for item in PROPOSED_NEED_CATEGORIES
        ] + [
            (
                "For broad navigation resources, should a Category appear only when the "
                "provider delivers that service directly, or also when it reliably connects "
                "the person to it?"
            )
        ],
    }


def save_mesa_category_redistribution_proposal(
    store: ResearchStore,
    study_id: int,
) -> dict[str, Any]:
    study = store.get_taxonomy_study(study_id)
    if study is None:
        raise TaxonomyStudyError("Taxonomy study not found")
    proposal = build_mesa_category_redistribution_proposal(study)
    proposal_sha256 = _sha256(proposal)
    revision = store.save_taxonomy_category_redistribution_proposal(
        study_id,
        proposal,
        proposal_sha256,
        based_on_category_review_sha256=study["categoryReviewSha256"],
        source="codex-resource-level-analysis",
        note=(
            "Resource-level need redistribution for Michael's review; no package or "
            "autoMesa resource was changed."
        ),
    )
    return {
        "studyId": int(study_id),
        "revision": revision,
        "proposalSha256": proposal_sha256,
        "proposal": proposal,
    }
