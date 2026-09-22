# Welfare Square handover — user-requested stop, September 22

Michael asked to stop at an appropriate checkpoint because about 25% of his
Codex allowance remained. **Do not restart until he asks to resume.** Earlier
permission to finish curation and review does not override this later stop.

## Stop boundary

The supervisor was terminated and coordinator suspended while Transportation
batch 10 finished, preventing batch 11 or another category from launching.
`data/welfare-square-curation-20260921/audit/stop-after-current-worker-20260922.py`
is the finite local shutdown helper, not an AI worker. Its final evidence is
`audit/user-requested-stop-20260922/stopped.json`. **Stop completed at 22:27 UTC.**
Batch 10 saved and validated with nine resources / ten candidate decisions;
batch 11 has no directory and was not launched. Coordinator 15292, supervisor
15296, worker 24798 and caffeinate 15293 are confirmed absent. No other curation
workers were found. The helper made no model calls. Original sealed inputs and
native output are preserved. No review-completion or human Curated flag is set.
Validated batch 10 SHA256:
`88efa21ff9cd759e221d33747f926fd3d81f5cfaa2f1cd79d9916684ffce2c8d`.
Final preservation passes 37 research tables and 121 reviewed original hashes:
`audit/research-preservation-20260922T222759Z.json`.

## Resume context

- Checkout `/Users/michaelbendio/resource-scout-pairwise`, branch
  `pairwise-research-experiment`. Preserve the unrelated tracked deletion of
  `docs/scout-discovery-and-maintenance-proposal-20260920.md`.
- Database: `data/welfare-square-production-20260921-codex-grok/research.sqlite3`,
  import 1 / curation job 1. Run directory:
  `data/welfare-square-curation-20260921/`.
- Research is 21/21. Curation is 18/21: Transportation assigned,
  Utilities/Phone/Internet and Veterans pending. Transportation has 11 batches.
- Native settings remain gpt-5.5, xhigh, 10 candidates / 25000 characters,
  compact prior index. Do not start new discovery, alternate paid reviewers,
  subagents or duplicate workers.
- Latest allowance reading after stop: **75% used / 25% remaining** at
  22:28 UTC; it is a snapshot, not a forecast.
- Monitor port 8770 is a separate local web process (PID 78304 at inspection),
  not the curation worker. Its presence does not mean curation is active.

When Michael resumes, read `AGENTS.md`, the current `SCOUT_STATUS.md` and
`docs/scout-orchestration.md`, then inspect actual processes, stop evidence and
database. Reuse the existing launch command and saved batch files; update the
launch manifest PID/status and supervisor attachment for the new coordinator.
The user-stop flags must only be superseded by his resume instruction. Existing
worker-recovery code accepts saved results without another paid generation.
Do not rerun applied revision scripts or already-run preparation scripts.

## Root review preserved

All 18 completed categories have applied content-review revisions. The latest
is Seniors: 72 resources / 94 decisions, hash
`d9763929335379b27d73b4cb494bf4554e88a79065138cc01fc61f0097cc5dce`.
Earlier category decisions and exact source obligations are in
`docs/welfare-square-review-checkpoint-20260922.md` and
`audit/cross-category-correction-obligations.json`.

Transportation batches **1–9** have prepared source corrections, not applied:
`audit/transportation-prepared-source-corrections-001.json` through `-009.json`.
They contain 67 per-batch field changes. Matching source folders and
`audit/content-checkpoints/transportation-batch-*.json` preserve evidence.
Batch 10 is the stopping boundary and has **not** received root content review;
batch 11 and the next two categories remain. Do not represent prepared work as
an applied category revision.

Selection must verify both category-hash references and
`preparedCorrectionPath`/`preparedCorrectionSha256` references. Batch 3 Family
Promise uses reviewed ID-only-exclusion evidence; batch 8 NEMT explicitly builds
on prepared batch 5. Reconcile repeated fields against the final native category
result instead of blindly overwriting it. Use the Mental Health selection/apply
pattern, with backup, expected hash, original hashes, candidate links and four
Information headings. Preserve each saved category copy's own factual details.

Main new findings: Molina's $75/$40 monthly allowances combine transportation
and OTC; Mercy's qualifying recurring trips are not excluded merely because
each trip is local; Miracle Flights has a separate all-age service-dog branch;
direct grants need appropriate Financial Assistance membership. Full shared
medical, survivor, housing, disability, aging, document and legal bodies were
restored in prepared copies. Preserve Ryan White's 500% case-management versus
250% core/support/ADAP limits, current INN referral contact, UTA rider-guide
booking/service limits and FAREPAY caps. DCFS coordinator rosters conflict by
page/purpose; retain both accurately. TURN's actual HTML posts a 15–20 year
DSPD employment waitlist. Native UOVC travel evidence includes its 2024 annual
report; root retrieval of that PDF failed, so retain that verification limitation.

## Remaining completion work

Finish content review and category selection, then global identity, duplicate,
alias and category-membership reconciliation. Complete evidenced Types, For
assignments or explicit no-group decisions, and per-membership priorities,
reasons and focused questions. Existing provisional ledgers are not final
certification. Follow `docs/scout-workbench-readiness.md`.

Perform actual final reader/editor/browser checks, including four sections,
Type OR / For AND and Match Any, priority versus alphabetical with identical
filtered resources, override/reload and no new human Curated marks. Preserve
other offices' browser-local edits. Only then record the exact reviewed
fingerprint and deliver an actual monitor Save/download; no office publication.

Browser note: dedicated browser APIs reported no browser. Native Safari works
through `cua.getApp('com.apple.Safari')`. A separate tab was opened at
`http://127.0.0.1:8770/`; it showed the initial connection view, not a verified
final Welfare workbench. Native Chrome returned a stale menu and no screenshot.
No other office tabs or stored edits were changed. No final usability or Save
check has been claimed.

Keep output and tool results small. Do not reread reviewed bodies without a
specific issue, dump source captures, or start another conversation against the
same running job. Use durable checkpoints for details.
