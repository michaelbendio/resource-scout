# Codex instructions for Resource Scout

Before doing substantive Scout work, read `SCOUT_STATUS.md`.

Before starting, resuming, changing, or supervising a Scout worker, also read
[`docs/scout-orchestration.md`](docs/scout-orchestration.md) and follow its
monitoring, checkpoint, recovery, evidence-preservation, and handoff instructions.
The supervising assistant owns routine monitoring and recovery; Michael should
not have to babysit the run.

Treat `SCOUT_STATUS.md` as the current operational handoff. Verify live process/database state before acting because long-running experiments may have advanced since the file was last updated.

For the final six-category architecture analysis, use **Extra High reasoning effort** and follow the evaluation checklist in `SCOUT_STATUS.md`.

Do not launch the full 21-category St. George production run until that architecture review is complete.

When curation finishes, hand off as **Ready for Codex review**. Michael starts a
Codex session to request that review. Follow the review checklist and completion
recording instructions in `docs/scout-orchestration.md`; do not automatically
launch a paid review worker or mark a review complete just to enable Save.

A requested post-curation review also requires reading and completing
[`docs/scout-workbench-readiness.md`](docs/scout-workbench-readiness.md).
Resource-content checks alone do not make the workbench ready: verify Stephanie's
four rendered Information sections, useful Category Types with complete assignments,
and an evidenced For-group design with explicit no-group decisions. Inspect the
actual browser filters and editor. Do not record completion merely to enable Save.
