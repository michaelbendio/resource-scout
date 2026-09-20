# St. George AND-group and local-check delivery review — September 20, 2026

The workbench now defaults to **Match all selected groups (AND)**. **Match any
selected group (OR)** remains available. This applies to Find resources for and
Category group filters; multiple Types still use OR and the Type/group dimensions
combine with AND. The current selection mode follows navigation and resets to AND
when the file is reopened.

## Corrected assignments

All **12 Deaf & hard of hearing** resources now also have **People with
disabilities**, including Utah Children’s Hearing Aid Program (CHAP). The same
check found missing parent assignments among vision resources: all **13 Blind &
low vision** resources now carry the broader label too.

Nine hearing assignments and six vision assignments were missing that parent;
one resource belongs to both, so **14 unique resources changed**. The broader
group increased from **133 to 147**. There are still **879 resources, 21 Categories,
25 groups, 674 resources with groups and 205 with an explicit no-group proposal**.
No resource facts, Categories, Types, sources or human Curated selections changed.

The correction is durable navigation revision 2, with supporting evidence inherited
from the approved sensory group. The original navigation revision remains history.

| Corrected resource | Existing group supporting the parent |
| --- | --- |
| Utah Children’s Hearing Aid Program (CHAP) | Deaf & hard of hearing |
| Utah Early Hearing Detection and Intervention (EHDI) newborn hearing follow-up | Deaf & hard of hearing |
| Utah Schools for the Deaf and the Blind Parent Infant Program - Southern Utah access | Deaf & hard of hearing, Blind & low vision |
| National Federation of the Blind of Utah Red Rocks Chapter | Blind & low vision |
| Olive Osmond Hearing Fund Here 2 Hear hearing aid assistance | Deaf & hard of hearing |
| Sego Lily Center for the Abused Deaf St. George support, advocacy, and legal-resource navigation | Deaf & hard of hearing |
| Utah DSBVI Low Vision Services | Blind & low vision |
| Utah DSBVI St. George vocational rehabilitation, blind services, and skills training | Blind & low vision |
| Utah DSDHH Southern Utah Program / Southern Center case management, benefits access, classes, and senior events | Deaf & hard of hearing |
| Utah Schools for the Deaf and the Blind Southern Utah School of the Deaf and outreach | Deaf & hard of hearing |
| Utah DSBVI Business Enterprise Program | Blind & low vision |
| Utah DSBVI Deafblind Services Support Service Provider Program | Deaf & hard of hearing |
| The Deaf Hotline by ADWAS and The Hotline | Deaf & hard of hearing |
| Utah Council of the Blind Driver/Guide and Subsidized Transportation Program | Blind & low vision |

## Two local checks in Resource Assistant and generated workbenches

1. Only the two approved hearing/vision → People with disabilities relationships
   are automatic. Both labels must already exist in the office catalog. Search
   includes the parent even for an older imported record; resource editing saves
   the parent tag. The system does not invent groups or infer other overlaps.
2. Resource editing requires an explicit confirmation of all applicable groups,
   or an explicit no-specific-group decision. All 25 St. George definitions appear
   beside the checkboxes and are editable under Admin → For. Changes to relevant
   resource content, Categories, Types, assigned groups or catalog definitions make
   a review outdated. Phone/address/hours-only edits preserve a current review.

Imports and merges retain the resources but show missing/outdated reviews in
Admin → Resources, with Review next. Definitions and review metadata survive
package round trips and Scout's compact browser storage. Merging contradictory
same-time definitions reports a conflict instead of choosing silently. Scout blocks
Curated and selected-resource packaging until the review is current. A scoped
export retains the review date and adjusts its change detector for the smaller
catalog; adding group choices later requires another review.

These checks make approved relationships consistent and require a human group
decision. They do **not** prove complete semantic classification or individual
eligibility. All 879 original resources start without human review stamps; no
human Curated flag was set by this delivery. No AI worker, provider-page extraction,
research or paid service was used. The earlier content/readiness reports remain
applicable except for this explicit navigation and interface change.

## Validation

- Scout: **261 tests**, passed with one existing optional test skipped. An initial
  full run hit the existing macOS process-launch identity timing test; that test
  passed in isolation and the complete suite passed on rerun. No worker-lifecycle
  change was made as part of this group-filter task.
- Resource Assistant: release verification for proposed **2.3.9 build 159** passed:
  **39 Python tests** (two optional skips) and **142 browser self-tests**.
- Additional fresh-profile Chrome checks: **34 Scout + 27 Resource Assistant**
  assertions, plus reload checks for persisted reviews, new-resource no-group
  decisions, all definitions and AND default. These used test-only local edits,
  discarded with the isolated profiles; they did not modify the production data.
- Browser confirmed hearing AND disability gives **12**, switching to ANY gives
  **147**, and CHAP remains findable. Inspected group controls, definitions and
  explicit confirmation in the rendered UI. Tested Curated/export blocking,
  stale reviews, scoped export round trip and unchanged review dates.
- Raw research tables, historical experiment databases and the frozen research
  snapshot match the previous preservation manifest. All **2,421 candidate
  decisions** and sealed curation assignments remain preserved. SQLite quick check
  returned `ok`; source facts and category membership are unchanged.
- Shared local-check JavaScript is identical in Resource Assistant's module and
  Scout's template. The prevention instructions are in
  [workbench readiness](scout-workbench-readiness.md), which AGENTS.md requires.

## Delivery record

Final result fingerprint:
`080bd9563ba0522bba750855e0f227b95aa28cfeb0e3f3d16c2b254586a553d0`

Navigation proposal SHA-256:
`b7352942b6f8f7e2d38ad45ee3c2bbb4e4facbafbdf82c10ea54f34b811f7636`

Master: `data/st-george-curation-20260919/autoStGeorge.html`.
Audit and online backup: `data/st-george-curation-20260919/audit/group-checks-20260920/`.
The evidence JSON alongside this report records preservation, browser checks and
the fourteen corrections. The actual monitor download is checked after recording
this review; its receipt is saved in that audit directory. Existing downloaded HTML
files do not update themselves. Use Save autoStGeorge.html at port **8769** again.
