# Las Vegas Valley research

## Required time accounting

Michael requested actual processing time separately from elapsed time. Research
workers already persist per-attempt runtimes. Refresh the derived snapshot with:

`python3 scripts/report-scout-timing.py data/las-vegas-production-20260923`

This writes `timing-summary.json`, counts failed attempts separately and avoids
counting DeepSeek's imported telemetry twice. Worker totals include provider/search
latency; overlapping workers add together. They are not GPU-compute measurements.
In-flight work and connectivity probes are excluded. Keep unknown durations visible.

When curation starts, supply `--curation-dir ACTUAL_OUTPUT_DIRECTORY` on every
report; preserve all execution and failure artifacts. For final review/corrections,
start each actively supervised work session with `--review-start DESCRIPTION`,
and close it with `--review-stop` before pausing or handing off. Resume with a new
session. If a session is left open, reconcile its true stop from evidence before
reporting; do not count unattended idle time as review. These flags only record
time and do not authorize or launch curation/review. No review session has begun.
Record delivery time in launch.json's `deliveredAt` to freeze elapsed time at delivery.

Refresh at category/phase checkpoints and before answering timing questions.

Michael authorized Las Vegas Valley, Codex High primary, and DeepSeek V4.1-Flash
challenger. Automatic curation and automatic review remain off.

Michael explicitly approved DeepSeek max: "Continue with max--that's fine."
Codex primary remains High.


Source: `/Users/michaelbendio/resource-assistant/las-vegas.html`, unchanged.
SHA256: `904b144f424abba85c9aee65588867e92e057404e56071bce2e4acc416c84dd5`.
The source has21 research categories, no resources and no For groups.
The imported service area covers Las Vegas, North Las Vegas, Henderson and
surrounding valley communities. Countywide/statewide/remote services qualify when
they serve valley residents; programs solely for outlying Clark County towns do not.

## Runtime and evidence

`data/las-vegas-production-20260923/launch.json` contains exact commands, source
hash, service area, authorization and PIDs. The canonical database is
`research.sqlite3`, import1. Monitor: http://127.0.0.1:8771.

Codex runs gpt-5.5 at High with `--primary-only`. Its legacy profile is codex-grok;
this mode makes no Grok calls. Sealed primary results and metrics persist in SQLite;
the existing primary transport does not preserve its complete native event stream.

The persistent `deepseek_challenger_runner` reads completed primary category packets,
retains the original seal, and researches through DeepSeek's Anthropic-compatible
endpoint using `deepseek-flash`, max effort, native web search and read-only public
page/PDF fetches. No Claude inference or OpenAI search relay is used.
The credential is read from the existing local configuration, never saved in evidence.

`deepseek-challenger/assignment-*` preserves baseline, original/replacement prompts,
requests, responses, tool results, usage, cost estimates and result checkpoints.
Results are imported only after acquiring the canonical runner lock, generally after
the primary coordinator finishes. Audited provider replacements retain original
assignments. The monitor projects the bound DeepSeek manifest/checkpoints without
changing seals or declaring a category complete before database import.

## Budget and supervision

Initial account balance was $6.48; the challenger has a $5 run allowance and
$0.25 account reserve. Conservative peak token estimates and request reservations
guard subsequent requests; they are not an exact invoice cap. Addiction's first
response saved11 leads with upper token cost $0.0405042. Category costs vary.

The challenger persists checkpoints and requests local notifications on terminal
failure/completion. Unknown in-flight requests and substantive failures stop for
diagnosis rather than replaying paid calls. Research completion pauses ready to
curate. No automatic paid review is launched.

The assistant must still monitor the primary process and resolve substantive stops.
The challenger is not a primary-process crash supervisor: if primary stops before
sealing remaining categories it can wait indefinitely. OS reboot recovery and
guaranteed notification delivery are not implemented. Check real processes, the
latest runner event, checkpoint age and errors; a waiting heartbeat is not progress.

## Validation

The live native-search probe and first real category succeeded. The monitor was
restarted independently, and Chrome visibly showed DeepSeek-V4.1-Flash.
Local suite:299 tests, one skipped, including six unrelated untracked Jev tests
which are excluded from this change. Regression checks cover lock-safe import,
seals, paid-call replay prevention, budget guards and the monitor projection.
