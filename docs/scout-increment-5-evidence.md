# Increment 5A: capture attributable evidence

Implemented on `v2.0`. Scout now has a separate SQLite evidence ledger and
operator CLI. It observes packages, curator history, and delivery receipts;
it does not edit office resources, activate lessons, or infer human verification.

## Routine project intake (implemented September 6)

Connecting a current package in writing improvement, classification or maintenance
now captures evidence automatically. The existing project connection supplies the
explicit relationship; Scout never guesses a predecessor from a filename or date.
Before resetting reviews, it preserves the previous connected package (or original
baseline), incoming bytes, current project history and export receipts. It compares
these packages and saves a short summary on the project. No separate curator task
or full comparison report is created.

All writes share the package-connection transaction: a failure rolls back both the
connection and evidence. Reconnecting an unchanged package is a no-op. Collection
identity is project-scoped; historical status is inherited and completeness stays
unknown. Older packages without an embedded office name retain their exact bytes
and record the office explicitly confirmed in the project. A conflicting embedded
office remains an error. Cross-project/manual proposal attribution still uses the
explicit operator tools below; the generic discovery upload does not guess lineage.

Only matching delivered export proposals support linked adoption. No review choice
or changed text establishes provider verification. Manual edits remain observations
unless supporting evidence is explicitly linked. The project shows the change and
adoption counts without a new review requirement.

Comparisons in the three workflow pages bold additions/replacements and bold and
cross out removed wording on the current side. Existing links and text are
preserved. Future Mesa evidence and Provo maintenance report builds use the same
highlighter, including print copies; previously accepted reports are not regenerated.
For exceptionally large edits the highlighter bounds its memory and marks the
changed middle passage more broadly, retaining all original text.

Validation: 293 tests passed, one skipped. Regression cases cover all three workflow
connections, missing office identity, exact bytes, retry behavior, rollback and
adoption after an acknowledged export. Maintenance browser QA and comparison
browser QA passed, including safe escaping, links, multiple edits and print styling.

Michael approved the prior evidence distinctions and spot-checked the real Mesa
comparison. His feedback: full-package comparison reviews are too burdensome.
Future review summaries should show a few representative examples and consequential
questions, with changed words bold. Detailed evidence remains available on demand.

Next: select the current working office package and perform a useful office run.
Lesson generation remains pending attributable vetting outcomes and the readiness
review; adaptive research is increment 6. No additional evidence pilot is required.

## Explicit operator use

Use one explicit collection for a related set of office packages. Declare each
package's scope; neither a filename nor a higher version establishes lineage.
The following commands print JSON containing IDs for subsequent commands:

```sh
python3 -m resource_research_agent --database data/research-agent.sqlite3 evidence import prior.zip --collection provo --office Provo --scope full
python3 -m resource_research_agent --database data/research-agent.sqlite3 evidence import later.zip --collection provo --office Provo --scope full
python3 -m resource_research_agent --database data/research-agent.sqlite3 evidence capture-project 1 --collection provo
python3 -m resource_research_agent --database data/research-agent.sqlite3 evidence compare BEFORE_ID AFTER_ID --reviewer 'Operator name' --lineage-note 'How this predecessor was established' --capture CAPTURE_ID
python3 -m resource_research_agent --database data/research-agent.sqlite3 evidence report COMPARISON_ID
```

Use actual package office names and returned IDs. Historical/development inputs
must use `--historical` at import and a separate collection; they cannot be
mixed with production projects. `--scope partial` and `--scope unknown` preserve
uncertainty about coverage. There is no automatic predecessor selection.

The existing normal `import` command is unchanged. This first increment is an
explicit operator workflow, allowing lineage and scope decisions to be checked
before wiring it into routine intake. The curator needs no new scoring or report
editor. Existing review and export protections remain unchanged.

## What the ledger retains

- Original ZIP bytes, attachments, declared scope, and office/collection identity.
- Immutable project captures: complete state, review-event history, assignment
  and policy data, export manifests, exact output bytes, and acknowledgments.
- Field-level before/after observations, including missing versus null values.
- Catalog changes, explicit deletion history/requests, and changed attachment hashes.
- Explicit predecessor decisions and curator-supplied identity links for ID changes,
  merges, or splits. Those identity links do not imply service verification.
- Delivered manual-report proposals with verified artifact hashes and preserved bytes.
- Optional, explicit verification evidence for one changed field at a time.

Review state, delivery, later adoption, and verification remain distinct. A
prepared export that was not acknowledged cannot establish delivered adoption.
A saved title-only export matched in a later package establishes adoption of
that title, not verification of the rest of the resource. Export-time reviews
are identified as such; they are not continuing blanket approval.

Captures retain superseded decisions as history. Select one applicable capture
per project; conflicting attributable proposals remain ambiguous. The ledger
does not pool policy versions. It retains only the researcher/runtime metadata
actually present in the source; missing model-version information is not invented.

Re-imports are idempotent. Known set-valued taxonomy fields are compared without
order; original prose and unknown lists are not normalized. Harmless package
metadata alone creates no field correction. Equivalent observations have stable
event IDs, and repeated copies of the same sourced verification are not counted
as independent confirmations.

## Manual office edits and read-only reports

Use `evidence manual-proposal proposal.json` to register an existing-resource
proposal delivered in a standalone HTML report. Its JSON fields are:

- `collection`, `baseline_id`, and stable `resource_id`.
- `fields`: the exact proposed fields and values, excluding IDs/verification metadata.
- `artifact`: existing file `path`, exact lowercase SHA-256 `sha256`, and timezone-aware
  ISO `deliveredAt`. The file bytes are verified and copied into the ledger.
- `configuration`: the recorded research and guidance versions, with provenance.

This records the operator's delivery assertion and checks the referenced bytes;
it does not prove the recipient opened the file or approved its contents.
Compare a later package using the returned proposal ID as `--capture`. Matching
text and baseline can establish linked adoption, not the reason for a human edit.
Unlinked manual additions remain newly observed resources, not automatically
human-authored discoveries or Scout misses.

## Explicit field verification

`evidence attest verification.json` records an attributable confirmation. Supply
`comparison_id`, `event_id`, `reviewer`, `method`, `note`, and `source`; optionally
`supersedes` identifies a prior verification
record being corrected. Methods are `phone`, `in-person`, or
`provider-written-confirmation`. Source references and notes must identify the
actual evidence and its date; do not use this command merely because a curator
accepted wording. `recordedAt` is the capture time, not an inferred contact date.

The event must be a changed, present resource field, not an absence or an edit
to `verifiedOn`. The ledger never writes `verifiedOn`. Multiple competing
verification records remain unresolved until supersession is explicitly stated.
A field verification is not counted as a fully vetted resource. The readiness
summary therefore says **not evaluated**, rather than fabricating terminal
resource-vetting outcomes or incrementing learning thresholds.

## Validation and demonstration

`tests/test_learning_evidence.py` covers imports/retries, exact values, taxonomy
order, attachment bytes, catalog edits, partial absence versus explicit history,
manual additions, report tampering, collection/development isolation, concurrent
lineage, explicit ID links/splits, policy ambiguity, verification supersession,
title-only approval, writing-workflow receipts, discovery adoption, and CLI use.

The demonstration is generated by:

```sh
PYTHONPATH=. python3 scripts/build_evidence_pilot.py output/scout-evidence-pilot
```

Its five cases use synthetic fixtures. They are not actual provider facts,
curator approvals, or independent AI research. They show an unlinked edit,
delivered proposal adoption, title-only approval followed by adoption, explicit
phone-field evidence, and partial-package absence. The TSO review artifact is
`autoScoutEvidencePilot.html`; the SQLite database and full JSON evidence stay
in the output directory. No production package is connected or changed.

## Grand plan and next increment

Review the demonstration with Michael and discuss any distinctions that do not
match the curator's work. Next, capture one attributable real office sequence
using confirmed package lineage and actual review/delivery records. If provenance
is missing, record observations and the uncertainty; do not manufacture a match.

Only after reviewing that experience should we consider routine intake integration
and evaluate readiness for method interpretation. The agreed 25-outcome,
three-category, 15-accepted-candidate, 90%-provenance review remains in force.
JSON/Markdown lesson proposals, evaluation/activation, and adaptive category run
planning remain later work.

## Real Mesa package comparison (September 6)

After approval of the synthetic demonstration, the evidence reader was exercised
with the two saved AutoMesa packages surrounding the Stephanie revisions.
`docs/pilots/mesa-package-evidence-manifest.json` records exact source hashes,
package evidence IDs, dates, intake warnings and the comparison summary.

Both contain the same 333 resource IDs. The ledger observed 333 Description and
333 Information changes, with no additions, absences or other compared changes.
A sampled Description adds service geography; its Information changes the first
heading to Programs and Services and incorporates program entries. This is
consistent with the documented Stephanie revisions, but is not independent proof
of an editing/export chain or individual curator acceptance.

No attributable proposal receipts or provider confirmations accompany this pair.
All 666 changes remain observations: zero linked adoptions, zero explicit field
verifications, zero inferred resource-vetting outcomes, zero activated lessons.
Completeness is recorded as unknown and the collection is historical. Directly
authorized writing guidance is not counted as repeated successful research.

The older schema-3 package has a string packageVersion (`"2"`). Evidence intake
now accepts a canonical ASCII nonnegative integer string while retaining its type,
raw JSON and exact ZIP bytes, and records an intake warning. Normal package reads,
updates and exports still require an integer. No schema-2 compatibility was added.

Reproduce (from the repository root, with PYTHONPATH=.):

```sh
python3 scripts/build_package_evidence_review.py BEFORE.zip AFTER.zip OUTPUT \
  --office AutoMesa --collection mesa-stephanie-historical \
  --lineage-note 'Describe the basis and limits of this selected sequence.'
```

The script is deliberately a historical observation review, not a live-vetting
importer. It writes the evidence database, complete JSON report and
`autoMesaEvidencePilot.html`. Resource details expand on screen. Print includes
only the overview. The published review is in the TSO folder; source ZIPs were
not changed.

Validation: regression coverage checks original bytes/type, comparison across
legacy and integer versions, malformed values, and continued strict normal
intake. Responsive browser checks cover 390/768/1200 pixels and print visibility.

Next discussion: routine intake should capture packages and available decision
receipts together. Missing attribution must remain visible. Actual phone-vetted
final packages are still needed before the research-learning readiness audit;
adaptive category assignments remain later in the grand plan.
