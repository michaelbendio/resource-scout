# Welfare Square review handover for a fresh context

## Continuation checkpoint — September 23, 17:17 UTC

Welfare Square review remains authorized and unfinished; Las Vegas is queued afterward.
Michael clarified: minimize context consumption, not useful progress updates. Avoid
repeated reads and copied evidence. Preserve judgment quality. A checkpoint is NOT
a stopping point; continue the authorized work without waiting for another prompt.

- **For: 1,096/1,096**, through115; complete initial per-resource coverage; semantic consistency audit remains.
- **Type/priority: 1,815/2,145**, through103; next104;330 pairs remain across166 already-For-reviewed resources.
- Use **corpus-snapshot-007.json**, catalog002 and **v13 helpers**. Exact effective
  override order is implemented by `effective_decisions_v13.py`.
  V9 additionally applies `membership-reconciliation-navigation-001.json` after
  Type-catalog002, rebinding one For/four category judgments to corpus007.
  V10 then applies semantic-consistency-resolution-005.json: removes Baby Watch
  Rehabilitation & Therapy because the record establishes the state gateway, not
  direct therapy. Other Types, resources, content and For groups are preserved.
  V11 then applies semantic-consistency-resolution-006.json: nine explicit
  Low-income corrections for direct Medicaid/SSI benefit pathways, supported by
  source-recheck-benefit-pathways-20260923-001.json. Ordinary Medicaid acceptance
  remains insufficient. No universal income/parental-income rule is inferred.
  V12 then applies semantic007 (Take Care Utah Low-income and CHIP-appeal Youth)
  and Type-catalog003 (Seniors Transportation includes fares/training and
  conditional programs). All six prior Transportation uses were reviewed.
  Followups005 is resolved; the separate68-candidate audit remains pending.
  New followups006 lists six affordability-consistency candidates; no automatic
  assignments. New Types include pet care (DV/homeless) and legal address
  confidentiality. Followups007 adds seven explicit court, accommodation,
  student-access and Type consistency questions. Recent Types also cover forensic
  care, survivor health coverage, crime-victim compensation, civil damages, legal
  identity changes, matched savings, college/afterschool learning, citizenship
  preparation and child academic support. Backfill earlier relevant memberships
  and consolidate overlapping Types during final assembly.
  V13 then applies semantic008: Southpointe broad adult16+ eligibility no longer
  implies Youth; Guadalupe and YouthCity Education Planning Types are removed
  because career instruction/exploration is not academic counseling. Other
  assignments/priorities are preserved. New Types also include basic literacy,
  informal language practice, reentry education, public Wi-Fi, course auditing,
  service placements and student childcare. Followups008 adds six explicit hub,
  library-child-access and education-award affordability consistency questions.
  The hub Basic Literacy assignment must be removed or substantiated before
  installation; a generic writing class is not proof of foundational literacy.
  New Types include formal School Courses, Credit for Prior Learning, Seniors
  Employment Support and Education Career Readiness. Followups009 records eight
  explicit new-Type backfill and provider-versus-program population checks.
  Provider portfolio/demographics do not automatically transfer to every service.
  Followups010 adds seven explicit conviction-access, Humanitarian Center address,
  VA/ACE funding and reentry Type checks. New Types include Correctional Housing
  (Housing/Reentry), Reentry Employment Support, Fidelity Bonds and Social Security
  Cards. Preserve restricted placement and unresolved Atherton gender information.
  Humanitarian Center1999 W1700 S versus ESLC1665 S Bennett needs source reconciliation.
  Followups011 adds seven explicit accommodation, supported-education, student
  fare, peer-professional, military-family and displacement interpretations.
  New Financial Type: Bank Account Access. All followups006–011 remain pending
  alongside the earlier68-candidate and VA/family audits; none are auto-assigned.
  source-recheck-beautiful-ability-20260923-001.json corroborates disability-focused
  employment from the provider site; detailed payer/referral rules remain open.
  Followups012 adds eleven explicit benefit/household/tax/Medicare/SSA consistency
  questions from105–107. Source rechecks preserve Lifeline and SSA categorical
  eligibility; WIC primary fetch403 does not establish closure. New Types:
  Seniors Utility Assistance and Income Benefits; Medical Bill Assistance;
  Financial Child Support; Utilities Phone Plans. Backfill relevant earlier pairs.
  Followups013 adds six explicit moratorium, income-replacement, tax-access,
  school-meal consistency and unspecified-diaper checks. New Types: Financial
  Utility Protections, Immigration Cash Assistance and Employment Unemployment
  Benefits. Followups006–013, earlier68 and VA/family audits remain pending.
  Followups014 adds seven explicit food-aid, child/diaper, school-meal, delivery
  and functional-disability checks. Current primary evidence confirms CBC’s named
  diaper partner moved into Utah Food Bank in2025 and serves babies/children and
  parents; source-recheck-midvale-diapers-20260923-001.json preserves it. Assess a
  brief partner-name clarification before final content assembly. New Food Types:
  Community Gardens and Pet Food. All pending audits remain unfinished.
  Followups015 adds four explicit clinical-versus-functional disability, SNAP,
  new-Type backfill and school-family/Justice vision-clinic checks. New Types:
  Seniors Food Benefits/Groceries; Disability and Veterans Food Assistance.
  All followups006–015,68-candidate and VA/family audits remain pending.
  Category-only backlog helper/input preparation is next: do not resave For
  ledgers. Next Type ledger104.330 pairs/166 resources await explicit judgments.
  Current unreviewed resources with Disability membership: 0.
  Type-catalog002: Adapted Homes includes accessibility
  modifications as well as acquisition/construction. All five pre-existing uses
  were reviewed explicitly. Use `prepare-numbered-input-v7.py` for new input packs.
- `continuation-checkpoint-029.json` passed live corpus/fingerprint, resource hashes,
  literal evidence, all26 group partitions/parents and defined Type checks.
- New `numbered_review_helpers_v7.py` and immutable numbered input packs reduce
  repeated text: reviewers explicitly choose labels, tiers and paragraph references;
  the helper only resolves exact evidence. It performs no classification.
- Latest batches057–115 add467 resources and917 category decisions since checkpoint006.
  Children, Clothing and Disability native For queues are finished; Domestic
  Violence and Education native For queues are finished; Employment native For queue is finished; Financial Assistance native For queue is finished; Food native For queue is finished. Every resource now has an all26 For decision; final semantic consistency work remains. Seventeen resources originating in other categories
  had Disability membership and awaited For review at797; recount before claiming
  complete disability coverage.
  This does not finish every additional category membership for earlier resources.
- For053 first draft had a nonliteral training excerpt;053-v2 passed. Preserve both.
  Never rerun successful prepare/save/checkpoint scripts; create new versions.
- All content followups001–012 are applied. No new content change was made.
  New source-recheck files cover UICSL, HRSS and USOR. HRSS survivor access was
  resolved through its adopted HUD definition; clinical/Medicaid criteria still apply.
  USOR sensory accommodations are corroborated by its linked official materials.
  UICSL pantry evidence remains dated with explicit current-operation questions.
- **Membership revision applied:** Salt Lake City Minor/Home Repairs retains four
  supported memberships; only unsupported Utilities membership was removed.
  `membership-reconciliation-applied-001.json` and
  `category-membership-resolution-slc-repairs-001.json` supersede the original
  proposal's pending flag. All facts/native copies/IDs/links remain; preservation
  and checkpoint010 passed. No pending membership decisions remain.
- Semantic004 remains effective. The68 diagnostic consistency candidates and older
  VA/family clusters remain pending. AAU trafficking now explicitly reconciles
  immigration-status accommodation; Food Type is Meals, with Groceries omitted.
  LDS storehouse Food is Groceries; generic Food Navigation was omitted.
- Audit new Types for earlier applicable memberships during final assembly:
  Childcare costs/Childcare Support, Nutrition education, Housing Navigation,
  Meals/Food Navigation, School Supplies, Laundry & Showers, Mail Services,
  Household Essentials, Recovery Support, Postpartum supplies, Supportive Housing,
  Haircuts & Grooming, Clothing Costs, Outdoor Essentials, Driver Licenses/Driver
  License Costs, Outreach Food, Travel Training and High School & Equivalency.
  New062 Types also need backfill review: Reentry Legal Help, Disability Peer &
  Community Support/Condition Education, and Housing Affordable Housing.
  New065–066 Types: Income Benefits, Benefits Appeals, Assistive Technology Costs
  and Workplace Accessibility. New067/069 Types: Immigration/Seniors Health Coverage
  and Education Independent Living Skills. New071–072: Medical Home Health Care /
  Medical Transportation; Employment Personal Assistance / Benefits Planning.
  New073 Financial Type: Transit Fares. New075 Medical Types: Neurology,
  Residential & Skilled Care and Respiratory Care. New076–077: Medical Hearing
  Care; Seniors/Legal Resident Rights; ID Recovery Immigration Documents.
  Source-recheck-pension-ship-20260923-001.json supports named income/age
  benefit pathways in077. UDVMA family-member claims were distinguished from
  dedicated support in a caregiving role; broader VA/family audits remain pending.
  New078–079 Types: DV Financial Assistance / Housing Support and
  Immigration/Legal Consular Protection. Audit earlier applicable memberships.
  New080 judgments explicitly cover PIK2AR Pacific Islander/women/men/youth
  pathways and RRC income/uninsured/immigration/correctional-facility access.
  Journey of Hope Men remains omitted: Day Won is partner context without
  confirmed independent public intake. Keep the access caveat and follow-up.
  Holding Out HELP has explicit host-home/student/displaced-family pathways;
  polygamous background alone does not establish abuse-survivor targeting.
  Keep supported living distinct from housing support.
- Updated ETA at15:28UTC:5–7 more working hours (14:30–16:30MDT) for Welfare
  Square, including
  consistency, browser and Save. Last80 resource reviews took28.4 minutes.
  Las Vegas remains afterward; this is an estimate, not a completion record.
- No navigation/priority installation, completion recording, human Curated change,
  browser verification, Save/download or Las Vegas launch. Preserve browser-local
  work and the unrelated tracked deletion. Full finish requirements remain below.

## Earlier checkpoint detail — 09:53 UTC

Checkpoint: **September 23, 2026, 09:53 UTC (03:53 MDT)**. This file is the current
continuation handover and supersedes older state/counts in historical status notes.
Michael warned that the conversation had little context left. The assistant saved
a verified checkpoint; **the review is unfinished and remains authorized**. Resume
from these artifacts without restarting research or repeating completed judgments.

## Authorization and next office

- Complete Welfare Square's requested post-curation review. Preserve identities,
  original outputs, source evidence, candidate links, sealed assignments, each
  native category copy's facts, and human Curated status. AI priority is separate
  from human approval. Keep every resource.
- No paid review worker or delegated subagent was launched. Do not launch one to
  accelerate continuation; proactive delegation is not authorized.
- After Welfare Square is actually reviewed, browser-verified and Save/download
  verified, create exact `lasVegas.html`, establish office/service area/package,
  and start/supervise Las Vegas Scout. **High effort is explicitly authorized for
  Las Vegas setup and launch.** Configure workers explicitly; the supervising
  conversation effort is user-controlled, so flag that transition for Michael.
- No Las Vegas file or worker exists. Establish office/service area through the
  applicable workflow; do not assume an approved county boundary.
- The last estimate was given at 09:08 UTC: 4–6 more hours for Welfare Square,
  then 20–40 minutes for Las Vegas setup/launch, research additional. This is a
  historical estimate, not a new forecast or a reason to shortcut review.

## Read and verify on resumption

Read `SCOUT_STATUS.md`, `docs/scout-orchestration.md` and
`docs/scout-workbench-readiness.md`. Verify live database/process state.
`docs/welfare-square-stopped-handover-20260923.md` retains older review history;
its historical stop instructions do not cancel authorized continuation.

Repository: `/Users/michaelbendio/resource-scout-pairwise`; current branch
`pairwise-research-experiment`. Previous handover commit20330f3 and code fix69103cc
are pushed; inspect Git for this checkpoint's later commit. The unrelated tracked
deletion `docs/scout-discovery-and-maintenance-proposal-20260920.md` must remain
untouched. Commit/push only scoped, verified changes on the current branch.

Working database:
`data/welfare-square-production-20260921-codex-grok/research.sqlite3`, import/job1.
Audit root: `data/welfare-square-curation-20260921/audit/`.
**`P` below means `final-navigation-review-001/` under that audit root.**
Audit artifacts and database backups are local, Git-ignored files; the committed
handover points to them but does not constitute a remote backup of their contents.

At 09:52 UTC native research/curation is terminal21/21, supervisor status
`ready-for-codex-review`. Only monitor PID6391/port8770 remains; no coordinator or
paid worker. Do not restart completed work. Preservation passes **37 research
tables,146 original native batch hashes and1,096 resource IDs**, plus SQLite,
candidate-link and four-section structural checks. Evidence:
`root-review-checkpoint-20260923T095207Z.json` and matching research-preservation
file. Re-run preservation read-only when resuming:

```sh
PYTHONPATH=. python3 data/welfare-square-curation-20260921/audit/check-review-preservation-002.py
```

`P/continuation-checkpoint-001.json` verifies the live corpus/fingerprint, exact
hashes and literal evidence after all overrides below; all26 group decisions per
reviewed resource, sensory-parent relationships, and defined/nonretired Types
pass. Its script uses a read-only SQLite connection and makes no classification.
Preserve that output; use a new checkpoint version for a later run.

No final navigation or priority proposal is installed. No review completion,
human Curated approvals or final Save has occurred. Actual browser checks remain
outstanding. Preserve any browser-local work; it has not been declared empty.
If resuming an existing CUA context, call `await cua.rewriteDocumentation()` first.

## Current corpus and review coverage

Use **`P/corpus-snapshot-004.json`**. Current curation fingerprint:
`c933f246610b4552e64ec1da89be1672f7e3f1a070c6ddcd656f56031650761c`.
The latest durable content revision/snapshot is **09:33:51 UTC**.
Full corpus: **1,096 resources / 2,145 category memberships**.

- **549 final resource/all26-group reviews**, through `for-reviewed-043-v2.json`;
  **547 remain**. Next batch **044**. Glob successful `for-reviewed-*.json`, including
  repaired versions020-v2,026-v2,030-v2 and043-v2. Do not promote failed raw drafts.
- **710 final category/resource Type and priority reviews**, through
  `navigation-priority-reviewed-030.json`; **1,435 memberships remain**. Next **031**.
- New batches040–042 finished the remaining native Addiction records and began
  Children/Pregnancy. Batch043-v2 covers Canyons Family Center through DDI Early
  Intervention. Do not infer that every additional category membership is complete.
- Earlier634 provisional For judgments still require reconciliation against the
  final bodies/catalog unless a successful final ledger already covers that ID.
  `P/prior-for-judgments.json` contains those earlier decisions, sometimes multiple
  category copies. Some lack judgmentNote; read noGroupReason/nonAssignmentReason.
- `P/prior-reconciliation-input-001.json` maps756/762 earlier hashes to historical
  resource objects; six unmatched hashes remain explicit. Historical hash matches
  are comparison evidence, not semantic review or permission to auto-promote rows.

Use **v4** helpers for new batches, bound to corpus004 and group catalog002:

- `save-manual-for-decisions-v4.py NNN` validates explicit
  `for-decisions-NNN.json` triples and writes `for-reviewed-NNN.json`.
- `navigation_priority_helpers_v4.py`: import `add as a, save`.
  `a(id,category,[(type,literal)],tier,reason,question,priorityLiteral)`;
  Types can quote description or Information; priority defaults to Information.
- `preflight-explicit-priority-v4.py prepare-navigation-priority-NNN.py` validates
  AST literal excerpts without saving. Pass the basename. Arguments must be
  literals, not replacement/capitalization calls.
- Helpers v1–v3 remain immutable and tied to older corpora. Do not use for new work.
- V4's Type catalog loader reads original final ledgers; it does **not** fold in
  `type-catalog-resolution-001.json`. Consult that resolution for new judgments,
  avoid retired aliases, and apply its definitions/overrides in final assembly.

Queue extraction:

```python
rs = json.loads((p/'corpus-snapshot-004.json').read_text())['resources']
done = {a['resourceId'] for f in p.glob('for-reviewed-*.json')
        for a in json.loads(f.read_text())['assignments']}
queue = [r for r in rs if r['id'] not in done]
```

Read complete final records, earlier decisions and consequential source questions.
No keyword/rule-based assignment or automatic classification replaces judgment.

## Completed content work — do not rerun

Earlier global audit completed328 shared-body comparisons and115 field corrections
in immutable global prepared/applied001–022. Identity consolidation002 reduced1101
to1096 with provenance retained. Retention-memberships002 restored enrolled/resident
services, removed incidental memberships and added Project Reality direct Medical.

`P/content-reconciliation-applied-001.json` resolves followups001–006: Habitat,
Valley and UCS descriptions; DAV disability-claims scope; precise VA former
homosexual-conduct discharge-bar wording; and unsupported GAU/private-guardianship
and County Library delivery Seniors memberships. The sole-discovery preservation
API fix is committed in69103cc; all37 related tests passed. Native discovery
resource count can intentionally differ from final browsing membership count.

`P/content-reconciliation-applied-002.json` resolves followup007 and category fit:

- 7th Street: separate30–60-day day treatment and weekly educational family group;
  preserve the existing duration conflict. Final overrides add Families & caregivers
  and Addiction Family recovery support.
- MCC: Immigration membership and clinical evaluation route/contact385-419-0216,
  attorney request, supported case/report types, telehealth timing and noncoverage.
  These are clinical reports, not legal representation. Removal-case support grounds
  its Justice group under the clarified definition.
- YouthHub: ID Recovery membership for explicit homelessness-verifier / ID fee-waiver
  assistance. Existing population decisions retained.
- Thirteen field changes across five native category results, snapshot003.
  `apply-content-reconciliation-002.py` failed its pre-write assertion because it
  retained old001 filenames. **`apply-content-reconciliation-002-v2.py` succeeded.**
  Preserve both attempts and the pre-change backup.

`P/content-reconciliation-applied-003.json` adds:

- CHC: explicit pediatric and senior care in Information and Seniors membership.
- Andy's Wellness: Medical membership for direct HIV/HCV testing and wound care.
- WhiteTree: Medical and Mental Health memberships for actual primary/family care,
  pain care and clinical counseling. No unsupported Psychiatry Type was retained.
- Nine field changes across five native results, snapshot004. All IDs, candidate
  links and sealed assignments remain unchanged. Scripts/backup are immutable.

For043's original draft failed a literal-field assertion; **043-v2** succeeded.
Type/priority029's original preflight found undefined labels; **prepare029-v2**
added the evidenced reentry Mental Health Treatment definition and used Housing
Supported Living. Type/priority030's original preflight failed a literal; **030-v2**
succeeded and also removed weak Canyons Parenting Support and WhiteTree Psychiatry
claims. Failed attempts remain evidence. Do not rerun successful scripts.

## Exact override order and resolved consistency decisions

Load successful final For and Type/priority ledgers, then apply full-record overrides
in this order. Each override replaces that resource or resource/category pair:

1. `content-reconciliation-navigation-001.json` — 7 For /9 pair overrides.
2. `content-reconciliation-navigation-002.json` — 3 For /11 pair overrides.
3. `content-reconciliation-navigation-003.json` — 2 For /3 pair overrides.
4. `semantic-consistency-resolution-001.json` — 12 For overrides.
5. `semantic-consistency-resolution-002.json` — 13 For overrides.
6. `semantic-consistency-resolution-003.json` — 2 For /1 pair overrides.
7. `type-catalog-resolution-001.json` — 4 pair overrides, definition overrides and
   four retired labels across three categories.

Use **`catalog-decision-002.json`**, retaining26 groups. Justice now means criminal
justice/corrections/reentry, criminal-history access barriers, or immigration
detention/removal services; ordinary civil court/benefit/record use is insufficient.
Catalog001 remains preserved. Sensory groups require People with disabilities.

Semantic001 resolves required means-qualified Medicaid/waiver benefits versus
ordinary payer acceptance. FACT, justice Medicaid, Imber and HTP gain Low-income;
ACT/VOA ACT/HOME/UMIC/Molina D-SNP retain it. Elite's unresolved advertised payer
claim does not qualify. Encircle and Project Connection retain their separate
scholarship/reduced-fee pathways. Required established income-related benefit or
explicit affordability assistance qualifies; routine insurance billing does not.
Do not import a universal income cutoff or imply every household member's income
was assessed. Current Utah eligibility/waiver/expansion primary pages were checked.

Semantic002 distinguishes relatives' own claims from supporting-caregiver roles:
PVA, American Legion and VA Regional Benefits get no Family merely from dependent
claims; SAH host-family adaptation, Women Veterans supporting callers, CHAMPVA's
PCAFC branch and DIC's surviving-parent child-care supplement qualify. CHAMPVA/DIC
retain Seniors specifically for55+/57+ remarriage benefit-retention branches, not
Medicare or grandparent status. DEA/VET TEC retain Students for separate approved
training funding; DEA Youth rests on its legacy age26 branch. Chapter36, Salesforce
and V School do not get Students merely from prospective/direct course enrollment.
TAPS does not get Students from camp readiness; its parent support supports Family.
V School gains Low-income for a separately documented tuition scholarship addressing
financial barriers, consistent with the existing affordability definition; no
means test is claimed. Earned VA entitlement/free courses alone are different.

Semantic003 audits67 already-assigned Justice records within the549 completed
reviews. Arches loses American Indian & Alaska Native: generic Indigenous/BIPOC
wording does not establish that narrower identity. Retain explicitly supported
Black/BIPOC, LGBTQ, adolescent and family services. SUPeRAD loses Justice and its
Addiction Justice-system treatment Type because unspecified court orders may be
civil; preserve that factual wording. True North's primary page explicitly confirms
probation coordination/compliance, supporting retention. Release/probation ID
accommodations address reentry barriers; EOIR removal assistance fits catalog002.
This audit does not cover the547 still-unreviewed resources.

Type-catalog001 consolidates Enbridge Billing Disputes→Billing & Service Disputes,
Recovery Ways Valor Detox→Withdrawal care, Veterans Consortium Naturalization Legal
Help→Citizenship, and Utah@EASE Immigration Legal Help→Attorney Referrals. It clarifies
clinical Residential treatment, MCC-compatible Legal & Immigration documentation,
Job Placement, Job Search Support, Business Support and Attorney Referrals.
Employment's older120-record provisional catalog must not be blindly unioned:
separate rights from benefits/work incentives, job search from sustained mentoring,
training from funding, and preserve actual trade/apprenticeship pathways. Other
useful provisional Types require explicit final resource/category judgments.

**Future content revisions must rebind these effective overridden rows**, not just
raw base ledgers. Keep all previous snapshots, overrides and failed attempts intact.

## Six pending sourced content corrections — not applied

Read exact proposals/source URLs and after-revision steps in these files:

- **`content-followups-008.json`**: SSVF `12cd5adc24ea5d7f95b075671a651da6`.
  Append the current VA low-income Veteran-family housing-stability scope; local
  staff assess current rules/funds. No old numerical threshold. Then add Low-income
  and rebind all affected rows; household eligibility alone does not add Family.
- **`content-followups-009.json`**: Project Connection
  `9142d56a175051d19f3bac9165c7ea66`, explicitly unfunded/underfunded case-by-case
  reduced fares. Retain affordability; do not equate funding gaps with uninsured.
  Encircle `55b6e133641c507192149bee81b9a1ae`, dated September23 scholarship
  application status, fully funded sessions and community-funding limits. Confirm
  current cycle/eligibility/wait; open applications are not an award/appointment.
- **`content-followups-010.json`**: Arches
  `a184bcd69c615310aecf63b5dbc2ee57`, explicit autism/neurodivergent/chronic-illness
  care and neurodivergent adult/teen groups. Add Disability category, disability
  group and explicit category Type/priority; retain the AIAN omission.
  True North `e1d33bef2b38538b89408aa970177ce6`, append probation coordination,
  compliance reporting and testing; rebind Justice with precise literal evidence.
  SUPeRAD `f12cb6971bde55dba0189ee44dbc1d2a`, append pediatric neonatal-withdrawal
  consultation, contraception and trauma-informed gynecology. Add Youth for direct
  pediatric consultation and Women for gynecology, retain Pregnant and omit Justice.
  Add Children/Pregnancy Child medical care and Addiction Withdrawal care (the
  latter from already-saved hospital stabilization). No new category needed.

Apply through durable per-native-copy revisions preserving each copy's text,
validate provenance/IDs/assignments, freeze a new corpus005 and version helpers.
Then rebind affected effective judgments and explicitly review new memberships.
These proposals are saved for continuation; none has been applied to the database.

## Remaining semantic work and finish sequence

- Continue547 full-record For judgments and1,435 category Type/priority judgments;
  counts will change if pending revisions add memberships.
- Compare VA enrollment32a3… / HBPC3165… general income/copays with VA travel6736…
  direct income/inability-to-pay assistance. This cluster remains unresolved.
- Family counterexamples ACP/BlueStar/CAN/VA telehearing were not reread this turn;
  keep the supporting-role rule consistent. Semantic002 resolves its13 listed
  records, not every similar resource in the full corpus.
- Reconcile Food's71 final memberships against63 native provisional judgments plus
  eight later memberships: AAUTIP loses unsupported Groceries but retains Meals;
  LDS storehouseccb82… loses generic Food Navigation but retains Groceries.
- Preserve group evidence boundaries: provider names/languages do not establish
  ethnicity; general free access does not establish Low-income/uninsured; adult-only
  parenting does not establish direct Youth service. Multi-program group matches
  do not imply one subprogram serves the intersection.
- Group catalog additions Asian American and Native Hawaiian/Pacific Islander have
  specific VA Minority9c801… / ITECa3e740… / PIK2AR RELS3d1b… evidence. PIK2AR pantry
  does not gain Pacific targeting from the provider name alone.

After all content and semantic review, assemble complete current navigation,
resolve duplicate/unused Types and coverage, and validate with `scout_navigation.py`.
Then bind priorities to that installed navigation using `scout_review_priorities.py`.
Neither structural validation nor installing a proposal completes the review.

Inspect actual four rendered Information sections, reader/editor, Category Types,
Browse by Group, search, Type OR / groups AND and Match any, empty combinations,
priority/A–Z equivalence with active filters, reasons/questions, personal overrides
and reload, shared Curated progress across categories and zero new human Curated
flags. Preserve browser-local edits. Follow the entire readiness checklist.

Only after those checks, write the report, record completion for the exact final
fingerprint through `scout_review_handoff.py`, and verify the monitor's actual Save
download. Then transition to Las Vegas at High under the office/orchestration
workflow. Never record completion merely to expose Save.
