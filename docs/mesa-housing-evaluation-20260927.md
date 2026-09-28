# Mesa Housing comparison — September 27, 2026

**Decision: targeted retest before expansion or adoption.** The authorized pilot finished. It found useful material quickly, but this run does not establish a reliable winner or justify replacing the existing primary researcher.

| Measure | DeepSeek existing-policy pilot | Historical primary |
| --- | --- | --- |
| Raw leads, not verified unique resources | 104 | 61 |
| Focused passes + gap pass | 5 + 1 | 5 + 1 |
| Paid API requests in this pilot | 6; all responses preserved | Historical request count not established |
| Active provider processing | 16.75 minutes | Not established from the historical records |
| First dispatch to final response | 23.18 minutes, including recovery/review pauses | Not a comparable processing measure |
| Final bill | Not reconciled | Not established |

The $3 ceiling was removed before dispatch, as Michael instructed. The 60-call, 60-active-minute and retry limits remained. No additional paid retry, fresh Codex control, other-category run, production import or identity-registry update occurred.

## What the source checks show

- **Useful additions:** AHCCCS [H2O](https://www.azahcccs.gov/Resources/Federal/HousingWaiverRequest.html) adds a specific eligibility/referral pathway. [Escobedo phase II](https://www.mesaaz.gov/Resident-Resources/Housing/Project-Based-Voucher-Program) adds a named site within the known Mesa PBV program, not a new provider. The [city confirms Helaman House](https://www.mesaaz.gov/Resident-Resources/Housing/Human-Services/Office-of-Homeless-Solutions), although its detailed intake still needs work. These are bounded findings, not a claim that every new-looking lead is useful or unique.
- **The gap pass helped:** it recovered MesaCAN, The Haven, Foster360 and ARM. Raw counts by pass: 45, 10, 17, 10, 11, 11.
- **A meaningful omission remains:** [one·n·ten housing support](https://onenten.org/lgbtq-programs/housing/) appears in the historical collection and remains publicly offered, but no corresponding lead appears in DeepSeek's final collection. This is housing support for LGBTQ+ youth, not emergency shelter.
- **An incorrect attribution needs correction:** DeepSeek attached Autumn House to Sojourner Center while also listing it under A New Leaf. The [provider identifies it as A New Leaf transitional housing](https://turnanewleaf.org/services/sexual-and-domestic-violence-services/autumn-house/). The affected claims are visibly held; raw output is unchanged.
- **Speculation is not a usable route:** “Covenant House Arizona” was explicitly marked unverified by the model. No Arizona location was established from the [official location list](https://www.covenanthouse.org/homeless-shelters/); it receives no confirmed-resource credit. A missing listing alone does not prove closure or nonexistence.
- **The historical output also needs current checking:** [Family Promise now restricts rental help to eligible program graduates](https://familypromiseaz.org/prevention/). Its historical general-prevention description is too broad today. A website/program change may explain that difference; it is not proof the earlier model was wrong when it researched it.

## Coverage decision

All five frozen essential needs were assessed. Emergency shelter, rent help, vouchers and affordable-housing routes have supported examples with limitations. Supportive housing has useful findings but a known-useful-route miss: one·n·ten. [MesaCAN](https://turnanewleaf.org/services/financial-empowerment/mesacan/mesacan-rent-and-utility-assistance/) has a limited appointment process; [Mesa PBV sites](https://www.mesaaz.gov/Resident-Resources/Housing/Project-Based-Voucher-Program) are referral-only; [HOM](https://www.hominc.com/need-housing-assistance/) does not accept direct assistance applications. Preparation must preserve these access distinctions.

This was an advancement-gate audit of all frozen essential needs and named findings, **not exhaustive vetting of 104 leads or a complete novelty census**. Remaining novelty is unscored. It does not demonstrate reduced Codex review work yet. The supervisor saw the provider and recognized examples; the A/B packet is not claimed to be a blinded evaluation.

## Operational and cost findings

Three responses used JSON/source-note wrappers that the initial adapter rejected. Tested parser corrections retained the original lead objects and source notes, then adopted the saved responses without another paid request. Recovery snapshots and code amendments remain in the local evidence directory.

The four-successful-native-search allowance was exhausted. Raw native usage reports 46 search requests, including limit errors; those are not all successful searches. A focused follow-up should test a larger declared search allowance and source-backed provider/program attribution using the same original inputs, without supplying expected missing-provider names. No follow-up has been launched.

Observed token arithmetic at the published [DeepSeek rates](https://api-docs.deepseek.com/quick_start/pricing/) is **$0.144 off-peak / $0.288 peak**, assuming disjoint uncached/cached counters and excluding any separate search charge. **This is a token-only illustration, not the bill.** Native billing remains unreconciled; ledger nulls mean unknown, not free. No account-wide balance movement is attributed to this test.

Preparation, review and global reconciliation costs remain unmeasured. A complete-office dollar/time saving cannot be calculated honestly from this pilot alone.

## Evidence and reproducibility

Local experiment: `data/evaluations/mesa-housing-existing-policy-20260927/` in the isolated implementation checkout. It contains the sealed original-input hashes, original raw import reconstruction, protocol/authorization, six requests/responses, source notes, ledger, scratch database, recovery amendments, A/B packet, dated judgments/corrections, actuals CSV/JSON and initial projection. The original package content and original known-resource manifest matched; original ZIP container bytes were unavailable and are not claimed recovered. Historical model/settings remain unknown where not recorded.

Implementation checks: 49 evaluation tests; the earlier 25 affected existing tests also passed. No production defaults or human resource decisions changed.
