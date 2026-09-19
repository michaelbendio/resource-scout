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
September 19. For the currently authorized Children/Pregnancy curation, use bounded fresh contexts:
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
- Michael authorizes Extra High through Children/Pregnancy, followed by an
  effort discussion before another category. Use Extra High for the supervising
  comparison, difficult source/identity decisions and final consolidation audit.
  Worker effort is a separate decision; do not infer a blanket Extra High setting
  from the assistant effort setting. The already-running Addiction assignment completed at High;
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

**Current effort gate (latest instruction): finish Children/Pregnancy at Extra
High, then stop before assigning another category. Compare its original worker
results with original Addiction (High), including decisions, Stephanie's criteria,
latency and native usage/tool counts, and discuss effort with Michael. Do not
continue curation until that discussion produces a decision. This replaces the
earlier plan to wait for Mental Health/all 21 categories before comparing.** Report concrete gains and adverse
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

## Research-to-curation transition and saving

During validation, research completion must visibly say "Research complete —
ready to curate and consolidate" and pause for an effort discussion with Michael.
Only after Michael and the assistant agree Scout is ready for unattended operation
should a configured unattended run automatically start curation when research
finishes, using the agreed effort. Authorization to implement supervision is not
permission to enable that transition early. The current category has explicit
Extra High authorization, followed by the effort gate above.

Keep a prominent **Save auto[Location].html** action when the review file is
available. Reuse the existing review-file download endpoint; do not add a second
competing export or label AI proposals as human approved.

## Making judgment review independent of the conversation

The supervising assistant currently reviews saved category results, investigates
consequential concerns, applies evidence-backed revisions, and performs the final
cross-category consolidation audit. It does not participate in every internal
worker decision. Michael wants Extra High available at these judgment checkpoints;
that does not imply Extra High for every curation worker.

Michael's latest agreed workflow is **curation finishes → Ready for Codex review
→ Michael starts a Codex session and asks for review → assistant reviews at Extra
High and records completion → Michael clicks Save auto[Location].html**. Do not
automatically launch a paid reviewer. The following checklist governs the
assistant's requested review and any future independently approved implementation;
a longer curation prompt alone does not reproduce this review function:

1. Run deterministic coverage, link, provenance and checkpoint checks.
2. Give a bounded reviewer the sealed assignment, original proposals, omission
   reasons, prior-resource changes and explicit office/service area. Review
   questionable merges, consequential pathway omissions, category fit, geography,
   conflicting eligibility and Stephanie's four information needs.
3. Investigate flagged source conflicts with targeted checks. An out-of-state
   address or area code is a concern to resolve, not automatic exclusion of a
   legitimate statewide/remote/cross-border service. Failed fetches are not closure.
4. Record findings and any corrections with source evidence and before/after
   versions. Preserve unresolved uncertainty; do not silently make claims stronger.
5. Audit the final cross-category result for duplicate identities, lost program
   details and conflicting claims before declaring the review HTML ready.
6. Measure missed errors, false alarms, added usage and curator burden against
   known cases, including the Washington County Maryland/Utah error. Test recovery
   and spending limits separately from judgment quality.

This is an implementation/validation requirement, not an already running reviewer
or authorization for a new paid review worker before the current effort discussion.
Human approval and telephone verification remain separate. Proposed lessons from
AI reviews are not automatically accepted training examples or canonical facts.

## Recording the requested Codex review

Curation completion and local draft generation do not complete the Codex review.
The monitor and browser download endpoint require a recorded review of the exact
current result fingerprint. A source-backed revision changes that fingerprint
and makes Save unavailable until the changed results are reviewed again.

At the start of Michael's requested review, inspect the handoff and retain its
fingerprint:

```sh
python3 -m resource_research_agent.scout_review_handoff --database DATABASE --job-id JOB
```

Complete the actual review checklist above, retain original outputs and versioned
corrections, inspect the final HTML, and save a review report with findings,
corrections, verification and remaining uncertainty. After any reviewed revisions,
obtain the final fingerprint. Only after the review is actually complete, record:

```sh
python3 -m resource_research_agent.scout_review_handoff --database DATABASE --job-id JOB --complete --expected-fingerprint FINGERPRINT --report REPORT.md
```

This command records completed work; it does not perform a review. Never run it
merely to expose the Save button. It stores the report and its hash in durable
SQLite progress history. Tell Michael when Save is ready. Do not label Codex review
as human resource approval, phone verification or office publication.
