# AutoCurator

AutoCurator is Resource Scout's Codex-controlled curation stage. It turns one
location's completed, consolidated discovery into a normal TSO Resources review
application such as `autoMesa.html` or `autoProvo.html`.

AutoCurator is not a separate dashboard or a separate resource-package format.
Resource Scout owns the research, consolidation, curation assignments, durable
curation results, progress, and provenance. Resource Assistant owns the regular
TSO Resources application, its editors, and its merge-compatible package format.

## End-to-end flow

1. Scout connects one office resource package and researches its named service
   categories with ChatGPT, Grok, Claude, and Perplexity.
2. Scout preserves each submitted response and consolidates the four candidate
   sets without losing source attribution or visible uncertainty.
3. After the named categories have completed research, Scout prepares one
   category at a time for Codex. Codex returns ordinary TSO resource records.
4. Scout validates and stores each curation result, including deterministic
   candidate-to-resource provenance. Completed categories are never silently
   repeated; interrupted work resumes from the durable category state.
5. Scout asks Resource Assistant's versioned generator to combine every curated
   category with the regular TSO Resources application. The result is
   `auto[Location].html` with all normal categories visible and only curated
   resources populated. `Miscellaneous` is ignored for research and curation.
6. Reviewers use the normal Admin editors. In AutoCurator mode, each resource has
   a **Ready to package** checkbox and a green ready indicator.
7. **Save N Ready Resources** exports one standard, additions-only resource
   package containing the marked resources, their category definitions,
   referenced For values, and attached PDFs. One batch may span categories.
8. After a successful save, those resources are hidden from that browser's
   active review queue. They remain recorded locally so a canceled or failed
   save cannot lose work. A fresh copy of the original HTML starts with the
   original embedded review set.
9. A reviewer merges the saved package through the normal office HTML. Stephanie
   and Sister Dewsnup may use independent copies and coordinate different
   categories; their local ready, edit, deletion, and packaged state does not
   synchronize.

## Review semantics

Unmarked is the only default review state. AutoCurator does not add separate
Needs Research, Rejected, or Packaged controls.

- A reviewer records needed clarification in Description or Information.
- Deleting a proposed resource removes it from that AutoCurator review copy.
  Because the proposal was never accepted into the office package, an
  AutoCurator export must not include a deletion tombstone for it.
- Editing a ready resource clears its ready mark. The reviewer marks the revised
  resource ready again after checking it.
- A successful package save hides its selected resources locally. Package
  cancellation or failure leaves them visible and ready.

The package remains a normal Resource Assistant package. AutoCurator-only review
state and candidate provenance are not exported as office administrative data.

## Curation contract

Scout creates one durable curation job for each researched, non-Miscellaneous
category. A job contains:

- location and office identity;
- source resource-package hashes and version;
- candidate-package hash and Scout version;
- category ID, label, and category definition;
- consolidated candidates, excluded records, original source responses, and
  existing-package comparisons for that category;
- an exact assignment version and creation time.

Codex returns one JSON object containing curated resources and a disposition for
every input candidate or consolidated candidate group. Dispositions exist for
provenance and completeness, not as reviewer-facing workflow states. Each
curated resource has a stable generated ID, ordinary Resource Assistant fields,
and links to all contributing candidate IDs. Scout rejects missing candidate
coverage, unknown candidate IDs, duplicate generated IDs, another category or
location, or invalid Resource Assistant fields.

The final human-vetted package is authoritative. A Codex result is a proposal and
must never overwrite an office package directly.

## Research pacing and progress

ChatGPT assignments use a randomly chosen baseline delay of 10 through 20
minutes after the preceding ChatGPT assignment completes. Before every delay,
the operator is told the selected duration and expected assignment time. Codex
may extend the delay when throttling feedback is indirect, abbreviated, less
explicit, incomplete, or otherwise suggests reduced availability. An explicit
reset time always takes precedence. ChatGPT assignments never overlap.

Scout records progress events durably, and Codex reports them in the active task:

- research start and curation start;
- each completed category with per-source, consolidated, and curated counts;
- the next ChatGPT category and scheduled assignment time;
- a heartbeat every 15 minutes during a long research or curation category;
- interruption, retry, validation failure, and completion.

Pacing uses an injectable clock and random-number source so automated tests do
not wait in real time.

## Office and version boundaries

Mesa and Provo remain independent workstreams. Research or curation from one
office is never pooled into another. If a newer office package is connected,
Scout reconciles preserved discoveries against the new package before curation;
it does not discard or rerun otherwise valid research.

Resource Assistant remains the template and package authority. Scout invokes a
configured Resource Assistant checkout and validates its generator contract and
version instead of copying the application into Scout. The generated file embeds
the office identity, source hashes, curated category manifest, and its independent
`autocurator-[location]` browser-storage identity.

## Acceptance gates

The first production gate requires all of the following:

- focused Scout storage, curation-contract, pacing, progress, and HTTP tests;
- Resource Assistant browser tests for ready marking, edit invalidation,
  selection-scoped packaging, PDFs and For values, cancellation, deletion
  isolation, local hiding, reload, and independent office storage;
- generator tests using a synthetic multi-category candidate package;
- a complete application verification in Resource Assistant;
- a Mesa pilot package merged into a disposable Mesa data copy with only the
  selected stable resource IDs incorporated;
- preservation of all unrelated packages and live Scout database files.

Stephanie's Employment feedback may refine the curation assignment before the
remaining Mesa categories are curated. Infrastructure and deterministic safety
tests do not depend on that wording.

The Resource Assistant generator's legacy `--category` option exists only to
reproduce the Employment-only `autoMesa.html` already sent to Stephanie. Remove
that option when Stephanie's feedback is incorporated; the production
AutoCurator path must then generate one all-category review file only.

At that same Stephanie-feedback gate, discuss and agree on three curation rules
before changing the Codex assignment: assigning one resource to every appropriate
category, conservatively detecting existing For groups, and handling a warranted
For group that is absent from the taxonomy. AutoCurator must not silently create
the missing group. The proposed behavior is to add an Information note beginning
`[Human--I suggest you make a new For group for ...]` for human review.
