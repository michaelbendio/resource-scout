# Increment 3: categories, Types, and groups

Status: implementation authorized by Michael. Slice 3A is implemented and
software-tested; its historical Provo pilot has completed definition review,
real classification research, all 18 external audits, and Codex reconciliation.
Michael has approved the six-resource pilot and reconciliation. Slice 3A is
accepted. The subsequent “go ahead” authorized 3B; its review tools are now
implemented and Michael has approved the historical group-review work, with
all 25 affected resources now researched. Migration completion still requires
human review of uncertain memberships and mappings, and a reader compatibility
fix. See [3B research proposals](scout-increment-3b-research.md) and
[3B results](scout-increment-3b-results.md).
Michael authorized 3C after reviewing the 3B research report. It is implemented
and tested in an isolated location-app checkout; preview review and release remain
pending. See [3C results](scout-increment-3c-results.md) and
[implementation status and remaining work](scout-increment-3-results.md).

Michael accepted the increment 2 pilot's writing and Scout's reconciliation of
the other AIs' findings. Build on that evidence without repeating the writing
exercise. Classification should help missionaries find appropriate resources
and keep printed information clear. Private research explanations stay outside
the client-facing Description and Information.

## What the current files establish

- The authorized historical Provo v41 ZIP has 183 resources, 20 categories,
  and seven group labels. Only 11 resources have groups and 16 have Types.
  These are assignment counts, not evidence that every blank needs filling.
- Seniors has 17 category members and Veterans has nine: 25 distinct resources
  in their union. Retiring those categories requires reviewing all affected
  resources, including resources outside a small pilot.
- Provo exports groups and Types as labels; categories have IDs. Its catalog
  does not supply full classification definitions. Preserve the package format
  and use a versioned office guidance document for definitions and aliases.
- `taxonomy_groups.py` has useful distinction and filter rules, but also a fixed
  catalog, legacy mappings, and Mesa resource-specific decisions.
  `taxonomy_types.py` includes Mesa category choices; `taxonomy_compile.py`
  compiles an AutoMesa-specific resource set. Do not make these the generic
  Provo classifier or alter their historical results.
- The increment 2 workflow already preserves package lineage, evidence,
  assignments, review revisions, PDFs, and later human edits. Its editable fields
  are only `description` and `informationText`; keep that contract intact.
- In the location app, `getCategoryFilterOptions()` currently offers groups used
  in that category, and `resourceMatchesSelectedCategoryFilters()` combines
  Types and groups with one OR. Increment 3 needs the approved separate
  dimensions: OR within Types, OR within groups, AND between the dimensions.

## Three usable slices, with discussion between them

### 3A. Propose and review classifications for existing resources

Start here on Scout's `v2.0` branch. Use a separate classification project kind
with its own versioned field policy. Reuse or extract the safe workflow services
without widening existing writing projects. Initial editable resource fields are
`categories`, `categoryFilters`, and `forGroups`; all other resource fields and
PDF bytes come from the latest connected package unchanged.

Import the connected office catalog exactly. Prepare a reviewable JSON/Markdown
guidance snapshot containing definitions, aliases, category-specific Type
ownership, and evidence rules. Draft definitions are not office approval.
Missing or ambiguous definitions leave dependent assignments pending. Existing
labels remain the export values; internal definition keys do not rename them.
Changes to the catalog itself are separate proposals, never automatic creations.

For each resource, propose its direct service needs, applicable Types, and
supported groups. More than one category is legitimate for substantial direct
services. Generic referrals, incidental benefits, and word matches do not
establish those services. A group requires explicit targeting or a meaningful
accommodation. Universal availability does not imply a group. Spanish-language
service supports language access, not inferred ethnicity. No Type or no group
can be the correct result.

Record each proposed addition, retention, disputed removal, or unresolved
assignment with the resource/program, term and definition version, supporting
text, source reference, evidence date when available, and explanation. Group
evidence also records targets or accommodates. Existing human assignments remain
the baseline; inability to reconfirm one is distinct from evidence against it.

Use Codex primary classification, independent ChatGPT/Grok/Perplexity checks,
and Codex reconciliation before human review. Reuse the accepted pilot evidence
where applicable; research unresolved classification questions. Bind exact
assignments to source records, evidence, guidance, and proposal revisions.
Specify literal result field names and validate submissions before advancing.
Record each researcher's attachment access; shared observations do not count as
independent PDF inspection. Preserve raw responses and any transport repairs.

Show original/latest/proposed classifications beside the resource's Information,
with simple reasons, source links, unresolved questions, and explicit reviewer
choices. Changed evidence or definitions invalidate dependent review. Changed
eligibility or access information marks dependent groups for recheck. Nothing
starts approved, and required audits cannot be skipped or simulated.

Reconnect the latest package before export. Compare memberships as sets while
preserving original labels and unaffected order. Preserve independent later
edits; surface opposing membership changes and category/Type dependency
conflicts. A removed category cannot leave orphaned Types. Reuse deletion,
stale-review, successful-save, and exact-export provenance safeguards. Review
must bind to the final merged membership set, not just the old proposal.

This slice can export reviewed assignments to existing terms. It cannot retire
Seniors or Veterans or silently remove their legacy memberships. Their proposed
full replacements remain a separate migration review for 3B. Writing changes
approved in increment 2 remain separate, attributable proposals; this pilot
does not silently merge them into the office package.

### 3B. Review group usefulness and complete category migrations

Produce group review cards with definitions, practical uses, current/proposed
unique resource counts, members, categories, provider concentration, possible
duplicates, and reviewed/unreviewed/unresolved coverage. Count a resource once
across categories; do not confuse distinct program records with independent
providers. A partial classification pilot is not an office-wide group audit.

Flag small, ambiguous, overlapping, or poorly supported groups for attention.
Do not impose a minimum membership, quota, quality score, or automatic deletion.
A small group can answer an important missionary question. Proposed outcomes
include retain, clarify, change prominence, merge, or retire, with explicit
membership dispositions and review of any proposed missing assignments.

For Seniors and Veterans, present one reviewed change set mapping every affected
resource to actual service categories, their Types, and supported groups. The
historical package has 25 affected resources; recompute against the latest
package. Any unreviewed member, unresolved mapping, changed dependency, or
orphaned reference blocks retirement. Use the location app's existing taxonomy
migration/deletion mechanisms and test normal package merges. Renames retain
identity and aliases in guidance; package label changes require explicit mapping.

### 3C. Make the classifications useful in the location app

This is required work within increment 3, not a deferred optional enhancement.
Implement in `resource-assistant` modular sources with a development preview
before its ordinary release process. Scout 1.0 remains usable on `main`.

Offer office-selected prominent groups and an accessible All groups list.
Show relevant groups in category context, retaining access to every approved
group. Use OR within each dimension and AND between Type and group selections.
Show matching counts for the current context and distinguish office totals.
A selected group with zero matches stays visible with a clear explanation and
a way to clear it; never silently broaden the search or hide the selection.
Office-wide prominence preferences must travel with the office configuration
through a tested compatible representation, not exist only in Scout's database.

Verify ordinary resource view, Admin, iPad navigation, and print output together.
Classification explanations belong in review tools; clients receive the approved
plain-language resource content. Follow the location repository's then-current
instructions for package compatibility, release verification, and publication.

## First pilot and tests

Use the already authorized historical `provo-resource-package-4.zip`, explicitly
marked historical. Start with six resources: the three accepted writing-pilot
resources (CSFP, Provo City Housing Authority, and Financial Literacy Classes),
DWS Veteran Services, DWS Overview, and Food and Care Coalition. They exercise
age eligibility, uncertain program access, language accommodation, a Veterans-only
category, direct services versus referrals, and multiple service categories.
Keep accepted writing/evidence as linked inputs alongside unchanged source
records. No current-package request is needed to begin this development pilot;
a production merge still requires the latest office package.

Implement meaningful tests with each slice:

| Slice | Required evidence |
| --- | --- |
| 3A definitions and decisions | Two offices with different catalogs; no Mesa IDs/rules leaking into Provo; missing definitions stay pending; Types belong to their categories; no invented terms; explicit accommodation versus generic availability, language versus ethnicity, direct service versus referral, and unknown versus disproven prior membership. |
| 3A durable review and export | Restart, assignment binding, complete independent audit roster, stale evidence/definition/review invalidation, later independent human changes, opposing changes, category/Type conflicts, deleted resources, exact PDFs and untouched-field preservation, save cancellation, and normal office-reader merge. Existing writing-project tests remain unchanged and pass. |
| 3B group and migration review | Unique counts across categories, provider concentration, partial coverage, a useful single-member group, and zero-member uncertainty. Include an unselected affected resource to prove partial pilots cannot retire categories; test stale migration plans and complete mappings with zero orphaned references. |
| 3C actual navigation | Rare groups reachable through All groups; OR/AND combinations; correct contextual counts; selected zero-match visibility; clear filter; keyboard and iPad use; unchanged resource/print content; package round-trip of office preferences. |

Use deterministic fixtures for software correctness and the named real services
for the research pilot. Run focused tests, the Scout suite, and relevant browser
checks after implementation. Real browser checks must use a disposable office
data store and inspect exported/reopened results. A passing fixture is not human
acceptance of a classification or independent AI research.

## Discussion and completion

After 3A, discuss whether classifications are convincing, whether reasons and
uncertainty are understandable, which definitions need clarification, and how
much reviewer work remains. Then refine 3B and 3C from that experience.

Increment 3 is complete only when classification, group review, safe migrations,
and usable location navigation have been exercised and reviewed. The grand plan
then continues with increment 4 (maintenance), 5 (proposed research lessons),
and 6 (adaptive research runs). Keep lessons as reviewable JSON/Markdown data;
this increment captures evidence but does not activate learned research policy.
