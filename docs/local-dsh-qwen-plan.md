# Local DSH and Qwen Plan

Status: Phase 1 implementation and calibration complete. The production cutover gate failed, so Phase 2 was not started.

## Objective

Run Resource Scout research through DeepSeek Harness (DSH) with Qwen3.8-27B on the local 64 GB M4 Pro Mac mini, free search, and safe local page retrieval. The finished production path must not require or silently fall back to a metered model or search provider.

Resource Scout continues to own the research workflow, prompts, imported package knowledge, stage persistence, candidates, duplicate decisions, lessons, review state, and exports. DSH remains a bounded execution layer that receives one stage assignment and returns one structured research result.

## Decisions

- Keep DSH as the harness.
- Keep the implementation in the Resource Scout repository initially.
- Use DSH's existing generic `dsh-llm-pi-ai` adapter for the local model endpoint.
- Use `mlx-community/Qwen3.8-27B-4bit` through an OpenAI-compatible MLX endpoint on `127.0.0.1:8080`. Calibration rejected the 8-bit artifact for throughput and selected 4-bit for the final Phase 1 evaluation.
- Start with a 65,536-token context limit and medium reasoning effort.
- Add a Resource Scout-owned DDGS search provider for DSH.
- Add a Resource Scout-owned safe HTTP fetch provider for DSH.
- Do not add browser automation until search plus safe fetching demonstrates a specific coverage gap.
- Never fall back automatically from the local configuration to DeepSeek or another cloud provider.
- Preserve the current DeepSeek path during evaluation as an explicit metered comparison option.
- Leave the production background service unchanged throughout Phase 1.

These initial model, context, and reasoning choices are benchmark inputs rather than permanent truths. The Mesa calibration gate may justify changing them before the full comparison.

## Target architecture

```text
Resource Scout
    |
    | one bounded stage prompt / one structured result
    v
DSH headless composition
    |-- local model provider --> MLX --> Qwen3.8-27B (calibration-selected quantization)
    |-- web_search -----------> DDGS
    `-- web_fetch ------------> safe local HTTP fetcher
```

The local composition exposes only the research tools required by the assignment. Shell, filesystem, editing, workflow, subagent, skill, and code-execution tools remain disabled. DSH continues to run each assignment from an empty temporary workspace.

## Zero-metered-services invariant

Resource Scout may display **Local - no metered services** only when all of the following are true:

- The resolved DSH model provider is the configured loopback Qwen endpoint.
- The resolved search provider is DDGS or another explicitly approved free/local provider.
- The resolved fetch provider is the project-owned local fetcher.
- No cloud fallback model is configured.
- No metered search fallback is configured.
- The local model health check succeeds.

Local mode must fail closed. If Qwen, DDGS, or fetching is unavailable, the stage fails with an actionable message. It must not switch providers automatically.

## Repository layout

The implementation is expected to remain alongside Resource Scout:

```text
resource-scout/
|-- dsh-plugins/
|   |-- web-search-ddgs/
|   `-- web-fetch-safe/
|-- dsh-runtime/
|-- docs/
|-- resource_research_agent/
`-- tests/
```

A plugin should move to a separate repository only after it proves useful outside Resource Scout and has a stable interface worth maintaining independently.

## Phase 1: build and prove the local path

Phase 1 is an experimental path run in the foreground against a separate benchmark database. It does not replace or modify the production background service.

### Step 1: baseline and configuration contract

Define a named DSH configuration, **Local Qwen**, with explicit model, search, fetch, context, reasoning, timeout, and fallback settings.

Tests:

- Run the complete existing Resource Scout test suite before changes.
- Resolve the DSH composition and assert the selected model, search, and fetch providers.
- Assert that no `deepseek-official` model route is active in Local Qwen mode.
- Assert that no DeepSeek search plugin or cloud fallback is active.
- Assert that an unavailable local dependency produces a clear failure.

Gate: existing tests remain green and the zero-metered-services invariant is represented by executable tests.

### Step 2: local Qwen runtime

Add supported installation, launch, health-check, and shutdown instructions or scripts for the pinned MLX runtime and model. During Phase 1 the service remains foreground/manual.

Tests:

- Installation and launcher tests use temporary directories and mocked commands where practical.
- `GET /v1/models` reports the configured model.
- A basic text completion succeeds.
- A representative structured-output request succeeds.
- A representative tool-call request is accepted and returned in the expected protocol.
- The service binds only to loopback.
- Stopping the service makes the health check fail promptly.
- A live measurement records memory pressure, prompt-processing speed, generation speed, and model load time on the target Mac.

Gate: Qwen is independently usable through the local API with safe memory headroom.

### Step 3: DSH local-model route

Configure `dsh-llm-pi-ai` with a `qwen-local` route and generalize Resource Scout's DSH adapter so provider selection is not hard-coded to `deepseek-official`.

Tests:

- A fake local API captures the exact request emitted by DSH.
- DSH selects `qwen-local` and the configured model.
- `DEEPSEEK_API_KEY` is neither required nor forwarded.
- Context and reasoning settings reach the endpoint correctly.
- Valid structured output is normalized through Resource Scout's existing result boundary.
- Empty output, malformed JSON, endpoint failure, timeout, and interruption retain clear error behavior.
- The temporary workspace and disabled-tool boundary remain intact.

Gate: DSH completes a one-shot structured task through local Qwen without web tools.

### Step 4: free search plugin

Create a Resource Scout-owned DSH search provider backed by DDGS. Its responsibility is discovery only: query in; normalized URLs, titles, snippets, optional dates, and truncation status out.

Tests:

- Normalize valid results.
- Reject invalid or unsupported URLs.
- Deduplicate equivalent URLs.
- Enforce the configured result limit.
- Handle no results, malformed results, throttling, timeout, and cancellation.
- Require no API key.
- Use deterministic mocked responses for routine tests.
- Provide an optional live test for one harmless query.

Gate: DSH's ordinary `web_search` tool works through a free provider.

### Step 5: safe page-fetch plugin

Create a Resource Scout-owned DSH fetch provider. It initially supports bounded HTML and plain-text retrieval rather than browser automation.

Security requirements:

- Allow only HTTP and HTTPS.
- Reject credentials embedded in URLs.
- Resolve and validate destinations before connecting.
- Block loopback, private, link-local, reserved, multicast, and metadata destinations for IPv4 and IPv6.
- Revalidate every redirect destination.
- Bound redirects, bytes, and elapsed time.
- Accept only approved content types initially.
- Convert HTML to bounded readable text.
- Return the final URL, status, content type, and truncation state.

Tests:

- Successful HTML and text retrieval.
- Ordinary redirects.
- Redirect-to-private-address rejection.
- IPv4 and IPv6 blocked-address cases.
- DNS resolution and rebinding-oriented cases.
- Oversized-response truncation.
- Unsupported content-type rejection.
- Timeout and cancellation.
- Malformed HTML handling.
- Search-result URL followed by successful retrieval.

Gate: Qwen can inspect primary-source page content rather than relying on search snippets.

### Step 6: Resource Scout integration

Generalize the existing DSH connection rather than introducing another harness.

Expected application behavior:

- The connection is labeled **DSH**.
- The user can choose **Local Qwen - no metered services** or an explicitly labeled metered DeepSeek configuration.
- Status reports the resolved model, endpoint, search provider, fetch provider, and readiness.
- Local mode never uses a cloud fallback.
- Each stage's existing usage/provenance record includes the resolved model, runtime, search provider, fetch provider, attempt number, and timing.
- Existing research data, staged progress, review state, and exports remain compatible.

Tests:

- Settings save and reload correctly.
- Only relevant DSH fields appear for the selected configuration.
- Local readiness requires both DSH and Qwen.
- DeepSeek credentials are irrelevant in Local Qwen mode.
- A cloud provider causes the no-metered-services status to fail closed.
- Stage provenance records the complete execution stack.
- Existing DeepSeek-mode and adapter-normalization tests remain green.
- Partial-run and resume behavior remains correct.
- The complete Resource Scout suite passes.

Gate: Resource Scout can launch Local Qwen research from its ordinary interface while the production service remains unchanged.

### Step 7: Mesa comparison

Run the benchmark defined in `docs/mesa-qwen-deepseek-benchmark.md`. It starts with a one-stage and one-category calibration before committing to all 20 categories.

Gate: the 20-category comparison is complete and its quality, quantity, reliability, and timing criteria justify production use. A failed gate sends the work back to the relevant Phase 1 component; it does not trigger production cutover.

Recorded outcome: the initial one-stage calibration passed operationally, but the complete Housing calibration was 62% slower than DeepSeek and produced 57% fewer candidates. A broader-search retry increased a representative stage by only one candidate while reducing evidence density. The gate failed, so the remaining 19 categories were not run.

### Phase 1 endpoint

- Local Qwen research works through DSH in the foreground.
- Search and page retrieval require no paid provider.
- One isolated Mesa benchmark database contains the frozen 20-category DeepSeek baseline, all Qwen calibration attempts, their raw outputs, and the completed Housing comparison.
- The DeepSeek production service and live research database remain untouched.
- The full automated test suite passes.
- Phase 1 changes are reviewed, committed, and pushed.

## Phase 2: production cutover

Phase 2 operationalizes the proven Phase 1 configuration. It is not another model experiment.

Status: not started. The Phase 1 evidence does not justify replacing the current production path with this Qwen configuration.

### Step 1: lock the approved stack

Pin the approved model artifact, MLX runtime, DSH runtime, context, reasoning level, search plugin, and fetch policy.

Tests:

- A clean installation reproduces the approved versions.
- The resolved DSH composition matches the approved benchmark configuration.
- No unpinned or automatic cloud fallback exists.

### Step 2: manage Qwen as a Mac service

Create a separate LaunchAgent for the model server so model lifecycle, restart behavior, health, and logs remain independent of Resource Scout.

Tests:

- Start at login, stop, start, restart, crash recovery, and logs.
- Loopback-only binding.
- No duplicate model processes.
- Resource Scout becomes unready while the model is stopped and ready after recovery.

### Step 3: cut the Resource Scout service over

Update the existing background launcher to start Resource Scout without retrieving a DeepSeek key. Preserve the current Tailscale behavior and database path.

Tests:

- Background installation no longer requires a DeepSeek Keychain item.
- LaunchAgent templates and control scripts pass their tests.
- Existing research history remains readable and exportable.
- Local DSH becomes the default after settings migration.
- No stage can silently switch to a metered provider.
- Local and Tailscale status endpoints remain healthy.

### Step 4: production burn-in

Run one complete four-stage category through the normal background service. Intentionally restart the application during a stage and exercise resume.

Tests and observations:

- All stages complete or resume correctly.
- Completed work survives restart.
- Candidates, drafts, and exports remain correct.
- iPad access through Tailscale works.
- No metered provider request occurs.
- Sustained memory pressure and temperature remain acceptable.

### Step 5: finish the cutover

- Document DSH with Local Qwen as the default.
- Label DeepSeek as an explicit metered fallback.
- Remove DeepSeek requirements from installation and service instructions.
- Do not delete an existing Keychain credential automatically.
- Run the complete test suite.
- Commit and push the production cutover.

### Phase 2 endpoint

Resource Scout starts automatically after login, reaches Qwen locally through DSH, researches through free search and safe page retrieval, remains available through Tailscale, survives restarts, and requires no paid-provider credential. DeepSeek is used only when deliberately selected.

## Rollback

Phase 1 requires no production rollback because it does not alter the production service.

During Phase 2 stabilization:

- Preserve the previous service launcher and configuration in version control.
- Keep the DeepSeek DSH configuration available as an explicit selection.
- Never select it automatically after a local failure.
- Preserve the live database before service migration.
- Roll back the launcher and selected configuration without rewriting research data.

## Deferred work

The following are optional improvements after Phase 2 and must not delay elimination of metered charges:

- Benchmark BaseRT against the approved MLX baseline.
- Revisit 4-bit versus 8-bit only if the selected 4-bit calibration reveals a material quality loss.
- Replace DDGS with self-hosted SearXNG if discovery quality warrants it.
- Add narrowly scoped browser automation for proven JavaScript-only coverage gaps.
- Experiment with longer context or other reasoning levels.
