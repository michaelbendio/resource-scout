# LSScout: list-seeding Scout

Concept as of 4 October 2026, for the TSO managers' meeting of 5 October. The 30 September
trial that started it is kept below as the evidence.

## Why

Running Scout on Claude is not viable (Michael, 3 October 2026): a Claude Scout run for
one category of one office cost about $450 at API prices, and most of the cost goes on
curating and reviewing a very wide net (Mesa: 1,867 prepared resources, of which Michael
would hand out about one in five). **LSScout** replaces it. It starts from the lists local
people already keep and checks a short list carefully, instead of researching broadly and
filtering afterwards. The goal is the same: about 10 to 30 resources a category that a
missionary would hand out. For now it is called LSScout to avoid confusion; the plan is to
call it simply Scout.

## How it works

1. **Find the office's lists.** For each of the 21 categories, 3 to 5 lists of local
   providers, preferring official ones (city, county, state), then 211, then regional
   networks (food-bank partners, legal-aid referral lists, aging agencies), then
   aggregator directories only where those are thin. Some official directories cover
   many categories at once (Clark County's Royal Pages, Washington County's health
   department sheet, Salt Lake's 211 resource list). The lists are saved per office in
   [`office-lists/`](../office-lists/), and state and national ones once for everyone.
2. **Collect every name the lists give.** All of them, not a sample: a county pantry list
   of 57 gives 57 names. Merge the same agency at the same address.
3. **Apply the four office-fit rules** ([office-fit-rules](office-fit-rules-20260928.md)):
   reachable from the office (phone and online count), the category is its main service,
   a person can contact it directly, one entry per agency.
4. **Check each one that passes on a real page.** The provider's own page, or where it has
   none or it will not load, an official or 211 entry giving its phone and address.
   Record the page. **No page read, no pass.** Never take a phone, address or hours from
   a search snippet. A name no list gave is left out, however good it looks.
5. **Write the candidate from the provider's pages**: the five template sections
   (Services Offered, Eligibility Requirements, Population Served, How to Best Connect,
   Important Information to Know) and a one-sentence summary. Every statement comes from
   a page read.
6. **Choose Types and For groups from a standard vocabulary**, never invent them (see
   below). A For group is tagged only when the provider's page names it or the service
   is designed for it, with the phrase that justified it recorded. When no Type fits,
   leave it blank and note what it would have been called; that note is how the
   vocabulary grows, reviewed by a person.
7. **Load into WSRS-TSO as unreviewed candidates**, where an office curator reviews and
   curates them as with Scout's. Until curated they print only with the warning "Not yet
   reviewed by the office. Call the provider to verify this information."
8. **Re-read the lists every month or two.** A new name is a lead; a name that drops off
   may be a closure. A few page reads, not a run.

## The standard vocabulary

Michael's idea (3 October 2026): instead of inferring Types and For groups office by
office, LSScout chooses from one standard set, with more Types per category than any
office needs and a very large set of For groups.

- **Start from what Scout already wrote**: Mesa's 263 Types and 25 groups, Welfare
  Square's 323 Types and 56 groups, all with definitions, plus Provo's and Albuquerque's
  own. Merged and de-duplicated, roughly 15 to 25 Types a category and 60-odd groups.
- **Definitions matter more than the list's size.** Scout's say what does not count
  ("Other uses of the word survivor do not qualify"), which keeps a large group list from
  being over-tagged.
- **WSRS-TSO needs no change.** An office's Types and groups are created only when a
  resource that uses them is curated, so a big vocabulary never clutters an office.
- One vocabulary across offices also makes cross-office reporting possible.

## What it has produced so far

Demo offices in production, 3 and 4 October 2026, pure list seeding with no Scout data:

| Office | Candidates | Notes |
| --- | --- | --- |
| Mesa (list-seeding) | 230 | Food's 20 written up in full (steps 5 and 6); 19 marked curated for the demo |
| Ogden (list-seeding) | 148 | Steps 1 to 4 only |
| St. George (list-seeding) | 161 | Steps 1 to 4 only |
| Las Vegas (list-seeding) | 283 | Steps 1 to 4; food 56 from Clark County's 57-pantry list |
| Welfare Square (list-seeding) | in progress | |

An office takes about 15 to 30 minutes with three research agents on Claude Sonnet.

## Quality: the first test

Ten Mesa food providers that both Scout and LSScout had, written up by each and shown to
Michael blind, side by side: **Scout better 6, about the same 4, LSScout better 0**
(`~/scout-claude/lsscout-trial-mesa-food/RESULT.md`). LSScout did not yet match Scout. Its
writing and length were equal; it lost on three things, all fixable:

- **Eligibility.** 4 of 10 said "None stated; call to confirm" where Scout found photo ID,
  proof of address and visit limits. LSScout read 2 to 4 pages a provider; it needs to
  look for eligibility, what to bring and visit limits specifically.
- **The whole agency.** The trial held LSScout to the food category. Scout files a
  provider under every category it serves (Paz de Cristo: 7 categories, 18 Types).
- **Other programmes.** Scout caught a monthly community dinner LSScout missed.

The next round repeats the comparison with those three fixed, on Sonnet first and then on
Opus if needed, to learn whether the gap is the method or the model.

## What was learned building it

- **Depth must be asked for.** The first Las Vegas pass recorded 4 to 10 names a category
  and 50 passes; told to record every name, the same lists gave 283.
- **Lists go stale and websites go bad.** Several providers' sites were parked, for sale
  or hijacked by spam; closures and moves turned up in every office. Checking each entry
  on a page catches them.
- **Some lists cannot be read by machine**: Nevada 211's provider search, Three Square's
  map, and many official pages that refuse automated reading.
- **Thin everywhere**: reentry, ID recovery, clothing and immigration have few or no
  local lists in any office tried. List seeding cannot fill them; a narrow search, need
  by need, still has to (not yet built).
- **List seeding gives contact details, not the handout.** Steps 1 to 4 find and check
  who to send people to. The handout text is step 5's job, which is where Scout's
  quality has to be matched.

## Open

- Run quality round two (above).
- Build the standard vocabulary from the existing taxonomies, and show Michael the counts.
- The gap search for thin categories.
- Michael's judging of the shortlist sample below was set aside as too much work; the
  side-by-side comparison replaced it as the quality measure.

---

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
