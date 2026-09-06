# Mesa program-title pilot

Michael approved a bounded review of the five A New Leaf entries in the saved
`autoMesa-enriched.html`, following approval of the program-label and research
refinements. The source contains 333 resources, no attached PDFs, and retains
its AutoMesa office name and package version 3.

## Results for discussion

- Three title proposals: Autumn House domestic violence housing, MesaCAN rent
  and utility assistance, and East Valley Men's Center shelter.
- One conditional title: Workforce Center @ Mesa. The City of Mesa entry already
  describes that center; review whether the A New Leaf record is a distinct
  service before making duplicate entries appear intentionally distinct.
- Michael's requested title: A New Leaf · Clothing, furniture and household
  essentials. The revised review assesses each service separately: interview
  clothing is a supported lead; furniture and household-item recipient routes
  remain unestablished. Preserve the other MesaCAN record's hygiene/diaper
  details as local leads. No automatic deletion or merge follows from partial
  uncertainty, and the original resource remains unchanged.

The City's workforce page advertises a clothing boutique and lists a 2:30 PM
closing time; MesaCAN lists workforce self-service ending at 1:30 PM. The
conflict becomes a question, and the donor information is not taken as proof
of public furniture access. Original local notes remain intact. The report also
flags separately described VITA services and an employer-only interest form.
See the source-linked observations and complete original records in
[pilot review data](pilots/mesa-program-title-review.json).

## Scope and limitations

This was a focused Codex web review using the approved `plain-language-v2` and
`maintenance-v2` guidance. The exact guidance is retained with the results.
It is not an end-to-end maintenance workflow run: there are no sealed workflow
assignments or fabricated audit responses. ChatGPT, Grok, and Perplexity audits
were not performed because the browser connector reported Chrome unavailable.
The limitation was disclosed during work and appears in the report.

The input is the saved HTML's embedded data, not unsaved browser edits. Source
HTML bytes, all stable IDs, names, local notes, classifications, and verification
dates remain unchanged. No new resource, office package, provider contact, or
application submission resulted. The EVMC form could not be read; utility
application contents were outside this focused recheck. Historical donation PDF
search-index evidence is labeled as such, not a current recipient-access check.

## Reproduction and validation

The versioned JSON contains the original five records, four related records,
eight source observations, source hash, guidance snapshot, and decisions.
Build the standalone read-only report with:

```sh
python3 scripts/build_program_title_review.py \
  docs/pilots/mesa-program-title-review.json \
  output/mesa-program-label-pilot/autoMesaProgramTitlePilot.html
```

The frozen source HTML is in `output/mesa-program-label-pilot/source.html`.
The QA script takes review JSON, source HTML, generated report, and QA directory
as its four arguments. It needs Playwright, Chrome, and Poppler. It checks exact
source/record preservation, all five decisions, all questions in printed output,
print/cancel/Escape behavior, original screen state, and 390/768-pixel layouts.
All 11 print choices passed: overview and individual working copies are one
page each; optional notes and sources are one or two pages. All 13 rendered
proof pages and the phone layout were inspected. PDFs are QA proofs only;
TSO receives just `autoMesaProgramTitlePilot.html`.

## Grand plan

Discuss these five decisions with Michael before applying any title change.
Distinguish approval of a title from confirmation of service availability or
resolution of the other questions. Next assess what the pilot shows about the
approved guidance. Research-method learning and adaptive category run planning
remain later increments with their established evidence/readiness review;
this focused Codex review does not manufacture independent or phone-vetted
outcomes toward that gate.

## Patron-usefulness follow-up

Michael requested briefly listing all meaningful resource types, and reasoning
from usefulness to TSO patrons without a special donation rule. The follow-up
uses `plain-language-v3` and `maintenance-v3`; initial guidance and decisions
remain traceable through the original snapshot and Git revision history. Four
other title decisions are unchanged. No independent audits were performed.

Codex rechecked the City workforce, donor, Rapid Rehousing, and MesaCAN pages.
The requested title is shown in full. A new What a patron can receive section
separates the three services and their access evidence. The published center
contact is identified as a general contact, not a confirmed boutique intake
line. The other MesaCAN record's hygiene/diaper details remain local knowledge
to investigate. A donor form is not presented as a patron request route.

The 63 targeted writing/curation/improvement/maintenance tests passed. All 11
browser print choices passed, including checks that every per-service finding
survives printing. Working copies remain one page each; optional source notes
remain at most two pages. These tests check guidance integration and artifact
integrity; model judgment is assessed through this real review, not simulated
by a keyword rule or a fabricated model response. Discuss the result with
Michael before advancing to research-method learning and adaptive assignments.
