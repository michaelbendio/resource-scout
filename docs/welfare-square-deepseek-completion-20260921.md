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
