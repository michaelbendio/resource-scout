# Shared resources prototype, v4

A single HTML file for Elder Bendio and Stephanie to try out and refine two designs
together, before either is built:

- **The draft standard vocabulary** of 20 October 2026 (`wsrs-tso/docs/vocabulary-design.md`):
  18 categories with definitions, their subcategories, 19 For groups with "only", and
  navigators in a strip at the end of a category. **Not yet approved by Stephanie.**
- **Shared resources** as the brainstorm of 20 October 2026 left them
  (`wsrs-tso/docs/shared-resources-brainstorm.md`), with Elder Bendio's decisions of
  24 October 2026 in [discussion-note.md](discussion-note.md): each kept once, editable by
  any office that sees it, coverage (national, states or counties) chosen by a vetter, a
  restriction said in words.

It is a prototype for defining the final outcome, not a referral directory.

## Build and open

The page holds every office's resources, including internal entries, and this repository
is **public**, so the built page and its data stay in `local/` (ignored by Git). Only the
scripts, the template and the brief are committed.

```sh
python3 build/gather.py      # every office's records -> local/records.json
# file each batch under the standard (AI readers, classify-brief.md) -> local/batches/out-*.json
python3 build/build.py       # -> local/index.html; open it in Safari or Chrome
```

`gather.py` reads Provo's WSRS package, Albuquerque's 6 October backup and the Scout files
loaded into the other ten offices; vetted status comes from production's 14 October
listing. `build.py` adds each resource's draft filing and the 21 October recount's
cross-office groups (`~/Documents/shared-recount-2026-10-21/`).

## What is draft

- **Every resource's filing** under the standard was made by an AI reader from its text,
  following `build/classify-brief.md`. "Draft filing" on each card shows what the office
  had. The Vocabulary tab shows where each office's old categories went and every
  "doesn't fit" note: the review queue for the standard.
- **Offices' counties** (`OFFICES` in `gather.py`): the brainstorm leaves them to be written
  down.
- **Coverage of each shared resource**: nationwide or statewide when the reader judged it
  so; otherwise the counties it serves plus those of every office that already lists it,
  with that as the reason (Lantern House reaches Provo this way).
- **Which copy's text a shared resource shows**: a reviewed copy first, then the copy with
  the most text.

## What to try

- Missionary: open a category; read its definition; use subcategories and **For**; note
  "Veterans only" and restriction badges, and the navigator strip at the end.
- Vetter, acting as the office selected at the top: edit any resource that office sees;
  change a shared resource's coverage (a county outside where it serves warns but is
  allowed; removing offices asks first); mark a copy "Not the same"; share a statewide
  resource; see the coverage table's gaps; undo from Changes.

## Limits

Changes stay in this browser. No synchronising, permissions or production publishing.
PDFs are left out. Production copies missing from the local files (mostly an earlier
Welfare Square load) appear only as "Copy in production" rows.
