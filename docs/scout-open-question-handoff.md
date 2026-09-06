# Open questions: curator handoff

Michael guides Scout's design; he is not the office curator. Open questions are
specific issues Scout identified but could not settle, not a substitute for full
curation of every resource. The approved admin-list wording is `open question`
or `N open questions`, beside the name. The resource editor shows each question
and why it remains unresolved. Patron views and printable resource cards omit
these administrative fields.

## Implemented

Resources carry an optional `openQuestions` array. Each question has a stable ID,
question, explanation, source reference, status and resolution note. The resource
editor can save a short resolution note and mark Resolved, or reopen it. These
changes use the existing Done/Cancel/save/history lifecycle and do not update
Verified. Resolution history stays with the resource. No badge means no recorded
open questions, not that the resource has been verified.

Scout curation assignments now request concise `question`/`explanation` pairs.
New-resource normalization assigns IDs and open status; model-supplied resolution
fields are rejected. Writing/classification exports preserve unresolved audit
findings and their reconciliation explanations; legacy finding text is retained
rather than paraphrased without evidence. Maintenance exports preserve their
follow-up questions and summaries. Existing curator resolutions survive when
Scout encounters the same question again. Earlier sealed exports are not rewritten.

The reader treats the field as an optional resource extension; no old package
conversion is needed. Unknown question data is retained. Resource-level
lastModified continues to govern package merge conflicts: an older package
cannot undo a newer resource's resolution. This does not introduce independent
per-question concurrent merging. Full resource conflict handling remains the
normal office workflow.

## Preview and validation

`output/open-question-preview/autoScoutOpenQuestions.html` uses the Provo working
copy to demonstrate six open questions across Housing Authority, Financial
Learning, DWS overview and DWS Veteran Services. This adds administrative handoff
only, not new research or answers. It has its own browser storage identity and
retains 183 resources and all 93 PDFs. Source question text is recorded in
`docs/pilots/provo-open-question-handoff.json`.

Scout's full suite passed (297 tests, one skipped); the additional new-resource
curation test then passed with its focused suite. The resource application
verifier passed 42 Python tests and 139 browser self-tests, and the dedicated
`tests/open-questions-browser-qa.py` passed actual list/editor, note validation,
Done/Cancel, reopen history, package round trip, old-package merge, responsive
layout and patron-handout exclusion checks. Browser-only resolution notes are
explicitly synthetic and are never written to the delivered seed package.

Application changes are in `/Users/michaelbendio/resource-assistant-scout-3c`.
Its existing Scout navigation changes remain in place. Proposed application
version is 2.3.7, build 153, subject `Add Scout navigation and curator open-question
handoff`. Application commit requires Michael's version approval under that
checkout's AGENTS.md. This is not a live office release.

## Next priority

A v2.0 autoMesa run takes priority over expanding Provo. This handoff equips its
curators to see specific unresolved questions while they review every resource.
Michael need only settle Scout design/policy choices; operational/provider
questions belong to the office curator and do not block independent research.
