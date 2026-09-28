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

## Ticket 1 — baseline and protocol complete

Added read-only WAL-aware baseline export, explicit original-package and primary
run/policy checks, immutable protocol verification, provider input allowlist,
path confinement and init/seal/status CLI. Original historical answers are held
in reviewer-only evidence; unknown model metadata needs a reason.
Checks: 7 protocol/baseline tests pass (including WAL, tampering, hidden canary,
original/current package mismatch, incompatible redaction, and symlink escape).
Config example and usage instructions are committed; examples contain synthetic
prices and no credentials. No live baseline or provider launch yet. Spend: $0.
Next: ticket 2, transactional reservations, native usage and resume accounting.

## Ticket 2 — transactional cost controls complete

Added durable per-attempt reservations, explicit stage/experiment/account
approval checks, conservative native-search generation bounds, exclusive cache
accounting, missing-usage holds, saved-response adoption, response/model metadata,
category call/time limits and diagnosed recovery controls. Unknown sent outcomes
cannot be automatically replayed or have their reservations released. Account
balance is never used to attribute unrelated account activity to this run.
A concurrency test exposed an immutable-file publication race; evidence writes
now publish complete bytes atomically and accept only identical competing writes.
Checks: all 16 baseline/protocol/ledger tests pass, including exact-cap races,
missing usage, changed rates, unknown tool charges and response adoption once.
No API calls; spend $0; no granted live envelope. Next: ticket 3 adapter and fake
native-search/fetch/resume tests. Live pricing and account identity remain preflight gates.

## Ticket 3 — evaluation-only DeepSeek adapter complete

Added Anthropic-format native search/public fetch loop, injected transport,
immutable requests/sanitized raw responses/source records, model allowlist,
search-limit handling, pause/one bounded length continuation, and resumable
response/tool adoption. Research requires successful native search evidence;
evidence-only contracts can complete without a new search. All outputs remain
non-importable. The production challenger module is imported only for its public
URL/parser/credential utilities; its orchestration/import functions are not invoked.
Explicitly closed SQLite connections after Python 3.14 exposed resource warnings.
Checks: 27 evaluation tests pass, including interruptions after response/fetch,
zero leads, prefatory commentary, model mismatch and uncertain paid timeouts.
Official API compatibility documentation checked; real pricing/billing bounds
and actual account authorization remain required before live use. API spend $0.
Next: ticket 4 scratch focused/gap execution and offline whole-category recovery.
