# Scout Current Status

Read this file before doing Resource Scout work from a fresh Codex session.

## Working copy

- Repo: `~/resource-scout-pairwise`
- Branch: `pairwise-research-experiment`
- Experiment directory: `data/pairwise-overnight-20260918-022703`
- Do not overwrite or restart completed experiment databases.
- Before acting on a live run, inspect processes and database state rather than inferring from browser polling.

## Six-category experiment

Three pairwise conditions:

1. `codex-grok.sqlite3` — six-category condition completed.
2. `codex-claude.sqlite3` — six-category condition completed.
3. `claude-grok.sqlite3` — remaining/adaptive condition. Verify current process/database state before resuming.

The six experimental categories are the first six non-Miscellaneous St. George categories:
Addiction, Children/Pregnancy, Clothing/Household, Disability, Domestic Violence, Education.

Do not run category 7 or the full 21-category St. George production run until the six-category architecture review is complete.

## Authentication diagnosis and partitioning rollback: September 18, 2026

The Grok timeouts were authentication stalls. Native CLI logs showed repeated
HTTP 401 failures and inability to refresh credentials from the strict sandbox
(`auth.json.lock`: Operation not permitted). The affected earlier monolithic and
partition workers recorded zero completed inference events and zero completed
tool events. They provide no evidence that the assignment was oversized.

After `grok login` and a successful strict-sandbox preflight, an unchanged replay
of the original sealed Addiction challenger assignment completed in 232.309 seconds
(3m52s), with 6 turns and 15 parseable leads. These are submitted leads, not curated
or accepted unique resources. The parser preserved leading progress commentary.
The successful replay has been saved to original assignment 1 (telemetry row 4);
Addiction is now completed. All 15 historical partition rows remain unchanged.
A pre-recovery SQLite backup is retained beside the replay artifacts.

The native usage envelope reports no web-search counter; zero in Scout's current
summary must not be interpreted as proof that no searches occurred.

Replay evidence is stored separately in:
`data/monolithic-auth-replay-20260918-114447/`

- `assignment.txt` and `manifest.json`: exact assignment, original hash, timing
- `result.json`: original response and provider usage envelope
- `authentication-evidence.json`: sanitized counts from prior worker logs
- `database-sha256-before.json`: preservation fingerprints

Validation: the full local suite passed 193 tests (one skipped), and the guarded
Grok preflight succeeded against the real CLI.

Automatic and recursive challenger partitioning has been reverted. Provider
telemetry, Claude's 60-turn limit, and resume-safe six-category cap remain.
Existing SQLite partition rows are retained as historical evidence, but the runner
no longer uses or expands them. The original Git commits also preserve the removed
implementation. Reconsider partitioning only if future authenticated runs demonstrate
an actual need; this replay does not establish that partitioning could never help.

A narrow Grok execution guard now watches new native authentication-failure events
for its own child process. It stops on an authentication failure and records a failed
attempt without automatic retries. The strict research sandbox is unchanged.
Credential refresh remains unresolved inside that sandbox; use `grok login` when
needed. If native logs are unavailable or their format changes, detection can fall
back to the ordinary timeout. No timeout can trigger partitioning after the rollback.

Before resuming, check actual runners, not monitor processes:

```bash
ps -axo pid,etime,command | grep "pairwise_runner.*claude-grok" | grep -v grep
```

Only if no runner is active and the six-category condition is unfinished:

```bash
caffeinate -dimsu python3 -m resource_research_agent.pairwise_runner \
  --database data/pairwise-overnight-20260918-022703/claude-grok.sqlite3 \
  --import-id 1 \
  --profile claude-grok \
  --max-categories 6
```

Keep preflight enabled. Never rerun Claude's completed Addiction primary work or the
successful original challenger replay. Check the database for their saved status.

Monitor URLs when running:

- Codex+Claude: http://127.0.0.1:8767
- Claude+Grok: http://127.0.0.1:8768

## Telemetry

Scout now persists per-provider/per-attempt telemetry including:

- provider, role, profile, category, pass/assignment, model
- start/end times and elapsed time
- retries/failures
- response size and lead count
- native turn counts when exposed
- web-search/tool counts when exposed
- provider token/model usage when exposed
- Claude API duration/cost/terminal reason when exposed
- leads per active research minute summary

Codex runs use JSONL execution telemetry. Grok uses JSON headless telemetry. Claude retains its JSON envelope metrics.

## Six-category architecture review

When all three conditions are complete, perform this analysis at **Extra High reasoning effort**.

Do not merely rank the three fixed pairs. Evaluate whether Scout should use an adaptive architecture.

Analyze:

- research quality
- consequential pathway misses
- primary/challenger complementarity
- accepted unique resources
- marginal challenger contribution
- wall-clock time
- turns
- searches/tool calls
- retries and failures
- curator burden
- duplicates/noise
- category-specific differences
- accepted unique identities per active research minute
- marginal accepted identities per additional research minute
- Claude turn-limit behavior
- Grok authentication stalls, unnecessary partitioning, and successful monolithic replay

Experimental fairness:

- Distinguish original Claude+Grok, authentication-blocked adaptive attempts, and authenticated monolithic recovery. Preserve all elapsed downtime as operational cost, separately from active research time.
- Claude's earlier 24-turn failures were an artificial wrapper ceiling; current runs use 60 turns.
- The observed Grok timeouts were authentication-confounded, not evidence of task size or model-quality failure.

Explicitly evaluate architectures beyond the three fixed pairs, including:

**Codex primary + Scout-controlled adaptive challenger routing and task granularity**, where Scout may choose challenger and partition strategy according to category characteristics and observed worker performance.

Do not launch the 21-category St. George production run until this review is complete.

## Production queue after St. George

Queued Scout locations include:

- Cedar City
- Las Vegas
- Salt Lake

More locations are expected.

The goal after choosing the architecture is to run all 21 St. George categories, curate/consolidate the result, and generate a usable `autoStGeorge.html`.

## Local-model experiment

After stabilizing the six-category experiment, prepare PrismML Ternary Bonsai 2 27B as a **separate local worker experiment** on the 64 GB M4 Pro Mac mini.

Do not add Bonsai to the live six-category experiment.

Preferred path:

- use PrismML's official `Bonsai-demo` repo
- use the official llama.cpp/Metal server for the approved first pilot; the current Bonsai 2 MLX server explicitly refuses this model because it needs a special loader
- replay already-completed sealed Scout assignments
- compare useful finds, unique accepted resources, latency, RAM use, tool-calling reliability, and curator burden

### Separate installation (September 18)

The user approved an initial official llama.cpp/Metal pilot after reviewing the
MLX server limitation. Installation lives at `~/scout-bonsai-pilot/Bonsai-demo`,
independent of this worktree and all experiment databases. Demo revision:
`ab39c615b30a982faf296100d6d0224a772c8772`; binary release:
`prism-b10685-7dffb15`. Model: Bonsai 2 27B PQ2_0 with Q8 vision projector.
MLX, Open WebUI, and code interpreter extras were skipped.

`~/scout-bonsai-pilot/README.md` documents the pilot. The local API uses
`127.0.0.1:8089`, one slot, 65,536-token context, and a 2,048-token reasoning budget.
Native tool-call emission and consumption passed a synthetic round-trip test.
`start-server.sh` starts it; `server.pid` and the live process table establish whether
it is actually running. Do not start duplicate servers.

Two completed assignments were exported read-only with matching sealed hashes:
Addiction challenger from Claude+Grok and Clothing/Household challenger from
Codex+Grok. `pilot.py` and `runs/*/state.json` hold independent replay checkpoints.
This is a supervised Codex-session web-search/fetch relay, not unattended integration
or a fourth six-category condition. No search API credential is configured here.
The first two Clothing/Household search responses were overly large (`long` relay
setting); turn 2 used `short`, then search excerpts were mechanically capped at
eight results / 600 characters each and fetch text at 12,000 characters. All timing
and raw evidence are retained. Addiction used these bounds from its first call.
These exploratory measurements require a later standardized comparison before
making performance or architecture claims. Submitted leads are not accepted resources.

Bonsai Clothing/Household exploratory replay reached a confirmed context error
(69,789 requested tokens versus 65,536 configured) after 13 completed model turns,
21 search calls, and 5 fetch calls, with no final lead JSON. Completed model calls
took 1,726.96 seconds; sampled server RSS peaked at 12.82 GiB. Large initial tool
responses confound this result. A fresh Addiction replay uses bounded retrieval
from its first call but also failed to emit final JSON: six completed model turns,
21 searches, three fetches, and a seventh request timing out against the remaining
30-minute aggregate allowance (1,800.02 seconds including failure). Its peak sampled
server RSS was 17.63 GiB. All 50 emitted calls across both replays had valid names
and JSON arguments; useful-find quality and accepted-resource yield remain unmeasured.

`~/scout-bonsai-pilot/REPORT.md` records results and limitations. Keep Bonsai available
for narrower extraction/verification experiments; do not adopt it as a broad Scout
challenger on these results. Different tools, supervised relay, retrieval adjustments,
and concurrent host use prevent a clean model ranking. The local server was stopped
after testing to release memory. Both completed experiment database hashes were
verified unchanged; no Bonsai outputs were submitted to Scout.

## Safety / preservation rules

- Never restart a primary run merely because a handoff was opened.
- Never overwrite completed experiment databases.
- Preserve durable SQLite state and resume from it.
- Verify process state before launching duplicate workers.
- Prefer small reversible changes with tests.
- Run the full test suite / CI before using new orchestration code on the experiment.
