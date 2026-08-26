# Manual multi-model discovery design

Implementation status (2026-08-25): Stages 0-4 are implemented on the
`manual-multimodel-discovery` branch. The frozen four-source fixtures, tolerant
parser, immutable provenance storage, category-neutral assignment generator,
local endpoints, copy/paste workspace, deterministic consolidation, identity
review, role routing, package duplicate signals, non-inflated funnel, lightweight
checks, minimal drafts, source-only preservation, and portable Curator handoff are
covered by regression tests. Stage 5 is in progress: the real 255-row Addiction
set has been replayed in an isolated pilot, version 0.31.2 corrected the resulting
large-review workflow, and a Food run is prepared for the required second-category
responses. The exact receipt and remaining approval gates are recorded in
`docs/manual-multimodel-pilot-2026-08-25.md`. Stage 6 remains gated on the pilot.
Production `main`, frozen
DeepSeek results, and existing agent-run records have not been rewritten.

Status: proposed implementation design. This document defines the branch work
that follows the 2026-08-25 Addiction pilot. It does not change production Scout,
start a model, or send data to an external service.

## Decision summary

Resource Scout will add a manual discovery path for answers copied from consumer
chat products. The default source labels are ChatGPT, Grok, Claude, and
Perplexity, but the storage and import contracts are source-neutral. Scout will:

1. prepare one category and service-area assignment for every selected chat;
2. accept pasted or uploaded responses without calling an API;
3. preserve each raw response and its source provenance;
4. consolidate duplicate identities conservatively without treating agreement
   as truth;
5. keep provider/program leads separate from directories and routing sources;
6. create minimally populated candidate drafts; and
7. export the run through the existing portable Resource Curator workflow.

Resource Specialists remain responsible for website checking, telephone
interviews, corrections, classification, printing, Ready for package, and the
final resource package. Scout does not score candidate worth, make Curator
outcomes, or establish final truth.

The existing DeepSeek and Qwen paths and their historical exports remain
readable. The new workflow is proved before either path is retired.

## Pilot evidence

The Addiction pilot used one discovery-only assignment in four manually operated
chats. The four responses contained 255 submitted rows. Exact organization and
program strings produced 192 apparent identities; conservative alias resolution
reduced the set to 109 organization clusters. Thirty-nine clusters appeared in
only one response. Grok and Claude were highly correlated, so source count cannot
be treated as independent confirmation.

Compared with the preserved 25-candidate DeepSeek Addiction Curator, the combined
chat set recovered 17 substantively similar services, retained parent or related
organization leads for four more, and omitted four: Banner Poison & Drug
Information Center, Calvary Healing Center, Oxford House, and Hushabye Nursery.
It also surfaced many useful organizations absent from the DeepSeek run, including
Monument Recovery and Canyon Vista Recovery Center. Some unique leads were stale,
non-public initiatives, or weakly supported. This supports a broad discovery
workflow with a lightweight identity/access check, not automatic acceptance and
not full dossier research.

## Product boundary

### Scout owns

- the selected resource package, category, and configured service area;
- the exact assignment and response schema shown to every source;
- raw contribution text, source label, import time, and content hash;
- tolerant parsing with visible warnings;
- conservative identity grouping and possible-duplicate signals;
- separation of direct leads, access points, routing sources, and directories;
- a minimal candidate draft and explicit unknowns;
- run and candidate provenance in the Curator export; and
- an optional follow-up packet for ambiguous or high-value leads.

### Curator and the Resource Specialist own

- whether a lead is worthwhile;
- whether related names are one resource, separate resources, or a duplicate of
  an existing package resource;
- telephone and website verification;
- eligibility, payment, hours, availability, referral requirements, practical
  access, and other resource details;
- Categories, Resource, and For editor changes;
- notes, checklist work, printing, Ready for package, outcomes, and
  saving packages; and
- the final, phone-vetted representation of the resource.

### Scout does not do

- call a consumer-chat API or automate a signed-in chat session;
- use a metered service or silently fall back to one;
- infer that a claim is true because two or more chats repeated it;
- combine factual claims from different programs into a synthetic dossier;
- require detailed completeness before Curator export;
- reject a provider because pet policy, hours, payment, or another supplementary
  field is unknown;
- turn a directory, partner list, or funding announcement into a direct provider
  without a distinct public access path; or
- require vetters to record structured reasons for every lead that does not enter
  a package.

## User workflow

1. Connect a resource package and select a category as today.
2. Choose **Manual chat discovery**.
3. Scout displays one copyable assignment. It includes the package service area,
   category scope, known-resource names, and a compact discovery schema. It asks
   for identities and access clues, not a complete resource dossier.
4. Paste the assignment into any selected chats.
5. Paste or upload each answer into its labeled contribution card. The default
   cards are ChatGPT, Grok, Claude, and Perplexity. A custom label is allowed.
6. Scout validates each contribution immediately and shows lead count, lead-type
   count, blank websites, parser warnings, and preserved trailing source text.
7. Choose **Consolidate leads**. Scout performs deterministic exact merges and
   displays only ambiguous identity suggestions that could materially combine or
   split candidates. No written justification is required.
8. Scout shows the funnel: submitted rows, parsed leads, exact duplicates,
   consolidated identities, possible duplicates, direct/provider leads, access
   points, routing sources/directories, and unresolved leads.
9. Optionally copy a focused follow-up packet for selected ambiguous or valuable
   leads and import the answer under a new source label such as `Codex follow-up`.
10. Choose **Finish discovery**. The finished snapshot becomes immutable and its
    candidate IDs remain stable. Further contributions create a new revision
    rather than silently changing an exported run.
11. Choose **Export Resource Curator**. Existing Curator behavior remains intact.

A run may finish with fewer than four contributions. Missing source cards remain
visible in the run record; they are not errors and do not block export.

## Discovery assignment contract

The manual assignment is category-neutral. Its category and geographic language
comes from the selected package and playbook, but its output is intentionally
shallower than the agent-research output.

Each response asks for:

```json
{
  "leads": [
    {
      "organization": "",
      "program": "",
      "website": "",
      "phone": "",
      "address": "",
      "leadType": "program | provider-organization | access-point | routing-source | directory",
      "locationOrServiceArea": "",
      "whyRelevant": "",
      "uncertainty": ""
    }
  ]
}
```

The assignment adds these safeguards:

- prefer an official organization or program URL when known;
- preserve a public phone number or address when readily available without
  turning discovery into full contact-detail research;
- use a plain URL rather than Markdown when possible;
- identify a named program separately only when it has a materially distinct
  service, population, intake, or administration;
- do not split ordinary locations or access offices into separate services;
- label directories and routing systems rather than presenting them as providers;
- do not claim Mesa or configured-area service without a credible indication;
- label historical, uncertain, planned, pilot, grant-funded, or limited-access
  initiatives explicitly; and
- omit detailed hours, cost, openings, eligibility, and intake research unless it
  is necessary to identify the lead.

Known package resources are supplied as names and stable IDs so a source can avoid
obvious repeats. Scout still performs its own package duplicate check because a
chat may overlook or rename a known resource.

## Parsing and normalization

The importer is tolerant at the boundary and strict after parsing.

Accepted inputs include:

- a plain JSON object;
- JSON inside a fenced block;
- leading explanatory text;
- a valid first JSON object followed by a source list;
- Markdown-formatted URL values such as `[Official site](https://example.org)`;
  and
- blank optional strings.

The importer preserves the entire original text before attempting repair. It may
extract one complete top-level object and normalize a Markdown URL into a separate
parsed field. It must not silently invent missing braces, names, types, URLs, or
claims. Unparseable input is retained with a visible error and can be replaced
before the run is finished.

After parsing, every row receives:

- contribution ID and ordinal;
- raw row JSON;
- normalized organization and program text;
- normalized plain URL plus the originally supplied value;
- declared lead type;
- parser warnings;
- source label and raw-response hash; and
- an immutable link back to the contribution.

Only `http` and `https` links become clickable. Pasted HTML, scripts, data URLs,
and event handlers are rendered as text. Existing upload-size limits are retained
or narrowed for contribution endpoints.

## Persistence model

Manual discovery reuses `research_runs`, `discoveries`, generated resource drafts,
package duplicate checks, and `build_review_copy`. It does not use the Qwen
optimization tables.

`research_runs` gains a category-neutral `run_kind` with
`agent-research` as the migration default and `manual-discovery` for this path.
A manual run uses adapter `manual-chat`, remains `running` while contributions can
change, and becomes `completed` when its snapshot is finished. It does not create
synthetic agent stages or attempts.

New normalized tables:

### `manual_discovery_contributions`

- `id`, `run_id`, `source_label`, and `source_position`;
- `created_at` and `updated_at`;
- `raw_text`, `raw_sha256`, and optional filename;
- parse status and parser version;
- parsed JSON and preserved trailing text; and
- warnings JSON.

Source labels are unique within a run. Replacing a contribution before finishing
updates the record and invalidates the current consolidation preview. Finished
contributions are immutable.

### `manual_discovery_leads`

- `id`, `contribution_id`, and source ordinal;
- the raw lead JSON;
- normalized identity fields and normalized URL;
- declared lead type; and
- parser warnings.

Rows are replaced transactionally when an unfinished contribution is replaced.

### `manual_discovery_identity_groups`

- stable group ID, run ID, and display identity;
- canonical organization, program, and preferred website;
- routed role;
- consolidation state: `exact`, `reviewed-merge`, `reviewed-separate`, or
  `unresolved`;
- lightweight-check states for identity, geography, category relevance, current
  signal, and public access; and
- created and updated timestamps.

### `manual_discovery_identity_members`

- group ID and lead ID;
- membership reason and deterministic signal; and
- source order for display.

Finishing a manual run creates one ordinary `discoveries` record for each
provider/program/access-point identity selected for Curator. The candidate JSON
contains a `manualDiscoveryProvenance` object pointing to its group and every
contribution member. Directories and routing sources remain preserved in the
manual tables and run summary; they do not inflate the Curator candidate count.

No existing table or historical row is rewritten during migration. Older runs
default to `agent-research` and export exactly as before.

## Consolidation rules

Consolidation is deterministic and conservative.

Scout may automatically group rows only when high-confidence identity signals
agree, such as:

- identical normalized organization and program;
- an exact official URL plus compatible identity text; or
- a reviewed alias already recorded within this unfinished run.

Scout must not automatically group rows merely because they share:

- a parent organization with different named programs;
- an address, phone number, or domain used by several programs;
- a generic service description;
- similar words such as `recovery`, `community`, or `center`; or
- agreement by several chat sources.

An organization-only row may support a named program group at the same
organization, but it does not erase other named programs and does not become a
separate provider candidate when it adds no distinct public service. Locations
remain attached to one program unless the submitted evidence indicates a
materially different service, population, intake, status, or administration.

The user may optionally inspect ambiguous merge suggestions as compact pairs or clusters. The
available actions are **Same identity**, **Keep separate**, and **Leave
unresolved**. These are identity corrections, not Curator acceptance decisions,
and no explanation is required. Unreviewed pairs remain separate, do not block
Finish discovery, and travel into Curator as possible-related submissions.

Every contribution remains viewable after grouping. Canonical display fields are
selected by deterministic preference rules; differing factual values remain
source-attributed alternatives rather than being blended.

## Plain-language discovery guidance

This check routes work; it does not score worth or decide a Curator outcome.

Internally, Scout records whether the pasted material provides:

- a coherent organization/program identity;
- plausible relevance to the selected category;
- plausible service to the configured area;
- a current signal or an explicit stale/unknown warning; and
- a public access, intake, meeting, referral, navigation, or follow-up path.

Each internal state is `present`, `uncertain`, `conflicting`, or `not-applicable`,
with the contributing chat details. Curator presents these as plain-language
questions such as **Appears to be active** and **Contact or intake route**; it does
not expose terms such as `currentSignal`. Missing details remain visible questions. A candidate
is not blocked for missing hours, payment, full eligibility, availability,
referral requirements, pet policy, or other dossier fields.

Provider, program, and distinct actionable access-point identities are exported
even when the lightweight check is uncertain; Curator shows the uncertainty.
Directories, referral systems, funding announcements, outreach partners without
a public access path, and organization-only fragments are preserved as discovery
sources or follow-up leads rather than counted as provider candidates. A clearly
closed or replaced identity is preserved with that warning and is not silently
deleted.

## Candidate and Curator representation

A finished identity becomes the smallest honest candidate draft:

- `name`: canonical organization and, when distinct, program;
- `organization` and `program`: kept separately;
- `website`: preferred submitted official URL, otherwise blank;
- `phone` and `address`: readily supplied values, otherwise blank and unverified;
- `geography`: submitted area statements, visibly attributed when conflicting;
- `description` and `serviceNeed`: a concise discovery-level summary, explicitly
  labeled unverified;
- `unknowns`: identity, geography, current-status, and access questions;
- `followUpBranches`: practical website and phone questions for the Resource
  Specialist; and
- `evidence`: submitted URLs as lead evidence, not verified factual receipts.

The candidate retains every source contribution, supplied contact detail,
rationale, uncertainty, and parser warning in `manualDiscoveryProvenance` for
Scout's audit trail. These internal discovery details are not shown in Curator;
chat row numbers and routing labels are not ordinary curation concepts. The
ordinary package duplicate warning remains available to Scout.

The Resource Curator export continues to use the existing self-contained HTML,
Editors, Notes, Print, Ready for package, Save work, and Save package workflow.
Editors and Notes fill the workspace side by side; Curator does not display a
separate Candidate Research pane. The discovery description continues to seed
the Resource editor's Description field. New Curators begin every candidate
Pending. The Outcome list includes **Worth pursuing**
as a positive triage decision; **Ready for package** remains the later completed-
resource state. A short Editors note points specialists to Resource for phone,
address, website, hours, description, and Information, and to For for population
labels.
Existing DeepSeek and Qwen Curators remain self-contained and unchanged.

If the additional provenance fields change the portable contract, increment the
review-copy schema and add backward-compatibility tests. The generated resource
draft uses the existing category taxonomy, stable ID rules, and package builder.
Blank fields remain blank; Scout does not insert prose such as `Unknown` into a
phone number, address, hours, or verified field.

### Contact lookup before Curator export

After discovery, Scout identifies candidates that have neither a website nor a
phone number. The run can export a structured contact-lookup request with three
suggested searches per candidate: exact-name plus Mesa and category, exact-name
plus Maricopa County and category, and exact-name plus Arizona official contact.
The wider searches avoid hiding countywide, regional, or tribal organizations
whose official pages do not use Mesa in their titles.

Imported lookup results preserve the cited source, checked date, and note. A
verified contact fills previously blank website, phone, and address fields. A
candidate may be marked unavailable only when a cited source credibly establishes
that the organization or program closed or ended; a failed search or broken page
alone is not proof of closure. A separate unreachable outcome applies when a
known official website is dead and the prescribed searches find no replacement
website or current public phone. It means the lead is not actionable now, not
that the organization legally closed. Scout retains unavailable and unreachable
leads in its audit display while excluding them from candidate counts and future
Curator exports. An inconclusive lookup remains a candidate and must include
concrete follow-up suggestions, which become unchecked items in the Curator Notes
pane.

## Follow-up packets

Follow-up is selective rather than a second full research run. Scout can generate
a copyable packet for chosen identities that asks for:

- official current identity and program boundary;
- whether the service plausibly serves the configured area;
- whether a person or referrer can actually reach it; and
- resolution of named conflicting URLs or stale-status signals.

The answer uses the same manual contribution importer and a user-chosen source
label. Scout never launches Codex or another chat automatically. Detailed resource
fields remain Curator work unless a particular follow-up is needed to identify or
route the lead.

## Historical results

The first implementation does not parse legacy Curator HTML. After the new path
passes its own pilot, add a bounded legacy intake that reads preserved Curator
exports and imports only candidate identity, program, submitted URLs, run/category
identity, and source date. Historical factual claims do not become current
evidence.

This is a one-time way to add the preserved DeepSeek and Qwen results to a lead
pool. It must not create a permanent DeepSeek-specific code path, mutate the
historical files, or block ordinary manual discovery.

## Staged implementation plan and gates

Each completed, verified repository change is committed and pushed. A
user-visible or functional stage increments the application version. Documentation
alone does not.

### Stage 0: freeze the design and pilot fixtures

Deliverables:

- this approved design;
- reduced, non-sensitive fixtures representing the four Addiction response
  shapes;
- an expected pilot accounting document for submitted rows, parser warnings,
  conservative exact groups, and DeepSeek comparison boundaries; and
- an explicit record that production main and historical exports are untouched.

Tests and gate:

- fixture hashes are stable;
- expected counts are reproducible without network access;
- no test fixture treats source agreement as verification; and
- `main` and the frozen DeepSeek benchmark remain unchanged.

### Stage 1: parser, provenance, and storage

Deliverables:

- manual-run and contribution persistence;
- tolerant first-object extraction and trailing-text preservation;
- Markdown URL normalization;
- raw-response hashing and parser warnings; and
- transactional replacement before finish plus immutable finished snapshots.

Tests and gate:

- plain, fenced, prefaced, and trailing-source JSON inputs;
- Markdown URL and plain URL inputs;
- blank optional fields and missing required keys;
- malformed, oversized, duplicate-label, and non-object inputs;
- script, HTML, `data:`, and unsafe-link inputs render inertly;
- raw text and trailing sources survive byte-for-byte;
- restart/resume produces the same contribution and lead records;
- an older database migrates without changing old runs or candidates; and
- no adapter, DSH process, network call, credential, or metered fallback is used.

### Stage 2: manual discovery workspace

Deliverables:

- research-method choice with Manual chat discovery as the new path and existing
  agent research retained as an advanced option;
- copyable category-neutral assignment;
- four default source cards plus custom labels;
- paste and text/JSON upload;
- immediate validation summaries; and
- unfinished-run editing, replacement, deletion confirmation, and recovery.

Tests and gate:

- package and category selection determine assignment and known-resource context;
- Food and Legal fixtures prove there is no Addiction or Housing constant;
- source cards are keyboard- and touch-usable on Mac and iPad widths;
- progress displays contributions received rather than synthetic agent stages;
- replacing one unfinished response invalidates only its parsed rows and the
  consolidation preview;
- finishing prevents silent edits;
- the source package remains byte-identical; and
- current agent-run creation, resume, display, and export tests remain green.

### Stage 3: conservative consolidation and routing

Deliverables:

- deterministic exact grouping;
- package duplicate signals;
- compact ambiguous-identity review;
- role routing for programs, provider organizations, access points, routing
  sources, directories, outreach initiatives, and unresolved leads;
- a visible funnel with non-inflated candidate counts; and
- stable finished group and discovery provenance.

Tests and gate:

- punctuation, corporate suffix, acronym, and Markdown URL variants;
- one organization with several genuine programs;
- several locations for one program;
- parent organization plus named program;
- access point versus provider;
- directory versus program;
- grant-funded or pilot initiative without a public intake;
- stale, successor, and possibly closed names;
- two-source agreement on the same false or weak lead;
- one-source unique lead remains preserved;
- automatic grouping is repeatable and order-independent;
- ambiguous names are never silently merged; and
- candidate totals count consolidated identities, not pages, locations, source
  rows, or model votes.

### Stage 4: lightweight checks and Curator export

Deliverables:

- identity/geography/category/current-signal/access check states;
- minimal candidate drafts with explicit unknowns;
- source-attributed discovery provenance retained in Scout's audit record;
- source-only records preserved without becoming provider candidates; and
- normal portable Curator and ready-resource package behavior.

Tests and gate:

- missing pet policy, hours, payment, full eligibility, or current openings never
  blocks export;
- uncertain geography, identity, or access remains visible;
- no factual majority vote or cross-program claim blending occurs;
- all new candidates begin Pending;
- no optional Curator outcome is preselected;
- generated phone, address, hours, and verified fields remain blank when unknown;
- known-resource duplicate signals still work;
- the export contains no raw package records, credentials, or agent settings;
- embedded contribution text cannot close a script tag or execute HTML;
- Save work, Print, Ready for package, and Save package remain functional;
- a saved package opens and merges through the established resource-package
  contract; and
- historical DeepSeek, normal Qwen, optimization Qwen, and demo-run Curator tests
  remain green.

### Stage 5: real two-category pilot

Deliverables:

- re-import the four Addiction responses through the actual UI;
- compare the resulting groups with the preserved DeepSeek Addiction Curator;
- run one materially different category through the same four-chat process;
- selectively follow up ambiguous or high-value leads; and
- record elapsed human handling time, submitted rows, consolidated identities,
  source-only records, uncertain leads, Curator candidates, and obvious stale or
  wrong-scope results.

Tests and gate:

- deterministic fixture counts match the UI and database;
- every exported candidate links back to all contributing rows;
- every source-only row remains recoverable;
- the second category requires no code or schema change;
- a Resource Specialist can understand the provenance and begin work without
  Scout access; and
- Michael approves the practical workload and candidate presentation before
  production becomes dependent on the new path.

### Stage 6: legacy intake and production decision

Deliverables:

- optional one-time identity-only intake from preserved Scout Curators;
- deduplication against the manual run with source provenance retained;
- documentation for the operating workflow;
- a complete stale/dead-end code audit; and
- an explicit decision about Qwen, trace tooling, old optimization commands, and
  agent-connection prominence.

Tests and gate:

- legacy intake is read-only and repeatable;
- historical details are not promoted to current facts;
- duplicate imports do not create duplicate contributions or candidates;
- normal historical Curator export remains available;
- production database backup and migration/rollback are exercised;
- loopback and Tailscale workflows are tested;
- the full Python and JavaScript suites pass; and
- production cutover occurs only after explicit approval.

## Rollback and compatibility

- Development occurs in a separate worktree and branch.
- Production `main`, its database, and its running process are not used for
  development tests.
- Additive tables and a defaulted `run_kind` keep old databases readable.
- No migration deletes or rewrites a historical run, contribution, candidate,
  Curator export, imported resource, optimization record, or lesson.
- Until production approval, rollback is simply continuing to run `main`.
- At deployment, back up and hash the production database before first start.
  If migration or UI verification fails, stop the new service and restart the
  prior release against the untouched backup.

## Stale and dead-end code review

The new path must not be layered indiscriminately on every experiment accumulated
during Qwen optimization. Before production cutover, classify each relevant path
as production, compatibility-only, calibration-only, temporary, or removable.
At minimum review:

- normal `ResearchCoordinator` and DSH adapter paths;
- optimization pipeline and standalone optimization Curator export;
- Trace Scout scripts, console, client, patch, tests, and disposable runtime home;
- prior-lead and referral-graph tools;
- batch category runner and Qwen launch/service scripts;
- obsolete UI connection choices and copy; and
- documentation that still presents deep automated dossier research as the only
  normal workflow.

Removal is not part of the early stages. Preserve anything needed to open old
runs or reproduce frozen benchmarks. Delete only code proven unreachable from
production, unnecessary for historical compatibility, and covered by a verified
replacement or an explicit retirement decision.

## Acceptance criteria

The new workflow is ready for production consideration when:

- a person can prepare an assignment, collect four responses, consolidate them,
  and export a Curator without an agent connection or API key;
- unique leads remain visible while directories and fragments do not inflate the
  candidate count;
- a Resource Specialist receives a comprehensible, minimally populated Curator
  with all source provenance and no invented facts;
- the Addiction pilot and a non-Addiction category complete through the same
  implementation;
- existing Curator and package workflows remain compatible;
- the full test suite passes with explicit no-metered-traffic coverage; and
- Michael approves the workflow after using the pilot export.
