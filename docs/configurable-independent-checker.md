# Choose the independent research checker

New sampled executions accept configuration schema 2 with an explicit
`blindResearcher`: `Grok`, `Claude`, `ChatGPT` or `Perplexity`.
The primary researcher remains Codex/Astra. The selected outside researcher
receives blind assignments; other outside researchers can receive explicitly
requested targeted challenges. They are not automatically called.

Copy [the Grok example](../resource_research_agent/maintenance_guidance/grok_execution.example.json)
into the run directory and set the office, categories and a fresh sampling seed.
This example deliberately checks Clothing; it does not randomly select other
categories. It requests Grok 4.6, but does not establish that the account or
interface offers that model. Verify availability and record the actual identity
before starting. Unknown identities remain null, never an invented model label.

Pass this file to `maintain prepare --execution-config FILE` or
`editor start-research PROJECT --execution-config FILE`. In schema 2, a non-null
model identity must match the returned receipt. An operating policy conflicting
with an explicitly requested model blocks preparation instead of silently
overriding the request.

Grok checks are saved as `blind:Grok`, shown under Grok in status and reports,
and reconciled under Grok finding IDs. No result is mislabeled Claude. The blind
researcher cannot also receive targeted challenges, which would reveal primary
findings. Existing fresh-context, category-freeze, availability and completeness
requirements apply to every supported checker. Missing access remains pending.

Schema 1 retains the original Claude blind role. Existing saved runs, manifests,
assignments and results are not migrated or rewritten. Changing the checker
means preparing a separate execution, optionally with `--supersedes`, operator
and reason. Resume an existing run by its saved ID. The legacy
`--blind-comparison` flag still selects its established Claude protocol; use the
sampled execution configuration for configurable research roles.

The editor is configured separately in the editor project. Selecting Grok for
research checks does not change Astra's final editing assignment or activate a
learning policy. Switching the checker is not yet an automatically learned
operating-policy decision.

Verification: the 432-test suite passed with one optional test skipped. New tests
exercise all four checkers, attribution, model/context validation, unavailable
providers, restart, separate legacy/new runs, challenge isolation and explicit
model conflicts with operating policies. These are synthetic contract tests,
not evidence of live Grok access or research quality.
