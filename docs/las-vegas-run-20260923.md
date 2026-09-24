# Las Vegas Valley research

## Authorized automatic phase transitions

Michael explicitly authorized starting curation after research and beginning the
review after curation, with xhigh review effort. This overrides earlier manual
start gates for Las Vegas only. `pipeline.json` preserves his authorization,
model/effort and limits; `pipeline-status.json` is the current phase. The persistent
`office_pipeline` process is identified in launch.json and logs to pipeline.log.

After all21 research categories are imported/complete and research coordinators
exit, the pipeline prepares the canonical curation job and starts the existing
curation supervisor. Curation uses gpt-5.5/High,30 candidates/60,000 characters per
batch and the compact prior-resource index. Original evidence remains complete.

After the curation supervisor reports verified completion, the pipeline checks the
canonical job again and starts a fresh Codex reviewer with an explicit
`model_reasoning_effort="xhigh"` override. This does not change the parent conversation
or global configuration. The review prompt requires the full content/navigation/
groups/priorities/readiness contract and actual browser/editor/filter/download
checks. Proposed Las Vegas workbench taxonomy remains distinct from human approval.

Review sessions retain sealed prompts, native events, final output and execution
timing under review/session-*. A durable STATUS.json/checkpoint controls continuation:
at most8 sessions of90 minutes each, only after new progress. Unknown exits, missing
checkpoints, stale progress or a session limit stop for diagnosis. No review is marked
complete merely because its process exits successfully. Missing browser tools leave
explicit needs-browser-verification status after non-UI review; they do not waive
the actual UI checks. The native final fingerprint must be recorded for completion.
Timing snapshots include curation and review sessions. macOS notifications are
requested at phase changes or stops; delivery and OS reboot recovery are not guaranteed.

## Required time accounting

Michael requested actual processing time separately from elapsed time. Research
workers already persist per-attempt runtimes. Refresh the derived snapshot with:

`python3 scripts/report-scout-timing.py data/las-vegas-production-20260923`

This writes `timing-summary.json`, counts failed attempts separately and avoids
counting DeepSeek's imported telemetry twice. Worker totals include provider/search
latency; overlapping workers add together. They are not GPU-compute measurements.
In-flight work and connectivity probes are excluded. Keep unknown durations visible.

When curation starts, supply `--curation-dir ACTUAL_OUTPUT_DIRECTORY` on every
report; preserve all execution and failure artifacts. For final review/corrections,
start each actively supervised work session with `--review-start DESCRIPTION`,
and close it with `--review-stop` before pausing or handing off. Resume with a new
session. If a session is left open, reconcile its true stop from evidence before
reporting; do not count unattended idle time as review. These flags only record
time and do not authorize or launch curation/review. No review session has begun.
Record delivery time in launch.json's `deliveredAt` to freeze elapsed time at delivery.

Refresh at category/phase checkpoints and before answering timing questions.

Michael authorized Las Vegas Valley, Codex High primary, and DeepSeek V4.1-Flash
challenger. His latest authorization enables the automatic transitions above.

Michael explicitly approved DeepSeek max: "Continue with max--that's fine."
Codex primary remains High.


Source: `/Users/michaelbendio/resource-assistant/las-vegas.html`, unchanged.
SHA256: `904b144f424abba85c9aee65588867e92e057404e56071bce2e4acc416c84dd5`.
The source has21 research categories, no resources and no For groups.
The imported service area covers Las Vegas, North Las Vegas, Henderson and
surrounding valley communities. Countywide/statewide/remote services qualify when
they serve valley residents; programs solely for outlying Clark County towns do not.

## Runtime and evidence

`data/las-vegas-production-20260923/launch.json` contains exact commands, source
hash, service area, authorization and PIDs. The canonical database is
`research.sqlite3`, import1. Monitor: http://127.0.0.1:8771.

Codex runs gpt-5.5 at High with `--primary-only`. Its legacy profile is codex-grok;
this mode makes no Grok calls. Sealed primary results and metrics persist in SQLite;
the existing primary transport does not preserve its complete native event stream.

The persistent `deepseek_challenger_runner` reads completed primary category packets,
retains the original seal, and researches through DeepSeek's Anthropic-compatible
endpoint using `deepseek-flash`, max effort, native web search and read-only public
page/PDF fetches. No Claude inference or OpenAI search relay is used.
The credential is read from the existing local configuration, never saved in evidence.

`deepseek-challenger/assignment-*` preserves baseline, original/replacement prompts,
requests, responses, tool results, usage, cost estimates and result checkpoints.
The primary coordinator now imports completed challenger results between passes
using `--challenger-output-dir`, under its existing canonical runner lock. The
challenger's own importer acquires that lock for remaining results after primary
research finishes. Audited provider replacements retain original assignments.
The monitor projects the bound DeepSeek manifest/checkpoints without changing
seals or declaring a category complete before database import. The original
whole-primary-run import delay was an orchestration defect, corrected after
Michael flagged the accumulating queue.

## Budget and supervision

Initial account balance was $6.48; the challenger has a $5 run allowance and
$0.25 account reserve. Conservative peak token estimates and request reservations
guard subsequent requests; they are not an exact invoice cap. Addiction's first
response saved11 leads with upper token cost $0.0405042. Category costs vary.

The challenger persists checkpoints and requests local notifications on terminal
failure/completion. Unknown in-flight requests and substantive failures stop for
diagnosis rather than replaying paid calls. Research completion pauses ready to
curate. The separately authorized office pipeline handles curation and review transitions.

The persistent research watchdog now observes both coordinator identities,
checkpoint ages and database completion every30 seconds. Its exact command/PID
is in launch.json; state is research-watchdog-status.json and issue history is
research-issues.jsonl. A separate lease prevents duplicate watchdogs.

It can recover schema-valid final JSON or a fully answered native-search-limit
response from saved evidence without new inference, then resume DeepSeek under
the unchanged spend/effort settings. Original failed states/responses are retained.
At most three automatic coordinator restarts are allowed across watchdog restarts.
The actual challenger lock prevents recovery while its worker is running.

Unknown in-flight requests, invalid findings, exhausted budget/authentication,
primary crashes and stale work require diagnosis; a local notification is requested.
The watchdog does not perform general AI diagnosis/code editing or blindly replay
uncertain paid calls. It keeps monitoring after flagging an issue. OS reboot recovery
and guaranteed notification delivery remain unimplemented. Human or assistant
diagnosis is still required for unfamiliar errors; a heartbeat is not progress.

## Validation

The live native-search probe and first real category succeeded. The monitor was
restarted independently, and Chrome visibly showed DeepSeek-V4.1-Flash.
Local suite:299 tests, one skipped, including six unrelated untracked Jev tests
which are excluded from this change. Regression checks cover lock-safe import,
seals, paid-call replay prevention, budget guards and the monitor projection.

## Native search limit recovery

Children/Pregnancy's first DeepSeek response returned all server-tool results,
including max_uses_exceeded errors, with stop_reason=tool_use and no client calls.
The original adapter rejected that combination. The tested fix accepts only fully
matched server search calls/results with an explicit limit error, checkpoints the
conversation once, then disables native search for that category while retaining
open_url and max effort. Unknown/unmatched tool stops still fail closed.

Original response, billing, failure and failed-state snapshot remain intact in
assignment-2/recovery-search-limit-001. Coordinator33105 resumed that evidence at
01:08UTC; it did not repeat initial discovery. The UI's saved-awaiting-import state
is distinct from failure: database handoff/import waits for the primary coordinator's
next checkpoint, or for the runner lock after primary research finishes.

## Checkpoint imports activated

The initial whole-run lock delayed all challenger imports unnecessarily. The new
primary coordinator imports finished challenger results between primary passes,
under the same exclusive lock; no concurrent writer bypass is used. Manifest binding,
lease ownership and import idempotence are tested. The saved results for Addiction,
Children/Pregnancy and Clothing/Household now show completed in the live monitor
API,3/21 overall. SQLite quick_check passes;301 local tests pass(1 skipped).

The one-time migration waited for the Disability non-obvious-primary-sources
worker's final output and terminal process before replacing the old coordinator.
`checkpoint-import-migration-003` retains the sealed pass, original worker result,
hash, process metadata and successful save record. That pass has one completion
telemetry row. Its192 seconds are terminal-process elapsed time rounded to seconds;
the old transport's native usage stream was unavailable. The new coordinator
PID34858 resumed with Disability's gap pass; no paid pass was repeated. Exact
updated command and PID are in launch.json. Original launch/migration failure logs
remain preserved. The later authorization above enables curation and review transitions.

## Domestic Violence parser correction and persistent supervision

The saved response contained interim progress text before native tool results and
a schema-valid final JSON answer afterward. The old parser joined both text blocks.
The correction selects only the final answer segment after native tool activity;
prose/conflicting output inside that final segment still fails validation. Seven
saved findings were recovered offline, preserving the complete original response,
failure and failed state in assignment-9/recovery-final-segment-001. No new Domestic
Violence inference was used; it is imported and complete (5/21 overall).

DeepSeek coordinator36061 resumed; watchdog36165 attached. The issue ledger also
records the previous search-limit and import-delay incidents with evidence paths.
Full local suite306 tests passes(1 skipped); targeted supervisor tests verify offline
recovery, original preservation, restart budgets, command/budget binding, no duplicate
live workers, and no replay of unknown requests. Live watchdog reports both workers
alive with no current issues. Six unrelated untracked Jev tests are part of the local
suite count and remain excluded from commits.
