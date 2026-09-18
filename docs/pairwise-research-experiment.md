# Pairwise Research Experiment

This branch adds opt-in pairwise researcher profiles without changing the baseline
researcher roster on `main`.

## Profiles

The API accepts a named `profile` when preparing Codex-first research:

- `codex-grok`: Codex primary, Grok challenger.
- `codex-claude`: Codex primary, Claude challenger.
- `claude-grok`: Claude primary, Grok challenger.

ChatGPT and Perplexity are disabled in all three profiles. The ordinary baseline
roster remains available when no profile is supplied.

Example:

```json
POST /api/codex-first-research
{
  "importId": 1,
  "profile": "codex-grok"
}
```

A request may supply either `profile` or an explicit `roster`, but not both.

## Research shape

The configured primary researcher performs the existing versioned focused passes
and deterministic coverage-gap pass. The challenger then receives the combined
identity exclusion list and performs the existing adversarial challenger pass.

The pairwise experiment deliberately keeps the existing storage schema and
candidate/consolidation pipeline so differences are attributable to researcher
configuration rather than a simultaneous data-model rewrite.

## Controlled comparison

Preserve the current St. George run as the baseline. Select 6–8 diverse
categories and rerun each from the same package baseline with:

1. current baseline roster,
2. `codex-grok`,
3. `codex-claude`,
4. `claude-grok`.

Do not merge results across conditions before scoring them.

For each category and condition record:

- accepted identities recovered from the baseline curated union,
- new accepted identities absent from the baseline,
- consequential service pathways missed,
- rejected/noise identities,
- duplicate identities,
- source/ecosystem diversity,
- source responses and submitted leads,
- curator decisions/time,
- assignment issue time,
- first-response time,
- completed-result time,
- category wall-clock completion time.

Primary summary metrics:

- curated-union recall,
- consequential-pathway miss count,
- accepted unique additions,
- accepted identities per wall-clock minute,
- incremental accepted identities per additional research minute,
- curator minutes per accepted identity.

The proposed replacement gate is approximately 95% recall of the curated union
with no consequential pathway misses, together with a material wall-clock or
operational improvement. Treat that as an experimental gate, not a permanent
product rule.

## Isolation

Run this experiment from a separate worktree checked out to
`pairwise-research-experiment`. Do not point the currently running Scout
process at that worktree or its configuration until the baseline run has reached
the chosen clean stopping boundary and its database/checkpoint has been copied.


## Running the Codex + Grok sample

With the pairwise Scout server running on port 8766 and the St. George package
imported as import 1, run the Codex primary passes from a second terminal:

```bash
cd ~/resource-scout-pairwise
git pull --ff-only
python3 -m resource_research_agent.pairwise_runner \
  --database data/research-agent.sqlite3 \
  --import-id 1 \
  --profile codex-grok \
  --max-categories 6
```

The runner uses one ephemeral Codex context per pass, with live web search and the
same response schema as the existing Codex replay runner. The Scout browser can
remain open at `http://127.0.0.1:8766`; its polling view will reflect database
progress while the runner works.

After each primary category reaches its gap pass, the runner prepares the Grok
challenger assignment. At the end it writes all pending Grok assignments plus a
manifest to `data/pairwise-challenges/`.


## Lock-step Grok handoff

Pairwise profiles now gate the primary researcher at the end of each category.
For `codex-grok`, Codex cannot begin the next category until Grok's challenger
result for the current category has been saved.

Read the pending Grok assignment, copy it to the macOS clipboard, and open the
Grok app:

```bash
python3 -m resource_research_agent.pairwise_challenge \
  --database data/codex-grok.sqlite3 \
  --import-id 1 \
  next --researcher Grok --copy --open-app
```

After Grok returns the required JSON, copy the JSON response and submit it
directly from the clipboard using the assignment ID printed by the previous
command:

```bash
python3 -m resource_research_agent.pairwise_challenge \
  --database data/codex-grok.sqlite3 \
  --import-id 1 \
  submit-clipboard ASSIGNMENT_ID
```

Then rerun the Codex primary runner. It will close that category and move to the
next one. This keeps Codex and Grok in lock-step and prevents Codex from running
ahead of the challenger.


## Fully automated Grok CLI mode

The pairwise runner can now execute Grok directly through xAI's official Grok CLI.
This avoids browser automation and the manual clipboard handoff.

Install the CLI on macOS if it is not already present:

```bash
curl -fsSL https://x.ai/cli/install.sh | bash
```

Authenticate once in an interactive terminal:

```bash
grok login
```

The CLI stores refreshable browser-login credentials. Scout performs a tiny
`GROK_READY` preflight before starting any Codex work so authentication failures
surface immediately rather than during an unattended run.

For a clean Codex + Grok experiment, use a fresh database and start Scout on the
pairwise port:

```bash
python3 -m resource_research_agent \
  --database data/codex-grok.sqlite3 \
  serve --port 8766
```

Import the St. George package, then run:

```bash
python3 -m resource_research_agent.pairwise_runner \
  --database data/codex-grok.sqlite3 \
  --import-id 1 \
  --profile codex-grok \
  --max-categories 6
```

The runner is lock-step and unattended:

1. run one fresh-context Codex pass;
2. continue until the current category's Codex gap pass closes;
3. create the Grok challenger assignment;
4. run a fresh headless Grok CLI session in a strict temporary sandbox;
5. validate and save Grok's JSON result;
6. close the category;
7. continue to the next category.

Each worker has independent retry handling. The Grok runner uses the CLI's current
default model unless `--grok-model` is supplied. Use `grok models` to inspect
models available to the authenticated account before overriding it.


## Three-condition overnight supervisor

The supervisor runs all three controlled conditions concurrently from the same
immutable import snapshot:

- `codex-grok`
- `codex-claude`
- `claude-grok`

Each condition gets its own fresh SQLite database. Only the import snapshot
(`imports`, categories, imported resources, known terms, and research seeds) is
cloned. Research runs, assignments, contributions, and curation state are not
copied between conditions.

Claude Code must be installed and authenticated before starting. Claude's
non-interactive print mode is used with JSON output and web-search/web-fetch
tools. The supervisor performs live Grok and Claude readiness probes before
creating the experiment databases.

To start the six-category overnight comparison:

```bash
cd ~/resource-scout-pairwise
git pull --ff-only
bash scripts/run-three-way-overnight.sh
```

The launcher wraps the supervisor in macOS `caffeinate -dimsu` so the Mac stays
awake while any of the three conditions is running.

A timestamped directory under `data/pairwise-overnight-*/` contains:

- one SQLite database per condition,
- one line-oriented log per condition,
- `manifest.json` with the common experiment setup, and
- `summary.json` with completion status, elapsed time, and lead counts.

The supervisor staggers condition starts slightly and each worker uses
retry/backoff handling to reduce the impact of transient provider rate limits.


## Browser monitoring

The three-way launcher now starts one Scout monitor server per condition and opens
all three pages automatically:

- http://127.0.0.1:8766 — Codex + Grok
- http://127.0.0.1:8767 — Codex + Claude
- http://127.0.0.1:8768 — Claude + Grok

Each page reads only its condition's SQLite database. The monitor servers are
separate from the research worker processes, so refreshing or leaving the tabs
open does not alter the experimental condition.

The supervisor refuses to start if any monitor port is already occupied. Monitor
PIDs, URLs, and server log paths are saved in the experiment `manifest.json`.
The monitor servers are intentionally left running after the experiment finishes
so the final state remains inspectable in the browser the next morning.


## Worker telemetry

Future pairwise and production runs persist one telemetry row per provider attempt
in `research_worker_telemetry`. The runner records:

- provider, role, profile, category, pass or challenger assignment, and model;
- attempt number, success/failure, start/end timestamps, and elapsed milliseconds;
- response size and parsed lead count;
- retries and failure text;
- native provider usage metadata when exposed by the CLI.

Codex runs use `codex exec --json` so Scout can retain Codex turn events, token
usage, completed item counts, and web-search item counts while still writing the
schema-constrained final response to the normal result file.

Grok headless runs use `--output-format json` so Scout can retain Grok
`num_turns`, token usage, model usage, session/request ids, stop reason, and
web-search counts when present.

Claude headless runs retain the existing JSON envelope fields including
`num_turns`, API duration, model usage, reported cost, stop/terminal reasons,
and web-search counts.

`codex_first_view` exposes an aggregate telemetry summary with attempts,
failures, active research minutes, turns, web searches, leads, and leads per
active research minute.

For the final architecture decision, telemetry should be combined with curation
provenance. The most useful efficiency metrics are accepted unique identities
per provider, accepted unique identities per active research minute, and
consequential-pathway misses—not raw lead count alone.

## September 18 authentication correction

The original sealed Claude+Grok Addiction challenger completed after reauthentication
in 232.309 seconds (6 turns, 15 parseable leads). Previous monolithic and partition
timeouts had recorded authentication failures without completed model responses.
Automatic and recursive partitioning was therefore reverted; historical database
rows and replay artifacts remain intact. See `SCOUT_STATUS.md` for the evidence.

Grok workers now stop promptly on native authentication-failure events for their own
PID, without automatic research retries. Run `grok login` and resume with preflight
enabled. Strict research isolation remains enabled; the guard does not repair
credential refresh inside the sandbox. Missing or changed native logs can leave the
ordinary worker timeout as the fallback. Separate authentication downtime from active
research when comparing conditions, and do not equate submitted leads with accepted
unique resources.
