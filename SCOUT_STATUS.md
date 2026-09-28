# Scout current status

Updated 28 September 2026. The research, evaluation and application branches are
consolidated for main. 754 tests ran successfully (4 skipped); no Scout workers were launched.
This is the operational handoff; historical checkpoints
are in the [archived status](docs/archive/20260928/SCOUT_STATUS.md).
Read [orchestration](docs/scout-orchestration.md) before operating a worker and
verify live processes/database state before acting.

## Stopped; next work is Welfare Square policy and run preparation

Michael requested stopping Scout before adding rules and a fresh Welfare Square
run. All observed workers, child tools, monitors, and dashboard/preview servers
were terminated; the follow-up process check found none. No new run has started.
Stop receipt: `~/resource-scout-pairwise/data/scout-stop-20260928.json` (local, ignored by Git).

The separate Claude-checkout Housing experiment was interrupted. Preserve its
ledger; an in-flight request can have an unknown outcome. Do not replay or resume
it automatically. The stop applies to all historical continuation authorizations.

The [four office-fit rules](docs/office-fit-rules-20260928.md) are now present in
this checkout at `dfe6fb2`, including Michael's decision that phone and online
services count when available to the office's residents. They are Scout policy,
not an experimental option. Frozen evaluation prompts remain unchanged.
Before the fresh run, confirm any further rules Michael wants, the intended
workflow and its policy coverage; use a new run directory and preserve old work.
This cleanup does not authorize provider calls or another production launch.

## Current deliveries and acceptance

- **Mesa Housing DeepSeek trial:** complete, Housing-only. 104 leads yielded
  100 records: 92 usable reserves, 8 needs-resolution, 10 starters and 90
  considerations. DeepSeek/max performed curation and one sequential review.
  The merged tree holds [the prepared file](deliveries/mesa-housing-deepseek-20260928/prepared-resources.json),
  [evaluation](deliveries/mesa-housing-deepseek-20260928/evaluation.json),
  and [readable report](deliveries/mesa-housing-deepseek-20260928/review.html).
  Commit `362bb37` is pushed on `docs/scout-evaluation-design-20260927`.
  82 evaluation tests passed before cleanup; package validation and offline resume
  passed. No WSRS-TSO import, human approval, or agency confirmation is claimed.
  Active processing including original research: 376.35 minutes; billing unreconciled.
- **Full Mesa:** [delivery](deliveries/mesa-complete-20260927-r2/prepared-resources.json)
  exists, but broad missionary exposure remains **on hold** for relevance,
  duplication and granularity concerns. Structural checks do not establish
  practical usefulness. See [the acceptance hold](docs/mesa-reserve-relevance-reopened-20260927.md).
- **Other offices:** preserve existing research and outputs. Historical running,
  automatic continuation and queued-office notes are not current launch authority.
  Cedar City's discussion hold remains; do not start another St. George run.

The merged and Housing implementation identity registries contain 1,923 identities
and were synchronized at delivery. Keep stable IDs, aliases, human decisions and
source evidence intact. Do not replace either with an older registry.

## Workspace map

| Checkout | Branch | Purpose |
| --- | --- | --- |
| `~/resource-scout-pairwise` | `pairwise-research-experiment` | Integration checkout; current research evidence remains here |
| `~/resource-scout-pairwise/data/evaluations/implementation` | `docs/scout-evaluation-design-20260927` | Housing evaluation implementation and delivery; distinct Git worktree |
| `~/resource-scout-claude` | `claude-evaluation` | Separate interrupted comparison; do not resume automatically |
| `~/resource-scout` | `main` | Canonical application checkout; consolidated code |
| `~/resource-scout-v1` | detached | Historical checkout; preserved |

Verify `git worktree list` and branch status before any consolidation. Do not merge,
remove or relocate worktrees merely because they appear old. The nested implementation
checkout is inside ignored `data/`; its tracked work is merged but its local evidence
remains there. Existing runtime paths have not been relocated.

## Operating rules and historical evidence

Use the [documentation guide](docs/README.md) for the prepared-resource contract,
review instructions and delivery references. New prepared outputs use five Information
sections, explained starters and reserves; old HTML tiers and four-section instructions
are historical. AI review never sets human Curated status or an agency verification date.

New workers require explicit scope/provider authorization. The operational policy
uses Codex primary and DeepSeek only as challenger; a separate comparison is not
permission to change production providers. Jev is not part of the workflow.
Preserve sealed prompts, native responses, failed attempts and completed databases;
do not rerun old work just to obtain a clean status. The six-category architecture
review uses Extra High and its [evaluation checklist](docs/archive/20260928/SCOUT_STATUS.md#architecture-review-checklist-retained-for-follow-up).

Cleanup preserved exact prior README/status snapshots in `docs/archive/20260928/`.
Untracked Jev preparation was moved to the local ignored archive
`~/resource-scout-pairwise/data/repository-cleanup-20260928/`; its manifest records original paths and hashes.
The previously deleted proposal is preserved in the historical documentation archive;
its old active path remains removed. No research data, resource or delivery was deleted.

Repository consolidation and preservation details: [cleanup record](docs/repository-cleanup-20260928.md).
