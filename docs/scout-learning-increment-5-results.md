# Increment 5 results — September 9, 2026

**Implemented on v2.0. No production policy was activated and no office package was changed.** All five numbered implementation increments in the learning/editor plan are now complete. Demonstrating an improvement in real research remains separate from completing its supporting machinery.

## What Scout can now do

- Preserve measured evidence and editor-authored proposals for exact office/category/discovery-or-recheck policies. Pass directions, required needs, stopping rules, model identities and sampling rates are stored as data.
- Compare a proposed policy with its baseline using sealed inputs, separate contexts and one declared comparison axis. Fixed-source screening is available; operating approval requires linked completed runs through the actual research scheduler.
- Assess the useful additions from each pass, count repeated findings once, and intentionally omit an undispatched tail when an approved stopping rule is satisfied. Every required need must be accounted for. Limits, unresolved gaps or sparse unexamined needs block stopping. Synthesis, primary freeze, outside checks and reconciliation remain required.
- Report unique outside assignments together with all overlapping category reasons. Deliberate and targeted checks survive changes to random sampling.
- Require recorded approval, apply policies only to new executions, reject stale activation, and roll back without rewriting old runs. Synthetic/historical approval cannot govern operational research.

The frontier editor still supplies judgments: what findings are useful, whether a need was adequately examined, whether results justify a new method, and why. Code does not infer suitability or verified provider facts from counters. Actual authorized policy approval remains a separate decision.

## Limited acceptance

The [replay](../experiments/operating-policy-20260909/replay.py) used a temporary database and synthetic responses through the actual scheduler. Its [saved result](../experiments/operating-policy-20260909/acceptance.json) shows:

| Check | Observed behavior |
| --- | --- |
| Baseline | Seven discovery passes completed |
| Candidate | Two passes completed; five deliberately omitted after synthetic duplicate-only findings and declared complete coverage |
| Remaining workflow | Both arms completed synthesis, freeze and reconciliation |
| Review/history | Paired evaluation, historical-only approval, activation in the temporary database, then rollback |
| Paid outside calls | Zero |
| Production policies activated | Zero |

**Seven versus two is test-fixture behavior, not a demonstrated research speedup or proof of equal quality.** The stopping decision relies on attributed editorial coverage judgments. The acceptance also imported the saved Mesa Employment tool batch as manual evidence, retaining its source hash and limitations. That observation did not create or activate a policy.

## Verification

The full Python suite passed: **421 tests run, one skipped** because the optional live Provo package environment variable was not supplied. This includes 27 new operating-policy tests. The suite emitted resource warnings about unclosed SQLite connections; no test failed. CLI discovery and whitespace checks passed. No new browser/HTML behavior was introduced.

New coverage includes immutable/malformed deliveries, separate contexts, fixed comparison axes and settings, unused model changes, incomplete/limited/late/cost-unknown results, duplicate findings, sparse needs, old-run preservation, model mismatch, changed guidance, overlap conflicts, unchanged baseline sampling, atomic failure/rollback, resumed stopping and historical-only safeguards.

## What the evidence does and does not support

We can now run and audit a real operating-policy experiment without changing production defaults first. We have not established a better live pass count, a cheaper model profile, a safe reduced sampling rate or a new real-world speedup in this increment. The earlier Mesa pilot remains too limited to justify those changes. Model/context identity and semantic coverage depend on honest operator receipts and review; the program cannot independently inspect a researcher's private reasoning. Trial allowances block approval of inadequate evidence, but do not enforce billing caps inside external chat services.

## Next in the grand plan

Use ordinary maintenance/editor outcomes to choose a defensible hypothesis, then run a small independent comparison through this machinery. Review the result and its limitations before activating anything. A negative or inconclusive result should leave the current policy alone. Later expansion of frontier-editor authority remains a separate discussion; completing these five increments does not automatically grant it.

See the [operator guide](scout-learning-increment-5-operations.md) for the workflow and exact input contracts, and the [design](scout-learning-increment-5-design.md) for the boundaries.
