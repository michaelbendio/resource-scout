# Scout: discussion handoff for the next session

September 27, 2026

## Start here: latest decision

Michael will do the **Mesa Housing comparison**. After that, he wants an **Extra High effort Codex session to think through the redesign and make appropriate changes**.

His exact closing direction was:

> I'll do the Housing comparison and have you with extra-high effort think through the redesign and make appropriate changes.

The next session should assess the Housing evidence, revisit the design and implementation plan, and implement the changes the evidence supports. The existing plan is a starting point for that judgment. Its later milestones are not an instruction to implement every proposed feature automatically or to finish every proposed evaluation before discussing the redesign.

Housing can inform primary research and discovery changes. Changes to preparation or final review still require evidence about those stages.

## Why we started this discussion

Mesa research, curation, and final review have become a substantial undertaking. Michael estimated the combined work in the neighborhood of **50 hours**. The design qualifies this as estimated cumulative workload across original research, challengers, current re-curation, and current review, excluding the original curation; it is not a measured 50-hour calendar turnaround.

Scout and the final review produce roughly a thousand or more resource candidates. Michael thinks approximately **150–200 good distinct resources** would be a reasonable useful collection for missionaries at a TSO. A wider search may improve the final collection, but at some point additional discovery mostly adds duplication, preparation, review, and maintenance work.

The priorities are:

1. Shorter reliable turnaround to a useful collection, with the required quality.
2. Lower AI usage and cost, including less correction and supervision work.

Michael reports having a **Max 20x plan** and says his usage limit is a real constraint. DeepSeek is attractive because it is inexpensive and uses a separate API allowance. The question is whether its complete work product is suitable, not merely whether its tokens are cheaper.

## What we agreed to investigate

Two related workstreams emerged:

- A bounded DeepSeek evaluation against saved Codex work, beginning with Housing. Replacing Codex throughout Scout and rerunning all of Mesa would be excessive just to answer the initial question.
- A redesign of Scout's discovery process to improve useful coverage and reduce unnecessary downstream work.

Keep three effects separate: **model choice**, **discovery policy**, and **how many resources receive full preparation**. Otherwise a cheaper run could appear better simply because it did less work or used a narrower quality standard.

The evaluation must also estimate the cost of a **complete DeepSeek office run**, not just the research passes. A hybrid arrangement with Codex final review must be estimated alongside it.

## Design direction already discussed and accepted

- **Keep the playbooks.** Preserve versioned service pathways, alternative vocabulary, source channels, and exclusions. Improve their use rather than discard the approach.
- **Assess supported coverage.** Candidate counts and completed passes do not establish that important needs have practical, well-supported service routes.
- **Change the challenger's role.** Challenge coverage, assumptions, sources, program boundaries, and access details; then conduct bounded follow-up where it could materially improve the collection. Preserve a small independently chosen exploration allowance so it can discover omissions outside the primary's framing. Finding no useful additions can be a valid result.
- **Screen before extensive preparation.** Establish identity, service relevance, geography, practical contact/intake, and potential contribution before spending heavily on drafting.
- **Separate core, prepared reserve, and research archive.** The 150–200 target is a planning range, not a quota or deletion rule. Useful specialized alternatives matter. Unprepared discoveries must not appear referral-ready.
- **Stop explicitly.** Record remaining gaps and whether work stopped for sufficient assessed coverage/low likely marginal benefit or because a budget was exhausted. Unresolved essential gaps remain visible.
- **Reuse evidence carefully.** Share evidence across categories and suitable offices while checking program identity, local scope, and freshness. Do not transfer an organization's general claims to every program.
- **Support maintenance after discovery.** Propose evidence-backed changes to existing collections. A broken webpage does not prove closure; human choices and trusted data are preserved.
- **Keep learning reviewed.** Preserve provenance and real office-vetting outcomes. Proposed playbook amendments remain inactive until the existing readiness/review process supports activation. Model self-assessment is not operational ground truth.

These are agreed directions, not evidence that the proposed architecture has been implemented or that every detail is optimal.

## The proposed comparison and its limits

For Housing, run DeepSeek as an **independent primary researcher** using the existing focused-pass and gap-pass policy. Compare it with one coherent saved Codex primary run. Do not combine Codex's strongest results from multiple runs, challengers, and final review into the baseline.

Give DeepSeek the original office inputs and applicable playbook. Later passes should see its own prior discoveries, not Codex discoveries leaked through copied exclusion lists. Preserve the baseline, prompts, settings, source dates, tool setup, raw answers, and failures. Use native search and direct fetching so routine DeepSeek research does not require a Codex search relay.

Judge essential pathways, useful distinct programs/access routes, practical intake, consequential errors, source quality, and correction work. Equivalent useful alternatives can count; identical names are not required. A missed known useful route cannot be excused by unsupported “unavailable” wording. Distinguish historical web changes and setup differences from model mistakes.

The earlier design proposes Food and Disability next if Housing is promising, then a 20-packet preparation/review sample: 12 reproducibly selected across the three categories and eight deliberately difficult cases, reported separately. Include collection-level identity, taxonomy, starters, and non-starter considerations. These remain proposed extensions for the next session to assess.

A fresh DeepSeek review context does not eliminate correlated errors from the same model. Preserve original errors and corrected outputs separately. Source-audited AI proposals are not office approval, and a small clean sample does not establish universal reliability.

## Cost and time outputs we need

Produce actual pilot spending first, then low/expected/high sensitivity scenarios for:

| Arrangement | Scope scenarios |
| --- | --- |
| DeepSeek research, preparation, and review | Current complete-delivery scope; core plus a selected prepared reserve |
| DeepSeek research/preparation with Codex final review | The same scope scenarios, with residual Codex work shown separately |

Include research, challenger/coverage assessment where applicable, follow-up, preparation, identity/taxonomy reconciliation, final review, corrections, retries/recovery, paid tools, and deterministic processing time. The primary-only Housing experiment omits the incumbent challenger; a full old-workflow projection must add its separately attributed contribution.

Separate uncached/cached input, output and any additionally billed reasoning according to the provider's actual billing definitions. Preserve missing counters as unknown. Do not treat token counts from different systems as interchangeable measures of quality or effort. Compare useful coverage and final usable output per dollar/time, plus remaining Codex and human work.

Distinguish summed worker time, calendar turnaround, waiting/tool latency, concurrency, and human review. Do not turn subscription-covered Codex usage into invented marginal dollar costs or infer account quota consumption from worker hours.

Mark measured versus extrapolated stages and assumptions. Three selected categories are scenario anchors, not a statistically representative office sample. Include incremental cost/time per additional 100 prepared reserve resources. Keep one-time evaluation costs separate from recurring operation.

## Constraints and decisions still open

The design proposes a **$20 total new DeepSeek/paid-tool pilot envelope**, split across stages. It also proposes category time/call limits and bounded diagnosed recovery. These are recommendations, not recorded spending authorization. At launch, locate the actual authorization already granted or resolve the remaining envelope; do not ask again if it has already been settled elsewhere.

The design's suggested DeepSeek configuration and rates must be verified when the test launches. No capability or price conclusion should be based solely on the model name or an earlier challenger result.

Preserve current full usable-reserve scope for the model comparison. A narrower production reserve policy still needs a concrete service-level decision. Preserve five Information sections, stable program identities, human state, 7–10 complementary starters per category with explained exceptions, and non-starter resource/category consideration reasons under the current contract. Starter placements across categories are not the same as distinct resources.

Current Mesa review and its eventual delivery are separate work. Read the latest operational status before touching that work; this discussion did not complete or approve its export.

## What exists now

This discussion produced and published documentation. No DeepSeek Housing outcome has been reviewed in this discussion, and the proposed evaluation/redesign code was not implemented here.

Repository: `michaelbendio/resource-scout`.

Documentation branch: `docs/scout-evaluation-design-20260927`.

- [Design document](scout-evaluation-and-discovery-design-20260927.md): rationale, experiment design, proposed workflow, cost requirements, and decision boundaries. Initially committed as `d288a07`.
- [Implementation plan](scout-evaluation-implementation-plan-20260927.md): 14 bounded tickets, exact file targets, interfaces, tests, milestones, and a reusable implementation request. Published as `c042c53`, together with a link from the design.
- This handoff records the later decision to return for Extra High redesign judgment after Housing. It governs the next conversational step where the earlier milestone sequence could imply otherwise.

The active local Scout checkout is `/Users/michaelbendio/resource-scout-pairwise`. At this handoff it remains on `pairwise-research-experiment` at `bf2655c`, with separate Mesa work and unrelated local changes. The documents were committed and pushed on their existing documentation branch without switching or modifying that checkout. Recheck current state before coding; preserve unrelated work. The ChatGPT project mirror's `sources/` files remain read-only reference material.

## Bring to the next session

Bring the Housing report and paths to its raw outputs, original baseline and hashes, playbook/prompts, provider settings, dated source evidence/audit, usage/cost records, timings, failures/retries, and correction notes. If some measurements are missing, identify them rather than reconstructing unsupported values.

The next Extra High session should:

1. Determine what the comparison actually establishes about DeepSeek's useful coverage, factual reliability, cost, elapsed time, and correction burden.
2. Separate model limitations from search/tooling, source-date, prompt, and workflow effects.
3. Reconsider the challenger, stopping rules, screening, preparation scope, and evidence reuse in light of those findings.
4. Revise the design/plan as necessary and implement the appropriate supported changes, with scoped verification and commits.
5. Identify the smallest additional evaluation needed for decisions Housing cannot support, especially preparation, final review, full-office projections, and another office's generalization.

Suggested next-session opening:

> Read `docs/scout-discussion-handoff-20260927.md` and its linked design and implementation plan. Here are the Mesa Housing comparison results and evidence paths: [insert paths]. At Extra High effort, assess what they establish, think through Scout's redesign, revise the plan where needed, and implement appropriate evidence-supported changes. Preserve ongoing Mesa work and existing delivery contracts, and identify any additional evidence needed before changing preparation or final review.
