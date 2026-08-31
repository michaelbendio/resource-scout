# Codex-led research learning design

Status: proposed for discussion. No behavior described here is active unless a
later Resource Scout release implements it.

Baseline: Resource Scout v0.43.1 build 9.

## Purpose

Resource Scout currently preserves and consolidates candidate research from
ChatGPT, Grok, Claude, and Perplexity, then gives Codex durable category-by-
category curation assignments. The Employment comparison among the four-model
candidate union, the earlier Employment-only `autoMesa.html`, the newer direct-
service Scout curation, and the Gassers' human-vetted Provo package showed that
Scout can improve both research and curation by comparing their differences.

That improvement is not persistent merely because Codex discussed it. Durable
learning requires versioned repository documentation, assignments, stored
evidence, code, and tests. Scout is a workflow application rather than an
autonomous agent: Scout prepares exact assignments, preserves state and
provenance, validates results, and reports progress; Codex performs research,
comparison, and judgment.

This design defines a staged path for testing whether focused Codex-led research
can match or exceed the useful candidate coverage of the four-AI union. It also
defines later releases for general category research, learning from successive
human-vetted packages, approved playbook adaptation, and maintenance research.

## Product decisions

1. The target is accepted-resource recall, not raw candidate volume.
2. The final human-vetted package is authoritative. AI results, including Codex
   results, are proposals.
3. Research and curation have separate versions, evidence, and evaluation.
4. Scout never silently activates a research or curation lesson.
5. A lesson is not active until its evidence is reviewable and the corresponding
   playbook or assignment receives a new version.
6. Materially different locations, models, research policies, playbook versions,
   and curation versions are not pooled as if they were one experiment.
7. Exact source responses, consolidated identities, curation dispositions, and
   final package outcomes retain deterministic provenance.
8. A broken or missing webpage is evidence to investigate, not proof that a
   resource closed.
9. `auto[Location].html` remains a transient Scout artifact and is never a
   learning database or committed source file.
10. The existing four-AI workflow remains available until a controlled comparison
    justifies changing the default.

## Non-goals

The first releases do not:

- retrain an underlying language model;
- make Scout an autonomous agent;
- automatically browse consumer AI applications;
- automatically rewrite an active playbook;
- automatically merge proposals into an office package;
- treat source uniqueness as proof of quality;
- replace human telephone, local, private-document, or practical verification;
- revive the former model-agent or optimization system described as removed from
  the current product;
- change the review-file Ready-to-package workflow; or
- finalize Stephanie's Information outline, multi-category policy, or missing
  For-group treatment before her feedback is incorporated.

## Employment evidence baseline

The v0.44.0 experiment must preserve this baseline before creating new results.

### Mesa research and curation

- Grok submitted 15 leads.
- Claude submitted 16 leads.
- ChatGPT submitted 24 leads.
- Perplexity submitted 17 leads.
- The 72 submitted leads became 63 consolidated identity groups.
- Seven identity groups contained more than one source; 56 appeared to be
  single-source identities.
- Fifty-four candidates reached direct-service curation.
- The earlier Employment-only `autoMesa.html` contained 25 resources.
- `codex-curation-v2-direct-service` produced 17 Employment proposals.

Six of the 17 direct-service proposals had only Claude or Perplexity candidate
provenance:

- Arouet Foundation employment readiness and reentry support for women;
- Chicanos Por La Causa workforce development and employment services;
- RISE Services supported employment;
- International Rescue Committee Phoenix refugee employment services;
- Lutheran Social Services of the Southwest refugee support services; and
- Society of St. Vincent de Paul workforce readiness and Neighborhood Brigade.

### Provo research and curation

- ChatGPT submitted 16 leads.
- Grok submitted 25 leads.
- Claude submitted 8 leads.
- Perplexity submitted 14 leads.
- The 63 submitted leads became 58 consolidated identity groups.
- Three identity groups contained more than one source; 55 appeared to be
  single-source identities.
- Forty-eight candidates reached curation.
- `codex-curation-v1` produced 24 Employment proposals.
- `codex-curation-v2-direct-service` produced 15 Employment proposals.
- Tightening all Provo categories reduced the curation result from 430 to 324
  distinct proposals.

Five of the original 24 Employment proposals had only Claude or Perplexity
candidate provenance:

- Express Employment Professionals Provo;
- Tech-Moms workforce re-entry training;
- DWS Registered Apprenticeship;
- Utah Valley Refugees employment and case management; and
- UVU Continuing Education career training.

Three of those survived direct-service tightening:

- Express Employment Professionals Provo;
- Tech-Moms workforce re-entry training; and
- Utah Valley Refugees employment and case management.

### Human-package evidence

The Gassers' Provo package contains 29 Employment resources. Thirteen are
Employment-only and 16 also belong to another category. It provides valuable
local and practical evidence, including staffing, immediate-income, training,
employer, reentry, supported-employment, and operational referral knowledge.
It also contains overlaps, broad category assignments, mixed Information
structures, internal instructions, uncertain details, and aggregate/individual
duplication. It is an important comparison source, not an assumed ideal.

### What the unique discoveries taught us

The Claude- and Perplexity-only proposals cluster around repeatable search gaps:

- refugee resettlement plus employment;
- supported employment for people with disabilities;
- women returning to work;
- women leaving incarceration;
- population-specific workforce programs;
- apprenticeships;
- university continuing education and short career training;
- local staffing offices;
- employment programs inside broader basic-needs organizations; and
- programs discoverable through contracts, grants, partner announcements,
  catalogs, or registries rather than obvious service pages.

Alternative vocabulary also matters: economic empowerment, workforce readiness,
career pathways, self-sufficiency, reentry stabilization, vocational development,
job retention, and family economic mobility can describe Employment services
without using the word `employment` prominently.

## Definition of research effectiveness

Codex-led research succeeds when it finds the distinct, current, geographically
relevant, actionable services that survive direct-service curation and human
review. It does not need to reproduce every raw lead returned by four models.

Primary outcome:

> The proportion of resources accepted into a final human-vetted package that
> Codex independently discovered under the tested playbook version.

Secondary outcomes:

- distinct candidate precision;
- duplicate-adjusted candidate recall;
- identity-consolidation accuracy;
- geographic accuracy;
- official or primary source coverage;
- actionable public intake coverage;
- curation survival;
- human editing burden;
- research time;
- number and value of shadow-model-only additions; and
- subscription or usage cost.

Contact-field counts, response length, raw lead count, and proposal count are
diagnostic measurements rather than success criteria.

## Architecture

### Responsibility boundary

Scout:

- loads a versioned category playbook;
- creates an immutable research-plan snapshot;
- prepares each exact focus assignment;
- persists focus-pass state;
- prevents duplicate work;
- accepts and validates structured responses;
- adds accepted pass responses to the existing manual-discovery run;
- consolidates candidates through the existing candidate pipeline;
- stores assignment, playbook, source, and pass provenance;
- builds deterministic evaluation reports; and
- reports progress and recovery state.

Codex:

- reads Scout's exact saved assignment;
- searches appropriate current sources;
- follows organizations to named programs and intake paths;
- returns the required structured leads;
- performs the requested gap analysis;
- resolves straightforward identity questions; and
- explains genuinely uncertain relationships without inventing facts.

### Relationship to current manual discovery

A focused research job owns one existing manual-discovery `research_run`. Each
focus pass becomes one traceable contribution to that run. This preserves the
current parser, source-response storage, identity consolidation, contact lookup,
candidate generation, reconciliation, and curation handoff.

The focused job adds orchestration and evidence; it does not create a second
candidate system.

### New durable records proposed for v0.44.0

`focused_research_jobs` records:

- research-run and import identity;
- location and category;
- playbook ID and version;
- immutable plan JSON and plan hash;
- current status;
- baseline candidate manifest hash;
- final candidate manifest hash;
- retrospective evaluation JSON and hash; and
- creation, update, and completion times.

`focused_research_passes` records:

- job ID and stable focus key;
- ordinal and pass kind (`focus` or `gap`);
- status (`pending`, `assigned`, `completed`, or `failed`);
- exact assignment and assignment hash;
- candidate-manifest hash visible when assigned;
- contribution ID created from the response;
- returned lead count;
- coverage and result summary JSON;
- timestamps; and
- an error message.

The new tables must be named for the current focused-research feature. The
implementation must not assume that legacy `optimization_*` or
`research_lessons` tables found in an older live database are current product
state. Existing databases may retain those unused tables, and migrations must
leave them untouched.

### Idempotency

- One focused job is unique for import, category, playbook version, plan hash,
  and experiment mode.
- One pass is unique for job and focus key.
- An assignment is immutable after the pass becomes assigned.
- Reposting an identical completed response returns the existing contribution.
- Posting a different response to a completed pass is rejected.
- Consolidation uses the complete ordered contribution manifest and is
  repeatable.
- A restart resumes the first incomplete pass without rescheduling or changing
  its assignment.
- A gap assignment is generated once from a fixed candidate-manifest hash.

### Focus-pass model

Employment v2 initially defines these passes:

1. public workforce infrastructure;
2. immediate employment and staffing;
3. training, credentials, apprenticeships, and advancement;
4. disability and supported employment;
5. refugee, immigrant, reentry, women, youth, senior, veteran, and other
   population-specific pathways;
6. employment support embedded in broader community organizations;
7. non-obvious source channels such as contracts, grants, partner lists,
   catalogs, and registries; and
8. a final gap pass generated after consolidation of the preceding passes.

Each focus assignment receives:

- office and service area;
- category definition;
- focus purpose and alternative vocabulary;
- included and excluded services;
- relevant current-package resources;
- a compact manifest of candidates already found;
- source-channel guidance;
- the existing structured lead schema; and
- explicit safeguards against invented geography, status, and contact facts.

The manifest contains enough identity information to avoid repeats but does not
replace the full stored candidate records.

### Gap pass

After the fixed passes complete, Scout consolidates their contributions and
builds a coverage summary. Codex receives the summary and an exact assignment to
search only material gaps, possible differently named equivalents, and unclear
program boundaries.

The gap pass must not be a second general Employment search. Its assignment is
bound to the fixed candidate-manifest hash so the reason for every follow-up is
auditable.

### Retrospective recovery evaluation

The primary retrospective target set contains the nine Claude/Perplexity-only
proposals that survived direct-service curation: six Mesa and three Provo. The
two additional Provo v1-only proposals are secondary diagnostic targets.

Target names and URLs are never inserted into the focused assignments. After a
job is closed, Scout compares the resulting identities against the stored target
manifest and classifies each target as:

- exact rediscovery;
- credible equivalent service;
- parent organization found but named program missed;
- ambiguous possible relationship; or
- not recovered.

Exact and equivalent matches require recorded evidence. Name similarity alone
is insufficient. Ambiguous relationships remain visible for Codex review.

Because Codex has previously seen these targets, retrospective recovery proves
that the revised method can retrieve known kinds of misses. It does not prove
generalization.

## Release roadmap

### v0.44.0 — Employment research laboratory

- preserve the evidence baseline;
- add experimental Employment playbook v2;
- add durable focused and gap passes;
- add Codex result validation and progress;
- improve the minimum identity handling required for fair recovery attribution;
- run and store the Mesa and Provo retrospective recovery evaluation; and
- leave the current four-AI workflow unchanged.

### v0.45.0 — Blind research comparison

- select several held-out categories with different research characteristics;
- seal shadow-model results until the Codex result is closed;
- compare duplicate-adjusted identities under one curation policy;
- report unique valid candidates, curation survival, reviewer effort, time, and
  marginal model contribution; and
- establish evidence for the Claude and Perplexity subscription decision.

### v0.46.0 — Codex-first research for every category

- introduce versioned focused playbooks for all non-Miscellaneous categories;
- make the researcher roster configurable by role: primary, challenger, shadow,
  or disabled;
- generalize focus, coverage, gap, resume, and progress behavior;
- preserve ChatGPT delay and cooldown behavior whenever ChatGPT is enabled; and
- complete one whole-office Codex-first research cycle before curation.

### v0.47.0 — Learning from human review and successive packages

- link submitted lead, candidate identity, generated proposal, review selection,
  packaged resource, and later office-package resource;
- compare accepted additions, human rewrites, merges, splits, category changes,
  For changes, duplicates, omissions, and human-added resources;
- preserve ambiguity when package absence has no explicit meaning; and
- produce evidence-backed proposed lessons without activating them.

### v0.48.0 — Approved adaptive playbooks

- allow proposed lessons to be reviewed, revised, approved, rejected, retired,
  and traced;
- show the exact playbook or assignment change before activation;
- create a new playbook version for every activation;
- retain prior versions for comparison and rollback; and
- run held-out regressions before activation.

### v0.49.0 — Maintenance research

- audit existing resources as current, changed, moved or renamed, possibly
  closed, unverifiable, identity-problematic, or related to a new program;
- show field-level old/new evidence and focused human questions;
- preserve unconfirmed trusted package data; and
- export only explicitly accepted maintenance changes.

### Stephanie feedback

Stephanie's Employment feedback is incorporated into the next appropriate
release rather than blocking v0.44.0 research work. It may revise:

- Description style;
- the Information outline;
- required operational detail;
- direct-service boundaries;
- multiple-category assignment;
- existing For-group inference; and
- the treatment of a warranted missing For group.

Any resulting curation change receives a new curation-assignment version and
tests. After that feedback is incorporated, remove the Employment-only review-
file compatibility option.

## v0.44.0 implementation plan

### Stage 0 — Freeze the baseline

Implementation:

- add this design and an evidence fixture containing the immutable baseline
  counts and target identities;
- snapshot the current `chat-discovery-v1` Employment playbook and
  `codex-curation-v2-direct-service` identifiers in the fixture;
- record source run IDs, import IDs, assignment hashes, and curation job IDs used
  by the evaluation; and
- keep live database files and generated review artifacts outside version
  control.

Tests:

- fixture schema validation;
- target IDs are unique and refer to recorded baseline evidence;
- six Mesa and three Provo primary targets are present;
- two Provo secondary targets are present;
- no target name or URL occurs in an experimental assignment fixture; and
- baseline counts fail loudly if changed without an explicit fixture revision.

### Stage 1 — Versioned Employment v2 playbook

Implementation:

- extend the playbook representation with immutable focus definitions,
  alternative vocabulary, source channels, and coverage labels;
- retain compact v1 compatibility;
- introduce a new playbook-library version;
- build deterministic focus assignments; and
- keep the ordinary lead-response schema so existing parsing remains reusable.

Tests:

- v1 playbooks still load unchanged;
- Employment v2 contains every required stable focus key;
- focus order and hashes are deterministic;
- only supported placeholders are accepted;
- service-area substitution cannot change the focus definition;
- assignments contain include, exclude, source, geography, and safeguarding
  guidance;
- assignments contain the required JSON response schema; and
- assignments contain none of the retrospective target names or URLs.

### Stage 2 — Durable focused-job storage

Implementation:

- add focused-job and focused-pass tables to the current schema;
- add non-destructive migration checks for existing databases;
- implement create, read, assign, complete, fail, resume, and summarize methods;
- make plan and assignment snapshots immutable after assignment; and
- preserve unused legacy tables without reading or rewriting them.

Tests:

- a clean database receives the new schema;
- a copied v0.43.1 database migrates without changing existing rows;
- duplicate job creation returns the same job;
- duplicate focus keys are rejected;
- only valid state transitions succeed;
- an identical result submission is idempotent;
- a conflicting completed result is rejected;
- deleting an import cascades only its focused jobs;
- restart returns the correct next incomplete pass; and
- legacy unused tables neither populate nor influence focused research.

### Stage 3 — Candidate-aware assignment generation

Implementation:

- build a compact, deterministic known-resource and prior-candidate manifest;
- bind every pass assignment to the manifest hash visible at assignment time;
- include category-specific focus and vocabulary;
- generate the gap pass only after all fixed passes complete and consolidate;
- preserve exact assignment text and hash; and
- ensure the gap assignment names material gaps rather than issuing a general
  second search.

Tests:

- known package resources appear without unnecessary full-record data;
- candidates from completed earlier passes appear once in the manifest;
- assignment hashes change when and only when their inputs change;
- a fixed pass cannot see candidates returned after it was assigned;
- the gap pass cannot be created early;
- repeated gap generation returns the same assignment;
- the gap assignment is bound to the correct candidate-manifest hash; and
- no other office's resources or candidates enter the assignment.

### Stage 4 — Codex result intake and progress

Implementation:

- expose focused-job and focused-pass endpoints through Scout's local API;
- return Scout's exact saved assignment;
- validate the structured response with the existing manual-discovery parser;
- save one traceable contribution per completed focus pass;
- show the active focus, completed-pass count, submitted-lead count, consolidated-
  identity count, remaining coverage, and current gap status in Section 02;
- report a 15-minute heartbeat during a long pass; and
- keep Section 03 scoped to the connected office and initially collapsed.

Tests:

- HTTP create, inspect, assign, submit, resume, and failure behavior;
- malformed JSON does not complete a pass;
- a valid response creates exactly one contribution;
- a retry cannot duplicate a contribution;
- progress counts derive from stored state rather than optimistic UI state;
- error and restart messages are durable;
- browser rendering escapes assignment and progress content;
- Section 03 remains office-scoped and collapsed; and
- the existing four-AI and ChatGPT scheduling endpoints remain unchanged.

### Stage 5 — Cross-pass consolidation and identity safeguards

Implementation:

- consolidate all completed focus contributions through the current identity
  pipeline;
- preserve pass key and Codex source attribution on every member lead;
- strengthen only evidence-supported alias relationships needed for the
  Employment evaluation;
- distinguish organization, named program, access point, directory, and ordinary
  location; and
- keep genuinely uncertain relationships visible instead of forcing a merge.

Tests:

- exact repeated URLs and compatible program identities merge;
- partnership-name variations for the same named program can merge with recorded
  evidence;
- parent organization and materially distinct program remain separate;
- ordinary locations do not become separate services without a distinct access
  path;
- conflicting geography prevents an automatic merge;
- ambiguous pairs remain unresolved;
- source/pass provenance survives merging; and
- consolidation is deterministic regardless of response import order.

### Stage 6 — Retrospective recovery report

Implementation:

- close the focused job before revealing the target manifest to evaluation;
- compare consolidated identities with the nine primary and two secondary
  targets;
- allow Codex to adjudicate ambiguous or equivalent matches with evidence;
- store an immutable report containing target classifications, successful focus
  keys, source paths, new candidates, duplicate counts, and unresolved misses;
- derive proposed research lessons without activating them; and
- display a concise completion summary in Scout.

Tests:

- target data cannot be read through assignment endpoints before job closure;
- exact, equivalent, parent-only, ambiguous, and missed outcomes validate;
- every target receives exactly one outcome;
- manual adjudication requires a note and evidence;
- report generation is deterministic;
- report hashes change if an outcome changes;
- proposed lessons remain inactive; and
- a negative experimental result remains a valid, reportable outcome.

### Stage 7 — Release verification

Implementation:

- update README and product design to describe only implemented behavior;
- increment Scout to v0.44.0 and increment its build;
- add accurate user-facing release notes;
- run the complete Python test suite;
- run the focused browser/manual smoke test against a copied database;
- verify restart during a pending and completed pass;
- verify the ordinary four-AI path still works; and
- commit and push source, documentation, and tests without generated artifacts or
  live data.

Tests and checks:

- `python3 -m unittest discover -s tests` passes;
- the v0.43.1 database copy opens and migrates;
- a new focused Employment job completes end to end;
- the retrospective report is reproducible;
- Scout restarts without repeating completed work;
- current candidate-package and review-file tests pass;
- ChatGPT schedule and cooldown tests pass;
- no live SQLite file, candidate ZIP, resource package, or `auto*.html` is staged;
  and
- the pushed commit contains the same version and build reported by Scout.

## v0.44.0 acceptance gates

### Software gate

The release is complete when:

- all stages are implemented and tested;
- the current four-AI workflow remains compatible;
- focused jobs resume without duplication;
- target identities cannot leak into research assignments;
- consolidation and evaluation are deterministic;
- negative findings are preserved rather than hidden;
- no lesson becomes active automatically; and
- the release is versioned, committed, pushed, and verified.

### Experimental gate for proceeding to v0.45.0

The software can succeed even if the research hypothesis fails. Before running
the experiment, Michael and Codex should agree on the advancement threshold so
the result is not judged after the fact.

Recommended threshold for discussion:

- recover at least eight of the nine primary direct-service targets as exact or
  credible equivalent services;
- recover at least one target through each materially represented missed search
  branch;
- preserve geography and public-access safeguards;
- avoid a large rise in duplicate or plainly marginal candidates; and
- explain every miss and every ambiguous match.

The two secondary Provo v1-only targets are diagnostic and do not count toward
the primary threshold because direct-service curation later omitted them.

Failure to meet the threshold does not invalidate v0.44.0. It means v0.45.0
should not assume that Codex can replace the four-model union without another
playbook revision.

## Test strategy across later releases

### v0.45.0

- sealed shadow-result access tests;
- held-out category selection and version isolation;
- duplicate-adjusted source-contribution calculations;
- one curation policy applied to every comparison arm;
- reviewer-outcome import fixtures;
- cost/time and marginal-contribution report determinism; and
- no access to shadow identities before Codex closes its result.

### v0.46.0

- every non-Miscellaneous category has valid focused guidance;
- generic focus-runner tests across unlike category shapes;
- configurable researcher-role tests;
- whole-office resume and completion tests;
- ChatGPT delay/cooldown tests when enabled;
- no ChatGPT pacing when it is disabled; and
- no curation start before the configured research plan is complete.

### v0.47.0

- candidate-to-proposal-to-package provenance fixtures;
- successive-package addition, edit, merge, split, category, For, and removal
  cases;
- explicit distinction among rejection, duplication, replacement, movement,
  research-further, and unexplained absence;
- no inference of closure from absence or a broken URL; and
- no pooling across incompatible playbook or curation versions.

### v0.48.0

- lesson state-transition authorization;
- exact proposed assignment diff rendering;
- new version required for activation;
- rollback to a prior playbook;
- held-out regression protection;
- no activation from one weak example; and
- full evidence and approval audit history.

### v0.49.0

- field-level maintenance evidence;
- current, changed, moved, possibly closed, and unverifiable fixtures;
- broken-page-with-live-program regression;
- trusted package remains unchanged until explicit acceptance;
- accepted changes export through the normal package pipeline; and
- maintenance history and last-verified provenance survive later packages.

## First-release decisions and result

Michael approved these v0.44.0 decisions before implementation:

1. The nine surviving direct-service proposals are the primary recovery targets.
2. The two Provo v1-only proposals remain secondary diagnostics.
3. Eight of nine exact-or-equivalent recoveries is the advancement threshold.
4. Codex-focused research is experimental and does not replace the four-AI
   default in v0.44.0.
5. The experiment runs for both Mesa and Provo Employment rather than only one
   location.
6. A credible equivalent local service counts separately from exact rediscovery
   and requires evidence.
7. Scout may add narrowly named focused-research tables but must not reactivate
   legacy optimizer tables.
8. Section 02 shows operational progress; detailed evaluation remains behind a
   compact result control rather than enlarging the main screen.
9. Stephanie's later feedback may revise curation but does not block this
   research experiment.
10. v0.44.0 stops after producing the retrospective report and does not begin a
    blind category comparison automatically.

The completed retrospective recovered all nine primary targets and both Provo
secondary diagnostics as exact matches. It required no credible-equivalent,
parent-only, ambiguous, missed, or human-adjudicated outcomes. The approved
eight-of-nine gate was therefore met at nine of nine. This result supports
proceeding to the separately authorized v0.45.0 blind comparison; it does not by
itself replace the four-AI production workflow or activate any proposed lesson.

## v0.45.0 implementation plan and completed result

### Stage 0 — Seal the held-out comparison

- preserve one exact Provo package, curation policy, four completed shadow runs,
  and their response hashes in a versioned fixture;
- select Housing, Medical/Dental/Vision, Clothing/Household, and Transportation
  because their service channels and direct-service boundaries differ; and
- reject the experiment if the package, curation result, response set, or policy
  changes.

### Stage 1 — Generalize focused research without changing production

- allow a focused job to name a category and experiment mode;
- add five fixed focus passes plus one deterministic gap pass for every held-out
  category;
- preserve the exact assignment, candidate manifest, contribution, pass focus,
  consolidation, and negative result; and
- keep the normal four-AI workflow and all active playbooks unchanged.

### Stage 2 — Enforce the blind boundary durably

- store comparison studies and category state in SQLite;
- expose only response counts, lead counts, and seals while Codex researches;
- require every Codex pass and gap pass to close before reveal; and
- revalidate every shadow response hash at reveal time.

### Stage 3 — Apply one source-hidden review

- combine duplicate-adjusted identities without exposing model attribution;
- review every candidate against the same smallest-set direct-service policy;
- record curated, omitted, already-known, needs-research, and explicit duplicate
  outcomes; and
- record decision, edit, adjudication, and elapsed-review counts.

### Stage 4 — Report evidence and progress

- calculate submitted leads, duplicate-adjusted identities, curated identities,
  survival rate, and model-only marginal curated identities;
- report Codex versus the four-AI union by category and in aggregate;
- show a compact sealed/revealed/completed metric in Scout Section 02; and
- treat the report as evidence for a subscription decision, not as authority to
  disable a researcher.

### Stage 5 — Verify and release

- test sealed access, changed-response rejection, restart-safe state,
  source-hidden assignments, complete dispositions, duplicate rules,
  deterministic reporting, APIs, progress, and existing workflows;
- preserve the immutable fixture and completed report in source control while
  excluding the live database; and
- release as Resource Scout v0.45.0 build 11.

### Completed blind result

The experiment closed 54 Codex leads into 53 identities before the four-AI
identities were revealed. The source-hidden union contained 130
duplicate-adjusted identities, of which 86 survived curation.

- Codex: 51 duplicate-adjusted identities, 45 curated, 88.24% survival, and 17
  marginal curated identities.
- ChatGPT: 46 identities, 34 curated, 73.91% survival, and 4 marginal curated
  identities.
- Grok: 55 identities, 37 curated, 67.27% survival, and 12 marginal curated
  identities.
- Claude: 41 identities, 27 curated, 65.85% survival, and 2 marginal curated
  identities.
- Perplexity: 41 identities, 31 curated, 75.61% survival, and 9 marginal curated
  identities.

Codex was the strongest individual researcher: it produced the most curated
identities and the highest survival rate. It did not match the union. Codex
contributed 45 curated identities, the four-AI union contributed 69, 28 were
shared, 17 were Codex-only, and 41 were four-AI-only. The result therefore
supports Codex-first research with challengers, but not a Codex-only production
default. Perplexity made a material marginal contribution in this sample.
Claude made the smallest marginal contribution, but four held-out categories in
one location are not enough to disable it automatically. The next release must
use this evidence when defining configurable primary, challenger, shadow, and
disabled roles and must preserve a challenger path until whole-office evidence
supports a narrower roster.

## v0.46.0 implementation plan and decisions

### Stage 1 — Retire the completed comparison runtime

- preserve the v0.45 fixture, immutable report, and historical design record;
- remove blind-study tables from new databases and remove its endpoints, UI,
  implementation module, and runtime-specific tests; and
- treat the comparison as evidence, not a recurring product mode.

### Stage 2 — Generalize category playbooks

- retain the specialized Employment, Housing, Clothing/Household,
  Medical/Dental/Vision, and Transportation playbooks;
- give every other non-Miscellaneous category a readable common focused
  strategy combined with its own JSON scope and exclusions;
- create a deterministic gap pass from actual pass yields and candidates; and
- snapshot the exact strategy, playbook version, assignments, and manifests in
  durable focused jobs.

### Stage 3 — Configure researcher roles

- use a readable versioned roster with exactly one primary;
- default Codex to primary, ChatGPT/Grok/Perplexity to challenger, and Claude to
  shadow;
- give each challenger or shadow one adversarial assignment after Codex closes
  its gap pass;
- include challenger responses in the candidate run, but retain shadow
  responses outside it as non-blocking evidence; and
- give disabled researchers no assignment and no pacing.

### Stage 4 — Whole-office orchestration

- prepare all non-Miscellaneous categories in connected-package order;
- process only the first incomplete category;
- resume immutable assigned passes and external assignments after restart;
- close a category only after Codex and every configured challenger complete;
  and
- refuse curation while any configured Codex-first category remains incomplete.

### Stage 5 — Pacing, progress, tests, and release

- reduce the random ChatGPT baseline from 10–20 to 5–10 minutes because the
  latest production run showed no automation warning;
- retain overdue-immediate delivery, explicit-reset precedence, one active
  assignment, and the 30-minute throttle cooldown;
- show whole-office Codex-first category/pass/lead progress in Scout Section 02;
- test playbook coverage, roster roles, disabled pacing, restart-safe state,
  challenger versus shadow inclusion, whole-office completion, curation gating,
  APIs, and existing browser behavior; and
- release as Resource Scout v0.46.0 build 12.
