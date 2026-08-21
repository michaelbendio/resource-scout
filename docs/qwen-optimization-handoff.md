# Qwen optimization handoff

Status: Ready for a fresh Codex task to begin design validation and implementation.

This document is the authoritative continuation point for optimizing Resource Scout's local Qwen research path. Read it together with:

- `docs/local-dsh-qwen-plan.md`
- `docs/mesa-qwen-deepseek-benchmark.md`
- `README.md`

Do not infer that Phase 2 production cutover has started. The current local path is operational but remains an opt-in experiment because the first Housing gate failed.

## Objective

Redesign Resource Scout's research workflow so local Qwen produces accurate, complete, well-sourced, useful resource candidates without metered model or search services. Compare both 4-bit and 8-bit Qwen under the redesigned workflow before selecting a quantization.

The immediate endpoint is a completed, preserved Housing calibration that supports an explicit decision to:

1. continue optimizing;
2. advance one locked configuration to the remaining 19 Mesa categories; or
3. stop because local Qwen still does not meet the quality requirements.

The endpoint is not production cutover. A successful calibration only authorizes the next benchmark step.

## User priorities

Evaluate and make decisions in this exact order:

1. Accurate information
2. Complete information
3. Number and quality of sources
4. Number of genuinely new, usable candidates
5. Elapsed research time

Time is recorded for planning and diagnosis, but it is almost unimportant. Do not trade accuracy, completeness, or source quality for speed. Do not collapse these priorities into a weighted average that lets candidate volume or speed conceal accuracy failures.

## Operating constraints

- Hardware: 64 GB Mac mini with M4 Pro.
- Model runtime: MLX LM on loopback only.
- Harness: DSH.
- Search: Resource Scout-owned DDGS plugin, without a paid search API.
- Fetch: Resource Scout-owned bounded, SSRF-resistant HTTP fetch plugin.
- No DeepSeek key or other metered-model credential may be forwarded to the local path.
- No silent metered fallback is allowed.
- The source resource package remains read-only.
- Completed work must persist at fine-grained checkpoints and resume after interruption rather than restart.
- Keep production DeepSeek behavior unchanged until a later, explicitly authorized cutover.
- Run calibration in the isolated benchmark database, not the live Scout database.

## Current repository state

- Repository: `/Users/michaelbendio/resource-scout`
- Branch: `main`
- Latest commit when this handoff was written: `8d5bbdb5ccaa5c3580b237a68d252cee6921cb99`
- Application version: `0.21.0`
- Phase 1 local-Qwen implementation commit: `81a9eeab49de8006bce32b137992777802db3606`
- Local Qwen default: `mlx-community/Qwen3.8-27B-4bit`
- Comparison artifact: `mlx-community/Qwen3.8-27B-8bit`
- Context window used in the first calibration: 65,536
- Reasoning setting used in the first calibration: medium
- Current conservative plugin limits: two searches and five fetches per stage
- The full Python suite most recently passed 90 tests with one optional skip.
- The JavaScript plugin suite most recently passed 20 tests.

The repository was clean and synchronized with `origin/main` when this handoff was created. Recheck before editing and preserve unrelated user work if the state has changed.

## Preserved benchmark data

The ignored benchmark directory is:

`data/benchmarks/mesa-qwen-2026-08-21/`

It contains:

- `mesa-deepseek-baseline.json`
- `mesa-qwen-benchmark.sqlite3`

The benchmark database contains the frozen 20-category DeepSeek baseline and all local Qwen calibration attempts. Do not modify or replace the baseline. New configurations must receive new labeled runs and complete provenance.

Important run IDs:

- Run 1: completed DeepSeek Housing baseline
- Run 21: failed initial 8-bit Housing-stage attempt
- Run 22: completed tuned 8-bit first Housing stage
- Run 23: completed conservative 4-bit full Housing run
- Run 24: broadened 4-bit first-stage retry; partial by design

Housing stages are:

1. Immediate safety and emergency access
2. Homelessness prevention and stabilization
3. Transitional and specialized housing
4. Permanent pathways and gap review

## Empirical starting point

Frozen DeepSeek baseline:

- 20 Mesa categories
- 536 candidates
- 15.33 successful-stage hours
- Housing: 30 candidates, 113 evidence items, 60 domains, 44.2 minutes
- Housing evidence density: 3.77 items per candidate

Conservative Qwen 4-bit full Housing run:

- 13 candidates
- 43 evidence items
- 33 domains
- 71.6 minutes
- Evidence density: 3.31 items per candidate
- Stage candidate counts: 5, 3, 3, 2
- Stage times: 17:58, 19:16, 16:35, 17:48

Tuned 8-bit first-stage attempt:

- 6 candidates
- 33 minutes 21 seconds
- 1.7 evidence items per candidate
- Detailed and Mesa-focused, but slower and less well sourced than the matching DeepSeek stage

Conservative 4-bit matching first stage:

- 5 candidates
- 17 minutes 58 seconds
- 13 evidence items across 12 domains
- 2.6 evidence items per candidate

Broadened 4-bit matching first stage:

- 6 candidates
- 19.0 minutes
- 11 evidence items across 10 domains
- Evidence density fell to 1.83
- Several outputs were broad routing concepts rather than actionable named programs

The earlier result rejected both simple cap expansion and an unchanged 8-bit workflow. It did not prove that 8-bit lacks a quality advantage under a better Scout-owned workflow.

## Lessons from the candidate comparisons

The next design must directly prevent the failures seen during the Housing review:

- Contact information was transferred between separate programs within the same organization.
- Programs serving different populations or locations were combined into one candidate.
- A New Leaf Rapid Re-Housing was conflated with the City of Mesa Housing Authority.
- The Brian Garcia Welcome Center was attributed to CASS rather than treated as a separate program and access point.
- An official jurisdiction document showing that HAMC does not serve Mesa proper was missed.
- Weak directories supplied phone numbers or facts that were presented with too much confidence.
- A sobriety restriction was inferred without supporting evidence.
- Related programs were sometimes overbundled; other times one organization/program appeared in fragmented or duplicate form.
- Useful details were present, but source-to-field attribution was not consistently reliable.

Accuracy requires program identity and evidence attribution to be explicit data, not prose that the model can blend.

## Optimization hypothesis

The primary problem is the workflow, not merely the prompt or tool-call cap. A 27B local model should not be asked to discover the field, browse broadly, resolve identities, extract every candidate, verify itself, and produce a large final JSON object in one context.

Resource Scout should own the systematic, deterministic parts. Qwen should perform bounded semantic work over prepared evidence.

The redesigned workflow should be source-driven and candidate-centered:

1. Scout plans and records systematic discovery.
2. Scout resolves candidate identities and excludes existing resources.
3. Scout acquires and classifies evidence.
4. Qwen extracts one candidate dossier at a time.
5. A fresh-context verification pass challenges each dossier.
6. Scout performs a coverage audit and targeted gap sweep.
7. Only then does Scout emit Curator candidates.

## Proposed research pipeline

### 1. Snapshot configuration and package identity

Before a run starts, persist:

- model artifact and quantization;
- MLX, DSH, plugin, prompt-policy, and playbook versions;
- source-package SHA-256 and package version;
- target location, regional scope, category, and stage;
- deterministic limits and stopping rules;
- the full query plan.

Test: two runs with different quantization or policy versions cannot be silently pooled as one configuration.

### 2. Build a coverage and query matrix

Scout should derive query families from the category playbook, location, regional scope, source types, and service sub-needs. Qwen may suggest terms, but Scout owns and persists the final matrix.

For Housing, the matrix should deliberately cover official city/county/state sources, coordinated entry and 211, direct providers, program-specific service needs, and geographically adjacent resources that explicitly serve Mesa.

Each query family must have a recorded purpose and coverage branch. Completion means every required branch was attempted, not merely that a model decided to stop searching.

Test: every required playbook branch has at least one executed query or an explicit, recorded reason it was not applicable.

### 3. Create a discovery ledger

Search results should enter a normalized ledger before Qwen creates candidates. Retain query, rank, title, URL, snippet, discovered time, redirect result, fetch status, and failure reason. Canonicalize URLs and collapse obvious duplicates without discarding provenance.

Use a saturation rule rather than a small global search cap: continue a coverage branch until repeated queries produce no new plausible organizations or programs. Bound the rule deterministically so a run cannot loop indefinitely.

Test: repeated equivalent results do not become duplicate leads, and a branch stops only according to its recorded saturation rule.

### 4. Resolve identities and package exclusions

Resolve organization and program identity before detailed extraction. The key identity is organization plus specific program, not organization alone.

- Exclude the same organization and same program when it is already represented in the supplied package.
- Continue to allow a genuinely different program from the same organization.
- Preserve possible-renaming, possible-duplicate, and uncertain-boundary states for review.
- Do not use a different program's phone, address, restrictions, or intake rules merely because the organization matches.

Test fixtures must cover A New Leaf, CASS/Brian Garcia, UMOM/Halle, and City of Mesa/HAMC-style boundaries.

### 5. Acquire and classify evidence

Scout should fetch promising pages, retain bounded source text, and classify source authority:

1. direct provider or program source;
2. government or authoritative referral system such as 211;
3. reputable secondary reporting;
4. directory or aggregator, usable primarily as a lead.

Record which program each page actually describes. A source at the same parent organization is not automatically evidence for every program.

Test: a directory-only phone number cannot silently override or populate a conflicting official-program field.

### 6. Build one candidate dossier per context

Give Qwen one resolved candidate identity, the relevant source extracts, the required Curator fields, the playbook questions, and the package-match result. Require field-level evidence references.

For every factual field, Qwen must return one of:

- supported value with evidence;
- conflicting values with evidence for each;
- unknown or not found.

Unknown is preferable to inference. Do not penalize an honest unknown as an accuracy error.

Test: unsupported eligibility, sobriety, service area, availability, intake, phone, and address claims are rejected or converted to explicit unknowns.

### 7. Verify in a fresh context

Use a separate Qwen call with no access to the first call's reasoning. Give it the dossier, identity, and sources and require it to check:

- source-to-field attribution;
- organization and program boundaries;
- jurisdiction and service area;
- conflicting contact or intake information;
- speculative restrictions;
- duplicate or fragmented candidates;
- missing required fields;
- whether each source actually supports the stated claim.

The verifier may flag, remove, or downgrade claims. It must not invent replacement facts.

Test: seeded attribution errors and program conflations are caught before candidate emission.

### 8. Audit completeness and perform a gap sweep

Completeness has two levels:

- Candidate completeness: every Curator and vetting-script field is supported, conflicting, or explicitly unknown.
- Coverage completeness: every required playbook branch has been searched and its plausible leads resolved.

After candidate verification, Scout should compare the retained set with the coverage matrix and run targeted searches for uncovered service needs or populations. The gap sweep must use the same ledger and identity rules.

Test: a deliberately omitted Housing sub-need is detected and creates a targeted gap query.

### 9. Emit candidates and an audit report

Curator candidates should contain only verified claims plus explicit conflicts and unknowns. Preserve the complete research trail outside the client-facing draft.

The run report should include:

- coverage branches attempted and completed;
- search and fetch counts by branch;
- unique leads, resolved identities, exclusions, and retained candidates;
- source authority and domain counts;
- field support, conflict, and unknown counts;
- verifier findings and resulting changes;
- package exclusion decisions;
- elapsed times, retries, and resource use;
- full configuration provenance.

## 4-bit versus 8-bit calibration

Do not compare quantizations by letting them browse different evidence. First isolate model quality:

1. Build and freeze one discovery ledger and source corpus for the first Housing stage.
2. Build identical candidate identity records and evidence packets.
3. Run 4-bit extraction and verification over those packets.
4. Run 8-bit extraction and verification over the identical packets.
5. Compare results in the user's priority order.

If quantization materially affects a semantic step, follow with one end-to-end run of the better configuration. If results are effectively tied on priorities 1 through 4, choose 4-bit because it is faster and uses less memory.

Do not choose 8-bit merely because it writes more or sounds more polished. Do not choose 4-bit merely because it finishes sooner.

## Evaluation rules

### Priority 1: accuracy

Block advancement for material program conflation, unsupported restrictions, incorrect jurisdiction, or source-to-field attribution errors. Record every field as supported, conflicting, unsupported, or unknown.

### Priority 2: completeness

Measure required-field coverage and playbook-branch coverage. A filled field without evidence is not complete. An explicit unknown is incomplete but not inaccurate.

### Priority 3: sources

Measure source count, unique domains, authority, reachability, recency where relevant, and the number of factual fields each source actually supports. Raw link count alone is not quality.

### Priority 4: candidates

Count unique, actionable organization-plus-program candidates after package exclusion, identity resolution, and verification. Report duplicates, fragments, broad directories, routing concepts, and non-actionable developments separately.

### Priority 5: time

Record discovery, fetch, extraction, verification, and total times. Time may break a true quality tie, but it must not excuse lower accuracy, completeness, source quality, or usable yield.

## Test strategy

Implement tests before or alongside each layer:

- Unit tests for query planning, URL normalization, source authority, identity keys, package exclusions, saturation rules, evidence bindings, and scoring.
- Fixture-based integration tests using saved HTML/text so correctness tests do not depend on the live web.
- Regression fixtures for every concrete Housing failure listed in this handoff.
- Resume tests that interrupt discovery, fetching, dossier extraction, verification, and the gap sweep independently.
- Provenance tests ensuring configuration and model artifacts cannot be mixed.
- Security tests preserving the existing SSRF, redirect, content-type, response-size, timeout, cancellation, and per-run boundary protections.
- No-metered-traffic tests proving the local path has no DeepSeek key and no metered fallback.
- Fair-comparison tests proving 4-bit and 8-bit receive identical frozen evidence packets.
- Export tests proving verified candidates still flow into the existing Scout and Curator formats.
- Full existing Python and JavaScript suites before and after implementation.

Do not use live-web results as the only automated acceptance test. Live tests may supplement deterministic fixtures.

## Implementation checkpoints

### Checkpoint A: design and fixtures

- Finalize data records and migrations.
- Add the Housing regression fixture set.
- Define deterministic coverage and saturation behavior.
- Review the design against all five priorities before starting model runs.

Gate: deterministic tests demonstrate that known conflations and unsupported-field cases cannot pass silently.

### Checkpoint B: discovery, identity, and evidence

- Implement the query matrix, discovery ledger, package exclusion, identity resolution, source acquisition, and source authority.
- Verify interruption and resume.

Gate: one fixture-driven Housing stage produces a complete, inspectable evidence corpus without invoking Qwen.

### Checkpoint C: candidate extraction and verification

- Implement one-candidate-per-context extraction.
- Implement the independent fresh-context verifier.
- Implement completeness and gap-sweep reporting.

Gate: seeded factual and attribution defects are caught, and every required field is supported, conflicting, or unknown.

### Checkpoint D: frozen-corpus quantization comparison

- Run 4-bit and 8-bit over identical first-stage evidence packets.
- Produce a blinded or model-neutral comparison report before examining speed.

Gate: select a quantization based on priorities 1 through 4; use time only for a quality tie.

### Checkpoint E: complete Housing calibration

- Lock the selected model, prompts, policies, and limits.
- Run all four Housing stages in the isolated benchmark database.
- Compare with the frozen DeepSeek Housing result and all previous Qwen runs.
- Preserve raw outputs, ledgers, evidence packets, verification records, failures, and timing.

Gate: explicitly decide whether to optimize again, stop, or authorize the remaining 19 categories. Do not start them automatically.

## Codex and Scout division of labor

Codex should perform the bounded high-judgment work:

- architecture and implementation;
- deterministic tests and regression fixtures;
- checkpoint reviews;
- diagnosis of failures;
- 4-bit/8-bit and DeepSeek quality comparison;
- documentation, commit, and push.

Scout and local Qwen should perform the long-running work:

- query execution;
- page fetching;
- local inference;
- checkpoint persistence;
- retries within policy;
- metrics and audit-report generation.

Do not keep Codex continuously polling a healthy local run. Long local inference does not itself consume the user's Codex allowance. Scout should persist enough state that Codex can inspect planned milestones or errors without holding an active conversation for the entire run.

## Existing-resource behavior

The supplied resource package is both context and an exclusion set:

- Ignore the same organization and same program during new-resource discovery.
- Permit a distinct program from the same organization.
- Preserve ambiguous matches for Curator rather than guessing.

An audit of whether existing resources remain current is a separate future maintenance mode and is not part of the immediate Qwen calibration. It will eventually classify existing resources as appears current, changed, possibly closed or moved, cannot verify, identity problem, or related new program. A broken page alone is never proof of closure. Scout will propose field-level changes; Curator and phone vetting remain the authority before package data changes.

## Deferred learning system

Do not activate or bulk-ingest the current agent-proposed lessons during this optimization. The live database previously contained 245 proposed lessons, none active. Leave them as an audit trail.

Future learning should use ordinary Curator and phone-vetting outcomes without asking vetters to score model candidates. The final phone-vetted resource package is ground truth. Qwen must not judge the truth of its own earlier output.

Revisit the learning system only when all are true:

1. at least 25 candidates have terminal normal-vetting outcomes;
2. outcomes span at least 3 categories;
3. at least 15 accepted candidates appear in final merged packages;
4. at least 90 percent of accepted candidates have unambiguous candidate-to-generated-to-final-resource linkage with before and after packages preserved; and
5. enough outcomes belong to the current Scout configuration to evaluate it separately.

Those thresholds trigger an audit and design review, not automatic lesson activation.

For organization-wide TSO use, future lessons need geographic scope:

- organization-wide research methods;
- regional systems and source knowledge;
- city- and program-specific facts.

Local facts must not become universal rules. A broadly reusable lesson should normally require at least three independently vetted examples spanning at least two cities unless it is a deterministic rule such as never transferring contact information between separate programs.

## Work discipline for the fresh task

- Start by rechecking repository status, current versions, available disk space, and the benchmark database hashes.
- Inspect existing data models and tests before choosing migrations.
- Prefer Scout-owned deterministic orchestration over increasingly elaborate monolithic prompts.
- Keep each checkpoint independently testable and resumable.
- Do not run 8-bit or a long calibration until the deterministic fixtures pass.
- Do not run the full Housing calibration until the frozen-corpus 4-bit/8-bit gate selects a configuration.
- Do not start the other 19 categories without explicit user authorization after Housing review.
- Work on the current branch. After each completed, verified repository change, commit and push unless the user asks to hold.
- Keep unrelated files and user changes out of commits.

## Suggested opening request for a new task

> Continue the Resource Scout Qwen optimization work from `docs/qwen-optimization-handoff.md`. Implement the plan through the first 4-bit/8-bit Housing-stage comparison, with tests and checkpoints. Preserve the frozen DeepSeek baseline, use no metered services, and do not compromise accuracy or completeness to save time. Stop for my review at every gate identified in the handoff.
