# St. George production launch handoff

**Research completed September 19, 2026, at 08:32:58 UTC (2:32:58 a.m. Mountain).**
All 21 categories finished and the worker exited normally. Monitor:
**http://127.0.0.1:8769**. See the
[completion report](st-george-research-completion-20260919.md) and frozen artifacts
in `data/st-george-completion-20260919/`.

The commands below are retained as execution history, not instructions to rerun
completed research. Next stage is consolidation/curation. Claude remains disabled.

## Workspace and preserved work

- Repository: `~/resource-scout-pairwise`
- Branch: `pairwise-research-experiment`
- Database: `data/st-george-production-20260918-codex-grok/research.sqlite3`
- Manifest: adjacent `research.preparation.json`
- Import: 1; total scope: 21 categories, six already complete.
- [Architecture review](six-category-architecture-review-20260918.md)
- [Five-worker comparison](five-worker-versus-codex-grok-20260918.md)

The six completed Codex+Grok jobs/passes/assignments are unchanged. Separate
curation-union runs retain 2,150 submitted rows from all three pairwise conditions
and the original five-worker run, including its 102 Claude shadow rows. These are
source submissions, not accepted unique resources. The curation selector uses the
richer union; the research monitor describes the preserved category jobs.

Completed work beyond six is also reused: eight Employment primary passes
(37 leads), including its gap pass, and two Financial Assistance primary passes
(11 leads). Employment needs its Grok challenger; Financial Assistance resumes
its remaining primary passes. The other thirteen categories are untouched.
No new Claude, ChatGPT or Perplexity assignment is carried into the production
plan; incomplete historical assignments remain in the untouched baseline.

Do not use `data/st-george-production-20260918-reviewed/`. That abandoned draft
failed during large SQLite consolidation and had now-prohibited Claude routes.
The manifest there says `abandoned-not-for-launch`. It remains as failure evidence.

## Verification

- All three experiment hashes and the earlier baseline hash unchanged.
- Six completed jobs, their passes and challenger assignments compare equal
  field-for-field to the Codex+Grok source.
- All ten reused partial-category passes retain sealed assignment hashes,
  original responses and original assignment/completion clocks.
- All category rosters enable only Codex and Grok.
- Production SQLite quick_check: `ok`.
- Full local suite: 207 tests, one skipped. This includes Claude execution/probe
  refusal, preservation/shadow/partial-work migration, and large consolidation
  under forced SQLite page-cache spill. Tests use mocked historical workers.
- Codex High/web/JSON and sandboxed Grok authentication probes passed earlier.
  They are historical readiness evidence; preflight is still required at launch.
- The preparation manifest is the pre-launch snapshot. Production subsequently
  started on explicit authorization; see `launch.json` and the runner log.

Implementation and reports are committed/pushed on the current branch as recorded
in Git history. Check the corresponding GitHub Actions run before launch.

## Before any resume

1. Launch authorization is already granted. CLI worker effort is explicitly
   set to High in the command below.
2. Read `SCOUT_STATUS.md`, inspect actual processes and this production database.
   Do not launch a second runner on it. A monitor is not a worker.
3. Keep preflight enabled. If Grok needs login, refresh outside the strict
   research sandbox and then resume. Do not weaken the sandbox, split the task,
   or use Claude to bypass authentication failure.

Read-only process inventory, without assignment text:

```bash
ps -axo pid,ppid,etime,comm | rg 'Python|python|codex|grok|claude|caffeinate'
```

Inspect a suspected worker's command/database path when necessary. A leftover
`.runner.lock` file does not imply a live process; OS locks release on exit. Do
not delete that file to evade an active lock.

## Historical command — research is complete; do not relaunch

```bash
caffeinate -dimsu python3 -u -m resource_research_agent.pairwise_runner \
  --database data/st-george-production-20260918-codex-grok/research.sqlite3 \
  --import-id 1 \
  --profile codex-grok \
  --reuse-completed \
  --max-categories 21 \
  --codex-model gpt-5.5 \
  --codex-reasoning-effort high \
  --grok-timeout-seconds 900 \
  >> data/st-george-production-20260918-codex-grok/runner.log 2>&1
```

The cap is **21 total**, including six reused completed categories. Resume with
the same command after inspecting any interruption. No Claude routing file or
Claude probe is allowed. Terminal authentication, timeout and turn-budget errors
stop without unchanged automatic retries or provider fallback. Diagnose the
actual error before deliberately changing a budget or task scope.

An optional monitor can run separately on an unused port:

```bash
python3 -m resource_research_agent \
  --database data/st-george-production-20260918-codex-grok/research.sqlite3 \
  serve --port 8769
```

After research, curate/consolidate the evidence before generating
`autoStGeorge.html`. Consult the [source audit](six-category-source-audit-20260918.md)
and five-worker comparison for known corrections and omissions. The manifest maps
source contributions and shadow assignments to promoted evidence. Track accepted
identities, marginal contributions and curator time rather than treating submitted
row counts as acceptance. Bonsai remains removed and extraction deferred.

## Preparation reproduction (new destination only)

```bash
python3 -m resource_research_agent.production_prep \
  --experiment data/pairwise-overnight-20260918-022703 \
  --destination data/NEW-UNUSED-DIRECTORY/research.sqlite3 \
  --review docs/six-category-architecture-review-20260918.md \
  --legacy-baseline ~/resource-scout-baselines/st-george-20260918-002522/research-agent.sqlite3
```

The existing prepared copy is ready; do not run preparation again merely to
resume. The command refuses an existing destination and opens its sources read-only.
