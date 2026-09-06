# Increment 3A: classification workflow

Status: implemented and software-tested on `v2.0`. The six-resource historical
Provo pilot has completed Codex primary research, all 18 actual ChatGPT/Grok/
Perplexity audits, and Codex reconciliation. Michael has approved the pilot
classifications and reconciliation. Slice 3A is accepted. [3B review tools](scout-increment-3b-results.md) are now
implemented; complete Provo retirement remains pending. [3C navigation and reader
compatibility](scout-increment-3c-results.md) are implemented for development review.
No office package has been exported from the real pilot, and no learning policy
has been activated.

## Michael's implementation acceptance

After implementation commit `2a5ea9c`, Michael said:

> I approve the changes in this implementation. There weren't many.

This records acceptance of the implemented classification workflow. The visible
changes are the classification review and office-definition controls; much of the
work provides evidence tracking, preservation of later office edits, and safe
export. That implementation acceptance did not approve resource classifications
or complete the migration/navigation slices. Michael's subsequent “go ahead”
authorized the proposed definitions and the actual six-resource research pilot.

## Michael's pilot acceptance

After reviewing `autoProvoClassificationPilot.html` on his device, Michael said:

> I found it and reviewed it. I approve. V2.0 will be a significant improvement.

This accepts the six-resource historical pilot and Scout's reconciliation,
including its explicit treatment of uncertain evidence. The exact feedback,
source package hash, guidance hash, reviewed HTML hash, and all six reconciled
proposal hashes are recorded in
`output/provo-classification-pilot/pilot-acceptance.json`.
The reviewed HTML remains unchanged as the acceptance artifact.

Approval does not establish new provider facts: the four underlying operational
questions remain recorded. Production packaging still requires the current office
package and the normal review/export workflow; no office package was changed.
The next discussion is 3B: group usefulness and complete category migrations.

## What is usable

Scout's home page links to **Review categories, Types and groups** at
`/classifications`. Import a schema 3 package, select existing resources, and
identify the office. Original ZIP bytes, complete records, referenced PDF bytes,
research inputs, and review events are retained in SQLite.

Review office definitions before dispatching classification research. Definitions
and aliases live in versioned JSON data tied to the exact connected catalog.
Only explicitly approved definitions can support additions or removals. Existing
memberships with pending definitions can be retained as unconfirmed. A draft
file cannot supply its own approval. New terms stay separate proposals.

Each selected resource requires Codex primary research, independent ChatGPT,
Grok, and Perplexity checks, and Codex reconciliation. The operator delivers
these assignments through the actual services; Scout's page and CLI do not
silently launch them. Every assignment has an exact JSON contract, an input
hash, the office definitions, complete resource information, attachment hashes,
and any explicitly linked prior evidence. Each researcher reports which PDF
bytes were inspected, which observations were supplied, or what was not read.
The software enforces provenance and stage completion; research judgment still
requires real research and human review.

Proposals contain categories, category-specific Types, groups, and a reason for
every prior and proposed membership. Group support distinguishes targets from
accommodates. Empty classifications need an explanation. Unconfirmed prior
memberships cannot silently disappear. Missing terms and population-category
migrations appear separately and are not applied by this slice.

The review page shows current/proposed memberships, program-specific reasons,
source excerpts, original information, attachments, linked accepted writing,
audit findings, and unresolved questions. Curated starts unmarked. Edits clear
acceptance; research metadata stays outside exported resource writing. An
advanced editor supports changes to classifications and their evidence.

Reconnect the current package before review/export. Independent later membership
additions and contact edits are preserved by default. Explicit Scout decisions
opposed by later human edits require a review note and a choice. The final
combination cannot leave Types without their category. A reviewer can explicitly
correct a later membership with evidence; that edit records the current comparison
baseline and preserves the original research result's hash.

Changes to resource writing, identity, local notes, or PDF bytes clear dependent
research and review, retaining previous runs. Catalog changes require matching
definitions; reviewed definition revisions require research under the new
version. Contact-only changes preserve completed research while clearing Curated
marks for review against the latest office record. Material unresolved audit
findings require recorded human resolutions.

Safe exports preserve latest writing, contacts, verification, unknown fields,
taxonomy metadata, history, and referenced PDF bytes. Resource IDs remain stable.
Resource and taxonomy deletion requests are respected. Exports retain exact
bytes and manifests; cancellation or failure does not hide resources. Successful
save acknowledgment hides only packaged resources and requires a fresh package
connection for the next batch.

Writing projects use the same tested lifecycle services but retain their original
two-field contract and prior project identities. Existing state without a project
kind remains a writing project. Each workflow rejects the other kind's project
IDs. The old Mesa-specific classification modules and completed artifacts remain
unchanged; the generic classifier does not import their fixed catalogs or decisions.

## Tests and browser checks

- Full Scout suite: 229 tests run, 228 passed, one optional test skipped.
- Focused writing/classification coverage includes project-kind isolation,
  old-state compatibility, two different office catalogs, exact contracts,
  pending definitions, unconfirmed membership preservation, evidence links,
  category/Type consistency, targeting/accommodation metadata, all required
  audits, stale inputs, linked evidence, deletion requests, explicit corrections
  to later memberships, save cancellation/retry, stale acknowledgment, and PDF
  preservation. Semantic research rules are instructions for the real researchers;
  synthetic responses are not evidence of their research quality.
- Real Chrome browser QA passed at desktop, iPad, and phone widths without
  JavaScript errors or horizontal overflow. Definition review, resource review,
  durable acceptance invalidation, editing, original/current PDF access, canceled
  save, byte-identical retry, save acknowledgment, and unchanged printed writing
  were exercised with synthetic data.
- Both classification and existing-writing exports merged through the actual
  `resource-assistant/provo.html` reader/merge functions in disposable browser
  contexts. Unselected resources and preserved fields survived.

Local evidence is under `output/classification-qa-final/` and
`output/improvement-classification-regression/`. These are synthetic QA artifacts,
not independent AI runs or Michael's approval. No location application sources,
production HTML files, or office resource packages were modified.

## Historical Provo pilot and next decision

The pilot database is `output/provo-classification-pilot/pilot.sqlite3`, project 1.
It contains six selected resources from the already authorized historical v41 ZIP:
CSFP, Provo City Housing Authority, Financial Literacy Classes, DWS Veteran
Services, DWS Overview, and Food and Care Coalition. The three accepted writing
results are linked with their exact result hashes and acceptance record, preserving the
scope of that approval and unresolved provider questions. Original source writing
is unchanged. Linked writing acceptance is not classification approval.

The [pilot definitions](scout-increment-3-definitions.md) cover 20 categories,
six groups, and six Types. **Medically vulnerable** and the other 34 Types remain
pending. The exact catalog and draft definitions are saved in
[`examples/provo-classification-pilot-definitions.json`](../examples/provo-classification-pilot-definitions.json).
The standalone `autoProvoClassificationDefinitions.html` in the pilot directory
is a readable definition-review artifact, not a completed classification review.

The 32 definitions were approved for the pilot as guidance version 2. The real
research is now complete; `autoProvoClassificationPilot.html` is the new portable,
read-only review artifact. The earlier definitions and accepted writing artifacts
remain separate. Pilot acceptance is now recorded separately. No production Curated decisions or
exports have been recorded.

### Actual research results

Across six records, Scout proposes **15 category additions, five Type additions,
and 11 group additions**, with no removal of existing memberships. Two original
memberships are retained explicitly as unconfirmed: PCHA Addiction and DWS
Overview Housing. Seniors and Veterans population categories remain in place
until a complete migration review.

| Resource | Main proposed additions |
| --- | --- |
| CSFP | Pantries; Seniors and Spanish speaking groups |
| Provo City Housing Authority | Employment, Education, Financial Assistance, Homeless Services; Rent Assistance; Seniors group |
| Financial Literacy Classes | Spanish speaking and Families with children, based on documented local class accommodations |
| DWS Veteran Services | Employment, Education, Reentry Support, Financial Assistance; Career; Veterans and Exiting corrections groups |
| DWS Overview | Food and Medical, Dental, Vision enrollment pathways; Career; Veterans, Spanish speaking, Families with children |
| Food and Care Coalition | Homeless Services, Education, Employment, Reentry Support, Addiction through the identified onsite partner; Career; Exiting corrections |

The 18 audits returned 25 findings. Codex addressed 16 and left nine findings
requiring human review, overlapping four underlying questions: PCHA's Addiction
association, current financial-class accommodations, the current veteran reentry
handoff, and DWS's role in the county housing program. Local evidence remains
attributed as local; “supported” does not mean independently confirmed current
availability. These proposals are not instructions to make an immediate referral.

Actual service threads:

- [ChatGPT audit](https://chatgpt.com/c/6a9cfd41-baa0-83e8-ab07-5099eceb82f9)
- [Grok audit](https://grok.com/c/bdbe4d84-0b5d-44c8-b2bd-d46b484493c9)
- [Perplexity audit](https://www.perplexity.ai/search/4fa27584-a820-4393-92d8-916d6145185d)

Codex rendered and visually inspected all 19 pages of the 12 original PDFs.
External auditors received labeled observations, not PDF bytes; their access
records say `supplied-observation`. Accepted writing research for the first three
resources was reused as sealed context, not counted as a new classification audit.
Raw outputs, submitted outputs, exact assignments, reconciliation, and events are
retained in the pilot directory/database. Perplexity's 16 finding field paths
needed transport-only normalization to the permitted field names; IDs, severities,
summaries, assignment hashes, and attachment hashes were preserved.

### Experience to discuss before the next slice

- Catalog labels and approved definitions are different. ChatGPT and Grok
  recommended several existing but undefined Homeless Services Types; Grok also
  recommended GED. Scout kept these pending instead of inventing meanings.
- Absence from a website does not invalidate locally gathered evidence. Spanish
  classes, childcare, interpreter access, and work bus passes need honest source
  attribution and operational confirmation, not automatic deletion.
- Audits are evidence to assess, not votes. One audit missed the explicit JTP
  location on its cited page; another confused its own lack of PDF access with
  Codex's actual visual inspection. These disagreements are preserved with the
  reconciliation reasons.
- Grok found the [live official staff page](https://jobs.utah.gov/veteran/employstaff.html)
  confirming Anfred Morillo. Codex checked
  it and did not replace the local contact using an older staff PDF. A search
  result for the [WIOA plan](https://jobs.utah.gov/wioa/wioastateplan.pdf)
  also exposed older text than the live 2026 PDF; a
  freshly returned search result is not necessarily freshly verified content.
- Program-specific evidence matters: childcare can accommodate parents without
  making financial classes a Children/Pregnancy service; an onsite jail-transition
  program supports Reentry Support while a general apprenticeship flyer welcoming
  applicants with convictions does not.

These are observations for discussion, not activated research lessons or changes
to the approved definitions. The current pilot is too small to judge whole-office
group usefulness or retire a population category.

### Pilot validation

All 22 classification tests passed. Independent checks of the completed pilot
verified six complete five-stage research chains, exact original resource records
and PDF bytes, sealed reconciliation hashes, no Curated decisions, and no exports.
Browser checks covered all six resources at 834px and 390px widths, compared every
displayed addition and unconfirmed label with the research data, exercised details,
found no horizontal overflow or JavaScript errors, and confirmed printing selects
only the displayed resource. The iPad and phone renderings were visually checked.
Evidence is saved in `output/provo-classification-pilot/review-checks.json`.

Discuss classification usefulness, uncertainty, and review effort before the
next slice: **3B, group usefulness and complete category migrations**, followed
by **3C, location-app navigation**. The grand plan then continues with maintenance,
proposed research lessons, and adaptive research runs.

## Operator commands

Use the normal `python3 -m resource_research_agent --database PATH` entry point
with `classify prepare`, `status`, `guidance`, `next`, `submit`, `connect`, `events`,
or `export`. The browser handles definition review, proposal edits, and Curated
choices. `next --researcher NAME --resource-id ID` scopes dispatch without skipping
required stages. Guidance approval takes an explicit reviewer and the exact JSON
keys `[field,categoryId,value]`; it cannot be inferred from an imported file.

Run the prepared pilot review server with:

```sh
python3 -m resource_research_agent --database output/provo-classification-pilot/pilot.sqlite3 serve --host 127.0.0.1 --port 8766
```

Then open `http://127.0.0.1:8766/classifications?project=1`. Use the existing private
access workflow for another device. Local HTML snapshots do not synchronize edits
with this live server.

Run software checks with:

```sh
python3 -m unittest discover -s tests -q
python scripts/check_classification_workflow.py --output output/classification-qa-new --office-html /Users/michaelbendio/resource-assistant/provo.html
```

The browser script requires an environment containing Playwright and installed
Chrome; the current Mac used `/tmp/scout-v2-browser-env/bin/python`. Use a fresh
output directory for each browser check.
