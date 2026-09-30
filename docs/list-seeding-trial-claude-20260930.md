# List-seeding trial, all Mesa categories — Claude, 30 September 2026

Done by Claude at Michael's request ("Go ahead and do it too"), following
[the brief](list-seeding-trial-brief-20260930.md), alongside Codex's run of the same brief.
Five research agents took four categories each; Food is Claude's earlier trial. Data:
[`list-seeding-trial-claude-20260930/`](list-seeding-trial-claude-20260930/), one JSON file
per category, plus the matching tool and the judging sample.

## The answer

**An office's own lists, filtered by the four office-fit rules, give a shortlist of the
right size: a median of 13 per category (2 to 22).** Scout's complete Mesa delivery already
had **85%** of those shortlisted names (224 of 265), buried among 3,998 usable category
memberships: the shortlist is about **6%** of what Scout prepared. Lists do not find much
that Scout misses; they **pick out** the core from what Scout finds.

Whether the shortlist is *good* is the open question. It needs Michael's judgement of the
sample below.

## By category

| Category | Lists | Names | Pass rules | Scout had | Scout lacked | Pass and Scout had | Pass, Scout lacked | Scout usable |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Addiction | 7 | 34 | 16 | 28 | 6 | 16 | 0 | 188 |
| Children/Pregnancy | 6 | 38 | 16 | 19 | 18 | 10 | 6 | 228 |
| Clothing/Household | 9 | 18 | 5 | 15 | 1 | 4 | 1 | 137 |
| Disability | 5 | 31 | 17 | 19 | 10 | 14 | 3 | 231 |
| Domestic Violence | 7 | 31 | 19 | 26 | 5 | 18 | 1 | 107 |
| Education | 6 | 27 | 8 | 14 | 12 | 5 | 3 | 272 |
| Employment | 6 | 31 | 13 | 24 | 7 | 11 | 2 | 324 |
| Financial Assistance | 6 | 30 | 6 | 21 | 5 | 6 | 0 | 250 |
| Food | 4 | 22 | 22 | 17 | 5 | 17 | 5 | 155 |
| Homeless Services | 9 | 35 | 14 | 30 | 2 | 14 | 0 | 171 |
| Housing | 6 | 36 | 12 | 20 | 11 | 9 | 3 | 315 |
| ID Recovery | 4 | 4 | 2 | 4 | 0 | 2 | 0 | 81 |
| Immigration | 5 | 28 | 8 | 16 | 8 | 7 | 1 | 88 |
| Legal | 6 | 55 | 21 | 35 | 16 | 19 | 2 | 214 |
| Medical, Dental, Vision | 9 | 38 | 18 | 30 | 8 | 14 | 4 | 266 |
| Mental Health | 6 | 34 | 21 | 25 | 8 | 16 | 5 | 276 |
| Reentry Support | 6 | 28 | 6 | 19 | 6 | 5 | 1 | 133 |
| Seniors | 7 | 25 | 6 | 19 | 5 | 6 | 0 | 126 |
| Transportation | 7 | 33 | 8 | 22 | 8 | 7 | 1 | 167 |
| Utilities, Phone, Internet | 7 | 26 | 8 | 21 | 2 | 8 | 0 | 131 |
| Veterans | 5 | 38 | 19 | 25 | 9 | 16 | 3 | 138 |
| **Total** | **133** | **642** | **265** | **449** | **152** | **224** | **41** | **3,998** |

"Scout had" means in this category; another 41 names were in Scout under a different
category. Of the 133 lists, 53 were official (City, County, State), 32 were 211 Arizona
searches, 26 were regional networks, and 22 were aggregator directories. The rules were
applied to what each listing alone shows: 265 pass, 187 fail, 190 are unclear. **Main
service** was the most common failure (90), then reach (40), one entry per agency (30) and
direct contact (26).

## Where lists are thin or wrong

- **Thin:** ID recovery (no official list at all), reentry (no Mesa or East Valley list),
  immigration (one Mesa provider), vision (no list names a Mesa provider), seniors (no
  Mesa-wide list), children's education (none), furniture, and phone and internet help.
- **Stale:** Mesa's own homeless-resources page and the regional sheet still send people to
  SAFEDVS, reported closed on 15 May 2026. The state dental list is from 2013. One
  aggregator still lists pandemic rental aid.
- **Phoenix-heavy:** 211 Arizona's results for Mesa lean to Phoenix and statewide entries,
  which is why so many names are "unclear" on reach.
- **Unreadable:** many official pages refuse automated reading (403): findhelp, Valley
  Metro, DES, Mesa Public Library, ARIZONA@WORK's resource page, the state refugee and
  corrections reentry pages.

## What it means for Scout

1. **Seed from the office's lists and the rules**: about 13 names a category.
2. **Search narrowly for gaps**, need by need. In the Food trial, two of Michael's four
   "would hand out" resources were on no list (Fountain of Life's Mission Kitchen 153;
   Chandler-Gilbert Community College's Coyote Cupboard in Mesa), and the thin categories
   above depend on search entirely.
3. **Curate and review only those**, about 20 to 30 a category rather than 150.
4. **Check list entries against the provider's own page**; lists go stale.

## Caveats

- The matching tool (`scout_match.py`) produced many false matches; the agents corrected
  about 90 by hand, noted in each file. Some "Scout had" matches are the right agency but a
  different programme. Counts are approximate.
- Some agents shared a scratch folder and overwrote each other's working files; the
  affected agent rebuilt its four files, and every file here parses and is complete.
- The rules were judged from listing text only, not researched.

## Judging sample for Michael

Ten names chosen at random from the **shortlist** (those passing the rules) in five
categories, or all of them where there were fewer: `judging-sample.json`. His verdicts
("would hand out" or not) measure the shortlist's precision directly.
