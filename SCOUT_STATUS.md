# Scout Current Status

Read this file before substantive Scout work. Verify live process/database state;
a monitor process is not a research worker.

## Live launch — September 18, 2026, 22:39 UTC

Michael explicitly authorized: “run the 21-category Scout and tell me the port
number.” Production is running with Codex+Grok, Codex CLI at High. Grok preflight
passed and the Employment challenger started. Runner PID at launch: 10099;
monitor PID: 10078. Monitor: **http://127.0.0.1:8769**. Verify current processes
before any resume; these PIDs are observations, not permanent identities.
`data/st-george-production-20260918-codex-grok/launch.json` records the command.
The runner log is adjacent. Do not launch a duplicate worker.

## Binding instructions

- Work in `~/resource-scout-pairwise`, branch `pairwise-research-experiment`.
- **Claude is disabled for all Scout work, including preflights and probes.**
  Michael reported more than $125 in unexpected Anthropic charges. Do not
  re-enable it without his explicit new instruction. Reading saved Claude
  responses is allowed; assigning it new work is not.
- Preserve the three completed experiment databases and the earlier five-worker
  baseline. Never rerun their completed categories or replace those databases.
- Michael explicitly authorized the 21-category production launch after the
  completed Extra High review. The run is now active. Codex CLI workers use
  High; no further launch confirmation is needed for an ordinary safe resume.
- Bonsai was removed at Michael's request. Structured extraction is deferred,
  not a current or near-term task.

## Current state: September 18, 2026

All three conditions in `data/pairwise-overnight-20260918-022703/` completed their
six categories: Addiction, Children/Pregnancy, Clothing/Household, Disability,
Domestic Violence, Education. The final Claude+Grok research worker exited after
Education; no seventh experimental category ran. The separate production worker has now started.

- `codex-grok.sqlite3`: complete, 473 submitted rows.
- `codex-claude.sqlite3`: complete, 567 submitted rows.
- `claude-grok.sqlite3`: complete, 698 submitted rows.

These are raw submissions, not accepted unique resources. All lack recorded
curator acceptance/time. Source hashes and frozen snapshots are in
`data/pairwise-review-20260918/final-evidence.json`.

Completed Extra High reports:

- [Architecture review](docs/six-category-architecture-review-20260918.md)
- [Earlier five-worker comparison](docs/five-worker-versus-codex-grok-20260918.md)
- [Consequential source audit](docs/six-category-source-audit-20260918.md)
- [Pairwise metrics](docs/six-category-results-20260918.json)
- [Five-worker metrics](docs/five-worker-comparison-results-20260918.json)

The older baseline is
`~/resource-scout-baselines/st-george-20260918-002522/research-agent.sqlite3`.
It contains 310 canonical submissions plus 102 separately saved Claude shadow
rows across these six categories. The new pair returned 473 versus those 412,
with about 91 versus 298 elapsed category minutes including shadows. The older
workflow included scheduling/manual handoffs; this is not an active-model-speed
ratio. It has useful findings missing from the new pair, including EnglishConnect,
BYU–Pathway, accessible library service and the Lifeline survivor benefit.
Some came from its Codex primary. Preserve the old evidence instead of replacing
it with the pair's list.

## Architecture decision

Use **Codex focused primary + Grok challenger**, with explicit pathway/gap checks
and narrow follow-up when a consequential gap is demonstrated. Claude routing
from an earlier draft was withdrawn. Current evidence does not justify a learned
provider router, five broad workers per category, automatic recursive splitting,
or acceptance/recall claims based on raw rows.

The Grok stalls were authentication failures (HTTP 401 and strict-sandbox
credential-lock errors), with zero completed inference/tool events in those
attempts. After login, the unchanged sealed Addiction request completed in
232.309 seconds, six turns, fifteen leads. Larger subsequent requests also
completed monolithically. Recursive partitioning was reverted; all fifteen
historical partition rows remain. Authentication/timeout/turn-limit failures
stop without unchanged automatic retries or provider fallback.

Claude's original 24-turn wrapper failures were an artificial ceiling; recovered
runs used 60. Keep that history distinct from the authentication outage and from
successful recovered calls. Historical native Claude/tool counters are not
uniformly comparable to Grok/Codex counters. Missing values remain unknown.

## Active production workspace

Database: `data/st-george-production-20260918-codex-grok/research.sqlite3`
Manifest: adjacent `research.preparation.json` records the pre-launch preparation
snapshot. The newer `launch.json` records the authorized active launch.
Read the [launch handoff](docs/st-george-production-handoff-20260918.md).

Verified preparation:

- All six completed Codex+Grok jobs, passes and assignments preserved unchanged.
- 2,150 source rows retained in six separate curation-union runs from the three
  pairs and the earlier five-worker run, including Claude shadow evidence.
- All eight completed Employment primary passes reused (37 leads). Its next
  research is the Grok challenger, not another primary run.
- Two completed Financial Assistance primary passes reused (11 leads); resume
  the remaining passes. Thirteen other categories remain untouched.
- Only Codex and Grok are enabled in every production category plan.
- All four source database hashes unchanged; production SQLite quick_check passed.
- Full local suite: 207 tests, one skipped. No live provider calls during these
  tests; historical Claude fixtures are mocked. Final commit/CI recorded in the
  handoff when available.

The initial draft copy at `data/st-george-production-20260918-reviewed/` failed
on SQLite cache-spill locking during consolidation. It is preserved and explicitly
marked `abandoned-not-for-launch`; its obsolete Claude routing must not be used.
The lock bug is fixed and regression-tested. Use only the new copy above.

The runner uses an exclusive database lock, a resume-safe total category cap,
explicit Codex High effort, and honest nullable telemetry. Prompt v4 adds geography,
service-exclusion, fee/availability and distinct-access-pathway checks. Those are
preventive guidance, not a new tested six-category condition.

## Launch/curation boundaries

Production is already running. Before any resume, inspect actual worker
processes and DB statuses; never start a duplicate. Keep
Codex/Grok preflight enabled. Refresh Grok login outside its strict research
sandbox when needed; never call Claude as fallback.

Monitors at 8767 and 8768, if still running, only view the completed experiment.
A production monitor can use 8769; a monitor does not perform research.

After research completes, consolidate and curate before creating usable
`autoStGeorge.html`. Stephanie wants eligibility requirements, how best to connect,
access (including hours), and important information. This does not reopen the
structured-extraction project. Cedar City, Las Vegas and Salt Lake remain queued.

## Architecture-review checklist retained for follow-up

Evaluate research quality and consequential pathway misses; primary/challenger
complementarity; accepted unique identities and marginal challenger contribution;
wall time and active/successful/failed worker time; turns, searches/tools, retries
and failures; curator time, duplicates and noise; category differences; accepted
identities per active research minute; marginal accepted identities per additional
research minute; Claude turn-limit history; Grok authentication versus task-shape
failures; and fairness between original and recovered conditions.

Consider adaptive task scope and provider choice rather than declaring a fixed
pair universally best. Current accepted-identity rates and curator minutes are
unknown. Record them during curation; do not manufacture a score from name/domain
counts. A future controlled replay should use the same sealed primary, blinded
identity decisions and repeated categories. No new replay is authorized now.
