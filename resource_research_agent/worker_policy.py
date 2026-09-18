"""Explicit worker exclusions requested by the operator, independent of rosters."""
from __future__ import annotations


DISABLED_WORKERS = {
    "claude": "Michael disabled all Claude work in Scout after unexpected Anthropic charges on 2026-09-18.",
}


class WorkerDisabledError(RuntimeError):
    pass


def assert_worker_enabled(provider: str) -> None:
    reason = DISABLED_WORKERS.get(provider.strip().casefold())
    if reason:
        raise WorkerDisabledError(
            f"{provider} execution is disabled. {reason} "
            "This includes preflights and probes. Preserve existing results; use Codex+Grok. "
            "Re-enabling requires an explicit new instruction from Michael."
        )
