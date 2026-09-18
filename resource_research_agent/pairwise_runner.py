from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from .codex_first_research import (
    codex_first_view,
    load_researcher_profile,
    next_codex_first_assignment,
    prepare_codex_first_plan,
    save_codex_first_external_result,
    save_codex_first_primary_result,
)
from .storage import ResearchStore


SCHEMA_PATH = Path(__file__).with_name("codex_replay_response.schema.json")
DEFAULT_CODEX_MODEL = "gpt-5.5"


def _codex_prompt(assignment: dict[str, Any]) -> str:
    research_pass = assignment["researchPass"]
    return "\n".join([
        "You are the fresh-context Codex primary researcher for Resource Scout.",
        "Research only the assignment below using live web search.",
        "Do not inspect local project files, the Scout database, prior sessions, or Scout APIs.",
        "Do not ask the user questions.",
        "Return only the JSON object required by the supplied output schema.",
        "Use empty strings for facts you cannot verify; do not invent them.",
        "",
        str(research_pass["assignment"]),
    ])


def _grok_prompt(assignment: dict[str, Any]) -> str:
    external = assignment["externalAssignment"]
    return "\n".join([
        "You are the fresh-context Grok challenger for Resource Scout.",
        "Research only the assignment below using live web research.",
        "Do not inspect local project files, the Scout database, prior sessions, or Scout APIs.",
        "Do not modify files, send messages, contact providers, or take external actions.",
        "Do not ask the user questions.",
        "Return exactly one JSON object with a leads array and no markdown fences or commentary.",
        "Every lead must contain organization, program, website, phone, address, leadType, "
        "locationOrServiceArea, whyRelevant, and uncertainty as text fields.",
        "Use empty strings for facts you cannot verify; do not invent them.",
        "",
        str(external["assignment"]),
    ])


def _run_codex_worker(
    assignment: dict[str, Any],
    *,
    codex_binary: str,
    model: str,
    timeout_seconds: int,
) -> str:
    with tempfile.TemporaryDirectory(prefix="scout-pairwise-codex-") as directory:
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
            "--model", model,
            "-",
        ]
        completed = subprocess.run(
            command,
            input=_codex_prompt(assignment),
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )
        if completed.returncode:
            detail = (completed.stderr or completed.stdout).strip()
            raise RuntimeError(
                f"Fresh Codex worker exited {completed.returncode}: {detail[-3000:]}"
            )
        if not output_path.exists():
            raise RuntimeError("Fresh Codex worker did not produce a result")
        value = json.loads(output_path.read_text(encoding="utf-8"))
        return json.dumps(value, ensure_ascii=False)


def _grok_command(
    grok_binary: str,
    prompt: str,
    *,
    directory: str,
    model: str,
) -> list[str]:
    command = [
        grok_binary,
        "--no-auto-update",
        "--no-alt-screen",
        "--always-approve",
        "--sandbox", "strict",
        "--cwd", directory,
        "-p", prompt,
        "--output-format", "plain",
    ]
    if model:
        command.extend(["--model", model])
    return command


def _run_grok_text(
    prompt: str,
    *,
    grok_binary: str,
    model: str,
    timeout_seconds: int,
) -> str:
    with tempfile.TemporaryDirectory(prefix="scout-pairwise-grok-") as directory:
        completed = subprocess.run(
            _grok_command(grok_binary, prompt, directory=directory, model=model),
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )
        if completed.returncode:
            detail = (completed.stderr or completed.stdout).strip()
            raise RuntimeError(
                f"Fresh Grok worker exited {completed.returncode}: {detail[-3000:]}"
            )
        raw = completed.stdout.strip()
        if not raw:
            detail = completed.stderr.strip()
            raise RuntimeError(
                "Fresh Grok worker returned no text"
                + (f": {detail[-2000:]}" if detail else "")
            )
        return raw


def _run_grok_worker(
    assignment: dict[str, Any],
    *,
    grok_binary: str,
    model: str,
    timeout_seconds: int,
) -> str:
    return _run_grok_text(
        _grok_prompt(assignment),
        grok_binary=grok_binary,
        model=model,
        timeout_seconds=timeout_seconds,
    )


def _grok_preflight(
    *,
    grok_binary: str,
    model: str,
    timeout_seconds: int,
) -> None:
    raw = _run_grok_text(
        "Return exactly the text GROK_READY and nothing else. Do not use tools.",
        grok_binary=grok_binary,
        model=model,
        timeout_seconds=min(timeout_seconds, 120),
    )
    if raw.strip() != "GROK_READY":
        raise RuntimeError(
            "Grok CLI preflight returned an unexpected response: " + raw[:500]
        )


def _run_with_retries(
    label: str,
    action: Any,
    *,
    retry_count: int,
    context: dict[str, Any],
) -> str:
    error: Exception | None = None
    for attempt in range(1, retry_count + 2):
        try:
            return str(action())
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as caught:
            error = caught
            print(json.dumps({
                "event": "worker-retry",
                "worker": label,
                "attempt": attempt,
                "error": str(caught),
                **context,
            }, ensure_ascii=False), flush=True)
    assert error is not None
    raise error


def run_pairwise(
    store: ResearchStore,
    import_id: int,
    *,
    profile: str,
    codex_binary: str,
    codex_model: str,
    grok_binary: str,
    grok_model: str,
    codex_timeout_seconds: int,
    grok_timeout_seconds: int,
    retry_count: int,
    max_passes: int | None,
    max_categories: int | None,
    grok_preflight: bool = True,
) -> dict[str, Any]:
    roster = load_researcher_profile(profile)
    primary = next(
        item["name"]
        for item in roster["researchers"]
        if item["role"] == "primary"
    )
    challengers = [
        item["name"]
        for item in roster["researchers"]
        if item["role"] == "challenger"
    ]
    if primary != "Codex" or challengers != ["Grok"]:
        raise ValueError(
            "The automated pairwise runner currently supports only codex-grok"
        )

    if not shutil.which(codex_binary) and not Path(codex_binary).exists():
        raise RuntimeError(f"Codex binary not found: {codex_binary}")
    if not shutil.which(grok_binary) and not Path(grok_binary).exists():
        raise RuntimeError(
            "Grok CLI not found. Install it from xAI, run grok login, "
            "then restart the pairwise runner."
        )

    if grok_preflight:
        print(json.dumps({
            "event": "grok-preflight-started",
            "profile": profile,
        }), flush=True)
        _grok_preflight(
            grok_binary=grok_binary,
            model=grok_model,
            timeout_seconds=grok_timeout_seconds,
        )
        print(json.dumps({
            "event": "grok-preflight-completed",
            "profile": profile,
        }), flush=True)

    prepare_codex_first_plan(store, import_id, roster=roster)
    starting_view = codex_first_view(store, import_id)
    starting_completed_categories = int(starting_view["completedCategories"])
    codex_passes_this_run = 0
    grok_challenges_this_run = 0

    while True:
        view = codex_first_view(store, import_id)
        completed_this_run = (
            int(view["completedCategories"]) - starting_completed_categories
        )
        if max_categories is not None and completed_this_run >= max_categories:
            break
        if max_passes is not None and codex_passes_this_run >= max_passes:
            break

        primary_assignment = next_codex_first_assignment(store, import_id, "Codex")
        if primary_assignment is not None:
            research_pass = primary_assignment["researchPass"]
            category = str(primary_assignment["job"]["categoryLabel"])
            focus_key = str(research_pass["focusKey"])
            print(json.dumps({
                "event": "codex-pass-started",
                "category": category,
                "focusKey": focus_key,
                "passKind": str(research_pass.get("passKind") or ""),
                "codexPassesThisRun": codex_passes_this_run,
            }, ensure_ascii=False), flush=True)
            raw = _run_with_retries(
                "Codex",
                lambda: _run_codex_worker(
                    primary_assignment,
                    codex_binary=codex_binary,
                    model=codex_model,
                    timeout_seconds=codex_timeout_seconds,
                ),
                retry_count=retry_count,
                context={"category": category, "focusKey": focus_key},
            )
            save_codex_first_primary_result(
                store,
                int(primary_assignment["job"]["id"]),
                focus_key,
                raw,
            )
            codex_passes_this_run += 1
            view = codex_first_view(store, import_id)
            print(json.dumps({
                "event": "codex-pass-completed",
                "category": category,
                "focusKey": focus_key,
                "codexPassesThisRun": codex_passes_this_run,
                "completedCategories": view["completedCategories"],
                "totalCategories": view["totalCategories"],
            }, ensure_ascii=False), flush=True)
            continue

        grok_assignment = next_codex_first_assignment(store, import_id, "Grok")
        if grok_assignment is not None:
            external = grok_assignment["externalAssignment"]
            category = str(grok_assignment["job"]["categoryLabel"])
            assignment_id = int(external["id"])
            print(json.dumps({
                "event": "grok-challenge-started",
                "category": category,
                "assignmentId": assignment_id,
                "grokChallengesThisRun": grok_challenges_this_run,
            }, ensure_ascii=False), flush=True)
            raw = _run_with_retries(
                "Grok",
                lambda: _run_grok_worker(
                    grok_assignment,
                    grok_binary=grok_binary,
                    model=grok_model,
                    timeout_seconds=grok_timeout_seconds,
                ),
                retry_count=retry_count,
                context={
                    "category": category,
                    "assignmentId": assignment_id,
                },
            )
            saved = save_codex_first_external_result(store, assignment_id, raw)
            grok_challenges_this_run += 1
            view = codex_first_view(store, import_id)
            print(json.dumps({
                "event": "grok-challenge-completed",
                "category": category,
                "assignmentId": assignment_id,
                "leadCount": int(saved["leadCount"]),
                "grokChallengesThisRun": grok_challenges_this_run,
                "completedCategories": view["completedCategories"],
                "totalCategories": view["totalCategories"],
            }, ensure_ascii=False), flush=True)
            continue

        break

    view = codex_first_view(store, import_id)
    print(json.dumps({
        "event": "pairwise-run-stopped",
        "profile": profile,
        "status": view["status"],
        "completedCategories": view["completedCategories"],
        "totalCategories": view["totalCategories"],
        "codexPassesThisRun": codex_passes_this_run,
        "grokChallengesThisRun": grok_challenges_this_run,
    }, ensure_ascii=False), flush=True)
    return view


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(
        description="Run lock-step Codex + Grok Resource Scout research"
    )
    value.add_argument("--database", default="data/research-agent.sqlite3")
    value.add_argument("--import-id", type=int)
    value.add_argument("--profile", default="codex-grok", choices=("codex-grok",))
    value.add_argument("--codex-binary", default=shutil.which("codex") or "codex")
    value.add_argument("--codex-model", default=DEFAULT_CODEX_MODEL)
    value.add_argument("--grok-binary", default=shutil.which("grok") or "grok")
    value.add_argument(
        "--grok-model",
        default="",
        help="Optional Grok model override; blank uses the CLI default",
    )
    value.add_argument("--codex-timeout-seconds", type=int, default=1800)
    value.add_argument("--grok-timeout-seconds", type=int, default=1800)
    value.add_argument("--retry-count", type=int, default=2)
    value.add_argument("--max-passes", type=int)
    value.add_argument(
        "--max-categories",
        type=int,
        help="Stop after this many fully completed Codex+Grok categories",
    )
    value.add_argument(
        "--skip-grok-preflight",
        action="store_true",
        help="Skip the small Grok authentication/readiness probe",
    )
    return value


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    store = ResearchStore(args.database)
    import_id = int(args.import_id or store.latest_import_id() or 0)
    if not import_id:
        raise SystemExit("Import a resource package before running pairwise research")
    run_pairwise(
        store,
        import_id,
        profile=args.profile,
        codex_binary=args.codex_binary,
        codex_model=args.codex_model,
        grok_binary=args.grok_binary,
        grok_model=args.grok_model,
        codex_timeout_seconds=args.codex_timeout_seconds,
        grok_timeout_seconds=args.grok_timeout_seconds,
        retry_count=args.retry_count,
        max_passes=args.max_passes,
        max_categories=args.max_categories,
        grok_preflight=not args.skip_grok_preflight,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
