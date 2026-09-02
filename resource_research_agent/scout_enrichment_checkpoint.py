from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import tempfile
import zipfile
from contextlib import closing
from pathlib import Path
from typing import Any

from .scout_enrichment import (
    enrichment_project_summary,
    ensure_scout_enrichment_audits,
)
from .storage import ResearchStore


CHECKPOINT_SCHEMA_VERSION = 1
DATABASE_MEMBER = "research-agent.sqlite3"
MANIFEST_MEMBER = "checkpoint.json"


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def export_scout_enrichment_checkpoint(
    store: ResearchStore, project_id: int, output_path: str | Path
) -> dict[str, Any]:
    project = ensure_scout_enrichment_audits(store, project_id)
    output = Path(output_path).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="scout-checkpoint-") as directory:
        database_path = Path(directory) / DATABASE_MEMBER
        with closing(sqlite3.connect(store.path)) as source:
            with closing(sqlite3.connect(database_path)) as target:
                source.backup(target)
        database_bytes = database_path.read_bytes()
        manifest = {
            "checkpointSchemaVersion": CHECKPOINT_SCHEMA_VERSION,
            "databaseMember": DATABASE_MEMBER,
            "databaseSha256": _sha256_bytes(database_bytes),
            "project": enrichment_project_summary(project),
            "scopeNote": (
                "The checkpoint contains the complete local Resource Scout database "
                "so foreign-key and workflow history remain intact."
            ),
        }
        temporary_output = output.with_name(output.name + ".tmp")
        with zipfile.ZipFile(
            temporary_output, "w", compression=zipfile.ZIP_DEFLATED
        ) as archive:
            archive.writestr(
                MANIFEST_MEMBER,
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            )
            archive.write(database_path, DATABASE_MEMBER)
        os.replace(temporary_output, output)
    archive_bytes = output.read_bytes()
    return {
        "projectId": project_id, "outputPath": str(output),
        "byteCount": len(archive_bytes), "sha256": _sha256_bytes(archive_bytes),
        "databaseSha256": manifest["databaseSha256"],
        "progress": project["progress"],
    }


def import_scout_enrichment_checkpoint(
    archive_path: str | Path, database_path: str | Path
) -> dict[str, Any]:
    source = Path(archive_path).expanduser().resolve()
    destination = Path(database_path).expanduser().resolve()
    if destination.exists():
        raise ValueError(
            "Checkpoint import refuses to overwrite an existing Scout database"
        )
    with zipfile.ZipFile(source, "r") as archive:
        names = set(archive.namelist())
        if names != {MANIFEST_MEMBER, DATABASE_MEMBER}:
            raise ValueError("Checkpoint contains unexpected or missing files")
        manifest = json.loads(archive.read(MANIFEST_MEMBER))
        if manifest.get("checkpointSchemaVersion") != CHECKPOINT_SCHEMA_VERSION:
            raise ValueError("Unsupported Scout enrichment checkpoint schema")
        database_bytes = archive.read(DATABASE_MEMBER)
    if _sha256_bytes(database_bytes) != manifest.get("databaseSha256"):
        raise ValueError("Checkpoint database hash does not match its manifest")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".importing")
    temporary.write_bytes(database_bytes)
    try:
        imported_store = ResearchStore(temporary)
        expected = manifest.get("project") or {}
        project = imported_store.get_scout_enrichment_project(int(expected["id"]))
        if project is None:
            raise ValueError("Checkpoint does not contain its declared project")
        if project["sourceSha256"] != expected.get("sourceSha256"):
            raise ValueError("Checkpoint project source hash does not match its manifest")
        if project["resourceCount"] != expected.get("resourceCount"):
            raise ValueError("Checkpoint project resource count does not match its manifest")
        os.replace(temporary, destination)
    finally:
        if temporary.exists():
            temporary.unlink()
    return {
        "project": enrichment_project_summary(project),
        "databasePath": str(destination),
        "databaseSha256": manifest["databaseSha256"],
    }
