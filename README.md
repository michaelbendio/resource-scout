# Resource Scout — category research foundation

This is a standalone, local resource research workspace. Its default package-backed mode learns from a Resource Assistant `resource-package.zip` without changing that package: it discovers the schema and taxonomy, preserves complete imported records, and builds a known-resource index. Every discovered package category uses its Types, For groups, existing-resource context, and category-aware research guidance. The explicitly selected standalone-location mode remains Housing-only exploratory research for a place that does not yet have a resource package.

The app deliberately maintains separate bodies of data:

- **Imported knowledge** is an immutable snapshot of the package: all records are indexed for research context and duplicate detection.
- **Research work** contains candidates and review state. An imported resource is never inserted as a new discovery. A candidate with a strong package match is labeled `already-known` automatically.
- **Accepted resources** are persistent, reviewer-editable drafts associated with one package-backed research run. They are never written into the imported snapshot.

Standalone-location runs have no imported knowledge. Their candidates are not compared with the latest package, their location-specific lessons remain separate from package-backed lessons and other locations, and their review copies state that the research is exploratory rather than an official or comprehensive TSO Resources inventory.

The source ZIP is opened read-only. Browser uploads are written to a temporary file only long enough to read and hash them, then deleted. The app never produces a modified copy of that package. Its optional resource-package export is a new, lightweight additions package containing only resources marked **Ready for package**, their curator-attached PDFs, and the unchanged category and For definitions needed to merge them.

## Research connections

Hermes and DeepSeek Harness are connected through the same replaceable research-agent interface. The app owns the research brief, imported context, assignments, candidate records, duplicate decisions, review state, and lessons. The selected harness receives one bounded assignment and returns a structured research result. Switching harnesses does not move or migrate application data.

Category research runs as four persisted, category-specific stages. Candidates are saved after each completed stage rather than waiting for the entire assignment. If a later stage times out or fails, the run becomes **partial**: completed candidates remain reviewable and exportable, and **Resume research** retries only the unfinished stage before continuing.

**Recent runs** presents completed findings behind **Show full findings**, with one card per research stage. Inline `(1)`, `(2)`, and similar findings from older runs are rendered as numbered lists rather than a single paragraph. New stages return a short overview plus separate key findings, cautions, practical access steps, and gaps so the research remains scannable without changing or rerunning earlier results.

## Human-reviewed category playbooks

Every category in the current resource package has a specialized playbook in `resource_research_agent/playbook_library/`. Each category is one readable JSON file containing its assignment, what to include, what to exclude, verification questions, and four research stages. `base.json` holds the shared evidence rules, Stephanie's resource-gathering requirements, default service area, and the playbook-library version. Those shared requirements ask every category for consistent organization and contact details, services, eligibility, what to expect, the best way to connect, and additional practical notes. Category playbooks supplement rather than replace that common direction. The adjacent editing guide explains how a human can review and sharpen the guidance without changing Python code.

The library is validated when the application starts. Future or locally defined categories remain runnable through a conservative generated fallback until a reviewed category file is added. Every new run snapshots the playbook version and source, resolved assignment, inclusion and exclusion guidance, verification questions, and stage instructions; later edits therefore change future research without rewriting the record of earlier runs.

The workflow is:

1. Choose a Resource Assistant package. It connects automatically, and package-backed research remains selected by default.
2. Choose any category discovered in the package. Its existing resources, Types, and global For groups are included as research context.
3. If no package exists, explicitly select **Research a location without a package**, enter the location and optionally identify nearby areas whose services may realistically serve it.
4. Edit the assignment and select **Start research**. Runs continue in the background, with progress displayed for each bounded stage.
5. Use **View candidates** on a research run, or the inbox's run selector, to review that run separately. Open candidates as stages finish to inspect access, restrictions, availability, pet policy, lived-experience findings, evidence, unknowns, and follow-up branches. **All candidates** remains available for cross-run review. If a stage fails, review or export the completed work and use **Resume research** without repeating completed stages.
6. When a package-backed candidate resembles an imported resource, use the separate relationship panel to choose **Same resource**, **Same organization, different program**, **Related but distinct**, or **Not related**. The app explains the fields that triggered the comparison; the percentage remains supporting detail rather than the decision.
7. Independently choose **Accept**, **Research further**, **Already known**, **Wrong category**, or **Reject** for the candidate itself. In a package-backed run, **Accept** immediately creates a persistent TSO Resources draft. Open **View or edit generated TSO resource** to review its Name, contact fields, Hours, Description, Information, categories, category-specific Types, global For groups, and optional Verified month before export. Written feedback can become an active lesson included in later research runs for that category and context.
8. Choose **Export resource package** on that run whenever one or more candidates are ready. The cumulative ZIP always reflects the run's currently ready resources and saved edits. Rejecting or reclassifying a candidate removes it from the next export without deleting its retained draft.
9. Approve or retire agent-proposed lessons in the **Research lessons** panel.
10. Choose **Export Resource Curator** on any completed run to download the standalone Curator app. It opens directly in a browser without Scout or an agent connection. Its three movable, resizable windows keep candidate research, resource editing, and the curator's notes and clickable checklist visible together. Work is saved automatically in the browser and can be moved or backed up with a portable work file.

Both external harnesses are optional while exploring the app. Choose **Built-in demo** under **Research agent connection** to exercise the complete workflow without an account or model charge.

## Portable Resource Curator

Curators are generated only when a user clicks **Export Resource Curator** on a research run. The export always uses that associated run, regardless of which Candidate inbox is visible. Nothing is written to an export folder on the server. Each download is one self-contained HTML file with versioned JSON embedded inside it for future migration.

The export contains only the selected completed or partially completed run, stage status, its candidates, human review notes, editable resource drafts, run-specific lessons, the source taxonomy needed for valid package creation, limited source-package provenance, and the known-resource fields needed to explain duplicate signals. It excludes API keys, connection settings, raw agent output, the research database, source-package attachments, and full imported-resource records.

Curator progress is saved locally by the browser when available. Each candidate has its own notes and clickable checklist; changing candidates changes the Notes window to that candidate's work. **Save work** creates the portable JSON checkpoint used to pause, move, back up, or resume the work. It records every decision, curator note, checklist state, future-research flag, relationship assessment, resource draft, curator taxonomy edits, curator-attached PDF, stable ID, timestamp, and source-package identity. Scout does not consume this feedback yet. **Save a resource package** is separate: it is unavailable with no ready candidates, contains one resource when one is ready, and grows cumulatively as more are made ready. Standalone-location Curators can save work but cannot create a resource package.

The right-hand Resource Editors window has separate **Categories**, **Resource**, and **For** tabs. **Categories** can add Types within each category, while **For** can add global For groups. Curator is additive-only for governed taxonomy: Type and For-group deletion remains in TSO Resources. **Resource** edits contact and descriptive fields, composes formatted Information, assigns Categories and their Types, chooses For groups, and attaches PDFs. Only curator-added PDFs travel with portable work and ready-resource packages; the original source package remains untouched.

## Mergeable ready-resource packages

Resource-package export is available only for research runs that started from an imported TSO Resources package. It is scoped to the run whose **Export resource package** button is clicked; accepting candidates in a different run cannot affect it. Each download contains:

- the current schema and source package version;
- the imported definition for every category assigned during review, with the Curator's Type edits applied;
- the source package's For definitions with the Curator's edits applied;
- only the run's currently ready, curator-edited resources and their attached PDFs; and
- no imported baseline resources or assets, credentials, or research internals.

The downloaded ZIP is ready for an ordinary TSO Resources user to merge through **Merge Resources**. Resource Scout does not perform that merge. Repeated exports are cumulative snapshots, so a curator can stop, return later, prepare or edit more candidates, and download the latest ready set. Stable resource IDs allow TSO Resources' normal timestamp-aware merge to recognize a later corrected export of the same resource.

The candidate's service-need summary becomes the generated resource's Description. Contact details and Hours fill their matching fields; the remaining research details become formatted Information using TSO Resources' `* ` bullets, `**bold**`, `__underline__`, and `---` divider conventions. Verified remains blank unless a reviewer enters `MM/YY`. Agent suggestions preselect only Type and For labels that exist in the imported package; the human reviewer remains responsible for classification. Missing or renamed labels are reported for explicit mapping and are never silently changed.

Imports created before version 0.12 did not retain the package's top-level For definitions. Re-import the current source package once after upgrading to make its complete For list available; existing runs, candidates, reviews, and accepted-resource drafts remain in place.

### DeepSeek Harness developer preview

DeepSeek Harness is an experimental adapter pinned to `@deepseek-ai/dsh` version `0.1.0-rc.6`. Its runtime is isolated under `dsh-runtime/`, and its changing command-line details remain inside `DSHCLIAdapter`. Imported records, prompts, discoveries, and reviews do not depend on DSH data structures.

Install the pinned runtime once:

```sh
./install-dsh.sh
```

Start the app through the Keychain-aware launcher:

```sh
./run-dsh.sh
```

On macOS, the first launch securely prompts once to save the key in the user's Keychain; later launches retrieve it automatically. A `DEEPSEEK_API_KEY` already present in the environment takes precedence. On systems without the macOS `security` command, the launcher falls back to a hidden prompt for that launch. The key is never written to the app database or a project file. Select **DeepSeek Harness (experimental)** in **Research agent connection**, save, and the status card will show when it is ready.

The DSH research overlay gives DeepSeek a social-service resource researcher persona, exposes DeepSeek's server-side `web_search` tool, and disables shell, filesystem, editing, skill, workflow, and subagent tools. DSH also runs from an empty temporary working directory. `web_fetch` remains disabled in this first connection because DSH's own preview ships it disabled while its HTTP provider lacks a complete SSRF boundary.

### Hermes

To install Hermes using its supported macOS installer:

```sh
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
```

Then run `hermes setup` once to choose a provider and model. Resource Scout never stores provider credentials in its database. It discovers the `hermes` command automatically; an explicit command, profile, provider, or model override can be saved in the connection panel.

## Run the app

The core app requires Python 3.10 or newer and no third-party Python packages. The optional DSH connection additionally requires Node.js and the one-time `./install-dsh.sh` step above.

From a Git clone:

```sh
git clone https://github.com/michaelbendio/resource-scout.git
cd resource-scout
./run.sh
```

Or from the downloadable archive:

```sh
unzip resource-research-agent-v6.zip
cd resource-research-agent
./run.sh
```

Open <http://127.0.0.1:8765> and choose a `resource-package.zip`; it connects automatically. Stop the app with Control-C.

The research database is created at `data/research-agent.sqlite3`. It does not contain or modify the source ZIP.

## Private iPad access with Tailscale

For access away from the Mac's local network, install and connect [Tailscale](https://tailscale.com/download) on both the Mac and iPad. Then start the same Resource Scout data with:

```sh
./run-tailscale.sh
```

The launcher prints a private `https://…ts.net` iPad address and the app displays it in a **Private iPad access** panel. Open that address in Safari on an iPad connected to the same Tailscale network. The Mac must remain on and the launcher window must remain open; on macOS the launcher also prevents idle system sleep while it is running.

On the first run, Tailscale may print a web address asking the tailnet owner to approve HTTPS. Open it, approve Tailscale Serve, and run the launcher again. Resource Scout remains bound to `127.0.0.1`; Tailscale Serve is the only remote entry point. This launcher checks for and refuses an existing public Funnel configuration, and it never runs a Funnel command that would publish the app to the internet.

Normal Mac-only use is unchanged: `./run.sh` still serves only <http://127.0.0.1:8765>. If that launcher is already running, stop it with Control-C before starting `./run-tailscale.sh`.

For a reviewer outside the owner's tailnet, Tailscale supports sharing this Mac with a specific person. Apply a narrow Tailscale access policy so only the intended reviewer can reach it. The identity displayed by the app is informational; Tailscale's sharing and access policy are the security boundary.

## Keep the agent running in the background on macOS

The macOS background service starts the DeepSeek-and-Tailscale launcher when you sign in, keeps it running if it exits, and uses this clone's existing `data/research-agent.sqlite3`. Install it from the clone that should be the agent's permanent home. First run `./run-dsh.sh` once if the DeepSeek key has not already been saved in Keychain, then stop that foreground copy and install the service:

```sh
./background-service.sh install
```

The service does not need a Terminal window. The Mac must remain signed in, awake, online, and connected to Tailscale. Use these commands from the same clone when needed:

```sh
./background-service.sh status
./background-service.sh restart
./background-service.sh logs
./background-service.sh stop
./background-service.sh start
```

Use `restart` after updating the agent. `uninstall` removes only the macOS startup entry; it leaves the research database and log files in `data/` untouched. The private address remains the Mac's `https://…ts.net` Tailscale address. The agent continues to listen only on localhost, and the service never enables public Tailscale Funnel.

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
- which resources belong to each discovered category, including multi-category records.

The identity index uses available names, aliases, websites/domains, addresses, organization/provider/program fields, and conservative name variants. The match result explains its signals; it does not silently merge records.

## Test

```sh
python3 -m unittest discover -s tests -v
PROVO_RESOURCE_PACKAGE=/path/to/provo-resource-package.zip \
  python3 -m unittest discover -s tests -v
```

The live-package integration test verifies schema/category discovery and multi-category inclusion. The unit tests also prove that the source ZIP remains byte-for-byte unchanged, full records survive import, every discovered category can start research, category Types and For definitions survive import and export, imported resources remain separate from discoveries, non-selected resources still participate in duplicate checks, unsafe ZIP paths are rejected, Hermes and DSH one-shot results are normalized through the same adapter result, editable Curators keep notes separate by candidate, and ready-resource packages are openable, cumulative, run-scoped, editable, multi-category, and capable of carrying curator-attached PDFs.
