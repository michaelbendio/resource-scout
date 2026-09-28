# Limited saved-case learning pilot — September 9, 2026

Real Claude desktop responses, **Opus 5 / High**, with exact source material and immutable assignments. This folder contains no API credentials or user browser state. See the [plain-language result](../../docs/scout-learning-editor-results.md).

- `source-package.zip` is the exact 460-entry pre-edit Mesa draft.
- `editorial-decisions.json` is the attributable Astra editorial ledger, not human verification.
- `lesson-proposal.json` proposes one practical-entry instruction based on the Dignity Threads observation. Its embedded baseline is the actual Clothing/Household playbook snapshot.
- `trial-specification.json` selects six different resource IDs. Five are within Clothing; the apprenticeship probe was an unsuccessful cross-category test design.
- `*-packet.json`, `*-response.json`, and `*-receipt.json` preserve the two actual assignments, verbatim JSON replies, model/context provenance and limitations.
- `assessment.json` and `report.json` record **no clear accuracy gain**, without activating guidance.
- `checkpoint-*/` and `full-checkpoint-*/` contain raw phase timings and exact-input reports. `codec-trial.json` records rejected compression alternatives.
- `synthetic-browser-result.json` is software QA only, not real provider research or human curation.
- `verification.json` records final tests. `artifact-hashes.json` fingerprints the evidence files.

These samples concern public program descriptions in saved Scout research. No new provider facts were checked. Response cost is unknown, and elapsed workbench time is contaminated by operator preparation/coding/capture; it cannot compare provider speed. Both chats used the same account with personalization uncontrolled.

The pilot's assessment was made by the coordinating Astra editor after both replies. It is not a blind human gold standard. The earlier whole-corpus edit was known to the coordinator, though the respondent packets excluded previous editorial decisions and the specific lesson-support example.

To verify the workflow using the saved historical responses without contacting an AI:

```sh
PYTHONPATH=. python3 experiments/learning-pilot-20260909/replay.py
```

The replay uses a disposable database and reproduces hashes, classification of the result and quality counts. It deliberately does not claim to reproduce historical latency or rerun model reasoning. A new live experiment requires a separately named specification and fresh contexts.
