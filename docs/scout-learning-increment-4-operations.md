# Operating the Increment 4 learning loop

Use the same Scout database for intake evidence, learning and new research/editor projects. An active manifest is local to that database; these commands do not publish an office or synchronize independent databases. Back up the database using SQLite backup when it is in use, not by copying only the main file while a WAL is live.

## Ordinary feedback

The existing project `connect_latest` path records comparisons of explicitly connected packages, including question answers/history. `learning inbox` and `learning feedback` collect those comparisons automatically and idempotently. For a separate incoming package, use existing `evidence import` and `evidence compare` commands with explicit collection, office, source scope and lineage.

```sh
python3 -m resource_research_agent --database scout.sqlite3 learning inbox
python3 -m resource_research_agent --database scout.sqlite3 learning feedback > feedback.json
```

The queue groups observations by source lineage, resource and field. Exact before/after values remain available. Question transitions have labels for resolution, reopening, changed answers and removal; removal does not count as resolution. Different verification versions share a distinct event count, never an inferred independent-confirmation count. Restored IDs can reference earlier exclusions from the same embedded office; that is a lead for lineage review, not proof that the curator overturned Scout. Reidentified or combined resources still require explicit identity links and editor judgment.

An editor reads related groups and distills a concise hypothesis. No second form is imposed on curators and no model is automatically launched by these commands. This is the boundary where frontier judgment participates in learning; the program validates and preserves its output rather than inventing methods through keyword rules.

`learning distill document.json` accepts exactly:

```json
{
  "reviewer": "Name and role of the actual reviewing editor",
  "observationIds": ["existing observation ID"],
  "counterevidenceIds": [],
  "kind": "method",
  "interpretation": "Why this may be a recurring method issue; distinguish a later provider change, an earlier miss and an editorial preference.",
  "proposal": {
    "title": "Short method title",
    "supportIds": ["the same observation ID"],
    "scope": {"office": "Exact office name", "category": "category-id", "stage": "research"},
    "hypothesis": "Expected improvement",
    "alternativeExplanation": "What else could explain the observation",
    "counterexample": "A case the method must not mishandle",
    "baseline": {"path": "relative/path/to/current-guidance.json", "sha256": "exact file hash", "text": "exact guidance text"},
    "addition": "A concise proposed method, not a provider-specific fact",
    "evaluationQuestion": "What bounded test would distinguish improvement from harm?"
  }
}
```

For `resource-fact`, `policy` or `unsettled`, `proposal` must be null. Those interpretations remain evidence/review records and cannot enter the active playbook. Method proposals and their distillation record commit atomically. Counterevidence remains attached and its resource IDs are excluded from that lesson's test cases, just like supporting examples.

## Experiment and assessment

Existing `learning prepare`, `packet`, `submit`, `assess` and `report` commands remain compatible. Version 1 saved-case packets retain their original shared instructions—including the limitation identified in the earlier pilots. They are historical artifacts, not silently corrected control arms.

An optional `researchProtocol` in a new trial specification selects version 2:

```json
{"version": 2, "maxSourcePages": 24, "maxWebCalls": 24}
```

Version 2 requires a research-stage lesson. It supplies only resource names and website URLs, neutral shared procedural instructions, the scope and the exact baseline/candidate guidance. Preserve tool traces and actual delivery receipts outside the response contract. Page/call ceilings are prompt instructions; use an external runner for time limits and audit compliance before recommending activation. The experiment's `maxSeconds` is total dispatch-to-submission elapsed allowance, including operator handoff. A runner may impose a tighter per-arm process allowance.

When an amendment is already active for the scope, a new trial seals it into the baseline. Its candidate is the base file plus the proposed replacement amendment. Include any existing directions you intend to carry forward in that replacement. This prevents comparing a new amendment only against an obsolete clean baseline. The initial implementation allows one active amendment bundle per exact office/category/stage; unrelated scopes can have separate bundles. Broader scope needs its own proposal/evidence, not a wildcard activation.

An assessment alone changes no production instruction. A positive label cannot override newly introduced critical errors or unsupported promises. Research activation requires a real-retrieval protocol, both complete timely responses, a promising assessment, matching office/category, unchanged underlying guidance and comparison against the currently active amendment. Reviewers must examine the actual evidence and compliance limitations; the CLI is not an authentication system or a substitute for judgment.

## Explicit review, activation and rollback

Record actual authorization in the review; do not invent Michael's approval or provider verification. The frontier editor's current authority does not include independently approving production lesson activation.

```sh
python3 -m resource_research_agent --database scout.sqlite3 learning manifest
python3 -m resource_research_agent --database scout.sqlite3 learning review LESSON_ID review.json
python3 -m resource_research_agent --database scout.sqlite3 learning activate REVIEW_ID --expected-manifest CURRENT_MANIFEST_ID
```

`review.json` has exactly these fields:

```json
{
  "reviewer": "Actual authorized reviewer",
  "decision": "activate",
  "rationale": "Why the applicable evaluation supports this scope, including the evidence and limitations reviewed",
  "trialIds": ["applicable promising evaluated trial ID"],
  "supersedes": []
}
```

Other review decisions are `reject` and `defer`; they do not activate anything. Replacement must explicitly list the currently active amendment for the same scope. A changed manifest, changed baseline file, newer review, or incompatible experiment blocks stale activation. Roll back active guidance before rejecting it.

```sh
python3 -m resource_research_agent --database scout.sqlite3 learning rollback EARLIER_MANIFEST_ID --expected-manifest CURRENT_MANIFEST_ID --reviewer "Actual reviewer" --reason "Why rollback is appropriate"
```

Rollback restores the complete earlier manifest, with an immutable new history record. It refuses stale requests and restoration of a lesson with a later rejection/deferral. Ordinary statuses include proposed, experiment, evaluated, active, rejected and superseded. A deferred review leaves the lesson's evidence stage visible.

## What receives active guidance

New `astra-sampled-v1` maintenance/discovery projects seal applicable research amendments. New frontier-editor projects seal applicable editorial amendments for both editing stages. Assignments for other offices/categories/stages do not receive them. Claude's blind input excludes them. Existing projects—including assignments not yet dispatched—keep the snapshots sealed when the project was prepared. Use the explicit protocol-replan mechanism to change an existing research run. Legacy execution paths are unchanged; they do not silently pick up learned guidance.

Neither activation nor rollback rewrites package facts, question histories, provider-verification fields, historical packets, delivered HTML, or playbook source files. The immutable SQLite manifest and JSON lesson records determine guidance for new supported workflows.
