"""Gather every office's resources into one file for the shared-resource prototype.

Reads the newest full records on this Mac (production exports for the offices in use, and
the Scout files that were loaded into the other offices), keeps the fields the prototype shows, and
marks a resource vetted when production's 14 October listing had it as curated.
Writes local/records.json, which holds office data and is never committed: this
repository is public.
"""
from __future__ import annotations

import json
import re
import sys
import zipfile
from pathlib import Path

HOME = Path.home()
BACKUPS = HOME / "WSRS-Backups"
SCOUT = HOME / "scout-claude"
HERE = Path(__file__).resolve().parent
LOCAL = HERE.parent / "local"

# Office -> (label, state, draft counties served). Counties are a draft: the
# brainstorm of 20 October 2026 says each office's counties are still to be written down.
OFFICES = {
    "provo": ("Provo", "UT", ["Utah"]),
    "albuquerque": ("Albuquerque", "NM", ["Bernalillo"]),
    "mesa": ("Mesa", "AZ", ["Maricopa"]),
    "welfare-square": ("Welfare Square", "UT", ["Salt Lake"]),
    "st-george": ("St. George", "UT", ["Washington"]),
    "ogden": ("Ogden", "UT", ["Weber", "Davis"]),
    "las-vegas": ("Las Vegas", "NV", ["Clark"]),
    "cedar-city": ("Cedar City", "UT", ["Iron"]),
    "logan": ("Logan", "UT", ["Cache"]),
    "brigham-city": ("Brigham City", "UT", ["Box Elder"]),
    "bridgeport": ("Bridgeport (Potential)", "NJ", ["Gloucester", "Salem", "Camden"]),
    "boise": ("Boise (Potential)", "ID", ["Ada", "Canyon"]),
}

# Provo, Albuquerque and Mesa are in use (Elder Bendio, 20 October 2026), so they come
# from their newest production export (npm run recovery -- export, in wsrs-tso).
SOURCES = {
    "provo": ("export", None),
    "albuquerque": ("export", None),
    "mesa": ("export", None),
    "welfare-square": ("scout", SCOUT / "lsscout-welfare-square-merge-20261007/scout-welfare-square-merged-26-10-07.json"),
    "st-george": ("scout", SCOUT / "lsscout-st-george-merge-20261007/scout-st-george-merged-26-10-07.json"),
    "ogden": ("scout", SCOUT / "lsscout-ogden-20261006/ogden-lsscout-20261006.loaded.json"),
    "las-vegas": ("scout", BACKUPS / "scout-las-vegas-prepared-resources-26-10-06.json"),
    "cedar-city": ("scout", BACKUPS / "scout-cedar-city-prepared-resources-26-10-07-v3-loaded.json"),
    "logan": ("scout", BACKUPS / "scout-logan-lsscout-20261007.json"),
    "brigham-city": ("scout", BACKUPS / "scout-brigham-city-lsscout-20261007.json"),
    "bridgeport": ("scout", BACKUPS / "scout-bridgeport-prepared-resources-26-10-14.json"),
    "boise": ("scout", BACKUPS / "scout-boise-prepared-resources-26-10-14.json"),
}

PRODUCTION_LISTING = SCOUT / "all-resources-20261014.json"
LISTING_OFFICE = {v[0]: k for k, v in OFFICES.items()}


def norm_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (name or "").lower())


def package_records(office: str, data: dict) -> list[dict]:
    """WSRS package or backup: categories by id, Types under categoryFilters."""
    labels = {c["id"]: c.get("name") or c.get("label") for c in data["categories"]}
    out = []
    for r in data["resources"]:
        cats = [labels.get(c, c) for c in r.get("categories") or []]
        types = sorted({t for ts in (r.get("categoryFilters") or {}).values() for t in ts})
        out.append({
            "sourceId": r["id"],
            "name": r.get("name", ""),
            "description": r.get("description") or "",
            "information": r.get("informationText") or "",
            "phone": r.get("phone") or "",
            "website": r.get("website") or "",
            "address": r.get("address") or "",
            "hours": r.get("hours") or "",
            "oldCategories": cats,
            "oldTypes": types,
            "oldGroups": list(r.get("forGroups") or []),
            "verifiedOn": r.get("verifiedOn") or "",
        })
    return out


def scout_records(office: str, data: dict) -> list[dict]:
    """Scout prepared file: categories, Types and groups by id, labels in its taxonomy."""
    tax = data.get("taxonomy") or {}
    cat = {c["id"]: c["label"] for c in tax.get("categories", [])}
    typ = {t["id"]: t["label"] for t in tax.get("types", [])}
    grp = {g["id"]: g["label"] for g in tax.get("groups", tax.get("forGroups", []))}
    out = []
    for r in data["resources"]:
        out.append({
            "sourceId": r["id"],
            "name": r.get("name", ""),
            "description": r.get("description") or "",
            "information": r.get("informationText") or "",
            "phone": r.get("phone") or "",
            "website": r.get("website") or "",
            "address": r.get("address") or "",
            "hours": r.get("hours") or "",
            "oldCategories": [cat.get(c, c) for c in r.get("categories") or []],
            "oldTypes": [typ.get(t, t) for t in r.get("types") or []],
            "oldGroups": [grp.get(g, g) for g in r.get("forGroups") or []],
            "verifiedOn": "",
        })
    return out


def newest_export(office: str) -> Path:
    return sorted(BACKUPS.glob(f"{office}-wsrs-tso.crm.dynamics.com-*.wsrs.zip"))[-1]


def export_records(office: str, path: Path) -> list[dict]:
    """A production export: its reviewed resources, and the unreviewed Scout reserve its
    missionaries also see, chosen as wsrs-tso's readerReserve chooses it: usable rows of
    every imported snapshot, not withdrawn, not already reviewed, not deleted."""
    with zipfile.ZipFile(path) as z:
        package = json.load(z.open("resources.json"))
        tables = json.load(z.open("snapshot.json"))["tables"]
    rows = package_records(office, package)
    curated = {r.get("aei_sourcekey") for r in tables["aei_tsoresource"]} - {None}
    deleted = {c["aei_sourcekey"] for c in tables["aei_tsocandidatestate"] if c.get("aei_deleted") is True}
    taxonomy = {}
    for snap in tables["aei_tsoscoutsnapshot"]:
        tax = json.loads(snap.get("aei_taxonomy") or "{}")
        for kind in ("categories", "types", "groups", "forGroups"):
            taxonomy.setdefault(kind, []).extend(tax.get(kind, []))
    seen, reserve = set(), []
    for row in tables["aei_tsoscoutresource"]:
        record = json.loads(row["aei_record"])
        key = row.get("aei_sourcekey") or record["id"]
        if (row.get("aei_state") != 100000000 or row.get("aei_withdrawn") is True
                or key in curated or key in deleted or record["id"] in seen):
            continue
        seen.add(record["id"])
        reserve.append(record)
    return rows + scout_records(office, {"taxonomy": taxonomy, "resources": reserve})


def load(office: str) -> list[dict]:
    kind, path = SOURCES[office]
    if kind == "export":
        return export_records(office, newest_export(office))
    if kind == "backup":
        with zipfile.ZipFile(path) as z:
            data = json.load(z.open("resources.json"))
    else:
        data = json.loads(path.read_text())
    return package_records(office, data) if kind == "backup" else scout_records(office, data)


def main() -> int:
    listing = json.loads(PRODUCTION_LISTING.read_text())
    curated = {(LISTING_OFFICE.get(r["office"]), norm_name(r["name"])) for r in listing if r["kind"] == "curated"}
    records = []
    for office in OFFICES:
        rows = load(office)
        for n, r in enumerate(rows):
            r["id"] = f"{office}:{r.pop('sourceId')}"
            r["office"] = office
            r["vetted"] = (office, norm_name(r["name"])) in curated or bool(r["verifiedOn"])
            records.append(r)
        print(f"{office:15} {len(rows):4} resources, {sum(r['vetted'] for r in rows):4} vetted", file=sys.stderr)
    LOCAL.mkdir(exist_ok=True)
    offices = [{"id": k, "label": v[0], "state": v[1], "counties": v[2]} for k, v in OFFICES.items()]
    (LOCAL / "records.json").write_text(json.dumps({"offices": offices, "records": records}, ensure_ascii=False))
    print(f"{len(records)} resources -> {LOCAL / 'records.json'}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
