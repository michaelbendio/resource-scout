from __future__ import annotations

import hashlib
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
    package_content_sha256,
    package_identity,
    resource_category_ids,
    resource_id,
    resource_name,
)
from .manual_discovery import parse_manual_contribution


SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS imports (
    id INTEGER PRIMARY KEY,
    source_name TEXT NOT NULL,
    source_sha256 TEXT NOT NULL,
    content_sha256 TEXT NOT NULL,
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
    manifest_json TEXT NOT NULL,
    for_groups_json TEXT NOT NULL DEFAULT '[]',
    office_name TEXT NOT NULL DEFAULT '',
    service_area TEXT NOT NULL DEFAULT '',
    identity_source TEXT NOT NULL DEFAULT ''
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
    run_id INTEGER REFERENCES research_runs(id) ON DELETE CASCADE,
    FOREIGN KEY (matched_import_id, matched_resource_id) REFERENCES imported_resources(import_id, resource_id)
);
CREATE TABLE IF NOT EXISTS discovery_contact_lookups (
    discovery_id INTEGER PRIMARY KEY REFERENCES discoveries(id) ON DELETE CASCADE,
    run_id INTEGER NOT NULL REFERENCES research_runs(id) ON DELETE CASCADE,
    status TEXT NOT NULL CHECK (
        status IN ('verified-contact', 'unavailable', 'unreachable', 'unresolved')
    ),
    checked_at TEXT NOT NULL,
    website TEXT NOT NULL DEFAULT '',
    phone TEXT NOT NULL DEFAULT '',
    address TEXT NOT NULL DEFAULT '',
    source_url TEXT NOT NULL DEFAULT '',
    note TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS research_runs (
    id INTEGER PRIMARY KEY,
    created_at TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT,
    status TEXT NOT NULL,
    adapter TEXT NOT NULL,
    run_kind TEXT NOT NULL DEFAULT 'manual-discovery',
    assignment TEXT NOT NULL,
    research_mode TEXT NOT NULL DEFAULT 'package',
    target_location TEXT,
    regional_scope TEXT NOT NULL DEFAULT '',
    target_category_id TEXT NOT NULL DEFAULT 'housing',
    target_category_label TEXT NOT NULL DEFAULT 'Housing',
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
CREATE TABLE IF NOT EXISTS manual_discovery_contributions (
    id INTEGER PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES research_runs(id) ON DELETE CASCADE,
    source_label TEXT NOT NULL,
    source_key TEXT NOT NULL,
    source_position INTEGER NOT NULL CHECK (source_position > 0),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    raw_text TEXT NOT NULL,
    raw_sha256 TEXT NOT NULL CHECK (length(raw_sha256) = 64),
    filename TEXT NOT NULL DEFAULT '',
    parse_status TEXT NOT NULL CHECK (parse_status IN ('parsed', 'error')),
    parser_version TEXT NOT NULL,
    parsed_json TEXT,
    trailing_text TEXT NOT NULL DEFAULT '',
    warnings_json TEXT NOT NULL DEFAULT '[]',
    parse_error TEXT NOT NULL DEFAULT '',
    UNIQUE (run_id, source_key),
    UNIQUE (run_id, source_position)
);
CREATE TABLE IF NOT EXISTS manual_discovery_leads (
    id INTEGER PRIMARY KEY,
    contribution_id INTEGER NOT NULL
        REFERENCES manual_discovery_contributions(id) ON DELETE CASCADE,
    source_ordinal INTEGER NOT NULL CHECK (source_ordinal > 0),
    raw_json TEXT NOT NULL,
    organization TEXT NOT NULL DEFAULT '',
    program TEXT NOT NULL DEFAULT '',
    website_raw TEXT NOT NULL DEFAULT '',
    website_normalized TEXT NOT NULL DEFAULT '',
    phone TEXT NOT NULL DEFAULT '',
    address TEXT NOT NULL DEFAULT '',
    lead_type TEXT NOT NULL DEFAULT '',
    location_or_service_area TEXT NOT NULL DEFAULT '',
    why_relevant TEXT NOT NULL DEFAULT '',
    uncertainty TEXT NOT NULL DEFAULT '',
    normalized_organization TEXT NOT NULL DEFAULT '',
    normalized_program TEXT NOT NULL DEFAULT '',
    warnings_json TEXT NOT NULL DEFAULT '[]',
    UNIQUE (contribution_id, source_ordinal)
);
CREATE TABLE IF NOT EXISTS manual_discovery_consolidations (
    run_id INTEGER PRIMARY KEY REFERENCES research_runs(id) ON DELETE CASCADE,
    input_sha256 TEXT NOT NULL CHECK (length(input_sha256) = 64),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    funnel_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS manual_discovery_identity_groups (
    id INTEGER PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES research_runs(id) ON DELETE CASCADE,
    stable_key TEXT NOT NULL,
    display_name TEXT NOT NULL,
    organization TEXT NOT NULL DEFAULT '',
    program TEXT NOT NULL DEFAULT '',
    preferred_website TEXT NOT NULL DEFAULT '',
    routed_role TEXT NOT NULL,
    consolidation_state TEXT NOT NULL CHECK (
        consolidation_state IN ('exact', 'reviewed-merge', 'reviewed-separate', 'unresolved')
    ),
    identity_check TEXT NOT NULL DEFAULT 'uncertain',
    geography_check TEXT NOT NULL DEFAULT 'uncertain',
    category_check TEXT NOT NULL DEFAULT 'uncertain',
    current_signal_check TEXT NOT NULL DEFAULT 'uncertain',
    public_access_check TEXT NOT NULL DEFAULT 'uncertain',
    checks_json TEXT NOT NULL DEFAULT '{}',
    duplicate_matches_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE (run_id, stable_key)
);
CREATE TABLE IF NOT EXISTS manual_discovery_identity_members (
    group_id INTEGER NOT NULL
        REFERENCES manual_discovery_identity_groups(id) ON DELETE CASCADE,
    lead_id INTEGER NOT NULL REFERENCES manual_discovery_leads(id) ON DELETE CASCADE,
    membership_reason TEXT NOT NULL,
    deterministic_signal TEXT NOT NULL,
    source_order INTEGER NOT NULL,
    PRIMARY KEY (group_id, lead_id)
);
CREATE TABLE IF NOT EXISTS manual_discovery_identity_decisions (
    id INTEGER PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES research_runs(id) ON DELETE CASCADE,
    left_key TEXT NOT NULL,
    right_key TEXT NOT NULL,
    decision TEXT NOT NULL CHECK (decision IN ('same', 'separate', 'unresolved')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE (run_id, left_key, right_key),
    CHECK (left_key < right_key)
);
CREATE TABLE IF NOT EXISTS research_run_reconciliations (
    id INTEGER PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES research_runs(id) ON DELETE CASCADE,
    target_import_id INTEGER NOT NULL REFERENCES imports(id),
    created_at TEXT NOT NULL,
    result_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS discovery_reconciliation_matches (
    reconciliation_id INTEGER NOT NULL
        REFERENCES research_run_reconciliations(id) ON DELETE CASCADE,
    discovery_id INTEGER NOT NULL REFERENCES discoveries(id) ON DELETE CASCADE,
    resource_id TEXT NOT NULL,
    score REAL NOT NULL,
    classification TEXT NOT NULL,
    signals_json TEXT NOT NULL DEFAULT '[]',
    PRIMARY KEY (reconciliation_id, discovery_id)
);
CREATE TABLE IF NOT EXISTS scout_curation_jobs (
    id INTEGER PRIMARY KEY,
    import_id INTEGER NOT NULL REFERENCES imports(id),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending', 'in-progress', 'completed')),
    assignment_version TEXT NOT NULL,
    candidate_package_sha256 TEXT NOT NULL CHECK (length(candidate_package_sha256) = 64),
    location_name TEXT NOT NULL,
    office_name TEXT NOT NULL DEFAULT '',
    service_area TEXT NOT NULL DEFAULT '',
    source_package_sha256 TEXT NOT NULL,
    source_package_content_sha256 TEXT NOT NULL,
    source_package_version TEXT NOT NULL DEFAULT '',
    UNIQUE (import_id, candidate_package_sha256, assignment_version)
);
CREATE TABLE IF NOT EXISTS scout_curation_categories (
    job_id INTEGER NOT NULL REFERENCES scout_curation_jobs(id) ON DELETE CASCADE,
    category_id TEXT NOT NULL,
    category_label TEXT NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN ('pending', 'assigned', 'completed', 'failed')
    ),
    canonical_run_id INTEGER REFERENCES research_runs(id),
    candidate_count INTEGER NOT NULL DEFAULT 0,
    assignment_json TEXT NOT NULL,
    assignment_sha256 TEXT NOT NULL CHECK (length(assignment_sha256) = 64),
    result_json TEXT,
    result_sha256 TEXT NOT NULL DEFAULT '' CHECK (
        result_sha256 = '' OR length(result_sha256) = 64
    ),
    resource_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    assigned_at TEXT,
    completed_at TEXT,
    updated_at TEXT NOT NULL,
    error TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (job_id, category_id)
);
CREATE TABLE IF NOT EXISTS scout_curation_progress_events (
    id INTEGER PRIMARY KEY,
    job_id INTEGER NOT NULL REFERENCES scout_curation_jobs(id) ON DELETE CASCADE,
    category_id TEXT,
    created_at TEXT NOT NULL,
    phase TEXT NOT NULL,
    message TEXT NOT NULL,
    details_json TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS scout_workflow_progress_events (
    id INTEGER PRIMARY KEY,
    import_id INTEGER NOT NULL REFERENCES imports(id) ON DELETE CASCADE,
    category_id TEXT,
    created_at TEXT NOT NULL,
    phase TEXT NOT NULL,
    message TEXT NOT NULL,
    details_json TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS chatgpt_assignment_schedules (
    id INTEGER PRIMARY KEY,
    import_id INTEGER NOT NULL REFERENCES imports(id) ON DELETE CASCADE,
    category_id TEXT NOT NULL,
    category_label TEXT NOT NULL,
    assignment TEXT NOT NULL,
    delay_minutes INTEGER NOT NULL CHECK (delay_minutes >= 0),
    scheduled_at TEXT NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN ('scheduled', 'due', 'sent', 'cooling-down')
    ),
    reason TEXT NOT NULL DEFAULT '',
    status_note TEXT NOT NULL DEFAULT '',
    cooldown_until TEXT,
    sent_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS chatgpt_assignment_import_status
    ON chatgpt_assignment_schedules(import_id, status, id);
"""


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


class ResearchStore:
    def __init__(
        self,
        path: str | Path,
        *,
        recover_interrupted: bool = False,
    ) -> None:
        self.path = Path(path).expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.executescript(SCHEMA)
            self._migrate(connection)
            self._backfill_research_seeds(connection)

    @staticmethod
    def _migrate(connection: sqlite3.Connection) -> None:
        contact_row = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' "
            "AND name = 'discovery_contact_lookups'"
        ).fetchone()
        contact_sql = str(contact_row["sql"] or "") if contact_row else ""
        if contact_row and "'unreachable'" not in contact_sql:
            connection.execute("DROP TABLE IF EXISTS discovery_contact_lookups_migration")
            connection.execute(
                """CREATE TABLE discovery_contact_lookups_migration (
                       discovery_id INTEGER PRIMARY KEY
                           REFERENCES discoveries(id) ON DELETE CASCADE,
                       run_id INTEGER NOT NULL
                           REFERENCES research_runs(id) ON DELETE CASCADE,
                       status TEXT NOT NULL CHECK (
                           status IN (
                               'verified-contact', 'unavailable',
                               'unreachable', 'unresolved'
                           )
                       ),
                       checked_at TEXT NOT NULL,
                       website TEXT NOT NULL DEFAULT '',
                       phone TEXT NOT NULL DEFAULT '',
                       address TEXT NOT NULL DEFAULT '',
                       source_url TEXT NOT NULL DEFAULT '',
                       note TEXT NOT NULL DEFAULT '',
                       updated_at TEXT NOT NULL
                   )"""
            )
            connection.execute(
                """INSERT INTO discovery_contact_lookups_migration (
                       discovery_id, run_id, status, checked_at, website,
                       phone, address, source_url, note, updated_at
                   )
                   SELECT discovery_id, run_id, status, checked_at, website,
                          phone, address, source_url, note, updated_at
                   FROM discovery_contact_lookups"""
            )
            connection.execute("DROP TABLE discovery_contact_lookups")
            connection.execute(
                "ALTER TABLE discovery_contact_lookups_migration "
                "RENAME TO discovery_contact_lookups"
            )

        discovery_columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(discoveries)")
        }
        for name, definition in {
            "run_id": "INTEGER",
        }.items():
            if name not in discovery_columns:
                connection.execute(
                    f"ALTER TABLE discoveries ADD COLUMN {name} {definition}"
                )

        run_columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(research_runs)")
        }
        for name, definition in {
            "source_import_id": "INTEGER REFERENCES imports(id)",
            "run_kind": "TEXT NOT NULL DEFAULT 'manual-discovery'",
            "research_mode": "TEXT NOT NULL DEFAULT 'package'",
            "target_location": "TEXT",
            "regional_scope": "TEXT NOT NULL DEFAULT ''",
            "target_category_id": "TEXT NOT NULL DEFAULT 'housing'",
            "target_category_label": "TEXT NOT NULL DEFAULT 'Housing'",
        }.items():
            if name not in run_columns:
                connection.execute(
                    f"ALTER TABLE research_runs ADD COLUMN {name} {definition}"
                )
        if "source_import_id" not in run_columns and "seed_import_id" in run_columns:
            connection.execute(
                "UPDATE research_runs SET source_import_id = seed_import_id "
                "WHERE seed_import_id IS NOT NULL"
            )

        group_columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(manual_discovery_identity_groups)"
            )
        }
        for name, definition in {
            "identity_check": "TEXT NOT NULL DEFAULT 'uncertain'",
            "geography_check": "TEXT NOT NULL DEFAULT 'uncertain'",
            "category_check": "TEXT NOT NULL DEFAULT 'uncertain'",
            "current_signal_check": "TEXT NOT NULL DEFAULT 'uncertain'",
            "public_access_check": "TEXT NOT NULL DEFAULT 'uncertain'",
            "checks_json": "TEXT NOT NULL DEFAULT '{}'",
        }.items():
            if name not in group_columns:
                connection.execute(
                    f"ALTER TABLE manual_discovery_identity_groups "
                    f"ADD COLUMN {name} {definition}"
                )

        lead_columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(manual_discovery_leads)"
            )
        }
        for name in ("phone", "address"):
            if name not in lead_columns:
                connection.execute(
                    f"ALTER TABLE manual_discovery_leads "
                    f"ADD COLUMN {name} TEXT NOT NULL DEFAULT ''"
                )

        import_columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(imports)")
        }
        for name, definition in {
            "for_groups_json": "TEXT NOT NULL DEFAULT '[]'",
            "office_name": "TEXT NOT NULL DEFAULT ''",
            "service_area": "TEXT NOT NULL DEFAULT ''",
            "identity_source": "TEXT NOT NULL DEFAULT ''",
            "content_sha256": "TEXT NOT NULL DEFAULT ''",
        }.items():
            if name not in import_columns:
                connection.execute(
                    f"ALTER TABLE imports ADD COLUMN {name} {definition}"
                )

        connection.execute(
            """UPDATE research_runs
               SET source_import_id = (
                   SELECT imports.id
                   FROM imports
                   WHERE imports.imported_at <= research_runs.created_at
                   ORDER BY imports.imported_at DESC, imports.id DESC
                   LIMIT 1
               )
               WHERE research_mode = 'package'
                 AND source_import_id IS NULL"""
        )
        rows = connection.execute(
            "SELECT id, source_name, metadata_json FROM imports "
            "WHERE office_name = '' OR service_area = ''"
        ).fetchall()
        for row in rows:
            metadata = json.loads(row["metadata_json"] or "{}")
            office_name, service_area, source = package_identity(
                row["source_name"], metadata
            )
            connection.execute(
                "UPDATE imports SET office_name = ?, service_area = ?, "
                "identity_source = ? WHERE id = ?",
                (office_name, service_area, source, row["id"]),
            )
        content_rows = connection.execute(
            "SELECT id, for_groups_json, office_name, service_area FROM imports "
            "WHERE content_sha256 = ''"
        ).fetchall()
        for row in content_rows:
            categories = [
                {
                    "id": item["category_id"],
                    "label": item["label"],
                    "raw": json.loads(item["raw_json"]),
                }
                for item in connection.execute(
                    "SELECT category_id, label, raw_json FROM categories "
                    "WHERE import_id = ? ORDER BY category_id",
                    (row["id"],),
                ).fetchall()
            ]
            resources = [
                json.loads(item["raw_json"])
                for item in connection.execute(
                    "SELECT raw_json FROM imported_resources WHERE import_id = ?",
                    (row["id"],),
                ).fetchall()
            ]
            content_sha256 = package_content_sha256(
                resources,
                categories,
                json.loads(row["for_groups_json"] or "[]"),
                row["office_name"],
                row["service_area"],
            )
            connection.execute(
                "UPDATE imports SET content_sha256 = ? WHERE id = ?",
                (content_sha256, row["id"]),
            )

        ResearchStore._migrate_legacy_curation_tables(connection)

    @staticmethod
    def _migrate_legacy_curation_tables(connection: sqlite3.Connection) -> None:
        """Move v0.41.0 curation rows from their short-lived table names."""
        legacy_job_table = "auto" + "curator_jobs"
        legacy_category_table = "auto" + "curator_categories"
        legacy_progress_table = "auto" + "curator_progress_events"
        existing_tables = {
            str(row["name"])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        if legacy_job_table not in existing_tables:
            return

        legacy_count = int(
            connection.execute(
                f"SELECT COUNT(*) AS count FROM {legacy_job_table}"
            ).fetchone()["count"]
        )
        current_count = int(
            connection.execute(
                "SELECT COUNT(*) AS count FROM scout_curation_jobs"
            ).fetchone()["count"]
        )
        if legacy_count and current_count:
            raise RuntimeError(
                "Both legacy and current Scout curation jobs contain data; "
                "refusing an ambiguous automatic migration"
            )

        if legacy_count:
            connection.execute(
                f"""INSERT INTO scout_curation_jobs (
                       id, import_id, created_at, updated_at, status,
                       assignment_version, candidate_package_sha256,
                       location_name, office_name, service_area,
                       source_package_sha256, source_package_content_sha256,
                       source_package_version
                   )
                   SELECT id, import_id, created_at, updated_at, status,
                          assignment_version, candidate_package_sha256,
                          location_name, office_name, service_area,
                          source_package_sha256, source_package_content_sha256,
                          source_package_version
                   FROM {legacy_job_table}"""
            )
            if legacy_category_table in existing_tables:
                connection.execute(
                    f"""INSERT INTO scout_curation_categories (
                           job_id, category_id, category_label, status,
                           canonical_run_id, candidate_count, assignment_json,
                           assignment_sha256, result_json, result_sha256,
                           resource_count, created_at, assigned_at, completed_at,
                           updated_at, error
                       )
                       SELECT job_id, category_id, category_label, status,
                              canonical_run_id, candidate_count, assignment_json,
                              assignment_sha256, result_json, result_sha256,
                              resource_count, created_at, assigned_at, completed_at,
                              updated_at, error
                       FROM {legacy_category_table}"""
                )
            if legacy_progress_table in existing_tables:
                connection.execute(
                    f"""INSERT INTO scout_curation_progress_events (
                           id, job_id, category_id, created_at, phase, message,
                           details_json
                       )
                       SELECT id, job_id, category_id, created_at, phase, message,
                              details_json
                       FROM {legacy_progress_table}"""
                )

        for table_name in (
            legacy_progress_table,
            legacy_category_table,
            legacy_job_table,
        ):
            if table_name in existing_tables:
                connection.execute(f"DROP TABLE {table_name}")

    @staticmethod
    def _backfill_research_seeds(connection: sqlite3.Connection) -> None:
        """Make every imported category usable after upgrading older databases."""
        rows = connection.execute(
            """SELECT resource.import_id, resource.resource_id, resource.name,
                      resource.category_ids_json, resource.raw_json
               FROM imported_resources AS resource
               LEFT JOIN research_seeds AS seed
                 ON seed.import_id = resource.import_id
                AND seed.resource_id = resource.resource_id
               WHERE seed.resource_id IS NULL"""
        ).fetchall()
        for row in rows:
            categories = json.loads(row["category_ids_json"])
            if not categories:
                continue
            resource = json.loads(row["raw_json"])
            relationship_terms = [
                {"type": kind, "value": value}
                for kind, value in iter_index_values(resource)
                if kind.startswith("relationship:")
                or kind in ("organization_name", "program_name")
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
                (
                    int(row["import_id"]),
                    str(row["resource_id"]),
                    str(row["name"]),
                    _json(resource),
                    _json(seed_context),
                ),
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
                    source_name, source_sha256, content_sha256, imported_at, json_member, resource_path,
                    category_path, schema_version, package_version, target_category_id,
                    target_category_label, resource_count, target_resource_count,
                    multicategory_target_count, metadata_json, manifest_json, for_groups_json,
                    office_name, service_area, identity_source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    package.source_name,
                    package.sha256,
                    package.content_sha256,
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
                    _json(package.for_groups),
                    package.identity["officeName"],
                    package.identity["serviceArea"],
                    package.identity["identitySource"],
                ),
            )
            import_id = int(cursor.lastrowid)
            if package.for_groups:
                # Re-importing the same package should also repair older snapshots
                # created before top-level For definitions were retained. Historical
                # runs remain linked to those snapshot ids.
                connection.execute(
                    """UPDATE imports
                       SET for_groups_json = ?
                       WHERE source_sha256 = ?
                         AND (for_groups_json IS NULL OR for_groups_json = '[]')""",
                    (_json(package.for_groups), package.sha256),
                )
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
                if categories:
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
        return import_id

    def latest_import_id(self) -> int | None:
        with self.connect() as connection:
            row = connection.execute("SELECT id FROM imports ORDER BY id DESC LIMIT 1").fetchone()
        return int(row["id"]) if row else None

    @staticmethod
    def _taxonomy_labels(values: Any) -> list[str]:
        if not isinstance(values, list):
            return []
        result: list[str] = []
        for value in values:
            if isinstance(value, str):
                label = value.strip()
            elif isinstance(value, dict):
                label = str(value.get("label") or value.get("name") or value.get("id") or "").strip()
            else:
                label = ""
            if label and label not in result:
                result.append(label)
        return result

    def list_import_categories(self, import_id: int | None = None) -> list[dict[str, Any]]:
        from .playbooks import playbook_for

        import_id = import_id or self.latest_import_id()
        if import_id is None:
            return []
        with self.connect() as connection:
            import_row = connection.execute(
                "SELECT service_area FROM imports WHERE id = ?", (import_id,)
            ).fetchone()
            category_rows = connection.execute(
                "SELECT category_id, label, raw_json FROM categories WHERE import_id = ? ORDER BY rowid",
                (import_id,),
            ).fetchall()
            resource_rows = connection.execute(
                "SELECT category_ids_json FROM imported_resources WHERE import_id = ?",
                (import_id,),
            ).fetchall()
        membership = [json.loads(row["category_ids_json"]) for row in resource_rows]
        result: list[dict[str, Any]] = []
        for row in category_rows:
            category_id = str(row["category_id"])
            raw = json.loads(row["raw_json"])
            raw_object = raw if isinstance(raw, dict) else {}
            label = str(row["label"])
            resource_count = sum(category_id in ids for ids in membership)
            playbook = playbook_for(
                category_id, label, import_row["service_area"] if import_row else None
            )
            result.append({
                "id": category_id,
                "label": label,
                "types": self._taxonomy_labels(raw_object.get("filters")),
                "active": raw_object.get("active") is not False,
                "resourceCount": resource_count,
                "multiCategoryResourceCount": sum(
                    category_id in ids and len(ids) > 1 for ids in membership
                ),
                "supported": True,
                "defaultAssignment": playbook.default_assignment,
                "playbookVersion": playbook.library_version,
                "playbookSource": playbook.source,
                "specializedPlaybook": playbook.source != "generated fallback",
            })
        return result

    def import_category(self, import_id: int, category_id: str) -> dict[str, Any] | None:
        wanted = str(category_id or "").strip().casefold()
        for category in self.list_import_categories(import_id):
            if wanted in {category["id"].casefold(), category["label"].casefold()}:
                with self.connect() as connection:
                    row = connection.execute(
                        "SELECT raw_json FROM categories WHERE import_id = ? AND category_id = ?",
                        (import_id, category["id"]),
                    ).fetchone()
                raw = json.loads(row["raw_json"]) if row else {}
                value = dict(raw) if isinstance(raw, dict) else {}
                value.update({"id": category["id"], "label": category["label"]})
                return value
        return None

    def import_for_groups(self, import_id: int) -> list[Any]:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT for_groups_json FROM imports WHERE id = ?", (import_id,)
            ).fetchone()
        return json.loads(row["for_groups_json"]) if row else []

    def import_taxonomy(self, import_id: int) -> dict[str, Any]:
        return {
            "categories": self.list_import_categories(import_id),
            "forGroups": self._taxonomy_labels(self.import_for_groups(import_id)),
        }

    def import_summary(self, import_id: int | None = None) -> dict[str, Any] | None:
        import_id = import_id or self.latest_import_id()
        if import_id is None:
            return None
        with self.connect() as connection:
            row = connection.execute("SELECT * FROM imports WHERE id = ?", (import_id,)).fetchone()
            if not row:
                return None
        categories = self.list_import_categories(import_id)
        legacy_category = next(
            (item for item in categories if item["id"] == row["target_category_id"]),
            {"id": row["target_category_id"], "label": row["target_category_label"]},
        )
        seeds = self.list_seeds(import_id, str(legacy_category["id"]))
        return {
            "id": row["id"],
            "sourceName": row["source_name"],
            "sourceSha256": row["source_sha256"],
            "contentSha256": row["content_sha256"],
            "officeName": row["office_name"],
            "serviceArea": row["service_area"],
            "identitySource": row["identity_source"],
            "importedAt": row["imported_at"],
            "schema": {
                "jsonMember": row["json_member"],
                "resourcePath": row["resource_path"],
                "categoryPath": row["category_path"],
                "schemaVersion": row["schema_version"],
                "packageVersion": row["package_version"],
            },
            "category": {"id": legacy_category["id"], "label": legacy_category["label"]},
            "categories": categories,
            "forGroups": self._taxonomy_labels(json.loads(row["for_groups_json"])),
            "resourceCount": row["resource_count"],
            "targetResourceCount": row["target_resource_count"],
            "multiCategoryTargetResourceCount": row["multicategory_target_count"],
            "targetOnlyResourceCount": row["target_resource_count"] - row["multicategory_target_count"],
            "seedNames": [{"id": seed["resourceId"], "name": seed["name"]} for seed in seeds],
        }

    def list_imports(self) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute("SELECT id FROM imports ORDER BY id DESC").fetchall()
        return [summary for row in rows if (summary := self.import_summary(int(row["id"]))) is not None]

    def list_seeds(
        self, import_id: int | None = None, category_id: str | None = None
    ) -> list[dict[str, Any]]:
        import_id = import_id or self.latest_import_id()
        if import_id is None:
            return []
        with self.connect() as connection:
            import_row = connection.execute(
                "SELECT target_category_id FROM imports WHERE id = ?", (import_id,)
            ).fetchone()
            if not import_row:
                return []
            selected_category_id = str(category_id or import_row["target_category_id"])
            rows = connection.execute(
                "SELECT * FROM imported_resources WHERE import_id = ? ORDER BY name COLLATE NOCASE",
                (import_id,),
            ).fetchall()
            category_rows = connection.execute(
                "SELECT category_id, label FROM categories WHERE import_id = ?",
                (import_id,),
            ).fetchall()
        category_labels = {row["category_id"]: row["label"] for row in category_rows}
        result: list[dict[str, Any]] = []
        for row in rows:
            category_ids = json.loads(row["category_ids_json"])
            if selected_category_id not in category_ids:
                continue
            full_record = json.loads(row["raw_json"])
            relationship_terms = [
                {"type": kind, "value": value}
                for kind, value in iter_index_values(full_record)
                if kind.startswith("relationship:") or kind in ("organization_name", "program_name")
            ]
            result.append({
                "importId": row["import_id"],
                "resourceId": row["resource_id"],
                "name": row["name"],
                "categories": [
                    {"id": category_id, "label": category_labels.get(category_id, category_id)}
                    for category_id in category_ids
                ],
                "fullRecord": full_record,
                "seedContext": {
                    "origin": "imported-existing-resource",
                    "isNewDiscovery": False,
                    "categoryIds": category_ids,
                    "relationships": relationship_terms,
                    "researchInstruction": "Use this known resource as a starting point for deeper research and branching discovery; never present it as newly discovered.",
                },
            })
        return result

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

    def create_manual_discovery_run(
        self,
        assignment: str,
        prompt: dict[str, Any],
        source_import_id: int | None = None,
        *,
        research_mode: str = "package",
        target_location: str | None = None,
        regional_scope: str = "",
        target_category_id: str = "housing",
        target_category_label: str = "Housing",
    ) -> int:
        if research_mode not in {"package", "standalone-location"}:
            raise ValueError(f"Unsupported research mode: {research_mode}")
        now = datetime.now(timezone.utc).isoformat()
        with self.connect() as connection:
            cursor = connection.execute(
                """INSERT INTO research_runs (
                       created_at, started_at, status, adapter, run_kind,
                       assignment, research_mode, target_location, regional_scope,
                       target_category_id, target_category_label, source_import_id,
                       prompt_json
                   ) VALUES (?, ?, 'running', 'chat', 'manual-discovery', ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    now,
                    now,
                    assignment,
                    research_mode,
                    target_location,
                    regional_scope,
                    target_category_id,
                    target_category_label,
                    source_import_id,
                    _json(prompt),
                ),
            )
            return int(cursor.lastrowid)

    def delete_empty_manual_discovery_run(self, run_id: int) -> bool:
        with self.connect() as connection:
            cursor = connection.execute(
                """DELETE FROM research_runs
                   WHERE id = ? AND run_kind = 'manual-discovery' AND status = 'running'
                     AND NOT EXISTS (
                       SELECT 1 FROM manual_discovery_contributions
                       WHERE run_id = research_runs.id
                     )""",
                (run_id,),
            )
            return cursor.rowcount > 0

    def save_manual_contribution(
        self,
        run_id: int,
        source_label: str,
        raw_text: str,
        *,
        filename: str = "",
    ) -> dict[str, Any]:
        label = " ".join(str(source_label).split())
        if not label:
            raise ValueError("Source label is required")
        if len(label) > 100:
            raise ValueError("Source label may not exceed 100 characters")
        source_key = label.casefold()
        parsed = parse_manual_contribution(raw_text)
        now = datetime.now(timezone.utc).isoformat()
        raw_sha256 = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
        safe_filename = Path(filename).name if filename else ""
        with self.connect() as connection:
            run = connection.execute(
                "SELECT run_kind, status FROM research_runs WHERE id = ?",
                (run_id,),
            ).fetchone()
            if not run:
                raise ValueError("Research run not found")
            if run["run_kind"] != "manual-discovery":
                raise ValueError("Contributions can only be saved to a manual discovery run")
            if run["status"] != "running":
                raise ValueError("Contributions can only be changed while the run is open")
            existing = connection.execute(
                """SELECT id, source_position, created_at, source_label, raw_sha256, filename
                   FROM manual_discovery_contributions
                   WHERE run_id = ? AND source_key = ?""",
                (run_id, source_key),
            ).fetchone()
            unchanged = bool(
                existing
                and existing["source_label"] == label
                and existing["raw_sha256"] == raw_sha256
                and existing["filename"] == safe_filename
            )
            if unchanged:
                contribution_id = int(existing["id"])
            else:
                self._invalidate_manual_consolidation(connection, run_id)
            if existing and not unchanged:
                contribution_id = int(existing["id"])
                connection.execute(
                    """UPDATE manual_discovery_contributions
                       SET source_label = ?, updated_at = ?, raw_text = ?, raw_sha256 = ?,
                           filename = ?, parse_status = ?, parser_version = ?, parsed_json = ?,
                           trailing_text = ?, warnings_json = ?, parse_error = ?
                       WHERE id = ?""",
                    (
                        label,
                        now,
                        raw_text,
                        raw_sha256,
                        safe_filename,
                        parsed["status"],
                        parsed["parserVersion"],
                        _json(parsed["parsed"]) if parsed["parsed"] is not None else None,
                        parsed["trailingText"],
                        _json(parsed["warnings"]),
                        parsed["error"],
                        contribution_id,
                    ),
                )
                connection.execute(
                    "DELETE FROM manual_discovery_leads WHERE contribution_id = ?",
                    (contribution_id,),
                )
            elif not existing:
                position = int(
                    connection.execute(
                        """SELECT COALESCE(MAX(source_position), 0) + 1
                           FROM manual_discovery_contributions WHERE run_id = ?""",
                        (run_id,),
                    ).fetchone()[0]
                )
                cursor = connection.execute(
                    """INSERT INTO manual_discovery_contributions (
                           run_id, source_label, source_key, source_position, created_at,
                           updated_at, raw_text, raw_sha256, filename, parse_status,
                           parser_version, parsed_json, trailing_text, warnings_json, parse_error
                       ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        run_id,
                        label,
                        source_key,
                        position,
                        now,
                        now,
                        raw_text,
                        raw_sha256,
                        safe_filename,
                        parsed["status"],
                        parsed["parserVersion"],
                        _json(parsed["parsed"]) if parsed["parsed"] is not None else None,
                        parsed["trailingText"],
                        _json(parsed["warnings"]),
                        parsed["error"],
                    ),
                )
                contribution_id = int(cursor.lastrowid)
            if not unchanged:
                for lead in parsed["leads"]:
                    connection.execute(
                        """INSERT INTO manual_discovery_leads (
                               contribution_id, source_ordinal, raw_json, organization, program,
                               website_raw, website_normalized, phone, address, lead_type,
                               location_or_service_area, why_relevant, uncertainty,
                               normalized_organization, normalized_program, warnings_json
                           ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            contribution_id,
                            lead["ordinal"],
                            _json(lead["raw"]),
                            lead["organization"],
                            lead["program"],
                            lead["websiteRaw"],
                            lead["website"],
                            lead["phone"],
                            lead["address"],
                            lead["leadType"],
                            lead["locationOrServiceArea"],
                            lead["whyRelevant"],
                            lead["uncertainty"],
                            lead["normalizedOrganization"],
                            lead["normalizedProgram"],
                            _json(lead["warnings"]),
                        ),
                    )
        contribution = self.get_manual_contribution(run_id, contribution_id)
        if contribution is None:  # pragma: no cover - guarded by the transaction above
            raise RuntimeError("Saved contribution could not be read")
        return contribution

    def list_manual_contributions(self, run_id: int) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """SELECT * FROM manual_discovery_contributions
                   WHERE run_id = ? ORDER BY source_position""",
                (run_id,),
            ).fetchall()
            return [self._manual_contribution_dict(connection, row) for row in rows]

    def get_manual_contribution(
        self, run_id: int, contribution_id: int
    ) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                """SELECT * FROM manual_discovery_contributions
                   WHERE run_id = ? AND id = ?""",
                (run_id, contribution_id),
            ).fetchone()
            if not row:
                return None
            return self._manual_contribution_dict(connection, row)

    def delete_manual_contribution(self, run_id: int, contribution_id: int) -> bool:
        with self.connect() as connection:
            run = connection.execute(
                "SELECT run_kind, status FROM research_runs WHERE id = ?",
                (run_id,),
            ).fetchone()
            if not run:
                raise ValueError("Research run not found")
            if run["run_kind"] != "manual-discovery":
                raise ValueError("Contributions only belong to manual discovery runs")
            if run["status"] != "running":
                raise ValueError("Contributions can only be changed while the run is open")
            cursor = connection.execute(
                """DELETE FROM manual_discovery_contributions
                   WHERE run_id = ? AND id = ?""",
                (run_id, contribution_id),
            )
            if cursor.rowcount > 0:
                self._invalidate_manual_consolidation(connection, run_id)
            return cursor.rowcount > 0

    @staticmethod
    def _invalidate_manual_consolidation(
        connection: sqlite3.Connection, run_id: int
    ) -> None:
        connection.execute(
            "DELETE FROM manual_discovery_identity_groups WHERE run_id = ?", (run_id,)
        )
        connection.execute(
            "DELETE FROM manual_discovery_identity_decisions WHERE run_id = ?", (run_id,)
        )
        connection.execute(
            "DELETE FROM manual_discovery_consolidations WHERE run_id = ?", (run_id,)
        )

    def manual_leads_for_consolidation(self, run_id: int) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """SELECT leads.*, contributions.source_label,
                          contributions.source_position, contributions.raw_sha256
                   FROM manual_discovery_leads AS leads
                   JOIN manual_discovery_contributions AS contributions
                     ON contributions.id = leads.contribution_id
                   WHERE contributions.run_id = ?
                   ORDER BY contributions.source_position, leads.source_ordinal""",
                (run_id,),
            ).fetchall()
        return [
            {
                "id": row["id"],
                "contributionId": row["contribution_id"],
                "sourceLabel": row["source_label"],
                "sourcePosition": row["source_position"],
                "sourceOrdinal": row["source_ordinal"],
                "rawSha256": row["raw_sha256"],
                "raw": json.loads(row["raw_json"]),
                "organization": row["organization"],
                "program": row["program"],
                "websiteRaw": row["website_raw"],
                "website": row["website_normalized"],
                "phone": row["phone"],
                "address": row["address"],
                "leadType": row["lead_type"],
                "locationOrServiceArea": row["location_or_service_area"],
                "whyRelevant": row["why_relevant"],
                "uncertainty": row["uncertainty"],
                "normalizedOrganization": row["normalized_organization"],
                "normalizedProgram": row["normalized_program"],
                "warnings": json.loads(row["warnings_json"]),
            }
            for row in rows
        ]

    def manual_identity_decisions(self, run_id: int) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """SELECT * FROM manual_discovery_identity_decisions
                   WHERE run_id = ? ORDER BY left_key, right_key""",
                (run_id,),
            ).fetchall()
        return [
            {
                "leftKey": row["left_key"],
                "rightKey": row["right_key"],
                "decision": row["decision"],
                "createdAt": row["created_at"],
                "updatedAt": row["updated_at"],
            }
            for row in rows
        ]

    def save_manual_identity_decision(
        self, run_id: int, left_key: str, right_key: str, decision: str
    ) -> dict[str, Any]:
        left, right = sorted((str(left_key), str(right_key)))
        if not left or left == right:
            raise ValueError("Two different identity groups are required")
        if decision not in {"same", "separate", "unresolved"}:
            raise ValueError("Identity decision must be same, separate, or unresolved")
        now = datetime.now(timezone.utc).isoformat()
        with self.connect() as connection:
            run = connection.execute(
                "SELECT run_kind, status FROM research_runs WHERE id = ?", (run_id,)
            ).fetchone()
            if not run or run["run_kind"] != "manual-discovery":
                raise ValueError("Manual discovery run not found")
            if run["status"] != "running":
                raise ValueError("Identity decisions can only change while the run is open")
            connection.execute(
                """INSERT INTO manual_discovery_identity_decisions (
                       run_id, left_key, right_key, decision, created_at, updated_at
                   ) VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(run_id, left_key, right_key) DO UPDATE SET
                       decision = excluded.decision, updated_at = excluded.updated_at""",
                (run_id, left, right, decision, now, now),
            )
        return {"leftKey": left, "rightKey": right, "decision": decision}

    def save_manual_identity_decisions(
        self, run_id: int, decisions: list[dict[str, str]]
    ) -> list[dict[str, str]]:
        normalized = []
        for item in decisions:
            left, right = sorted(
                (str(item.get("leftKey") or ""), str(item.get("rightKey") or ""))
            )
            decision = str(item.get("decision") or "")
            if not left or left == right:
                raise ValueError("Two different identity groups are required")
            if decision not in {"same", "separate", "unresolved"}:
                raise ValueError("Identity decision must be same, separate, or unresolved")
            normalized.append({"leftKey": left, "rightKey": right, "decision": decision})
        now = datetime.now(timezone.utc).isoformat()
        with self.connect() as connection:
            run = connection.execute(
                "SELECT run_kind, status FROM research_runs WHERE id = ?", (run_id,)
            ).fetchone()
            if not run or run["run_kind"] != "manual-discovery":
                raise ValueError("Manual discovery run not found")
            if run["status"] != "running":
                raise ValueError("Identity decisions can only change while the run is open")
            for item in normalized:
                connection.execute(
                    """INSERT INTO manual_discovery_identity_decisions (
                           run_id, left_key, right_key, decision, created_at, updated_at
                       ) VALUES (?, ?, ?, ?, ?, ?)
                       ON CONFLICT(run_id, left_key, right_key) DO UPDATE SET
                           decision = excluded.decision, updated_at = excluded.updated_at""",
                    (
                        run_id,
                        item["leftKey"],
                        item["rightKey"],
                        item["decision"],
                        now,
                        now,
                    ),
                )
        return normalized

    def replace_manual_consolidation(
        self,
        run_id: int,
        input_sha256: str,
        groups: list[dict[str, Any]],
        funnel: dict[str, int],
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self.connect() as connection:
            run = connection.execute(
                "SELECT run_kind, status FROM research_runs WHERE id = ?", (run_id,)
            ).fetchone()
            if not run or run["run_kind"] != "manual-discovery":
                raise ValueError("Manual discovery run not found")
            if run["status"] != "running":
                raise ValueError("Consolidation can only change while the run is open")
            connection.execute(
                "DELETE FROM manual_discovery_identity_groups WHERE run_id = ?", (run_id,)
            )
            for group in sorted(groups, key=lambda item: item["stableKey"]):
                cursor = connection.execute(
                    """INSERT INTO manual_discovery_identity_groups (
                           run_id, stable_key, display_name, organization, program,
                           preferred_website, routed_role, consolidation_state,
                           identity_check, geography_check, category_check,
                           current_signal_check, public_access_check, checks_json,
                           duplicate_matches_json, created_at, updated_at
                       ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        run_id,
                        group["stableKey"],
                        group["displayName"],
                        group["organization"],
                        group["program"],
                        group["website"],
                        group["routedRole"],
                        group["consolidationState"],
                        group["checks"]["identity"]["state"],
                        group["checks"]["geography"]["state"],
                        group["checks"]["categoryRelevance"]["state"],
                        group["checks"]["currentSignal"]["state"],
                        group["checks"]["publicAccess"]["state"],
                        _json(group["checks"]),
                        _json(group.get("duplicateMatches", [])),
                        now,
                        now,
                    ),
                )
                group_id = int(cursor.lastrowid)
                for position, member in enumerate(group["members"], start=1):
                    connection.execute(
                        """INSERT INTO manual_discovery_identity_members (
                               group_id, lead_id, membership_reason,
                               deterministic_signal, source_order
                           ) VALUES (?, ?, ?, ?, ?)""",
                        (
                            group_id,
                            member["id"],
                            member["membershipReason"],
                            member["deterministicSignal"],
                            position,
                        ),
                    )
            connection.execute(
                """INSERT INTO manual_discovery_consolidations (
                       run_id, input_sha256, created_at, updated_at, funnel_json
                   ) VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(run_id) DO UPDATE SET input_sha256 = excluded.input_sha256,
                       updated_at = excluded.updated_at, funnel_json = excluded.funnel_json""",
                (run_id, input_sha256, now, now, _json(funnel)),
            )

    def manual_consolidation_snapshot(self, run_id: int) -> dict[str, Any] | None:
        with self.connect() as connection:
            consolidation = connection.execute(
                "SELECT * FROM manual_discovery_consolidations WHERE run_id = ?", (run_id,)
            ).fetchone()
            if not consolidation:
                return None
            group_rows = connection.execute(
                """SELECT * FROM manual_discovery_identity_groups
                   WHERE run_id = ? ORDER BY display_name COLLATE NOCASE, stable_key""",
                (run_id,),
            ).fetchall()
            groups = []
            for row in group_rows:
                member_rows = connection.execute(
                    """SELECT members.membership_reason, members.deterministic_signal,
                              leads.*, contributions.source_label,
                              contributions.source_position
                       FROM manual_discovery_identity_members AS members
                       JOIN manual_discovery_leads AS leads ON leads.id = members.lead_id
                       JOIN manual_discovery_contributions AS contributions
                         ON contributions.id = leads.contribution_id
                       WHERE members.group_id = ? ORDER BY members.source_order""",
                    (row["id"],),
                ).fetchall()
                groups.append({
                    "id": row["id"],
                    "stableKey": row["stable_key"],
                    "displayName": row["display_name"],
                    "organization": row["organization"],
                    "program": row["program"],
                    "website": row["preferred_website"],
                    "routedRole": row["routed_role"],
                    "consolidationState": row["consolidation_state"],
                    "checks": json.loads(row["checks_json"]),
                    "duplicateMatches": json.loads(row["duplicate_matches_json"]),
                    "members": [
                        {
                            "id": member["id"],
                            "sourceLabel": member["source_label"],
                            "sourcePosition": member["source_position"],
                            "sourceOrdinal": member["source_ordinal"],
                            "organization": member["organization"],
                            "program": member["program"],
                            "website": member["website_normalized"],
                            "phone": member["phone"],
                            "address": member["address"],
                            "leadType": member["lead_type"],
                            "locationOrServiceArea": member["location_or_service_area"],
                            "whyRelevant": member["why_relevant"],
                            "uncertainty": member["uncertainty"],
                            "membershipReason": member["membership_reason"],
                            "deterministicSignal": member["deterministic_signal"],
                        }
                        for member in member_rows
                    ],
                })
        return {
            "inputSha256": consolidation["input_sha256"],
            "createdAt": consolidation["created_at"],
            "updatedAt": consolidation["updated_at"],
            "funnel": json.loads(consolidation["funnel_json"]),
            "groups": groups,
        }

    def manual_discovery_progress(self, run_id: int) -> dict[str, int]:
        with self.connect() as connection:
            row = connection.execute(
                """SELECT COUNT(*) AS contribution_count,
                          SUM(parse_status = 'parsed') AS parsed_count,
                          SUM(parse_status = 'error') AS error_count,
                          (SELECT COUNT(*) FROM manual_discovery_leads leads
                           JOIN manual_discovery_contributions contributions
                             ON contributions.id = leads.contribution_id
                           WHERE contributions.run_id = ?) AS lead_count
                   FROM manual_discovery_contributions WHERE run_id = ?""",
                (run_id, run_id),
            ).fetchone()
        return {
            "contributionCount": int(row["contribution_count"] or 0),
            "parsedContributionCount": int(row["parsed_count"] or 0),
            "errorContributionCount": int(row["error_count"] or 0),
            "leadCount": int(row["lead_count"] or 0),
        }

    def finish_manual_consolidated_run(
        self,
        run_id: int,
        candidates: list[dict[str, Any]],
        funnel: dict[str, int],
    ) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        with self.connect() as connection:
            run = connection.execute(
                "SELECT run_kind, status FROM research_runs WHERE id = ?", (run_id,)
            ).fetchone()
            if not run or run["run_kind"] != "manual-discovery":
                raise ValueError("Manual discovery run not found")
            if run["status"] != "running":
                raise ValueError("Manual discovery run is already closed")
            consolidation = connection.execute(
                "SELECT 1 FROM manual_discovery_consolidations WHERE run_id = ?", (run_id,)
            ).fetchone()
            if not consolidation:
                raise ValueError("Consolidate the current responses before finishing discovery")
            existing = connection.execute(
                "SELECT 1 FROM discoveries WHERE run_id = ?", (run_id,)
            ).fetchone()
            if existing:
                raise ValueError("This manual discovery run already has candidate records")
            for item in candidates:
                candidate = item["candidate"]
                match = item.get("match")
                duplicate = bool(match and match.get("score", 0) >= 0.86)
                connection.execute(
                    """INSERT INTO discoveries (
                           created_at, updated_at, status, origin, name, candidate_json,
                           matched_import_id, matched_resource_id, duplicate_score,
                           notes, run_id
                       ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, '', ?)""",
                    (
                        now,
                        now,
                        "already-known" if duplicate else "candidate",
                        "matched-imported-resource" if duplicate else "manual-chat-discovery",
                        str(candidate.get("name") or "Unnamed candidate"),
                        _json(candidate),
                        match.get("importId") if match else None,
                        match.get("resourceId") if match else None,
                        match.get("score") if match else None,
                        run_id,
                    ),
                )
            summary = (
                f"Manual discovery consolidated {funnel['parsedLeads']} parsed lead"
                f"{'s' if funnel['parsedLeads'] != 1 else ''} into "
                f"{funnel['consolidatedIdentities']} identit"
                f"{'ies' if funnel['consolidatedIdentities'] != 1 else 'y'} and created "
                f"{len(candidates)} candidate record{'s' if len(candidates) != 1 else ''}."
            )
            result = {
                "summary": summary,
                "manualDiscoveryProgress": self.manual_discovery_progress(run_id),
                "manualDiscoveryFunnel": funnel,
                "candidateCount": len(candidates),
            }
            connection.execute(
                """UPDATE research_runs
                   SET status = 'completed', completed_at = ?, output_text = '',
                       result_json = ?, usage_json = NULL, error = ''
                   WHERE id = ?""",
                (now, _json(result), run_id),
            )
        finished = self.get_run(run_id)
        if finished is None:  # pragma: no cover - guarded by lookup above
            raise RuntimeError("Finished run could not be read")
        return finished

    @staticmethod
    def _manual_contribution_dict(
        connection: sqlite3.Connection, row: sqlite3.Row
    ) -> dict[str, Any]:
        lead_rows = connection.execute(
            """SELECT * FROM manual_discovery_leads
               WHERE contribution_id = ? ORDER BY source_ordinal""",
            (row["id"],),
        ).fetchall()
        leads = [
            {
                "id": lead["id"],
                "ordinal": lead["source_ordinal"],
                "raw": json.loads(lead["raw_json"]),
                "organization": lead["organization"],
                "program": lead["program"],
                "websiteRaw": lead["website_raw"],
                "website": lead["website_normalized"],
                "phone": lead["phone"],
                "address": lead["address"],
                "leadType": lead["lead_type"],
                "locationOrServiceArea": lead["location_or_service_area"],
                "whyRelevant": lead["why_relevant"],
                "uncertainty": lead["uncertainty"],
                "normalizedOrganization": lead["normalized_organization"],
                "normalizedProgram": lead["normalized_program"],
                "warnings": json.loads(lead["warnings_json"]),
            }
            for lead in lead_rows
        ]
        return {
            "id": row["id"],
            "runId": row["run_id"],
            "sourceLabel": row["source_label"],
            "sourcePosition": row["source_position"],
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"],
            "rawText": row["raw_text"],
            "rawSha256": row["raw_sha256"],
            "filename": row["filename"],
            "parseStatus": row["parse_status"],
            "parserVersion": row["parser_version"],
            "parsed": json.loads(row["parsed_json"]) if row["parsed_json"] else None,
            "trailingText": row["trailing_text"],
            "warnings": json.loads(row["warnings_json"]),
            "error": row["parse_error"],
            "leads": leads,
        }

    def get_run(self, run_id: int) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                """SELECT research_runs.*, imports.office_name AS source_office_name,
                          imports.service_area AS source_service_area,
                          imports.source_sha256 AS source_package_sha256,
                          imports.content_sha256 AS source_package_content_sha256
                   FROM research_runs
                   LEFT JOIN imports ON imports.id = research_runs.source_import_id
                   WHERE research_runs.id = ?
                     AND research_runs.run_kind = 'manual-discovery'""",
                (run_id,),
            ).fetchone()
        if not row:
            return None
        value = self._run_dict(row)
        value["manualProgress"] = self.manual_discovery_progress(run_id)
        value["reconciliation"] = self.latest_run_reconciliation(run_id)
        return value

    def list_runs(
        self,
        limit: int | None = 30,
        *,
        import_id: int | None = None,
    ) -> list[dict[str, Any]]:
        package_scope = ""
        parameters: tuple[Any, ...]
        if import_id is not None:
            package_scope = """
                     AND COALESCE(
                           (SELECT target_import_id
                              FROM research_run_reconciliations
                             WHERE run_id = research_runs.id
                             ORDER BY id DESC LIMIT 1),
                           research_runs.source_import_id
                         ) = ?"""
            parameters = (int(import_id),)
        else:
            parameters = ()
        limit_clause = ""
        if limit is not None:
            limit_clause = " LIMIT ?"
            parameters += (max(1, min(limit, 100)),)
        with self.connect() as connection:
            rows = connection.execute(
                f"""SELECT research_runs.*, imports.office_name AS source_office_name,
                          imports.service_area AS source_service_area,
                          imports.source_sha256 AS source_package_sha256,
                          imports.content_sha256 AS source_package_content_sha256
                   FROM research_runs
                   LEFT JOIN imports ON imports.id = research_runs.source_import_id
                   WHERE research_runs.run_kind = 'manual-discovery'
                   {package_scope}
                   ORDER BY research_runs.id DESC{limit_clause}""",
                parameters,
            ).fetchall()
        result = []
        for row in rows:
            value = self._run_dict(row)
            value["manualProgress"] = self.manual_discovery_progress(int(row["id"]))
            value["reconciliation"] = self.latest_run_reconciliation(int(row["id"]))
            result.append(value)
        return result

    def save_run_reconciliation(
        self,
        run_id: int,
        target_import_id: int,
        matches: list[dict[str, Any]],
        result: dict[str, Any],
    ) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        with self.connect() as connection:
            run = connection.execute(
                "SELECT status, run_kind, research_mode FROM research_runs WHERE id = ?",
                (run_id,),
            ).fetchone()
            if not run or run["run_kind"] != "manual-discovery":
                raise ValueError("Discovery run not found")
            if run["status"] != "completed":
                raise ValueError("Finish discovery before reconciling its candidates")
            if run["research_mode"] != "package":
                raise ValueError("Standalone-location research has no package to reconcile")
            if not connection.execute(
                "SELECT 1 FROM imports WHERE id = ?", (target_import_id,)
            ).fetchone():
                raise ValueError("Resource package snapshot not found")
            discovery_ids = {
                int(row["id"])
                for row in connection.execute(
                    "SELECT id FROM discoveries WHERE run_id = ?", (run_id,)
                ).fetchall()
            }
            if any(int(item["discoveryId"]) not in discovery_ids for item in matches):
                raise ValueError("A reconciliation match does not belong to this discovery run")
            cursor = connection.execute(
                """INSERT INTO research_run_reconciliations (
                       run_id, target_import_id, created_at, result_json
                   ) VALUES (?, ?, ?, ?)""",
                (run_id, target_import_id, now, _json(result)),
            )
            reconciliation_id = int(cursor.lastrowid)
            for item in matches:
                connection.execute(
                    """INSERT INTO discovery_reconciliation_matches (
                           reconciliation_id, discovery_id, resource_id, score,
                           classification, signals_json
                       ) VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        reconciliation_id,
                        int(item["discoveryId"]),
                        str(item["resourceId"]),
                        float(item["score"]),
                        str(item["classification"]),
                        _json(item.get("signals", [])),
                    ),
                )
        saved = self.latest_run_reconciliation(run_id)
        if saved is None:  # pragma: no cover - guarded by insert above
            raise RuntimeError("Saved reconciliation could not be read")
        return saved

    def latest_run_reconciliation(self, run_id: int) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                """SELECT reconciliations.*, imports.source_name,
                          imports.source_sha256, imports.content_sha256,
                          imports.package_version,
                          imports.office_name, imports.service_area
                   FROM research_run_reconciliations reconciliations
                   JOIN imports ON imports.id = reconciliations.target_import_id
                   WHERE reconciliations.run_id = ?
                   ORDER BY reconciliations.id DESC LIMIT 1""",
                (run_id,),
            ).fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "runId": row["run_id"],
            "targetImportId": row["target_import_id"],
            "createdAt": row["created_at"],
            "result": json.loads(row["result_json"]),
            "targetPackage": {
                "sourceName": row["source_name"],
                "sourceSha256": row["source_sha256"],
                "contentSha256": row["content_sha256"],
                "packageVersion": row["package_version"],
                "officeName": row["office_name"],
                "serviceArea": row["service_area"],
            },
        }

    def reconciliation_matches(self, reconciliation_id: int) -> dict[int, dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """SELECT matches.*, reconciliations.target_import_id
                   FROM discovery_reconciliation_matches matches
                   JOIN research_run_reconciliations reconciliations
                     ON reconciliations.id = matches.reconciliation_id
                   WHERE matches.reconciliation_id = ?""",
                (reconciliation_id,),
            ).fetchall()
        return {
            int(row["discovery_id"]): {
                "importId": row["target_import_id"],
                "resourceId": row["resource_id"],
                "score": row["score"],
                "classification": row["classification"],
                "signals": json.loads(row["signals_json"]),
            }
            for row in rows
        }

    @staticmethod
    def _run_dict(row: sqlite3.Row) -> dict[str, Any]:
        prompt = json.loads(row["prompt_json"] or "{}")
        source_package = prompt.get("researchContext", {}).get("sourcePackage") or {}
        return {
            "id": row["id"],
            "createdAt": row["created_at"],
            "startedAt": row["started_at"],
            "completedAt": row["completed_at"],
            "status": row["status"],
            "assignment": row["assignment"],
            "researchMode": row["research_mode"],
            "targetLocation": row["target_location"],
            "regionalScope": row["regional_scope"],
            "targetCategoryId": row["target_category_id"],
            "targetCategoryLabel": row["target_category_label"],
            "sourceImportId": row["source_import_id"],
            "sourcePackageSha256": (
                row["source_package_sha256"]
                if "source_package_sha256" in row.keys()
                else source_package.get("sourceSha256")
            ),
            "sourcePackageContentSha256": (
                row["source_package_content_sha256"]
                if "source_package_content_sha256" in row.keys()
                else source_package.get("contentSha256")
            ),
            "sourceOfficeName": row["source_office_name"]
                if "source_office_name" in row.keys()
                else source_package.get("officeName"),
            "sourceServiceArea": row["source_service_area"]
                if "source_service_area" in row.keys()
                else source_package.get("serviceArea"),
            "prompt": prompt,
            "result": json.loads(row["result_json"])
                if row["result_json"] else None,
        }

    def get_discovery(self, discovery_id: int) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM discoveries WHERE id = ?", (discovery_id,)
            ).fetchone()
        return self._discovery_dict(row) if row else None

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

    def apply_contact_lookup_results(
        self, run_id: int, results: list[Any]
    ) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        prepared: list[dict[str, Any]] = []
        seen: set[int] = set()
        allowed = {"verified-contact", "unavailable", "unreachable", "unresolved"}
        for raw in results:
            if not isinstance(raw, dict):
                raise ValueError("Every contact lookup result must be a JSON object")
            try:
                discovery_id = int(raw.get("candidateId"))
            except (TypeError, ValueError) as error:
                raise ValueError("Every contact lookup result needs a candidateId") from error
            if discovery_id in seen:
                raise ValueError(f"Candidate {discovery_id} appears more than once")
            seen.add(discovery_id)
            status = str(raw.get("status") or "").strip()
            if status not in allowed:
                raise ValueError(f"Candidate {discovery_id} has an unsupported lookup status")
            website = str(raw.get("website") or "").strip()
            phone = str(raw.get("phone") or "").strip()
            address = str(raw.get("address") or "").strip()
            source_url = str(raw.get("sourceUrl") or "").strip()
            note = str(raw.get("note") or "").strip()
            suggested_next_steps_raw = raw.get("suggestedNextSteps") or []
            if not isinstance(suggested_next_steps_raw, list):
                raise ValueError(
                    f"Candidate {discovery_id} suggestedNextSteps must be a list"
                )
            suggested_next_steps = [
                str(value or "").strip()
                for value in suggested_next_steps_raw
                if str(value or "").strip()
            ]
            checked_at = str(raw.get("checkedAt") or now).strip()
            try:
                datetime.fromisoformat(checked_at.replace("Z", "+00:00"))
            except ValueError as error:
                raise ValueError(
                    f"Candidate {discovery_id} checkedAt must be an ISO-8601 timestamp"
                ) from error
            if status == "verified-contact" and not website:
                raise ValueError(
                    f"Candidate {discovery_id} needs a website for verified-contact"
                )
            if status in {"verified-contact", "unavailable", "unreachable"}:
                if not source_url.startswith(("https://", "http://")):
                    raise ValueError(
                        f"Candidate {discovery_id} needs a cited source URL"
                    )
            if status in {"unavailable", "unreachable", "unresolved"} and not note:
                raise ValueError(
                    f"Candidate {discovery_id} needs a note explaining the lookup result"
                )
            if status == "unresolved" and not suggested_next_steps:
                raise ValueError(
                    f"Candidate {discovery_id} needs suggestedNextSteps for Curator Notes"
                )
            if website and not website.startswith(("https://", "http://")):
                raise ValueError(f"Candidate {discovery_id} website must be an HTTP URL")
            prepared.append(
                {
                    "discoveryId": discovery_id,
                    "status": status,
                    "website": website,
                    "phone": phone,
                    "address": address,
                    "sourceUrl": source_url,
                    "note": note,
                    "suggestedNextSteps": suggested_next_steps,
                    "checkedAt": checked_at,
                }
            )

        counts = {key: 0 for key in allowed}
        with self.connect() as connection:
            run = connection.execute(
                "SELECT status FROM research_runs WHERE id = ?", (run_id,)
            ).fetchone()
            if not run:
                raise ValueError("Research run not found")
            if run["status"] not in {"completed", "partial"}:
                raise ValueError("Contact lookup results require a finished research run")
            for item in prepared:
                row = connection.execute(
                    "SELECT * FROM discoveries WHERE id = ? AND run_id = ?",
                    (item["discoveryId"], run_id),
                ).fetchone()
                if not row:
                    raise ValueError(
                        f"Candidate {item['discoveryId']} does not belong to research run {run_id}"
                    )
                candidate = json.loads(row["candidate_json"])
                existing_website = str(candidate.get("website") or candidate.get("url") or "").strip()
                existing_phone = str(candidate.get("phone") or "").strip()
                if item["website"] and existing_website and item["website"] != existing_website:
                    raise ValueError(
                        f"Candidate {item['discoveryId']} already has a different website"
                    )
                if item["phone"] and existing_phone and item["phone"] != existing_phone:
                    raise ValueError(
                        f"Candidate {item['discoveryId']} already has a different phone"
                    )
                if item["status"] == "verified-contact":
                    if item["website"]:
                        candidate["website"] = item["website"]
                    if item["phone"]:
                        candidate["phone"] = item["phone"]
                    if item["address"] and not str(candidate.get("address") or "").strip():
                        candidate["address"] = item["address"]
                candidate["contactLookup"] = {
                    "status": item["status"],
                    "checkedAt": item["checkedAt"],
                    "sourceUrl": item["sourceUrl"],
                    "note": item["note"],
                    "suggestedNextSteps": item["suggestedNextSteps"],
                }
                restored_status = (
                    "already-known" if row["matched_resource_id"] else "candidate"
                )
                discovery_status = (
                    item["status"]
                    if item["status"] in {"unavailable", "unreachable"}
                    else restored_status
                )
                connection.execute(
                    """UPDATE discoveries
                       SET updated_at = ?, status = ?, candidate_json = ?
                       WHERE id = ?""",
                    (now, discovery_status, _json(candidate), item["discoveryId"]),
                )
                connection.execute(
                    """INSERT INTO discovery_contact_lookups (
                           discovery_id, run_id, status, checked_at, website,
                           phone, address, source_url, note, updated_at
                       ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                       ON CONFLICT(discovery_id) DO UPDATE SET
                           status = excluded.status,
                           checked_at = excluded.checked_at,
                           website = excluded.website,
                           phone = excluded.phone,
                           address = excluded.address,
                           source_url = excluded.source_url,
                           note = excluded.note,
                           updated_at = excluded.updated_at""",
                    (
                        item["discoveryId"], run_id, item["status"], item["checkedAt"],
                        item["website"], item["phone"], item["address"],
                        item["sourceUrl"], item["note"], now,
                    ),
                )
                counts[item["status"]] += 1
        return {
            "runId": run_id,
            "resultCount": len(prepared),
            "verifiedContactCount": counts["verified-contact"],
            "unavailableCount": counts["unavailable"],
            "unreachableCount": counts["unreachable"],
            "unresolvedCount": counts["unresolved"],
        }

    def create_scout_curation_job(
        self,
        job: dict[str, Any],
        categories: list[dict[str, Any]],
    ) -> int:
        if not categories:
            raise ValueError("Resource Scout curation needs at least one researched category")
        now = datetime.now(timezone.utc).isoformat()
        with self.connect() as connection:
            existing = connection.execute(
                """SELECT id FROM scout_curation_jobs
                   WHERE import_id = ? AND candidate_package_sha256 = ?
                     AND assignment_version = ?""",
                (
                    int(job["importId"]),
                    str(job["candidatePackageSha256"]),
                    str(job["assignmentVersion"]),
                ),
            ).fetchone()
            if existing:
                return int(existing["id"])
            cursor = connection.execute(
                """INSERT INTO scout_curation_jobs (
                       import_id, created_at, updated_at, status,
                       assignment_version, candidate_package_sha256,
                       location_name, office_name, service_area,
                       source_package_sha256, source_package_content_sha256,
                       source_package_version
                   ) VALUES (?, ?, ?, 'pending', ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    int(job["importId"]), now, now,
                    str(job["assignmentVersion"]),
                    str(job["candidatePackageSha256"]),
                    str(job["locationName"]),
                    str(job.get("officeName") or ""),
                    str(job.get("serviceArea") or ""),
                    str(job["sourcePackageSha256"]),
                    str(job["sourcePackageContentSha256"]),
                    str(job.get("sourcePackageVersion") or ""),
                ),
            )
            job_id = int(cursor.lastrowid)
            for category in categories:
                connection.execute(
                    """INSERT INTO scout_curation_categories (
                           job_id, category_id, category_label, status,
                           canonical_run_id, candidate_count, assignment_json,
                           assignment_sha256, created_at, updated_at
                       ) VALUES (?, ?, ?, 'pending', ?, ?, ?, ?, ?, ?)""",
                    (
                        job_id,
                        str(category["categoryId"]),
                        str(category["categoryLabel"]),
                        category.get("canonicalRunId"),
                        int(category.get("candidateCount") or 0),
                        _json(category["assignment"]),
                        str(category["assignmentSha256"]),
                        now,
                        now,
                    ),
                )
            connection.execute(
                """INSERT INTO scout_curation_progress_events (
                       job_id, category_id, created_at, phase, message, details_json
                   ) VALUES (?, NULL, ?, 'curation-start', ?, ?)""",
                (
                    job_id,
                    now,
                    f"Resource Scout curation prepared {len(categories)} categories for Codex.",
                    _json({"categoryCount": len(categories)}),
                ),
            )
        return job_id

    def record_scout_workflow_progress(
        self,
        import_id: int,
        phase: str,
        message: str,
        *,
        category_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        with self.connect() as connection:
            if not connection.execute(
                "SELECT 1 FROM imports WHERE id = ?", (int(import_id),)
            ).fetchone():
                raise ValueError("Resource package snapshot not found")
            cursor = connection.execute(
                """INSERT INTO scout_workflow_progress_events (
                       import_id, category_id, created_at, phase, message,
                       details_json
                   ) VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    int(import_id),
                    str(category_id or "").strip() or None,
                    now,
                    str(phase).strip(),
                    str(message).strip(),
                    _json(details or {}),
                ),
            )
            event_id = int(cursor.lastrowid)
        return self.get_scout_workflow_progress_event(event_id)

    @staticmethod
    def _chatgpt_timestamp(value: str | datetime, field: str) -> datetime:
        if isinstance(value, datetime):
            parsed = value
        else:
            text = str(value or "").strip()
            if not text:
                raise ValueError(f"ChatGPT assignment needs {field}")
            try:
                parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
            except ValueError as error:
                raise ValueError(
                    f"ChatGPT assignment {field} must be an ISO-8601 time"
                ) from error
        if parsed.tzinfo is None:
            raise ValueError(f"ChatGPT assignment {field} must include a time zone")
        return parsed.astimezone(timezone.utc)

    @staticmethod
    def _refresh_chatgpt_assignment_states(
        connection: sqlite3.Connection,
        *,
        import_id: int | None = None,
        now: datetime | None = None,
    ) -> None:
        current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat()
        scope = " AND import_id = ?" if import_id is not None else ""
        parameters: tuple[Any, ...] = (
            (current, current, int(import_id))
            if import_id is not None
            else (current, current)
        )
        connection.execute(
            """UPDATE chatgpt_assignment_schedules
               SET status = 'due', updated_at = ?
               WHERE status = 'scheduled' AND scheduled_at <= ?""" + scope,
            parameters,
        )
        connection.execute(
            """UPDATE chatgpt_assignment_schedules
               SET status = 'due', updated_at = ?, cooldown_until = NULL
               WHERE status = 'cooling-down' AND cooldown_until <= ?""" + scope,
            parameters,
        )

    def create_chatgpt_assignment_schedule(
        self,
        import_id: int,
        category_id: str,
        category_label: str,
        assignment: str,
        delay_minutes: int,
        scheduled_at: str | datetime,
        *,
        reason: str = "",
        now: datetime | None = None,
    ) -> dict[str, Any]:
        category_id = str(category_id or "").strip()
        category_label = str(category_label or "").strip()
        assignment = str(assignment or "").strip()
        delay_minutes = int(delay_minutes)
        if not category_id or not category_label or not assignment:
            raise ValueError(
                "ChatGPT assignment needs a category, category label, and assignment"
            )
        if delay_minutes < 0 or delay_minutes > 24 * 60:
            raise ValueError("ChatGPT assignment delay is outside the supported range")
        scheduled = self._chatgpt_timestamp(scheduled_at, "scheduled time")
        current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        initial_status = "due" if scheduled <= current else "scheduled"
        current_text = current.isoformat()
        with self.connect() as connection:
            if not connection.execute(
                "SELECT 1 FROM imports WHERE id = ?", (int(import_id),)
            ).fetchone():
                raise ValueError("Resource package snapshot not found")
            self._refresh_chatgpt_assignment_states(
                connection, import_id=int(import_id), now=current
            )
            active = connection.execute(
                """SELECT id FROM chatgpt_assignment_schedules
                   WHERE import_id = ?
                     AND status IN ('scheduled', 'due', 'cooling-down')
                   ORDER BY id DESC LIMIT 1""",
                (int(import_id),),
            ).fetchone()
            if active:
                raise ValueError(
                    f"ChatGPT assignment {active['id']} is already active for this package"
                )
            cursor = connection.execute(
                """INSERT INTO chatgpt_assignment_schedules (
                       import_id, category_id, category_label, assignment,
                       delay_minutes, scheduled_at, status, reason,
                       status_note, cooldown_until, sent_at, created_at, updated_at
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, '', NULL, NULL, ?, ?)""",
                (
                    int(import_id),
                    category_id,
                    category_label,
                    assignment,
                    delay_minutes,
                    scheduled.isoformat(),
                    initial_status,
                    str(reason or "").strip(),
                    current_text,
                    current_text,
                ),
            )
            schedule_id = int(cursor.lastrowid)
        schedule = self.get_chatgpt_assignment_schedule(schedule_id, now=current)
        if schedule is None:  # pragma: no cover - guarded by the insert above
            raise RuntimeError("Created ChatGPT assignment schedule could not be read")
        return schedule

    def get_chatgpt_assignment_schedule(
        self,
        schedule_id: int,
        *,
        now: datetime | None = None,
    ) -> dict[str, Any] | None:
        with self.connect() as connection:
            self._refresh_chatgpt_assignment_states(connection, now=now)
            row = connection.execute(
                "SELECT * FROM chatgpt_assignment_schedules WHERE id = ?",
                (int(schedule_id),),
            ).fetchone()
        return self._chatgpt_assignment_dict(row) if row else None

    def latest_chatgpt_assignment_schedule(
        self,
        import_id: int,
        *,
        active_only: bool = False,
        now: datetime | None = None,
    ) -> dict[str, Any] | None:
        with self.connect() as connection:
            self._refresh_chatgpt_assignment_states(
                connection, import_id=int(import_id), now=now
            )
            active_clause = (
                " AND status IN ('scheduled', 'due', 'cooling-down')"
                if active_only
                else ""
            )
            row = connection.execute(
                """SELECT * FROM chatgpt_assignment_schedules
                   WHERE import_id = ?""" + active_clause + " ORDER BY id DESC LIMIT 1",
                (int(import_id),),
            ).fetchone()
        return self._chatgpt_assignment_dict(row) if row else None

    def due_chatgpt_assignment_schedules(
        self,
        import_id: int | None = None,
        *,
        now: datetime | None = None,
    ) -> list[dict[str, Any]]:
        with self.connect() as connection:
            self._refresh_chatgpt_assignment_states(
                connection, import_id=import_id, now=now
            )
            if import_id is None:
                rows = connection.execute(
                    """SELECT * FROM chatgpt_assignment_schedules
                       WHERE status = 'due' ORDER BY scheduled_at, id"""
                ).fetchall()
            else:
                rows = connection.execute(
                    """SELECT * FROM chatgpt_assignment_schedules
                       WHERE import_id = ? AND status = 'due'
                       ORDER BY scheduled_at, id""",
                    (int(import_id),),
                ).fetchall()
        return [self._chatgpt_assignment_dict(row) for row in rows]

    def mark_chatgpt_assignment_sent(
        self,
        schedule_id: int,
        *,
        sent_at: str | datetime | None = None,
    ) -> dict[str, Any]:
        sent = self._chatgpt_timestamp(
            sent_at or datetime.now(timezone.utc), "sent time"
        )
        updated = datetime.now(timezone.utc).isoformat()
        with self.connect() as connection:
            self._refresh_chatgpt_assignment_states(connection, now=sent)
            row = connection.execute(
                "SELECT status FROM chatgpt_assignment_schedules WHERE id = ?",
                (int(schedule_id),),
            ).fetchone()
            if not row:
                raise ValueError("ChatGPT assignment schedule not found")
            if row["status"] == "sent":
                raise ValueError("ChatGPT assignment was already marked sent")
            if row["status"] != "due":
                raise ValueError("ChatGPT assignment is not due yet")
            connection.execute(
                """UPDATE chatgpt_assignment_schedules
                   SET status = 'sent', sent_at = ?, cooldown_until = NULL,
                       status_note = '', updated_at = ? WHERE id = ?""",
                (sent.isoformat(), updated, int(schedule_id)),
            )
        schedule = self.get_chatgpt_assignment_schedule(schedule_id, now=sent)
        if schedule is None:  # pragma: no cover
            raise RuntimeError("Sent ChatGPT assignment schedule could not be read")
        return schedule

    def cool_down_chatgpt_assignment(
        self,
        schedule_id: int,
        cooldown_until: str | datetime,
        *,
        note: str = "",
        now: datetime | None = None,
    ) -> dict[str, Any]:
        current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        retry = self._chatgpt_timestamp(cooldown_until, "cooldown time")
        if retry <= current:
            raise ValueError("ChatGPT cooldown time must be in the future")
        with self.connect() as connection:
            self._refresh_chatgpt_assignment_states(connection, now=current)
            row = connection.execute(
                "SELECT status FROM chatgpt_assignment_schedules WHERE id = ?",
                (int(schedule_id),),
            ).fetchone()
            if not row:
                raise ValueError("ChatGPT assignment schedule not found")
            if row["status"] != "due":
                raise ValueError("Only a due ChatGPT assignment can enter cooldown")
            connection.execute(
                """UPDATE chatgpt_assignment_schedules
                   SET status = 'cooling-down', cooldown_until = ?,
                       status_note = ?, updated_at = ? WHERE id = ?""",
                (
                    retry.isoformat(),
                    str(note or "").strip(),
                    current.isoformat(),
                    int(schedule_id),
                ),
            )
        schedule = self.get_chatgpt_assignment_schedule(schedule_id, now=current)
        if schedule is None:  # pragma: no cover
            raise RuntimeError("Cooling ChatGPT assignment schedule could not be read")
        return schedule

    @staticmethod
    def _chatgpt_assignment_dict(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": int(row["id"]),
            "importId": int(row["import_id"]),
            "categoryId": row["category_id"],
            "categoryLabel": row["category_label"],
            "assignment": row["assignment"],
            "delayMinutes": int(row["delay_minutes"]),
            "scheduledAt": row["scheduled_at"],
            "status": row["status"],
            "reason": row["reason"],
            "statusNote": row["status_note"],
            "cooldownUntil": row["cooldown_until"],
            "sentAt": row["sent_at"],
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"],
        }

    def get_scout_workflow_progress_event(
        self, event_id: int
    ) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM scout_workflow_progress_events WHERE id = ?",
                (int(event_id),),
            ).fetchone()
        return self._scout_workflow_progress_dict(row) if row else None

    def list_scout_workflow_progress(
        self, import_id: int, *, limit: int = 50
    ) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """SELECT * FROM scout_workflow_progress_events
                   WHERE import_id = ? ORDER BY id DESC LIMIT ?""",
                (int(import_id), max(1, min(int(limit), 500))),
            ).fetchall()
        return [self._scout_workflow_progress_dict(row) for row in rows]

    @staticmethod
    def _scout_workflow_progress_dict(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "importId": row["import_id"],
            "categoryId": row["category_id"],
            "createdAt": row["created_at"],
            "phase": row["phase"],
            "message": row["message"],
            "details": json.loads(row["details_json"] or "{}"),
        }

    def get_scout_curation_job(self, job_id: int) -> dict[str, Any] | None:
        with self.connect() as connection:
            job = connection.execute(
                "SELECT * FROM scout_curation_jobs WHERE id = ?", (job_id,)
            ).fetchone()
            if not job:
                return None
            categories = connection.execute(
                """SELECT * FROM scout_curation_categories
                   WHERE job_id = ? ORDER BY rowid""",
                (job_id,),
            ).fetchall()
        category_values = [self._scout_curation_category_dict(row) for row in categories]
        completed = sum(item["status"] == "completed" for item in category_values)
        failed = sum(item["status"] == "failed" for item in category_values)
        return {
            "id": job["id"],
            "importId": job["import_id"],
            "createdAt": job["created_at"],
            "updatedAt": job["updated_at"],
            "status": job["status"],
            "assignmentVersion": job["assignment_version"],
            "candidatePackageSha256": job["candidate_package_sha256"],
            "locationName": job["location_name"],
            "officeName": job["office_name"],
            "serviceArea": job["service_area"],
            "sourcePackageSha256": job["source_package_sha256"],
            "sourcePackageContentSha256": job["source_package_content_sha256"],
            "sourcePackageVersion": job["source_package_version"],
            "progress": {
                "completed": completed,
                "failed": failed,
                "total": len(category_values),
            },
            "categories": category_values,
        }

    def list_scout_curation_jobs(self, import_id: int | None = None) -> list[dict[str, Any]]:
        with self.connect() as connection:
            if import_id is None:
                rows = connection.execute(
                    "SELECT id FROM scout_curation_jobs ORDER BY id DESC"
                ).fetchall()
            else:
                rows = connection.execute(
                    """SELECT id FROM scout_curation_jobs
                       WHERE import_id = ? ORDER BY id DESC""",
                    (int(import_id),),
                ).fetchall()
        return [
            job for row in rows
            if (job := self.get_scout_curation_job(int(row["id"]))) is not None
        ]

    def mark_scout_curation_category_assigned(
        self, job_id: int, category_id: str
    ) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        with self.connect() as connection:
            row = connection.execute(
                """SELECT status FROM scout_curation_categories
                   WHERE job_id = ? AND category_id = ?""",
                (job_id, category_id),
            ).fetchone()
            if not row:
                raise ValueError("Resource Scout curation category not found")
            if row["status"] == "completed":
                raise ValueError("Resource Scout curation category is already completed")
            connection.execute(
                """UPDATE scout_curation_categories
                   SET status = 'assigned', assigned_at = COALESCE(assigned_at, ?),
                       updated_at = ?, error = ''
                   WHERE job_id = ? AND category_id = ?""",
                (now, now, job_id, category_id),
            )
            connection.execute(
                """UPDATE scout_curation_jobs
                   SET status = 'in-progress', updated_at = ? WHERE id = ?""",
                (now, job_id),
            )
            connection.execute(
                """INSERT INTO scout_curation_progress_events (
                       job_id, category_id, created_at, phase, message, details_json
                   ) VALUES (?, ?, ?, 'category-assigned', ?, '{}')""",
                (job_id, category_id, now, f"{category_id} was assigned to Codex."),
            )
        job = self.get_scout_curation_job(job_id)
        return next(item for item in job["categories"] if item["categoryId"] == category_id)

    def update_scout_curation_category_assignment(
        self,
        job_id: int,
        category_id: str,
        assignment: dict[str, Any],
        assignment_sha256: str,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self.connect() as connection:
            row = connection.execute(
                """SELECT status FROM scout_curation_categories
                   WHERE job_id = ? AND category_id = ?""",
                (job_id, category_id),
            ).fetchone()
            if not row:
                raise ValueError("Resource Scout curation category not found")
            if row["status"] == "completed":
                raise ValueError("Completed Resource Scout curation assignments are immutable")
            connection.execute(
                """UPDATE scout_curation_categories
                   SET assignment_json = ?, assignment_sha256 = ?, updated_at = ?
                   WHERE job_id = ? AND category_id = ?""",
                (_json(assignment), assignment_sha256, now, job_id, category_id),
            )

    def save_scout_curation_category_result(
        self,
        job_id: int,
        category_id: str,
        result: dict[str, Any],
        result_sha256: str,
        resource_count: int,
    ) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        with self.connect() as connection:
            row = connection.execute(
                """SELECT category_label FROM scout_curation_categories
                   WHERE job_id = ? AND category_id = ?""",
                (job_id, category_id),
            ).fetchone()
            if not row:
                raise ValueError("Resource Scout curation category not found")
            connection.execute(
                """UPDATE scout_curation_categories
                   SET status = 'completed', result_json = ?, result_sha256 = ?,
                       resource_count = ?, completed_at = ?, updated_at = ?, error = ''
                   WHERE job_id = ? AND category_id = ?""",
                (
                    _json(result), result_sha256, int(resource_count), now, now,
                    job_id, category_id,
                ),
            )
            remaining = int(connection.execute(
                """SELECT COUNT(*) FROM scout_curation_categories
                   WHERE job_id = ? AND status != 'completed'""",
                (job_id,),
            ).fetchone()[0])
            connection.execute(
                """UPDATE scout_curation_jobs SET status = ?, updated_at = ?
                   WHERE id = ?""",
                ("completed" if remaining == 0 else "in-progress", now, job_id),
            )
            connection.execute(
                """INSERT INTO scout_curation_progress_events (
                       job_id, category_id, created_at, phase, message, details_json
                   ) VALUES (?, ?, ?, 'category-completed', ?, ?)""",
                (
                    job_id, category_id, now,
                    f"{row['category_label']} curation completed with {resource_count} resources.",
                    _json({"resourceCount": int(resource_count)}),
                ),
            )
        job = self.get_scout_curation_job(job_id)
        if job and job["status"] == "completed":
            self.record_scout_curation_progress(
                job_id,
                "curation-completed",
                f"Resource Scout curation completed all {job['progress']['total']} categories.",
                details=job["progress"],
            )
            job = self.get_scout_curation_job(job_id)
        return job

    def record_scout_curation_progress(
        self,
        job_id: int,
        phase: str,
        message: str,
        *,
        category_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        with self.connect() as connection:
            if not connection.execute(
                "SELECT 1 FROM scout_curation_jobs WHERE id = ?", (job_id,)
            ).fetchone():
                raise ValueError("Resource Scout curation job not found")
            cursor = connection.execute(
                """INSERT INTO scout_curation_progress_events (
                       job_id, category_id, created_at, phase, message, details_json
                   ) VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    job_id, category_id, now, str(phase), str(message),
                    _json(details or {}),
                ),
            )
        return {
            "id": int(cursor.lastrowid),
            "jobId": job_id,
            "categoryId": category_id,
            "createdAt": now,
            "phase": str(phase),
            "message": str(message),
            "details": details or {},
        }

    def list_scout_curation_progress(self, job_id: int) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """SELECT * FROM scout_curation_progress_events
                   WHERE job_id = ? ORDER BY id""",
                (job_id,),
            ).fetchall()
        return [
            {
                "id": row["id"],
                "jobId": row["job_id"],
                "categoryId": row["category_id"],
                "createdAt": row["created_at"],
                "phase": row["phase"],
                "message": row["message"],
                "details": json.loads(row["details_json"]),
            }
            for row in rows
        ]

    @staticmethod
    def _scout_curation_category_dict(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "jobId": row["job_id"],
            "categoryId": row["category_id"],
            "categoryLabel": row["category_label"],
            "status": row["status"],
            "canonicalRunId": row["canonical_run_id"],
            "candidateCount": row["candidate_count"],
            "assignment": json.loads(row["assignment_json"]),
            "assignmentSha256": row["assignment_sha256"],
            "result": json.loads(row["result_json"]) if row["result_json"] else None,
            "resultSha256": row["result_sha256"],
            "resourceCount": row["resource_count"],
            "createdAt": row["created_at"],
            "assignedAt": row["assigned_at"],
            "completedAt": row["completed_at"],
            "updatedAt": row["updated_at"],
            "error": row["error"],
        }

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
            "notes": row["notes"],
            "matchAssessment": "",
        }
