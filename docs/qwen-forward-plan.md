# Qwen forward optimization plan

Status: all seven approved optimization steps are complete. Expanded comparison
v9 selected 8-bit Qwen, and the corrected four-stage Housing result retained 38
unique usable identities with no verifier-completeness failures. This document
remains the benchmark record. Michael separately authorized production cutover
on 2026-08-24; follow Phase 2 in `local-dsh-qwen-plan.md` for that work.

## Goal

Determine whether the redesigned, unmetered Resource Scout workflow with 8-bit
Qwen can find a broad set of real, actionable programs while keeping every claim
traceable and safe for Curator and phone vetting. The frozen DeepSeek baseline,
all earlier Qwen runs, and every historical failure remain immutable comparison
evidence.

The current-status sweep is category-neutral and may include identities routed
to every playbook stage. Its schema-2 cache embeds the exact query plan; the
freeze path refuses a cache without that snapshot rather than rebuilding a
Housing-only subset.

Recorded all-stage audit (2026-08-23): the final discovery ledger contains 139
persisted unmetered searches, 938 fully dispositioned URLs, and 44 resolved or
preserved identities. The qualification manifest reports 27 eligible identities,
9 review-required identities, and 8 noncandidates across all four Housing stages.
For urgent access, 17 are eligible, 5 remain review-required, and 4 are retained
noncandidates. Relative to the older 22-packet urgent corpus, the new gate keeps
15 eligible, holds CAAFA, DVSTOP, Mesa House, Mesa I-HELP, and Washington Street
Shelter for unresolved geography or intake/current evidence, and retains the CoC
referral system and Lost Our Home pet-care program as noncandidates. The targeted
branch adds the two new eligible coordinated-entry access points, producing the
final 17. SafeDVS and the former La Mesita family shelter are explicitly retained
as inactive identities rather than silently disappearing.

The immediate endpoint is a complete four-stage Housing calibration followed by
an explicit decision to optimize again, stop, or request authorization for the
remaining 19 benchmark categories. No production default, live database, normal
Curator inbox, or TSO Resources package changes automatically.

## Category-neutral architecture

Housing and Mesa are the first calibration configuration and regression fixture,
not the architecture. Every reusable verifier, promotion rule, entity role,
saturation rule, prior-result manifest, referral edge, evidence record, audit,
and Curator linkage must be category- and location-neutral. Required fields,
service needs, source families, geography, and stages come from the selected
package schema, category playbook, and versioned run configuration.

Reusable code must not contain Housing field lists, Mesa provider names, the four
Housing stage keys, or benchmark-specific queries. Those belong in fixtures and
configuration. Tests must include at least one non-Housing category fixture before
the reusable implementation gates pass.

Playbooks are versioned configuration, not prompt prose that reusable code may
silently replace. Before freezing the revised Housing corpus, audit its branches,
service needs, populations and barriers, authoritative source families, geography,
entity roles, critical and supplementary fields, gap-search terms, and
current-status signals. After the Housing/Curator cycle, validate the generic
playbook contract and audit each category before any 19-category run. Do not
speculatively rewrite every playbook before that evidence exists.

## Approved decision rules

Scout uses hard candidate gates before ranking breadth or completeness. A lead is
not a counted candidate unless all of the following are true:

- the organization-plus-program identity is resolved well enough to avoid
  bundling or fragmentation;
- the category is correct and there is credible evidence of service relevance to
  Mesa or the configured service area;
- no factual claim is invented, transferred from another program, or silently
  inferred;
- at least one adequate source supports the program's existence and relevance;
- uncertainty is explicit;
- a plausible client access or follow-up path exists; and
- the same program is not already represented in the source package.

After those gates, make decisions in this order:

1. breadth of genuinely new, actionable candidates;
2. authority and adequacy of the supporting sources;
3. completeness of access-critical fields;
4. completeness of supplementary fields; and
5. elapsed time.

Accuracy, identity, jurisdiction, and safety are gates rather than quantities that
can be outweighed. An explicit unknown is incomplete, not inaccurate. Unknown pet
policy or another supplementary field does not discard an otherwise valid
candidate. Unknown service geography, program identity, or whether a purported
program actually exists blocks candidate promotion until resolved. Time may break
only a genuine quality tie.

## Candidate-count integrity

Searches and models produce leads. Scout alone promotes leads to counted
candidates through deterministic identity, evidence, geography, package, and
actionability checks.

Count one resolved, package-eligible organization-plus-program identity. Split
records only when authoritative evidence names separate programs and shows a
material distinction such as service, population, intake, status, jurisdiction,
or independently administered facility. Different pages, addresses, telephone
numbers, or application offices alone do not justify multiple candidates.
Multiple sites normally remain access locations attached to one program.

Every resolved entity receives one role:

- `direct-program`;
- `access-assessment-service`;
- `service-location`;
- `referral-system`;
- `directory`;
- `organization-only`; or
- `unresolved-lead`.

An access or assessment service counts only when it is itself a distinct,
actionable service with a supported intake function, such as coordinated entry or
211. A directory, organization-only record, mere application office, uncertain
program boundary, possible duplicate, or weak named lead does not count. Preserve
those records for follow-up without allowing them to inflate candidate totals.

Generic directories create leads only. A program-specific authoritative referral
may support promotion when Scout obtains corroborating current evidence. Report
the complete funnel separately: raw results, canonical URLs, leads, resolved
identities, package exclusions, noncandidate roles, evidence packets, verifier
outcomes, Curator dispositions, phone-vetted outcomes, and final-package
acceptances. The strongest usable-yield measure is a distinct resource accepted
into a later phone-vetted package.

## Preserved starting evidence

- Frozen DeepSeek baseline SHA-256:
  `0914c6278d36177cc29d75b297249815386355ceb9d634b1ac23372aa18c5491`
- Expanded reviewed corpus 6 SHA-256:
  `204ef0cbf2c7d889fc84f544c601bd2bd9b1543a9636a7a9195742c5270e6379`
- Frozen packet-set SHA-256:
  `876bc83ff280a154d1ec94c2139ed90531a3cdb81e2f1c32a5907b1223d75501`
- Model-neutral v9 report SHA-256:
  `dadc0d197341ea7fac2f7d548dd188771a569fcd0b09010507cd4966770b51a1`
- Revealed v9 decision SHA-256:
  `ae5470960eb477e57935f078c6cc808b56111d6056a411e01eb70afc93b8f968`
- Selected optimization input: 8-bit Qwen. Across the identical 22 packets it
  produced 7 passed, 15 needs-review, and 0 failed dossiers. All 22 are usable
  Curator material under the frozen policy. The 4-bit result was 1 passed, 18
  needs-review, and 3 failed, or 19 usable dossiers.
- The 8-bit run recorded 261 supported, 245 unknown, and 0 conflicting field
  states. The 4-bit run recorded 276 supported, 224 unknown, and 3 conflicting
  states. Quality selected 8-bit before timing was revealed. It took 49,148
  seconds versus 34,197 seconds for 4-bit; time did not affect the decision.

At this checkpoint the selected 8-bit configuration was an optimization input,
not a production selection. Michael later authorized production cutover on
2026-08-24; application 0.30.4 carries that decision into the normal service.

## Seven approved steps

### 1. Record the completed comparison and revised gates

Reconcile the handoff, benchmark, deterministic design, local runtime plan,
README, and this plan. Correct stale running-comparison and 4-bit-selection text,
the earlier apples-to-oranges DeepSeek comparison, and the incorrect claim that
the frozen DeepSeek Housing output omitted Justa Center and Salvation Army.

Gate: documentation agrees with the persisted database and v9 artifacts; frozen
baseline and source-package hashes remain unchanged.

### 2. Correct the verifier contract

The schema-validated extraction dossier remains Scout-owned. The verifier returns a
constrained field-by-field decision or patch rather than rewriting the complete
dossier. Allowed operations are:

- keep a validated field;
- downgrade it to explicit unknown;
- mark supported values as conflicting;
- attach a review finding; or
- report a material identity, attribution, geography, or evidence defect.

Scout applies only allowed operations and validates the result again. The
verifier cannot invent replacement facts, mutate frozen identity, alter sources,
or delete a field by omission. Every field required by the selected package schema
and category playbook receives a verifier decision.
If a decision is absent, Scout preserves the validated extraction state and adds
`verification-incomplete`, producing `needs-review` rather than a failed or
dropped candidate.

`failed` is reserved for a material identity conflation, wrong category or
geography, altered or invented source, unsupported safety-critical claim, or lack
of credible evidence that the candidate is real and relevant. Explicit unknowns,
ordinary conflicts, weak-but-usable sourcing, uncertain current status, and an
incomplete verifier checklist produce `needs-review`.

Category playbooks separately identify supplementary fields. A missing, unknown,
or weakly supported supplementary field never makes a candidate fail or removes
it from Curator output. In Housing, `petPolicy` is supplementary: even if the
verifier incorrectly reports an unknown pet policy as a material defect, Scout
ignores that attempted defect, preserves the field as unknown, and keeps the
candidate usable with a visible `needs-review` finding.

Gate: deterministic regression tests cover omission, every allowed patch,
forbidden mutation, restart/resume, and the actual Justa Center `petPolicy`,
Coordinated Entry `petPolicy`, and UMOM `serviceNeed` losses. The old runs remain
unchanged and the new policy receives a new provenance label.

Recorded outcome (2026-08-23): playbook library 1.2.0 now owns the factual and
supplementary field contracts; Housing adds `petPolicy` only through its category
configuration. The verifier returns a constrained decision patch, cannot rewrite
identity or sources, preserves omitted extraction fields, and cannot promote a
supplementary field to a candidate-blocking defect. Exact regression fixtures
cover the three historical omissions, and a Food integration test proves that
the reusable discovery and model pipelines derive stages and fields without a
Housing constant. The v9 comparison coordinator is now a read-only historical
report rebuild so it cannot accidentally run the new policy under old provenance.
The gate passed 160 Python tests (one skipped platform check), 20 JavaScript tests,
the frozen-artifact hash checks, and the stale-symbol trace for the replaced
whole-dossier verifier path.

### 3. Expand discovery without gaming candidate count

#### Continue the unsaturated coordinated-entry branch

Preserve corpus 6 and its 70 searches. Create a versioned query plan that reuses
the frozen base responses and appends an initial batch of five targeted,
referral-derived queries. Stop the appended branch after three consecutive
queries yield no new package-eligible identity. Add another bounded batch only if
the branch reaches its maximum while still producing eligible identities. Run a
deterministic current-status query for each new identity and report marginal
eligible yield, authority, duplication, noise, and routed later-stage identities.

#### Use preserved results as a lead manifest

Create a generic, versioned prior-result lead-manifest format. The initial Mesa
manifest may contain frozen DeepSeek Housing candidates and every preserved Qwen
Housing lead, including routed, rejected, and unresolved identities. Import only
organization/program names, aliases, URLs, and source-run/stage/date provenance;
never import historical factual claims as current evidence.

The initial harvest is a one-time calibration input. The generic manifest reader
remains available for future periodic Scout runs, but no DeepSeek-specific path is
permanent. Every imported lead must pass current search/fetch, identity resolution,
package exclusion, current-status, geography, actionability, and evidence gates.
Historical entries do not count as queries, saturation, current evidence, or
candidates merely because they exist.

#### Add a bounded authoritative referral graph

Add category-generic, resumable, one-hop referral expansion from direct-provider,
government, coordinated-entry, and authoritative referral sources. Persist every
edge as source page -> named program -> destination URL with nearby context.
Edges are leads, never candidates. Fetch the exact current program page, resolve
identity and stage, check the package and current status, and retain provenance.
Bound edges per source, canonicalize destinations, deduplicate identities, and do
not traverse broad directories or a second hop in this calibration.

Gate: fixtures cover branch saturation, historical manifest provenance, loops,
duplicate edges, parent organizations with multiple programs, access locations,
wrong-stage routing, stale or successor names, broad directories, irrelevant
partners, confidential shelters, resume behavior, candidate-count roles, and a
non-Housing playbook. Missing playbook sections must fail closed rather than fall
back to Housing defaults. A
live unmetered discovery-only run must improve eligible yield or demonstrate
branch-level saturation before any model inference.

Implementation checkpoint (2026-08-23): `candidate-qualification-gates-v2` is
active in the reusable discovery pipeline. Identity review must explicitly record
role, geography, target-category fit, actionability, current status, and evidence
readiness. Scout derives
promotion deterministically and reports eligible, noncandidate, and
review-required identities separately. Only `direct-program` and independently
actionable `access-assessment-service` roles can produce packets; service
locations, referral systems, directories, organization-only records, package
duplicates, and weak or unresolved leads remain in the ledger. A directory-only
source cannot back an eligible packet, and inconsistent qualification decisions
for the same identity fail closed instead of becoming query-order-dependent.
Category fit is independent of supplementary completeness: adjacent-support and
wrong-category programs cannot inflate yield, while missing Housing `petPolicy`
cannot block an otherwise qualified Housing candidate.
`prior-result-leads-v1` is also implemented and persisted: historical names and
URLs produce no candidate or evidence by import, every lead receives a current
search, and the manifest is hashed into the corpus ledger. The reproducible
one-time Mesa v1 harvest contains 623 deduplicated leads from 22 frozen DeepSeek
and Qwen run-stage sources. `authoritative-one-hop-referrals-v1` now persists and
resumes bounded source-to-program-to-destination edges, rejects directories,
loops, duplicates, category/location mismatches, and unknown playbook stages, and
keeps edge context out of candidate evidence. Housing and Food integration
fixtures prove that only a fresh destination fetch can support a promoted
identity. The first five-query, versioned coordinated-entry depth branch ran
against unmetered DDGS while reusing all 112 prior responses. It returned 38 raw
results and 30 URLs not present in the parent review. Current-source review found
two genuinely new eligible urgent-access identities (Native American Connections
and Community Bridges coordinated-entry access points), one new routed
stabilization identity (MesaCAN Rent and Utility Assistance), and one newly
preserved inactive access identity (SafeDVS). The other 26 URLs were policy
material, directories, duplicates, or irrelevant results. Queries three through
five yielded no new eligible identity, satisfying the three-query saturation rule;
no additional batch is justified.

`candidate-qualification-gates-v2` also has an exact-coverage, identity-keyed
manifest workflow. It applies one audited gate decision to every URL occurrence
of a normalized identity and fails on missing, extra, invalid, or identity-changing
entries. Referral evidence separately persists the actual page organization and
program, preventing a referring page from being mislabeled as candidate-authored
evidence.

The first live Mesa graph now has an exact edge-keyed
`reviewed-referral-destinations-v1` decision manifest. Its 16 edges resolve to 7
candidate decisions, 6 unresolved leads, and 3 excluded dead or misdirected
destinations. Candidate evidence must include the exact destination and an exact
reviewed excerpt present in the fresh fetch; referral context alone cannot
qualify a program. A referral-only live pilot produced 6 urgent packets and
routed the seventh candidate, MesaCAN Rent and Utility Assistance, to
stabilization. Four urgent identities were new to the prior qualification
manifest: Community Bridges PATH Outreach, Native American Connections HomeBase
Youth Services, UMOM Halle Women's Center, and the Phoenix VA Community Resource
and Referral Center. The same run retained every unresolved and excluded edge
without counting it. The one-time 623-lead historical sweep is independently
resumable and preserves 75 completed current searches. On 2026-08-23 Michael
removed the remaining historical haystack from the calibration scope after
repeated unmetered DDGS connection timeouts. Preserve the manifest, completed
searches, and exact resume point, but do not treat the 548 unchecked leads as
negative findings or restart the sweep automatically. The current calibration
may proceed using the completed current-status search, coordinated-entry, and
authoritative-referral branches. Its final claim is bounded to those executed
branches; it must not claim that every preserved historical DeepSeek and Qwen
lead was refreshed.

### 4. Freeze the revised first-stage corpus

Resolve all newly discovered and preserved leads under the approved gates. Run
current-status checks, acquire and classify current evidence, perform package
exclusions, route non-urgent identities to later Housing stages, and freeze one
immutable packet per counted urgent-access identity. Preserve weak and unresolved
leads outside the candidate count.

First audit and version the Housing playbook configuration. Do not freeze a corpus
whose required branches, candidate roles, field criticality, or gap-search rules
remain implicit.

Preparation checkpoint (2026-08-23):
`optimization-playbook-audit-v1` now makes that contract explicit and is consumed
by the revised freeze path. The first Mesa Housing audit binds the exact coverage
plan, playbook source hashes, 10 coverage branches, 2 dynamic operational
branches, service needs, populations, barriers, source families, geography,
candidate roles, required/access-critical/supplementary fields, gap triggers,
current-status signals, and reviewed referral components. Food regression proves
the validator is category-neutral. The audit confirms that pet policy is
supplementary; it does not change candidate gates or rewrite the category
playbook. Final freezing may proceed from the completed in-scope branches. The
preserved historical branch is explicitly outside this calibration's required
scope; its unchecked leads remain unknown rather than exclusions.

Step 5 preparation also removed the old Housing-only gap list from the model
runner. Required coverage tags and deterministic follow-up queries now come from
the validated playbook audit; the qualification manifest can preserve reviewed
coverage tags without affecting promotion. The current urgent audit explicitly
checks adult, family, domestic-violence, youth, medical-respite, veteran,
disability-access, animal-barrier, transportation, and language-access coverage.
The selected runner refuses an audit hash that differs from the frozen discovery
configuration.

Recorded outcome (2026-08-23): discovery run 31 froze superseding corpus 8 with
21 qualified urgent-access packets and 61 current evidence sources. It executed
94 queries over all 11 audited branches, retained 46 resolved or preserved
identities, routed 16 identities outside urgent access, and preserved 9
review-required and 7 noncandidate identities outside the packet count. The
corpus and packet-set SHA-256 values are respectively
`ab01e4ae11be0727593bfa8ea6372ba8f05ca324c7232487d3294de4f62207b0`
and `57ec18618856491e339cfd0ccb6dc11eada24742e07d3c40f4e47be716e46ac6`.
The frozen configuration SHA-256 is
`0ddb2c5ed0dcb3c92e530dd07ad728053c515bde07d246f7f3f2684b7d236ec3`.
Reviewed coverage tags now correctly identify adult, family,
domestic-violence, youth, veteran, coordinated-entry, and transportation paths;
medical respite, disability access, animal barriers, and language access remain
real targeted gap-search needs. Partial runs 27, 28, and 30 and the earlier
frozen corpus 7 remain preserved rather than overwritten. The final freeze used
stable current excerpts for pages with shallow, stale, or intermittently loaded
content and did not weaken identity, geography, source, or actionability gates.

Gate: all required coverage branches have a recorded terminal state; every packet
has one resolved identity, an eligible role, Mesa-relevance evidence, a plausible
access path, and current evidence; all hashes and runtime versions are recorded.

### 5. Validate selected 8-bit extraction and verification

Run only the selected 8-bit model over the revised first-stage frozen packets
using the corrected verifier policy. Preserve raw outputs, deterministic patches,
findings, explicit unknowns, usage, retries, and timing. Do not rerun 4-bit unless
a later controlled question requires it.

Gate: no true deterministic failures; all verifier fields have decisions or an
explicit `verification-incomplete` review finding; source and field quality do not
regress merely to increase candidate count. Only then may the four-stage Housing
configuration be locked.

Recorded outcome (2026-08-24): run 32 completed all 21 selected 8-bit extraction
and verification packets without retry. Application `0.24.0` separates
candidate-fatal defects from field defects that Scout can quarantine while
retaining a truthful candidate, preserves verifier-corrected source bindings and
genuine conflicts, and treats resolved verifier diagnostics separately from
unresolved review findings. The original 7 passed, 10 needs-review, and 4 failed
derived interpretation remains in immutable revision source snapshot
`06ef0ccd6247395b120932e80b6737c7af6e017f22f7ca58e4f5a6e93912630e`.
Recomputation from the same raw outputs, with zero model, search, or fetch calls,
produced 8 passed, 13 needs-review, and 0 failed dossiers, with 295 supported,
186 unknown, and 2 conflicting fields. Derived snapshot
`8b8f0f505ba71e42367e851ec6c510f78bff7a471fd6584f642053201c1c4c91`
passes the quality gate. All 21 candidates are usable Curator material. The four
planned coverage-gap queries remain separate from candidate eligibility. Step 5
is complete.

### 6. Validate Curator and iterative package integration

First test the isolated optimization export path. Passed and needs-review
candidates must reach Curator; failed and noncandidate leads must not. Preserve
findings, evidence, unknowns, conflicts, source/configuration/package provenance,
stable candidate IDs, and deterministic generated-resource IDs. Research-model
behavior, the live database, and production DeepSeek execution remain unchanged.
Human curation belongs to Curator for every model; Scout must not retain a second
decision or package-preparation path.

Use all final first-stage candidates for the Curator pilot rather than a favorable
sample. Record dispositions for duplicates, fragments, access points, directories,
wrong geography/category, weak leads, research-further cases, and candidates
prepared for ordinary phone vetting. Preserve deterministic candidate -> packet ->
Curator draft -> additions resource -> final-package resource links and the before
and after complete packages.

A source-package merge or live Curator mutation still requires Michael's explicit
authorization. After an authorized normal merge, run a separately labeled second
Scout cycle using the new package as its exclusion set. Report already-merged
exclusions, distinct programs at the same organization, recurring weak leads, new
eligible yield, and branch saturation. Do not activate deferred model lessons.

Gate: export and provenance tests pass; observed usable yield is based on normal
Curator/phone-vetting outcomes and final-package acceptance, not model self-rating.

Preparation checkpoint (2026-08-23): the isolated export and outcome path is now
category-neutral. Curator titles, assignments, labels, draft categories, and
final-package imports use the run's selected category; a Food regression guards
against Housing leakage. New candidate and generated-resource IDs bind the locked
configuration hash to the immutable packet SHA-256 rather than database row
numbers. Packet row IDs remain in provenance for local inspection, and the
outcome reader recognizes both the new content-linked resource ID and the legacy
row-linked ID so already-vetted packages are not stranded. Failed dossiers and
noncandidate leads remain excluded from this export. This completes deterministic
preparation only; the all-candidate Curator pilot, phone vetting, source-package
merge, and iterative second Scout cycle have not been performed. Live Curator or
source-package mutation still requires Michael's explicit authorization.

Operational workflow checkpoint (2026-08-24): Curator schema 10 and work schema 2
make curation additive rather than exhaustive. Every newly exported DeepSeek or
Qwen candidate begins Pending. Ready for package is the positive package action;
Research further, Duplicate/already known, Wrong category, and Reject are optional
outcomes and require no explanation. Absence from a package remains Pending, not a
negative result. Saving a package archives included candidates from the active
queue while preserving their complete state, outcome history, deterministic
resource linkage, edits, and package history. Schema-1 saved work migrates on
open. Scout's Accept/Reject, relationship-assessment, generated-resource editing,
and direct-package UI and HTTP routes were removed; legacy database records remain
readable for compatible Curator export. The Editors title and Print/Ready control
height are corrected. The workflow gate originally passed 209 Python tests with one optional
live-package skip and all 20 JavaScript plugin tests. Production Scout was
restarted and a real DeepSeek Housing Curator downloaded through its private
Tailscale URL reported schemas 10 and 2 and contained no stale Scout-decision UI.
The isolated comparison command now accepts saved work-schema-2 Curator JSON,
validates the locked review, candidate set, category, and package identity, and
distinguishes Pending, Ready, packaged, Research further, Duplicate, Wrong
category, and Reject from final-package acceptance. Final-package presence wins
over an older Curator state. Canonical work hashes permit successive immutable
outcome reports for the same run and package while preserving schema-2 reports.
The non-Housing integration regression passes Curator-JavaScript-generated Food
work and its additions-only package directly into the Python outcome reader. It
also proves that the generated resource recovers its original organization and
program for exact same-program exclusion in the next Scout cycle. Package identity
recovery prefers explicit fields, then Curator's labeled Resource details, and
uses the resource name only as a compatibility fallback. Migration and
mixed-outcome tests also pass. The all-candidate Qwen pilot, phone
vetting, source-package merge, and iterative second Scout cycle remain pending.
The subsequent stale-path audit removed Scout's unreachable accepted-resource
manager and its decision, generated-resource editing, relationship-assessment,
and package-building storage mutations. Historical rows and generated drafts
remain read-compatible for Curator export. Playbook configuration now supplies
category-specific supplementary draft fields. Package upload no longer requires a
Housing category. The exact Mesa Housing query matrix has been removed from the
reusable optimization primitives and isolated in
`optimization_housing_calibration.py` as calibration-only configuration. The
unreachable legacy Markdown renderer and orphaned selectors left behind by Scout's
structured-stage and Curator-owned-vetting transitions were removed in the final
UI dead-code pass. The
current full suite passes 212
Python tests with one optional skip and all 20 JavaScript plugin tests.

All-candidate export checkpoint (2026-08-24): the completed Step 5 result exports
all 21 usable run-32 candidates in one 1,063,237-byte Curator, with 21 unique
candidate IDs, 21 unique generated-resource IDs, 8 passed statuses, 13
needs-review statuses, and zero candidate-fatal defects. It binds the selected
8-bit run, corpus, configuration, source package, and
`verifier-candidate-salvage-v1` derivation. Export SHA-256
`7562ffb9eafe7b1a981509eefcb2b7e6d352b77b47823c1355ba696324faafaa`.
The export and provenance portion of Step 6 passes. Normal phone vetting, saved
work, package acceptance, merge, and the iterative second Scout cycle remain
pending; their results must come from Curator and the final package, not model
self-rating.

### 7. Complete Housing calibration

Lock the 8-bit artifact, verifier and extraction policies, playbook, query plan,
limits, stopping rules, package hash, and runtime versions. Run all four Housing
stages in the isolated benchmark database with fine-grained checkpointing. The 16
identities routed by the authoritative completed discovery run 31 are starting
leads for stages 2 through 4, not prequalified candidates: 9 were eligible in the
earlier stage, 4 required review, and 3 were noncandidates. Every one must pass a
fresh search, identity, geography, current-status, actionability, evidence, and
package-exclusion decision for its target stage.

Preparation checkpoint (2026-08-24): application `0.25.0` adds distinct,
versioned Mesa Housing calibration query plans for stabilization, specialized
housing, and long-term/gap review while preserving the frozen urgent plan. The
reusable cache boundary consumes an explicit validated query plan and is covered
by a Food regression. Corpus freezing and model execution derive category,
stage, location, regional scope, playbook, and labels from the frozen inputs.
Playbook-audit schema 2 permits a stage to explicitly declare that it has no
reviewed referral graph instead of requiring a fake Housing component. A
read-only routed-stage exporter emits only names, aliases, URLs, and immutable
run provenance; current qualification facts cannot enter the manifest, and each
lead receives its own current search before it can become a candidate.
The real run-31 export produced exactly 5 stabilization leads (2 routed, 1
needs-review, 2 rejected), 6 specialized-housing leads (5 routed, 1
needs-review), and 5 long-term/gap leads (2 routed, 2 needs-review, 1 rejected).
Their manifest SHA-256 values are respectively
`e9a7e15a6e6420dd75d953e5cb05ae268eb08d50585a469063d112a7413eef4d`,
`bbe7821f341774c543e13e66c8308a3f8a095668b55c1de7fb70dc3be76c1b35`,
and `e79ffba82a00ada80a00a90ec9d3214bf91246924e21e7c728f59d3e5b7d930d`.
The three fresh DDGS ledgers then completed 118 unmetered searches: 35
stabilization searches with 192 unique URLs, 42 specialized-housing searches
with 248, and 41 long-term/gap searches with 243. Their query-plan SHA-256 values
are `e2a5869f3034aa45b4caeb9ecfac3bca2d45681f3038cc6b03d5c60cb0394227`,
`048025262652d427dba9b5e1133275655d8f17ff6e6f6c9b67697353734ad466`,
and `fe1951c7bb15011db4336fe6db2fd4280e363f531ba915819020c93265239946`;
their response-cache hashes are
`31b9ca06310cc7d8b2e96e78b4844b62d17e45dd1ce7a2e8abe2b18b7157f40a`,
`6598140da4e61f55773dc5dd2ba39e09b980f55cb2438e5de5b5bd8fb36f4920`,
and `91d087202d25420f242aba5ebd8a0b8abf7501e0bbc29efbf769939f8776e19f`.
The stage URL sets contain 618 unique URLs after cross-stage overlap. The first
conservative review pass excluded 165 obvious platforms, ordinary listings,
wrong-geography results, and unrelated content. Application `0.26.0` then added
an exact-result reuse gate: only a previous exclusion with the identical URL,
title, and snippet may carry forward. It reused 5, 14, and 8 exclusions across
the three stages; it copied zero candidate decisions, and every changed result
remained Pending. The completed exact ledgers now disposition all 683 stage URL
occurrences. Stabilization preserves 16 identities: 8 eligible, 2
review-required, and 6 noncandidates. Specialized housing preserves 32
identities: 11 eligible, 11 review-required, and 10 noncandidates. Long-term and
gap review preserves 26 identities: 12 eligible, 8 review-required, and 6
noncandidates. Their final review SHA-256 values are
`e610a8bf82e96d394c4e1358151dfd9fb3293556f7c1c5f8cfc7dbcd58708877`,
`21fc0e57c7c0f57e6cebe464b0db3b163815a9f062d20aca5e16a85db6aa2d12`,
and `2bd5d54d3e961e834e8765218a04679b3b30f594e46d968ab2352fe57f6ce7e7`.
The matching schema-2 playbook-audit hashes are
`0b91425c682ac0ba4a7c5596bf9e4377fe5dd2b088ea4162d6a08d6d4f2a4839`,
`35a9783a563335c131bca3120348b76cf3299c862027818d32e1e1c620be4c7a`,
and `39bafa353151452456bf48033dd0d6e057239bfe7c52616474303effd3a5aa94`.
They explicitly record that no referral graph was used, preserve unknown pet
policy as supplementary and nonblocking, and enforce one program identity
rather than one candidate per directory, access point, property fragment, or
evidence copy.

Application `0.27.0` closes the later-stage freeze handoff: a cache whose exact
query plan includes a prior-result lead-manifest hash must now receive the
matching `--prior-lead-manifest`, which is normalized and passed into discovery.
Missing, extra, or hash-mismatched manifests fail before a run is created. This
preserves routed-lead provenance without copying historical qualification facts.

Application `0.28.0` closes the corresponding model-run boundary for stages
without referral-graph expansion. Frozen configurations persist an absent graph
and review as the explicit sentinel `none`; playbook-audit normalization now
treats that sentinel as absence while continuing to validate real component
hashes. The regression test exercises the same schema-2, graph-free audit shape
used by the later-stage Housing corpora.

Frozen later-stage outcome (2026-08-24): runs 39–41 completed all 18 candidate
packets and 36 model operations without a retry, failed attempt, paid call, or
candidate failure. Stabilization was 4 passed/1 needs review, specialized was
2/3, and long-term/gaps was 4/4, for 10 passed, 8 needs review, and 0 failed
overall. The three quality gates passed. This is the immutable pre-correction
comparison point; it is not overwritten by the next run.

Review of those results found that the model was often reacting correctly to
weak upstream evidence: unsupported identity labels, a mid-sentence clip,
access-point/system attribution, fax/phone confusion, City pages clipped before
their body, and a search title concatenated with unrelated results. It also found
a missed verifier defect in a nominally passed packet: organization footer/admin
addresses had become program addresses and Phoenix service geography. The old
gap audit separately manufactured eight false gaps from pluralized/granular tag
names and already-completed operational checks.

Application `0.29.1` therefore adds a category-neutral reviewed evidence contract
before the corrected model run. Each eligible source receives explicit authority,
current-page identity receipts, and a complete-page or one-or-more exact-section
selection. Current page headings replace search-result titles; multiple sections
can preserve separated candidate-wide facts while excluding property/footer
blocks. Ordinary search results and authoritative referral destinations share the
same validator. Extraction and the independent verifier receive explicit contact,
entity-boundary, footer/admin-address, service-geography, and exact-program-URL
rules. Coverage needs now distinguish exact equivalent any/all tags from
operational checks, and combined population needs are split rather than allowing
one covered population to hide another.

Prepared evidence manifest hashes are
`959026d62a1766c5a4eee2309e723a999c60a418e3f6023ffde940e8ceeaa66e`,
`1c37f4773c95d3d339d8e6c94764641b1891db3a6c475ff2019a16b8a6030b56`,
and `20d06995267ede9cf9882565a8ae6de30c52c856a8387d829221b6cc1aa7a47b`.
Corrected audit hashes are
`5164f67f7fc2c36db20bd56d32ff2ebca2383bcd6607b3211a055ce1959f63c9`,
`187ab0b20e84c69d6ab0e16ea42a6dab2f7019d43cfed1676e7b28fc15cf72b7`,
and `c7242b95ff9a7c54ae069c22dda7363d31e339caf423395a9d66a6ecc50a0cf7`.
The corrected gap receipt contains 15 still-uncovered pathways rather than the
frozen report's 23; no search was rerun and no unresolved lead was converted into
a candidate to obtain that correction. Before the corrected corpus run, the full
repository suite passed 228 Python tests with one optional live-package skip and
all 20 JavaScript plugin tests.

Corrected runs 45–47 completed all 18 packets and all 36 extraction/verification
operations on their first attempt. The raw specialized 4/5 pass result exposed
one post-model validator defect: the immutable reviewed program-identity receipt
was not consulted when Qwen omitted the duplicate `source.supports` entry. The
`verifier-candidate-salvage-v2` correction accepts that receipt only for matching
organization/program identity fields and leaves every ordinary factual-field
evidence rule unchanged. It rederived specialized housing to 5/5 without search,
fetch, or model inference.

Application `0.29.2` adds the next generic evidence-usefulness boundary: every
additional phone number needs its source-supported purpose. A bare alternate
number is preserved and sent to human review; it is not deleted and does not fail
the candidate. `verifier-candidate-salvage-v3` rederived the completed runs without
external or model work. The final corrected result is 13 passed, 5 needs review,
0 failed, 265 supported fields, 149 unknown fields, and 0 conflicts. The five
reviews consist of three unlabeled alternate phone purposes, one thin but credible
source, and one program-name/geography identity question. All 18 candidates remain
usable, all three quality gates pass, and 15 honest coverage gaps remain explicit.

Compare the complete result with frozen DeepSeek Housing and every preserved Qwen
Housing run. Compare like stages and report the union and overlap only after
identity resolution; the historical DeepSeek total of 30 spans all four stages,
whereas corpus 6's 22 packets cover only stage 1.

Completed comparison (2026-08-24): the selected corrected four-stage Qwen result
contains 39 usable packets but 38 unique program identities because urgent packet
99 and specialized packet 134 are the same Native American Connections
coordinated-entry service. Twenty-four unique Qwen identities have a counterpart
in 18 DeepSeek records; 14 are Qwen-only. Twelve whole DeepSeek records and two
clearly separate named components inside otherwise matched DeepSeek bundles are
not represented by Qwen. The conservative resolved union is at least 52 service
identities or program families. Remaining multi-program DeepSeek records are not
split merely to raise the count. The reviewed mapping is
`docs/mesa-housing-identity-comparison-v1.json`, SHA-256
`6a1001782db7ecb11b7f8f27950f252f836e96f795aa9ee3e086a46fdd45c3f3`.

The gate decision is to retain 8-bit and stop model optimization. Do not start
the remaining categories. The next implementation stage must close alias-aware
cross-stage deduplication and produce one combined category-level Curator handoff;
then complete the intended category playbook audits and run one non-Housing pilot.
This was the gate result before Michael explicitly authorized production Qwen
cutover on 2026-08-24. Application 0.30.4 implements the separately documented
Phase 2 service cutover; it does not authorize the remaining 19 benchmark
categories.

Gate result: stop model optimization. Never start the remaining 19 categories
automatically.

Before any such authorization can be exercised, validate the generic playbook
contract against the Housing/Curator evidence and audit every intended category's
playbook. A category with an incomplete playbook remains blocked rather than
inheriting Housing behavior.

After step 7, pause for Michael's requested discussion of the three preserved
4-bit completeness failures. Do not silently reclassify them. Review whether
unknown pet policy should ever exclude a candidate, how `serviceNeed` should be
handled, and whether the new verifier contract resolves the failure mode without
weakening evidence requirements.

## Deferred DeepSeek v2 experiment

Do not place a DeepSeek verifier experiment ahead of the seven approved steps.
The redesigned deterministic Scout workflow could later be run with DeepSeek as a
separate, explicitly metered configuration. It must use the same frozen corpus and
must disable supplemental search for a controlled extraction/verification
comparison. The original DeepSeek baseline remains unchanged. No paid request or
hybrid fallback is authorized by this plan.

## Stop conditions requiring user attention

Stop and consult Michael if work would require a paid service, production or live
Curator mutation, a source-package merge, weakening a hard candidate or evidence
gate, discarding frozen evidence, accepting an unresolved material accuracy
defect, or authorizing the other 19 categories. Local implementation,
deterministic fixture tests, isolated unmetered discovery, selected local 8-bit
inference, and removable optimization exports may proceed autonomously after their
preceding gates pass.
