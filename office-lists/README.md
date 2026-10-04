# Office lists

The lists of local providers that list seeding found for each office: 211 searches and
sheets, city, county and state pages, regional networks and aggregator directories.
Saved so a later Scout run can **start from an office's known lists** rather than search
from nothing, and so the lists can be **re-read later and compared**: a new name is a
lead, a name that drops off may be a closure. Statewide lists (211 Utah, DWS) serve every
office in the state.

| File | Office | Trial | Distinct lists |
| --- | --- | --- | --- |
| `mesa.json` | Mesa, Arizona | 30 September 2026, [write-up](../docs/list-seeding-trial-claude-20260930.md) | 102 |
| `ogden.json` | Ogden, Utah | 3 October 2026 | 83 |

The trials' own counts (133 for Mesa, 137 for Ogden) count a list once per category it
served; these files count it once.

Each list carries its `kind`, the `categories` it served, the trial's `notes` on it per
category (current or stale, readable or refused), how many names it gave (`namesFound`),
and `firstFound`/`lastChecked` dates. `gaps` holds each category's note on where lists
were thin or missing: where Scout's own search still has to do the work.

Built by `build_office_lists.py` from the trial files in `~/scout-claude/list-seeding*/`.
