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
    package_identity,
    resource_attachments,
    resource_category_ids,
    resource_id,
    resource_name,
)
from .optimization import configuration_snapshot


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
    stage_id INTEGER,
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
CREATE TABLE IF NOT EXISTS research_run_stages (
    id INTEGER PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES research_runs(id) ON DELETE CASCADE,
    stage_key TEXT NOT NULL,
    title TEXT NOT NULL,
    instruction TEXT NOT NULL,
    position INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued',
    created_at TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT,
    output_text TEXT NOT NULL DEFAULT '',
    result_json TEXT,
    usage_json TEXT,
    error TEXT NOT NULL DEFAULT '',
    UNIQUE (run_id, stage_key),
    UNIQUE (run_id, position)
);
CREATE TABLE IF NOT EXISTS research_stage_attempts (
    id INTEGER PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES research_runs(id) ON DELETE CASCADE,
    stage_id INTEGER NOT NULL REFERENCES research_run_stages(id) ON DELETE CASCADE,
    attempt_number INTEGER NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    status TEXT NOT NULL,
    prompt_chars INTEGER NOT NULL DEFAULT 0,
    output_chars INTEGER NOT NULL DEFAULT 0,
    output_text TEXT NOT NULL DEFAULT '',
    result_json TEXT,
    usage_json TEXT,
    error TEXT NOT NULL DEFAULT '',
    UNIQUE (stage_id, attempt_number)
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
    research_mode TEXT NOT NULL DEFAULT 'package',
    target_location TEXT,
    target_category_id TEXT NOT NULL DEFAULT 'housing',
    target_category_label TEXT NOT NULL DEFAULT 'Housing',
    stage_id INTEGER,
    run_id INTEGER REFERENCES research_runs(id),
    discovery_id INTEGER REFERENCES discoveries(id)
);
CREATE TABLE IF NOT EXISTS generated_resources (
    discovery_id INTEGER PRIMARY KEY REFERENCES discoveries(id) ON DELETE CASCADE,
    run_id INTEGER NOT NULL REFERENCES research_runs(id) ON DELETE CASCADE,
    source_import_id INTEGER NOT NULL REFERENCES imports(id),
    resource_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    resource_json TEXT NOT NULL,
    UNIQUE (run_id, resource_id)
);
CREATE TABLE IF NOT EXISTS optimization_configurations (
    id INTEGER PRIMARY KEY,
    created_at TEXT NOT NULL,
    configuration_hash TEXT NOT NULL UNIQUE CHECK (length(configuration_hash) = 64),
    label TEXT NOT NULL,
    model_artifact TEXT NOT NULL,
    quantization TEXT NOT NULL CHECK (quantization IN ('4-bit', '8-bit', 'none')),
    model_provider TEXT NOT NULL,
    model_endpoint TEXT NOT NULL,
    mlx_version TEXT NOT NULL,
    dsh_version TEXT NOT NULL,
    search_provider TEXT NOT NULL,
    fetch_provider TEXT NOT NULL,
    search_plugin_version TEXT NOT NULL,
    fetch_plugin_version TEXT NOT NULL,
    prompt_policy_version TEXT NOT NULL,
    playbook_version TEXT NOT NULL,
    source_package_sha256 TEXT NOT NULL CHECK (length(source_package_sha256) = 64),
    source_package_version TEXT NOT NULL,
    target_location TEXT NOT NULL,
    regional_scope TEXT NOT NULL,
    target_category_id TEXT NOT NULL,
    stage_key TEXT NOT NULL,
    limits_json TEXT NOT NULL,
    stopping_rules_json TEXT NOT NULL,
    query_plan_json TEXT NOT NULL,
    snapshot_json TEXT NOT NULL
);
CREATE TRIGGER IF NOT EXISTS optimization_configurations_immutable
BEFORE UPDATE ON optimization_configurations
BEGIN
    SELECT RAISE(ABORT, 'optimization configuration snapshots are immutable');
END;
CREATE TABLE IF NOT EXISTS optimization_runs (
    id INTEGER PRIMARY KEY,
    created_at TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT,
    label TEXT NOT NULL UNIQUE,
    configuration_id INTEGER NOT NULL REFERENCES optimization_configurations(id),
    corpus_id INTEGER REFERENCES optimization_corpora(id),
    run_kind TEXT NOT NULL CHECK (
        run_kind IN ('discovery', 'model-evaluation', 'end-to-end')
    ),
    status TEXT NOT NULL CHECK (
        status IN ('queued', 'running', 'partial', 'completed', 'failed', 'cancelled')
    ),
    current_phase TEXT NOT NULL,
    error TEXT NOT NULL DEFAULT '',
    CHECK (run_kind != 'model-evaluation' OR corpus_id IS NOT NULL),
    UNIQUE (id, corpus_id)
);
CREATE TABLE IF NOT EXISTS optimization_checkpoints (
    id INTEGER PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES optimization_runs(id) ON DELETE CASCADE,
    phase TEXT NOT NULL,
    item_type TEXT NOT NULL,
    item_key TEXT NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN ('queued', 'running', 'completed', 'failed', 'not-applicable')
    ),
    attempt_count INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
    state_json TEXT NOT NULL DEFAULT '{}',
    state_sha256 TEXT NOT NULL CHECK (length(state_sha256) = 64),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE (run_id, phase, item_type, item_key)
);
CREATE TABLE IF NOT EXISTS optimization_coverage_branches (
    id INTEGER PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES optimization_runs(id) ON DELETE CASCADE,
    branch_key TEXT NOT NULL,
    purpose TEXT NOT NULL,
    required INTEGER NOT NULL CHECK (required IN (0, 1)),
    status TEXT NOT NULL CHECK (
        status IN ('queued', 'running', 'saturated', 'maximum-reached', 'not-applicable', 'failed')
    ),
    not_applicable_reason TEXT NOT NULL DEFAULT '',
    minimum_queries INTEGER NOT NULL CHECK (minimum_queries > 0),
    maximum_queries INTEGER NOT NULL CHECK (maximum_queries >= minimum_queries),
    saturation_queries INTEGER NOT NULL CHECK (saturation_queries > 0),
    consecutive_no_new_leads INTEGER NOT NULL DEFAULT 0 CHECK (consecutive_no_new_leads >= 0),
    consecutive_no_new_eligible_identities INTEGER NOT NULL DEFAULT 0
        CHECK (consecutive_no_new_eligible_identities >= 0),
    executed_query_count INTEGER NOT NULL DEFAULT 0 CHECK (executed_query_count >= 0),
    new_lead_count INTEGER NOT NULL DEFAULT 0 CHECK (new_lead_count >= 0),
    new_eligible_identity_count INTEGER NOT NULL DEFAULT 0
        CHECK (new_eligible_identity_count >= 0),
    new_routed_identity_count INTEGER NOT NULL DEFAULT 0
        CHECK (new_routed_identity_count >= 0),
    UNIQUE (run_id, branch_key)
);
CREATE TABLE IF NOT EXISTS optimization_queries (
    id INTEGER PRIMARY KEY,
    branch_id INTEGER NOT NULL REFERENCES optimization_coverage_branches(id) ON DELETE CASCADE,
    query_key TEXT NOT NULL,
    position INTEGER NOT NULL CHECK (position > 0),
    purpose TEXT NOT NULL,
    query_text TEXT NOT NULL,
    prior_lead_key TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL CHECK (
        status IN ('planned', 'running', 'completed', 'failed', 'cancelled')
    ),
    executed_at TEXT,
    new_lead_count INTEGER NOT NULL DEFAULT 0 CHECK (new_lead_count >= 0),
    new_eligible_identity_count INTEGER NOT NULL DEFAULT 0
        CHECK (new_eligible_identity_count >= 0),
    new_routed_identity_count INTEGER NOT NULL DEFAULT 0
        CHECK (new_routed_identity_count >= 0),
    result_json TEXT,
    error TEXT NOT NULL DEFAULT '',
    UNIQUE (branch_id, query_key),
    UNIQUE (branch_id, position)
);
CREATE TABLE IF NOT EXISTS optimization_prior_lead_manifests (
    id INTEGER PRIMARY KEY,
    run_id INTEGER NOT NULL UNIQUE REFERENCES optimization_runs(id) ON DELETE CASCADE,
    manifest_id TEXT NOT NULL,
    policy_version TEXT NOT NULL,
    imported_at TEXT NOT NULL,
    manifest_json TEXT NOT NULL,
    manifest_sha256 TEXT NOT NULL CHECK (length(manifest_sha256) = 64)
);
CREATE TABLE IF NOT EXISTS optimization_prior_leads (
    id INTEGER PRIMARY KEY,
    manifest_id INTEGER NOT NULL REFERENCES optimization_prior_lead_manifests(id) ON DELETE CASCADE,
    lead_key TEXT NOT NULL,
    organization TEXT NOT NULL DEFAULT '',
    program TEXT NOT NULL DEFAULT '',
    aliases_json TEXT NOT NULL,
    urls_json TEXT NOT NULL,
    historical_disposition TEXT NOT NULL,
    provenance_json TEXT NOT NULL,
    UNIQUE (manifest_id, lead_key)
);
CREATE TABLE IF NOT EXISTS optimization_query_attempts (
    id INTEGER PRIMARY KEY,
    query_id INTEGER NOT NULL REFERENCES optimization_queries(id) ON DELETE CASCADE,
    attempt_number INTEGER NOT NULL CHECK (attempt_number > 0),
    started_at TEXT NOT NULL,
    completed_at TEXT,
    status TEXT NOT NULL CHECK (status IN ('running', 'completed', 'failed', 'cancelled')),
    result_json TEXT,
    error TEXT NOT NULL DEFAULT '',
    UNIQUE (query_id, attempt_number)
);
CREATE TABLE IF NOT EXISTS optimization_discovery_leads (
    id INTEGER PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES optimization_runs(id) ON DELETE CASCADE,
    canonical_url TEXT NOT NULL,
    title TEXT NOT NULL,
    snippet TEXT NOT NULL,
    discovered_at TEXT NOT NULL,
    origin_type TEXT NOT NULL DEFAULT 'search-result' CHECK (
        origin_type IN ('search-result', 'referral-edge')
    ),
    origin_key TEXT NOT NULL DEFAULT '',
    redirect_url TEXT,
    fetch_status TEXT NOT NULL DEFAULT 'pending' CHECK (
        fetch_status IN ('pending', 'fetched', 'failed', 'rejected', 'not-selected')
    ),
    failure_reason TEXT NOT NULL DEFAULT '',
    UNIQUE (run_id, canonical_url)
);
CREATE TABLE IF NOT EXISTS optimization_referral_graphs (
    id INTEGER PRIMARY KEY,
    run_id INTEGER NOT NULL UNIQUE REFERENCES optimization_runs(id) ON DELETE CASCADE,
    graph_id TEXT NOT NULL,
    policy_version TEXT NOT NULL,
    imported_at TEXT NOT NULL,
    graph_json TEXT NOT NULL,
    graph_sha256 TEXT NOT NULL CHECK (length(graph_sha256) = 64)
);
CREATE TABLE IF NOT EXISTS optimization_referral_edges (
    id INTEGER PRIMARY KEY,
    graph_id INTEGER NOT NULL REFERENCES optimization_referral_graphs(id) ON DELETE CASCADE,
    edge_key TEXT NOT NULL,
    source_url TEXT NOT NULL,
    source_title TEXT NOT NULL,
    source_authority TEXT NOT NULL,
    destination_url TEXT NOT NULL,
    organization TEXT NOT NULL,
    program TEXT NOT NULL,
    target_stage_key TEXT NOT NULL,
    relationship TEXT NOT NULL,
    context TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'planned' CHECK (
        status IN ('planned', 'expanded', 'unresolved')
    ),
    lead_id INTEGER REFERENCES optimization_discovery_leads(id),
    expanded_at TEXT,
    UNIQUE (graph_id, edge_key)
);
CREATE TABLE IF NOT EXISTS optimization_fetch_attempts (
    id INTEGER PRIMARY KEY,
    lead_id INTEGER NOT NULL REFERENCES optimization_discovery_leads(id) ON DELETE CASCADE,
    attempt_number INTEGER NOT NULL CHECK (attempt_number > 0),
    started_at TEXT NOT NULL,
    completed_at TEXT,
    status TEXT NOT NULL CHECK (status IN ('running', 'completed', 'failed', 'rejected', 'cancelled')),
    final_url TEXT,
    status_code INTEGER,
    content_type TEXT,
    truncated INTEGER CHECK (truncated IN (0, 1)),
    extract_sha256 TEXT CHECK (extract_sha256 IS NULL OR length(extract_sha256) = 64),
    error TEXT NOT NULL DEFAULT '',
    UNIQUE (lead_id, attempt_number)
);
CREATE TABLE IF NOT EXISTS optimization_lead_queries (
    lead_id INTEGER NOT NULL REFERENCES optimization_discovery_leads(id) ON DELETE CASCADE,
    query_id INTEGER NOT NULL REFERENCES optimization_queries(id) ON DELETE CASCADE,
    result_rank INTEGER NOT NULL CHECK (result_rank > 0),
    result_url TEXT NOT NULL,
    PRIMARY KEY (lead_id, query_id)
);
CREATE TABLE IF NOT EXISTS optimization_candidate_identities (
    id INTEGER PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES optimization_runs(id) ON DELETE CASCADE,
    organization TEXT NOT NULL,
    program TEXT NOT NULL,
    identity_key TEXT NOT NULL,
    boundary_state TEXT NOT NULL CHECK (
        boundary_state IN ('resolved', 'uncertain-boundary', 'possible-renaming', 'possible-duplicate', 'excluded-existing')
    ),
    package_match_state TEXT NOT NULL CHECK (
        package_match_state IN ('not-matched', 'same-program', 'different-program', 'ambiguous')
    ),
    package_resource_id TEXT,
    target_stage_key TEXT NOT NULL DEFAULT '',
    candidate_role TEXT NOT NULL DEFAULT 'unresolved-lead' CHECK (
        candidate_role IN (
            'direct-program', 'access-assessment-service', 'service-location',
            'referral-system', 'directory', 'organization-only', 'unresolved-lead'
        )
    ),
    geography_state TEXT NOT NULL DEFAULT 'unknown' CHECK (
        geography_state IN (
            'confirmed-target', 'confirmed-serves-target', 'unknown', 'outside-target'
        )
    ),
    category_state TEXT NOT NULL DEFAULT 'unknown' CHECK (
        category_state IN ('confirmed', 'adjacent-support', 'unknown', 'wrong-category')
    ),
    actionability_state TEXT NOT NULL DEFAULT 'uncertain' CHECK (
        actionability_state IN ('actionable', 'uncertain', 'informational-only')
    ),
    current_status_state TEXT NOT NULL DEFAULT 'uncertain' CHECK (
        current_status_state IN ('current', 'uncertain', 'inactive', 'successor')
    ),
    evidence_readiness TEXT NOT NULL DEFAULT 'lead-only' CHECK (
        evidence_readiness IN (
            'current-authoritative', 'current-corroborated', 'lead-only', 'stale'
        )
    ),
    promotion_state TEXT NOT NULL DEFAULT 'review-required' CHECK (
        promotion_state IN (
            'eligible', 'noncandidate', 'review-required', 'excluded-existing'
        )
    ),
    promotion_reasons_json TEXT NOT NULL DEFAULT '[]',
    decision_reason TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    UNIQUE (run_id, identity_key)
);
CREATE TABLE IF NOT EXISTS optimization_identity_leads (
    identity_id INTEGER NOT NULL REFERENCES optimization_candidate_identities(id) ON DELETE CASCADE,
    lead_id INTEGER NOT NULL REFERENCES optimization_discovery_leads(id) ON DELETE CASCADE,
    relationship TEXT NOT NULL CHECK (
        relationship IN ('describes-program', 'describes-organization', 'possible-match', 'excluded')
    ),
    metadata_json TEXT NOT NULL DEFAULT '{}',
    PRIMARY KEY (identity_id, lead_id)
);
CREATE TABLE IF NOT EXISTS optimization_evidence_sources (
    id INTEGER PRIMARY KEY,
    identity_id INTEGER NOT NULL REFERENCES optimization_candidate_identities(id) ON DELETE CASCADE,
    canonical_url TEXT NOT NULL,
    authority TEXT NOT NULL CHECK (
        authority IN ('direct-provider', 'government-referral', 'reputable-secondary', 'directory-lead')
    ),
    page_identity_key TEXT NOT NULL,
    fetched_at TEXT NOT NULL,
    final_url TEXT NOT NULL,
    status_code INTEGER NOT NULL,
    content_type TEXT NOT NULL,
    truncated INTEGER NOT NULL CHECK (truncated IN (0, 1)),
    extract_json TEXT NOT NULL,
    extract_sha256 TEXT NOT NULL CHECK (length(extract_sha256) = 64),
    UNIQUE (identity_id, canonical_url)
);
CREATE TABLE IF NOT EXISTS optimization_corpora (
    id INTEGER PRIMARY KEY,
    discovery_run_id INTEGER NOT NULL REFERENCES optimization_runs(id),
    created_at TEXT NOT NULL,
    frozen_at TEXT,
    status TEXT NOT NULL CHECK (status IN ('building', 'frozen')),
    ledger_sha256 TEXT NOT NULL CHECK (length(ledger_sha256) = 64),
    identities_sha256 TEXT NOT NULL CHECK (length(identities_sha256) = 64),
    sources_sha256 TEXT NOT NULL CHECK (length(sources_sha256) = 64),
    packets_sha256 TEXT NOT NULL CHECK (length(packets_sha256) = 64),
    corpus_sha256 TEXT NOT NULL UNIQUE CHECK (length(corpus_sha256) = 64)
);
CREATE TRIGGER IF NOT EXISTS optimization_frozen_corpora_no_update
BEFORE UPDATE ON optimization_corpora
WHEN OLD.status = 'frozen'
BEGIN
    SELECT RAISE(ABORT, 'frozen optimization corpora are immutable');
END;
CREATE TRIGGER IF NOT EXISTS optimization_frozen_corpora_no_delete
BEFORE DELETE ON optimization_corpora
WHEN OLD.status = 'frozen'
BEGIN
    SELECT RAISE(ABORT, 'frozen optimization corpora are immutable');
END;
CREATE TABLE IF NOT EXISTS optimization_evidence_packets (
    id INTEGER PRIMARY KEY,
    corpus_id INTEGER NOT NULL REFERENCES optimization_corpora(id) ON DELETE CASCADE,
    identity_key TEXT NOT NULL,
    packet_json TEXT NOT NULL,
    packet_sha256 TEXT NOT NULL CHECK (length(packet_sha256) = 64),
    UNIQUE (corpus_id, identity_key),
    UNIQUE (corpus_id, packet_sha256),
    UNIQUE (id, corpus_id)
);
CREATE TRIGGER IF NOT EXISTS optimization_frozen_packets_no_insert
BEFORE INSERT ON optimization_evidence_packets
WHEN (SELECT status FROM optimization_corpora WHERE id = NEW.corpus_id) = 'frozen'
BEGIN
    SELECT RAISE(ABORT, 'frozen optimization evidence packets are immutable');
END;
CREATE TRIGGER IF NOT EXISTS optimization_frozen_packets_no_update
BEFORE UPDATE ON optimization_evidence_packets
WHEN (SELECT status FROM optimization_corpora WHERE id = OLD.corpus_id) = 'frozen'
BEGIN
    SELECT RAISE(ABORT, 'frozen optimization evidence packets are immutable');
END;
CREATE TRIGGER IF NOT EXISTS optimization_frozen_packets_no_delete
BEFORE DELETE ON optimization_evidence_packets
WHEN (SELECT status FROM optimization_corpora WHERE id = OLD.corpus_id) = 'frozen'
BEGIN
    SELECT RAISE(ABORT, 'frozen optimization evidence packets are immutable');
END;
CREATE TABLE IF NOT EXISTS optimization_model_attempts (
    id INTEGER PRIMARY KEY,
    run_id INTEGER NOT NULL,
    packet_id INTEGER NOT NULL,
    corpus_id INTEGER NOT NULL REFERENCES optimization_corpora(id),
    operation TEXT NOT NULL CHECK (operation IN ('extract', 'verify')),
    attempt_number INTEGER NOT NULL CHECK (attempt_number > 0),
    started_at TEXT NOT NULL,
    completed_at TEXT,
    status TEXT NOT NULL CHECK (status IN ('running', 'completed', 'failed', 'cancelled')),
    prompt_sha256 TEXT NOT NULL CHECK (length(prompt_sha256) = 64),
    raw_output TEXT NOT NULL DEFAULT '',
    parsed_json TEXT,
    usage_json TEXT,
    error TEXT NOT NULL DEFAULT '',
    UNIQUE (run_id, packet_id, operation, attempt_number),
    FOREIGN KEY (run_id, corpus_id)
        REFERENCES optimization_runs(id, corpus_id) ON DELETE CASCADE,
    FOREIGN KEY (packet_id, corpus_id)
        REFERENCES optimization_evidence_packets(id, corpus_id)
);
CREATE TABLE IF NOT EXISTS optimization_candidate_dossiers (
    id INTEGER PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES optimization_runs(id) ON DELETE CASCADE,
    packet_id INTEGER NOT NULL REFERENCES optimization_evidence_packets(id),
    extraction_attempt_id INTEGER NOT NULL REFERENCES optimization_model_attempts(id),
    dossier_json TEXT NOT NULL,
    dossier_sha256 TEXT NOT NULL CHECK (length(dossier_sha256) = 64),
    UNIQUE (run_id, packet_id)
);
CREATE TABLE IF NOT EXISTS optimization_verifications (
    id INTEGER PRIMARY KEY,
    dossier_id INTEGER NOT NULL REFERENCES optimization_candidate_dossiers(id) ON DELETE CASCADE,
    verification_attempt_id INTEGER NOT NULL REFERENCES optimization_model_attempts(id),
    status TEXT NOT NULL CHECK (status IN ('passed', 'failed', 'needs-review')),
    verified_dossier_json TEXT NOT NULL,
    verified_dossier_sha256 TEXT NOT NULL CHECK (length(verified_dossier_sha256) = 64),
    findings_json TEXT NOT NULL,
    UNIQUE (dossier_id)
);
CREATE TABLE IF NOT EXISTS optimization_gap_queries (
    id INTEGER PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES optimization_runs(id) ON DELETE CASCADE,
    corpus_id INTEGER NOT NULL REFERENCES optimization_corpora(id),
    need_key TEXT NOT NULL,
    need_label TEXT NOT NULL,
    reason TEXT NOT NULL,
    query_text TEXT NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN ('planned', 'running', 'completed', 'failed', 'not-needed')
    ),
    result_json TEXT,
    error TEXT NOT NULL DEFAULT '',
    UNIQUE (run_id, need_key)
);
CREATE TABLE IF NOT EXISTS optimization_comparisons (
    id INTEGER PRIMARY KEY,
    created_at TEXT NOT NULL,
    label TEXT NOT NULL UNIQUE,
    corpus_id INTEGER NOT NULL REFERENCES optimization_corpora(id),
    four_bit_run_id INTEGER NOT NULL,
    eight_bit_run_id INTEGER NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN ('planned', 'blinded-review', 'priorities-scored', 'revealed', 'decided')
    ),
    priorities_one_through_four_json TEXT NOT NULL DEFAULT '{}',
    timing_json TEXT NOT NULL DEFAULT '{}',
    decision_json TEXT NOT NULL DEFAULT '{}',
    CHECK (four_bit_run_id != eight_bit_run_id),
    FOREIGN KEY (four_bit_run_id, corpus_id)
        REFERENCES optimization_runs(id, corpus_id),
    FOREIGN KEY (eight_bit_run_id, corpus_id)
        REFERENCES optimization_runs(id, corpus_id)
);
CREATE TRIGGER IF NOT EXISTS optimization_comparison_configuration_guard
BEFORE INSERT ON optimization_comparisons
BEGIN
    SELECT CASE
        WHEN (SELECT status FROM optimization_corpora WHERE id = NEW.corpus_id) != 'frozen'
        THEN RAISE(ABORT, 'optimization comparisons require a frozen corpus')
    END;
    SELECT CASE
        WHEN (
            SELECT configuration.quantization
            FROM optimization_runs AS run
            JOIN optimization_configurations AS configuration
              ON configuration.id = run.configuration_id
            WHERE run.id = NEW.four_bit_run_id
        ) != '4-bit'
        THEN RAISE(ABORT, 'four-bit comparison run must use a 4-bit configuration')
    END;
    SELECT CASE
        WHEN (
            SELECT configuration.quantization
            FROM optimization_runs AS run
            JOIN optimization_configurations AS configuration
              ON configuration.id = run.configuration_id
            WHERE run.id = NEW.eight_bit_run_id
        ) != '8-bit'
        THEN RAISE(ABORT, 'eight-bit comparison run must use an 8-bit configuration')
    END;
END;
CREATE TABLE IF NOT EXISTS optimization_audits (
    id INTEGER PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES optimization_runs(id) ON DELETE CASCADE,
    audit_type TEXT NOT NULL CHECK (
        audit_type IN ('coverage', 'candidate-completeness', 'quality-gate', 'comparison')
    ),
    created_at TEXT NOT NULL,
    report_json TEXT NOT NULL,
    report_sha256 TEXT NOT NULL CHECK (length(report_sha256) = 64),
    UNIQUE (run_id, audit_type)
);
CREATE TABLE IF NOT EXISTS optimization_package_outcomes (
    id INTEGER PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES optimization_runs(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL,
    final_package_sha256 TEXT NOT NULL CHECK (length(final_package_sha256) = 64),
    curator_work_sha256 TEXT NOT NULL DEFAULT '' CHECK (
        curator_work_sha256 = '' OR length(curator_work_sha256) = 64
    ),
    report_json TEXT NOT NULL,
    report_sha256 TEXT NOT NULL CHECK (length(report_sha256) = 64),
    UNIQUE (run_id, final_package_sha256, curator_work_sha256)
);
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
            if recover_interrupted:
                self._recover_interrupted_runs(connection)
                self._recover_interrupted_optimization(connection)

    @staticmethod
    def _migrate(connection: sqlite3.Connection) -> None:
        outcome_columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(optimization_package_outcomes)"
            )
        }
        if "curator_work_sha256" not in outcome_columns:
            connection.execute(
                "DROP TABLE IF EXISTS optimization_package_outcomes_migration"
            )
            connection.execute(
                """CREATE TABLE optimization_package_outcomes_migration (
                       id INTEGER PRIMARY KEY,
                       run_id INTEGER NOT NULL
                           REFERENCES optimization_runs(id) ON DELETE CASCADE,
                       created_at TEXT NOT NULL,
                       final_package_sha256 TEXT NOT NULL
                           CHECK (length(final_package_sha256) = 64),
                       curator_work_sha256 TEXT NOT NULL DEFAULT '' CHECK (
                           curator_work_sha256 = ''
                           OR length(curator_work_sha256) = 64
                       ),
                       report_json TEXT NOT NULL,
                       report_sha256 TEXT NOT NULL
                           CHECK (length(report_sha256) = 64),
                       UNIQUE (
                           run_id, final_package_sha256, curator_work_sha256
                       )
                   )"""
            )
            connection.execute(
                """INSERT INTO optimization_package_outcomes_migration (
                       id, run_id, created_at, final_package_sha256,
                       curator_work_sha256, report_json, report_sha256
                   )
                   SELECT id, run_id, created_at, final_package_sha256,
                          '', report_json, report_sha256
                   FROM optimization_package_outcomes"""
            )
            connection.execute("DROP TABLE optimization_package_outcomes")
            connection.execute(
                "ALTER TABLE optimization_package_outcomes_migration "
                "RENAME TO optimization_package_outcomes"
            )
        columns = {row["name"] for row in connection.execute("PRAGMA table_info(discoveries)")}
        additions = {
            "run_id": "INTEGER",
            "reviewed_at": "TEXT",
            "review_feedback": "TEXT NOT NULL DEFAULT ''",
            "match_assessment": "TEXT",
            "match_assessed_at": "TEXT",
            "stage_id": "INTEGER",
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
        run_additions = {
            "research_mode": "TEXT NOT NULL DEFAULT 'package'",
            "target_location": "TEXT",
            "regional_scope": "TEXT NOT NULL DEFAULT ''",
            "target_category_id": "TEXT NOT NULL DEFAULT 'housing'",
            "target_category_label": "TEXT NOT NULL DEFAULT 'Housing'",
        }
        for name, definition in run_additions.items():
            if name not in run_columns:
                connection.execute(f"ALTER TABLE research_runs ADD COLUMN {name} {definition}")
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
        lesson_columns = {row["name"] for row in connection.execute("PRAGMA table_info(research_lessons)")}
        lesson_additions = {
            "research_mode": "TEXT NOT NULL DEFAULT 'package'",
            "target_location": "TEXT",
            "stage_id": "INTEGER",
            "target_category_id": "TEXT NOT NULL DEFAULT 'housing'",
            "target_category_label": "TEXT NOT NULL DEFAULT 'Housing'",
        }
        for name, definition in lesson_additions.items():
            if name not in lesson_columns:
                connection.execute(f"ALTER TABLE research_lessons ADD COLUMN {name} {definition}")
        import_columns = {row["name"] for row in connection.execute("PRAGMA table_info(imports)")}
        if "for_groups_json" not in import_columns:
            connection.execute("ALTER TABLE imports ADD COLUMN for_groups_json TEXT NOT NULL DEFAULT '[]'")
        import_additions = {
            "office_name": "TEXT NOT NULL DEFAULT ''",
            "service_area": "TEXT NOT NULL DEFAULT ''",
            "identity_source": "TEXT NOT NULL DEFAULT ''",
        }
        for name, definition in import_additions.items():
            if name not in import_columns:
                connection.execute(f"ALTER TABLE imports ADD COLUMN {name} {definition}")
        optimization_identity_columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(optimization_candidate_identities)"
            )
        }
        if "metadata_json" not in optimization_identity_columns:
            connection.execute(
                "ALTER TABLE optimization_candidate_identities "
                "ADD COLUMN metadata_json TEXT NOT NULL DEFAULT '{}'"
            )
        if "target_stage_key" not in optimization_identity_columns:
            connection.execute(
                "ALTER TABLE optimization_candidate_identities "
                "ADD COLUMN target_stage_key TEXT NOT NULL DEFAULT ''"
            )
        identity_qualification_additions = {
            "candidate_role": "TEXT NOT NULL DEFAULT 'unresolved-lead'",
            "geography_state": "TEXT NOT NULL DEFAULT 'unknown'",
            "category_state": "TEXT NOT NULL DEFAULT 'unknown'",
            "actionability_state": "TEXT NOT NULL DEFAULT 'uncertain'",
            "current_status_state": "TEXT NOT NULL DEFAULT 'uncertain'",
            "evidence_readiness": "TEXT NOT NULL DEFAULT 'lead-only'",
            "promotion_state": "TEXT NOT NULL DEFAULT 'review-required'",
            "promotion_reasons_json": "TEXT NOT NULL DEFAULT '[]'",
        }
        for name, definition in identity_qualification_additions.items():
            if name not in optimization_identity_columns:
                connection.execute(
                    f"ALTER TABLE optimization_candidate_identities ADD COLUMN {name} {definition}"
                )
        optimization_identity_lead_columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(optimization_identity_leads)"
            )
        }
        if "metadata_json" not in optimization_identity_lead_columns:
            connection.execute(
                "ALTER TABLE optimization_identity_leads "
                "ADD COLUMN metadata_json TEXT NOT NULL DEFAULT '{}'"
            )
        optimization_discovery_lead_columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(optimization_discovery_leads)"
            )
        }
        for name, definition in {
            "origin_type": "TEXT NOT NULL DEFAULT 'search-result'",
            "origin_key": "TEXT NOT NULL DEFAULT ''",
        }.items():
            if name not in optimization_discovery_lead_columns:
                connection.execute(
                    f"ALTER TABLE optimization_discovery_leads ADD COLUMN {name} {definition}"
                )
        connection.execute(
            """UPDATE optimization_candidate_identities
               SET target_stage_key = (
                   SELECT configuration.stage_key
                   FROM optimization_runs AS run
                   JOIN optimization_configurations AS configuration
                     ON configuration.id = run.configuration_id
                   WHERE run.id = optimization_candidate_identities.run_id
               )
               WHERE target_stage_key = ''"""
        )
        for table, additions in {
            "optimization_queries": {
                "new_eligible_identity_count": "INTEGER NOT NULL DEFAULT 0",
                "new_routed_identity_count": "INTEGER NOT NULL DEFAULT 0",
                "prior_lead_key": "TEXT NOT NULL DEFAULT ''",
            },
            "optimization_coverage_branches": {
                "new_eligible_identity_count": "INTEGER NOT NULL DEFAULT 0",
                "new_routed_identity_count": "INTEGER NOT NULL DEFAULT 0",
                "consecutive_no_new_eligible_identities": "INTEGER NOT NULL DEFAULT 0",
            },
        }.items():
            existing_columns = {
                row["name"]
                for row in connection.execute(f"PRAGMA table_info({table})")
            }
            for name, definition in additions.items():
                if name not in existing_columns:
                    connection.execute(
                        f"ALTER TABLE {table} ADD COLUMN {name} {definition}"
                    )
            connection.execute(
                f"UPDATE {table} SET new_eligible_identity_count = new_lead_count "
                "WHERE new_eligible_identity_count = 0 AND new_lead_count > 0"
            )
        rows = connection.execute(
            "SELECT id, source_name, metadata_json FROM imports WHERE office_name = '' OR service_area = ''"
        ).fetchall()
        for row in rows:
            metadata = json.loads(row["metadata_json"] or "{}")
            office_name, service_area, source = package_identity(row["source_name"], metadata)
            connection.execute(
                "UPDATE imports SET office_name = ?, service_area = ?, identity_source = ? WHERE id = ?",
                (office_name, service_area, source, row["id"]),
            )

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

    @staticmethod
    def _recover_interrupted_runs(connection: sqlite3.Connection) -> None:
        now = datetime.now(timezone.utc).isoformat()
        message = "The app stopped before this research stage finished. Resume the run to retry it."
        connection.execute(
            """UPDATE research_stage_attempts
               SET status = 'failed', completed_at = ?, error = ?
               WHERE status = 'running'""",
            (now, message),
        )
        connection.execute(
            """UPDATE research_run_stages
               SET status = 'failed', completed_at = ?, error = ?
               WHERE status = 'running'""",
            (now, message),
        )
        connection.execute(
            """UPDATE research_runs
               SET status = CASE
                       WHEN EXISTS (
                           SELECT 1 FROM research_run_stages AS stage
                           WHERE stage.run_id = research_runs.id AND stage.status = 'completed'
                       ) THEN 'partial'
                       ELSE 'failed'
                   END,
                   completed_at = ?, error = ?
               WHERE status IN ('queued', 'running')""",
            (now, message),
        )

    @staticmethod
    def _recover_interrupted_optimization(connection: sqlite3.Connection) -> None:
        now = datetime.now(timezone.utc).isoformat()
        message = (
            "The app stopped before this optimization item finished. "
            "Resume the labeled run to retry only this item."
        )
        connection.execute(
            """UPDATE optimization_query_attempts
               SET status = 'failed', completed_at = ?, error = ?
               WHERE status = 'running'""",
            (now, message),
        )
        connection.execute(
            """UPDATE optimization_fetch_attempts
               SET status = 'failed', completed_at = ?, error = ?
               WHERE status = 'running'""",
            (now, message),
        )
        connection.execute(
            """UPDATE optimization_model_attempts
               SET status = 'failed', completed_at = ?, error = ?
               WHERE status = 'running'""",
            (now, message),
        )
        connection.execute(
            """UPDATE optimization_queries
               SET status = 'failed', error = ? WHERE status = 'running'""",
            (message,),
        )
        connection.execute(
            """UPDATE optimization_coverage_branches
               SET status = 'failed' WHERE status = 'running'"""
        )
        connection.execute(
            """UPDATE optimization_checkpoints
               SET status = 'failed', updated_at = ? WHERE status = 'running'""",
            (now,),
        )
        connection.execute(
            """UPDATE optimization_runs
               SET status = 'partial', current_phase = 'resume-required', error = ?
               WHERE status = 'running'""",
            (message,),
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
                    multicategory_target_count, metadata_json, manifest_json, for_groups_json,
                    office_name, service_area, identity_source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
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
                    for attachment in resource_attachments(resource):
                        content = package.seed_assets.get(attachment["path"])
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

    def import_target_category(self, import_id: int) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT target_category_id FROM imports WHERE id = ?", (import_id,)
            ).fetchone()
        return self.import_category(import_id, str(row["target_category_id"])) if row else None

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
            category_ids = json.loads(row["category_ids_json"])
            if selected_category_id not in category_ids:
                continue
            full_record = json.loads(row["raw_json"])
            stored_assets = {asset["path"]: asset for asset in assets_by_resource.get(row["resource_id"], [])}
            attachments = []
            for attachment in resource_attachments(full_record):
                attachments.append(stored_assets.get(attachment["path"], {
                    "path": attachment["path"], "name": attachment["name"],
                    "mediaType": "application/pdf", "bytes": None, "available": False,
                }))
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
                "attachments": attachments,
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
            "dshCommand", "dshConfiguration", "dshModel", "command", "profile", "provider", "model",
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

    def save_optimization_configuration(self, value: dict[str, Any]) -> int:
        record = configuration_snapshot(value)
        snapshot = record["snapshot"]
        with self.connect() as connection:
            existing = connection.execute(
                "SELECT id, snapshot_json FROM optimization_configurations WHERE configuration_hash = ?",
                (record["configurationHash"],),
            ).fetchone()
            if existing:
                if json.loads(existing["snapshot_json"]) != snapshot:
                    raise ValueError("Optimization configuration hash collision")
                return int(existing["id"])
            cursor = connection.execute(
                """INSERT INTO optimization_configurations (
                       created_at, configuration_hash, label, model_artifact, quantization,
                       model_provider, model_endpoint, mlx_version, dsh_version,
                       search_provider, fetch_provider, search_plugin_version,
                       fetch_plugin_version, prompt_policy_version, playbook_version,
                       source_package_sha256, source_package_version, target_location,
                       regional_scope, target_category_id, stage_key, limits_json,
                       stopping_rules_json, query_plan_json, snapshot_json
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    datetime.now(timezone.utc).isoformat(),
                    record["configurationHash"],
                    record["label"],
                    snapshot["modelArtifact"],
                    snapshot["quantization"],
                    snapshot["modelProvider"],
                    snapshot["modelEndpoint"],
                    snapshot["mlxVersion"],
                    snapshot["dshVersion"],
                    snapshot["searchProvider"],
                    snapshot["fetchProvider"],
                    snapshot["searchPluginVersion"],
                    snapshot["fetchPluginVersion"],
                    snapshot["promptPolicyVersion"],
                    snapshot["playbookVersion"],
                    snapshot["sourcePackageSha256"],
                    snapshot["sourcePackageVersion"],
                    snapshot["targetLocation"],
                    snapshot["regionalScope"],
                    snapshot["targetCategoryId"],
                    snapshot["stageKey"],
                    _json(snapshot["limits"]),
                    _json(snapshot["stoppingRules"]),
                    _json(snapshot["queryPlan"]),
                    _json(snapshot),
                ),
            )
        return int(cursor.lastrowid)

    def optimization_configuration(self, configuration_id: int) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM optimization_configurations WHERE id = ?",
                (configuration_id,),
            ).fetchone()
        if not row:
            return None
        return {
            "id": int(row["id"]),
            "createdAt": row["created_at"],
            "configurationHash": row["configuration_hash"],
            "label": row["label"],
            "snapshot": json.loads(row["snapshot_json"]),
        }

    def create_research_run(
        self,
        adapter: str,
        assignment: str,
        prompt: dict[str, Any],
        source_import_id: int | None = None,
        seed_resource_id: str | None = None,
        *,
        research_mode: str = "package",
        target_location: str | None = None,
        regional_scope: str = "",
        target_category_id: str = "housing",
        target_category_label: str = "Housing",
        stages: list[dict[str, str]] | None = None,
    ) -> int:
        now = datetime.now(timezone.utc).isoformat()
        with self.connect() as connection:
            cursor = connection.execute(
                """INSERT INTO research_runs (
                       created_at, status, adapter, assignment, research_mode,
                       target_location, regional_scope, target_category_id,
                       target_category_label, source_import_id,
                       seed_import_id, seed_resource_id, prompt_json
                   ) VALUES (?, 'queued', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    now, adapter, assignment, research_mode, target_location,
                    regional_scope, target_category_id, target_category_label, source_import_id,
                    source_import_id if seed_resource_id else None, seed_resource_id, _json(prompt),
                ),
            )
            run_id = int(cursor.lastrowid)
            for position, stage in enumerate(stages or [], start=1):
                connection.execute(
                    """INSERT INTO research_run_stages (
                           run_id, stage_key, title, instruction, position, created_at
                       ) VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        run_id,
                        str(stage["key"]),
                        str(stage["title"]),
                        str(stage["instruction"]),
                        position,
                        now,
                    ),
                )
        return run_id

    def mark_run_running(self, run_id: int) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self.connect() as connection:
            connection.execute(
                """UPDATE research_runs
                   SET status = 'running', started_at = COALESCE(started_at, ?),
                       completed_at = NULL, error = '' WHERE id = ?""",
                (now, run_id),
            )

    def list_run_stages(self, run_id: int) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM research_run_stages WHERE run_id = ? ORDER BY position",
                (run_id,),
            ).fetchall()
        return [self._stage_dict(row) for row in rows]

    def _list_run_stage_summaries(self, run_id: int) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """SELECT id, run_id, stage_key, title, position, status,
                          created_at, started_at, completed_at, error
                   FROM research_run_stages WHERE run_id = ? ORDER BY position""",
                (run_id,),
            ).fetchall()
        return [
            {
                "id": row["id"], "runId": row["run_id"], "key": row["stage_key"],
                "title": row["title"], "position": row["position"],
                "status": row["status"], "createdAt": row["created_at"],
                "startedAt": row["started_at"], "completedAt": row["completed_at"],
                "error": row["error"],
            }
            for row in rows
        ]

    def add_run_stages(self, run_id: int, stages: list[dict[str, str]]) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self.connect() as connection:
            existing = connection.execute(
                "SELECT COUNT(*) AS count FROM research_run_stages WHERE run_id = ?", (run_id,)
            ).fetchone()
            if existing and existing["count"]:
                raise ValueError("Research stages already exist for this run")
            if not connection.execute("SELECT id FROM research_runs WHERE id = ?", (run_id,)).fetchone():
                raise ValueError("Research run not found")
            for position, stage in enumerate(stages, start=1):
                connection.execute(
                    """INSERT INTO research_run_stages (
                           run_id, stage_key, title, instruction, position, created_at
                       ) VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        run_id, str(stage["key"]), str(stage["title"]),
                        str(stage["instruction"]), position, now,
                    ),
                )

    def mark_stage_running(self, stage_id: int, *, prompt_chars: int = 0) -> int:
        now = datetime.now(timezone.utc).isoformat()
        with self.connect() as connection:
            stage = connection.execute(
                "SELECT run_id FROM research_run_stages WHERE id = ?", (stage_id,)
            ).fetchone()
            if not stage:
                raise ValueError("Research stage not found")
            attempt_number = int(
                connection.execute(
                    "SELECT COALESCE(MAX(attempt_number), 0) + 1 AS value "
                    "FROM research_stage_attempts WHERE stage_id = ?",
                    (stage_id,),
                ).fetchone()["value"]
            )
            connection.execute(
                """UPDATE research_run_stages
                   SET status = 'running', started_at = ?, completed_at = NULL, error = ''
                   WHERE id = ?""",
                (now, stage_id),
            )
            cursor = connection.execute(
                """INSERT INTO research_stage_attempts (
                       run_id, stage_id, attempt_number, started_at, status, prompt_chars
                   ) VALUES (?, ?, ?, ?, 'running', ?)""",
                (stage["run_id"], stage_id, attempt_number, now, max(0, prompt_chars)),
            )
        return int(cursor.lastrowid)

    def complete_stage(
        self,
        stage_id: int,
        output: str,
        result: dict[str, Any],
        usage: dict[str, Any] | None,
        *,
        attempt_id: int | None = None,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self.connect() as connection:
            connection.execute(
                """UPDATE research_run_stages
                   SET status = 'completed', completed_at = ?, output_text = ?,
                       result_json = ?, usage_json = ?, error = ''
                   WHERE id = ?""",
                (now, output, _json(result), _json(usage) if usage else None, stage_id),
            )
            if attempt_id is not None:
                connection.execute(
                    """UPDATE research_stage_attempts
                       SET status = 'completed', completed_at = ?, output_chars = ?,
                           output_text = ?, result_json = ?, usage_json = ?, error = ''
                       WHERE id = ? AND stage_id = ?""",
                    (
                        now, len(output), output, _json(result),
                        _json(usage) if usage else None, attempt_id, stage_id,
                    ),
                )

    def fail_stage(
        self, stage_id: int, error: str, output: str = "", *, attempt_id: int | None = None
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self.connect() as connection:
            connection.execute(
                """UPDATE research_run_stages
                   SET status = 'failed', completed_at = ?, output_text = ?, error = ?
                   WHERE id = ?""",
                (now, output, error, stage_id),
            )
            if attempt_id is not None:
                connection.execute(
                    """UPDATE research_stage_attempts
                       SET status = 'failed', completed_at = ?, output_chars = ?,
                           output_text = ?, error = ? WHERE id = ? AND stage_id = ?""",
                    (now, len(output), output, error, attempt_id, stage_id),
                )

    def list_stage_attempts(self, stage_id: int) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM research_stage_attempts WHERE stage_id = ? ORDER BY attempt_number",
                (stage_id,),
            ).fetchall()
        return [
            {
                "id": row["id"], "runId": row["run_id"], "stageId": row["stage_id"],
                "attemptNumber": row["attempt_number"], "startedAt": row["started_at"],
                "completedAt": row["completed_at"], "status": row["status"],
                "promptChars": row["prompt_chars"], "outputChars": row["output_chars"],
                "output": row["output_text"],
                "result": json.loads(row["result_json"]) if row["result_json"] else None,
                "usage": json.loads(row["usage_json"]) if row["usage_json"] else None,
                "error": row["error"],
            }
            for row in rows
        ]

    def update_run_progress(
        self,
        run_id: int,
        output: str,
        result: dict[str, Any],
        usage: dict[str, Any] | None,
    ) -> None:
        with self.connect() as connection:
            connection.execute(
                """UPDATE research_runs
                   SET output_text = ?, result_json = ?, usage_json = ? WHERE id = ?""",
                (output, _json(result), _json(usage) if usage else None, run_id),
            )

    def partial_run(
        self,
        run_id: int,
        error: str,
        output: str,
        result: dict[str, Any],
        usage: dict[str, Any] | None,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self.connect() as connection:
            connection.execute(
                """UPDATE research_runs
                   SET status = 'partial', completed_at = ?, output_text = ?,
                       result_json = ?, usage_json = ?, error = ? WHERE id = ?""",
                (now, output, _json(result), _json(usage) if usage else None, error, run_id),
            )

    def prepare_run_resume(self, run_id: int) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute("SELECT status FROM research_runs WHERE id = ?", (run_id,)).fetchone()
            if not row:
                return None
            if row["status"] not in {"failed", "partial"}:
                raise ValueError("Only failed or partial research runs can be resumed")
            connection.execute(
                """UPDATE research_run_stages
                   SET status = 'queued', started_at = NULL, completed_at = NULL,
                       output_text = '', result_json = NULL, usage_json = NULL, error = ''
                   WHERE run_id = ? AND status IN ('failed', 'running')""",
                (run_id,),
            )
            connection.execute(
                """UPDATE research_runs
                   SET status = 'queued', completed_at = NULL, error = '' WHERE id = ?""",
                (run_id,),
            )
        return self.get_run(run_id)

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
        if not row:
            return None
        value = self._run_dict(row)
        value["stages"] = self.list_run_stages(run_id)
        value["progress"] = self._stage_progress(value["stages"])
        return value

    def list_runs(self, limit: int = 30) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """SELECT research_runs.id, research_runs.created_at, research_runs.started_at,
                          research_runs.completed_at, research_runs.status, research_runs.adapter,
                          research_runs.assignment, research_runs.research_mode,
                          research_runs.target_location, research_runs.regional_scope,
                          research_runs.target_category_id, research_runs.target_category_label,
                          research_runs.source_import_id, research_runs.seed_import_id,
                          research_runs.seed_resource_id, research_runs.error,
                          imports.office_name AS source_office_name,
                          imports.service_area AS source_service_area,
                          json_extract(result_json, '$.summary') AS result_summary,
                          json_extract(result_json, '$.stageSummaries') AS result_stage_summaries,
                          json_extract(result_json, '$.isPartial') AS result_is_partial,
                          result_json IS NOT NULL AS has_result
                   FROM research_runs
                   LEFT JOIN imports ON imports.id = research_runs.source_import_id
                   ORDER BY research_runs.id DESC LIMIT ?""",
                (max(1, min(limit, 100)),),
            ).fetchall()
        result = []
        for row in rows:
            value = {
                "id": row["id"], "createdAt": row["created_at"],
                "startedAt": row["started_at"], "completedAt": row["completed_at"],
                "status": row["status"], "adapter": row["adapter"],
                "assignment": row["assignment"], "researchMode": row["research_mode"],
                "targetLocation": row["target_location"], "regionalScope": row["regional_scope"],
                "targetCategoryId": row["target_category_id"],
                "targetCategoryLabel": row["target_category_label"],
                "sourceImportId": row["source_import_id"], "seedImportId": row["seed_import_id"],
                "sourceOfficeName": row["source_office_name"],
                "sourceServiceArea": row["source_service_area"],
                "seedResourceId": row["seed_resource_id"], "prompt": {"selectedSeed": None},
                "output": "", "usage": None, "error": row["error"],
                "result": (
                    {
                        "summary": str(row["result_summary"] or ""),
                        "stageSummaries": self._safe_stage_summaries(row["result_stage_summaries"]),
                        "isPartial": bool(row["result_is_partial"]),
                    }
                    if row["has_result"] else None
                ),
            }
            value["stages"] = self._list_run_stage_summaries(int(row["id"]))
            value["progress"] = self._stage_progress(value["stages"])
            result.append(value)
        return result

    @staticmethod
    def _safe_stage_summaries(value: str | None) -> list[dict[str, Any]]:
        try:
            parsed = json.loads(value or "[]")
        except (TypeError, json.JSONDecodeError):
            return []
        if not isinstance(parsed, list):
            return []
        return [item for item in parsed if isinstance(item, dict)]

    @staticmethod
    def _stage_progress(stages: list[dict[str, Any]]) -> dict[str, int]:
        return {
            "total": len(stages),
            "completed": sum(stage["status"] == "completed" for stage in stages),
            "failed": sum(stage["status"] == "failed" for stage in stages),
        }

    @staticmethod
    def _run_dict(row: sqlite3.Row) -> dict[str, Any]:
        value = {
            "id": row["id"], "createdAt": row["created_at"], "startedAt": row["started_at"],
            "completedAt": row["completed_at"], "status": row["status"], "adapter": row["adapter"],
            "assignment": row["assignment"], "researchMode": row["research_mode"],
            "targetLocation": row["target_location"], "regionalScope": row["regional_scope"],
            "targetCategoryId": row["target_category_id"],
            "targetCategoryLabel": row["target_category_label"],
            "sourceImportId": row["source_import_id"],
            "seedImportId": row["seed_import_id"],
            "seedResourceId": row["seed_resource_id"], "prompt": json.loads(row["prompt_json"]),
            "output": row["output_text"],
            "result": json.loads(row["result_json"]) if row["result_json"] else None,
            "usage": json.loads(row["usage_json"]) if row["usage_json"] else None,
            "error": row["error"],
        }
        source_package = value["prompt"].get("researchContext", {}).get("sourcePackage") or {}
        value["sourceOfficeName"] = source_package.get("officeName")
        value["sourceServiceArea"] = source_package.get("serviceArea")
        return value

    @staticmethod
    def _stage_dict(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"], "runId": row["run_id"], "key": row["stage_key"],
            "title": row["title"], "instruction": row["instruction"],
            "position": row["position"], "status": row["status"],
            "createdAt": row["created_at"], "startedAt": row["started_at"],
            "completedAt": row["completed_at"], "output": row["output_text"],
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
        stage_id: int | None = None,
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
                    matched_import_id, matched_resource_id, duplicate_score, notes, run_id, stage_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    now, now, status, origin, name, _json(candidate),
                    match.get("importId") if match else None,
                    match.get("resourceId") if match else None,
                    match.get("score") if match else None,
                    notes, run_id, stage_id,
                ),
            )
            discovery_id = int(cursor.lastrowid)
        return {"id": discovery_id, "status": status, "origin": origin, "isNewDiscovery": not duplicate}

    def get_discovery(self, discovery_id: int) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM discoveries WHERE id = ?", (discovery_id,)
            ).fetchone()
        return self._discovery_dict(row) if row else None

    def get_generated_resource(self, discovery_id: int) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM generated_resources WHERE discovery_id = ?", (discovery_id,)
            ).fetchone()
        return self._generated_resource_dict(row) if row else None

    @staticmethod
    def _generated_resource_dict(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "discoveryId": row["discovery_id"], "runId": row["run_id"],
            "sourceImportId": row["source_import_id"], "resourceId": row["resource_id"],
            "createdAt": row["created_at"], "updatedAt": row["updated_at"],
            "resource": json.loads(row["resource_json"]),
        }

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
            "stageId": row["stage_id"],
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
        research_mode: str = "package",
        target_location: str | None = None,
        target_category_id: str = "housing",
        target_category_label: str = "Housing",
        stage_id: int | None = None,
    ) -> dict[str, Any]:
        text = text.strip()
        if not text:
            raise ValueError("Lesson text is required")
        if scope not in {"category", "general"}:
            raise ValueError("Lesson scope must be category or general")
        if status not in {"active", "proposed", "retired"}:
            raise ValueError("Lesson status must be active, proposed, or retired")
        if research_mode not in {"package", "standalone-location"}:
            raise ValueError(f"Unsupported research mode: {research_mode}")
        target_location = target_location.strip() if target_location else None
        if research_mode == "standalone-location" and not target_location:
            raise ValueError("A target location is required for a standalone-location lesson")
        if research_mode == "package":
            target_location = None
        now = datetime.now(timezone.utc).isoformat()
        with self.connect() as connection:
            cursor = connection.execute(
                """INSERT INTO research_lessons (
                       created_at, updated_at, scope, text, rationale, status,
                       source, research_mode, target_location, run_id, discovery_id, stage_id
                       , target_category_id, target_category_label
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    now, now, scope, text, rationale.strip(), status, source,
                    research_mode, target_location, run_id, discovery_id, stage_id,
                    target_category_id, target_category_label,
                ),
            )
            lesson_id = int(cursor.lastrowid)
        return self.get_lesson(lesson_id) or {}

    def get_lesson(self, lesson_id: int) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute("SELECT * FROM research_lessons WHERE id = ?", (lesson_id,)).fetchone()
        return self._lesson_dict(row) if row else None

    def list_lessons(
        self,
        active_only: bool = False,
        research_mode: str | None = None,
        target_location: str | None = None,
        target_category_id: str | None = None,
    ) -> list[dict[str, Any]]:
        query = "SELECT * FROM research_lessons"
        clauses: list[str] = []
        parameters: list[Any] = []
        if active_only:
            clauses.append("status = ?")
            parameters.append("active")
        if research_mode is not None:
            clauses.append("research_mode = ?")
            parameters.append(research_mode)
        if research_mode == "standalone-location":
            clauses.append("target_location = ? COLLATE NOCASE")
            parameters.append((target_location or "").strip())
        if target_category_id is not None:
            clauses.append("(scope = 'general' OR target_category_id = ? COLLATE NOCASE)")
            parameters.append(target_category_id.strip())
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY id DESC"
        with self.connect() as connection:
            rows = connection.execute(query, tuple(parameters)).fetchall()
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
            "discoveryId": row["discovery_id"], "researchMode": row["research_mode"],
            "targetLocation": row["target_location"], "stageId": row["stage_id"],
            "targetCategoryId": row["target_category_id"],
            "targetCategoryLabel": row["target_category_label"],
        }
