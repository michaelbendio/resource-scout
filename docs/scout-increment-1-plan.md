# Increment 1 implementation plan: better resource writing

Status: implemented on `v2.0`, September 5, 2026; human pilot review pending.
The six-increment roadmap and Express writing example are approved. This is the
approved implementation plan, with baseline observations retained below.
See the [implementation and validation results](scout-increment-1-results.md).

## Outcome and scope

Normal Scout curation will produce concise Description and Information text in
the [approved style](scout-writing-example.md). The generated review file and its
printed resources will show the five agreed Information sections. New resources
will not require a separate enrichment job merely to obtain that structure.

The deliverable is versioned writing guidance, its integration into curation,
automated regression coverage, and a small editorial/print pilot for discussion.
Existing-resource package updates belong to increment 2; taxonomy improvements
belong to increment 3. Discovery strategy, researcher roles, pacing, adaptive
learning, and missionary problem-report forms are outside this increment.

## Development isolation and baseline

- Develop on branch `v2.0` in `/Users/michaelbendio/resource-scout-v2`.
- Keep `/Users/michaelbendio/resource-scout` on `main`, with its runtime and data
  available for the existing Scout line. The branch starts at `a3cb004`; that
  source declares version `0.50.0`, build 17. The user's 1.0/2.0 distinction names
  the established and new development lines, not an already completed version
  bump or release.
- Keep `/Users/michaelbendio/resource-scout-enrichment` and its completed Mesa
  database, later commits, and unfinished batch-audit changes intact. This
  increment does not require merging that checkout's work. Its full-package
  export addition and Windows prompt fix are separate baseline-integration
  decisions, not prerequisites for writing guidance.
- Use temporary test databases and disposable pilot artifacts. Never point a
  v2 process at either existing database or install/restart the current service.
  Use a separate local port if browser testing needs a server.
- Keep generated examples and exports visibly associated with the pilot, away
  from live office files. Do not publish, replace office packages, or deploy the
  current service as part of validation.

Baseline check completed in the isolated v2.0 checkout: `python3 -m unittest
discover -s tests` ran 181 tests in 19.520 seconds, with 180 passing and one
skipped. The skipped test requires `PROVO_RESOURCE_PACKAGE` for a live-package
check. This baseline establishes the starting point; the results document
records the additional writing tests and integrated validation.

## What the baseline code already provided

`scout_curation.py` creates immutable category assignments, validates candidate
coverage and resource identities, saves results, and builds review seeds. Its
current output contract accepts free-form `description` and `informationText`;
it does not enforce the approved writing structure.

`storage.py` already stores assignment JSON/hashes, result JSON/hashes, canonical
research-run links, and progress. Job reuse currently depends on the import,
candidate-package hash, and assignment version. These records can preserve the
writing guidance without adding a general learning subsystem.

`scout_review.py` builds Scout's owned HTML template. That template already
renders bold Information headings, plain paragraphs, and bullets in the resource
view and print workflow. Its resource schema has phone, address, website, and
hours, but no dedicated email field. Legacy `scout_enrichment.py` follows a
different contract that appends original Scout Findings; keep that versioned
behavior intact for existing projects.

## Implementation steps

### 1. Add a small, versioned writing-guidance bundle

Proposed files:

- `resource_research_agent/writing_guidance/default.json`: guidance/schema
  version, stable section keys and exact headings/order, and the Markdown
  instruction reference.
- `resource_research_agent/writing_guidance/plain_language.md`: audience,
  Description guidance, brevity, meaningful uncertainty, concrete next steps,
  appropriate placement of details, and preservation of material conditions.
- `resource_research_agent/resource_writing.py`: generic loading, validation,
  canonical hashing, section validation, and Information composition.

Resolve and validate the complete bundle once when preparing a job. Store its
exact JSON and Markdown content with the assignment. Do not reload mutable
files when resuming an existing job or validating its result. Fail visibly if
the selected bundle is missing, malformed, or unsupported; do not silently fall
back to the older writing style.

The bundle is reviewed guidance shipped with v2.0. No active-lesson registry,
automatic approval, or learned policy selection is needed in this increment.
Keep the approved Express example as an editorial reference and test fixture;
do not inject its provider names, contact details, or requirements into unrelated
resource assignments.

### 2. Introduce a structured curation response for new assignments

Add a new curation assignment/result contract alongside the legacy contract.
Each proposed resource returns its ordinary fields plus `informationSections`
with these keys:

| Key | Printed heading |
| --- | --- |
| `programsAndServices` | Programs and Services |
| `eligibilityRequirements` | Eligibility Requirements |
| `howToBestConnect` | How to Best Connect |
| `access` | Access |
| `importantInformationToKnow` | Important Information to Know |

Each value is a nonempty string containing plain paragraphs and optional simple
bullets. The model supplies section bodies; the composer supplies headings and
order. Reject missing/unknown keys, malformed values, and a competing free-form
`informationText` in the new response. Validate a nonempty Description. Detect
reserved section headings pasted into section bodies, including legacy Scout
Findings and Services Provided headings; do not reject ordinary prose merely
because it contains those words.

The composition result remains the existing package `informationText` string,
using the template's supported `**heading**` and bullet syntax. Preserve Unicode
and paragraph boundaries. Keep the package schema unchanged.

Where a material detail is unknown, ask for a short resource-specific statement
or question, not an invented fact or a repeated generic disclaimer. Exact
wording, semantic duplication, appropriate section placement, and factual
faithfulness require editorial evaluation; section validation cannot prove them.
Do not impose a universal word count or reading-grade pass threshold.

Map Description, phone, address, website, and hours to their existing fields.
Put a useful email address under How to Best Connect because there is no email
field in the current package/rendering contract. Keep the approved reference
document unchanged and show this presentation adaptation in the pilot. Do not
invent a new field that normalization would silently discard.

### 3. Integrate guidance, provenance, and compatibility into curation

Update `_assignment`, `prepare_scout_curation_job`, and
`save_scout_curation_result` in `scout_curation.py`:

- Include the resolved writing bundle, its digest, the required result schema,
  and the writing output contract in each new assignment.
- Include the guidance digest in durable job identity. Prefer an effective
  `assignmentVersion` composed from the curation contract version and guidance
  digest, using the existing storage uniqueness key. Store the base contract
  version and expected result schema explicitly, so validation does not guess
  them from a version-string prefix. Guidance edits must not reuse a job created
  with different text, even if a human forgets to change its version label.
- Validate and compose the five sections before saving any completed result.
  A rejected result leaves the category available for correction; it does not
  mark the job complete or destroy its assignment.
- Preserve source responses and original candidate text in the sealed
  assignment. Preserve the structured section response in result-level writing
  metadata keyed by resource ID, outside exported resource fields. Record
  supporting source references and any new source material consulted during
  curation there, rather than dropping that evidence during normalization.
  This is evidence storage, not automatic fact verification.
- Preserve candidate-to-resource and canonical-run links. The writing change
  must not alter candidate coverage, omission rules, resource identity,
  categories, groups, attachments, or existing cross-category merge behavior.
  Check that final merged resource text still has the required structure.
- Dispatch legacy/new validation from the sealed assignment contract. Pending
  and completed legacy jobs continue to use their original contracts and text.
  Preparing a new job under the writing bundle does not rewrite an old job.
- Keep generated `verifiedOn` unset for new AI-curated resources; a writing
  pass cannot establish a human verification date. Retain old jobs unchanged.

The writer may use the candidate evidence and research available to curation.
Additional research must have recorded sources; sparse evidence must remain
visible as uncertainty. Existing research completion and human-vetting gates
remain in force. Formatting success does not satisfy an outstanding audit or
establish that a resource is verified. Do not reuse the legacy enrichment
composer or run its Scout Findings append as the new writing path.

### 4. Exercise the existing review and package path

Send composed resources through `build_scout_review_seed` and
`build_scout_review_file`. Keep writing provenance in Scout records rather than
adding internal policy text or source audits to the missionary handout.

Expect the existing renderer to support the new text without a template redesign.
If the actual pilot reveals a rendering defect, fix the smallest necessary part
of Scout's owned template and add a regression case. Separately record any
location-app change needed; do not edit generated live `provo.html` or
`albuquerque.html` as a shortcut.

Confirm that marking Curated, editing, printing, saving a selected package,
reloading, and reopening that package preserve the resource content. This
increment continues to produce reviewed additions; safe updates to accepted
office resources remain increment 2.

## Automated test plan

Use the repository's Python `unittest` suite and existing Node-based JavaScript
test approach. Use temporary directories/databases, fixed response fixtures,
and controlled timestamps. Tests must not call paid models, depend on live
provider sites, or modify live office data.

| Area | Meaningful cases and expected result |
| --- | --- |
| Guidance loading | Valid JSON/Markdown resolves; missing files, unknown schema, duplicate section keys, and malformed definitions fail with useful errors |
| Guidance identity | Editing Markdown while leaving its version label unchanged creates a different job identity; identical guidance and input reuse the job |
| Durable resume | After job preparation, change or remove guidance files; existing assignments still use their stored text, including categories not yet assigned |
| Legacy compatibility | Explicit legacy fixtures resume, accept legacy results, and build unchanged resources; completed enrichment projects still preserve their original Scout Findings contract |
| Structured response | Reject missing/blank sections, wrong types, unknown keys, pasted reserved headings, and conflicting free-form Information; do not mark completion |
| Result binding | Wrong assignment digest, category, or schema is rejected; a result from another writing revision cannot be saved into this job |
| Composition | Exact headings appear once and in order; bullets, accents, apostrophes, middle dots, URLs, and line breaks survive; HTML-like source text is escaped in the rendered view |
| Field and evidence preservation | Contact fields, resource IDs, candidate links, PDFs, and taxonomy survive serialization; original text/evidence stays in Scout, while writing metadata stays out of the exported resource |
| Verification semantics | A new AI response cannot supply a human verification date; writing-policy changes do not modify old records or source-package files |
| Cross-category reuse | The same resource reused by a later category retains identity and accumulated candidate links; its final Information still meets the new contract |
| Pipeline integration | A fixture candidate package goes through assignment, response validation, storage, completed-job seed, and HTML generation; its required text is actually in the generated resource |
| Review/package round trip | Selected curated resources retain Description, five sections, email text, contacts, and PDF references through package export/import; untouched resources and source snapshots remain unchanged |
| Existing review behavior | Curated defaults, edit invalidation, cancellation, reload, and office/artifact isolation continue passing their existing tests |

Put loader/composer cases in `tests/test_resource_writing.py`; extend
`tests/test_scout_curation.py` for versioning, provenance, integration, and legacy
dispatch. Add `tests/test_scout_writing_rendering.py` to exercise the actual
Information rendering functions with representative text. Extend existing
review persistence/export tests only where the new content needs an assertion.
Keep legacy enrichment tests as legacy tests instead of rewriting them to expect
the new format.

Use the approved example as an exact composer/rendering fixture, not an
expectation that a live model must reproduce identical prose. Add editorial
fixtures with source text, must-preserve facts, and prohibited unsupported
inferences. These document evaluation criteria; a substring match alone cannot
certify semantic accuracy.

Run targeted suites while implementing, then the complete existing suite once
the integrated change is ready:

```sh
python3 -m unittest discover -s tests -p 'test_resource_writing.py'
python3 -m unittest discover -s tests -p 'test_scout_curation.py'
python3 -m unittest discover -s tests -p 'test_scout_writing_rendering.py'
python3 -m unittest discover -s tests -p 'test_scout_enrichment.py'
python3 -m unittest discover -s tests
git diff --check
```

## Editorial and printed-output pilot

Prepare six cases: the supplied Express text, a shelter, a food pantry, a
government assistance program, a resource with limited confirmed details, and
a resource with important geographic or access conditions. Select actual source
material from saved research where available and record its identity/date;
fictional edge cases must be labeled synthetic. Do not present historical facts
as newly verified. Keep the full approved Express text unchanged in its reference.

Run the new writing instructions on the bounded source cases. Preserve each
exact input, assignment, output, and edit in a disposable pilot directory.
An offline pilot harness can use explicitly scoped fixtures without changing
the production requirement that research be complete before normal curation.
Fixture completion must not be recorded as fresh research or audited evidence.

For each result, compare it with its source and check:

- Help offered and geographic scope are quickly understandable.
- Requirements, costs, limitations, documents, and useful local details survive.
- Contact routes and next steps are supported, with no invented appointment,
  eligibility, timing, transportation, language, or benefit promises.
- Services and application instructions are not repeated across sections.
- Material uncertainty is brief and actionable; the writing remains respectful.
- Contact details and the five Information sections remain usable on paper.

Inspect generated resource views, Admin previews, and print previews in a real
browser. Inspect a US Letter print-to-PDF output for readable text, working line
wrap, complete phone/address/URL/email text, and acceptable page breaks. Include
a multi-resource selection. Do not force a one-page result by shrinking text or
dropping necessary conditions. Browser/print inspection supplements the tests;
it is not satisfied by inspecting HTML source or Node output alone.

Discuss the six results with Michael, including editing needed and any facts
that were lost or overstated. Record the guidance changes that follow and rerun
affected cases. Pilot approval must come from that discussion, not a model's
self-score. No dedicated missionary feedback form is introduced.

## Completion and next checkpoint

Increment 1 is complete when the normal curation path uses the saved guidance,
automated tests pass, legacy behavior remains usable, the source-to-handout
pilot has no unresolved material errors, and Michael has reviewed the resulting
content/print experience. Report automated validation separately from real-use
experience still to be gained.

At the checkpoint, remind Michael of the grand plan and discuss increment 2:
safe improvements to existing resources. Bring concrete lessons about writing,
review effort, and printing to that discussion. Do not start increment 2 merely
because this roadmap lists it.
