# Scout: discovery, resource improvement, and classification

Approved extension: [Astra-led research and playbook learning](scout-playbook-learning-design.md)
and its [implementation plan](scout-playbook-learning-plan.md) develop the unfinished
learning/adaptation work below. The [research foundation](scout-astra-foundation.md)
adds an opt-in protocol; the old autoMesaV2 execution remains historical evidence.
Learning experiments and active lesson adoption are later increments.

Status: design proposal, September 5, 2026. This document specifies future
behavior; it does not mean that behavior is implemented. The existing runtime
and completed Mesa artifacts remain the baseline. It supersedes the separate
enrichment stage as the intended normal workflow, while retaining that stage as
a migration path for earlier review files.

Michael approved the writing example and the six-increment implementation
sequence below. Other open design details remain subject to discussion. Roadmap
approval does not mark any increment implemented or complete.

Implementation update: increment 1's writing guidance and curation integration
are implemented on `v2.0`. Michael accepted the writing pilot, completing increment 1;
see [results](scout-increment-1-results.md). The remaining design below continues
to describe future work.

Increment 2 update: its safe existing-resource writing workflow is implemented
and software-tested. Michael authorized the historical Provo package for the
real four-AI pilot and accepted its writing and reconciliation decisions.
Provider questions and production package review remain open.
See [increment 2 status](scout-increment-2-results.md).

Increment 3 update: slice 3A is implemented and software-tested, and Michael
accepted its implementation changes. The six-resource
historical Provo pilot awaits office definition review before real classification
research. Group/migration review and location navigation remain planned. See the
[implementation status](scout-increment-3-results.md) and
[implementation and test plan](scout-increment-3-plan.md).

V2.0 development uses branch `v2.0` in `/Users/michaelbendio/resource-scout-v2`.
The existing checkout stays on `main` so the established Scout line remains
usable. See the [increment 1 implementation and test plan](scout-increment-1-plan.md).

## Product outcome

Scout helps an office build and maintain a useful resource collection. It can
find additional resources, improve existing Information, and infer appropriate
category Types and groups for existing resources. Each capability can run on its
own or as part of one project. Classification does not require repeating a
discovery run or rewriting human-curated Information.

Recurring maintenance is a first-class use case: discover additions and detect
changes or disappearance among known resources. Initial discovery, improvement
of an existing collection, and maintenance share the same evidence, identity,
review, and export mechanisms.

New resources should be useful on their first review. Stephanie's requested
Information and her subsequently endorsed additions belong in normal curation.
The Mesa enrichment run was a retrofit, not a required extra step for every
future office.

Use **groups** in conversation and new Scout interface copy. Preserve the
existing `forGroups` package field and identifiers for compatibility. A wording
change does not rename stored groups or change the office package schema.

## People using the resources

The purpose is to help service missionaries counsel people with real needs and
help those people take a practical next step. Missionaries are often retired
and may have limited confidence with computers. The people receiving printed
resources may need considerable support with reading, remembering instructions,
or navigating services, especially while under stress. Write respectfully for
adults with varied abilities and circumstances; do not assume digital access,
familiarity with service systems, or the ability to work out unstated steps.

The location application's responsibility is easy navigation through a large
collection: familiar, concise labels, clear distinctions between needs and
groups, and straightforward resource selection and printing. Scout supplies the
clear descriptions, useful classification, and actionable Information that make
that navigation effective. More discoveries or longer descriptions alone do
not establish success.

Scout's audience and writing instructions belong in versioned JSON/Markdown
guidance alongside the research playbooks. Apply them to initial curation,
existing-resource improvement, and maintenance proposals. Preserve detailed
research evidence for review without turning the recipient's handout into a
research report.

## Office workflow

1. Connect the office's latest human-vetted resource package. Show the location,
   package version, resource count, and taxonomy. An earlier Scout review file
   can instead be connected explicitly as a proposal source; it is not silently
   treated as the office's authoritative package.
2. Choose the work: **Find additional resources**, **Improve Information**,
   **Review classification**, or **Maintenance**. Maintenance combines new-lead
   discovery with rechecking existing resources. Allow combinations and a resource/category scope.
   An initial collection can use an office-approved empty package and taxonomy.
3. Show the scope and intended field changes. Classification alone changes no
   descriptions, contact details, or Information. Research can use the whole
   office collection to detect existing resources even when the work is scoped.
4. Research the selected resources and gaps. Preserve sources and uncertainty;
   resolve identities before counting or proposing additions.
5. Draft Information when requested, then infer categories, their Types, and
   groups from the same reconciled evidence. Validate the resource as a whole.
6. Complete required audits and reconciliation. Recompute affected assignments
   when the accepted research changes; assignments cannot silently remain based
   on an earlier Information revision.
7. Review group membership and usefulness for the office, with coverage clearly
   distinguished from the scope of this run. Reviewers inspect proposed changes
   before marking resources Curated and creating a package.
8. Reconcile accepted changes against the latest office package before export.
   Human review and the normal office merge remain the publication boundary.

The planned Provo upgrade combines **Improve Information** and **Review
classification** on the existing package. Its resources must comply with
Stephanie's revised Information structure and geographic description guidance,
as well as receive supported Types and groups. Classification-only remains an
available mode for later targeted work; it is not the full Provo acceptance
target. All proposals update the same existing resource IDs.

Finding additional resources can be a later or parallel workstream with separate
progress; it must not block completion of the selected existing-resource work.

### Provo input evidence and current-source gate

The inspected local `provo.html` copies in `Documents/TSO` and
`resource-assistant` are identical August 28 application files. Their embedded
seed contains 22 categories, seven groups, and **zero resources**. Startup loads
saved browser data or an imported resource package. The HTML's embedded taxonomy
is a starter preset, not evidence of the current office inventory or definitions.
The source-selection screen must distinguish an application shell, an embedded
review artifact, an exported package, and unsaved browser review state. Do not
interpret an empty HTML seed as an empty office or automatically begin discovery.

A locally available **historical sample**, `provo-resource-package-4.zip`, is
version 41, created August 12, 2026. Its SHA-256 is
`dc883d19eff7a30e78d33df580ea8408a50788eade33647c40ec6a23f0201a49`.
It contains 183 unique resource IDs, 20 categories, and seven defined groups:

- 172 resources have no group assignments; 167 have no Type assignments.
- 78 resources belong to multiple categories.
- Seniors contains 17 resources as a category but only three as a group.
- Veterans contains nine resources as a category but only one as a group.
- The package's Types differ from the HTML preset: Housing has none, Employment
  has only Temp Agencies, and Food uses Pantries rather than Pantry.

These are snapshot observations, not current Provo counts. Confirm the current
package with the office before fixing its proposed taxonomy, selecting the
pilot, or running classification. The design draft remains provisional on those
Provo-specific details until that input is identified and inspected.

This sample establishes why coverage must precede group-size judgments. It also
contains substantial human-curated Information, named program contacts, PDFs,
and multi-location/directory resources such as the Deseret Industries locations
and the Department of Workforce Services overview. Missing dedicated contact
fields or multiple listed programs must not trigger deletion or automatic
splitting. Preserve such entries and their assets, and present any proposed
individual-resource cleanup separately. New-candidate direct-service exclusions
must not be reused to discard accepted lists or navigation resources.

For the full Provo upgrade, reorganize useful existing Information into Programs
and Services, Eligibility Requirements, How to Best Connect, Access, and
Important Information to Know. Research missing details, preserve local
knowledge, and surface conflicting or dated claims for review. Combine repeated
service descriptions instead of appending a second account of the same service.
Retain the original text in provenance and keep PDFs attached. Propose concise
location/coverage additions to existing descriptions without erasing their
useful summaries. Review the resulting category Types and groups against this
updated evidence, not only against the older package text.

The intended result is visible in the ordinary Provo resource view, Admin
editor, and printed output after the approved package is merged. Updating the
empty HTML seed alone cannot accomplish that. Validate the actual loaded Provo
package and rendered views; if presentation changes are needed, implement them
in the application's modular source and normal release workflow, rather than
patching a generated `provo.html` in isolation.

Resources assigned only to a retiring population category need explicit service
classification before migration can complete. For example, the historical DWS
Veteran Services entry is Veterans-only even though its description discusses
employment help. That is a migration-review case, not authorization to assign a
new category or verify that service's current status without research.

## Information produced on the first pass

Render one Information block with these sections, in this proposed order:

| Section | Content |
| --- | --- |
| Programs and Services | Specific assistance and programs, combining the useful content formerly split between Services Provided and Programs and services. |
| Eligibility Requirements | Who qualifies, including relevant age, income, geographic, documentation, and referral requirements. |
| How to Best Connect | A concrete contact/application route, appointments, walk-ins, and practical steps for the person seeking help. |
| Access | Service area and relevant access arrangements; distinguish the provider's location from the area it serves. |
| Important Information to Know | Material limitations, unresolved details, costs, availability, and questions to check. Preserve the purpose of Verify before Referral under the revised heading. |

Do not invent missing facts or fill sections with generic boilerplate. Make
material uncertainty explicit in the relevant section. Do not repeat the same
program description or caution under several headings. How to Best Connect
should support the individual's next action where appropriate.

### Writing for counseling and printed handouts

Michael approved the [Express Employment Professionals writing example](scout-writing-example.md)
as the reference for Scout's style and level of detail. It demonstrates a concise
Description, separate contact details, and the five Information sections below
those fields. Its wording approval resolves the need for an agreed content
example; provider verification and evaluation of the actual printed layout
remain separate. Use its approach with each resource's own evidence, not its
provider-specific facts. The earlier fictional Maple example is not the approved
reference.

- Use everyday words, short sentences, and brief paragraphs or simple bullets.
  Explain an unavoidable unfamiliar term or acronym on first use. Avoid agency
  jargon, promotional language, and abstract descriptions of assistance.
- Let Description quickly answer what help is available and where it is
  available. Keep the most useful facts easy for a missionary to scan while
  counseling someone.
- Make the next step concrete: whom to contact, how to contact them, what to
  ask for, and any verified preparation needed. Prefer one clearly identified
  starting route when evidence supports that choice; include a useful supported
  alternative when access barriers make it relevant. Do not invent a preferred
  route, required document, phone number, or offline option.
- Keep Information to the point. Include eligibility, costs, service-area
  limits, appointments, documents, and availability details when they affect
  whether or how the person can get help. Remove repetition and incidental
  organizational background; brevity must not erase a consequential condition.
- Write directly and respectfully to the person seeking help. Avoid language
  that judges ability or circumstances, assumes computer confidence, or promises
  eligibility, an appointment, funding, or service availability without support.
- Make the printed resource stand on its own. Essential instructions must not
  depend on clicking a link, hovering, or having the missionary explain an
  omitted step. A web-only service must be identified honestly, with its usable
  application address in the printed contact information. Avoid repeating
  contact details already clearly printed elsewhere on the same resource.
- State material uncertainty briefly and specifically, including what needs
  checking. Keep research-process commentary and extensive source comparisons
  in review evidence rather than the recipient's Information.

Evaluate actual rendered handouts with missionaries: can they quickly identify
an appropriate resource, and can the recipient identify the help offered, the
relevant conditions, and the next action? Treat readability scores and word
counts as supporting signals only, not substitutes for those practical checks.
Use experience from each increment to refine the writing guidance.

Do not display a Scout Findings heading or append the old Information wholesale.
Keep the exact original Information and every research revision in Scout's
provenance. When Information improvement is selected, carry forward useful
human-vetted details and surface conflicts for review rather than silently
replacing trusted local knowledge with web results.

For new resources, include a concise, evidence-supported coverage/location cue
in Description so it is visible before the resource is opened. Label a physical
location as a location and a service area as a service area. Do not infer that
an office address limits eligibility to that city. For existing resources,
suggest a description edit only when that field is in scope; preserve the
reviewer's existing text and show the proposed addition.

## Categories, Types, and groups

| Dimension | Meaning | Illustrative example |
| --- | --- | --- |
| Category | The need directly addressed | Housing |
| Type | The service or intervention within that category | Rental assistance |
| Group | A population explicitly served or meaningfully accommodated | Veterans |

A resource can have multiple categories when it directly provides substantial
services in each, and multiple Types and groups when supported. Each Type
belongs to its category. Referrals, incidental benefits, and plausible client
overlap do not alone establish another category.

Group definitions distinguish **targets** from **accommodates** internally.
Dedicated eligibility or a service track supports targets; a concrete language,
accessibility, safety, cultural, or logistical arrangement supports accommodates.
These relationships share the simple groups interface, while reviewers can
inspect why each assignment was proposed.

Start from the connected office's approved definitions, aliases, categories,
Types, and groups. Do not impose Mesa's fixed catalog or resource-specific
exceptions on Provo. Matching a word is a research lead, not sufficient evidence
for assignment. Universal availability, a provider name, neighborhood, or a
general statement about adults does not justify population tags. A documented
Spanish-language service does not establish ethnicity. An empty groups list is
valid for a broadly available resource without a distinctive supported group.

Every proposed assignment records the resource/program it applies to, definition
version, supporting text/source, evidence date where available, and the reason.
Retain human-established assignments as the baseline; propose disputed removals
explicitly with evidence. Missing confirmation is not proof an assignment is
wrong. Terms absent from the office taxonomy become separate review proposals,
with a definition, examples, and overlap analysis. They are not created silently.

### Moving population categories into groups

Veterans and Seniors describe populations. A migration proposal maps their
resources to the actual needs served, the appropriate Types within those needs,
and supported Veterans/Seniors group assignments. Preserve legacy membership
as evidence and make the before/after mapping reviewable. Do not simply remove
the category and strand resources or copy its Types into an unrelated category.

Retiring a category, remapping its Types, and migrating its memberships are one
reviewed change set. Check every affected resource, including unselected ones,
and use the existing office taxonomy/deletion mechanisms after approval. An
incomplete classification pass cannot automatically retire a category.

## Group quality: membership before size

Evaluate groups after resource research, identity review, and assignment
reconciliation. The Mesa retrofit preserved earlier tags while expanding the
Information, so its small counts can reflect incomplete tagging as well as a
narrow group. Do not grow membership merely to make a group look worthwhile.

For each group, provide a review card containing:

- Definition and the practical selection question it answers.
- Current and proposed member counts, counting each resource ID once across
  all categories; additions/removals and their evidence remain inspectable.
- The resource list, applicable categories, and the specific program or
  accommodation supporting membership.
- Provider concentration and unresolved duplicate/program overlap. Two records
  from one provider are not automatically duplicates, but are not presented as
  two independent providers either.
- Classification coverage: reviewed, not reviewed, and unresolved resources.
  A partial review must not be labeled an office-wide membership audit.
- Definition ambiguity, overlap with other groups, and plausible missing
  assignments found in the research. Text mentions stay candidates until
  reviewed against the definition.
- A reasoned proposal: retain, clarify/rename, change prominence, merge, or
  retire. No recommendation is applied without review.

Judge usefulness, clarity, and supported distinct membership together. There
is no minimum-member rule, demographic quota, automatic merge, or automatic
deletion. Rank review attention using small size, stale/unreviewed membership,
definition ambiguity, and duplicate concentration; show those reasons instead
of a single opaque quality score. A one-resource group may still answer an
important access question. A large group may be too vague to help.

Renaming preserves the group's identity and aliases. Merging or retirement
requires reviewing each membership and its replacement/disposition. Preserve
research evidence and prior decisions. Hiding a group is not deleting it, and
absence from a new research result is not a deletion instruction.

### Membership and prominence are separate decisions

Maintain one office catalog of approved groups. Offer a small, office-selected
set prominently, plus **All groups** with names and counts. Small useful groups
remain searchable and available there. Office reviewers choose prominence;
counts alone never determine visibility or silently change that preference.

In a category view, highlight relevant groups without losing the All groups
route. Show a selected group even when it has zero matches in the current view,
with a clear explanation and a way to clear the selection. Do not silently
broaden results. A zero contextual count does not mean zero office membership.
Counts must use the same deduplication and query semantics as the result list.

Preserve current selection behavior: groups are ORed, Types within a category
are ORed, and those two sets are intersected. Label multi-selection as **Any of
these groups**. A resource tagged both Veterans and Seniors must not imply that
both characteristics are required; actual eligibility remains in Information.
An all-selected-groups search is not introduced by this design.

### Mesa evidence for the design

The inspected September 4 `autoMesa-enriched.html` contains 333 unique resource
IDs and 19 groups. Its group assignments match the accompanying local resource
package. The file's SHA-256 is
`65f26f690534927c7c359b0c082b25e950fe996eec0b64b79a632edad89f2831`.

| Group | Assigned resources | Review issue |
| --- | ---: | --- |
| Medically vulnerable | 3 | Specialty dental care, medical respite, and medical-equipment electricity support need a coherent definition. |
| Pet owners | 4 | All concern domestic-violence shelter access; two are Sojourner records. Accommodation can still be important. |
| Men | 5 | Check dedicated programs and meaningful accommodations, not generic statements that adults are served. |
| LGBTQ+ | 5 | Assess supported usefulness and membership rather than applying a size cutoff. |
| Native American | 6 | Review distinct programs and actual targeting/eligibility. |
| Women | 10 | Check current evidence and program-specific membership. |
| Spanish | 11 | Nineteen additional untagged records mention Spanish; mentions are leads for review, not nineteen proven omissions. |

For example, Southwest Human Development's enriched text describes bilingual
English/Spanish specialists, but its resource lacks the Spanish group. This is
a concrete consistency-review case, not a finding that every Spanish mention
should produce a tag. These observations do not authorize editing the Mesa
artifact or establish that any small group should be removed.

## Review, updates, and export integrity

Scout stores an immutable source snapshot and field-level proposals. Review
shows current and proposed values with reasons, separates additions from updates
to existing resources, and keeps proposals unmarked by default. Reviewers can
edit, accept, or decline changes; editing an accepted proposal clears Curated
until reviewed again. Internal job/audit states do not become extra mandatory
resource controls. Group-definition changes have their own review decision.

Preserve stable resource IDs, assets, history, and out-of-scope fields. A
classification-only proposal cannot erase phone, website, hours, address,
Description, Information, PDFs, or other curated data. Shared providers/intake
addresses require program identity review rather than automatic merging.

Before materializing an existing-resource update, compare the current office
record with the sealed base and proposal. Retain later changes to untouched
fields; conflicting changes to the same field require reconciliation. If the
latest package is unavailable, the review remains usable but export of existing
resource updates waits for reconnection. Do not manufacture a newer timestamp
on a stale whole-record copy to win the office merge.

Export approved changes through the standard package format and existing
merge/version/history rules. New resources and existing-resource updates retain
their respective identities. Approved taxonomy changes and affected memberships
travel together; block a partial export that would leave dangling Types/groups
or omit a required migration. Declining a proposal never deletes an existing
office resource. Real deletions use the office's explicit deletion workflow.
Failed or canceled saves retain review selections and visible resources. A
successful save records exactly what was packaged before hiding selected work.

Raw research, assignment hashes, group evidence, declined changes, and the exact
original Information stay in Scout. The missionary-facing artifact contains
useful content, not raw audit transcripts or implementation metadata. Human
reviewed exports remain proposals until merged in the office workflow.

## Durable execution and maintenance

Reuse immutable assignments, evidence capture, validated results, independent
audits, reconciliation, checkpoints, and artifact identities. Define durable
stages for scope, research, Information, classification, audit/reconciliation,
group review, and package preparation. Each stage records its input hashes and
policy version. Resuming skips matching completed work. Changed research or
taxonomy invalidates dependent proposals without deleting earlier evidence.

Keep a configurable researcher roster and the existing consumer-assignment
boundary. Codex performs research and reconciliation; Scout manages state and
validation. Neither the design nor a stored provider name implies direct API
access to a consumer subscription. Preserve operator-controlled pacing and
progress; changing models, research roles, or pacing is not part of this design.

Progress distinguishes primary research complete, audits pending, classification
reviewed, and ready for human review. Do not call the whole project complete
because all primary results exist. Required audit findings about eligibility,
service scope, or accommodations must reach classification before export.

Later maintenance starts from the current human-vetted package and the last
accepted evidence. It can revisit stale facts, coverage, or classification
without rediscovering the whole office. A broken website is an investigation
lead, not proof of closure. Learning from final human-vetted outcomes remains
proposed/inactive until its separate evidence and approval gates are satisfied.

## Maintenance runs

Start each run from the current office package and Scout's prior evidence, not
from the last unaccepted AI proposal. A run has two independently resumable
workstreams: search for additions and recheck known resources. Neither new-lead
research nor a failed website should erase an existing record. Keep retired
identities and declined proposals available for matching so that discovery does
not repeatedly propose the same closed resource or recreate an accepted record
under a slightly different name. A later reopening can generate a new review
proposal linked to that history.

Rechecking assesses the named program and service, not only whether its
organization or website still exists. Look for changes to operation, intake
routes, address, coverage, eligibility, cost, services, and accommodations. A
provider can remain open after a particular program ends; a moved or renamed
program can remain the same resource. Research resulting category, Type, and
group changes together with the Information changes.

### Operational evidence and proposed dispositions

| Finding | Scout response |
| --- | --- |
| Current evidence supports continued operation | Record the supporting observation and date; propose content changes only when needed. Do not treat this as a new human verification. |
| Website or contact route fails; service status unclear | Record the failure, search for replacement routes and current official information, and retain the resource while requesting follow-up. |
| Resource moved, renamed, or changed intake route | Propose an update linked to the existing identity; review possible duplicate or successor records. |
| Service is temporarily paused or unavailable | Propose an availability note and recheck date, keeping temporary status distinct from permanent closure. |
| Credible evidence states that the named program closed or ended | Present the exact evidence, date, affected program, and a proposed retirement for human review. |
| Office coverage or eligibility changed | Propose an update and explain its impact on this office's users; leaving the service area is distinct from organizational closure. |
| Evidence conflicts or cannot establish current operation | Show what is known, what remains uncertain, and the specific call or other check needed. |

An explicit provider/government closure notice or a recorded, attributable human
confirmation can support a retirement proposal. A dead URL, search omission,
old page, unanswered call, removed directory listing, or repeated inability to
verify does not alone prove closure. Repeated failures can raise review priority
and trigger a fresh independent check, but never automatically become confirmed
closure. A successor's existence does not itself justify merging or deleting
the original program. Closure/retirement proposals require an independent
evidence check and a human decision before an office deletion action.

Store checks as dated observations with sources and scope: last attempted check,
last evidence supporting operation, last human verification, uncertainty, and
the next proposed review date are different facts. Automated research must not
silently advance the office's `verifiedOn` human-verification field. Older local
knowledge remains visible when it conflicts with current public evidence.

### Review and cadence

The run summary reports proposed additions, changed resources, possible
retirements, unresolved checks, and resources with no change supported by this
check. These are evidence/result summaries, not new mandatory resource controls.
Show source dates and before/after values. Reviewers can accept additions and
updates independently while a possible closure awaits a phone call. A retirement
decision uses the normal office deletion/tombstone process; an unsuccessful
check never exports a deletion or silently hides the resource.

Let the office choose run scope and cadence. Prioritize stale evidence,
unresolved checks, volatile services, and time-sensitive intake information;
rotate remaining resources through a complete review cycle. Show how many known
resources were checked, which remain unchecked, and whether all categories were
searched for additions. A scoped or interrupted run must not imply that the
whole office collection is current. Scheduling and background execution are
implementation options; this design does not create a schedule or start a run.

Maintenance produces changes for review, not a replacement package generated
from scratch. Apply the same current-package reconciliation, protected-field,
audit, and export rules as other existing-resource work. Human outcomes feed the
next maintenance baseline and retain their provenance.

## Learning from successive packages

Importing a later human-vetted package is a natural feedback opportunity. Use
three linked records where available: the earlier office package, the Scout
proposal actually delivered for review, and the later office package. Without
the proposal link, Scout can observe a package change but cannot reliably
attribute it to correction or acceptance of its work. Without human-review
evidence, matching content is adoption evidence, not proof of vetting.

### 1. Establish package lineage at intake

Reuse `imports`, `imported_resources`, `categories`, and stored source/content
hashes. Add an office/collection identity and package-lineage record containing
source import ID, explicit predecessor, scope (full, selected subset, or
unknown), review authority, and available export/proposal provenance. Preserve
the complete input JSON, deletion/history metadata, and attachment hashes;
resource content alone is not the whole package history.

Select predecessors within the same office collection. Neither a filename, a
higher packageVersion, nor the globally latest import is sufficient. Older and
concurrent exports must not become a false linear history. If legacy metadata
cannot establish identity or scope, show the proposed relationship for
confirmation; comparisons can remain observations while authority is unknown.
Re-importing the same content or selecting another category creates no duplicate
learning events. Metadata-only and packaging-order differences are recorded
without being interpreted as human editorial corrections.

### 2. Compute changes deterministically

Add `package_comparison.py` to compare the sealed snapshots by stable resource
ID and field. Classify additions, edits, taxonomy/membership changes, explicit
deletion records, and unexplained absence. Compare group/category/Type sets
without interpreting ordering changes as new assignments; preserve exact
before/after prose, IDs, attachment references, and provenance. Resource IDs
changed by a merge/split need an explicit identity link or an unresolved match
proposal. Name similarity, a shared website, or a shared address is not enough
to establish that programs are the same.

Store immutable comparison events keyed by predecessor/current content,
resource identity, and field/change type. Retry safely and expose comparison
coverage. A selected export does not imply its missing resources were deleted.
Absence from even a full package does not explain a closure, rejection, or
duplicate merge without supporting history. No change implies neither fresh
verification nor reviewer endorsement.

### 3. Link observed changes to Scout's actual work

Add `proposal_outcomes.py` and a durable proposal/export manifest linking
research run, candidate IDs, generated resource ID, exact proposed fields,
assignment/policy/model versions, review artifact, and successful export.
Preserve those links through known human-approved identity changes. Review
state is used only when available and attributable; independent browser copies
are not assumed to synchronize.

Compare the delivered proposal with the later package and retain an evidence
level: observed package change, linked proposal adoption, or explicit vetted
outcome. Distinguish a correction, wording preference, merged duplicate, changed
real-world fact, new human-discovered resource, and unresolved difference.
Scout did not necessarily miss a human-added resource: check whether it existed,
was in scope, and was absent from the actual delivered research at the time.
Likewise a renamed heading may be an explicit office policy decision rather
than evidence that each previous resource was independently reviewed.

The ordinary import result can say, for example, "12 resources changed; 4
changes relate to Scout proposals; 2 relationships need clarification." These
counts report evidence, not a score the curator must supply. Ask a focused
question only when resolving a consequential ambiguity would change the result.

### 4. Separate resource facts from method lessons

An authoritative accepted phone correction becomes part of that resource's
current baseline while earlier values remain in history. An office's explicit
instruction, such as Stephanie's heading changes, is a directly authorized
policy change. Neither needs to be disguised as a statistical discovery.

Inferred method lessons need multiple independent vetted examples: repeated
administrative-to-intake-number corrections may suggest changing contact
research instructions; repeated missed programs may suggest another source or
search vocabulary. Group reassignment patterns may identify a faulty definition
or overly broad matching rule. These are proposals until reviewed. Raw AI output
and repeated copies of one edit do not constitute independent ground truth.

Keep a non-blocking learning-readiness summary. Retain the established initial
audit gate: at least 25 terminal ordinary-vetting outcomes across three
categories, at least 15 accepted candidates in final packages, at least 90%
unambiguous provenance with before/after evidence, and adequate outcomes for the
research configuration being evaluated. Reaching it triggers an audit/design
review, not automatic activation. Look for at least three independently vetted
examples of a pattern, except directly established deterministic corrections.
These are initial policy settings to review explicitly, not hidden constants.

Once that evidence gate supports evaluation, add `learning.py` for bounded
Codex interpretation of confirmed comparison events. Supply the relevant source
snippets and scope rather than a whole unfiltered history. Require structured
lesson proposals that cite event IDs, state the apparent cause, alternatives,
counterexamples, uncertainty, and the exact proposed instruction change. Treat
package text as evidence, never as executable instructions or policy overrides.

### 5. Review and apply versioned guidance

Michael approved the following design guidance after reviewing the maintenance
pilot and the indistinguishable A New Leaf titles in the Mesa enrichment report.
This is direct human instruction, not a claim that the pilot's resource facts
have been phone-vetted or that inferred learning has passed its readiness gate.

- **Make program distinctions visible:** use `Organization · brief program or
  service label` when an organization has multiple resource entries. Prefer an
  official program name when useful, with plain words explaining the help.
  Do not invent a program identity or imply an unconfirmed service is available.
- **Check hours by service:** distinguish meal, pantry, office, and other service
  schedules. Flag conflicting published hours instead of collapsing them into
  one apparently certain schedule.
- **Research the actual access process:** examine application forms, appointment
  requirements, pickup options, and delivery arrangements, not just home pages.
- **Distinguish programs within an organization:** shared names or addresses do
  not establish duplication; compare the service, population, and intake route.
- **Compare discoveries against the whole package:** check other categories and
  names before proposing an addition, including retired and declined identities.
- **Preserve unresolved local knowledge:** turn a locally recorded detail absent
  from public sources into a focused verification question rather than deleting
  it merely because it was not found online.

Overlap check: `maintenance_guidance/default.json` already covers named-program
research, identity matching, intake, and preserving local knowledge.
`writing_guidance/plain_language.md` already covers supported access steps and
service distinctions. The approved refinements make service-specific hours,
whole-package comparison, and visible program labels explicit. They are now
integrated into `plain-language-v2`, `maintenance-v2`, and
`existing-resource-improvement-v2`. Newly prepared jobs seal these revisions;
existing jobs retain their original guidance. Writing-only assignments record
title suggestions in reviewNotes; maintenance can propose a title change for
the existing stable ID through normal human review. Existing Mesa resources are
not renamed by this change; the mixed clothing/household entry still needs
program-boundary review.

Validation: 63 targeted writing, curation, improvement, rendering, and
maintenance tests passed. Added integration coverage checks new policy revisions
versus resumed assignments, whole-package identity context for discovery, and
review-gated title export preserving IDs and unrelated fields. These synthetic
checks establish workflow behavior, not the quality of future AI research.
The next reviewed research run should assess title clarity, service schedules,
access steps, and preservation questions before further guidance refinement.
Automatic lesson inference and adaptive run planning remain later increments,
subject to their evidence/readiness review.

The [Mesa program-title pilot](scout-program-title-pilot.md) now provides the
first focused review of these refinements: three title proposals, one conditional
on resolving an existing-record overlap, and Michael’s requested clothing,
furniture and household essentials title with service-by-service access findings.
This Codex-only review awaits Michael's decisions; no Mesa resource was changed.

Michael's next approved refinement is now in `plain-language-v3` and
`maintenance-v3`: briefly list multiple meaningful service types, and assess
usefulness from the patron's perspective (help, eligible recipient, and supported
access route). Determine the purpose and audience of source material rather
than adding keyword exclusions or a donation-specific rule. Evaluate partial
support service by service, preserving useful help and local knowledge. The
revised Mesa review shows the requested full title and preserves interview
clothing while flagging unestablished furniture/household-item access. This is
an approved policy refinement and a focused Codex application of it, not proof
of reliable autonomous judgment or a completed independent-audit cycle.

The subsequent curator boundary is implemented in `plain-language-v4` and
`maintenance-v4`: Scout chooses one short title for straightforward cases;
significant identity, service, access, or overlap questions go to the curator.
An unrelated question does not block a clear title. Existing review/export
protections remain in force. The [increment 5 evidence plan](scout-increment-5-evidence-plan.md)
sets out the next implementation: attributable review/package observations before
method inference, including title-only approvals that do not imply service vetting.

The bounded [increment 5A evidence ledger](scout-increment-5-evidence.md) is now
implemented through operator commands and routine project package connections.
It preserves packages and review history, distinguishes adoption from explicit
field verification, and leaves readiness unevaluated rather than counting
editorial choices as vetted resources. Michael approved the synthetic distinctions
and spot-checked the historical Mesa comparison. Package connections now capture
comparisons and available receipts automatically, without another full review.
Comparisons bold changed wording and identify removals. The next practical step
is a current office run; method inference and adaptive runs remain later work.

Store proposed lessons separately from operational facts. A lesson records its
supporting events, office/category scope, relevant research configuration,
proposed change, review decision, and policy version. Keep office-specific
practices local unless independent evidence supports broader applicability.
Do not pool incompatible model, research-policy, or curation versions.

Show a concise before/after instruction change with representative examples.
The reviewer may approve, revise, decline, or defer it. Approval creates a new
version of the appropriate research playbook, Information instructions, group
rules, or maintenance policy. Test it against held-out resources and known
counterexamples before activation; retain the prior version for rollback.
Every new assignment seals the versions and applicable approved guidance it
uses. Existing completed research and office packages are not rewritten by
activating a lesson. Proposed, declined, and retired lessons never silently
enter worker prompts.

### 6. Keep learned guidance in JSON and Markdown

Learnings are versioned data, not new category-specific Python conditions.
Build on the existing JSON guidance in
[`playbook_library`](../resource_research_agent/playbook_library/README.md) and
[`focused_research_strategy.json`](../resource_research_agent/focused_research_strategy.json).
The latter already defines four default research focuses. Extend this existing
loading model rather than introducing a competing set of active playbooks.

Use JSON for machine-readable lesson IDs, versions, status, scope, evidence
references, review decisions, evaluation results, and proposed configuration
changes. Use Markdown where longer research instructions, explanations,
examples, or counterexamples are easier to maintain as prose. A JSON record can
reference its Markdown file and hash; keep each instruction's canonical text in
one place rather than maintaining divergent copies in both formats.

Keep proposed and retired versions alongside their history. An explicit active
manifest selects approved, validated revisions of playbooks and applicable
lessons. A status change in the observations database alone cannot activate a
lesson. Publish a complete manifest revision atomically after validating its
references, hashes, scope, and compatible versions. Resolve office/category
scope explicitly; conflicting applicable instructions require resolution before
activation. Do not silently let the last loaded file win.

The database retains package snapshots, comparison events, research outcomes,
and provenance. Guidance files are the canonical reusable instructions; database
indexes of those files are derived. Each assignment stores the exact resolved
guidance, including referenced Markdown, version IDs, and content hashes, so its
behavior remains explainable after files change. A new guidance revision affects
new assignments; an existing run keeps its sealed configuration unless explicitly
replanned with new provenance. Rollback selects an earlier approved revision.

Code handles loading, schema validation, scope selection, execution, measurement,
and enforcing package integrity and review boundaries. Search vocabulary,
source channels, focus passes, learning thresholds, and adjustable stopping
criteria belong in validated configuration. Guidance cannot override provenance,
required review, or data-protection rules. Adding an ordinary research lesson
should require editing guidance and validating it, without changing Python.

### 7. Learn research methods from combined discoveries

Other AIs' findings and later human additions can expose missing programs,
source types, vocabulary, and search pathways. Preserve contributor and source
provenance, resolve duplicates at the program/service level, and validate the
underlying facts before treating the combined findings as a reference set.
Disagreement and unsupported claims remain visible. Repeated reports citing one
source are not independent corroboration.

The validated union is a useful comparison set, not proof of all available
resources. Separate resources Scout could reasonably have found at the time
from later openings, out-of-scope services, and information available only
through human contacts. A human addition may improve the package without
demonstrating a web-research failure.

Turn missed discoveries into proposed reusable search instructions. When only
results are available, describe a plausible recovery method as a hypothesis;
do not claim to know another researcher's actual search process. Keep known
provider names and answers in evaluation evidence, rather than inserting them
into the general playbook and calling subsequent retrieval improved discovery.

Evaluate revised playbooks on held-out categories or locations with comparable
time, tools, and source access. Seal reference answers until the research ends.
Measure recovery of validated discoveries, useful discoveries beyond the
reference set, factual errors, duplicates, and cost. Label retrospective tests
separately from blind evaluations. Activate a lesson only after its scoped
review and validation; importing another AI's output does not approve it.

### 8. Make further research passes depend on their value

Sol's playbooks and four-or-more focused passes provide the starting approach.
The four existing focus definitions are configurable defaults. Further passes
should address identifiable coverage gaps or promising source channels, with
their value assessed against time and research cost.

Record the focus and guidance version for each pass, its distinct supported
additions, useful corrections, unresolved gaps, and cost. Keep provisional
research yield separate from later human-vetted usefulness. Raw result counts,
duplicate programs, and reworded descriptions do not establish additional value.
Learn which focuses help particular categories and offices without pooling
incompatible configurations or treating one sparse run as a universal rule.

Store pass budgets, minimum coverage, and diminishing-return criteria in JSON.
The executor applies those settings and records why it continued or stopped.
It may propose another targeted pass, finish after sufficient coverage and low
recent yield, or report a budget stop with gaps still unresolved. Required
verification and review cannot be skipped because discovery yield has fallen.
Occasional broader comparison runs should test for blind spots; low yield from
repeating one method is not evidence that every useful method is exhausted.

### Learning capabilities within the main roadmap

These capabilities support the approved six-increment sequence below; they are
not a separate implementation order. Capture evidence from the early increments
and add interpretation and adaptation only when reviewed outcomes support them.

| Capability | Place in the main roadmap | Deliverable and boundary |
| --- | --- | --- |
| Recorded research and proposals | Begin in increment 1 and extend with each workflow | Preserve source snapshots, exact guidance, run goals, results, and delivered proposals; missing review evidence remains unknown |
| Package change history and linked feedback | Develop with existing-resource work in increment 2 and continue through increments 3 and 4 | Office-scoped, idempotent comparisons and attributable outcomes; no inferred vetting or automatic prompt changes |
| Reviewed lessons | Increment 5, after the learning-readiness review supports it | Evidence-backed, scoped playbook revisions with review, validation, version history, and rollback |
| Adaptive research | Increment 6, after approved guidance and accumulated experience support it | Category-specific run goals, sequence, and stopping with traceable decisions; no silent changes to accepted office resources |

The comparison engine and its read-only import summary support existing-resource
work; they are not the first product increment or a prerequisite for the writing
pilot. Start comparisons after successful snapshot storage; a failed comparison
is retryable and must not make a valid package unusable. Use unique event
keys/transactions for retries. Implement provenance capture alongside each
review/export workflow before expecting learning-quality outcomes from its runs.
Historical comparisons remain useful even when missing provenance prevents
reliable learning attribution.

Test reordered/reimported packages, selected exports, concurrent histories,
cross-office packages, timestamp-only edits, taxonomy changes, explicit
deletions, unexplained absence, identity merges/splits, and corrections made
after real-world facts changed. Verify that none turns weak evidence into a
confirmed outcome or active lesson.

## Implementation sequence

### Review after every increment

After implementing and verifying each agreed increment, remind Michael of the
grand plan and identify the proposed next increment. Report what is now usable,
what validation established, and what still needs experience from real use.
Discuss that experience with Michael before starting the next increment; do
not treat this roadmap as blanket authorization to implement every stage.
Record the discussion's conclusions and adjust the next increment accordingly.
If operational experience is not yet available, make that explicit rather than
presenting implementation checks as evidence of research usefulness.

### Approved six-increment sequence

This is the main roadmap, approved by Michael in the design discussion. Organize
each increment around usable output and a bounded pilot. Review its experience
before wider use and before proceeding to the next increment. Later steps may
be adjusted or divided into smaller slices through that discussion.

| Increment | What becomes usable | Experience to discuss |
| --- | --- | --- |
| 1. Better resource writing | Normal Scout curation produces Description and Information in the approved style, using saved guidance | Is it clear, concise, complete enough, and useful when printed? How much editing remains? |
| 2. Improve existing resources safely | Scout proposes Information and Description improvements to an existing package, preserving local knowledge, attachments, and later human edits | Does it improve the collection without losing useful details? Is reviewing changes manageable? |
| 3. Better classification | Scout proposes categories, Types, and groups from the researched information, with review of ambiguous or sparsely populated groups | Can missionaries find appropriate resources more easily? Are the distinctions useful? |
| 4. Maintain the collection | Scout finds additions and rechecks existing resources, proposing changes and possible retirements | What changes most often? How frequently should we check? How much review work results? |
| 5. Propose improvements to research methods | Scout uses attributable human changes and validated discoveries from other researchers to propose category-playbook revisions | Are the proposed lessons supported, useful, and appropriately scoped? |
| 6. Adapt the research runs | Scout uses approved guidance and accumulated experience to choose run goals, sequence, and stopping points for each category assignment | Does it find useful resources with less wasted research? What does it still miss? |

The full Provo improvement requires increments 2 and 3 together. Completing
writing changes alone does not fulfill the Provo objective. Michael authorized
the historical Provo package for development pilots; select and inspect the
current package before a production merge.

Increment 1 starts with a small, varied sample using the approved Express
Employment Professionals example as the writing reference. Include different
service shapes, such as a shelter, food pantry, and government program, to expose
different writing problems. Inspect the generated content and actual printed
output together before treating the guidance as ready for broad use. Apply the
approved Information structure during normal curation so new resources do not
need a separate enrichment job.

### Technical groundwork attached to the increments

The design can be reviewed independently of implementation. Michael selected
a separate v2.0 branch; it now has its own checkout. That decision does not
authorize combining the enrichment checkout's unfinished code or restarting runs.

- Before implementation, verify reusable capabilities on the v2.0 branch.
  Its starting baseline includes core enrichment
  (`a3cb004`); the separate enrichment checkout has later commits and unfinished
  changes with a Lexar bundle remote. Refresh that inventory before integrating
  changes and preserve completed Mesa data and artifacts. This is preparation,
  not a separate large redesign before the writing pilot.
- From increment 1, preserve the source package, exact guidance, run goals,
  results, delivered proposals, and available review outcomes. Reuse existing
  records and add missing links with the workflows that produce them. Missing
  evidence remains unknown. Evidence capture does not activate learning.
- Increment 2 adds the field-level proposals, package lineage/comparisons,
  current-package reconciliation, and safe export needed for existing-resource
  improvements. Preserve IDs, PDFs, history, local knowledge, and later edits.
  A review preview does not count as completion of the safe update workflow.
- Increment 3 adds office-supplied taxonomy definitions and evidence/version
  dependencies, extracting reusable rules from Mesa-specific code. Retain
  frozen Mesa decisions as historical evidence. Include consistency checks,
  audit-driven reclassification, reviewed population-category migrations, and
  group usefulness review. Attach required location-app navigation work to this
  increment explicitly. Michael's device review simplified it to matching groups
  shown directly, Type/group filtering, contextual counts, and Clear filters;
  prominence settings and All groups were removed.
- Increment 4 reuses the safe update workflow and tests moved, renamed, paused,
  closed, reopened, and inconclusive cases alongside discovery of additions.
- Increments 5 and 6 depend on the learning-readiness review and sufficient
  applicable evidence. Add reviewed lesson interpretation, validated guidance
  revisions, and then adaptive run planning. Keep the adjustable research
  strategy in JSON/Markdown and retain traceable decisions and rollback.

## Acceptance criteria

- Scout's descriptions and Information use respectful, plain, concise language
  suited to counseling and printed handouts. The rendered resource clearly
  identifies the help offered, material access conditions, and a supported next
  step without relying on interactive controls or unstated service knowledge.
  Pilot feedback from missionaries informs subsequent writing improvements.
- A newly discovered resource receives the five-section Information structure
  during normal curation; no second enrichment job is needed. Duplicate service
  sections and the displayed Scout Findings heading are absent, while original
  source content remains retrievable in provenance.
- Provo classification-only work proposes Types and groups on existing IDs,
  preserves every out-of-scope field, and does not inherit Mesa-specific IDs,
  catalogs, or decisions. No new taxonomy term is created automatically.
- The full Provo pilot also produces Stephanie's revised Information sections
  and evidence-supported geographic cues in descriptions. Useful local notes,
  contact details, list entries, and attachments survive. Duplicate service
  sections and the displayed Scout Findings heading are absent. The merged
  result is checked in the ordinary resource view, Admin editor, and print view,
  with assignments consistent with the updated Information.
- A changed eligibility/access finding marks dependent group assignments for
  review. A supported bilingual service can receive Spanish; an incidental
  mention or translation disclaimer alone cannot automatically receive it.
- An existing but unconfirmed tag is distinguishable from a disproven tag;
  neither research omission nor a small count silently removes it.
- A resource appearing in multiple categories counts once per group. Program
  and provider concentration are visible; potential duplicates are flagged
  without being merged solely to adjust counts.
- Every group with matches in the current category is directly accessible,
  regardless of size. A selected zero-match group remains visible; unselected
  zero-match groups are hidden. Counts reflect the current Type/group context.
- A partial classification run exposes its coverage and cannot retire groups
  or categories on the assumption that unreviewed resources are nonmembers.
- A Veterans/Seniors category migration preserves traceable service assignments
  for every affected resource and exports no orphaned taxonomy references.
- Restarting or importing a checkpoint resumes valid work; stale proposals are
  invalidated visibly. No output containing required pending audits is described
  as fully reviewed or ready to merge.
- A later human edit survives a nonconflicting update; a same-field conflict
  blocks materialization until resolved. Declining an update creates no deletion.
  Canceled or failed export loses no review state or selections.
- Reviewers can inspect and accept or decline the smallest Mesa groups using
  actual membership evidence and utility, with no automatic numerical cutoff.
- A maintenance run searches for additions and checks known resources, reporting
  separate coverage and resumable progress for each workstream. Accepted,
  retired, and previously declined identities are matched before proposing an
  apparent new resource.
- Maintenance reports retain the full introduction, questions, AI commentary,
  auditor findings, and Scout decisions on screen. Michael prefers making office
  changes with a printed reference rather than editing within the report. Print
  offers a short overview or one resource's working copy, with that resource's
  full audit details optional. Never default to a large all-resource audit printout.
- A broken URL with a replacement site produces an update proposal; a broken
  URL without corroborating closure evidence produces an unresolved check, not
  a deletion. Repeated failures do not change that evidence standard.
- A program closure is distinguished from provider closure, a temporary pause,
  a move, a rename, and a change of office coverage. Retirement requires reviewed
  evidence and the office's explicit deletion workflow.
- Automated rechecks preserve human `verifiedOn` values and historical local
  evidence. A reopened service can be proposed with its earlier identity and
  retirement history visible. No check or run silently rewrites the office
  package or claims unreviewed resources were checked.
- Repeated import and harmless ordering changes create no duplicate learning
  evidence. Partial exports, older packages, and cross-office packages cannot
  masquerade as a later authoritative full version.
- A before/after change is attributable to Scout only with the corresponding
  delivered proposal and review evidence. Missing resources are not counted as
  rejected proposals or closures without an explicit supported disposition.
- Each proposed method lesson cites independently vetted examples and stays
  inactive until its scoped instruction change is approved and validated.
  Assignment records identify the active guidance versions, and rollback is
  possible without changing existing resource data.
- An ordinary approved research lesson can be added through JSON/Markdown
  without changing Python. Invalid references, conflicting instructions, or
  unapproved revisions cannot enter an assignment; replay uses its sealed text.
- Research comparisons keep held-out answers hidden, distinguish supported
  unique findings from duplicates, and preserve human/AI provenance. Adaptive
  stopping records its configured reason and any unresolved coverage gaps.

## Evidence and related documents

- Stephanie's September 4 feedback on `autoMesa-enriched`: combine service
  sections, remove the displayed Scout Findings label, retain Access and its
  coverage information, rename Verify before Referral, and surface geographic
  information in Description. Section order and the interface behavior above
  are design proposals, not quotations from that email.
- September 5 design discussion: support Provo existing-resource Types/groups,
  separate populations from service categories, and assess small groups only
  after membership quality, clarity, and practical value are understood. Include
  recurring discovery of additions and evidence-based detection of services
  that have gone away.
- [Current enrichment implementation contract](scout-enrichment.md).
- [Current curation and review workflow](scout-curation.md).
- [Research learning and maintenance design](codex-research-learning-design.md).
- [Group inference implementation](../resource_research_agent/taxonomy_groups.py)
  and [Type design implementation](../resource_research_agent/taxonomy_type_design.py).

## Current operational priority (September 6)

Michael prioritizes the v2.0 autoMesa run ahead of Provo expansion. The [open-question handoff](scout-open-question-handoff.md) carries specific unresolved questions to office curators, while Michael supplies design guidance. Every generated resource still requires full curation.
