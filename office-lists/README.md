# Office lists

The lists of local providers that list seeding found for each office: 211 searches and
sheets, city, county and state pages, regional networks and aggregator directories.
Saved so a later Scout run can **start from an office's known lists** rather than search
from nothing, and so the lists can be **re-read later and compared**: a new name is a
lead, a name that drops off may be a closure. Statewide lists (211 Utah, DWS) serve every
office in the state.

| File | Office | Trial | Distinct lists |
| --- | --- | --- | --- |
| `mesa.json` | Mesa, Arizona | 30 September 2026, [write-up](../docs/list-seeding-trial-claude-20260930.md) | 92 |
| `ogden.json` | Ogden, Utah | 3 October 2026 | 67 |
| `logan.json` | Logan, Utah | 6 October 2026, lists only | 45 |
| `brigham-city.json` | Brigham City, Utah | 6 October 2026, lists only | 32 |
| `cedar-city.json` | Cedar City, Utah | 6 October 2026, lists only | 25 |
| `las-vegas.json` | Las Vegas, Nevada | 3 October 2026 | 78 |
| `st-george.json` | St. George, Utah | 3 October 2026 | 35 |
| `welfare-square.json` | Welfare Square (Salt Lake City), Utah | 3 October 2026 | 64 |
| `bridgeport.json` | Bridgeport, New Jersey (with Delaware County and Philadelphia, PA, and New Castle County, DE) | 13 October 2026, lists only, by Codex's publisher playbook; each list carries `coverage`, `read` and `residency`, plus `publishers` and `requests` ([brief](brief-lists-only-bridgeport-20261013.md)); area file `bridgeport-area.json` (draft) | 124 |
| `boise.json` | Boise, Idaho (Ada and Canyon counties) | 14 October 2026, lists only, by the publisher playbook, statewide lists in `states/idaho.json` ([brief](brief-lists-only-boise-20261013.md)); area file `boise-area.json` (draft: office address unknown, measured from 83706, 20 miles provisional) | 41 |

The trials' own counts (133 for Mesa, 137 for Ogden) count a list once per category it
served; these files count it once.

Each list carries its `kind`, the `categories` it served, the trial's `notes` on it per
category (current or stale, readable or refused), how many names it gave (`namesFound`),
and `firstFound`/`lastChecked` dates. `gaps` holds each category's note on where lists
were thin or missing: where Scout's own search still has to do the work.

Built by `build_office_lists.py` from the trial files in `~/scout-claude/list-seeding*/`.

The three files of 3 October for Las Vegas, St. George and Welfare Square were gathered on 6 October
from their demo trials by `build_office_lists.py`. Logan, Brigham City and Cedar City were
found by a lists-only search (`brief-lists-only-20261006.md`): no providers recorded.
`ogden-gaps.md` says what the Ogden LSScout run of 6 October could not find; its full
notes are `gapsAfterLsscout` in `ogden.json`.

## Shared state and federal lists (13 October 2026)

Elder Bendio: "the idea is to share state and federal resource lists with other Scout runs."
An office's lists search reads these first and searches only for what they lack.

| File | Scope | Built |
| --- | --- | --- |
| `federal.json` | National locators, directories and hotlines: 65, each tested for Bridgeport (08014) and Boise (83702), with how to ask it for one place and whether a script can read it | 13 October 2026 ([brief](brief-federal-20261013.md)); category ids normalised to the app's 21 by Claude |
| `states/new-jersey.json` | The 21 statewide New Jersey lists | Taken from `bridgeport.json`, 13 October 2026 |
| `states/utah.json` | 52 statewide Utah lists | Moved from the six Utah offices' files, 13 October 2026 |
| `states/nevada.json` | 35 statewide Nevada lists | Moved from `las-vegas.json`, 13 October 2026 |
| `states/arizona.json` | 10 statewide Arizona lists | Moved from `mesa.json`, 13 October 2026 |
| `states/idaho.json` | 33 statewide Idaho lists | Boise's lists search, 14 October 2026 |

Each moved list keeps every office's own notes and name counts under `byOffice`. A state
page with a section for each county (the Utah Maternal Resource Guide, the Utah Domestic
Violence Coalition's list) counts as statewide: an office reads its own county's section.
Searches of a statewide directory near one town ("211 Arizona search: dental near Mesa")
stay in that office's file. The office counts above are after the move.

