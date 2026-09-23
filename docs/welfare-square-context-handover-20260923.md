# Welfare Square review handover for a fresh context

Checkpoint: September 23, 2026; review boundary09:12 UTC (03:12 MDT).

Michael requested continuation in a **new terminal session**. The assistant saved
this file-based handover and stopped the old session at a safe review boundary.
A new Codex session asked to continue per this handover should resume the review.
The pause does not cancel Welfare Square or the queued Las Vegas work. Do not
mistake earlier historical stop notes for an instruction against that resumption.

## Authorization and next office

- Complete Welfare Square's requested post-curation review. Be judicious about
  retained pathways, category fit and navigation. Preserve resource identities,
  source evidence, original outputs and human Curated status.
- No paid review worker or delegated subagent was launched. Do not launch one just
  to accelerate this handover. Applicable developer policy forbids proactive
  delegation unless explicitly authorized by the user or applicable instructions.
- After Welfare Square is actually reviewed, browser-verified and Save/download
  verified, create exact `lasVegas.html`, establish office/service area/package,
  and start/supervise Las Vegas Scout. **High effort is explicitly authorized for
  Las Vegas setup and launch.** Configure workers explicitly; the supervising
  conversation effort is user-controlled, so flag that transition for Michael.
- No Las Vegas file or worker exists. Office/service area still needs establishing
  through the applicable workflow; do not silently assume a previously approved
  county boundary.
- Latest estimate given at 09:08 UTC: **4–6 more hours for Welfare Square**, then
  **20–40 minutes for Las Vegas setup/launch**, research time additional. Earlier
  3–5-hour estimate was acknowledged as too optimistic.

## Read and verify on resumption

Read `SCOUT_STATUS.md`, `docs/scout-orchestration.md` and
`docs/scout-workbench-readiness.md` before substantive work. Verify live DB/process
state. The earlier `docs/welfare-square-stopped-handover-20260923.md` provides older
retention history; this handover supersedes its current-state instructions.

Repository: `/Users/michaelbendio/resource-scout-pairwise`, current branch
`pairwise-research-experiment`. Latest code/checkpoint commit before this handover:
**69103cc**, pushed. The unrelated tracked deletion
`docs/scout-discovery-and-maintenance-proposal-20260920.md` must remain untouched.
Commit/push only scoped, verified changes on this branch.

Working database:
`data/welfare-square-production-20260921-codex-grok/research.sqlite3`, import/job1.
Audit root: `data/welfare-square-curation-20260921/audit/`.
Final navigation directory below is relative to that audit root:
`final-navigation-review-001/` (called `P` below).

Native curation/research is terminal21/21. Only monitor PID6391/port8770 remained;
no coordinator or paid worker. Do not restart completed research or curation.
Preservation at **09:12:07 UTC** passes37 unchanged research tables,146 original
native batch hashes and1,096 IDs. Evidence:
`root-review-checkpoint-20260923T091207Z.json` and matching research-preservation
file. Re-run read-only preservation with:

```sh
PYTHONPATH=. python3 data/welfare-square-curation-20260921/audit/check-review-preservation-002.py
```

No completion event, human Curated approvals, navigation installation or final
Save has occurred. Actual final browser reader/editor/filter/priority/override
checks remain outstanding. If continuing an existing CUA context, first call
`await cua.rewriteDocumentation()`; browser-local edits have not been discarded
or declared empty.

## Completed content and storage work

- Earlier global audit completed328 shared-body comparisons and115 field
  corrections in immutable global prepared/applied001–022.
- Identity consolidation002 reduced1101 to1096 resources, with all provenance
  retained. Retention-memberships002 restored resident/enrolled service details,
  removed incidental memberships and added Project Reality direct Medical care.
  Do not rerun successful scripts. Failed attempts remain evidence.
- Content followups001–006 are now durably resolved in
  `P/content-reconciliation-applied-001.json`: Habitat mortgage-rate description,
  Valley three-property description, UCS transport description, DAV disability
  claims scope, explicit VA former homosexual-conduct discharge-bar wording, and
  two unsupported Seniors memberships (GAU private guardianship and County Library
  at Your Door). These are seven changed resources / four native category results.
- The two Seniors discoveries had no other native copy. A scoped API change now
  allows explicit `reviewed_category_removals` only after curation completes. It
  preserves the sole discovery record, facts, candidates, dispositions, other
  memberships and sealed assignment. Worker validation still requires its native
  category. Only rejected membership, its filters and lastModified may change for
  those rows. Later fact revisions retain the reviewed removal. Native result
  resource count and final category membership count are intentionally different.
- Code/docs/test change is committed/pushed in69103cc. All37 curation, runner and
  result-repair tests pass, including strict rejection, original-result
  preservation, fingerprint change, seed export and subsequent revision tests.
- Prepared/applied content-reconciliation001 scripts and pre-change DB backup are
  immutable. Last DB mutation was **08:55:45 UTC**. No DB changes since.

## Current frozen corpus and ledgers

Use **`P/corpus-snapshot-002.json`** for all new judgments. Do not overwrite the
original `corpus-snapshot.json` (the pre-content-reconciliation corpus).

Current curation fingerprint:
`c5688159e8c72f2b06e8ce46eff755bb0c2e2e76f1f949dce5311a864d92f96f`.
Current Veterans result hash:
`cfcfef9773efedfdb7a41f3fb54b21305c29b3f4322f881bbc1e057fe433cbbd`.
Full corpus: **1,096 resources / 2,139 category memberships**.

Saved final navigation judgments (all uninstalled):

- **503 unique resource/all26-group reviews**, through
  `for-reviewed-039.json`. Versions020-v2,026-v2 and030-v2 preserve earlier
  validation repairs; use globbed successful `for-reviewed-*.json`, not failed
  draft assumptions. Resources without earlier provisional judgments are complete
  (463 records, with one overlap against the earlier634 inventory). Earlier-body
  reconciliation began in037–039; **593 resources remain**.
- **616 category/resource Type and priority reviews**, through
  `navigation-priority-reviewed-026.json`. **1,523 memberships remain**.
  Prepare026 first failed preflight for two undefined labels; Supported Employment
  and Child Safety were added from the established provisional definitions, the
  preflight passed, and026 was saved successfully. Do not rerun it.
- Next group checkpoint: **040**. Next Type/priority checkpoint: **027**.
- No automatic classification is used. Each resource and category pair gets
  explicit semantic judgment, literal evidence, priority reason and useful
  question. Keep all resources; priority is not human Curated status.

Existing seven-resource rebind is complete in
**`P/content-reconciliation-navigation-001.json`**. It contains7 For overrides,
9 Type/priority overrides, and verifies456 other For rows /525 other Type-priority
rows are byte-equivalent resource objects across snapshots. Apply these overrides
when assembling final proposals; do not simply load old hashes. DAV now has
People with disabilities, without inferring caregivers from family claims for
one's own benefit. Its disability Type evidence/reason was clarified. COD LGBTQ
now uses the precise appended literal sentence. Other notes mark queued changes
as resolved. Do not rewrite old ledgers.

For new batches use the versioned helpers bound to corpus002:

- `save-manual-for-decisions-v2.py NNN` reads explicit
  `for-decisions-NNN.json` triples, validates all labels/evidence/duplicates/parent
  groups, and writes `for-reviewed-NNN.json`.
- `navigation_priority_helpers_v2.py`: import `add as a, save` in new scripts.
  Signature `a(id,category,[(type,literal)],tier,reason,question,literalPriorityQuote)`.
  Types may quote description or Information; priority defaults to Information.
  `save('NNN', definitions)` rejects duplicate pairs and undefined/conflicting Types.
- `preflight-explicit-priority-v2.py prepare-navigation-priority-NNN.py` validates
  draft literals with AST without saving. Pass the basename, not a repeated path.
  All `a()` arguments must be literals, not `.replace()`/`.capitalize()` calls.
- Old helpers remain unchanged and tied to corpus001; do not use them for new work.

Queue extraction:

```python
rs = json.loads((p/'corpus-snapshot-002.json').read_text())['resources']
done = {a['resourceId'] for f in p.glob('for-reviewed-*.json')
        for a in json.loads(f.read_text())['assignments']}
queue = [r for r in rs if r['id'] not in done]
```

Read complete final resource bodies, existing prior decisions and relevant changed
facts. Replacing URLs in displayed text for readability is okay; retain source URLs
in artifacts. Do not truncate clinical/eligibility/access text to force a batch.
`P/prior-for-judgments.json` contains634 unique earlier provisional resource
judgments, sometimes multiple category copies. Some older rows lack judgmentNote;
use noGroupReason/nonAssignmentReason rather than crashing.

`P/prior-reconciliation-input-001.json` additionally maps756/762 earlier resource
hashes to exact historical objects recovered read-only from durable SQLite result
revisions and corpus001. Six unmatched hashes remain visible. This can support
precise body comparisons; hash matching or JSON coverage alone is not a semantic
review. No earlier judgments were automatically promoted based on this map.

## Latest substantive navigation decisions

037–039 reconcile the first40 earlier Addiction/shared records. Examples:

- BAART: add explicit pregnancy coordination; routine veteran Community Care payer
  acceptance alone is not a dedicated military service.
- Clinical Consultants: actual merged youth9–17 counseling and family therapy.
- Fourth Street: homelessness, explicit uninsured care/sliding fees and bounded
  jail-release continuity. Preserve established-patient limits and separate
  medical/dental/pharmacy hours, records-fax route and ride staffing uncertainty.
- House of Hope: women/youth/caregivers plus justice-specific income-related TAM
  access; no pregnancy inference merely from motherhood.
- MCC: survivor therapy, sliding fees, explicit ASL+disability parent and U-visa/VAWA
  clinical evaluations. Language access alone supplies no ethnicity. Its Domestic
  Violence Legal & Immigration Type describes clinical reports, not legal representation;
  make the final definition inclusive of this support without creating redundant Types.
- Project Reality: pregnancy funding, jail MAT and sliding fees; birth-control and
  general care do not establish a blanket women or uninsured group.
- Asian Association behavioral health: refugees/youth/survivors/IPS functional
  employment support. **No Asian American tag from the provider's name.**
- Rescue Mission New Life: indigent/homeless/direct-jail access and distinct male /
  female graduate homes now support Low-income/Justice/Men/Women beyond the older
  general mixed-gender description.
- Salt Lake Behavioral Health: merged adolescent12–18 mental-health and Strong
  Hope military pathways now support Youth/Veterans. Do not infer adolescent SUD
  admission, immediate beds or free care.
- Youth Hub: youth/family crisis, law-enforcement receiving and direct homeless
  youth access. Do not infer abuse/foster eligibility merely from safety/DCFS.
- Family Peer Specialists: direct caregiver support; children's age/risk alone
  does not make it a direct youth, foster or justice intake.
- General free peer/crisis services are not automatically Low-income/uninsured.
  Ordinary Medicaid acceptance is different from delivery of an income-related
  benefit or required means-qualified plan. Reconcile remaining edge cases below.

## New pending content and fit issues

1. **`P/content-followups-007.json`**, not applied: 7th Street
   `fde8d51158b453cb9475c9f8a0e127ac`. Current provider
   `https://7treatment.org/change/` confirms separate30–60-day day treatment and a
   weekly structured educational family group. Add the supported access paragraph,
   preserving existing duration conflict, current body and sources. Then rebind
   For037 and add Families & caregivers; add Addiction Family recovery support to
   Type/priority024. Outpatient already covers the day-treatment level. The saved
   proposal needs ordinary spaces around numbers before insertion.
   The page also confirms vouchers addressing affordability/criminal-history
   barriers, supporting the new Low-income/Justice judgments already in037.
2. Consider on resumed category-fit review (not an approved change yet): Youth Hub
   `01464b9b2c335e66b90d6e1e37be21d9` has explicit approved homelessness-verifier / ID
   fee-waiver support in the final body, but lacks ID Recovery membership. Compare
   with Fourth Street's supporting-record/verification treatment and decide if a
   category addition is warranted; preserve all native copies. MCC's specific
   U-visa/VAWA clinical evaluations likewise may merit Immigration membership;
   check for a separate retained evaluation record before adding/duplicating.

## Outstanding semantic and taxonomy consistency

Read `P/semantic-consistency-followups-001.json`–`003.json` and preserve them.
Resolve before final installation, with explicit override/decision artifacts:

- Required Medicaid versus ordinary acceptance: Odyssey FACT98f…, ACTca26…,
  VOA ACT79d574…, HOME61b42…, UMICb47f6…, justice Medicaid6a596…, SSVF12cd…;
  MolinaD-SNPadf32… versus Imber00bb27…, HTPfdc0…, Elite6015…. Decide from actual
  benefit/eligibility, not an insurance keyword. Encircle55b6… and Project
  Connection9142… scholarship/reduced-fee cases also need consistency.
- VA enrollment32a3… and HBPC3165… general income/copay references versus VA
  travel6736… explicit income/inability-to-pay branch.
- Families means relatives/parents/unpaid caregivers in supporting roles.
  Military spouse's own career/training or survivor's own benefits alone is not
  caregiver support. Explicit caregiver grants, companion flights, support-person
  hearing/care navigation, family-host adapted housing and parent benefits tied
  to child care can qualify. Resolve CHAMPVA/DIC/SAH and comparable programs
  consistently; retain separate subprogram eligibility.
- Seniors: CHAMPVA6b528… and DIC3ab615… were tagged from55+/57+remarriage benefit
  exceptions, not Medicare. Review whether that fits the final catalog consistently.
- Students/Youth: dedicated enrolled-student support is distinct from enrolling
  in the listed course. Review dependent18–23 coverage, legacy DEA age26 branch,
  VETTEC funding, V School, Salesforce, TAPScamp and Chapter36 consistently.
- Justice definition in catalog001 is too broad about courts. Clarify criminal
  justice/corrections/reentry, criminal-history access barriers and immigration
  detention/removal, while excluding ordinary civil-benefit/record use. Reconcile
  existing labels against the precise final definition; keep catalog001 immutable.
- ArchesBIPOCa184b…: Black is supported by explicit BIPOC therapy. Indigenous does
  not necessarily establish the narrower American Indian/Alaska Native group;
  investigate or omit unsupported Native assignment. Do not infer all ethnic
  groups from a generic people-of-color umbrella.
- Utilities: Billing Disputes (Enbridge014) duplicates earlier Billing & Service
  Disputes. Prefer the earlier broader label/definition, with explicit override.
- Addiction: Detox018 overlaps original Withdrawal care, which is now used in024
  and026. Consolidate Detox to Withdrawal care after preserving its evidence;
  reconcile the two Residential treatment definitions without silently overwriting.
- Employment has multiple older/new labels needing semantic reconciliation:
  Employment Rights vs Employment Rights & Benefits; Job Search Support vs Job
  Search & Career Help; Job Training vs Training & Credentials / Apprenticeships &
  Trades; Job Placement vs Staffing & Job Placement. Retain useful distinctions,
  avoid duplicate filters and do not blindly union the two catalogs. Business
  Support definitions also differ slightly. Supported Employment introduced026
  uses the earlier explicit definition.
- Food provisional amendments remain: AAUTIP should lose Groceries (general food
  is not confirmed take-home groceries), retain Meals. LDS storehouseccb82… should
  lose Food Navigation (generic referrals not food navigation), retain Groceries.
  Reconcile the complete71-resource final Food union with63 native judgments and
  eight later memberships. Preserve all resources.

Catalog001 proposes26 groups, adding Asian American and Native Hawaiian/Pacific
Islander. Every final resource review considers all26. Sensory tags require People
with disabilities parent. New-group evidence is VA Minority9c801…, ITECa3e740…
and PIK2AR RELS3d1b…; do not infer Pacific targeting for PIK2AR pantry74bec… merely
from the provider name. The catalog remains a proposal for human review.

## Finish sequence

Continue complete-record group reconciliation and all remaining category Types /
priorities. Resolve recorded content/identity/category concerns via durable
revisions, preserve each category copy's own text and rebind exact hashes/fingerprint.
Construct a complete navigation proposal only after semantic review, then priorities
bound to that navigation. Resolve duplicate/unused Types and inconsistent group
rules rather than satisfying JSON coverage mechanically.

Use `scout_navigation.py` / `scout_review_priorities.py` normal validators. Inspect
actual rendered four Information headings, reader/editor, Category Types, Browse
by Group, search, Type OR / groups AND and Match any, empty combinations, priority
and A–Z equivalence, reasons/questions, personal overrides/reload, shared progress
and zero new human Curated flags. Preserve browser-local work. Build/report/code
checks alone do not finish this stage.

Only after actual review and UI checks, write the report and record completion for
exact current fingerprint through `scout_review_handoff.py`. Verify the monitor's
actual Save download. Then transition to Las Vegas at High under the office and
orchestration workflows. Never mark completion merely to expose Save.
