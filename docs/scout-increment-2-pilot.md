# Increment 2: real Provo pilot

September 5, 2026, America/Denver. Some service evidence dates are September 6
UTC. This is a research and review pilot, not a production package release.

Michael authorized the historical input explicitly: "It's not current but use
it anyway. It will still be useful." The original ZIP remains unchanged:

- Source: `~/Downloads/provo-resource-package-4.zip`
- Package version 41, created August 12, 2026
- SHA-256: `dc883d19eff7a30e78d33df580ea8408a50788eade33647c40ec6a23f0201a49`
- Explicit office identity: Provo TSO; `historical=True`
- Isolated database: `output/provo-improvement-pilot/pilot.sqlite3`, project 1

## Michael's pilot acceptance

After reviewing the pilot, Michael said:

> The text changes were good. And I agreed with Scout's decisions of what to keep from the other AIs.

This accepts the three writing proposals and Scout's reconciliation choices,
including its decisions to preserve local knowledge, reject unsupported audit
suggestions and leave genuine conflicts visible. It supplies positive human
feedback on the pilot's writing and research judgment. No rewriting or repeat
research is needed solely to obtain that approval again.

It does not establish answers to the provider questions Scout left unresolved,
confirm corrected contact fields or attachments, or identify a current office
package for a production merge. Per-resource Curated decisions and export gates
remain in place. The historical review HTML remains a snapshot of what Michael
reviewed; a separate local `pilot-acceptance.json` binds his feedback to the
review-copy and proposal hashes. No research lesson is automatically activated.

## Scope and actual research

| Existing resource | Stable ID | Audit findings |
| --- | --- | ---: |
| Utah Food Bank - Commodity Supplemental Food Program | `83cef4c7ca6a62e9bf4ab6d694f78bd9` | 6 |
| Provo City Housing Authority | `provo-city-housing-authority` | 8 |
| Community Actions Services - Financial Literacy Classes | `4e2aee885b2126ae255d187c8496758b` | 3 |

Codex researched current official sources, prepared three writing proposals,
and visually read all six pages in the four scanned housing PDFs. ChatGPT,
Grok and Perplexity each received a separate packet containing all three exact
sealed assignments through their actual signed-in consumer browser services.
All nine audits returned, and Codex reconciled all 17 findings. These are real
service results, not synthetic QA responses or substitute Codex agents.

The independent audit threads are:

- [ChatGPT](https://chatgpt.com/c/6a9ce282-a568-83e8-8d57-d0a9f904f2a9)
- [Grok](https://grok.com/c/6b5cd946-fb01-452b-ad2a-5691ea242504)
- [Perplexity](https://www.perplexity.ai/search/d7d48d75-8293-4309-8c53-d4ebf3523838)

The external auditors received explicitly labeled Codex observations about the
scanned PDFs, **not the original PDF binaries**. Their checks therefore do not
constitute independent visual attachment verification. All three services
recorded this limitation. No organization, provider or client was contacted.
Original `verifiedOn` values are preserved; no new human verification is claimed.

## What the extra research added

For CSFP, ChatGPT caught the 10-day deadline to report household income/member
changes. Grok and Perplexity pointed out additional application submission
routes. Perplexity found an official page still stating a 130% poverty limit.
Codex resolved that discrepancy against the explicit 150% rule in the dated
2026 application and 2026 state plan, also supported by the main program page.
The earlier application-process page remains in the evidence rather than being
silently discarded. The state plan also supplied the nursing-home exclusion and
the distinction between yearly eligibility checks and formal recertification.

Sources: [CSFP overview](https://www.utahfoodbank.org/how-we-help/csfp/),
[2026 application](https://www.utahfoodbank.org/how-we-help/csfp/csfp-application-english-2026/),
[2026 state plan](https://www.utahfoodbank.org/how-we-help/csfp/csfp-state-plan/),
[conflicting application-process page](https://www.utahfoodbank.org/how-we-help/csfp/csfp-application-process/).

For housing, ChatGPT supplied a more useful FSS referral route and flagged
citizenship/immigration screening, including reduced assistance for some
mixed-status households. Grok and Perplexity independently found a consequential
conflict: the voucher page states restrictions on advancement for nonresidents
and single adults who are neither elderly nor disabled, while the application
page describes a living/working preference and the original local record says
willingness to move is sufficient. The revised writing makes the conflict
visible and asks staff to confirm the specific program. It does not pick a
winner by AI vote. Local criminal-screening language also needs confirmation.

Sources: [application page](https://provohousing.org/apply/),
[voucher page](https://provohousing.org/programs/vouchers/),
[FSS route](https://provohousing.org/programs/family-self-sufficiency-fss/),
[HUD verification guidance](https://www.hud.gov/sites/dfiles/PIH/documents/PHA-Letter-on-Citizenship-and-Immigration-Status-Verification.pdf).

For financial classes, Perplexity's search extract did not show individual
coaching. Codex rejected the proposed downgrade because the directly opened
current program page explicitly offers it; ChatGPT and Grok confirmed it too.
Free classes, languages, childcare and refreshments were retained from local
knowledge with practical confirmation wording. Website silence did not erase
them. [Current Financial Learning page](https://communityactionprovo.org/get-help/education-and-support/financial-learning.html).

## Review issues that writing alone cannot finish

- The CSFP dedicated address has `90 S.`; the official distribution-center
  address is `900 S.`. Its displayed office is not necessarily the person's
  assigned pickup location. The correction is prominently flagged.
- Financial Learning's dedicated website needs a redirect/currency check or
  manual correction. The proposed Information supplies the current full URL.
- Housing's Rent Limits attachment includes figures dated April 2025 that differ
  from the current site. The PDF named Government Subsidized Housing actually
  contains a March 2026 rental-contact list; the Information PDF contains the
  program guide. All originals are preserved, with review needed before handout
  distribution.
- The housing residency/household-type conflict and local criminal-screening
  rule still need provider clarification. Historical FSS flyer work/benefit
  conditions are retained as questions for the coordinator, not silently lost.

Every record remains unmarked. Six audit resolutions remain `needs-review`,
including four material findings. Material findings require human resolution
before acceptance/export; the separate source-address warning also needs review.
No selected record, contact field, category, group, Type, verification date or PDF
was changed in an office package. No update package was exported.

## Artifacts and fidelity checks

All pilot artifacts are under `output/provo-improvement-pilot/`:

- `autoProvoPilot.html`: standalone read-only iPad review, original/proposed
  writing, source links, findings and reconciliation decisions, draft printing.
- `pilot.sqlite3`, `review-snapshot.json`, `events.json`: durable project and
  audit history. The historical source ZIP bytes are stored in the database.
- `primary-*.assignment.json`, `primary-*.result.json`, each consumer's packet,
  raw/submitted results, and `reconcile-*.assignment.json` / `*.result.json`.
- `pilot-progress.json`: service-thread URLs, actual coverage and raw-result
  hashes. `transport-normalizations.json`: explicit import adaptations.
- `review-browser-checks.json` and `review-*.png`: generated review verification.

The review HTML was copied to iCloud Drive `Documents/TSO/autoProvoPilot.html`
and verified byte-for-byte on the Mac. This does not prove it has synchronized
to the iPad. Once available there, use the TSO viewer's Switch control as with
the earlier writing pilot. It is a read-only comparison, not the durable Curated
review interface.

Consumer findings sometimes named a section instead of its parent package
field. Those section locations were mapped to `informationText` for import.
Perplexity's outside-scope website finding was retained with an explicit
dedicated-website prefix and a pending human resolution. IDs, assignment hashes,
severity, evidence and finding substance were preserved. Exact original outputs
remain separately saved; normalized imports are not mislabeled as raw responses.
The assignment instructions should make the allowed field names clearer in a
later refinement.

ChatGPT and Grok results were downloaded as JSON. Perplexity's PDF export clipped
long JSON lines, so it was not used to reconstruct missing text. Its actual code
block was copied through the UI and saved as plain text, then parsed as JSON.
The clipped PDF remains only as a transport diagnostic, not authoritative output.

Checks confirmed all 15 research stages completed, all three original/current
records equal their source records, the source SHA unchanged, and all four PDF
byte hashes preserved. Zero Curated decisions and zero packaged resources remain.
The standalone page passed checks at iPad and phone widths, five exact headings
per proposal, resource selection, no horizontal overflow, selected-resource
print visibility and no JavaScript errors. All three iPad views and print-media
layout were visually inspected. Printed pagination and real iPad synchronization
have not been claimed as tested.

The pilot also exposed a dispatch need: `improve next --resource-id` now allows
selecting a pending assignment without bypassing stage gates, altering sealed
assignments or expanding project scope. Fourteen focused workflow tests pass,
including this dispatch behavior. Earlier full-suite/browser package-merge QA
remains described in the increment results; no production merge was performed.

## Next discussion after acceptance

Michael approved the writing and reconciliation choices. The useful lesson is
that other AIs can contribute missing details and expose conflicts, while Scout
still needs to judge their evidence; accepting every suggestion would have
removed a supported coaching service. Preserve this evidence-based approach for
classification as well.

Remaining operational discussion concerns the effort required to resolve genuine
conflicts and how to handle contact/attachment corrections adjacent to writing.
Independent attachment access and strict consumer result formatting also deserve
a small operational refinement. These are distinct from the accepted text.

The grand plan remains better writing, safe existing-resource improvements,
classification, maintenance, proposed research lessons and adaptive research
runs. The next planned increment is categories, category-specific Types and
groups. Plan it from the accepted pilot experience; discuss that implementation
before beginning it.
