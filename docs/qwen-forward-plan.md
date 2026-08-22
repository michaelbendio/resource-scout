# Qwen forward optimization plan

Status: active on 2026-08-22. This plan begins after Checkpoint D and must be
read with `qwen-optimization-handoff.md` and `qwen-optimization-design.md`.

## Goal and decision order

Determine whether local 4-bit Qwen can become an accurate, complete, well-sourced,
high-recall Scout for the Scout -> Curator -> phone vetter -> TSO Resources package
workflow. Decisions remain lexicographic: accuracy, completeness, sources, usable
new candidates, then time. No faster or larger result may conceal an accuracy
failure.

The frozen DeepSeek baseline remains immutable. Search and Qwen inference remain
local or unmetered, with no paid fallback. All calibration work stays outside the
live Scout and Curator databases until an explicit, reversible integration step.

## Preserved starting evidence

- Frozen DeepSeek baseline SHA-256:
  `0914c6278d36177cc29d75b297249815386355ceb9d634b1ac23372aa18c5491`
- Reviewed first-stage corpus 3 SHA-256:
  `a2af690eb3446253c5582844f412322989dd386d366a4f67f6dd93421c086d08`
- Corrected comparison report SHA-256:
  `a01f05cbe6c6c853473e909bb9a0c9a2dd861ab113242cac4f666c5b81bdeb0c`
- Revealed decision SHA-256:
  `48cdb660adb976dbf8f68b5d9031a5d150e3783a027ef182ceef6c2712cda63e`
- Selected optimization input: 4-bit Qwen, with one passed, two needs-review,
  and three true-failed dossiers in the first-stage comparison. This is not a
  production selection.

For discovery work, record this funnel for every branch and run:

1. search results returned;
2. canonical unique URLs;
3. plausible program/referral leads;
4. resolved organization-plus-program identities;
5. package-excluded same-program identities;
6. fetched evidence sources and domains by authority;
7. frozen evidence packets;
8. passed, needs-review, and true-failed dossiers;
9. usable new candidates delivered to Curator;
10. phone-vetted candidates accepted into a later package.

Search saturation must use package-eligible identity novelty, not raw URLs or an
identity already excluded by the current package.

## Ordered work and gates

### 1. Correct the three true failures

The preserved 4-bit failures have different causes and must not receive one broad
exception:

- `City of Mesa :: Homeless Resource Line and Outreach` is an upstream reviewed-
  identity conflation. Split the Homeless Resource Line and Street Outreach
  Services before freezing a corrected corpus.
- `City of Mesa :: Off the Streets` contains Qwen paraphrases and synthesized
  values that do not exactly match their source-support bindings. Its evidence
  also exposes the difference between truly incompatible scalar values and
  complementary descriptive facts.
- `La Mesita Family Shelter :: Family Homeless Shelter` retains organization and
  program claims without exact source-support bindings.

The correction may strengthen extraction instructions and deterministic
post-processing. Scout may conservatively replace an invalid factual-field claim
with an explicit unknown and a visible needs-review finding. It may not invent a
replacement. Identity mismatches, altered or invented sources, and other
structural defects remain true failures. The verifier prompt, checklist, and
strictness are not weakened.

Gate: regression tests pass; the corrected identity review, corpus, prompt policy,
and model run all have new provenance labels; the old corpus and runs remain
unchanged. Re-run only the corrected 4-bit first stage initially.

### 2. Improve unmetered discovery recall

First correct saturation accounting so an existing-package match does not count as
new eligible discovery. Persist both raw identity novelty and package-eligible
novelty so the stopping decision is auditable.

Then improve DDGS discovery in bounded, measurable increments:

- allow a higher per-query result depth and more than six planned queries only
  through versioned configuration, never an unrecorded global cap change;
- expand official/referral pages into specific named programs and provider pages;
- route useful wrong-stage results to their proper Housing stage instead of
  discarding them;
- add targeted queries from uncovered needs, populations, access barriers, and
  referral-page names;
- deduplicate by canonical URL and organization-plus-program identity while
  retaining every query/rank provenance record;
- distinguish no new URLs, no new identities, no new package-eligible identities,
  and no new usable verified candidates.

The first discovery calibration is model-free. Compare each increment against the
same source package and report marginal eligible identities, sources, domains, and
branch coverage. Do not accept more weak directories or generic routing concepts
as a substitute for actionable programs.

Gate: deterministic fixtures cover package-aware saturation, referral expansion,
stage routing, resume behavior, and provenance. A live unmetered discovery-only
run must show improved eligible yield or explain branch-level saturation without
model inference.

### 3. Recalibrate the selected 4-bit workflow

Freeze the improved first-stage corpus and run 4-bit extraction and independent
verification under the corrected prompt policy. Preserve raw output, corrected
dossiers, deterministic remediation, findings, and timing.

Gate: no true deterministic failures; needs-review candidates remain visible with
their findings; source and field metrics do not regress merely to increase count.
Only after this gate may the four-stage Housing configuration be locked.

### 4. Integrate Curator reversibly

Add an explicit optimization export/import path that writes to a separate Curator
inbox or profile. Do not change the normal Scout database, normal Curator inbox,
production adapter, startup defaults, or DeepSeek behavior. Include verification
status, verifier findings, conflicts, unknowns, source evidence, run/configuration
IDs, corpus hash, candidate identity key, and source-package hash.

Verify the export can be removed by configuration rollback and that returning to
the pre-integration commit restores code behavior. Data rollback must be a scoped
removal of the isolated optimization inbox, not a repository rollback that risks
unrelated later work.

Gate: export tests prove passed and needs-review candidates reach Curator, failed
candidates do not, findings remain intact, and existing Scout/Curator operation is
unchanged.

### 5. Close the Curator and package feedback loop

Curator prepares candidates for phone vetting. The vetter interviews the candidate
contact, corrects and completes the resource, and creates a resource package for
TSO Resources. Preserve candidate-to-generated-to-final resource linkage and both
the before and after packages. Merge the vetted package into the Mesa TSO Resources
package through its normal reviewed workflow, then begin a separately labeled Scout
run using that new package as its exclusion set.

Measure whether successive runs find genuinely new package-eligible candidates and
whether marginal yield approaches saturation. Do not assume one new package causes
Qwen to search deeper; the package-aware stopping correction must be in place.

Gate: the second-cycle report distinguishes already merged resources, distinct
programs at the same organization, new usable candidates, and exhausted branches.

### 6. Evaluate a verifier for DeepSeek separately

The frozen DeepSeek baseline has no fresh-context verifier. A verifier could improve
its attribution and unsupported-claim detection, but it creates a new hybrid or
DeepSeek-plus-verifier configuration. Preserve the original baseline unchanged.
Use local Qwen as verifier only under an explicit hybrid label; never forward a
DeepSeek key to the local path and never use metered verification without explicit
authorization.

Gate: compare the new verified result with the frozen baseline and Qwen using the
same quality definitions. This experiment cannot retroactively rewrite baseline
evidence.

### 7. Complete Checkpoint E

After the first-stage accuracy and discovery gates pass, lock the 4-bit artifact,
prompt policy, playbook, query plan, limits, stopping rules, package hash, and all
runtime versions. Run all four Housing stages in the isolated benchmark database,
preserving fine-grained checkpoints and all raw evidence.

Compare the result with frozen DeepSeek Housing and every preserved Qwen Housing
run in the five-priority order. Explicitly decide to optimize again, stop Qwen, or
authorize the remaining 19 categories. Never start those categories automatically.

## Stop conditions requiring user attention

Stop and consult the user if work would require a paid service, production or live
Curator mutation, a source-package merge, weakening a quality gate, discarding
frozen evidence, accepting an unresolved material accuracy defect, or authorizing
the other 19 categories. Ordinary local implementation, deterministic tests,
isolated benchmark runs, and reversible isolated exports may proceed.
