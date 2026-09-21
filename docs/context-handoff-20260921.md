# Scout context handoff — September 21, 2026

Verified live at **20:04 UTC / 14:04 MDT**. This is a conversation handoff, not an
instruction to launch workers or prepare a new editor export.

## Start here

- Checkout: `/Users/michaelbendio/resource-scout-pairwise`.
- Branch: `pairwise-research-experiment`.
- Read `AGENTS.md`, the newest entries in `SCOUT_STATUS.md`, and
  `docs/scout-orchestration.md` before operating workers.
- Recheck processes, database, and git status. A monitor is not a research worker.
- All requested work from the preceding context is complete. **Keep research and
  curation paused until Michael chooses the next step.** No scheduled restart exists.

## Welfare Square: primary complete, challengers paused

Database (import 1):
`data/welfare-square-production-20260921-codex-grok/research.sqlite3`.
Office: Welfare Square. Service area: **all of Salt Lake County, Utah**, including
statewide/remote programs demonstrably serving county residents.

Live verification: **21/21 Codex primary Categories; 112 saved primary passes**.
**16/21 Categories fully researched**. Five sealed Grok challengers remain assigned:
Mental Health; Seniors; Transportation; Utilities, Phone, Internet; Veterans.
There are **zero curation jobs and zero research coordinators**. SQLite quick_check
is OK. Runtime `launch.json` says `paused-by-user` and automatic restart is off.

Monitor: **http://127.0.0.1:8770**, responding at handoff (last monitor PID 70753).
Its full-research count of 16 is correct; it cannot count pending challengers as
complete. An assigned challenger is durable pending work, not proof of a live worker.

The latest bounded run completed 21 new passes across the final four Categories,
using **gpt-5.5 / High**, with no failures, retries, Grok calls, or Claude calls.
All 91 preceding primary passes, 16 saved challenger results and 16 completed jobs
were verified unchanged. See `docs/welfare-square-all-primary-20260921.json`.
Backup, before snapshot, launch command and verification are under
`data/welfare-square-production-20260921-codex-grok/remaining-primary-only-20260921/`.

The implemented `pairwise_runner --primary-only` mode skips challenger binaries,
probes and calls; reuses completed passes; advances primary work across Categories;
and includes gap passes. It preserves the roster and pending challengers. Normal
mode remains lock-step. **Do not blindly rerun `launch.json`'s original command**:
it invokes Grok. All primary work is now complete, so another primary-only launch
would have no useful work. No duplicate or replacement database is needed.

## Next decision belongs to Michael

Discuss what to do with the five remaining challengers: resume Grok when he chooses,
or design/test a Codex alternative if he authorizes it. He reported exhausted Grok
usage, declined more spending, and mentioned Wednesday afternoon, September 23.
That is not approval for a scheduled restart. His interest in “all-Codex all the
time” is not yet an approved architecture change. Preserve the 16 Grok results and
all 21 primary results when considering alternatives; do not silently close pending
Categories, change their sealed rosters, or rerun completed research.

Claude remains disabled for all calls, probes and fallback due unexpected charges.
Bonsai was removed at Michael's request; structured extraction is deferred, not a
next task. Automatic curation remains off. Discuss curation effort before starting.
Curation uses explicit AI workers; a later requested post-curation Codex review is
a separate step. Never equate AI output with human Curated approval.

Historical six-category experiment and St. George analysis/run requests are already
past work. Do not restart those experiments or recreate their databases.

## Workbench Help and controls: delivered

Scout **0.51.1, build 20**. Updated current copies in place:

| File | Embedded resources |
| --- | ---: |
| `/Users/michaelbendio/Documents/TSO/autoMesa.html` | 268 |
| `/Users/michaelbendio/Documents/TSO/autoProvo.html` | 211 |
| `/Users/michaelbendio/Downloads/autoStGeorge.html` | 879 |
| `data/st-george-curation-20260919/autoStGeorge.html` | 879 |

All four files still match the final upgrade audit at this handoff. Their embedded
resource seeds and metadata/storage/artifact identifiers were preserved exactly.
Provo's embedded PDF script and Mesa/Provo's unresolved-question editor were kept.
Browser-local curation edits are separate from the embedded HTML: do not overwrite
or reset them, and do not claim an HTML seed contains later browser edits. No human
Curated marks were made during our verification. Backups and merged legacy runtime:
`data/workbench-help-controls-20260921/`. Manifest:
`docs/workbench-help-controls-20260921.json`.

Changes include curation-specific Help/Admin Help, Match all/Match any examples
using each file's own group labels, Stephanie's four Information headings,
handout-printing advice, batch export guidance, and a printable **Curate your first
resource** walkthrough (verified as one Letter page). Mesa/Provo also gained current
group matching/review controls. Their existing group names and resource assignments
were preserved; missing group confirmations were not fabricated. Priority controls
require an existing priority proposal; no new ranking was invented.

**Michael's final correction:** only Help and the red hint explain entering Admin.
`Ctrl+Alt+A` (`Control+Option+A` on Mac) reveals the Admin entry; then click **Admin →
Admin Help**. Admin Help assumes the user is already there. The walkthrough says
“Open Resources, select that resource, and click Edit.” No personalized wording for
Matt. Print the resource to assess its suitability as a handout.

The Scout template applies this help to future auto[Location] files, including
Welfare Square after its later curation/review. Older archived pilots and obsolete
duplicate downloads were not changed. Do not replace current Mesa/Provo with a plain
template regeneration: preserve their question-editor extensions and attachment
scripts. Save any open edits before reloading an existing browser tab.

St. George remains complete and reviewed: monitor **http://127.0.0.1:8769** (last PID
70750), Save endpoint verified serving the updated help with 879 resources and the
review gate satisfied. No new content review is pending from this interface update.

## Verification and git

- Full suite: 267 tests passed, one optional skip; GitHub CI passed.
- Nine persistence/control checks also passed using the merged legacy interface.
- Safari verified Help, Admin Help, shortcut, question editor, group review, and
  printing. Mesa Disabled + Youth returned 6 with Match all versus 69 with Match any.
- Relevant pushed commits: `381e172` primary-only mode; `e375e06` Help/control update
  and active-primary monitor correction; `9c3ca23` Admin Help correction; `9eff190`
  completed-primary pause record. This handoff adds documentation only.
- Existing unrelated worktree deletion:
  `docs/scout-discovery-and-maintenance-proposal-20260920.md`.
  **Do not restore, stage, or commit that deletion as part of routine Scout work.**
- Preserve completed historical experiment and St. George databases. Use read-only
  SQLite for inspection; constructing ResearchStore may perform migrations.
