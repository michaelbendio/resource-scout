# Resource Research Agent — Housing first cut

This is a standalone, local research workspace for learning from a Resource Assistant `resource-package.zip` without changing that package. It discovers the package schema, identifies the Housing category, preserves complete imported records, builds a known-resource index, and exposes existing Housing records as research seeds.

The app deliberately maintains two separate bodies of data:

- **Imported knowledge** is an immutable snapshot of the package: all records are indexed for duplicate detection, and Housing records become seeds.
- **Research work** contains candidates and review state. An imported seed is never inserted as a new discovery. A candidate with a strong package match is labeled `already-known` automatically.

The source ZIP is opened read-only. Browser uploads are written to a temporary file only long enough to read and hash them, then deleted. No extracted package directory or modified package is produced.

Housing seeds open as readable profiles: category labels, contact details, description, safely rendered Markdown-style information, stored PDF attachments, verification metadata, and an optional raw-JSON view. Only Housing-referenced attachments are copied into the separate research database so their links continue to work after the temporary upload is deleted.

## Hermes research connection

Hermes is connected through a replaceable research-agent interface. The app owns the research brief, imported context, assignments, candidate records, duplicate decisions, review state, and lessons; Hermes receives one bounded assignment and returns a structured research result. A future DSH adapter can receive the same context without migrating application data out of Hermes.

The workflow is:

1. Import a Resource Assistant package.
2. Choose **Research Housing broadly** or branch from one existing Housing seed.
3. Edit the assignment and select **Start research**. Runs continue in the background.
4. Open candidates in the **Candidate inbox** to inspect access, restrictions, availability, pet policy, lived-experience findings, evidence, unknowns, and follow-up branches.
5. Choose **Accept**, **Research further**, **Already known**, **Wrong category**, or **Reject**. Written feedback can become an active lesson included in later research runs.
6. Approve or retire Hermes-proposed lessons in the **Research lessons** panel.

Hermes is optional while exploring the app. Choose **Built-in demo** under **Hermes connection settings** to exercise the complete workflow without an account or model charge.

To install Hermes using its supported macOS installer:

```sh
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
```

Then run `hermes setup` once to choose a provider and model. The Resource Research Agent never asks for or stores provider credentials. It discovers the `hermes` command automatically; an explicit command, profile, provider, or model override can be saved in the connection panel.

## Run the app

Requires Python 3.10 or newer; no third-party packages are needed.

From a Git clone:

```sh
git clone https://github.com/michaelbendio/resource-research-agent.git
cd resource-research-agent
./run.sh
```

Or from the downloadable archive:

```sh
unzip resource-research-agent-hermes-v3.zip
cd resource-research-agent
./run.sh
```

Open <http://127.0.0.1:8765>, choose a `resource-package.zip`, and select **Import package**. Stop the app with Control-C.

The research database is created at `data/research-agent.sqlite3`. It does not contain or modify the source ZIP.

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

The importer searches JSON members inside the ZIP and scores resource-like collections rather than assuming a fixed filename. It recognizes common resource collection/category-definition names, nested package objects, explicit categories, and category IDs inferred from resource records. Housing can be resolved by category ID or label, including when the ID is not literally `housing`.

For each import it records:

- ZIP SHA-256 and member manifest;
- JSON member and discovered resource/category paths;
- package and schema versions where present;
- all category definitions;
- all complete resource records, including unknown extension fields;
- which resources belong to Housing, including multi-category records.

The identity index uses available names, aliases, websites/domains, addresses, organization/provider/program fields, and conservative name variants. The match result explains its signals; it does not silently merge records.

## Test

```sh
python3 -m unittest discover -s tests -v
PROVO_RESOURCE_PACKAGE=/path/to/provo-resource-package.zip \
  python3 -m unittest discover -s tests -v
```

The live-package integration test verifies schema/category discovery and multi-category inclusion. The unit tests also prove that the source ZIP remains byte-for-byte unchanged, full records survive import, non-Housing resources participate in duplicate checks, seeds remain separate from discoveries, unsafe ZIP paths are rejected, Hermes one-shot results are parsed, and research feedback becomes application-owned learning state.
