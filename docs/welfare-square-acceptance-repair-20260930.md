# Welfare Square acceptance audit and assembly repair

On September 30 Michael reported that the dashboard needed attention. Native
session 054 had exited successfully at the intentionally required assistant
acceptance gate. Its submitted output had not been exported. The pipeline retained
an obsolete context-exhaustion reason from an earlier recovery.

The supervising assistant rejected the submission after inspecting category
judgments, selection ledgers, the compiler and actual payload:

- All eight name/description/contact/Information fields were unchanged across
  all 1,124 retained resources, despite individually recorded corrections. Examples
  include the Steps Murray and Taylorsville CTC contact decisions in Addiction
  checkpoint 004; their requested changes did not reach the payload.
- The compiler used raw suggested Types/groups instead of the consolidated
  category taxonomy: 991 Types, 763 groups, including 50 Housing Types.
- 865 of 1,089 non-starter considerations came from generic fallback templates.
- The compiler loaded only `candidateReviews`, ignoring `candidateReview` in
  35 checkpoint files and `candidateReviewNotes` in 16. Fallback to original
  curation dispositions is not independent review.
- Generic identity decisions and relabeling duplicates to avoid established-ID
  conflicts require explicit reconciliation and any necessary migration plan.

Structural validators had passed. These findings demonstrate why structural
coverage and fingerprints do not substitute for acceptance of the actual content.
The saved individual review remains useful; the repair must apply and reconcile it,
not repeat broad research or discard completed work.

## Bounded continuation

The rejected bundle, content freeze, category files, compiler, reports and runtime
configuration were copied with SHA-256 evidence under the run's
`supervisor-acceptance-repair-20260930T082830Z/` directory. No registry mutation,
export, WSRS-TSO import or approval was performed in this audit.

Session 055 continues the same single sequential Extra High review. Mandatory
`review/ASSEMBLY_REPAIR_INSTRUCTIONS.md` requires per-category structured
finalization, explicit disposition of every suggested correction, normalized
taxonomy assignments/evidence, authored consideration reasons, collection fact and
identity reconciliation, and an assembly audit comparing output to actual decisions.
Missing decisions must stop compilation rather than generate reassuring defaults.
The worker must return to the supervising assistant for substantive acceptance;
the run-specific wrapper continues to block automatic export.

The finite total session ceiling is 90 instead of 64, preserving 54 consumed
sessions. This allowance covers the newly diagnosed repair work; context/transport
retry budgets are unchanged. Recovery monitoring was attached after verifying the
pipeline and reviewer were live. The initial monitor exited before the pipeline
PID was recorded; its status is preserved and only that monitor was restarted.

The pipeline code now clears obsolete reasons at phase changes and uses the current
review checkpoint summary at handoff. Regression coverage exercises a previously
failed pipeline progressing to a new reviewer checkpoint. Live progress remains on
port 8770. Mesa's independent work and shared-registry changes remain untouched.

Validation: 796 tests ran successfully (4 skipped). The live dashboard API reports
`review` and the assembly-repair summary; the recovery monitor reports `monitoring`,
and session 055 is producing native events. This verifies continuation, not final
acceptance or delivery readiness.
