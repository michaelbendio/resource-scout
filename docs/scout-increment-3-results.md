# Increment 3A: classification workflow

Status: implemented and software-tested on `v2.0`. The six-resource historical
Provo pilot is prepared; office definition review is pending, so its real
classification research has not started. This is not completion of increment 3.
No office package has been exported from the real pilot, and no learning policy
has been activated.

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

The [proposed definitions](scout-increment-3-definitions.md) cover 20 categories,
six groups, and six Types. **Medically vulnerable** and the other 34 Types remain
pending. The exact catalog and draft definitions are saved in
[`examples/provo-classification-pilot-definitions.json`](../examples/provo-classification-pilot-definitions.json).
The standalone `autoProvoClassificationDefinitions.html` in the pilot directory
is a readable definition-review artifact, not a completed classification review.

Michael has been asked whether to use these definitions for the historical pilot.
After that decision, record the approved definition keys, perform the real
six-resource classification/audit/reconciliation runs, and present their results.
Do not substitute synthetic QA results or claim this pilot is complete while
that research remains pending.

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
