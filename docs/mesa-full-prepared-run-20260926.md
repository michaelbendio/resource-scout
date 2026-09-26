# Full Mesa prepared-resource run

Michael authorized Scout re-curation of the saved Mesa research, followed by one
Extra High Codex review and a complete `prepared-resources.json`. Workers run at
High. Cedar City remains held. The first four-category delivery stays immutable.

Current run: `data/mesa-prepared-full-20260926-source-checks/`; database
`research.sqlite3`, import 4, curation job 5. Launch: September 26, 06:42:32 UTC.
The persistent supervisor checks every 30 seconds and preserves worker checkpoints.
The supervisor handles curation only; it does not approve the final export or
launch another reviewer. Verify current processes and logs before resuming.

September26,18:40UTC checkpoint: twelve categories are prepared; Housing is on
batch3/9. Homeless Services working review covers126 batch versions,77 aggregate
drafts,144 dispositions and49 source-only groups/members. Saved proposals contain
two duplicate groups/two rejected category memberships,73 reasons,12 Types,
explicit group decisions,ten starters and14 reserve additions or matches.
Three additions are administrator holds, including both historical LSS I-HELP IDs.
Apply the scoped TCAA/LSS and MANA/SSVF identity corrections before registry binding.
Final whole-office matching, content application, human-state reconciliation and
review signature remain pending.

The progress monitor now appends a remaining-curation ETA after every batch,
using actual candidate-weighted overall/recent pace. At this checkpoint it reads
"Curating Housing: batch 3/9, Done in 6 - 12 hours." This excludes the subsequent
review/export. Monitor28847 replaced20319 on port8773; worker/supervisor unchanged,
and all12 completed category hashes preserved.31 targeted tests pass. The only
initial failure was sandbox denial of a test listening socket; that test passed
with the required permission. Runtime audit: monitor-eta-reload.json.

The earlier `mesa-prepared-full-20260926-all-research` attempt started at 06:12 UTC
and is now held. Its first three completed batches used no live source checks and
overused needs-resolution for ordinary missing details. The coordinator was stopped;
its fourth worker finished separately. All four outputs remain intact and accompany
the current assignments as explicitly unreviewed supporting drafts. Policy v4 now
requires targeted primary-source checks, clearer reserve-state decisions and
client-facing wording. The consumer artifact remains schema version 1. Include the
earlier attempt's approximately 27.9 worker-minutes in eventual processing totals;
its fourth worker's end was observed from its last native event, not coordinator
execution metadata. See `preserved-attempt-timing.json` in the current run.

The input inventory has 3,920 candidate records in 21 research categories, split
into 151 bounded batches. These are overlapping evidence records, not 3,920 unique
resources. Earlier manual discovery, focused research, Codex-first v2 and the
retained Housing pilot are included. The normal canonical-run selector would
omit the candidates behind the September 24 review, so this new prepared job uses
explicit `--all-research-runs` and sealed `--reviewed-context` inputs.

All 341 previously reviewed resources have historical candidate links in the new
assignments. Six saved human resource overrides and seven hidden resources are
retained for reconciliation. The office catalog has 22 exact IDs, including
Miscellaneous. Never substitute the older reviewed seed's 20-category taxonomy.

## Completion work

September26,17:45UTC checkpoint: eleven categories are prepared; Homeless Services
is on batch3/6. Current-run worker execution is about645.2minutes. Medical/Dental/
Vision's164 batch versions,124 aggregate drafts,177 dispositions and64 source-only
groups/65 members have saved working decisions:22 duplicate groups/23 overlaps,
100 retained-category reasons,14 Types,explicit For-group/no-group proposals,ten
starters and22 reserve additions/matches (21 usable,one intake-resolution hold).
These remain unapplied and unsigned. Preserve the Sun Life full-HTML service evidence,
MCC patient phone and discounts,dated clinic closures and vaccine changes,and the
current successor route for PAN copay help. Keep the planned SVdP Mesa clinic on
hold and San Diego's Lions clinic in the audit. Resolve composite DES VR/ILOB scope
and preserve both SVdP medical/dental links for candidate893. All eleven sealed
snapshots equal the live database. Final content application,whole-office matching,
human-state preservation,registry binding and export remain pending.

September26,16:58UTC checkpoint: ten categories are prepared; Medical/Dental/Vision
is on batch4/7. Current-run worker execution is about600.8minutes. Food's130 batch
versions,96 aggregate drafts,158 dispositions and58 source-only groups/members
have saved working decisions:12 duplicate groups/13 overlaps,83 retained-category
reasons,11 Types,explicit food-focused For-group/no-group proposals,ten starters
and14 reserve additions or matches. RSM's senior/veteran canonical identity must
remain distinct from its general pantry/mobile scopes; NATIVE WIC remains distinct
from its pantry, and SVdP food-box routing must survive the dining-room merge.
New primary evidence resolves both Red Mountain pantry locations and current
Phoenix WIC access for Valle del Sol. All ten sealed snapshots match the liveDB;
see review/completed-snapshot-preservation-check-20260926T1658.json. Working
proposals remain unapplied, unsigned and subject to whole-office reconciliation.

The earlier15:24UTC Financial
Assistance's sealed snapshot has 133 resources/188 dispositions; all 176 batch
versions and 50 source-only groups/51 members have saved working assessments.
Working proposals contain 15 duplicate groups/15 overlaps, 107 retained-category
reasons, 14 Types with explicit assignments, ten starters and 19 reserve proposals
(18 usable, one administrator identity hold). Several proposals match later worker
drafts. Four content patches address consequential H2O eligibility/referral,
Police/Prosecutor contact confusion, Energy Share intake and dated VITA details.
Final whole-office matching, human-state reconciliation, fact application and
signature remain pending. The City utility umbrella/two-program overlap still
needs a final identity decision. Working proposals are not a completed review.

- Audit all candidate dispositions, cross-batch merges and prior reviewed pathways.
- Review program identity and bind aliases to the existing committed registry;
  preserve the canonical IDs in the four-category delivery and all human state.
- Complete the five-section content, source, service-area and uncertainty review.
- Derive useful Types/groups from the complete collection, retaining existing
  taxonomy IDs where their meanings remain the same; record assignment evidence
  and explicit no-group decisions.
- Select 7–10 complementary starters per category, with contributions and limits;
  explain genuine size exceptions. Assess Miscellaneous explicitly.
- Give every non-starter resource/category pair a specific consideration reason,
  checking comparisons against the actual starters.
- Seal the reviewed bundle, validate and export a new complete delivery with the
  partial snapshot as predecessor. Review its readable preview. Commit the updated
  registry before handoff. WSRS-TSO performs actual import validation.

Keep timing from `supervisor-start.json`, each worker's `worker.json` and completed
execution metadata. Report elapsed time separately from accumulated worker time.
The initial launch passed 28 focused tests and 17 legacy curation regression tests;
the corrected policy passed 29 focused tests, including sealed-policy compatibility.
The earlier `data/mesa-prepared-full-20260926/` is a rejected preflight, never a
second runnable job. No paid worker ran there.

## Saved category repair and preliminary review

At08:47UTC, Children/Pregnancy batch5 stopped because one visitation-center
resource added an invented `foster-kinship` category alongside its valid
`children-pregnancy` membership. The automatic link-only repair correctly left
it unchanged: its contract forbids editing categories. That unnecessary repair
call exposed a runner defect: any validation error had been routed to a worker
that could only correct links. The runner now distinguishes repairable link or
placeholder errors from other validation failures. Category/For-group/content
errors stop for supervisory judgment without that paid call.

The supervising review removed only the invented extra category in a hashed
`reviewed-result-repair.json`; all27 resources,28 dispositions, facts, source
links, IDs and original worker files are preserved. Validation passed before
resuming. Prepared validation also now uses the sealed office catalog, so Mesa's
Miscellaneous category is permitted even without a discovery assignment. Unknown
IDs still fail.40 focused recovery/preparation tests passed; the test log is
`/private/tmp/mesa-recovery-tests.log`.

`recovery-001.json` records the controlled restart. Supervisor12216 and
caffeinate12217 replace the stopped processes; verify live state. The prior
launch count remains recorded, with a total ceiling of3 to allow the known
repair resume and one bounded transport recovery. High effort is unchanged.
The failed repair's execution time remains in accumulated processing totals.

All 135 Addiction, 123 Children/Pregnancy and 122 Clothing/Household draft
Information bodies, descriptions and contact/source fields have received an
initial read. Targeted primary checks, corrections and identity proposals are
saved under `review/`; none is a signed final review. Explicit source-routing
assessments now cover all 75 Addiction, 55 child and 45 clothing source-only rows.
Addiction has six usable direct-program restoration proposals, one administrator
hold and seven public navigation/service proposals. Children has 11 restorations;
Clothing has three usable proposals and one administrator hold. Whole-office
identity matching is required before adding any record.

The child identity file proposes 17 duplicate groups covering 19 overlaps;
Clothing proposes 17 groups covering 18 overlaps. Working ledgers contain 135
Addiction, 104 child and 104 clothing individually authored consideration reasons.
Prospective starters are included: export only final non-starter pairs and recheck
comparisons after selection. Child and Clothing have explicit Type assignments
for their 104 provisional distinct records and ten-member starter comparison sets.
Current source responses are preserved under `review/source-checks/`.

At 11:05 UTC, Disability completed with 140 draft resources and 227 candidate
dispositions; its immutable completed snapshot is saved. Scout advanced to
Domestic Violence. Disability findings001–008 cover all
194 batch resource versions; the aggregate differs only by unioned candidate IDs
and groups. All61 source-only groups and their members have explicit assessments.
Working proposals contain14 merge groups/18 overlaps,122 consideration rows,
14 Types with explicit assignments, ten starter contributions/limitations, and
18 reserve additions. Full-office identity, group and human-state decisions remain
pending; none of these drafts is a final signed output.

Material review points include omitted DDD onset/functional eligibility, the
fact that statewide Pre-ETS does not require VR membership (one provider still
requires a VR referral), countable versus gross earnings for Freedom to Work,
Ticket to Work's ages 18–64, and preservation of human-hidden identities. The
new `az-caregiver-coalition-respite-230` draft describes the same program as hidden
legacy `b21220ad00416ac580741d14ba3a1e7d`: merge those affirmed aliases while keeping
the human suppression. Preserve current canonical Valley Metro identity and its
supported services when later disability-focused drafts omit other transit paths.

Source checks also distinguish temporary intake/office pauses from closure:
DRAZ announced September28 reopening; AzTAP posts an October2 closure and October5
reopening. Recheck date-sensitive notices at delivery. About316.5 current-run
worker-minutes are accumulated, plus the preserved initial attempt; final timing
must be recalculated after completion.

Additional source checks corrected three consequential details: Power AZ stopped
accepting applications after September21 while LIHEAP remains separately active;
Disability Help Group's current representation fee terms conflict with an old
no-charge directory claim; and the2026–2027 Family Transition Navigation pilot
requires public-school enrollment and a current IEP as well as age14–22. Mesa's
paused emergency-repair program retains only a clearly labeled future-interest
route; RTVOS ramps remain an audit watch because applications are closed. These
are proposed evidence-backed corrections, not claims of office approval.

At 12:08 UTC, Domestic Violence is complete and Education is on batch 2/5.
The Domestic Violence immutable snapshot has 91 resources and 184 dispositions;
all 162 batch versions and every member of 48 source-only groups were read.
Its working identity proposal has five groups/six overlaps; three memberships
are proposed for removal or audit-only handling (closed SERF funding, generic
one-n-ten partner routing and unconfirmed ACDHH direct DV service). Working files
contain 82 retained-category reasons, 12 explicitly assigned Types, ten starter
contributions/limitations and eight reserve restoration proposals. Seven are
proposed usable and ASAFSF remains administrator-only because its former website
now redirects to unrelated gambling content. This is not evidence of agency closure.

Material Domestic Violence findings: centralized SAFEDVS placement guidance
conflicts with current provider evidence, so direct shelter contacts are needed;
HonorHealth's non-reporting sexual-assault-exam route is an evidenced 24-hour
callback, not necessarily a live operator; Fresh Start now provides free legal
document preparation and disallows children at appointments/classes; approved
court organizations do not necessarily have an active certified advocate.
Current primary pages support narrower usable records for SWIWC's public directory
and Sahara's Arizona-facing survivor program; missing bed counts or a general
licensing question alone were not grounds for exclusion. Preserve the source
checks and exact program limitations. DOVES ancestry still intersects the hidden
historical AAA umbrella and must be resolved before publication.

Current-run worker time includes the failed repair and is separate from this
supervising review's wall time. No final review, human approval or import is signed.

Later versions, global identities, final taxonomy, all-category starters/reasons,
human-state preservation and final review/export remain pending. Read
`review/final-assembly-plan.md` before applying corrections: later versions may
add useful facts that an earlier body must not overwrite. Nothing here is human
Curated approval or a completed full-office export.

At 12:48 UTC, six categories are prepared and Employment is on batch 2/11.
Education's sealed snapshot contains 82 resources (80 worker-usable, two worker
holds) and 136 candidate dispositions. All 116 batch versions and 90 source-only
groups/members were read. Ten source-backed reserve proposals are saved; Grace
and ETV now match completed drafts, so they are not automatic additional resources.
Remaining source-only program checks, final Types, starters and reasons are pending.
The root reviewer independently confirmed Make Welcome is a Charlotte, NC program.

Education exposed a draft-ID program switch between the City Workforce Center at
635 E. Broadway and the County East Valley Career Center at 1001 W. Southern.
Resolve the source aliases explicitly before registry binding, preserving both
programs and the earlier human MesaCAN override. Do not blend their contacts.
Restore Graduation Alliance's administrator hold because current state funding
and its old advertisement conflict; Smart Schools' closed workforce-funded intake
does not prove Graduation Alliance has a waitlist. Grace UMC Mesa's current calendar
supports a narrower usable adult-learning record. Preserve distinct Mesa, Maricopa
and Arizona Promise eligibility and correct Friendly House's program-site address.

Current-run accumulated worker time is about 356.4 minutes, plus the separately
preserved initial attempt. Live PIDs and actual execution metadata confirm High
workers; this root session retains the single Extra High review. No final review
or complete export is signed.

At 13:11 UTC, Employment is on batch4/11, with 373.0 accumulated current-run
worker-minutes. All64 resource versions from its first three batches have working
review findings. Live worker18667 was confirmed at High during its output interval;
the supervisor/coordinator remain12216/12219. Verify again rather than reuse PIDs.

Education now has four proposed identity groups/five overlapping records, two
specific closed programs retained in Scout audit, 75 retained-category reasons,
13 defined/used Types, ten explained starters and26 restoration proposals. Grace
and ETV match existing drafts; cross-category matches remain explicit. These are
working judgments, not applied resources or a final signed taxonomy.

The City/County workforce ID switch is now traced to nine original candidates and
the prior reviewed collection. Historicalc3ab belongs to the City Broadway center;
the original444882 draft belongs to the County Southern Avenue center. Apply the
source-level decision in `review/education-workforce-identity-resolution-working.json`
before registry allocation, retaining the human7f314 City override and separate
MesaCAN program identity. Rebind the Education row-based reasons/Types by their
intended program; do not trust the exchanged worker IDs alone.

Employment primary checks also found CPLC's15–18 Growth Opportunities grant targets
Las Vegas/North Las Vegas, while its Phoenix WIOA/YouthBuild programs remain useful.
The A New Leaf Transition Academy lead belongs to Owasso, Oklahoma, not Arizona.
DES/IRS pages still describe WOTC2026 applications held pending renewal; do not
promise a current tax credit. SNAP CAN's16+/Nutrition Assistance/not-TANF eligibility
and SCSEP's55+/income/employment-barrier rules were checked against current DES pages.
No original worker output, human approval or WSRS-TSO state has been changed.

At 13:33 UTC, Scout is on Employment batch7/11, with 51 completed executions and
397.5 current-run worker-minutes. Batches1–6 contain145 reviewed resource versions;
each has durable findings. The source-only inventory has54 groups, all read, with
11 verified reserve-restoration proposals so far. Sources and findings live under
the current run's `review/`; full-office matching and final application remain pending.

New review corrections include removing healthcare-category memberships from a
college behavioral-health certificate, distinguishing shelter-enrolled employment
help from public job services, and retaining pre-release enrollment restrictions
for Father Matters and Televerde pathways. St. Mary's Skills Center publishes
material drug-screening, background, housing and full-time attendance requirements;
replace the worker's vague wording. Preserve the separate Kitchen and LIFT tracks.
The state Pre-ETS contractor directory confirms usable EES and Empowering Services
contacts despite limited/maintenance-mode provider pages. Do not infer closure.

At 13:50 UTC, Employment is on batch9/11; 53 completed executions total414.3
current-run worker-minutes. Its first eight batches contain199 reviewed versions.
All54 source-only groups now have explicit working dispositions, including19
reserve proposals and matches to existing programs. Several proposals (Father
Matters, Empowering Services, HBI) now have later worker matches; consolidate them
before adding anything. The original outputs are unchanged.

Two `employment-content-patches*` files contain22 explicit client-facing fixes for
final assembly, supplementing the per-batch findings. Apply only after program
identity and full-office service preservation are resolved. Current Habitat CTP
evidence lists $13,995 tuition with potential funding, whereas HBI's separate
Phoenix program is tuition-free for accepted participants. Current FBC evidence
supports a narrow usable prison-braille training route; its unconfirmed EPIC/public
parolee extension stays out of offered services. These corrections are not a signed
review or a completed export. User ETA update at13:30 estimated12–14hours for
remaining curation alone; final review/export requires additional time.

At14:14UTC, Employment is complete and Financial Assistance is on batch2/8;
57 completed executions total442.2 current-run worker-minutes. Employment's
260 batch versions, 183 aggregate drafts and18 special merge rationales have
been inspected. The276 disposition links are accounted for; the combined
Apprenticeship/Workforce2You source candidate needs links to both distinct programs.
Working proposals contain14 duplicate groups/17 overlaps,163 membership reasons,
11 Types with explicit assignments and ten starters. These remain unapplied and
unsigned. Televerde, Father Matters Reentry and Empowering Services restoration
proposals now match completed Employment drafts; preserve their richer facts.

Root primary checks confirmed MCC Welding's480-461-7131 program phone and
NATIVE HEALTH Mesa's separate BuildingC Tuesday workforce session and BuildingD
Monday/Wednesday/Friday benefits sessions. The latter supports AHCCCS/SNAP/TANF,
not a Utilities category. Pima Medical Institute is training, not a patient-care
provider. PeopleReady's two verified Phoenix branches are alternatives, not a
replacement address or an invented Mesa location.

The current-run Mesa dashboard is on127.0.0.1:8773, detached PID20319 at launch,
with its command in `dashboard-start.json`. HTTP status and Mesa import4 were
verified; no second curation coordinator was started. At14:06UTC the user received
an estimated12–14hours for remaining curation and18–24hours for final delivery,
with review overlapping curation and final assembly/validation afterward.

At16:10UTC, nine categories are prepared and Food is on batch4/6. There are73
completed executions and558.3current-run worker-minutes. Reentry Support's114
batch versions,103aggregate drafts and138dispositions have been read; all80
source-only groups/81members now have explicit working decisions. The review
proposes11duplicate groups/12overlaps,86retained-category reasons,11Types,
ten starters and23reserve restorations (20usable,3administrator holds).
These are durable proposals, not applied revisions or a signed final review.

Before combining IDs, apply the scoped Smart Justice identity correction:
Reentry row24 reused the general County Career Center ID, while its facts and
candidates describe the distinct Smart Justice program. Preserve the general
County canonical identity and bind the program occurrence separately. New
Freedom's existing canonical identity already covers core and outpatient
services; preserve it with separate program rules and contacts in the text.

Primary-source review retains AZRSOL's limited reentry expense grant, GLO's
transport/ID help, Bridges women's residential program, federal-supervision
treatment and family/custody pathways that were left in source-only material.
It also corrects a website-vendor phone mistakenly presented as housing intake,
removes unsupported Stone income/insurance groups, and separates civil mental-
health and dependency court programs from criminal Reentry membership. The
in-custody Merging Two Worlds omission needs a usable facility-case-manager
pathway linked to its original candidate, not silent deletion from the evidence.

The latest user ETA, at16:02UTC, is September27 roughly1–7a.m. Mountain time
(15–21hours), including full-office consolidation, review and validation.

Food batch4 stopped on an invalid For-group label on Family Promise. The root
removed only `Children/Pregnancy`, retaining valid Families/Homeless/Pet owners
and every factual field, ID, source and candidate decision. All27resources and
28dispositions pass full application/link validation; the repair loader verifies
the preserved original and correction hashes. No replacement model call was made.
`recovery-002.json` records the repair and preserved pre-recovery status.
Supervisor25181/caffeinate25182 resumed coordinator25184 at High; cumulative
launch count3/max4 retains one bounded transport recovery. Food batch5 has fresh
native events. Verify live processes before any later recovery.

Food batches1–3 contain63read resource versions with saved findings. Root primary
checks resolve St Stephen's pantry operation and published Wednesday evening
session, retain House of Refuge's literal Monday-and-Friday hours, and distinguish
RSM's senior federal boxes from separate under60 veteran assistance. UFB's Mesa
Neighbor's Pantry and TCAA's Tempe pantry are separate programs; preserve their
source and identity boundaries. City Hope's location-specific page establishes
food-only service in Mesa, government ID, one visit per center per month and an
arrival cutoff fifteen minutes before closing; the generic home-page text does
not establish clothing service there. Full-office review and delivery remain pending.

### 17:54 UTC recovery checkpoint

Homeless Services batch3 emitted a nonexistent `youth` category on HomeBase.
The reviewed repair removes only that category, preserving the valid Youth For
group, every fact, all27 resources and29 candidate dispositions. Full application
and link validators plus the hash-checking repair loader pass. Original native
output and events are unchanged. `recovery-003.json` records the evidence and
preserved supervisor state. Supervisor27600/caffeinate27601 resumed High curation
and advanced to batch4/6. This consumes launch4 of the existing maximum4; no
unchanged automatic retries remain. Eleven completed categories remain intact.
The root review continues; none of its working proposals is applied or signed.
## Challenger selection correction — September26,19:50UTC

Michael requested DeepSeek alone. Live process inspection found no research
workers: only supervisor27600 and High curation coordinator27606 were running.
The three challengers in the monitor were completed historical Mesa research,
not new calls. The monitor now labels the results historical. New plans select
DeepSeek only; the worker policy also blocks Grok/ChatGPT/Perplexity probes and
calls. Native DeepSeek packets now work with the independent challenger; old
sealed handoffs remain readable. No sealed research/curation input was changed,
and no worker restart or new research was needed. Browser automation was
unavailable; the live served JavaScript was verified byte-for-byte and curation
continued at ID Recovery3/5 with a5–9hour curation-only estimate.
Validation:41 relevant tests pass, including native DeepSeek import, preserved
legacy handoffs, blocked probes and HTTP progress; JavaScript syntax also passes.
