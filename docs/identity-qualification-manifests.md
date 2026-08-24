# Identity qualification manifests

`candidate-qualification-gates-v2` assigns one audited qualification to each
normalized organization-plus-program identity. The manifest is category-neutral;
category playbooks and the reviewed target stage supply the category context.

Generate an incomplete template from a search review with:

```sh
python3 qualify-identity-review.py --review REVIEW.json --output TEMPLATE.json
```

The template deliberately leaves every gate and reason blank. A reviewer must
resolve all of them before application:

- `candidateRole`: whether this is a program, actionable assessment service,
  location, referral system, directory, organization-only page, or unresolved
  lead;
- `geographyState`: whether the program is in or explicitly serves the target;
- `categoryState`: whether the program itself belongs to the target category,
  is only adjacent support, remains unknown, or is wrong-category;
- `actionabilityState`: whether the record supplies an independent way to seek
  help;
- `currentStatusState`: current, uncertain, inactive, or a possible successor;
- `evidenceReadiness`: current authoritative/corroborated evidence, lead-only
  evidence, or stale evidence; and
- `boundaryState`, a concise `reviewReason`, and the current pages used for the
  decision.

Apply a completed manifest with:

```sh
python3 qualify-identity-review.py --review REVIEW.json \
  --manifest MANIFEST.json --output QUALIFIED-REVIEW.json
```

Application fails unless the manifest exactly covers the review's identities,
matches its cache hash and policy, preserves identity text, supplies evidence and
a reason, and uses valid gate values. The same decision is copied to every URL
occurrence of an identity, preventing query-order-dependent role or category
judgments.

When the evidence page belongs to a referring organization rather than the
candidate, the URL-level identity decision must also record `pageOrganization`
and `pageProgram`. Scout persists that referring page identity in the frozen
source envelope; it never relabels a referral as a direct candidate page.

Every new frozen candidate source also uses
`reviewed-evidence-scope-and-identity-v1`. Its URL-level identity decision must
record:

- `reviewedAuthority`: one explicit direct-provider, government-referral,
  reputable-secondary, or directory-lead classification. The reviewed value
  takes precedence over host-name inference.
- `evidenceSelection`: either `{"mode": "full-page"}` for a page whose complete
  bounded extract safely describes the candidate; a `reviewed-section` with
  exact, uniquely occurring `startExcerpt` and `endExcerpt` boundaries; or
  `reviewed-sections` with 2–10 ordered, non-overlapping exact sections. Multiple
  sections retain separated candidate-wide passages while omitting intervening
  program, access-point, property, partner, or other entity blocks.
- `identitySupport`: separate organization and program receipts. Each receipt
  records `relationship` (`exact-label` or `reviewed-alias`), the exact
  `sourceLabel`, and an exact `evidenceExcerpt` containing that label. A
  reviewed alias also requires a concise reason establishing why the source
  label and candidate label are the same entity.

Review validation rejects missing or malformed receipts before a discovery run
is created. Fetching then fails closed if either section boundary or identity
excerpt is absent from the bounded current page. Direct-provider pages are no
longer clipped to a generic character window; a reviewed full-page selection
retains the complete bounded extract. Focused selections contain only the exact
reviewed section and therefore cannot end mid-phrase or silently include a
sibling section. Multiple selected sections are joined in source order, and the
receipt preserves the original start and end offsets for every section.

`prepare-qwen-evidence-review.py` applies these receipts as a separate
schema-1 manifest bound to the exact search-cache hash, base-review hash, and
stage key. Its `sources` array identifies the pre-correction identity key and
records the final organization/program labels, reason, authority, selection,
and two identity-support receipts. The source set must exactly cover every
eligible identity in the current stage; missing, duplicate, extra, routed, or
noncandidate entries fail before an output review is written. The output review
records the manifest hash in its application history and is then passed through
the same current-policy validator used by corpus freezing.

Category fit and field completeness are separate. An adjacent pet-care service
does not count as Housing; an actual Housing program does not lose eligibility
because `petPolicy` is absent or unknown. Supplementary fields are not accepted
by this manifest and cannot affect promotion.
