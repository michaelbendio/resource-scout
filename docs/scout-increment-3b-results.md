# Increment 3B: group review and complete migration planning

Status: review tools implemented on `v2.0` following Michael's “go ahead” after
accepting the 3A pilot. Michael has reviewed `autoProvoGroupReview` and approved Scout’s work.
The implemented review tools and historical inventory are accepted.
**Provo retirement is not complete:** 21 of 25 affected resources still need
classification research, all 25 need migration review, and an existing location
reader compatibility problem must be fixed before export. No production office
package, group label, or location application was changed.

## Michael's acceptance

Michael reviewed the portable group-review page and said:

> I've reviewed autoProvoGroupReview. I approve Scout's work.

Acceptance is recorded in `output/provo-group-review/review-acceptance.json`,
bound to reviewed HTML SHA-256
`0955361959d40844d5d7ff05fd02f274ca5744f0f7efdaf20941aaa7d92429ba`.
The reviewed page is preserved unchanged. This accepts the work presented;
the remaining research, explicit per-resource migration reviews, and reader
compatibility fix remain necessary before Provo retirement. No group outcomes
or resource mapping decisions have been invented from this overall approval.

## What is usable

Open `/taxonomy-review` from the classification page and choose a project.
The complete connected package supplies the counts, not just selected resources.
Group cards show definitions and aliases, current/proposed distinct resource
counts, members, categories, coverage, group evidence, overlap, possible duplicate
records, and website/phone provider clusters. Clusters are candidates, not a
verified count of independent providers. Distinct programs remain separate.

A small group may answer an important missionary question. No minimum, quota,
quality score, or automatic retirement is used. Zero members do not prove a group
is unnecessary when classification coverage is incomplete. A group's unresolved
count conservatively includes members with unresolved resource-level audit
findings, even where the disputed finding concerns another classification.

Reviewers can recommend retain, clarify, change prominence, merge, or retire.
They record a practical use, rationale, reviewer, and disposition for every
current or proposed member, including proposed removals. Merge targets must be
existing exact office groups. These are **recommendations only**: group labels,
memberships, aliases, and the location app's display preferences do not change.
Definition clarification continues through the versioned definition reviewer;
label renaming requires a future explicit membership migration. Recommendations
become stale when source data, definitions, or classification work changes.

A category-migration draft inventories every affected resource across the whole
package, including old category-owned Types and legacy aliases. The review
requires completed research, choices among current/researched memberships,
explicit Type dispositions, human resolutions for material findings, and a
supported service category for each resource. Supported groups may be empty with
an explicit explanation. Unconfirmed memberships must be resolved in the
classification editor before the migration can pass. The six-resource pilot's
acceptance does not resolve its remaining provider questions or approve these
migration mappings.

A draft can add unselected source-package members to classification research
without repeating completed work. Use the classification page/CLI to deliver the
new assignments to the actual services. This changes the inputs, so create a
fresh complete migration draft after the research is ready. A resource newly
added after the project began requires a project based on the latest package;
the original project source is never rewritten to accommodate it.

For compatible migrations, an explicit whole-plan approval is required after all
resource mappings. Exports preserve the complete latest package, IDs, unrelated
fields, contacts, writing, history, and exact referenced PDFs. Per-resource
classification changes receive newer timestamps and history entries. Retired
categories receive the existing `categoryMigrations` and deletion tombstones.
Revision/input hashes reject changed evidence or reviews. Export retries return
the same bytes; cancellation does not mark anything saved. Only a successful
save acknowledgment archives the migration and requires a new package connection.

## Historical Provo review

The portable **autoProvoGroupReview.html** is a read-only inventory built from a
copy of project 1 in the accepted pilot database. It contains no new research,
reviews, or approvals. Its source remains historical v41:
`dc883d19eff7a30e78d33df580ea8408a50788eade33647c40ec6a23f0201a49`.
The accepted `autoProvoClassificationPilot.html` remains separate and unchanged.

| Group | Current resources | With completed pilot proposals |
| --- | ---: | ---: |
| Exiting corrections | 1 | 3 |
| Families with children | 4 | 6 |
| Medically vulnerable | 0 | 0 |
| Seniors | 3 | 5 |
| Spanish speaking | 3 | 6 |
| Veterans | 1 | 3 |
| Women | 0 | 0 |

There are 183 office resources; only six have completed classification research.
Counts retain unresearched human memberships. They are not the final group
inventory. Medically vulnerable's definition is also still pending. There is no
basis here for automatically retiring either zero-member group.

Seniors has 17 category members, Veterans nine, and their union is 25 distinct
resources. Four have completed research. The draft also identifies two old IDs
that redirect to these categories: `Seniors` and
`8ad17c9098d5a2d035768a60bd4367ff`. Every affected mapping remains unreviewed.

Local artifacts: `output/provo-group-review/` contains the copied review database,
JSON snapshot, portable HTML, and manifest. The HTML is copied to the established
iCloud `Documents/TSO` review location; local byte equality is verified. That does
not establish that an iPad has already synchronized or opened the file.

To reproduce in a new output directory:

```sh
python3 scripts/build_taxonomy_review.py \
  --database output/provo-classification-pilot/pilot.sqlite3 --project 1 \
  --output output/provo-group-review-new --retire seniors veterans
```

## Reader compatibility finding

The current `resource-assistant` reader merges category migrations by source ID,
with the incoming record winning. After retirement, an older incoming package can
replace an alias's retirement with its old redirect. The target category has
already been deleted, and final validation rejects the merge as an unknown
target. This was reproduced through the actual `provo.html` merge functions in
an isolated Chrome profile. No live office data was involved.

Scout includes these aliases in the complete draft but **blocks whole-plan
approval and export whenever such aliases exist**. There is no override or
unverified claim that the present reader supports this. Slice 3C must add and
verify reader compatibility before this block can be relaxed. Required cases:
old and new package order, repeated merges, older aliases, exact unaffected field
and PDF preservation, no category resurrection, and no orphaned migration target.
Use the location repository's modular sources and its then-current release rules.
Do not solve this by silently dropping migration history in Scout.

## Verification

- 18 focused synthetic taxonomy tests cover whole-office unique counts, provider
  candidates and duplicates, partial coverage, single/zero-member groups,
  explicit removals, empty groups, complete mappings, old Types, incomplete
  research, unsupported assignments, unresolved findings, stale packages and
  definitions, preserved research, alias export blocking, full ZIP preservation,
  exact retry/save acknowledgment, workflow isolation, and stale revisions.
- Full Scout suite before the final three added tests: 244 tests, 243 passed,
  one optional test skipped. The additional three focused tests pass.
- Real Chrome QA exercises group recommendations, all mapping reviews,
  whole-plan approval and invalidation, unsaved-edit protection, cancellation,
  byte-identical download retry, save acknowledgment, and 1024/768/390 widths.
  Compatible no-alias migrations merge, reopen, and merge an older package
  through the actual Provo reader without resurrecting categories. The separate
  alias case is captured as an expected compatibility failure, not a passing
  production migration.
- Existing classification browser/office-merge regression passes. Existing
  writing tests pass in the full suite. Portable historical review has seven
  cards, 25 migration records, no editing forms, and no browser errors or
  horizontal overflow at the checked widths.

Browser evidence: `output/taxonomy-browser-verified/` and
`output/taxonomy-classification-regression/`. Synthetic QA does not count as
independent AI research or Michael's approval.

## Next discussion and the grand plan

Discuss whether the group cards make usefulness and coverage understandable,
and how much review effort the complete migration requires. Complete the
remaining actual research and human mappings before any Provo retirement.
The next coding slice is 3C: fix the reader compatibility issue, then implement
prominent/All groups, contextual counts, and OR within each dimension / AND
between Types and groups. A development preview and normal location-app release
review precede publication. Increment 3 is not complete until those behaviors
and the migration have been exercised and reviewed.

The grand plan then continues with increment 4 (maintenance), increment 5
(proposed lessons from vetted package changes), and increment 6 (adaptive
category-specific research runs). Lessons remain reviewable JSON/Markdown data;
this increment activates no learning policy.
