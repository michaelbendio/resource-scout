# Explicit prepared-review decisions, version 1

Effective September 30, 2026. New Mesa review uses `reviewDecisionContract: 1`.
This is the shared remedy for heuristic-generated judgments and ignored corrections.
The compiler checks faithful assembly, not whether a judgment is thoughtful or true.
A substantive supervising-assistant acceptance audit remains mandatory before export.

## Workflow and boundaries

1. Independently review the completed curation inputs and original candidate evidence.
   Write individual decisions below in groups of at most 15 resources or 30
   candidate/category pairs. A session completes at most two resource batches and four candidate batches
   (preferably linked to those resources), OR one category's taxonomy/selection
   finalization, then checkpoints before 75 minutes or context pressure. These are
   maxima, not required quotas. Resume saved work.
2. Reconcile Types/groups across the collection and explicitly revise affected
   resource decisions. Use evidence for every assignment; a no-group decision needs
   its own reason. No substring/keyword inference, scoring, generated reasons,
   blanket approvals, catch-all defaults, or automatic taxonomy mappings.
3. Author 7–10 starters with contributions/limitations, ordered complements with
   a reassessment after each addition, and considerations for every other retained
   resource/category membership. Uncovered Types are considered, never automatically
   selected. Keep remaining usable candidates searchable; unresolved items are
   administrator-only. Empty or smaller starter sets require evidenced exceptions.
4. Hash all authored files in `decision-manifest.json`. Compile; freeze its exact
   output as `content-reviewed.json` BEFORE reading the identity registry. The bundle
   uses precisely those four compiled fields, then adds identity decisions, input
   hashes and final review judgments. Reopen decisions and repeat compilation/freeze
   if reconciliation changes content. Never patch only the bundle.
5. Worker submits `STATUS.json` with `review-complete`. The pipeline validates the
   submission and stops for supervisor acceptance; it does not export or allocate
   permanent IDs. The supervisor audits actual category judgments and assembly,
   authors findings outside `review/`, and seals acceptance of that exact output.
6. Only accepted export writes the registry/delivery. Existing registry allocations
   and historical sealed deliveries remain intact. Office human approval and agency
   verification are never implied by either AI review or supervisor acceptance.

## Exact files

All referenced decision files must be under the review directory. Paths are relative
 to the manifest. SHA-256 means file bytes, not parsed JSON. Required lists cannot
 be omitted. Documents can be revised explicitly; regenerate hashes afterward.

`decision-manifest.json`:

```json
{
  "schemaVersion": 1,
  "draftsSha256": "SHA256 of curation/prepared-drafts.json",
  "resourceBatches": [{"path":"decisions/resources-001.json","sha256":"…"}],
  "candidateBatches": [{"path":"decisions/candidates-001.json","sha256":"…"}],
  "categories": [{"path":"categories/housing.json","sha256":"…"}],
  "collection": {"path":"collection.json","sha256":"…"}
}
```

A resource batch is `{"decisions":[...]}`; every original draft ID occurs exactly
once across batches. Restored resources also need a decision. Each row:

```json
{
  "resourceId": "provisional draft ID",
  "inputFingerprint": "resource_identity.fingerprint(original full draft object)",
  "assessment": {"state":"usable","reason":"Specific evidenced disposition"},
  "evidence": [{"reference":"official URL or exact saved evidence file/record","finding":"What it establishes"}],
  "ruleFindings": {
    "housing": {
      "reach":"Office reach/eligibility finding",
      "mainService":"Why housing is a main service",
      "directContact":"Direct intake route finding",
      "agencyBoundary":"Client-meaningful boundary or consolidation finding"
    }
  },
  "fieldDecisions": {
    "name":{"action":"retain","reason":"Specific source support"},
    "description":{"action":"retain","reason":"Specific source support"},
    "phone":{"action":"replace","value":"Corrected value","reason":"Evidence for correction"},
    "address":{"action":"retain","reason":"Specific source support"},
    "website":{"action":"retain","reason":"Specific source support"},
    "email":{"action":"retain","reason":"Specific source support or explicit unknown"},
    "hours":{"action":"retain","reason":"Specific source support or explicit unknown"},
    "informationText":{"action":"retain","reason":"Five sections and supported facts checked"}
  },
  "typeEvidence":{"housing-costs":"Resource-specific assignment basis"},
  "groupEvidence":{},
  "noGroupReason":"Why no evidenced group assignment applies",
  "result": "The FULL final resource object, as specified below; not a string"
}
```

`result` is the prepared payload resource shape: `id`, `state`, `name`,
`description`, `phone`, `address`, `website`, `email`, `hours`, `informationText`,
`categories`, `types`, `forGroups`, `sourceIds`, `researchedAt` (explicit null if
unknown); `resolutionReason` is required for `needs-resolution`. Use the existing
prepared-resource validator for details. All eight content fields are explicit.
For `retain`, the value must exactly equal the draft (an absent field is empty).
For `replace`, `value` must exactly equal the result; the reason is authored.
`ruleFindings` covers the union of original and final categories, including removed
memberships. `typeEvidence`/`groupEvidence` keys exactly match assigned IDs.

Excluded states are `not-offered`, `suppressed`, or `merged`; `result` must be null,
and no field/type/group decisions are required. Evidence and rule findings remain
required. A merged assessment includes `target`, the retained provisional ID.
For a restored resource, `inputFingerprint` is null and all fields use `replace`.
The collection's `restoredCandidates` maps its new provisional ID to original
candidate IDs; provenance must agree with candidate dispositions.

A candidate batch is `{"decisions":[...]}`, at most 30 rows. Every original
assignment candidate/category pair occurs once, including curation omissions:

```json
{
  "categoryId":"housing", "candidateId":"original assignment ID",
  "decision":"retain", "reason":"Individual evidenced decision",
  "resourceIds":["retained provisional ID"],
  "evidence":[{"reference":"assignment/category/candidate or official URL","finding":"Specific supporting finding"}]
}
```

`exclude` has an empty `resourceIds` list. The pipeline checks exact coverage against
completed curation assignments, and every retained resource needs this provenance.

A category document:

```json
{
  "categoryId":"housing",
  "taxonomyJudgment":"Evidence for useful distinctions and synonym consolidation",
  "starterSet": {
    "categoryId":"housing", "rationale":"Balanced set rationale", "gaps":"Remaining gaps",
    "members":[{"resourceId":"draft ID","position":1,"contribution":"Specific contribution","limitation":"Evidence-based limitation"}]
  },
  "considerations":[{"resourceId":"other retained draft ID","categoryId":"housing","reason":"Why a curator should consider it"}],
  "complements":[{"resourceId":"other usable draft ID","position":1,"contribution":"Benefit compared with starters AND earlier complements","limitation":"Known limitation","remainingGaps":"Reassessed gaps after this addition"}],
  "stoppingReason":"Why further complementary selections are not warranted"
}
```

Complete all scope categories exactly once. `starterSet.sizeException` is required
when size is outside 7–10. Complement positions start at 1, contiguous and unique;
complements are usable nonstarters. An empty list is valid with a stopping reason.
Considerations cover **every** retained nonstarter membership, including complements
and administrator-only unresolved records (explain the unresolved limitation).
Complement order stays in the ledger/report until export/import support is agreed.

`collection.json`:

```json
{
  "taxonomyJudgment":"Collection-wide normalization and assignment audit",
  "identityBoundaryJudgment":"Agency/program boundaries before registry matching",
  "preservationJudgment":"Source facts and human suppression preservation audit",
  "restoredCandidates":{},
  "payloadBase": {
    "office":{"slug":"mesa","name":"Mesa"},
    "scope":{"categoryIds":["all exact review scope IDs"],"completeScope":true,"completeOffice":true},
    "taxonomy":{"categories":[],"types":[],"forGroups":[]},
    "sources":[]
  }
}
```

Populate the exact office category catalog, Types/groups with stable IDs, labels and
meaningful definitions, and deduplicated source catalog in the existing prepared
schema. Resources reference sources by ID. Same-category Type labels and collection
For-group labels differing only by whitespace/case are rejected. This detects one
class of error; the reviewer must still consolidate semantic synonyms thoughtfully.

## Compilation and acceptance commands

```sh
python3 -m resource_research_agent.review_decisions \
  --manifest RUN/review/decision-manifest.json \
  --drafts RUN/curation/prepared-drafts.json \
  --output RUN/review/content-reviewed.json
```

Also writes `reviewed-selections.json` beside the content. Include the manifest byte
hash as `bundle.inputs.decisionManifestSha256`; preserve all existing input hashes,
identity decisions, review fingerprint and report requirements.

Only the supervising assistant, AFTER substantive inspection, authors a findings
JSON outside `review/`: nonempty `content`, `taxonomy`, `selections`, `assembly`,
`identity`, `preservation`, plus `categoryChecks` covering every scoped category.
Each check has `categoryId`, `finding`, and `sampleResourceIds` of actual retained
records (empty only for an empty category). This records audit evidence, not an
algorithmic quality score. Investigate suspicious patterns beyond minimum samples.

```sh
python3 -m resource_research_agent.review_acceptance \
  --bundle RUN/review/reviewed-bundle.json --findings RUN/audit/findings.json \
  --output RUN/supervisor-acceptance.json --reviewer 'Supervising Codex assistant' \
  --manifest RUN/review/decision-manifest.json --drafts RUN/curation/prepared-drafts.json
```

The receipt binds the bundle, review fingerprint, report, findings, drafts, manifest
and all decision documents. Any changed byte makes it stale. Never overwrite an
acceptance receipt; a revised audit gets a new path configured as
`supervisorAcceptancePath`. This is an operational role boundary, not a cryptographic
sandbox; a worker sharing a filesystem is explicitly prohibited from authoring it.

Existing sealed review work, including Welfare Square, may use the explicit
`--preserved-evidence` adapter **only after supervisor inspection**, without repeating
already authored review. Its JSON contains `compatibilityReason`, `content` equal to
the bundle's complete payload/assessments/candidateReview/restoredCandidates fields
that exist, and `decisionFiles:[{path,sha256}]` binding the original authored evidence.
It is never an automatic grandfathering or an alternative for new Mesa's required
structured contract. Every export, including evaluation handoffs, requires acceptance.

Evaluation `reconcile_and_export` first prepares `handoff/reviewed-bundle.json` and
stops before registry/output mutation when `acceptance_path` is absent. Inspect the
frozen evaluation decisions and exact bundle, add `handoff/report.md`, create an
outside-handoff supervisor receipt using the preserved adapter, then resume with
`acceptance_path`. Frozen evaluations and existing sealed outputs are not rewritten.
