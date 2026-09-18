# Earlier five-worker Scout versus Codex+Grok

Reviewed September 18, 2026, at Extra High. No new research worker was launched.
Claude is disabled for all future Scout work, including probes.

## Judgment

**Codex+Grok is the better operating default, but this evidence does not establish
that it preserves all the useful coverage of the five-worker approach.** It
returned more candidates with much shorter elapsed category windows and a smaller
narrative payload. Nevertheless, the earlier run contains consequential omissions
from the new pair, including EnglishConnect, BYU–Pathway, accessible library
service and the Lifeline survivor benefit. Keep the earlier evidence; replacing
its findings with the pair's list would lose useful information.

This comparison strengthens the case for a focused Codex primary, an independent
Grok challenger, and explicit checks for missing access pathways. It does not
justify five broad workers on every category. Several important old-only finds
came from the earlier **Codex primary**, so they do not demonstrate an exclusive
ability of ChatGPT, Claude or Perplexity. Changed primary execution and ordinary
variation matter substantially.

## What was compared

Read-only sources:

- Earlier five-worker baseline:
  `~/resource-scout-baselines/st-george-20260918-002522/research-agent.sqlite3`,
  SHA-256 `82398c38c15fd4818f4d6d23008bf427adf84caf5d8d9d1fef9ac2f5c394134b`.
- New pair: `data/pairwise-overnight-20260918-022703/codex-grok.sqlite3`,
  SHA-256 `9435f9862e6d6fb95e687a1eab55929264839832da38ccff60eac25fff671089`.

Both have the same six completed categories, empty imported-resource baseline,
category definitions and source-package identity. The import timestamp differs;
after removing only that operational timestamp, their baseline fingerprints match:
`f936df55650dc190afe42765d0e6b8add18588b44f41538f4b37b8c065a978f0`.

The older workflow had Codex primary, ChatGPT/Grok/Perplexity challengers, and
**Claude as a nonblocking shadow**. Its 102 Claude rows live in saved assignment
JSON, outside the canonical manual-run contributions. A comparison using only
that run would count 310 and understate the five-worker evidence. Here all 412
submitted rows are included. No candidate is counted as accepted simply because
it was submitted or appeared in several workers' responses.

## Counts and operational effort

| Category | Earlier main run | Claude shadow | All five submitted rows | Codex+Grok rows | Earlier elapsed min, through shadow | Pair elapsed min |
|---|---:|---:|---:|---:|---:|---:|
| Addiction | 50 | 11 | 61 | 67 | 41.2 | 14.2 |
| Children/Pregnancy | 55 | 25 | 80 | 93 | 55.7 | 14.6 |
| Clothing/Household | 30 | 10 | 40 | 48 | 52.6 | 17.5 |
| Disability | 63 | 17 | 80 | 100 | 51.3 | 15.8 |
| Domestic Violence | 58 | 16 | 74 | 78 | 47.5 | 15.3 |
| Education | 54 | 23 | 77 | 87 | 49.9 | 13.7 |
| **Total** | **310** | **102** | **412** | **473** | **298.3** | **91.1** |

The earlier blocking category windows total 294.4 minutes; waiting for each final
shadow response brings the sum to 298.3. These are sums of per-category windows,
not necessarily one nonoverlapping project clock. The earlier workflow included
browser/manual handoffs and scheduled ChatGPT waits. Thus the roughly 69% shorter
windows are an operational advantage of the tested setup, **not proof that two
models perform the same research 3.3 times faster**. Comparable active worker
minutes, turns, searches, token usage and complete dollar costs were not retained
for the old workflow.

| Worker | Earlier submissions | New pair submissions |
|---|---:|---:|
| Codex primary | 143 | 376 |
| Grok challenger | 66 | 97 |
| ChatGPT challenger | 65 | — |
| Perplexity challenger | 36 | — |
| Claude shadow | 102 | — |

Most of the change is in the primary: 143 to 376 rows. Both used the same named
focused passes and gap pass; even the first sealed Addiction assignment is
byte-identical. This was a fresh primary execution, not the old 143-row primary
with three challengers removed. The saved evidence does not establish identical
execution settings or effort. Do not credit the whole result difference to model
pairing or treat the older challengers' 269 submissions as unique additions.

The pair has 61 more submitted rows (14.8%). Its `whyRelevant` plus `uncertainty`
payload is 28,669 words versus 32,050 (10.5% less); median row length is 59 versus
73 words. This is a reading-payload comparison, not measured curator time. More
rows can still require more identity decisions even when their text is shorter.

## Coverage findings across all six

This is an evidence-based, purposive comparison, not exhaustive blinded curation
or a measured recall percentage. IDs below refer to the source database's manual
lead IDs; `shadow-assignment-ordinal` identifies the separately saved Claude row.

| Category | Comparative finding |
|---|---|
| Addiction | The new pair covers substantially more Medicaid, justice-involved, recovery-housing and peer-support routes. Earlier stand-alone leads include Hand in Hand mobile syringe services (old Grok 31) and Utah Naloxone (old ChatGPT 91; shadow-4-9), absent as named leads in the pair. The pair does cover naloxone and syringe-service directories (18, 27, 31), so these are narrower provider/access-detail differences, not absence of harm reduction. Current local delivery details still need verification. Both runs include questionable At The Crossroads substance-use framing. |
| Children/Pregnancy | The pair has more specific public-benefit, childcare and developmental pathways. The older ChatGPT response retained Millcreek High School's young-parent/childcare route (174), missing from the pair's six-category text. Current school staffing supports a childcare function, while eligibility/hours still need confirmation. Do not confuse it with the old Claude school-clinic claim, whose current operation is unverified. |
| Clothing/Household | Both find the central local closets, school clothing and basic-needs providers. The pair carries BREATHE Care in its primary (167), which required ChatGPT in the older run (210). Operation School Bell appears in four older challenger/shadow responses (186-series Grok 188, Perplexity 193, ChatGPT 208, shadow-12-1); the pair carries one Clothing lead (164). Some apparent omissions are category placement: Cherish Families is in old Clothing shadow-12-2 but is present in the pair's Domestic Violence lead 327, including basic-needs help. Little Lambs is an older indirect lead with unconfirmed southern Utah distribution, not an established local miss. |
| Disability | The pair is broader on named waiver and assistive-technology routes, but misses the accessible library program found by old ChatGPT 236 and shadow-16-10. General library access, equipment lending and disability advocacy do not replace accessible books. Guardianship Associates' training (old ChatGPT 237) is another distinct route to retain for review; the pair's public guardian is a different service. |
| Domestic Violence | Both cover the main shelter, advocacy, legal and forensic routes. The pair preserves more named forensic access locations. However, old **Codex primary 158** already found the Lifeline survivor benefit that the new pair missed. Old ChatGPT also found Give Back a Smile (303), a conditional dental-restoration program absent from the pair. Availability and qualification constraints must remain explicit. |
| Education | The pair adds more technical training and funding detail, including HB144 resident-tuition access (473). Yet it misses **old Codex primary 196 and 197: EnglishConnect and BYU–Pathway**. These remain actionable official programs. The pair's generic immigrant English-class lead 457 neither identifies nor explains these routes. More rows did not preserve two obvious, relevant options for this office. |

### Source checks and limits

- [EnglishConnect enrollment](https://www.englishconnect.org/get-started) confirms
  free beginner levels, group enrollment, and a separate intermediate level.
  [BYU–Pathway admissions](https://www.byupathway.edu/admissions) confirms online
  certificate/degree access with academic, technology and faith-related requirements.
  These are distinct education routes, not aliases for any generic ESL lead.
- [Utah's accessible library](https://blindlibrary.utah.gov/) confirms a free
  braille/talking-book service and a direct application. This supports the
  practical significance of the old library find.
- [USAC's Safe Connections Act page](https://www.usac.org/lifeline/safe-connections-act/)
  confirms a temporary survivor communications benefit, hardship criteria and
  line-separation documentation. It is not unconditional free phone service.
- [Give Back a Smile's application](https://www.givebackasmile.com/apply) provides
  a specific survivor application and qualification screen. This establishes a
  real route to investigate, not guaranteed placement with a nearby dentist.
- [Millcreek's current staff](https://mhs.washk12.org/staff/) lists child-care
  assistants. The old ChatGPT response already marked its detailed nursery rules
  as coming from an older handbook. Current staffing supports retaining the lead;
  it does not verify every old eligibility or schedule claim.
- [Family Healthcare's current locations](https://www.familyhc.org/locations)
  do not list the old Millcreek school clinic. That discrepancy makes the shadow
  clinic claim a verification task, not a confirmed additional provider or proof
  of closure.
- [Cherish Families' current services](https://cherishfamilies.org/what-we-offer)
  include basic needs and housing, consistent with the pair's cross-category lead.
  Do not penalize the pair for missing the organization solely in Clothing.

The earlier ensemble also had duplicates, uncertain local eligibility, dated
sources and program-to-location assumptions. Its several workers did not
independently validate every primary assertion. Conversely, the new pair's
longer candidate list contains repeat access points and uncertain leads. Neither
raw total establishes quality, and neither run has recorded curator acceptance.

## Consequences for Scout

1. Use Codex+Grok as the cost-conscious research core. Claude is prohibited by
   Michael's latest instruction; no probe or fallback may invoke it.
2. Carry forward **all saved evidence**, including the five-worker shadow results
   and all three pairwise conditions, for reconciliation. Preserve source identity
   and distinguish source coverage from accepted uniqueness.
3. Keep category gap checks focused on missing service/access mechanisms, including
   affordable remote and faith/community education, accessible formats, and
   eligibility-specific benefits. Seeing an organization somewhere is not proof
   that each relevant pathway is covered. Avoid hard-coded lists that only pass
   these six known examples or a rule that merely demands more rows.
4. Do not automatically call more providers or recursively split on raw count.
   Use narrow follow-up scope when a consequential gap is demonstrated; the six
   runs do not calibrate an automatic threshold or prove a learned routing policy.
5. Do not rerun these six categories. The older baseline also contains completed
   Employment primary passes and two Financial Assistance passes. Production
   preparation must reuse that saved work rather than silently start those
   categories from scratch.

No accepted-unique count, accepted resources per active minute, marginal accepted
challenger rate, precision/recall percentage or curator-time saving is claimed.
Those require identity decisions and source verification beyond this architecture
review. The old experimental proposal's accepted-union recall target therefore
has not been measured or passed.

## Reproduction

```bash
python3 scripts/compare-five-worker-baseline.py \
  --baseline ~/resource-scout-baselines/st-george-20260918-002522/research-agent.sqlite3 \
  --codex-grok data/pairwise-overnight-20260918-022703/codex-grok.sqlite3 \
  --output data/pairwise-review-20260918
```

This produces `five-worker-comparison.json` and an old-lead export that includes
shadow rows. It opens both source databases read-only and starts no workers.
