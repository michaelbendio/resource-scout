# Mesa Employment architecture pilot

The live pilot uses project 1 in `output/autoMesaV2-astra/research.sqlite3`,
with the baseline and fixed sampling configuration recorded beside it. The
old `output/autoMesaV2/` run remains archived, not converted into new-protocol work.

Seven Employment discovery focuses, six existing-resource primary proposals and
twelve discovery proposals were completed and frozen before any Claude assignment
was dispatched. Claude receives original-package inputs in separate incognito
conversations, without Scout's playbooks or new conclusions. Actual responses and
rejected transport attempts remain under `employment/claude/`. Research is still
in progress; freezing or receiving a reply is not category completion or curation.

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

The browser test uses `scripts/check_curator_question_loop.py`; app editor checks
use `tests/open-questions-browser-qa.py` in the common application worktree.
Disposable fixture copies and exact results are in
`output/autoMesaV2-astra/question-loop-qa/`. Synthetic answers are not real calls.
The common release verifier passed 42 Python tests and 145 browser self-tests.
The actual office HTML delivery remains pending; testing a disposable copy does
not establish compatibility of an older iCloud office file.

## Pilot limitation found

Initial primary-pass timing values were rough estimates, not measured effort.
Later zero values mean unmeasured timing, not zero work. Do not use either for
efficiency experiments or ETA calibration. The immutable receipts are preserved;
`employment/timing-quality-note.md` records the limitation. Dispatch/checkpoint
timestamps measure elapsed wall time only. The schema should distinguish unknown
timing before timing-dependent learning experiments.

Next: complete and source-check Claude's comparisons, preserve explicit decisions
against the frozen primary results, and build the small working Employment review.
Proposed lessons and bounded experiments remain subsequent work in the grand plan.
