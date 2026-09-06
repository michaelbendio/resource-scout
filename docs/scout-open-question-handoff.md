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
conversion is needed. Valid unknown extension fields are retained. Malformed
questions, duplicate IDs and invalid resolution histories fail visibly before a
package replaces office data.

The common application merges questions by ID independently of other resource
fields. A newer contact edit from an older editor cannot erase questions. Saved
decision history identifies later resolutions and reopenings. Concurrent decisions
keep both notes and reopen the question for a curator to settle; a resource
lastModified timestamp does not decide which curator is right.

Existing-resource exports normally include accepted changes only. The operator
can also export questions without accepting any service changes:

```sh
python3 -m resource_research_agent improve export PROJECT --revision REV --output questions.zip --questions-only
python3 -m resource_research_agent classify export PROJECT --revision REV --output questions.zip --questions-only
python3 -m resource_research_agent maintain export PROJECT --revision REV questions.zip --questions-only
```

This explicit path includes reconciled questions on existing resources even when
the proposed edits are unreviewed or the maintenance decision is Keep. It preserves
service fields, resource timestamps and PDF bytes; it does not create unaccepted
new resource identities or mark anything curated, packaged or provider-verified.
Saved bytes and research state are checked before acknowledgment, and the updated
office package must be reconnected before another export. Its receipt remains
administrative evidence, not acceptance of a research proposal. The existing
review pages retain their usual export behavior; this additional path is an
operator command.

## Preview and validation

`output/open-question-preview/autoScoutOpenQuestions.html` uses the Provo working
copy to demonstrate six open questions across Housing Authority, Financial
Learning, DWS overview and DWS Veteran Services. This adds administrative handoff
only, not new research or answers. It has its own browser storage identity and
retains 183 resources and all 93 PDFs. Source question text is recorded in
`docs/pilots/provo-open-question-handoff.json`.

The high-effort review added regression checks for newer legacy-package edits,
concurrent resolutions, reopenings, malformed and duplicate questions, question
loss across research categories, and administrative-only exports. Scout's full
suite passed 306 tests (one skipped). The resource application verifier passed
42 Python tests and 144 browser self-tests. Dedicated browser QA checks actual
list/editor behavior, Done/Cancel, required resolution notes, reopen history, ZIP
round trip, older and newer package merges, red/bold text, patron-handout exclusion,
and responsive layout. Synthetic QA resolution notes never enter the delivered
seed package.

Michael's September 6 language direction applies generally: explain what Scout
found, why it leaves a question, and what the curator needs to check, in everyday
language with enough detail to act. Reusable writing guidance is now
plain-language-v5; writing, classification and maintenance policies also carry the
rule in their sealed assignments. No fixed word count or place-specific rule is
introduced. Existing sealed assignments and historical research remain unchanged;
older exports can still contain the older finding wording.

The preview's six explanations illustrate the rule using recorded research, not
new provider checks. The revised preview uses `scout-open-questions-preview-v2`
storage so its new seed appears without erasing edits in the earlier preview.
The saved local package, application page and voucher page are described separately
in the housing example; the next step asks about applying, advancing and receiving
help by program. Other questions likewise identify the actual uncertainty and a
practical next step.

Application changes are in `/Users/michaelbendio/resource-assistant-scout-3c`.
Its existing Scout navigation changes remain in place. Michael approved application
version 2.3.7, build 153, subject `Add Scout navigation and curator open-question
handoff`. Version approval was supplied on September 6. Open-question labels and unresolved
question text are red and bold. The editor omits the reminder about every resource
needing curation, as Michael requested. This is not a live office release.

## Next priority

A v2.0 autoMesa run takes priority over expanding Provo. This handoff equips its
curators to see specific unresolved questions while they review every resource.
Michael need only settle Scout design/policy choices; operational/provider
questions belong to the office curator and do not block independent research.
