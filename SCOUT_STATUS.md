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

## Claude+Grok adaptive challenger work

Last known important state:

- Addiction Claude primary work completed with 81 candidate identities/leads in the challenger exclusion set.
- A monolithic Grok challenger timed out at 30 minutes.
- Scout added adaptive challenger partitioning.
- The first broad `direct-service-landscape` Grok partition then timed out at 15 minutes.
- Scout now supports recursive partitioning.

Current recursive behavior:

- Oversized challenger assignments are proactively partitioned.
- A monolithic challenger timeout switches to partitioned mode instead of retrying the same giant prompt.
- Challenger partitions are persisted in SQLite and resumable.
- A timed-out partition is superseded by smaller child partitions rather than retried unchanged.
- Broad partitions split first by coverage pathway, then (if needed) by source channel, then by broad source ecosystem.
- Parent partitions remain as durable history but do not count as active leaves once children exist.
- Completed leaf partitions are merged and deduplicated before one logical challenger result is saved.
- The worker receives compact identity anchors; Scout retains responsibility for final duplicate removal.
- Browser monitor reports current leaf-partition progress.

Default adaptive thresholds:

- proactive candidate threshold: 36 identities
- proactive assignment-size threshold: 18,000 characters
- leaf partition timeout: 900 seconds
- Claude max turns: 60

Relevant events:
`challenger-partition-triggered`
`challenger-partitioning-started`
`challenger-partition-split`
`challenger-partition-started`
`challenger-partition-completed`

Resume Claude+Grok only after checking no older runner is still active:

```bash
ps -axo pid,etime,command | grep "pairwise_runner.*claude-grok" | grep -v grep
```

If no runner is active:

```bash
caffeinate -dimsu python3 -m resource_research_agent.pairwise_runner \
  --database data/pairwise-overnight-20260918-022703/claude-grok.sqlite3 \
  --import-id 1 \
  --profile claude-grok \
  --max-categories 6 \
  --skip-preflight
```

Monitor URLs when running:

- Codex+Claude: http://127.0.0.1:8767
- Claude+Grok: http://127.0.0.1:8768

Browser monitor processes are not research workers.

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
- Grok monolithic-challenger failure and recursive-partition recovery

Experimental fairness:

- Distinguish original Claude+Grok monolithic behavior from adaptive Claude+Grok behavior.
- Claude's earlier 24-turn failures were an artificial wrapper ceiling; current runs use 60 turns.
- Grok timeouts should be interpreted as task-shape/orchestration evidence, not automatically as model-quality failure.

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
- prefer the MLX path
- replay already-completed sealed Scout assignments
- compare useful finds, unique accepted resources, latency, RAM use, tool-calling reliability, and curator burden

## Safety / preservation rules

- Never restart a primary run merely because a handoff was opened.
- Never overwrite completed experiment databases.
- Preserve durable SQLite state and resume from it.
- Verify process state before launching duplicate workers.
- Prefer small reversible changes with tests.
- Run the full test suite / CI before using new orchestration code on the experiment.
