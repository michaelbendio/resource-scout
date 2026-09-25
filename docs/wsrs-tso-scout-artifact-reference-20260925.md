# WSRS-TSO feedback on a Scout data artifact

Date: 2026-09-25

Status: design input, not an approved schema or implementation specification.

The resulting [Scout design draft](scout-prepared-resources-design-20260925.md) addresses this feedback and records remaining decisions.

Michael asked Claude, “Could Scout give you a more useful artifact than an HTML file”. Michael supplied the response below and requested that it be saved and consulted when preparing Scout's design document.

## How to use this reference

Read this document when designing Scout's curation/review changes and its data handoff to WSRS-TSO. Address each numbered request below in the design document, recording the proposed treatment, evidence about existing behavior, and unresolved decisions. Claude's descriptions of current implementation are supplied observations, not independently verified findings in this document.

Keep the original feedback distinct from the subsequent design agreement:

- The working direction is 7–10 complementary starter resources per category, with explanations and a recommended order within the starter set. No tiers or three-resource opening set; a complete ranking of all reserve resources is not required.
- Retain full AI preparation of usable reserve resources for extended search. Starter selection remains separate from human Curated status and publication.
- Develop useful, consistent Types and For groups from the whole prepared collection. Consolidate redundant labels without erasing meaningful, searchable service or eligibility distinctions. Labels must help narrow results; fewer labels is not an end in itself.
- New application functionality belongs in WSRS-TSO. Michael withdrew the request for enhancements to [location].html. The existing auto[Location] workbench remains a handoff/curation tool; this note does not authorize enhancements to it or prescribe its retirement.
- Scout supplies prepared information and AI review proposals. WSRS-TSO's planned Ask is a separate AI capability.
- Geographic reach, service location, eligibility/service area, and client travel preferences are different concepts. A simple reach label cannot substitute for that future design.
- Cross-office reuse of curated information remains a design topic, with office-specific applicability preserved.

## Claude's response, as supplied

Yes, and it's closer than you might think. Scout already makes a data file: the workbench's meta tags name a "candidate package" by its checksum, and the embedded data is in TSO resource-package format (resourcePackageSchemaVersion). The HTML wraps that data in a viewer so a person can curate in a browser. WSRS-TSO has to dig the data back out of 5.8 MB of HTML, and it can only read what the package format has room for.

On the container: I'd ask Scout for the candidate package on its own, as a JSON file, or a ZIP if it ever carries flyers. Keep the HTML as a separate output for anyone curating without WSRS-TSO, generated from the same data. That gives three things:
- A schema and a version of its own, which WSRS-TSO can check and reject clearly when a file doesn't fit. Today the Curate tab infers the file's type from a meta tag.
- Reading and diffing become trivial. It could also be imported once into a Dataverse table, so curators no longer choose the file every visit: the superseded candidates-table idea, which is much easier with a clean data file.
- Nothing in it pretends to be an office's own package. Today the file carries fields like deletions, changes and packageVersion that mean nothing for candidates.

The contents matter more than the container. What would make me a better partner, in the order I'd ask for it:

1. IDs that stay the same across Scout runs. This matters most. Curated, Deleted, drafts and pins are all recorded against Scout's candidate ID. If a new run gives the same organisation a new ID, a curated resource reappears as a candidate and deleted ones come back. I don't know whether today's IDs (hashes) are stable; it's worth asking Scout.
2. What changed since the last run: new, changed and gone candidates, so the second workbench a curator sees is a short list rather than 1,096 again.
3. One agreed list of Types per category. Coverage (B) only works if "Housing Costs" is always spelled the same way. Today the Types arrive loose on each candidate.
4. Ranking, the opening and starter sets, and reach, as in the brief.
5. Sources for each candidate: the web pages Scout used for the phone, hours and eligibility. Curating means checking AI-written text, and a link to the source is how a curator checks it quickly. The file already carries an evidence field on each priority, which WSRS-TSO doesn't read yet. It should be on the candidate's facts too.
6. Scout's research date as its own field, not in verifiedOn. Today WSRS-TSO has to discard it, because the handout prints that field as confirmation with the agency.
7. Likely duplicates grouped together, such as the same agency under two names, so the curator decides once.
Let's discuss it.

## Questions the design must resolve

- Verify the existing candidate/package artifacts, metadata, identity generation, and exports before deciding whether to extend an existing format or introduce a distinct versioned exchange format.
- Distinguish raw research candidate IDs from consolidated resource/program IDs and downstream office IDs. Define stability across runs, identity reconciliation, and merge/split history without assuming that one organization means one resource.
- Define snapshot and change semantics. Absence from a new search must not silently mean closure, deletion, or withdrawal of a human-curated resource.
- Define category/Type/group identifiers, display labels, assignments, and revision behavior so labels can change without losing curator decisions.
- Specify starter membership, within-set order, reasons, and evidence separately from approval and user preferences. Reconcile Claude's item 4 with the current direction above.
- Define fact-level source references and research/check dates separately from human or agency verification. Preserve unknowns and avoid implying contact with an agency.
- Define how suspected duplicates are presented and reconciled while preserving genuinely different programs, eligibility, source evidence, and existing human decisions.
- Agree on the import/update behavior with WSRS-TSO before finalizing the contract; a clean file alone does not establish Dataverse storage or synchronization behavior.

This reference records discussion input only. It does not start workers, change existing resource data, or implement a new export.
