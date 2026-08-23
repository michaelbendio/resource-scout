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

Category fit and field completeness are separate. An adjacent pet-care service
does not count as Housing; an actual Housing program does not lose eligibility
because `petPolicy` is absent or unknown. Supplementary fields are not accepted
by this manifest and cannot affect promotion.
