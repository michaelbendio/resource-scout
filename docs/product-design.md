# Resource Scout product design

## Product boundary

Resource Scout owns the path from office-package intake through multi-model
research, conservative consolidation, Codex-controlled curation, and generation
of a transient office review file such as `autoMesa.html`.

The review file is a normal TSO Resources application with additional proposal
review controls. It is an artifact created by Scout, not a separate product, and
is never named `autoNew.html` or Resource Curator.

## Research and consolidation

Codex performs one versioned category playbook at a time, including focused
passes and a deterministic coverage-gap pass. After Codex closes its passes,
ChatGPT, Grok, and Perplexity each receive one adversarial assignment to find
what Codex missed. Claude is retained as a non-blocking shadow source. The
readable researcher roster can assign primary, challenger, shadow, or disabled
roles; disabled researchers receive no assignment or pacing. Challenger results
join the candidate run. Shadow results remain durable evidence but do not enter
candidate packages. Scout preserves every exact assignment, response, role, and
attribution.

ChatGPT assignments are spaced by a randomly selected 5-to-10-minute baseline.
Codex may extend that delay when indirect feedback suggests throttling and reports
the chosen delay before each assignment. Long categories receive a progress
heartbeat every 15 minutes.

## Curation and office review

After all named categories have been researched, Scout gives Codex one durable
curation assignment at a time. `Miscellaneous` is ignored. Completed work resumes
without repetition, and every consolidated candidate receives a deterministic
disposition. These dispositions establish completeness and provenance; they are
not reviewer-facing outcomes.

Scout then generates `auto[Location].html` with all ordinary categories visible
and only curated resources populated. Reviewers edit proposals in the normal Admin
experience and mark satisfactory resources **Ready to package**. Saving creates
one standard additions-only resource package containing all currently ready
resources, even when they span categories. After a successful save, those
resources are hidden locally but retained in packaged history. Deleting a proposal
discards it from that review copy without creating an exportable tombstone.

The final human-vetted package is authoritative. Scout never writes curated
proposals directly into the office package or office HTML.

## Progress and history

The main screen stays intentionally small:

- package intake has no operator-facing candidate-package export;
- Scout progress shows the office, current phase, actual research and curation
  counts, current activity, latest update, next ChatGPT category, delay duration,
  scheduled assignment time, and any adjustment reason;
- the progress area announces when `auto[Location].html` is ready or created and
  provides its download;
- Resource candidates is section 03 and is scoped to the currently connected
  office package.

## Reconciliation

A completed discovery remains linked to the package that shaped its assignment.
When a connected package genuinely changes, Scout can append reconciliation
against the newer snapshot without repeating discovery or rewriting the original
record. A candidate is omitted as already represented only when exact identity is
supported by an exact website or address. Weaker relationships stay visible for
review.

## Curation enrichment

Stephanie's Information feedback is implemented as a separate, versioned
enrichment stage over an existing `auto[Location].html`. The source artifact is
immutable. Each resource gains Services Provided, Eligibility Requirements, and
How to Best Connect, following the exact approved guidance. Its previous
Information is appended verbatim under Scout Findings. Resource identity,
Description, contact fields, Categories, Types, and For groups do not change in
this stage. The completed work builds a new `auto[Location]-enriched.html` with a
separate artifact identity. See `scout-enrichment.md`.
