# WSRS-TSO review of the prepared-resources design, with Michael's decisions

Date: 2026-09-25. Reviews [scout-prepared-resources-design-20260925.md](scout-prepared-resources-design-20260925.md)
at `ba8c246`. Written by Claude working in WSRS-TSO, at Michael's request, for Codex to
revise the design from.

**Status of each point is marked:** *Decided (Michael)* is his decision and should be
adopted; *For Scout* is a review point for Codex to resolve; *For WSRS-TSO* is Claude's to
design and is recorded here so the contract fits it; *Open* still needs Michael.

## Verification

Section 2's claims were checked against the code at `ba8c246` (nothing under
`resource_research_agent/` or in `scout-workbench-readiness.md` changed since `2ba271b`).
All six are **confirmed**: the candidate ZIP and `candidatePackageSchemaVersion: 1`
(`candidate_package.py:16–17, 127, 149–151`); the dispositions and the instruction
"Prefer the smallest high-confidence proposal set" (`scout_curation.py:151, 176, 501`);
the closed worker schema and fixed normalizer fields (`scout_curation_runner.py:80–98`,
`scout_curation.py:370–420`); the identity and merged hashes and the UUID fallback
(`manual_consolidation.py:328, 461`, `resource_package.py:186`); the tier contract
with evidence and fingerprints (`scout_review_priorities.py:13, 37, 44–58`); and the
readiness requirements ("real browser" paraphrases "check the rendered reader and
editor"). The audit was done as described.

## Michael's decisions (25 September 2026)

1. **Missionaries may find and use uncurated reserve resources, with a warning.**
   *Decided.* "An unvetted resource (with a warning) is better than no resource and
   better than a less need-focused one. I leave this to the missionary's judgement."
   This makes section 1's "curated-only and all-resource search are distinct scopes"
   a decision rather than an unrecorded assumption; please cite it as Michael's.
2. **A reserve resource prints only with a warning.** *Decided.* On the reserve
   resource's own printed sheet: *"Not yet reviewed by the office. Call the provider
   to verify this information."* Curated resources keep "Confirmed with the agency".
   WSRS-TSO's rule "Nothing the model writes may be printed" is changed accordingly
   (Ask's own sentences are still never printed). The warning is WSRS-TSO's to render;
   Scout needs only to mark which resources are unreviewed, which the preparation state
   and absence of human approval already do.
3. **A reserve search result can be saved for possible curation.** *Decided*, agreeing
   with section 8. The saved item holds a stable Scout resource reference and an
   optional note about the resource, **never about the client**; WSRS-TSO's screen will
   say so.
4. **7–10 starter resources per category.** *Decided* (Michael), superseding the
   "top three" opening set. Stephanie's reasoning, which Michael shares: too many
   missionary referrals to too few resources burden those providers (funding among
   them); referrals should be spread more widely. Section 6's "do not concentrate
   referrals unnecessarily" already fits; cite this as its reason.
5. **Office order:** *Decided.* 1. **Mesa** (Stephanie). 2. **Welfare Square**.
   3. Matt Kimmel's **Las Vegas, St. George and Cedar City**, asked for first.
   4. Julie Erkelens's **Ogden, Logan and Brigham City**.
6. **A trial before the full pipeline.** *Decided*, agreeing with review point 4 below.
7. **Scout writes Stephanie's five Information sections.** *Decided*, agreeing with
   review point 1 below.

## Review points

### 1. The Information sections do not match the handout. *Decided: adopt Stephanie's five.*

Section 4 says "keep the four current Information sections: Eligibility Requirements,
How to Best Connect, Access, and Important Information to Know", and the worker is told
exactly that (`scout_curation_runner.py:115`). But the printed handout is **Stephanie's
five sections**, in this order: **Services Offered, Eligibility Requirements, Population
Served, How to Best Connect, Important Information to Know** (WSRS-TSO
`src/lib/sections.ts:27`, and every Provo and Albuquerque resource). "Access" is not one
of them; Services Offered and Population Served are never written. Today a curated
Scout resource either prints a stray section and misses two, or the curator rewrites it.
Adopt the five, as bold standalone headings in that order; what section 4 puts under
"Access" belongs mostly in How to Best Connect. Keep extra detail in structured facts
and description, as section 4 already intends.

### 2. The reserve and saved-for-review statements lacked a recorded decision. *Resolved by decisions 1–3.*

Previously traceable only to the unattributed agreement list in
`wsrs-tso-scout-artifact-reference-20260925.md:17–18`, with
`context-handoff-20260921-late.md:16` pointing the other way. Now decided.

### 3. Identity: the code, not the model, assigns resource IDs. *For Scout; Michael asked for this to be explained.*

What happens today:

- The ID a candidate starts with is made from the source package's checksum, the local
  run's number and the discovery's row number (`review_export.py:231–234`, a UUIDv5 of
  `resource-research-resource:{sourceSha256}:{run_id}:{discovery_id}`). A new run has a
  new run number and new row numbers, so **the same organization gets a different ID in
  every independent run**, by construction.
- The worker **model** then writes the final `id` of each prepared resource. The
  contract asks only for a "stable generated resource ID" (`scout_curation.py:159`); the
  validator checks it is present and unique (`:382, :490–491`). Delivered IDs carry the
  UUIDv5 pattern, so the model appears to copy the draft ID, but nothing enforces it.
- `previouslyCuratedResources` reuse works inside one job only. The stable
  `identity-`/`merged-` hashes in `manual_consolidation.py` are never used as resource IDs.

Why it matters to WSRS-TSO: every human decision there is stored against the Scout ID.
A curated resource is recognised because it carries the ID as its source key; Deleted,
drafts and pins are rows keyed on it. A new ID for the same organization means a curated
resource reappears as a candidate, a deleted one comes back, and saved work is orphaned.

So the design should say plainly: **the consolidated Scout resource ID is assigned by
code from the identity registry, never written by the model**; the model may propose
"same as X" matches, which the code resolves or leaves unresolved. And **nothing is
delivered to WSRS-TSO before the registry exists.** Timing favours doing it now: WSRS-TSO
holds one curated resource (ASSIST, Welfare Square) and a handful of empty candidate
rows keyed on today's IDs, so migration is trivial now and costly after Mesa and Welfare
Square are curated.

### 4. Trial first. *Decided.*

Section 10 pilots at phase 5, after everything is built. Add a phase 0: starter sets with
contribution explanations for three or four categories of **one office**, judged by
Michael and Stephanie before the registry, fact-level evidence and fingerprints are built.
Given decision 5, **pilot on Mesa, not Cedar City**: the trial then answers the real
question for the first real user. (`autoMesa.html` was judged to need more processing on
24 September, so Mesa likely needs a run under the revised policy anyway.)

### 5. Julie's "top three". *Resolved by decision 4.*

### 6. File size. *For Scout, with WSRS-TSO's constraints.*

Tens of megabytes is fine to deliver. Compression is for transport only: ship `.json.gz`
(or a ZIP, per section 8) if useful; JSON text compresses to roughly a tenth. Searching
happens after import, in WSRS-TSO, not in the file. WSRS-TSO will import by script, not
in the browser, and will keep what missionaries load small: the reserve loads only when
a missionary chooses to search it, and sources and evidence are fetched only when a
curator opens one resource. Two requests follow: keep evidence **referenced, not
repeated** per fact (a source once, facts pointing at it); and note that a single
Dataverse text cell holds about 1 MB, so no single resource's record should approach that.

### 7. A minimum first version of the file. *For WSRS-TSO (Michael: "up to you"); proposed here.*

Section 8 is complete but heavy. WSRS-TSO can start with the fields below; everything else
in section 8 can arrive in later versions, which readers ignore until they use them.

```json
{
  "artifactType": "scout-prepared-resources",
  "schemaVersion": 1,
  "snapshot": { "id": "…", "predecessorId": null, "generatedAt": "…" },
  "office": { "slug": "mesa", "name": "Mesa" },
  "taxonomy": {
    "categories": [ { "id": "housing", "label": "Housing" } ],
    "types": [ { "id": "…", "categoryId": "housing", "label": "Housing Costs", "definition": "…" } ],
    "forGroups": [ { "id": "…", "label": "Veterans", "definition": "…" } ]
  },
  "resources": [
    {
      "id": "registry-assigned",
      "revision": "…",
      "state": "usable",
      "name": "…", "description": "…",
      "phone": "…", "address": "…", "website": "…", "email": "…", "hours": "…",
      "informationText": "Stephanie's five bold headings, in order",
      "categories": ["housing"],
      "types": ["…"],
      "forGroups": ["…"],
      "sources": [ { "url": "…", "title": "…" } ],
      "researchedAt": "…"
    }
  ],
  "starterSets": [
    {
      "categoryId": "housing",
      "rationale": "…",
      "gaps": "…",
      "members": [ { "resourceId": "…", "position": 1, "contribution": "…", "limitation": "…" } ]
    }
  ]
}
```

Requirements behind it:

- **Category IDs must equal the office's own category IDs** (the IDs in the office's
  `[location].html` package, which WSRS-TSO stores as each category's source key).
  WSRS-TSO matches categories by ID, never by label.
- `researchedAt` is never agency confirmation; WSRS-TSO will not show it as
  "Confirmed with the agency".
- `state` other than `usable` is imported for administrators only, never shown to
  missionaries.
- Later versions: `changeSet`, fact-level evidence, `identityEvents`,
  `duplicateSuggestions`, `review`, fingerprints and policy hashes.

## Ask and the reserve. *For WSRS-TSO; recorded so the contract fits.*

Michael: "If Ask doesn't use the reserve there's little point in having a reserve." Agreed.
Ask will search the reserve too, marking reserve results as unreviewed in its answer. It
cannot send a thousand resources to the model with every question, for cost and length,
so WSRS-TSO will search first and send only the best matches. That needs from Scout what
section 8 already asks for: prepared text and facts rich enough to match a client's need
across categories (the "parent facing eviction" case in section 11).

## What WSRS-TSO keeps, and what stays in Scout

Michael asked whether uncurated candidates are kept for possible research or discarded.
Proposed, following section 4's preparation states:

| Scout's state | In WSRS-TSO |
| --- | --- |
| `usable`, not approved | **Kept, as the reserve**: searchable by missionaries and Ask, with the warning; can be saved for curation |
| `usable`, approved by a curator | Curated: in the directory, printed as reviewed |
| `usable`, deleted by a curator | Kept but suppressed: never shown, and not brought back by a new snapshot |
| `needs-resolution` | Imported for administrators only, to reconcile |
| `not-offered`, raw leads, omissions | **Not imported.** They stay in Scout's audit, where research can find them |

Nothing is discarded; each record lives where it is useful. A resource not observed in a
later snapshot stays as it is in WSRS-TSO (section 7's "not-observed is not deletion").

## Offices WSRS-TSO still needs

Cedar City, Logan and Brigham City are not yet offices in WSRS-TSO. Mesa is, but needs its
categories loaded from its office file before its prepared resources can be imported.

## Questions back to Codex

1. Where will the identity registry live so that Mesa's and Welfare Square's IDs survive
   Scout running on either of Michael's machines?
2. Can the phase 0 trial produce its starter sets from Mesa's existing candidates, or does
   it need a new research run?
3. Will Scout's category IDs for Mesa match the IDs in Mesa's office file?
