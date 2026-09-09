# Scout: evaluated learning, efficient execution and frontier editing

September 9, 2026. Michael authorized this design/implementation work after the Mesa editorial trial. This refines the September 7 playbook-learning design; it does not retrospectively change sealed runs or grant automatic lesson activation.

## Purpose and measures

Real service missionaries need a manageable, useful collection to help real people. Human curators check details, call providers and decide what is ready for use. Scout should improve practical access, preserve consequential information and reduce wasted research and curator effort.

Measure useful coverage, consequential errors, wrongly excluded useful resources, lost critical details, active work, wall-clock waiting, retries, user interventions and actual incremental expense. Unknown cost or model identity stays unknown. Token throughput, resource count and agreement with another AI are diagnostic measures, not success criteria. A subscription's included allowance is distinct from additional dollars spent.

Implementation status is recorded in the [current plan](scout-learning-editor-plan.md) and [results](scout-learning-editor-results.md); the section below describes the starting point.

## Existing foundation and missing pieces

The current v2.0 implementation has category playbooks, sealed/resumable research, sampled outside checks, reconciliation, review applications, question/history merging and an attributable package evidence ledger. The manual Mesa edit produced 268 resources from 460 original entries: 41 overlapping entries were folded into retained resources, 123 reserved and 28 excluded. The decisions are AI editorial evidence, not human verification.

The complete lesson lifecycle, bounded experiments, controlled learned-guidance activation and adaptive research policy remain to be connected. The frontier editor is currently a manual process. Broad project checkpoints still reserialize growing project state. These are separate gaps with separate acceptance tests.

## Learning records and responsibility

Three changes have different destinations:

- **Resource facts** update a particular resource through curation, with dated supporting evidence.
- **Explicit product policy**, such as the Caregiving scope decision, is an authorized guidance change. Do not pretend it was inferred statistically.
- **Research/editorial methods** are hypotheses. Store them as proposed, test them and evaluate their limits before activation.

Evidence can come from source-checked model findings, editorial decisions, subsequent human package edits and resolved curator questions. Keep their provenance and strength distinct. A changed field is not automatically a phone confirmation, a partial-package absence is not a rejection, and one curator's answer is not necessarily a global rule. Repeated imports must not multiply examples.

Store exact source artifacts once, by content hash. Small observation records reference those bytes and stable resource/question IDs. Preserve editorial reasons and source-to-destination mappings, including scope removed within retained umbrella entries. Human feedback can confirm, correct or overturn an editorial decision. Periodically examine a small varied sample of exclusions and combinations so learning is not restricted to survivors.

A lesson records supporting observation IDs, its apparent cause, alternative explanation, counterexample, scope, exact baseline guidance/hash, proposed instruction and evaluation question. Existing guidance that was ignored may need better execution rather than another paragraph. Prefer a small general principle with scoped examples to a growing provider-specific rule list.

Lifecycle: observed → proposed → approved for bounded experiment → evaluated → explicitly approved active or rejected. Keep evaluated/rejected versions, supersession and rollback history. A favorable experiment does not activate anything by itself. Activation must change an atomic scoped manifest; assignments already sealed keep their old resolved instructions. The initial delivery implements the proposal/experiment/evaluation portion; production activation is a later explicit checkpoint.

## Bounded experiments

Use the same case inputs, model/product/settings and permitted tools in both arms; vary only the proposed guidance. Each packet has immutable instructions and a hash. Use fresh isolated contexts; do not include expected answers, editorial decisions, proposed-lesson examples or the other arm's response. The coordinator keeps source evidence and evaluation criteria separate. A context receipt is an operator attestation, not proof of what an external service remembered.

Case IDs used as explicit lesson evidence must not also be test cases. Same-corpus saved cases can establish a limited interpretation result; disclose prior coordinator exposure. They cannot demonstrate better discovery in another community. Research-method promotion eventually requires a small real retrieval test on unfamiliar material. Do not confuse an experiment's software validation with learning efficacy.

Persist raw responses before normalization. Require every case to be accounted for. Record actual model/settings, context identity, elapsed time, known cost and interruptions. Permit incomplete/failed/budget-stopped outcomes; never convert them into zero errors or success. Assess consequential differences against supplied evidence with explicit reasons, not an exact-match comparison against the previous editor's choices. Freeze the assessment and its provenance. Report small-sample uncertainty and counterexamples.

An experiment has configured assignment and time allowances. Code can enforce dispatch/result-count limits and mark late results; it cannot guarantee a remote chat stopped generating at a deadline or know hidden subscription usage. No implicit paid API or overflow authorization. Save received work after a limit, mark the limit honestly and prohibit further dispatch until an explicit new allowance is recorded. The first live pilot uses two short saved-case assignments, no web-research tools, existing chat access and no new paid service. An optional model comparison has its own record and allowance.

Model comparisons use fixed guidance; playbook experiments use fixed model configuration. Pin versions when supported and record actual identities otherwise. Keep model-specific operating profiles separate from category research guidance. Use measured performance to propose future routing and budgets; do not implement a complex routing optimizer before there is useful evidence.

## New-office discovery with a frontier-level editor

1. **Establish office scope.** Preserve the actual input package or extracted HTML snapshot, authoritative source, taxonomy, attachments and completeness. Existing browser edits must be included explicitly. An empty new-office baseline is not evidence that the community lacks resources.
2. **Discover a broad set of plausible leads.** Use category playbooks and stable candidate identities. Gather enough program/access evidence for a responsible early judgment; a search snippet alone does not settle suitability.
3. **Early frontier editorial review.** Identify obvious duplicates, unsupported scope and impractical routes before expensive full expansion. Retain promising leads, combine true duplicates and reserve uncertain ones with a reason and a specific possible follow-up. Keep a sample of excluded/reserved leads for later quality checks. No arbitrary category quotas.
4. **Research selected leads and important gaps.** Resolve the actual help, eligibility and entry route. Follow up where a scarce service or likely useful alternative warrants the effort. Internal treatment supports do not automatically become public employment or transportation services.
5. **Independent checks where selected.** Record actual workload as well as category sampling rate. Primary findings stay frozen before outside results are revealed. A raw outside finding is a lead to reconcile, not an automatic correction.
6. **Full frontier editorial pass.** Review the whole collection for practical usefulness, meaningful alternatives, program identity and duplication. Improve titles and concise five-section text without losing critical details; reconcile categories, types and groups. Preserve questions and provenance. Multiple editors can use the same interchange contract.
7. **Human curation.** Deliver a usable auto[Location].html and package with no invented human approvals. Curators call providers, check all details, resolve questions and export their curated entries. Merging into the office preserves their answers/history. Omission from a draft is not an office deletion instruction.
8. **Capture experience.** Compare explicit subsequent packages and editor decisions, queue potential lessons, and produce a short evaluation summary. Normal curation should not require a second large scoring exercise.

The editor is a frontier model exercising whole-resource and whole-collection judgment. Initial authority includes reversible selection/consolidation, supported writing and classification edits within approved scope, and focused curator questions. It cannot invent verification, silently change significant scope, publish an office release, buy model access or activate learned policy. Later authority expansion is evaluated independently for factual edits, taxonomy, scope and delivery.

Integration must be opt-in so existing discovery/research sequences and main's established Scout remain usable. The early and final editor stages have durable assignment/result contracts, model receipts, decisions for every candidate, resumable statuses and explicit output validation. If a model cannot produce the package itself, Scout applies validated structured changes and generates the application; it does not rely on a model rewriting application JavaScript.

## Speed: measure before structural changes

Add opt-in, content-free timing records for serialization, compression, decoding, database reads/writes/commit and execution validation. Record counts/bytes and distinguish success/failure. Instrumentation must not alter saved data, hashes, transaction behavior, resumption or normal CLI output. Measure representative saved-state copies; avoid timing assertions that depend on a particular Mac's speed.

The next proposed storage layout retains immutable evidence and assignments once, with small versioned task/status rows. Updating one result should not rewrite every earlier response. Preserve frequent commits. Before migration, establish baseline operation times, peak memory where measurable, transaction/lock time and bytes rewritten. Demonstrate exact restart behavior and migration rollback using copies; do not mutate the historical Mesa run during benchmarking.

Scheduling changes follow measured dependencies. Independent work may overlap within actual provider limits, while an outside answer remains sealed until the relevant primary freeze. Examine cross-category expansion: the Mesa continuation configured 194 outside checks for 346 tasks, despite category-based sampling. A future planner must expose actual task/check counts and expected work before dispatch, without silently rerolling selections or dropping hard cases.

Preserve responses when delivery fails; request only missing output where possible. Cache/reuse source evidence within permitted roles, with source age and scope recorded. Do not leak the primary's chosen evidence or findings into a claimed blind comparison. Record budget stops and service outages visibly, allowing unrelated work to continue.

## Review and rollout

Each increment ends with a short outcome, executed tests, measured limitations and the next step in the grand plan. No whole-office run is needed to test the initial learning machinery. The first pilot derives one practical-entry hypothesis from Mesa editorial evidence, tests different saved cases in two fresh contexts and keeps the result inactive. A separate Grok/Claude comparison is optional and must not be presented as evidence that the guidance change worked.

Implementation sequence and acceptance tests: [scout-learning-editor-plan.md](scout-learning-editor-plan.md).
