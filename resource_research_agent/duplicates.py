from __future__ import annotations

from collections import defaultdict
from difflib import SequenceMatcher
from typing import Any

from .importer import iter_index_values, normalize_index_value, resource_name
from .storage import ResearchStore


TYPE_WEIGHTS = {
    "name": 1.00,
    "alias": 0.98,
    "name_variant": 0.94,
    "organization_name": 0.88,
    "program_name": 0.84,
    "website": 0.96,
    "address": 0.88,
}


class DuplicateIndex:
    def __init__(self, store: ResearchStore) -> None:
        self.store = store

    def match(self, candidate: dict[str, Any], import_id: int | None = None, limit: int = 5) -> list[dict[str, Any]]:
        import_id = import_id or self.store.latest_import_id()
        if import_id is None:
            return []
        candidate_terms = [
            (kind, value, normalize_index_value(kind, value))
            for kind, value in iter_index_values(candidate)
            if normalize_index_value(kind, value)
        ]
        if not candidate_terms:
            return []
        scores: dict[str, list[dict[str, Any]]] = defaultdict(list)
        metadata: dict[str, dict[str, Any]] = {}
        for known in self.store.known_terms(import_id):
            metadata[known["resource_id"]] = known
            for candidate_type, candidate_value, candidate_normalized in candidate_terms:
                signal = self._signal(candidate_type, candidate_normalized, known["term_type"], known["normalized"])
                if signal < 0.62:
                    continue
                scores[known["resource_id"]].append(
                    {
                        "candidateField": candidate_type,
                        "candidateValue": candidate_value,
                        "knownField": known["term_type"],
                        "knownValue": known["value"],
                        "strength": round(signal, 4),
                    }
                )
        matches: list[dict[str, Any]] = []
        for rid, signals in scores.items():
            strengths = sorted((signal["strength"] for signal in signals), reverse=True)
            combined = strengths[0]
            for extra in strengths[1:3]:
                combined += (1 - combined) * extra * 0.25
            known = metadata[rid]
            matches.append(
                {
                    "importId": import_id,
                    "resourceId": rid,
                    "name": known["name"],
                    "isTargetCategory": bool(known["is_target"]),
                    "score": round(min(combined, 1.0), 4),
                    "classification": "already-known" if combined >= 0.86 else "possible-duplicate",
                    "signals": sorted(signals, key=lambda item: item["strength"], reverse=True)[:5],
                }
            )
        return sorted(matches, key=lambda item: item["score"], reverse=True)[:limit]

    def explain_saved_match(self, discovery: dict[str, Any]) -> dict[str, Any] | None:
        return self.explain_match(discovery.get("candidate", {}), discovery.get("match"))

    def explain_match(
        self,
        candidate: dict[str, Any],
        stored: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if not stored:
            return None
        import_id = int(stored["importId"])
        resource_id = str(stored["resourceId"])
        recomputed = next(
            (
                match
                for match in self.match(
                    candidate, import_id=import_id, limit=100
                )
                if match["resourceId"] == resource_id
            ),
            None,
        )
        if recomputed:
            if stored.get("classification") in {"already-in-package", "possible-duplicate"}:
                recomputed = {**recomputed, "classification": stored["classification"]}
            return recomputed
        record = self.store.full_resource(import_id, resource_id)
        return {
            "importId": import_id,
            "resourceId": resource_id,
            "name": resource_name(record or {}) or resource_id,
            "isTargetCategory": None,
            "score": stored.get("score"),
            "classification": "historical-signal",
            "signals": [],
        }

    @staticmethod
    def _signal(candidate_type: str, candidate: str, known_type: str, known: str) -> float:
        compatible_name = candidate_type in {"name", "alias", "name_variant", "organization_name", "program_name"} and known_type in {
            "name", "alias", "name_variant", "organization_name", "program_name"
        }
        if candidate_type != known_type and not compatible_name:
            return 0.0
        if candidate == known:
            return min(TYPE_WEIGHTS.get(candidate_type, 0.78), TYPE_WEIGHTS.get(known_type, 0.78))
        if candidate_type == "website" and known_type == "website":
            candidate_host = candidate.split("/", 3)[2] if candidate.startswith("https://") else candidate
            known_host = known.split("/", 3)[2] if known.startswith("https://") else known
            return 0.91 if candidate_host == known_host else 0.0
        if candidate_type == "address" and known_type == "address":
            return SequenceMatcher(None, candidate, known).ratio() * 0.88
        if compatible_name:
            ratio = SequenceMatcher(None, candidate, known).ratio()
            shorter, longer = sorted((candidate, known), key=len)
            containment = len(shorter) / len(longer) if shorter in longer and longer else 0
            return max(ratio, containment) * min(TYPE_WEIGHTS.get(candidate_type, 0.84), TYPE_WEIGHTS.get(known_type, 0.84))
        return 0.0
