# Resource Scout curation and review files

Resource Scout owns the complete candidate workflow: research, consolidation,
Codex-controlled curation, and generation of a location review file such as
`autoMesa.html` or `autoProvo.html`. Curation is a stage of Resource Scout, not a
separate product.

An `auto[Location].html` file is a self-contained TSO Resources application. It
has the ordinary reading, searching, printing, and Admin editing experience,
plus review controls for Scout's proposed resources. The file is generated
directly by the versioned Scout release and is not derived from another local
HTML file or another repository at generation time.

## End-to-end flow

1. Scout connects one office resource package and researches every named service
   category with ChatGPT, Grok, Claude, and Perplexity.
2. Scout preserves each submitted response and consolidates the four candidate
   sets without losing source attribution or visible uncertainty.
3. After all named categories have completed research, Scout prepares one
   category at a time for Codex. `Miscellaneous` is ignored.
4. Scout validates and stores each curation result, including deterministic
   candidate-to-resource provenance. Completed categories are not silently
   repeated; interrupted work resumes from durable category state.
5. Scout combines every completed category into `auto[Location].html`. All
   ordinary categories remain visible, while only curated resources are
   populated.
6. Reviewers edit resources through the normal Admin editors. Each proposed
   resource has a **Ready to package** checkbox and a green ready indicator.
7. **Save N Ready Resources** exports one standard additions-only TSO Resources
   package containing every marked resource, its category definitions,
   referenced For values, and attached PDFs. One batch may span categories.
8. After a successful save, those resources are hidden from that browser's
   active review queue. They remain in local packaged history so work is not
   lost. A canceled or failed save leaves them visible and ready.
9. A reviewer merges the saved package through the normal office HTML.
   Stephanie and Sister Dewsnup may use independent review-file copies and
   coordinate different categories; their local review state does not
   synchronize.

## Review semantics

Unmarked is the only default review state. Scout does not add separate Needs
Research, Rejected, or Packaged controls.

- A reviewer records needed clarification in Description or Information.
- Deleting a proposal removes it from that review-file copy. Because it was
  never accepted into the office package, the exported package contains no
  deletion tombstone for it.
- Editing a ready resource clears its ready mark. The reviewer marks the revised
  resource ready again after checking it.
- A successful save hides its selected resources locally. Cancellation or
  failure leaves them visible and ready.

Review state and candidate provenance remain local to Scout's review file and
are not exported as office administrative data. The exported file is a standard
mergeable TSO Resources package.

## Curation contract

Scout creates one durable curation job for each researched,
non-`Miscellaneous` category. A job records:

- location and office identity;
- source resource-package hashes and version;
- candidate-package hash and Scout version;
- category ID, label, and definition;
- consolidated candidates, excluded records, original source responses, and
  existing-package comparisons;
- an exact assignment version and creation time.

Codex returns one JSON object containing curated resources and a disposition for
every input candidate or consolidated candidate group. Dispositions provide
provenance and completeness; they are not reviewer-facing workflow states. Each
curated resource has a stable generated ID, ordinary TSO Resources fields, and
links to all contributing candidate IDs. Scout rejects missing candidate
coverage, unknown candidate IDs, duplicate generated IDs, a wrong location, or
invalid fields.

The final human-vetted package is authoritative. A Codex result is a proposal
and never overwrites an office package directly.

## Research pacing and progress

ChatGPT assignments use a randomly selected baseline delay of 10 through 20
minutes after the preceding ChatGPT assignment completes. Before every delay,
the operator is told the chosen duration and expected assignment time. Codex may
extend the delay when indirect or abbreviated feedback suggests throttling. An
explicit reset time always takes precedence. ChatGPT assignments never overlap.

Scout records progress durably, and Codex reports it in the active task:

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
Scout reconciles preserved discoveries against it before curation; it does not
discard or rerun otherwise valid research.

The Scout release owns and versions the self-contained review template. Every
generated file embeds Scout's version and build, office identity, source hashes,
curated category manifest, and an independent `scout-review-[location]` browser
storage identity.

## Acceptance gates

The first production gate requires:

- focused storage, curation-contract, pacing, progress, HTTP, and review-file
  generation tests;
- browser tests for ready marking, edit invalidation, selection-scoped
  packaging, PDFs and For values, cancellation, deletion isolation, local
  hiding, reload, and independent office storage;
- a synthetic multi-category review-file test;
- a Mesa pilot package merged into a disposable Mesa data copy with only the
  selected stable resource IDs incorporated;
- preservation of unrelated packages and live Scout database files.

The Employment-only compatibility path exists solely to reproduce the
`autoMesa.html` already sent to Stephanie. Remove it when Stephanie's feedback
is incorporated; the production path then creates one all-category review file.

At that same feedback gate, discuss and agree on three rules before changing
the Codex assignment: assigning a resource to every appropriate category,
conservatively detecting existing For groups, and handling a warranted For
group absent from the taxonomy. Scout must not silently create a missing group.
The proposed behavior is to add an Information note beginning
`[Human--I suggest you make a new For group for ...]` for human review.
