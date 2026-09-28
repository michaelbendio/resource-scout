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
