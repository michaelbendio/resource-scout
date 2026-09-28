# Increment 4: maintenance workflow

Status: implemented and software-tested on Scout `v2.0`. Michael authorized the
next increment after accepting the simplified navigation. Review of this
maintenance implementation and a real office pilot remain pending. No real
resource was rechecked, no consumer research service was called for the software
tests, and no production resource package was changed.

## What is usable

Open `/maintenance` in a running Scout server, or use `maintain` operator commands.
Start from an explicitly selected package, office identity, run name, and scope.
Select known resources to recheck and categories to search for additions separately.
The page shows completed/selected/office totals for both workstreams. A partial
run never implies that the whole office has been checked.

Each assignment freezes the package identity, target program or category, office
catalog, prior observations and identity history, writing guidance, policy, and
researcher roster. Primary research and reconciliation belong to Codex, with
ChatGPT, Grok, and Perplexity audits between them. Assignments are retrieved and
results submitted through the existing consumer-research boundary; provider
names do not mean Scout has subscription API access. Existing operator pacing
continues to apply. No scheduler or background research was started.

Completed results cannot be overwritten. Restarting retrieves matching sealed
assignments and skips completed stages. Audit findings require explicit
reconciliation, and unresolved material findings require a human resolution.
Prior checks remain dated history, not a new trusted baseline or human verification.

## Findings and review

Maintenance distinguishes current, changed, moved, renamed, paused, possibly
closed, reopened, inconclusive, identity/program-boundary problems, and new leads.
It records source dates, quoted evidence, the named program, follow-up questions,
last research attempt, last evidence supporting operation, and a suggested next
check. The existing human `verifiedOn` value is shown separately and never advanced.

Closure requires an explicit official-program-closure notice, a quote present in
the cited excerpt, and independent checks bound to the same program. A failed
contact route is not a closure notice. These structural checks do not establish
that a researcher's assertion is true: the reviewer can inspect original and
independent sources and retains the decision. The software does not invent a
human phone confirmation; an unresolved check stays open for human follow-up.

Review shows current/proposed fields, later office conflicts, local details,
independent evidence, and focused questions. Reviewers choose each changed field,
record their rationale and classification consequences, and resolve material
findings. Proposed classifications must use exact existing office terms. New
resources require a service category, Description, and all five Information
sections. No taxonomy term is created automatically.

New leads are matched against current identities, tombstones, and prior reviewed
maintenance identities. The ledger retains original program contact details so
closed records remain discoverable by identity evidence. Shared providers are
candidates for review, not proof that two programs are identical. A distinct
program requires an explicit human distinction; a direct retired-program match
or reopening claim cannot be exported as a new resource. Reopening a retired
record is handed back for office identity/deletion review, rather than bypassing
a tombstone. Current records that resume operation can be updated on their existing ID.

## Safe package delivery

Reconnect the latest office package before accepting or exporting changes.
Later same-field edits are shown as conflicts; unrelated current fields win.
A new connection invalidates earlier acceptance. Changed identity evidence,
removed taxonomy terms, deletion tags, and tombstones block unsafe updates while
leaving the findings available for review or decline.

Exports include the complete connected package, reviewed changes, history,
monotonic version/timestamps, and exact referenced PDFs. Review records, source
packages, assignments, and observations stay in Scout's durable event history.
A human retirement decision exports only a **pending resource deletion request**:
the resource remains in place for the ordinary location-app deletion review.
No maintenance export silently deletes or hides a resource.

Reviewed updates/additions can export while other tasks remain unfinished.
Repeated preparation returns the same bytes. Failed/canceled saves leave review
state available. With a file picker, Scout verifies saved bytes before marking
items saved. On iPad-style download browsers, the reviewer must explicitly confirm
the file exists in Files/Downloads; a download alone is not a successful-save
acknowledgment. Review changes reject stale acknowledgments. Subsequent exports
require reconnecting the current office package.

## Commands

```sh
python3 -m resource_research_agent --database data/research-agent.sqlite3 maintain prepare /path/to/current.zip --office 'Provo TSO' --run-name 'September food check' --resource-id RESOURCE_ID --category-id food
python3 -m resource_research_agent --database data/research-agent.sqlite3 maintain status PROJECT_ID
python3 -m resource_research_agent --database data/research-agent.sqlite3 maintain next PROJECT_ID --researcher Codex --task-id recheck:RESOURCE_ID
python3 -m resource_research_agent --database data/research-agent.sqlite3 maintain submit PROJECT_ID primary /path/to/result.json
python3 -m resource_research_agent --database data/research-agent.sqlite3 maintain connect PROJECT_ID /path/to/current.zip --office 'Provo TSO' --revision REVISION
python3 -m resource_research_agent --database data/research-agent.sqlite3 maintain review PROJECT_ID /path/to/review.json --revision REVISION
python3 -m resource_research_agent --database data/research-agent.sqlite3 maintain export PROJECT_ID /path/to/reviewed.zip --revision REVISION
```

Repeat `--resource-id` or `--category-id` for the selected scope. Either workstream
may run alone. Use `--historical` explicitly for an authorized historical pilot.
Use a new run name for a later recheck of the same package and scope. `events`
returns the durable research/review/export history. Review JSON uses `taskId`,
`itemId`, `decision`, `choices`, `reviewer`, `note`, optional `identityDecision`,
and `findingNotes`; the web page supplies those controls without requiring JSON.

## Verification and portable example

- Full Scout suite: 274 tests; 273 passed, one optional test skipped.
- 25 focused maintenance tests cover all operational outcomes, explicit closure
  evidence, program-boundary binding, identity and prior checks, later human edits,
  removed taxonomy terms, exact PDF/unknown-field preservation, no automatic human
  verification, separate coverage, restart, stale review/export, cancellation,
  repeated exports, HTTP endpoints, and CLI saved-byte verification.
- Disposable Chromium at 768 × 1024 and 390 × 844 exercises required human finding
  resolution, update/addition/retirement review, actual ZIP download, cancellation,
  retry with identical bytes, explicit save acknowledgment, and no page errors or
  horizontal overflow.
- The existing location reader (schema 3, checkout HEAD `199d146`) successfully
  merges the actual QA ZIP twice: ten resources, one pending retirement request,
  no actual deletions, unchanged human verification. This workflow does not depend
  on publishing the still-pending 3C location-app release.

`output/maintenance-qa-v3/` holds the synthetic source/database, pre-review
snapshot, ZIPs, screenshots, and verification JSON. Regenerate with
`scripts/maintenance_browser_qa.py --output FRESH_DIRECTORY` in an environment
with Playwright and Google Chrome. The read-only `autoScoutMaintenanceReview.html`
is generated by `scripts/maintenance_review_preview.py` from that explicitly
synthetic snapshot and copied to iCloud Documents/TSO for device review. It uses
invented programs and notices, not actual external AI research or human approval.
It does not expose an office package save action.

## Discuss before the next increment

Michael accepted the software demonstration and authorized the real maintenance
pilot on September 6, 2026. The [Provo Food pilot](scout-increment-4-pilot.md)
completed two Food-focused rechecks and one bounded addition search against the
previously authorized historical v41 package. All nine independent audits and
31 finding dispositions are recorded. Two updates and one addition await review;
no current production package was connected and no changes were exported.
Discuss the actual research, identity decisions, uncertainty, and review effort
before calling the real office workflow accepted.

The grand plan continues with increment 5: proposed method lessons from
attributable, human-vetted outcomes, kept inactive until its readiness/approval
gates are satisfied. Increment 6 later adapts category-specific run goals and
stopping points. Maintenance observations are provenance, not activated learning.
