# Curation effort checkpoint: Addiction and Children/Pregnancy

September 19, 2026. **Recommendation: use High for the remaining curation workers,
keep the saved-batch workflow, and use Extra High for Michael's requested Codex
review after curation.** The observed gains do not justify a blanket Extra High
worker setting. This is a practical recommendation under uncertainty; this
comparison cannot isolate the effect of effort.

Children/Pregnancy completed at 17:08 UTC (11:08 a.m. Mountain). Scout stopped at
**2/21 curated categories**. Clothing/Household and the other 18 categories remain
pending. No worker is running and no next category was assigned. Michael requested
this pause to discuss effort; do not resume merely because a recommendation exists.

## What was measured

| Measure | Addiction, High | Children/Pregnancy, Extra High |
|---|---:|---:|
| Candidate records assessed | 196 | 264 |
| Original member submissions behind those records | 229 | 317 |
| Retained resource records | 72 | 136 |
| Candidate dispositions: curated / merged / omitted | 72 / 76 / 48 | 134 / 106 / 24 |
| Successful worker elapsed time | about 11.5 min | 73.0 min |
| Failed whole-category attempt | none | 4.4 min |
| Worker time including that failure | about 11.5 min | 77.4 min |
| Native web-tool actions, successful work | 16 | 200 |
| Native shell-tool actions, successful work | 6 | 98 |
| Native input tokens, successful work | 399,417 | 4,691,586 |
| Cached input within those totals | 185,472 | 2,376,960 |
| Native output tokens, successful work | 35,655 | 216,688 |
| Native reasoning-output field | 9,526 | 125,486 |
| Median information-text words, excluding URLs | 53 | 119 |

The failed Extra High attempt also recorded 17 web actions and 14 shell actions;
its token usage is unavailable. Two native error events describe the same context
failure. The later duplicate-row validation failure is a separate event.

The Extra High workflow took about 90.3 wall-clock minutes from its initial launch
to category completion, including diagnosis, batching implementation and coordinator
transitions. These figures exclude the supervising conversation's usage and final
comparison work. Addiction timing and one Extra High batch use preserved transition
metadata and should be treated as approximate. Token counts are not dollar charges
or subscription quota percentages; do not add cached input to total input, or
reasoning output to total output. Native web actions can contain multiple searches
or fetches and do not establish how many pages were verified.

Retained records are **AI proposals**, not human-accepted unique identities. The
higher Children/Pregnancy count is not an effort-attributable gain. We lack a
matched reference set, human acceptance decisions and measured human review time.
Word counts describe reading volume, not quality or measured curator minutes.

Full counters and artifact hashes: [evidence JSON](curation-effort-results-20260919.json).

## What Extra High contributed—and what still needs review

The Children/Pregnancy output contains useful, specific eligibility, contact and
access details. Examples include separating Root for Kids Early Head Start from
early intervention; distinguishing clinical maternity services, childbirth classes
and specialized support; and expanding shared SBHC/New Season/SUPeRAD records with
pregnancy-related access information. Its information text is typically more than
twice as long as Addiction's. Some additions are useful; many follow naturally
from the different category and from extra source checking.

High already handled consequential distinctions, including FourPoints outpatient
access versus tribal-member residential eligibility, Desert Haven's women/young-child
pathway, and the difference between local care and northern-Utah SUPeRAD access.
The presence of good detailed work at Extra High does not show High was incapable
of doing it under the same batching and review instructions.

Specific review findings:

- **High had a serious geography error.** Addiction retained Maryland's Washington
  County harm-reduction service and displaced Utah's Hand in Hand. The supervising
  audit corrected it using Utah DHHS evidence. The original result and a versioned
  correction remain preserved; this is a separate review intervention, not a
  matched worker-effort result. See the existing audit record in
  `data/st-george-curation-20260919/audit/harm-reduction-correction-applied.json`.
- **Extra High still produced an invalid result.** Batch 4 duplicated an entire
  Root for Kids Early Head Start resource row. Validation stopped the coordinator.
  The rows were fully identical, so Scout now removes that exact duplication,
  retains both native output and a normalization record, and continues without
  repeating a worker call. Conflicting records with a shared ID still fail.
- **A shared resource title became misleading.** The final Children/Pregnancy
  result renames `res-sbhc-outpatient` as services for pregnant and parenting women,
  while its eligibility text still correctly includes youth and adults. Because
  the same ID also appears in Addiction, its title should retain the broader scope.
  This remains a flagged review finding; the original Extra High result is intact.
- **Some promised incorporation did not preserve the practical access route.**
  Candidate 673, Intermountain financial assistance, was omitted with a rationale
  that it belongs inside clinical records. The final maternity/NICU entries still
  lack the specific financial-counselor/application route. The official Utah page
  provides application forms, eligibility guidance and counselor phone 866-415-6556.
  Review should incorporate the useful access details or retain an appropriate
  linked resource. [Intermountain financial assistance](https://intermountainhealthcare.org/for-patients/financial-assistance/utah-idaho-nevada).
- **Category fit needs consistent judgment.** BREATHE CARE remains in
  Children/Pregnancy despite its entry stating infant supplies are unconfirmed;
  the bishops' storehouse candidate was omitted for lacking a verified
  child-specific supply pathway. This is a policy-consistency question to resolve
  during review. Switchpoint's separately evidenced diaper service is distinguishable.
- **Source-version uncertainty remains.** The indexed official SUN Bucks page
  names a 2026 cancellation; a direct retrieval names 2027 and retains 2025
  application dates. Those statements do not prove opposite participation in 2026.
  The current application route was not established. Preserve that uncertainty
  rather than treating candidate 808's omission as a cleanly resolved date issue.
  [Utah DWS SUN Bucks](https://jobs.utah.gov/customereducation/services/sebt/).

Some good omissions also act on uncertainty already explicit in the input. The
expired diaper demonstration lead already warned of a 2025 wind-down; Kids On The
Move leads already warned their local presence was supported only by directories.
The current official respite page lists Orem, Lehi and Springville. These are useful
verification decisions, but not evidence of a capability unique to Extra High.
[Kids On The Move respite locations](https://kotm.org/program/respite-care/).

The comparison spot checks are not a completed final review of all resources.
No real curation job was marked Codex-reviewed to enable Save.

## Limits and the next operating choice

Both categories use the same four historical research sources and 27 saved source
responses, and both received **identical source-audit text**. Children/Pregnancy
has more candidates, different needs and prior curated context. Addiction used one
context; Children/Pregnancy used nine contexts after a real context-window failure,
with more explicit instructions for selective, bounded evidence reads. Later
batches could reread and extend earlier records. These differences prevent a
causal High-versus-Extra-High conclusion. Earlier commentary describing additional
source-audit guidance was imprecise: the audit text itself did not change.

The practical choice is High workers with bounded assignments, complete candidate
accounting, durable checkpoints and validation, followed by the explicitly requested
Extra High Codex review. Keep original results and targeted corrections. Clarify
that a claimed incorporation must actually preserve supported facts and candidate
links, and that shared titles must remain accurate across categories. Track future
worker time and concrete review corrections to judge whether this choice needs
adjustment; no extra replay is necessary to make the current operating decision.

Before claiming unattended reliability, also bound the growing prior-resource
context and test recovery beyond the exact-duplicate case. An automatic final AI
reviewer is not the agreed current workflow: Michael starts a Codex session to
request review after curation. Save becomes available after that review is recorded
against the exact results; later result changes require review again.

At this checkpoint, all four historical database hashes and the frozen research
snapshot remain unchanged. All 36 non-curation tables match the frozen snapshot,
and the working database passes SQLite quick_check. Completed research was not
repeated. The remaining 19 curation categories await the effort discussion.
