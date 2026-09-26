# Mesa prepared resources for WSRS-TSO

Only **Housing, Food, Transportation and ID Recovery** are in this snapshot.
The category catalog contains all 22 Mesa IDs; the other categories are outside scope.

- Import `prepared-resources.json` (or decompress `prepared-resources.json.gz`).
- Apply `identity-migration.json` first so existing human decisions keep their references.
  Preserve human suppressions, approvals, edits, verification dates, drafts, pins and notes.
- `receipt.json` records the reviewed inputs, registry, content and byte hashes.
- Open `starters-and-five-more.html` or `.md` to judge the starter sets and alternatives.

143 resources: **125 usable**, **18 administrator-only needs-resolution**.
37 starter memberships across 34 distinct resources; 118 non-starter consideration
reasons. The reserve has no total rank. Choose alternatives using actual curated
Type coverage, then alphabetical order, five at a time.

`researchedAt` is not a human verified date. An uncurated reserve resource prints
only with: **Not yet reviewed by the office. Call the provider to verify this information.**
No resource has been marked human Curated by Scout. Never overwrite human-edited
facts or delete a resource because it is absent from a later snapshot.

[Full handoff and consumer acceptance checks](../../docs/mesa-wsrs-tso-handoff-20260925.md)
· [Contract](../../docs/scout-prepared-resources-contract.md)
· [Schema](../../schemas/scout-prepared-resources-v1.schema.json)

Scout validation: 108 tests passed, independent schema validation passed, exact
reproduction and original-text preservation passed, readable preview inspected.
Actual WSRS-TSO import validation is the next step with Claude.
