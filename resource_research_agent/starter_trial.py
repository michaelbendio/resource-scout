"""Compile authored starter-set judgments into a non-importable evaluation.

Phase 0 deliberately uses existing IDs. This does not allocate production IDs,
classify candidates, revise resources, or record office review completion.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
from html import escape
import json
from pathlib import Path
from urllib.parse import urlsplit


ARTIFACT_TYPE = "scout-starter-evaluation"


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def required_text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Missing {label}")
    return value


def compile_trial(seed_bytes: bytes, state_bytes: bytes, proposal: dict) -> dict:
    if proposal.get("schemaVersion") != 1 or proposal.get("evaluationOnly") is not True:
        raise ValueError("Expected a version-1 evaluation-only proposal")
    for name, raw in (("seedSha256", seed_bytes), ("stateSha256", state_bytes)):
        if proposal.get(name) != digest(raw):
            raise ValueError(f"Stale trial: {name} does not match")
    seed, state = json.loads(seed_bytes), json.loads(state_bytes)
    resources = {r["id"]: deepcopy(r) for r in seed["resources"]}
    if len(resources) != len(seed["resources"]):
        raise ValueError("Duplicate source resource IDs")
    for resource in state.get("resourceOverrides", []):
        if resource["id"] not in resources:
            raise ValueError("Unknown browser override")
        resources[resource["id"]].update(deepcopy(resource))
    if state.get("addedResources"):
        raise ValueError("Review added browser resources before compiling this trial")
    hidden = set(state.get("deletedResourceIds", []))
    categories = state.get("categoriesOverride")
    catalog = {c["id"]: c for c in (seed["categories"] if categories is None else categories)}

    def resolve(ref):
        # Short references are authoring conveniences only, tied to the exact seed.
        if not isinstance(ref, str) or len(ref) < 8:
            raise ValueError("Resource references need at least eight characters")
        matches = [rid for rid in resources if rid.startswith(ref)]
        if len(matches) != 1:
            raise ValueError(f"Unknown or ambiguous resource reference: {ref}")
        return matches[0]

    sets, all_selected, used_categories = [], set(), set()
    for authored in proposal["categories"]:
        cid = authored["categoryId"]
        if cid not in catalog or cid in used_categories:
            raise ValueError("Unknown or duplicate category")
        used_categories.add(cid)
        eligible = {rid for rid, r in resources.items() if cid in r["categories"]}
        decisions, members = {}, []
        for position, pick in enumerate(authored["members"], 1):
            rid = resolve(pick["ref"])
            if rid not in eligible or rid in hidden or rid in decisions:
                raise ValueError(f"Invalid, suppressed, or repeated selection: {rid}")
            evidence = pick["evidence"]
            field = evidence["field"]
            excerpt = required_text(evidence.get("text"), "evidence excerpt")
            if field not in ("description", "informationText") or excerpt not in resources[rid].get(field, ""):
                raise ValueError(f"Evidence does not occur in saved resource: {rid}")
            member = {key: required_text(pick.get(key), key) for key in
                      ("label", "contribution", "limitation")}
            member.update(resourceId=rid, position=position, evidence=deepcopy(evidence),
                          resource=deepcopy(resources[rid]))
            members.append(member)
            decisions[rid] = {"decision": "selected", "reason": member["contribution"]}
            all_selected.add(rid)
        if not 7 <= len(members) <= 10:
            raise ValueError("Trial categories require 7–10 authored selections")
        for ref, reason in authored["notSelected"].items():
            rid = resolve(ref)
            if rid not in eligible or rid in decisions or rid in hidden:
                raise ValueError(f"Invalid or duplicate assessment: {rid}")
            decisions[rid] = {"decision": "not-selected", "reason": required_text(reason, "assessment")}
        for rid in eligible & hidden:
            decisions[rid] = {"decision": "suppressed", "reason": "Excluded by saved human browser state."}
        if set(decisions) != eligible:
            missing = sorted(rid[:8] for rid in eligible - set(decisions))
            raise ValueError(f"Incomplete assessment in {cid}: {missing}")
        ledger = [dict(resourceId=rid, name=resources[rid]["name"], **decisions[rid])
                  for rid in sorted(decisions, key=lambda rid: (resources[rid]["name"].casefold(), rid))]
        sets.append(dict(categoryId=cid, label=catalog[cid]["label"],
                         rationale=required_text(authored.get("rationale"), "rationale"),
                         gaps=required_text(authored.get("gaps"), "gaps"),
                         candidateCount=len(eligible), members=members, assessments=ledger))
    if not 3 <= len(sets) <= 4:
        raise ValueError("Phase 0 covers three or four categories")
    return dict(artifactType=ARTIFACT_TYPE, schemaVersion=1, evaluationOnly=True,
                office=deepcopy(proposal["office"]), seedSha256=digest(seed_bytes),
                stateSha256=digest(state_bytes), proposalSha256=digest(json.dumps(
                    proposal, sort_keys=True, ensure_ascii=False).encode()),
                uniqueResources=len(all_selected), categoryEntries=sum(len(s["members"]) for s in sets),
                assessedMemberships=sum(s["candidateCount"] for s in sets),
                notes=deepcopy(proposal["notes"]), checks=deepcopy(proposal.get("checks", [])),
                starterSets=sets)


def safe_url(value):
    value = str(value or "")
    parsed = urlsplit(value)
    return value if parsed.scheme in ("http", "https") and parsed.netloc else ""


def render_html(trial: dict) -> str:
    e = escape
    parts = ["<!doctype html><html lang='en'><meta charset='utf-8'>",
             "<meta name='viewport' content='width=device-width,initial-scale=1'>",
             "<title>Mesa starter-set evaluation</title>",
             "<style>body{font:17px/1.55 system-ui,sans-serif;max-width:920px;margin:auto;padding:24px;color:#203039}"
             "h1,h2,h3{line-height:1.2}h2{margin-top:2.5em;border-bottom:2px solid #b8c8cb;padding-bottom:12px}"
             "article{padding:18px 0;border-bottom:1px solid #ccd6d8}.notice{background:#fff3cf;padding:16px}"
             "a{color:#075a82}nav a{margin-right:20px}summary{cursor:pointer}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:14px/1.5 system-ui}"
             "table{width:100%;border-collapse:collapse;font-size:14px}td,th{text-align:left;vertical-align:top;border-bottom:1px solid #ddd;padding:8px}"
             "small{color:#53646c}@media print{nav,details{display:none}article{break-inside:avoid}body{font-size:11pt}h2{break-before:page}}</style>",
             "<body><h1>Mesa starter-set evaluation</h1>",
             "<p class='notice'><strong>Evaluation for Michael and Stephanie.</strong> These are proposed resources to curate, not an approved directory or a WSRS-TSO import. Existing IDs are for this trial only.</p>",
             f"<p>{trial['uniqueResources']} distinct resource records · {trial['categoryEntries']} category entries · {trial['assessedMemberships']} candidate memberships assessed.</p>",
             "<p>One record used in several categories is one curation task. Separate records for the same provider may still need later identity reconciliation.</p>",
             "<nav>" + " ".join(f"<a href='#{e(s['categoryId'])}'>{e(s['label'])}</a>" for s in trial["starterSets"]) + "</nav>",
             "<p><strong>For your feedback:</strong> Would these choices make a useful first directory? Which would you replace, and why? Are important kinds of help or practical provider alternatives missing?</p>",
             "<details><summary>Scope and method: source snapshot, exclusions and limitations</summary><ul>"]
    parts += [f"<li>{e(note)}</li>" for note in trial["notes"]]
    parts.append("</ul></details>")
    for section in trial["starterSets"]:
        parts += [f"<h2 id='{e(section['categoryId'])}'>{e(section['label'])}: {len(section['members'])} proposed resources</h2>",
                  f"<p>{e(section['rationale'])}</p><p><strong>Remaining gaps:</strong> {e(section['gaps'])}</p>"]
        for member in section["members"]:
            r = member["resource"]
            parts += [f"<article><h3>{member['position']}. {e(member['label'])}</h3>",
                      f"<p><strong>What it adds:</strong> {e(member['contribution'])}</p>",
                      f"<p><strong>Check before curating:</strong> {e(member['limitation'])}</p>"]
            url = safe_url(r.get("website"))
            if url:
                parts.append(f"<p><a href='{e(url, quote=True)}' rel='noreferrer'>Saved provider/source page</a></p>")
            parts += ["<details><summary>Inspect saved resource and selection evidence</summary>",
                      f"<p>{e(r.get('description', ''))}</p><pre>{e(r.get('informationText', ''))}</pre>",
                      f"<p><strong>Evidence used:</strong> {e(member['evidence']['text'])}</p>",
                      f"<small>Existing ID: {e(member['resourceId'])}</small></details></article>"]
        parts += [f"<details><summary>All {section['candidateCount']} candidate assessments</summary><table><tr><th>Resource</th><th>Decision</th><th>Reason</th></tr>"]
        parts += [f"<tr><td>{e(a['name'])}</td><td>{e(a['decision'])}</td><td>{e(a['reason'])}</td></tr>" for a in section["assessments"]]
        parts.append("</table></details>")
    parts.append("<h2>Targeted source checks</h2><ul>")
    for check in trial["checks"]:
        url = safe_url(check["url"])
        label = f"<a href='{e(url, quote=True)}'>{e(check['label'])}</a>" if url else e(check["label"])
        parts.append(f"<li>{label}: {e(check['finding'])}</li>")
    parts += ["</ul><p><small>Research observations are not agency confirmation. No Curated flags or verification dates were assigned.</small></p></body></html>"]
    return "\n".join(parts)


def render_markdown(trial: dict) -> str:
    lines = ["# Mesa starter-set evaluation", "", "Evaluation only — not an approved directory or production import.", "",
             f"{trial['uniqueResources']} distinct records; {trial['categoryEntries']} category entries; {trial['assessedMemberships']} memberships assessed.", ""]
    lines += [f"- {note}" for note in trial["notes"]]
    for section in trial["starterSets"]:
        lines += ["", f"## {section['label']}", "", section["rationale"], "", "Remaining gaps: " + section["gaps"]]
        for m in section["members"]:
            lines += ["", f"### {m['position']}. {m['label']}", "", m["contribution"], "", "Check before curating: " + m["limitation"], "", f"Existing ID: `{m['resourceId']}`"]
    lines += ["", "## Targeted source checks", ""]
    for c in trial["checks"]:
        url = safe_url(c["url"])
        label = f"[{c['label']}]({url})" if url else c["label"]
        lines.append(f"- {label}: {c['finding']}")
    lines += ["", "## Feedback for Michael and Stephanie", "", "Which choices would you replace, and why? Are the explanations useful? What important help or provider alternatives are missing?", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("seed", "state", "proposal", "output"):
        parser.add_argument("--" + key, required=True, type=Path)
    args = parser.parse_args()
    trial = compile_trial(args.seed.read_bytes(), args.state.read_bytes(), json.loads(args.proposal.read_text()))
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "evaluation.json").write_text(json.dumps(trial, ensure_ascii=False, indent=2) + "\n")
    (args.output / "evaluation.html").write_text(render_html(trial))
    (args.output / "evaluation.md").write_text(render_markdown(trial))
    print(f"Trial: {trial['uniqueResources']} distinct records, {trial['categoryEntries']} category entries; {trial['assessedMemberships']} assessments. {args.output / 'evaluation.html'}")


if __name__ == "__main__":
    main()
