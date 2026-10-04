"""Gather the lists a list-seeding trial found for an office into one file.

    python3 office-lists/build_office_lists.py <categories-dir> <office-slug> "<Office name>" <trial-date> <out.json>

Each list appears once, with every category it served and what the trial noted about
it there (current or stale, readable or not). Each category keeps its "thin" note: where
lists were missing, which is where Scout's own search still has to work.
"""
import json
import sys
from pathlib import Path


def main(folder, slug, name, date, out):
    lists, gaps = {}, {}
    for path in sorted(Path(folder).glob("*.json")):
        data = json.loads(path.read_text())
        category = data["category"]
        if data.get("thin"):
            gaps[category] = data["thin"]
        named = {}
        for seed in data.get("seeds", []):
            for url in seed.get("sources", []):
                named[url] = named.get(url, 0) + 1
        for entry in data.get("lists", []):
            held = lists.setdefault(entry["url"], {
                "url": entry["url"],
                "title": entry.get("title") or entry["url"],
                "kind": {"network": "regional"}.get(entry.get("kind", ""), entry.get("kind", "")),
                "categories": [],
                "notes": {},
                "namesFound": {},
                "firstFound": date,
                "lastChecked": date,
            })
            if category not in held["categories"]:
                held["categories"].append(category)
            if entry.get("note"):
                held["notes"][category] = entry["note"]
            held["namesFound"][category] = named.get(entry["url"], 0)
    body = {
        "office": {"slug": slug, "name": name},
        "about": "Lists of local providers found by list seeding, for seeding and re-checking Scout runs. "
                 "Notes are the trial's own words; namesFound counts the trial's seeds citing the list.",
        "lists": sorted(lists.values(), key=lambda l: (l["kind"], l["title"].lower())),
        "gaps": gaps,
    }
    Path(out).write_text(json.dumps(body, indent=1, ensure_ascii=False) + "\n")
    kinds = {}
    for l in lists.values():
        kinds[l["kind"]] = kinds.get(l["kind"], 0) + 1
    print(f"{out}: {len(lists)} distinct lists {kinds}, {len(gaps)} category gap notes")


if __name__ == "__main__":
    main(*sys.argv[1:6])
