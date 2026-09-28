# Office-fit rules — 28 September 2026

**Decision (Michael):** these rules are Scout's policy, not an experiment. Add four rules to Scout's research, curation and review, for the
Codex primary researcher and every challenger alike. When they conflict with existing
instructions, settle it "in the way that most narrows the output."

**Why.** The measure of a resource is whether a missionary would hand it to someone
across the desk, not how many Scout finds. In a random sample of 20 Food resources from
the complete Mesa delivery, Michael would hand out 4. Every one of the four was in Mesa
and gave food directly. A sample of 20 from DeepSeek's reviewed Housing, judged the same
way, kept about 8. The failures fell into four patterns, which became the rules.

## The rules (`resource_research_agent/office_fit.py`)

1. **Reach from the office.** An in-person service must be in, or reasonably reachable
   from, the office's own city or service area. A countywide or statewide front door
   (coordinated entry, a hotline that is the real way in, a shelter at a confidential
   site) passes wherever its office is. **A service reached by phone or online passes**
   when the office's residents can use it. A programme limited to another city's
   residents fails.
2. **Main service.** A resource goes in a category only when that category is its main
   service, not something it mentions among others.
3. **Direct contact.** A person must be able to contact or apply to it themselves.
   Referral-only (hospital, caseworker, child welfare, health plan) or already-enrolled
   programmes fail; name the front door instead.
4. **One entry per agency**, unless its programmes differ in a way a client would
   notice: a different phone number, intake or eligibility.

They are written relative to the office, so they apply to every office unchanged.

## Where they apply

- **Research:** `pairwise_runner._research_prompt`, used by the Codex primary and by the
  DeepSeek, Grok and Claude challengers. `RESEARCH_PROMPT_VERSION` is now
  `scout-research-2026-09-28-v5-office-fit`.
- **Curation:** `preparation_contract.preparation_instructions`.
- **Review:** `office_pipeline.review_prompt`.

## Conflicts settled by narrowing

- Curation said *"Retain each distinct, supported, actionable resource, including useful
  reserve options. Do not minimize the collection"*. It now says *"Retain only distinct,
  supported, actionable resources that pass the office-fit rules; ten right resources
  beat a hundred plausible ones."* `tests/test_preparation_contract.py` guarded the old
  wording and now guards the new.
- Review said *"Preserve all resources and all human Curated flags."* Human Curated
  flags are still preserved; a resource that fails a rule is removed, with the rule
  recorded.

## Not changed

- **The evaluation harness** (`resource_research_agent/evaluation/`) keeps its frozen
  prompts, so the DeepSeek and Claude Housing comparisons stay like for like.
- *(Settled the same day.)* This note first left open whether phone and online
  resources count, because Michael had rejected two in the Food sample. His decision:
  **"Phone and online resources count."** Rule 1 now says so.

Tests: `tests/test_office_fit.py`.

## Gaps closed after the merge into `main` (same day)

An audit of every model-facing prompt on `main` after Codex's reconciliation found the
rules missing or contradicted in several live places. Fixed, with a test for each in
`tests/test_office_fit.py`:

- **Default curation** (the schema-2 writing contract, used by `office_pipeline` and the
  server) had no rule text. Its instructions are now `scout_curation.curation_instructions()`,
  led by the rules; `SCOUT_CURATION_ASSIGNMENT_VERSION` is `codex-curation-v4-writing-office-fit`.
- **Prepared curation could reuse a job sealed before the rules**, because its version
  was unchanged. `ASSIGNMENT_VERSION` is now `codex-preparation-v5-office-fit`; v4 jobs
  remain readable. Its objective no longer reads "Prepare every distinct supported
  resource", and an unresolved lead is kept for administrators only if it would pass
  the rules once resolved.
- **The curation worker** no longer says unresolved useful leads "may be retained", or
  that a duplicate should be kept when it contributes to a retained programme.
- **Review** no longer tells the reviewer to preserve every resource identity.
- **Challengers** are sent to look for "front doors a person can contact directly", not
  "referral pathways".
- **The manual challenger** (`pairwise_challenge`) now pastes the rules ahead of its
  assignment.
- **`AGENTS.md`** states the rules, which the review Michael starts by hand reads. It,
  the orchestration guide, the prepared-resource contract and the curation guide no
  longer ask for "useful reserves" or to "preserve all resources".

**Left for Codex:** the evaluation harness's curation step
(`evaluation/preparation.py`) calls the live `prepared_assignment`, so a *new* evaluation
would get the rules at curation but not at research or review. Sealed evaluations are
unaffected. For a like-for-like comparison, freeze a copy of the older instructions in
the harness.
