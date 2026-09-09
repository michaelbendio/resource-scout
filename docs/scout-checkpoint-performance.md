# Checkpoint save performance

Historical September 8 measurement. September 9 adds a new lossless shared-context storage format; see [current results](scout-learning-editor-results.md) and [compatibility/rollback instructions](scout-learning-editor-operations.md). The old-reader compatibility statements below describe the earlier zlib-level-only change, not the new v2 shared format.

Large research projects use the existing `scout-project-json-zlib-v1` envelope
with zlib level 1 instead of the default level 6. Each assignment and accepted
result rewrites the project checkpoint, so faster compression reduces repeated
local processing. Small and legacy plain-JSON projects are unchanged.

The decoder, schema, research stages, save frequency, transaction boundaries,
sealed assignments, evidence and sampling manifest are unchanged. Existing
compressed checkpoints resume directly, and the previous decoder can read the
new checkpoints. No migration or research restart is required. The faster setting
applies at the next normal save; it does not rewrite the paused production run.

## Measurement on the paused autoMesaV2 project

One same-input comparison on September 8, 2026, using 1,272,430,578 bytes of
serialized project state:

| Compression | Seconds | Compressed bytes before base64 |
|---|---:|---:|
| Previous default, level 6 | 22.470 | 337,619,287 |
| Fast, level 1 | 6.603 | 427,006,388 |

Both decompressed to the exact original bytes. The tradeoff is about 26% more
compressed storage for about 71% less compression time in this measurement.
Encoding and issuing the SQL save on an isolated database copy took 12.193
seconds with the new setting; that measurement excludes transaction commit.

These measurements are not an end-to-end research speedup or a forecast of
remaining run time. Reading, parsing and validating the project still take time,
and local saves can overlap browser research. This change does not reduce the
number or duration of Claude checks or alter the agreed research cutoff.

## Verification

- Storage, research execution, maintenance, blind comparison and improvement
  suites: `python3 -m unittest tests.test_project_state tests.test_research_execution
  tests.test_scout_maintenance tests.test_scout_maintenance_blind tests.test_scout_improvement`.
- Compatibility tests cover old and new compression in both directions, plus
  restarting a legacy blind-check checkpoint through reconciliation while
  preserving earlier assignments, frozen results, the execution manifest,
  source-package bytes, curator answers and PDF attachments.
- A copy of the paused production database is used for storage-only resume QA.
  No synthetic research or curator decision is submitted to the real run.
  Local evidence is under `output/checkpoint-performance-qa-20260908/`.
