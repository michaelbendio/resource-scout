# Increment 1 implementation and pilot results

September 5, 2026. Increment 1 is complete on branch `v2.0`: implemented,
automatically validated, and accepted by Michael after reviewing the writing
pilot. This is development work, not an office release or provider verification.

Michael's acceptance: “It looks good. It is much better than what Scout was
previously producing.” He also emphasized that conciseness must not lose
important details. The guidance has no fixed word count or one-page target;
eligibility, application steps, costs, geographic limits, and other consequential
conditions must survive shortening. Continued real use can still reveal needed
writing or printing improvements.

## Implemented behavior

New normal curation jobs use the approved plain-language guidance and return
five structured Information bodies. Scout composes the exact headings, retains
evidence in its durable records, and exports ordinary resource fields. Email
belongs in How to Best Connect because the package has no email field.

The guidance JSON and Markdown are copied into assignments and identified by
their complete content hash. Changing either affects new job identity; existing
jobs resume their sealed instructions. Legacy schema 1 jobs and the separate
enrichment contract still work. No database migration, active playbook changes,
existing-resource updates, or new classification behavior were introduced.

Print inspection found a heading at the foot of a page with its body on the next
page. The review template now identifies full bold heading lines and keeps them
with following text when printing. Body text remains 11 points; long resources
can continue on another page.

Development is isolated in `/Users/michaelbendio/resource-scout-v2`. The existing
`resource-scout` checkout remains on `main` at `a3cb004`, with its runtime and data
untouched. The independent enrichment checkout was not changed. Source release
metadata remains 0.50.0/build 17 until a release is designated.

## Validation

- Full suite: **193 tests run, 192 passed, 1 skipped**, in 19.642 seconds.
  Command: `python3 -m unittest discover -s tests`. The skipped test requires
  `PROVO_RESOURCE_PACKAGE`; no live package was supplied for that optional check.
- New coverage exercises malformed guidance, content-based job identity,
  sealed resume without guidance files, an actual baseline schema 1 fixture,
  structured response rejection, verification semantics, evidence/field
  preservation, Unicode, escaping, heading composition, and rendering.
- Real Chrome checks pass for the resource view, Admin preview, single-resource
  and selection printing, Curated defaults, edit invalidation, canceled saves,
  selected ZIP export, reload, and reopening exported package data. No JavaScript
  errors were recorded. Focused writing/curation tests were rerun after
  clarifying the exact evidence field names in the final guidance. Exported text and contact fields match the review seed;
  internal writing metadata is absent. Existing attachment/taxonomy regression
  tests also pass; the six editorial samples themselves have no PDF attachments.
- Visually inspected the one-page Express PDF and every page of the seven-page
  six-resource packet, plus resource, Admin, and print views. Headings, accented
  text, phone/address/URL/email text, and bullets remain legible without clipping.
  An automated PDF check also rejects headings stranded at page ends.

These checks establish software behavior. They cannot establish semantic truth,
research completeness, or suitability for every person receiving a handout.

## Source-only pilot and experience to discuss

The six cases are Express, CASS, Christ the King Hope pantry, Arizona RSA/VR,
Southwest Human Development, and Desert Manna. Express uses Michael's supplied
text and approved rewrite. The other five retain their complete source records
and provenance from the saved Mesa enrichment artifact. No new provider research
or phone verification was performed. The pilot uses a synthetic Writing samples
category and does not propose taxonomy changes.

The approved Express reference is unchanged; its email is placed in How to Best
Connect in the package. The other samples were revised after source/print review
to turn research-process commentary into useful questions and remove repeated
delivery information. The earlier local pilot preserves the first response;
the revised source cases and response are in `output/writing-pilot-v3`.

Observations for our discussion:

- Express is readable on one Letter page. Several complex programs need more
  space. The packet lets CASS continue before the pantry starts; RSA occupies
  two pages. We have not shrunk text or removed meaningful requirements to meet
  a page-count target. Continued use should assess these page breaks in practice.
- Distinctions matter: enrolling a newborn before 90 days is different from
  support continuing through age five; pantry street boundaries may be strict
  in one program and flexible in another. Those distinctions remain explicit.
- Historical source conflicts require review: CASS intake routes, the local
  RSA office, and Desert Manna contact/location details remain qualified.
  Concise writing cannot itself settle those facts.
- This controlled pilot preserves original names and dedicated contact fields.
  RSA's long name and its directory instruction in the Phone field remain
  awkward on paper. Its usable general number appears in How to Best Connect.
  A writing-only improvement does not make all old resource fields ready for use.

## Reproducing the pilot

From this checkout, choose a fresh output directory:

```sh
python3 scripts/build_writing_pilot.py output/writing-pilot-new
```

This uses a disposable SQLite database and fixture research-completion records,
then passes through normal assignment, result validation, storage, seed, and HTML
generation. It refuses to reuse an existing pilot database. The generated
assignment contains the exact guidance and original source contributions.

The optional browser checker needs Playwright, pypdf, and installed Chrome.
Install those Python packages in an isolated environment, then run:

```sh
python scripts/check_writing_pilot.py output/writing-pilot-new
```

Use `--chrome` to supply a different Chrome executable. It uses a new headless
browser context and exercises simulated review/export only in that isolated
copy. Its marks are QA actions, not human approval. It saves screenshots,
`browser-checks.json`, an exported ZIP, and PDFs in the output parent's `pdf`
directory. Generated output is ignored by Git; fixtures and scripts are tracked.

The reviewed local artifact is `output/writing-pilot-v3/autoWritingPilot.html`.
Its SHA-256 is
`23e359ef54a2182d7f3b3e539884c44c968e009f5e1bce30c14e1b65ae078753`.
The sealed guidance SHA-256 is
`4fe6835e066f5931d85d06ea15f1c92521762b634012e2aaf4804d76e8e10b8a`.
Assignment/result/source snapshots, the pilot database, and review notes live
beside that HTML. Printed samples are `output/pdf/scout-writing-express.pdf`
and `output/pdf/scout-writing-six-samples.pdf`.

## Next checkpoint

Michael accepted the samples, completing the first writing checkpoint. The
grand plan remains: better writing, safe
existing-resource improvements, classification, maintenance, proposed research
lessons, and adaptive research runs. Increment 2 should add reviewed improvements
to existing packages while preserving trusted text, identities, and evidence.
It has not started. No lessons from this pilot have been activated automatically.
