"""Build local/shared-resources.html: Provo's Resource Assistant page with every office's
resources, the draft standard vocabulary and shared resources.

The page is ~/resource-assistant/provo.html unchanged, given three additions:
- the data, and shared-prelude.js, which gives the app the chosen office's view on start;
- the shared-resource layer (shared-layer.js), run after the app;
- a storage id and title of its own, so it never touches Provo's saved data.

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
BASE = Path.home() / "resource-assistant/provo.html"
RECOUNT = Path.home() / "Documents/shared-recount-2026-10-21/shared-recount.csv"

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


# Federal programs each state runs (shared-resources brainstorm, 20 October 2026: they are
# state-level, with a front door per state). Found from a resource's name and description
# for the prototype; a vetter corrects them in the editor.
FEDERAL_PROGRAMS = [
    ("SNAP", r"\bSNAP\b|food stamps|nutrition assistance"),
    ("Medicaid", r"medicaid|\bAHCCCS\b|centennial care|turquoise care|nj ?familycare"),
    ("CHIP", r"\bCHIP\b|kidscare|children'?s health insurance program"),
    ("WIC", r"\bWIC\b|women,? infants,? (and|&) children"),
    ("TANF", r"\bTANF\b|temporary assistance for needy families|family employment program|\bnm works\b"),
    ("LIHEAP", r"\bLIHEAP\b|home energy assistance|\bHEAT\b program"),
]


def federal_programs(r: dict) -> list[str]:
    """Named in the resource's name, or its description says you apply for it there; a
    clinic that only accepts Medicaid is not a front door to it."""
    if re.search(r"(accepts?|those on|for people on) medicaid|\(medicaid\)", r["name"], re.I):
        return []

    def found(pattern: str) -> bool:
        return bool(re.search(pattern, r["name"], re.I)
                    or re.search(rf"\b(apply|applying|application|enrol\w*|sign up)\b[^.]{{0,60}}({pattern})", r["description"], re.I))
    return [name for name, pattern in FEDERAL_PROGRAMS if found(pattern)]


def clean_filing(f: dict, standard: dict) -> dict:
    """Keep only ids and labels the standard has; the readers were told to, this checks."""
    cats = {c["id"]: c for c in standard["categories"]}
    groups = {g["id"]: g for g in standard["groups"]}
    categories = [c for c in f.get("categories") or [] if c in cats][:2]
    subs = {c: [s for s in (f.get("subcategories") or {}).get(c, []) if s in cats[c]["subcategories"]] for c in categories}
    serves = f.get("serves") or {}
    level = serves.get("level") if serves.get("level") in ("national", "state", "local") else "local"
    serves = {"level": level, "state": state_code(serves.get("state")),
              "counties": [re.sub(r"\s+County$", "", c) for c in serves.get("counties") or []]}
    chosen = [g for g in f.get("groups") or [] if g.get("id") in groups]
    # One rule for who is eligible (shared-resources brainstorm, 20 October 2026): a place
    # restriction and a group's "only" are both said in words on the card.
    restriction = [f.get("restriction") or ""] + [f"{groups[g['id']]['label']} only" for g in chosen if g.get("only")]
    return {
        "categories": categories,
        "categoryFilters": {c: s for c, s in subs.items() if s},
        "forGroups": sorted(groups[g["id"]]["label"] for g in chosen),
        "serves": serves,
        "restriction": "; ".join(x for x in restriction if x),
        "missionariesOnly": bool(f.get("missionariesOnly")),
    }


def coverage_for(members: list[dict]) -> dict:
    """Draft coverage: the widest place any copy serves."""
    levels = [m["serves"]["level"] for m in members]
    if "national" in levels:
        return {"level": "national"}
    states = sorted({m["serves"]["state"] for m in members if m["serves"]["level"] == "state" and m["serves"]["state"]})
    if states:
        return {"level": "state", "states": states}
    return {"level": "county", "counties": sorted({f"{m['serves']['state']}:{c}" for m in members
                                                  if m["serves"]["state"] for c in m["serves"]["counties"]})}


def shared_groups(records: list[dict], offices: dict) -> dict:
    """The recount's cross-office groups, linked to this prototype's records."""
    by_name, by_pw = defaultdict(list), defaultdict(list)
    for r in records:
        by_name[(r["office"], norm(r["name"]))].append(r["id"])
        by_pw[(r["office"], digits(r["phone"]), host(r["website"]))].append(r["id"])
    rows = defaultdict(list)
    for row in csv.DictReader(RECOUNT.open()):
        rows[row["Group"]].append(row)
    rec = {r["id"]: r for r in records}
    out = {}
    for gid, group in rows.items():
        ids = []
        for m in group:
            hit = by_name.get((m["Office"], norm(m["Name"]))) or by_pw.get((m["Office"], digits(m["Phone"]), host(m["Website"])))
            if hit and hit[0] not in ids:
                ids.append(hit[0])
        if not ids:
            continue
        members = [rec[i] for i in ids]
        coverage = coverage_for(members)
        keeper = keeper_of(members, coverage)
        reasons = {}
        if coverage["level"] == "county":
            for o in sorted({m["office"] for m in members}):
                for c in offices[o]["counties"]:
                    key = f"{offices[o]['state']}:{c}"
                    if key not in coverage["counties"]:
                        reasons[key] = f"{offices[o]['label']} lists it already (recount, 21 October 2026)"
                        coverage["counties"].append(key)
            coverage["counties"].sort()
        held = {m["office"] for m in members}
        out[f"sg-{gid}"] = {"keeper": keeper, "members": ids, "matchedBy": group[0]["Matched by"],
                            "productionOnly": sorted({m["Office"] for m in group} - held),
                            "coverage": coverage, "reasons": reasons}
    return out


def keeper_of(members: list[dict], coverage: dict) -> str:
    """The copy whose text is shown: one serving as widely as the coverage, then a reviewed
    one, then the one with the most text."""
    level = {"county": "local"}.get(coverage["level"], coverage["level"])
    return max(members, key=lambda r: (r["serves"]["level"] == level, bool(r["verifiedOn"]) or r["vetted"],
                                       len(r["description"]) + len(r["informationText"])))["id"]


def nationwide_groups(records: list[dict], shared: dict) -> dict:
    """A resource the reader judged nationwide is shared nationwide (Elder Bendio, 25 October
    2026), once: joined to a nationwide shared resource, or to the other offices' copies, with
    the same phone number. Hotlines are national by their number; one office's copy that is a
    different program can still be split off with "Not the same"."""
    rec = {r["id"]: r for r in records}
    in_group = {m for g in shared.values() for m in g["members"]}
    by_phone = {}
    for gid, g in shared.items():
        if g["coverage"]["level"] == "national":
            for m in g["members"]:
                if len(digits(rec[m]["phone"])) == 10:
                    by_phone.setdefault(digits(rec[m]["phone"]), gid)
    out = {}
    for r in records:
        if r["id"] in in_group or r["serves"]["level"] != "national":
            continue
        phone = digits(r["phone"])
        gid = by_phone.get(phone) if len(phone) == 10 else None
        if gid in shared:
            shared[gid]["members"].append(r["id"])
            continue
        if gid in out:
            out[gid]["members"].append(r["id"])
            out[gid]["keeper"] = keeper_of([rec[m] for m in out[gid]["members"]], out[gid]["coverage"])
            out[gid]["matchedBy"] = "phone, judged nationwide"
            continue
        gid = f"nat-{r['id']}"
        if len(phone) == 10:
            by_phone[phone] = gid
        out[gid] = {"keeper": r["id"], "members": [r["id"]], "matchedBy": "judged nationwide by the reader",
                    "productionOnly": [], "coverage": {"level": "national"}, "reasons": {}}
    return out


def payload() -> dict:
    standard = json.loads((HERE / "standard.json").read_text())
    data = json.loads((LOCAL / "records.json").read_text())
    filings = {}
    for f in sorted((LOCAL / "batches").glob("out-*.json")):
        for row in json.loads(f.read_text()):
            filings[row["id"]] = row
    # Front doors to federal programs, judged by AI readers from programs-brief.md where a
    # resource mentions one; the name match below only for any they have not read.
    programs = {}
    for f in sorted((LOCAL / "batches").glob("programs-out-*.json")):
        for row in json.loads(f.read_text()):
            programs[row["id"]] = [p for p in row.get("federalPrograms") or [] if p in dict(FEDERAL_PROGRAMS)]
    # Resources added for the prototype from public sources (additions.json), each with its
    # filing and programs; one may replace an office's narrower entry for the same agency.
    for a in json.loads((HERE / "additions.json").read_text()):
        data["records"] = [r for r in data["records"] if r["id"] not in a.get("replaces", [])]
        data["records"].append({k: a.get(k, "") for k in ("id", "office", "name", "description", "information",
                                                          "phone", "website", "address", "hours", "verifiedOn")}
                               | {"vetted": a.get("vetted", False)})
        filings[a["id"]] = a["filing"]
        programs[a["id"]] = a["federalPrograms"]
    offices = {o["id"]: o for o in data["offices"]}
    records, missing = [], 0
    for r in data["records"]:
        if r["id"] not in filings:
            missing += 1
            continue
        records.append({
            "id": r["id"], "office": r["office"], "name": r["name"], "description": r["description"],
            "informationText": r["information"], "phone": r["phone"], "website": r["website"],
            "address": r["address"], "hours": r["hours"], "verifiedOn": r["verifiedOn"] or None, "pdfs": [],
            "vetted": r["vetted"], "federalPrograms": programs.get(r["id"], federal_programs(r)),
            **clean_filing(filings[r["id"]], standard),
        })
    if missing:
        print(f"{missing} resources have no filing and are left out", file=sys.stderr)
    shared = shared_groups(records, offices)
    shared.update(nationwide_groups(records, shared))
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    vocabulary = {
        "categories": [{"id": c["id"], "label": c["label"], "active": True, "filters": c["subcategories"]}
                       for c in standard["categories"]],
        "forGroups": [g["label"] for g in standard["groups"]],
        "forGroupDefinitions": {g["label"]: {"description": f"{g['who']}. Counts when: {g['counts']}.", "lastModified": now}
                                for g in standard["groups"]},
    }
    return {"built": dt.datetime.now().strftime("%Y-%m-%d %H:%M"), "offices": data["offices"],
            "federalPrograms": [name for name, _ in FEDERAL_PROGRAMS],
            "vocabulary": vocabulary, "resources": {r["id"]: r for r in records}, "shared": shared}


# "Subcategory" for "Type" in everything the page says (Elder Bendio, 25 October 2026). The
# package keys and the verb are protected; code names have no word boundary to match.
KEEP_TYPE = ['"Types", "types"', '"Types", "typesByCategory"', "Type 1, 2, or 3", "<li>Type the following"]


def subcategories(page: str) -> str:
    for n, text in enumerate(KEEP_TYPE):
        assert text in page, f"provo.html has changed: expected {text!r}"
        page = page.replace(text, f"\0KEEP{n}\0")
    page = re.sub(r"\bTypes\b", "Subcategories", page)
    page = re.sub(r"\bType\b", "Subcategory", page)
    page = page.replace("Add specific types for this category.", "Add specific subcategories for this category.")
    for n, text in enumerate(KEEP_TYPE):
        page = page.replace(f"\0KEEP{n}\0", text)
    return page


# Favourites are left out (Elder Bendio, 25 October 2026): Help no longer describes them.
FAVORITES_HELP = """        <h3>Favorites</h3>
        <p>Click the outline star next to a resource to add it to <strong>Favorites</strong>. A filled star means the resource is a favorite. Click the filled star to remove it. Click the outline star beside <strong>Categories</strong> to view favorite resources.</p>
"""


def main() -> int:
    page = subcategories(BASE.read_text())
    data = json.dumps(payload(), ensure_ascii=False).replace("</", "<\\/")
    prelude = (HERE / "shared-prelude.js").read_text()
    layer = (HERE / "shared-layer.js").read_text()
    replacements = [
        (FAVORITES_HELP, ""),
        ('<meta name="tso-storage-id" content="provo">', '<meta name="tso-storage-id" content="shared-resources">'),
        ("<title>Provo TSO Resources</title>", "<title>Shared Resources Prototype</title>"),
        # The data and the prelude go after the starter data, which the prelude replaces,
        # and before the app's own scripts, which read it on start.
        ('<script id="app-release-data" type="application/json">',
         f'<script id="shared-data" type="application/json">{data}</script>\n<script>\n{prelude}\n</script>\n'
         '<script id="app-release-data" type="application/json">'),
    ]
    for old, new in replacements:
        if page.count(old) != 1:
            print(f"provo.html has changed: expected one {old!r}", file=sys.stderr)
            return 1
        page = page.replace(old, new)
    end = page.rindex("</body>")
    page = page[:end] + f"<script>\n{layer}\n</script>\n" + page[end:]
    out = LOCAL / "shared-resources.html"
    out.write_text(page)
    print(f"{len(page) // 1024} KB -> {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
