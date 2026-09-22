# Curated DeepSeek–Grok comparison — September 21, 2026

**DeepSeek's higher discovery volume survives curation: 77 distinct direct-service
proposals versus Grok's 50.** Fourteen are shared, giving 113 in the combined set:
63 DeepSeek-only and 36 Grok-only. This supports DeepSeek as a credible inexpensive
discovery option in these three Categories. Grok contributes important independent
coverage; neither provider's set is a complete reference answer.

Models compared: **DeepSeek V4.1-Flash** and the saved **Grok 4.6** results.
This is not a Grok 4.7 test. All results below are AI proposals,
**Ready for Codex review**, not human Curated approvals.

## Retained findings

| Original research Category | DeepSeek | Grok | Shared | Combined |
| --- | ---: | ---: | ---: | ---: |
| Housing | 22 | 16 | 7 | 31 |
| Employment | 20 | 14 | 4 | 30 |
| Disability | 35 | 20 | 3 | 52 |
| **Total** | **77** | **50** | **14** | **113** |

Rows attribute discoveries to their original research Category. Workbench Category
lists can contain additional cross-category assignments; those do not create
additional globally distinct resources.

All **140 original submissions** received a disposition. DeepSeek supplied 86:
76 submissions contributed to direct services and 10 were omitted. Grok supplied
54: 51 contributed to direct services, two were omitted, and one was retained
separately as navigation. Submission and resource counts differ: MDA's clinic and
summer camp became two resources; self-administered supports were incorporated
into existing waiver resources; aliases were merged.

The native curators retained 114 records. The supervisor classified Grok's
[All Means All directory](https://www.usu.edu/childcarehelp/all-means-all-childcare-programs-in-utah)
as navigation, consistently excluding it from the direct-service totals and HTML
drafts. It lists certified child-care providers to contact, rather than delivering
child care or a subsidy itself. The original curator decision and complete record
are preserved in the audit and `navigation-resources.json`.

## What each provider adds

DeepSeek retains more resources in every Category. Its independent findings include
youth housing vouchers, senior/recovery housing, remote veteran and immigrant
career support, staffing providers, accessible books and telephone captions,
specialist clinics, disability-specific dental assistance, arts and peer support.
These are more than extra names: the curated records contain eligibility, actual
contact/intake actions, access conditions, costs and remaining uncertainties.

Grok's independent contributions include REACH gas assistance, weatherization,
West Valley home repairs, specialized housing, SLCC truck-driving training, state
disability hiring/internships, UCAT, blindness-specific employment, Medicaid
personal care and waiver detail, caregiver compensation, adult day services and
hospital adaptive care. A consequential public benefit can matter more than
several alternative providers; counting resources does not measure beneficiary
value or immediate availability.

The earlier 80% recovery-of-Grok target is not the winner-selection rule here.
DeepSeek's 63 independent curated resources also demonstrate coverage absent from
Grok. The evidence favors DeepSeek on retained breadth and original model cost in
this sample, while supporting preservation of both providers' useful findings.
It does not establish general superiority from three Categories or authorize a
production architecture change.

## Contribution beyond the original Codex research

Useful existing services stay in the curated drafts, but repeated primary coverage
does not earn new discovery credit. Against each Category's sealed original Codex
primary, the following counts include **new named services or substantive expanded
service/delivery detail**:

| Original Category | DeepSeek new/expanded | Grok new/expanded | Shared | Combined |
| --- | ---: | ---: | ---: | ---: |
| Housing | 21 | 15 | 6 | 30 |
| Employment | 20 | 13 | 4 | 29 |
| Disability | 35 | 14 | 3 | 46 |
| **Total** | **76** | **42** | **13** | **105** |

Eight retained resources repeat already-described services: Valor House (both
providers), Choose to Work, Aging Waiver, Veteran Directed Care, The Alternatives
Program, 0–8 care coordination, Parent Center training and Baby Watch (Grok).
Community Transitions also overlaps the primary, but its merged self-administered
support details earn expansion credit. This judgment is explicit in the ledger;
it is not counted as a wholly new organization or service system.

This is category-relative coverage, **not office-wide novelty across all 21
Categories**. For example, a specialist employment service may already appear in
the Disability primary. The original primary records themselves are uncurated
research, not approved facts. The [full audit](challenger-curation-comparison-20260921.json)
includes each resource's classification, exact matching primary records, and
source-file hashes so these judgments can be challenged or changed.

## Corrections, exclusions and access limits

- DeepSeek's Friendship Manor lead was salvaged using the correct Salt Lake
  property site; its submitted Illinois website remains an original-answer error.
  Manpower's address was corrected/qualified, and ESLC's old Murray address was
  replaced with its current West Valley City address.
- RedRover pet boarding was omitted from Housing. Documentation-fee waivers,
  expungement and child-care subsidies were omitted from Employment as indirect
  barriers rather than direct employment services. Grok's Work Success entry was
  omitted because a current stand-alone intake could not be established.
- The UCC/One Utah submission was narrowed to the currently actionable One Utah
  Service Fellowship route. Filled UCC crews and unavailable partner placements
  were not presented as open opportunities. AmeriCorps allowance is distinguished
  from an ordinary wage.
- Splore was omitted as insufficiently actionable by the fresh curator. The prior
  audit additionally documented its merger into the already-listed National
  Ability Center. Its independent-provider/novelty claim remains unsupported.
- The VA disability submission was narrowed to evidenced VA support access;
  bundled housing-adaptation benefits were not turned into guaranteed eligibility.
  Medicaid personal care is retained with current detailed eligibility left for
  confirmation. OPG's record still needs fuller eligibility detail in final review.

Retained does not mean available today. Habitat's application deadline, winter
shelter activation, corrections placement requirements, DSPD/VR funding and
waiting lists, cohort openings, insurance, tuition and vacancies remain explicit
constraints. Southland's conflicting official contact snapshots and GEO capacity
figures need confirmation; capacity is not bed availability. No phone verification
or acceptance test with service users was performed.

The final DeepSeek count happens to equal the earlier **77 useful pathways**, but
it is a different set and unit of measurement: exclusions, salvaged submissions,
and splits offset one another. Grok's earlier 43 excluded primary repeats and used
different research-stage rules. Neither earlier number should be silently
substituted for the curated count.

## Method, effort and artifacts

All original submissions, including earlier rejected leads, entered six bounded
fresh Codex **gpt-5.5 / High** contexts. The shuffled combined packets withheld
provider labels and earlier scores. Standard Scout curation supplied current-source
checks, four Information sections, alias consolidation and complete provenance.
Shared resources credit both contributing providers. This common curation can
use either submission to repair a record; it does not measure independent provider
curation ability or original-answer accuracy. The supervisor knew the earlier
experiment, and styles could reveal providers, so this was not double-blind.

Curation took **39.27 worker minutes**, with six normal completions, no failed
runs, no retries and no structural-repair calls. No new DeepSeek, Grok or Claude
inference occurred. The earlier DeepSeek discovery estimate remains **$0.2575**;
saved Grok telemetry was **$2.9928**, not a new charge. Shared Codex curation,
search and supervision are additional effort with no separately measured
per-provider bill. See the [original cost and experiment report](deepseek-challenger-comparison-20260921.md).

Isolated drafts, all Scout 0.51.1 build 20:

- [Combined: 113 resources](../data/challenger-curation-comparison-20260921/autoWelfareSquareCombinedComparison.html)
- [DeepSeek: 77 resources](../data/challenger-curation-comparison-20260921/autoWelfareSquareDeepSeekComparison.html)
- [Grok: 50 resources](../data/challenger-curation-comparison-20260921/autoWelfareSquareGrokComparison.html)
- [Complete decisions, curated text, provenance and measurements](challenger-curation-comparison-20260921.json)

The HTML files and native evidence are local, git-ignored artifacts under
`data/challenger-curation-comparison-20260921/`; the report and full JSON audit are
versioned. Native assignments/results were preserved. `compare` in the harness
reports native attribution; this report separately records the directory exclusion
and primary-overlap judgments. The local `finalize-analysis.py` recipe and input
judgments are retained beside the native evidence.

All 114 native records have four nonempty standalone Information sections and
source URLs. All three draft seeds match the stated counts. Safari verified the
combined reader and editor, including those four rendered sections and **zero
human Curated marks**. The three harness tests pass. Types, For-group design and
review priorities remain pending; the combined draft visibly reports 113 pending
For-group reviews. No group confirmations or review completion were fabricated.

Read-only hashes confirm **every production table unchanged**. Welfare Square
retains 21 completed primary Categories, 112 passes, 16 saved Grok results, five
pending challengers and zero production curation jobs. Production research and
curation remain paused with automatic restart off. No office package was published.
