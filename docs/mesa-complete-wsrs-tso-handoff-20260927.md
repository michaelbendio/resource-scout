# Complete Mesa handoff to WSRS-TSO — 27 September 2026

**Acceptance reopened:** hold broad missionary exposure pending
[reserve relevance correction](mesa-reserve-relevance-reopened-20260927.md).
A spot-check found apparent duplicate pathways and questions about which entries
deserve separate client-facing records. The artifact below remains the preserved
export, not a corrected or newly accepted reserve. Existing human work must remain.

The full Mesa re-curation and requested single Codex review are complete.
Use **[prepared-resources.json](../deliveries/mesa-complete-20260927-r2/prepared-resources.json)**
or its [gzip copy](../deliveries/mesa-complete-20260927-r2/prepared-resources.json.gz).
This supersedes the four-category scope; the earlier delivery remains historical.

- **1,866 resources:** 1,785 usable reserve candidates and 81 administrator-only
  `needs-resolution` records. No resource is marked human Curated or verified.
- **22 exact Mesa categories:** 218 starter memberships representing 195 distinct
  resources. Twenty sets have ten; Miscellaneous and Reentry Support have nine.
- **3,947 non-starter considerations**, 269 Types, 25 groups and 2,764 source URLs.
- Thirteen separated programmes are available as reserve candidates as Michael
  requested. Seven original human hides remain suppressed.

For Michael: [readable starter sets and five more](../deliveries/mesa-complete-20260927-r2/starters-and-five-more.html)
or [Markdown](../deliveries/mesa-complete-20260927-r2/starters-and-five-more.md).
The preview assumes starter Types are covered; WSRS-TSO should calculate coverage
from actual human curation. Held records are displayed separately.

## Import instructions for Claude

1. Apply [identity-migration.json](../deliveries/mesa-complete-20260927-r2/identity-migration.json)
   before importing candidates. All 150 previously allocated resource IDs and
   their existing aliases survive. Preserve Curated, deleted/suppressed, draft,
   pin, saved-for-review and resource-note decisions; conflicting human rows
   need administrator reconciliation. Registry IDs are code-assigned.
2. Read [taxonomy-transition.json](../deliveries/mesa-complete-20260927-r2/taxonomy-transition.json).
   Housing Legal Help retains its established Type ID. Thirteen other earlier
   Types have explicit broader proposals. Keep old office Types and human
   assignments; do not automatically delete them or retag curated records.
   This supplement is a reviewed compatibility handoff, not a new import
   requirement silently assumed to be implemented in WSRS-TSO.
3. Match the office category IDs exactly. The complete 22-category catalog
   includes Miscellaneous. Import `usable` for reserve use and `needs-resolution`
   for administrators only. Never treat `researchedAt` as agency verification.
4. Preserve human edits; updated Scout facts are proposals for reconciliation.
   Missing records are not deletions. The one ARM waitlist withdrawal event asks
   for administrator review, not automatic removal or unpublishing. The changed
   scope intentionally generates no disappearance claims.
5. Show starter contribution/limitation reasons and the other considerations.
   Alternatives have no rank: uncovered Type first, then alphabetical, five at
   a time. Shared resources should share curation progress across categories.
6. Validate idempotent import, previous deletion and edited-draft preservation,
   the Type transition, reserve search/Ask and printing. Test a parent facing
   eviction across housing, legal, shelter, food and transportation; also test
   formula, ADA paratransit, tribal credentials and military-record needs.
   Narrow service facts remain in prepared text even where navigation is broader.
   Print uncurated records with the agreed warning; Ask's prose is never printed.

## Validation and evidence

**52 relevant tests pass**, including full and prior Mesa delivery regressions,
independent JSON Schema validation, human-hide preservation, all thirteen releases,
exact consideration coverage, Type continuity, read-only preview ordering and
two byte-identical export attempts using an isolated registry copy. No runtime
dependency was added. The preview matches the visually inspected rendering.

Read the [collection review](mesa-complete-review-20260927.md) and its
[Type continuity amendment](mesa-taxonomy-continuity-review-20260927.md).
The [final static attestation](prepared/mesa-complete-review-attestation-20260927-r2.json),
[receipt](../deliveries/mesa-complete-20260927-r2/receipt.json),
[input manifest](../deliveries/mesa-complete-20260927-r2/final-collection-input-manifest.json)
and [final validation](../deliveries/mesa-complete-20260927-r2/validation.json)
bind the reviewed data and exported bytes. Original evidence and superseded
assemblies remain in the local research archive. The final registry is committed
with the delivery; it must be preserved for subsequent runs and a successor.

Snapshot: `ss_5e50a92e977f6d87f39fbc550ee569b4`.
JSON SHA256: `a2cf8a8cc0ae15659460952065a04240615a408a7bd5fed9cf93019f8ebcb1af`.
JSON is approximately 6.6 MB; gzip approximately 1.7 MB; every resource is under
5 KB. The schema remains major version 1.

Scout's review/export work is complete. Phase 5 means **actual WSRS-TSO consumer
validation**, which remains with Claude. No Dataverse import, office publication,
new paid worker, Cedar City resumption or consumer acceptance is claimed.
