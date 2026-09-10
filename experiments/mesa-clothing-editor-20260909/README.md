# Mesa Clothing: live research, Grok blind check and Astra editing

Completed September 9, 2026, from Michael's approved saved 268-resource Mesa
draft. The bounded assignment was 19 Clothing rechecks, at most five new
candidates, Astra primary research, Grok 4.6 independent blind research, and
Astra final editing, within two hours. No Claude was used.

**Result: 21 resources — 19 retained plus two additions.** Four existing entries
have patron-text changes and one new curator question was added. Nothing was
combined, reserved or excluded. All 26 original question objects and all 19
existing resource IDs are preserved exactly. There were no provider calls,
human approvals, verification-date changes or lesson activations.

Download and extract the [complete handoff bundle](mesa-clothing-pilot-handoff.zip).
It includes the working HTML, full 21-resource pilot package, concise report
with expandable **bold** comparisons, two-page printable PDF, original
268-resource source package, outside research results, model configuration,
ledgers and verification evidence. The pilot is partial; merging all its
entries with the saved full draft yields 270 resources. The original is unchanged.

## Consequential decisions

- **The Worker:** accepted Grok's housing correction after checking the provider
  page: shared one-bedroom housing, 2–3 month wait, employment/pay-stub and
  savings conditions, and **one year** of follow-up instead of nine months.
  This is a correction to a shared entry, not a completed Housing-category run.
- **Dress for Success:** rejected a proposed appointment restriction. The
  provider's FAQ explicitly permits walk-ins and requires no referral; an
  appointment button on another page does not revoke those statements.
- **New Hope:** saved one question about a directory's **90-day clothing visit
  interval**, which the provider page does not state. No directory-only rule
  was silently promoted into confirmed eligibility.
- **City Hope Gilbert and Jose's Closet:** two distinct, actionable additions.
  Grok independently found Jose's Closet; City Hope Gilbert was an Astra
  discovery. Existing City Hope Mesa provides food only. Helen's Hope Chest
  and Jose's Closet have different providers, entry rules and visit intervals.
- **Navigation and wording:** clarified clothing/gathering access at La Mesa,
  student-only clothing at MCC Southern/Dobson, and clothing pickup language
  at Streets of Joy. Used existing supported types/groups and pruned unused
  navigation terms from the partial pilot.

## Architecture actually exercised

The saved four-pass Clothing playbook, schema-2 configured Grok checker, sealed
assignments, category-wide primary freeze, fresh isolated outside context,
actual-model receipts, explicit reconciliation, direct final-editor entry,
21 individually reasoned editorial decisions, learning-observation recording,
and draft HTML/package export all ran. Maintenance project 1 reached revision
170; the editor project is recorded in [manifest.json](manifest.json).

Grok received original records and a shared original identity catalog, not
Astra's current findings. It reported reading only part of that catalog;
Astra checked additions against the full 268-record source. The one overlapping
discovery was reconciled into one stable new identity. This was a bounded
maintenance pilot, not exhaustive discovery or a controlled Claude comparison.

The [Grok Build transport notes](../../docs/grok-build-research-transport.md)
record the verified executable, OAuth/model identities, prompt splitting,
permission-rule aliases and restart handling. Three returned prose fields
failed the structured-section contract. Their raw text was preserved and
mechanically split into the required five sections with exact round-trip
equality; the handoff records this format repair.

## Measured outcome and checks

- About **59 minutes** from invocation through prepared, verified delivery,
  including login/setup and transport corrections. See
  [measurements.json](measurements.json) for timestamps and interrupted attempts.
- The successful Grok research response took **409 seconds**, across nine
  model turns. Its CLI receipt reports **$0.2579** in accounting, not a confirmed
  incremental subscription charge. Startup attempts are additional; the first
  interruption lacks a completion-cost receipt. Per-resource active minutes
  were not measured.
- [Structural verification](structural-verification.json): exact identity and
  question preservation, no new provider-verification dates or deletions,
  unchanged original bytes, complete editor workflow and 21 saved editorial
  learning observations. The source package had no attachments to exercise.
- [Browser verification](browser-verification.json): actual editor save/reload,
  curated-selection export, 270-resource merged result preserving the 249
  unselected records in the receiving app's canonical representation, and a
  synthetic resolved question surviving an older-package replay. Synthetic
  curation never entered the delivery. Responsive report checks passed at
  820 and 390 pixels, with no page errors. The final two-page PDF was visually
  inspected.

To repeat the browser check in a disposable Chrome context, extract the bundle
and run `python check_browser.py /absolute/path/to/extracted-bundle` with
Playwright installed. It specifically resolves the new New Hope question in
synthetic browser state and verifies that answer survives export, merge and
older-package replay. It leaves the delivered package and PDF unchanged.

## Learning and next step

This produced learning evidence, not an activated lesson. A useful bounded
experiment would test whether researchers consult explicit program/FAQ
statements before inferring a restriction from an appointment button or an
omission elsewhere. Judge useful corrections and false restrictions, not just
agreement or resource counts.

The larger workflow remains research → frontier editing → human curation →
maintenance with evaluated learning. Michael can review this small pilot;
later curator packages and resolved questions provide the next feedback.
This run does not establish that Grok is faster or more accurate than Claude.
