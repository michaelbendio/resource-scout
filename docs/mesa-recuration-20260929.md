# Mesa re-curation and review — September 29, 2026

Michael requested pausing Welfare Square and starting new Mesa curation and Codex
review after confirming the starter policy, four office-fit rules and consolidated
complementary-selection guidance. This supersedes the earlier Mesa launch hold.

## Inputs and scope

- Working run: `data/mesa-recuration-20260929/`, database import 4, prepared job 6.
- Source: a SQLite backup of `data/mesa-prepared-full-20260926-source-checks/research.sqlite3`.
  An immutable backup is retained in `source-snapshot/research.sqlite3` before
  the fresh job is created in the working copy. The original remains untouched.
- All completed research is included: 3,920 candidate/category entries across
  21 service categories. Overlap and marginal candidates are inputs to assess,
  not approved resources. No new broad discovery is launched.
- New assignments use `codex-preparation-v5-office-fit`. No previous reviewed
  context or prepared-resource collection is supplied as accepted curation input.
- Office category IDs were checked against `~/resource-assistant/mesa.html`.
  The review explicitly addresses Miscellaneous as the 22nd catalog category;
  it must justify an empty set if no assigned evidence supports suitable entries.
- The source manifest binds the database backup, office source and prior delivery.
  A separate preservation file carries identity aliases and seven existing human
  suppressions. Export refuses to resurrect a matched suppressed identity.
  A genuinely distinct program does not inherit an old bundled parent's suppression.

## Sequence and supervision

High Codex curation prepares batches of at most 30 candidates/60,000 characters.
It applies all four office-fit rules, consolidates appropriate agency/program
entries and records exclusions while preserving the research evidence. Targeted
official-source checks fill material gaps; this is not a new discovery run.

One sequential Extra High Codex review follows, with durable checkpoints and
bounded sessions. It reviews all dispositions, retained resources, identity,
taxonomy, 7–10 explained starters, selected ordered complements (including uncovered
Types), and usable reserves. Remaining candidates are not retained merely to fill
a quota. Complementary order is recorded in the review ledger/report; dedicated
JSON and WSRS-TSO support for that order remains pending.

The supervisor validates coverage, inputs, human-state preservation, schema and
export readback. The target is
`deliveries/mesa-recuration-20260929/scout-mesa-prepared-resources-<YYYY-MM-DD>.json`,
dated at generation, plus receipts, identity migration and readable reports/previews.
The old complete delivery remains on its acceptance hold until a replacement is
actually reviewed and delivered. No office approval, agency verification or app
import is implied. Registry commit and the final handoff gate remain required.

The dashboard uses port **8771**. Curation and pipeline supervisors preserve native
attempts and completed batches. Launch commands/PIDs, source hashes and authorization
are in the run directory; verify live state rather than relying on recorded PIDs.
The timing report distinguishes research already performed from this run's new
curation/review sessions; copied research telemetry is not a new research charge.
The pause/continuation and review-progress changes passed 778 tests (4 skipped).

The same dashboard is available through a separate listener on the Mac mini's
Tailscale address, recorded in the ignored run's `launch.json`. Both dashboard APIs
were verified without restarting curation. During review it shows saved category
checks for content, Types/groups and selections, plus collection-wide identity and
validation stages, current session and checkpoint time. These are reviewer-reported
checkpoints, separate from final delivery validation, with no invented percentage.

## Welfare Square pause

Welfare Square finished Housing and stopped at **13/21 categories**. Its existing
paid worker was adopted by a coordinator limited to that category boundary, so
no completed work was replayed. Its automatic review is stopped. Dashboard port
8770 shows the saved pause. Original manifests, category hashes and pause receipts
are under `data/welfare-square-fresh-20260928/pause-for-mesa-20260929/`.
Resuming requires Michael's instruction and restoration of the preserved full
category limit/continuation settings; restarting the limited finisher is not a resume.
