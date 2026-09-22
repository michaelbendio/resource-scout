# Welfare Square active-run handover — September 21, 22:44 MDT

Verified September 22, 04:44 UTC. Read this and the newest SCOUT_STATUS entry first.
This supersedes the earlier September 21 paused handover. Work is unfinished.

## Authorization and context discipline

Michael: “Finish the job. Then review without asking me.” Then “BTW, you probably
want xhigh.” Then “When you do your review be very judicious about what you include.”
Latest: “I've got 5% context. Make a handover. Can you radically reduce your
contribution to the context?” Handover is requested; no worker pause was requested.

Continue existing curation and the already-authorized root review without another
approval. Keep xhigh. Select actionable, distinct or consequential pathways; omit
weak fits and redundant alternatives with explicit reasons and preserved research.
No numerical quota, new core/reserve UI, human Curated marks, or office publication.
No further Grok, Claude or DeepSeek inference is needed. Do not spawn subagents.

**Keep context small:** query summaries and exact fields; inspect saved final
results in about 5–8-resource chunks. Do not print full event streams, whole JSON
results, repeated intermediate model output, or concatenate large documents.
Put detailed findings in audit files; report changes/counts/decisions briefly.
The preceding turn lost context through oversized tool output; do not repeat it.
Read required operating documents individually with bounded output, not one huge
parallel result. Do not reread reviewed records absent changes or a specific issue.

## Live state

- Checkout `/Users/michaelbendio/resource-scout-pairwise`, branch
  `pairwise-research-experiment`.
- Original database `data/welfare-square-production-20260921-codex-grok/research.sqlite3`,
  import 1, curation job 1. Office Welfare Square; all Salt Lake County, Utah.
- Research 21/21 complete. Curation 2/21 complete: Addiction 73 selected resources;
  Children/Pregnancy 96 original curator drafts, not yet root-revised.
- Clothing/Household batch 1/4 active. Coordinator PID 79229; persistent supervisor
  PID 79234; live processes verified; coordinator restarts 0. Native events were
  19 seconds old at the 04:44:15 supervisor sample. SQLite quick_check OK.
- Runtime `data/welfare-square-curation-20260921/`; read
  `supervisor-status.json` for current native event path, liveness and category.
  Supervisor stays running across this conversation handoff, with bounded recovery.
  It does not conduct substantive review or recover every possible failure.
- Runner uses gpt-5.5/xhigh, 30 candidates/60,000 characters, max 21 completed
  categories. First Addiction batch originally High and preserved; all new batches
  xhigh. Total plan 100 batches, 2,153 candidate identities including 77 supplements.
- Verify live state before action; never launch a duplicate worker or rerun research.
  Read AGENTS.md, docs/scout-orchestration.md and docs/scout-workbench-readiness.md.
  Monitor actual native activity at least once/minute while supervising.
- Last quota read 04:31 UTC: 58% remaining, resets Sept 25 at 14:12 MDT. This is a
  snapshot, not a forecast. Read-only helper: audit/read-usage.py under runtime.
- Welfare monitor 8770 (previous PID 78304); St. George 8769 is separate and complete.
- Unrelated tracked deletion `docs/scout-discovery-and-maintenance-proposal-20260920.md`:
  do not restore, stage or commit it.

## Research/cost preservation

All 112 original primary passes, 21 original external assignments, 16 original
completed jobs and 128 original contributions were preserved. Five DeepSeek
replacement records 22–26 completed; original Grok 17–21 remain historical assigned
records. Keep 16 saved Grok results. DeepSeek produced 136 raw submissions through
125 calls; peak-price estimate $0.811819368 includes one output-limit failure.
Observed balance $6.52 at 03:01 UTC; billing lag possible. Search and Codex are excluded.
Evidence: `data/welfare-square-deepseek-finish-20260921/`, including source-audit.md.
77 reviewed supplements: Housing 22, Employment 20, Disability 35, sealed inputs.

## Review evidence map

All following paths relative to `data/welfare-square-curation-20260921/audit/`.

- `review-plan.json`, `batch-plan.json`: selective-review contract and batch plan.
- `content-checkpoints/`, `selection-checkpoint-*`: reviewed batches and reasons.
- Addiction all 85 original drafts and 91 dispositions read; versioned corrections
  applied in `addiction-source-revision-001/`, `-002/`,
  `addiction-selection-revision-001/`. **Do not rerun applied scripts.**
- `apply-addiction-selection.py`: example of guarded supported revision API use.
- `cross-category-correction-obligations.json`: later copies needing reconciliation.
- `addiction-navigation-priority-checkpoint-001.json` and `-002.json`: all 73
  selected resources have manual provisional Type/priority/reason/evidence/question
  decisions. Not installed final navigation or priorities. Complete category-fit,
  literal Type evidence, For catalog decisions, and final-copy reconciliation first.
- Children saved batches 1–4 fully read, including all dispositions; respective
  output counts 26/22/23/19. **Batch 5 still needs a bounded full read**. Last tool
  printed it alongside large documents and truncated output, so do not count it
  reviewed. Path: `job-1/children-pregnancy/*/batches-v1/005-*/validated-result.json`.
  Category final has 96 resources and 112 candidate identities; verify exact links.
- Children batch 3 early intermediate output differed substantially from the final.
  Final had 23 resources and 19 web events, all read. Concern about blanket unverified
  dates was resolved in `children-pregnancy-batch3-verification-finding.json`.
  Do not clear dates wholesale or rerun this paid batch. Use saved validated results.

## Addiction final-copy obligations

85 original → 84 after De Novo/True North predecessor-successor merge → 73 after
11 specifically reasoned exclusions. Keep True North ID
`e1d33bef2b38538b89408aa970177ce6`; candidate 16 and 59 link there. Current address
120 W Vine Ste 140, Murray; 801-263-1056; source truenorthutah.com/about-true-north/.
Old De Novo pregnancy priority is not established for the successor.

Excluded: A/D Psychotherapy, Anicka, Ascend, Brighton, CMAP, Pinnacle, Red Willow,
Upward Motion, Steps Murray, Turning Point, Wasatch Recovery. Use exact IDs/reasons
from applied script/evidence, not name-based deletion. They were not declared
closed or poor quality. Other category inclusion requires distinct supported value.

Corrections also include supported hours, crisis-line distinctions, VOAFCC age,
Haven Sublocade policy (not Suboxone), LDS withdrawal contact and plain user wording.
Later copies may overwrite corrected bodies because `_completed_resources` unions
memberships but latest body wins. Final all-copy consistency is required. Addiction
CHC screening may merge with Children CHC clinic network; Corner Canyon/Valley CORE
are primarily Mental Health. NEMT/TAM Justice should retain appropriate memberships.
Later Children updates to SUPeRAD/Project Reality/House of Hope must be reconciled.

## Children pending revisions — prepared, NOT applied

`children-pregnancy-prepared-source-corrections-001.json`, `-002.json`, `-003.json`
contain source URLs and exact expected-old/new fields. **Collapse to the latest
decision per (resourceId, field)** before checking against final category. The 003
South Main patch supersedes 002 because batch 4 added teen-clinic facts. If batch 5
changed a field, inspect and deliberately reconcile; never overwrite blindly.

Prepared changes: obsolete Midtown PCN removal (ended April 2019); supported access
hours; Children's Center eligibility/fees/referral; South Main uninsured discounts;
Healing Group removal of invented two-year eligibility limit; Family Support Center
crisis nursery site hours; SUPeRAD current call/text 385-881-3035 M–F 8–5; Road Home
Connie Crosby family shelter 24h and correct identity; OWH Mountain hours; WIC five
direct clinic numbers/hours; CHIP versus State CHIP (State CHIP new enrollment closed
Jan 31, 2026, existing members remain covered); Medicaid pregnancy/postpartum/temporary
BYB/PE distinctions; Canopie app versus live care; emergency Medicaid plain wording;
DWS childcare work/age criteria and immigration/SSN distinctions.

Restore useful omitted candidate 112 using `children-pregnancy-restore-guadalupe.json`
(ID bd09046bcfe45fec8b80de746131e4b1): free weekly Guadalupe home visits pregnancy to
age 3, Lupita Avila, 801-531-6100. Sources current ELC overview/staff and indexed
program page; direct fetch failure is not closure.

`children-pregnancy-proposed-guadalupe-center-merge.json`: combine center toddler
and preschool programs (candidates 111/113), keep a95b7fa7afa25ef6b6245b236dcfb67f,
remove 0922a29f28405097b2adc3b8be343328. Preserve age-specific schedules, free program,
lottery/waitlist, preschool-only bus qualification. Home visits remain distinct.

Proposed omissions for specific low added value (not yet final/applied):
- 92 Similac 9bff8c598cf05cf597b9192885130dde: corporate feeding info, no formula aid;
  WIC and clinical pathways are more actionable.
- 124 Intermountain routine midwife e338b9d3c729590b9a7abaeba7d6767b: generic billed
  clinic, unclear affordability; retained subsidized clinics and distinct specialist
  or virtual/24h on-call birth-care pathways cover stronger access options.
- 127 Primary Pantry b06360b84b305b87b74d3d636dfc3602: 2023 hospital patient-only
  announcement, no current direct hours/intake; public pantries more actionable.
- 139 PCAU PAT 6eeb96628aae55b8b1fa0a471857d6d0: unclear current pilot/model/intake;
  county PAT, district PAT and Guadalupe have clearer active access.
- 141 Promise Baby and You 8346a9019e82533aa545d49a8cd25dfd: judgment still needed.
  Free 9-session course Sept 12–Nov 14 Saturdays already underway; application link
  remains, so do NOT claim closed. 2027 coming soon. $500 My529 requires all sessions
  and child SSN/TaxID; ongoing alternatives may justify omission. Source
  https://promise.sslc.gov/baby-and-you.
- 176 MyLantern dfc31be3a41a507f91e25a7f49f1b521: generic automated parent tips add
  little alongside active classes/home visiting/care coordination.

Ohana candidate 136 / 6cec681ce58159779c0ce78750439395 likely merits narrow retention,
but needs source-scope correction: https://ohanabeginnings.life/services/therapy-services/
explicitly describes referrals to external professionals, not direct clinical therapy.
General services page offers mentoring, navigation, six free parenting classes and
baby items. Do not imply direct daycare/therapy or infer religion/medical policy from
partners. **Read the childcare-services/ and parenting-classes/ pages**: opened in
prior turn but not fully read. Then prepare evidenced changes and category fit.

Possible further merge (not prepared): ISP 681a69f8d28b54249144acb2797ebe2b and 0–8
b0625e08f4ef529b90d3b3cbbf3c0a46 under same Utah program umbrella, candidates 185/186.
Keep distinct eligibility/contacts: ISP ages 0–22 special needs 801-273-2988;
0–8 all parents 801-273-2804, no disability requirement. Both free navigation, not
clinical treatment. Source familyhealth.utah.gov/cshcn/integrated-services-program/.

Batch 4 omitted NEMT 182 and SNAP 190 for category fit only: check later Transportation/
Medical and Food/Financial retention. Batch 3 restored St Andrew pantry 144 already;
do not duplicate. Forever Ours is former Share Parents Utah; reconcile aliases later.
Keep rare consequential pathways (perinatal palliative care, donor milk, Spanish
grief, hearing aid assistance, safe haven, etc.) when useful; small numbers don't
justify dropping them. Do not infer For groups just from parent services/languages.

## Applying and finishing

Read final Children batch 5; decide final omissions/merges; apply prepared corrections
with before/proposed/evidence snapshots and expected-result-hash guard through
`revise_scout_curation_result`, preserving immutable batch outputs. Inspect example
script first. Every candidate needs an exact disposition/resource link. Update
cross-category obligations because Clothing was sealed before Children revisions.
Use SQLite read-only for inspection; ResearchStore initialization may migrate and
is reserved for intentional supported versioned writes.

Continue reviewing saved batches while supervisor curates remaining categories.
Do not alter sealed prompts to reduce worker output: `write_once(prompt.txt)` also
checks completed batches on resume; a prompt edit can break sealed resumption.
No worker-prompt code change was made or promised. Typical xhigh batches take
8–20 minutes; native activity, not heartbeat alone, establishes progress.

Still required: content/omissions audit, cross-category identity/body/category
reconciliation, useful Types with complete evidenced assignments, For-group catalog
and every-resource decisions including explicit no-group reasons, category-specific
human review priorities with literal evidence/reasons/questions. Then actual HTML
reader/editor and combined filters, priority/A–Z same resources, local overrides,
shared progress and zero human Curated marks. Consult readiness document/API.
Only after actual full review use exact fingerprint `scout_review_handoff --complete`;
never record merely to expose Save. Verify 8770 Save endpoint and deliver
autoWelfareSquare.html plus report. No office publication.

Before Safari work after compaction call `cua.rewriteDocumentation()`. Do not reload
or reset other open Mesa/Provo/St. George tabs with browser-local edits. Use Welfare's
own artifact/storage identity. Save original research, curation and revision history.

Prior code commits 75fa094/05cb92c passed CI; 278 tests, one optional skip, and nine
recovery checks passed. No code changes in the latest review segment. Recent pushed
handoff commits 9d317c9/fc3f028. Update scoped status/review documentation and commit/
push meaningful checkpoints; exclude unrelated deletion. Data-only review corrections
need targeted integrity/source checks, not repetitive full test suites.
