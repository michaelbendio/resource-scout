from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Iterable
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .optimization import (
    HOUSING_STAGE_KEYS,
    branch_stop_state,
    candidate_identity_key,
    canonical_json,
    configuration_snapshot,
    coverage_branch_complete,
    organization_key,
    package_exclusion_state,
    sha256_json,
)
from .storage import ResearchStore


SearchCallback = Callable[[str, int], list[dict[str, Any]]]
FetchCallback = Callable[[str], dict[str, Any]]
IdentityCallback = Callable[
    [dict[str, Any]], dict[str, Any] | list[dict[str, Any]] | None
]
ProgressCallback = Callable[[dict[str, Any]], None]


class OptimizationPipelineError(RuntimeError):
    pass


@dataclass(frozen=True)
class DiscoveryCorpusResult:
    run_id: int
    configuration_id: int
    corpus_id: int
    corpus_sha256: str
    branch_count: int
    query_count: int
    lead_count: int
    identity_count: int
    eligible_identity_count: int
    routed_identity_count: int
    excluded_identity_count: int
    source_count: int
    packet_count: int


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonicalize_discovery_url(value: Any) -> str:
    text = str(value or "").strip()
    try:
        parsed = urlsplit(text)
        port = parsed.port
    except ValueError as error:
        raise ValueError(f"Invalid discovery URL: {text}") from error
    scheme = parsed.scheme.casefold()
    if scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError(f"Unsupported discovery URL: {text}")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("Discovery URLs containing credentials are not allowed")
    hostname = parsed.hostname.casefold()
    rendered_host = f"[{hostname}]" if ":" in hostname else hostname
    if port is not None and not (
        (scheme == "http" and port == 80) or (scheme == "https" and port == 443)
    ):
        rendered_host = f"{rendered_host}:{port}"
    ignored_parameters = {"fbclid", "gclid", "mc_cid", "mc_eid"}
    query = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key.casefold() not in ignored_parameters
        and not key.casefold().startswith("utm_")
    ]
    path = parsed.path or "/"
    if path != "/":
        path = path.rstrip("/") or "/"
    return urlunsplit((scheme, rendered_host, path, urlencode(sorted(query)), ""))


def source_authority(
    url: str,
    *,
    direct_domains: Iterable[str] = (),
    reviewed_authority: str | None = None,
) -> str:
    hostname = (urlsplit(url).hostname or "").casefold()
    normalized_direct = {
        str(domain).strip().casefold().removeprefix("www.")
        for domain in direct_domains
        if str(domain).strip()
    }
    comparable = hostname.removeprefix("www.")
    if any(comparable == domain or comparable.endswith(f".{domain}") for domain in normalized_direct):
        return "direct-provider"
    if comparable.endswith(".gov") or comparable in {
        "211arizona.org",
        "211.org",
        "hud.gov",
    }:
        return "government-referral"
    if reviewed_authority == "reputable-secondary":
        return "reputable-secondary"
    return "directory-lead"


class OptimizationDiscoveryPipeline:
    def __init__(
        self,
        store: ResearchStore,
        configuration: dict[str, Any],
        *,
        search: SearchCallback,
        fetch: FetchCallback,
        resolve_identity: IdentityCallback,
        existing_resources: Iterable[dict[str, Any]] = (),
        progress: ProgressCallback | None = None,
    ) -> None:
        self.store = store
        self.configuration = configuration
        self.configuration_record = configuration_snapshot(configuration)
        self.search = search
        self.fetch = fetch
        self.resolve_identity = resolve_identity
        self.existing_resources = tuple(existing_resources)
        self.progress = progress or (lambda _event: None)

    def run(self) -> DiscoveryCorpusResult:
        configuration_id = self.store.save_optimization_configuration(self.configuration)
        run_id = self._ensure_run(configuration_id)
        existing = self._existing_corpus(run_id)
        if existing is not None:
            return self._result(run_id, configuration_id, existing)
        self._ensure_query_plan(run_id)
        self._mark_run(run_id, status="running", phase="discovery")
        try:
            self._execute_queries(run_id)
            self._mark_run(run_id, status="running", phase="fetch")
            self._fetch_leads(run_id)
            self._mark_run(run_id, status="running", phase="freeze-corpus")
            corpus_id = self._freeze_corpus(run_id)
        except Exception as error:
            self._mark_run(run_id, status="partial", phase="resume-required", error=str(error))
            if isinstance(error, OptimizationPipelineError):
                raise
            raise OptimizationPipelineError(str(error)) from error
        self._mark_run(run_id, status="completed", phase="complete")
        return self._result(run_id, configuration_id, corpus_id)

    def _ensure_run(self, configuration_id: int) -> int:
        label = f"{self.configuration_record['label']}-discovery"
        with self.store.connect() as connection:
            row = connection.execute(
                "SELECT id, configuration_id FROM optimization_runs WHERE label = ?",
                (label,),
            ).fetchone()
            if row:
                if int(row["configuration_id"]) != configuration_id:
                    raise OptimizationPipelineError(
                        "A discovery run label cannot be resumed under a different configuration"
                    )
                return int(row["id"])
            cursor = connection.execute(
                """INSERT INTO optimization_runs (
                       created_at, label, configuration_id, run_kind, status, current_phase
                   ) VALUES (?, ?, ?, 'discovery', 'queued', 'query-plan')""",
                (_now(), label, configuration_id),
            )
        return int(cursor.lastrowid)

    def _ensure_query_plan(self, run_id: int) -> None:
        plan = self.configuration_record["snapshot"]["queryPlan"]
        with self.store.connect() as connection:
            existing = connection.execute(
                "SELECT COUNT(*) AS count FROM optimization_coverage_branches WHERE run_id = ?",
                (run_id,),
            ).fetchone()
            if existing and int(existing["count"]):
                return
            for branch in plan["branches"]:
                saturation = branch["saturation"]
                branch_id = connection.execute(
                    """INSERT INTO optimization_coverage_branches (
                           run_id, branch_key, purpose, required, status,
                           minimum_queries, maximum_queries, saturation_queries
                       ) VALUES (?, ?, ?, ?, 'queued', ?, ?, ?)""",
                    (
                        run_id,
                        branch["key"],
                        branch["purpose"],
                        int(bool(branch["required"])),
                        saturation["minimumQueries"],
                        saturation["maximumQueries"],
                        saturation["consecutiveNoNewIdentityQueries"],
                    ),
                ).lastrowid
                for query in branch["queries"]:
                    connection.execute(
                        """INSERT INTO optimization_queries (
                               branch_id, query_key, position, purpose, query_text, status
                           ) VALUES (?, ?, ?, ?, ?, 'planned')""",
                        (
                            branch_id,
                            query["key"],
                            query["position"],
                            query["purpose"],
                            query["query"],
                        ),
                    )

    def _execute_queries(self, run_id: int) -> None:
        with self.store.connect() as connection:
            branches = connection.execute(
                "SELECT * FROM optimization_coverage_branches WHERE run_id = ? ORDER BY id",
                (run_id,),
            ).fetchall()
        for branch in branches:
            branch_id = int(branch["id"])
            with self.store.connect() as connection:
                queries = connection.execute(
                    "SELECT * FROM optimization_queries WHERE branch_id = ? ORDER BY position",
                    (branch_id,),
                ).fetchall()
            for query in queries:
                with self.store.connect() as connection:
                    completed_counts = [
                        int(row["new_eligible_identity_count"])
                        for row in connection.execute(
                            """SELECT new_eligible_identity_count FROM optimization_queries
                               WHERE branch_id = ? AND status = 'completed'
                               ORDER BY position""",
                            (branch_id,),
                        ).fetchall()
                    ]
                state = branch_stop_state(
                    completed_counts,
                    minimum_queries=int(branch["minimum_queries"]),
                    maximum_queries=int(branch["maximum_queries"]),
                    saturation_queries=int(branch["saturation_queries"]),
                )
                if state != "continue":
                    self._update_branch(branch_id, state)
                    break
                if query["status"] == "completed":
                    continue
                self._execute_query(run_id, branch_id, query)
            with self.store.connect() as connection:
                current = connection.execute(
                    "SELECT * FROM optimization_coverage_branches WHERE id = ?", (branch_id,)
                ).fetchone()
                counts = [
                    int(row["new_eligible_identity_count"])
                    for row in connection.execute(
                        """SELECT new_eligible_identity_count FROM optimization_queries
                           WHERE branch_id = ? AND status = 'completed' ORDER BY position""",
                        (branch_id,),
                    ).fetchall()
                ]
            state = branch_stop_state(
                counts,
                minimum_queries=int(current["minimum_queries"]),
                maximum_queries=int(current["maximum_queries"]),
                saturation_queries=int(current["saturation_queries"]),
            )
            if state != "continue":
                self._update_branch(branch_id, state)
            elif current["status"] != "not-applicable":
                raise OptimizationPipelineError(
                    f"Coverage branch {current['branch_key']} ended before its stopping rule"
                )
        with self.store.connect() as connection:
            final_branches = connection.execute(
                "SELECT * FROM optimization_coverage_branches WHERE run_id = ? ORDER BY id",
                (run_id,),
            ).fetchall()
        incomplete = [
            str(branch["branch_key"])
            for branch in final_branches
            if not coverage_branch_complete(
                {
                    "status": branch["status"],
                    "notApplicableReason": branch["not_applicable_reason"],
                }
            )
        ]
        if incomplete:
            raise OptimizationPipelineError(
                f"Coverage branches are incomplete: {', '.join(incomplete)}"
            )

    def _execute_query(self, run_id: int, branch_id: int, query: sqlite3.Row) -> None:
        query_id = int(query["id"])
        with self.store.connect() as connection:
            attempt_number = int(
                connection.execute(
                    "SELECT COALESCE(MAX(attempt_number), 0) + 1 AS value "
                    "FROM optimization_query_attempts WHERE query_id = ?",
                    (query_id,),
                ).fetchone()["value"]
            )
            attempt_id = connection.execute(
                """INSERT INTO optimization_query_attempts (
                       query_id, attempt_number, started_at, status
                   ) VALUES (?, ?, ?, 'running')""",
                (query_id, attempt_number, _now()),
            ).lastrowid
            connection.execute(
                "UPDATE optimization_queries SET status = 'running', error = '' WHERE id = ?",
                (query_id,),
            )
            connection.execute(
                "UPDATE optimization_coverage_branches SET status = 'running' WHERE id = ?",
                (branch_id,),
            )
        try:
            maximum_results = max(
                1,
                int(
                    self.configuration_record["snapshot"]["limits"].get(
                        "searchResultsPerQuery", 8
                    )
                ),
            )
            raw_results = self.search(str(query["query_text"]), maximum_results)
            if not isinstance(raw_results, list):
                raise ValueError("Search provider did not return an array")
        except Exception as error:
            with self.store.connect() as connection:
                connection.execute(
                    """UPDATE optimization_query_attempts
                       SET completed_at = ?, status = 'failed', error = ? WHERE id = ?""",
                    (_now(), str(error), attempt_id),
                )
                connection.execute(
                    "UPDATE optimization_queries SET status = 'failed', error = ? WHERE id = ?",
                    (str(error), query_id),
                )
                connection.execute(
                    "UPDATE optimization_coverage_branches SET status = 'failed' WHERE id = ?",
                    (branch_id,),
                )
            raise OptimizationPipelineError(
                f"Query {query['query_key']} failed: {error}"
            ) from error

        normalized_results: list[dict[str, Any]] = []
        new_identity_count = 0
        new_eligible_identity_count = 0
        new_routed_identity_count = 0
        with self.store.connect() as connection:
            for rank, result in enumerate(raw_results, start=1):
                if not isinstance(result, dict):
                    continue
                try:
                    canonical_url = canonicalize_discovery_url(result.get("url"))
                except ValueError:
                    continue
                normalized = {
                    "url": canonical_url,
                    "title": str(result.get("title") or "").strip(),
                    "snippet": str(result.get("snippet") or "").strip(),
                    "rank": rank,
                }
                normalized_results.append(normalized)
                lead = connection.execute(
                    "SELECT id FROM optimization_discovery_leads WHERE run_id = ? AND canonical_url = ?",
                    (run_id, canonical_url),
                ).fetchone()
                if lead:
                    lead_id = int(lead["id"])
                else:
                    lead_id = int(
                        connection.execute(
                            """INSERT INTO optimization_discovery_leads (
                                   run_id, canonical_url, title, snippet, discovered_at
                               ) VALUES (?, ?, ?, ?, ?)""",
                            (
                                run_id,
                                canonical_url,
                                normalized["title"],
                                normalized["snippet"],
                                _now(),
                            ),
                        ).lastrowid
                    )
                connection.execute(
                    """INSERT OR IGNORE INTO optimization_lead_queries (
                           lead_id, query_id, result_rank, result_url
                       ) VALUES (?, ?, ?, ?)""",
                    (lead_id, query_id, rank, str(result.get("url") or "")),
                )
                decision_value = self.resolve_identity(result)
                if decision_value is None:
                    continue
                decisions = (
                    [decision_value]
                    if isinstance(decision_value, dict)
                    else decision_value
                    if isinstance(decision_value, list)
                    else []
                )
                if not decisions or any(
                    not isinstance(decision, dict) for decision in decisions
                ):
                    raise OptimizationPipelineError(
                        f"Identity resolver returned invalid decisions for {canonical_url}"
                    )
                for decision in decisions:
                    identity_id, created = self._save_identity(
                        connection, run_id, decision
                    )
                    new_identity_count += int(created)
                    if created:
                        identity = connection.execute(
                            """SELECT boundary_state, target_stage_key
                               FROM optimization_candidate_identities WHERE id = ?""",
                            (identity_id,),
                        ).fetchone()
                        new_eligible_identity_count += int(
                            identity["boundary_state"] != "excluded-existing"
                            and identity["target_stage_key"]
                            == self.configuration_record["snapshot"]["stageKey"]
                        )
                        new_routed_identity_count += int(
                            identity["target_stage_key"]
                            != self.configuration_record["snapshot"]["stageKey"]
                        )
                    relationship = str(
                        decision.get("leadRelationship") or "describes-program"
                    )
                    if relationship not in {
                        "describes-program",
                        "describes-organization",
                        "possible-match",
                        "excluded",
                    }:
                        raise OptimizationPipelineError(
                            f"Invalid lead relationship for {canonical_url}: {relationship}"
                        )
                    lead_metadata = {
                        "directDomains": sorted(
                            {
                                str(domain).strip().casefold()
                                for domain in decision.get("directDomains", [])
                                if str(domain).strip()
                            }
                        ),
                        "reviewedAuthority": decision.get("reviewedAuthority"),
                        "coverageTags": sorted(
                            {
                                str(tag).strip()
                                for tag in decision.get("coverageTags", [])
                                if str(tag).strip()
                            }
                        ),
                        "evidenceExcerpt": str(
                            decision.get("evidenceExcerpt") or ""
                        ).strip(),
                    }
                    connection.execute(
                        """INSERT INTO optimization_identity_leads (
                               identity_id, lead_id, relationship, metadata_json
                           ) VALUES (?, ?, ?, ?)
                           ON CONFLICT(identity_id, lead_id) DO UPDATE SET
                               relationship = excluded.relationship,
                               metadata_json = excluded.metadata_json""",
                        (
                            identity_id,
                            lead_id,
                            relationship,
                            canonical_json(lead_metadata),
                        ),
                    )
            payload = {"sources": normalized_results, "truncated": False}
            now = _now()
            connection.execute(
                """UPDATE optimization_query_attempts
                   SET completed_at = ?, status = 'completed', result_json = ? WHERE id = ?""",
                (now, canonical_json(payload), attempt_id),
            )
            connection.execute(
                """UPDATE optimization_queries
                   SET status = 'completed', executed_at = ?, new_lead_count = ?,
                       new_eligible_identity_count = ?, new_routed_identity_count = ?,
                       result_json = ?, error = ''
                   WHERE id = ?""",
                (
                    now,
                    new_identity_count,
                    new_eligible_identity_count,
                    new_routed_identity_count,
                    canonical_json(payload),
                    query_id,
                ),
            )
            aggregates = connection.execute(
                """SELECT COUNT(*) AS query_count,
                          COALESCE(SUM(new_lead_count), 0) AS lead_count,
                          COALESCE(SUM(new_eligible_identity_count), 0)
                              AS eligible_identity_count,
                          COALESCE(SUM(new_routed_identity_count), 0)
                              AS routed_identity_count
                   FROM optimization_queries
                   WHERE branch_id = ? AND status = 'completed'""",
                (branch_id,),
            ).fetchone()
            completed_counts = [
                int(row["new_eligible_identity_count"])
                for row in connection.execute(
                    """SELECT new_eligible_identity_count FROM optimization_queries
                       WHERE branch_id = ? AND status = 'completed' ORDER BY position""",
                    (branch_id,),
                ).fetchall()
            ]
            raw_completed_counts = [
                int(row["new_lead_count"])
                for row in connection.execute(
                    """SELECT new_lead_count FROM optimization_queries
                       WHERE branch_id = ? AND status = 'completed' ORDER BY position""",
                    (branch_id,),
                ).fetchall()
            ]
            no_new_eligible = 0
            for count in reversed(completed_counts):
                if count:
                    break
                no_new_eligible += 1
            no_new_raw = 0
            for count in reversed(raw_completed_counts):
                if count:
                    break
                no_new_raw += 1
            connection.execute(
                """UPDATE optimization_coverage_branches
                   SET executed_query_count = ?, new_lead_count = ?,
                       new_eligible_identity_count = ?,
                       new_routed_identity_count = ?,
                       consecutive_no_new_leads = ?,
                       consecutive_no_new_eligible_identities = ? WHERE id = ?""",
                (
                    int(aggregates["query_count"]),
                    int(aggregates["lead_count"]),
                    int(aggregates["eligible_identity_count"]),
                    int(aggregates["routed_identity_count"]),
                    no_new_raw,
                    no_new_eligible,
                    branch_id,
                ),
            )
        self.progress(
            {
                "phase": "discovery",
                "queryKey": query["query_key"],
                "newIdentityCount": new_identity_count,
                "newEligibleIdentityCount": new_eligible_identity_count,
                "newRoutedIdentityCount": new_routed_identity_count,
            }
        )

    def _save_identity(
        self, connection: sqlite3.Connection, run_id: int, decision: dict[str, Any]
    ) -> tuple[int, bool]:
        organization = str(decision.get("organization") or "").strip()
        program = str(decision.get("program") or "").strip()
        identity_key = candidate_identity_key(organization, program)
        boundary = str(decision.get("boundaryState") or "resolved")
        if boundary not in {
            "resolved",
            "uncertain-boundary",
            "possible-renaming",
            "possible-duplicate",
        }:
            raise OptimizationPipelineError(f"Invalid identity boundary state: {boundary}")
        target_stage_key = str(
            decision.get("stageKey")
            or self.configuration_record["snapshot"]["stageKey"]
        ).strip()
        if target_stage_key not in HOUSING_STAGE_KEYS:
            raise OptimizationPipelineError(
                f"Invalid Housing stage route: {target_stage_key or '(blank)'}"
            )
        package_state = "not-matched"
        package_resource_id = None
        for existing in self.existing_resources:
            state = package_exclusion_state(
                organization,
                program,
                str(existing.get("organization") or ""),
                str(existing.get("program") or ""),
            )
            if state == "same-program":
                package_state = state
                package_resource_id = str(existing.get("resourceId") or "") or None
                boundary = "excluded-existing"
                break
            if state == "different-program":
                package_state = state
        existing_row = connection.execute(
            "SELECT id FROM optimization_candidate_identities WHERE run_id = ? AND identity_key = ?",
            (run_id, identity_key),
        ).fetchone()
        if existing_row:
            return int(existing_row["id"]), False
        metadata = {
            "directDomains": sorted(
                {
                    str(domain).strip().casefold()
                    for domain in decision.get("directDomains", [])
                    if str(domain).strip()
                }
            ),
            "reviewedAuthority": decision.get("reviewedAuthority"),
            "coverageTags": sorted(
                {
                    str(tag).strip()
                    for tag in decision.get("coverageTags", [])
                    if str(tag).strip()
                }
            ),
            "stageKey": target_stage_key,
            "evidenceExcerpt": str(decision.get("evidenceExcerpt") or "").strip(),
        }
        cursor = connection.execute(
            """INSERT INTO optimization_candidate_identities (
                   run_id, organization, program, identity_key, boundary_state,
                   package_match_state, package_resource_id, target_stage_key,
                   decision_reason, metadata_json
               ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                run_id,
                organization,
                program,
                identity_key,
                boundary,
                package_state,
                package_resource_id,
                target_stage_key,
                str(decision.get("decisionReason") or "Explicit fixture or human-reviewed identity decision"),
                canonical_json(metadata),
            ),
        )
        return int(cursor.lastrowid), True

    def _update_branch(self, branch_id: int, status: str) -> None:
        with self.store.connect() as connection:
            connection.execute(
                "UPDATE optimization_coverage_branches SET status = ? WHERE id = ?",
                (status, branch_id),
            )

    def _fetch_leads(self, run_id: int) -> None:
        with self.store.connect() as connection:
            leads = connection.execute(
                """SELECT DISTINCT lead.*
                   FROM optimization_discovery_leads AS lead
                   JOIN optimization_identity_leads AS link ON link.lead_id = lead.id
                   JOIN optimization_candidate_identities AS identity ON identity.id = link.identity_id
                   WHERE lead.run_id = ?
                     AND identity.boundary_state != 'excluded-existing'
                     AND identity.boundary_state = 'resolved'
                     AND identity.target_stage_key = ?
                   ORDER BY lead.id""",
                (run_id, self.configuration_record["snapshot"]["stageKey"]),
            ).fetchall()
        for lead in leads:
            if lead["fetch_status"] == "fetched":
                continue
            self._fetch_lead(run_id, lead)

    def _fetch_lead(self, run_id: int, lead: sqlite3.Row) -> None:
        lead_id = int(lead["id"])
        with self.store.connect() as connection:
            attempt_number = int(
                connection.execute(
                    "SELECT COALESCE(MAX(attempt_number), 0) + 1 AS value "
                    "FROM optimization_fetch_attempts WHERE lead_id = ?",
                    (lead_id,),
                ).fetchone()["value"]
            )
            attempt_id = connection.execute(
                """INSERT INTO optimization_fetch_attempts (
                       lead_id, attempt_number, started_at, status
                   ) VALUES (?, ?, ?, 'running')""",
                (lead_id, attempt_number, _now()),
            ).lastrowid
            identities = connection.execute(
                """SELECT identity.*, link.metadata_json AS lead_metadata_json
                   FROM optimization_candidate_identities AS identity
                   JOIN optimization_identity_leads AS link
                     ON link.identity_id = identity.id
                   WHERE link.lead_id = ? AND identity.boundary_state = 'resolved'
                     AND identity.target_stage_key = ?
                   ORDER BY identity.id""",
                (lead_id, self.configuration_record["snapshot"]["stageKey"]),
            ).fetchall()
        try:
            fetched = self.fetch(str(lead["canonical_url"]))
            text = str(fetched.get("text") or "").strip()
            if not text:
                raise ValueError("Fetch returned no bounded text")
            final_url = canonicalize_discovery_url(
                fetched.get("finalUrl") or lead["canonical_url"]
            )
            status_code = int(fetched.get("statusCode") or 0)
            content_type = str(fetched.get("contentType") or "text/plain")
            if not 200 <= status_code < 300:
                raise ValueError(f"Fetch returned HTTP {status_code}")
            if content_type.split(";", 1)[0].strip().casefold() not in {
                "text/html",
                "application/xhtml+xml",
                "text/plain",
            }:
                raise ValueError(f"Fetch returned unsupported content type {content_type}")
            maximum_characters = max(
                1,
                int(
                    self.configuration_record["snapshot"]["limits"].get(
                        "evidenceExtractMaxChars", 30000
                    )
                ),
            )
            was_over_limit = len(text) > maximum_characters
            text = text[:maximum_characters]
            truncated = bool(fetched.get("truncated")) or was_over_limit
            full_extract = {
                "title": str(lead["title"]),
                "text": text,
                "sourceUrl": str(lead["canonical_url"]),
                "finalUrl": final_url,
            }
            full_extract_hash = sha256_json(full_extract)
            identity_extracts: dict[int, dict[str, Any]] = {}
            context_characters = max(
                0,
                int(
                    self.configuration_record["snapshot"]["limits"].get(
                        "referralEvidenceContextCharacters", 2000
                    )
                ),
            )
            for identity in identities:
                lead_metadata = json.loads(identity["lead_metadata_json"] or "{}")
                excerpt = str(lead_metadata.get("evidenceExcerpt") or "").strip()
                identity_extract = dict(full_extract)
                if excerpt:
                    position = text.find(excerpt)
                    if position < 0:
                        raise ValueError(
                            "Reviewed evidence excerpt is absent for "
                            f"{identity['identity_key']}"
                        )
                    start = max(0, position - context_characters)
                    end = min(
                        len(text), position + len(excerpt) + context_characters
                    )
                    identity_extract["text"] = text[start:end]
                    identity_extract["selection"] = {
                        "method": "reviewed-exact-excerpt",
                        "excerpt": excerpt,
                        "sourceStart": start,
                        "sourceEnd": end,
                    }
                identity_extracts[int(identity["id"])] = identity_extract
        except Exception as error:
            with self.store.connect() as connection:
                connection.execute(
                    """UPDATE optimization_fetch_attempts
                       SET completed_at = ?, status = 'failed', error = ? WHERE id = ?""",
                    (_now(), str(error), attempt_id),
                )
                connection.execute(
                    """UPDATE optimization_discovery_leads
                       SET fetch_status = 'failed', failure_reason = ? WHERE id = ?""",
                    (str(error), lead_id),
                )
            raise OptimizationPipelineError(
                f"Fetch failed for {lead['canonical_url']}: {error}"
            ) from error
        with self.store.connect() as connection:
            for identity in identities:
                metadata = json.loads(identity["metadata_json"] or "{}")
                lead_metadata = json.loads(identity["lead_metadata_json"] or "{}")
                extract = identity_extracts[int(identity["id"])]
                extract_hash = sha256_json(extract)
                page_organization = str(
                    fetched.get("pageOrganization") or identity["organization"]
                )
                page_program = str(fetched.get("pageProgram") or identity["program"])
                page_identity_key = candidate_identity_key(page_organization, page_program)
                authority = source_authority(
                    final_url,
                    direct_domains=lead_metadata.get(
                        "directDomains", metadata.get("directDomains", [])
                    ),
                    reviewed_authority=lead_metadata.get(
                        "reviewedAuthority", metadata.get("reviewedAuthority")
                    ),
                )
                connection.execute(
                    """INSERT OR REPLACE INTO optimization_evidence_sources (
                           identity_id, canonical_url, authority, page_identity_key,
                           fetched_at, final_url, status_code, content_type, truncated,
                           extract_json, extract_sha256
                       ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        identity["id"],
                        lead["canonical_url"],
                        authority,
                        page_identity_key,
                        _now(),
                        final_url,
                        status_code,
                        content_type,
                        int(truncated),
                        canonical_json(extract),
                        extract_hash,
                    ),
                )
            now = _now()
            connection.execute(
                """UPDATE optimization_fetch_attempts
                   SET completed_at = ?, status = 'completed', final_url = ?,
                       status_code = ?, content_type = ?, truncated = ?, extract_sha256 = ?
                   WHERE id = ?""",
                (
                    now,
                    final_url,
                    status_code,
                    content_type,
                    int(truncated),
                    full_extract_hash,
                    attempt_id,
                ),
            )
            connection.execute(
                """UPDATE optimization_discovery_leads
                   SET redirect_url = ?, fetch_status = 'fetched', failure_reason = ''
                   WHERE id = ?""",
                (final_url if final_url != lead["canonical_url"] else None, lead_id),
            )
        self.progress({"phase": "fetch", "url": lead["canonical_url"]})

    def _freeze_corpus(self, run_id: int) -> int:
        with self.store.connect() as connection:
            branches = [
                dict(row)
                for row in connection.execute(
                    "SELECT * FROM optimization_coverage_branches WHERE run_id = ? ORDER BY id",
                    (run_id,),
                ).fetchall()
            ]
            queries = [
                dict(row)
                for row in connection.execute(
                    """SELECT query.* FROM optimization_queries AS query
                       JOIN optimization_coverage_branches AS branch ON branch.id = query.branch_id
                       WHERE branch.run_id = ? ORDER BY branch.id, query.position""",
                    (run_id,),
                ).fetchall()
            ]
            leads = [
                dict(row)
                for row in connection.execute(
                    "SELECT * FROM optimization_discovery_leads WHERE run_id = ? ORDER BY id",
                    (run_id,),
                ).fetchall()
            ]
            identities = [
                dict(row)
                for row in connection.execute(
                    "SELECT * FROM optimization_candidate_identities WHERE run_id = ? ORDER BY identity_key",
                    (run_id,),
                ).fetchall()
            ]
            sources = [
                dict(row)
                for row in connection.execute(
                    """SELECT source.* FROM optimization_evidence_sources AS source
                       JOIN optimization_candidate_identities AS identity ON identity.id = source.identity_id
                       WHERE identity.run_id = ? ORDER BY identity.identity_key, source.canonical_url""",
                    (run_id,),
                ).fetchall()
            ]
        sources_by_identity: dict[int, list[dict[str, Any]]] = {}
        for source in sources:
            decoded = dict(source)
            decoded["extract"] = json.loads(decoded.pop("extract_json"))
            sources_by_identity.setdefault(int(source["identity_id"]), []).append(decoded)
        packets: list[dict[str, Any]] = []
        for identity in identities:
            if (
                identity["boundary_state"] != "resolved"
                or identity["target_stage_key"]
                != self.configuration_record["snapshot"]["stageKey"]
            ):
                continue
            identity_sources = sources_by_identity.get(int(identity["id"]), [])
            if not identity_sources:
                raise OptimizationPipelineError(
                    f"Resolved identity {identity['identity_key']} has no fetched evidence"
                )
            identity_metadata = json.loads(identity["metadata_json"] or "{}")
            packets.append(
                {
                    "schemaVersion": 1,
                    "candidateIdentity": {
                        "organization": identity["organization"],
                        "program": identity["program"],
                        "identityKey": identity["identity_key"],
                        "boundaryState": identity["boundary_state"],
                        "coverageTags": identity_metadata.get("coverageTags", []),
                    },
                    "packageMatch": {
                        "state": identity["package_match_state"],
                        "resourceId": identity["package_resource_id"],
                        "reason": identity["decision_reason"],
                    },
                    "sources": identity_sources,
                }
            )
        if not packets:
            raise OptimizationPipelineError("Discovery produced no resolved evidence packets")
        ledger_record = {"branches": branches, "queries": queries, "leads": leads}
        identity_record = identities
        source_record = sources
        packet_hashes = [sha256_json(packet) for packet in packets]
        hashes = {
            "ledger": sha256_json(ledger_record),
            "identities": sha256_json(identity_record),
            "sources": sha256_json(source_record),
            "packets": sha256_json(packet_hashes),
        }
        corpus_hash = sha256_json(hashes)
        with self.store.connect() as connection:
            existing = connection.execute(
                "SELECT id FROM optimization_corpora WHERE corpus_sha256 = ?",
                (corpus_hash,),
            ).fetchone()
            if existing:
                return int(existing["id"])
            corpus_id = int(
                connection.execute(
                    """INSERT INTO optimization_corpora (
                           discovery_run_id, created_at, status, ledger_sha256,
                           identities_sha256, sources_sha256, packets_sha256, corpus_sha256
                       ) VALUES (?, ?, 'building', ?, ?, ?, ?, ?)""",
                    (
                        run_id,
                        _now(),
                        hashes["ledger"],
                        hashes["identities"],
                        hashes["sources"],
                        hashes["packets"],
                        corpus_hash,
                    ),
                ).lastrowid
            )
            for packet, packet_hash in zip(packets, packet_hashes, strict=True):
                connection.execute(
                    """INSERT INTO optimization_evidence_packets (
                           corpus_id, identity_key, packet_json, packet_sha256
                       ) VALUES (?, ?, ?, ?)""",
                    (
                        corpus_id,
                        packet["candidateIdentity"]["identityKey"],
                        canonical_json(packet),
                        packet_hash,
                    ),
                )
            connection.execute(
                """UPDATE optimization_corpora
                   SET status = 'frozen', frozen_at = ? WHERE id = ?""",
                (_now(), corpus_id),
            )
            report = {
                "complete": True,
                "branchCount": len(branches),
                "executedQueryCount": sum(
                    1 for query in queries if query["status"] == "completed"
                ),
                "leadCount": len(leads),
                "resolvedIdentityCount": len(packets),
                "packageEligibleIdentityCount": sum(
                    1
                    for identity in identities
                    if identity["boundary_state"] != "excluded-existing"
                    and identity["target_stage_key"]
                    == self.configuration_record["snapshot"]["stageKey"]
                ),
                "routedIdentityCount": sum(
                    1
                    for identity in identities
                    if identity["target_stage_key"]
                    != self.configuration_record["snapshot"]["stageKey"]
                ),
                "packetCount": len(packets),
            }
            connection.execute(
                """INSERT OR REPLACE INTO optimization_audits (
                       run_id, audit_type, created_at, report_json, report_sha256
                   ) VALUES (?, 'coverage', ?, ?, ?)""",
                (run_id, _now(), canonical_json(report), sha256_json(report)),
            )
        return corpus_id

    def _existing_corpus(self, run_id: int) -> int | None:
        with self.store.connect() as connection:
            row = connection.execute(
                """SELECT id FROM optimization_corpora
                   WHERE discovery_run_id = ? AND status = 'frozen' ORDER BY id DESC LIMIT 1""",
                (run_id,),
            ).fetchone()
        return int(row["id"]) if row else None

    def _mark_run(
        self, run_id: int, *, status: str, phase: str, error: str = ""
    ) -> None:
        now = _now()
        with self.store.connect() as connection:
            connection.execute(
                """UPDATE optimization_runs
                   SET status = ?, current_phase = ?, error = ?,
                       started_at = COALESCE(started_at, ?),
                       completed_at = CASE WHEN ? IN ('completed', 'failed', 'cancelled')
                                           THEN ? ELSE NULL END
                   WHERE id = ?""",
                (status, phase, error, now, status, now, run_id),
            )

    def _result(
        self, run_id: int, configuration_id: int, corpus_id: int
    ) -> DiscoveryCorpusResult:
        with self.store.connect() as connection:
            corpus = connection.execute(
                "SELECT * FROM optimization_corpora WHERE id = ?", (corpus_id,)
            ).fetchone()
            branch_count = int(
                connection.execute(
                    "SELECT COUNT(*) AS count FROM optimization_coverage_branches WHERE run_id = ?",
                    (run_id,),
                ).fetchone()["count"]
            )
            query_count = int(
                connection.execute(
                    """SELECT COUNT(*) AS count FROM optimization_queries AS query
                       JOIN optimization_coverage_branches AS branch ON branch.id = query.branch_id
                       WHERE branch.run_id = ? AND query.status = 'completed'""",
                    (run_id,),
                ).fetchone()["count"]
            )
            lead_count = int(
                connection.execute(
                    "SELECT COUNT(*) AS count FROM optimization_discovery_leads WHERE run_id = ?",
                    (run_id,),
                ).fetchone()["count"]
            )
            identity_counts = connection.execute(
                """SELECT COUNT(*) AS total,
                          SUM(CASE WHEN boundary_state = 'excluded-existing' THEN 1 ELSE 0 END) AS excluded,
                          SUM(CASE WHEN target_stage_key != ? THEN 1 ELSE 0 END) AS routed,
                          SUM(CASE WHEN boundary_state != 'excluded-existing'
                                    AND target_stage_key = ? THEN 1 ELSE 0 END) AS eligible
                   FROM optimization_candidate_identities WHERE run_id = ?""",
                (
                    self.configuration_record["snapshot"]["stageKey"],
                    self.configuration_record["snapshot"]["stageKey"],
                    run_id,
                ),
            ).fetchone()
            source_count = int(
                connection.execute(
                    """SELECT COUNT(*) AS count FROM optimization_evidence_sources AS source
                       JOIN optimization_candidate_identities AS identity ON identity.id = source.identity_id
                       WHERE identity.run_id = ?""",
                    (run_id,),
                ).fetchone()["count"]
            )
            packet_count = int(
                connection.execute(
                    "SELECT COUNT(*) AS count FROM optimization_evidence_packets WHERE corpus_id = ?",
                    (corpus_id,),
                ).fetchone()["count"]
            )
        return DiscoveryCorpusResult(
            run_id=run_id,
            configuration_id=configuration_id,
            corpus_id=corpus_id,
            corpus_sha256=str(corpus["corpus_sha256"]),
            branch_count=branch_count,
            query_count=query_count,
            lead_count=lead_count,
            identity_count=int(identity_counts["total"] or 0),
            eligible_identity_count=int(identity_counts["eligible"] or 0),
            routed_identity_count=int(identity_counts["routed"] or 0),
            excluded_identity_count=int(identity_counts["excluded"] or 0),
            source_count=source_count,
            packet_count=packet_count,
        )
