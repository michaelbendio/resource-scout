# Resource Scout — category research foundation

This is a standalone, local resource research workspace. Its default package-backed mode learns from a Resource Assistant `resource-package.zip` without changing that package: it discovers the schema and taxonomy, preserves complete imported records, and builds a known-resource index. Every discovered package category uses its Types, For groups, existing-resource context, and category-aware research guidance. The explicitly selected standalone-location mode remains Housing-only exploratory research for a place that does not yet have a resource package.

The app deliberately maintains separate bodies of data:

- **Imported knowledge** is an immutable snapshot of the package: all records are indexed for research context and duplicate detection.
- **Research work** contains candidates, evidence, run provenance, and deterministic possible-match signals. An imported resource is never inserted as a new discovery.
- **Curation work** lives in the exported Resource Curator, where vetters record outcomes, edit resource drafts, print them, and prepare additions packages without access to Scout.

Standalone-location runs have no imported knowledge. Their candidates are not compared with the latest package, their location-specific lessons remain separate from package-backed lessons and other locations, and their review copies state that the research is exploratory rather than an official or comprehensive TSO Resources inventory.

The source ZIP is opened read-only. Browser uploads are written to a temporary file only long enough to read and hash them, then deleted. Scout never produces a modified copy of that package. Curator can create a new, lightweight additions package containing only resources marked **Ready for package**, their curator-attached PDFs, and the category and For definitions needed to merge them.

## Research connections

The manual copy/paste workflow for ChatGPT, Grok, Claude, Perplexity, and other
user-operated chats is specified in
[`docs/manual-multimodel-discovery-design.md`](docs/manual-multimodel-discovery-design.md).
It preserves the existing portable Resource Curator handoff while moving detailed
website and telephone verification to Resource Specialists. On the
`manual-multimodel-discovery` branch, the version 0.31.8 workspace can generate a
category-specific assignment, preserve pasted or uploaded responses with source
provenance, validate them, replace or delete unfinished contributions, and recover
an open run after restart. It also consolidates exact repeats, keeps distinct named
programs separate, routes directories and limited initiatives outside the provider
count, and exposes package-duplicate signals. Ambiguous identity review is optional;
unreviewed relationships stay separate and travel into Curator as possible-related
context for ordinary specialist investigation. Finished direct-service candidates
carry plain-language questions about identity, service area, category fit, whether
the service is still operating, and how people contact it. Source-only records remain
visible outside the candidate list, and minimally populated resource drafts leave
unavailable contact, hours, and verification fields blank. Production `main` is unchanged.

The Curator presents those checks as ordinary questions rather than internal signal
names, keeps source-by-source chat details collapsed unless needed, and offers
**Worth pursuing** as a positive lead outcome. Manual assignments preserve public
phone numbers and addresses when a chat can supply them readily; specialists still
verify and complete Resource, For, and Information fields during curation.

**Manual chat discovery** is the recommended research method on this branch. It
does not call a chat API: copy the displayed assignment into the chats you choose,
then use the default ChatGPT, Grok, Claude, and Perplexity cards—or a custom source
card—to save each answer. A run may use fewer than four sources. Parser errors must
be corrected or deleted before finishing; a finished response snapshot is
immutable. Finishing also requires the visible consolidation funnel and a decision
of **Same identity**, **Keep separate**, or **Leave unresolved** for each ambiguous
pair. **Research agent** remains available as the advanced choice and retains
the existing DeepSeek, local Qwen, Hermes, and demo behavior.

For a large run, **Leave all pending pairs unresolved** records every remaining
relationship as uncertain and keeps the identities separate. It performs no
bulk merge. Recorded decisions remain collapsed but individually editable until
the run is finished.

Hermes and DeepSeek Harness are connected through the same replaceable research-agent interface. Scout owns the research brief, imported context, assignments, candidate records, deterministic duplicate signals, and research lessons. The selected harness receives one bounded assignment and returns a structured research result. Human curation outcomes do not belong to the harness or Scout. Switching harnesses does not move or migrate application data.

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
5. Use **View candidates** on a research run, or the Research candidates run selector, to inspect that run separately. Open candidates as stages finish to inspect access, restrictions, availability, pet policy, lived-experience findings, evidence, unknowns, follow-up branches, and possible package relationships. If a stage fails, inspect or export the completed work and use **Resume research** without repeating completed stages.
6. Approve or retire agent-proposed lessons in the **Research lessons** panel. These are research-method controls, not vetter outcomes.
7. Choose **Export Resource Curator** on any completed run. Curator opens directly in a browser without Scout or an agent connection. Its three movable, resizable windows keep candidate research, the Categories/Resource/For editors, and the vetter's notes and clickable checklist visible together. Every candidate begins **Pending**. **Worth pursuing** is the positive lead outcome; **Ready for package** is the later completed-resource action. Research further, Duplicate/already known, Wrong category, and Reject record other conclusions. An untouched candidate may remain Pending.

Both external harnesses are optional while exploring the app. Choose **Built-in demo** under **Research agent connection** to exercise the complete workflow without an account or model charge.

### Scout, Curator, vetter, and final package

Resource Scout research is the beginning of the resource-creation workflow, not its authority. Scout produces candidates and evidence for Resource Curator. Curator is the vetter's workspace: the vetter decides which candidates warrant follow-up, conducts the phone interview, checks the website and evidence, resolves practical access details, prepares and prints the resource, marks it **Ready for package**, and creates an additions resource package. That package is merged into TSO Resources, where the office reviews the result and saves a new complete resource package.

The newly saved, phone-vetted TSO Resources package is the ground truth for retrospective Scout evaluation. Evaluation compares each preserved Scout candidate with its corresponding final resource, using an explicit candidate-to-draft-to-final-resource link rather than name similarity alone. Preserve the Scout candidate snapshot, Curator work, additions package, and the TSO Resources packages from before and after the merge. Record whether each candidate field was confirmed, corrected, added during vetting, omitted from the final resource, or remained unknown. An explicit Scout unknown counts against completeness but is not an accuracy error.

Preserved research can be reused through the generic
[`docs/prior-result-lead-manifests.md`](docs/prior-result-lead-manifests.md)
format. It imports names, URLs, and historical provenance only; every lead must
be searched and qualified again under current policy before it can count.
Reviewed provider and referral relationships use the separate generic
[`docs/authoritative-referral-graphs.md`](docs/authoritative-referral-graphs.md)
one-hop format and an exact edge-keyed destination review; edge context is
provenance, never candidate evidence, and a candidate requires a fresh fetch of
the reviewed destination.
Revised corpus freezing also requires a versioned
[`optimization playbook audit`](docs/optimization-playbook-audits.md) that binds
the selected playbook, coverage branches, roles, fields, geography, source
families, gap rules, status signals, and referral components. Candidate gap
needs use explicit exact/any/all tag receipts, while already-completed
operational checks are excluded from candidate-gap generation.

Vetting remains ordinary resource preparation. Vetters are not asked to score the model or its candidates, and Qwen does not judge its own work. Scout scoring is computed afterward from the preserved linkage and package comparison. Candidate yield counts only unique, usable candidates that become corresponding resources in a final saved package; the comparison must keep accuracy, completeness, source quality, usable yield, and elapsed research time as separate measures in that order.

## Portable Resource Curator

Curators are generated only when a user clicks **Export Resource Curator** on a research run. The export always uses that associated run, regardless of which Research candidates view is visible. Nothing is written to an export folder on the server. Each download is one self-contained HTML file with versioned JSON embedded inside it for future migration.

The export contains only the selected completed or partially completed run, stage status, its candidates, editable resource drafts, run-specific lessons, the source taxonomy needed for valid package creation, limited source-package provenance, and the known-resource fields needed to explain possible relationships. It excludes API keys, connection settings, raw agent output, the research database, source-package attachments, and full imported-resource records. Scout status is retained only as source provenance; it does not pre-decide Curator outcomes.

Curator progress is saved locally by the browser when available. Each candidate has its own notes and clickable checklist; changing candidates changes the Notes window to that candidate's work. **Save work** creates the portable JSON checkpoint used to pause, move, back up, or resume the work. It records Pending/Ready state, outcomes, outcome history, notes, checklist state, relationship assessment, resource draft, taxonomy edits, attached PDFs, stable IDs, timestamps, source-package identity, and package history. No reason or terminal outcome is required for candidates left Pending. **Save a resource package** is separate: it is unavailable with no ready candidates and contains only resources currently marked ready. After the ZIP is created, those candidates leave the active queue, but their full state and package linkage remain archived in saved work. Standalone-location Curators can save work but cannot create a resource package.

The right-hand **Editors** window has separate **Categories**, **Resource**, and **For** tabs. **Categories** can add Types within each category, while **For** can add global For groups. Curator is additive-only for governed taxonomy: Type and For-group deletion remains in TSO Resources. **Resource** edits contact and descriptive fields, composes formatted Information, assigns Categories and their Types, chooses For groups, and attaches PDFs. A **Print** button matching the height of **Ready for package** prints the current client-facing resource draft—Name, Description, contact fields, Hours, and formatted Information—without research evidence, curator notes, classifications, or outcome status. Only curator-added PDFs travel with portable work and ready-resource packages; the original source package remains untouched.

## Mergeable ready-resource packages

Resource-package export is available only inside Curators made from research runs that started from an imported TSO Resources package. It is scoped to that Curator and its ready queue; activity in a different Curator cannot affect it. Each download contains:

- the current schema and source package version;
- the imported definition for every category assigned during review, with the Curator's Type edits applied;
- the source package's For definitions with the Curator's edits applied;
- only the run's currently ready, curator-edited resources and their attached PDFs; and
- no imported baseline resources or assets, credentials, or research internals.

The downloaded ZIP is ready for an ordinary TSO Resources user to merge through **Merge Resources**. Resource Scout and Curator do not perform that merge. Each export consumes its ready queue: candidates included in the ZIP are archived from the active Curator queue with their work and package history preserved, while Pending and optional-outcome candidates remain available.

The candidate's service-need summary becomes the generated resource's Description. Contact details and Hours fill their matching fields; the remaining research details become formatted Information using TSO Resources' `* ` bullets, `**bold**`, `__underline__`, and `---` divider conventions. Verified remains blank unless a reviewer enters `MM/YY`. Agent suggestions preselect only Type and For labels that exist in the imported package; the human reviewer remains responsible for classification. Missing or renamed labels are reported for explicit mapping and are never silently changed.

Imports created before version 0.12 did not retain the package's top-level For definitions. Re-import the current source package once after upgrading to make its complete For list available; existing runs, candidates, historical Scout review data, and generated drafts remain preserved for compatible Curator export.

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

On macOS, the first launch securely prompts once to save the key in the user's Keychain; later launches retrieve it automatically. A `DEEPSEEK_API_KEY` already present in the environment takes precedence. On systems without the macOS `security` command, the launcher falls back to a hidden prompt for that launch. The key is never written to the app database or a project file. Select **DSH (experimental)** and **DeepSeek — metered** in **Research agent connection**, save, and the status card will show when it is ready.

The DSH research overlay gives DeepSeek a social-service resource researcher persona, exposes DeepSeek's server-side `web_search` tool, and disables shell, filesystem, editing, skill, workflow, and subagent tools. DSH also runs from an empty temporary working directory. `web_fetch` remains disabled in this first connection because DSH's own preview ships it disabled while its HTTP provider lacks a complete SSRF boundary.

### Production Local Qwen runtime

Resource Scout's production path uses the pinned
`mlx-community/Qwen3.8-27B-8bit` model through MLX LM. Model inference stays on
loopback, discovery uses the project-owned DDGS runtime, page retrieval uses the
safe local fetcher, and the production launcher enforces that unmetered route even
if an older database still contains DeepSeek settings. It does not retrieve a
DeepSeek credential or fall back to a metered provider.

The redesign is category- and location-neutral. Mesa Housing supplies the first
calibration configuration and regression fixtures only; reusable verification,
candidate promotion, discovery expansion, provenance, playbook validation, and
Curator integration derive their fields and rules from the selected package and
category playbook. The exact Mesa Housing query matrix is isolated in
`optimization_housing_calibration.py`; it is calibration data consumed by the
historical benchmark workflow, not a fallback for other categories.

Install or update MLX LM with Homebrew, then stop Homebrew's generic service if it is running. The project installer verifies MLX, installs the pinned DSH runtime, and creates an isolated Python environment for the free DDGS search plugin:

```sh
brew install mlx-lm
brew services stop mlx-lm
./install-local-qwen.sh
```

For a foreground diagnostic start, run the pinned 8-bit model on loopback:

```sh
./local-qwen.sh serve
```

Keep that terminal open. From another terminal, verify both the exact model catalog entry and a real completion:

```sh
./local-qwen.sh catalog
./local-qwen.sh health
```

The live health check records which running server completed the validation;
Resource Scout fails closed if that process changes. The production service runs
this completion check automatically after every model start. In a foreground
diagnostic session, run `./local-qwen.sh health` yourself. DeepSeek remains an
explicitly metered comparison configuration for deliberate interactive use, but
the production service never loads its credential.

Stop a foreground model server with Control-C in its terminal. The launcher
exposes a loopback-only compatibility endpoint at `127.0.0.1:8080` and keeps MLX
itself on loopback at port 8081. The compatibility endpoint adapts DSH's
OpenAI-style message roles and token field for Qwen; it never forwards requests
off the Mac. The launcher selects the pinned model explicitly and refuses to
start while another API is using port 8080. Set `RESOURCE_SCOUT_MLX_SERVER` only
when testing a specific MLX executable outside Homebrew.

Install and control both production services together:

```sh
./background-service.sh install
./background-service.sh status
./background-service.sh logs
```

The installer creates separate persistent LaunchAgents for Local Qwen and
Resource Scout. Qwen may remain temporarily unready while the 8-bit model loads
and completes its automatic validation. Scout and its Tailscale page stay
available during that interval and report the model as unready. `start`, `stop`,
`restart`, and `uninstall` manage both services; uninstalling preserves research
data, model cache, logs, and any existing Keychain credential.

To research a package's categories sequentially without making multiple runs
compete for the one local model, use the batch runner. The runner skips
Miscellaneous by default. This Mesa command also requires the connected package
to contain no resources:

```sh
python3 run_scout_category_batch.py \
  --require-empty-package
```

The runner first proves that Scout is using the unmetered Local Qwen route. It
then starts one four-stage category run at a time and writes progress to
`data/scout-category-batch.json`. Press Control-C to stop the runner safely; run
the same command again to continue. An interrupted Scout run is resumed up to
three times, but repeated failure stops the batch for attention. The state is
bound to the exact connected package and category plan, and a new batch refuses
to begin unless Recent runs is empty. Use `--dry-run` to inspect the plan without
creating a run or state file. Miscellaneous can be added only with the explicit
`--include-miscellaneous` option.

### Temporary Trace Scout

To watch Scout, DSH, Qwen, DDGS search, and safe page retrieval communicate,
start the isolated Trace Scout:

```sh
./trace-scout.sh
```

Keep that Terminal window open, then open the two addresses it prints:

1. `http://127.0.0.1:8082` — Trace Console, where each logical handoff appears
   and waits for approval.
2. `http://127.0.0.1:8766` — a temporary Resource Scout that still uses the
   production 8-bit Qwen model through the trace.

Start one category or standalone-location stage in the temporary Scout. The
console pauses at complete messages rather than model-token fragments. **OK —
next message** releases one handoff. **Skip N** releases a chosen number. **Run
to…** stops at the next Qwen message, search, page fetch, error, or stage
boundary. **Continue without pausing** lets the run finish, and **Pause again**
reinstates the next-message gate. Select any message to inspect its complete
payload or isolate its stage-wide flow. **Download trace** saves the complete
JSON-lines record, including correlation and request/reply identifiers.

The experiment is loopback-only, uses no metered model or fallback, and writes to
`data/trace-scout.sqlite3`, not the production research database. Its first start
creates a clean disposable snapshot containing the current resource package but
no production runs, candidates, or lessons. Later starts resume that temporary
database. Use `./trace-scout.sh --fresh` when you intentionally want to replace
it and `data/scout-trace.jsonl` with a clean production snapshot. Control-C in
its Terminal stops the Trace Console, model proxy, and temporary Scout;
production Scout, production Qwen, and their data are unaffected.

Before Mesa calibration, freeze the historical comparison into an ignored, separate benchmark directory:

```sh
./prepare-mesa-benchmark.py \
  --database data/research-agent.sqlite3 \
  --mesa-package /path/to/mesa-resource-package.zip \
  --output-directory data/benchmarks/mesa-qwen-YYYY-MM-DD
```

The command refuses a package whose SHA-256 differs from the Mesa imports, requires exactly 20 completed four-stage DSH runs, copies the database through SQLite's consistent backup operation, and writes a machine-readable baseline manifest. Qwen calibration and comparison use the copied database, never the live one.

The following Housing-calibration command reproduces the preserved v9 workflow
and also prepares any of the four audited Housing stages. Mesa/Housing query text
stays in the calibration fixture; caching, review, qualification, freezing, and
model execution derive category, stage, location, and field contracts from their
versioned inputs rather than from Housing defaults.
`run-qwen-quantization-comparison.py` is now deliberately read-only: it rebuilds
the historical v9 reports from the completed persisted runs and never starts a
model server or performs inference under the old provenance label.
Expanded Housing discovery can reuse a completed base DDGS cache while appending
one current-status query for each human-resolved urgent candidate:

```sh
./cache-qwen-housing-searches.py \
  --stage-key urgent-access \
  --cache /path/to/housing-stage1-ddgs-v3.json \
  --review /path/to/housing-stage1-identity-review-v3.json \
  --previous-cache /path/to/housing-stage1-ddgs-v2.json \
  --previous-review /path/to/housing-stage1-identity-review-v2.json \
  --candidate-status-review /path/to/housing-stage1-identity-review-v2.json \
  --minimum-queries 4 \
  --maximum-queries 10 \
  --saturation-queries 3 \
  --results-per-query 12
```

For a later stage, first export the identities routed there as names-and-URLs-only
lead hints. This does not copy their earlier qualification or factual claims and
does not promote them to candidates. Add the resulting manifest to that stage's
fresh query plan with `--prior-lead-manifest`:

```sh
./export-qwen-routed-stage-leads.py \
  --database /path/to/mesa-qwen-benchmark.sqlite3 \
  --source-run-id 31 \
  --target-stage-key stabilization \
  --manifest-id mesa-housing-stabilization-routed-v1 \
  --output /path/to/mesa-housing-stabilization-routed-v1.json

./cache-qwen-housing-searches.py \
  --stage-key stabilization \
  --prior-lead-manifest /path/to/mesa-housing-stabilization-routed-v1.json \
  --cache /path/to/housing-stabilization-ddgs-v1.json \
  --review /path/to/housing-stabilization-review-v1.json

./freeze-qwen-housing-corpus.py \
  --database /path/to/mesa-qwen-benchmark.sqlite3 \
  --package /path/to/resource-package.zip \
  --cache /path/to/housing-stabilization-ddgs-v1.json \
  --review /path/to/housing-stabilization-review-v1.json \
  --playbook-audit /path/to/mesa-housing-stabilization-audit-v1.json \
  --prior-lead-manifest /path/to/mesa-housing-stabilization-routed-v1.json
```

Before freezing, every candidate source in the reviewed ledger must carry the
current evidence receipt described in
`docs/identity-qualification-manifests.md`: an explicit authority, either a
complete-page or one-or-more exact-section selection, and organization/program identity
support. Direct-provider pages keep the complete bounded extract. Referral or
directory pages that mention several programs should use exact section
boundaries so neighboring access-point, property, partner, or program facts
cannot be attributed to the candidate. Several ordered, non-overlapping
sections may retain later candidate-wide facts while omitting intervening
entity-specific blocks. Unsupported labels and missing current
section text fail closed before model inference. The source title is refreshed
from the current bounded page instead of trusting a stale or concatenated search
result title.

Apply a reviewed, stage-exact receipt manifest without hand-editing the ledger:

```sh
python3 prepare-qwen-evidence-review.py \
  --cache /path/to/search-cache.json \
  --review /path/to/completed-identity-review.json \
  --manifest /path/to/evidence-preparation-manifest.json \
  --output /path/to/prepared-identity-review.json
```

The manifest is bound to both the cache and base-review hashes and must cover
every eligible identity in that stage exactly once. It may correct the final
organization/program labels, but each corrected label must still carry an exact
source-label receipt (or a reasoned reviewed alias). Routed, review-required,
and noncandidate leads remain in the ledger without being promoted.

The resulting hashed query plan records the candidate-specific closure, relocation,
renaming, and intake sweep. Matching base queries are copied from the prior cache;
only the new status queries call the unmetered search provider. Human decisions can
be applied in labeled, replay-safe batches without losing result/query provenance:

```sh
./apply-qwen-identity-review.py \
  --review /path/to/housing-stage1-identity-review-v3.json \
  --patch /path/to/labeled-review-decisions.json
```

For a reviewed ledger with many obvious nonprogram results, an explicit policy
can build the corresponding exact-URL exclusion patch. The policy must name its
rules and matching values; the command does not infer exclusions and does not
apply the patch:

```sh
./build-qwen-exclusion-patch.py \
  --review /path/to/current-stage-review.json \
  --policy /path/to/reviewed-exclusion-policy.json \
  --output /path/to/exact-exclusions.json
```

When a later ledger repeats a previously excluded search result, Scout can reuse
that exclusion only if URL, title, and snippet are all identical. Candidate
decisions and changed results are never copied:

```sh
./build-qwen-reused-exclusion-patch.py \
  --review /path/to/current-stage-review.json \
  --previous-review /path/to/previous-reviewed-ledger.json \
  --label exact-prior-exclusions-v1 \
  --output /path/to/exact-prior-exclusions-v1.json
```

A completed optimization model run can be exported to its own Resource Curator
without inserting anything into the normal Scout inbox:

```sh
python3 export-qwen-curator.py \
  --database data/benchmarks/mesa-qwen-YYYY-MM-DD/mesa-qwen-benchmark.sqlite3 \
  --run-id 11 \
  --output /path/to/curator-exports
```

The export contains passed and `needs-review` dossiers, their verifier findings,
evidence, conflicts, unknowns, and configuration/corpus/package provenance. True
failed dossiers are not exported. The command is read-only with respect to Scout
and Curator data; undo consists of deleting the standalone HTML export. The same
builder is available at `/api/optimization-runs/{run-id}/review-copy` only when a
server is deliberately started against the isolated benchmark database. Normal
research execution does not invoke this calibration-only, manually reviewed
evidence pipeline. All human outcomes and package preparation occur in Curator
for both historical DeepSeek and Qwen exports.

After Curator work is saved and phone vetting produces an additions package,
compare both with the originating optimization run. The same command can later
use the final merged package as the stronger ground-truth snapshot:

```sh
./compare-qwen-curator-package.py \
  --database data/benchmarks/mesa-qwen-YYYY-MM-DD/mesa-qwen-benchmark.sqlite3 \
  --run-id 11 \
  --curator-work /path/to/housing-curator-work.json \
  --package /path/to/phone-vetted-resource-package.zip \
  --report /path/to/qwen-package-outcome.json
```

Optimization Curators assign every draft a deterministic resource ID derived from
the configuration hash and frozen packet SHA-256. The comparison uses that ID to prove
candidate-to-final-resource linkage, records phone-vetted changes to core fields,
and persists a hashed outcome report in the isolated benchmark database. Saved
Curator work adds explicit Pending, Ready, packaged, Research further, Duplicate,
Wrong category, and Reject states without requiring a vetter to disposition every
candidate. Package presence takes precedence and proves acceptance. Absence from
the supplied package remains Pending unless Curator recorded an explicit outcome;
it is never silently interpreted as rejection. The canonical Curator-work hash is
part of report provenance, so later saved-work revisions produce new immutable
reports rather than overwriting earlier evidence. Omitting `--curator-work` retains
the legacy package-only schema-2 comparison.

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

## Keep Scout and Local Qwen running in the background on macOS

The macOS background service starts the unmetered Local Qwen service and the
Tailscale Resource Scout launcher when you sign in, keeps both running if they
exit, and uses this clone's existing `data/research-agent.sqlite3`. Install it
from the clone that should be Scout's permanent home. It never retrieves or
requires a DeepSeek key:

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

The live-package integration test verifies schema/category discovery and multi-category inclusion. The unit tests also prove that the source ZIP remains byte-for-byte unchanged, full records survive import, every discovered category can start research, category Types and For definitions survive import and export, imported resources remain separate from discoveries, non-selected resources still participate in duplicate checks, unsafe ZIP paths are rejected, Hermes and DSH one-shot results are normalized through the same adapter result, Scout exposes no human-curation or direct-package routes, editable Curators keep notes separate by candidate, outcomes are not required for candidates left Pending, and ready-resource packages are openable, run-scoped, editable, multi-category, capable of carrying curator-attached PDFs, and archive packaged candidates without losing their work or linkage history.
