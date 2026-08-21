# Qwen optimization deterministic design

Status: Checkpoints A through C implemented for deterministic discovery, candidate dossiers, fresh-context verification, completeness, and gap-audit reporting.

This document fixes the data boundaries, persistence records, Housing regression fixtures, coverage matrix, stopping behavior, quality gate, and downstream ground-truth linkage before any new model run. It does not authorize Checkpoint B or production cutover.

## Decision order

Every gate and comparison uses these priorities without a weighted average:

1. accurate information;
2. complete information;
3. number and quality of sources;
4. genuinely new, usable candidates; and
5. elapsed research time.

Material program conflation, unsupported restrictions, incorrect jurisdiction, or source-to-field attribution errors block advancement. An explicit unknown is incomplete but not inaccurate. Time is diagnostic and may break only a true quality tie across priorities one through four.

## Pipeline records

The migration adds the following isolated records. Existing `research_runs`, DeepSeek behavior, and the frozen baseline remain unchanged.

- `optimization_configurations` is an immutable, hashed snapshot of the model artifact and quantization; MLX and DSH versions; search and fetch providers and plugin versions; prompt-policy and playbook versions; source-package identity; target and stage; deterministic limits and stopping rules; and the complete query plan. The display label is not part of the hash. Changing quantization, a policy version, the package, a limit, or any planned query creates a different configuration.
- `optimization_runs` records a labeled discovery, model-evaluation, or end-to-end run and its current phase. A model-evaluation run must identify one frozen corpus.
- `optimization_checkpoints` records resumable phase-and-item state, attempt count, payload digest, status, and timestamps. Work resumes from the smallest incomplete item rather than restarting the stage.
- `optimization_coverage_branches` and `optimization_queries` preserve every required branch, purpose, planned query, execution outcome, novelty count, saturation state, failure, and explicit not-applicable reason.
- `optimization_discovery_leads` and `optimization_lead_queries` form the normalized discovery ledger while retaining every query/rank/URL route that found a canonical lead.
- `optimization_candidate_identities` and `optimization_identity_leads` preserve organization-plus-program identity, uncertain boundaries, possible renamings or duplicates, package-exclusion decisions, and the lead evidence behind them.
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

The regression fixtures cover A New Leaf program contact transfer, CASS/Brian Garcia attribution, UMOM/Halle overbundling, and City of Mesa/HAMC-style jurisdiction boundaries.

## Evidence and field findings

Each source is classified as:

1. direct provider or program;
2. government or authoritative referral system;
3. reputable secondary source; or
4. directory or aggregator used as a lead.

Every factual Housing field has exactly one state:

- `supported`: one retained value with one or more exact field/value evidence bindings;
- `conflicting`: two or more distinct values, each with its own evidence bindings; or
- `unknown`: no retained factual value and a reason it was not found.

The factual field set covers identity and contact, geography, services, access timeline, description, eligibility, intake and connection steps, barriers, availability, pet policy, and experience information. Empty omission is not a fourth state.

Program-scoped bindings must come from a source classified as describing the same identity. Organization-wide bindings must explicitly say so and match the organization. A directory cannot be the only support for sensitive access fields. Captured contradictory evidence or multiple authoritative values forces an explicit conflict or removal; it cannot remain a single supported value. The verifier may remove, downgrade, or flag a claim but may not invent a replacement.

## First Housing-stage coverage matrix

The frozen-corpus comparison begins with `urgent-access`, Immediate safety and emergency access. Scout persists nine required coverage branches:

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
