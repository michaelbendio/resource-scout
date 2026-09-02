# Resource Scout

Resource Scout researches, consolidates, and curates resource candidates gathered
from several consumer AI products. It creates a self-contained TSO Resources
review file such as `autoMesa.html` for human vetting and package creation. It is
designed for repeated use across TSO locations and resource categories.

Version 0.48.0 gives generated `auto[Location].html` files a dedicated Curated
workflow. Every review begins with no curated resources. Reviewers curate an
open resource, preview its unsaved edits in the missionary-facing print layout,
open its website directly from the editor, toggle Curated beside Done, and save
only the checked resources from the Resources work area. Scout review files hide
Office Setup and Publish to SharePoint because their job ends with a mergeable
resource package.

Version 0.47.0 compiles an approved, source-hashed taxonomy study into
`auto[Location].html`. The compilation applies need-based Categories,
category-specific Types, and comprehensive For groups to the frozen corpus,
records the exact proposal hashes, and refuses unresolved or stale inputs.
The review file lets missionaries browse by need or find resources for one or
more For groups; Type choices are ORed, group choices are ORed, and the two
dimensions are combined with AND.

Version 0.46.0 makes Codex-first research the durable whole-office workflow.
Every non-Miscellaneous category has a versioned focused playbook and gap pass.
The readable researcher roster assigns Codex as primary, ChatGPT, Grok, and
Perplexity as one-pass challengers, and Claude as a non-blocking shadow source.
Scout saves every exact assignment and response, excludes shadow results from
candidate packages, resumes category state after restart, and prevents curation
until the configured research plan is complete. ChatGPT's random baseline is
now 5–10 minutes; the existing 30-minute throttle cooldown remains. The v0.45
blind-comparison runtime was retired after its immutable evidence and report
were preserved.

The source-hidden Codex-first replay compares the completed v1 run with a fresh
v2 proposal on the same immutable package baseline. Saved provider results are
split into anonymous lesson evidence and sealed identities; providers do not
rerun, and no active playbook changes automatically. See
[`docs/codex-first-replay.md`](docs/codex-first-replay.md) for its durable study,
API, metrics, and evidence-boundary contract.

Version 0.44.0 added an evidence-gated Codex focused-research laboratory without
changing Scout's existing four-AI workflow. Employment research can now run as
durable, candidate-aware focus passes followed by a deterministic gap pass.
Scout preserves each pass, its exact assignment, leads, source focus, and
cross-pass provenance; Section 02 shows compact operational progress. A sealed
Mesa-and-Provo retrospective recovered all nine primary targets and both
secondary diagnostics, exceeding the approved eight-of-nine advancement gate.
The detailed result remains an evaluation artifact and no learned guidance is
activated automatically.

Version 0.43.1 preserves every completed research run for the connected office
when Scout builds its candidate snapshot, even after many newer runs have been
created for another office. Long-lived Mesa and Provo research therefore remains
available for later curation without depending on the recent-runs display limit.

Version 0.43.0 makes proposal quality, rather than proposal volume, the curation
target. Codex must keep the smallest high-confidence set of direct, actionable
services, explicitly dispose of every candidate, consolidate related programs
that share an organization or intake path, and add another category only when
the same program directly serves it. Indirect barrier removal and downstream
outcomes no longer justify category assignment.

Version 0.42.1 keeps each generated review file's embedded curated resources as
an immutable base and saves only the reviewer's compact changes, selection marks,
deletions, and packaged-resource IDs. This avoids duplicating a large curation
result in browser storage and keeps the review file usable under Safari's
smaller local-file storage allowance. Review state is scoped to the exact
generated curation artifact.

Version 0.42.0 added durable ChatGPT assignment scheduling with explicit
scheduled, due, sent, and cooldown states. A past-due assignment becomes due
immediately when Scout restarts instead of receiving another delay.
The former model-agent, optimization, benchmark, trace, and teaching systems are
not part of this codebase.

## Workflow

1. Connect an existing TSO Resources package.
2. Codex performs focused and coverage-gap research category by category.
   ChatGPT, Grok, and Perplexity each receive one adversarial assignment to find
   what Codex missed. Claude may run as a non-blocking shadow source. Scout
   preserves exact assignments, responses, roles, and attribution.
3. Scout's progress area reports research and curation counts, the current
   activity, the selected delay, scheduled time, and delivery state for the next
   ChatGPT run, and a 15-minute heartbeat during long categories.
4. After research finishes, Scout curates each non-Miscellaneous category through
   durable Codex-controlled assignments.
5. Scout creates a transient `auto[Location].html` for human review and displays
   a ready message and download control.
6. Reviewers edit ordinary resources in that file, mark vetted resources
   **Curated**, save a standard package containing the curated selection, and merge
   it into the office HTML. Successfully packaged resources are hidden locally.

## Candidate packages

Scout can build an internal location-wide candidate snapshot such as
`mesa-candidates.zip`. It contains the consolidated candidates from every
completed discovery associated with the connected package, grouped by category
and accompanied by their source responses, source-only records, closed or
unreachable records, and package provenance. The main Scout screen does not ask
the operator to save this intermediate package.

Candidate packages are a portable Scout snapshot. They do not contain curation
decisions and do not alter the connected resource package.

## Resource Scout curation

After all named service categories have completed research, Scout prepares one
durable curation assignment at a time for Codex. It validates and stores a
disposition for every consolidated candidate, resumes completed work without
repeating it, and carries previously curated resources forward so one program
can be classified under more than one category.

When every category except Miscellaneous is curated, Scout creates a versioned,
self-contained `auto[Location].html`. Reviewers mark any vetted resources
**Curated** in that normal TSO Resources file. Each successful save
exports one standard additions-only package and removes the saved resources from
that browser's active review queue. See
[`docs/scout-curation.md`](docs/scout-curation.md) for the full contract and pacing
policy.

When a genuinely changed resource package is connected after discovery has
finished, Scout can reconcile the preserved discoveries against it without
repeating research. It omits only candidates supported as the same resource by
an exact identity plus exact website or address and keeps weaker relationships
for review. The resulting office review file uses that reconciled package as its
additions-only base.

Resource Specialists perform the website review, telephone interview,
classification, editing, printing, and final package decision in Scout's normal
TSO Resources review file.

## Run Scout

Python 3.10 or newer is required. Scout has no third-party Python dependency.

```sh
./run.sh
```

Open [http://127.0.0.1:8765](http://127.0.0.1:8765).

For private access from an iPad connected to the same Tailscale network:

```sh
./run-tailscale.sh --port 8767
```

The command prints the private address to open on the iPad.

## Background service on macOS

```sh
./background-service.sh install
./background-service.sh status
./background-service.sh restart
./background-service.sh logs
```

The service starts Scout with private Tailscale access. Uninstalling the service
does not remove Scout's database or logs.

## Data and privacy

The connected package is read without modifying the source ZIP. Scout stores an
immutable import snapshot, chat responses, deterministic consolidation records,
contact-search results, completed candidate records, curation assignments, and
workflow progress in its local SQLite database. A generated office review file
contains curated proposals and only the office/package provenance needed for
review and standard package creation.

## Tests

```sh
python3 -m unittest discover -s tests
```

The suite covers package import and duplicate indexing, category guidance,
response parsing, conservative consolidation, identity decisions, contact lookup,
focused-research planning, resumability, target sealing, gap analysis, provenance,
retrospective evaluation, Curator isolation and package creation, Tailscale
behavior, background service configuration, Resource Scout curation durability,
curation validation, progress and pacing, Scout-owned review-file generation, and
Scout/review-file UI wiring.
