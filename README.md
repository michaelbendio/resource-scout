# Resource Research Agent — category research foundation

This is a standalone, local resource research workspace. Its default package-backed mode learns from a Resource Assistant `resource-package.zip` without changing that package: it discovers the schema and taxonomy, preserves complete imported records, builds a known-resource index, and exposes existing records in the selected category as research seeds. Housing, Food, and Employment have research playbooks now; every other package category is shown but disabled until its playbook is designed. The explicitly selected standalone-location mode remains Housing-only exploratory research for a place that does not yet have a resource package.

The app deliberately maintains separate bodies of data:

- **Imported knowledge** is an immutable snapshot of the package: all records are indexed for duplicate detection, and Housing, Food, or Employment records become seeds when that category is selected.
- **Research work** contains candidates and review state. An imported seed is never inserted as a new discovery. A candidate with a strong package match is labeled `already-known` automatically.
- **Accepted resources** are persistent, reviewer-editable drafts associated with one package-backed research run. They are never written into the imported snapshot.

Standalone-location runs have no imported knowledge. Their candidates are not compared with the latest package, their location-specific lessons remain separate from package-backed lessons and other locations, and their review copies state that the research is exploratory rather than an official or comprehensive TSO Resources inventory.

The source ZIP is opened read-only. Browser uploads are written to a temporary file only long enough to read and hash them, then deleted. The app never produces a modified copy of that package. Its optional resource-package export is a new, lightweight additions package containing only accepted resources and the unchanged category and For definitions needed to merge them.

Seeds open as readable profiles: category labels, contact details, description, safely rendered Markdown-style information, stored PDF attachments, verification metadata, and an optional raw-JSON view. Attachments referenced by supported-category seeds are copied into the separate research database so their links continue to work after the temporary upload is deleted.

## Research-agent connections

Hermes and DeepSeek Harness are connected through the same replaceable research-agent interface. The app owns the research brief, imported context, assignments, candidate records, duplicate decisions, review state, and lessons. The selected harness receives one bounded assignment and returns a structured research result. Switching harnesses does not move or migrate application data.

Broad assignments run as four persisted, category-specific stages. Candidates are saved after each completed stage rather than waiting for the entire assignment. If a later stage times out or fails, the run becomes **partial**: completed candidates remain reviewable and exportable, and **Resume research** retries only the unfinished stage before continuing. Focused research branching from one imported seed remains a single bounded stage.

The workflow is:

1. Import a Resource Assistant package. Package-backed research remains selected by default.
2. Choose Housing, Food, or Employment, then research the category broadly or branch from one of its existing seeds. The package's Types and global For groups are included in the research brief.
3. If no package exists, explicitly select **Research a location without a package**, enter the location and optionally identify nearby areas whose services may realistically serve it.
4. Edit the assignment and select **Start research**. Runs continue in the background, with progress displayed for each bounded stage.
5. Use **View candidates** on a research run, or the inbox's run selector, to review that run separately. Open candidates as stages finish to inspect access, restrictions, availability, pet policy, lived-experience findings, evidence, unknowns, and follow-up branches. **All candidates** remains available for cross-run review. If a stage fails, review or export the completed work and use **Resume research** without repeating completed stages.
6. When a package-backed candidate resembles an imported resource, use the separate relationship panel to choose **Same resource**, **Same organization, different program**, **Related but distinct**, or **Not related**. The app explains the fields that triggered the comparison; the percentage remains supporting detail rather than the decision.
7. Independently choose **Accept**, **Research further**, **Already known**, **Wrong category**, or **Reject** for the candidate itself. In a package-backed run, **Accept** immediately creates a persistent TSO Resources draft. Open **View or edit generated TSO resource** to review its Name, contact fields, Hours, Description, Information, categories, category-specific Types, global For groups, and optional Verified month before export. Written feedback can become an active lesson included in later research runs for that category and context.
8. Choose **Export resource package** on that run whenever one or more candidates are accepted. The cumulative ZIP always reflects the run's currently accepted resources and saved edits. Rejecting or reclassifying a candidate removes it from the next export without deleting its retained draft.
9. Approve or retire agent-proposed lessons in the **Research lessons** panel.
10. Choose **Export review copy** on any completed run to download a standalone, read-only HTML report. The file opens directly in a browser without this app or an agent connection and preserves the summary, assignment, research provenance, interactive candidate profiles, evidence links, candidate decisions, relationship assessments, lessons, and explained match evidence.

Both external harnesses are optional while exploring the app. Choose **Built-in demo** under **Research agent connection** to exercise the complete workflow without an account or model charge.

## Portable review copies

Review copies are generated only when a user clicks **Export review copy** on a research run. The export always uses that associated run, regardless of which Candidate inbox is visible. Nothing is written to an export folder on the server. Each download is one self-contained HTML file with versioned JSON embedded inside it for future migration.

The export contains only the selected completed or partially completed run, stage status, its candidates, human review notes, run-specific lessons, limited source-package provenance, and the known-resource fields needed to explain duplicate signals. It excludes API keys, connection settings, raw agent output, the research database, seed attachments, and full imported-resource records. The result is intentionally read-only: changes made later in the live Research Agent require a new export.

## Mergeable accepted-resource packages

Resource-package export is available only for research runs that started from an imported TSO Resources package. It is scoped to the run whose **Export resource package** button is clicked; accepting candidates in a different run cannot affect it. Each download contains:

- the current schema and source package version;
- the unchanged imported definitions for every category assigned during review;
- the source package's For definitions;
- only the run's currently accepted, reviewer-edited resources; and
- no imported baseline resources, PDFs, other attachments, credentials, or research internals.

The downloaded ZIP is ready for an ordinary TSO Resources user to merge through **Merge Resources**. The Research Agent does not perform that merge. Repeated exports are cumulative snapshots, so a reviewer can stop, return later, accept or edit more candidates, and download the latest set. Stable resource IDs allow TSO Resources' normal timestamp-aware merge to recognize a later corrected export of the same accepted resource.

The candidate's service-need summary becomes the generated resource's Description. Contact details and Hours fill their matching fields; the remaining research details become formatted Information using TSO Resources' `* ` bullets, `**bold**`, `__underline__`, and `---` divider conventions. Verified remains blank unless a reviewer enters `MM/YY`. Agent suggestions preselect only Type and For labels that exist in the imported package; the human reviewer remains responsible for classification. Missing or renamed labels are reported for explicit mapping and are never silently changed.

Imports created before version 0.12 did not retain the package's top-level For definitions. Re-import the current source package once after upgrading to make its complete For list available; existing runs, candidates, reviews, and accepted-resource drafts remain in place.

### DeepSeek Harness developer preview

DeepSeek Harness is an experimental adapter pinned to `@deepseek-ai/dsh` version `0.1.0-rc.6`. Its runtime is isolated under `dsh-runtime/`, and its changing command-line details remain inside `DSHCLIAdapter`. Imported records, prompts, discoveries, and reviews do not depend on DSH data structures.

Install the pinned runtime once:

```sh
./install-dsh.sh
```

Start the app through the key prompt:

```sh
./run-dsh.sh
```

The prompt does not display the key, pass it as a command-line argument, write it to the app database, or save it to a project file. The key exists only in the app process environment. Select **DeepSeek Harness (experimental)** in **Research agent connection**, save, and the status card will show when it is ready.

The DSH research overlay exposes DeepSeek's server-side `web_search` tool and disables shell, filesystem, editing, skill, workflow, and subagent tools. DSH also runs from an empty temporary working directory. `web_fetch` remains disabled in this first connection because DSH's own preview ships it disabled while its HTTP provider lacks a complete SSRF boundary.

### Hermes

To install Hermes using its supported macOS installer:

```sh
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
```

Then run `hermes setup` once to choose a provider and model. The Resource Research Agent never stores provider credentials in its database. It discovers the `hermes` command automatically; an explicit command, profile, provider, or model override can be saved in the connection panel.

## Run the app

The core app requires Python 3.10 or newer and no third-party Python packages. The optional DSH connection additionally requires Node.js and the one-time `./install-dsh.sh` step above.

From a Git clone:

```sh
git clone https://github.com/michaelbendio/resource-research-agent.git
cd resource-research-agent
./run.sh
```

Or from the downloadable archive:

```sh
unzip resource-research-agent-v6.zip
cd resource-research-agent
./run.sh
```

Open <http://127.0.0.1:8765>, choose a `resource-package.zip`, and select **Import package**. Stop the app with Control-C.

The research database is created at `data/research-agent.sqlite3`. It does not contain or modify the source ZIP.

## Private iPad access with Tailscale

For access away from the Mac's local network, install and connect [Tailscale](https://tailscale.com/download) on both the Mac and iPad. Then start the same Research Agent data with:

```sh
./run-tailscale.sh
```

The launcher prints a private `https://…ts.net` iPad address and the app displays it in a **Private iPad access** panel. Open that address in Safari on an iPad connected to the same Tailscale network. The Mac must remain on and the launcher window must remain open; on macOS the launcher also prevents idle system sleep while it is running.

On the first run, Tailscale may print a web address asking the tailnet owner to approve HTTPS. Open it, approve Tailscale Serve, and run the launcher again. The Research Agent remains bound to `127.0.0.1`; Tailscale Serve is the only remote entry point. This launcher checks for and refuses an existing public Funnel configuration, and it never runs a Funnel command that would publish the app to the internet.

Normal Mac-only use is unchanged: `./run.sh` still serves only <http://127.0.0.1:8765>. If that launcher is already running, stop it with Control-C before starting `./run-tailscale.sh`.

For a reviewer outside the owner's tailnet, Tailscale supports sharing this Mac with a specific person. Apply a narrow Tailscale access policy so only the intended reviewer can reach it. The identity displayed by the app is informational; Tailscale's sharing and access policy are the security boundary.

## Command line

Import a package and print a report:

```sh
python3 -m resource_research_agent --database data/research-agent.sqlite3 \
  import /path/to/provo-resource-package.zip --report import-report.json
```

Check a candidate against every imported resource (not only Housing):

```sh
python3 -m resource_research_agent --database data/research-agent.sqlite3 \
  match candidate.json
```

## What schema discovery supports

The importer searches JSON members inside the ZIP and scores resource-like collections rather than assuming a fixed filename. It recognizes common resource collection/category-definition names, nested package objects, explicit categories, and category IDs inferred from resource records. The initial Housing anchor can be resolved by category ID or label, including when the ID is not literally `housing`; the complete discovered taxonomy then drives category selection.

For each import it records:

- ZIP SHA-256 and member manifest;
- JSON member and discovered resource/category paths;
- package and schema versions where present;
- all category definitions;
- all complete resource records, including unknown extension fields;
- each category's concise Types, the package's global For definitions, and category resource counts;
- which resources belong to each supported category, including multi-category records.

The identity index uses available names, aliases, websites/domains, addresses, organization/provider/program fields, and conservative name variants. The match result explains its signals; it does not silently merge records.

## Test

```sh
python3 -m unittest discover -s tests -v
PROVO_RESOURCE_PACKAGE=/path/to/provo-resource-package.zip \
  python3 -m unittest discover -s tests -v
```

The live-package integration test verifies schema/category discovery and multi-category inclusion. The unit tests also prove that the source ZIP remains byte-for-byte unchanged, full records survive import, category Types and For definitions survive import and export, Food and Employment seeds remain separate from discoveries, unsupported categories cannot start runs, non-selected resources still participate in duplicate checks, unsafe ZIP paths are rejected, Hermes and DSH one-shot results are normalized through the same adapter result, and accepted-resource packages remain cumulative, run-scoped, editable, multi-category, additions-only, and asset-free.
