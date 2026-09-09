# Detailed editorial decisions: portable format

Use a UTF-8 JSON document named `editorial-decisions.json`. This is a proposed interchange format for editorial trials, **not an existing Scout import API**. Its job is to make each editor's judgments comparable and preserve evidence for later implementation.

## Document fields

- `formatVersion`: `1`.
- `run`: editor identity, date, office, trial mode, source filename/hash, source record count, research scope and previous-result exposure. Unknown values are `null`, not guesses.
- `decisions`: exactly one record for every original stable resource ID, including anything unreviewed.
- `newOutputResources`: explicit new resource IDs caused by an authorized addition or split, with source links/reason; empty when none.
- `suggestions`: proposed improvements using the report's evidence/scope/test fields.
- `output`: filenames/hashes and final unique count; `null` if artifact construction is pending.

## A decision record

| Field | Meaning |
| --- | --- |
| `resourceId`, `originalName` | Exact source identity and name. Do not use array position as the persistent identity. |
| `disposition` | `retain`, `combine`, `reserve`, `exclude`, or `unreviewed`. |
| `targetResourceIds` | Output identities receiving this record's content. Required for `combine`; more than one is permitted with an explanation. For `retain`, name its retained ID. Empty for reserved/excluded/unreviewed records. |
| `reason` | Plain-language judgment specific to this resource, including the practical consequence. |
| `evidence` | Saved package fields, supplied documents or actually checked sources; record method/date and distinguish editorial inference from provider evidence. |
| `fieldChanges` | Exact field/path, before value, after value and reason. Empty for unchanged entries. Use separate draft resource JSON for lengthy complete replacements if needed. |
| `serviceScopeChanges` | Services removed or narrowed inside a retained entry, why, and where their original details remain. |
| `questionActions` | Question ID, action, destination and reason. Preserve actual answers/history; editorial archiving is not a human resolution. |
| `uncertainties` | Consequential unresolved facts and the appropriate next check/owner. |
| `originalRecordReference` | Location of the immutable complete original record, including provenance and attachments. |

Example structure, with deliberately fictional placeholders:

```json
{
  "resourceId": "SOURCE-ID-REQUIRED",
  "originalName": "Example Organization · Duplicate Program Entry",
  "disposition": "combine",
  "targetResourceIds": ["RETAINED-OUTPUT-ID-REQUIRED"],
  "reason": "The saved records describe the same program and intake. Keep one entry while preserving the separate appointment instruction.",
  "evidence": [
    {
      "kind": "saved-research",
      "reference": "inputs/original-resources.json#SOURCE-ID-REQUIRED",
      "fields": ["informationText", "phone", "address"],
      "checkedAt": null,
      "note": "No new provider contact; consolidation is an editorial judgment."
    }
  ],
  "fieldChanges": [],
  "serviceScopeChanges": [],
  "questionActions": [],
  "uncertainties": [],
  "originalRecordReference": "inputs/original-resources.json#SOURCE-ID-REQUIRED"
}
```

## Reconciliation checks

Every source ID appears once. Retain + combine + reserve + exclude + unreviewed equals the original unique count. A combine source is counted once even if parts go to two destinations; its targets must exist in the final output, without unresolved mapping cycles.

With no additions or splits, the final count equals retained source records. A source record folded into another is represented in that retained entry; it is not an additional final listing. Report additions/splits separately and explain the count equation when used.

Category totals count memberships and overlap. Keep unique resource counts, organization counts, estimated calls and measured curator time separate. A reduction in one does not establish the same reduction in another.

Preserve exact source packages alongside the ledger. Never treat reserve/exclude status as an instruction to delete a previously curated office resource or to record provider closure. A proposed lesson in this file has no activation effect.
