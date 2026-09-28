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

## Ticket 4 — M0 offline foundation complete

Implemented scratch-only original-policy execution, sequential focused passes and
one existing gap pass, CLI dry-run/explicit execute, Housing-only stage eligibility,
owned-path checks, and resumable whole-category output. Source/reference database
aliases, including hardlinks, are rejected. Original known-resource and policy
hashes are checked before dispatch; historical discoveries never enter exclusions.
Held outcomes preserve partial evidence. Late response adoption uses saved or
bounded request timing rather than counting the review pause as processing time.
Live execution additionally requires reviewer-frozen essential coverage criteria.

Checks: **43 evaluation tests pass**, including interrupted versus uninterrupted
whole-category results/charges, zero leads, invalid results, shared category caps,
draft-criteria rejection, and original-input reconstruction. **25 affected existing
tests pass** (`test_focused_research`, `test_codex_first_research`,
`test_worker_metrics`); local socket fixtures required running outside the sandbox.
`git diff --check` passes. No provider requests; actual spend/reservations **$0**.

Real offline preflight: `data/evaluations/mesa-housing-m0-preflight-20260927/`.
The earliest completed original Mesa Housing primary was selected before examining
its findings. The original ZIP was unavailable. An explicit reconstruction from
its preserved raw import rows matches the original canonical content hash; the
scratch original-known-resource manifest and five-focus policy independently match
the historical primary. ZIP container bytes differ and that limitation is recorded.
This is a justified original-input recovery, not a substitution of today's package.
Original records and hidden historical outputs remain in ignored local evidence.

**Not launchable:** that offline preflight freezes draft criteria, incomplete pricing
and the preceding code commit. It has no spending authorization. The proposed $20
total and $3 Housing cap remain proposals, not granted envelopes. No research quality
comparison, review, policy adoption or production change has been completed by M0.

**Next: ticket 5 / M1.** Resolve native-search/cache billing and usage conventions,
verify credential availability without exposing credentials, finish generic essential
coverage criteria, then seal a fresh Housing protocol at the committed code revision.
Prepare a concrete bounded launch for Michael's spending authorization; only then
execute and monitor Housing. Build the blinded audit and initial measured-research /
unmeasured-preparation projection. The exact gated execute command and reconstruction
configuration are in `docs/scout-evaluation-usage.md`. Later tickets remain evidence-gated.

## Housing launch authorized — September 27

Michael: "Run the test when you're ready. Take the $3 limit off first."
This supersedes the proposed Housing dollar ceiling. Authorization is limited to
the existing-policy Housing comparison, not later categories or production changes.
Explicit `none-authorized` dollar-cap mode retains the 60-call, 3,600-active-second,
24-turn and two-diagnosed-recovery limits. It may record unknown price/reservation
amounts as null; it cannot silently turn missing native billing details into zero.
Ordinary capped experiments still reject unpriced dispatch. Native-search/cache
billing is incompletely documented; raw usage is retained for later reconciliation.
44 evaluation tests pass, including removal of the dollar limit without removal of
the category call limit. The credential is available; no credential is in artifacts.
Next: seal the authorized protocol and execute the supervised Housing comparison.

## Ticket 5 — live comparison in progress; offline review tools available

Housing is running under Michael's explicit cap-removal authorization. The first
responses required source-appendix/fenced-JSON handling, recovered from immutable
responses without replay. Runtime amendments retain pre-recovery states and exact
code commits; the original sealed protocol is unchanged. Native max-uses errors
are evidence of a limited search, not successful extra searches.

Added offline `audit-packet`, `record-audit` and `report` commands, anonymous A/B
collections with separate reveal, dated essential-pathway judgment gates, actual
usage CSV/JSON and a projection that leaves later unmeasured stages explicit.
49 evaluation tests pass. Source review remains ongoing; no advancement or
complete Housing comparison is claimed by this tooling checkpoint.
