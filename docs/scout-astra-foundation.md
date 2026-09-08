# Astra research foundation: first implementation checkpoint

The new workflow can finish primary-only research, require a sampled blind
comparison, or add targeted checks without requiring all challengers everywhere.
It uses the existing maintenance, review and package mechanisms and the existing
category playbook library. The public package/review requirements do not change.

## What is implemented

- Opt-in `astra-sampled-v1` execution, separate from legacy required-auditor and
  required-blind jobs. Preparing a new execution never converts an old one.
- A sealed manifest containing baseline package hash, office/service area, scope,
  roles, model identities (null when unknown), guidance and category playbooks.
- Resumable discovery focus passes, primary synthesis, and a primary-only
  self-review/freeze. Employment uses its existing seven focuses. Resource
  rechecks use the relevant guidance to examine one whole resource.
- Category sampling with a recorded seed, deterministic SHA-256 ranking,
  algorithm version and selected set. Deliberate comparisons are kept separate.
  The example configuration starts at one third plus deliberate Employment.
- Claude assignments built from original identities, service information,
  neutral category scope, office taxonomy and common writing requirements.
  Primary findings, learned search vocabulary, pass plans, prior research checks
  and administrative question hints are excluded. All primary tasks touching a
  category freeze before outside assignments for that category become available.
- Targeted ChatGPT, Grok and Perplexity assignments with an operator and specific
  reason. They examine the frozen result. Requests must precede sealed final
  reconciliation; a later change needs an explicit new execution.
- Availability records, pending-check reporting, and assignment receipts for
  actual context, model, coverage gaps and active/waiting time. Unavailability
  never becomes a zero-finding result. It does not block unrelated categories or
  prevent saving a reply already received before the outage.
- Reconciliation requires a disposition for every supplied outside finding.
  Original and assisted results stay separate. Unresolved Claude findings can
  enter the existing administrative question-export path without service approval.
- Protocol/scope changes can name a predecessor and reason. They create a fresh
  execution, preserve the old one, and retain prior sampled categories. Additional
  categories receive a separate sampling cohort; old samples are not rerolled.

Research completion is not curation, provider verification, publication or lesson
activation. A context receipt is an operator attestation; code cannot establish
what a remote browser conversation actually saw. Use fresh isolated Claude
contexts and retain actual provider replies. Known context reuse across primary
or challenger work is rejected. Do not mark a partial transport packet complete.

## Operator workflow

Copy `resource_research_agent/maintenance_guidance/astra_execution.example.json`
into the new run directory. Set the actual service area, deliberate category IDs
and known model identities. Generate the random seed once before preparing the
scope, save it in that configuration, and keep the same file on resume. The
example placeholder seed is rejected. Production sampling should be drawn over
the planned scope rather than creating one-category random cohorts repeatedly.

Prepare with the existing command and an explicit new database, for example:

```sh
python3 -m resource_research_agent --database output/autoMesaV2-astra/research.sqlite3 maintain prepare BASELINE.zip --office 'Mesa TSO' --run-name autoMesaV2 --category-id employment --execution-config output/autoMesaV2-astra/execution.json
```

Use the package's actual office identity. Add explicit `--resource-id` selections
to recheck known resources; category selections alone perform discovery. All
package identities remain available for duplicate checks.

Continue through `maintain next PROJECT` and `maintain submit PROJECT STAGE FILE`.
Each result must match the sealed assignment hash and exact output contract.
Pass replies contain observations; primary, freeze and final replies contain full
resource proposals. Preserve raw external responses separately from parsed JSON.

Before requesting an outside assignment, use `maintain provider PROJECT
--revision REV --researcher Claude --status available --operator NAME --reason
EVIDENCE --context-id SESSION`. This records an actual browser check; it does not
open the service or purchase access. For limits, record `unavailable` and announce
the limitation. `maintain status` reports pending checks and timing; timing sums
are assignment effort, not wall-clock duration when assignments overlap.

Request a specific challenge with `maintain challenge PROJECT --revision REV
--task-id TASK --researcher Grok --operator NAME --reason REASON`. ChatGPT and
Perplexity use the same route. Availability alone does not select a challenger.

For an explicit replacement or scope addition in the same database, prepare with
`--supersedes PROJECT --operator NAME --change-reason REASON`. A sampled predecessor
retains its existing random and deliberate comparisons and seed/rate. Added
categories form a recorded cohort. New assignments start empty; old results are
not relabeled fresh. Changing the comparison policy is a separate future reviewed
operation, not an undocumented way to waive a missing Claude check.

## Verification and preserved work

Synthetic tests cover primary-only completion, all three targeted challengers,
blind input exclusions, category freeze barriers, unchanged legacy behavior,
restart/idempotence, incomplete replies, context misattribution, immutable
guidance and primary freezes, required dispositions, availability outages,
scope amendments, question export and transaction rollback.

Final verification: the full Python suite ran 337 tests successfully, with one
existing skip. The 21 new execution tests include guidance snapshots, input
isolation, all targeted roles, amended sampling, interruption rollback and curator
question handoff. `git diff --check` passed. No provider/browser availability is
implied by synthetic tests.

The old `output/autoMesaV2/` artifacts remain in place. `ARCHIVED.md` marks their
status and `archive-checkpoint-20260907/` holds verified checkpoint copies and an
inventory. The old 2.7 GB database was not copied, migrated or deleted. The latest
old Education packet remains uncollected, with conversation URLs preserved.
The new live execution will use a separate `output/autoMesaV2-astra/` directory.
No new live research or subscription changes were made for these software tests.

## Next checkpoint in the grand plan

Run the Mesa Employment demonstration with a deliberate Claude comparison and a
small review summary with bold changes. Implement the agreed curator-question UI
in common application sources and verify the full autoMesa-to-office-to-Scout
package round trip, including answers and history. Current iCloud mesa.html still
needs the question-aware common application update before delivery. The browser
package test's missing Playwright dependency must be addressed for that test.

Then implement proposed lessons and bounded experiments. Automatic playbook
activation and adaptive pass selection/stopping are not implemented here. Their
evaluation will use pilot experience and later curator packages, not synthetic
test results as research evidence.
