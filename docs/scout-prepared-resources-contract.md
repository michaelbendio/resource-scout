# Prepared-resource delivery contract

Implemented first delivery: [Mesa, four categories](mesa-wsrs-tso-handoff-20260925.md).
This is the data delivery mode approved September 25, not the older HTML workbench
contract. [Design and decisions](scout-prepared-resources-design-20260925.md) explain
the policy; the [JSON Schema](../schemas/scout-prepared-resources-v1.schema.json)
and `prepared_resources.validate_artifact` define structural and semantic checks.

## Delivery file name

From 28 September 2026 `prepared_export` writes
`scout-<office>-prepared-resources-<YYYY-MM-DD>.json` and its `.json.gz` copy, where
`<office>` is the office slug and the date is the snapshot's generation date, for example
`scout-welfare-square-prepared-resources-2026-09-28.json`. Agreed with WSRS-TSO on
26 September so deliveries can be told apart; the receipt records it as `artifactFile`.
Earlier deliveries keep their plain `prepared-resources.json` names.

## Preparation and review

New curation jobs explicitly select `scout_curation_runner --prepared`. This seals
policy `prepared-resources-v1-five-sections` into assignment version
`codex-preparation-v5-office-fit` (from 28 September 2026; earlier jobs used
`codex-preparation-v4-source-checks`), distinct from existing jobs. It retains only
proposals that pass the [office-fit rules](office-fit-rules-20260928.md); until that
date it retained "useful reserve proposals rather than minimizing their count", which
Michael reversed ("settle the conflict in the way that most narrows the output"). The closed worker response
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

For re-curation, `--reviewed-context FILE` seals earlier reviewed records and human
state cautions as evidence, with a bounded candidate-linked index and separate
`reviewed-resources.json`. It never skips a new candidate disposition or supplies
human approval. `--all-research-runs` explicitly includes every completed research
collection returned for the office, retaining candidate IDs, source responses and
run provenance. Both switches require prepared mode and change the job fingerprint;
existing checkpoints remain intact. Without the latter switch, the established
single-canonical-run selection remains unchanged. The persistent supervisor checks
the saved prepared draft hash before declaring **Ready for Codex review**.

Version 4 clarifies that preparation includes targeted official-source checks for
material gaps. A usable reserve resource needs credible identity, relevant service
and a practical contact/intake route; unknown hours, costs, insurer participation
or capacity alone do not require administrator-only status. Consequential identity,
existence, geography, service or access conflicts do. Information is written for
missionaries and clients, with research-process reasoning kept in the internal
evidence. Older version 3 assignments and drafts retain their recorded policy;
worker prompts read the sealed instructions rather than silently substituting the
latest instructions. This does not change the consumer artifact's major version.

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
No opening set of three or total ranking of the reserve is introduced.

## Starter sets, selected complements and reserve — Michael, September 29

During whole-collection review, after facts, office fit, identity and taxonomy have
been reviewed, apply this sequence to every category:

1. Select **7–10 starters**, with individual contribution and limitation explanations.
   Record an evidenced size exception when fewer suitable resources are available.
2. **Select and order the strongest complementary additions.** Explicitly consider
   **uncovered Types** (kinds of help not yet represented), different eligibility,
   locations, languages, access arrangements, and useful alternative providers that
   help spread referrals. Compare each addition against both the starters and the
   complements already selected. Reassess remaining gaps after every selection.
3. Keep the other usable, uncurated resources in the **searchable reserve**. Failure
   to make either selected list is not itself a reason to exclude a resource.

An uncovered Type merits consideration, not automatic selection. Sharing a Type
does not make a resource redundant. Distinguish useful alternatives from duplicates
through evidenced differences that matter to a client. For every selected complement,
explain its practical contribution and limitations relative to what is already
selected. Do not invent benefits, claim available capacity without evidence, or fill
a numerical quota. Stop when further additions lack a clear complementary benefit;
record remaining gaps and why selection stopped, including when none are justified.

All four [office-fit rules](office-fit-rules-20260928.md) apply to **every retained
resource**, including reserves. Preserve evidence and record the reason for omissions.
Needs-resolution records remain administrator-only; selection never confers human
Curated approval or agency verification. Retain a consideration reason for every
exported non-starter membership, including selected complements.

Record each category's ordered complements, reasons, limitations and stopping reason
in the review ledger and report. **Export/import follow-up remains:** an explicit
complementary-selection field and corresponding WSRS-TSO reader support are needed
to carry this order into the app. This instruction change does not implement those
features. Existing JSON and read-only previews still use the behavior below; do not
claim that they already display the AI's complementary order. Frozen comparison
experiments retain their original instructions.

## Live review progress — September 29

The reviewer initializes `review/progress.json` and replaces it atomically after
each completed category check and major stage, across all sessions. This file is
for the progress dashboard, not import or human approval. Use the actual category
IDs in the run's review scope, with one row for every category:

```json
{
  "updatedAt": "actual UTC timestamp",
  "stage": "content",
  "summary": "Specific completed work and current task",
  "checkpointFile": "/absolute/run/path/review/decision-ledger.md",
  "identityStatus": "pending",
  "validationStatus": "pending",
  "categories": [
    {"categoryId": "housing", "content": "in-progress", "taxonomy": "pending", "selection": "pending"}
  ]
}
```

`stage` is `content`, `identity`, `taxonomy`, `selection`, or `validation`.
Each status is `pending`, `in-progress`, or `complete`. The checkpoint must be a
nonempty saved file inside this run's review directory, documenting the decisions.
Content completion means the category's candidate dispositions and retained facts
were assessed. Taxonomy completion means supported Types/groups and no-group
decisions were reviewed. Selection completion means starters, ordered complements,
consideration reasons and gaps are authored. Identity and validation are
collection-wide stages. Reopen a completed status when later findings require work.
Update the file before ending a session and at final completion.

Counts represent completed judgments, never files read, elapsed time or native
heartbeats. The dashboard labels them reviewer-reported checkpoints. They do not
replace the full input, preservation, schema and export gates; a completed progress
file alone never makes a delivery ready. The dashboard deliberately shows separate
stage counts rather than inventing an overall percentage or review ETA.

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

There is no reserve rank. In the current export/reader contract, WSRS-TSO chooses five at a time, prioritizing a Type not
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
