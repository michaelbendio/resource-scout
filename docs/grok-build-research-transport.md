# Grok Build as Scout's independent researcher

Verified on Michael's Mac on September 9, 2026, during the Mesa Clothing
maintenance-and-editor pilot. Scout remains the orchestrator. Grok Build carries
out its sealed outside-research assignments; Astra reconciles the results and
performs the final editorial review.

## Connection and model identity

The installed executable is `~/.grok/bin/grok`, version
`0.2.112 (9bbd559437aa)`. It was already installed but absent from this shell's
PATH. The official OAuth login succeeded through Michael's grok.com account.
No API key was created and the installed binary was not upgraded.

```sh
~/.grok/bin/grok login --oauth
~/.grok/bin/grok models
```

The model list offered `grok-4.6`. A live response reported
`grok-4.6-build`. Use the former as the CLI selection and the latter as the
actual model identity in this pilot's schema-2 execution configuration and
receipts. Recheck these labels on a future installation; do not silently
substitute a model.

The official [Build overview](https://docs.x.ai/build/overview) and
[headless scripting guide](https://docs.x.ai/build/cli/headless-scripting)
describe the direct CLI route. A Codex plugin, router, or model-picker change
was not needed for this integration.

## Dispatch a real research assignment

1. Complete and freeze the primary research before preparing blind packets.
2. Record Grok's successful availability check and a new context UUID in Scout.
3. Save the exact sealed assignments. Prepare a documented transport projection
   containing the original resource fields, exact editable-field whitelist,
   complete result contracts, common guidance and original
   identity catalog. Exclude the current primary findings and challenger work.
4. Split large inputs into one readable JSON file per task, plus separate common
   files. Keep an index and hashes. The installed CLI offloads large prompts;
   a giant single-line JSON value is difficult to read completely through its
   file tool. Permit reads of supplied inputs and the session's own offloaded
   outputs. Use a neutral temporary directory and disable memory and subagents.
5. Run with an explicit model, bounded turns and an external wall-time limit.
   Use a dedicated, short leader-socket path for the workflow. Preserve partial
   output on cancellation or timeout; neither constitutes completed research.
6. Preserve actual web-tool evidence and returned JSON. Validate all assignment
   hashes, task IDs, fields, model/context receipts and coverage gaps through
   Scout before reconciliation. A connection test alone does not verify that
   research tools work.

The first Clothing transport omitted the explicit editable-field whitelist.
Grok returned three Information edits as `informationText`; Scout correctly
rejected them. The operator preserved the raw reply and split its existing five
headings into `informationSections`, asserting exact rendered-text equality and
recording the normalization. This was format repair, not a new research answer.
Future packets should include the whitelist and require the structured sections
for every Information edit, including rechecks.

Command shape for the installed CLI (replace the example paths and UUID):

```sh
~/.grok/bin/grok \
  --leader-socket /tmp/scout-grok-pilot.sock \
  --cwd /tmp/scout-blind-packet \
  --no-memory --no-subagents \
  --tools read_file,web_search,web_fetch \
  --allow Read --allow WebSearch --allow WebFetch \
  --permission-mode dontAsk \
  --max-turns 90 --session-id UUID \
  -m grok-4.6 --output-format streaming-json \
  -p 'Read index.json and its supplied task files. Carry out the sealed blind research and return the required JSON.'
```

For this installed version, the tool-list names are lowercase, while permission
rules use `Read`, `WebSearch` and `WebFetch`. Lowercase permission rules caused
an automatic cancellation under `dontAsk`; that was an operator configuration
failure, not a provider refusal, user cancellation or usage-limit event.

Resume the same sealed context with `--resume UUID` in place of
`--session-id UUID`. Do not move an assignment into a different context without
recording a new execution. Scope the prompt's file permission to supplied
research inputs; the tool allowlist is not itself a filesystem sandbox.

## Measurements and evidence

Capture start/end wall time, interruptions, input/output/cache tokens, tool
activity, returned model identity and validation failures. CLI-reported cost is
accounting information, not proof of an incremental charge to the subscription.
Do not read or copy OAuth credentials into Scout artifacts.

Streaming output includes reasoning events; progress monitoring should use
tool metadata and completion status. Keep human-facing updates focused on
research progress, consequential findings, blockers and estimates. Avoid
publishing internal reasoning in reports or committed evidence.
