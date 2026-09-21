# DeepSeek challenger comparison — September 21, 2026

**DeepSeek V4.1-Flash is promising for inexpensive supplementary discovery. It did
not meet this trial's predeclared coverage-preservation gate for replacing Grok.**
It produced more useful candidate pathways, but substantially different coverage.
No production integration or replacement has been made.

Three completed DeepSeek runs cost an estimated **$0.2575** in model usage.
At 23:32 UTC, the account displayed **$7.29**, down $0.25 from $7.54; displayed
balances round to cents and billing lagged during the run. Search, supervision,
and this audit used the Codex session and are **not included** in that API figure.

## Results

| Category | Grok / DeepSeek submitted | Useful Grok / DeepSeek pathways | Grok pathways recovered | Additional DeepSeek pathways |
| --- | ---: | ---: | ---: | ---: |
| Housing | 16 / 24 | 15 / 21 | 6 / 15 (40%) | 15 |
| Employment | 16 / 27 | 14 / 22 | 5 / 14 (36%) | 17 |
| Disability | 22 / 35 | 14 / 34 | 3 / 14 (21%) | 31 |
| Total | 54 / 86 | 43 / 77 | **14 / 43 (32.6%)** | **63** |

The replacement threshold was at least 80% recovery of verified useful Grok
additions, plus useful independent findings and acceptable error behavior. The
recovery condition failed. Conversely, Grok's saved results contain only 14 of
DeepSeek's 77 useful pathways. This asymmetric reference test is **not evidence
that Grok is generally better**, nor that either result is complete ground truth.
Their combined set contains 106 useful category-level pathways: 14 shared,
29 Grok-only, and 63 DeepSeek-only.

Counts represent distinct services within each Category, not globally deduplicated
resources or human Curated approvals. A program-specific eligibility or delivery
route can add useful coverage beyond a generic primary directory without adding
a new organization. Useful-with-correction entries count as promising candidates;
they are not ready to publish. Navigation-only entries and repeated primary
services are excluded from the strict score.

## What the different coverage means

DeepSeek's independent Housing additions include emergency pet boarding through
RedRover, youth vouchers, senior housing, recovery residences and reentry housing.
Its Employment additions include remote veteran/immigrant coaching, staffing
agencies, peer-support certification and documentation fee waivers. Disability
adds accessible books and calls, disease-specific support, specialist clinics,
inclusive schools, dental assistance, arts and veteran benefits.

Consequential Grok findings not recovered include:

- Housing: REACH, Ballington, Columbus residential services, West Valley repairs,
  weatherization, and additional affordable-homeownership pathways.
- Employment: UCA workforce development, Year Up, SLCC truck driving, disability
  state hiring/internships, UCAT, blindness-specific employment and Project Read.
- Disability: Medicaid personal-care/waiver detail, caregiver compensation and
  self-administered supports, Neighborhood House adult day care, hearing/vision
  infant services, DHH employment and hospital adaptive-care support.

These are meaningful differences in beneficiary access. More leads alone do not
demonstrate that an existing challenger's contribution has been preserved. The
Disability results particularly favor new specialist organizations over expansion
of already-known public systems; that is a useful complement, not equivalent
coverage. This is an interpretation of these three samples, not a stable model trait.

## Verification findings

The audit checked both sets against the sealed original Codex primary evidence and
live provider/government sources. Every submitted lead has a decision, reason,
source URL and original submission in the [machine-readable audit](deepseek-challenger-comparison-20260921.json).

Two DeepSeek submissions failed substantive checks: Friendship Manor's website
belongs to an Illinois provider, while the Salt Lake property's current site is
[Friendship Manor on Tamarack](https://friendship.tamarackpm.com/); Splore was
claimed to be independent of the already-listed National Ability Center, whose
[official history records their 2017 merger](https://new.discovernac.org/discover/).
The Salt Lake housing candidate remains salvageable; the submitted website is not.

Other accepted candidates need corrections. Examples include a conflicting
Manpower street address, Jordan Valley school ages, and bundled VA benefits with
different eligibility rules. Both providers also repeated primary services or
used details needing intake confirmation. The saved Grok personal-care benefit
was supported by an official archived manual, but its cited March 2026 PDF could
not be reopened independently; current terms remain unverified. No phone calls,
vacancy checks, or human approval were performed.

## Cost, timing and reliability

| Category | DeepSeek API estimate | DeepSeek wall / API streaming minutes | Saved Grok wall minutes / reported cost |
| --- | ---: | ---: | ---: |
| Housing | $0.0971 | 12.56 / 7.70 | 6.31 / $0.9720 |
| Employment | $0.0789 | 17.81 / 6.02 | 7.38 / $1.2316 |
| Disability | $0.0815 | 11.44 / 6.19 | 5.76 / $0.7893 |
| Total | **$0.2575** | **41.81 / 19.91** | **19.46 / $2.9928** |

Token estimates use the verified [official DeepSeek Flash pricing](https://api-docs.deepseek.com/quick_start/pricing):
off-peak input cache hit $0.003, input miss $0.15, output $0.60 per million tokens.
All 60 calls ran during the applicable off-peak UTC period. Cached multi-turn
input contributes to the low price. The conservative peak-price budget ledger
total is $0.5151; no second model or paid search API was purchased.

Grok cost is historical CLI telemetry for `grok-4.6-build`, not a new charge or
measured subscription debit. The roughly 12-fold difference between these model
figures is not a complete operating-cost comparison. At the observed average of
about 8.6 cents per category, $7.29 would fund roughly 85 similar model runs
arithmetically, but prompt size, caching, search costs and quality vary; this is
neither a production estimate nor authorization to spend the remaining balance.

DeepSeek wall time includes polling, manual tool relay, web latency and recovery.
Employment alone spent 11.79 minutes outside API streaming. These figures do not
establish intrinsic model speed or the runtime of an automated production adapter.

There were **zero failed provider calls and one malformed web-tool argument**
(Disability turn 13). The original event was preserved; the supervisor returned a
validation error, executed the other valid request and continued at turn 14.
There was no category restart or unchanged paid retry. All three final responses
passed the existing lead schema. The spend guard was strengthened after observed
billing lag to reserve against accumulated peak-rate usage as well as account
balance; prompts, model settings and tool responses were unchanged.

## Experimental limits and operational finish

DeepSeek received each original sealed challenger assignment and primary evidence,
with only the provider name changed, through the existing research-prompt wrapper.
It did not receive Grok answers. Model: `deepseek-flash`, verified V4.1-Flash alias;
thinking enabled and explicit `reasoning_effort=max`. The supervisor relayed
model-selected searches and page reads through the Codex web tool unchanged.
This is a historical same-day comparison of different research setups, one sample
per Category, not a randomized model-only benchmark.

Review packets shuffled provider labels and froze decisions before opening the
mapping. The same supervisor operated and reviewed the test; writing style could
reveal a provider. This was not independent, double-blind, or human curation.

All paid work is stopped. Read-only row hashes verify **every production table
unchanged**, SQLite quick_check is OK, no research coordinator or curation worker
is running, and both current monitors respond. Welfare Square retains 21 completed
primary Categories / 112 passes, 16 saved Grok results, five pending challengers
and zero curation jobs. Runtime remains `paused-by-user`, automatic restart off.

The isolated script has seven passing budget/schema tests. Native events, exact
requests, tool responses, costs, frozen packets and production snapshots are
preserved under `data/deepseek-challenger-trial-20260921/` (ignored by git).
No credentials are saved in the trial artifacts. This report, public lead audit,
bounded harness and its tests are retained in the repository. A further run or
production change requires Michael's next decision.
