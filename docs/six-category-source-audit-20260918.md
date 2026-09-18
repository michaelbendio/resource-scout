# Six-category source audit — September 18, 2026

Reviewed September 18, 2026. These are purposively selected consequential cases,
not a random sample, a complete curation, or an estimate of precision/recall.
Lead numbers refer to the indicated condition database. CG = Codex+Grok;
CC = Codex+Claude; ClG = Claude+Grok. Primary/challenger provenance matters:
recovering a different primary's miss is not proof of a uniquely capable model.

| Category / case | Experiment evidence | Source check and interpretation |
|---|---|---|
| Addiction: Family Healthcare MAT | CG challenger 57; ClG primary 27; CC challenger 77's maternal-guide note calls Family Healthcare a former name of FourPoints | [Family Healthcare primary care](https://www.familyhc.org/primary-care) advertises MAT. [FourPoints](https://fourpointshealth.org/) is a separately active clinic network with a different St. George address. The rebrand claim is unsupported; keep distinct identities. A useful Grok addition to its own primary. |
| Addiction: At The Crossroads | CG primary 45; CC primary 44; ClG challenger 86 | [Provider contact page](https://www.atthecrossroads.com/contact-us/) expressly excludes detox and substance-use-disorder treatment. Transitional support may belong elsewhere, but do not promote this as addiction treatment. All three conditions need the same negative-evidence check. |
| Clothing/Household: BREATHE Care | CG primary 167; CC primary 194; ClG challenger 301 | [Provider](https://nowbreathecare.org/) advertises food and essential household supplies with a Santa Clara intake. Grok recovered a concrete local access route despite Claude's larger primary list. |
| Clothing/Household: one-off events | CC challenger 247 Molina fair and 250 Kindness in Motion | The candidates themselves acknowledge only a past event or a news story, with no verified standing intake or recurrence. Discovery follow-up leads, not established ongoing access routes. Not a verified closure. |
| Clothing/Household: Momivate closet | CG challenger 208; ClG challenger 302 | [Program page](https://momivate.org/revolving-closets/) retrieved inconsistently; St. George availability not established by this audit. Leave unverified, not rejected for fetch failure. |
| Disability: blind library | CC challenger 339; ClG primary 361 | [Utah State Library blind services](https://blindlibrary.utah.gov/) confirms accessible reading service and application route. A useful statewide program accessible remotely. Claude primary also found it; it is missing from the Codex+Grok named-program list. |
| Disability: UCAT / ABLE | CC challenger 338 / 342; CG primary 215 / 275; ClG primary 338 / 319 | These Claude additions repair that condition's primary misses; they are already present in other primaries. They do not establish uniquely Claude-only capability. |
| Domestic Violence: survivor phone benefit | CC challenger 467 | [USAC Safe Connections Act](https://www.usac.org/lifeline/safe-connections-act/) confirms a temporary Lifeline pathway for qualifying survivors, with documentation and eligibility conditions. Useful complement to shelter/hotline lists; not universally free service. Neither the completed CG nor ClG Domestic Violence list names this benefit. |
| Domestic Violence: forensic access sites | CG primary 311 plus challengers 373, 374, 382–384 | [St. George Police victim services](https://sgcityutah.gov/departments/police_department/victim_services.php) explicitly lists local hospitals, Family Healthcare, UTU Booth Wellness, Doctors Volunteer Clinic and [Southwest Forensic Nursing](https://www.swforensichealthcare.org/), with a nurse routing number. These are supported access locations, not five proven independent new programs. Preserve access details while reviewing identity grouping. Do not reject official corroboration merely because a clinic's own page omits forensic care. |
| Education: Boys & Girls Clubs costs | CG challenger 472; CC challenger 553 | [Paradise Canyon program](https://bgcutah.org/paradisecanyon/) states annual and weekly fees plus financial assistance. CC's blanket free-membership/no-cost description overstates the evidence. CG identifies the fees and uncertainty. Program is useful after correction; do not confuse assistance with universal free access. |

Other leads for final cross-condition checking: Angel Watch (CG primary 82,
CC challenger 164, ClG primary 188); GED testing (CG primary 389, CC challenger
548); Utah Promise (CG challenger 466, CC primary 496); HB144 (CG challenger
473); Immigrant Welcome Center (CG challenger 457). Angel Watch, Utah Promise and HB144 are checked below; GED and the Immigrant
Welcome Center remain unverified in this audit. Milk donation depots must not be conflated
with recipient access to donor milk.

Additional source checks:

- [Angel Watch](https://intermountainhealthcare.org/services/womens-health/angel-watch)
  confirms statewide Utah coverage and free perinatal palliative support, with
  email contact. All three conditions cover it, but CC needs its challenger.
- [TURN's trust page](https://turncommunityservices.org/project/utah-pooled-trust/)
  says Utah citizens with disabilities may participate and describes both self-
  and third-party funding. CC 369's suggested intellectual/developmental-only
  restriction is not supported by this provider page. The page cautions about
  trust limitations and suggests considering ABLE; verify new enrollment before
  promising it. ClG primary 421 also finds this program; CG misses this distinct
  benefits-planning pathway despite finding TURN's direct services.
- [AbilityIS pooled trust](https://www.abilityis.org/pooled-trust) does state an
  intellectual/developmental disability condition and both funding methods. CC
  370 discovers a distinct program, but its claimed inability to verify those
  details adds unnecessary curator work. Do not transfer one trust's eligibility
  requirements to another. These are provider descriptions, not a legal opinion
  or verification of all current benefits rules.
- [Utah Tech state scholarships](https://scholarships.utahtech.edu/state-of-utah-scholarships/)
  explicitly links the HB144 affidavit pathway (CG challenger 473) and identifies
  Trailblazer Promise as its branding for Utah Promise. CG 466's statewide grant
  may extend campus coverage but is not automatically an independent new benefit.
  ClG primary 678 independently finds the HB144 pathway; ClG primary 616 also
  covers the accessible library program in Education. Those are useful primary
  findings, not uniquely Grok- or Claude-challenger capabilities.
- [Family Support Center](https://www.fsc4kids.org/) returned HTTP 403 in this
  review. This is a retrieval limitation, not evidence of closure or invalidity.
- CC Education challenger 547 presents the Center for Inclusion and Belonging as
  a current, distinct tutoring route, based partly on a 2022 university article.
  [Utah Tech's own HB261 notice](https://utahtech.edu/hb261/) says the center was
  dissolved and staff reassigned. The [2026–27 Student Resource Center catalog
  entry](https://catalog.utahtech.edu/campusresources/womensresourcecenter/)
  supplies a current successor access route, already represented in the primary.
  This is documented reorganization, not a closure inferred from a broken URL.
  Do not count the obsolete center as an additional accepted current resource.

Implications: preserve provider/program/access-point hierarchy;
verify explicit exclusions, cost and eligibility before publication; count marginal
service identities only after curation; target pathway gaps rather than treating
every uncertainty string as a reason for another broad research pass. All observed
candidates contain uncertainty text, so that boolean trigger would select everything.


## Additional Clothing/Household and access-pathway checks

- **Christmas Box resource room:** CC challenger 234 and ClG primary 274
  identify a caseworker-mediated St. George clothing/household route absent
  from CG. The [current staff directory](https://thechristmasbox.org/staff-directory/)
  names a St. George coordinator. The organization's [2023–24 activity report](https://thechristmasbox.org/wp-content/uploads/2024/12/FY2023_2024-DASHBOARD.pdf)
  documents St. George DCFS use. This supports a real local pathway, while current
  hours, stock and referral rules still require confirmation. ClG 286 is also
  the associated DCFS access office, not automatically a second supply program.
  CC primary 218 mentions Christmas Box as a partner of a different resource
  center but has no verified local access; the challenger supplies that distinct
  St. George route rather than discovering the organization's name from nothing.
- **Hurricane pantry:** CG challenger 204 uses the older AAA/Five County listing;
  CC challenger 236 points to Utah Food Bank. The provider's [2024 opening notice](https://www.utahfoodbank.org/utah-food-bank-hurricane-valley-food-pantry-is-now-complete/)
  expressly says the new pantry replaces the former one and partners with Five
  County. Treat provider/address versions as an identity-resolution task. The
  notice alone does not establish current diaper or hygiene-kit stock.
- **American Legion assistance:** ClG challenger 305 finds Temporary Financial
  Assistance, a narrow family-eligibility route. The [Utah program page](https://utlegion.org/programs/temporary-financial-assistance/)
  confirms local-post initiation and eligibility; the [national 2025 booklet](https://www.legion.org/getmedia/46d6f74a-c4dc-4c5f-8ab0-cf62bda11619/305acy0325-whole-child-booklet.pdf)
  includes clothing among basic needs. A useful candidate after confirming
  current limits and the local application contact; not a public clothing closet.
- **Grok's eight CG clothing additions are not eight established new services.**
  They include a restricted foster-family closet, conditional tribal vouchers,
  a storehouse route related to existing DI help, the old pantry listing,
  plan-dependent vocational support, patient-only hospital supplies,
  Cedar City Transitional Services with unconfirmed St. George access, and
  Momivate's unverified local closet. Several limitations are candidly stated
  by the worker itself. Keep relevant follow-up evidence without treating the
  whole tail as accepted marginal yield.
- **Claude's seventeen CC clothing additions also require triage.** They include
  the useful Christmas Box route, indirect supply/referral organizations,
  school clothing funding related to an existing counselor route, a past fair,
  and an event-specific donation effort. Encircle's general clothing connection
  is not verification of a St. George clothing service. Its uncertainty note
  correctly acknowledges that distinction. Raw count alone favors neither model.
- **ClG's seasonal additions 306–307** explicitly describe a December exchange
  and a tribal toy/clothing drive, rather than year-round public closets. They
  need current season and access confirmation. Their seasonal nature is a
  curation condition, not evidence that the workers invented them.
- **Free Legal Answers:** CC challenger 466 and ClG challenger 563 identify
  a pathway absent from the CG Domestic Violence list. The [service itself](https://utah.freelegalanswers.org/)
  confirms qualifying civil questions answered online, excludes court
  representation and cannot promise an answer before a deadline. A practical
  advice route with a consequential limitation; both challenger providers can
  recover it depending on the primary exclusion set.

## Education geographic contradiction

The completed ClG challenger adds Suazo Business Center (697), already present in
CG primary 422 and CC primary 510. The [provider's site](https://suazocenter.org/)
confirms business education, bilingual advising, a St. George location and virtual
Utah access. This is another concrete omission recovered after a much larger
Claude primary. DI's training/education pathway appears in all three challengers
(CG 455, CC 560, ClG 684); the [provider's program page](https://www.deseretindustries.org/work-at-deseret-industries)
confirms training, development counseling and help accessing education, with
application through the store. Neither is a uniquely single-model discovery.

ClG primary **642** assigns a grant-funded afterschool program at Vernon and Kate
Smith elementary schools to the St. George area. It invents Enterprise/Hurricane
associations and calls the source's 850 phone code an apparent typo. The actual
[district notice](https://www.wcsdschools.com/2025/1/21st-century-rural-expansion-grant)
and [district homepage](https://www.wcsdschools.com/) explicitly give **Chipley,
Florida**, whereas the [Utah district](https://www.washk12.org/) gives St. George.
This is a wrong-entity geographic attribution, not merely missing contact detail
or an unverified local opening. The cited source does not support this Utah lead.
Preserve it in the evidence, but exclude that claimed local program at curation
unless separate, valid Utah evidence is supplied. Do not reject legitimate remote
or national providers solely because their address or phone is out of state.

The production prompt now explicitly requires resolving conflicting geography
instead of explaining it away. This is preventive guidance, not proof that a
model will always comply. The larger Claude primary list still needs geographic
and identity review, as do the other conditions.

The audit preserves uncertainty instead of assigning unsupported rejection or
acceptance labels. Source access occurred during this review; a current page
can still require confirmation of capacity or individual eligibility. No provider
was contacted and no experiment database was edited to impose these judgments.
