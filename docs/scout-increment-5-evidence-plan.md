# Increment 5: evidence from curator decisions

Status: the bounded evidence-capture step is implemented. See
[implementation and operator guide](scout-increment-5-evidence.md).
Automatic lesson inference and activation are not implemented by this plan.

## Division of judgment

Scout chooses one short title when identity and service scope are clear. The
curator settles significant questions about identity, access, supported services,
overlap, or retaining a resource. Scout supplies the evidence and a focused
question; routine wording does not require another editorial approval round.
The existing package review/export gate still applies.

The runtime guidance is `plain-language-v4` and `maintenance-v4`. These are
Michael's direct policy instructions, not inferred lessons or phone-vetted
resource outcomes. The current Mesa review already leaves consequential access
and overlap questions unresolved; regenerating it is unnecessary for this rule.

## What is already available

`scout_improvement.py` records reviewer, time, field choices, note, finding
resolutions, connected package hash, and proposal hash. Its export manifest
retains proposals, reviews, and assignment hashes. `scout_maintenance.py` retains
review decisions and prepared export records, and checks the exact package hash
when a saved export is acknowledged. Research history and source packages are
already durable.

These records are useful evidence, but a saved export is not proof that it was
merged into the final office package. A curator's acceptance of a title is not
verification of all service details. Manual changes made in the office app while
reading the HTML report have no automatic review-event link today. The report
remains read-only, as Michael requested.

## Next implementation: collect and link evidence

Build a bounded evidence ledger before interpreting lessons. Reuse existing
review and export records; add immutable links to later office packages. Store:

- Office/collection identity and whether a package is full, partial, or unknown.
- Prior and current package hashes, stable resource ID, and exact field values.
- Scout project/task/proposal/assignment hashes and guidance/researcher versions.
- Available curator decision, reviewer, time, note, and the fields it actually covers.
- Successful export acknowledgment and later package adoption as separate events.
- Evidence level: observed change, linked adoption, or explicit vetted outcome.
- Ambiguity and development-only status, with source references for each claim.

Keep review, delivery, adoption, and vetting separate. Use deterministic event
keys so repeated imports and retries do not create additional outcomes. Preserve
superseded decisions as history; select the applicable decision without counting
both as independent examples. Reordering tags or packaging metadata alone is
not a correction. A resource absent from a partial package is not a deletion.

For manual office edits, compare the later package with the saved proposal and
baseline. Matching text supports adoption only. Do not infer that the curator
called the provider, why a record disappeared, or that unchanged text was
endorsed. If identity or package lineage is consequentially ambiguous, leave the
link unresolved and ask one focused question through the ordinary review flow.
Avoid extra curator scoring or a new report editor.

Human-added resources receive the same provenance treatment. A later addition
is not automatically a Scout miss: compare its timing, category scope, and the
actual delivered research before interpreting it.

## Representative outcomes

| Observation | Evidence retained | What it does not establish |
| --- | --- | --- |
| Curator accepts a straightforward title | Exact title choice and its proposal link | Phone verification or approval of unrelated fields |
| Curator records that goods are only for enrolled residents | Specific decision, supporting note, and affected access fields | A universal rule about this provider's other services |
| Later package adopts that wording | Before/after package and proposal adoption | Independent confirmation beyond the recorded review |
| Resource disappears from a subset export | Observed absence and partial scope | Closure, rejection, or deletion |
| Curator adds a previously missed program | Attributable addition with dates and scope | A general research-method lesson from one case |

## Tests for that implementation

Use synthetic packages to verify exact before/after preservation; idempotent
re-import; partial-package absence; stale or superseded reviews; concurrent
package lineages; explicit merge/split identity links; manual adoption without
vetting; historical-pilot isolation; and distinct research-policy versions.

Exercise a complete synthetic path from proposal through field-specific review,
acknowledged export, and later package import. Assert the correct evidence level
at each step. Include a title-only approval with unresolved access questions so
it cannot become a fully vetted resource outcome. Verify new human additions
and missing proposal links remain accurately attributed or visibly unresolved.

## Discuss the experience before inference

After one small evidence-capture pilot, show Michael the linked observations
and unresolved relationships. Discuss whether they reflect what the curator
actually decided before implementing method interpretation.

Retain the existing readiness review: 25 terminal ordinary-vetting outcomes
across three categories, 15 accepted candidates in final packages, at least 90%
unambiguous provenance, and adequate evidence for the research configuration.
These thresholds trigger a design/readiness audit, not automatic activation.
Repeated independently vetted patterns can then support proposed lessons in
JSON/Markdown, with scope, evidence, evaluation, version history, and rollback.
Direct human policy instructions stay separately attributable and need not be
misrepresented as statistically learned patterns.

Increment 6 later adapts category-specific goals, run counts, and stopping
criteria. Neither automatic inference nor adaptive runs are authorized by
collecting an evidence ledger alone.

Real-package follow-through: the historical Mesa comparison is complete; see the [evidence guide](scout-increment-5-evidence.md#real-mesa-package-comparison-september-6). It produces observations only, not vetted research outcomes.
