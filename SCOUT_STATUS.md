# Scout Current Status

Read this file and [orchestration instructions](docs/scout-orchestration.md)
before operating or supervising Scout. Verify live process/database state;
a monitor process is not a research worker.

## AND group matching and explicit group checks — September 20

The workbench now defaults to **Match all selected groups (AND)**, with **Match
any** available. All **12 Deaf & hard of hearing** and **13 Blind & low vision**
resources also have People with disabilities. Fourteen distinct records needed
that broader assignment; its total increased from **133 to 147**. All 879 resources,
21 Categories, 25 group labels, facts and original research remain preserved.

Two local checks are implemented in Resource Assistant and Scout's generated HTML:
approved sensory-disability parent tags, and an explicit editor group-review
confirmation (including an explicit no-specific-group decision). Definitions appear
beside checkboxes. Relevant edits and changed group catalogs invalidate the review;
imports/merges flag missing or outdated reviews. Scout's Curated and package export
require a current review. This calls no AI and does not establish semantic completeness
or human eligibility. All 879 source records remain unreviewed by a human.

Read the [delivery review](docs/st-george-and-groups-review-20260920.md) and
[evidence](docs/st-george-and-groups-evidence-20260920.json). The active prevention
instructions remain [workbench readiness](docs/scout-workbench-readiness.md).

**Save autoStGeorge.html is enabled at http://127.0.0.1:8769.** Download a fresh
copy; an older HTML does not update itself. Master:
`data/st-george-curation-20260919/autoStGeorge.html`. Audit, prior SQLite/HTML backup,
14-record correction list, browser checks and download receipt:
`data/st-george-curation-20260919/audit/group-checks-20260920/`.

Review recorded **2026-09-20 16:25:46 UTC**, contract v2, fingerprint:
`080bd9563ba0522bba750855e0f227b95aa28cfeb0e3f3d16c2b254586a553d0`.
Navigation revision 2 SHA-256:
`b7352942b6f8f7e2d38ad45ee3c2bbb4e4facbafbdf82c10ea54f34b811f7636`.

Scout's full suite passed: 261 tests, one optional skip. The monitor-only process
is **PID 53076**, port **8769**. No research/curation worker or supervisor was
launched. Verify liveness before acting. Earlier review fingerprints and monitor
PIDs below are historical and are superseded by this delivery.

## Workbench omissions corrected and prevention added — September 20

Michael identified three delivery omissions after the content review: no For
groups, no Category Types, and Information rendered as inline topic labels. He
requested a St. George-specific group proposal and confirmed that he had only
inspected the earlier HTML, with no edits or human Curated selections.

The corrected workbench contains **879 resources**, Types in **all 21 Categories**,
and **25 proposed For groups** derived from these records. **674 resources** have
population labels; **205** have recorded no-group decisions. Every Information
field now has Stephanie's four bold headings, with supported hours/availability
under Access. The source facts, 2,421 candidate decisions, sealed assignments and
historical research databases are preserved. No paid worker was launched.

Read the [completion and prevention report](docs/st-george-workbench-readiness-review-20260920.md)
for the group list, Category Types, validation, classification limits and remaining
source uncertainties. This is a proposed finding-aid taxonomy for human vetting,
not human approval of resources or a published office taxonomy.

**Save autoStGeorge.html is enabled at http://127.0.0.1:8769.** The new file replaces
the older download, which does not update itself. Master file:
`data/st-george-curation-20260919/autoStGeorge.html`. Audit/backup and all assignment
excerpts: `data/st-george-curation-20260919/audit/navigation-20260920/`; Information
before/after evidence is in the sibling `information-format-20260920/` directory.
The actual download matches the inspected resource seed and artifact ID.

Current contract-v2 review recorded at **2026-09-20 13:50:22 UTC** for fingerprint:
`fc38acb44b43e653216154f2409c3aa068bc2e161c778a89dc81eb9e173eac1b`.
Navigation proposal SHA-256:
`c0b7b875952edcb60b567e81b2569f7fa69f6d234332fe0638c338de94933466`.

Scout now blocks review completion for missing Information sections, Type coverage,
or navigation review decisions. Navigation changes also invalidate prior approval.
The monitor describes outstanding requirements. `AGENTS.md` now requires the
[workbench readiness checklist](docs/scout-workbench-readiness.md), including actual
reader/editor and Type/For-filter inspection. Structural checks do not establish
semantic correctness; the separate requested Codex review remains necessary.

Monitor-only restart: PID **50733**, serving port **8769** with the new code. No
research/curation worker or supervisor was active at verification. Check processes
before acting; do not restart completed work. The earlier review snapshot below
is historical and superseded for delivery readiness by this correction.

## Earlier resource-content review — September 20 (delivery assessment superseded)

All **21 categories** completed curation at September 20, 07:03:46 UTC. Michael
requested the separate Extra High review; it is now complete and recorded for the
exact revised results at **12:59:55 UTC**. Read the
[review report](docs/st-george-curation-review-20260920.md) and
[evidence summary](docs/st-george-curation-review-evidence-20260920.json).

The reviewed workbench contains **879 consolidated resource records** and retains
all **2,421 candidate decisions**. The review corrected a Minnesota/Utah library
source mix-up, overstated treatment scope, lost shared-resource access routes,
two duplicate identities, an omitted local housing counselor, and a source-date
uncertainty. Eighteen category results have versioned revisions; original worker
outputs and sealed assignments remain preserved. All historical source databases
and the frozen completed-research snapshot retain their original hashes.

**Save autoStGeorge.html is enabled at http://127.0.0.1:8769.** The download endpoint
returns the same resource seed and artifact ID as the inspected HTML. The local
reviewed file is `data/st-george-curation-20260919/autoStGeorge.html`; audit evidence
and the pre-review SQLite backup are in
`data/st-george-curation-20260919/audit/final-review-20260920/`.

Reviewed fingerprint:
`e5e014245310e23001079d365f21233a82b55427321a37f6a09131b7bbe67568`.

Next step is Michael's human vetting in the workbench. No human Curated flags were
set, no phone verification or office publication was claimed, and no new worker
was launched. At review time no research/curation worker or supervisor was active;
the monitor remained running. Do not resume completed jobs. Earlier running
snapshots and launch manifests below are historical, not current liveness evidence.
Any later substantive result correction needs another fingerprint-bound review.

## Discovery and maintenance proposal — September 19 evening

Michael requested a clean-sheet design for new-office discovery and maintenance
of existing resource packages. The [proposal](docs/scout-discovery-and-maintenance-proposal-20260920.md)
uses one evidence and human-review process, Stephanie's four information headings,
separate complementary-search and verification responsibilities, and safe old/new
maintenance proposals. It recommends testing same-model roles with optional provider
diversity, not assuming the recent two-category pilot proves replacement equivalence.
This is a proposal for discussion; it does not change the running architecture,
worker effort, final-review gate, or authorize new worker experiments.

Live snapshot at September 20, 04:22 UTC: supervisor **39227** and coordinator
**39230** remain active. SQLite records **13/21 categories completed**; Housing
finished 85 candidates into 70 proposals at 04:21:41 UTC, and ID Recovery batch
**1/2** started at High. Monitor: **http://127.0.0.1:8769**. Verify live state;
earlier counts and worker PIDs below are historical snapshots.

## Agreed ongoing review handoff

Scout finishes curation and shows **Ready for Codex review**. Michael starts a
Codex session and requests the review; the reviewing assistant uses Extra High,
checks sources/omissions/identities and final consolidation, makes traceable
corrections, records completion for the exact results, and tells Michael. Only
then does **Save auto[Location].html** become available. Do not automatically
launch a separate paid reviewer. This replaces the proposed automatic AI review
stage as the current operating plan; a future unattended reviewer remains a
possible improvement to evaluate separately. Human approval/phone verification
are still separate from Codex review.

## Separate Codex complementary-assignment pilot — September 19 evening

Michael authorized testing a differently scoped second assignment to the same
model as an alternative to a different-model challenger. A bounded pilot reuses
the sealed Codex primary for Addiction and Education from `codex-grok.sqlite3`.
Two fresh Codex `gpt-5.5` High calls, maximum 900 seconds and 20 leads each, no
automatic retries. This authorization supersedes older no-new-replay wording
only for this isolated pilot. No Claude calls, production imports or research reruns.

Plan and interpretation: [pilot review](docs/codex-followup-pilot-20260920.md).
Evidence: `data/codex-followup-pilot-20260920/`. Both calls finished successfully
at September 20, 02:14:50 UTC: 31 raw rows in 6.50 worker minutes, screened as 23
supported additional leads (not accepted/publishable resources), versus 27 in the
saved Grok comparison. Six supported identities overlap. Codex recovered
EnglishConnect/BYU-Pathway but missed Family Healthcare MAT and returned four
wrong-jurisdiction library entries plus outdated Pathway eligibility details.
Pilot runner 40046 has finished; do not relaunch research. Saved results are
reusable without another paid call. Historical comparison changes model and
prompt together and is not a holdout. No production architecture switch is justified
yet; see the report's task-diversity and independent-verification recommendations.

Production curation continues independently under supervisor 39227/coordinator
39230. At September 20, 02:20 UTC, Education completed all nine batches:
255 candidates, 135 resource proposals. Six categories are complete; Employment
batch 1/2 started automatically at High. The saved batch-3 repair was reused;
completed Education did not need another research run.
Monitor remains **http://127.0.0.1:8769**. These are snapshots; verify live state.

## Education validation stop and recovery — September 19 evening

Five categories are completed: Addiction, Children/Pregnancy, Clothing/Household,
Disability and Domestic Violence. Education stopped at batch 3 of 9 on September
19, 19:58 UTC (1:58 p.m. Mountain): candidate 1648 had a valid SUU tutoring record
plus a stray row literally named "Duplicate placeholder remove". The native worker
finished normally; exact-link validation stopped curation. No authentication or
usage failure was observed. The original supervisor stopped as `needs-attention`.

The supervising assistant removed only that placeholder in a hash-bound reviewed
repair. All 30 decisions and the real tutoring entry remain unchanged. Education
batches 1 and 2 and all five completed categories are preserved. Audit:
`data/st-george-curation-20260919/audit/education-batch3-placeholder-repair.json`.
No additional worker call was used to repair this result.

Michael asked to fix the worker workflow. Future validation failures now receive
one bounded structural correction attempt at High, with web research disabled;
code rejects factual changes, changed decisions or substantive resource removal.
Saved corrections survive restarts, and failed corrections do not repeat. See the
latest section of `docs/scout-orchestration.md`. This is not the final Codex review.

Curation resumed at September 20, 01:45 UTC (September 19, 7:45 p.m. Mountain).
Supervisor PID **39227**, coordinator **39230**, and Education batch-4 worker
**39237** were verified alive. Education batches 1–3 are validated; batch 4 of 9
is running at High. All five completed category result hashes remain unchanged.
The persistent supervisor retained its existing recovery counter (2 of 3 launches
used). Verify the current `supervisor-status.json`, actual processes and SQLite
state; these and the older PIDs below are handoff snapshots. The monitor stays
at **http://127.0.0.1:8769**. Finish at **Ready for Codex review**.

## Curation resumed at High — September 19, 17:28 UTC

Michael read the comparison, selected High and explicitly instructed: "Continue
curation." The effort gate is satisfied. Original coordinator PID 32965 resumed job 1 with
`--effort high --batch-candidates 30 --batch-chars 60000 --max-categories 21`.
Addiction and Children/Pregnancy are preserved; the remaining 19 categories are
authorized. Verify actual processes/database progress before acting. Monitor:
**http://127.0.0.1:8769**. No automatic final reviewer is authorized; finish at
**Ready for Codex review**. Conversation effort and worker effort remain separate.

Persistent supervisor PID **33716** now monitors the run every 30 seconds. It
launched replacement coordinator **33718** to load tested recovery/readable
evidence changes; the existing batch-3 worker **33369** was adopted intact, with
no duplicate paid call. The two already validated Clothing/Household batches were
reused. Check `data/st-george-curation-20260919/supervisor-status.json` for live
state; these PIDs are a handoff snapshot. The durable coordinator recovery budget
is three launches, one used for this transition. A confirmed transport failure
allows one additional attempt per batch. Other failure classes stop for diagnosis,
with a monitor message and a requested local macOS notification. This remains a
limited supervisor, not a claim that all unattended operation requirements are met.


## Historical effort checkpoint — Children/Pregnancy

**At the comparison checkpoint, curation paused at 2/21 categories.**
Children/Pregnancy completed September 19 at 17:08:07 UTC (11:08 a.m. Mountain).
The coordinator enforced `--max-categories 2` and exited normally. Latest runner
PID 31492 is historical; monitor PID 31256 serves **http://127.0.0.1:8769**.
The monitor says `curation-awaiting-effort-review`. Verify live state before acting.

Michael requested the pause to compare Children/Pregnancy (Extra High) with
Addiction (High) and discuss effort before another category. The offered earlier
batch checkpoint received no answer; the original category-end instruction was
followed. **That discussion is now complete; High resumption is authorized above.**

Read [effort comparison](docs/curation-effort-review-20260919.md) and
[evidence](docs/curation-effort-results-20260919.json). Recommendation: **High for
remaining curation workers with bounded batches; Extra High for Michael's requested
Codex review after curation.** Michael subsequently approved High and resumption; see the current state above.
The old plan to compare Addiction with Mental Health after all categories is
superseded by this completed Children/Pregnancy checkpoint comparison.

- Addiction: High, 196 candidates, 72 proposals, about 11.5 worker minutes;
  dispositions 72 curated / 76 merged / 48 omitted.
- Children/Pregnancy: Extra High, 264 candidates, 136 proposals, 73 successful
  worker minutes plus 4.4 minutes for the failed whole-category attempt;
  dispositions 134 curated / 106 merged / 24 omitted. Nine batches are validated.
- Native successful-work input/output tokens: High 399,417 / 35,655;
  Extra High 4,691,586 / 216,688. These are not dollar or quota figures.
- At the checkpoint, Clothing/Household and the other 18 categories were pending.

The comparison is observational: both categories have the same four historical
research sources and identical source-audit text, but different candidate pools,
prior context, task breadth, batching and evidence-reading guidance. Original
worker results remain unchanged; root review corrections are separate.

The first whole-category Extra High attempt exhausted context. Completed bounded
work uses parent assignment `77ad03dcfbf51f0c...`. Batch 4 contained one fully
identical duplicate Root for Kids Early Head Start row. Scout preserved the raw
output and recorded exact-row normalization, then resumed without a worker rerun.
Conflicting same-ID records still fail. See `result-normalization.json` beside that
batch's original `result.json`. The failure remains visible in the experiment.

The comparison identified shared-title narrowing, incomplete incorporation of
financial-access details, category-fit consistency questions and a source-version
uncertainty. These are flagged in the report for review, not silently treated as
corrected or human approved. Future worker prompts now explicitly require actual
fact/link incorporation when merging access information and broad shared titles.
These instruction changes were made after Children/Pregnancy completed.

**Earlier Addiction audit correction applied:** Maryland's Washington County
harm-reduction program (candidate 594) was removed and Utah's Hand in Hand mobile
service (candidate 468) restored from Utah DHHS evidence. The count remains 72.
`scout_curation_result_revisions` preserves original/revised results, sources,
reason and hashes. Children received the corrected prior-resource context.

Artifacts and logs: `data/st-george-curation-20260919/`.
`launch.json` is historical execution evidence, not proof a process is still alive.
The comparison/preservation records are in its `audit/` subdirectory. No final
`autoStGeorge.html` has been generated from this incomplete curation job. After
all 21 categories finish, the monitor must hand off **Ready for Codex review**;
Save is withheld until the requested review is complete for the exact results.

## Research complete — September 19, 2026

All 21 categories completed at 08:32:58 UTC (2:32:58 a.m. Mountain). No research
worker remains. The Codex+Grok jobs contain 1,613 submitted rows. The richer curation
selection contains 3,290 source rows and 2,421 candidate records; these are not
accepted unique resources. All four historical database hashes and the frozen
snapshot remain unchanged. At the effort checkpoint, all 36 non-curation tables
in the working database matched the frozen snapshot; SQLite quick_check passed.

Frozen database, candidate ZIP and completion/checksum manifest:
`data/st-george-completion-20260919/`.
Read [research completion report](docs/st-george-research-completion-20260919.md)
and [curation operations](docs/scout-curation-runner.md). Do not restart completed
research or completed categories.

The run had one expired-token Grok authentication failure at September 18,
23:51 UTC. OAuth sign-in refreshed outside the strict sandbox and the run resumed
at September 19, 05:03 UTC. No further failures were recorded. Completed work was
reused; no Claude work was performed. Recovery history remains in `launch.json`
and `runner.log` beside the production database.

## Newly authorized reliability deliverable

Michael explicitly authorizes the work needed to make Scout routinely usable
from its shell script without an active supervising conversation. Continue the
current curation and final audit/comparison while implementing and testing
persistent supervision, durable recovery, bounded retries and actionable
account/usage alerts. Do not call it unattended-ready until interruption and
recovery paths have been tested. A model worker running in the background is
not by itself a supervisor. See `docs/scout-orchestration.md`.

## Binding instructions

- Work in `~/resource-scout-pairwise`, branch `pairwise-research-experiment`.
- **Claude is disabled for all Scout work, including preflights and probes.**
  Michael reported more than $125 in unexpected Anthropic charges. Do not
  re-enable it without his explicit new instruction. Reading saved Claude
  responses is allowed; assigning it new work is not.
- Preserve the three completed experiment databases and the earlier five-worker
  baseline. Never rerun their completed categories or replace those databases.
- Michael explicitly authorized the 21-category production launch after the
  completed Extra High review. The run is now complete. Do not restart completed research. Codex CLI workers
  used High; Claude remains prohibited for any next-stage work.
- Bonsai was removed at Michael's request. Structured extraction is deferred,
  not a current or near-term task.

## Completed six-category experiment: September 18, 2026

All three conditions in `data/pairwise-overnight-20260918-022703/` completed their
six categories: Addiction, Children/Pregnancy, Clothing/Household, Disability,
Domestic Violence, Education. The final Claude+Grok research worker exited after
Education; no seventh experimental category ran. The separate production run has now completed all 21 categories.

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

## Completed production workspace

Database: `data/st-george-production-20260918-codex-grok/research.sqlite3`
Manifest: adjacent `research.preparation.json` records the pre-launch preparation
snapshot. The newer `launch.json` records execution/recovery and completion.
Read the [launch handoff](docs/st-george-production-handoff-20260918.md).

Verified preparation:

- All six completed Codex+Grok jobs, passes and assignments preserved unchanged.
- 2,150 source rows retained in six separate curation-union runs from the three
  pairs and the earlier five-worker run, including Claude shadow evidence.
- All eight completed Employment primary passes were reused (37 leads); its
  Grok challenger and the category are now completed.
- Two completed Financial Assistance primary passes were reused (11 leads).
  All remaining passes and categories have now finished.
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

Production research is complete; there is nothing to resume. Preserve the
completed evidence and use the curation workflow for the next stage. Never call
Claude as a fallback or launch another locale without a new instruction.

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
