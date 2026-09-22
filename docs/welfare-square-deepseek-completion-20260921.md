# Welfare Square: authorized DeepSeek completion

Michael authorized completing Welfare Square and then performing the Codex review
without another approval question on September 21, 2026. The agreed scope is five
remaining DeepSeek challengers, Codex High curation, and the requested review.
Claude and additional Grok inference remain disabled.

The original production database and all completed research are retained. Explicit
provider handoffs connect the five original Grok assignment IDs (17–21) to new
DeepSeek assignments (22–26). Original assignments, hashes and sealed plans are
unchanged; the effective roster and completion checks follow the durable handoff.
An obsolete runner configuration stops before provider probes. Completed results
cannot be replaced, handoffs are immutable and idempotent, and superseded
assignments cannot accept new results.

`scripts/deepseek-welfare-finish.py` uses the previously tested DeepSeek transport
and supervised web relay, with max reasoning, durable native events, per-request
cost reservation and a $2 ceiling (including a conservative $0.25 reserve). The
supervising Codex session relays the model's web requests and saves raw results.
This is supervised operation, not a self-contained unattended search adapter.

Run evidence is under `data/welfare-square-deepseek-finish-20260921/`: SQLite
backup, table snapshots, original assignments, manifest, requests, streams,
billing, supervisor acceptance and handoff records. Search and Codex work are not
included in DeepSeek inference cost. Completed states cannot be rerun.

The previously reviewed trial contributes 77 supplemental proposals: Housing 22,
Employment 20, Disability 35. These are sealed curation inputs with revised drafts,
original submissions and the review-report hash. They neither reopen completed
research nor import prior taxonomy or human approval. Whole-office curation must
reconcile them against all primary and challenger findings. Supplemental inputs
are immutable and must be sealed before curation starts; assignment fingerprints
include their provenance and contents.

Initial validation: 278 tests passed with one optional skip, plus a temporary-copy
exercise of handoff idempotency, supplemental ingestion and preservation. All
112 primary pass rows, 21 original challenger assignment rows, 16 completed
Category job rows and 128 original contribution rows remain byte-for-byte equal
at the SQLite field level. The live monitor shows 17/21 completed after importing
the 26-lead Mental Health result. Mental Health eligibility corrections and
category-fit concerns are retained in `source-audit.md` for curation.

This is an in-progress execution record. Final curation, navigation, priorities,
browser checks and exact-fingerprint review completion are still required.

## Research complete; whole-office curation running

At September 21, 21:01 MDT all 21 Categories are fully researched. The five
DeepSeek completions contain 136 raw submissions, before whole-office curation:

| Category | Raw submissions | API calls | Peak-price estimate |
| --- | ---: | ---: | ---: |
| Mental Health | 26 | 17 | $0.132647340 |
| Seniors | 21 | 30 | $0.167125692 |
| Transportation | 25 | 30 | $0.178437456 |
| Utilities, Phone, Internet | 10 | 29 | $0.154875456 |
| Veterans | 54 | 19 | $0.178733424 |
| Total | 136 | 125 | $0.811819368 |

The total includes the single output-limit failure described below. Observed
account balance is $6.52; rounding and billing lag may affect it. These are API
inference costs, excluding supervised search and Codex work. Original raw outputs
are unchanged. Supervisory acceptance means suitable inputs for curation, not
factual approval of every submitted claim. Source checks found consequential
corrections, including VET TEC 2.0 not requiring remaining education entitlement,
Survivors Pension not requiring service-connected death, unsupported new-client
Utah Headstrong access, and Utah utility assistance's 12-month cap period.

Job 1 seals 2,153 candidate identities across 21 Categories, including all 77
reviewed supplements. `gpt-5.5` / High curation started at 03:00:51 UTC September 22
with bounded batches, a persistent supervisor, native events and a pre-curation
backup in `data/welfare-square-curation-20260921/`. No additional research inference
is planned. Curation completion and the already-requested review remain pending.

At 21:07 MDT Michael directed xhigh. The supervisor and coordinator were restarted
with xhigh for new calls, preserving and adopting the active first High worker.
No batch or research was repeated. Original native worker metadata identifies the
first batch as High; progress from the new coordinator carries its xhigh setting.
The effort-change record preserves both launch configurations and process IDs.

## Diagnosed output-limit continuation

Utilities/Phone/Internet's first response ended at the 32,768-token output limit
without making a research tool call. The response, native stream, usage, failure
and failed state are retained. A single changed continuation directs the model
to use the preserved planning and begin source checks. It retains max reasoning,
the original assignment and accumulated spending; it neither replays an unchanged
request nor starts the Category over. This recovery path cannot run twice for
the same Category. Separate failure/completion telemetry avoids counting the
failed output's tokens and cost twice. Nine transport/recovery tests passed.
