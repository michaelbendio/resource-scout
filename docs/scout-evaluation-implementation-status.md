# Scout evaluation implementation status

## Ticket 0 — isolated checkout established (September 27, 2026)

Implementation worktree: `/Users/michaelbendio/resource-scout-pairwise/data/evaluations/implementation`.
Branch: `docs/scout-evaluation-design-20260927`; starting commit `b96cf55`.
The documentation branch's code baseline is `6eb7934`. No later Mesa recovery or
review changes were adopted. The parent Mesa checkout, index, published delivery,
and unrelated local changes are untouched. Its relevance acceptance remains reopened.
This worktree's historical `SCOUT_STATUS.md` does not authorize resuming old workers.

Checks: attached worktrees and parent status inspected; `git check-ignore
 data/evaluations/example/manifest.json` confirms runtime artifacts are ignored.
No experiment worker has started; actual spend and outstanding reservations: $0.
No evaluation spending envelope has been granted. The proposed $20 is not approval.

Scope: implement M0 tickets 1–4 in order, with offline tests, then prepare the
Housing launch gate. Later measured milestones and adoption remain evidence-gated.
Michael's latest instruction retains DeepSeek for this implementation; Claude's
provider/service-level alternatives are recorded recommendations, not production changes.

Next: ticket 1 — immutable protocol, read-only baseline export, original-input
checks, model-visible allowlist, CLI init/seal and synthetic tests.
