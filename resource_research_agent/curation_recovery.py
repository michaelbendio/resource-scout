"""Bounded recovery of one sealed curation batch, retaining every attempt."""
from __future__ import annotations

import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .worker_failures import classify_worker_failure, native_error
from .worker_lifecycle import atomic_json, await_orphan


INPUT_FILES = ("assignment.json", "view.json", "prior-resources.json", "source-only.json",
               "excluded.json", "schema.json", "prompt.txt")


def reviewed_context_attempt(directory: Path) -> Path | None:
    """Accept one explicitly diagnosed context retry, never an automatic retry.

    The supervisor prepares the reduced view/prompt and seals their hashes. All
    assignment, candidate, prior-record and schema bytes remain unchanged.
    """
    plan_path = directory / "reviewed-context-recovery.json"
    if not plan_path.exists():
        return None
    plan = json.loads(plan_path.read_text())
    if (plan.get("schemaVersion") != 1 or not plan.get("reviewer")
            or not plan.get("reason") or plan.get("maximumAttempts") != 1):
        raise ValueError("Invalid reviewed context recovery plan")
    if classify_worker_failure(failure_detail(directory)).kind != "context":
        raise ValueError("Reviewed context recovery requires a confirmed context failure")
    if (directory / "result.json").exists() or not (directory / "execution.json").exists():
        raise ValueError("Context recovery requires an exited worker without a result")
    attempt = directory / "context-retry-1"
    originals = plan.get("originalHashes", {})
    outputs = plan.get("retryHashes", {})
    required = set(INPUT_FILES) | {"events.jsonl", "execution.json"}
    if not required <= set(originals) or not (set(INPUT_FILES) | {"prior-resource-index.json"}) <= set(outputs):
        raise ValueError("Context recovery is missing sealed hashes")
    for folder, hashes in ((directory, originals), (attempt, outputs)):
        for name, expected in hashes.items():
            if Path(name).name != name:
                raise ValueError("Context recovery filenames must be local basenames")
            if hashlib.sha256((folder / name).read_bytes()).hexdigest() != expected:
                raise ValueError(f"Context recovery sealed input changed: {folder / name}")
    for name in (*INPUT_FILES, "reviewed-resources.json"):
        if name in ("view.json", "prompt.txt") or not (directory / name).exists():
            continue
        if (directory / name).read_bytes() != (attempt / name).read_bytes():
            raise ValueError(f"Context recovery changed original evidence: {name}")
    if (attempt / "prompt.txt").stat().st_size >= (directory / "prompt.txt").stat().st_size:
        raise ValueError("Context retry must reduce the inline context")
    from .scout_curation_runner import file_index_view
    expected_view, expected_index = file_index_view(json.loads((directory / "view.json").read_text()))
    if (json.loads((attempt / "view.json").read_text()) != expected_view
            or json.loads((attempt / "prior-resource-index.json").read_text()) != expected_index):
        raise ValueError("Context recovery view must preserve all candidates and identities")
    return attempt


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
                   allow_transport_retry: bool = True,
                   **worker_options: Any) -> Path:
    """Adopt surviving workers; allow at most one retry of a transport failure.

    A result, even an invalid one, is never regenerated here. Validation is the
    caller's responsibility. Authentication, quota, context and unknown failures
    stop for diagnosis. Retry inputs are byte-identical; failed output is retained.
    The on-disk attempt path is the budget, including across coordinator restarts.
    """
    context_attempt = reviewed_context_attempt(directory)
    if context_attempt is not None:
        # The normal path adopts an orphan and preserves a failed retry. No
        # nested context recovery is permitted; the plan allows one attempt.
        if (context_attempt / "reviewed-context-recovery.json").exists():
            raise ValueError("Nested context recovery is not permitted")
        return recover_result(context_attempt, execute, heartbeat=heartbeat,
                              timeout=timeout, allow_transport_retry=False, **worker_options)
    retry = directory / "transport-retry-1"
    for attempt in ((directory, retry) if allow_transport_retry else (directory,)):
        if attempt == retry:
            attempt.mkdir(exist_ok=True)
            for name in (*INPUT_FILES, "reviewed-resources.json", "prior-resource-index.json"):
                if not (directory / name).exists():
                    if name in INPUT_FILES:
                        raise ValueError(f"Missing retry input: {name}")
                    continue
                original = (directory / name).read_bytes()
                target = attempt / name
                if target.exists():
                    if target.read_bytes() != original:
                        raise ValueError(f"Retry sealed input changed: {target}")
                else:
                    with target.open("xb") as handle:
                        handle.write(original)
        if ((attempt / "events.jsonl").exists()
                and not (attempt / "execution.json").exists()
                and not (attempt / "orphan-recovery.json").exists()):
            # A crashed coordinator may have left its worker alive. Never start
            # another worker or inspect a half-written result until it exits.
            try:
                await_orphan(attempt, timeout, heartbeat)
            except TimeoutError as error:
                atomic_json(attempt / "failure.json", {
                    "kind": "timeout", "message": str(error), "retryable": False,
                })
                raise
            if (attempt / "worker.json").exists():
                worker = json.loads((attempt / "worker.json").read_text())
                atomic_json(attempt / "orphan-recovery.json", {
                    "workerPid": worker["pid"], "workerIdentity": worker.get("identity"),
                    "exitObservedAt": datetime.now(timezone.utc).isoformat(),
                    "exitCode": None, "elapsedSeconds": None,
                    "note": "Worker exited after its original coordinator; exact exit code and runtime unavailable.",
                })
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
        if attempt == retry or not allow_transport_retry:
            raise RuntimeError(f"Curation transport retry exhausted at {attempt}: {detail}")
        atomic_json(directory / "recovery-plan.json", {
            "kind": failure.kind, "reason": detail, "maximumRetries": 1,
            "retryDirectory": retry.name,
        })
    raise AssertionError("unreachable")
