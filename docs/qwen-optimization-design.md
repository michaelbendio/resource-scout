# Qwen optimization deterministic design

Status: Checkpoints A through D are implemented. Expanded 22-packet comparison
v9 completed on 2026-08-23 and selected 8-bit Qwen for continued isolated
optimization. Forward-plan step 2 implemented a category- and location-neutral
field contract and replaced whole-dossier verification with a constrained
decision-patch contract.

This document fixes the data boundaries, persistence records, Housing regression fixtures, coverage matrix, stopping behavior, quality gate, and downstream ground-truth linkage before any new model run. It does not authorize Checkpoint B or production cutover.

## Decision order

Material program conflation, unsupported or transferred claims, incorrect
jurisdiction, wrong category, and source-to-field attribution errors are hard
gates. After those gates pass, compare genuinely new actionable candidates,
source authority and adequacy, access-critical completeness, supplementary
completeness, and finally time. An explicit unknown is incomplete but not
inaccurate. Time is diagnostic and may break only a true quality tie.

## Category-neutral boundary

The package schema, selected category playbook, location scope, and immutable run
configuration define fields, service needs, queries, and stages. Reusable code
must not contain Housing field lists, Mesa organizations, or the Housing stage
layout. Housing remains the first calibration fixture. At least one non-Housing
fixture is required for every reusable verifier, promotion, discovery-expansion,
provenance, and Curator-integration gate.

## Pipeline records

The migration adds the following isolated records. Existing `research_runs`, DeepSeek behavior, and the frozen baseline remain unchanged.

- `optimization_configurations` is an immutable, hashed snapshot of the model artifact and quantization; MLX and DSH versions; search and fetch providers and plugin versions; prompt-policy and playbook versions; source-package identity; target and stage; deterministic limits and stopping rules; and the complete query plan. The display label is not part of the hash. Changing quantization, a policy version, the package, a limit, or any planned query creates a different configuration.
- `optimization_runs` records a labeled discovery, model-evaluation, or end-to-end run and its current phase. A model-evaluation run must identify one frozen corpus.
- `optimization_checkpoints` records resumable phase-and-item state, attempt count, payload digest, status, and timestamps. Work resumes from the smallest incomplete item rather than restarting the stage.
- `optimization_coverage_branches` and `optimization_queries` preserve every required branch, purpose, planned query, execution outcome, novelty count, saturation state, failure, and explicit not-applicable reason.
- `optimization_discovery_leads` and `optimization_lead_queries` form the normalized discovery ledger while retaining every query/rank/URL route that found a canonical lead.
- `optimization_candidate_identities` and `optimization_identity_leads` preserve organization-plus-program identity, uncertain boundaries, possible renamings or duplicates, package-exclusion decisions, candidate role, geography, actionability, current status, evidence readiness, deterministic promotion state, and the lead evidence behind them.
- `optimization_evidence_sources` records authority, the program identity actually described by the page, bounded extract, retrieval metadata, and extract digest.
- `optimization_corpora` and `optimization_evidence_packets` freeze the ledger, identities, sources, and one-candidate packets by digest. The database requires a model attempt's packet to belong to the same corpus as its model-evaluation run. This prevents 4-bit and 8-bit from silently receiving different evidence.
- `optimization_model_attempts`, `optimization_candidate_dossiers`, and `optimization_verifications` retain every extraction and fresh-context verification attempt, raw output, parsed record, usage, errors, dossier, verified dossier, and findings.
- `optimization_comparisons` pairs exactly one 4-bit run and one 8-bit run on the same frozen corpus. Database constraints reject a mismatched quantization or corpus before a comparison record can exist.
- `optimization_audits` preserves coverage, candidate-completeness, quality-gate, and model-neutral comparison reports.

JSON payloads use canonical UTF-8 serialization with sorted keys and compact separators before SHA-256 hashing. Configuration snapshots are immutable in SQLite. Frozen corpus hashes are comparison inputs, not descriptive metadata.

## Identity and package exclusion

The identity key is normalized organization plus specific program. It is never organization alone.

- The same organization and same program is `same-program` and is excluded when already represented in the supplied package.
- The same organization with a genuinely different program is `different-program` and remains eligible.
- Unclear boundaries remain `uncertain-boundary`, `possible-renaming`, `possible-duplicate`, or `ambiguous` for human review.
- One emitted dossier may contain only one resolved organization-plus-program identity.
- A page describing another program cannot support a program-scoped phone, address, hours, eligibility, restriction, intake rule, or other field merely because the organization is shared.

Resolved entities also receive a category-neutral role. Only a `direct-program`
or independently actionable `access-assessment-service` may be promoted to a
counted candidate. A `service-location`, `referral-system`, `directory`,
`organization-only`, or `unresolved-lead` remains in the ledger without inflating
candidate yield. Multiple access sites normally remain attached to one program.
Splitting requires authoritative evidence of a material program distinction.
`candidate-role-gates-v1` enforces this before saturation counts or packet
freezing. Missing gate observations remain `review-required`; terminal
noncandidate roles remain in the funnel; contradictory reviewed gate decisions
for the same identity stop the run for correction.

The regression fixtures cover A New Leaf program contact transfer, CASS/Brian Garcia attribution, UMOM/Halle overbundling, and City of Mesa/HAMC-style jurisdiction boundaries.

## Evidence and field findings

Each source is classified as:

1. direct provider or program;
2. government or authoritative referral system;
3. reputable secondary source; or
4. directory or aggregator used as a lead.

Every factual field required by the selected package schema and category playbook
has exactly one state:

- `supported`: one retained value with one or more exact field/value evidence bindings;
- `conflicting`: two or more distinct values, each with its own evidence bindings; or
- `unknown`: no retained factual value and a reason it was not found.

The Housing calibration field set covers identity and contact, geography,
services, access timeline, description, eligibility, intake and connection steps,
barriers, availability, pet policy, and experience information. Another category
supplies its own schema-driven field set. Empty omission is not a fourth state.

The validated extraction dossier is Scout-owned. Under the next policy, the
fresh-context verifier returns explicit keep, downgrade-to-unknown,
mark-conflicting, review, or material-defect decisions for schema-required
fields. Scout applies those operations and revalidates. Omission cannot delete a
field: an absent verifier decision preserves the validated extraction state and
adds `verification-incomplete`. The verifier cannot invent a replacement, mutate
frozen identity, or alter a source envelope.

Program-scoped bindings must come from a source classified as describing the same
identity. Organization-wide bindings must explicitly say so and match the
organization. A directory cannot be the only support for a factual field.
Captured contradictory evidence or multiple authoritative values forces an
explicit conflict or downgrade; it cannot remain a single supported value. The
verifier returns decisions, while Scout applies the allowed patch and may not
invent a replacement.

## First Housing-stage calibration matrix

The frozen-corpus comparison begins with `urgent-access`, Immediate safety and emergency access. These are playbook configuration and fixtures, not hard-coded reusable branches. Scout persists nine required coverage branches:

1. official City of Mesa sources;
2. official Maricopa County sources, including jurisdiction boundaries;
3. official Arizona sources;
4. coordinated entry and 211, followed to named programs;
5. direct emergency providers and their intake paths;
6. domestic-violence, family, youth, medical, veteran, and disability-specific safety paths;
7. voucher issuers, temporary lodging, and bridge programs;
8. adjacent regional programs that explicitly serve Mesa; and
9. access barriers including transportation, pets, documents, family composition, sobriety, and referrals.

Each branch has six queries persisted before execution. The first two are mandatory. After that, the branch stops when two consecutive executed queries produce no new normalized organization-plus-program identity, or after the sixth query. A branch may be marked not applicable only with a recorded reason. Failed or cancelled queries do not count as successful attempts and do not satisfy saturation. Coverage is complete only when every required branch is saturated, reaches its deterministic maximum, or has an approved explicit not-applicable reason.

Novelty for saturation is identity novelty, not a new URL, domain, or wording for an already known lead. Canonical duplicate results retain query provenance but do not inflate novelty.

## Resume boundaries

Checkpoint state is written after each query, lead normalization, fetch, identity decision, evidence packet, extraction attempt, verification attempt, and audit branch. On interruption, a running item becomes failed with its retained attempt record. Resume starts with that item. Previously completed query results, sources, packets, and model outputs are not silently re-executed or overwritten.

Configuration and corpus digests are checked before resuming. A changed model, policy, query plan, package, source extract, or evidence packet requires a new labeled run or corpus. It is never patched into an existing comparison.

## Scout to final-resource ground truth

The operational workflow is:

1. Scout produces candidates, evidence, and explicit unknowns.
2. Resource Curator preserves and reviews the candidate and prepares it for human follow-up.
3. A vetter conducts a phone interview with a contact person for each candidate being prepared as a resource, resolves access facts, and prepares the resource.
4. The vetter creates an additions resource package.
5. The additions package is merged into TSO Resources, reviewed there, and saved as a new complete resource package.

The corresponding resource in that newly saved, phone-vetted package is the ground truth for later Scout scoring. Preserve an unambiguous candidate-to-Curator-draft-to-additions-resource-to-final-resource link plus the before and after complete packages. Do not infer the link from a similar name when a stable identifier or explicit mapping is available.

Retrospective comparison records each Scout field as confirmed, corrected, added during phone vetting, omitted from the final resource, or still unknown. Accuracy measures supported Scout claims against the final resource and preserved vetting outcome. Completeness measures how much needed final information Scout supplied, treating explicit unknowns as incomplete rather than false. Source analysis remains separate because the final client resource does not itself prove which web source supported a Scout claim. Usable yield counts candidates that become distinct resources in a final saved package.

Vetters perform normal resource preparation and are not asked to score Scout or Qwen. Scoring happens afterward from preserved artifacts. The deferred learning thresholds in the handoff still apply; this linkage does not activate lesson ingestion or allow Qwen to judge its own earlier output.

## Checkpoint A gate

Checkpoint A passes only when deterministic tests prove all of the following:

- configuration changes cannot be silently pooled;
- model attempts cannot mix frozen corpora;
- all nine coverage branches and their saturation rules are deterministic;
- same-organization/different-program package behavior is preserved;
- every factual field is supported, conflicting, or explicitly unknown;
- seeded contact transfer, program conflation, jurisdiction, directory-only contact, and unsupported sobriety failures are rejected; and
- existing no-metered and security tests remain green.

Passing this gate authorizes only a request for approval to begin Checkpoint B. It does not authorize discovery, Qwen inference, 8-bit loading, the full Housing run, the other Mesa categories, or production cutover.

Future changes to these reusable layers additionally require a non-Housing fixture
and a stale-path trace proving that the tested entry point reaches the current
implementation rather than a superseded compatibility branch.

## Checkpoint D gate

Checkpoint D first completed on 2026-08-22 using six identical immutable packets
from reviewed Housing corpus
`a2af690eb3446253c5582844f412322989dd386d366a4f67f6dd93421c086d08`.
Corrected comparison 2 selected 4-bit only as the input to the next correction
cycle; neither option passed its accuracy gate.

The replacement Checkpoint D comparison completed on 2026-08-23 using 22
identical packets from corpus
`204ef0cbf2c7d889fc84f544c601bd2bd9b1543a9636a7a9195742c5270e6379`.
The model-neutral report selected option A before timing was revealed: 7 passed,
15 needs-review, 0 failed, and 22 usable dossiers versus option B's 1 passed, 18
needs-review, 3 failed, and 19 usable dossiers. The reveal mapped option A to
8-bit. The 8-bit selection authorizes the approved forward optimization plan. It
does not lock production, start the other categories, or rewrite historical
results.

The expanded reviewed-corpus comparison uses runtime provenance suffix `arrays-cache-materialization-v1`. An initial v4 attempt over corpus `204ef0cbf2c7d889fc84f544c601bd2bd9b1543a9636a7a9195742c5270e6379` reached MLX's Metal buffer-object limit during its first 4-bit extraction because the MLX 0.31.3 hybrid Qwen server cache retained a lazy metadata graph on every generated token. The MLX background generation thread died while the HTTP process remained alive, so ordinary catalog health checks could not detect the failure. The v5 runtime wrapper materializes the affected `ArraysCache` metadata after each advance, preserving the configured output allowance instead of truncating the model response. This runtime change has an explicit configuration hash and new run label; the failed v4 attempt remains preserved.

The v5 run then completed five candidates with zero true verification failures before packet 47 exhausted a long extraction without returning one complete JSON object. Diagnosis identified avoidable output expansion: the extraction prompt asked Qwen to reproduce immutable source URL, title, fetched text, authority, and page identity even though Scout already owns those frozen values, and earlier verifier findings showed that copied envelopes could be altered. Prompt-policy v4 therefore limits model source output to source ID plus `supports` and `contradicts` bindings; Scout deterministically restores every immutable envelope field from the packet before validation and persistence. Failed completions now retain their raw output and usage for diagnosis. This extraction-structure change receives v6 run and comparison labels, preserves the v5 evidence, does not weaken the verifier, and requires both quantizations to restart against the unchanged frozen corpus.

The first v6 extraction produced the intended sparse bindings and a valid dossier, but its verifier response was malformed at the boundary between a fully copied source array and the findings array. The retained raw output showed a complete substantive response with one closing brace in the wrong order. Verifier prompt-policy v4 therefore removes the same redundant envelope copies from the dossier supplied to and returned by the verifier. The verifier still receives the complete frozen packet separately, keeps the same checklist and strictness, and remains responsible for source support and conflict bindings; Scout restores immutable source fields after the response. This receives v7 run and comparison labels and preserves the v6 attempt and raw failure evidence.

The v7 run completed packet 42 cleanly, then packet 43 ended with one true deterministic `identity-key-mismatch`. The verifier correctly flagged that the source's public program wording differed from the reviewed corpus label, but it changed `program` while retaining the frozen identity key. Candidate organization, program, identity key, and the one component key are immutable corpus boundaries, not model-owned corrections. Deterministic post-processing v1 now restores those four values after both extraction and verification while preserving verifier findings, boundary state, and coverage tags. This clears internally inconsistent identity mutation without suppressing the review finding, receives v8 run and comparison labels, and preserves the v7 dossiers and true-failure evidence.

The v8 4-bit run completed eleven candidates with no true deterministic failures before packet 53 exhausted the client's 16,384-token completion allowance. The retained raw response contained a substantive Family Promise Emergency Shelter dossier but ended mid-JSON, and its usage record showed exactly 16,384 completion tokens, local-only execution, and no fallbacks. Completion-allowance v1 raises the client request to the already pinned local server ceiling of 32,768 tokens, persists `modelMaxCompletionTokens` inside the immutable configuration limits, records the provider finish reason when available, and emits an explicit limit-exhaustion error instead of a generic malformed-JSON error. This runtime correction receives v9 run and comparison labels, preserves the v8 failure and raw output, and requires both quantizations to restart against the unchanged frozen corpus.
