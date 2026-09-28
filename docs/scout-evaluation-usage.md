# Isolated Scout evaluation

Use `python3 -m resource_research_agent.evaluation --help` from the implementation
checkout. Copy `tests/fixtures/scout_evaluation/config.example.json` to an ignored
local location. Its IDs, hashes, criteria and rates are placeholders; **its prices
are synthetic, not live rates**. Fill in the original source database/package,
explicit primary job selection and reason, code commit, original policy/redaction,
model configuration, dated pricing evidence and reviewer-frozen generic needs.
Never put credentials in configuration or fixtures.

```
python3 -m resource_research_agent.evaluation init --config LOCAL_CONFIG.json --out data/evaluations/mesa-housing
python3 -m resource_research_agent.evaluation seal --experiment data/evaluations/mesa-housing
python3 -m resource_research_agent.evaluation status --experiment data/evaluations/mesa-housing
```

Initialization reads the source through SQLite `mode=ro` and the backup API.
The copied original package must have the selected import's exact checksum.
If the archive is unavailable, explicitly set `baseline.originalPackage` to null,
`baseline.reconstructOriginalSnapshot` to true, and `baseline.expectedContentSha256`
to the original import's canonical content hash. This fallback accepts only the
original raw resource/category/group rows whose recomputed hash matches both the
stored import and configured hash. It preserves the original source filename for
legacy office inference and independently requires the scratch known-resource
manifest to match the original primary job. The manifest records that the ZIP
container bytes differ; this does not recover or claim the original ZIP bytes.
Historical answers remain reviewer-only. Sealing binds original inputs, baseline,
criteria, system instructions and provider/pricing settings. Changed inputs need
another experiment; initialization and evidence files are not reset operations.

No command above calls a provider. Paid authorization is separate from a sealed
protocol. All experimental output remains evaluation-only and non-importable.

## DeepSeek API and billing gate

The isolated adapter uses the existing DeepSeek credential lookup, only at explicit
live execution, and sends it only to the official Anthropic-format Messages endpoint.
It exposes native web search and public HTML/text/PDF fetching, with no shell,
local-file or database tool. It preserves requests, sanitized raw responses,
source evidence, usage and returned model metadata; unexpected model aliases hold
results. Production challenger orchestration and imports are not called.

Documentation checked September 27:
[DeepSeek's Anthropic compatibility](https://api-docs.deepseek.com/guides/anthropic_api/)
confirms the endpoint, model alias handling, thinking/effort fields and search result
blocks. [Pricing](https://api-docs.deepseek.com/quick_start/pricing/) must be frozen
for a real launch, including native-search charges, token/cache accounting and a
context upper bound. API support does not itself establish a safe spending bound.
The included example remains synthetic and cannot authorize live dispatch.

A live authorization must identify this exact protocol hash, provider, billing
owner/account, approval text/date, total cap, explicit stage caps and categories.
Each native request reserves its worst-case charge before dispatch. Unknown usage
retains the reservation; a timeout after sending does not permit automatic replay.
Never copy the synthetic test authorization into a paid experiment.

Live dispatch also requires coverage criteria with `status: "frozen"`, nonempty
`essentialNeeds`, `frozenBy`, and `frozenAt`. These record a completed reviewer
judgment; sealing a draft or entering a spending approval cannot substitute for it.

## Existing-policy execution

```
python3 -m resource_research_agent.evaluation run --experiment EXPERIMENT --condition existing-policy --category housing --dry-run
```

This imports only frozen original inputs into an owned scratch database and checks
the original known-resource baseline and focused policy. The full next assignment
is saved locally; later assignments depend on the condition's own findings.
Omitting both execution flags also defaults to dry-run. No production store,
office delivery, identity registry or human curation state is changed.

After the launch gates above are actually satisfied, the exact paid command is:

```
python3 -m resource_research_agent.evaluation run --experiment EXPERIMENT --condition existing-policy --category housing --execute
```

Do not use the offline Mesa preflight as a live experiment: its criteria are draft,
pricing is incomplete, and its recorded commit predates the final ticket-4 code.
Create and seal a new experiment at the committed code revision for a real launch.
Only Housing is eligible for paid execution at M0/M1. Research completion remains
`completed-research-awaiting-source-audit`, with no quality or adoption approval.
Resume with the same command; immutable responses and ledger entries prevent
replaying completed calls. Uncertain paid outcomes remain held for reconciliation.

An explicit user removal of the Housing dollar cap is recorded as
`dollarCapMode: "none-authorized"`, `totalUsd: null`,
`stageCapsUsd: {"housing-research": null}`, and `categories: ["housing"]`,
with the actual approval text. This narrow override permits unknown billing bounds
to remain null; it does not waive call/time/retry limits, frozen criteria, source
isolation or uncertain-request holds. It does not authorize any other stage.

## Offline comparison artifacts

After all original-policy passes complete:

```
python3 -m resource_research_agent.evaluation audit-packet --experiment EXPERIMENT --category housing
python3 -m resource_research_agent.evaluation report --experiment EXPERIMENT
python3 -m resource_research_agent.evaluation record-audit --experiment EXPERIMENT --category housing --judgment AUDIT.json
```

A/B labels separate explicit provider attribution; recognizability must still be
acknowledged. `record-audit` records supplied reviewer judgments and cannot perform
source review. Advancement needs every frozen essential need addressed with dated
evidence, consequential errors resolved, no repeated consequential error awaiting
retest, all claimed unique additions audited, and useful reduction in Codex work.
The initial projection explicitly leaves unmeasured preparation/reconciliation
stages unmeasured. These commands never start paid requests.
