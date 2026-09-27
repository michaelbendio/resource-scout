# Scout evaluation and discovery: implementation plan

September 27, 2026 · Version 1 · Implementation instructions, not a run authorization

Companion to [Scout: DeepSeek evaluation and discovery design](scout-evaluation-and-discovery-design-20260927.md).

## Outcome and working method

Implement a small, isolated DeepSeek evaluation first. Use its results to decide which Scout workflow changes to build and adopt. Deliver a complete-office cost estimate, including preparation, final review, corrections, tools, and remaining Codex demand. Do not rerun all of Mesa to answer these questions.

This plan supplies the implementation choices that a lower-effort coding session should otherwise have to reconstruct. Work through **one numbered ticket at a time**, run its checks, and save a handoff. Routine coding can follow these instructions at a lower effort level. Source interpretation, consequential identity decisions, and advancement judgments remain explicit reviewer tasks; passing tests does not replace them. Follow the repository's current effort requirements for those reviews.

The first useful milestone is **M1: one independently researched Housing comparison, actual pilot spending, and a provisional full-run estimate with unmeasured stages exposed**. The complete cost assessment is M2, after preparation/review sampling. The redesign starts at M3, after the original-policy measurements are frozen.

| Milestone | Tickets | Deliverable |
| --- | --- | --- |
| M0: offline foundation | 0–4 | Sealed protocol, isolated runner, cost controls, simulated end-to-end run |
| M1: first answer | 5 | Housing comparison and preliminary cost report; continue/retest/stop judgment |
| M2: model assessment | 6–8 | Three-category research, preparation/review sample, complete-run scenarios |
| M3: workflow assessment | 9–10 | Coverage-based challenger and screening comparison with the same model |
| M4: bounded adoption | 11 | Different-office trial and explicit production configuration decision |
| M5: continuing operation | 12–13 | Shared evidence refresh and maintenance; learning remains proposed/inactive |

Complete the offline implementation without requesting routine permission. Before a paid launch, check whether a concrete envelope has already been authorized; the design's **proposed $20 limit is not itself authorization**. A request to implement this plan does not authorize replacing production defaults, spending without an envelope, or starting a full-office run.

## 0. Establish the checkout, inputs, and handoff

**Existing baseline.** The published design is commit `d288a078ce77d4ab39150b815e874b5e601cbdc8`, branch `docs/scout-evaluation-design-20260927`, repository `michaelbendio/resource-scout`. Its code parent is `6eb7934`. At plan creation, the shared local checkout was on `pairwise-research-experiment` at `bf2655c`, with unrelated changes and active Mesa review work. Those facts are a dated checkpoint, not instructions to reset anything.

1. Read `AGENTS.md`, [SCOUT_STATUS.md](../SCOUT_STATUS.md), [orchestration instructions](scout-orchestration.md), and the [prepared-resource contract](scout-prepared-resources-contract.md). Check live work before starting workers.
2. Use an available isolated checkout, or create a managed worktree from the published documentation branch after inspecting attached worktrees. Keep the current Mesa checkout and its index intact. Do not absorb unpublished changes merely because they are present locally.
3. Record the actual implementation commit and any intentionally adopted later fixes. The newer local curation-recovery changes are not a prerequisite for the isolated experiment.
4. Create `docs/scout-evaluation-implementation-status.md` in the implementation checkout. Record completed tickets, commits, exact checks/results, remaining questions, and the next ticket. Keep runtime evidence paths and hashes in the local run manifest; publish only suitable summaries.
5. Use `data/evaluations/<experiment-id>/` for runtime data. The repository already ignores `data/` and SQLite files. Check ignore behavior before writing evidence; do not commit credentials, source databases, or raw private office packages.

**Done when:** the working branch/base and isolated directory are recorded; current Mesa work is preserved; no experiment worker has started.

## Fixed implementation choices

These are decisions for this version, not a menu of alternative architectures.

- Add a small `resource_research_agent/evaluation/` package with a single CLI. Do not build a new server, dashboard, provider framework, or job queue.
- Run one paid evaluation worker at a time initially. Keep focus passes sequential within a category. Measure before adding concurrency.
- Read production evidence through read-only SQLite connections and a consistent local snapshot. Initialize a **fresh scratch database from the original office package** for each experimental condition. Never initialize the live database with `ResearchStore`: its constructor performs schema/backfill work.
- Reuse the existing focused-research functions on the scratch database for Stage A. Keep the existing production challenger runner unchanged; reuse its suitable helpers through a narrow adapter. Do not call its `supervise`, `import_completed`, or `import_completed_locked` paths from evaluation.
- Put experiment-specific coverage fields in versioned sidecar files. Do not migrate production job tables or change sealed production playbooks during the pilot.
- Save original outputs, corrections, and reviewer judgments separately. All sample collections are visibly evaluation-only and non-importable.
- Preserve the current full usable-reserve preparation scope for the model comparison. Core plus selected reserve is a separate scenario until Michael chooses that service level.

### File map

All paths below are relative to the repository. **New files and functions are proposed work; they do not exist merely because this plan names them.** Add an empty `evaluation/__init__.py` and use standard-library `unittest`, JSON, CSV, SQLite, and `Decimal` unless existing dependencies already meet a need.

| New file under `resource_research_agent/evaluation/` | Responsibility |
| --- | --- |
| `__main__.py` | Argument parsing and subcommand dispatch; no paid action by default |
| `protocol.py` | Manifest validation/sealing, input hashes, path confinement, stage decisions |
| `baseline.py` | Read-only historical export, original package provenance, answer isolation |
| `ledger.py` | Durable attempts, reservations, charges, time, and unknown outcomes |
| `deepseek.py` | Evaluation-only native search/tool loop with injected transport for tests |
| `research.py` | Scratch focused jobs, own-result exclusion lists, primary pass completion |
| `audit.py` | Anonymous comparison packets, evidence-backed judgments, advancement records |
| `preparation.py` | Reproducible sample, drafting/review packets, collection checks |
| `cost_report.py` | Actuals, assumptions, projections, Codex demand, elapsed-time scenarios |
| `coverage.py` | Coverage sidecar validation, challenger assignments, bounded follow-up |
| `screening.py` | Evidence-supported preparation selection; core/reserve/archive disposition |

Add matching tests as `tests/test_evaluation_<module>.py`, plus `tests/test_evaluation_offline.py`. Store synthetic fixtures under `tests/fixtures/scout_evaluation/`. Use no real credentials or private package content in fixtures. Maintenance files are specified in later tickets; do not create empty scaffolding for them now.

### Runtime records

Use immutable JSON files for inputs/results and a local `ledger.sqlite3` for transactional accounting. The directory contains:

```text
manifest.json                       # sealed configuration and hashes
authorization.json                  # actual spending scope, when supplied
inputs/                             # original package and provider-visible material
reference/                          # historical answers; reviewer-only
scratch/<condition>.sqlite3          # fresh store per condition
attempts/<attempt-id>/               # exact request, response, tools, failure evidence
results/<condition>/<category>/      # original and revised outputs, never overwritten
audit/                              # criteria, frozen judgments, reveal, stage decisions
reports/                            # Markdown, CSV, JSON, assumptions
ledger.sqlite3                      # reservations, usage, outcomes, event history
```

Separate directories alone do not enforce blinding: construct model requests from an explicit input allowlist. Offer public URL fetching and native search, with no shell, local-file, database, or directory-reading tool. Store only a hash of the hidden reference in the model-visible protocol. Sealing fails if inputs changed or hidden answer records entered an assignment. Do not log credential values or authorization headers.

The manifest must record experiment ID, code commit, input hashes, original office/import/category IDs, research version, condition, provider configuration, playbook/prompt/schema versions, dates, sample seed, coverage criteria version, pricing reference, budgets, and limits. Record unavailable historical model/settings as `null` with a reason. Keep mutable progress and stage decisions outside the sealed manifest.

## 1. Freeze the baseline and experiment protocol

**Files:** `protocol.py`, `baseline.py`, CLI `init`/`seal`; corresponding tests.

**Reuse:** `importer.ResourcePackageImporter`, `focused_research.build_focused_plan`, and saved focused-job/pass metadata. Consult [the Mesa run record](mesa-full-prepared-run-20260926.md) for historical locations; discover and verify actual IDs rather than hardcoding its import/job numbers.

1. Implement `export_baseline(source_db, selection, destination)`. Open the source with SQLite `mode=ro`, back it up through SQLite's backup API to a local evidence snapshot, close it, and hash the snapshot. Do not copy only the main live database file: WAL content may be missing. Never instantiate `ResearchStore` against the source or reviewer snapshot.
2. Inventory saved primary runs, original office packages, pass outputs, playbook definitions, and available telemetry. Choose one coherent Codex primary research version with provenance for Housing, then Food and Disability. Do not choose each category's most successful run after inspecting outcomes. Record selection criteria and incompatibilities before DeepSeek runs.
3. Recover the original known-resource baseline. A present-day curated package is not interchangeable. If exact original inputs or compatible pass semantics cannot be established, stop the affected comparison and record the missing evidence. Other offline tickets can continue.
4. Save Codex results in `reference/`. Freeze evaluator-only essential pathways and the hidden useful-resource reference. Provider-visible playbook needs can use generic pathway descriptions, not hidden resource names or access routes learned from later Codex answers.
5. Implement `seal_protocol` and `verify_protocol`. Hash immutable inputs, prompt templates, criteria, schemas, and pricing. Later changes create a new protocol version/condition; resume rejects a changed sealed input.
6. Use explicit experiment identifiers and redaction policy. `focused_research` defaults to `employment-retrospective-v1`; never inherit that unrelated default accidentally. For original-policy replay, record the actual original redaction behavior and reproduce it. Record any unavoidable setup differences.

**Checks:** `test_evaluation_protocol.py`, `test_evaluation_baseline.py`. Include a source database with WAL data, a canary hidden answer, an altered sealed file, an incompatible historical policy, and an original-package/current-package mismatch. Prove the source is opened read-only and receives no evaluation records. For a live database, do not mistake concurrent legitimate writes for writes by the exporter.

**Done when:** a reviewer can trace each baseline to its source, and a fake provider receives only allowed original inputs and its own earlier discoveries.

## 2. Implement accounting before paid execution

**Files:** `ledger.py`, `protocol.py`, CLI `status`; `test_evaluation_ledger.py`.

1. Implement `reserve_attempt`, `record_response`, `record_failure`, and `summarize_usage`. Use `BEGIN IMMEDIATE` transactions and unique attempt IDs. A reservation must be durable before the network request. Save raw response evidence before interpreting or validating it.
2. Store condition/category/pass/stage, request hash, requested/returned model, timestamps, outcome, native usage, pricing version, reservation, calculated cost, known billed cost if available, tool counts, and diagnosis/recovery links. Use decimal strings for money. Preserve missing counters as unknown; reuse `worker_metrics.optional_counter`/`observed_counter` semantics.
3. Support attempt states `reserved`, `sent`, `responded`, `failed-not-sent`, and `unknown-outcome`. A crash after sending does not release the reservation or permit an automatic replay. Resume adopts a saved response once; a genuinely uncertain paid outcome needs reconciliation or remains conservatively reserved.
4. Calculate a maximum next-request charge from the sealed model/input/output bounds and maximum native-tool use, including tool-generated context. Obtain current provider billing definitions before live use. Reject paid dispatch if the bound is unavailable or the remaining stage/experiment envelope cannot cover it. Do not reuse the challenger's hardcoded `$0.35` reservation or `peak_cost` rates as the evaluation cost model.
5. Normalize mutually exclusive uncached/cache-hit/cache-write/output billing components. Record reasoning separately only if its billing is additional; otherwise it is already included in output. Record actual versus estimated charges distinctly. Account balance is a corroborating signal, not per-request attribution when the account has concurrent activity.
6. Enforce category limits across all passes and recovery: proposed 60 paid calls and 60 minutes of active worker elapsed time, plus the stage and experiment dollar caps. Human review pauses are separate from active worker time; store both. Permit at most two diagnosed transport recovery attempts within the same cap. Count schema repairs, continuations, and paid source checks too.
7. Make the launch envelope explicit: proposed reservations are $3 Housing, $6 Food/Disability combined, $4 preparation/review, $6 revised-policy comparisons, and $1 contingency. Store authorized reallocations within the total; never silently borrow beyond it. No credit purchase, paid fallback, or automatic fresh Codex control.

**Checks:** reservation race, exact boundary, over-cap call rejected before transport, crash after send, response before crash, duplicate resume, missing usage, cache/reasoning double counting, rate change, unknown tool charge, and a separately active account. A reservation may be released only with evidence that it is unused or reconciled.

**Done when:** simulated failures and concurrent reservation attempts cannot produce an unrecorded dispatch or exceed the authorized envelope.

## 3. Add the evaluation-only DeepSeek adapter

**Files:** `deepseek.py`; `test_evaluation_deepseek.py`.

**Reuse:** suitable helpers in `deepseek_challenger_runner.py`: `credential`, `public_url`, `open_url`, and final-answer/search-limit parsing behavior. Keep the production runner's behavior and entry points intact. If parsing needs a reusable small helper, extract only that helper with compatibility tests; do not refactor the whole runner during this ticket.

1. Implement `run_assignment(packet, ledger, transport, output_contract)`. Inject a fake transport in tests. Resolve model, endpoint, thinking settings, and tool definitions from the sealed configuration; do not embed a provider name inside research-policy decisions.
2. Use native search plus the existing public-page/PDF fetch behavior. Preserve each source URL, retrieval time, content hash, returned text, fetch outcome, and linkage to the request/candidate. Treat page text as evidence, never instructions. Failed fetching is not evidence of closure.
3. Persist every request, assistant/tool response, stop reason, usage record, and tool result. Handle `tool_use`, `pause_turn`, bounded output continuation, search-limit exhaustion, and final JSON. A saved tool response is reused on resume. Do not repeat the entire assignment after a transport or parser failure.
4. Separate final JSON extraction from validation: research uses the existing leads contract; preparation and review later supply their own contracts. Count successful live search evidence for research, but do not require a new search for an explicitly evidence-only review packet. Reject incomplete stop states as completed results.
5. Preserve the existing 24-turn assignment ceiling as an additional guard; the category-wide and dollar limits still win. Bound timeouts by remaining worker time and checkpoint before dispatch.
6. Record requested and returned model metadata. Allow only a predeclared provider alias mapping; an unexpected model/version holds the result for diagnosis rather than silently combining conditions.

**Checks:** fake native search/fetch cycle, tool error, length continuation, search-limit response, final JSON after commentary/tool blocks, valid zero leads, missing live research evidence, missing usage, model mismatch, and interrupted resume. Run `test_deepseek_challenger_runner.py` if any shared code is touched.

**Done when:** one fake research and one fake non-research assignment complete through the same adapter without production imports or real network traffic.

## 4. Execute the existing research policy in isolation

**Files:** `research.py`, CLI `run`; `test_evaluation_research.py`, `test_evaluation_offline.py`.

1. Initialize `scratch/<condition>.sqlite3` using only the frozen original package and `ResourcePackageImporter`. Save an explicit map from original IDs to scratch IDs. Reject a scratch path outside the experiment or resolving to the source database, including symlink aliases.
2. Call `prepare_focused_research_job` with explicit category/mode/redaction arguments. Verify the resulting plan against the frozen baseline semantics before dispatch. Reuse `next_focused_research_assignment`, `save_focused_research_result`, and `prepare_focused_gap_pass` on this scratch store.
3. Complete fixed focus passes sequentially, then exactly the existing gap pass. Save validated outputs into the scratch run so later exclusions contain only that condition's discoveries. Do not copy historical later-pass prompts containing Codex's discoveries.
4. Keep the original-policy condition free of an additional challenger. Primary is compared with primary. Scratch completion does not mark any production job complete or create an office export.
5. Make `--dry-run` emit assignments and validation diagnostics with zero provider requests. `run` without `--execute` must not dispatch. `--execute` also requires the sealed protocol, authorized envelope, and stage eligibility; a command-line flag cannot manufacture authorization.
6. Run a synthetic whole category, interrupt it, resume it, and compare results/charges with the uninterrupted version. Freeze the output and produce a summary of counts, time, source outcomes, and spend, keeping unknowns visible.

**Checks:** hidden-reference leakage through subsequent exclusions, original redaction semantics, duplicate invocation, distinct programs sharing a domain, zero-lead pass/gap behavior, invalid result, capped category, changed manifest, and prohibited production path. Run `test_focused_research.py`, `test_codex_first_research.py`, and `test_worker_metrics.py` alongside new tests.

**Done when:** an offline end-to-end category and recovery scenario pass, with no live provider call and no production changes. Commit M0 and save the exact paid-launch command without executing it until its gate is satisfied.

## 5. Run Housing and make the first decision

**Files:** `audit.py`, minimal actuals/projection output in `cost_report.py`; `test_evaluation_audit.py`.

**Before paid launch:** verify applicable model/tool/pricing documentation and credential availability without exposing keys; seal those facts; record the already-granted or newly confirmed spending envelope. Follow the worker monitoring instructions. This plan does not itself ask Michael to fund the proposed limit.

1. Run only Housing under `existing-policy`. Preserve the completed, capped, or failed outcome. A capped result is not scored as a completed comparison.
2. Implement `build_audit_packet` with anonymous A/B labels, original outputs, generic essential pathways, and source claims. Keep identity attribution/reveal separate. Freeze judgments before reveal where practical; acknowledge recognizable historical examples.
3. Audit every predeclared essential pathway and each claimed unique useful addition. Separate organization/program/access-route novelty, duplicate, correction, unsupported assertion, omission, and evidence-backed limitation. Credit an outcome once. Verify identity, geography, eligibility, operation, and practical intake from sources. Store dated source evidence and before/after corrections.
4. Record raw errors separately from corrected final outputs. A known useful missed pathway remains a miss even if the model wrote “unavailable.” Attribute plausible historical website/tooling changes separately; use a fresh bounded Codex control only if that ambiguity could change the decision and its scope is authorized.
5. `record_stage_decision` accepts `advance`, `targeted-retest`, or `stop` with result/criteria hashes and reviewer reasons. Advancement requires each frozen essential need to have a supported route or evidence-backed limitation; a missed known useful route cannot pass as a limitation. Repeated consequential errors require a diagnosed targeted retest before expansion. Correct or visibly hold discovered consequential errors before labeling any output ready. Acceptable quality plus useful reduction in Codex work supports advancing; counts alone do not.
6. Produce `reports/housing-comparison.md`, actual usage CSV/JSON, and an initial full-run scenario table. Research has measured anchors; preparation/review/global reconciliation must be marked unmeasured or explicitly assumed at this point. Do not present a complete measured dollar total.

**Done when:** Michael can see what Housing found/missed, its cost/time, remaining Codex work, the uncertainty in the initial projection, and the reason to continue, retest, or stop. M1 is useful even if DeepSeek fails the gate.

## 6. Extend research to Food and Disability

**Files:** existing evaluation modules and runtime records; add tests only for newly discovered defects.

1. Confirm the Housing advancement record and remaining envelope. Freeze compatible baselines and essential pathways for Food and Disability before either condition runs.
2. Execute one category at a time with the same model/settings and original policy. Derive pass counts from actual frozen playbooks, including default focused strategies; do not assume every category has Housing's number of passes.
3. Repeat the source audit and stage decisions. Report each category separately before combining results. Preserve unsuccessful categories in totals; do not quietly substitute another category to improve the apparent result.
4. Update the actuals and projection. Record source/date/setup incompatibilities and outstanding uncertainty. Do not scale “average cost of three categories × 21” as the sole office estimate.

**Done when:** all three category outcomes are audited, or an explicit stop/retest decision explains why the sample remains smaller.

## 7. Measure preparation and review, including collection decisions

**Files:** `preparation.py`, CLI `sample`; `test_evaluation_preparation.py`.

**Reuse:** `preparation_contract.prepared_assignment`/`preparation_instructions`, `scout_curation_runner.response_schema`/`worker_prompt`/`validate_links`, `resource_identity` validation, and `prepared_resources` semantic rules. Never invoke the production runner's Codex execution path to draft DeepSeek samples.

1. Freeze an eligible sampling frame of original candidate packets and source evidence from the three categories. Select 12 without replacement using a saved seed: four per category. Select eight distinct difficult cases using the design's risk types. Save IDs, selection reasons, and frame hash. If a stratum has fewer than four eligible packets, record that limitation and reviewer-approved redistribution before sampling.
2. Keep random and purposive groups separate in metrics. Do not expose polished Codex answers to DeepSeek. Historical preparation comparisons must share the five-section/source-check policy or be explicitly labeled incompatible.
3. Draft through the evaluation adapter using the current preparation contract. Create a fresh DeepSeek review context with the original evidence, frozen draft, and explicit review tasks. Retain the draft, review findings, revised output, cost, and corrections independently.
4. Form a compact collection from those 20 packets, preserving overlapping identities and cross-category memberships. Require reviewed program boundaries, supported Types/groups, explicit no-group decisions, starters with contribution/limitations, and a consideration reason for every non-starter resource/category pair. Record a size exception if the sample cannot supply 7–10 valid starters. Do not inflate the fixture with invented resources.
5. Use a scratch identity registry only. Keep the serialized result in an `evaluationOnly:true`, `importable:false` envelope. For checks, assemble an in-memory payload with the exact production field rules and scratch IDs; do not write that payload as an importable delivery. The existing `prepared_resources.validate_artifact` must continue rejecting evaluation-only artifacts. Do not weaken production validation or invoke `prepared_export.export_bundle` or `complete_codex_review` for the sample.
6. Require an independent source audit of the final sample, with consequential errors corrected or visibly held. Mark “source-audited evaluation sample,” never office approved or completed Mesa review. Use labeled diagnostic fixtures for deliberately introduced errors; keep their detection rate separate from natural error frequency.
7. Measure resource-level work and collection-level identity/taxonomy/starter/consideration work separately. Record Codex audit minutes/tokens when available, human minutes, repair cycles, and unknowns. This is the evidence for residual Codex demand and review cost.

**Checks:** reproducible selection, no overlap between groups, every candidate disposition, five sections, preserved conflicting evidence, non-starter pair coverage, no unsafe shared-domain merge, human-state/verification-date preservation, scratch IDs, and rejected evaluation import. Run `test_preparation_contract.py`, `test_prepared_resources.py`, and `test_resource_identity.py`.

**Done when:** there are 20 traceable packet outcomes, collection judgments, original/reviewed versions, and separate random/difficult-group measurements. If the cap prevents completion, report the actual denominator and missing work.

## 8. Deliver the complete-run cost and time report

**Files:** `cost_report.py`, CLI `report`; `test_evaluation_cost_report.py`.

Produce `reports/full-run-cost.md`, `actuals.csv`, `scenarios.csv`, `assumptions.json`, and `measurements.json`. CSV/JSON plus Markdown satisfy the design's machine-readable workbook-equivalent requirement; do not add spreadsheet tooling just for this pilot.

1. Report pilot spend first: settled charges, calculated charges, outstanding reservations/unknown outcomes, paid tools, and Codex audit demand. Separate one-time implementation/evaluation effort from projected recurring office operation.
2. Inventory the actual office category catalog and research plan. Current Mesa has 21 research categories and an additional Miscellaneous delivery category; verify both from the frozen inputs. Include Miscellaneous review even when it has no discovery pass.
3. Map each research category to an observed workload anchor with an explicit complexity reason. Scale research by pass mix/calls/evidence work; preparation by eligible prepared volume and easy/difficult mix; collection work by identities, overlaps, memberships, taxonomy, starters, and exception burden. Show sensitivity for unmeasured global interactions rather than assuming linear scaling.
4. Produce low/expected/high **sensitivity scenarios** for both model arrangements (DeepSeek throughout; DeepSeek plus Codex final review), both preparation scopes (current full reserve; core plus selected reserve), and both research policies once Stage C exists. Before Stage C, mark that policy unmeasured. Keep model, policy, and scope axes distinct.
5. For reduced-scope illustrations use core targets 150 and 200 and selected-reserve counts 0, 100, and 300, bounded by eligible volume. These are what-if inputs, not a recommended reserve policy or automatic cuts. Count distinct newly prepared identities once and category memberships separately. Show marginal cost/time per additional 100 reserve records.
6. Include research, coverage/challenger/follow-up, preparation, collection reconciliation, final review, corrections, retries/recovery, paid tools, and deterministic processing time. Stage A intentionally omits the incumbent production challenger: use compatible saved telemetry or an explicit assumption for that contribution when projecting the full old workflow. Do not silently omit it. Report telephone vetting and future maintenance separately. Do not charge the independent pilot audit as a recurring all-DeepSeek stage while simultaneously claiming the pilot required no Codex audit.
7. Every coefficient carries its unit, source/measurement hash, sample size, measured/inferred/assumed status, and uncertainty reason. If a necessary coefficient is unknown, emit a subtotal and explicit missing contribution, or a labeled assumption range; never silently use zero. Rates must reconcile with the sealed provider billing definitions.
8. Show DeepSeek dollars and remaining Codex tokens/calls/active time side by side. Do not translate subscription usage into invented dollars or percentage of a Max allowance. Account-level usage readings with concurrent work cannot attribute quota consumption to this test.
9. Report summed worker time, calendar elapsed/critical path, tool waiting, supervision, and human review separately. For projection, model sequential dependencies and a stated concurrency level, initially one; show provider/quota interruption assumptions. The discussed 50 hours is a qualified historical workload reference, not a proven calendar baseline.

**Checks:** a hand-calculable synthetic ledger; missing usage; cache/reasoning accounting; duplicate attempt/resume; rejected/capped runs included; per-membership versus per-identity scaling; no duplicate global-review charge; unknown coefficients visible; dollar-cap reconciliation; sequential and parallel time examples.

**Done when:** a reader can reproduce the totals from the ledger and assumptions and see which stages dominate the plausible full-run cost/time. Complete M2 and record the stage-specific model recommendation before building the policy experiment.

## 9. Implement the revised discovery policy behind an experiment switch

**Files:** `coverage.py`, `screening.py`, `evaluation/coverage_playbooks/{housing,food,disability}.json`, optional helpers in `research.py`; `test_evaluation_coverage.py`, `test_evaluation_screening.py`.

Implement condition `coverage-policy-v1`. Keep `existing-policy` unchanged. The first revised version retains the same fixed primary focus passes, replaces its count-driven gap pass with coverage assessment/follow-up, and screens before detailed preparation. Adaptive omission of primary passes is later work, justified only by measured evidence.

1. Add versioned sidecar pathways with `needId`, description, essential/optional priority, applicable scope, evidence requirements, and existing focus keys. A reviewer freezes these without looking at the condition's answers. Keep this list manageable; do not generate every population-by-service combination.
2. Store coverage rows with status (`supported`, `weak`, `unresolved`, `investigated-without-supported-route`), candidate/evidence references, practical access, limitations, investigation date/scope, and reason. Validators enforce evidence/reference rules; models/reviewers supply the substantive judgment. Candidate counts cannot set status.
3. Give a fresh coverage assessor a compact coverage account and source access. Its output contains concerns, proposed corrections, and bounded follow-up assignments. Each assignment names the need/assumption, evidence weakness, expected benefit, and search limit. Zero useful additions is a valid output.
4. Preserve one independent exploration assignment per category, even when the primary claims strong coverage. Count it inside the first follow-up round and the same budget. Use the same DeepSeek configuration for the controlled comparison; fresh context does not imply an independently reliable model.
5. Permit at most two targeted follow-up rounds, including independent exploration. Follow-up requests and assessor calls use the common ledger and category limits. Record whether independent exploration completed; if the cap prevents it, mark that check incomplete.
6. A satisfied stop needs assessed essential coverage and a reason that remaining searches have little expected material value. A budget/time/call/round stop retains unresolved essential gaps visibly. Persist `stopReason`, remaining gaps, round count, and marginal findings by round; never label exhausted budget as sufficient coverage.
7. Screen for credible program identity, direct service, geography, practical contact/intake, and potential contribution before full drafting. Save every lead with source-linked reasons and disposition: `core-preparation-candidate`, `prepared-reserve-candidate`, `research-archive`, or `needs-investigation`. These are workflow decisions, not human Curated state or existing delivery states.
8. Protect rare essential routes and complementary alternatives. Generate proposed core/reserve choices with evidence and allow reviewer decisions; do not implement “take the top 200” or raw-confidence ranking. `research-archive` remains searchable internally but never appears referral-ready. Existing usable reserve remains preserved in the current-scope condition.

**Checks:** many duplicate listings do not prove coverage; one distinct program may cover several needs; unsupported “no service” cannot close a need; zero-addition challenger; exploration despite apparent completeness; two-round ceiling; cap before exploration; unresolved essential stop; rare route preservation; shared-domain distinct programs; no loss/demotion of existing prepared records.

**Done when:** simulated revised-policy categories stop for the correct reason, retain evidence/uncertainty, and do not affect existing-policy behavior or production defaults.

## 10. Compare the revised policy and preparation scopes

**Files:** runtime condition records, audits, and updated reports; repair code only for diagnosed defects.

1. Freeze Stage A results before running the revised Housing condition. Use the same starting package, model/settings, sources/tools configuration, limits, and research date proximity where possible. Record changed web evidence and unavoidable date differences.
2. Compare supported pathways, consequential errors, distinct useful additions, source work, candidate-to-preparation flow, correction burden, dollars, summed worker time, calendar time, and Codex/human audit demand. Report the yield of each research/follow-up round, including useful corrections rather than only new names. Label the direct Stage A comparison as primary-policy versus revised-policy; it does not by itself measure savings against the full incumbent primary-plus-challenger system. Keep any historical challenger contribution separately attributed in that wider projection.
3. Separate two comparisons: policy effect under the existing preparation scope, and the incremental effect of selecting a narrower preparation scope. Reuse already frozen candidate outputs to evaluate selection; do not silently rerun discovery for each reserve count. Any unexecuted preparation savings remain estimated, supported by Stage B coefficients.
4. Expand revised-policy testing to Food/Disability only if Housing warrants it within the envelope. Repeat the smallest informative condition for a material ambiguity; do not require a full four-way matrix or spend the contingency automatically.
5. Record `adopt-for-trial`, `revise-and-retest`, or `keep-existing-policy`, with reasons and scope. Update the cost report with measured versus projected savings. Fewer candidates alone cannot justify adoption.

**Done when:** M3 shows whether the model substitution, discovery changes, and preparation-scope choice each help, with their effects and uncertainties separated.

## 11. Trial another office and integrate only the selected roles

**Files likely involved:** `researcher_roster.json`, `researcher_pair_profiles.json`, `codex_first_research.py`, `office_pipeline.py`, and orchestration documentation. Inspect the selected path at this ticket; do not modify them during M0–M3.

1. Prepare a bounded different-office trial with a frozen baseline, quality criteria, spending envelope, and chosen model roles. Use the same contracts and evidence preservation. Record authorization for that trial before dispatch.
2. Keep an explicit configuration distinction between provider/model and research policy. A default change affects newly created jobs only; existing sealed jobs resume with their original behavior.
3. Integrate only roles supported by stage-specific results. DeepSeek research success does not by itself authorize DeepSeek final review. Preserve **Ready for Codex review** when Codex review remains required. Do not set completion flags to enable export.
4. Before narrower preparation becomes production policy, obtain or locate Michael's actual core/reserve service-level decision and reconcile the prepared-resource contract. Preserve existing human choices and prepared records. A scenario table is not that decision.
5. Validate the bounded office output through the real identity, taxonomy, starter, consideration, preservation, and export gates. Use a fresh scoped output and retain previous deliveries. If UI is changed, perform its required browser checks; this plan does not require a new UI.
6. Make rollback a configuration change for new jobs plus retained sealed evidence, not deletion of results. Document the chosen configuration, limitations, ongoing review responsibility, and rollback trigger.

**Checks:** relevant existing researcher/focused/curation/delivery tests, plus a full `python3 -m unittest discover -s tests` run before production integration. Review failures against the actual base; do not hide unrelated failures. Keep scope-specific semantic review separate from test results.

**Done when:** the other-office trial supports the chosen behavior and the production change is explicitly scoped, verified, and reversible. No full Mesa rerun is required.

## 12. Add shared evidence and refresh incrementally

**New files:** `resource_research_agent/evidence_store.py`, `evidence_refresh.py`; matching tests. Extract the proven evaluation evidence format rather than inventing another one.

1. Store immutable evidence objects by content hash with URL, retrieved time, source type, program/entity link, geographic scope, claims, and fetch status. Allow references from multiple candidates/categories; preserve each claim's original provenance.
2. Add a versioned refresh policy by claim type. Volatile availability/intake windows require run-time rechecking; local scope/eligibility/contact must be assessed for the target office. Stable national guidance can be reused when the saved policy allows it. Freeze actual refresh intervals in configuration before use rather than letting workers invent them.
3. Return fresh-enough evidence or a refresh task; never silently upgrade old evidence's date. Failed refresh retains prior evidence and adds uncertainty. Planning/funding pages do not establish active direct service.
4. Pilot reuse in one bounded category. Measure saved searches/time and stale-claim errors before expanding across offices. Identity and geography checks are prerequisites to sharing facts between programs.

**Checks:** immutable content, same URL changed content, multiple program scopes, stale availability, failed refresh, historical date preservation, and cross-office inapplicability.

**Done when:** evidence reuse demonstrably saves work without transferring unsupported program/local facts. This ticket is not a dependency for M1 or M2.

## 13. Add maintenance proposals; preserve the learning gate

**New files:** `resource_research_agent/maintenance.py`, `maintenance_report.py`; matching tests. Add CLI wiring only after the selected production path is clear.

1. Read an existing trusted office package and compare current evidence. Classify each record as appears-current, changed, possibly closed/moved, cannot-verify, identity/scope conflict, or new related program.
2. Produce field-level old/new claims, dated sources, confidence/uncertainty, provenance links, and concrete vetting questions. Never automatically overwrite trusted fields, mark human verification, or infer closure from a broken page.
3. Apply explicitly confirmed changes only through the existing package/history path, preserving stable IDs, human edits/suppressions, and verification provenance. Keep proposed and confirmed outcomes separate.
4. Preserve candidate → generated resource → final package identity links and normal vetting outcomes. Show a non-blocking learning-readiness count. Carry forward Michael's recorded readiness policy: at least 25 terminal normal-vetting outcomes, three categories, 15 accepted candidates in final packages, and 90% unambiguous provenance with before/after packages for the relevant configuration. Verify that policy against current instructions when reaching this ticket. Reaching it triggers an audit, not automatic activation.
5. Keep playbook amendments proposed/inactive until that audit finds repeated supported patterns and activation is explicitly reviewed/versioned. Model self-assessment and synthetic test outcomes are not phone-vetted ground truth. Do not build automated lesson ranking/distillation in advance of that gate.

**Checks:** broken page without closure, changed phone without silent overwrite, identity conflict, rejected update retained, confirmed change history, missing provenance excluded from readiness, and proposed lesson remaining inactive.

**Done when:** maintenance produces useful reviewable changes, with trusted office data and learning authority preserved.

## Commands and verification discipline

Run commands from the isolated repository root. Existing test invocation:

```sh
python3 -m unittest discover -s tests -p 'test_focused_research.py'
```

After each ticket, run its new test file(s) and only the affected existing suites named above. To run all new evaluation tests after M0 or subsequent cross-module changes:

```sh
python3 -m unittest discover -s tests -p 'test_evaluation_*.py'
```

Use fake transport and synthetic fixtures for automated tests. Tests must fail on accidental live network requests. A separate explicitly executed pilot supplies live evidence; do not run paid tests as part of the normal suite.

**Target CLI contract — implement before use:**

```sh
python3 -m resource_research_agent.evaluation init --config LOCAL_CONFIG.json --out data/evaluations/EXPERIMENT
python3 -m resource_research_agent.evaluation seal --experiment data/evaluations/EXPERIMENT
python3 -m resource_research_agent.evaluation run --experiment data/evaluations/EXPERIMENT --condition existing-policy --category housing --dry-run
python3 -m resource_research_agent.evaluation run --experiment data/evaluations/EXPERIMENT --condition existing-policy --category housing --execute
python3 -m resource_research_agent.evaluation audit-packet --experiment data/evaluations/EXPERIMENT --condition existing-policy --category housing
python3 -m resource_research_agent.evaluation record-audit --experiment data/evaluations/EXPERIMENT --file AUDIT.json
python3 -m resource_research_agent.evaluation sample --experiment data/evaluations/EXPERIMENT
python3 -m resource_research_agent.evaluation report --experiment data/evaluations/EXPERIMENT
python3 -m resource_research_agent.evaluation status --experiment data/evaluations/EXPERIMENT
```

`LOCAL_CONFIG.json`, `EXPERIMENT`, and `AUDIT.json` are placeholders. Ticket 1 must supply a documented config example with no real credentials and CLI help. Extend `run` in Ticket 7 with `--stage preparation|sample-review`, and in Ticket 9 with condition `coverage-policy-v1`. Do not overload `sample` or `report` to start paid work. `record-audit` validates and records a completed review; it never performs or fabricates one.

## Handoff and escalation rules

After each ticket, commit and push only its verified changes on the implementation branch, unless Michael asks to hold. Include a short status entry:

```text
Ticket and commit:
Files/behavior changed:
Checks run and results:
Runtime evidence and hashes, if any:
Actual spend / outstanding reservations / remaining authorized cap:
Unresolved semantic judgments or missing measurements:
Next ticket and exact next action:
```

Continue autonomously for ordinary implementation, diagnosis, and in-envelope recovery. Stop only the affected operation when original inputs cannot be reconstructed, a paid outcome is ambiguous, budget is exhausted, source evidence conflicts consequentially, or a requested change would alter human state/production policy without authority. Preserve all evidence and state exactly what must be resolved; continue independent offline work where useful.

Do not use lower coding effort to overrule a required substantive review. Do not ask Michael to make routine code-organization choices already settled here. If the repository materially diverges from this plan, record the concrete incompatibility and smallest necessary adjustment before proceeding.

## Ready-to-use implementation request

> Implement the next incomplete ticket in `docs/scout-evaluation-implementation-plan-20260927.md`. First read the implementation status and applicable repository instructions. Use an isolated checkout that preserves ongoing Mesa work. Follow the named interfaces and acceptance checks, keep paid calls disabled unless the specific launch is already authorized, and do not change production defaults. Complete the ticket, run its targeted checks, commit and push its scoped changes, and update the handoff with the next exact action. Escalate substantive research/identity judgments instead of treating structural validation as approval.

This document plans future work. No evaluation code, paid research, production configuration change, or review completion is created by publishing it.
