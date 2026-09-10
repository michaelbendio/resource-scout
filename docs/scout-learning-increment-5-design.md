# Increment 5: measured operating policies

Implement on v2.0 without changing active research defaults or old projects. The current small pilots are useful observations, not sufficient evidence for an automatic scheduling change.

## Evidence and decisions

A policy workbench stores immutable source artifacts, observations, proposed policies, sealed paired trials, delivered results, evaluations and approval records. Policies have exact office/category/task-kind scope. Research content remains in playbooks; a policy can specify ordered passes and their goals, required needs, a stopping rule, model identities and a blind-sampling rate. Provider roles remain unchanged: Claude is blind, other outside researchers are challengers. Explicit deliberate checks are never cancelled by random sampling.

The operator/editor interprets results. Code does not decide that a provider is suitable or invent a lesson from keywords. Retained findings use stable semantic keys supplied by the evaluator; repeated keys count once. Reports distinguish observations, source artifacts, actual work and independent trials. Evidence imported from a manual pilot remains manual evidence, not scheduler completion or human verification.

## Controlled comparisons and approval

Seal source material, baseline/candidate policies, goals, limits and an evaluation rule before delivering packets. A trial changes exactly one axis: model identities, pass/stopping/sampling schedule, or pass goals. Other settings remain fixed. Two distinct fresh contexts must return the original assignment identities. Preserve incomplete/limit-hit deliveries; they cannot establish coverage or justify activation. Dollar cost is nullable and separate from subscription allowance and reported time. Fixed-source screens cannot authorize activation: live comparisons link to completed experimental scheduler runs without first activating the policy. Historical/synthetic approvals cannot govern operational research. Trial allowances are eligibility checks, not external billing controls.

Evaluation records retained value, lost needs, errors and the decision with reasons. Activation requires a complete applicable promising comparison with no lost needs/errors, all required needs covered, and explicit recorded approval. Approval/activation must still match the active baseline. Atomic manifest updates use compare-and-swap and retain history; rollback is explicit. This increment implements the mechanism, but does not approve a real policy change.

## Production integration

New sampled maintenance/discovery runs resolve approved exact-scope policies and seal them into the execution manifest. Old projects never consult live policy files or heads. Per-category sampling is reproducible from the existing run seed; overlapping categories produce one outside assignment per task, while the workload report shows all reasons. Conflicting model profiles on a cross-category task fail visibly rather than choosing silently.

An operator can assess each completed discovery pass against its sealed result, recording retained finding keys, covered needs, unresolved needs and limit status. A stop request only omits an undispatched tail after the approved minimum and consecutive zero-new-value criteria are met, all required needs are covered, and no relevant incomplete/limit/gap condition remains. Required needs preserve the original playbook coverage; proposals can add required needs. A small or sparse need is not dropped because its resource count is low. Skipped passes are recorded as intentionally omitted, not completed assignments; primary synthesis, freeze, required outside checks and reconciliation remain mandatory.

## Tests and acceptance

Exercise duplicate evidence and findings, incomplete/limit-hit results, one-axis comparisons, context reuse, immutable deliveries, sparse-need protection, stale approvals, atomic activation/rollback, changed models, overlapping-category workload, preserved deliberate/targeted reasons, sealed old runs, interrupted/resumed pass review and stopping, and no silent publication. Use synthetic fixtures for state transitions and the saved Mesa pilot as explicitly manual evidence. Run targeted checks, then the full suite once. Report implementation behavior separately from demonstrated research improvement.
