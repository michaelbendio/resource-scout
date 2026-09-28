# Resource Scout: handover for a frontier-level editor

Prepared September 9, 2026. This is a working brief for any capable frontier model, including the current editor, Astra. Scout now has an operator-driven editorial integration; see [Start Scout with an editor](start-scout-with-editor.md). This brief supplies the editorial context.

## Start with the people

**Real service missionaries will use your work to help real people in need.** A misleading eligibility statement, an inaccessible referral, or a missing appointment requirement can mean a wasted trip, lost money, frustration or delayed help.

TSO service missionaries counsel people seeking practical assistance. Many missionaries are retired and may not be especially comfortable with computers. People seeking help may be under considerable stress and have limited money, transportation, internet access, documentation or ability to navigate complicated systems. These circumstances vary: write respectfully, preserve the person's choices and avoid assumptions about an individual's abilities.

The aim is a manageable collection of useful paths to help, with enough alternatives for different needs, eligibility, location and availability. Discovery volume, the fewest possible entries and agreement with another AI are not measures of success by themselves. Housing, employment and clothing are especially common requests in Michael's experience.

## How the pieces fit together

**Scout research → frontier editorial preparation → human curation → office resource package → missionary use → later maintenance and potential learning.** Scout supports saved early/final editor assignments, validated decisions, learning evidence and draft export. An assistant or operator carries out the model assignments. Expanding editorial authority remains a separate decision.

Scout has two intended continuing roles: initial discovery for a new TSO, and periodic maintenance of an existing office's resources. Maintenance should check for changes, useful additions and possible closures. Its frequency is not yet established.

### The location application

`[location].html` means an office-specific application such as `mesa.html` or `provo.html`. These files are generated from the common `new.html` code base. They contain the resource collection and its navigation and editing interface; this is more than a static research report.

A missionary discusses a person's needs, then browses a service **category**, uses **types** and **groups** to narrow the choices, searches by words, or starts with **Find resources for**. They expand promising resources, compare the actual help and entry requirements, and select suitable resource cards to print for the person. Favorites can make frequently used resources easier to find. The missionary's judgment remains central; a filter match is not an eligibility determination.

For example, a missionary helping a parent seek work and suitable clothing can inspect employment options, then clothing resources, check sizes, travel and access requirements, and print the few options useful to that person. They should not have to hand over the whole directory or interpret a long research narrative for every entry.

**Categories describe needs/services. Types distinguish services within a category. Groups describe people for whom a resource has a supported, useful fit.** Veterans and Seniors are groups, not substitutes for identifying the actual service. One resource can properly belong to several categories. Do not create copies merely to put it in different places. Current filter semantics are OR within selected types, OR within selected groups, and AND between those dimensions; selecting two groups does not guarantee a resource serves their intersection.

### The Scout review application and packages

`autoMesa.html` is the Scout preparation/curation copy. It uses the resource application's navigation and editors, but its purpose is to prepare a resource package for the office. A curator edits entries in Admin → Resources, can adjust categories/types and groups, marks entries **Curated** when ready, and saves the selected curated entries as a package. Research-ready, editor-retained, Curated and provider-verified are distinct states.

A resource package is a ZIP containing resource data and any packaged attachments. The office merges curated packages into its `[location].html` application. Multiple curators can divide the work and contribute packages. Preserve stable resource and question IDs, histories, attachments and provenance so their work can be reconciled. Agree on work allocation to reduce conflicting edits; do not invent assignments to particular people.

### Accepted editorial inputs: package or complete HTML

An editor must be able to work from either a resource-package ZIP or a complete `auto[Location].html`, subject to the tools available in its session. Prefer a current package for structured data and packaged attachments; use the HTML to inspect the actual resource presentation and navigation. The supplied Mesa trial packet includes both, prepared from the same original research snapshot.

For a package, read `tso-resources.json` and inventory attachments; preserve the package metadata, complete taxonomy and unknown extension fields. For a Scout HTML file, extract the embedded JSON in the `seed-data` script, then inventory any embedded or externally referenced attachments. Rendering the page alone is not a complete data import. Existing Scout code exposes `extract_scout_seed` in `scout_enrichment.py`; that reads embedded data only. It does not capture a user's browser-local changes or automatically collect all attachments.

At intake, report the actual unique resource count, office, categories/groups, question/history presence and attachment status. Record the file hash and whether scope is full, partial or unknown. If both formats are supplied, compare their identities and consequential data; use the explicitly designated authority or resolve a material mismatch before editing. Do not infer the baseline from filenames alone.

HTML may contain an earlier embedded snapshot while later edits live in browser storage. Scout supports complete research-draft packages; its review editor's curated-resource export is a separate selected-only path. A generated full-draft download may also predate subsequent browser edits. Obtain and verify the full current draft needed for the assignment; never mark resources Curated simply to extract them. If only the original HTML is available, state that you are editing its embedded snapshot. If your tools cannot read the archive or extract the HTML data, disclose the limitation and request an extracted data copy rather than reviewing only visible snippets.

These intake instructions define the editorial handover contract. They do not claim that arbitrary external models are already integrated into Scout's software or that a new universal import adapter has been implemented.

Omitting a record from an editorial draft does **not** instruct a populated office to delete it. Existing-resource retirement uses the office's separate deletion/merge workflow. Check the receiving application's version before relying on newer question/history behavior; do not assume every existing office file already has the latest common code.

## The human curators are partners

Human curators take over the prepared collection and share in the remaining editorial work. They check the wording, services, classifications and access details, call providers, correct errors, add local knowledge, resolve uncertainties and decide what is ready for missionary use. An editor should save them unnecessary calls and confusing interpretation while leaving them a clear, editable record.

In the current Mesa workflow, Sister Dewsnup calls every provider using a script agreed with Stephanie. That script is **not supplied in this handover**; do not claim to have followed it or invent its contents. One appropriate contact may cover several programs, but a shared organization name does not establish a shared intake or one-call verification. Resource counts and actual provider-call counts are different measures.

Michael guides the product and its policies; he is not the office curator. Send provider-specific questions to the curator. Escalate to Michael when a material scope or design decision is required. Ordinary curator questions need not halt unrelated editorial work.

### Questions for the curator

The Resources list shows a red, bold **open question** label when a resource has an unresolved issue. In the editor, give the question, the concrete conflicting or missing facts, and a useful next check in ordinary language. For example: explain whether a provider's page says “Mesa residents” while its application describes a wider service area, and ask which rule applies to the named program. Do not just write “eligibility is unclear.”

The curator enters what they found, including how and when they checked, and marks the question Resolved. They may also need to change the service text or classifications. The answer and history should survive package export, merge and later maintenance. Conflicting human answers need a visible resolution, not a winner chosen merely by a resource timestamp. No open-question badge does not mean the resource is verified.

Administrative research and curator questions do not belong in patron handouts. Separate curator reports may include them for the calling workflow. If your own consolidation settles a structural question, record an editorial action and preserve the original question; do not manufacture a human resolution or phone verification.

## What to expect from Scout today

The checked v2.0 checkout provides these building blocks:

| Capability | What it means for the editor |
| --- | --- |
| Versioned category playbooks and sealed assignments | Research scope, instructions and source package are recorded. An assignment is category/office work; a pass is a bounded part of that work. Existing assignments retain their original guidance. |
| Discovery, existing-resource writing/classification and maintenance workflows | Scout supplies candidates, proposed changes, source references and questions. Research may still be broad, repetitive, overinclusive or mistaken about practical access. |
| Saved responses, resumable stages and reconciliation | Trace a finding to its evidence. Check actual completion and limitations, rather than trusting a “done” label or the existence of a file. |
| An opt-in primary/sampled-comparison protocol | Astra/Codex can research and freeze an initial result; Claude can supply a selected independent comparison; ChatGPT, Grok and Perplexity can supply targeted challenges. These are available roles, not proof all models ran or a mandate to call them on every resource. |
| Review HTML, resource packages and curator questions | Produce editable drafts while preserving human decisions. A draft's existence does not establish human approval. |
| A package/history evidence ledger | Attributable package changes, proposals, adoption and explicit field-verification evidence can be retained. Supported writing, classification and maintenance intake captures comparisons using explicit project lineage. |

**The complete learning loop is not in place.** Evaluating proposed lessons in bounded experiments, controlled activation/rollback of learned guidance, and experience-driven pass selection/stopping remain pending in the reviewed staged plan. Saved observations, JSON/Markdown guidance and an evidence ledger are useful foundations, but do not demonstrate that these later capabilities operated. The September 9 editorial selection was manually authored; no reusable autonomous frontier-editor engine or new lesson activation resulted from it.

The latest broad Mesa run used primary research and Claude comparisons. Do not describe that as all four outside products participating. Consult a run's manifest and actual response receipts for identities, roles, dates, coverage and missing work. Cost and delay were significant; request additional research for a clear decision-relevant reason and record its value. Do not relabel another model's repetition of the primary's finding as a new discovery.

In a sampled comparison, a fresh researcher context receives the permitted neutral inputs and must not see the primary's answers before its result is frozen. An editor who has read a previous editor's decisions is doing an informed second opinion. Both are useful, but report them honestly. Changing the primary model requires an explicit configuration/run record; an external model can perform this handover's editorial review without pretending it has already been wired into Scout's runtime.

## Editing recommendations

### Judge usefulness and practical access

Read the whole entry, especially eligibility, first contact and important limitations. Ask: **Can a missionary help this person take a concrete, realistic next step toward the named help?** Assess the actual program and entry route, not the reputation of its parent organization or how closely its keywords match a category.

Keep meaningful alternatives. Consider service differences, geography, funding variability, eligibility and routes for people who cannot use a common option. Avoid an arbitrary top-three list or a target number per category. Do not add speculative demographic fine-tuning now; Mesa's Native American pathways can be important. Michael's present scope decision excludes Caregiving as a category for TSOs; independently useful meals, rides, parenting or disability-access services still need their own assessment.

Use four dispositions: **retain**, **combine**, **reserve** and **exclude**. Reserve means a potentially useful but conditional, uncertain or currently impractical lead kept out of the ordinary maintained/calling collection. Exclude means out of this collection's scope or unsuitable on the recorded evidence. Neither means the provider is bad or has closed.

Dignity Threads illustrates the access problem: the saved research required an approved nonprofit partner's referral, normally after four to six months in that partner's program, without establishing an accessible approved partner for the person. Possible exceptions do not make that a dependable clothing pathway. Generalize the issue as an incomplete or impractical entry route, not as a blacklist of names or all referral-based services. A named, accessible school counselor or known assistance intake can be a useful intermediary. Months spent receiving training are different from months required before receiving the needed help.

For every reserve or exclusion, give the actual obstacle. Do not discard scarce specialist help simply because it serves fewer people. Evaluate whether it addresses a real need with a usable route and offers value missing elsewhere. When an important service has uncertain access, preserve a focused question or reserve lead rather than invent certainty.

### Combine without obscuring different services

Combine overlapping descriptions when a single entry can clearly explain the help and its entry routes. Preserve meaningful program-specific eligibility, phone numbers, hours, locations, costs, documents and restrictions. Useful source material must not vanish with a duplicate record.

Keep separate programs when joining them would muddy what someone can obtain, who qualifies or where to start. Sharing an agency is insufficient. In the Mesa edit, AzEIP early intervention remained separate from child-care subsidies and developmental-disability services, correcting an earlier combination recommendation.

Prefer the established resource ID for a retained program. Record every source-to-destination mapping, including a donor whose distinct details go to more than one destination. Carry source evidence, attachments, questions and previous human work forward. Make any partial removal of services within a retained umbrella entry explicit.

### Write for the missionary and the person receiving a handout

Use a recognizable organization name plus a brief description of the particular program. Briefly name multiple important resource types: “Clothing, Furniture and Household Essentials” is more useful than several indistinguishable organization titles. Choose straightforward titles yourself; leave significant program-boundary uncertainties visible for curators.

Keep a short description of what the person can obtain, accurate contact fields, and these five Information headings:

1. **Programs and Services** — the help available.
2. **Eligibility Requirements** — who can use it and the requirements that matter.
3. **How to Best Connect** — a usable first step, including appointment or referral arrangements.
4. **Access** — service area, locations, language or disability arrangements and other practical access details.
5. **Important Information to Know** — consequential costs, delays, limits and preparation not already clear above.

There is no fixed word limit. Be concise by removing repetition, promotional language and research commentary. Never shorten away the detail that changes whether someone qualifies, what they must bring, where they must go, what they must pay or whether help is available in time. Avoid false promises of immediate jobs, funds, admission or openings. Review title, description, fields, Information and classifications together after editing; one corrected section must not leave a contradictory promise elsewhere.

An approved writing example is supplied separately. It demonstrates style, not newly verified provider facts. Do not copy its eligibility assumptions into other records.

### Make navigation match the final collection

Assign categories for supported services or accountable entry routes. A residential treatment program's internal job coaching does not automatically make it an ordinary public employment service. Being beside a bus stop is not transportation assistance.

Use types that accurately narrow the resources in each category. After consolidation, remove unused types and correct misleading assignments. Infer groups from actual targeted service, eligibility or meaningful accommodation; general availability to everyone is insufficient. Website translation alone does not establish service in that language. Never infer a person's ethnicity or other identity from language.

Check group membership against retained resources. Remove empty choices; assess the usefulness and prominence of sparse groups without an automatic minimum-members rule. Do not delete accurate memberships just to tidy counts. Introduce new taxonomy only within the assignment's authority, with a reason and supporting resources; flag material scope changes for Michael.

## Run an editorial trial

1. Record the editor/model identity as actually known, source package hash, date, office, scope, available tools and permitted work. Unknown model version or cost stays unknown.
2. Choose **independent editorial comparison** or **informed revision**. For comparison, start from the same original research and common policy brief, save your decisions before opening the previous editor's output, and disclose any prior exposure. This tests editorial judgment on shared research; it is not independent resource discovery.
3. Review every in-scope source record. Save one disposition with a reason for each stable ID. Mark anything not reviewed explicitly; do not silently treat a sample as a full review.
4. Prepare the selected collection, consolidate carefully, rewrite where useful and reconcile types/groups. Save the original records and a durable decision ledger. If tools cannot generate valid HTML/packages, deliver complete proposed changes by ID and say artifact construction remains pending.
5. Validate identities, counts, classifications, five-section structure, attachments, question histories and absence of invented verification. Exercise the actual editor, selected export and office merge where tools permit. Distinguish executed checks from recommendations.
6. Deliver a short report using the common template, with detailed decisions and comparisons available on demand. Highlight changed words in **bold**. Give a few consequential examples rather than asking Michael to review hundreds of rows.

The initial trial authorizes preparing a separate, reversible draft within the supplied scope. Preserve production files and source packages. Do not mark AI selections human-curated, alter verification dates without the corresponding human process, publish an office release or activate playbooks as a side effect. Work through routine editing decisions; promptly disclose missing critical inputs or limits that prevent a valid result.

Michael explicitly wants judgment, including disagreement when a requested approach seems counterproductive. Explain the concern and offer a better approach; do not mechanically optimize for a requested count or accept a prior editor's decision without examining it.

## Turn experience into proposed improvements

Report improvements to Scout's research, playbooks, editing process and curator workflow separately. Include successes worth preserving, not just mistakes. For each proposed lesson, state the evidence, scope, likely cause, alternative explanation, counterexample and an exact change worth testing. A new provider, a factual change after research, a retrieval failure and an instruction ignored by the researcher call for different responses.

Later curated packages and resolved questions are promising evidence. Preserve the curator's answer and checking method, then evaluate what it implies. An accepted edit is not automatically a phone-confirmed fact; a missing record in a partial package is not a rejection or closure. Do not turn one local exception into a global rule, append endless provider-specific instructions, or silently activate suggestions.

Recommend bounded experiments: hold the inputs and other conditions comparable, vary a small instruction or pass, use withheld examples or another suitable office, and measure useful coverage, consequential errors, curator effort, time and cost. The outcome may justify keeping the old guidance. Fresh model contexts matter when withholding answers; another pass by the same model can share the same blind spot.

The future editor's authority should expand separately for selection, consolidation, prose, classification, factual correction and delivery. In your report, name any additional authority that would help, the evidence needed to justify it, and how changes could be audited or reversed. These are recommendations for the upcoming design discussion, not permissions granted by this handover.

## Reference trail

This brief draws on Michael's design and editorial instructions, the approved writing example, current Scout documentation/code, and the September 9 research and editorial artifacts. Live provider facts were not re-researched for it.

Repository references: `docs/scout-writing-example.md`, `docs/scout-open-question-handoff.md`, `docs/scout-increment-5-evidence.md`, `docs/scout-astra-foundation.md`, `docs/scout-playbook-learning-design.md`, `docs/scout-playbook-learning-plan.md`, `resource_research_agent/learning_evidence.py`, and `resource_research_agent/scout_review_template.html`. Historical progress paragraphs may be stale; verify the active run and implementation before claiming a capability was exercised.

Use `frontier-editor-report-template.md` for your result and `frontier-editor-decision-format.md` for the detailed record. The optional Astra comparison pack contains an example report, the previous selection and its editable application. Keep it unopened until your first decision set is saved if making an independent comparison.
