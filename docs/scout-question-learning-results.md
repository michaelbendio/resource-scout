# Curator-question learning test — September 9, 2026

**The new lesson did not demonstrate enough benefit to activate.** Both real research sessions completed. The result is saved as `no-clear-benefit`; the lesson remains inactive. The predeclared rule does not trigger a confirmation run.

We tested whether a final check against already reviewed sources would turn unnecessary curator questions into supported facts, while preserving questions that really need a person to settle them. Two fresh Astra sessions researched the same six Denver Employment leads with the same existing playbook and budgets. Only one received the proposed lesson. Neither saw the other response or the scoring rubric.

| Measurement | Existing guidance | With the proposed lesson |
|---|---:|---:|
| Completed resources assessed | 6 | 6 |
| Question entries | 24 | **18** |
| Response words | 1,397 | **1,720** |
| Research process time | 2m 57s | **3m 11s** |
| Recorded web calls | 12 | **11** |
| Confirmed fully source-answerable question issues | 0 identified | 0 identified |
| Partly source-answerable question issues | 1 identified | 0 identified |

An entry can contain several questions. These counts do not measure how many calls a curator would make, how long curation would take, or whether a resource is fully verified. Unavailable source evidence was not treated as a clean result.

## What changed

The lesson version omitted several requests for placement statistics and other outcome reporting. That can make a handoff more useful, but it is **different from answering questions using sources already reviewed**, which was the test's primary measure. It also bundled remaining questions into fewer entries and produced more text overall.

For Work Options, the existing-guidance response asked about meal assistance even though its cited program page partly addressed that subject. The lesson version dropped the subject without carrying over the supported information. Even generously counting that as one improvement, it falls short of the required improvement across **at least two cases**. The page reports meal assistance in its program outcomes; it does not settle a new applicant's current entitlement. [Work Options programs](https://workoptions.org/programs/)

The lesson version also found useful additional material: a dated Work Options application and a discrepancy in ActivateWork/Per Scholas education requirements. Those are worth preserving as observations. Because it retrieved different pages, they do not establish that the lesson corrected failures to use evidence the other session had already reviewed. [ActivateWork admissions](https://activatework.org/learn/tuition-free-tech-training/), [Per Scholas FAQ](https://perscholas.org/faqs/)

Differences cut both ways. The baseline included construction credentials from Second Chance Center's detailed services page; the candidate asked about those credentials after reviewing other pages. Mi Casa's general training page answers some admission questions left by the candidate, but that page was not among its cited sources. Those are retrieval/completeness observations, not proof that the proposed final check helped. [Second Chance Center services](https://scccolorado.org/services-all/), [Mi Casa training requirements](https://micasaresourcecenter.org/career-trainings/)

For Employment First, production-page access differed. One session retained the resource; the other kept it as **needs-check** with contact leads and explicit uncertainty. We did not treat inaccessible pages as evidence that the service had closed, or count that classification difference alone as an error.

## What the learning machinery actually exercised

1. Imported earlier editorial observations with their source package and provenance. These were AI observations, not human phone confirmations or blanket approval of those resources.
2. Distilled a proposed research method, with supporting examples and a counterexample requiring dated-information uncertainty to remain visible.
3. Stored the proposal separately from the unchanged production playbook.
4. Prepared a bounded trial and sealed its criteria before dispatch.
5. Ran two isolated research sessions on fresh leads, then collected their actual replies, timing, usage and source traces.
6. Recorded an immutable evaluation and retained the unsuccessful proposal as evidence. **No guidance was activated.**

This exercises learning evaluation and the decision to withhold an unproven addition. It does **not** demonstrate improved production research from an activated lesson. It also does not exercise maintenance-package feedback from a new human curation cycle.

## What the instrumentation tells us

Fewer questions did not mean less work: the candidate took about **8% longer** and produced **23% more words**. Recorded web-tool intervals totaled approximately 13 seconds for baseline and 12 seconds for candidate. Those intervals do not explain the remaining wall time; model processing, orchestration and other delays were not independently separated.

The CLI reported 106,759 versus 112,413 uncached input tokens, with substantial cached input in both sessions. These are cumulative CLI usage measurements, not fresh prompt sizes. Subscription dollar cost and complete source-page counts were unavailable. We cannot responsibly claim a cost saving, a speed improvement, or a measured curator-time saving.

The useful optimization finding is to measure **finished work and retained information**, not just the number of displayed questions. This small pair provides no basis for another implementation optimization or an adaptive model-selection policy.

## Recommendation and remaining plan

Keep the current guidance. Do not run successive variants just to obtain a positive demonstration. If further investigation is useful, a separately designed test using the **same saved source material** in both sessions could isolate final question editing from retrieval differences. That would answer a different, narrower question; it is not a claim that today's lesson passed.

**Increment 5 remains the only numbered implementation increment left in the current learning/editor plan:** adapt research passes, stopping and model sampling using measured outcomes. It has not started. Today's measurements are useful evidence, but one small pair does not justify changing those policies. Broader operational validation and eventual expansion of editor authority remain separate work.

The complete [experiment evidence](../experiments/learning-questions-20260909/README.md) includes both responses, the predeclared rubric, entry-by-entry question judgments, instrumentation, immutable assessment, and an offline replay. No production office HTML, resource package or active playbook was changed.

## Verification

Offline replay checks artifact hashes, evidence import, lesson distillation, identical baseline/candidate inputs except for the lesson, exact delivery metadata removal, response import, assessment and an empty activation manifest. This validates the saved learning workflow; it does not independently re-research the providers or prove the coordinator's judgments correct.
