# Cedar City, Utah — Scout run

Michael requested: “Now have Scout do Cedar City, Utah.”

Office: **Cedar City**. Service area: services usable by Cedar City residents.
Iron County, southwest Utah, statewide, national and remote programs qualify when
Cedar City residents can use them; this is not an all-Iron-County discovery run.
Nearby service sites must serve Cedar City, with travel and access limits explicit.

No existing Cedar City HTML was found in resource-assistant or the checked TSO
directories. The empty Las Vegas source supplies only the category scaffold:
22 source categories, of which Scout researches21 and excludes Miscellaneous.
The new immutable package has Cedar City office/service-area metadata, zero
resources and zero For groups. No Las Vegas resource content was copied.

## Runtime

- Run directory: `data/cedar-city-production-20260924/`.
- Canonical database: `research.sqlite3`, import1.
- Monitor: http://127.0.0.1:8772. Actual Safari display confirms Cedar City and
  DeepSeek-V4.1-Flash, with Addiction running.
- Primary: Codex gpt-5.5, High; primary-only coordinator with locked challenger
  imports between passes. The legacy profile name is codex-grok; no Grok calls run.
- Challenger: DeepSeek V4.1-Flash (`deepseek-flash`), max thinking effort, native
  search/public page fetch. Existing credential storage is reused without copying
  credentials into run artifacts. Conservative per-run ceiling: $5.00; starting
  account balance: $5.23. Balance and preserved usage enforce the ceiling.
- Persistent research watchdog:30-second checks, bounded evidence-preserving
  recovery, at most3 challenger restarts. Local notifications are requested.
- Pipeline: after21 completed categories and research-worker exit, supervised
  Codex High curation,30-candidate/60,000-character batches, compact prior index.
- **automaticReview:true**, explicitly authorized after launch. Michael first
  requested xhigh for both phases, then confirmed **High curation** after discussing
  the recommendation. The effective settings match Las Vegas: High curation,
  followed by **xhigh Codex review**. Use one sequential reviewer.
- The pipeline may continue that review through at most8 bounded90-minute sessions
  only with durable new progress. All source/content, navigation, group, priority,
  browser and exact-fingerprint requirements remain. Missing browser capabilities
  leave review visibly incomplete; no automatic completion merely to enable Save.

Exact commands, authorization, service area, source hash and current PIDs are in
`launch.json`; phase/configuration in `pipeline-status.json` and `pipeline.json`.
Native evidence, original submissions, failures and billing remain in their own
directories. Supervision cannot resolve every substantive error unattended; it
preserves unknown failures for diagnosis and does not expand spending or lower effort.

## Launch verification and timing

Codex authentication and DeepSeek balance checks passed. Primary research began
September25 at03:13UTC; the challenger correctly waits for completed primary packets.
An initial watchdog log-name mismatch was repaired by preserving/renaming the
live logs and restarting only the watchdog. Its original error is retained in
`watchdog-startup-error-001.json`; subsequent status showed no issues.

Twenty-two pipeline, watchdog and challenger tests passed, including manual-review
handoff without launching a reviewer and refusal to hand off incomplete curation.

Refresh timing with `python3 scripts/report-scout-timing.py
data/cedar-city-production-20260924`; add `--curation-dir
data/cedar-city-production-20260924/curation` after curation starts. Worker timings
include provider/search latency; parallel durations add together. Record a future
requested review session separately. No review timer is open for Cedar City.

## Updated authorization

`pipeline-authorization-change-001/` preserves the previous launch, configuration,
status and exact user instructions. Only the waiting pipeline process was restarted;
research workers and completed work were untouched. The new configuration hash is
bound to the preserved waiting-research checkpoint. Tests verify that configured
xhigh curation is not silently lowered and that review prompts use Cedar City’s
actual geography and handoff rather than Las Vegas’s. Final curation remains High
by Michael’s latest choice. Research effort remains Codex High / DeepSeek max.
