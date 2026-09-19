"""Bounded recovery of one sealed curation batch, retaining every attempt."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from .worker_failures import classify_worker_failure, native_error
from .worker_lifecycle import atomic_json, await_orphan


INPUT_FILES = ("assignment.json", "view.json", "prior-resources.json", "source-only.json",
               "excluded.json", "schema.json", "prompt.txt")


def failure_detail(directory: Path) -> str:
    recorded = directory / "failure.json"
    if recorded.exists():
        failure = json.loads(recorded.read_text())
        # A deadline is decisive even if the native tail contains an earlier
        # recoverable connection error.
        if failure.get("kind") == "timeout":
            return "Worker timeout: " + str(failure.get("message", "deadline exceeded"))
    return native_error(directory)


def recover_result(directory: Path, execute: Callable[..., None], *,
                   heartbeat: Callable[[float], None], timeout: int,
                   **worker_options: Any) -> Path:
    """Adopt surviving workers; allow at most one retry of a transport failure.

    A result, even an invalid one, is never regenerated here. Validation is the
    caller's responsibility. Authentication, quota, context and unknown failures
    stop for diagnosis. Retry inputs are byte-identical; failed output is retained.
    The on-disk attempt path is the budget, including across coordinator restarts.
    """
    retry = directory / "transport-retry-1"
    for attempt in (directory, retry):
        if attempt == retry:
            attempt.mkdir(exist_ok=True)
            for name in INPUT_FILES:
                original = (directory / name).read_bytes()
                target = attempt / name
                if target.exists():
                    if target.read_bytes() != original:
                        raise ValueError(f"Retry sealed input changed: {target}")
                else:
                    with target.open("xb") as handle:
                        handle.write(original)
        if (attempt / "events.jsonl").exists() and not (attempt / "execution.json").exists():
            # A crashed coordinator may have left its worker alive. Never start
            # another worker or inspect a half-written result until it exits.
            try:
                await_orphan(attempt, timeout, heartbeat)
            except TimeoutError as error:
                atomic_json(attempt / "failure.json", {
                    "kind": "timeout", "message": str(error), "retryable": False,
                })
                raise
        if (attempt / "result.json").exists():
            if attempt == retry:
                atomic_json(directory / "recovery-result.json", {
                    "resultDirectory": retry.name, "method": "one transport retry",
                })
            return attempt
        if not (attempt / "events.jsonl").exists():
            try:
                execute(attempt, timeout=timeout, heartbeat=heartbeat, **worker_options)
            except TimeoutError as error:
                atomic_json(attempt / "failure.json", {
                    "kind": "timeout", "message": str(error), "retryable": False,
                })
                raise
            except Exception:
                # Only a positively identified native transport failure permits
                # another paid attempt. All other failures retain the traceback.
                if not classify_worker_failure(failure_detail(attempt)).retryable:
                    raise
            if (attempt / "result.json").exists():
                if attempt == retry:
                    atomic_json(directory / "recovery-result.json", {
                        "resultDirectory": retry.name, "method": "one transport retry",
                    })
                return attempt
        detail = failure_detail(attempt)
        failure = classify_worker_failure(detail)
        if not failure.retryable:
            raise RuntimeError(f"Curation {failure.kind} failure at {attempt}: {detail}")
        if attempt == retry:
            raise RuntimeError(f"Curation transport retry exhausted at {attempt}: {detail}")
        atomic_json(directory / "recovery-plan.json", {
            "kind": failure.kind, "reason": detail, "maximumRetries": 1,
            "retryDirectory": retry.name,
        })
    raise AssertionError("unreachable")
