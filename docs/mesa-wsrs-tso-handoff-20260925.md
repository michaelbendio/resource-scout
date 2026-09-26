# Mesa handoff to WSRS-TSO — four categories

Michael accepted the starter trial and requested preparation of only Housing,
Food, Transportation and ID Recovery, including their usable reserve. He then
approved Claude's addition of a consideration reason for every non-starter
resource/category pair. This handoff incorporates both instructions.

Import [prepared-resources.json](../deliveries/mesa-four-categories-20260925/prepared-resources.json)
or its [gzip transport copy](../deliveries/mesa-four-categories-20260925/prepared-resources.json.gz).
Apply [identity-migration.json](../deliveries/mesa-four-categories-20260925/identity-migration.json)
before candidate import. [receipt.json](../deliveries/mesa-four-categories-20260925/receipt.json)
records hashes, review evidence and counts. Read the [exchange contract](scout-prepared-resources-contract.md)
and [schema](../schemas/scout-prepared-resources-v1.schema.json).

For Michael: [starters and five more — readable preview](../deliveries/mesa-four-categories-20260925/starters-and-five-more.html)
and [Markdown](../deliveries/mesa-four-categories-20260925/starters-and-five-more.md).
The preview shows five alternatives at a time, with all other reasons available
and unresolved items separated. Its coverage calculation assumes the starter Types
are covered; WSRS-TSO should calculate from actual human curation progress.

## Contents and decisions

- 143 distinct resources: **125 usable**, **18 needs-resolution** for administrators.
- 37 accepted starter memberships: Housing 9, Food 10, Transportation 9, ID Recovery 9.
  These represent **34 distinct resources**, so cross-category appearances share
  one curation decision.
- **118 non-starter considerations**, one per exported non-starter membership.
- 35 defined Types (from 41 old labels), 22 defined population/access groups, and
  140 shared source entries. Types remain selective: no Type covers every usable
  resource in its category. Rare meaningful pathways remain, including formula,
  paratransit, tribal credentials and document storage.
- All 22 authoritative Mesa category IDs are included in the catalog, checked
  against `/Users/michaelbendio/resource-assistant/mesa.html`. Only the four named
  categories are in scope; `completeScope:true`, `completeOffice:false`.
- Every resource uses the five Information sections. Starter populations have
  separately reviewed concise prose. Other migrated Population Served sections
  conservatively repeat existing eligibility where separately reviewed population
  wording was unavailable. New preparation workers write distinct sections.
- Three confirmed consolidations: Paz de Cristo's four overlapping records, the
  two Family Housing Hub records, and the two La Mesa Resource Center records.
  Original service-specific paragraphs remain labelled; no organization-wide merge.
  Other possible overlaps stay visible in consideration reasons.
- The 155 scoped source records are all assessed: five duplicate source rows merge
  into the retained identities, three human-hidden records stay suppressed, and
  four unsupported category-only records stay in Scout rather than this export.
  Three additional ambiguous housing pathways were moved to needs-resolution
  while writing the new considerations. No record is marked human Curated.

The data comes from the completed Mesa review and saved reconciled browser state,
plus the accepted trial's targeted checks and limitations. It is not a new full
research run or an agency-verification pass. Existing human titles and edits are
preserved; the clothing/furniture versus Autumn House conflict is admin-only.
Later office/browser edits must be reconciled through existing human state, never
overwritten by this frozen Scout snapshot. No ordinary location HTML was changed.

## What Claude should validate in WSRS-TSO

1. Apply aliases to existing Curated, suppressed/deleted, draft, pin, saved-for-review
   and resource-note references before import; flag conflicts between merged rows.
   Preserve the three saved suppressions even though those records are not imported.
2. Check major version and the exact office category IDs; import the same snapshot
   twice and confirm no duplicate candidates or changed human decisions.
3. Show only `usable` reserve resources to missionaries and Ask; expose the 18
   unresolved records to administrators. Apply the agreed warning when printing
   uncurated resources. Never derive a human verified date from `researchedAt`.
4. Show accepted starter reasons, then use `considerations` for alternatives:
   uncovered Type first, alphabetical second, five at a time. These reasons contain
   no rank. Shared resources share curation progress across categories.
5. Test a changed resource, a human-edited draft, a prior deletion, a narrower
   snapshot and an evidence-backed withdrawal. Keep human edits pending reconciliation;
   neither absence nor a withdrawal event automatically removes a resource.
6. Try a parent facing eviction across categories; retain housing, renter legal help,
   family shelter, food benefits and transportation facts in retrieval. Also test
   military-record and infant-formula needs in the reserve. Search relevance, Ask's
   output and printed warnings are consumer tests, not claims made by Scout's validator.

## Reproduction and phase status

The individual semantic choices are in
[mesa-four-category-review.json](prepared/mesa-four-category-review.json) and
[mesa-considerations-20260925.json](prepared/mesa-considerations-20260925.json).
The [static review attestation](prepared/mesa-review-attestation.json) binds the exact
reviewed payload and bundle; a compiler or data change cannot silently re-attest itself.
Original snapshots remain under `data/mesa-review-20260924/`; versioned intermediate
bundles remain under `data/mesa-prepared-four-20260925/`. All input hashes are checked.
The exporter refuses changed delivery bytes; use a new output directory for updates.

```sh
python3 -m resource_research_agent.mesa_prepared \
  --office-file /Users/michaelbendio/resource-assistant/mesa.html \
  --output /tmp/mesa-reviewed-preparation.json
python3 -m resource_research_agent.prepared_export \
  --bundle /tmp/mesa-reviewed-preparation.json \
  --output /tmp/mesa-four-delivery
python3 -m resource_research_agent.prepared_preview \
  /tmp/mesa-four-delivery/prepared-resources.json --output /tmp/mesa-four-delivery
```

Phase 0 accepted by Michael; phases 1–4 implemented for this scoped delivery.
Phase 5 **actual WSRS-TSO import validation remains with Claude**. No Dataverse
import, office publication, new paid worker or Cedar City resumption is claimed.
Other offices and Mesa's remaining categories are outside this first delivery.

## Validation completed

108 tests passed across the registry, preparation contract, worker/storage path,
export, Mesa delivery, starter trial and existing curation/recovery/review contracts.
The production JSON also passed independent Draft 2020-12 JSON Schema validation
using a temporary `jsonschema` installation; no runtime dependency was added.
Source seed, saved browser-state and original decision hashes still match.
Every migrated original Information paragraph survives, including Access and the
program-specific text of merged records. Regeneration produced identical delivery
JSON and alias mapping without allocating another ID. JSON is 491,525 bytes;
gzip is 102,644 bytes; the largest individual resource is under 11 KB.

| Phase | Checks completed here |
| --- | --- |
| 0 | Accepted selection compiler, evidence and source fingerprints, complete assessment coverage |
| 1 | Registry continuity, reviewed alias matches, conflicting identity rejection, exact office IDs and major-version rejection |
| 2 | Five-section schema/prompt/normalization, new-field persistence, preserved legacy seals, cross-category evidence, draft resume without new worker calls |
| 3 | Complete starter and consideration coverage, stale-review rejection, selective Types, rare pathways, program-specific explanations and static review attestation |
| 4 | Production registry binding, suppression migration, source links, original-text preservation, byte-identical regeneration, gzip, schema and size checks |
| 5 | Actual WSRS-TSO import/Ask/printing tests remain pending with Claude |

The read-only preview was rendered and inspected in an isolated headless Chrome
profile. It shows the starter reasons, first five alternatives, expandable further
batches and separate administrator-resolution items. This is a report check, not
a claim that WSRS-TSO's Curate tab was tested. The full local test log is
`/private/tmp/scout-prepared-regression.log`.
