# Scout prepared resources, starter sets, and WSRS-TSO handoff

Date: 2026-09-25 · Status: proposed design for discussion; not implemented.

This design turns Michael's September 25 discussion into changes to Scout's AI instructions, stored results, review requirements, and exported data. It incorporates [Claude's artifact feedback](wsrs-tso-scout-artifact-reference-20260925.md), preserving the distinction between user decisions and implementation proposals. WSRS-TSO application design will be discussed separately with Claude.

## 1. Outcome and boundaries

An office receives a fully prepared collection and a manageable recommendation of 7–10 resources per category, each explaining its contribution. Human curators approve the permanent directory. Other usable resources remain available as a reserve for finding help when the published directory does not fit a client.

Scout owns research, AI preparation, identity reconciliation, evidence, proposed taxonomy, AI review, starter recommendations, and the data export. WSRS-TSO owns its search, Ask, human decisions, publication, saved-for-review queue, and storage. auto[Location] remains the existing generated curation workbench; it does not have AI of its own.

No enhancements to [location].html are included. This design does not implement WSRS-TSO, select its AI provider, launch a worker, resume Cedar City's review, or authorize new research. Existing artifacts and human edits remain intact. Shared curation across offices and distance-aware matching are future work; the data should support them without pretending they are already designed.

### Agreed direction

- Keep the broad research net and full AI preparation of usable candidates.
- Replace tiers with a recommended starter set of 7–10 per category and explanations. No three-resource opening set or total ranking of the reserve.
- Choose complementary help and practical alternatives, considering eligibility, access, geography, and provider choice. Do not concentrate referrals unnecessarily or claim knowledge of capacity/funding without evidence.
- Consolidate Types and For groups from the whole collection. Reduce redundant distinctions, not useful selectivity. Retain specific service and population details for search.
- Curated-only and all-resource search are distinct scopes. All resources means the curated collection plus usable reserve resources, not every raw lead.
- A promising reserve resource can be saved for a later human decision. Saving and AI recommendation do not publish it. Human Curated approval publishes it in WSRS-TSO.

The following architecture and field names are proposals, not a finalized consumer contract.

## 2. What exists today

Findings below come from the checkout at `2ba271b`, not an audit of WSRS-TSO or every historical run.

| Existing component | Observed behavior | Design implication |
| --- | --- | --- |
| `candidate_package.py` | Produces a ZIP containing `scout-candidates.json`, with `candidatePackageSchemaVersion: 1`, research runs, candidates, source responses, and a source-package reference. | A separate data artifact already exists, but it is research input to curation, not the reviewed collection described here. Preserve it. |
| `scout_curation.py` | Builds explicit AI assignments; dispositions are `curated`, `merged`, or `omitted`. Reuses prior prepared resource IDs. Instructions prefer the smallest high-confidence proposal set. | Distinguish AI-prepared from human Curated, and stop treating a small prepared collection as a goal. |
| `scout_curation_runner.py` and the curation normalizer | Worker output has a closed schema; the normalizer returns a fixed list of resource fields. | Merely asking for new evidence fields would not preserve them. Prompt, schema, normalization, storage, and export must change together. |
| `manual_consolidation.py` | Some identity keys hash identity signals; some merged keys hash group membership. `resource_package.py` can generate a UUID when no resource ID is supplied. | These mechanisms do not establish stable consumer identities across independent runs. Audit every producer and migration path before claiming that guarantee. |
| `scout_review_priorities.py` | Requires a tier, reason, and saved-resource evidence for every resource/category pair; fingerprints bind proposals to their inputs. | Replace the tier contract with starter-set decisions while retaining evidence, complete assessment, and staleness protection. |
| `scout-workbench-readiness.md` | Requires substantive content, Type/group judgments, all-category priority coverage, and real browser verification. | Revise this requirement alongside its validators; do not bypass existing gates to export a new artifact. |

Source links: [candidate package](../resource_research_agent/candidate_package.py), [curation](../resource_research_agent/scout_curation.py), [runner](../resource_research_agent/scout_curation_runner.py), [identity consolidation](../resource_research_agent/manual_consolidation.py), [resource conversion](../resource_research_agent/resource_package.py), [priorities](../resource_research_agent/scout_review_priorities.py), [readiness](scout-workbench-readiness.md).

The older [product design](product-design.md) describes historical behavior and is not sufficient evidence of the current implementation. This design does not adopt Claude's implementation observations as verified facts about either application.

## 3. Pipeline and responsibilities

The sequence becomes:

1. **Research:** find leads and preserve source submissions and category coverage.
2. **AI curation:** account for every candidate, resolve supported identities, and prepare independently understandable resources with evidence and uncertainties.
3. **Collection-wide review:** check substantive facts, consequential omissions and merges; consolidate the proposed taxonomy; assess every prepared resource/category membership; choose starter sets and explain them.
4. **Validation and export:** check the exact reviewed snapshot and emit the consumer data file. Generate any supported HTML view from the same prepared content.
5. **Human curation in the consuming application:** approve, edit, suppress, pin, or save resources for later consideration. These decisions remain application-owned.

Review remains one sequential reviewer for the current office work, not parallel reviewers. Research, preparation, review, and human approval are separate events. Current curation disposition `curated` means AI preparation, not human approval; the new exchange format must not expose that word with an ambiguous meaning.

## 4. Curation changes

Replace minimization language with: **retain each distinct, supported, actionable resource; exclude or hold a candidate for an explicit substantive reason, never merely to reduce the directory's size.** Full candidate accountability does not require accepting every lead.

Audit existing exclusion instructions as part of this revision. Distinguish a generic directory or referral-only page from an actionable navigation/intake service that itself helps a client. Do not delete all conservative inclusion rules merely to enlarge the reserve; document any changed service boundary and its evidence.

Each usable resource must be understandable outside its discovery category. Prepare its specific services, eligibility, access/intake, costs where established, hours where known, service geography, contact details, sources, and uncertainties. Keep the four current Information sections: Eligibility Requirements, How to Best Connect, Access, and Important Information to Know. Preserve useful service details in description and structured facts rather than inventing an incompatible fifth-section requirement.

Do not erase distinctions such as rent arrears, security deposits, and eviction representation when consolidating labels. Preserve detailed statements in searchable fields and source-linked facts. Do not add keyword lists that imply unsupported services or populations.

During batching, reuse labels whose meaning fits. Retain proposed service/population concepts and evidence for later whole-collection consolidation. Existing curation forbids creating missing For groups; replace that restriction only through a versioned policy that permits proposing concepts separately from approving final taxonomy. Never silently modify an existing office's human-approved taxonomy.

Resolve supported aliases while preserving genuinely different programs and eligibility pathways. A shared organization or website alone is insufficient to merge everything. Preserve program/site distinctions that change access; don't split ordinary locations into duplicates unnecessarily.

Proposed preparation outcomes for the exchange are `usable`, `needs-resolution`, and `not-offered`, each with reasons where relevant. These are preparation states, not confidence scores, tiers, or approval states. Raw leads and omissions stay in the audit. Only usable prepared resources belong in the default referral-search collection; unresolved/withdrawn records remain available for administrative reconciliation. Unknown nonessential details need not disqualify a usable resource, but consequential uncertainty must be visible.

## 5. Types and For groups

Review the full prepared collection before finalizing the proposed taxonomy. Each category has a catalog of Types with stable IDs, labels, definitions, and aliases. For groups have their own catalog. Membership references IDs, not spelling. Retain evidence for assignments and explicit no-group decisions; AI proposals do not certify a human group review.

Judge labels by meaning, selectivity, distinctness, and importance. Compute matching counts and overlap to inform judgment, not to automate merging. A label shared by every resource provides no narrowing in that category; a one-resource label may still represent an important need. Two groups with identical matches are not necessarily synonymous. Preserve supported population/eligibility distinctions and avoid inferring identity from names or language access.

There is no universal target number of Types/groups or percentage cutoff. Do not create narrow groups merely to make result lists shorter. Search can use details that do not deserve navigation labels.

The reviewer records why labels were merged, retained, renamed, or split, maps original labels to the proposal, and rechecks assignments. Use stable IDs across label renames; merges and splits require explicit mappings. Every included resource/category membership needs at least one supported Type or a recorded issue preventing final readiness. Every group assignment needs evidence, including care with multiple programs whose eligibility cannot safely be intersected.

Export full-collection counts and denominators as descriptive metadata if useful. WSRS-TSO computes live counts for its curated-only or all-resource scope. One published resource means a Type is represented; it does not establish adequate coverage or capacity.

A human Type-editing interface is separate from a coverage view and remains a WSRS-TSO design decision. Scout supplies definitions, proposed mappings, explanations, and inspectable resources that could support either.

## 6. Starter selection and review

After taxonomy reconciliation, assess the whole usable collection and recommend 7–10 distinct resources within each category. A resource may belong to several category sets; count unique human curation tasks separately from memberships. Do not pad a sparse category or hide a consequential gap to meet a number: document a justified size exception and its implications.

Selection considers complementary kinds of help, meaningful eligibility pathways, usable intake, location/remote access, urgency, and alternative providers. A set of near-identical providers is not automatically better than one covering different needs; nor should apparent Type coverage eliminate valuable alternatives. Retain national/federal and statewide services when relevant to the office. Do not promise availability or enforce equal referrals without evidence.

Each selected membership has a unique position within its category, a concise contribution explanation, supporting fact references, and any material limitation or human check. For example: “Adds eviction-representation help not offered by the other selections.” Comparative statements must be checked against the rest of the set. Order recommends human review sequence, not provider quality or live client suitability.

Each category also has a short rationale describing the set, remaining gaps, and reasons for any size exception. Maintain an internal assessment ledger covering all resource/category pairs: selected, considered-but-not-selected, or unresolved, with a resource-specific basis. This ensures the reviewer considered the reserve without burdening the consumer with tiers or a fabricated total ranking.

Starter membership is independent of publication: an unapproved starter resource remains reserve in the application, and a human-approved nonstarter is curated. Human edits and additions may change the best set; the exported recommendation is explicitly tied to its reviewed snapshot, not silently recomputed by a non-AI workbench.

## 7. Stable identity, changes, and human decisions

Use three distinct identifiers: research observation/candidate ID, consolidated Scout resource ID, and consumer office-record ID. Export links among them where known. Consumer decisions attach to the stable consolidated ID plus office context, not run-local lead IDs or mutable names.

Proposed implementation: maintain a durable identity registry with an explicit producer namespace, aliases, prior mappings, and supported program boundaries. Reconcile each new run against it before allocating an ID. IDs do not change for a renamed program, corrected address, new category, new source, or a reordered batch. Ambiguous matches stay unresolved rather than automatically overwriting identities. A fresh database must import registry continuity or clearly declare a new lineage; a UUID by itself does not solve rediscovery.

Use explicit merge/split events. A merge identifies predecessor IDs and the survivor; a split names successors and requires review of affected consumer decisions. Do not blindly transfer Curated, Deleted, pins, or notes where identities or human choices conflict. Bootstrap existing artifact IDs through an explicit migration map and preserve unmapped decisions for resolution. Audit more than one historical run before promising cross-run stability.

Export a complete snapshot first, optionally accompanied by a changes summary against an identified predecessor. Record added/changed resources, changed field paths and evidence, identity events, and resources not observed again. A `not-observed` event is not deletion or closure. Evidence-backed withdrawal is distinct and cannot silently unpublish an office's human-curated record. Unsupported partial-run comparisons must not produce “gone” claims.

The same snapshot can be imported repeatedly without recreating records or resetting human state. Compare source-owned revisions to source-owned revisions; consumer edits, suppression, drafts, pins, publication, and saved-for-review notes remain separate. Scout can propose corrections; the consumer owns reconciliation with human overrides. The detailed return channel for sharing approved corrections is deferred, not an assumption of automatic synchronization.

## 8. Proposed exchange artifact

Add a reviewed-resource artifact, distinct from the existing research candidate ZIP and from an office's curated resource package. Proposed filename: `scout-<office>-prepared-resources.json`; proposed discriminator: `artifactType: "scout-prepared-resources"`, with `schemaVersion: 1`. Exact names need agreement with Claude before implementation.

Plain UTF-8 JSON is the first format. A later ZIP may contain the same JSON plus a manifest of attachments and checksums; the filename, media type, and relative-path rules must then be specified. Do not add empty office `deletions`, `changes`, or `packageVersion` fields merely to imitate an office package. Scout's proposed `changeSet` has the explicit semantics above and is not an office deletion instruction.

| Proposed section | Required meaning |
| --- | --- |
| `artifactType`, `schemaVersion` | Explicit reader dispatch and compatibility. Reject unsupported versions with a clear error. |
| `producer`, `policyVersions` | Scout version, identity namespace, and research/curation/review policy versions/hashes. |
| `snapshot` | Stable snapshot ID, predecessor where available, generated time, content fingerprint, and review status. |
| `scope` | Office context, service-area description, included categories, and completeness of research/review. |
| `resources` | Consolidated IDs, revisions, prepared facts/text, category/Type/group memberships, preparation states, candidate links, and uncertainty. |
| `taxonomy` | Versioned category/Type/group definitions, aliases, and migration mappings. |
| `sources` and fact references | URLs, source identity, observation dates, relevant evidence, and the claims they support. |
| `starterSets` | Per-category selections, positions, contribution explanations, evidence references, set rationale, gaps, and size exceptions. |
| `identityEvents`, `duplicateSuggestions` | Confirmed identity changes separately from unresolved possible matches, with reasons/evidence. |
| `changeSet` | Explicit baseline and semantic changes; no implied publication/deletion action. |
| `review` | Input fingerprint, completion evidence, known limitations, and audit references. |

Absence of a predecessor means an initial snapshot, not that all resources were newly discovered. Resource content revisions exclude packaging timestamps so regenerating identical content does not manufacture changes. Define canonical serialization and hash exclusions in the executable schema/specification; the fingerprint must cover substantive facts, taxonomy, identity mappings, and recommendations, not self-reference itself.

### Evidence and dates

Reference evidence from facts, not merely a whole resource or priority. Phone, hours, eligibility, and service-area assertions need identifiable support or an explicit unconfirmed status. Use typed field paths or stable fact IDs, source references, and short relevant excerpts. A general homepage link is not automatically evidence for every claim. Track conflicts without averaging them into a fabricated answer.

Separate research/observation times, AI review time, and agency-confirmation records. Proposed `researchedAt`/`observedAt` fields never imply agency contact. Human or agency confirmation needs method, date, provenance, and field scope; never infer it from legacy `verifiedOn`. Preserve legacy values with their known/unknown provenance, and map only demonstrated agency confirmation into any consumer field with that meaning. Unknown historical source dates remain unknown rather than being assigned the export date.

Preserve location, service-area and eligibility statements, remote access, and their evidence. Do not reduce them to a guessed `reach` enum. National/statewide applicability does not imply uniform local intake. Distance calculations and client travel preferences are outside this version.

### Search and consumer expectations

Export enough prepared text and facts for WSRS-TSO to search across categories and for Ask to explain matches and uncertainties. Do not encode every circumstance as a Type/group. Curated-only versus all-resource scope and the default scope are application choices; our suggested default is curated-only with an explicit reserve expansion.

Reserve labels describe absence of human approval, not lower provider quality. Saving a reserve candidate is an application event containing a stable resource reference and optional resource-focused note. Scout does not receive or require identifiable client situations. The queue's persistence, permissions, and Ask implementation belong in Claude's application design.

## 9. Compatibility and delivery gates

Preserve old research packages, result versions, and delivered HTML files. Add a versioned adapter from reviewed stored results to the new artifact; never scrape HTML as the primary export pipeline. Both outputs must derive from the same resource snapshot when they are emitted together, with documented format-specific metadata.

Do not map new recommendations into invented legacy tiers or discard extra prepared information to satisfy the old office-package schema. Retain the legacy export path for existing reviewed runs. New data-only delivery may be introduced as a separate explicitly supported mode; generating a new-style workbench would require a deliberate compatibility change and corresponding UI checks, not a hidden enhancement in this design.

Current review-completion rules remain operative until implementation revises them coherently. Then data delivery requires content/identity/taxonomy/starter review and artifact validation; any emitted HTML additionally requires its actual browser/editor/filter checks. Both completion records bind to the exact delivered fingerprint. Revisions invalidate affected reviews rather than inheriting a stale “complete” flag.

Do not mechanically reprocess all prior offices. Pilot on a frozen Cedar City copy after the discussion hold is lifted. Assess existing evidence and fill specific preparation gaps; preserve original resources, category copies, dispositions, and review history. No replay of human approval or edits. Older sources lacking fact-level links may need targeted review; migration must not invent those links.

## 10. Implementation plan and affected instructions

1. **Agree the exchange contract and audit identity.** Inventory ID paths and real multi-run examples, specify migration, and settle required consumer fields with Claude. Create a schema and small synthetic fixtures before producing a real release.
2. **Version preparation policy and data.** Update `scout_curation.py`, `scout_curation_runner.py`, normalization/storage/revision handling, and documentation together. Preserve prior sealed assignments; hash the new policy into new assignments. Keep worker schemas and Python validators consistent.
3. **Implement whole-collection taxonomy and starter review.** Extend navigation metadata and replace the tier proposal contract with a versioned starter/assessment contract. Update `office_pipeline.py` review prompts, `scout_review_priorities.py`, navigation/readiness validators, and completion fingerprint dependencies.
4. **Implement deterministic export and migrations.** Add a dedicated prepared-resource exporter, identity continuity, fact/source/date handling, change comparison, and compatibility tests. Publish machine-readable data independently of HTML.
5. **Run the bounded pilot and consumer handoff.** Review a preserved Cedar City copy under the revised instructions, inspect the artifact and import behavior with Claude, document gaps, and then decide which earlier offices need migration or targeted re-review.

Documentation changes include `docs/scout-curation.md`, `docs/scout-curation-runner.md`, `docs/scout-workbench-readiness.md`, `docs/scout-orchestration.md`, `docs/product-design.md`, `SCOUT_STATUS.md`, and `AGENTS.md` where its review contract references priorities. The category playbooks remain broad discovery guidance; change individual playbooks only for demonstrated discovery gaps, not to enforce starter sizes.

English policy is part of the implementation. A Markdown-only edit cannot change a sealed curation assignment. Document the authoritative policy and ensure worker prompts receive it; record policy versions/hashes so results can be traced to their instructions. Reviewer judgment cannot be replaced by deterministic completeness checks or keyword-generated reasons.

## 11. Acceptance evidence

- Every source candidate retains an explicit disposition and provenance; every usable resource survives independently of starter selection. One resource in multiple categories stays one human task.
- A renamed resource, changed URL, changed category, reordered run, and alias rediscovery preserve identity where supported. Ambiguous merges/splits and registry loss produce explicit reconciliation, not silent resurrection or overwrite.
- Importing the same artifact twice preserves Curated, Deleted/suppressed, drafts, pins, and notes. Changed Scout facts do not overwrite human edits without reconciliation. Consumer-side evidence for this must come from Claude/WSRS-TSO, not a Scout-only test.
- Missing-from-run, confirmed closure, and narrower research scope are distinguished. An incomplete run cannot falsely report disappearance.
- New evidence and date fields survive worker output, normalization, persistence, revision, and export. Schema/version and dangling references fail clearly. Unknown research dates do not become agency confirmations.
- Each category has a justified starter set, individual contributions and limitations, valid positions, and a full internal assessment ledger. No tiers, opening set, reserve total ranking, or automatic approval is introduced.
- Semantic review checks Type selectivity/overlap, justified rare labels, consistent definitions, all memberships, and group evidence/no-group decisions. Counts alone cannot pass this check.
- A synthetic cross-category search case, such as a parent facing eviction, retains the relevant legal/housing/family-service facts in the artifact; application relevance and Ask behavior are tested separately in WSRS-TSO.
- Regenerating identical substantive content preserves its semantic fingerprint. Changing facts, taxonomy, or starter selections marks dependent review metadata stale. Any continued HTML output passes its actual browser checks.

## 12. Decisions still needed and traceability

The direction is sufficiently defined to implement after these design choices are resolved; the draft is not itself approval to start implementation.

| Decision | Proposed default / remaining question |
| --- | --- |
| Consumer schema and migration | Separate reviewed-resource JSON with explicit discriminator/version. Agree exact names, required fields, and migration of existing candidate-keyed decisions with Claude. |
| Stable identity continuity | Durable namespaced registry and explicit lineage events. Determine where the registry persists across installations/offices before claiming cross-office identity reuse. |
| Legacy workbench compatibility | Preserve current artifacts and old export mode; prioritize new JSON delivery. Decide whether new-style HTML curation support is still needed before changing its UI. |
| Human feedback returning to Scout | Preserve source/human ownership now. Define a later update/import contract if curated corrections are to improve future Scout runs. |
| Pilot scope | Proposed Cedar City preserved-copy pilot. Existing discussion hold remains until Michael directs continuation. |

Claude's seven requests are addressed as follows: stable IDs (§7); changes since last run (§7–8); agreed Types (§5); starter selection and geographic data with the opening-set proposal superseded (§6, §8); fact sources (§8); separate research/agency dates (§8); and duplicates (§4, §7–8). The JSON/ZIP proposal and separation from office packages are covered in §8–9.

No production code, worker settings, resource facts, human approvals, or existing delivery gates change merely by saving this document.
