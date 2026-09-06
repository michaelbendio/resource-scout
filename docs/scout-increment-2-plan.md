# Increment 2: improve existing resources safely

Implementation authorized September 5, 2026. Work stays on `v2.0` with isolated
databases. Increment 1 is accepted. Increment 2's pilot writing and
reconciliation decisions are now accepted; production package review is separate.
The software workflow and validation are implemented, and the authorized
historical Provo pilot has completed real research and reconciliation. Michael
approved the text and Scout's decisions; see [status and evidence](scout-increment-2-results.md) and
the [three-resource pilot report](scout-increment-2-pilot.md).

## Scope and decisions

Accept a standard resource ZIP and an explicit office identity. Freeze the full
package, its bytes, attachment hashes, selected stable resource IDs, writing
guidance, and researcher roster. An HTML application shell is not a package.
Only Description and Information are proposed for change in this increment;
all contacts, names, taxonomy, attachments, verification, and unknown fields are
preserved from the latest office record. Classification remains increment 3.

Codex researches selected resources; ChatGPT, Grok, and Perplexity independently
check the proposed information against the original and current evidence.
Codex reconciles their findings before human review. Every exact assignment and
response is durable. Required checks cannot be replaced by synthetic completion
in a real project. Consumer assignments retain the existing operator-controlled
delivery/pacing boundary; this increment does not add subscription API access.
The roster and stage instructions are saved data, not learned changes.

Provide a Scout review page with original/latest/proposed text, source evidence,
editable proposed fields, and explicit Curated/decline decisions. Editing clears
acceptance. Export requires a reconnected current package; a new connection
invalidates previous acceptance. Compare base/current/proposal field by field:
retain later changes to untouched fields, identify same-field conflicts, and
require a recorded reviewer choice. Missing/deleted resources cannot be
resurrected. Unresolved material audit findings need explicit human resolution.

Prepare selected updates as a standard package, preserving latest taxonomy,
history, deletion metadata, and referenced PDF bytes. Update timestamps only
after reconciliation and review. Preserve exact exported bytes and a manifest
linking base, latest, proposal, review, and final stable IDs. Record successful
save before hiding reviewed work; cancellation leaves it available. Repeated
requests must not silently create conflicting packages or lose review state.

## Tests and pilot

Exercise archive validation, guidance/roster snapshots, restart/idempotence,
assignment binding, independent checks and reconciliation, review invalidation,
same-field conflicts, later untouched-field edits, missing/deleted resources,
wrong-office and older-package connections, attachment preservation, exact
export/reopen behavior, failed saves, and concurrent/stale review submissions.
Use the real browser review page and ordinary office package reader/merge on a
disposable copy. Run focused tests and then the complete suite.

The known Provo v41/August 12 package is historical development evidence only.
Michael has been asked to identify the current package for the real pilot. Do
not label a historical fixture or simulated AI/reviewer response as current
Provo research or human approval. Implement and test independently while that
input is pending. Start with a small real pilot before the whole collection.

At completion, discuss evidence preservation, review effort, conflicting local
knowledge, and printed usefulness. Remind Michael that classification is next,
followed by maintenance, proposed research lessons, and adaptive research runs.
