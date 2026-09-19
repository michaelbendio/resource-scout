# Scout orchestration and supervision

This is the operating contract for the Codex assistant supervising Scout.
Read `AGENTS.md`, `SCOUT_STATUS.md`, and this file before starting, resuming,
changing, or supervising any Scout worker. User instructions override this file.
`SCOUT_STATUS.md` identifies the current database, phase, effort, processes and
pending work; verify those facts live. This document describes how to operate.

## Own the run

Michael should not have to watch the monitor, discover a stopped worker, or
perform routine recovery. The supervising assistant owns that work.

- Inspect actual worker processes, SQLite state, the latest runner log and native
  worker events before launch. A browser monitor is not a research/curation worker.
- Hold the database runner lock. Never launch a duplicate coordinator or worker.
- While supervising, check liveness and new error/completion events at least once
  per minute, including while coding or auditing another result. Check immediately
  after a launch or transition. A heartbeat says the coordinator is alive; it
  does not prove a model has made new progress.
- Report each category completion and material failure/recovery. Give concise
  progress updates during long work without asking Michael to monitor for you.
- Continue through the authorized deliverable, including validation and audits;
  starting a background process alone is not completion.
- Do not promise monitoring after the assistant turn ends unless a persistent
  supervisor actually performs it. If work must be handed off, record the live
  state and remaining responsibility candidly.

## Preserve completed work

Keep the completed six-category experiment databases, earlier baseline, frozen
research snapshot and original worker outputs intact. Use the designated working
database for curation. Never restart completed research or completed categories.

Seal assignments and preserve their hashes, original source submissions, output,
native event stream, effort/model, timing and failure details. A retry or changed
assignment gets a distinct durable attempt record; never overwrite a failed
attempt to make the history appear clean. Reuse validated saved results without
another model call. Resume-safe limits mean completed categories total.

## Size and checkpoint curation

Research and curation are different workloads. The old Grok recursive research
partitioning was reverted after authentication was shown to cause those stalls.
Do not restore it merely because a worker is slow.

Children/Pregnancy curation actually exhausted the model context window on
September 19. For the remaining current curation, use bounded fresh contexts:
`--batch-candidates 30 --batch-chars 60000 --effort xhigh`. These limits bound the
submitted candidate evidence, not a guarantee about all future tool output.
Avoid dumping full provenance files or long webpages into context.

Persist every batch result and its validated form. Give later batches the prior
resource identities and access to their complete records. Merge the batch results
into one normal category result, checking every candidate's disposition and exact
resource links before saving it. Only then advance the category count. Preserve
already-completed batches if a later batch fails. Do not trade away evidence or
silently omit candidates to fit a context window.

## Diagnose and recover

Read the native error before deciding on recovery. Never treat every timeout as
an inference, model-quality or task-size failure.

- **Context exhaustion:** preserve the attempt and completed batches. Reduce the
  remaining batch/evidence size or use bounded evidence reads. Resume only the
  incomplete work; do not resend the same oversized prompt unchanged.
- **JSON/schema/link failure:** preserve the output. Diagnose the exact missing,
  inconsistent or invalid fields. Repair the bounded result with the evidence
  already collected; do not restart discovery or omit inconvenient candidates.
- **Authentication or credential lock:** verify actual authentication state and
  the sandbox/credential interaction. Use authorized local recovery where
  possible. Do not route to another paid provider or repeatedly retry unchanged.
- **Transient transport/service error:** a bounded retry may be appropriate after
  inspecting the evidence; preserve each attempt and cap retries. Stop escalating
  repeated identical failures into more unattended spending.
- **Timeout/no recent model events:** inspect liveness, completed tool activity,
  output generation, authentication and native logs. Coordinator heartbeats alone
  are insufficient evidence of useful progress. Preserve artifacts on termination.
- **Code/monitor defect:** fix and test it. Restart only the process that must load
  the change. A monitor restart must not restart research or curation.

Do not reduce an explicitly requested effort setting to escape an error.
Escalate to Michael only when action or a decision is genuinely required from him
(for example, an interactive account login, exhausted usage, or a new spend/scope
choice). Explain the concrete blocker and what was already preserved or tried.
Routine investigation and repair belong to the assistant.

## Current worker and review policy

- Claude is disabled for every Scout call, including probes, preflight and
  fallback. Reading historical Claude evidence is allowed.
- Michael requested Extra High for current category curation workers and the
  supervising audit. The already-running Addiction assignment completed at High;
  preserve that original for comparison. The conversation effort and CLI worker
  effort are separate; verify the actual CLI argument/metadata.
- Address Stephanie's four needs: eligibility, how best to connect, access/hours,
  and important information. Verify direct service, identity and geography;
  unfamiliar laws, area codes or addresses are conflicts to resolve, not typos to
  explain away. A failed fetch does not establish closure.
- Keep explicit candidate dispositions. Preserve distinct programs, merge aliases,
  and apply cross-category labels only for substantial direct services.
- Apply only existing, evidenced For groups. Do not create or suggest missing ones.
- AI-curated proposals are not human-approved or phone-vetted. Never automatically
  check the human Curated field to enable an export.

## Audit and delivery

Audit merges, consequential omissions, eligibility/access claims, geography and
cross-category consistency before presenting the final review file. Corrections
must preserve original results and record a reason, sources and before/after
hashes. Check whether in-flight or later categories reused a corrected resource.
Do not silently change research evidence or experimental results.

After all 21 categories complete, compare original Addiction (High) with Mental
Health (Extra High), including overlapping providers, decisions, Stephanie's
criteria, latency and native usage/tool counts. Report concrete gains and adverse
cases. Source pools, order and prior curated context differ; this is observational,
not a causal effort experiment. Also record the curation batching/prompt change.

Verify candidate coverage, final identities, output integrity and the review UI.
Deliver `autoStGeorge.html`, audit findings and the effort comparison. Do not
publish an office package or start another city without authorization. Update
`SCOUT_STATUS.md`; commit/push tested code and handoff changes on the current
branch, excluding unrelated files.

For a later Welfare Square run, explicitly establish `officeName` and
`serviceArea` before preparing assignments. A filename such as WelfareSquare is
not an adequate geographic definition. Do not launch that run now.

## Authorized next implementation: unattended shell operation

Michael explicitly approved the work required to reach this state on September
19. It is now a deliverable alongside completing St. George curation, its final
audit, review HTML and the requested effort comparison. Preserve live work while
implementing it. Build persistent supervision and structured failure reporting,
durable recovery of incomplete batches, bounded evidence-preserving retries,
and actionable account/usage alerts. Test interrupted workers, context limits,
invalid results, transient failures, exhausted recovery budgets and resumed
completion. State what still requires human action. Do not equate a background
worker, monitor heartbeat or untested retry loop with unattended reliability.
