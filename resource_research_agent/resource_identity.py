"""Code-owned resource identities, independent of runs, names and locations.

Matching is an explicit reviewed decision. This module never guesses identity
from a name, domain, address, or a model-generated identifier.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import uuid


class IdentityError(ValueError):
    pass


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def fingerprint(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def new_registry():
    return dict(schemaVersion=1, namespace=str(uuid.uuid4()), nextSequence=1,
                resources={}, aliases={}, events=[])


def validate_registry(registry):
    if registry.get("schemaVersion") != 1:
        raise IdentityError("Unsupported registry schema")
    try:
        uuid.UUID(registry["namespace"])
    except (ValueError, KeyError, TypeError) as exc:
        raise IdentityError("Invalid registry namespace") from exc
    resources, aliases = registry["resources"], registry["aliases"]
    sequences = []
    for rid, record in resources.items():
        seq = record["sequence"]
        expected = "sr_" + uuid.uuid5(uuid.UUID(registry["namespace"]), str(seq)).hex
        if rid != expected or type(seq) is not int or seq < 1:
            raise IdentityError("Resource ID was not allocated by this registry")
        sequences.append(seq)
    if len(set(sequences)) != len(sequences) or type(registry["nextSequence"]) is not int:
        raise IdentityError("Invalid identity sequence")
    if registry["nextSequence"] <= max(sequences, default=0):
        raise IdentityError("Registry sequence would reuse an identity")
    for alias, rid in aliases.items():
        try:
            parts = json.loads(alias)
        except (ValueError, TypeError) as exc:
            raise IdentityError("Invalid alias key") from exc
        if not isinstance(parts, list) or len(parts) != 2 or not all(isinstance(p, str) and p for p in parts):
            raise IdentityError("Alias needs namespace and existing source ID")
        if rid not in resources:
            raise IdentityError("Dangling identity alias")


def alias_key(namespace, source_id):
    if not all(isinstance(x, str) and x.strip() for x in (namespace, source_id)):
        raise IdentityError("Empty identity alias")
    return canonical([namespace, source_id])


def register_reviewed(registry, *, source_namespace, decisions):
    """Return a revised registry and source-ID map; never mutate the input.

    decisions: [{members: [source IDs], match: existing registry ID or null,
                 label: reviewed program label, reason: identity justification}]
    A group is one affirmed program identity, not everything at an organization.
    Conflicting established identities require a separate, explicit migration.
    """
    validate_registry(registry)
    result = deepcopy(registry)
    mapping, seen = {}, set()
    for decision in decisions:
        members = decision.get("members")
        if not isinstance(members, list) or not members or any(not isinstance(x, str) or not x for x in members):
            raise IdentityError("Each reviewed identity needs source members")
        if len(set(members)) != len(members) or seen.intersection(members):
            raise IdentityError("Repeated source identity decision")
        seen.update(members)
        for key in ("label", "reason"):
            if not isinstance(decision.get(key), str) or not decision[key].strip():
                raise IdentityError("Identity decisions require a label and reason")
        keys = [alias_key(source_namespace, member) for member in members]
        known = {result["aliases"][key] for key in keys if key in result["aliases"]}
        match = decision.get("match")
        if match is not None:
            if match not in result["resources"]:
                raise IdentityError("Unknown proposed match; model IDs cannot allocate identities")
            known.add(match)
        if len(known) > 1:
            raise IdentityError("Conflicting existing identities require an explicit migration")
        if known:
            rid = next(iter(known))
        else:
            seq = result["nextSequence"]
            rid = "sr_" + uuid.uuid5(uuid.UUID(result["namespace"]), str(seq)).hex
            result["nextSequence"] += 1
            result["resources"][rid] = dict(sequence=seq, initialLabel=decision["label"])
        added = [member for key, member in zip(keys, members) if key not in result["aliases"]]
        for key, member in zip(keys, members):
            result["aliases"][key] = rid
            mapping[member] = rid
        if added:
            result["events"].append(dict(kind="identity-bound", resourceId=rid,
                sourceNamespace=source_namespace, sourceIds=added, label=decision["label"], reason=decision["reason"]))
    validate_registry(result)
    return result, mapping


def load_registry(path: Path):
    if not path.is_file():
        raise IdentityError("Registry missing. Restore the committed registry; do not silently initialize another lineage.")
    registry = json.loads(path.read_text())
    validate_registry(registry)
    return registry


def save_registry(path: Path, registry, *, expected_fingerprint):
    """Atomic update for the documented single-writer Mac mini workflow."""
    validate_registry(registry)
    if path.exists():
        if expected_fingerprint is None or fingerprint(load_registry(path)) != expected_fingerprint:
            raise IdentityError("Registry changed since review; reload before saving")
    elif expected_fingerprint is not None:
        raise IdentityError("Expected registry disappeared; restore it")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".identities-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as handle:
            handle.write(json.dumps(registry, ensure_ascii=False, indent=2) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
