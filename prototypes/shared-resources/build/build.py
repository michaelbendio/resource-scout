"""Build local/index.html: records + draft filings + shared groups + the draft standard.

Run gather.py first, then the classification batches (local/batches/out-*.json, written
by AI readers from classify-brief.md). Output holds office data, so it stays in local/.
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
LOCAL = ROOT / "local"
RECOUNT = Path.home() / "Documents/shared-recount-2026-10-21/shared-recount.csv"
INFO_LIMIT = 1500  # characters of the details text kept for each card

STATE_CODES = {"Utah": "UT", "Arizona": "AZ", "Nevada": "NV", "New Mexico": "NM", "Idaho": "ID",
               "New Jersey": "NJ", "Pennsylvania": "PA", "Delaware": "DE"}


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def digits(s: str) -> str:
    return re.sub(r"\D", "", s or "")[:10]


def host(u: str) -> str:
    return re.sub(r"^(https?://)?(www\.)?", "", (u or "").lower()).rstrip("/")


def state_code(s: str | None) -> str:
    s = (s or "").strip()
    return STATE_CODES.get(s, s.upper()[:2]) if s else ""


def clean_filing(f: dict, standard: dict) -> dict:
    """Keep only ids and labels the standard has; the readers were told to, this checks."""
    cats = {c["id"]: c for c in standard["categories"]}
    groups = {g["id"] for g in standard["groups"]}
    categories = [c for c in f.get("categories") or [] if c in cats][:2]
    subs = {c: [s for s in (f.get("subcategories") or {}).get(c, []) if s in cats[c]["subcategories"]] for c in categories}
    serves = f.get("serves") or {}
    level = serves.get("level") if serves.get("level") in ("national", "state", "local") else "local"
    serves = {"level": level, "state": state_code(serves.get("state")),
              "counties": [re.sub(r"\s+County$", "", c) for c in serves.get("counties") or []]}
    return {
        "categories": categories,
        "subcategories": subs,
        "groups": [{"id": g["id"], "only": bool(g.get("only"))} for g in f.get("groups") or [] if g.get("id") in groups],
        "navigator": bool(f.get("navigator")),
        "serves": serves,
        "restriction": f.get("restriction") or "",
        "missionariesOnly": bool(f.get("missionariesOnly")),
        "noFit": f.get("noFit") or "",
        "note": f.get("note") or "",
    }


def shared_groups(records: list[dict], offices: dict) -> list[dict]:
    """The recount's cross-office groups, linked to this prototype's records."""
    by_name, by_pw = defaultdict(list), defaultdict(list)
    for r in records:
        by_name[(r["office"], norm(r["name"]))].append(r["id"])
        by_pw[(r["office"], digits(r["phone"]), host(r["website"]))].append(r["id"])
    rows = defaultdict(list)
    for row in csv.DictReader(RECOUNT.open()):
        rows[row["Group"]].append(row)
    rec = {r["id"]: r for r in records}
    out = []
    for gid, members in rows.items():
        ids = []
        for m in members:
            hit = by_name.get((m["Office"], norm(m["Name"]))) or by_pw.get((m["Office"], digits(m["Phone"]), host(m["Website"])))
            if hit and hit[0] not in ids:
                ids.append(hit[0])
        if not ids:
            continue
        # Keeper: a reviewed copy first, then the one with the most text.
        keeper = max(ids, key=lambda i: (rec[i]["vetted"], len(rec[i]["description"]) + len(rec[i]["information"])))
        k = rec[keeper]
        held = sorted({m["Office"] for m in members})
        reasons = {}
        if k["serves"]["level"] == "national":
            coverage = {"level": "national"}
        elif k["serves"]["level"] == "state" and k["serves"]["state"]:
            coverage = {"level": "state", "states": [k["serves"]["state"]]}
        else:
            counties = {f"{k['serves']['state']}:{c}" for c in k["serves"]["counties"] if k["serves"]["state"]}
            for o in held:
                if o not in offices:
                    continue
                for c in offices[o]["counties"]:
                    key = f"{offices[o]['state']}:{c}"
                    if key not in counties:
                        reasons[key] = f"{offices[o]['label']} lists it already (recount, 21 October 2026)"
                        counties.add(key)
            coverage = {"level": "county", "counties": sorted(counties)}
        out.append({"id": f"sg-{gid}", "keeper": keeper, "members": ids, "offices": held,
                    "matchedBy": members[0]["Matched by"], "coverage": coverage, "reasons": reasons})
    return out


def main() -> int:
    standard = json.loads((HERE / "standard.json").read_text())
    data = json.loads((LOCAL / "records.json").read_text())
    filings = {}
    for f in sorted((LOCAL / "batches").glob("out-*.json")):
        for row in json.loads(f.read_text()):
            filings[row["id"]] = row
    offices = {o["id"]: o for o in data["offices"]}
    records, missing = [], 0
    for r in data["records"]:
        if r["id"] not in filings:
            missing += 1
            continue
        info = r["information"]
        records.append({
            "id": r["id"], "office": r["office"], "name": r["name"], "description": r["description"],
            "information": info if len(info) <= INFO_LIMIT else info[:INFO_LIMIT] + "…",
            "phone": r["phone"], "website": r["website"], "address": r["address"], "hours": r["hours"],
            "vetted": r["vetted"],
            "old": {"categories": r["oldCategories"], "types": r["oldTypes"], "groups": r["oldGroups"]},
            **clean_filing(filings[r["id"]], standard),
        })
    shared = shared_groups(records, offices)
    built = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    payload = {
        "built": built,
        "meta": {"builtAt": built, "sources": "Provo's WSRS package; Albuquerque's 6 October backup; the Scout files loaded into the other ten offices; vetted status from production's 14 October listing; shared groups from the 21 October recount"},
        "standard": standard, "offices": data["offices"], "resources": records, "shared": shared,
    }
    html = (ROOT / "template.html").read_text().replace("/*DATA*/null", json.dumps(payload, ensure_ascii=False).replace("</", "<\\/"))
    (LOCAL / "index.html").write_text(html)
    print(f"{len(records)} resources ({missing} without a filing), {len(shared)} shared groups, "
          f"{len(html) // 1024} KB -> {LOCAL / 'index.html'}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
