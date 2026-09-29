# Scout current status

## Routine review recovery enabled — September 29

Michael requested automatic handling of issues like the Welfare Square context
failure. Session 011 exhausted context in Food, after saving four groups covering
60/69 draft resources and 63/74 original candidate dispositions. The worker exited
with code 1, not a timeout. Session 012 is now running at the same Extra High effort;
nine prior categories and all four Food groups are preserved. Recovery evidence:
`data/welfare-square-fresh-20260928/review-context-recovery-20260929T232950Z/`.
Next sessions cap content work at two bounded groups and separate taxonomy/selection
when needed. Depth and the final supervising-assistant acceptance gate remain.

Persistent review-recovery monitors are attached to both pipelines: Welfare Square
PID 78888 and Mesa PID 78889. Verify live receipts/status before using those PIDs.
Each run has `review-recovery-launch.json`, `review-recovery-status.json`, and a
separate supervisor log. Native context exhaustion with new saved decisions and
bounded transient failures resume in a fresh session automatically. Repeated
no-progress, account, unknown and acceptance failures remain explicit rather than
triggering unlimited paid retries. Original attempts and retry budgets are durable.
Welfare Square's exact acceptance-wrapper command is retained on every restart.
Mesa remains in curation (19/21 complete at this checkpoint); its review monitor
will cover the automatically started review. See orchestration's recovery section.

## Welfare Square thorough review rerun — September 29, 12:43 Mountain

Michael requested: **"Run the review again. I want a thorough job."** This supersedes
the first review's completion and delivery-ready status. All 21 original curation
categories remain complete and unchanged. The first 21-minute review relied on
heuristic-generated taxonomy, selections and blanket assessments; structural checks
did not substantiate the required individual judgments. Its delivery is provisional
and marked `deliveries/welfare-square-fresh-20260928/SUPERSEDED.md`; do not commit or
import it as an accepted delivery.

- Original review, config/status, registry snapshot and SHA-256 manifest are preserved
  under `data/welfare-square-fresh-20260928/thorough-review-restart-20260929T184336Z/`.
- Fresh sequential gpt-5.5/xhigh review uses the same completed job/database and fresh
  `review/` directory. Read `review/RERUN_INSTRUCTIONS.md`: individual evidence-backed
  four-rule decisions, original candidate omissions, bounded groups of at most 15,
  at most one completed category per session, collection reconciliation, authored
  taxonomy/selections and evidence-based complement stopping. No heuristic compiler.
- Persistent supervisor retains native logs/checkpoints and bounded continuation
  (64 sessions maximum, 90-minute per-session safety timeout; checkpoint before
  75 minutes). New instruction requests a final `needs-attention` checkpoint for
  assistant acceptance; the run-specific supervisor independently blocks autoexport.
- Launch entrypoint is the preserved amendment's `supervise_thorough_review.py`,
  with this run's `pipeline.json`. Verify live status/PIDs before operating it.
- Supervising assistant must audit the actual authored decisions and coverage, then
  perform locked registry/export validation and commit/handoff. New delivery target:
  `deliveries/welfare-square-fresh-20260928-r2/`. Registry allocations from the first
  export are preserved; do not roll back the shared registry or disturb Mesa.
- Mesa continues independently under its existing authorization and supervisor.
- Welfare Square's dashboard at http://127.0.0.1:8770 now shows category checks,
  optional saved record counts/findings and separate native reviewer activity,
  polling every 15 seconds. The live reviewer instructions include
  `review/UI_PROGRESS_CONTRACT.md`; future prepared-review prompts include the same
  checkpoint fields. Only the dashboard server was reloaded for the UI update.
- Michael also requested a full-review completion estimate. The dashboard now
  includes content pace plus explicit planning allowances for cross-category
  consolidation, taxonomy, selections and final validation/supervisor audit.
  See the prepared-resource contract's estimate section. Checkpoint observations
  persist in `review-estimate-history.json`; superseded session timing is excluded.

## Current focus — parallel Welfare Square and Mesa, September 29

Michael explicitly requested: restart Welfare Square curation alongside Mesa,
verify separate databases/output folders, and automatically start both Codex reviews.
This supersedes every Welfare Square pause/hold in the historical notes below.

- **Welfare Square:** resumed job 1 from 13/21 completed categories; ID Recovery
  batch 1/3 is active. Database `data/welfare-square-fresh-20260928/research.sqlite3`;
  curation and review directories are under that run; final output is
  `deliveries/welfare-square-fresh-20260928/`. Curation supervisor 35589,
  coordinator 35599, pipeline 35590; dashboard remains port 8770.
- **Mesa:** job 6 remains active, 8/21 complete and Reentry Support active at this
  checkpoint. Database `data/mesa-recuration-20260929/research.sqlite3`; curation
  and review directories are under that run; final output is
  `deliveries/mesa-recuration-20260929/`. Original curation supervisor 19901 and
  coordinator 19906 were preserved; pipeline supervisor reloaded as 35593.
  Dashboard remains port 8771.
- Both configs retain `automaticReview:true`, `preparedReviewAuthorized:true`,
  High curation and `gpt-5.5`/Extra High review. Each review follows its own office's
  curation automatically; neither waits for the other office. Persistent supervisors
  perform bounded monitoring/recovery. Final registry commit and delivery handoff
  remain the supervising assistant's responsibility.
- The identity registry is intentionally shared. Both pipeline supervisors now
  load the registry export lock: only final validation/allocation/export/readback
  takes turns; curation and reviews can proceed concurrently. Review workers must
  not write the registry themselves. Do not launch a separate unguarded exporter.
- Resume evidence, prior manifests/status and hashes of all 13 completed Welfare
  Square categories are preserved in
  `data/welfare-square-fresh-20260928/resume-parallel-20260929T141759Z/`.
  No research was restarted and no sealed assignment was changed. Verify live
  process/status/database state before acting; the counts and PIDs above are a checkpoint.

## Earlier Mesa launch checkpoint — September 29

Michael superseded the earlier Mesa hold: **pause Welfare Square curation and
start new Mesa curation and review**. Welfare Square is now paused at 13/21 saved
categories, including Housing; its automatic review is stopped. Its dashboard on
8770 remains available (PID 19899). The category-limited finisher reused the active
paid worker, saved Housing, then exited without assigning another category. Prior
category hashes were verified unchanged. Pause receipts and original continuation
settings are in `data/welfare-square-fresh-20260928/pause-for-mesa-20260929/`.
Do not resume Welfare Square without Michael's instruction.

**Mesa is running on port 8771:** `data/mesa-recuration-20260929/research.sqlite3`,
import 4, fresh prepared job 6, policy `codex-preparation-v5-office-fit`. High curation
uses all preserved research: 3,920 candidate/category entries across 21 researched
categories. These are screening inputs, not an assertion of useful resource count.
Old prepared text, starter choices and reviewed context are not supplied. Each new
assignment contains all four office-fit rules. The source database snapshot and
office category IDs are frozen; all older research and deliveries remain untouched.
Seven human-suppressed identities and prior identity aliases are separately preserved,
with an export gate against resurrecting those identities. Meaningfully distinct
programs do not inherit an old parent's suppression automatically.

Mesa's curation coordinator is PID 19906, curation supervisor 19901, pipeline 19902,
local dashboard 20294 and Tailscale dashboard 20295. Verify live manifests/status
because PIDs and progress can change. Both listeners use port 8771; the private
Tailscale address is recorded in the ignored run's `launch.json`.
Initial progress is Addiction batch 1/10. One sequential Extra High Codex review
and validated prepared export follow automatically. Review covers the 21 service
categories and explicitly assesses Miscellaneous from assigned evidence; no new
broad discovery. Output target: `scout-mesa-prepared-resources-<YYYY-MM-DD>.json`
under `deliveries/mesa-recuration-20260929/`, dated at generation. Registry commit
and final handoff still follow the prepared-delivery gate. 778 tests passed, 4 skipped.
The dashboard shows review stages and completed category checks from saved review
checkpoints, including content, taxonomy and selections. Identity and validation
are collection-wide stages. Counts are reviewer-reported, not an acceptance gate;
no percentage is inferred from elapsed time. Both dashboard APIs were checked live
without restarting curation; Welfare Square still reports paused.
See [current Mesa run](docs/mesa-recuration-20260929.md).

## September 29 review instructions

Michael initially held Mesa curation while inspecting policy, then explicitly
authorized the new run above. He approved consolidating the
review guidance: 7–10 explained starters, then AI-selected ordered complements
considering uncovered Types and other evidenced practical benefits, then searchable
usable reserves. Apply the four office-fit rules throughout; no filler quota,
invented benefit or unsupported capacity claim. The consolidated instructions are
in the prepared-resource contract and prepared review prompt, with a pointer in
AGENTS.md. Complementary selections are recorded in the review ledger/report;
export/import support for that explicit order remains pending. Frozen Housing
comparisons retain their original protocol. The separate Church-account Claude
Housing experiment is not this full-Mesa Codex run.

## Fresh Welfare Square run — September 28 (now paused)

Michael authorized a blank-sheet Welfare Square run, with earlier research archived
apart. The fresh database is `data/welfare-square-fresh-20260928/research.sqlite3`.
Only office scope and category IDs/labels are supplied: zero resources, Types,
For groups, imported discoveries or review context. Twenty-one new research jobs
are sealed for Codex High primary plus DeepSeek V4.1-Flash/max challenger only.
The service area remains Salt Lake County, including eligible phone/online routes.
Current office-fit rules apply. No completed category or old run is reused.

Earlier Welfare Square research, curation, DeepSeek and Jev evidence is now at
`~/resource-scout-archive/welfare-square-before-20260928-fresh/`: 6,686 files,
6,684,105,581 bytes, with original paths and SHA-256 hashes in `manifest.json`.
Do not read that archive into fresh worker assignments. Old absolute runtime paths
are historical; no redirect or symlink exposes them through the fresh directory.

Research is complete for all 21 categories. On September 28 evening, curation
stopped in Domestic Violence batch 3 because the native result omitted five
consecutive characters from its assignment checksum. All 15 candidate dispositions
and 12 resources passed full validation after restoring only that checksum.
The native output remains untouched; the separately sealed reviewed repair and
recovery audit are under `curation/recovery-hash-copy-001/` and the original batch.
Four completed category result hashes were preserved. New batch response schemas
now require the exact assigned checksum/category; existing schemas remain sealed.
775 tests passed (4 skipped). No research or completed curation was repeated.

Historical recovery: curation resumed at 2026-09-29 03:04 UTC: worker PID 12564, curation supervisor
12566, full-delivery pipeline 12567; dashboard remains 96687 on port 8770.
Verify `launch.json`, curation launch/status and live database state before acting;
PIDs and progress can change. The existing coordinator restart budget was preserved.
Domestic Violence then completed with 55 resources (five categories complete);
Education batch 1/4 is now active.
The dashboard is assigned port 8770. Automatic High **prepared-mode** curation
follows completed research; no previous reviewed context is supplied. Michael then
explicitly requested the complete run, including the final work product. The pipeline
now continues through **one sequential Extra High prepared-resource review** and
validated export: `scout-welfare-square-prepared-resources-<YY-MM-DD>.json`, dated
when generated, under `deliveries/welfare-square-fresh-20260928/`. The dashboard
shows that JSON target, not autoWelfareSquare.html. All 773 tests passed (4 skipped).
The original config/status and new authorization are preserved under
`complete-delivery-amendment-001/` in the run directory; research was not restarted.
Persistent
research and curation supervisors own bounded recovery and preserve every attempt.
See [fresh-run record](docs/welfare-square-fresh-run-20260928.md).
After `prepared-delivery-ready`, verify the JSON/receipts, commit the registry and
scoped delivery, record the commit in pipeline status, then set
`prepared-delivery-complete` to enable its download. This last handoff remains the
supervising assistant's responsibility. No legacy HTML review gate applies.
The current Mesa authorization and Welfare Square pause above supersede continuation here.

## Repository consolidation and previous stop record

Updated 28 September 2026. The research, evaluation and application branches are
consolidated for main. 754 tests ran successfully (4 skipped); no Scout workers were launched.
This is the operational handoff; historical checkpoints
are in the [archived status](docs/archive/20260928/SCOUT_STATUS.md).
Read [orchestration](docs/scout-orchestration.md) before operating a worker and
verify live processes/database state before acting.

## Previous stop and policy preparation (superseded for the fresh run above)

Michael requested stopping Scout before adding rules and a fresh Welfare Square
run. All observed workers, child tools, monitors, and dashboard/preview servers
were terminated; the follow-up process check found none. No new run has started.
Stop receipt: `~/resource-scout-pairwise/data/scout-stop-20260928.json` (local, ignored by Git).

The separate Claude-checkout Housing experiment was interrupted. Preserve its
ledger; an in-flight request can have an unknown outcome. Do not replay or resume
it automatically. The stop applies to all historical continuation authorizations.
A later cleanup check saw the separate Claude run active again; its worker exited
before termination, its monitor was stopped, and a final check found no Scout
processes. The latest receipt is
`~/resource-scout-pairwise/data/repository-cleanup-20260928/final-stop.json`.
Two uncommitted Claude adapter/test edits appeared during integration; they remain
in that checkout and in `claude-concurrent-draft.patch` beside the receipt. They
are not part of the tested merge; inspect them before any future comparison run.

The [four office-fit rules](docs/office-fit-rules-20260928.md) are now present in
this checkout at `dfe6fb2`, including Michael's decision that phone and online
services count when available to the office's residents. They are Scout policy,
not an experimental option. Frozen evaluation prompts remain unchanged.
Before the fresh run, confirm any further rules Michael wants, the intended
workflow and its policy coverage; use a new run directory and preserve old work.
This cleanup does not authorize provider calls or another production launch.

## Current deliveries and acceptance

- **Mesa Housing DeepSeek trial:** complete, Housing-only. 104 leads yielded
  100 records: 92 usable reserves, 8 needs-resolution, 10 starters and 90
  considerations. DeepSeek/max performed curation and one sequential review.
  The merged tree holds [the prepared file](deliveries/mesa-housing-deepseek-20260928/prepared-resources.json),
  [evaluation](deliveries/mesa-housing-deepseek-20260928/evaluation.json),
  and [readable report](deliveries/mesa-housing-deepseek-20260928/review.html).
  Commit `362bb37` is pushed on `docs/scout-evaluation-design-20260927`.
  82 evaluation tests passed before cleanup; package validation and offline resume
  passed. No WSRS-TSO import, human approval, or agency confirmation is claimed.
  Active processing including original research: 376.35 minutes; billing unreconciled.
- **Full Mesa:** [delivery](deliveries/mesa-complete-20260927-r2/prepared-resources.json)
  exists, but broad missionary exposure remains **on hold** for relevance,
  duplication and granularity concerns. Structural checks do not establish
  practical usefulness. See [the acceptance hold](docs/mesa-reserve-relevance-reopened-20260927.md).
- **Other offices:** preserve existing research and outputs. Historical running,
  automatic continuation and queued-office notes are not current launch authority.
  Cedar City's discussion hold remains; do not start another St. George run.

The merged and Housing implementation identity registries contain 1,923 identities
and were synchronized at delivery. Keep stable IDs, aliases, human decisions and
source evidence intact. Do not replace either with an older registry.

## Workspace map

| Checkout | Branch | Purpose |
| --- | --- | --- |
| `~/resource-scout-pairwise` | `pairwise-research-experiment` | Integration checkout; current research evidence remains here |
| `~/resource-scout-pairwise/data/evaluations/implementation` | `docs/scout-evaluation-design-20260927` | Housing evaluation implementation and delivery; distinct Git worktree |
| `~/resource-scout-claude` | `claude-evaluation` | Separate interrupted comparison; do not resume automatically |
| `~/resource-scout` | `main` | Canonical application checkout; consolidated code |
| `~/resource-scout-v1` | detached | Historical checkout; preserved |

Verify `git worktree list` and branch status before any consolidation. Do not merge,
remove or relocate worktrees merely because they appear old. The nested implementation
checkout is inside ignored `data/`; its tracked work is merged but its local evidence
remains there. Existing runtime paths have not been relocated.

## Operating rules and historical evidence

Use the [documentation guide](docs/README.md) for the prepared-resource contract,
review instructions and delivery references. New prepared outputs use five Information
sections, explained starters and reserves; old HTML tiers and four-section instructions
are historical. AI review never sets human Curated status or an agency verification date.

New workers require explicit scope/provider authorization. The operational policy
uses Codex primary and DeepSeek only as challenger; a separate comparison is not
permission to change production providers. Jev is not part of the workflow.
Preserve sealed prompts, native responses, failed attempts and completed databases;
do not rerun old work just to obtain a clean status. The six-category architecture
review uses Extra High and its [evaluation checklist](docs/archive/20260928/SCOUT_STATUS.md#architecture-review-checklist-retained-for-follow-up).

Cleanup preserved exact prior README/status snapshots in `docs/archive/20260928/`.
Untracked Jev preparation was moved to the local ignored archive
`~/resource-scout-pairwise/data/repository-cleanup-20260928/`; its manifest records original paths and hashes.
The previously deleted proposal is preserved in the historical documentation archive;
its old active path remains removed. No research data, resource or delivery was deleted.

Repository consolidation and preservation details: [cleanup record](docs/repository-cleanup-20260928.md).
