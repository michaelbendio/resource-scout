# Scout orchestration and supervision

This is the operating contract for the Codex assistant supervising Scout.
Read `AGENTS.md`, `SCOUT_STATUS.md`, and this file before starting, resuming,
changing, or supervising any Scout worker. User instructions override this file.
`SCOUT_STATUS.md` identifies the current database, phase, effort, processes and
pending work; verify those facts live. This document describes how to operate.

## Las Vegas automatic continuation authorized

Michael explicitly instructed: "When the research passes are done, start curation.
When curation is finished I am authorizing you to begin your review. Can you set
your effort to xhigh for review?"

For this Las Vegas Valley run, this supersedes the historical manual curation/review
start gates below. The persistent office pipeline waits for21 completed research
categories and finished research coordinators, starts supervised High curation in
30-candidate/60,000-character batches, then starts the requested gpt-5.5/xhigh review.
Exact configuration/authorization is data/las-vegas-production-20260923/pipeline.json.
This is not authorization to bypass completion/readiness checks or mark human
Curated approval. The review must cover content, navigation, For groups, priorities,
actual browser/editor/filter checks and download verification. Missing browser
capabilities must leave those checks visibly pending, not falsely passed.
The pipeline preserves native events and timing, allows bounded fresh review
sessions only with new durable progress, and stops on unknown launch/worker failures.
Other offices retain their existing authorization boundaries.

## Cedar City automatic continuation authorized

For the Cedar City run, Michael explicitly requested curation after research and
xhigh Codex review after curation. After an effort discussion, he confirmed
“High curation.” Effective sequence: Codex High/DeepSeek max research → High
curation → one sequential xhigh Codex review. This supersedes Cedar City’s initial
manual review handoff, not the evidence, browser, completion or Save requirements.
Exact authorization and the prior configuration are preserved under
`data/cedar-city-production-20260924/pipeline-authorization-change-001/`.
The current pipeline config sets `automaticReview:true` and retains bounded
sessions, durable progress checks and the final fingerprint gate.

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

## Research with challengers paused

When Michael authorizes only the remaining primary research, use the existing
pairwise runner with `--primary-only`, the original database/profile, and explicit
model/effort. This opt-in mode advances the primary across Categories, reuses
completed passes, includes each required gap pass, and stops when primary work is
exhausted. It neither checks challenger binaries nor probes or calls challengers.
It preserves the original roster and seals pending challenger assignments; those
Categories remain incomplete and unavailable for curation. The default mode stays
lock-step. `--max-categories` still counts fully completed pairwise Categories;
`--max-passes` bounds new primary passes within this invocation.

Inspect processes first and audit prior results afterward. A later normal-mode
resumption can complete pending challengers without rerunning the primary, but
requires separate authorization while the provider is paused. Do not mistake
primary completion for a switch to a single-provider research architecture.

For an authorized independent DeepSeek challenger, start the primary-only runner
with `--challenger-output-dir PATH`. The primary coordinator imports completed
challenger checkpoints before selecting its next pass, while retaining its one
canonical runner lock. The manifest must match the database/import/model and carry
authorization. No second writer bypasses that lock. The independent challenger
retains its lock-acquiring importer for the final tail after primary research exits.
Saved results may briefly await the current primary pass; they need not wait for
all Categories. Imported completion remains distinct from curation and review.

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
- **Grok usage balance exhausted (HTTP 402):** stop immediately and preserve the
  failed attempt. Do not retry the unchanged request. Resume with preflight only
  after Michael restores usage or explicitly authorizes a different architecture.
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

## Current authorization — September 19, 17:28 UTC

Michael has read the effort comparison and instructed "Continue curation" at
High. Resume the remaining 19 categories with `--effort high`, batches of at most
30 candidates / 60,000 candidate-view characters, and a completed-total category
limit of 21. Preserve both completed categories. This satisfies the historical
effort gate below; do not ask again. The final review remains a separate
Michael-requested Codex session, preferably Extra High.

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
- Information must render four distinct bold headings, with relevant paragraphs
  beneath them: **Eligibility Requirements**, **How to Best Connect**, **Access**,
  and **Important Information to Know**. Access must include the supported hours
  or availability limits. A keyword-presence check or inline colon labels are
  insufficient. Inspect the generated reader view and editor before handoff.
- Keep explicit candidate dispositions. Preserve distinct programs, merge aliases,
  and apply cross-category labels only for substantial direct services.
- Curation workers apply only supplied, evidenced For groups; they do not invent
  missing labels. After curation, the requested review must explicitly resolve
  missing Types and For groups under the [workbench readiness contract](scout-workbench-readiness.md).
  A blank starting taxonomy is unfinished work, not evidence that no groups are useful.
  Michael has authorized a corpus-derived St. George proposal for human vetting.
- AI-curated proposals are not human-approved or phone-vetted. Never automatically
  check the human Curated field to enable an export.

## Audit and delivery

Audit merges, consequential omissions, eligibility/access claims, geography and
cross-category consistency before presenting the final review file. Corrections
must preserve original results and record a reason, sources and before/after
hashes. Check whether in-flight or later categories reused a corrected resource.
Do not silently change research evidence or experimental results.

**Historical effort gate (now satisfied by the High resumption authorization above): finish Children/Pregnancy at Extra
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

For every new office run, explicitly establish `officeName` and `serviceArea`
before preparing assignments. A filename such as WelfareSquare is not an adequate
geographic definition. On September 21 Michael authorized Welfare Square with all
of Salt Lake County, Utah; see `docs/welfare-square-run-20260921.md`. This supersedes
the earlier instruction to defer that launch. Its automatic curation remains off.

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
permission to enable that transition early. The remaining curation categories now have explicit High authorization. The
comparison effort gate is satisfied; the unattended-operation agreement is separate.

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
   details and conflicting claims. Complete [workbench readiness](scout-workbench-readiness.md):
   four rendered Information sections with relevant text and hours/uncertainty;
   defined Types in every Category and supported assignments in every resource's
   Categories; defined For groups, supported assignments or explicit no-group
   decisions. Inspect the rendered reader/editor and combined Type/For filters.
   Propose the human review order within every Category at this same checkpoint:
   Start here, Important specialized help, Additional options, with concise reasons,
   supporting excerpts and useful unresolved questions. Record priorities through
   `scout_review_priorities.py` as required by workbench readiness. This judgment is
   supplied by the requested AI reviewer, not by Scout's deterministic orchestrator.
   Keep rare consequential pathways prominent; preserve all resources and human
   Curated status. Inspect local overrides and shared progress across Categories.
   A successful HTML build or occurrence of four keywords is insufficient.
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
current result and navigation fingerprint. Scout's versioned readiness gate blocks
completion when Information sections, Types, For-group review, or current
per-category review priorities are missing. Completion contract v3 requires the
priority proposal as well as the curation and navigation fingerprints.
Definitions/assignments changed after review invalidate the earlier approval;
legacy review records from before this contract cannot enable Save. A source-backed revision changes that fingerprint
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

## September 19 effort checkpoint reached

Children/Pregnancy has completed at Extra High; Addiction completed at High.
The requested comparison is in `docs/curation-effort-review-20260919.md`.
The runner stopped at 2/21 and the remaining 19 categories are pending. Do not
resume until Michael and the assistant agree on worker effort. The recommendation
is High workers with the current batching/checkpoints and Extra High for the
requested final Codex review. This supersedes the earlier wait-for-Mental-Health
comparison plan. No automatic reviewer is authorized by this recommendation.

The current runner automatically normalizes only fully identical resource rows,
retaining raw output and a normalization manifest. It does not choose between
conflicting same-ID records. The comparison also prompted explicit instructions
to actually incorporate supported access facts with candidate links when merging,
and to keep shared resource titles accurate for every retained category.


## Persistent curation supervisor and bounded recovery

`python3 -m resource_research_agent.curation_supervisor --launch-manifest PATH
--attach-pid PID --notify` attaches to an existing coordinator without starting a
second worker. Omit `--attach-pid` to resume the saved curation command. Use a
preserved launch manifest with explicit effort, output, database and total category
limit. Run from the repository root. A separate per-database supervisor lock
prevents duplicate supervisors; the runner retains its own exclusive lock.

The supervisor checks every 30 seconds, records native event age separately from
coordinator liveness, and persists its coordinator restart budget. On a coordinator
crash it can restart within that budget. The runner waits for an identified live
orphan before reading its result or starting work. Completed batches are validated
and reused. A confirmed transient transport failure allows one additional worker
attempt per batch in `transport-retry-1`, retaining every original artifact and
sealed input; restarting does not reset this budget. Timeout, authentication,
quota, context and content/validation failures require diagnosis and do not trigger
an unchanged automatic paid retry. The sole automatic content normalization remains
removal of fully identical resource rows.

`supervisor-status.json` records current state and recovery counts. Terminal states
are also visible through the existing monitor; `--notify` requests a local macOS
notification at completion or a stop requiring attention, subject to macOS
notification settings. No provider messages or automatic final AI review are sent.
An assistant must still resolve substantive curation failures. This is not a claim
that all unattended-recovery requirements have been completed: automatic context
resizing, semantic-result repair and OS-reboot recovery remain unimplemented.

New evidence JSON is written over multiple lines so a line search does not return
an entire minified document. Resumption accepts the prior representation only when
its parsed value still matches the sealed assignment, and never rewrites its bytes.


## Structural self-correction after the Education stop

Michael explicitly asked to fix the worker workflow that produced the Education
placeholder. After a result fails validation, Scout now allows one additional
Codex correction attempt for that sealed batch/result at the configured effort
(currently High), with web search disabled and a 600-second maximum. This is
curation output correction, not the separately requested final Codex review.

The `structural-repair-1` directory retains the original output, exact validation
error, prompt, native events and proposed correction. Code permits only candidate /
resource link reconciliation using associations asserted on at least one side of
the original output. It forbids changed facts, IDs, curation decisions, omission
reasons or candidate coverage. A non-resource placeholder may be removed only
under the explicit marker, unreferenced-row, matching-program and retained-candidate
checks in `curation_result_repair.py`. A failed or unsafe correction stops; a
restart does not grant another paid attempt. Both structural checks and full
curation validation must pass before completion. Ordinary valid results cost no
additional worker call.

For a supervising assistant's evidence-backed correction, `reviewed-result-repair.json`
records the original byte hash, corrected result/hash, reviewer, timestamp, reason
and evidence. The loader rejects a changed original, a hash mismatch or a changed
sealed assignment/category identity; it still runs all normal validation. This
supports repair of unfinished batches without overwriting native output. Completed
category corrections continue to use `scout_curation_result_revisions`.

The Education batch-3 correction removed only `res-duplicate-placeholder-remove`;
all 30 decisions and the actual SUU tutoring entry were unchanged. It used no new
AI call. Its audit record is `audit/education-batch3-placeholder-repair.json` under
the curation output directory. The five completed category hashes were captured
before resumption. This fixes the observed defect but does not guarantee that every
future content error is structurally repairable.

Stopped curation now has a prominent stopped headline and correction-needed panel.
The supervisor retains the active category in its terminal event. Notification
requests record success/failure details and explicitly do not claim the user saw
a notification; macOS notification delivery remains outside Scout's control.


## Where AI participates in this run

Michael reaffirmed the separate post-curation review on September 19 evening.
Research uses Codex primary plus Grok challenger. Curation uses fresh Codex High
workers for the saved batches: candidate decisions, source checks, resource text,
alias merging and reuse of prior program IDs happen there. Deterministic code
validates each output, combines batches and persists category completion. The
supervisor itself is ordinary code, with no general AI judgment. A failed
structural validation can invoke the single constrained High correction described
above; a valid result does not incur another AI call. This remains distinct from
Michael later asking a Codex assistant to conduct the broader post-curation review
at Extra High, including substantive decisions and cross-category consistency.
