# Active Housing run — September 28, 2026

Operational checkpoint, not completion. Verify live state before acting.

**Latest, 10:13 UTC:** Curation complete; **56/104 leads reviewed**. Code
**fb93687**, `reviewed-08a` running under the existing coordinator. ONE sequential
DeepSeek reviewer/max. **81 evaluation tests pass**. Latest overall ETA: 2–3 hours.
Verify live ledger/progress/lock; no duplicate coordinator. No final importable
package. Review07b's complete JSON had a lone trailing Markdown closing fence;
validated offline adoption added four reviewed leads without a new API call.
Reusable offline helper: trial `recovery/adopt-reviewed-response.py` (batch key).

Curation:104 leads →101 batch proposals (93usable,8needs-resolution),3omissions;
collection:100 identities,14 Types,18 groups,10 suggested starters. Still drafts.
Curation used166.69 active minutes (155.60 preparation +11.09 collection), including
failed responses, across192+4 API requests. Elapsed06:09:51→08:32:08UTC was142.3
minutes. Original research is separate:16.75 active minutes. Final timing must use
the ledger, not just elapsed time from the last resumed process.

Execution plan v5 has26 batches. Two parallel curation workers finished; review
always stays sequential. The26 review batches are followed by whole-collection
review, then the separately authorized import reconciliation below. Current total
engineering stops:400 calls/eight active hours; all prior usage retained. Michael
removed the Housing dollar cap. Monitor headroom before the final stages.

Completed recoveries, all with original evidence preserved:
- Initial batch02 output exhaustion: preserve first8, split remaining96 into4s.
  Failed06b was subsequently split into two2-lead batches. All104 stay covered.
- Prelude/fence parsing:03b curation and06a review were adopted from saved JSON
  with ZERO paid replay. Provider prose remains unendorsed source notes.
- Context accounting now counts decoded prompt strings, uses native saved-prefix
  counters, and does not charge an exact saved assistant response again as bytes
  on top of its native input/cache/output counts. Guards remain conservative;
  no thinking/source messages were deleted. Recomputed bounds preserve old records.
- Whole-collection curation produced two32,768-token thinking-only replies, then
  a65,536-token reply with a truncated JSON answer. Its100 identities,14 Types,
 18 groups and98 complete assignments were frozen. The bounded completion script
  asked for only2 missing assignments plus starter/finding fields in the SAME
  conversation. Response03 completed; full validation passed. `assemblyEvidence`
  hashes record this. Original partial text, held states and prefix remain in
  `recovery/`. No Codex resource judgment was inserted.
- Existing HTML bytes were preserved when only embedded JSON key order differed;
  other mutations still fail. Future normalized results are reloaded canonically.
- Review plan v4 uses complete cross-batch identity/description/source/omission
  indexes for previously unstarted batches, retaining each assigned batch's full
  facts and the full final collection review. Existing01/02a/02b packets unchanged.
- Review06b1 echoed2 `lastModified` values exactly from code-generated input.
  Offline assembly removed ONLY those metadata echoes, retained all facts/findings,
  and recorded source hashes. Plan v5 omits server timestamps only from future
  examples. Normalization evidence is included in evaluation export metadata.
- The supervisor's offline timing notes used assignedCandidates/elapsedSeconds;
  ETA expected candidates/seconds.06b2 was already saved before reporting failed.
  Code now accepts both; missing timing gives no ETA instead of stopping saved work.

For offline response adoption, restore BOTH the exact request messages and its
search-tool availability flag; processing a response can change searchLimitReached.
Use a transport that forbids dispatch. Preserve held state, response hash and
normalization evidence. Never blindly replay a sent or unknown-outcome request.

All changes are recorded under `recovery/`, execution plan/control/amendments,
authorizations and native attempt files. This is an evolving operational trial,
not one unchanged benchmark condition. Curation previews are in reports/curated*
and reports/curated-with-selections*. Independent review gets no prior Codex
pilot answers or legacy prepared resources. Legacy identity/taxonomy context enters
only after review for import. No Jev, other category or second reviewer is involved.

Michael explicitly requested DeepSeek curation AND paid review. This overrides
the default manual Codex handoff for this trial. Automatic approval once missed
that instruction; reconsideration quoting “And then I'd like DeepSeek to do the
review too” approved the same workflow. No new permission is needed for this scope.

## Final collection input measurement (prepared, not yet used)

The running coordinator still uses fb93687. On its next necessary restart, code
can accept a local offline token measurement for ONLY the first
`reviewed-collection` / `import-reconciliation` request. It first preserves the
exact rejected request. Run `scripts/measure-housing-collection-input.py` with
`data/evaluations/tokenizer-tools/bin/python`, the trial root, assignment ID, and
`data/evaluations/tokenizer-tools/deepseek-v41-tokenizer.json` if the byte guard
holds a final prompt. The tool hashes the official tokenizer and exact request;
changed requests fail closed. It counts plain user text, adds25% headroom,
byte-counts all metadata, and adds8192 framing tokens. This is a recorded
engineering allowance, not billing or a proven API upper bound. Later native
response counters still govern the saved-prefix bound. Export includes receipts.
No source or reasoning text is removed; all paid/time safeguards stay in place.

Sources: [official V4.1 tokenizer provenance](https://github.com/deepseek-ai/deepseek-recipe/tree/main/static/tokenizers/v41)
and [official tokenizer guide](https://github.com/deepseek-ai/deepseek-recipe/blob/main/docs/tokenizer.md).
Pinned SHA256:81f64d1248a68ce3663e07ab3ee48b851e5df0e32d27cb98e4c9a268151e8d99.
Offline cross-checks: review08a first user text101363 tokens versus native input
101751; curated-collection-v2 text227147 versus native227535. Review01 native
counters are higher because server-search context is also included. Runtime
installation is isolated under ignored data; no global Python install changed.

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
