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

## Authorized next sequence and effort levels

Michael authorized the following sequence on September 18 after the Bonsai removal:
finish Claude+Grok's six-category condition; analyze all three conditions; revise
Scout's architecture and implementation as supported by the evidence; validate
changes with required tests/CI; then start the full 21-category St. George run.
No additional routine launch approval is needed once those prerequisites pass.
Preserve the experiment databases and do not conflate raw lead counts with curated
accepted identities. Production must use separate durable state.

Requested effort: High for remaining experiment supervision; Extra High for the
architecture analysis and consequential design review; High for routine production
execution. Worker reasoning settings are separate from the supervising chat's
setting; do not change ongoing experimental worker settings to match the chat.
The assistant has no exposed tool to switch this conversation's reasoning effort.
Michael must select Extra High in the conversation before that analysis begins;
editing CLI defaults does not establish that the active chat has changed effort.
No automatic chat effort switching or post-completion wake-up has been configured.

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

## Bonsai experiment closed; extraction deferred

On September 18, Michael directed removal of Bonsai after reviewing its research
and extraction results. The separate `~/scout-bonsai-pilot` installation, model
weights, virtual environment, test files, and model-specific Hugging Face cache
were removed. No Bonsai server remains running. Do not reinstall or resume this
experiment unless Michael requests it.

Historical outcome: neither broad research replay produced a final lead list.
A constrained extraction using Stephanie's four criteria produced JSON in 70
seconds, but geographic and eligibility interpretation errors required review.
The demonstrated benefit did not justify further integration effort. Earlier Git
history retains the operational summaries; the local pilot artifacts are deleted.
No Bonsai output was submitted to an experiment database. Both completed condition
database fingerprints were verified unchanged before removal.

**Structured text extraction is deferred to the distant backlog, with no near-term
work planned.** Do not start implementation, additional tests, or replacement-model
experiments for it. Current priorities remain the six-category experiment and the
required architecture review before any 21-category production run.

Stephanie's criteria, as clarified by Michael, are **Eligibility requirements;
How to best connect; Access (hours, etc); Important information to know.** The
existing production enrichment headings have not been changed in this work.

## Safety / preservation rules

- Never restart a primary run merely because a handoff was opened.
- Never overwrite completed experiment databases.
- Preserve durable SQLite state and resume from it.
- Verify process state before launching duplicate workers.
- Prefer small reversible changes with tests.
- Run the full test suite / CI before using new orchestration code on the experiment.
