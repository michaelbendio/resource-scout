"""Checkpoint-based curation estimates from the current job's recorded batches."""
from __future__ import annotations

from datetime import datetime, timezone
from math import ceil, floor
from typing import Any


ACTIVE_PHASES = {
    "codex-curation-started", "codex-curation-active",
    "codex-curation-batch-started", "codex-curation-batch-completed",
    "codex-curation-completed",
}


def _time(value: Any) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed
    except (TypeError, ValueError):
        return None


def estimate_curation(job: dict[str, Any], events: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Recalculate only on batch completion, never on wall-clock polling.

    Weight by candidates because evidence-size limits produce unequal batches.
    A resumed runner re-emits saved completions; each category/batch counts once.
    Overall and recent (12 batch) throughput provide a deliberately broad range,
    not a statistical confidence interval. This excludes later review/export.
    """
    if job.get("status") in {"completed", "failed"}:
        return None
    categories = {c["categoryId"]: c for c in job.get("categories", [])}
    starts: dict[tuple[str, int], dict[str, Any]] = {}
    completed: set[tuple[str, int]] = set()
    consumed: dict[str, int] = {}
    samples: list[tuple[float, int]] = []
    checkpoint = None
    for event in events:
        details = event.get("details") or {}
        category = event.get("categoryId")
        batch = details.get("batch")
        if category not in categories or not isinstance(batch, int) or batch < 1:
            continue
        key = (category, batch)
        if event.get("phase") == "codex-curation-batch-started":
            starts.setdefault(key, event)
        elif event.get("phase") == "codex-curation-batch-completed" and key not in completed:
            start = starts.get(key)
            count = ((start or {}).get("details") or {}).get("candidateCount")
            if not isinstance(count, int) or count <= 0:
                continue
            completed.add(key)
            consumed[category] = consumed.get(category, 0) + count
            checkpoint = event.get("createdAt")
            begin, end = _time(start.get("createdAt")), _time(checkpoint)
            if begin and end and (seconds := (end - begin).total_seconds()) >= 1:
                samples.append((seconds, count))
    if len(samples) < 2:
        return None
    remaining = sum(
        max(0, int(c.get("candidateCount") or 0) - consumed.get(category, 0))
        for category, c in categories.items() if c.get("status") != "completed"
    )
    if not remaining:
        return None
    def pace(rows: list[tuple[float, int]]) -> float:
        return sum(seconds for seconds, _ in rows) / sum(count for _, count in rows)
    overall, recent = pace(samples), pace(samples[-12:])
    low_seconds = remaining * min(overall, recent) * 0.8
    high_seconds = remaining * max(overall, recent) * 1.3
    unit, divisor = ("hours", 3600) if low_seconds >= 3600 else ("minutes", 60)
    low = max(1, floor(low_seconds / divisor))
    high = max(low + 1, ceil(high_seconds / divisor))
    return {
        "label": f"Done in {low} - {high} {unit}",
        "lowerSeconds": round(low_seconds), "upperSeconds": round(high_seconds),
        "updatedAt": checkpoint, "completedBatches": len(completed),
        "remainingCandidates": remaining, "scope": "curation",
    }
