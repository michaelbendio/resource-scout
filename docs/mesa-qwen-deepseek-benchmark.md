# Mesa Qwen versus DeepSeek Benchmark

Status: The original Phase 1 calibration failed and the full 20-category run was
not started. The redesigned Scout optimization subsequently completed expanded
first-stage comparison v9 on 2026-08-23 and selected 8-bit Qwen for continued
isolated work. The frozen later-stage 8-bit benchmark completed on 2026-08-24;
the corrected later-stage validation is the remaining model run before the
four-stage comparison. No production cutover is authorized.

## Purpose

Compare the quantity, quality, reliability, and elapsed processing time of Resource Scout research performed by:

- The existing DSH and DeepSeek path.
- DSH with local Qwen3.8-27B, free search, and safe local page retrieval.

This is a comparison of the complete research configurations, not merely a model trivia test. The Qwen side includes the local model, DDGS discovery, safe fetching, DSH tool behavior, and Resource Scout prompts. The DeepSeek side includes the historical DSH configuration and DeepSeek server-side search.

Reusable redesign work is category- and location-neutral. Mesa Housing is the
first frozen calibration configuration and regression fixture; verifier,
candidate-promotion, discovery-expansion, provenance, playbook validation, and
Curator-integration code must not hard-code it.

## Comparison scope correction

The frozen DeepSeek Housing result has 30 candidates across all four stages: 10
urgent access, 7 stabilization, 7 specialized housing, and 6 long-term/gap
candidates. Expanded Qwen corpus 6 has 22 packets for urgent access only. A
statement such as "DeepSeek 30 versus Qwen 22" is therefore not a valid quality or
yield comparison, and neither is an unresolved union count.

Compare stage 1 with stage 1 first. DeepSeek's 10 stage-1 records correspond to
roughly 12 distinct identities under the redesigned organization-plus-program
boundary because some historical records bundle programs. The redesigned Scout
corpus has 22 distinct stage-1 identities. Justa Center and Salvation Army are in
both stage-1 results; the earlier statement that DeepSeek missed them was wrong.
Any later overlap, union, or novelty total must use resolved program identities and
like-for-like stages.

## Expanded first-stage quantization result

Comparison 3 used 22 identical packets from corpus 6
(`204ef0cbf2c7d889fc84f544c601bd2bd9b1543a9636a7a9195742c5270e6379`).
The model-neutral report selected option A before model identity and time were
revealed.

| Measure | 8-bit Qwen | 4-bit Qwen |
|---|---:|---:|
| Passed dossiers | 7 | 1 |
| Needs-review dossiers | 15 | 18 |
| Failed dossiers | 0 | 3 |
| Usable dossiers | 22 | 19 |
| Supported field states | 261 | 276 |
| Unknown field states | 245 | 224 |
| Conflicting field states | 0 | 3 |
| Elapsed seconds | 49,148 | 34,197 |

The reveal mapped option A to 8-bit. Quality selected it before timing was known;
the approximately 44 percent longer runtime did not affect the decision. All
attempts were local and unmetered, and the frozen DeepSeek baseline remained
unchanged. This selects 8-bit for the approved optimization plan, not production.

## Revised selected-model first-stage result

The superseding first-stage corpus 8 contains 21 qualified urgent-access packets
from the expanded category-neutral discovery and qualification workflow. Selected
8-bit model-evaluation run 32 completed all 42 model operations—21 extractions and
21 independent verifications—without retry or error.

The original derived verifier interpretation was 7 passed, 10 needs review, and
4 failed. It was preserved before applying application `0.24.0` policy
`verifier-candidate-salvage-v1`. That policy reserves candidate failure for a core
identity, current-service, relevant-geography, or credible-existence defect that
cannot leave a truthful candidate after unsafe fields are removed. Field defects
are quarantined; genuine conflicts remain visible; and a multi-organization host
page does not become cross-program evidence merely because another organization
hosts the page.

Recomputation used only persisted dossiers and completed raw verifier responses:

| Measure | Original derivation | v0.24.0 derivation |
|---|---:|---:|
| Passed dossiers | 7 | 8 |
| Needs-review dossiers | 10 | 13 |
| Failed dossiers | 4 | 0 |
| Usable dossiers | 17 | 21 |
| Supported field states | 266 | 295 |
| Unknown field states | 217 | 186 |
| Conflicting field states | 0 | 2 |
| New model/search/fetch calls | — | 0 |

The immutable source snapshot is
`06ef0ccd6247395b120932e80b6737c7af6e017f22f7ca58e4f5a6e93912630e`;
the new derived snapshot is
`8b8f0f505ba71e42367e851ec6c510f78bff7a471fd6584f642053201c1c4c91`.
Quality-gate report
`86188d29f3e735ef42a90a24780f925237bbe0ad7c788feeb380aff7424130c5`
passes with zero verification failures. Medical respite, disability access,
animal barriers, and language access remain separately recorded targeted gaps;
they do not exclude any of the 21 current candidates.

## Frozen later-stage 8-bit result

Runs 39–41 preserve the first complete selected-8-bit result for the three later
Housing stages. They used frozen corpora 10–12 and the pre-correction v10 evidence
clips and verifier prompt. All 36 operations completed on their first attempt,
locally and without metered traffic.

| Stage | Packets | Passed | Needs review | Failed | Supported | Unknown | Model seconds |
|---|---:|---:|---:|---:|---:|---:|---:|
| Stabilization | 5 | 4 | 1 | 0 | 48 | 67 | 5,396 |
| Specialized housing | 5 | 2 | 3 | 0 | 65 | 50 | 6,213 |
| Long-term and gaps | 8 | 4 | 4 | 0 | 72 | 112 | 7,892 |
| **Total** | **18** | **10** | **8** | **0** | **185** | **229** | **19,501** |

Sequence time was 19,533 seconds (5h25m33s). The quality-gate reports for all
three stages pass and have SHA-256 values
`fa6c0b7578361bc90bd2ecba12ed119ee6c8133f677df30b051b970b3e5c38cc`,
`2c5b1c1e7ec991c3796226eb1d7f4ed16e3db1c297d4b54d98fdc9638ef3ad77`,
and `a06eac37c645462d2e545b99446ad63fd514ca32cdc87b53a63988665b508b68`.
The frozen DeepSeek baseline remained byte-identical at
`0914c6278d36177cc29d75b297249815386355ceb9d634b1ac23372aa18c5491`.

The eight needs-review dossiers were not eight bad candidates. They exposed one
or more upstream evidence defects: unsupported or inflated labels for the City
deposit, Maggie's Place, coordinated entry, and City voucher candidates; a House
of Refuge eligibility phrase clipped mid-sentence; access-point facts attributed
to a regional system; a fax treated as a phone; and Newtown evidence clipped
before its actual Community Land Trust section. Manual review also found a defect
the frozen verifier missed in a passed NAC 55+ dossier: footer/admin and outpatient
addresses were promoted to the program, and Phoenix was inferred as its service
geography from those addresses.

Application `0.29.0` addresses those causes upstream rather than changing the
frozen result. The corrected evidence manifests bind current-page identity labels
and complete-page or exact-section scope; the age-55 NAC packet uses two sections
to keep program-wide eligibility/application text while excluding its property
block and footer. The model prompts add contact-type, access-point/property,
footer/admin-address, service-geography, and exact-program-URL checks. The old
literal gap matcher is also replaced by explicit any/all tag equivalence and
non-candidate operational checks. That reduces the honest later-stage gap set
from 23 to 15—4 stabilization, 6 specialized, and 5 long-term—without another
search and without promoting a weak lead.

The corrected run will receive new corpora and v11 labels. It must process all
18 affected packets; selective reruns would make the comparison invalid.

## Frozen DeepSeek baseline

The active Resource Scout database currently contains 20 completed Mesa research runs, each with four completed stages.

Baseline totals:

- Categories: 20
- Completed stages: 80
- Saved candidates: 536
- Mean candidates per category: 26.8
- Successful final-attempt stage time: 15.33 hours
- Mean successful final-attempt time per category: 46.0 minutes
- Mean successful final-attempt time per stage: 11.5 minutes
- Fastest category: Employment, 35.8 minutes
- Slowest category: Seniors, 50.7 minutes
- Smallest candidate set: Transportation, 18
- Largest candidate set: Utilities, Phone, Internet, 33

The 20-category baseline is:

| Category | Candidates | Successful final-attempt minutes |
|---|---:|---:|
| Housing | 30 | 44.2 |
| Food | 24 | 45.4 |
| Employment | 24 | 35.8 |
| Mental Health | 29 | 45.3 |
| Medical, Dental, Vision | 32 | 46.0 |
| Reentry Support | 30 | 48.8 |
| Addiction | 25 | 40.9 |
| Children/Pregnancy | 28 | 44.9 |
| Clothing/Household | 26 | 47.6 |
| Disability | 31 | 44.3 |
| Domestic Violence | 29 | 49.8 |
| Education | 26 | 44.5 |
| Financial Assistance | 24 | 50.6 |
| Homeless Services | 26 | 48.7 |
| Immigration | 26 | 49.0 |
| Legal | 30 | 48.8 |
| Seniors | 22 | 50.7 |
| Transportation | 18 | 45.9 |
| Utilities, Phone, Internet | 33 | 46.1 |
| Veterans | 23 | 42.8 |

The imported Mesa package contains 22 category definitions. ID Recovery and Miscellaneous are not represented in the historical 20-run baseline, so they are excluded from this comparison. They may be researched separately later but must not be added only to one side of this benchmark.

## Timing caveat

Resource Scout resets a stage's `started_at` timestamp when a failed stage is resumed. The 15.33-hour figure therefore sums the successful final attempts and avoids long wall-clock gaps, but it does not include time spent in overwritten failed attempts. Run-level wall time is also unsuitable because several runs overlapped and some completed after restart gaps.

The report must present timing in separate categories:

1. Successful-attempt processing time, available consistently for both configurations.
2. Failed-attempt and retry time, reconstructed for DeepSeek when evidence exists and captured prospectively for every Qwen attempt.
3. End-to-end wall time for the Qwen benchmark schedule.
4. Throughput under the chosen sequential schedule.

Unknown historical failed-attempt time must remain labeled unknown rather than estimated into the primary number.

## Isolation and reproducibility

The benchmark must not run against the live production database.

Before Qwen research begins:

- Copy the live database to a dated benchmark database.
- Record SHA-256 hashes for the source database, benchmark copy, and Mesa resource package.
- Record the 20 baseline run IDs and their four stage IDs.
- Export a machine-readable baseline manifest containing prompts, stage definitions, results, candidates, sources, timestamps, errors, and available usage data.
- Preserve the original files unchanged.
- Use the exact baseline `prompt_json`, category, assignment, service area, imported package snapshot, stage keys, stage titles, and stage instructions for the Qwen run.
- Prevent proposed Qwen lessons or discoveries from changing the starting context of another category.

Later stages within a Qwen category should receive that Qwen run's prior-stage findings, just as the production workflow operates. This measures the real end-to-end research system. If a model-only replay is later desired, it should be a separately labeled experiment using captured identical stage prompts.

## Attempt recording

Every Qwen stage attempt must retain rather than overwrite:

- Run, category, and stage identity.
- Attempt number.
- Start and completion timestamps.
- Status and error.
- Resolved model, quantization, runtime, context, and reasoning level.
- Search and fetch providers.
- Prompt size when available.
- Model usage and generation metrics when available.
- Search count and fetch count.
- Raw output size.
- Parsed-result success or failure.

This attempt history is benchmark provenance and should also improve ordinary Resource Scout diagnostics.

## Execution schedule

Do not launch all 20 local runs immediately and do not run them concurrently on the single Mac model server.

### Calibration A: one stage

Choose a representative stage with several expected searches and primary-source checks. Record:

- Model load time.
- Prompt-processing time.
- Total stage time.
- Search and fetch activity.
- Candidate count.
- Structured-output validity.
- Peak memory pressure.
- Errors or retries.

Gate: the stage completes correctly without metered traffic or unsafe fetching.

Recorded calibration evidence (2026-08-21):

- 8-bit attempt 1 was stopped and retained as a failed attempt after 30 minutes 25 seconds. Six full-page fetch turns had grown as large as 33,088 prompt tokens and the stage had not returned a result.
- 8-bit attempt 2 capped fetched text at 30,000 characters and instructed Qwen to use no more than two searches and five fetches. It completed in 33 minutes 21 seconds with six valid candidates, 40,791 output characters, and no metered traffic.
- The matching DeepSeek stage completed in 11 minutes 53 seconds with ten candidates and 62,717 output characters.
- The tuned 8-bit output was detailed and Mesa-focused, but it remained about 2.8 times slower, found fewer candidates, and averaged fewer evidence items per candidate (1.7 versus 3.3).
- Result: do not advance the 8-bit configuration unchanged. Calibration restarts with `mlx-community/Qwen3.8-27B-4bit`, retaining the tuned fetch and tool budgets, to test whether faster decode preserves acceptable quality.
- The 4-bit attempt completed in 17 minutes 58 seconds using about 15.2 GB resident memory. It returned five candidates, 35,890 output characters, 13 evidence items across 12 domains, and no metered traffic.
- Compared with tuned 8-bit, 4-bit was 46% faster, used roughly half the resident memory, and improved evidence density from 1.7 to 2.6 items per candidate, although it returned one fewer candidate. Compared with DeepSeek, it was about 1.5 times slower and returned half as many candidates in this stage.
- Result: 4-bit passes Calibration A's correctness, safety, and operational gate. Calibration B uses this configuration unchanged so the complete-category comparison can show whether lower stage quantity persists or is offset by specificity and source quality.

### Calibration B: one complete category

Run all four stages sequentially for one representative category. Compare its result with the corresponding DeepSeek baseline and project the full 20-category duration.

Gate: decide explicitly whether to continue unchanged, adjust reasoning, change quantization/runtime, improve search or fetching, or stop. Any configuration change restarts calibration so the 20-category run uses one consistent stack.

Recorded Housing evidence (2026-08-21):

| Measure | Local Qwen 4-bit | DeepSeek baseline |
|---|---:|---:|
| Successful stage time | 71.6 minutes | 44.2 minutes |
| Candidates | 13 | 30 |
| Raw stage output | 126,619 characters | 213,395 characters |
| Evidence items | 43 | 113 |
| Unique evidence domains | 33 | 60 |
| Evidence items per candidate | 3.31 | 3.77 |
| Candidates with evidence | 13 of 13 | 30 of 30 |
| Candidates with official, government, or direct-provider evidence | 9 of 13 | 27 of 30 |

Qwen stage results were 5, 3, 3, and 2 candidates in 17:58, 19:16, 16:35, and 17:48. The fourth stage emitted a substantively complete 29,547-character JSON result but omitted its final top-level closing brace. A narrowly scoped parser repair added only that single missing brace, after verifying that strings and every nested object and array were otherwise balanced. The captured attempt was then accepted without another model or web run; the original completion time and raw output remain preserved.

The Qwen result contains several strong Mesa or Maricopa County resources and explicit unknowns, but its breadth is materially below the baseline. Seven resource families clearly overlap the DeepSeek set despite naming differences. Qwen also surfaced six different entries, including I-HELP, AHCCCS Housing Programs, and Eden Village, while DeepSeek covered substantially more emergency, family, eviction-prevention, medical-respite, and transitional programs. Two Qwen entries in the final stage are less immediately actionable for Mesa: a Phoenix-administered waitlist and a 21-unit Mesa development that was not yet accepting applications.

Gate decision: do not begin the 20-category run unchanged. This configuration is 62% slower for Housing and produced 57% fewer candidates with slightly lower evidence density. Applying its observed time ratio to the 15.33-hour DeepSeek baseline projects about 24.8 successful-attempt hours for 20 categories, before retries. Applying its candidate ratio projects only about 232 candidates versus 536. Keep the 4-bit model and local runtime, but recalibrate the agent policy for greater breadth, explicit per-stage candidate targets, and deterministic search/fetch limits. Any tuned result is a new calibration and must not be mixed into the final 20-category dataset.

A second Calibration A tried that tuning with a six-to-eight candidate target, four searches, seven fetches, eight search results per query, and shorter fetched text. It completed correctly in 19.0 minutes with six candidates and 38,279 output characters, but produced only 11 evidence items across 10 domains. That was one more candidate than the conservative 4-bit run, at slightly greater elapsed time, while evidence density fell from 2.60 to 1.83 items per candidate. Several results were broad routing concepts rather than clearly named, actionable programs. It remained far behind the matching DeepSeek stage's ten candidates and 33 evidence items.

Final Phase 1 decision: stop before another category or the full run. Retain the original conservative two-search/five-fetch policy as the opt-in local configuration, now enforced deterministically by the Resource Scout plugins. Local Qwen is operational, private, and unmetered, but this evidence does not justify replacing the current DeepSeek research path. Phase 2 replacement work is therefore not started. A future model/runtime/search change must begin a new labeled calibration rather than reuse these results.

### Full run: 20 categories

Not executed in Phase 1 because Calibration B and the tuned Calibration A retry failed their gates.

- Run one category at a time.
- Run stages in their normal order.
- Permit pause and restart between categories.
- Use one locked configuration for all 20 categories.
- Record every failure and retry.
- Do not silently rerun a poor result until it looks better. A retry must have a recorded operational reason.

## Quantity measurements

Measure all 20 categories and all candidates.

### Output volume

- Candidates per category and stage.
- Total candidates.
- Unique organizations and programs after normalization.
- Candidate overlap between Qwen and DeepSeek.
- Candidates unique to each configuration.
- Output size and structured sections produced.

### Duplication and novelty

- Strong matches to the imported Mesa package.
- Duplicate candidates within a category.
- Duplicate candidates across categories.
- Same organization represented as legitimately distinct programs.
- Broad directories incorrectly presented as individual resources.

### Evidence and completeness

- Sources per candidate.
- Unique source domains.
- Share of candidates with at least one reachable source.
- Share with an official or direct-provider source.
- Broken or blocked URLs.
- Presence of service area, eligibility, cost, hours, contact, intake, and restrictions.
- Explicit unknowns rather than unsupported assertions.

Quantity is not treated as quality. More candidates may indicate better coverage, duplication, fragmentation, or noise; the quality review determines which.

## Reliability and performance measurements

- First-attempt completion rate.
- Structured-output validation rate.
- Tool-call errors.
- Empty-search and fetch-failure rates.
- Retry count and reason.
- Successful-attempt time per stage and category.
- Total failed-attempt time.
- Total benchmark wall time.
- Model load and restart events.
- Peak memory pressure.
- Resource Scout responsiveness during sustained research.

The primary speed comparison uses summed successful-attempt stage time. Failure overhead is reported separately and also included in a secondary total-work figure where both sides have evidence.

## Quality evaluation

Quality has two layers: automated evidence checks over every candidate and blinded human review.

### Automated checks over every candidate

- Required structure is valid.
- Candidate name and category are usable.
- URLs are syntactically valid and reachable when checked.
- Claims have cited evidence.
- Official/direct sources are distinguished from directories and lived-experience sources.
- Key access fields are present or explicitly unknown.
- Duplicate signals are calculated consistently.
- Unsupported time-sensitive claims are flagged.

Automated checks are quality indicators, not final judgments.

### Blinded human review

Generate a benchmark review kit that hides model names, timing, and configuration. Randomize which result is labeled A or B independently for each category and retain the mapping separately until review is complete.

The kit should support all candidates. If reviewing every candidate is impractical, select a reproducible stratified sample before looking at model identity, with representation from every category and every stage.

Candidate-level judgments:

- Acceptable resource.
- Research further.
- Already known.
- Wrong category.
- Reject.
- Critical factual or safety problem.

Candidate quality dimensions, scored consistently:

- Correctness and evidentiary support.
- Practical actionability.
- Specificity of the actual program or service.
- Eligibility and service-area clarity.
- Contact and intake usefulness.
- Appropriate handling of uncertainty.
- Source quality and recency.

Category-level judgments:

- Which result set has better useful coverage: A, B, or tie?
- Which contains less duplication or noise?
- Which gives a curator better material with less corrective work?
- Are important service pathways missing from either set?

The model-identity mapping is revealed only after judgments are saved.

## Curator artifacts

The existing Curator format should remain the basis for practical candidate review. The benchmark may add a batch export or comparison wrapper, but it should not create a separate incompatible review model.

Expected artifacts:

- A frozen DeepSeek baseline manifest.
- A Qwen result manifest with complete attempt provenance.
- Curator-compatible exports for both configurations.
- A randomized A/B review kit.
- A hidden A/B mapping file.
- Machine-readable review decisions.
- A final CSV or JSON metrics table.
- A readable comparison report.

Export files remain explicit user downloads. Their destination is chosen through the browser or device file picker; the server must not assume a Downloads folder or silently write them to an export directory.

## Pass criteria for Phase 1

Production cutover requires all of the following:

- All 20 Qwen categories complete under one locked configuration, or any excluded category has a documented, approved reason.
- No metered model or search request occurs.
- Structured output is reliable enough for unattended staged execution.
- Every retained candidate has reachable evidence or a clearly stated unresolved limitation.
- No unacceptable increase in fabricated, misleading, wrong-category, or unsafe candidates.
- Human review finds Qwen practically comparable to or better than DeepSeek after considering corrective effort.
- Search coverage does not systematically omit important provider classes.
- Duplicate and already-known rates remain acceptable.
- Runtime, memory pressure, and operational stability are acceptable for overnight or multi-day use.
- All automated tests pass.

Failure of a criterion does not automatically reject Qwen. It identifies whether the next iteration belongs in model settings, search, fetching, prompting, or runtime performance. The full benchmark is repeated only after the configuration is locked again.

## Benchmark endpoint

The benchmark is complete when the project contains enough preserved evidence to answer, by category and overall:

- Which configuration found more candidates?
- Which found more unique, usable resources?
- Which produced more duplicates or noise?
- Which provided stronger and more reachable evidence?
- Which required less curator correction?
- Which was more reliable?
- How long did successful work and failed work take?
- Is the local Qwen configuration good enough to become Resource Scout's default production path?
