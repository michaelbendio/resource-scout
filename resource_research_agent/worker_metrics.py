"""Provider counters are observations; missing metadata is never a zero."""
from __future__ import annotations

from typing import Any


def optional_counter(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if value < 0 or not float(value).is_integer():
        return None
    return int(value)


def model_counter(model_usage: Any, key: str) -> int | None:
    if not isinstance(model_usage, dict) or not model_usage:
        return None
    values = [
        optional_counter(item.get(key)) if isinstance(item, dict) else None
        for item in model_usage.values()
    ]
    return sum(values) if all(value is not None for value in values) else None


def observed_counter(usage: dict[str, Any], key: str) -> int | None:
    value = optional_counter(usage.get(key))
    # Earlier adapters coerced absent fields to zero. Positive legacy values are
    # useful observations; legacy zeros cannot distinguish missing from zero.
    if value == 0 and usage.get("counterSchemaVersion") != 2:
        return None
    return value
