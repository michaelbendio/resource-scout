# Welfare Square Housing — kinds-checklist trial

**TRIAL — NOT FOR IMPORT.** Prepared 30 September 2026 from public sources on main
`2112171`. Branch: `codex/welfare-square-housing-kinds-trial-20260930`.

Start with the [judging sample](results/judging-sample.md): **all 16 prepared usable
resources**, in a reproducibly shuffled order. The trial has **10 starters covering
8 of the 9 original kinds**, compared with **2 of 9** in the delivered Housing
starter set. One proposed new kind covers tenant navigation and mediation.

- [Prepared Housing JSON](results/scout-welfare-square-prepared-resources-26-09-30.json)
- [Content review and important limitations](review/content-review.md)
- [Research decisions, exclusions and gaps](research/decisions.json)
- [Recorded metrics](metrics/run.json) and [baseline measurements](review/baseline-comparison.json)

## Comparison

| Measure | Current delivered Housing | Checklist trial |
| --- | --- | --- |
| Original kinds covered by starters | 2 / 9 | 8 / 9 |
| Leads researched / preparation input | 85 raw discovery rows; 72 consolidated candidates | 21 named routes investigated; 16 prepared, 5 not selected/deferred |
| Final prepared/reviewed resources | 53: 52 usable, 1 administrator-only | 16 usable; no administrator-only records in this trial export |
| Starters | 10 | 10 |
| Non-starters with reasons | 43 memberships | 6 |
| Model calls | Full count unavailable; 7 saved research contributions, not necessarily 7 calls | One interactive Codex session; inference-call count unavailable; 0 separate model API/worker calls |
| Wall-clock time | Research interval 5 h 5 m; Housing curation interval 21 m 39 s; review time not separately attributable | 20.1 minutes from recorded trial start through content review and six passing checks; setup and final report/publication extra |
| Cost | Housing-only total unavailable | $0 additional direct model API charges; Codex subscription/token allocation and tool cost unavailable, so total cost is **unknown** |
| Human judging | Earlier production delivery | Pending Michael's verdicts |

These are not controlled performance measurements. Research rows and investigated
routes are different units. The baseline clocks include waiting, and its review
ran across an entire office. The trial used this Codex session with Scout's existing
preparation contract and semantic review instructions, rather than paid worker
launches. Do not extrapolate a whole-office dollar estimate or speed multiplier.
The initial clock starts after setup/main pull; metrics record that boundary.

The current baseline was read from the accepted `welfare-square-fresh-20260928-r2`
delivery, not an old workbench. Its frozen Housing projection and full-delivery
checksum are in [inputs/baseline-housing.json](inputs/baseline-housing.json).
The checksum was rechecked after the trial; production output was unchanged.

## Coverage and starter choices

| Original Housing kind | Current starters | Trial starter |
| --- | --- | --- |
| Public housing authority | Housing Connect, HASLC | Housing Connect |
| Rent and deposit assistance | UCA, DWS; narrow TRC relocation route | Utah Community Action |
| Transitional housing | No specific residential program in starter contribution | HomeInn and LifeStart Village |
| Home repair | None | ASSIST |
| Homebuying help | None | CDCU |
| Veterans' housing | None | The Road Home SSVF |
| Low-cost shared housing for fixed incomes | None | **Gap** |
| Rental listings and extended-stay hotels | None | AffordableHousing.com rental search |
| Crisis sheltering for pets | None | Ruff Haven |

The tenth starter is **Salt Lake City Tenant Resource Center**, selected for the
proposed additional tenant-support kind. Its narrow relocation assistance is not
treated as a second general rent program. Two transitional starters are justified:
HomeInn's single rooms and LifeStart's single-parent apartments serve materially
different households. The original starter set's five emergency-shelter entries
were not counted as checklist housing programs merely because they offer housing
case management.

The first five proposed complements are **Milestone** (young adults), **HASLC**
(another authority/property portfolio), **Habitat repairs**, **UCA mediation** and
**Salt Lake City repairs**. **WoodSpring Bluffdale** follows as a paid extended-stay
option with cost and travel cautions. Every non-starter has its own exported
`considerations` reason. This ordering is a trial suggestion, not a change to
WSRS-TSO's import or ordering behavior.

## Gap and proposed addition

**Fixed-income shared housing:** not established in this bounded pass. Checked the
local lists, the Provo example “One New Light,” targeted Salt Lake searches, historic
Road Home shared-housing material and Aspen Living. Aspen's current indexed pages
leave important questions about HRSS/Medicaid admission and ongoing rent. Neither
shared amenities at HomeInn nor a historical program proves this kind is currently
available to an ordinary fixed-income applicant. The full attempts and URLs are in
the research ledger. This is not a claim that no such service exists.

**Add tenant support and eviction prevention:** the city navigator and UCA mediation
help with tenancy problems independently of receiving money or obtaining a new
unit. Their distinct direct intake routes justify two program records. This is a
proposed checklist/Type addition only.

## Method and boundaries

Read five list pages from four publishers: Salt Lake City, Salt Lake County, Utah
211 and South Salt Lake. Merge repeated seeds, map the nine kinds, apply all four
office-fit rules, then check provider intake pages. Use narrow searches only for
missing kinds or a consequential uncovered client need. Stop once each kind has a
supported route or a documented gap. The expected 20–30 is not a quota: this trial
stopped at 16 prepared records.

Church resources were checked through the official locations index and locator
entry points. No direct Housing service was established there. The welfare locator
could not be read, which is recorded as a limitation rather than a negative claim
about Church assistance. No general web search substituted for that locator check.

The comparison was not blind: the baseline was available and its Aspen entry
prompted a final targeted gap check. Its descriptions, approvals and identities
were not recycled into the prepared records. No agency was called, contacted or
sent a form; no live availability is implied.

To repeat the **method** elsewhere, change the office/service area and use that
category's checklist; find its own local lists, then follow the same capped
selection, evidence, preparation and review steps. The builder packages the authored
trial decisions; it is not a new autonomous Scout research engine. Production
pipeline prompts and policy were not changed by this experiment.

## Format, identity and validation

The file uses the prepared-resource envelope, five Information sections, source
catalog/references, category ID `housing`, Types, groups, starters and considerations.
`evaluationOnly: true`, `importable: false`, explicit trial notes and code-assigned
`trial_` IDs keep it separate from production. `completeOffice` and `completeScope`
are false. The production validator rejects it even if the evaluation flag is
removed, because these are provisional identities. No production registry entries,
identity migrations, human Curated flags or verification dates were created.

Six tests passed: rejection at the import boundary; source/section/human-state
checks; starter/consideration/coverage consistency; taxonomy and complete review
ledger; reproducible sample; and metrics/disposition reconciliation. Reproduce from
the repository root:

```sh
python3 trials/welfare-square-housing-kinds-20260930/curation/write_drafts.py
python3 trials/welfare-square-housing-kinds-20260930/build.py
python3 trials/welfare-square-housing-kinds-20260930/validate_trial.py
```

**No Claude calls. No imports.** Michael's sample judgments, especially the commercial
lodging, pet-care boundary and admissions limitations, determine whether this method
is good enough to adopt.
