# Scout Current Status

Read this file and [orchestration instructions](docs/scout-orchestration.md)
before operating or supervising Scout. Verify live process/database state;
a monitor process is not a research worker.

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

## Latest effort decision — stop after Children/Pregnancy

Michael requests that the current Children/Pregnancy category finish at Extra
High, then curation **pause before another category**. Compare it with original
Addiction (High) and discuss effort before continuing. This supersedes the older
Mental Health/end-of-run comparison timing below. Preserve the original results
and distinguish category/source-pool differences, batching, prior context and
separate audit corrections from any effort benefit.

During validation, research completion must visibly prompt a curation-effort
discussion. Automatic research-to-curation transition is a future mode to enable
only after explicit agreement that Scout is ready to run unattended. The existing
review HTML download should be a prominent Save auto[Location].html action.

## Research complete — September 19, 2026

**All 21 categories completed at 08:32:58 UTC (2:32:58 a.m. Mountain).**
The research runner exited normally; no worker remains. Monitor PID 10078 was
still serving **http://127.0.0.1:8769** at verification. It reports research 21/21,
curation 0/21 and ready for Codex-controlled curation. A monitor is not a worker.

The Codex+Grok research jobs contain 1,613 submitted rows. The richer curation
selection, including preserved historical findings, contains 3,290 source rows
and 2,421 candidate records. These are not accepted unique resources. All source
databases retain their verified hashes; production SQLite integrity passed.

Frozen database, complete candidate ZIP and completion/checksum manifest:
`data/st-george-completion-20260919/`.
Read [completion report](docs/st-george-research-completion-20260919.md).
Curation job 1 started September 19 at 15:26 UTC (9:26 a.m. Mountain).
**Addiction completed: 196 candidates, 72 proposals, 76 merged-candidate
and 48 omitted-candidate dispositions.** The first worker used High and took
about 11 minutes. Its unchanged final result was validated and saved.

Michael explicitly requested **Extra High for the category workers too**.
The coordinator transitioned at the category boundary, preserving Addiction.
Current runner PID **30612**, Codex `gpt-5.5`, `--effort xhigh`,
`--batch-candidates 30 --batch-chars 60000 --max-categories 2`. Children/Pregnancy is running
in nine saved batches after the whole-category Extra High attempt exhausted
its context window at 263.73 seconds. The failed attempt is preserved under
`job-1/children-pregnancy/a33833317d3c23d0/`; bounded recovery uses parent
assignment `77ad03dcfbf51f0c...`. No completed research/category was rerun.
Verify live processes and logs; this snapshot will advance.
Monitor PID 31256 remains **http://127.0.0.1:8769**, curation 1/21 at restart.
The coordinator records batch progress as well as completed-category counts.

**Material Addiction audit correction applied:** remove Maryland's Washington
County harm-reduction program (candidate 594, `res-washco-harm-reduction`) and
restore Utah's Hand in Hand mobile service (candidate 468,
`res-hand-in-hand-stgeorge`) from Utah DHHS evidence. The count remains 72.
The SQLite `scout_curation_result_revisions` table preserves the original High
result plus sources, reason and before/after hashes. Original worker files are
unchanged. Audit artifacts: `data/st-george-curation-20260919/audit/`.
Children's failed assignment was archived and its prior-resource context was
explicitly refreshed to include the correction before bounded recovery.

After curation completes, Michael explicitly requests an effort comparison:
**Addiction (High) versus Mental Health (Extra High)**. Compare overlapping
providers, consolidation/omission decisions, direct category fit, Stephanie's
four information criteria, and latency/usage. Identify concrete added value;
do not attribute every difference to effort. Addiction has a richer historical
source union and Mental Health receives prior curated resources, so this is an
observational comparison, not a controlled same-assignment experiment. Extra High recovery also changes
batch size and evidence-reading guidance; the root audit corrections are a
separate intervention. Preserve
both inputs, outputs, web/tool events and effort metadata. Do not rerun Addiction
just to manufacture a matched comparison without discussing the extra work.

Working artifacts/log: `data/st-george-curation-20260919/`.
Completed category results are durable in the production working database.
The frozen research snapshot and all historical source databases remain unchanged.
No `autoStGeorge.html` has yet been generated from this run. The curation runner
will generate it after all 21 categories pass candidate-coverage/link validation.
Read [curation operations](docs/scout-curation-runner.md).
Do not restart completed research.

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

## Current state: September 18, 2026

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
