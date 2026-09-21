# Welfare Square research launch — September 21, 2026

Michael authorized a fresh Scout run and explicitly selected **all of Salt Lake
County, Utah**. Office name: **Welfare Square**. Statewide/remote programs are
within scope when they explicitly serve county residents. Assignments expressly
avoid restricting discovery to Salt Lake City or the Welfare Square campus.

Monitor: **http://127.0.0.1:8770**. The independent St. George monitor remains at
8769. No St. George or historical experiment database was changed for this launch.

Database: `data/welfare-square-production-20260921-codex-grok/research.sqlite3`.
Import 1, **21 research categories**, Codex primary plus Grok challenger. Codex
uses the previously agreed `gpt-5.5`/High configuration; Claude is disabled.
Grok preflight is enabled, with a 900-second research timeout. The initial
preflight detected expired credentials and stopped before assignments. Device
login completed, the repeated preflight passed, and Codex's Addiction
`direct-service-landscape` assignment started with the correct sealed geography.

## Starter package and provenance

`data/welfare-square-production-20260921-codex-grok/welfare-square-resource-package.zip`
contains a blank resource list, office/service-area metadata and the category
list. The categories were obtained from the St. George import baseline and then
verified against `/Users/michaelbendio/resource-assistant/new.html`: IDs, labels
and order match exactly, including Miscellaneous. Scout researches the 21 named
service categories; Miscellaneous has no separate discovery assignment. Current
`new.html` also has no starting For groups. Types and For groups remain required
corpus-based work during the requested review; the empty starting taxonomy is
not a completed finding aid.

The [launch and source verification](welfare-square-run-20260921.json) records
hashes, actual commands/PIDs, authorization, startup failure/recovery and sealed
first assignment. Runtime `launch.json` and `runner.log` are in the run directory.
Do not recreate or replace the ZIP/database when resuming.

## Continuation

Before any resume, inspect the actual worker process and database. The monitor
is not a worker. Use the saved launch command with preflight enabled and retain
all completed passes/results. The runner holds an exclusive database lock and
uses bounded retries; authentication, quota/turn-limit and timeout failures stop
for diagnosis. This launch does not add an independent research supervisor or
promise that the assistant keeps monitoring after the session ends.

Automatic curation remains **off** under the existing research-to-curation policy.
After research, discuss/confirm the curation transition and worker effort. After
curation, Michael requests the separate AI review: verify source facts and
geography, Stephanie's four headings, Types, For groups, and per-category review
priorities. Both Review priorities and All resources A–Z must be available. Only
after that review should Save produce the vetted workbench `autoWelfareSquare.html`.
Human Curated approval and office-package publication remain separate.
