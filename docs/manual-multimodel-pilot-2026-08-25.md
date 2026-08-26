# Manual multi-model discovery pilot

Status: in progress. The real Addiction contribution set has been replayed through
the version 0.31.2 manual-discovery endpoints in an isolated branch database. The
Food run is prepared but has no responses. Michael has not yet approved the
practical workload or candidate presentation, so this is not a production-cutover
record.

## Isolation and preserved inputs

- Development branch: `manual-multimodel-discovery`
- Pilot database: ignored branch-local data; not the production Scout database
- Source package SHA-256:
  `c7a2251d7d638472f90207c24a28ec71c24515ea5d1aafced68a38fdce3d30f8`
- Frozen DeepSeek baseline SHA-256:
  `0914c6278d36177cc29d75b297249815386355ceb9d634b1ac23372aa18c5491`
- Preserved DeepSeek Addiction Curator SHA-256:
  `44fdaf15d2a7803fbf2df80f44356bd5ef6596180bf3a6b0ac73f5e94cad0cde`

No model, search service, API, credential, or metered fallback was used during
the replay. Production Scout and its normal local-Qwen service were not stopped,
redirected, or written by the pilot.

The exact response hashes are:

| Source label | SHA-256 |
|---|---|
| ChatGPT | `9cc12da303a2b19fb35b9d017a06787733b3d2e136397dc05732cbb96c700af6` |
| Grok | `9bd82d3a1383c3aebc72827ed49fe8b3edb4e6335edc980097514625e358bd98` |
| Claude | `ecf1c9d9fec763a2f5ea5689ec2146a0fe1338602a492d8d0c52f5601d1c319f` |
| Perplexity | `ccc74055525d7290751e3107614e552be00bc9038140ba02f5490f6cec4bb9eb` |

The contribution-set receipt is
`50f58904b1cedd81611b537715a48953e41834d86d331cdb9f3adb6ac301c6d5`.
Raw responses remain outside the repository; the repository retains only the
reduced deterministic fixtures and this receipt.

## Addiction replay

| Measure | Result |
|---|---:|
| ChatGPT rows | 53 |
| Grok rows | 72 |
| Claude rows | 89 |
| Perplexity rows | 41 |
| Submitted and parsed rows | 255 |
| Exact repeated rows collapsed | 66 |
| Conservative identities before human decisions | 189 |
| Provider/program identities | 150 |
| Access-point identities | 9 |
| Routing sources/directories | 30 |
| Ambiguous identity pairs | 72 |
| Direct candidate identities before decisions | 159 |

All 255 rows parsed. Perplexity retained one parser warning and 3,214 characters
of trailing source text; the other three inputs had no parser warning. The
consolidation kept 108 direct candidate identities represented by only one
source, 43 represented by two, seven represented by three, and one represented
by all four. Those counts describe submitted overlap, not truth or verification.

The lightweight checks marked all identities, submitted geography, and submitted
category relevance present. Fifty-two direct candidates still have an uncertain
current-status signal and 56 have an uncertain public-access signal. Those states
remain visible and do not exclude the lead.

The 72 pair prompts exposed an impractical click-and-redraw path. Version 0.31.2
therefore adds an atomic **Leave all pending pairs unresolved** action. It keeps
the identities separate, records rather than hides uncertainty, and leaves every
decision individually editable before finish. It never treats source agreement
as verification or performs a bulk merge.

## Preserved DeepSeek comparison boundary

The preserved DeepSeek Addiction Curator contains 25 candidates. The earlier
human-reviewed comparison found 17 substantively similar services in the four-chat
set, four additional parent or related organization leads, and four omissions:
Banner Poison & Drug Information Center, Calvary Healing Center, Oxford House,
and Hushabye Nursery. This comparison is intentionally not recomputed from a
looser name or URL heuristic; the historical human boundary remains the accepted
comparison receipt.

The manual set is much broader than the DeepSeek candidate list, but 159 direct
identities are not 159 verified resources. They include aliases, parent/program
relationships, several programs sharing one organization page, uncertain access,
and single-source leads. The pilot must not present this number as superior yield
or send the entire set to Resource Specialists without Michael reviewing the
workload and presentation.

## Remaining Stage 5 gates

- Review the real Addiction identity presentation in the pilot app.
- Make selective same/separate decisions where they materially reduce duplicate
  Curator work; unresolved is acceptable when the evidence is insufficient.
- Decide whether the resulting Curator candidate volume is practical.
- Collect ChatGPT, Grok, Claude, and Perplexity responses for the prepared Food
  assignment and import them through the same workspace.
- Record actual human handling time for at least one manually operated category.
- Export and inspect both Curators, including source-only records and provenance.
- Obtain Michael's approval before production becomes dependent on the workflow.

Stage 6 legacy intake, retirement decisions, and production cutover remain gated
on this pilot. No legacy Curator has been imported and no historical factual
claim has been promoted to current evidence.
