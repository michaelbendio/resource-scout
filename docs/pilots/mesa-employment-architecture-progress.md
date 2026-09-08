# Mesa Employment architecture pilot

The live pilot uses project 1 in `output/autoMesaV2-astra/research.sqlite3`,
with the baseline and fixed sampling configuration recorded beside it. The
old `output/autoMesaV2/` run remains archived, not converted into new-protocol work.

Seven Employment discovery focuses, six existing-resource primary proposals and
twelve discovery proposals were completed and frozen before any Claude assignment
was dispatched. Claude receives original-package inputs in separate incognito
conversations, without Scout's playbooks or new conclusions. Actual responses and
rejected transport attempts remain under `employment/claude/`. All seven pilot
tasks are now reconciled: six resource rechecks and one discovery assignment.
This does not complete Employment: 36 of its 42 original resources remain.

## Research outcome

The working review contains six updates and twenty new proposals. The primary
freeze found twelve new programs. Claude's ten discovery items contributed seven
additional programs, two overlaps and one program already in the original package
(Ability360 Benefits2Work/WIPA). A separate Claude Goodwill recheck identified
The Excel Center; its independent origin remains explicit. No proposal was marked
Curated, approved, phone-verified or automatically made into an active lesson.

Reconciliation corrected the older VA page's overbroad 12-year eligibility rule,
separated Copa customer billing from participant wages, verified accessible DES
contact routes and appeal timing, and used an updated apprenticeship list.
Concrete eligibility and access questions remain where sources did not settle
them. Raw rejected replies and corrected responses are preserved; format errors
were not accepted as valid research. Future assignments now explain the required
category-to-Type mapping and which statuses permit field updates.

## Curator feedback loop verified

Common application branch `scout-3c`, commit `5912233`, version 2.3.7 build 154:

- The editor asks **What did you find out?** and prompts for how the answer was
  checked, when a provider was contacted, and related resource edits.
- Progress notes save while Resolved is unchecked. Resolved questions remain
  editable inside a collapsed group. Done, Cancel and reopening preserve history.
- A disposable two-instance test exported the actual ZIP from autoMesaV2, merged
  it through the office application's ZIP importer, reloaded the office, exported
  again and imported into Scout's evidence ledger. Exact question identity, text,
  explanation, sources, answers, dated history and PDF hashes survived.
- Repeat import, an older unanswered package, and a newer legacy contact edit
  did not erase the resolution. The decision was recorded as an observed change,
  without automatic provider verification or active lesson creation.

The Scout review template now uses the same question module and styles, copied
from the common application with `scripts/sync_review_questions.py`. Its editor,
validation and merge hooks preserve Scout's separate curation controls. The
roundtrip was repeated in actual Scout curation mode: an answer edit invalidated
Curated, the selected resource alone was exported, saved answers survived a
review reload, and the office retained unrelated resources. Exact results are in
`question-loop-qa/scout-roundtrip/` under the pilot output directory.

The browser test uses `scripts/check_curator_question_loop.py`; app editor checks
use `tests/open-questions-browser-qa.py` in the common application worktree.
Disposable fixture copies and exact results are in
`output/autoMesaV2-astra/question-loop-qa/`. Synthetic answers are not real calls.
The common release verifier passed 42 Python tests and 145 browser self-tests.
Stage 3 publication subsequently passed for all three iCloud office HTML files:
Mesa, Provo and Albuquerque, version 2.3.7 build 154, commit `5912233`. Original
office shells were backed up in the pilot output directory. No office resource
package or real browser curation state was modified by the synthetic checks.

## Working review delivery

`scripts/build_maintenance_review.py` renders completed maintenance research in
the real Scout template without creating a curation job or approval. It preserves
original IDs, unknown fields, prior question answers/history and exact attachments.
The renderer blocks stale revisions, newer conflicting office edits, incomplete
research and uncertain closure decisions. Content-scoped browser storage isolates
different drafts. An embedded attachment never overwrites a curator's replacement.

The 26-resource artifact passed the actual ZIP question loop, all three editors,
initial Curated count zero, 390/768-pixel layout, and exclusion of administrative
questions from patron printing. A separate synthetic attachment test exercised
the new renderer and preserved a replacement PDF through reload. The companion
report has bold wording changes; its default overview prints on two Letter pages,
and individual resource reviews can be printed separately.

Artifacts and manifests are in `output/autoMesaV2-astra/employment/delivery/`;
browser evidence is in `employment/delivery-qa/`. The full Python suite passed
342 tests with one existing skip. A pre-existing ZIP byte-equality assertion
was corrected to compare data and attachment bytes rather than variable ZIP
header timestamps. Synthetic evidence stays separate from the research ledger.

## Pilot limitation found

Initial primary-pass timing values were rough estimates, not measured effort.
Later zero values mean unmeasured timing, not zero work. Do not use either for
efficiency experiments or ETA calibration. The immutable receipts are preserved;
`employment/timing-quality-note.md` records the limitation. Dispatch/checkpoint
timestamps measure elapsed wall time only. The schema should distinguish unknown
timing before timing-dependent learning experiments.

Next research: continue the remaining original Employment resources, then the
remaining Mesa categories, keeping the original seed and sampling history.
Cross-category duplicate checks must include the pilot's pending proposals as
unapproved leads; do not treat them as curated baseline facts or show them to the
blind researcher. Report a new whole-run estimate after six completed categories.

The next implementation increment in the grand plan remains proposed lessons and
bounded experiments. Pilot observations are inputs for that discussion, not an
automatic playbook activation or a claim that the adaptive learning engine exists.
