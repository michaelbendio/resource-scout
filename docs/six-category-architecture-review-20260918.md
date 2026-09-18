# St. George six-category architecture review

Status: architecture review complete, September 18, 2026, at Extra High.
Production preparation may proceed. **The production run remains unstarted**;
Michael will return and select High before launch.

## Decision

Use Codex for focused primary research and Grok for the ordinary challenger.
Claude is disabled for all future Scout work, including preflights, after Michael
reported more than $125 in unexpected Anthropic charges. That reported cost has
not been reconciled against billing records; the prohibition applies regardless.
The earlier draft's scoped Claude recommendation is withdrawn.

Preserve all three pairwise conditions **and the earlier five-worker evidence**.
The [five-worker comparison](five-worker-versus-codex-grok-20260918.md) confirms a
large operational speed improvement but meaningful omissions from the new pair,
including EnglishConnect, BYU–Pathway, accessible library services and the survivor
phone benefit. Some were found by the earlier Codex primary. Therefore the right
response is evidence retention and explicit pathway checks, not a claim that more
workers or a particular provider guarantees coverage.

This is a provisional operating choice, not a statistically established best
model pair or measured accepted-resource recall. Use narrow follow-up assignments
when an actual consequential gap is identified; do not automatically commission a
third broad list, switch provider after authentication failure, or split by count.
Production remains held for Michael to return and select High. Its preparation
must also reuse the older Employment primary and completed Financial Assistance
passes rather than rerun saved work.

Do not restore automatic recursive partitioning. The observed stalls were
authentication failures; the unchanged, authenticated monolithic assignment
succeeded. Keep partitioning available as a future hypothesis if an authenticated
worker demonstrates a real task-size limit.

## Evidence and limits

Inputs are the three original databases in
`data/pairwise-overnight-20260918-022703/`, original runner logs, the sealed
Addiction replay, and native Claude transcripts matched to both the assignment
and the exact saved final response. Read-only exports and audit notes are in
`data/pairwise-review-20260918/`. The completed Codex conditions were fingerprinted
before analysis and remain unchanged. The final evidence manifest records all
three database hashes and the analysis artifacts.

All conditions used the same empty-resource St. George package baseline (logical
SHA-256 `fbab7d779f2d30949c18ba0dc0afac2c2fdbde6f63b5b7faafd762fbc1b02819`).
They used four focused primary passes (five category-specific passes for
Clothing/Household), followed by one gap pass and a challenger that saw its own
primary's exclusion set. Compare all saved results, not just the last process's
counters.

These are six categories, one locale, one run per condition. The Codex primaries
were rerun independently and returned different lists. Challenger differences
therefore mix model behavior with different primary omissions; this is not a
frozen-primary randomized experiment. Runs also occurred at different times,
under changing wrapper limits and authentication availability. Production's
corrected prompt has not been evaluated as a new six-category condition. We preserve the original observations rather than
retroactively calling them tests of the revised code.

**No condition has recorded curator acceptance decisions or curator minutes.**
Consequently accepted unique identities, marginal accepted challenger identities,
accepted identities per active research minute, and marginal accepted identities
per additional research minute are **not measured**. Exact names, domains, source
rows and model-produced leads cannot substitute for those quantities. This review
completes the architecture decision with that limitation explicit; it does not
claim a curated recall or precision gate has passed. Production research readiness
is separate from readiness to publish `autoStGeorge.html`.

## Counts, time and execution cost

All eighteen category-condition results are complete. These are submitted rows,
not accepted unique identities. Time columns are minutes.

| Condition | Primary rows | Challenger rows | Total rows | Successful primary estimate | Successful challenger estimate | Successful total estimate | Category elapsed windows, including failures/pauses |
|---|---:|---:|---:|---:|---:|---:|---:|
| codex-grok | 376 | 97 | 473 | 61.7 | 29.3 | 91.1 | 91.1 |
| codex-claude | 410 | 157 | 567 | 63.9 | 63.4 | 127.3 | 488.1 |
| claude-grok | 603 | 95 | 698 | 264.3 | 31.7 | 296.1 | 810.3 |

The successful estimates combine uninterrupted assignment windows for historical
Codex+Grok, recovered Claude transcript durations, and saved Grok attempt timing.
They are useful approximations, not one perfectly uniform clock. The category
elapsed windows retain the large Addiction failures and pauses; the three
conditions overlapped, so summing their wall times is not project duration.

The 94 extra rows in Codex+Claude versus Codex+Grok comprise 34 extra primary
rows and 60 extra challenger rows. They cannot all be credited to the challenger.
Claude primary used about 4.3 times Codex+Grok primary time for about 1.6 times
as many submitted rows; accepted marginal value remains unknown.

### Category differences

Each cell is **primary + challenger rows; successful total estimate / elapsed
category window**, in minutes.

| Category | Codex+Grok | Codex+Claude | Claude+Grok |
|---|---|---|---|
| Addiction | 56 + 11; 14.2 / 14.2 | 66 + 16; 18.9 / 379.5 | 81 + 15; 49.6 / 563.4 |
| Children/Pregnancy | 73 + 20; 14.5 / 14.6 | 81 + 27; 20.0 / 20.1 | 125 + 20; 49.8 / 49.9 |
| Clothing/Household | 40 + 8; 17.5 / 17.5 | 43 + 17; 23.4 / 23.4 | 59 + 7; 50.8 / 50.9 |
| Disability | 79 + 21; 15.8 / 15.8 | 83 + 53; 27.1 / 27.1 | 128 + 17; 54.8 / 54.9 |
| Domestic Violence | 61 + 17; 15.3 / 15.3 | 64 + 21; 18.0 / 18.0 | 102 + 21; 45.0 / 45.1 |
| Education | 67 + 20; 13.7 / 13.7 | 73 + 23; 19.9 / 20.0 | 108 + 15; 46.1 / 46.2 |

### Throughput and review payload

These rates deliberately count raw rows, **not accepted resources**. Narrative
words count only `whyRelevant` plus `uncertainty`; they are a reading-payload
proxy, not timed curator effort.

| Condition | Raw rows / successful minute | Challenger rows / challenger minute | Narrative words | Median words per row |
|---|---:|---:|---:|---:|
| codex-grok | 5.19 | 3.31 | 28,669 | 59 |
| codex-claude | 4.45 | 2.48 | 44,720 | 62 |
| claude-grok | 2.36 | 2.99 | 64,044 | 89 |

### Recovered native activity

| Observed work | Successful calls | Assistant messages | WebSearch invocations | WebFetch invocations | ToolSearch invocations | Explicit WebFetch errors |
|---|---:|---:|---:|---:|---:|---:|
| Claude challenger in Codex+Claude | 6 | 162 | 274 | 96 | 6 | 1 |
| Claude primary in Claude+Grok | 31 | 832 | 1084 | 478 | 31 | 15 |

Grok's six successful Claude+Grok challengers report 33 native turns. Comparable
Codex and historical Codex+Grok counters were not retained. Grok search totals
are unknown. The larger Claude tool totals reflect its much larger role as a
primary, not a controlled per-call efficiency comparison. Provider `num_turns`
and native assistant-message counts must not be combined as one unit.

The [machine-readable results](six-category-results-20260918.json) retain exact
values, time bases, source hashes and unmeasured outcome fields.

Elapsed worker time includes provider waiting and tool latency. Database assignment
windows include orchestration overhead and, when a run was interrupted, downtime.
Recovered native Claude durations span the first user prompt to the final saved
assistant response, excluding process startup and exit. None is pure inference
time. Successful-call time is useful for architecture capacity planning; failed
calls and human recovery are real operational costs and remain separately visible.

Codex+Grok predates complete Scout telemetry, as does most Codex+Claude work. Do
not report absent searches or turns as zero. Native Claude assistant-message and
tool-invocation counts are a different unit from its provider `num_turns` and
billed/server web-search counters. Grok's successful envelopes do not expose a
usable search total. There is no defensible combined token, search, turn or dollar
cost ranking across all three conditions. Subscription usage cannot be inferred
from raw lead counts or these partial counters.

At review time the installed CLIs were Codex 0.154.0, Claude Code 2.1.266, and
Grok 1.0.34. Matched Claude transcripts report High effort and `claude-opus-5`;
its usage envelopes also include Haiku activity associated with web work. Grok's
recovered envelopes identify `grok-4.6-build`. These compare complete worker setups,
not isolated base-model benchmarks. Production explicitly requests Codex `gpt-5.5`
at High; requested defaults and exposed effective model metadata are retained for
the other CLIs. A future CLI or default-model change should be treated as a change
in the operating condition.

The historical Codex calls did not retain comparable effective-effort metadata.
Do not infer it from the conversation's High or Extra High setting: independent
CLI workers have their own settings. Explicit production effort removes that
ambiguity going forward without relabeling the original experiment.

### Failures and fairness

Separate three Claude+Grok histories:

1. Original execution: Claude's 24-turn wrapper ceiling caused terminal failures.
   It was a configuration limit, not evidence that Claude cannot do the task.
2. Authentication-blocked monolithic and recursive attempts: native Grok logs
   record repeated HTTP 401/credential-lock failures and zero completed inference
   or tool events. Those calls never supplied a valid test of task granularity.
   Preserve their elapsed time as operational loss, not active successful research.
3. Authenticated recovery: the unchanged original Addiction assignment completed
   in 232.309 seconds, six native turns, and fifteen submitted leads. Subsequent
   ordinary category challengers also completed without partitioning.

The recovered Disability challenger handled 128 primary leads and a 28,706-character
assignment in about 5.6 minutes. Children/Pregnancy handled 125 leads and 25,545
characters in about 5.3 minutes. Both exceed the removed proactive thresholds
(36 candidates or 18,000 characters). Those thresholds would split work that
demonstrably completed monolithically; candidate count alone is not a justified
trigger in this evidence.

Four original 24-turn failures occurred in each Claude-bearing condition. The
native failure envelopes provide about 19.5 failed worker minutes in Codex+Claude
and 19.4 in Claude+Grok; their much larger Addiction assignment windows include
pauses and recovery. Historical authentication evidence includes overlapping
observations and preflights; do not add every log duration to SQLite attempts as
though they were independent research calls. Three recorded 900-second Grok
attempts are only a subset of the earlier outage. All fifteen historical partition
rows remain as evidence and are not production tasks.

The 60-turn setting completed the recovered work. Native `num_turns` may exceed
the command's round budget; use the CLI's terminal result, not an assumed equality
between counters, to diagnose exhaustion. The runner now stops terminal budget,
authentication and timeout failures instead of retrying the same assignment.

## Research quality and complementarity

The [source audit](six-category-source-audit-20260918.md) is a purposive review of
consequential cases across every category and all three conditions, not a random
sample or full curation. It tests the practical importance of misses and the
plausibility of additional rows. It does not yield a precision percentage.

| Category | What the evidence changes about the architecture decision |
|---|---|
| Addiction | Grok recovered Family Healthcare MAT after its Codex primary. Claude also found it as a primary, while one Claude challenger conflated it with FourPoints. All three conditions included At The Crossroads despite its explicit treatment exclusions. Keep an independent challenger and check negative service evidence. |
| Children/Pregnancy | Angel Watch was covered by all three conditions but required the Claude challenger in one. More primary rows did not establish a unique model capability. Public-system and population-specific pathways matter alongside familiar providers. |
| Clothing/Household | BREATHE Care was found by both Codex primaries and only by Grok after Claude. Claude found the caseworker-mediated Christmas Box resource room, absent from the Codex+Grok list. Both challengers also produced seasonal, indirect or geographically uncertain entries. A broad third list for every category would create real review burden. |
| Disability | Claude added accessible library service and pooled trusts; several other apparent Claude wins were already in a different Codex primary. Trust eligibility was also misstated. Distinct benefit/access mechanisms deserve attention, while counts of organizations or rows obscure them. |
| Domestic Violence | Claude found the temporary survivor phone benefit; Grok found supported forensic access sites and later legal-advice routes. Several sites belong to one forensic pathway, not separate programs. Target entitlement/access gaps and preserve location detail without multiplying identities. |
| Education | The audit found a useful HB144 tuition pathway, overstatement of free program access, an obsolete campus center, and statewide/local branding of the same grant. Claude primary also misattributed a Florida school program to Utah despite contradictory contact evidence. Current geography, enrollment, cost and successor-program checks matter more than list length. Its final Grok challenger also recovered Suazo business education after the 108-lead primary. |

No provider deserves blanket trust or blanket rejection. A sparse provider site
can still have strong government corroboration. A broken page alone proves neither
closure nor invalidity. A directory, eligibility route or accessible intake can
be useful without being an independent direct-service organization.

The challengers were asked to find omissions, not to validate every primary
claim. Adding a challenger therefore does not establish that the primary list
is correct; agreement between models is not source verification either. The
At The Crossroads and Florida-district cases make the separate curation and
verification stage essential under every architecture considered here.

These assignments requested discovery, not complete provider dossiers. Missing
hours or detailed eligibility is not by itself a discovery failure. Incorrect
claims, an unusable service-area assumption, or confusing donations with access
are different. Later curation/enrichment must address Stephanie's four criteria:
eligibility, how best to connect, access (including hours), and important information
to know. This review does not reopen the deferred structured-extraction project.

## Curator burden, duplicates and the missing outcome measures

More rows and longer narratives impose a plausible review cost, but no human
timings were recorded. The audit found ordinary locations split as resources,
cross-category repeated programs, aliases, one-off events, unclear current intake,
an obsolete predecessor, and unsupported service or eligibility claims. Those
are concrete forms of curator work; not every repeated organization is a duplicate
because materially different programs can share an organization or domain.

The production preparation must retain all completed source responses with condition,
role, assignment hash and contribution provenance. Its curation union does not
invent acceptance. Curation should record a final identity and decision reason
for each relevant lead, including merge, incorrect scope, stale, unverifiable,
and accepted. Attribute a challenger contribution only when it adds a materially
new accepted service/program/access pathway beyond that condition's primary;
credit a correction separately from a new identity. Measure curator time and
successful/failed worker time separately.

Then compute:

- accepted unique identities / successful worker elapsed minutes;
- challenger-only accepted identities / challenger successful worker minutes;
- the same measures including failed worker time as an operational sensitivity;
- curator minutes per accepted identity and per challenger-only accepted identity.

For a controlled follow-up, replay different challengers against the **same sealed
primary** and blind the condition during identity decisions. Repeated categories
and other locales are needed before learning performance thresholds. This is a
future evaluation design, not permission to rerun completed work now.

## Alternatives considered

| Architecture | Assessment |
|---|---|
| Codex alone | Fastest plausible option, but observed consequential primary misses make removing the challenger a poor choice. No need to save a few minutes at the expense of the demonstrated checks. |
| Fixed Codex+Grok | Best observed speed baseline, with useful concrete additions. It still missed library, trust and survivor-benefit pathways; raw yield is not a quality guarantee. Use as the core, not as the only available structure. |
| Fixed Codex+Claude | Useful historical benefit/access discoveries, with longer calls and questionable candidates. Prohibited for future work by the cost instruction. |
| Fixed Claude+Grok | Much slower primary and more material to review; Grok still recovered misses. Historical evidence only; future Claude work is prohibited. |
| Codex plus both broad challengers everywhere | Not tested; likely expensive and duplicative. Different fixed-pair results cannot estimate the marginal value of Claude after the actual Codex+Grok union. Reject as the default. |
| Codex with selected scoped Claude work after Grok | Earlier draft option withdrawn after the explicit no-Claude instruction. Do not invoke it, including probes. |
| Codex+Grok with preserved prior findings and explicit pathway checks | Chosen operating policy. Use bounded follow-up only for demonstrated gaps. Measure accepted incremental value before expanding automated routing. |
| Earlier Codex+ChatGPT+Grok+Claude+Perplexity | 412 rows including Claude shadow, versus 473 for the pair; about 298 versus 91 elapsed category minutes. Useful old-only pathways remain. Preserve findings, but the evidence does not justify five broad workers on every category. |
| Scout learns provider/task size from performance | Desirable direction once accepted outcomes and comparable cost data exist. Raw row counts, uncertainty presence, or an unauthenticated timeout are insufficient feedback signals. Do not claim the present explicit policy is a learned router. |
| Recursive challenger partitioning by count/size | Not supported by this incident. Splitting authentication failures only multiplies waiting and recovery. Reconsider after a real authenticated limit, with sealed disjoint scopes, leaf provenance and measured marginal return. |

## Production policy and implementation

Production uses the `codex-grok` profile without a Claude routing policy. Scout
blocks Claude at runner entry, native execution, historical supervisor entry and
production-policy validation. Existing Claude responses remain usable evidence;
reading saved results is not a new assignment. Mocked unit tests may exercise old
formats without executing a provider.

Codex retains focused passes and a gap pass; Grok challenges the actual exclusion
set. Gap checks should cover distinct access mechanisms and provider ecosystems,
including remote/faith/community education, accessible formats, targeted benefits
and population-specific intake. No automatic uncertainty trigger is justified:
all observed leads contain uncertainty text. No failure silently changes providers
or task scope. Diagnose authentication, execution and source problems separately.

Production explicitly requests Codex High and uses a fifteen-minute Grok timeout.
Authenticated Grok calls here fit within that budget. A timeout stops for diagnosis
and does not automatically discard, split or retry an unchanged assignment.

Implementation includes an exclusive per-database lock, resume-safe total-category
caps, explicit Codex effort, missing-counter handling, separate failed/successful
time, and prompt checks for service exclusions, costs, stale events and unsupported
rebrands. Prompt v4 adds explicit checks for distinct benefit/access mechanisms and resolves geographic contradictions rather than inventing local
sites. These are preventive instructions, not verified cures or a rerun of the
experiment.

Production preparation must keep the six completed Codex+Grok jobs unchanged,
retain all old and pairwise submissions in separate provenance-bearing curation
runs, and reuse completed primary passes from the older partial categories.
Sources are opened read-only and fingerprinted afterward. The research monitor
and candidate-union views describe different stages; neither is an accepted list.

Codex High and sandboxed Grok readiness probes previously passed. A Claude probe
also ran before the cost prohibition; it is historical only and must not be
repeated. Final implementation checks and the actual production database are
recorded in the [handoff](st-george-production-handoff-20260918.md). Preparation
success does not itself authorize launching production.

## Reproduction

```bash
python3 scripts/analyze-pairwise-experiment.py \
  data/pairwise-overnight-20260918-022703 \
  --output data/pairwise-review-20260918 --require-complete
python3 scripts/recover-claude-experiment-metrics.py \
  data/pairwise-overnight-20260918-022703 \
  --output data/pairwise-review-20260918/claude-native-metrics.json
```

These tools do not call research workers or write to the experiment databases.
The production preparation command and exact future launch command are recorded
in the final handoff. Do not point production at an experiment database.
