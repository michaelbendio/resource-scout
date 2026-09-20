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
4. **Usability:** inspect Category Types, Browse by Group, search, and combined
   Type/For filters. Multiple Types use OR; multiple groups default to AND, with an explicit
   Match any option for OR. The two dimensions combine with AND. Check meaningful matches and empty combinations.
   Inspect the Information reader and editor and confirm zero new human Curated
   flags. Preserve browser-local work if Michael has already edited the older file.
5. **Delivery:** preserve source evidence and candidate dispositions, write a report
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
