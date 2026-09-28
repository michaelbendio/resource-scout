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
