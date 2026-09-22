# Codex curation runner

The CLI bridge completes Scout's existing sealed category curation contract. It
uses Codex CLI at the selected High or Extra High effort, saves each validated result to SQLite, and generates the
review HTML after all categories finish. It never calls Claude or starts research.
The monitor's curation count means **completed categories**, not individual
resources; an active-category heartbeat is recorded every 30 seconds.

Current St. George launch:

```sh
caffeinate -dimsu python3 -m resource_research_agent.scout_curation_runner \
  --database data/st-george-production-20260918-codex-grok/research.sqlite3 \
  --import-id 1 \
  --effort xhigh \
  --batch-candidates 30 --batch-chars 60000 \
  --output data/st-george-curation-20260919 \
  --source-audit docs/six-category-source-audit-20260918.md
```

Inspect actual worker processes and SQLite state before resuming. A database
runner lock blocks concurrent launches. Completed categories are skipped.
`--max-categories` means completed categories total, including previous work.
Michael requested Extra High for the St. George category workers after the first
Addiction assignment had begun at High; preserve that work and use Extra High
for subsequent categories. The effort is explicitly passed to each CLI worker
and recorded in its execution metadata.

The default one-hour per-category timeout stops without automatic retry or
provider fallback. If an attempt stopped, inspect its saved artifacts before an
explicit recovery; the runner refuses to overwrite attempt logs or sealed input.
A complete saved JSON result can be validated and ingested on resume without
another model call.

Each category directory contains the exact assignment, its compact view, original
source-only evidence, prior curated resources, prompt, schema, CLI event stream,
stderr, final result and execution metadata. The view removes duplicated
consolidation metadata and presents each original member submission once; full
raw responses remain accessible in the original assignment. Manual notes, draft
edits and existing-resource matches are retained. Source-only records are
reference evidence and cannot silently become new candidate IDs.

Curation must account for every candidate, consolidate aliases, preserve distinct
programs and reuse stable IDs across categories. Every disposition must match
its actual contributing resource links. Only existing For groups are allowed.
Retained proposals address eligibility, best connection route, access/hours and
important information, with source URLs and explicit unknowns. The dated source
audit supplies consequential corrections to check, including wrong-geography
school programs, unsupported rebrands and obsolete program names.

Generated resources are **proposals for human review**, not human-approved or
phone-vetted resources. A web verification date does not mark them Curated.
The runner does not publish an office package, enable structured extraction,
contact providers or start another city.

## Context recovery and audit corrections

Children/Pregnancy exhausted its context window on the first whole-category
Extra High attempt. Remaining curation now uses saved batches of at most 30
candidates and approximately 60,000 characters of original member evidence.
The full sealed assignment remains in SQLite; batch assignments and results
are under `batches-v1/`. Each validated batch is reused on resume, including
its normalization timestamps, so later assignment hashes remain stable.

`revise_scout_curation_result` applies source-backed corrections to a completed
category without another worker call. It validates full candidate coverage and
links, rejects stale edits by expected result hash, and atomically preserves the
old/new results and evidence in `scout_curation_result_revisions`. Assignments
and original completion times remain unchanged. Later assignments receive the
corrected resources; already-sealed in-flight assignments need explicit review.

Read [the orchestration contract](scout-orchestration.md) before supervising
these operations. Bounded batching and durable results are implemented; the
CLI still stops for unexpected failures. It is not yet a self-repairing unattended
supervisor. The assistant owns diagnosis and recovery during the current run.

## Large prior-resource index recovery

Welfare Square ID Recovery exhausted context on September 22 after 13 categories
completed. For that remaining run, use `--batch-candidates 10 --batch-chars 25000
--compact-prior-index` at the already authorized xhigh effort. The opt-in index
keeps every prior resource ID, name, website and categories inline, with complete
descriptions and Information bodies still available in `prior-resources.json`.
`priorIndexFormat: identity-v1` is part of the batch assignment hash, so changed
projections create distinct sealed attempts; the default preserves legacy batch
bytes/hashes. The option requires batching. Preserve the failed attempt and any
completed batches before changing limits; do not repartition completed work.
