# Resource Scout curation and enrichment

Resource Scout can freeze an existing `auto[Location].html` into a durable,
resource-by-resource enrichment project. This stage does not rerun discovery,
change the taxonomy, or overwrite the source artifact.

## Information contract

Every completed resource has one deterministic Information block in this order:

1. **Services Provided** — Describe what the organization offers. Be specific—
   types of assistance, programs, or resources available.
2. **Eligibility Requirements** — Who qualifies for services? Include age,
   income, geographic boundaries, documentation needed, referral requirements,
   etc.
3. **How to Best Connect** — Tips for success—whether appointments are required,
   walk-in availability, online application links.
4. **Scout Findings** — the resource's complete pre-enrichment `informationText`,
   appended verbatim by Scout rather than rewritten by the research worker.

The first three sections must be nonempty. When current public sources do not
confirm a detail, the result says so rather than inventing it. Workers return
evidence URLs for validation and audit, although evidence metadata is not added
to the missionary-facing Information block.

## Hybrid research and audit

Codex produces the primary enrichment for every resource. Scout then applies a
deterministic risk policy. An independent audit is required when the primary
result contains explicit uncertainty, has no usable evidence URL, gives no
concrete intake action, the source has neither website nor phone, or the resource
is safety-sensitive (for example crisis, overdose, detox, domestic-violence,
legal, medical, or behavioral-health services).

Flagged resources rotate in stable resource order across ChatGPT, Grok,
Perplexity, and Claude from `researcher_roster.json`. Scout stores the outside
AI's response separately. A fresh Codex context then reconciles the primary
result and audit using their evidence. Neither result can change Scout Findings.
The build remains blocked until every required reconciliation is complete.

The outside-AI boundary matches Scout's existing research workflow: Scout
creates durable assignments and accepts saved JSON responses, but does not claim
direct API access to consumer AI subscriptions.

## Integrity and durability

Preparing a project stores the source HTML, source seed, their SHA-256 hashes,
and one hashed assignment for each resource. Re-preparing the identical artifact
and enrichment version returns the same project. Results must match the resource
ID and assignment hash; a conflicting second result is rejected.

The build is gated until every resource is complete. It changes only
`informationText`, verifies every original resource hash, and emits a new
artifact ID so browser-local review state cannot collide with the source file.
All IDs, descriptions, addresses, phones, hours, websites, Categories, Types,
For groups, and other source fields remain unchanged.

## Commands

```sh
python -m resource_research_agent.cli enrichment-prepare autoMesa.html
python -m resource_research_agent.cli enrichment-status 1
python -m resource_research_agent.cli enrichment-next 1
python -m resource_research_agent.cli enrichment-submit 1 result.json
python -m resource_research_agent.cli enrichment-audit-next 1 --researcher ChatGPT
python -m resource_research_agent.cli enrichment-audit-submit 1 audit-result.json
python -m resource_research_agent.cli enrichment-reconcile-next 1
python -m resource_research_agent.cli enrichment-reconcile-submit 1 final-result.json
python -m resource_research_agent.scout_enrichment_runner 1 --max-resources 5
python -m resource_research_agent.cli enrichment-build 1
python -m resource_research_agent.cli enrichment-checkpoint-export 1 data/mesa-checkpoint.zip
```

The runner gives each resource a fresh Codex context with live web research and
can stop after a pilot batch. Without `--max-resources`, it resumes until the
project is complete. The default output name is `auto[Location]-enriched.html`.
Scout rejects an output path that would overwrite the original file.

## Move the run to another computer

Export a checkpoint only while no enrichment runner is active. The ZIP contains
a consistent SQLite backup plus a manifest recording its hash and the project's
source hash, resource count, and progress. It contains the complete local Scout
database so related history and foreign keys are not separated. Handle it with
the same care as the source database.

On the destination computer, pull the same Resource Scout code and import into a
new database path:

```sh
python -m resource_research_agent.cli \
  --database data/research-agent.sqlite3 \
  enrichment-checkpoint-import mesa-checkpoint.zip
```

Import refuses to overwrite an existing database. The source HTML does not need
to be copied separately because its exact content is sealed in the database.
