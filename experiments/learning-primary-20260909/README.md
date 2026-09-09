# Fresh primary-research learning trial — September 9, 2026

Eight Denver Employment leads, two fresh Astra CLI sessions, existing Employment playbook versus the first-reachable-help addition. Rubric and packets were sealed before model dispatch. Results are **mixed / no-clear-benefit**, evaluated and inactive.

The [short report](../../docs/scout-learning-increment-4-results.md) explains the result. `assessment.json` records case-level judgments; `question-review.json` evaluates curator workload separately. `measurements.json` preserves actual process times, CLI token/cache counts and unknown subscription dollar costs. The CLI traces are task-specific and contain no authenticated browser/profile captures.

`prepare.py` and `run.py` document how this **live** experiment was conducted. Do not run them to replay evidence: `run.py` makes real model calls. Its elapsed ceiling is enforced, while source-page counts are not independently exposed by the CLI. Visible baseline/candidate labels and an unblinded assessor are additional limitations. No activation review was created.

Run the offline replay from the repository root:

```sh
PYTHONPATH=. python3 experiments/learning-primary-20260909/replay.py
```

The replay verifies file hashes, reproduces the sealed packets, imports actual saved responses and re-evaluates the saved judgments in a temporary database. It makes no model calls, edits no office file and activates nothing. Supporting editorial evidence is reused by exact hash from `../learning-pilot-20260909/`; it is not copied into respondent packets.
