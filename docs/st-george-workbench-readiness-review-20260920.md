# St. George workbench completion and prevention review — September 20, 2026

The replacement workbench contains **879 resource proposals**, Types in all **21 Categories**, and **25 proposed For groups** derived from these records. All 879 Information fields now have Stephanie’s four distinct headings with text beneath each. This supplement corrects the incomplete delivery assessment in the earlier [content review](st-george-curation-review-20260920.md).

Michael authorized a St. George-specific group proposal and confirmed he had only inspected the old download. No human work needed migration. The navigation remains a proposal for human vetting; no resource was marked Curated.

## What changed

- Reformatted saved eligibility, connection, access and important-information text into four standalone bold sections. Retained existing body text, source links and limitations. Copied saved hours into Access; three records with no saved hours explicitly say the schedule needs confirmation. No new availability facts were invented.
- Defined service Types in every Category and assigned at least one in each resource’s Category memberships. Multiple Types are permitted where supported.
- Assigned evidenced For groups to **674** resources. The other **205** have explicit no-group decisions. Broad public availability does not require a population label.
- Stored navigation as a SQLite revision with definitions, per-assignment source excerpts, reason and exact curation hash. Preserved original facts, IDs, Categories, candidate links and worker outputs.
- Added structural release checks, regression tests, visible monitor explanations and a mandatory review checklist linked from AGENTS.md. Later resource or navigation changes invalidate the earlier review.

## Where prevention belongs

Both code and instructions are necessary. [Scout’s readiness checks](../resource_research_agent/scout_review_readiness.py) enforce completeness before a review can enable Save. [Navigation validation](../resource_research_agent/scout_navigation.py) requires definitions, full assignment coverage and evidence or explicit no-group decisions. The [review checklist](scout-workbench-readiness.md), required by [AGENTS.md](../AGENTS.md), governs meaning, source scope and actual browser behavior. A machine can check that an excerpt is present; its presence alone does not establish that a label is justified.

The omission started with an empty imported taxonomy and a worker rule allowing only supplied labels. Export had not lost data. The missing step was post-curation navigation design, compounded by a review that checked topic keywords instead of rendered sections and working finding aids. The existing Mesa-specific prototype was not safe to apply unchanged to St. George.

## Proposed For groups

Counts overlap. These are initial finding aids, not new eligibility claims or human-approved office taxonomy. Definitions and every evidence excerpt are retained in the local proposal.

| For group | Resources | Meaning |
|---|---:|---|
| People in recovery | 70 | Explicit substance-use recovery, sober-living or treatment support for people affected by addiction. |
| Veterans & military families | 93 | Explicit veteran, military, dependent or military-family eligibility or dedicated support. |
| Seniors | 51 | Explicit older-adult or senior eligibility or dedicated service. |
| Families with children | 92 | Parents, children or family households explicitly served. |
| Children & teens | 172 | Direct services or eligibility for minors, including adolescents. |
| Young adults | 22 | A dedicated young-adult or transition-age service, not general adult eligibility. |
| Pregnant & postpartum people | 41 | Explicit pregnancy, prenatal, postpartum or maternity support. |
| Women | 13 | A women-specific program or explicitly limited female population; general access is insufficient. |
| Men | 4 | A men-specific program or explicitly limited male population. |
| People with disabilities | 133 | Explicit disability eligibility, dedicated support or documented accommodation. |
| Deaf & hard of hearing | 12 | Dedicated hearing-related support or documented Deaf access. |
| Blind & low vision | 13 | Dedicated vision-disability support or documented blind access. |
| Spanish-speaking people | 41 | Documented Spanish service, materials or meeting access; confirm availability where qualified. |
| Immigrants & refugees | 41 | Explicit immigrant, refugee, newcomer or asylum-seeker support. |
| Native & tribal communities | 19 | Explicit tribal, American Indian or Alaska Native eligibility or service. |
| LGBTQ+ people | 12 | Explicit LGBTQ services or documented affirming specialty. |
| People experiencing homelessness | 29 | Explicit homelessness service, eligibility or prevention targeting unhoused people. |
| Abuse & violence survivors | 55 | Explicit services for survivors or victims of abuse, assault, trafficking or domestic violence. |
| People leaving incarceration | 22 | Explicit reentry, justice involvement or release-related support. |
| Low-income households | 83 | Explicit income restriction, means-tested benefit or income-based discount; free alone is insufficient. |
| Uninsured & underinsured | 16 | Explicit uninsured access or inadequate-coverage eligibility; not inferred from all health care. |
| Caregivers | 48 | Dedicated caregiver or family-carer support, respite or training. |
| Foster & kinship families | 13 | Explicit foster, adoption-from-care or kinship-family support. |
| People with serious illness | 15 | Condition-specific help for people with cancer, kidney disease or other named serious illness. |
| Students | 44 | Requires current student enrollment or explicitly targets students; open public learning alone is insufficient. |

## Category Types

| Category | Types |
|---|---|
| Addiction | Treatment costs & coverage; Crisis & withdrawal care; Outpatient treatment; Residential treatment; Medication treatment; Recovery housing; Peer & family support; Court & DUI services; Overdose prevention; Tobacco cessation; Treatment navigation; Co-occurring care |
| Children/Pregnancy | Pregnancy & newborn care; Child care; Parenting & family support; Development & disability; Safety & protection; Youth support & activities; Supplies & basic needs; Health & counseling; School & learning; Foster care & adoption; Family legal help |
| Clothing/Household | Clothing & shoes; Diapers & baby supplies; Furniture & household goods; Hygiene & personal care; School & work supplies; Medical equipment; Basic-needs assistance |
| Disability | Benefits & rights; Daily living & support; Equipment & access; Communication access; Child development; Employment support; Education & skills; Health & rehabilitation; Caregiver & respite help; Transport & housing; Activities & peer support; Service navigation |
| Domestic Violence | Crisis & safety planning; Shelter & housing; Legal protection; Victim advocacy; Medical & forensic care; Counseling & support; Financial & practical help; Privacy & digital safety; Abuse reporting & prevention |
| Education | Business & life skills; Citizenship & civics; Adult basics & GED; English & language learning; College & career pathways; Tuition & financial aid; Job training & apprenticeships; Tutoring & learning support; School & early learning; Disability accommodations; Digital skills & access; Libraries & enrichment; Parent & student support |
| Employment | Job search & placement; Skills & job training; Career coaching; Supported employment; Self-employment; Work access & benefits; Workplace rights |
| Financial Assistance | Rent & housing costs; Utilities & connectivity; Food & family benefits; Medical costs & coverage; Taxes & credits; Money & debt counseling; Disability & retirement benefits; Emergency & targeted aid; Education & work costs |
| Food | Targeted food assistance; Groceries & pantries; Meals & community dining; Home-delivered food; Nutrition benefits; Produce & gardening; Infant feeding; Food access guidance |
| Homeless Services | Work & communication access; Shelter & overnight stays; Housing entry & placement; Outreach & case management; Food & daily necessities; Documents & legal access; Health & recovery; Youth & school access |
| Housing | Medical travel lodging; Affordable rentals & vouchers; Rent & eviction prevention; Transitional & supportive housing; Shelter & crisis housing; Housing counseling; Homeownership & foreclosure; Repairs & accessibility; Residential care; Housing rights & legal help |
| ID Recovery | Mail & official documentation; Birth & vital records; State ID & driver licensing; Social Security documents; Immigration & travel documents; Document assistance; Legal identity & records |
| Immigration | Immigration legal help; Citizenship & civics; Refugee settlement; Language access & learning; Consular & identity services; Rights & safety; Community & benefits access |
| Legal | General legal aid & referral; Family & protective orders; Housing & tenant rights; Immigration law; Criminal & record clearance; Disability & public benefits; Employment & civil rights; Money, tax & consumer law; Court access & self-help; Victim rights & safety |
| Medical, Dental, Vision | Primary & preventive care; Dental care; Vision care; Medication & pharmacy; Coverage & financial access; Pregnancy & reproductive care; Urgent, crisis & forensic care; Behavioral health; Specialty & chronic care; Home care & rehabilitation; Equipment & patient support |
| Mental Health | Wellness & connection; Coverage & care coordination; Crisis & urgent support; Counseling & therapy; Psychiatry & medication; Intensive & residential care; Peer & family support; Trauma & grief support; Assessment & developmental care; Service navigation; Recovery & co-occurring care |
| Reentry Support | Employment & training; Housing & shelter; Legal & record clearance; Documents & benefits; Recovery & health; Basic needs & transport; Mentoring & navigation |
| Seniors | Work & volunteering; Home repairs & safety; Home support & caregiving; Meals & nutrition; Transport & mobility; Housing & residential care; Benefits & money help; Legal help & protection; Health & wellness; Activities & connection; Service navigation |
| Transportation | School & student rides; Public & regional transit; Accessible rides; Medical travel; Senior & community rides; Fare, fuel & travel aid; Vehicles & driver access; Travel planning & advocacy |
| Utilities, Phone, Internet | Energy bill assistance; Water & sewer help; Phone service; Internet service; Devices & digital access; Weatherization & repairs; Billing & consumer help |
| Veterans | Benefits & claims; Health care; Mental health & recovery; Housing & homelessness; Employment & business; Education & training; Family & caregiver support; Financial & basic needs; Legal assistance; Burial & memorial help; Transport & access; Community & service navigation |

## Verification and limits

All 879 records passed structural checks, with complete Type coverage and explicit group decisions. Existing source/identity findings from the earlier content review remain in effect. Taxonomy preparation used local rule-assisted draft assignments followed by targeted semantic review and corrections; this is not a claim of perfect classification or a fresh verification of every provider. Human vetting should adjust labels and specific eligibility where needed.

Corrections addressed high-school seniors versus older adults, abuse versus stroke/bereavement survivors, prescription glasses versus medication, university-hosted children’s programs versus college-entry services, housing-cost help versus residential treatment, and referral/coverage routes versus direct clinical care. The local drafting script is an audit aid for this corpus, not an automatic production classifier.

Browser inspection confirmed four bold Information headings in the reader, editable text in the editor, 25 group choices, populated Category Types and zero human Curated flags. Combined filters returned the expected intersections:

- Food: **Groceries & pantries + Seniors** — 3 matching resources.
- Medical, Dental, Vision: **Dental care + Uninsured & underinsured** — 6 matching resources.
- Housing: **Rent & eviction prevention + Veterans & military families** — 5 matching resources.

The full unit suite passed: **259 tests**, one existing skip. Focused checks for the final validation changes also passed. The audit retained all **2,421 candidate decisions**; 36 research tables match the frozen snapshot and pre-review backup. The three six-category databases, five-model baseline and frozen production-research file retain their recorded hashes. SQLite integrity is OK. No research, curation, Claude or other paid worker was launched.

The source uncertainties identified in the earlier report still require follow-up, including current housing funding/waitlists, conflicting BREATHE hours and Sun Country website availability. Navigation labels do not resolve those uncertainties.

## Artifacts

- Corrected file: `data/st-george-curation-20260919/autoStGeorge.html`.
- Monitor and Save: `http://127.0.0.1:8769`.
- Navigation proposal, definitions, evidence, drafting/refinement scripts, backup, screenshots, rendered seed and verification: `data/st-george-curation-20260919/audit/navigation-20260920/`.
- Information before/after evidence: `data/st-george-curation-20260919/audit/information-format-20260920/`.
- The older downloaded file does not update itself; use the new Save download.

Final review fingerprint: `fc38acb44b43e653216154f2409c3aa068bc2e161c778a89dc81eb9e173eac1b`.

Navigation proposal SHA-256: `c0b7b875952edcb60b567e81b2569f7fa69f6d234332fe0638c338de94933466`.

The final review record is bound to this content under readiness contract version 2. It permits downloading the proposed workbench; it does not approve resources for publication.
