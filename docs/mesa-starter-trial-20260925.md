# Mesa starter-set trial — phase 0

Status: implemented evaluation, awaiting Michael and Stephanie's assessment before full prepared-resource implementation.

Open the [readable evaluation](trials/mesa-starter-evaluation-20260925/evaluation.html) or [Markdown copy](trials/mesa-starter-evaluation-20260925/evaluation.md). The [authored proposal](trials/mesa-starter-proposal-20260925.json) records the individual selections and reasons; the [compiled evaluation](trials/mesa-starter-evaluation-20260925/evaluation.json) contains existing full IDs, evidence, and all assessments. Neither JSON file is a production prepared-resources import.

## Scope and results

Housing: 9 selections from 74 records. Food: 10 from 47. Transportation: 9 from 26. ID Recovery: 9 from 22. Total: 169 category memberships assessed, 37 selected memberships, 35 distinct selected records. Paz de Cristo's broad record is shared by three categories. Distinct records are not necessarily distinct providers; remaining identity overlaps are explicitly discussed rather than silently merged.

This uses the reviewed 341-resource Mesa collection (`after-seed.json`) and saved reconciled browser state. All four category IDs appear in Claude's supplied Mesa office catalog. These source files remain unchanged. Later browser edits are outside the saved snapshot and must be reconciled before production delivery.

The reviewer compared the saved descriptions of all candidates in the four categories, read shortlisted records in full, and investigated selected consequential uncertainties using official pages. Every membership has an authored selection/nonselection reason or an explicit saved-human-suppression decision. This is not a renewed full-content audit of every reserve resource. The existing four-section text is available for inspection; it is not misrepresented as having received the new five-section preparation.

The sets deliberately test different kinds of help, eligibility pathways, local and national resources, and alternative providers. They do not maximize Type counts, repeat the old tiers, or claim current capacity. Recommendations include limitations and specific questions for curation.

Two consequential findings changed the proposed selections: ARM's official page currently closes its waitlist to new applicants, and AllThrive's current transportation page does not establish Mesa coverage. Both remain in the retained collection. Other issues include the known A New Leaf name/program conflict, duplicate Family Housing Hub/Paz records, uncertain Mesa I-HELP intake, and housing memberships whose descriptions only establish counseling or navigation. The trial does not mutate these records.

## Code delivered

`resource_research_agent/starter_trial.py` compiles authored decisions into evaluation JSON, Markdown and a readable HTML document. It never invents choices or reasons. It rejects changed source snapshots, missing category assessments, duplicate picks, selections excluded by saved human state, wrong category membership, and evidence that does not occur in the effective saved resource. Short authoring references resolve unambiguously against the exact source snapshot; the output preserves full existing IDs.

The code deliberately uses the `scout-starter-evaluation` discriminator and `evaluationOnly: true`; no production identity registry or prepared-resource import is created. It does not update curation databases, mark review complete, alter Curated state, assign verification dates, launch workers, or resume Cedar City.

Reproduce locally:

```sh
python3 -m resource_research_agent.starter_trial \
  --seed data/mesa-review-20260924/after-seed.json \
  --state data/mesa-review-20260924/browser-state-reconciled-v3.json \
  --proposal docs/trials/mesa-starter-proposal-20260925.json \
  --output docs/trials/mesa-starter-evaluation-20260925
```

The compiled document is committed for reviewers who do not have the original ignored run data. Recompilation requires those exact local inputs; their hashes are recorded in both the proposal and output.

## Validation

Ten focused tests passed for complete coverage and ID reuse, unchanged input state, stale snapshots, saved exclusions, evidence after human overrides, duplicate/missing decisions, category membership, ambiguous authoring references, removed categories, added browser resources, and safe HTML rendering. The final HTML was rendered in an isolated headless Chrome session and visually inspected. Both original input hashes still match; no office data or browser storage was changed. The temporary browser was closed after inspection.

Run the tests with `python3 -m unittest discover -s tests -p 'test_starter_trial.py' -q`.

## Evaluation gate

Michael's adopted design requires a trial judged by Michael and Stephanie before full implementation. See [phase 0](scout-prepared-resources-design-20260925.md): “Michael and Stephanie judge whether the selections and explanations are useful before full implementation.” The document is now concrete and ready for that judgment.

Feedback requested: Which choices should be replaced, and why? Do the contribution explanations make the choices understandable? Are there important missing services or insufficient provider alternatives? The next implementation phase incorporates that feedback before building the production registry, new preparation contract and JSON handoff.
