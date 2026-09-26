# WSRS-TSO contract follow-up

Date: 2026-09-25. Claude's answers relayed by Michael following the [design review](wsrs-tso-review-of-prepared-resources-design-20260925.md). Preserved below as supplied. Incorporated into the [prepared-resources design](scout-prepared-resources-design-20260925.md).

## Claude's response

Thanks, good catches. My answers:

Your five points
1. Registry gate: agreed. The Mesa trial can use existing IDs as a clearly marked evaluation document for Michael and Stephanie. The registry gate applies only to real imports into WSRS-TSO.
2. Mesa: you're right; my note from 24 September was out of date. Start from the reviewed collection and look for specific gaps.
3. Small export, internal safeguards kept: agreed.
4. State handling: my inconsistency. Import usable and needs-resolution; keep not-offered and raw leads in Scout. If a resource later looks unavailable, send an evidence-backed withdrawn event. WSRS-TSO will flag it for an administrator and never remove it automatically.
5. Sources: agreed, a top-level source catalog with references from resources. My example contradicted my own request.

Your questions
- Agency confirmation: Curated means the office reviewed the resource, not that anyone called the agency. WSRS-TSO now uses provo.html's word: the sheet prints "verified June 2026" only when someone has entered that date. The resource missionaries fill it in during their periodic re-verification, and curation starts with it blank. Every printed sheet already says "Please call before you go." So Scout never supplies a verified date. researchedAt is only ever the research date.
- Mesa's category IDs: from mesa.html (23 September, tso-storage-id "mesa"), 22 categories:
  addiction, children-pregnancy, clothing-household, disability, domestic-violence, education, employment, financial-assistance, reentry-support, food, medical-dental-vision, homeless-services, housing, id-recovery, immigration, legal, mental-health, miscellaneous, seniors, transportation, utilities-phone-internet, veterans.
  That's Welfare Square's 21 plus miscellaneous. "Stop and report, don't translate by name" is right.
- Registry hosting: Scout runs only on Michael's Mac mini, so keep it simple: the registry is a file in Scout's own repository, committed like code and backed up with it. No shared service and no lease file are needed now. Please design it so a successor can take it over, since Michael's service ends around November 2027. A plain file in the repository does that.
- Schema evolution: yes. Optional additions stay within version 1, and readers ignore fields they don't know. Removing a field or changing what it means is version 2, and WSRS-TSO refuses a major version it doesn't know, with a clear message.

## Scout's local category comparison

Read-only check on September 25 against `data/mesa-review-20260924/after-seed.json`: 341 reviewed resources, 20 categories. This checks the saved reviewed collection, not browser-local edits or a live WSRS-TSO database.

- Reviewed IDs absent from Claude's office list: `caregiving`, `clothing`, `household-essentials`, `independent-living`, `parenting-child-development`.
- Office IDs absent from the reviewed collection: `children-pregnancy`, `clothing-household`, `disability`, `miscellaneous`, `reentry-support`, `seniors`, `veterans`.
- Fifteen IDs match exactly. Missing categories do not prove that relevant services are absent from the collection.

Reconcile memberships by service evidence against the office's exact IDs; do not silently rename labels or discard resources. A proposed mapping is an explicit review artifact, and export must reject unresolved or foreign category IDs. The Mesa evaluation can begin with matching categories and existing IDs before production identity/category migration.
