# September 9: learning test, editor integration and speed results

Scout now has a working evidence → proposal → paired experiment → assessment path, plus an opt-in early/final frontier editor connected to its existing research engine. A measured checkpoint optimization is implemented. Production playbooks and the completed Mesa delivery were not changed.

## What the real learning test found

Claude desktop displayed **Opus 5, High**. Two separate new chats received the same six saved Mesa cases, one with the existing Clothing/Household playbook and one with an additional practical-entry instruction derived from the Dignity Threads editorial decision. Neither received the previous editor's decisions or the other response. Dignity Threads itself was excluded from the test cases.

| Saved case | Existing guidance | Added instruction | Assessment |
|---|---|---|---|
| ASA Now | Retain | Retain | Both preserved narrow eligibility, documentation and the direct request route. |
| Clothes Cabin | Retain | Retain | Both preserved ID accommodations, frequency, workwear evidence and access limits. |
| House of Refuge household goods | Reserve | **Exclude as a stand-alone public clothing route** | Candidate is more decisive; baseline already identified the resident-only limitation. |
| Valley Bloom school clothing | Retain | Retain | Both preserved the usable school referral rather than rejecting referrals generally. |
| CarePortal | Reserve | Reserve | Both wanted local participation established; the test does not settle reserve versus conditional retention. |
| Electrical apprenticeship | Exclude from Clothing | Exclude from Clothing | **Poor transfer-test design:** category mismatch dominated; this did not adequately test long program duration versus delay before help. |

**Conclusion: no clear accuracy gain.** There was no demonstrated reduction in the tracked consequential-error flags; one more decisive selection is not enough to establish better accuracy. This is useful evidence against adding guidance simply because we can. The lesson remains proposed/evaluated evidence, inactive in production.

The next version of this experiment should be correctly scoped and scored for the uncertainty we actually care about. For example, use Employment guidance when testing a long training program, and predefine how actionable a conditional referral must be before retention is justified. A small unfamiliar-office retrieval test is needed to assess research learning, rather than interpretation of already rewritten facts.

Limits: five in-category cases and one unsuccessful exploratory transfer case; one response per arm; controller had previously seen the corpus; account-level personalization was not disabled/audited. The raw replies and case-by-case assessment are preserved. No provider calls, fresh web verification or human curator judgments were created. Incremental cost is unknown. Recorded workbench elapsed time includes preparation, coding and UI capture; it is not Claude response speed. There were no model follow-ups or user interventions. Clipboard/capture recovery took additional operator work, documented in the receipts. Grok comparison was not run; it remains a separate fixed-guidance experiment.

[Exact packets, raw replies, receipts and assessment](../experiments/learning-pilot-20260909/README.md).

## What the instrumentation showed and what changed

The full saved Mesa project was read **without writing its database**, at project 2, revision 2681. Temporary databases exercised serialization, compression, SQL update and commit. Encoding/compression dominated; database commit was not the bottleneck. Large known-resource collections and other context appeared repeatedly inside sealed assignments.

The new lossless format stores repeated large sections once inside the checkpoint. The decoder restores separate mutable objects, so changing one loaded assignment cannot mutate another through a shared reference. Existing assignment/result hashes, research stages, sampling and original source facts are unchanged.

| Full saved Mesa checkpoint | Previous write format | Shared-context format |
|---|---:|---:|
| Stored checkpoint text | 812,799,240 characters | **11,562,611 characters** |
| Isolated save, including encode/SQL/commit | 16.83 seconds | **6.66 seconds** |
| Decode plus full equality check | 9.18 seconds | **4.63 seconds** |
| Expanded state equality | Passed | Passed |

That is about **61% less save time (2.5× faster)** and **98.6% less stored checkpoint text** in this comparison. The smaller real pilot checkpoint also improved, from 0.431 to 0.167 seconds per save over two/three repetitions. Codec-only alternatives were measured and rejected: several zlib strategies were slower or materially larger, and uncompressed storage tripled the compressed payload.

The full-checkpoint comparison has one legacy save and two compact saves (6.65 and 6.66 seconds), including a repeat after the final code review; the smaller checkpoint has repeated measurements. These are local component tests, not an end-to-end research speed claim or a forecast of future run duration. The old-format save rewrote the same saved state; the new-format save changed its encoding. Source database startup, remote model time, scheduler waits and operator handoff are not part of the save comparison. Raw phase measurements are committed with the experiment.

Remaining measured costs include approximately six seconds of sealed-assignment validation and six seconds identifying repeated context on this large project. A later task/evidence-store redesign could avoid revisiting unchanged material; it was not necessary to obtain this first improvement. Reads still reconstruct the full state. Historical source databases were not compacted in place. [Copy-first conversion and legacy-reader rollback](scout-learning-editor-operations.md#timing-optimization-and-rollback) are available and tested.

## What is implemented and verified

- Exact editorial/package-comparison evidence, idempotent collection, proposed lessons, sealed same-model trials, separate-context receipts, bounded dispatch, raw/partial/late response retention, explicit assessments and no activation side effects.
- Opt-in discovery-lead intake using Scout's existing lead contract; early frontier selection; explicit sampled research configuration; existing research/check/reconciliation engine; final frontier editing; standard HTML and full draft package output.
- Supported field and five-section validation, no invented curation, source/destination accounting, unused Type/group cleanup, exact original/donor records, PDF preservation and refusal to silently combine conflicting curator answers.
- Restart/immutability, invalid identity/hash/receipt handling, malformed response preservation, transactional rollback, legacy/compact checkpoint round trips, no-clobber database copying, timing-output failures and synthetic browser/editor/export/merge checks.

The final verification receipt beside the experiment records the exact test count and result. The external-model test is real; the new-discovery end-to-end test is synthetic. A real new-office/category editor pilot is still required before broad operation.

## Where we are in the grand plan

We have moved beyond merely saving observations: Scout can now preserve an experiment and its actual outcome, including an unconvincing result. Frontier editing is connected to research and delivery as an opt-in operator workflow, with machine-checked accounting and preserved evidence. The first measured storage improvement is complete.

The next increment should be a small real discovery pilot through these editorial stages, paired with a better-scoped learning test. After reviewing that experience, add reviewed guidance activation/rollback and ordinary feedback distillation, then adaptive research passes/model choices. No bulk lesson activation, new whole-office Mesa run or production publication occurred in this delivery.
