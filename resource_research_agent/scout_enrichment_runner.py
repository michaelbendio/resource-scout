from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from .scout_enrichment import (
    enrichment_project_summary,
    next_scout_enrichment_assignment,
    next_scout_enrichment_reconciliation,
    save_scout_enrichment_result,
    save_scout_enrichment_reconciliation_result,
)
from .storage import ResearchStore


SCHEMA_PATH = Path(__file__).with_name("scout_enrichment_response.schema.json")
WORKER_MODEL = "gpt-5.5"


def _worker_prompt(assignment: dict[str, Any]) -> str:
    reconciliation = assignment.get("role") == "codex-audit-reconciliation"
    return "\n".join([
        "You are a fresh-context Resource Scout curation and enrichment worker.",
        (
            "Reconcile the sealed primary result with the independent external audit."
            if reconciliation else
            "Research this one resource independently using live web search."
        ),
        "Prefer official sources; use reliable government or referral sources when needed.",
        "Follow all three supplied section definitions, including their guidance text.",
        "Be concrete and useful for a human making a referral.",
        "If a detail cannot be confirmed, say that plainly instead of guessing.",
        "Do not inspect local files or ask the user a question.",
        "Do not rewrite Scout Findings; the application preserves it mechanically.",
        "Return only the JSON object required by the supplied output schema.",
        "Copy resourceId and assignmentSha256 exactly from the assignment.",
        "Use the current date in YYYY-MM-DD for each accessedOn value.",
        "",
        json.dumps(assignment, ensure_ascii=False, indent=2),
    ])


def _run_worker(
    assignment: dict[str, Any], *, codex_binary: str, model: str,
    timeout_seconds: int,
) -> str:
    with tempfile.TemporaryDirectory(prefix="scout-enrichment-") as directory:
        output_path = Path(directory) / "result.json"
        command = [
            codex_binary, "--search", "--ask-for-approval", "never",
            "--sandbox", "read-only", "exec", "--ephemeral",
            "--ignore-user-config", "--skip-git-repo-check", "--cd", directory,
            "--output-schema", str(SCHEMA_PATH),
            "--output-last-message", str(output_path), "--model", model, "-",
        ]
        completed = subprocess.run(
            command, input=_worker_prompt(assignment), text=True,
            capture_output=True, timeout=timeout_seconds, check=False,
        )
        if completed.returncode:
            detail = (completed.stderr or completed.stdout).strip()
            raise RuntimeError(
                f"Enrichment worker exited {completed.returncode}: {detail[-2000:]}"
            )
        if not output_path.exists():
            raise RuntimeError("Enrichment worker did not produce a result")
        return output_path.read_text(encoding="utf-8")


def run_enrichment(
    store: ResearchStore, project_id: int, *, codex_binary: str,
    model: str = WORKER_MODEL, timeout_seconds: int = 1800,
    retry_count: int = 2, max_resources: int | None = None,
) -> dict[str, Any]:
    completed = 0
    while max_resources is None or completed < max_resources:
        assignment = next_scout_enrichment_assignment(store, project_id)
        if assignment is None:
            assignment = next_scout_enrichment_reconciliation(store, project_id)
        if assignment is None:
            break
        reconciliation = assignment.get("role") == "codex-audit-reconciliation"
        error: Exception | None = None
        for attempt in range(1, retry_count + 2):
            try:
                raw_result = _run_worker(
                    assignment, codex_binary=codex_binary, model=model,
                    timeout_seconds=timeout_seconds,
                )
                summary = (
                    save_scout_enrichment_reconciliation_result(
                        store, project_id, raw_result
                    )
                    if reconciliation else
                    save_scout_enrichment_result(store, project_id, raw_result)
                )
                error = None
                break
            except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as caught:
                error = caught
                print(json.dumps({
                    "event": "worker-retry", "projectId": project_id,
                    "resourceId": assignment["resourceId"],
                    "phase": "reconciliation" if reconciliation else "primary",
                    "attempt": attempt,
                    "error": str(caught),
                }, ensure_ascii=False), flush=True)
        if error is not None:
            raise error
        completed += 1
        print(json.dumps({
            "event": (
                "reconciliation-completed" if reconciliation else "resource-completed"
            ), "projectId": project_id,
            "resourceId": assignment["resourceId"], "progress": summary["progress"],
        }, ensure_ascii=False), flush=True)
    project = store.get_scout_enrichment_project(project_id)
    if project is None:
        raise ValueError("Scout enrichment project not found")
    return enrichment_project_summary(project)


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(
        description="Enrich one Resource Scout resource per fresh Codex context"
    )
    value.add_argument("project_id", type=int)
    value.add_argument("--database", default="data/research-agent.sqlite3")
    value.add_argument("--codex-binary", default=shutil.which("codex") or "codex")
    value.add_argument("--model", default=WORKER_MODEL)
    value.add_argument("--timeout-seconds", type=int, default=1800)
    value.add_argument("--retry-count", type=int, default=2)
    value.add_argument("--max-resources", type=int)
    return value


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    summary = run_enrichment(
        ResearchStore(args.database), args.project_id,
        codex_binary=args.codex_binary, model=args.model,
        timeout_seconds=args.timeout_seconds, retry_count=args.retry_count,
        max_resources=args.max_resources,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
