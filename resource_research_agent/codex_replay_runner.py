from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from .codex_replay import (
    codex_replay_view,
    next_codex_replay_assignment,
    reveal_and_complete_codex_replay,
    save_codex_replay_result,
)
from .storage import ResearchStore


SCHEMA_PATH = Path(__file__).with_name("codex_replay_response.schema.json")
WORKER_MODEL = "gpt-5.5"


def _worker_prompt(assignment: dict[str, Any]) -> str:
    return "\n".join([
        "You are the fresh-context Codex worker for one sealed Resource Scout replay pass.",
        "Research only the assignment below using live web search.",
        "Do not inspect any local project file, database, prior session, or Scout API.",
        "Do not try to infer a held-out answer key or ask the user a question.",
        "Return only the JSON object required by the supplied output schema.",
        "Use empty strings for facts you cannot verify; do not invent them.",
        "",
        str(assignment["researchPass"]["assignment"]),
    ])


def _run_fresh_worker(
    assignment: dict[str, Any],
    *,
    codex_binary: str,
    model: str,
    timeout_seconds: int,
) -> str:
    with tempfile.TemporaryDirectory(prefix="scout-codex-replay-") as directory:
        output_path = Path(directory) / "result.json"
        command = [
            codex_binary,
            "--search",
            "--ask-for-approval", "never",
            "--sandbox", "read-only",
            "exec",
            "--ephemeral",
            "--ignore-user-config",
            "--skip-git-repo-check",
            "--cd", directory,
            "--output-schema", str(SCHEMA_PATH),
            "--output-last-message", str(output_path),
        ]
        command.extend(["--model", model])
        command.append("-")
        completed = subprocess.run(
            command,
            input=_worker_prompt(assignment),
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )
        if completed.returncode:
            detail = (completed.stderr or completed.stdout).strip()
            raise RuntimeError(
                f"Fresh Codex worker exited {completed.returncode}: {detail[-2000:]}"
            )
        if not output_path.exists():
            raise RuntimeError("Fresh Codex worker did not produce a result")
        value = json.loads(output_path.read_text(encoding="utf-8"))
        return json.dumps(value, ensure_ascii=False)


def run_replay(
    store: ResearchStore,
    study_id: int,
    *,
    codex_binary: str,
    model: str = WORKER_MODEL,
    timeout_seconds: int = 1800,
    retry_count: int = 2,
    max_passes: int | None = None,
    reveal: bool = False,
) -> dict[str, Any]:
    completed_passes = 0
    while max_passes is None or completed_passes < max_passes:
        assignment = next_codex_replay_assignment(store, study_id)
        if assignment is None:
            break
        error: Exception | None = None
        for attempt in range(1, retry_count + 2):
            try:
                raw_text = _run_fresh_worker(
                    assignment,
                    codex_binary=codex_binary,
                    model=model,
                    timeout_seconds=timeout_seconds,
                )
                save_codex_replay_result(
                    store,
                    study_id,
                    int(assignment["jobId"]),
                    str(assignment["researchPass"]["focusKey"]),
                    raw_text,
                )
                error = None
                break
            except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as caught:
                error = caught
                print(json.dumps({
                    "event": "worker-retry",
                    "studyId": study_id,
                    "category": assignment["categoryLabel"],
                    "focusKey": assignment["researchPass"]["focusKey"],
                    "attempt": attempt,
                    "error": str(caught),
                }, ensure_ascii=False), flush=True)
        if error is not None:
            raise error
        completed_passes += 1
        view = codex_replay_view(store, study_id)
        job = next(
            item["v2Job"] for item in view["categories"]
            if int(item["v2JobId"]) == int(assignment["jobId"])
        )
        print(json.dumps({
            "event": "pass-completed",
            "studyId": study_id,
            "category": assignment["categoryLabel"],
            "focusKey": assignment["researchPass"]["focusKey"],
            "categoryPasses": job["progress"],
            "studyProgress": view["progress"],
        }, ensure_ascii=False), flush=True)

    view = codex_replay_view(store, study_id)
    if reveal and view["status"] == "codex-closed":
        view = reveal_and_complete_codex_replay(store, study_id)
        print(json.dumps({
            "event": "replay-completed",
            "studyId": study_id,
            "status": view["status"],
            "progress": view["progress"],
            "reportSha256": view["reportSha256"],
        }, ensure_ascii=False), flush=True)
    return view


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(
        description="Run a sealed Codex replay with one ephemeral Codex context per pass"
    )
    value.add_argument("study_id", type=int)
    value.add_argument("--database", default="data/research.sqlite3")
    value.add_argument("--codex-binary", default=shutil.which("codex") or "codex")
    value.add_argument("--model", default=WORKER_MODEL)
    value.add_argument("--timeout-seconds", type=int, default=1800)
    value.add_argument("--retry-count", type=int, default=2)
    value.add_argument("--max-passes", type=int)
    value.add_argument("--reveal", action="store_true")
    return value


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    view = run_replay(
        ResearchStore(args.database),
        args.study_id,
        codex_binary=args.codex_binary,
        model=args.model,
        timeout_seconds=args.timeout_seconds,
        retry_count=args.retry_count,
        max_passes=args.max_passes,
        reveal=args.reveal,
    )
    print(json.dumps({
        "studyId": view["id"],
        "status": view["status"],
        "progress": view["progress"],
    }, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
