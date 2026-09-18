# Pairwise Research Experiment

This branch adds opt-in pairwise researcher profiles without changing the baseline
researcher roster on `main`.

## Profiles

The API accepts a named `profile` when preparing Codex-first research:

- `codex-grok`: Codex primary, Grok challenger.
- `codex-claude`: Codex primary, Claude challenger.
- `claude-grok`: Claude primary, Grok challenger.

ChatGPT and Perplexity are disabled in all three profiles. The ordinary baseline
roster remains available when no profile is supplied.

Example:

```json
POST /api/codex-first-research
{
  "importId": 1,
  "profile": "codex-grok"
}
```

A request may supply either `profile` or an explicit `roster`, but not both.

## Research shape

The configured primary researcher performs the existing versioned focused passes
and deterministic coverage-gap pass. The challenger then receives the combined
identity exclusion list and performs the existing adversarial challenger pass.

The pairwise experiment deliberately keeps the existing storage schema and
candidate/consolidation pipeline so differences are attributable to researcher
configuration rather than a simultaneous data-model rewrite.

## Controlled comparison

Preserve the current St. George run as the baseline. Select 6–8 diverse
categories and rerun each from the same package baseline with:

1. current baseline roster,
2. `codex-grok`,
3. `codex-claude`,
4. `claude-grok`.

Do not merge results across conditions before scoring them.

For each category and condition record:

- accepted identities recovered from the baseline curated union,
- new accepted identities absent from the baseline,
- consequential service pathways missed,
- rejected/noise identities,
- duplicate identities,
- source/ecosystem diversity,
- source responses and submitted leads,
- curator decisions/time,
- assignment issue time,
- first-response time,
- completed-result time,
- category wall-clock completion time.

Primary summary metrics:

- curated-union recall,
- consequential-pathway miss count,
- accepted unique additions,
- accepted identities per wall-clock minute,
- incremental accepted identities per additional research minute,
- curator minutes per accepted identity.

The proposed replacement gate is approximately 95% recall of the curated union
with no consequential pathway misses, together with a material wall-clock or
operational improvement. Treat that as an experimental gate, not a permanent
product rule.

## Isolation

Run this experiment from a separate worktree checked out to
`pairwise-research-experiment`. Do not point the currently running Scout
process at that worktree or its configuration until the baseline run has reached
the chosen clean stopping boundary and its database/checkpoint has been copied.


## Running the Codex + Grok sample

With the pairwise Scout server running on port 8766 and the St. George package
imported as import 1, run the Codex primary passes from a second terminal:

```bash
cd ~/resource-scout-pairwise
git pull --ff-only
python3 -m resource_research_agent.pairwise_runner \
  --database data/research-agent.sqlite3 \
  --import-id 1 \
  --profile codex-grok \
  --max-categories 6
```

The runner uses one ephemeral Codex context per pass, with live web search and the
same response schema as the existing Codex replay runner. The Scout browser can
remain open at `http://127.0.0.1:8766`; its polling view will reflect database
progress while the runner works.

After each primary category reaches its gap pass, the runner prepares the Grok
challenger assignment. At the end it writes all pending Grok assignments plus a
manifest to `data/pairwise-challenges/`.


## Lock-step Grok handoff

Pairwise profiles now gate the primary researcher at the end of each category.
For `codex-grok`, Codex cannot begin the next category until Grok's challenger
result for the current category has been saved.

Read the pending Grok assignment, copy it to the macOS clipboard, and open the
Grok app:

```bash
python3 -m resource_research_agent.pairwise_challenge \
  --database data/codex-grok.sqlite3 \
  --import-id 1 \
  next --researcher Grok --copy --open-app
```

After Grok returns the required JSON, copy the JSON response and submit it
directly from the clipboard using the assignment ID printed by the previous
command:

```bash
python3 -m resource_research_agent.pairwise_challenge \
  --database data/codex-grok.sqlite3 \
  --import-id 1 \
  submit-clipboard ASSIGNMENT_ID
```

Then rerun the Codex primary runner. It will close that category and move to the
next one. This keeps Codex and Grok in lock-step and prevents Codex from running
ahead of the challenger.
