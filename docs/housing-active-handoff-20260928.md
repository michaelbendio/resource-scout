# Active Housing run — September 28, 2026

Operational checkpoint, not completion. Verify live state before acting.

**Latest, 07:35 UTC:** 64 of104 leads are prepared. Coordinator56181 stopped
cleanly after08b hit the conservative input guard and09a completed.08b is pending
at turn10: NO sent request needs replay. Code now uses native saved-prefix token
counts plus a byte upper bound for appended messages.218,647 native input/cache
tokens became a257,082 next-input upper bound, plus32,768 output allowance, under
the unchanged one-million limit. Messages, source evidence and thinking remain
unchanged. Recovery: `recovery/08b-context-accounting.json`.71 tests pass.

Earlier06b output recovery split four leads into two (both finished). Current
plan has26 batches; all104 leads remain accounted for. Max thinking stays.
The recorded400-call/eight-active-hour engineering amendment is loaded; all prior
charges and original sealed configuration remain. Compact collection input uses
complete research replies plus exact source-member mappings. No completed review
or importable package exists. Resume from checkpoints, do not start duplicate
coordinators. Latest ETA: curation25–50 minutes, overall3–5hours, provisional.

Michael explicitly requested DeepSeek curation AND review; this overrides the
ordinary manual Codex handoff for this trial. One review, two curation batches.
The earlier automatic approval rejection was resolved by citing this exact
conversation authorization. No Jev is used or run.

## User decisions

- DeepSeek curates its 104 original Housing leads and then reviews them in fresh
  contexts using Codex's substantive review instructions. Max thinking remains.
- Deliver BOTH the full evaluation JSON and an **importable Mesa Housing
  `prepared-resources.json`** for WSRS-TSO, plus a readable HTML review.
- The $3 Housing cap was explicitly removed earlier. No new dollar cap. Existing
  request/time safeguards and unknown-outcome holds remain.
- No second Codex reviewer, no new broad research or other-category expansion.
- User prefers small tool outputs and concise updates. Latest rough ETA was
  2–4 hours, then explicitly made provisional after the output-limit recovery.

## Workspace and live state

All implementation is in this isolated checkout:
`/Users/michaelbendio/resource-scout-pairwise/data/evaluations/implementation`
branch `docs/scout-evaluation-design-20260927`.

Trial root relative to it:
`data/evaluations/mesa-housing-preparation-review-20260928-r3`.
Read `runner.log`, `progress.json`, `ledger.sqlite3` and the newest attempt's
response/state. The worker holds `runner.lock`. Do not launch a duplicate.
The supervising assistant checks at least every minute and owns recovery.

- Original research: six requests, 104 leads, 16.75 active minutes, completed.
- Initialization r1/r2 never sent paid calls; their failures are recorded.
- Trial first dispatch: **06:09:51 UTC**.
- `curated-01`: complete, eight proposals, six usable / two needs-resolution,
  530 seconds. Partial readable preview: `reports/curation-progress-01.html`.
- `curated-02`: held after two `max_tokens` responses containing thinking, no final
  JSON, with a tool round between. All three responses are known and preserved.
- `execution-plan.json` v2 preserves the completed first eight, then assigns the
  remaining 96 in four-lead batches (`02a`, `02b`, … `13b`), 25 batches total.
  Their prompts keep assigned original provenance and omit unrelated corpus and
  later pipeline tasks. This is not a reduction of thinking effort.
- Recovery is recorded under `recovery/batch-02-*`. Code commit `6310c91`.
- Resumed `curated-02a` at **06:29:58 UTC**, unified exec session **91334**.
  Old stopped session was 43317. A session ID is not a process PID.
- 64 evaluation tests pass. Do not repeat paid requests to recover formatting.

Runner, if it has actually stopped and recovery is diagnosed:

```sh
python3 -m resource_research_agent.evaluation.preparation \
  --experiment data/evaluations/mesa-housing-preparation-review-20260928-r3 \
  --execute >> data/evaluations/mesa-housing-preparation-review-20260928-r3/runner.log 2>&1
```

Use network escalation for the explicitly authorized official DeepSeek endpoint.
No credentials may be printed or committed. API alias `deepseek-flash`, effort
`max`, output limit 32768, 12 native searches/assignment, 600-second request
timeout. Frozen total limits: 150 calls, four active hours. Monitor remaining
headroom; these are engineering stops, not user-imposed dollar caps. Preserve and
diagnose any hold rather than resetting checkpoints. Adapter allows one output
length continuation; failed batch 2 exhausted it.

## Remaining work

The runner automatically completes curation batches, whole-collection curation,
fresh review batches and whole-collection review. It preserves original raw API
responses, normalized batches, evidence, before/after findings and stage previews.
After two successful timings it emits candidate-weighted remaining-batch minutes;
that estimate excludes collection selection, subsequent review and import work.

Watch for a collection prompt exceeding the adapter's one-million-byte conservative
bound; all original candidates plus output may approach it. A safe remedy is to
give original `sourceResponses` (84 KB) plus the ID/name index instead of repeated
candidate provenance; preserve the full frozen input and log the new assignment.
Do not weaken substantive checks or silently alter a sealed packet.

When `progress.json` says completed, run the explicitly authorized import handoff:

```python
from pathlib import Path
from resource_research_agent.evaluation.prepared_handoff import reconcile_and_export
reconcile_and_export(
    Path('data/evaluations/mesa-housing-preparation-review-20260928-r3'),
    production_registry=Path('/Users/michaelbendio/resource-scout-pairwise/registry/resource-identities.json'),
    previous_artifact=Path('/Users/michaelbendio/resource-scout-pairwise/deliveries/mesa-complete-20260927-r2/prepared-resources.json'),
    destination_registry=Path('registry/resource-identities.json'),
    output=Path('deliveries/mesa-housing-deepseek-20260928'))
```

This is one additional DeepSeek import reconciliation context, introduced only
AFTER the independent review freezes. It receives old identity/taxonomy labels,
not permission to replace independently researched facts. It matches actual
programs, retains Type/group IDs where meanings match, consolidates aliases with
full sources/candidate links and before/after findings, then uses production
`prepared_export.finalize` gates.

The isolated checkout initially has a stale 150-identity registry. The parent
production checkout has **1,891 identities / 7,744 aliases**, same namespace, a
superset. The handoff preserves that complete production registry, guards against
concurrent changes and synchronizes newly allocated identities to BOTH files.
Both registry updates need committed provenance. Preserve the parent's unrelated
deleted proposal document and untracked Jev files; stage only intended changes.
Do not overwrite the previous full Mesa export. Scope is Housing, not complete
office; absence in this snapshot is not deletion or loss of other memberships.

Outputs: prepared JSON/gzip, evaluation JSON, readable `review.html` with full
facts/sources and batch findings, starter Markdown, evaluation HTML, identity
migration, receipt and usage. Review author is DeepSeek, never Codex or the office.

Before final delivery: inspect rendered HTML, validate JSON/registry/category IDs,
assess the known pilot errors against the final result WITHOUT feeding those
answers into DeepSeek's trial, report honest remaining gaps, update status/docs,
commit/push scoped changes and provide concise artifact links and measured time.
The trial remains a Housing quality experiment, not the later three-category
20-item milestone or a whole-Mesa acceptance review.
