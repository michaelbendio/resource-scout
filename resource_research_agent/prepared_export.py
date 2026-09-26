"""Finalize a reviewed preparation bundle through the code-owned identity gate.

No model calls, identity guesses, taxonomy inference, or human approval changes.
Review bundles are internal; only prepared-resources.json is the import payload.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import gzip
import hashlib
import json
from pathlib import Path

from .preparation_contract import POLICY_VERSION
from .prepared_resources import build_snapshot, validate_artifact, require, text
from .resource_identity import (fingerprint, new_registry, load_registry,
                                register_reviewed, save_registry)


def review_fingerprint(bundle):
    return fingerprint({k: v for k, v in bundle.items() if k != "review"})


def finalize(bundle, registry, *, previous=None):
    require(bundle.get("artifactType") == "scout-reviewed-preparation", "Expected a reviewed preparation bundle")
    require(bundle.get("policyVersion") == POLICY_VERSION, "Unknown preparation policy")
    review = bundle.get("review", {})
    require(review.get("inputFingerprint") == review_fingerprint(bundle), "Stale preparation review")
    require(text(review.get("reviewer")) and text(review.get("reviewedAt")), "Review completion evidence missing")
    for key in ("identity", "content", "taxonomy", "starterSets", "preservation"):
        require(text(review.get(key)), f"Missing {key} judgment")
    inputs = bundle["inputs"]
    require(inputs and all(text(v) for v in inputs.values()), "Input hashes missing")
    decisions = bundle["identityDecisions"]
    members = [m for d in decisions for m in d["members"]]
    assessments = bundle["assessments"]
    require(set(members) == set(assessments) and len(members) == len(assessments), "Identity decisions must cover every assessed source record once")
    payload = deepcopy(bundle["payload"])
    require('considerations' in payload, 'New deliveries require reasons for every non-starter membership')
    proposed = {r["id"] for r in payload["resources"]}
    require(len(proposed) == len(payload["resources"]), "Repeated draft identity")
    for rid, decision in assessments.items():
        require(decision.get("state") in ("usable", "needs-resolution", "not-offered", "suppressed", "merged"), "Unaccounted source record")
        require(text(decision.get("reason")), "Assessment needs a specific reason")
        if decision["state"] in ("usable", "needs-resolution"):
            require(rid in proposed, "A prepared reserve resource was lost")
        else:
            require(rid not in proposed, "Excluded record entered delivery")
        if decision["state"] == "merged":
            require(decision.get("target") in proposed, "Merge destination missing")
    require(proposed <= set(assessments), "Unreviewed resource entered delivery")
    updated, mapping = register_reviewed(registry,
        source_namespace=bundle["sourceNamespace"], decisions=decisions)
    for rid, decision in assessments.items():
        if decision["state"] == "merged":
            require(mapping[rid] == mapping[decision["target"]], "Merge identity disagrees with preservation assessment")
    for resource in payload["resources"]:
        require(resource["state"] == assessments[resource["id"]]["state"], "State differs from reviewed assessment")
        resource["id"] = mapping[resource["id"]]
    hidden = {mapping[rid] for rid, a in assessments.items() if a["state"] == "suppressed"}
    require(not hidden.intersection(r["id"] for r in payload["resources"]), "A merge would resurrect a human-hidden resource")
    for starter in payload["starterSets"]:
        for member in starter["members"]:
            member["resourceId"] = mapping[member["resourceId"]]
    for item in payload['considerations']:
        item['resourceId'] = mapping[item['resourceId']]
    if previous:
        validate_artifact(previous, updated)
    artifact = build_snapshot(payload, generated_at=review["reviewedAt"], previous=previous)
    counts = validate_artifact(artifact, updated, office_category_ids=bundle["officeCategoryIds"])
    migration = dict(artifactType="scout-identity-migration", schemaVersion=1,
        office=deepcopy(artifact["office"]), sourceNamespace=bundle["sourceNamespace"],
        snapshotId=artifact["snapshot"]["id"], registryNamespace=updated["namespace"],
        aliases=[dict(legacyId=old, resourceId=new) for old, new in sorted(mapping.items())],
        suppressedResourceIds=sorted(hidden),
        rule="Migrate existing decisions by alias before import; preserve human edits, approvals, verification dates, deletions, drafts, pins and notes. Conflicting rows require administrator reconciliation.")
    receipt = dict(artifactType="scout-preparation-receipt", schemaVersion=1,
        snapshotId=artifact["snapshot"]["id"], contentFingerprint=artifact["snapshot"]["contentFingerprint"],
        reviewFingerprint=review["inputFingerprint"], registryFingerprint=fingerprint(updated),
        inputHashes=deepcopy(inputs), counts=counts, review=deepcopy(review))
    return artifact, updated, migration, receipt


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()


def export_bundle(bundle_path, registry_path, output, *, initialize_registry=False, previous_path=None):
    bundle = json.loads(bundle_path.read_text())
    if initialize_registry:
        require(not registry_path.exists(), "Registry already exists; initialization is never a reset")
        registry, before = new_registry(), None
    else:
        registry = load_registry(registry_path)
        before = fingerprint(registry)
    previous = json.loads(previous_path.read_text()) if previous_path else None
    artifact, updated, migration, receipt = finalize(bundle, registry, previous=previous)
    artifact_bytes = encoded(artifact)
    receipt["artifactSha256"] = hashlib.sha256(artifact_bytes).hexdigest()
    files = {"prepared-resources.json": artifact_bytes,
             "prepared-resources.json.gz": gzip.compress(artifact_bytes, mtime=0),
             "identity-migration.json": encoded(migration), "receipt.json": encoded(receipt)}
    # Validate everything before any durable write; retries reuse assigned IDs.
    for name, raw in files.items():
        destination = output / name
        require(not destination.exists() or destination.read_bytes() == raw,
                f"Refusing to replace a delivered artifact: {destination}")
    save_registry(registry_path, updated, expected_fingerprint=before)
    output.mkdir(parents=True, exist_ok=True)
    for name, raw in files.items():
        destination = output / name
        if not destination.exists():
            with destination.open("xb") as handle:
                handle.write(raw)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", required=True, type=Path)
    parser.add_argument("--registry", type=Path, default=Path("registry/resource-identities.json"))
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--previous", type=Path)
    parser.add_argument("--initialize-registry", action="store_true")
    args = parser.parse_args()
    try:
        receipt = export_bundle(args.bundle, args.registry, args.output,
            initialize_registry=args.initialize_registry, previous_path=args.previous)
    except (ValueError, KeyError) as exc:
        parser.exit(2, f"Prepared export refused: {exc}\n")
    print(json.dumps(receipt["counts"], sort_keys=True))


if __name__ == "__main__":
    main()
