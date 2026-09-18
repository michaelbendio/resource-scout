#!/usr/bin/env python3
"""Recover transcript observations only when assignment and saved result match.

Does not infer a failed call merely because a native session was not saved. Does
not equate assistant-message counts or tool invocations with provider turn/usage
counters. All experiment databases and native logs are read-only inputs.
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import hashlib
import json
from pathlib import Path
import sqlite3


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("experiment", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--native-root", type=Path, default=Path.home() / ".claude/projects")
    args = parser.parse_args()
    assignments = []
    for profile in ("codex-claude", "claude-grok"):
        db = sqlite3.connect((args.experiment / (profile + ".sqlite3")).resolve().as_uri() + "?mode=ro", uri=True)
        db.row_factory = sqlite3.Row
        if profile == "claude-grok":
            query = """SELECT p.id,p.focus_key,p.assignment,p.assignment_sha256,p.status,j.category_label,m.raw_text
              FROM focused_research_passes p JOIN focused_research_jobs j ON j.id=p.job_id
              LEFT JOIN manual_discovery_contributions m ON m.id=p.contribution_id ORDER BY p.id"""
        else:
            query = """SELECT a.id,'' focus_key,a.assignment,a.assignment_sha256,a.status,j.category_label,m.raw_text
              FROM codex_first_research_assignments a JOIN focused_research_jobs j ON j.id=a.job_id
              LEFT JOIN manual_discovery_contributions m ON m.id=a.contribution_id
              WHERE a.researcher='Claude' ORDER BY a.id"""
        assignments.extend({**dict(row), "profile": profile} for row in db.execute(query) if row["assignment"])
        db.close()
    observations = []
    for path in sorted(args.native_root.glob("*scout-pairwise-claude*/*.jsonl")):
        records = []
        for line in path.read_text().splitlines():
            try:
                records.append(json.loads(line))
            except ValueError:
                pass
        first = next((r for r in records if r.get("type") == "user" and isinstance(r.get("message", {}).get("content"), str)), None)
        if not first:
            continue
        prompt = first["message"]["content"]
        matches = [a for a in assignments if a["assignment"] in prompt]
        if len(matches) != 1:
            continue
        assignment = matches[0]
        assistants = [r for r in records if r.get("type") == "assistant"]
        if not assistants:
            continue
        last = assistants[-1]
        final = "\n".join(block.get("text", "") for block in last.get("message", {}).get("content", []) if block.get("type") == "text").strip()
        saved = str(assignment["raw_text"] or "").strip()
        matched = bool(saved) and final == saved and assignment["status"] == "completed"
        tools = {block["id"]: block["name"] for r in assistants for block in r.get("message", {}).get("content", []) if block.get("type") == "tool_use"}
        tool_errors = {
            block["tool_use_id"]: tools.get(block["tool_use_id"], "unknown")
            for r in records if r.get("type") == "user" and isinstance(r.get("message", {}).get("content"), list)
            for block in r["message"]["content"] if block.get("type") == "tool_result" and block.get("is_error") is True
        }
        messages = {r["message"]["id"] for r in assistants if r.get("message", {}).get("id")}
        start, end = first.get("timestamp"), last.get("timestamp")
        elapsed = (dt.datetime.fromisoformat(end.replace("Z", "+00:00")) - dt.datetime.fromisoformat(start.replace("Z", "+00:00"))).total_seconds() if start and end else None
        observations.append({
            "profile": assignment["profile"], "role": "primary" if assignment["profile"] == "claude-grok" else "challenger",
            "category": assignment["category_label"], "focusKey": assignment["focus_key"], "assignmentId": assignment["id"],
            "assignmentSha256": assignment["assignment_sha256"], "nativeTranscript": str(path),
            "nativeTranscriptSha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "savedResultMatched": matched, "savedResultNormalizedSha256": sha(saved) if saved else None,
            "startedAt": start, "lastAssistantAt": end, "transcriptElapsedSeconds": elapsed,
            "assistantMessageCount": len(messages), "toolInvocationCounts": dict(collections.Counter(tools.values())),
            "explicitToolErrorCounts": dict(collections.Counter(tool_errors.values())),
            "cliVersion": last.get("version"), "reportedEffort": last.get("effort"),
            "modelIds": sorted({r.get("message", {}).get("model") for r in assistants if r.get("message", {}).get("model")}),
        })
    matched_by_assignment = collections.Counter((o["profile"], o["assignmentId"]) for o in observations if o["savedResultMatched"])
    if any(count != 1 for count in matched_by_assignment.values()):
        raise SystemExit("Ambiguous multiple native sessions match a saved result; review manually")
    result = {
        "generatedAt": dt.datetime.now(dt.timezone.utc).isoformat(),
        "limits": [
            "Only savedResultMatched sessions are usable as recovered successful execution observations.",
            "Transcript elapsed time excludes process startup and completion overhead; it is not pure inference time.",
            "Assistant messages and tool invocations are not interchangeable with provider num_turns or billed web-search requests.",
            "Tool invocation counts include requested calls; explicit tool-result errors are listed separately.",
            "Unmatched sessions may be failures, preliminary replays or active calls; do not label them failures without separate evidence.",
        ], "observations": observations,
    }
    args.output.write_text(json.dumps(result, indent=2))
    for profile in ("codex-claude", "claude-grok"):
        rows = [o for o in observations if o["profile"] == profile and o["savedResultMatched"]]
        print(profile, "matched successful sessions", len(rows), "transcript minutes", round(sum(o["transcriptElapsedSeconds"] or 0 for o in rows) / 60, 2))


if __name__ == "__main__":
    main()
