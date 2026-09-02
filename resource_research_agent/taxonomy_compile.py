from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from .scout_curation import build_scout_review_seed
from .storage import ResearchStore
from .taxonomy_category_proposal import RETIRED_CATEGORY_IDS
from .taxonomy_study import TaxonomyStudyError


FINAL_CATEGORY_REPLACEMENTS: dict[str, list[str]] = {
    "children-pregnancy": ["parenting-child-development"],
    "clothing-household": ["clothing", "household-essentials"],
    "disability": ["independent-living", "caregiving"],
    "reentry-support": [],
    "miscellaneous": [],
    "seniors": [],
    "veterans": [],
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


def _latest_by_category(values: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for value in values:
        result[str(value["categoryId"])] = value
    return result


def _final_category_order(
    source_categories: list[dict[str, Any]],
    final_category_ids: set[str],
) -> list[str]:
    result: list[str] = []
    for category in source_categories:
        category_id = str(category.get("id") or "")
        replacements = FINAL_CATEGORY_REPLACEMENTS.get(category_id, [category_id])
        for replacement in replacements:
            if replacement in final_category_ids and replacement not in result:
                result.append(replacement)
    missing = sorted(final_category_ids - set(result))
    result.extend(missing)
    return result


def _compile_inputs(
    store: ResearchStore,
    study_id: int,
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    list[dict[str, Any]],
    dict[str, Any],
]:
    study = store.get_taxonomy_study(study_id)
    if study is None:
        raise TaxonomyStudyError("Taxonomy study not found")
    proposals = study.get("categoryRedistributionProposals") or []
    approval = study.get("categoryApproval")
    if not proposals or not approval:
        raise TaxonomyStudyError("Approve the latest Category proposal before compilation")
    category_proposal = proposals[-1]
    if approval["proposalSha256"] != category_proposal["proposalSha256"]:
        raise TaxonomyStudyError("The approved Category proposal is not the latest proposal")

    packets = store.list_taxonomy_type_review_packets(study_id)
    designs = store.list_taxonomy_type_design_revisions(study_id)
    latest_designs = _latest_by_category(designs)
    if len(packets) != 20 or len(latest_designs) != 20:
        raise TaxonomyStudyError("Every approved need Category needs a Type design")
    packet_by_category = {str(item["categoryId"]): item for item in packets}
    if set(packet_by_category) != set(latest_designs):
        raise TaxonomyStudyError("Type packets and Type designs cover different Categories")
    for category_id, design in latest_designs.items():
        packet = packet_by_category[category_id]
        if design["basedOnPacketSha256"] != packet["packetSha256"]:
            raise TaxonomyStudyError(f"The {category_id} Type design is stale")
        if int(design["design"]["coverage"]["unresolvedCount"]) != 0:
            raise TaxonomyStudyError(f"Resolve every {category_id} Type decision")

    group_packet = store.get_taxonomy_group_review_packet(study_id)
    group_revisions = store.list_taxonomy_group_inference_revisions(study_id)
    if not group_packet or not group_revisions:
        raise TaxonomyStudyError("Complete the full-corpus For-group review")
    group_proposal = group_revisions[-1]
    if group_proposal["basedOnPacketSha256"] != group_packet["packetSha256"]:
        raise TaxonomyStudyError("The For-group proposal is stale")
    coverage = group_proposal["proposal"]["coverage"]
    if int(coverage["unresolvedCount"]) != 0:
        raise TaxonomyStudyError("Resolve every For-group decision")
    if int(coverage["resourcesNeedingExistingOnlyReview"]) != 0:
        raise TaxonomyStudyError("Review every existing-only For-group decision")
    return study, category_proposal, list(latest_designs.values()), group_proposal


def _compile_seed(
    base_seed: dict[str, Any],
    study: dict[str, Any],
    category_revision: dict[str, Any],
    type_revisions: list[dict[str, Any]],
    group_revision: dict[str, Any],
    *,
    compiled_at: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    proposal = category_revision["proposal"]
    category_assignments = {
        str(item["corpusKey"]): item
        for item in proposal["assignments"]
    }
    group_proposal = group_revision["proposal"]
    group_assignments = {
        str(item["corpusKey"]): item
        for item in group_proposal["assignments"]
    }
    corpus_resources = study["corpus"]["resources"]
    corpus_keys = {str(item["corpusKey"]) for item in corpus_resources}
    if set(group_assignments) != corpus_keys:
        raise TaxonomyStudyError("The For-group proposal does not cover the frozen corpus")

    source_categories = list(study["corpus"]["categories"])
    source_category_by_id = {
        str(item["id"]): item for item in source_categories
    }
    proposed_category_by_id = {
        str(item["id"]): item for item in proposal["proposedNeedCategories"]
    }
    designs_by_category = {
        str(item["categoryId"]): item for item in type_revisions
    }
    final_category_ids = set(designs_by_category)
    category_order = _final_category_order(source_categories, final_category_ids)
    if len(category_order) != 20:
        raise TaxonomyStudyError(
            f"Expected 20 final need Categories, found {len(category_order)}"
        )

    categories: list[dict[str, Any]] = []
    assignments_by_category: dict[str, dict[str, dict[str, Any]]] = {}
    for category_id in category_order:
        revision = designs_by_category[category_id]
        design = revision["design"]
        definitions = design.get("types") or []
        type_labels = [str(item["label"]) for item in definitions]
        if len(type_labels) != len(set(type_labels)):
            raise TaxonomyStudyError(f"{category_id} has duplicate Type labels")
        source = source_category_by_id.get(category_id) or proposed_category_by_id.get(
            category_id
        )
        if source is None:
            raise TaxonomyStudyError(f"Missing Category definition for {category_id}")
        categories.append({
            "id": category_id,
            "label": str(design["categoryLabel"]),
            # The review package schema calls these category-scoped values
            # ``filters``.  In the public UI they are deliberately presented
            # as Types.
            "filters": type_labels,
            "active": True,
        })
        assignments_by_category[category_id] = {
            str(item["resourceId"]): item
            for item in design["assignments"]
        }

    transformed: list[tuple[str, dict[str, Any]]] = []
    seen_resource_ids: set[str] = set()
    for corpus_item in corpus_resources:
        corpus_key = str(corpus_item["corpusKey"])
        resource = deepcopy(corpus_item["resource"])
        resource_id = str(corpus_item["resourceId"])
        if resource_id in seen_resource_ids:
            raise TaxonomyStudyError(f"Duplicate stable resource ID: {resource_id}")
        seen_resource_ids.add(resource_id)

        category_assignment = category_assignments.get(corpus_key)
        category_ids = (
            list(category_assignment["proposedNeedCategories"])
            if category_assignment
            else [
                str(value)
                for value in corpus_item.get("categories") or []
                if str(value) not in RETIRED_CATEGORY_IDS
            ]
        )
        category_ids = list(dict.fromkeys(category_ids))
        unknown_categories = sorted(set(category_ids) - final_category_ids)
        if unknown_categories:
            raise TaxonomyStudyError(
                f"Resource {resource_id} has unknown final Categories: "
                + ", ".join(unknown_categories)
            )
        if not category_ids:
            raise TaxonomyStudyError(f"Resource {resource_id} has no final need Category")

        filters: dict[str, list[str]] = {}
        for category_id in category_ids:
            type_assignment = assignments_by_category[category_id].get(resource_id)
            if type_assignment is None:
                raise TaxonomyStudyError(
                    f"Resource {resource_id} has no {category_id} Type disposition"
                )
            disposition = str(type_assignment["disposition"])
            if disposition == "unresolved":
                raise TaxonomyStudyError(
                    f"Resource {resource_id} has an unresolved {category_id} Type"
                )
            selected_types = [str(value) for value in type_assignment.get("types") or []]
            allowed_types = {
                item["label"] for item in designs_by_category[category_id]["design"]["types"]
            }
            if set(selected_types) - allowed_types:
                raise TaxonomyStudyError(
                    f"Resource {resource_id} uses an unknown {category_id} Type"
                )
            if disposition == "assigned-types" and not selected_types:
                raise TaxonomyStudyError(
                    f"Resource {resource_id} has an empty assigned {category_id} Type"
                )
            if disposition == "no-type-needed" and selected_types:
                raise TaxonomyStudyError(
                    f"Resource {resource_id} has Types despite no-type-needed"
                )
            if selected_types:
                filters[category_id] = selected_types

        group_assignment = group_assignments[corpus_key]
        if group_assignment["reviewStatus"] != "ready":
            raise TaxonomyStudyError(f"Resource {resource_id} has unresolved For groups")
        group_labels = [
            str(item["label"]) for item in group_assignment.get("groups") or []
        ]

        resource["categories"] = category_ids
        resource["categoryFilters"] = filters
        resource["forGroups"] = list(dict.fromkeys(group_labels))
        transformed.append((str(corpus_item["origin"]), resource))

    # autoMesa remains the review queue of Scout-curated proposals. The connected
    # package records participate in the audit above but remain in their source
    # package until a reviewed update is deliberately merged.
    resources = [resource for origin, resource in transformed if origin == "automesa-curated"]
    expected = [
        item for item in study["corpus"]["resources"]
        if item["origin"] == "automesa-curated"
    ]
    if len(resources) != len(expected):
        raise TaxonomyStudyError("The compiled autoMesa resource set changed unexpectedly")

    catalog = group_proposal["catalog"]
    for_groups = [str(item["label"]) for item in catalog]
    seed = deepcopy(base_seed)
    seed.update({
        "categories": categories,
        "categoryMigrations": [],
        "forGroups": for_groups,
        "resources": resources,
        "changes": [],
        "deletionRequests": [],
        "deletions": [],
        "packageCreatedAt": compiled_at,
        "lastModified": compiled_at,
    })
    type_manifest = [
        {
            "categoryId": category_id,
            "designRevision": int(designs_by_category[category_id]["revision"]),
            "designSha256": str(designs_by_category[category_id]["designSha256"]),
        }
        for category_id in category_order
    ]
    return seed, type_manifest


def compile_taxonomy_study(
    store: ResearchStore,
    study_id: int,
) -> dict[str, Any]:
    existing = store.get_taxonomy_compilation(study_id)
    if existing is not None:
        return existing
    study, category_revision, type_revisions, group_revision = _compile_inputs(
        store, study_id
    )
    base_seed = build_scout_review_seed(store, int(study["curationJobId"]))
    compiled_at = datetime.now(timezone.utc).isoformat()
    seed, type_manifest = _compile_seed(
        base_seed,
        study,
        category_revision,
        type_revisions,
        group_revision,
        compiled_at=compiled_at,
    )
    type_manifest_sha256 = _sha256(type_manifest)
    return store.save_taxonomy_compilation(
        study_id,
        seed,
        _sha256(seed),
        based_on_corpus_sha256=study["corpusSha256"],
        category_proposal_sha256=category_revision["proposalSha256"],
        type_design_manifest=type_manifest,
        type_design_manifest_sha256=type_manifest_sha256,
        group_proposal_sha256=group_revision["proposalSha256"],
    )
