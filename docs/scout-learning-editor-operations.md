# Learning and frontier editing: operator guide

September 9 follow-up: [Increment 4 operations](scout-learning-increment-4-operations.md) adds the ordinary feedback queue, reviewed activation and rollback. Earlier experimental receipts remain historical and inactive.

Implemented on `v2.0`, September 9, 2026. See the [design](scout-learning-editor-design.md), [plan](scout-learning-editor-plan.md) and [measured pilot results](scout-learning-editor-results.md).

These are operator commands for an AI-assisted workflow. Curators continue using the existing Resource Editor. There is no automatic model purchasing, unattended browser dispatcher, lesson activation, or office publication.

## Learning workbench

Use a separate SQLite database for an experiment. Run the commands below from the Scout checkout.

```sh
python3 -m resource_research_agent --database trial.sqlite3 learning import-editorial original.zip editorial-decisions.json
python3 -m resource_research_agent --database trial.sqlite3 learning import-comparison COMPARISON_ID
python3 -m resource_research_agent --database trial.sqlite3 learning collect
python3 -m resource_research_agent --database trial.sqlite3 learning inbox
python3 -m resource_research_agent --database trial.sqlite3 learning propose lesson.json
python3 -m resource_research_agent --database trial.sqlite3 learning prepare LESSON_ID trial.json
python3 -m resource_research_agent --database trial.sqlite3 learning packet TRIAL_ID baseline --context-id FRESH_CONTEXT_A --fresh
python3 -m resource_research_agent --database trial.sqlite3 learning packet TRIAL_ID candidate --context-id FRESH_CONTEXT_B --fresh
python3 -m resource_research_agent --database trial.sqlite3 learning submit TRIAL_ID baseline response-a.json receipt-a.json
python3 -m resource_research_agent --database trial.sqlite3 learning submit TRIAL_ID candidate response-b.json receipt-b.json
python3 -m resource_research_agent --database trial.sqlite3 learning assess TRIAL_ID assessment.json
python3 -m resource_research_agent --database trial.sqlite3 learning report TRIAL_ID
```

`collect` imports comparisons already captured by ordinary package intake, including changed/resolved questions. Repeating it adds no duplicate observation versions. An updated attestation creates a distinguishable version; versions of the same event are not independent confirmations. `inbox` summarizes evidence/proposals without presenting hundreds of resources for Michael to score. An operator can inspect an observation with `learning inspect RECORD_ID` and propose a small method for testing. Collection does not automatically infer lessons.

The committed [pilot artifacts](../experiments/learning-pilot-20260909/README.md) show complete proposal, specification, packets, receipts and assessment formats. The baseline path/text/hash is sealed. Both arms have identical cases and model settings, with a two-assignment and one-hour maximum. Lesson-support IDs are excluded from test cases. A fresh-context receipt attests separate chats; Scout cannot prove what the service remembered through account-level personalization.

Raw deliveries are stored before parsing. Complete replies must cover every case; malformed replies remain delivery evidence without satisfying completion. Accepted responses/assessments are immutable. Further model attempts require a separately named trial; do not disguise a model retry as a local formatting fix. Late deliveries are retained and marked late. Clock allowances govern Scout dispatches, not a remote provider's ability to keep generating. Unknown incremental cost is `null`.

No command activates a lesson. Changing production guidance, adaptive pass counts and model routing remains a separate reviewed increment.

## New-discovery frontier workflow

Start from a standard resource package containing prospective leads, or bridge the existing manual-discovery JSON contract into a baseline package:

```sh
python3 -m resource_research_agent --database office-pilot.sqlite3 editor prepare-leads baseline.zip leads.json editor.json --office 'New TSO' --category housing
# Or use a resource package already containing the prospective resources:
python3 -m resource_research_agent --database office-pilot.sqlite3 editor prepare leads-package.zip editor.json --office 'New TSO'
python3 -m resource_research_agent --database office-pilot.sqlite3 editor packet EDITOR_PROJECT early
python3 -m resource_research_agent --database office-pilot.sqlite3 editor submit EDITOR_PROJECT early early-response.json editor-receipt.json
python3 -m resource_research_agent --database office-pilot.sqlite3 editor start-research EDITOR_PROJECT --execution-config research.json
```

`prepare-leads` accepts Scout's existing `leads` array with organization, program, website, leadType, locationOrServiceArea, whyRelevant and uncertainty. It preserves raw contribution bytes, assigns stable IDs within that contribution, keeps unknown facts unknown, and starts no detailed research before editorial selection. A new office may use an empty baseline resource array with its office taxonomy. Existing baseline resources also appear in the editor's accounting; omission is a draft decision, never an office deletion.

Editor configuration:

```json
{
  "name": "New TSO Housing pilot",
  "editor": "Actual editor provider/product",
  "model": null,
  "settings": {},
  "sourceScope": "full",
  "categoryIds": ["housing"],
  "authorityNote": "Reversible selection and supported editorial changes before human curation"
}
```

Use the actual available model label/settings; leave unknown model identity null. Research requires an explicit [sampled execution configuration](../resource_research_agent/maintenance_guidance/astra_execution.example.json). Set office/service area, actual model identities or null, deliberate categories and a fresh sampling seed. The editor command does not silently fall back to the older all-challenger workflow.

`start-research` returns a normal maintenance/research project ID. Use the existing `maintain next`, submission, provider-availability and reconciliation workflow for that ID. Its primary freezes, sampled Claude checks and optional targeted challengers are unchanged. Restart reuses sealed source bytes and configuration. After all selected tasks/checks/reconciliations finish:

```sh
python3 -m resource_research_agent --database office-pilot.sqlite3 editor finish-research EDITOR_PROJECT
python3 -m resource_research_agent --database office-pilot.sqlite3 editor packet EDITOR_PROJECT final
python3 -m resource_research_agent --database office-pilot.sqlite3 editor submit EDITOR_PROJECT final final-response.json editor-receipt.json
python3 -m resource_research_agent --database office-pilot.sqlite3 editor export EDITOR_PROJECT output-directory
```

Use a new export directory. It contains `auto[Location].html`, a full draft ZIP and a manifest. The HTML uses the common Scout template, isolated browser storage, existing resource editors and embedded PDF initialization. Its normal curated-selection export remains unchanged. The full ZIP is available directly from the output directory.

The packet is the authoritative response contract: assignment hash plus a decision for every source ID. Each decision has resourceId, disposition, targetResourceIds, reason, evidence, fields and questions. Each receipt has editor, model, settings, contextId and notes. Early review selects leads and combines duplicate identities; final review may change supported fields and five-section text. Write changes on retained destinations. Guidance is versioned JSON in `editor_guidance/default.json`, sealed into each project.

Initial integration supports retain/combine/reserve/exclude, one destination per combination, existing taxonomy and newly opened questions. Original records, donor PDFs and exact curator answers/history survive. Conflicting question histories block combination instead of discarding one answer. Significant additions/splits, new taxonomy definitions and unresolved research holds require their existing explicit review paths; this integration does not invent a way around them. Final output prunes unused Types/groups, retains category definitions for future gap research, and creates no deletion request or human approval. All accepted editorial decisions enter the learning evidence store.

This path now also has a real bounded Welfare Square Employment pilot with five retained resources; see [pilot results](scout-discovery-pilot-results.md). This does not establish complete office coverage or broad autonomous release. New final exports preserve scope and per-assignment gaps in `scoutDiscoveryCoverage` and the export manifest. Earlier sealed exports are not rewritten. Explain these limits in a companion overview.

## Timing, optimization and rollback

```sh
python3 -m resource_research_agent --database office-pilot.sqlite3 --timings timings.jsonl maintain status PROJECT_ID
python3 -m resource_research_agent timings timings.jsonl
PYTHONPATH=. python3 scripts/benchmark-checkpoint.py SOURCE.sqlite3 --project 2 --output new-benchmark-directory
```

Timing events contain phase/duration/status and numeric counters, not resource prose or errors. Phases can nest: their sum is not total elapsed time. Failed timing output does not invalidate work. Experiment receipts report handoff elapsed time separately from unknown provider time/cost; no subscription usage is guessed. UI recovery observations belong in receipt notes.

Large repeated context now uses `scout-project-shared-json-zlib-v2`. Existing plain JSON and zlib-v1 rows are still readable. All current checkpoint readers share that decoder. New compact rows require this release; an older checkout cannot read them directly. The original run database was not migrated or rewritten during testing.

```sh
# Copy first; source is read-only and an existing destination is refused.
python3 -m resource_research_agent checkpoint-copy SOURCE.sqlite3 COMPACT-COPY.sqlite3 --codec compact
# For an older reader, create a separate legacy-codec copy.
python3 -m resource_research_agent checkpoint-copy COMPACT-COPY.sqlite3 LEGACY-COPY.sqlite3 --codec legacy
```

Conversion preserves project IDs/revisions/events, exact expanded research state, evidence documents and unrelated database bytes. It checks round-trip equality, SQLite integrity and references before publishing the copy. Interrupted conversion leaves the source and any existing destination intact. Old software will ignore new learning/editor tables; a legacy-codec copy does not add those new capabilities to an old checkout.
