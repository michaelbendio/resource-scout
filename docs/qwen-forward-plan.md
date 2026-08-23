# Qwen forward optimization plan

Status: approved on 2026-08-23. Expanded first-stage comparison v9 is complete
and selected 8-bit Qwen for continued optimization. Steps 1 and 2 are complete;
step 3 is in progress. This is a staged benchmark plan, not a production cutover. Read
it with `qwen-optimization-handoff.md`, `qwen-optimization-design.md`, and
`mesa-qwen-deepseek-benchmark.md`.

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

The selected 8-bit configuration is an optimization input, not a production
selection. The existing opt-in local Scout route remains unchanged until a later
explicitly authorized cutover.

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
resumable and currently has 74 completed current searches. Because unmetered DDGS
is intermittent, Michael approved keeping step 3 formally open while step 4
playbook audit and freeze preparation proceed. This is a scheduling deferral, not
a completeness waiver: resume the same sweep opportunistically and integrate all
recovered candidates before final Housing completion in step 7. Do not restart
from zero, switch to a paid provider, silently skip a lead, or shorten the
manifest.

### 4. Freeze the revised first-stage corpus

Resolve all newly discovered and preserved leads under the approved gates. Run
current-status checks, acquire and classify current evidence, perform package
exclusions, route non-urgent identities to later Housing stages, and freeze one
immutable packet per counted urgent-access identity. Preserve weak and unresolved
leads outside the candidate count.

First audit and version the Housing playbook configuration. Do not freeze a corpus
whose required branches, candidate roles, field criticality, or gap-search rules
remain implicit.

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

### 6. Validate Curator and iterative package integration

First test the isolated optimization export path. Passed and needs-review
candidates must reach Curator; failed and noncandidate leads must not. Preserve
findings, evidence, unknowns, conflicts, source/configuration/package provenance,
stable candidate IDs, and deterministic generated-resource IDs. Normal Scout,
normal Curator, the live database, and production DeepSeek behavior remain
unchanged.

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

### 7. Complete Housing calibration

Lock the 8-bit artifact, verifier and extraction policies, playbook, query plan,
limits, stopping rules, package hash, and runtime versions. Run all four Housing
stages in the isolated benchmark database with fine-grained checkpointing. The 11
already routed identities from discovery run 19 are starting leads for stages 2
through 4, not prequalified candidates.

Compare the complete result with frozen DeepSeek Housing and every preserved Qwen
Housing run. Compare like stages and report the union and overlap only after
identity resolution; the historical DeepSeek total of 30 spans all four stages,
whereas corpus 6's 22 packets cover only stage 1.

Gate: make an explicit decision to optimize again, stop, or request authorization
for the remaining 19 categories. Never start those categories automatically.

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
