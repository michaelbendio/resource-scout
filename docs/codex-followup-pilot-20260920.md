# Codex complementary-assignment pilot

## Result and recommendation

**A different assignment to the same model produced useful complementary
research. It did not reproduce all of Grok's benefits, and it introduced serious
errors.** Keep this as a viable architecture to develop, especially for a future
single-provider deployment; do not replace the current production architecture
on this two-category result.

The two Codex High workers completed without failure or retry in **6.50 minutes**.
They returned 31 rows. Reviewing every row against the frozen primary and saved
Grok result produced **23 supported additional program/access-pathway leads**.
These are research leads worth carrying into curation, **not accepted resources
or publication-ready records**. Several supported identities need factual
corrections. The same review screened Grok's 31 saved rows as 27 supported
additions, three overlapping/restated rows, and one unresolved lead.

| Category / follow-up | Raw rows | Supported additions beyond primary | Other rows | Worker / assignment minutes | Supported additions per minute |
|---|---:|---:|---:|---:|---:|
| Addiction / new Codex brief | 11 | 7 | 4 | 2.78 | 2.52 |
| Addiction / saved Grok | 11 | 11 | 0 | 4.78 | 2.30 |
| Education / new Codex brief | 20 | 16 | 4 | 3.71 | 4.31 |
| Education / saved Grok | 20 | 16 | 4 | 4.16 | 3.85 |

Historical Grok time is assignment creation-to-completion, including orchestration;
Codex time is measured native worker elapsed. Rates exclude primary research and
review effort, and are descriptive, not a cost-effectiveness verdict. Actual
accepted-resource rates, billed cost and curator minutes remain unavailable.
Judgment calls include merging a hospital department into its existing admission
route, and not awarding discovery credit for a scholarship already named inside
a primary routing entry. Results are sensitive to the chosen program granularity.

Six supported program identities overlap between follow-ups: COMPASS, Church
ARP, Recovery Dharma, Wellbriety, Utah Tech tutoring and its disability center.
Seventeen supported Codex additions were absent from the saved Grok rows; 21
supported Grok additions were absent from the new Codex rows. This is substantial
complementarity, not interchangeability. It does not justify running both
follow-ups for every category without measuring curation cost.

## Consequential findings

- **Addiction:** the new assignment recovered COMPASS and several peer-support
  options, plus the [Calvary recovery ministry](https://www.calvarysg.com/care),
  [SMART online support](https://smartrecovery.org/meeting), and a concrete USARA
  test-strip pickup route. It still missed [Family Healthcare MAT](https://www.familyhc.org/primary-care),
  which Grok had recovered after the same primary. The test does not establish
  whether that repeated miss reflects shared model tendencies, prompt design or
  ordinary search variability.
- **Education:** Codex recovered [EnglishConnect](https://www.byupathway.edu/englishconnect)
  and [BYU-Pathway](https://www.byupathway.edu/admissions), absent from the saved
  Codex–Grok results. It also added prior-learning credit, statewide online school
  enrollment, FAFSA help, and other distinct routes. It did not recover Grok's
  DI training, SCSEP, HB144 tuition waiver or several scholarship pathways.
- **Wrong geography:** four Codex library rows joined a St. George address and
  phone to [Washington County, Virginia's database page](https://www.wcpl.net/learn/databases/).
  A supplemental [Brainfuse source](https://www.washcolibrary.org/node/48) is from
  Hagerstown, Maryland, not an older Utah domain. These entries get no addition
  credit as submitted. This does not prove the software is unavailable in Utah;
  it proves the worker did not establish the claimed Utah access.
- **Outdated eligibility:** the BYU-Pathway identity is useful, but its worker
  description used a legacy page's age/Church-ties rules and cited a test portal.
  The [current admissions page](https://www.byupathway.edu/admissions) gives
  different age and participation rules. A correct discovery can still mislead
  someone about eligibility.
- **Review burden remains on both sides:** Codex also returned an ambiguous
  Renaissance Recovery/Ranch identity and generic/out-of-area routing. Its USARA
  pickup hours came from a [DHHS list](https://opidemic.utah.gov/fentanyl-test-strips/fentanyl-test-strips-distribution/)
  that conflicts with the [host's hours](https://www.utahrecovers.org/locations/stg/).
  Grok's Addict II Athlete meeting time needs correction against its
  [provider schedule](https://www.addicttoathlete.com/supportgroup), and its Liahona
  description must respect the [provider's explicit mental-health rather than
  SUD-facility licensing distinction](https://liahonaacademy.com/). Neither set
  should bypass curation or final review.

## What Scout should learn from this

Treat **assignment diversity** and **provider diversity** as separate choices.
A fresh same-model worker with a different search perspective can add valuable
finds. The present primary already includes a gap pass, so simply adding another
generic request to find more resources is not enough to specify the architecture.

The next design worth testing has three distinct responsibilities: discover the
main services; search missing population/access pathways in a fresh context; then
verify geography, eligibility, current intake and identity conflicts in a separate
evidence review. That review may use the same available model, but it needs a
different task and source evidence, rather than trusting discovery prose.

Both pilot workers used **17 completed web actions**; native events report 45
Addiction and 63 Education search queries. Education's recorded actions were all
searches, with no separately recorded page opens. The stream does not show what
every backend search returned, so this does not prove the worker saw only short
snippets. It does show no auditable explicit full-page verification step.
Future tests should require opening decisive source pages and recording evidence
for actual jurisdiction and eligibility before accepting claims.

Do not tune the next prompt to the provider names exposed by this review and then
score it on the same cases as independent evidence. Use untouched categories,
freeze prompts/budgets in advance, separate same-prompt/model effects where
practical, and measure correction burden as well as marginal useful finds.
Claude-only performance and church hosting/account access remain untested.

## Execution and preservation

Completed September 20, 02:14:50 UTC (September 19, 8:14 p.m. Mountain).
Both calls used `gpt-5.5` at High, fresh ephemeral contexts, public web search and
a read-only sandbox. Neither native stream records local command execution or a
read of held-out answers. One native top-level turn each is **not** comparable to
Grok's internal turn count. Historical Grok tool/turn counters are unavailable.

Native usage reports Addiction 117,607 input / 6,356 output tokens and Education
121,369 input / 9,086 output tokens. These are reported API usage counters, not
context-window sizes or dollar charges. Prompts, results, command lines, event
streams and timing remain in the evidence directory. No Claude call occurred.

All original experiment databases, the five-worker baseline and frozen production
research snapshot retain their prior SHA-256 values. No pilot findings were
imported into production. Production curation continued independently.

Harness verification: **suite passed (256 tests, one skipped)**; focused tests cover
completed-result reuse, paid-attempt non-repetition, changed-input refusal, exact
identity/scope extraction and result validation. A second invocation reused both
saved results without launching a worker.

Every row's assessment, source URLs, reasons, timing and native counters are in
[the machine-readable audit](codex-followup-pilot-results-20260920.json). Supported
means a distinct, source-supported lead merits curation; it is not a finding that
every eligibility, schedule, cost, licensing or safety detail is correct. The
review was not blind, and curator time was not measured.

## Plan sealed before execution

Michael authorized testing whether another, differently scoped assignment to the
same model can supply useful challenger benefits. This is a separate exploratory
pilot, not a change to production or a test of Claude on church infrastructure.

Reuse the completed Codex primary evidence for **Addiction and Education** from
the six-category Codex–Grok condition. Run one fresh-context Codex `gpt-5.5`, High
follow-up per category, with the original category boundaries and identical primary
identity exclusions. The new brief starts from unmet needs and access barriers,
working backwards from intake pathways to providers. Workers receive neither
historical Grok answers nor the source audit/known omissions. Local evidence is
kept outside their assignment folders; prompt restrictions are not an OS security
boundary. Preserve native tool events to check what they actually consulted.

Budget: two sequential calls, 900 seconds maximum each, no automatic retries,
at most 20 leads each. Production curation continues independently at High.
Original databases remain read-only; no pilot discoveries enter production.

Before interpreting totals, review every returned lead against all saved primary
rows and the saved Grok result. Classify as supported additional program/pathway,
duplicate or narrower restatement, unresolved evidence, or unsuitable. Treat a
different program at an existing organization separately when its service and
access route warrant that distinction. Distinguish new organizations from new
programs and useful referral routes. Record consequential omissions and erroneous
claims as well as useful additions. Check current authoritative sources for
decision-relevant claims. These are reviewer assessments, not human acceptance.

Report raw rows, assessed useful additions, overlap with Grok, elapsed worker
time, native turns/tool activity, failures, and evidence/cleanup burden. Report
assessed useful additions per worker minute, not accepted identities per minute;
actual curator time and human acceptance are unavailable. Historical Grok data
may not contain directly comparable tool counters.

Interpretation limits: model and prompt change together; only two previously
examined categories, one execution each; historical timing/source effects and
different stopping rules; production curation may compete for throughput. This
can establish feasibility and suggest better assignments. It cannot establish
equivalence to cross-model challenge or predict Claude-only performance.

Evidence directory: `data/codex-followup-pilot-20260920/`. Its manifest seals the
source database, original assignments, new prompts and schemas by SHA-256.
