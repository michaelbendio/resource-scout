# Operating guide: measured research policies

Use this after ordinary research/editor work produces a plausible improvement hypothesis. It adds no forms for missionaries or curators. The frontier editor interprets the evidence; Scout seals, checks and preserves the decisions. Existing curator feedback and lesson activation remain in the [Increment 4 guide](scout-learning-increment-4-operations.md).

These commands use the same Scout database as research. Back up an in-use database through SQLite backup. Policy heads are database-local, not automatically synchronized between computers. No command here launches a model, purchases service, or publishes an office.

## From evidence to a bounded comparison

1. Capture an actual sampled execution, or import attributed manual measurements. Pending assignments are pending work; unknown dollar costs stay null. A manual pilot is not an independent multi-model comparison.
2. Ask the editor to propose one category/office/task-kind policy, explaining the expected benefit and risks. Start from `policy baseline`; retain every previously required need, including small needs. Do not optimize toward a resource quota.
3. Seal a comparison before research: one axis, source package/cases, evaluation rule, fresh contexts and allowances. A `models` comparison keeps goals and schedule fixed; `goals` keeps model and pass order fixed; `schedule` may reorder/subset unchanged passes and change stopping/sampling.
4. Deliver the two arms in separate fresh contexts. A fixed-source screen can help reject a weak proposal. Approval requires completed experimental executions through the actual scheduler, linked to the sealed packets. Neither arm changes the active policy.
5. Review usefulness, essential coverage, errors, gaps, elapsed time, reported effort, cost and limits. “Promising” requires adequate evidence, not merely fewer calls. An inconclusive result is a useful outcome.
6. Obtain actual authorized review before activation. The editor cannot manufacture Michael's approval. Activation and rollback record the reviewer and preserve all prior versions. Only newly prepared executions receive the active policy.

## Command sequence

Replace uppercase placeholders with returned IDs. JSON files are inputs, not commands to send unchanged to a researcher.

```sh
python3 -m resource_research_agent --database scout.sqlite3 policy manifest
python3 -m resource_research_agent --database scout.sqlite3 policy capture PROJECT employment discovery --reviewer "Actual evaluator"
python3 -m resource_research_agent --database scout.sqlite3 policy baseline PROJECT employment discovery > baseline.json
python3 -m resource_research_agent --database scout.sqlite3 policy propose proposal.json
python3 -m resource_research_agent --database scout.sqlite3 policy prepare PROPOSAL source.json design.json
python3 -m resource_research_agent --database scout.sqlite3 policy packet TRIAL baseline --context-id BASELINE_CONTEXT
python3 -m resource_research_agent --database scout.sqlite3 policy packet TRIAL candidate --context-id CANDIDATE_CONTEXT
```

Proposal fields are exactly `referenceProjectId`, `candidate` (edited baseline policy), `evidenceIds`, `reviewer`, and `rationale`. Model identities map Codex, Claude, ChatGPT, Grok and Perplexity to actual model identifiers or null when unknown. Null cannot establish a live model comparison for a provider that did work. Provider roles remain fixed: Codex primary, Claude blind, others targeted challengers. This increment adjusts their configured models and check frequency; it does not interchange those roles.

Policies contain `scope: {office, category, kind}`, ordered `passes`, `requiredNeeds`, `stopping: {minPasses, consecutiveNoGain}`, `models`, and `sampling: {numerator, denominator}`. Each pass has `key`, `label`, `direction`, `coverage`, `vocabulary`, `sourceChannels`. Recheck policies have no individual discovery passes. Directions and coverage are data in the sealed policy, not hardwired category rules.

A live comparison source has this shape. Use the SHA-256 of the exact ZIP bytes and actual task IDs:

```json
{
  "packageSha256": "EXACT_PACKAGE_SHA256",
  "cases": [
    {"caseId": "discovery:employment", "sourceText": "Scope and source description, without expected answers or prior editorial verdicts."}
  ]
}
```

The design file has exactly these fields:

```json
{
  "axis": "schedule",
  "researchMode": "live",
  "evaluationRule": "Preserve essential needs and supported details; compare distinct useful findings and actual effort. Explain every loss.",
  "maxSeconds": 3600,
  "maxCostUSD": null,
  "subscriptionAllowance": "Record actual available allowance separately; not a dollar cost estimate.",
  "caseIds": ["discovery:employment"]
}
```

Use a held-out package/case set and keep prior verdicts out of researcher inputs. Unlike lesson experiments with explicit example IDs, this workbench cannot automatically prove that imported unstructured pilot evidence does not overlap the new cases; the designer must document that check. The packet does not include proposal evidence or expected answers.

For each live arm, prepare an isolated execution:

```sh
python3 -m resource_research_agent --database scout.sqlite3 maintain prepare source.zip --office "Mesa" --run-name "Employment baseline comparison" --category-id employment --execution-config execution.json --operating-trial-packet PACKET
```

The package, office and selected tasks must match the sealed packet. Use identical execution configuration for both arms; the packet policy supplies the different model/schedule/goals. Changed guidance or other research context invalidates the comparison. Use the normal `maintain next`, provider availability and `maintain submit` workflow. Receipts attest actual model identity and context isolation. All Codex stages identify their arm's primary context; outside checks use separate provider contexts, with no context shared between arms. The same fresh primary context can continue successive passes of its arm; “fresh” attests isolation from the other arm, not a new conversation for every pass.

Do not use `--historical` for a real operational comparison. Historical/synthetic executions can test the complete machinery, but their approval cannot govern nonhistorical research. The program checks linked state and receipts; it cannot independently prove that a human correctly named the browser model or kept contexts isolated.

For a fixed-source screen, choose `researchMode: "fixed-source"`, `packageSha256: null`, and use `executionProjectId: null` in results. Such a screen cannot authorize policy activation.

## Assessing value and stopping optional passes

After each discovery pass, before dispatching another, an evaluator may submit:

```json
{
  "reviewer": "Actual frontier editor/evaluator",
  "resultSha256": "EXACT_COMPLETED_RESULT_HASH",
  "retainedFindingKeys": ["stable-key-for-one-useful-finding"],
  "coveredNeeds": ["Exact required need examined"],
  "unresolvedNeeds": [],
  "limitHit": false,
  "reason": "Why these findings are useful and what was actually examined."
}
```

Use the same semantic key for the same fact found again. Neither another URL nor repeated wording makes another useful finding. This is editorial judgment with evidence; code only checks accounting and guards.

```sh
python3 -m resource_research_agent --database scout.sqlite3 maintain assess-pass PROJECT discovery:employment pass:PASS_KEY assessment.json --revision CURRENT_REVISION
python3 -m resource_research_agent --database scout.sqlite3 maintain stop-optional-passes PROJECT discovery:employment --revision CURRENT_REVISION --reviewer "Actual evaluator" --reason "Evidence for omitting the remaining tail"
```

Stopping requires the approved minimum, the specified consecutive passes with no new retained finding, every required need covered, all pass reviews present, and no limits or unresolved gaps. It cannot omit an already dispatched pass. Synthesis, freeze, required outside checks and reconciliation still run. A stop is stored as an intentional omission, never fabricated completion. Low resource counts alone do not justify stopping.

## Results, review and activation

A result contains exactly:

- `assignmentSha256`, `contextId`, `fresh`, `models`, `caseIds` copied/attested against the packet;
- `executionProjectId` for a live arm;
- `complete`, `limitHit`, `coveredNeeds`, `remainingGaps`;
- `findings`, each with `key`, `caseId`, `evidence`, `retained`;
- `activeMinutes`, `waitingMinutes`, `costUSD` (null when unknown).

Live results seal the linked execution's revision/hash, required completion, model/context receipts and timing. Summary effort cannot understate execution receipts. Both arms must account for every assigned case. Raw deliveries survive parse errors; accepted results and evaluations are immutable. A failed or partial trial needs a new trial design/context to retry, not an overwritten success.

The assessment contains `reviewer`, `verdict` (`promising`, `no-clear-benefit`, `worse`, `inconclusive`), `rationale`, `criticalErrors`, and `lostNeeds`.

```sh
python3 -m resource_research_agent --database scout.sqlite3 policy submit PACKET response.json
python3 -m resource_research_agent --database scout.sqlite3 policy evaluate TRIAL evaluation.json
python3 -m resource_research_agent --database scout.sqlite3 policy approve EVALUATION --reviewer "Actual authorized reviewer" --rationale "Actual approval and evidence"
python3 -m resource_research_agent --database scout.sqlite3 policy activate APPROVAL --expected-manifest CURRENT_MANIFEST
python3 -m resource_research_agent --database scout.sqlite3 policy rollback EARLIER_MANIFEST --expected-manifest CURRENT_MANIFEST --reviewer "Actual authorized reviewer" --reason "Why rollback is appropriate"
```

A stale manifest fails atomically. Existing projects, including undispatched assignments, retain their sealed policy. Changed playbook guidance requires a new comparison/review. Conflicting model profiles on overlapping resources fail visibly. Rollback changes future preparation; it does not rewrite old research.

## Reading the measurements

`maintain status` exposes outside workload with actual unique task/check assignments and all category memberships/reasons. An overlapping resource's one Claude check is one assignment even when several categories justify it. Random, reviewed-policy random, deliberate and targeted checks remain distinguishable. Deliberate and targeted checks survive a lower random rate.

`policy capture` saves compact receipts, hashes, pass reviews, stop decisions and workload. `policy import-measurement SOURCE METADATA` accepts attributed manual evidence; metadata is exactly `kind` (`manual-pilot`, `synthetic`, `execution-capture`), `reviewer`, `scope`, `notes`. Use capture for scheduler evidence. Imported claims of execution provenance do not substitute for linked executions in an approval.

`policy report` exposes evidence/proposals/trials/evaluations/approvals and the active head. Reported effort totals are not elapsed duration when work overlaps. Allowances are evaluation gates: late, limited, incomplete, over-budget or unknown-cost-with-a-dollar-cap results cannot justify activation. These commands do not enforce billing caps in external chat services or terminate their tools; the operator/transport must honor the allowance and stop dispatching work. No real efficiency improvement was established by the synthetic acceptance test.
