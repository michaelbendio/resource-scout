# Shared resources prototype

`shared-resources.html` is Provo's Resource Assistant page (`~/resource-assistant/provo.html`)
holding every office's real resources, for Elder Bendio and Stephanie to try shared resources
in the screens missionaries and vetters already know. It differs from `provo.html` only
where shared resources need it (Elder Bendio, 25 October 2026):

- **Office**, beside the title: the page holds every office, so it asks which one you are
  in. Changing it reopens the page as that office.
- **Restriction**, in words under a resource's name ("Utah residents only", "Women only").
  The brainstorm's one rule for who is eligible, by place or by group.
- **Coverage and restriction** in the resource editor, after Categories: which offices see a
  shared resource (nationwide, states or counties), the offices that see it, a warning for a
  county outside where it serves, and the same resource in each office, with "Use this copy's
  text" and "Not the same". An office's own resource has "Share with other offices".
- **Coverage** tab in admin, for a category and subcategory:
  - **Nationwide**: the nationwide resources, and **federal programs run by each state** (SNAP, Medicaid, CHIP, WIC, TANF,
    LIHEAP): each state's front doors, with a state that has none in its offices' lists
    highlighted.
  - **A state**: its nationwide and statewide resources, then its counties against the
    county-level shared resources, counties with nothing highlighted. Each county's count of
    local resources that are not shared opens a list of them by name; those the office sees
    open in the editor, where its own can be shared.
- **Federal program run by each state**, in the editor: which program a resource is a
  state's front door to. First marked by AI readers following `build/programs-brief.md`
  (a missionary could send a person there to apply); the vetter corrects it.
- **Missionaries only** (Elder Bendio, 24 October 2026): said on the card, and never printed.
- Changes in the change log name the office that made them.
- **Interface changes asked for by Elder Bendio, 25 October 2026:** no Favorites (no stars,
  no Favorites view, nothing about them in the tip or Help); Categories in the middle of the
  top bar, with Print, Help and Admin on the right; and "Subcategory" for "Type" in
  everything the page says. The wording is changed by `build.py` as it copies `provo.html`.

The categories, subcategories and For groups are the **draft standard
vocabulary** of 20 October 2026 (`wsrs-tso/docs/vocabulary-design.md`), not yet approved by
Stephanie: shared resources need one vocabulary (brainstorm, "Answers", 1). The decisions and
questions are in [discussion-note.md](discussion-note.md). It is a prototype for defining the
final outcome, not a referral directory.

## Build and open

The page holds every office's resources, including internal entries, and this repository
is **public**, so the built page and its data stay in `local/` (ignored by Git). Only the
scripts and the brief are committed.

```sh
python3 build/gather.py      # every office's records -> local/records.json
# file each batch under the standard (AI readers, classify-brief.md) -> local/batches/out-*.json
python3 build/build.py       # -> local/shared-resources.html; open it in Safari or Chrome
```

`gather.py` reads Provo, Albuquerque and Mesa, the offices in use, from their newest
production export (`npm run recovery -- export` in wsrs-tso, into `~/WSRS-Backups`; read
25 October 2026): each office's resources, and for Mesa the unreviewed Scout resources its
missionaries also see, chosen as the app chooses them. The other nine offices come from
the Scout files loaded into them; vetted status from production's 14 October listing.
Re-export and rebuild to refresh them; resources without a filing are listed and left out
until a reader files them. `build.py` takes `provo.html` as it is, adds the data and `build/shared-prelude.js`
before the app starts and `build/shared-layer.js` after it, and stops if `provo.html` no
longer has the places it adds them. Shared resources come from the 21 October recount's
cross-office groups (`~/Documents/shared-recount-2026-10-21/`).

`build/additions.json` holds resources added for the prototype from public sources, each
with its filing and programs. One can replace an office's narrower entry for the same agency.
It has Nevada's Division of Social Services (Access Nevada, from dss.nv.gov, 26 October 2026)
for Las Vegas. It replaces Las Vegas's SNAP-only entry, and is Nevada's front door to SNAP,
Medicaid, CHIP (Nevada Check Up), TANF and LIHEAP (Energy Assistance Program).

## How it works

- Every resource is kept once, and each shared resource once, with its coverage.
- **An office sees** its own resources, and each shared resource whose coverage reaches one
  of its counties; its own copy of that resource is then hidden. Before the app starts,
  `shared-prelude.js` writes that view into the app's saved data, so search, categories,
  Types, groups, favourites, printing and the editor all work on it unchanged.
- **Any office may edit any resource its missionaries see** (Elder Bendio, 24 October 2026),
  shared ones included; the app only holds what the chosen office sees, so that is the rule.
  `shared-layer.js` writes each change back into the shared store, so it shows in every
  office that sees the resource.
- **Only changes are kept in the browser.** The office's view is handed to the app in
  memory, never saved: a whole office does not fit beside the other local office pages in
  the storage a browser gives local files, and the page opened empty when it tried.

## What is draft

- **Every resource the reader judged nationwide is shared nationwide** (Elder Bendio,
  25 October 2026), joined to the same resource elsewhere by phone number; "Not the same"
  splits off a wrong match. Unreviewed ones are shared too, marked "Not yet reviewed".

- **Every resource's filing** under the standard, made by an AI reader from its text
  following `build/classify-brief.md`.
- **Offices' counties** (`OFFICES` in `gather.py`): the brainstorm leaves them to be written down.
- **Coverage, and which copy's text is shown**: see "Still draft" in the discussion note.

## Limits

Changes stay in this browser, apart from anything `provo.html` itself saves. No synchronising, permissions or production publishing. PDFs are left
out. Production copies missing from the local files appear only as "Also held in
production by …" in the editor. Save Resource Package and Merge Resources work on the
office you are in, as in `provo.html`, and are not part of the prototype.
