# Stale and dead-end code audit

Status: pre-cutover classification on the `manual-multimodel-discovery` branch,
2026-08-25. This audit makes no production retirement decision. Removal and
service changes remain gated on the real two-category pilot and Michael's
approval.

## Method and result

The audit covered every top-level Python and shell command, every Python module,
the Scout and Curator JavaScript, the DSH patches and runtime launchers, the
LaunchAgent templates, documentation entry points, and their tests. Static import
reachability was checked from both the Scout command-line entry point and the
separate Local Qwen service. Public Python definitions with no repository caller
were inspected individually rather than deleted by name count. Scout/Curator DOM
references and JavaScript function references were rechecked by the existing
test suite and a declaration/reference scan.

No unaccounted production module, orphaned JavaScript function, stale Scout
curation-write route, or duplicate package-building path was found. Three Python
callables have no current in-repository caller, but each has an explicit retained
boundary:

- `ImportedPackage.target_assets` is a compatibility alias for `seed_assets`;
- `ResearchStore.import_target_category` is a compatibility accessor for older
  single-target-category callers; and
- `ReviewedIdentityResolver.from_path` is a calibration convenience for external
  reviewed manifests.

They are compatibility or calibration surface, not evidence of a safe deletion.
No file was removed solely because a static scan could not see an external or
historical caller.

## Production path

These components are live for current Scout, the manual workflow, Curator export,
or the separately supervised Local Qwen service:

- `resource_research_agent.__main__`, `cli`, `server`, `storage`, `importer`,
  `duplicates`, `playbooks`, and `tailscale`;
- `manual_discovery` and `manual_consolidation`;
- `resource_package`, `review_export`, the Curator HTML/JavaScript, and the Scout
  HTML/JavaScript;
- `research`, `agents`, and `dsh_configuration` for the advanced agent path and
  historical run compatibility;
- `local_qwen`, `mlx_server_workaround`, `local-qwen.sh`,
  `run-local-qwen-service.sh`, and `run-qwen-tailscale.sh` for the current
  unmetered production agent service; and
- `background-service.sh` plus both LaunchAgent templates.

The normal background launcher is Local Qwen plus Tailscale Scout. README text
that still called it the DeepSeek launcher and instructed the user to prepare a
DeepSeek key was stale and has been corrected by this audit.

## Historical compatibility surface

Keep the following while old runs and Curators must remain readable:

- agent adapters and configuration records for DeepSeek, Qwen, Hermes, and demo;
- historical Scout review and generated-resource database columns, which are
  read-only sources for portable Curator export;
- optimization review-copy support in `review_export`, including the HTTP export
  endpoint when Scout is deliberately opened on an isolated benchmark database;
- Curator schema compatibility and earlier candidate/resource ID recognition;
  and
- the three compatibility callables listed above.

This compatibility surface does not restore Scout-side vetting or package
creation. Tests continue to require the old write routes to return 404 while
historical exports remain available.

## Calibration and reproducibility surface

The following are not part of ordinary manual discovery and must not be presented
as its hidden fallback. They remain necessary to reproduce or audit the frozen
Qwen/DeepSeek evidence:

- `benchmark`, `optimization_*`, `optimization_pipeline`,
  `optimization_runtime`, `optimization_review`, and `optimization_outcomes`;
- the Housing-only `optimization_housing_calibration` fixture;
- the cache, review-patch, evidence-preparation, freeze, run, recompute, export,
  comparison, and package-outcome top-level commands; and
- the ignored frozen benchmark databases and artifacts documented by their
  receipts.

Several top-level calibration commands appear only in their own file during a
plain filename-reference scan. Their imported modules, command help, and frozen
artifact contracts show that they are explicit operator entry points, not
unreachable functions. They should eventually move behind an archival
`calibration/` layout or command group, but renaming them before the preserved
benchmark is archived would make reproduction harder without improving the
production path.

## One-time discovery-expansion surface

`identity_qualification`, `prior_leads`, `prior_lead_harvest`, `query_expansion`,
`referral_graph`, and `referral_review`, together with their manifest builders and
routed-lead exporter, are bounded one-time or calibration tools. They do not run
from manual discovery and do not promote historical facts into current evidence.
The abandoned 548-lead Mesa haystack remains preserved and must not resume
automatically.

These tools are not candidates for immediate deletion because their immutable
receipts explain earlier benchmark coverage. They are candidates for archival
separation after production cutover, not for continued prominence in the normal
README workflow.

## Temporary Trace Scout

`trace_scout`, `trace_console`, `trace_client`, `trace-scout.sh`,
`dsh-trace-qwen.patch.yml`, and the traced provider hooks form one isolated
diagnostic system. The normal configuration hides Trace Qwen unless an existing
trace setting is being recovered. Trace uses disposable ports and data and is not
a dependency of manual discovery.

The trace system is a post-pilot retirement candidate. Until Michael makes that
decision, retain it as one coherent, tested diagnostic rather than deleting only
the launcher or only the hidden configuration and leaving a half-live path.

## Batch runner and paid/slow agent paths

`run_scout_category_batch.py` is operational, resumable, and tested, but it exists
to drive the slow Local Qwen research route. It is not part of manual discovery.
The DeepSeek launchers and explicit metered configuration are also deliberate
advanced/compatibility paths; production does not silently select them.

After the two-category pilot, the production decision should address these as a
set:

1. whether Local Qwen remains an advanced on-demand option;
2. whether its 8-bit service should continue starting automatically and holding
   memory when manual discovery is the default;
3. whether the sequential batch runner remains documented or becomes archival;
4. whether DeepSeek remains selectable or only historical runs remain readable;
   and
5. whether Hermes and the built-in demo still earn foreground connection UI.

Stopping automatic Local Qwen startup is separable from deleting compatibility
code. Old Qwen and DeepSeek runs and their Curator exports do not require a model
service to remain running.

## Documentation findings

The main README correctly presents manual discovery as recommended and agent
research as advanced. This audit corrected the stale background-service text;
the service no longer uses or requires DeepSeek.

The long calibration instructions are accurate but too prominent for the future
manual product. After cutover they should move to an archival benchmark document,
leaving the README focused on package connection, manual discovery, consolidation,
Curator export, and background/Tailscale operation.

## Removal gate

No deletion is authorized before all of the following are true:

- Addiction and one materially different category complete through the manual
  workflow;
- Michael approves candidate volume, identity review, and Curator presentation;
- production database backup, migration, rollback, loopback, and Tailscale tests
  pass;
- frozen benchmark reproduction entry points and historical export requirements
  are explicitly separated from production requirements; and
- each retirement target is removed as a coherent path with its tests and docs,
  not as an isolated file guessed to be unused.

This leaves no known dead-end code silently attached to the manual workflow. It
also avoids deleting historical or diagnostic evidence merely because the new
workflow is promising.
