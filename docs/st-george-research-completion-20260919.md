# St. George research completion — September 19, 2026

**All 21 categories completed at 2:32:58 a.m. Mountain.** The runner exited
normally. The monitor remains available at http://127.0.0.1:8769 and reports
research complete, ready for Codex-controlled curation. No research worker remains.

## Saved results

The Codex+Grok research jobs contain **1,613 submitted rows**: 1,314 primary and
299 challenger rows. These include the six reused completed categories and ten
reused primary passes; they are not all new overnight work.

The curation selection preserves richer historical evidence for the first six
categories. Across its 21 selected category runs, it contains **3,290 submitted
source rows and 2,421 candidate records**. Candidate records are provisional
consolidation output, not accepted unique resources. Source-only records and
original responses also remain available for review. No curator acceptance or
curator-time metrics have yet been recorded.

The full candidate archive preserves 27 completed runs: the 21 research jobs
plus six richer curation unions. Scout's existing canonical selector chooses the
six unions and the fifteen remaining research runs. Do not sum every archive
version as though it represented additional unique resources.

| Category | Primary rows | Grok rows | Total rows |
|---|---:|---:|---:|
| Addiction | 56 | 11 | 67 |
| Children/Pregnancy | 73 | 20 | 93 |
| Clothing/Household | 40 | 8 | 48 |
| Disability | 79 | 21 | 100 |
| Domestic Violence | 61 | 17 | 78 |
| Education | 67 | 20 | 87 |
| Employment | 37 | 15 | 52 |
| Financial Assistance | 51 | 19 | 70 |
| Reentry Support | 64 | 18 | 82 |
| Food | 49 | 6 | 55 |
| Medical, Dental, Vision | 68 | 10 | 78 |
| Homeless Services | 52 | 11 | 63 |
| Housing | 80 | 11 | 91 |
| ID Recovery | 55 | 16 | 71 |
| Immigration | 51 | 11 | 62 |
| Legal | 80 | 19 | 99 |
| Mental Health | 72 | 18 | 90 |
| Seniors | 75 | 14 | 89 |
| Transportation | 63 | 9 | 72 |
| Utilities, Phone, Internet | 65 | 9 | 74 |
| Veterans | 76 | 16 | 92 |
| **Total** | **1314** | **299** | **1613** |

## Execution and preservation

During the production launches, recorded successful work was 71 Codex calls
(198.85 minutes) and 15 Grok calls (82.09 minutes). These totals exclude the
reused six-category work and ten saved primary passes. One Grok authentication
failure took 0.53 recorded worker minutes, followed by roughly 5 hours 11 minutes
of downtime before sign-in recovery. Research then finished without another
recorded failure. Total launch-to-completion elapsed time was about 9 hours
53 minutes, including that pause. No Claude worker ran in production.

All three experimental databases and the older five-worker baseline retain their
verified preparation hashes. Production SQLite quick_check passed; all 21 jobs,
all primary passes and all 21 challenger assignments are completed. No curation
job exists yet. The monitor's curation counter is 0 of 21.

A frozen database, the complete candidate export, and a checksum/provenance
manifest are saved in `data/st-george-completion-20260919/`:

- `research-completed.sqlite3` — finished database snapshot.
- `st-george-candidates.zip` — full candidate/source archive.
- `completion.json` — hashes, per-category counts, canonical selection and timing.

Production source SHA-256: `86b1efef80d4c087c7e712a1f11aff61107b0ea8721a17828e09cbe67df4d5bb`.
Snapshot SHA-256: `9e058883b1ff95c00128a68038d30b2f3c8ae11f47e1948f55a856635457d4a0`.

## Next stage

Research is finished. Do not restart it or launch another locale. The next stage
is Codex-controlled consolidation/curation across the 21 categories, using the
preserved historical unions and recording candidate dispositions. Resolve the
known source-audit errors and cross-category duplicate identities, and prepare
clear eligibility, contact/intake, access/hours and important-information details
for Stephanie's review. Missing details remain visibly uncertain.

No `autoStGeorge.html` has been generated from this completed run. Generate the
review file after curation; it remains a proposal until human review. Claude
remains disabled, Bonsai removed, and structured extraction deferred.

References: [architecture review](six-category-architecture-review-20260918.md),
[five-worker comparison](five-worker-versus-codex-grok-20260918.md),
[source audit](six-category-source-audit-20260918.md).
