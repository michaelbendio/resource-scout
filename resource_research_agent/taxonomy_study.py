from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any

from .scout_curation import completed_scout_curation_resources
from .storage import ResearchStore


TAXONOMY_STUDY_VERSION = "needs-types-for-v1"


class TaxonomyStudyError(ValueError):
    """Raised when Scout cannot prepare a reproducible taxonomy review."""


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _category_ids(resource: dict[str, Any]) -> list[str]:
    values = resource.get("categories")
    if not isinstance(values, list):
        return []
    result: list[str] = []
    for value in values:
        category_id = str(value or "").strip()
        if category_id and category_id not in result:
            result.append(category_id)
    return result


def _resource_entry(
    origin: str,
    resource: dict[str, Any],
    *,
    resource_id: str | None = None,
) -> dict[str, Any]:
    value = deepcopy(resource)
    selected_id = str(resource_id or value.get("id") or "").strip()
    if not selected_id:
        raise TaxonomyStudyError(f"A {origin} resource has no stable ID")
    return {
        "corpusKey": f"{origin}:{selected_id}",
        "origin": origin,
        "resourceId": selected_id,
        "name": str(value.get("name") or selected_id).strip(),
        "categories": _category_ids(value),
        "resource": value,
    }


def _curation_result_sha256(job: dict[str, Any]) -> str:
    manifest = [
        {
            "categoryId": category["categoryId"],
            "resultSha256": category["resultSha256"],
        }
        for category in job.get("categories") or []
    ]
    if not manifest or any(len(item["resultSha256"]) != 64 for item in manifest):
        raise TaxonomyStudyError("The Resource Scout curation result is incomplete")
    return _sha256(manifest)


def _attention_for(category_id: str) -> dict[str, str] | None:
    return {
        "seniors": {
            "kind": "population-shaped",
            "question": "Should Seniors become a For group while its resources move to need Categories?",
        },
        "veterans": {
            "kind": "population-shaped",
            "question": "Should Veterans become a For group while its resources move to need Categories?",
        },
        "children-pregnancy": {
            "kind": "mixed-population-and-need",
            "question": "Which needs belong in Categories, and which populations belong in For groups?",
        },
        "reentry-support": {
            "kind": "circumstance-shaped",
            "question": "Which reentry services are distinct needs, and when is Exiting corrections a For group?",
        },
        "disability": {
            "kind": "need-or-population-review",
            "question": "Which disability resources address a distinct need, and which use Disability as a For group?",
        },
        "miscellaneous": {
            "kind": "catch-all",
            "question": "Can each resource be assigned to a defined need instead of Miscellaneous?",
        },
    }.get(category_id)


def _category_review(
    categories: list[dict[str, Any]],
    resources: list[dict[str, Any]],
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for category in categories:
        category_id = str(category["id"])
        connected = [
            item for item in resources
            if item["origin"] == "connected-package"
            and category_id in item["categories"]
        ]
        curated = [
            item for item in resources
            if item["origin"] == "automesa-curated"
            and category_id in item["categories"]
        ]
        row = {
            "categoryId": category_id,
            "label": str(category.get("label") or category_id),
            "currentTypes": list(category.get("types") or []),
            "connectedResourceCount": len(connected),
            "autoMesaResourceCount": len(curated),
            "reviewStatus": "pending",
            "decision": None,
            "attention": _attention_for(category_id),
        }
        rows.append(row)
    return {
        "schemaVersion": 1,
        "purpose": "Decide whether each current heading represents a need Category.",
        "categoryTest": [
            "Is this something the person needs help obtaining or addressing?",
            "Would an interviewer reasonably look here regardless of population group?",
            "Are its resources connected by the need they address rather than merely by whom they serve?",
        ],
        "allowedDecisions": [
            "retain-need",
            "rename-need",
            "merge-needs",
            "split-needs",
            "reclassify-for",
            "reclassify-type",
            "record-as-access",
            "retire",
        ],
        "categories": rows,
        "workedExamples": [
            {
                "name": "Senior bus-pass program",
                "expectedCategory": "transportation",
                "expectedFor": ["Seniors"],
                "reason": "Transportation is the need; Seniors describes whom the program serves.",
            },
            {
                "name": "Veteran employment program",
                "expectedCategory": "employment",
                "expectedFor": ["Veterans"],
                "reason": "Employment is the need; Veterans describes whom the program serves.",
            },
            {
                "name": "Spanish-language online class",
                "expectedCategory": "education",
                "expectedType": ["Online Education"],
                "expectedFor": ["Spanish-speaking"],
                "reason": "The Type describes how education is delivered; For records language accommodation.",
            },
        ],
    }


def prepare_taxonomy_study(
    store: ResearchStore,
    import_id: int,
    *,
    curation_job_id: int,
    replay_study_id: int,
) -> dict[str, Any]:
    summary = store.import_summary(import_id)
    if not summary:
        raise TaxonomyStudyError("Connect a resource package before taxonomy review")
    curation = store.get_scout_curation_job(curation_job_id)
    if not curation or int(curation["importId"]) != int(import_id):
        raise TaxonomyStudyError("The curation job belongs to another resource package")
    if curation["status"] != "completed":
        raise TaxonomyStudyError("Finish Resource Scout curation before taxonomy review")
    replay = store.get_codex_replay_study(replay_study_id)
    if not replay or int(replay["importId"]) != int(import_id):
        raise TaxonomyStudyError("The replay study belongs to another resource package")
    if replay["status"] != "completed" or not replay.get("report"):
        raise TaxonomyStudyError("Finish and reveal the Codex replay before taxonomy review")

    connected = [
        _resource_entry(
            "connected-package",
            item["resource"],
            resource_id=item["resourceId"],
        )
        for item in store.list_import_resources(import_id)
    ]
    curated = [
        _resource_entry("automesa-curated", resource)
        for resource in completed_scout_curation_resources(curation)
    ]
    resources = connected + curated
    corpus = {
        "schemaVersion": 1,
        "import": {
            "id": int(import_id),
            "sourceName": summary["sourceName"],
            "sourceSha256": summary["sourceSha256"],
            "contentSha256": summary["contentSha256"],
            "officeName": summary["officeName"],
            "serviceArea": summary["serviceArea"],
        },
        "curation": {
            "jobId": int(curation_job_id),
            "candidatePackageSha256": curation["candidatePackageSha256"],
            "resultSha256": _curation_result_sha256(curation),
        },
        "replay": {
            "studyId": int(replay_study_id),
            "reportSha256": replay["reportSha256"],
        },
        "categories": deepcopy(summary["categories"]),
        "forGroups": deepcopy(summary["forGroups"]),
        "resources": resources,
    }
    corpus_sha256 = _sha256(corpus)
    category_review = _category_review(summary["categories"], resources)
    category_review_sha256 = _sha256(category_review)
    study_id = store.create_taxonomy_study({
        "importId": int(import_id),
        "curationJobId": int(curation_job_id),
        "replayStudyId": int(replay_study_id),
        "studyVersion": TAXONOMY_STUDY_VERSION,
        "sourcePackageContentSha256": summary["contentSha256"],
        "curationResultSha256": corpus["curation"]["resultSha256"],
        "replayReportSha256": replay["reportSha256"],
        "corpus": corpus,
        "corpusSha256": corpus_sha256,
        "categoryReview": category_review,
        "categoryReviewSha256": category_review_sha256,
    })
    result = store.get_taxonomy_study(study_id)
    if result is None:  # pragma: no cover
        raise RuntimeError("Created taxonomy study could not be read")
    return result


def taxonomy_study_summary(study: dict[str, Any]) -> dict[str, Any]:
    resources = study["corpus"]["resources"]
    categories = study["categoryReview"]["categories"]
    return {
        "id": study["id"],
        "status": study["status"],
        "studyVersion": study["studyVersion"],
        "importId": study["importId"],
        "curationJobId": study["curationJobId"],
        "replayStudyId": study["replayStudyId"],
        "corpusSha256": study["corpusSha256"],
        "categoryReviewSha256": study["categoryReviewSha256"],
        "resourceCounts": {
            "connectedPackage": sum(
                item["origin"] == "connected-package" for item in resources
            ),
            "autoMesaCurated": sum(
                item["origin"] == "automesa-curated" for item in resources
            ),
            "total": len(resources),
        },
        "categoryCount": len(categories),
        "attentionCategories": [
            {
                "categoryId": item["categoryId"],
                "label": item["label"],
                "attention": item["attention"],
            }
            for item in categories
            if item["attention"]
        ],
    }
