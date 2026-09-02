# Source-hidden Codex-first replay

The replay measures whether lessons derived from the saved research-team results
improve Codex's own research. It compares the completed Codex-first v1 run with
a fresh Codex-first v2 proposal for every non-Miscellaneous category.

## Fixed study boundary

- v1 and v2 use the same connected package import, office, service area,
  categories, and known-resource baseline;
- ChatGPT, Grok, Perplexity, and Claude do not run again;
- provider results are split into anonymous aggregate lesson evidence and sealed
  resource identities;
- v1 result snapshots and provider identities remain unavailable through the
  replay API until every v2 category is closed; and
- v2 runs in a fresh Codex context that receives only its current assignment.

The anonymous evidence contains fixed counts for source classes, lead shapes,
pathway signals, access concerns, and provider completion. It cannot contain a
resource name, program name, URL, host, phone number, or arbitrary provider
text. The v2 playbook proposal adds only the strongest anonymous patterns to the
same number of category passes.

Two incomplete shadow assignments do not invalidate the Mesa replay. Their
missing status is preserved in the evidence, while the three completed
challengers provide the required held-out identities. Missing evidence is never
silently represented as a zero-result submission.

## Durable states

A replay moves through `sealed`, `running`, `codex-closed`, `revealed`, and
`completed`. Assignments and results resume after restart. Repeating preparation
for the same package fixture returns the existing study. Category metrics and
the completed report become immutable once written.

The operational API is:

- `POST /api/codex-replays` to seal or resume a study;
- `GET /api/codex-replays?importId=4` and `GET /api/codex-replays/{id}` for
  progress;
- `POST /api/codex-replays/{id}/next-assignment` for the next fresh-context v2
  assignment;
- `POST /api/codex-replays/{id}/results` to save one pass; and
- `POST /api/codex-replays/{id}/reveal` only after all v2 work is closed.

Equivalent command-line operations are `replay-prepare`, `replay-status`,
`replay-next`, `replay-submit`, and `replay-reveal`.

The unattended runner starts one ephemeral, read-only Codex process for each
pass, gives it only the current assignment, enables live web search, validates
its JSON response, and checkpoints it before starting another fresh process.
It pins the worker model to `gpt-5.5` and ignores unrelated user/plugin
configuration so the execution environment cannot drift between passes:

```sh
python3 -m resource_research_agent.codex_replay_runner 1 \
  --database data/manual-multimodel-pilot.sqlite3 --reveal
```

An interrupted run resumes the assigned pass. Worker failures retry twice and
then stop with the answer key still sealed.

## Final comparison

After reveal, the report contains the exact v1 and v2 playbooks and assignments
for every category, plus recovery, retention, novelty, duplicate, uncertainty,
source-coverage, and research-time metrics. The result is proposal evidence
only. It does not alter an active playbook, provider roster, connected package,
or curation result.

## Next taxonomy checkpoint

The replay must finish before the taxonomy redesign. The next required work is
a full-corpus audit that proposes thoughtful Types for every need category and
infers comprehensive `For` groups from all resources. Categories remain needs;
Types describe how a resource addresses a need; `For` describes populations a
resource targets or accommodates. No proposal is activated without review.
