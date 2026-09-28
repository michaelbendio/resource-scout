# Scout documentation guide

Read the current [operational status](../SCOUT_STATUS.md) first. Historical files
record what happened; they are not instructions to resume stopped work. Michael's
current decisions take precedence over older contracts and sealed-run descriptions.

## Current policy and operation

| Document | Use |
| --- | --- |
| [Office-fit rules](office-fit-rules-20260928.md) | Reachability, main service, direct contact and distinct agency/program entries; phone and online services count |
| [Orchestration](scout-orchestration.md) | Monitoring, checkpointing, unknown outcomes, evidence preservation and handoff |
| [Prepared-resource contract](scout-prepared-resources-contract.md) | Five Information sections, registry IDs, starters, reserve explanations and export validation; office-fit policy narrows older retention wording |
| [Prepared-resource design](scout-prepared-resources-design-20260925.md) | Design rationale and delivery phases |
| [WSRS-TSO artifact reference](wsrs-tso-scout-artifact-reference-20260925.md) | Consumer needs and recorded decisions |
| [Schema](../schemas/scout-prepared-resources-v1.schema.json) | Machine-readable prepared-resource format |
| [Identity registry](../registry/README.md) | Stable identity storage and maintenance |

## Delivery and evaluation references

- [Mesa four-category handoff](mesa-wsrs-tso-handoff-20260925.md): earlier partial delivery.
- [Full Mesa acceptance hold](mesa-reserve-relevance-reopened-20260927.md): relevance and identity concerns remain unresolved.
- [Housing trial report](../data/evaluations/implementation/docs/mesa-housing-preparation-review-results-20260928.md): separate evaluation worktree; complete for Housing only.
- [Six-category architecture review](six-category-architecture-review-20260918.md): historical evidence, not current provider authorization.

The Housing report link requires the local implementation worktree. On GitHub,
its files are on branch `docs/scout-evaluation-design-20260927`; they are not files
tracked by this branch. Do not remove that worktree before preserving its local data.

## Legacy and historical material

[Legacy curation](scout-curation.md), [curation runner](scout-curation-runner.md),
[workbench readiness](scout-workbench-readiness.md), and
[enrichment](scout-enrichment.md) describe retained HTML workflows. Historical
provider rosters, review tiers and Information-section counts do not override
current prepared-mode or office-fit instructions. Existing sealed jobs retain their
original prompts; changing policy requires an explicit new run or supported transition.

Dated handovers, pilots and results remain at their existing paths to preserve links
and provenance. Exact pre-cleanup status and README snapshots are in
[the September 28 archive](archive/20260928/README-archive.md). Local unused Jev
preparation is archived under `data/repository-cleanup-20260928/`, outside Git.
