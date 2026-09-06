# Increment 3C: location navigation and reader compatibility

Michael authorized implementation after reading `scout-increment-3b-research.md`.
Implemented on Scout `v2.0` and location-app branch `scout-3c`, in
`/Users/michaelbendio/resource-assistant-scout-3c`. Development review and the
location-app release remain pending. Scout 1.0 is unchanged.

## Reader behavior

- Types use OR with other Types; groups use OR with other groups; a resource must
  satisfy both dimensions when both are selected.
- Admin → For lets the office choose prominent groups. They appear when the
  category has members; every approved group remains available in All groups.
  No minimum membership count, inferred group, or automatic retirement is added.
- Buttons show matches under the opposite dimension's selections. All groups
  also shows separately labeled office-wide totals. Selected groups stay visible
  even with zero matches, with an explanation and Clear filters.
- Buttons expose selected state, retain keyboard focus after updates, and have
  touch targets at least 44 pixels high. Navigation controls stay out of print.

## Package compatibility

The location reader migrates schemas 1–3 to schema 4. Its focused 3 → 4 migration
preserves retired-category source IDs while retiring aliases that lead to them.
Retirement wins over an old redirect when packages are merged in either order;
approved category tombstones also cover aliases. Invalid targets still fail.

Office preferences travel as `forGroupPreferences: {prominent, lastModified}`.
Absent preferences retain the previous display default. An empty list is an
explicit choice. Newer settings win; old packages with no settings cannot erase
those choices. Group deletion tombstones also remove matching preferences.

Scout accepts and preserves schemas 3 and 4, including preferences, unrelated
fields, and exact PDFs. Alias-retirement exports require a reconnected schema 4
package from the updated reader plus all existing mapping and whole-plan approvals.
Older readers reject schema 4, so offices need the reader update before using new
exports. No production office package was exported in this increment.

## Development preview

`output/provo-navigation-preview/autoProvoNavigationPreview.html` contains the
unchanged historical Provo v41 inventory: 183 resources, seven group labels,
and all 93 original PDF assets. Its visible banner identifies the preview, and
storage ID `provo-scout-3c-preview` keeps its browser data separate from Provo.
New research proposals and category retirements have not been applied.

Try a category, open All groups, select a group and a Type, and clear the filters.
In Admin → For, try changing which groups appear prominently. The historical
package has relatively few memberships; empty results reflect that inventory,
not a failed research run. These are distinct-resource counts, not verified counts
of independent providers.

The location checkout provides `make-scout-navigation-preview` to regenerate
this artifact from the original ZIP. It embeds PDFs only in the review artifact;
normal app builds and office data are not rewritten.

## Verification

- Scout: 249 tests, 248 passed and one optional test skipped.
- Location application: full `python3 verify-tso-release`, including 42 Python
  tests and 139 browser self-tests.
- Disposable Chromium browser QA at 768 × 1024 and 390 × 844: rare group access,
  Type/group intersection, contextual versus office counts, selected zero matches,
  clear filters, keyboard Space/focus, Admin checkbox persistence, no horizontal
  overflow, no browser errors, actual ZIP save/reload/merge, and exact PDF bytes.
- A full historical package save preserves all 183 resources' client text and
  all 93 original PDFs, verified by SHA-256 after reopening the ZIP.
- The historical resource's printable HTML is identical before and after
  navigation; classification research explanations are not added to client text.
- Fixtures cover old/new package merge order, repeated merges, alias chains,
  category/group tombstones, explicit empty preferences, absent preferences,
  malformed preference rejection, missing targets, preserved extensions and PDFs,
  and future-schema rejection. Scout's schema 3 export block still passes.

Screenshots, a synthetic QA ZIP, and browser results are local under
`output/provo-navigation-preview/browser-qa/`. Synthetic QA is not research or
human approval of a resource classification.

## Release and next increment

The original `resource-assistant` checkout has unrelated staged and unstaged
work, including pending 2.3.5 changes. Those were left intact. The isolated
checkout proposes 2.3.6/build 152, subject
`Add Scout group navigation and schema 4 package compatibility`. Its AGENTS.md
requires explicit version approval before commit/push. Integration with the
pending main-checkout work and ordinary release verification must precede active
office publication; no production office HTML has been published here.

The historical Provo research still has 25 unapproved migration mappings. This
implementation does not supply those human decisions or mark retirement complete.
After discussing the navigation experience and completing the remaining increment
3 review/release work, the grand plan proceeds to increment 4: maintenance runs
that find new resources and propose evidence-backed changes for resources that
may have closed. A broken webpage alone is not evidence of closure. Increment 5
learns from vetted package changes; increment 6 adapts category-specific research
assignments. Lessons remain reviewable JSON/Markdown data.
