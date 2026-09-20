# St. George For-group gap

Michael noticed that the reviewed workbench has no For groups. The resource-content
review is complete, but the population-browsing part of the workbench is unfinished.
The prior ready-to-save handoff should have called this out explicitly.

Verified against the active production database after the final review:

- Import 1, `st-george-resource-package.zip`, contains `for_groups_json = []`.
- Every one of the 21 sealed curation assignments has zero `availableForGroups`.
- Curation instructions permit only existing, evidenced groups; they forbid creating
  missing groups during that pass. All resulting resource group assignments are empty.
- No taxonomy study or taxonomy compilation exists in this database.
- Export preserves this empty group set; it did not drop populated groups.

The separate taxonomy code is not yet a general solution for this corpus.
`taxonomy_groups.build_group_review_packet` requires completed Category/Type design
and explicitly expects the earlier 342-resource study. Its inference module also
contains resource-specific Mesa decisions. Reusing those decisions or changing only
the expected count would not constitute a St. George review.

Two available starting points need to be distinguished:

1. Earlier local workbench packages contain seven labels: Veterans, Families with
   children, Women, Spanish speaking, Exiting corrections, Medically vulnerable,
   and Seniors. These files establish prior usage, not current human approval of
   a complete St. George taxonomy.
2. The separate taxonomy prototype has a broader 19-population catalog, including
   disability, pregnancy/postpartum, youth, immigration, homelessness, survivors,
   income eligibility, and insurance access. It is a useful design input, not a
   completed set of assignments for these 879 records.

Recommendation: propose a suitable St. George group list, then review all 879 saved
resource records against it. Each assignment should identify explicit eligibility,
dedicated service, or a documented accommodation. Universal availability alone is
insufficient; Spanish-language access does not establish ethnicity. Keep resources
with no justified population label ungrouped and surface ambiguous cases.

No research rerun is needed to begin this work. Preserve the reviewed facts, IDs,
candidate provenance, human Curated state, and sealed assignments. Applying groups
must produce a separately reviewable result and update the generated artifact and
review binding; it must not silently change what the earlier review fingerprint
claims to cover. If Michael has begun browser edits, preserve them before replacing
his workbench copy.

Current status: group-list preference requested; no group definitions or assignments
have been activated and no new worker has been started.
