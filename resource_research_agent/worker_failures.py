"""Classify native worker failures before choosing a bounded recovery action."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WorkerFailure:
    kind: str
    message: str
    retryable: bool = False


def classify_worker_failure(message: str, *, timed_out: bool = False) -> WorkerFailure:
    text = message.casefold()
    # Specific budget/account errors precede generic 429 or transport matching.
    if any(term in text for term in ("usage limit", "quota", "insufficient_quota", "credit balance", "billing hard limit", "rate limit resets")):
        return WorkerFailure("usage", message)
    if any(term in text for term in ("401", "unauthorized", "authentication", "invalid api key", "token expired", "sign in", "sign-in", "credential lock", "credentials")):
        return WorkerFailure("authentication", message)
    if any(term in text for term in ("context window", "context length", "context_length_exceeded", "maximum context", "too many tokens")):
        return WorkerFailure("context", message)
    if timed_out or "timed out" in text or "timeout" in text:
        return WorkerFailure("timeout", message)
    if any(term in text for term in ("connection reset", "connection closed", "stream disconnected", "temporarily unavailable", "server error", "503", "502", "429", "rate limit")):
        return WorkerFailure("transport", message, retryable=True)
    return WorkerFailure("unknown", message)


def native_error(directory: Path) -> str:
    """Read only a bounded tail; partial final JSONL lines are expected on crashes."""
    events = directory / "events.jsonl"
    if events.exists():
        with events.open("rb") as handle:
            handle.seek(max(0, events.stat().st_size - 65536))
            lines = handle.read().decode("utf-8", errors="replace").splitlines()
        for line in reversed(lines):
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if event.get("type") == "turn.failed":
                error = event.get("error") or {}
                return str(error.get("message") if isinstance(error, dict) else error)[:4000]
            if event.get("type") == "error" and event.get("message"):
                return str(event["message"])[:4000]
    stderr = directory / "stderr.log"
    if stderr.exists():
        with stderr.open("rb") as handle:
            handle.seek(max(0, stderr.stat().st_size - 4000))
            return handle.read().decode("utf-8", errors="replace").strip()
    return "Worker stopped without a native error message."
