# Workbench readiness after curation

A generated HTML file is a draft until the requested Codex review covers both
resource content and the tools people need to find and vet those resources.
Read this alongside `AGENTS.md`, `SCOUT_STATUS.md`, and `scout-orchestration.md`.
No new research or paid AI call is implied by this stage.

## Required delivery checks

1. **Information:** every resource has these four standalone bold Markdown
   headings, in order, each followed by relevant text:
   `Eligibility Requirements`, `How to Best Connect`, `Access`, and
   `Important Information to Know`. Put supported hours, appointments, access
   limits and availability in Access. State unknowns instead of inventing them.
   Preserve source links and limitations. Check the rendered reader and editor;
   searching for four words is insufficient.
2. **Types:** every Category has defined service Types. Every resource has at least
   one supported Type in each of its Categories. Keep labels useful and reasonably
   short; avoid generic catchalls, duplicate synonyms and provider-name Types.
   Inspect counts, empty filters, overbroad matches and important missing pathways.
3. **For groups:** review the actual corpus and the office's existing taxonomy.
   When authorized to design a new workbench taxonomy, propose groups supported by
   the resources. Record an evidence excerpt for every assignment. For each
   ungrouped resource, explicitly record why a population label is not established.
   If no groups are justified anywhere, document that catalog-level conclusion too.
   Blank starting groups alone do not satisfy this review.
   Review every resource against every defined group, including retained labels
   and plausible missing labels. Keep a per-resource decision ledger with evidence
   and explicit no-group reasons. A keyword scan, complete JSON coverage, or the
   sensory-disability parent check does not establish semantic completeness.
   Check consistent treatment of similar programs: adult-only parenting education
   versus child services, paid care jobs versus family-carer support, school
   seniors versus older adults, and documented language access versus ethnicity.
   Resolve material source questions before delivery, or explicitly omit an
   unsupported assignment and record why. An announced service without a confirmed
   offering must not be presented as currently accessible.
4. **Review priorities:** as part of this requested AI review, assess every
   resource in each of its Categories. Propose Start here, Important specialized
   help, or Additional options, with a short reason and a literal saved-resource
   evidence excerpt. Add a focused question when a consequential access issue needs
   human resolution. Consider local intake, practical accessibility, eligibility,
   distinct pathways, and urgency. Rare but consequential services can belong in
   Start here. Do not rank by keyword, provider fame, alphabetical order, group
   count, or a fixed quota; do not claim provider superiority or verification.
   The same resource can have different priority in different Categories. Preserve
   every resource, including lower-priority alternatives. Scout validates this
   judgment's coverage and currency; Scout itself does not judge marginal usefulness
   or automatically stop research. Keep the AI proposal separate from human
   priority overrides, resource facts, For groups, and Curated flags.
5. **Usability:** inspect Category Types, Browse by Group, search, and combined
   Type/For filters. Multiple Types use OR; multiple groups default to AND, with an explicit
   Match any option for OR. The two dimensions combine with AND. Check meaningful matches and empty combinations.
   Inspect the Information reader and editor and confirm zero new human Curated
   flags. Preserve browser-local work if Michael has already edited the older file.
   Also inspect priority sections, short reasons/questions, counts with active
   filters, personal overrides and reload, and shared Curated progress across
   Categories. Offer Review priorities and All resources A–Z in every Category. Both views
   must show the same matching resources and retain Type/For filters; the alphabetical
   view must be one ungrouped list. Search must still find Additional options. A priority change must
   not approve a resource. New resource/category entries must show Needs priority
   review instead of inheriting an invented AI judgment. Priority metadata must
   not enter ordinary curated office resource packages.
6. **Delivery:** preserve source evidence and candidate dispositions, write a report
   with counts, decisions, tests and uncertainties, then record review completion
   for the final fingerprint. Verify the monitor's actual Save download afterward.

These checks supplement source, identity, merge and omission review. They do not
replace Michael's human vetting or establish current availability, phone
verification or office approval.

## Evidence and judgment

A reference to another program is not evidence that the referring organization
provides that program. Do not turn financial assistance, a referral, eligibility
examples or historic coverage into a direct clinical-service claim. Negative or
unconfirmed statements do not justify a Type or For group. Check what ambiguous
words mean: high-school seniors are not older adults; stroke/bereavement survivors
are not abuse survivors; prescription glasses are not pharmacy assistance.

A generally available service need not acquire every possible population label.
Use explicit targeting, eligibility, dedicated service or documented accommodation.
Spanish access does not establish ethnicity. Do not infer identities from names.
Groups and Types in an auto workbench are proposals for human review, not silently
approved canonical office taxonomy. Creating a new office's taxonomy and modifying
an existing curated office taxonomy are separate decisions.

Groups describe supported access pathways in a resource. For a record containing
multiple programs, matching two groups does not establish that a single subprogram
serves that intersection. Keep each program's eligibility and availability clear in
Information. Do not equate an AI navigation audit with the editor's explicit human
For-group review or its separate Curated flag.

When adding a source-backed clarification to a resource appearing in multiple
saved category results, preserve each category copy's own existing text. Append or
revise through durable result revisions, verify against the pre-change snapshot,
and rebind the navigation proposal to the resulting curation fingerprint. Do not
copy the final merged description over all earlier category-specific versions.

## Scout enforcement and durable navigation

`scout_review_readiness.py` checks the structural contract before a review can be
recorded. `scout_navigation.py` validates an immutable navigation proposal against
the exact completed curation fingerprint and requires complete resource coverage,
defined labels, literal evidence, and explicit no-group decisions. It rejects
stale proposals and unused labels. These checks cannot judge whether an excerpt
actually supports a claim; that remains part of the requested review.

The proposal changes exported Types and groups only. It preserves resource IDs,
facts, Category membership, original results, sealed assignments and human approval.
SQLite retains navigation revisions and their reasons. The review fingerprint
includes the navigation content (or an existing compiled taxonomy's seed hash).
Later content or taxonomy changes require another review. Earlier review events
that lack the current readiness contract cannot enable Save. The monitor reports
an outstanding structural requirement while awaiting review.

For a completed job without an existing taxonomy compilation, prepare a JSON file:

```json
{
  "schemaVersion": 1,
  "baseFingerprint": "CURRENT_CURATION_FINGERPRINT",
  "categories": [{"id": "food", "types": [
    {"label": "Groceries", "definition": "Take-home grocery assistance"}
  ]}],
  "groups": [{"label": "Seniors", "definition": "Dedicated older-adult assistance"}],
  "assignments": [{
    "resourceId": "RESOURCE_ID",
    "types": {"food": [{"label": "Groceries", "evidence": {
      "field": "description", "text": "EXACT SUPPORTING TEXT FROM THIS RECORD"
    }}]},
    "forGroups": [],
    "noGroupReason": "The saved record establishes broad access, not population-specific service."
  }]
}
```

The abbreviated example must be expanded to cover all Categories and resources;
every defined label must be used. A group assignment has the same label/evidence
shape as a Type assignment. An intentionally empty `groups` list also requires
`noGroupCatalogReason`. Obtain the base hash with
`curation_fingerprint(store.get_scout_curation_job(JOB))`; it is distinct from the
final review fingerprint after navigation is present.

Save the actually reviewed proposal:

```sh
python3 -m resource_research_agent.scout_navigation --database DATABASE --job-id JOB --proposal PROPOSAL.json --reason "Reviewed navigation decisions"
```

Then build and inspect the local draft using `build_scout_review_file`. Follow the
review-report/completion commands in `scout-orchestration.md` only when the actual
review is finished. Saving a navigation proposal alone never enables Save.

Existing approved taxonomy compilations use their own study revision path. Do not
combine competing taxonomy mechanisms or rerun the old Mesa-specific prototype on
a different corpus. For St. George's 879 records, the reviewed navigation proposal
is the applicable path.

## Local For-group checks in every generated workbench

The workbench and Resource Assistant share two levels of local checks, with no AI
call. Keep the shared For-group module in Scout's template and
`resource-assistant/src/js/28-for-group-checks.js` synchronized when changing it.

1. Apply only the approved relationships: Deaf & hard of hearing and Blind & low
   vision each imply People with disabilities when both labels exist in the office
   catalog. Never create an unavailable group or infer unrelated labels. Navigation
   validation rejects proposals missing these parent assignments. Test both the
   underlying tags and combined AND results, including children's hearing programs.
2. Require the editor to confirm every applicable group, or explicitly confirm that
   no specific group applies, before saving resource edits. Show the group's saved
   definition beside its checkbox; definitions can be edited under Admin → For.
   A review is tied to the resource's name, description, Information, Categories,
   Types, assigned groups, and available group labels/definitions. A change to any
   of those requires another confirmation. Phone/address/hours-only edits preserve
   a current review. A missing legacy review still needs confirmation on editing.

Imports and merges retain resources, with missing/stale group reviews counted in
Admin → Resources and a Review next action. They do not silently mark resources as
reviewed. Scout also blocks marking Curated or exporting a selected curated resource
until its group review is current. Group review remains separate from human Curated
and telephone verification. Generated AI proposals begin without a human review stamp.
A scoped Scout export preserves the review date while rebasing its content key to
its reduced catalog. Adding catalog options later requires renewed review.

This is structural checking plus an explicit human decision. It cannot establish
that every semantic assignment is correct or that a person is eligible. No automatic
classification, paid AI calls or provider-page extraction are part of these checks.

## Durable priority proposal and completion contract

`scout_review_priorities.py` stores immutable revisions separately from resource
results and navigation. It supports both reviewed navigation and compiled taxonomy
workbenches. Its base fingerprint binds the completed curation and current
navigation/taxonomy; changing either invalidates priorities. The final review
fingerprint also includes the priority proposal, and contract v3 requires a complete
current priority review before Save is enabled. Old completion events do not satisfy
this contract. A draft HTML can still be built before priorities are ready.

Prepare an explicitly reviewed JSON proposal (expand to every category membership):

```json
{
  "schemaVersion": 1,
  "baseFingerprint": "PRIORITY_BASE_FINGERPRINT",
  "assignments": [{
    "resourceId": "RESOURCE_ID",
    "categoryId": "housing",
    "tier": "start",
    "reason": "Establish this local shelter intake and family eligibility first.",
    "question": "What is the current intake route and alternative when full?",
    "evidence": {"field": "description", "text": "EXACT SAVED RESOURCE EXCERPT"}
  }]
}
```

Get the base with `priority_base_fingerprint(job)` from `scout_review_handoff`,
then save with:

```sh
python3 -m resource_research_agent.scout_review_priorities --database DATABASE --job-id JOB --proposal PRIORITIES.json --reason "Completed per-category AI priority review"
```

This command records the reviewer's decisions; it does not classify resources.
Inspect the generated file before recording final review completion. Report tier
counts by category and unique resources in Start here so repeated listings do not
inflate the human workload estimate. Staff may override priority in their local
workbench without altering the saved AI proposal or marking anything Curated.

## Curation help and interface updates

Generated auto[Location] files use curation-specific Help and Admin Help. Keep the
red starting hint explicit: read both help sections; Ctrl+Alt+A (Control+Option+A
on Mac) reveals Admin, then click Admin and Admin Help. Keep entry instructions
in Help and the red hint; Admin Help assumes its reader is already in the workspace.
Include Match all/any
examples using available group labels, Stephanie's four headings, a printable
first-resource walkthrough, printed-handout suitability, human Curated status,
curated-batch export behavior, and browser-state/HTML/package distinctions.
Verify the actual shortcut and buttons in the rendered workbench.

When updating older workbench controls, retain the exact embedded seed, storage
and artifact identifiers, extra attachment scripts, and existing question editor.
Back up first; do not regenerate resources from a newer source or infer new group
assignments as part of a controls upgrade. Preserve prior approval marks. Missing
group-review confirmations remain honestly missing; an interface update is not
a content review or authorization to invent priority proposals. Verify legacy
persistence, questions and Match all/any behavior before replacing active copies.
