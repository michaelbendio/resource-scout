# Prepared-resource delivery contract

Implemented first delivery: [Mesa, four categories](mesa-wsrs-tso-handoff-20260925.md).
This is the data delivery mode approved September 25, not the older HTML workbench
contract. [Design and decisions](scout-prepared-resources-design-20260925.md) explain
the policy; the [JSON Schema](../schemas/scout-prepared-resources-v1.schema.json)
and `prepared_resources.validate_artifact` define structural and semantic checks.

## Preparation and review

New curation jobs explicitly select `scout_curation_runner --prepared`. This seals
policy `prepared-resources-v1-five-sections` into assignment version
`codex-preparation-v3-reserve`, distinct from existing jobs. It retains useful
reserve proposals rather than minimizing their count. The closed worker response
schema and normalizer preserve email, sources, research date, preparation state,
resolution reason and evidenced taxonomy suggestions. IDs are provisional draft
references. Workers cannot allocate production `sr_` IDs or supply `verifiedOn`.
Cross-category extensions preserve earlier source pages and taxonomy suggestions;
an earlier needs-resolution flag remains for the requested collection review to
resolve explicitly rather than disappearing when a later batch overlooks it.

Information has these standalone bold headings, in order:

1. Services Offered
2. Eligibility Requirements
3. Population Served
4. How to Best Connect
5. Important Information to Know

Access details belong under How to Best Connect. Specific facts remain searchable
even when their navigation labels become broader. Group suggestions are reviewed
across the collection; no new group is automatically created by a worker batch.
Draft output is `scout-preparation-drafts`, `importable:false`, and **Ready for
Codex review**. It does not enable legacy HTML Save or complete the requested review.
The existing office pipeline continues its established HTML mode unless a new run
is deliberately configured for the prepared workflow; no running office is converted.

The requested reviewer writes an internal `scout-reviewed-preparation` bundle:

- `inputs`: hashes of the exact reviewed source snapshots and decisions.
- `identityDecisions`: each source ID exactly once, with reviewed program boundary,
  optional existing canonical match, and reason. Names/domains are not automatic matches.
- `assessments`: a disposition for every scoped source record; every usable reserve
  record survives independently of starter selection. Merges point to a retained
  record. Human suppressions are preserved. Raw or not-offered records stay in Scout.
- `payload`: complete office category catalog, explicit export scope, reviewed
  taxonomy, prepared resources, source catalog, starter sets and considerations.
- `review`: reviewer, date, substantive identity/content/taxonomy/starter/preservation
  judgments, and fingerprint of everything above. A changed input requires a new review.

Bottom-up taxonomy review considers selectivity, overlapping meanings, useful rare
pathways, definitions, evidence for each assignment and explicit no-group decisions.
Counts cannot perform that judgment. Seven to ten complementary starter choices per
category have contribution and limitation explanations; justified exceptions are explicit.
No tiers, opening set of three, or total ranking of the reserve are introduced.

## Non-starter considerations — Michael/Claude change order

Every exported non-starter resource/category pair now has exactly one:

```json
"considerations": [
  {"resourceId": "sr_…", "categoryId": "housing",
   "reason": "Adds youth shelter and young-adult transitional housing, addressing the youth-specific gap identified in the starter set."}
]
```

Write one curator-facing sentence about what the resource adds or why it is worth
investigating. Check comparative claims against the actual starter set: do not say
it adds missing eviction legal help when eviction legal help is already selected.
Reasons for needs-resolution records explain why resolving the record could be useful;
they do not make it available to missionaries. Merged/excluded/hidden records are not
exported, so they do not get separate consideration entries.

There is no reserve rank. WSRS-TSO chooses five at a time, prioritizing a Type not
yet covered by curated resources, then alphabetical order. Scout's read-only
preview assumes the starter Types are covered only to make this next step testable.
`considerations` is an optional addition to major version 1 for compatibility with
older readers, but is mandatory on new Scout deliveries and checked for exact coverage.
The request came from Michael relaying Claude's `wsrs-tso/docs/scout-handoff-design.md`
sections 5 and 11; that external file was not inspected here.

## IDs, export and revisions

The committed [identity registry](../registry/README.md) allocates production IDs.
Code binds reviewed aliases to opaque, namespace-derived IDs. Independent run IDs,
renames, changed URLs, categories and ordering do not redefine identity. A new run
must explicitly match existing identities or leave uncertainty visible. Conflicting
established IDs stop for an explicit migration; this exporter does not guess merges
or splits. Human decision conflicts are reconciled in WSRS-TSO, never resolved by
last-writer-wins Scout import.

`python3 -m resource_research_agent.prepared_export --bundle REVIEW.json --output DELIVERY`
loads the registry and validates everything before writing. `--previous FILE` binds
the predecessor and compares revisions. The one-time `--initialize-registry` flag
refuses an existing file; never use it to replace a lost registry. Restore from Git.
The registry must be committed before a real handoff. Export refuses to replace
different delivery bytes; use a new directory for a changed snapshot. Interrupted
exports can reuse the already allocated aliases without inventing new identities.

Files: `prepared-resources.json`, deterministic `.json.gz`, `identity-migration.json`,
and `receipt.json`. Compression is transport only. The migration contains full legacy
IDs, canonical IDs and saved human suppressions. Apply it before importing candidates.
The receipt binds reviewed inputs, review fingerprint, registry fingerprint, semantic
snapshot fingerprint, output byte hash and counts. It is not human Curated approval.

Canonical hashing is Python `json.dumps(value, ensure_ascii=False, sort_keys=True,
separators=(',', ':'))`, encoded as UTF-8 and SHA-256 hashed. Resource revision hashes
exclude only `revision`. Snapshot content hashes exclude `snapshot`, `review`, and
`changeSet`; the review-bundle fingerprint excludes only `review`. Registry aliases
are covered by the review and receipt. Identical content reuses its snapshot ID;
with its prior snapshot supplied, regeneration retains that snapshot's metadata.
The exact algorithms are in `resource_identity.py` and `prepared_resources.py`.

The full office category catalog must equal the authoritative office IDs. Labels
are display text, never a matching substitute. `scope.categoryIds` identifies this
delivery's subset; `completeScope` means that subset was fully assessed, while
`completeOffice` says whether the entire office is represented. Only two complete,
matching scopes can report `notObserved`; it still never means deletion or closure.
Prepared taxonomy IDs are retained across later label edits. Do not allocate a new
Type/group ID merely because its wording improves.

## Import boundaries

Import `usable` for potential reserve use, and `needs-resolution` for administrators.
No human approval, deletion, pin, client note or verification date is in the resource
payload. Preserve all WSRS-TSO human state and edits; changed Scout facts are proposals
for reconciliation, not permission to overwrite human text. Missing records are kept.
`researchedAt` is a research date/time or null, never agency confirmation.

Reserve search and Ask may use usable uncurated records. Reserve printing requires:
**Not yet reviewed by the office. Call the provider to verify this information.**
Only an office-entered date produces a printed verified date. Ask's generated prose
is never printed. Saved-for-review items reference the stable resource ID and may
have a note about the resource, never about the client. These are consumer behaviors.

An evidence-backed withdrawal is `{resourceId, reason, sourceIds, action:"admin-review"}`
in `withdrawnEvents`. Referenced sources and identity must exist. It flags an
administrator; it does not unpublish or remove the resource automatically.

Sources are stored once in a top-level catalog and referenced by ID. Fact-level
evidence can be added later without repeating source bodies. This delivery uses
reviewed source URLs and preserves existing inline citations without inventing
fact-level provenance. A resource is limited to 500,000 canonical UTF-8 bytes,
providing headroom under WSRS-TSO's reported approximately 1 MB text-cell limit.

Optional additions stay in major version 1 and readers ignore unknown fields.
Removed fields or changed meaning require a new major version, rejected clearly by
older consumers. Scout tests the export contract, not Dataverse implementation:
real import idempotence, human-edit preservation, reserve warnings, Ask and printing
must be demonstrated by WSRS-TSO before phase 5 is called complete.
