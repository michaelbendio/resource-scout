from __future__ import annotations

from typing import Any

from .duplicates import DuplicateIndex
from .importer import normalize_index_value
from .storage import ResearchStore


def _normalized(value: Any) -> str:
    return " ".join(str(value or "").casefold().split())


def _same_normalized_signal(signal: dict[str, Any]) -> bool:
    candidate_kind = str(signal.get("candidateField") or "")
    known_kind = str(signal.get("knownField") or "")
    candidate = normalize_index_value(candidate_kind, str(signal.get("candidateValue") or ""))
    known = normalize_index_value(known_kind, str(signal.get("knownValue") or ""))
    return bool(candidate and candidate == known)


def _confirmed_existing(match: dict[str, Any]) -> bool:
    exact_kinds = {
        str(signal.get("candidateField") or "")
        for signal in match.get("signals", [])
        if _same_normalized_signal(signal)
    }
    name_kinds = {
        "name", "alias", "name_variant", "organization_name", "program_name"
    }
    has_name = bool(exact_kinds & name_kinds)
    return has_name and bool(exact_kinds & {"website", "address"})


def reconcile_completed_run(
    store: ResearchStore,
    run_id: int,
    target_import_id: int | None = None,
) -> dict[str, Any]:
    run = store.get_run(run_id)
    if not run:
        raise ValueError("Discovery run not found")
    if run["status"] != "completed":
        raise ValueError("Finish discovery before reconciling its candidates")
    if run.get("researchMode") != "package":
        raise ValueError("Standalone-location research has no package to reconcile")

    target_import_id = target_import_id or store.latest_import_id()
    if target_import_id != store.latest_import_id():
        raise ValueError("Reconciliation must use the currently connected package")
    target = store.import_summary(target_import_id)
    if not target:
        raise ValueError("Connect the newer resource package before reconciling")
    if not store.import_category(target_import_id, run["targetCategoryId"]):
        raise ValueError(
            f"The connected package does not contain {run['targetCategoryLabel']}"
        )

    current = run.get("reconciliation")
    effective_content_sha256 = (
        current["targetPackage"]["contentSha256"]
        if current
        else run.get("sourcePackageContentSha256")
    )
    if (
        effective_content_sha256
        and target["contentSha256"] == effective_content_sha256
    ):
        raise ValueError("This discovery run already uses the connected package")

    original = store.import_summary(run.get("sourceImportId"))
    if original:
        same_office = _normalized(original.get("officeName")) == _normalized(target.get("officeName"))
        same_area = _normalized(original.get("serviceArea")) == _normalized(target.get("serviceArea"))
        if not same_office and not same_area:
            raise ValueError(
                "The connected package belongs to a different office or service area"
            )

    discoveries = [
        item
        for item in store.list_discoveries(run_id)
        if item["status"] not in {"unavailable", "unreachable"}
    ]
    index = DuplicateIndex(store)
    saved_matches: list[dict[str, Any]] = []
    already_known = 0
    possible_relationships = 0
    for discovery in discoveries:
        matches = index.match(
            discovery.get("candidate", {}),
            import_id=target_import_id,
            limit=1,
        )
        if not matches:
            continue
        match = matches[0]
        confirmed_existing = _confirmed_existing(match)
        saved_matches.append({
            "discoveryId": discovery["id"],
            "resourceId": match["resourceId"],
            "score": match["score"],
            "classification": (
                "already-in-package" if confirmed_existing else "possible-duplicate"
            ),
            "signals": match["signals"],
        })
        if confirmed_existing:
            already_known += 1
        else:
            possible_relationships += 1

    known_category_resources = len(
        store.list_seeds(target_import_id, run["targetCategoryId"])
    )
    result = {
        "candidateCount": len(discoveries),
        "alreadyKnownCount": already_known,
        "possibleRelationshipCount": possible_relationships,
        "unmatchedCount": len(discoveries) - len(saved_matches),
        "knownCategoryResourceCount": known_category_resources,
        "targetCategoryId": run["targetCategoryId"],
        "targetCategoryLabel": run["targetCategoryLabel"],
    }
    reconciliation = store.save_run_reconciliation(
        run_id,
        target_import_id,
        saved_matches,
        result,
    )
    return {
        "runId": run_id,
        "reconciliation": reconciliation,
        **result,
    }
