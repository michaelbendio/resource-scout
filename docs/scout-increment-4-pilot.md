# Provo Food maintenance pilot

Michael accepted the maintenance demonstration and authorized this real pilot on
September 6, 2026. Scout now has two proposed resource updates and one proposed
addition, with dated evidence and explicit decisions on all 31 audit findings.
The proposals await Michael's review. No resource decision, human verification,
production package connection, or package export was made.

## Scope and source

The previously authorized historical Provo v41 package contains 183 resources,
20 categories, and 93 PDFs. Its SHA-256 is
`dc883d19eff7a30e78d33df580ea8408a50788eade33647c40ec6a23f0201a49`.
The pilot uses a separate database in `output/provo-maintenance-pilot/`.

- Recheck `casfb`: Community Action Services And Food Bank - Provo.
- Recheck `facc`: Food and Care Coalition.
- Search `food`: a bounded search for additions, including delivery access and
  identity matches inside existing resource text and other categories.

The known-resource checks focus on Food access. They do not certify every housing,
health, funding, or partner-service claim in these broader records. The other
181 resources and 19 categories were not rechecked. New to this historical
package does not mean newly opened or missing from today's office collection.

Codex completed three primary assignments. ChatGPT, Grok, and Perplexity each
independently audited all three, using their actual services. Codex reconciled
every finding. Perplexity mistyped one character in the discovery assignment
hash; the service reissued that result with the correct hash, and verification
confirmed all research content was unchanged. Original and corrected responses
are retained. There was one category assignment, with no back-to-back category
dispatch or additional pacing wait.

## Proposed changes

| Resource | Proposal | What remains uncertain |
| --- | --- | --- |
| Community Action, Provo | Add Suite 100 and ZIP to the address. | Conflicting official pantry hours, appointment rules, unhoused shopping frequency, satellite locations, dated local service limits, and the recorded food-bank email. |
| Food and Care Coalition | Separate meal and day-service hours; describe meals as open to anyone and distinguish meals from grocery-box referrals. | Hygiene distribution limits, Coalition versus partner case management, housing availability, and partner-clinic conditions. |
| Pantry to Porch | Add a Food resource describing free home delivery and arranged pickup, frequency limits, and the request process. | Phone-only intake, contact without text messages, pickup arrangements, pantry requirements, and household-specific capacity. |

Community Action's [Locations page](https://communityactionprovo.org/get-to-know-us/locations.html)
contains conflicting schedules within the same page. Its
[Food Pantries page](https://communityactionprovo.org/get-help/food-and-nutrition/food-pantries.html)
also combines appointment booking with lobby-intake instructions. The audits
corrected Codex's initial overconfidence that the hours had been confirmed.
Perplexity's claim that booking was absent was not adopted: Codex directly
observed the booking link. No schedule replacement or closure was inferred.

Food and Care's [program timetable](https://www.foodandcare.org/services/food)
supports Sunday/holiday lunch despite the [general contact page](https://www.foodandcare.org/contact)
listing Sunday business closure. ChatGPT caught the overly narrow meal population
in the historical Description; Perplexity emphasized meals versus grocery boxes.
The existing local Information remains intact while conflicting service rules
await confirmation.

All three auditors caught the pickup option omitted from the Pantry to Porch
draft. The [assistance page](https://www.pantrytoporch.org/assistance) advertises
monthly delivery and twice-monthly pickup. Codex also read the linked
[signup form](https://www.pantrytoporch.org/client-signup), without entering data
or submitting it. The final proposal includes third-party requests, approval/text
follow-up, and the conditional CSFP registration requirement. A capacity message
in parsed form content was not treated as confirmed current availability or pause.
Phone contact is not represented as a confirmed phone-only application route.

Thirteen finding dispositions still require human follow-up; several concern
the same underlying issue. The review groups practical questions before the full
auditor details. `lastEvidenceOfOperationOn` stays blank: web observation dates
are not invented dates of actual service delivery. September 13 is a suggested
follow-up date, not an automatic scheduled task.

## Other search outcomes

- Elevate Utah/Centro Hispano and UVU already appear in Food; no duplicates.
- [MTECH's pantry](https://mtec.edu/mtech-pantry/) is a supported student/staff
  service, including Provo campus arrangements. The college already exists.
  Its program boundary, differing timetable blocks, and Food classification
  deserve a separate existing-resource review.
- MAG's existing Seniors entry already mentions meals on wheels. Preserve the
  pending migration decisions; this is a discoverability/classification question.
- [Lasagna Love](https://lasagnalove.org/request/) remains a lead because current
  Provo volunteer availability was not established.

The bounded search is complete with recorded gaps; it is not an exhaustive Food
inventory. Food was the only classification proposed for Pantry to Porch. No
Type or group was invented or forced onto a delivery/pickup intermediary.

## Review artifact and verification

`output/provo-maintenance-pilot/autoProvoMaintenancePilot.html` is a standalone,
read-only review, also copied to iCloud Drive `Documents/TSO` for the iPad viewer.
It shows historical/current wording beside proposals, original local Information,
sources, every audit disposition, follow-ups, and links to the external threads.

Verified:

- All three tasks completed their frozen five-stage workflow, including nine
  independently supplied audits and exactly 31 finding dispositions.
- Source ZIP bytes and all 93 PDFs unchanged; no field, ID, taxonomy, or
  verification-date mutation in the office package.
- Zero human reviews and zero exports; export correctly refuses until the
  current office package is connected.
- Browser review at 1024×768, 768×1024, and 390×844: all expanders open, every
  audit finding is present, source links use HTTP(S), no horizontal overflow,
  no JavaScript errors, and no package-changing controls.

The first narrow-screen check exposed a long-text overflow; the report's wrapping
was fixed and all three sizes passed. This pilot changes no application code, so
the preceding increment's software-suite result remains separate from these
real-data and browser checks.

See [the research manifest](scout-increment-4-pilot-manifest.json) for source and
artifact hashes, actual service threads, final proposals, and preserved audits.
The resumable SQLite database, sealed assignments, raw responses, snapshots,
verification results remain in the pilot output directory. The report builder is
now versioned at `scripts/provo_maintenance_pilot_review.py`.

## Printing feedback and implementation

Michael liked What Scout checked, Questions to settle, the AI introductions, and
the Auditor finding/Scout decision presentation. He prefers a printable reference
while making changes in the office app over editing directly in this report.
He rejected a large full-report printout and requested that the complete screen
report remain available while Print offers manageable handouts.

The Print report button now opens a choice of the overview or one resource.
A resource working copy contains current/proposed wording, Scout's explanation,
and all its questions. A checkbox optionally adds that resource's AI introductions,
sources, findings, and decisions. Existing local notes remain on screen. No
research findings are removed or altered, and no office-editing controls are added.
Browser-menu printing uses the selected handout, initially the overview.

`scripts/provo_maintenance_print_qa.py` exercises the actual report: print and
cancel controls, Escape/focus behavior, optional audit inclusion, all questions,
screen-state preservation, and narrow-screen layout. It generates PDF proofs and
checks their text and page counts. The rendered proofs were inspected for layout.
No full-report PDF is distributed; iCloud receives the updated selectable HTML.

## Grand plan and next discussion

Discuss the pilot, its review burden, and Michael's decisions first. Useful
observations include internal provider-page contradictions, embedded identities,
cross-category gaps, program-specific access, and application-form research.
They remain observations, not active learned rules or phone-vetted outcomes.

Increment 5 is proposed research-method learning from attributable human-vetted
outcomes, subject to the agreed readiness/design review. This small historical
pilot does not satisfy that gate or authorize bulk lesson activation. Increment
6 later adapts category assignment goals, run counts, and stopping decisions.
Scout remains on `v2.0`; v1 and the pending location-app release are unaffected.
