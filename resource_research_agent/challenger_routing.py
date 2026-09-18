"""Explicit, versioned category routing; no learned winner or count heuristic."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .codex_first_research import validate_researcher_roster


def load_challenger_routing(path: Path) -> dict[str, dict[str, Any]]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("schemaVersion") != 1:
        raise ValueError("Challenger routing requires schemaVersion 1")
    version = value.get("version")
    categories = value.get("categories")
    if not isinstance(version, str) or not version.strip() or not isinstance(categories, dict):
        raise ValueError("Challenger routing needs a version and category rules")
    result = {}
    for category_id, rule in categories.items():
        if not isinstance(rule, dict) or not isinstance(rule.get("scope"), str) or not rule["scope"].strip():
            raise ValueError(f"{category_id}: a concrete second-opinion scope is required")
        if not isinstance(rule.get("reason"), str) or not rule["reason"].strip():
            raise ValueError(f"{category_id}: an explicit routing reason is required")
        result[category_id] = validate_researcher_roster({
            "schemaVersion": 1,
            "version": "pairwise-" + version.strip(),
            "researchers": [
                {"name": "Codex", "role": "primary"},
                {"name": "Grok", "role": "challenger"},
                {"name": "Claude", "role": "challenger", "after": "Grok",
                 "scope": rule["scope"], "routingReason": rule["reason"]},
            ],
        })
    return result
