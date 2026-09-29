# Codex instructions for Resource Scout

Before doing substantive Scout work, read `SCOUT_STATUS.md`.

**Office-fit rules (Michael, 28 September 2026: policy, "not an experiment").** Every
research, curation and review step keeps only resources that pass all four, and where
they conflict with older wording here or in other docs, the narrower reading wins:

1. **Reach from the office.** In person, in or reasonably reachable from the office's
   city or service area; a countywide or statewide front door passes; **phone and
   online services count**; a programme limited to another area's residents fails.
2. **Main service.** A category only for a resource's main service.
3. **Direct contact.** A person can contact or apply to it themselves; referral-only or
   already-enrolled programmes fail, so name the front door instead.
4. **One entry per agency**, unless its programmes differ in a way a client would notice.

The text is in `resource_research_agent/office_fit.py`; the reasons are in
[`docs/office-fit-rules-20260928.md`](docs/office-fit-rules-20260928.md).

For prepared-resource JSON delivery, follow
[`docs/scout-prepared-resources-contract.md`](docs/scout-prepared-resources-contract.md).
Michael's September 25 decisions require Stephanie's **five** Information sections,
reserve preparation of resources that pass the office-fit rules, 7–10 complementary starter choices with explanations,
and a consideration reason for every non-starter resource/category membership.
Michael's September 29 review instructions also require selecting and ordering
the strongest complements after the starters, explicitly considering uncovered
Types and other evidenced client benefits. Reassess gaps after each addition;
keep the remaining usable resources searchable. Follow the consolidated sequence
and safeguards in the prepared-resource contract. Complementary order is currently
recorded in the review ledger/report; its export/import support is still pending.
Review Types/groups across the collection, preserve human state, and use only
code-assigned registry IDs for delivery. Complete the data/fingerprint gates;
do not apply the legacy four-section/tier gate to JSON delivery. Existing sealed
HTML workbenches retain the legacy contract below. Any newly emitted HTML workbench
still requires its actual browser/editor/filter checks.

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

A requested legacy HTML post-curation review also requires reading and completing
[`docs/scout-workbench-readiness.md`](docs/scout-workbench-readiness.md).
Resource-content checks alone do not make the workbench ready: verify Stephanie's
four rendered Information sections, useful Category Types with complete assignments,
an evidenced For-group design with explicit no-group decisions, and per-category
AI-proposed human review priorities with reasons and resource evidence. Scout
checks completeness and staleness; the requested reviewer supplies the judgment.
Preserve human Curated status and keep priority separate from it; a resource that fails an office-fit rule is removed. Inspect the
actual browser filters and editor. Do not record completion merely to enable Save.
