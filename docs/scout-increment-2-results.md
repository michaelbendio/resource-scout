# Increment 2 status and usage

September 5, 2026. The existing-resource update workflow is implemented on
`v2.0` and has passed software and browser checks. Michael explicitly authorized
the historical August 12 Provo package for a useful pilot. **The real four-AI
pilot is now researched and reconciled; Michael's review remains pending.**
Three Codex primary results, nine independent consumer-service audits, and three
Codex reconciliations are saved. No human acceptance or provider phone
verification is claimed. See [pilot results](scout-increment-2-pilot.md).

## What is implemented

Scout's home page now links to **Improve existing resources**. Select an office
package and a bounded resource scope. Scout saves the exact ZIP bytes and full
source records, referenced PDF hashes, writing guidance, researcher roster, and
stage instructions. Application HTML is rejected as package input. Historical
development projects are explicitly marked and remain historical projects even
if another package is connected later.

The default sequence for each selected resource is Codex primary research,
independent checks by ChatGPT, Grok, and Perplexity, and Codex reconciliation.
Each assignment and submitted response is sealed; retrying an identical result
is idempotent, while overwriting an earlier result is rejected. Assignments and
results survive restart and use the saved guidance. This implementation keeps
the existing consumer/operator delivery boundary: it generates assignments and
accepts completed results, but does not itself send prompts to consumer services
or introduce API access, change research pacing, or activate learned guidance.

The scope is Description and Information only. Proposed text follows the five
approved sections. Findings about contact fields or classification are retained
for review; this increment does not change those fields. Complete original
records, research evidence, named contacts, and PDFs remain available.

The review page displays current/proposed writing, original writing, readable
research findings and sources, original/current PDF links, editable proposed
sections, field choices, and Curated/decline controls. Nothing starts Curated.
Beginning an edit clears an existing Curated decision durably; unsaved edits
block export and navigation within the workflow. Failed/stale requests preserve
the previous saved record and explain that the reviewer must reload/reconcile.

Before accepting/exporting updates, reconnect the current office package.
Another office or an older package version is rejected. If a selected resource
is absent or has a deletion record/request, an update cannot recreate it.
Changes to the same writing field require a recorded review choice and note.
Material unresolved audit findings require explicit human resolution notes.
Later edits to other fields come from the latest record, not the old snapshot.
All-current/no-change selections are declined or left unmarked rather than
exported as fabricated updates.

Export creates a standard schema 3 ZIP containing selected updates, latest
taxonomy/history/deletion metadata, and exact referenced PDF bytes. IDs,
verification dates, unknown fields, and later contact edits survive. Only then
are update timestamps advanced; package version exceeds the connected versions
and earlier prepared exports. A separate durable manifest links source package,
latest package, assignment/result/proposal/review records, and exported IDs and
hashes. Research metadata does not leak into exported resource fields.

Prepared exports are byte-stable on retry. A successful file-picker write/close
is acknowledged before resources are hidden. With the ordinary browser-download
fallback, the review stays available until the reviewer clicks **Package saved
successfully**. Canceling, keeping the review, or failing a save leaves resources
available. Editing the proposal or reconnecting another package invalidates a
pending export acknowledgment. Another batch requires a fresh current-package
connection, preventing continued use of a silently aging snapshot.

## Validation completed

- Full suite: **206 tests run, 205 passed, one skipped**, in 20.716 seconds.
  The skipped test requires `PROVO_RESOURCE_PACKAGE`; a historical sample was
  not mislabeled as current to satisfy that test. The 13 focused improvement
  tests were rerun after final input-validation refinements and passed.
- Focused tests cover immutable inputs, restart, idempotence, result binding,
  mandatory independent checks, reconciliation completeness, human resolution,
  fresh-package gates, wrong-office/older packages, missing/deleted resources,
  same-field conflicts, later untouched-field edits, PDFs, history, unknown
  fields, review invalidation, stale revisions, cancellation, export retries,
  saved-state recovery, and the next-batch reconnection requirement.
- A real Chrome test exercised package intake/selection, research/review gates,
  current-package connection, keeping a newer office description, immediate
  acceptance invalidation on edit, canceled file picking, download retention,
  exact export retries, save acknowledgment, and reload. It verified PDF byte
  preservation and used the actual `resource-assistant/provo.html` package
  reader/merge in a disposable browser context. The unselected resource remained
  intact. No JavaScript errors occurred.
- Visually inspected the comparison page and print-media rendering. The print
  view uses the selected field choices and the same Information renderer as
  Scout's owned review template. Actual real-resource printed usefulness remains
  part of the pending human pilot; synthetic software checks do not establish it.
- Read the historical Provo v41 ZIP through the new snapshot reader: all 183
  resources and 93 referenced PDF assets validated. This was a read-only
  compatibility check, not fresh research or confirmation of the current office
  collection.

Generated QA artifacts remain local under `output/improvement-qa-final` and the
subsequent final UI check directory. They contain synthetic source/results and
simulated reviewer decisions explicitly labeled as QA. Source fixtures, the
browser checker, and unit tests are tracked in Git. No live office file, main
Scout database, or independent enrichment checkout was changed.

## Running the workflow

Run v2 with its own database and port, leaving the established service alone:

```sh
python3 -m resource_research_agent --database data/scout-v2.sqlite3 serve --port 8767
```

Open `http://127.0.0.1:8767/improvements` on the Mac. Use the existing private
Scout access setup when arranging iPad access; this change does not reconfigure
that setup or publish an endpoint. Review lives in this Scout server workflow,
not in a standalone iCloud HTML copy.

The `improve` CLI provides `prepare`, `status`, `next`, `submit`, `connect`,
`events`, and `export`. For example:

```sh
python3 -m resource_research_agent --database data/scout-v2.sqlite3 improve next 1
python3 -m resource_research_agent --database data/scout-v2.sqlite3 improve next 1 --researcher ChatGPT
python3 -m resource_research_agent --database data/scout-v2.sqlite3 improve next 1 --researcher ChatGPT --resource-id RESOURCE_ID
python3 -m resource_research_agent --database data/scout-v2.sqlite3 improve submit 1 audit:ChatGPT result.json
```

Use each subcommand's `--help` for arguments. `prepare` requires explicit office
identity and selected existing resource IDs. `connect` and `export` require the
current project revision shown by `status`; stale requests are rejected. Human
review occurs in the page. CLI export writes a new file, verifies its exact bytes,
then acknowledges success; it refuses to overwrite an existing output file.

The optional `next --resource-id` allows an operator to prepare several sealed
assignments for one consumer-service packet while an earlier assignment remains
pending. It cannot bypass primary/audit/reconciliation dependencies or expand
the project's selected resource scope. The pilot exposed this dispatch need;
14 focused improvement tests now pass, including out-of-order dispatch,
restart/idempotence and preservation of those gates.

To reproduce browser QA with Playwright installed in an isolated environment:

```sh
python scripts/check_improvement_workflow.py output/improvement-qa-new \
  --office-html /path/to/provo.html
```

Use a fresh output directory. The checker starts and stops its own local server
and uses a fresh browser context. Its synthetic responses are not independent
AI research and its reviewer name is not Michael's approval.

## Pilot baseline and next checkpoint

The newest nonempty Provo ZIP located locally is
`Downloads/provo-resource-package-4.zip`, version 41, created August 12, 2026,
SHA-256 `dc883d19eff7a30e78d33df580ea8408a50788eade33647c40ec6a23f0201a49`.
The other found packages are older versions 21/22 or an empty package. Michael
said, "It's not current but use it anyway. It will still be useful." That
authorization settled the pilot input. Its project remains historical, including
when the same historical ZIP is reconnected for comparison. This does not
establish that it is the current Provo office collection.

The local read-only review is `output/provo-improvement-pilot/autoProvoPilot.html`.
The durable project uses `output/provo-improvement-pilot/pilot.sqlite3`, project 1.
All resources remain unmarked; no office update package was exported. A current
office package and human decisions remain necessary before a production merge.

The grand plan remains writing, safe existing-resource improvements,
classification, maintenance, proposed research lessons, and adaptive research
runs. Finish the increment 2 pilot and discuss its review effort and preservation
of important details before starting increment 3's categories, Types, and groups.
