from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from .importer import (
    ImportedPackage,
    iter_index_values,
    normalize_index_value,
    resource_attachments,
    resource_category_ids,
    resource_id,
    resource_name,
)


SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS imports (
    id INTEGER PRIMARY KEY,
    source_name TEXT NOT NULL,
    source_sha256 TEXT NOT NULL,
    imported_at TEXT NOT NULL,
    json_member TEXT NOT NULL,
    resource_path TEXT NOT NULL,
    category_path TEXT,
    schema_version TEXT,
    package_version TEXT,
    target_category_id TEXT NOT NULL,
    target_category_label TEXT NOT NULL,
    resource_count INTEGER NOT NULL,
    target_resource_count INTEGER NOT NULL,
    multicategory_target_count INTEGER NOT NULL,
    metadata_json TEXT NOT NULL,
    manifest_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS categories (
    import_id INTEGER NOT NULL REFERENCES imports(id) ON DELETE CASCADE,
    category_id TEXT NOT NULL,
    label TEXT NOT NULL,
    raw_json TEXT NOT NULL,
    PRIMARY KEY (import_id, category_id)
);
CREATE TABLE IF NOT EXISTS imported_resources (
    import_id INTEGER NOT NULL REFERENCES imports(id) ON DELETE CASCADE,
    resource_id TEXT NOT NULL,
    name TEXT NOT NULL,
    is_target INTEGER NOT NULL CHECK (is_target IN (0, 1)),
    category_ids_json TEXT NOT NULL,
    raw_json TEXT NOT NULL,
    PRIMARY KEY (import_id, resource_id)
);
CREATE TABLE IF NOT EXISTS known_terms (
    import_id INTEGER NOT NULL,
    resource_id TEXT NOT NULL,
    term_type TEXT NOT NULL,
    value TEXT NOT NULL,
    normalized TEXT NOT NULL,
    FOREIGN KEY (import_id, resource_id) REFERENCES imported_resources(import_id, resource_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS known_terms_lookup ON known_terms(import_id, normalized);
CREATE TABLE IF NOT EXISTS research_seeds (
    import_id INTEGER NOT NULL,
    resource_id TEXT NOT NULL,
    name TEXT NOT NULL,
    full_record_json TEXT NOT NULL,
    seed_context_json TEXT NOT NULL,
    PRIMARY KEY (import_id, resource_id),
    FOREIGN KEY (import_id, resource_id) REFERENCES imported_resources(import_id, resource_id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS seed_assets (
    import_id INTEGER NOT NULL,
    resource_id TEXT NOT NULL,
    asset_path TEXT NOT NULL,
    name TEXT NOT NULL,
    media_type TEXT NOT NULL,
    content BLOB NOT NULL,
    PRIMARY KEY (import_id, resource_id, asset_path),
    FOREIGN KEY (import_id, resource_id) REFERENCES research_seeds(import_id, resource_id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS discoveries (
    id INTEGER PRIMARY KEY,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    status TEXT NOT NULL,
    origin TEXT NOT NULL,
    name TEXT NOT NULL,
    candidate_json TEXT NOT NULL,
    matched_import_id INTEGER,
    matched_resource_id TEXT,
    duplicate_score REAL,
    notes TEXT NOT NULL DEFAULT '',
    match_assessment TEXT,
    match_assessed_at TEXT,
    FOREIGN KEY (matched_import_id, matched_resource_id) REFERENCES imported_resources(import_id, resource_id)
);
CREATE TABLE IF NOT EXISTS agent_settings (
    key TEXT PRIMARY KEY,
    value_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS research_runs (
    id INTEGER PRIMARY KEY,
    created_at TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT,
    status TEXT NOT NULL,
    adapter TEXT NOT NULL,
    assignment TEXT NOT NULL,
    source_import_id INTEGER REFERENCES imports(id),
    seed_import_id INTEGER,
    seed_resource_id TEXT,
    prompt_json TEXT NOT NULL,
    output_text TEXT NOT NULL DEFAULT '',
    result_json TEXT,
    usage_json TEXT,
    error TEXT NOT NULL DEFAULT '',
    FOREIGN KEY (seed_import_id, seed_resource_id)
        REFERENCES research_seeds(import_id, resource_id)
);
CREATE TABLE IF NOT EXISTS research_lessons (
    id INTEGER PRIMARY KEY,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    scope TEXT NOT NULL,
    text TEXT NOT NULL,
    rationale TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL,
    source TEXT NOT NULL,
    run_id INTEGER REFERENCES research_runs(id),
    discovery_id INTEGER REFERENCES discoveries(id)
);
"""


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


class ResearchStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.executescript(SCHEMA)
            self._migrate(connection)

    @staticmethod
    def _migrate(connection: sqlite3.Connection) -> None:
        columns = {row["name"] for row in connection.execute("PRAGMA table_info(discoveries)")}
        additions = {
            "run_id": "INTEGER",
            "reviewed_at": "TEXT",
            "review_feedback": "TEXT NOT NULL DEFAULT ''",
            "match_assessment": "TEXT",
            "match_assessed_at": "TEXT",
        }
        for name, definition in additions.items():
            if name not in columns:
                connection.execute(f"ALTER TABLE discoveries ADD COLUMN {name} {definition}")
        run_columns = {row["name"] for row in connection.execute("PRAGMA table_info(research_runs)")}
        if "source_import_id" not in run_columns:
            connection.execute(
                "ALTER TABLE research_runs ADD COLUMN source_import_id INTEGER REFERENCES imports(id)"
            )
            connection.execute(
                "UPDATE research_runs SET source_import_id = seed_import_id WHERE seed_import_id IS NOT NULL"
            )

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def save_import(self, package: ImportedPackage) -> int:
        target_ids = {resource_id(item) for item in package.target_resources}
        schema = package.schema.as_dict()
        now = datetime.now(timezone.utc).isoformat()
        with self.connect() as connection:
            cursor = connection.execute(
                """INSERT INTO imports (
                    source_name, source_sha256, imported_at, json_member, resource_path,
                    category_path, schema_version, package_version, target_category_id,
                    target_category_label, resource_count, target_resource_count,
                    multicategory_target_count, metadata_json, manifest_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    package.source_name,
                    package.sha256,
                    now,
                    schema["jsonMember"],
                    schema["resourcePath"],
                    schema["categoryPath"],
                    None if schema["schemaVersion"] is None else str(schema["schemaVersion"]),
                    None if schema["packageVersion"] is None else str(schema["packageVersion"]),
                    package.target_category_id,
                    package.target_category_label,
                    len(package.resources),
                    len(package.target_resources),
                    package.multicategory_target_count,
                    _json(package.root_metadata),
                    _json(package.manifest),
                ),
            )
            import_id = int(cursor.lastrowid)
            for category in package.categories:
                connection.execute(
                    "INSERT INTO categories VALUES (?, ?, ?, ?)",
                    (import_id, str(category["id"]), str(category["label"]), _json(category["raw"])),
                )
            for resource in package.resources:
                rid = resource_id(resource)
                name = resource_name(resource) or rid
                is_target = int(rid in target_ids)
                categories = resource_category_ids(resource)
                connection.execute(
                    "INSERT INTO imported_resources VALUES (?, ?, ?, ?, ?, ?)",
                    (import_id, rid, name, is_target, _json(categories), _json(resource)),
                )
                seen_terms: set[tuple[str, str]] = set()
                for term_type, value in iter_index_values(resource):
                    normalized = normalize_index_value(term_type, value)
                    key = (term_type, normalized)
                    if not normalized or key in seen_terms:
                        continue
                    seen_terms.add(key)
                    connection.execute(
                        "INSERT INTO known_terms VALUES (?, ?, ?, ?, ?)",
                        (import_id, rid, term_type, value, normalized),
                    )
                if is_target:
                    relationship_terms = [
                        {"type": kind, "value": value}
                        for kind, value in iter_index_values(resource)
                        if kind.startswith("relationship:") or kind in ("organization_name", "program_name")
                    ]
                    seed_context = {
                        "origin": "imported-existing-resource",
                        "isNewDiscovery": False,
                        "categoryIds": categories,
                        "relationships": relationship_terms,
                        "researchInstruction": "Use this known resource as a starting point for deeper research and branching discovery; never present it as newly discovered.",
                    }
                    connection.execute(
                        "INSERT INTO research_seeds VALUES (?, ?, ?, ?, ?)",
                        (import_id, rid, name, _json(resource), _json(seed_context)),
                    )
                    for attachment in resource_attachments(resource):
                        content = package.target_assets.get(attachment["path"])
                        if content is None:
                            continue
                        media_type = "application/pdf" if attachment["path"].lower().endswith(".pdf") else "application/octet-stream"
                        connection.execute(
                            "INSERT INTO seed_assets VALUES (?, ?, ?, ?, ?, ?)",
                            (import_id, rid, attachment["path"], attachment["name"], media_type, content),
                        )
        return import_id

    def latest_import_id(self) -> int | None:
        with self.connect() as connection:
            row = connection.execute("SELECT id FROM imports ORDER BY id DESC LIMIT 1").fetchone()
        return int(row["id"]) if row else None

    def import_summary(self, import_id: int | None = None) -> dict[str, Any] | None:
        import_id = import_id or self.latest_import_id()
        if import_id is None:
            return None
        with self.connect() as connection:
            row = connection.execute("SELECT * FROM imports WHERE id = ?", (import_id,)).fetchone()
            if not row:
                return None
            seeds = connection.execute(
                "SELECT resource_id, name FROM research_seeds WHERE import_id = ? ORDER BY name COLLATE NOCASE",
                (import_id,),
            ).fetchall()
        return {
            "id": row["id"],
            "sourceName": row["source_name"],
            "sourceSha256": row["source_sha256"],
            "importedAt": row["imported_at"],
            "schema": {
                "jsonMember": row["json_member"],
                "resourcePath": row["resource_path"],
                "categoryPath": row["category_path"],
                "schemaVersion": row["schema_version"],
                "packageVersion": row["package_version"],
            },
            "category": {"id": row["target_category_id"], "label": row["target_category_label"]},
            "resourceCount": row["resource_count"],
            "targetResourceCount": row["target_resource_count"],
            "multiCategoryTargetResourceCount": row["multicategory_target_count"],
            "targetOnlyResourceCount": row["target_resource_count"] - row["multicategory_target_count"],
            "seedNames": [{"id": seed["resource_id"], "name": seed["name"]} for seed in seeds],
        }

    def list_imports(self) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute("SELECT id FROM imports ORDER BY id DESC").fetchall()
        return [summary for row in rows if (summary := self.import_summary(int(row["id"]))) is not None]

    def list_seeds(self, import_id: int | None = None) -> list[dict[str, Any]]:
        import_id = import_id or self.latest_import_id()
        if import_id is None:
            return []
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM research_seeds WHERE import_id = ? ORDER BY name COLLATE NOCASE",
                (import_id,),
            ).fetchall()
            category_rows = connection.execute(
                "SELECT category_id, label FROM categories WHERE import_id = ?",
                (import_id,),
            ).fetchall()
            asset_rows = connection.execute(
                "SELECT resource_id, asset_path, name, media_type, length(content) AS bytes FROM seed_assets WHERE import_id = ?",
                (import_id,),
            ).fetchall()
        category_labels = {row["category_id"]: row["label"] for row in category_rows}
        assets_by_resource: dict[str, list[dict[str, Any]]] = {}
        for asset in asset_rows:
            assets_by_resource.setdefault(asset["resource_id"], []).append({
                "path": asset["asset_path"],
                "name": asset["name"],
                "mediaType": asset["media_type"],
                "bytes": asset["bytes"],
                "available": True,
            })
        result: list[dict[str, Any]] = []
        for row in rows:
            full_record = json.loads(row["full_record_json"])
            stored_assets = {asset["path"]: asset for asset in assets_by_resource.get(row["resource_id"], [])}
            attachments = []
            for attachment in resource_attachments(full_record):
                attachments.append(stored_assets.get(attachment["path"], {
                    "path": attachment["path"], "name": attachment["name"],
                    "mediaType": "application/pdf", "bytes": None, "available": False,
                }))
            category_ids = resource_category_ids(full_record)
            result.append({
                "importId": row["import_id"],
                "resourceId": row["resource_id"],
                "name": row["name"],
                "categories": [
                    {"id": category_id, "label": category_labels.get(category_id, category_id)}
                    for category_id in category_ids
                ],
                "attachments": attachments,
                "fullRecord": full_record,
                "seedContext": json.loads(row["seed_context_json"]),
            })
        return result

    def seed_asset(self, import_id: int, resource_id_value: str, asset_path: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                """SELECT name, media_type, content FROM seed_assets
                   WHERE import_id = ? AND resource_id = ? AND asset_path = ?""",
                (import_id, resource_id_value, asset_path),
            ).fetchone()
        if not row:
            return None
        return {"name": row["name"], "mediaType": row["media_type"], "content": bytes(row["content"])}

    def known_terms(self, import_id: int | None = None) -> list[dict[str, Any]]:
        import_id = import_id or self.latest_import_id()
        if import_id is None:
            return []
        with self.connect() as connection:
            rows = connection.execute(
                """SELECT term.resource_id, resource.name, resource.is_target,
                          term.term_type, term.value, term.normalized
                   FROM known_terms AS term
                   JOIN imported_resources AS resource
                     ON resource.import_id = term.import_id AND resource.resource_id = term.resource_id
                   WHERE term.import_id = ?""",
                (import_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def full_resource(self, import_id: int, resource_id_value: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT raw_json FROM imported_resources WHERE import_id = ? AND resource_id = ?",
                (import_id, resource_id_value),
            ).fetchone()
        return json.loads(row["raw_json"]) if row else None

    def get_settings(self) -> dict[str, Any]:
        with self.connect() as connection:
            rows = connection.execute("SELECT key, value_json FROM agent_settings").fetchall()
        return {row["key"]: json.loads(row["value_json"]) for row in rows}

    def save_settings(self, values: dict[str, Any]) -> dict[str, Any]:
        allowed = {
            "adapter", "hermesCommand", "hermesProfile", "hermesProvider", "hermesModel",
            "dshCommand", "dshModel", "command", "profile", "provider", "model",
            "timeoutSeconds", "maxTurns",
        }
        with self.connect() as connection:
            for key, value in values.items():
                if key not in allowed:
                    continue
                connection.execute(
                    """INSERT INTO agent_settings (key, value_json) VALUES (?, ?)
                       ON CONFLICT(key) DO UPDATE SET value_json = excluded.value_json""",
                    (key, _json(value)),
                )
        return self.get_settings()

    def create_research_run(
        self,
        adapter: str,
        assignment: str,
        prompt: dict[str, Any],
        source_import_id: int | None = None,
        seed_resource_id: str | None = None,
    ) -> int:
        now = datetime.now(timezone.utc).isoformat()
        with self.connect() as connection:
            cursor = connection.execute(
                """INSERT INTO research_runs (
                       created_at, status, adapter, assignment, source_import_id,
                       seed_import_id, seed_resource_id, prompt_json
                   ) VALUES (?, 'queued', ?, ?, ?, ?, ?, ?)""",
                (
                    now, adapter, assignment, source_import_id,
                    source_import_id if seed_resource_id else None, seed_resource_id, _json(prompt),
                ),
            )
        return int(cursor.lastrowid)

    def mark_run_running(self, run_id: int) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self.connect() as connection:
            connection.execute(
                "UPDATE research_runs SET status = 'running', started_at = ? WHERE id = ?",
                (now, run_id),
            )

    def complete_run(
        self, run_id: int, output: str, result: dict[str, Any], usage: dict[str, Any] | None
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self.connect() as connection:
            connection.execute(
                """UPDATE research_runs
                   SET status = 'completed', completed_at = ?, output_text = ?,
                       result_json = ?, usage_json = ?, error = ''
                   WHERE id = ?""",
                (now, output, _json(result), _json(usage) if usage else None, run_id),
            )

    def fail_run(self, run_id: int, error: str, output: str = "") -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self.connect() as connection:
            connection.execute(
                """UPDATE research_runs
                   SET status = 'failed', completed_at = ?, output_text = ?, error = ?
                   WHERE id = ?""",
                (now, output, error, run_id),
            )

    def get_run(self, run_id: int) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute("SELECT * FROM research_runs WHERE id = ?", (run_id,)).fetchone()
        return self._run_dict(row) if row else None

    def list_runs(self, limit: int = 30) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM research_runs ORDER BY id DESC LIMIT ?", (max(1, min(limit, 100)),)
            ).fetchall()
        return [self._run_dict(row) for row in rows]

    @staticmethod
    def _run_dict(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"], "createdAt": row["created_at"], "startedAt": row["started_at"],
            "completedAt": row["completed_at"], "status": row["status"], "adapter": row["adapter"],
            "assignment": row["assignment"], "sourceImportId": row["source_import_id"],
            "seedImportId": row["seed_import_id"],
            "seedResourceId": row["seed_resource_id"], "prompt": json.loads(row["prompt_json"]),
            "output": row["output_text"],
            "result": json.loads(row["result_json"]) if row["result_json"] else None,
            "usage": json.loads(row["usage_json"]) if row["usage_json"] else None,
            "error": row["error"],
        }

    def save_discovery(
        self,
        candidate: dict[str, Any],
        match: dict[str, Any] | None = None,
        notes: str = "",
        run_id: int | None = None,
    ) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        duplicate = bool(match and match.get("score", 0) >= 0.86)
        status = "already-known" if duplicate else "candidate"
        origin = "matched-imported-resource" if duplicate else "research-discovery"
        name = str(candidate.get("name") or candidate.get("title") or "Unnamed candidate")
        with self.connect() as connection:
            cursor = connection.execute(
                """INSERT INTO discoveries (
                    created_at, updated_at, status, origin, name, candidate_json,
                    matched_import_id, matched_resource_id, duplicate_score, notes, run_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    now, now, status, origin, name, _json(candidate),
                    match.get("importId") if match else None,
                    match.get("resourceId") if match else None,
                    match.get("score") if match else None,
                    notes, run_id,
                ),
            )
            discovery_id = int(cursor.lastrowid)
        return {"id": discovery_id, "status": status, "origin": origin, "isNewDiscovery": not duplicate}

    def review_discovery(self, discovery_id: int, status: str, feedback: str = "") -> dict[str, Any] | None:
        allowed = {"accepted", "rejected", "research-further", "already-known", "wrong-category"}
        if status not in allowed:
            raise ValueError(f"Unsupported review action: {status}")
        now = datetime.now(timezone.utc).isoformat()
        with self.connect() as connection:
            connection.execute(
                """UPDATE discoveries
                   SET status = ?, updated_at = ?, reviewed_at = ?, review_feedback = ?
                   WHERE id = ?""",
                (status, now, now, feedback, discovery_id),
            )
            row = connection.execute("SELECT * FROM discoveries WHERE id = ?", (discovery_id,)).fetchone()
        return self._discovery_dict(row) if row else None

    def assess_discovery_match(self, discovery_id: int, assessment: str) -> dict[str, Any] | None:
        allowed = {
            "same-resource",
            "same-organization-different-program",
            "related-distinct",
            "not-related",
        }
        if assessment not in allowed:
            raise ValueError(f"Unsupported match assessment: {assessment}")
        now = datetime.now(timezone.utc).isoformat()
        with self.connect() as connection:
            row = connection.execute(
                "SELECT matched_resource_id FROM discoveries WHERE id = ?", (discovery_id,)
            ).fetchone()
            if not row:
                return None
            if not row["matched_resource_id"]:
                raise ValueError("This candidate does not have a known-resource match to assess")
            connection.execute(
                """UPDATE discoveries
                   SET match_assessment = ?, match_assessed_at = ?, updated_at = ?
                   WHERE id = ?""",
                (assessment, now, now, discovery_id),
            )
            updated = connection.execute(
                "SELECT * FROM discoveries WHERE id = ?", (discovery_id,)
            ).fetchone()
        return self._discovery_dict(updated) if updated else None

    def list_discoveries(self, run_id: int | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM discoveries"
        parameters: tuple[Any, ...] = ()
        if run_id is not None:
            query += " WHERE run_id = ?"
            parameters = (run_id,)
        query += " ORDER BY id DESC"
        with self.connect() as connection:
            rows = connection.execute(query, parameters).fetchall()
        return [self._discovery_dict(row) for row in rows]

    @staticmethod
    def _discovery_dict(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"], "createdAt": row["created_at"], "updatedAt": row["updated_at"],
            "status": row["status"], "origin": row["origin"], "name": row["name"],
            "candidate": json.loads(row["candidate_json"]), "runId": row["run_id"],
            "match": (
                {"importId": row["matched_import_id"], "resourceId": row["matched_resource_id"], "score": row["duplicate_score"]}
                if row["matched_resource_id"] else None
            ),
            "notes": row["notes"], "reviewedAt": row["reviewed_at"],
            "reviewFeedback": row["review_feedback"],
            "matchAssessment": row["match_assessment"],
            "matchAssessedAt": row["match_assessed_at"],
        }

    def save_lesson(
        self,
        text: str,
        scope: str = "category",
        rationale: str = "",
        status: str = "active",
        source: str = "human",
        run_id: int | None = None,
        discovery_id: int | None = None,
    ) -> dict[str, Any]:
        text = text.strip()
        if not text:
            raise ValueError("Lesson text is required")
        if scope not in {"category", "general"}:
            raise ValueError("Lesson scope must be category or general")
        if status not in {"active", "proposed", "retired"}:
            raise ValueError("Lesson status must be active, proposed, or retired")
        now = datetime.now(timezone.utc).isoformat()
        with self.connect() as connection:
            cursor = connection.execute(
                """INSERT INTO research_lessons (
                       created_at, updated_at, scope, text, rationale, status,
                       source, run_id, discovery_id
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (now, now, scope, text, rationale.strip(), status, source, run_id, discovery_id),
            )
            lesson_id = int(cursor.lastrowid)
        return self.get_lesson(lesson_id) or {}

    def get_lesson(self, lesson_id: int) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute("SELECT * FROM research_lessons WHERE id = ?", (lesson_id,)).fetchone()
        return self._lesson_dict(row) if row else None

    def list_lessons(self, active_only: bool = False) -> list[dict[str, Any]]:
        query = "SELECT * FROM research_lessons"
        parameters: tuple[Any, ...] = ()
        if active_only:
            query += " WHERE status = ?"
            parameters = ("active",)
        query += " ORDER BY id DESC"
        with self.connect() as connection:
            rows = connection.execute(query, parameters).fetchall()
        return [self._lesson_dict(row) for row in rows]

    def update_lesson_status(self, lesson_id: int, status: str) -> dict[str, Any] | None:
        if status not in {"active", "proposed", "retired"}:
            raise ValueError("Lesson status must be active, proposed, or retired")
        now = datetime.now(timezone.utc).isoformat()
        with self.connect() as connection:
            connection.execute(
                "UPDATE research_lessons SET status = ?, updated_at = ? WHERE id = ?",
                (status, now, lesson_id),
            )
        return self.get_lesson(lesson_id)

    @staticmethod
    def _lesson_dict(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"], "createdAt": row["created_at"], "updatedAt": row["updated_at"],
            "scope": row["scope"], "text": row["text"], "rationale": row["rationale"],
            "status": row["status"], "source": row["source"], "runId": row["run_id"],
            "discoveryId": row["discovery_id"],
        }
