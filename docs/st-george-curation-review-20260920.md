# St. George final curation review — September 20, 2026

The reviewed workbench is ready for human vetting: **879 consolidated resource records across all 21 categories**. The final review made consequential corrections before release. It did not approve resources on behalf of a human or verify them by telephone. Every human **Curated** flag remains unset.

Review was performed in Michael's requested Extra High Codex session. No research or curation worker was launched, no Claude call was made, and no completed category was rerun.

## What changed

The starting result contained 880 distinct resource IDs. Two duplicate pairs were consolidated and one existing omitted candidate was restored, leaving 879. Fourteen final resource records changed or were added. Fifteen recorded review actions, including one omission-reason clarification, required versioned revisions to 18 category results because shared resources occur in several results.

| Finding | Correction and evidence |
|---|---|
| A Utah library card incorporated Minnesota computer-access rules. | Removed `washcolib.org` and the unsupported guest/laptop instructions. Replaced them with the actual [St. George branch](https://library.washco.utah.gov/st-george/), [Utah fee schedule](https://library.washco.utah.gov/services-fees/), and [MakerSpace information](https://library.washco.utah.gov/st-george/makerspace/). Local contact details alone had concealed the wrong source. |
| Liahona's card overstated its substance-use treatment scope. | Removed day/PHP/IOP claims. Its [official site](https://liahonaacademy.com/) explicitly distinguishes its mental-health residential license from substance-abuse treatment licensing and excludes detox. The card now states that distinction and retains appropriately qualified co-occurring support. |
| SBHC's general outpatient title sounded restricted to pregnant and parenting women. | Restored a general outpatient substance-use title while retaining pregnancy-related priority information. The [provider describes both youth/adult services and that priority](https://www.sbhc.us/services/substance-use-disorders). |
| Three shared clinic cards lost forensic-exam routing during later mental-health consolidation. | Restored the nurse-routing number for Booth Wellness, Doctors' Volunteer Clinic, and Family Healthcare. The [city's victim-services page](https://sgcityutah.gov/departments/police_department/victim_services.php) lists the sites and route. Routine student or safety-net eligibility is explicitly separated from forensic access. |
| Hospital financial assistance was omitted on the premise that it belonged inside clinical cards, but its actionable contact was absent. | Incorporated the [financial counselor/application route](https://intermountainhealthcare.org/for-patients/financial-assistance/utah-idaho-nevada) in NICU and maternity records. Candidate 673 is now linked as merged into those cards. |
| RISE had two IDs for the same St. George branch and overlapping services. | Kept the earlier ID, all category/candidate links, and both [local adult/family programs](https://riseservicesincut.org/location/st-george/) and [youth after-school/summer access](https://riseservicesincut.org/after-school-summer-programs/). |
| UALD had two IDs covering the same complaint intake. | Kept one broad employment/fair-housing record and preserved the distinct filing routes and deadlines from [employment](https://laborcommission.utah.gov/divisions/utah-antidiscrimination-and-labor-uald/employment-discrimination/) and [housing](https://laborcommission.utah.gov/divisions/utah-antidiscrimination-and-labor-uald/fair-housing/) sources. |
| The shared VA clinic summary lost a consequential homelessness contact. | Restored the [VA homelessness call-center route](https://www.va.gov/homeless/nationalcallcenter.asp) alongside ordinary clinic access. |
| SGHA's final veteran-oriented summary dropped several earlier pathways. | Restored rental-assistance inquiry, VAWA procedure questions, and [Utah-approved homeless-status verification](https://vitalrecords.utah.gov/homeless-service-providers) for document fee-waiver applications. Rental funding and current openings remain explicitly unconfirmed; the authority's pages failed to fetch during this review. |
| A senior-focused rewrite named other produce programs but dropped their useful access routes. | Restored Double Up grocery/market and Family Healthcare Produce Rx inquiry routes alongside senior coupons, using [Utah DHHS's current program page](https://dhhs.utah.gov/communityfood/). |
| A local housing counselor was excluded by a standard not applied consistently to other retained counselors. | Restored Sun Country Home Solutions from existing candidate 2244. [HUD's Utah agency list](https://apps.hud.gov/offices/hsg/sfh/hcc/hcs_print.cfm?searchstate=UT&webListAction=search) and [CFPB's local lookup](https://www.consumerfinance.gov/find-a-housing-counselor/?zipcode=84780) corroborate the local route. The card promises counseling, not rental payments or placement. |
| SUN Bucks' omission reason treated conflicting source versions as a settled current-year fact. | Kept the lead unresolved and corrected the reason. The [live DWS page](https://jobs.utah.gov/customereducation/services/sebt/) now refers to summer 2027; earlier indexed text referred to 2026. Neither establishes a current application route for this workbench. |

All corrections preserve original category results in SQLite revision history. Original worker output and sealed assignments were not overwritten. Shared corrected records were reconciled across their category results so a later stored version cannot silently reintroduce the reviewed error. Candidate links remain valid after both ID merges.

## Scope and limits of this review

The review combined whole-corpus structural checks with an identity/category inventory, omission screening, comparison of shared-resource versions, and targeted primary-source verification of consequential or conflicting claims. It covered geography, local versus statewide/remote access, identity/program boundaries, eligibility, contact routes, and Stephanie's four information needs.

This was **not a fresh verification of every claim on every one of the 879 cards**. The original curation evidence remains part of the basis for unchanged records. Source checks were selected for risk rather than randomly sampled, so the findings cannot be used to estimate an overall error rate or compare worker effort levels statistically.

The final checks confirm all records have content for eligibility, how to connect, access, and important information. Some earlier cards use abbreviated headings such as “How to connect” and “Important”; these are not missing information. Missing-phone comparison produced 17 flags. Several were changes to a current central/local contact rather than a lost pathway; numbers were not restored automatically. Genuine losses were investigated and corrected as described above.

The previously identified Maryland harm-reduction substitution remains removed, with the Utah Hand in Hand route retained. Wrong-state school/library leads rejected during curation remain excluded. Distinct service programs and intake routes were not collapsed merely because they share a provider or telephone number.

## Remaining human-vetting priorities

- **Current access:** confirm beds, waitlists, funding, insurance participation, service radius, and appointments. A current website is not a promise of availability.
- **SGHA:** confirm rental-assistance operation and limits, current housing waits, and whether staff will complete a homeless-status verification for the particular applicant. Earlier saved official-page evidence was preserved; unsuccessful live fetches are not proof of closure.
- **BREATHE CARE:** its own pages publish conflicting hours. The card exposes that conflict and asks people to confirm pickup time.
- **Sun Country:** verify appointment arrangements and fees using the HUD/CFPB-listed phone; its own website did not load during review.
- **Unresolved leads:** the St. George Immigrant Welcome Center, local Latinos in Action enrollment, Project Lifesaver, and local Arc/autism-group identities remain useful follow-up leads where current local intake was not established. They are preserved in candidate evidence, not silently classified as closed. SUN Bucks needs the same care with source dates.
- **Category policy:** the current direct-service rule sometimes excludes useful barrier-removal services from related categories. For example, transportation may be relevant to treatment while retained primarily under Transportation. A future policy review should consider explicit related-access links; this review did not broaden every category or invent For groups.

## Final counts

All **2,421 candidate decisions** remain accounted for: 924 “curated,” 1,135 “merged,” and 362 “omitted.” Those are AI disposition labels, not human acceptance counts. The two changed disposition outcomes are candidate 673, omitted → merged, and candidate 2244, omitted → curated.

The final workbench counts below include resources assigned to the category by other categories' workers. Therefore they can exceed that category's own result-row count. Resources can appear in multiple categories; **do not sum this column as unique resources**. A resource record can represent a service program rather than a whole organization.

| Category | Candidate decisions | Final workbench records |
|---|---:|---:|
| Addiction | 196 | 78 |
| Children/Pregnancy | 264 | 164 |
| Clothing/Household | 147 | 42 |
| Disability | 314 | 176 |
| Domestic Violence | 238 | 92 |
| Education | 255 | 166 |
| Employment | 52 | 78 |
| Financial Assistance | 67 | 77 |
| Food | 41 | 35 |
| Homeless Services | 56 | 40 |
| Housing | 85 | 89 |
| ID Recovery | 59 | 46 |
| Immigration | 55 | 46 |
| Legal | 87 | 93 |
| Medical, Dental, Vision | 66 | 91 |
| Mental Health | 79 | 98 |
| Reentry Support | 72 | 62 |
| Seniors | 78 | 62 |
| Transportation | 63 | 48 |
| Utilities, Phone, Internet | 67 | 38 |
| Veterans | 80 | 78 |

## Verification and delivery

- All 21 completed result schemas and exact candidate/resource link checks pass. Result and sealed-assignment hashes validate; there are 879 unique final IDs and no remaining Minnesota library URL in resource content.
- All four historical source database hashes and the frozen completed-research snapshot hash match the earlier preservation checkpoint. All 36 non-curation tables match both that frozen snapshot and the pre-review working-database backup. SQLite `quick_check` returns `ok`.
- The generated HTML loads in an isolated headless Chrome profile with 21 categories and 879 resources, without application JavaScript exceptions. The category grid, corrected library search/detail view, source links, and resource editor were inspected. The editor's Curated control is unset, and the browser reports zero human-curated resources.
- No application implementation changed in this review. Verification exercised the existing revision, validation, generation, and browser paths against the actual data.

Reviewed result fingerprint:

`e5e014245310e23001079d365f21233a82b55427321a37f6a09131b7bbe67568`

The review-completion record binds this report to that exact fingerprint. The monitor's existing **Save autoStGeorge.html** action at **http://127.0.0.1:8769** supplies the reviewed workbench after that record is saved. Subsequent substantive result changes require review again. Saving this HTML begins human vetting; it is not office publication or approval of the whole package.

Local deliverable: `data/st-george-curation-20260919/autoStGeorge.html`.

Local audit evidence: `data/st-george-curation-20260919/audit/final-review-20260920/` contains before/after resources, original results, the pre-review SQLite backup, correction script, proposed results, findings, revision hashes, preservation checks, and rendered browser screenshots. A portable evidence summary is in [the review evidence JSON](st-george-curation-review-evidence-20260920.json).

## What this teaches us about Scout

The separate final review has earned its place. The main recurring problem was that a later category could replace the shared resource's factual text while retaining earlier category and candidate links. Structural validity alone cannot detect that loss. The next implementation priority should be a reviewable comparison of old and proposed shared-resource facts, with an explicit disposition for each removed intake route or restriction. Blind text concatenation would preserve contradictions as well as useful facts.

The wrong-state library source also shows why matching a provider name and local contact fields is insufficient: the source page's actual jurisdiction must match the claim. These are concrete findings to use when designing future checks. This review does not establish that uniformly higher worker effort, a different model, or another broad research pass would have prevented them.
