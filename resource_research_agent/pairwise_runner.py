from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Callable

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


def _research_prompt(
    assignment_text: str,
    researcher: str,
    role: str,
) -> str:
    return "\n".join([
        f"You are the fresh-context {researcher} {role} researcher for Resource Scout.",
        "Research only the assignment below using live web research.",
        "Search broadly and verify consequential claims with authoritative sources.",
        "Do not inspect local project files, the Scout database, prior sessions, or Scout APIs.",
        "Do not modify files, send messages, contact providers, or take external actions.",
        "Do not ask the user questions.",
        "Return exactly one JSON object with a leads array and no markdown fences or commentary.",
        "Every lead must contain organization, program, website, phone, address, leadType, "
        "locationOrServiceArea, whyRelevant, and uncertainty as text fields.",
        "leadType must be one of program, provider-organization, access-point, routing-source, or directory.",
        "Use empty strings for facts you cannot verify; do not invent them.",
        *(
            [
                "Do not try to use Bash, shell commands, local-file tools, curl, or pdftotext.",
                "If a PDF or page cannot be usefully read with WebFetch, find an alternate authoritative web source or record the limitation in uncertainty.",
                "Finish the requested JSON once coverage is strong; do not keep searching merely to exhaust every possible lead.",
            ]
            if researcher == "Claude"
            else []
        ),
        "",
        assignment_text,
    ])


def _run_codex_worker(
    assignment_text: str,
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
        ]
        if model:
            command.extend(["--model", model])
        command.append("-")
        completed = subprocess.run(
            command,
            input=_research_prompt(assignment_text, "Codex", "primary"),
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
    assignment_text: str,
    *,
    role: str,
    grok_binary: str,
    model: str,
    timeout_seconds: int,
) -> str:
    return _run_grok_text(
        _research_prompt(assignment_text, "Grok", role),
        grok_binary=grok_binary,
        model=model,
        timeout_seconds=timeout_seconds,
    )


def _claude_command(
    claude_binary: str,
    prompt: str,
    *,
    model: str,
    max_turns: int,
) -> list[str]:
    command = [
        claude_binary,
        "-p", prompt,
        "--output-format", "json",
        "--max-turns", str(max_turns),
        "--allowedTools", "WebSearch,WebFetch",
    ]
    if model:
        command.extend(["--model", model])
    return command


def _run_claude_text(
    prompt: str,
    *,
    claude_binary: str,
    model: str,
    timeout_seconds: int,
    max_turns: int,
) -> str:
    with tempfile.TemporaryDirectory(prefix="scout-pairwise-claude-") as directory:
        env = dict(os.environ)
        env["DISABLE_AUTOUPDATER"] = "1"
        completed = subprocess.run(
            _claude_command(
                claude_binary,
                prompt,
                model=model,
                max_turns=max_turns,
            ),
            cwd=directory,
            env=env,
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )
        if completed.returncode:
            detail = (completed.stderr or completed.stdout).strip()
            raise RuntimeError(
                f"Fresh Claude worker exited {completed.returncode}: {detail[-3000:]}"
            )
        try:
            envelope = json.loads(completed.stdout)
        except json.JSONDecodeError as error:
            raise RuntimeError(
                "Fresh Claude worker did not return its JSON envelope: "
                + completed.stdout[-2000:]
            ) from error
        if envelope.get("is_error"):
            raise RuntimeError(
                "Fresh Claude worker reported an error: "
                + str(envelope.get("result") or envelope)[-2000:]
            )
        raw = str(envelope.get("result") or "").strip()
        if not raw:
            raise RuntimeError("Fresh Claude worker returned no result text")
        return raw


def _run_claude_worker(
    assignment_text: str,
    *,
    role: str,
    claude_binary: str,
    model: str,
    timeout_seconds: int,
    max_turns: int,
) -> str:
    return _run_claude_text(
        _research_prompt(assignment_text, "Claude", role),
        claude_binary=claude_binary,
        model=model,
        timeout_seconds=timeout_seconds,
        max_turns=max_turns,
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


def _claude_preflight(
    *,
    claude_binary: str,
    model: str,
    timeout_seconds: int,
    max_turns: int,
) -> None:
    raw = _run_claude_text(
        "Use WebSearch once to search for Anthropic, then return exactly CLAUDE_WEB_READY and nothing else.",
        claude_binary=claude_binary,
        model=model,
        timeout_seconds=min(timeout_seconds, 180),
        max_turns=max(3, min(max_turns, 5)),
    )
    if raw.strip() != "CLAUDE_WEB_READY":
        raise RuntimeError(
            "Claude CLI preflight returned an unexpected response: " + raw[:500]
        )


def _run_with_retries(
    label: str,
    action: Callable[[], str],
    *,
    retry_count: int,
    context: dict[str, Any],
) -> str:
    error: Exception | None = None
    for attempt in range(1, retry_count + 2):
        try:
            return action()
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as caught:
            error = caught
            final_attempt = attempt >= retry_count + 1
            print(json.dumps({
                "event": "worker-retry" if not final_attempt else "worker-failed",
                "worker": label,
                "attempt": attempt,
                "error": str(caught),
                **context,
            }, ensure_ascii=False), flush=True)
            if not final_attempt:
                time.sleep(min(60, 5 * (2 ** (attempt - 1))))
    assert error is not None
    raise error


def _binary_available(value: str) -> bool:
    return bool(shutil.which(value) or Path(value).exists())


def _run_provider(
    provider: str,
    assignment_text: str,
    *,
    role: str,
    codex_binary: str,
    codex_model: str,
    grok_binary: str,
    grok_model: str,
    claude_binary: str,
    claude_model: str,
    codex_timeout_seconds: int,
    grok_timeout_seconds: int,
    claude_timeout_seconds: int,
    claude_max_turns: int,
) -> str:
    if provider == "Codex":
        return _run_codex_worker(
            assignment_text,
            codex_binary=codex_binary,
            model=codex_model,
            timeout_seconds=codex_timeout_seconds,
        )
    if provider == "Grok":
        return _run_grok_worker(
            assignment_text,
            role=role,
            grok_binary=grok_binary,
            model=grok_model,
            timeout_seconds=grok_timeout_seconds,
        )
    if provider == "Claude":
        return _run_claude_worker(
            assignment_text,
            role=role,
            claude_binary=claude_binary,
            model=claude_model,
            timeout_seconds=claude_timeout_seconds,
            max_turns=claude_max_turns,
        )
    raise ValueError(f"Unsupported automated researcher: {provider}")


def run_pairwise(
    store: ResearchStore,
    import_id: int,
    *,
    profile: str,
    codex_binary: str,
    codex_model: str,
    grok_binary: str,
    grok_model: str,
    claude_binary: str,
    claude_model: str,
    codex_timeout_seconds: int,
    grok_timeout_seconds: int,
    claude_timeout_seconds: int,
    claude_max_turns: int,
    retry_count: int,
    max_passes: int | None,
    max_categories: int | None,
    preflight: bool = True,
) -> dict[str, Any]:
    roster = load_researcher_profile(profile)
    primary = next(
        str(item["name"])
        for item in roster["researchers"]
        if item["role"] == "primary"
    )
    challengers = [
        str(item["name"])
        for item in roster["researchers"]
        if item["role"] == "challenger"
    ]
    if len(challengers) != 1:
        raise ValueError("Automated pairwise profiles require exactly one challenger")
    challenger = challengers[0]
    enabled = {primary, challenger}

    binaries = {
        "Codex": codex_binary,
        "Grok": grok_binary,
        "Claude": claude_binary,
    }
    for provider in enabled:
        if not _binary_available(binaries[provider]):
            raise RuntimeError(
                f"{provider} CLI not found: {binaries[provider]}"
            )

    if preflight:
        if "Grok" in enabled:
            print(json.dumps({"event": "grok-preflight-started", "profile": profile}), flush=True)
            _grok_preflight(
                grok_binary=grok_binary,
                model=grok_model,
                timeout_seconds=grok_timeout_seconds,
            )
            print(json.dumps({"event": "grok-preflight-completed", "profile": profile}), flush=True)
        if "Claude" in enabled:
            print(json.dumps({"event": "claude-preflight-started", "profile": profile}), flush=True)
            _claude_preflight(
                claude_binary=claude_binary,
                model=claude_model,
                timeout_seconds=claude_timeout_seconds,
                max_turns=claude_max_turns,
            )
            print(json.dumps({"event": "claude-preflight-completed", "profile": profile}), flush=True)

    prepare_codex_first_plan(store, import_id, roster=roster)
    primary_passes_this_run = 0
    challenger_runs_this_run = 0

    while True:
        view = codex_first_view(store, import_id)
        if (
            max_categories is not None
            and int(view["completedCategories"]) >= max_categories
        ):
            break
        if max_passes is not None and primary_passes_this_run >= max_passes:
            break

        primary_assignment = next_codex_first_assignment(store, import_id, primary)
        if primary_assignment is not None:
            research_pass = primary_assignment["researchPass"]
            category = str(primary_assignment["job"]["categoryLabel"])
            focus_key = str(research_pass["focusKey"])
            assignment_text = str(research_pass["assignment"])
            print(json.dumps({
                "event": "primary-pass-started",
                "profile": profile,
                "researcher": primary,
                "category": category,
                "focusKey": focus_key,
                "passKind": str(research_pass.get("passKind") or ""),
                "primaryPassesThisRun": primary_passes_this_run,
            }, ensure_ascii=False), flush=True)
            raw = _run_with_retries(
                primary,
                lambda: _run_provider(
                    primary,
                    assignment_text,
                    role="primary",
                    codex_binary=codex_binary,
                    codex_model=codex_model,
                    grok_binary=grok_binary,
                    grok_model=grok_model,
                    claude_binary=claude_binary,
                    claude_model=claude_model,
                    codex_timeout_seconds=codex_timeout_seconds,
                    grok_timeout_seconds=grok_timeout_seconds,
                    claude_timeout_seconds=claude_timeout_seconds,
                    claude_max_turns=claude_max_turns,
                ),
                retry_count=retry_count,
                context={"profile": profile, "category": category, "focusKey": focus_key},
            )
            save_codex_first_primary_result(
                store,
                int(primary_assignment["job"]["id"]),
                focus_key,
                raw,
            )
            primary_passes_this_run += 1
            view = codex_first_view(store, import_id)
            print(json.dumps({
                "event": "primary-pass-completed",
                "profile": profile,
                "researcher": primary,
                "category": category,
                "focusKey": focus_key,
                "primaryPassesThisRun": primary_passes_this_run,
                "completedCategories": view["completedCategories"],
                "totalCategories": view["totalCategories"],
            }, ensure_ascii=False), flush=True)
            continue

        challenger_assignment = next_codex_first_assignment(
            store, import_id, challenger
        )
        if challenger_assignment is not None:
            external = challenger_assignment["externalAssignment"]
            category = str(challenger_assignment["job"]["categoryLabel"])
            assignment_id = int(external["id"])
            assignment_text = str(external["assignment"])
            print(json.dumps({
                "event": "challenger-started",
                "profile": profile,
                "researcher": challenger,
                "category": category,
                "assignmentId": assignment_id,
                "challengerRunsThisRun": challenger_runs_this_run,
            }, ensure_ascii=False), flush=True)
            raw = _run_with_retries(
                challenger,
                lambda: _run_provider(
                    challenger,
                    assignment_text,
                    role="challenger",
                    codex_binary=codex_binary,
                    codex_model=codex_model,
                    grok_binary=grok_binary,
                    grok_model=grok_model,
                    claude_binary=claude_binary,
                    claude_model=claude_model,
                    codex_timeout_seconds=codex_timeout_seconds,
                    grok_timeout_seconds=grok_timeout_seconds,
                    claude_timeout_seconds=claude_timeout_seconds,
                    claude_max_turns=claude_max_turns,
                ),
                retry_count=retry_count,
                context={
                    "profile": profile,
                    "category": category,
                    "assignmentId": assignment_id,
                },
            )
            saved = save_codex_first_external_result(store, assignment_id, raw)
            challenger_runs_this_run += 1
            view = codex_first_view(store, import_id)
            print(json.dumps({
                "event": "challenger-completed",
                "profile": profile,
                "researcher": challenger,
                "category": category,
                "assignmentId": assignment_id,
                "leadCount": int(saved["leadCount"]),
                "challengerRunsThisRun": challenger_runs_this_run,
                "completedCategories": view["completedCategories"],
                "totalCategories": view["totalCategories"],
            }, ensure_ascii=False), flush=True)
            continue

        break

    view = codex_first_view(store, import_id)
    print(json.dumps({
        "event": "pairwise-run-stopped",
        "profile": profile,
        "primary": primary,
        "challenger": challenger,
        "status": view["status"],
        "completedCategories": view["completedCategories"],
        "totalCategories": view["totalCategories"],
        "primaryPassesThisRun": primary_passes_this_run,
        "challengerRunsThisRun": challenger_runs_this_run,
    }, ensure_ascii=False), flush=True)
    return view


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(
        description="Run one lock-step Resource Scout pairwise research condition"
    )
    value.add_argument("--database", default="data/research-agent.sqlite3")
    value.add_argument("--import-id", type=int)
    value.add_argument(
        "--profile",
        default="codex-grok",
        choices=("codex-grok", "codex-claude", "claude-grok"),
    )
    value.add_argument("--codex-binary", default=shutil.which("codex") or "codex")
    value.add_argument("--codex-model", default=DEFAULT_CODEX_MODEL)
    value.add_argument("--grok-binary", default=shutil.which("grok") or "grok")
    value.add_argument("--grok-model", default="")
    value.add_argument("--claude-binary", default=shutil.which("claude") or "claude")
    value.add_argument("--claude-model", default="")
    value.add_argument("--codex-timeout-seconds", type=int, default=1800)
    value.add_argument("--grok-timeout-seconds", type=int, default=1800)
    value.add_argument("--claude-timeout-seconds", type=int, default=1800)
    value.add_argument("--claude-max-turns", type=int, default=60)
    value.add_argument("--retry-count", type=int, default=3)
    value.add_argument("--max-passes", type=int)
    value.add_argument(
        "--max-categories",
        type=int,
        help="Stop after this many fully completed pairwise categories",
    )
    value.add_argument(
        "--skip-preflight",
        action="store_true",
        help="Skip provider authentication/readiness probes",
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
        claude_binary=args.claude_binary,
        claude_model=args.claude_model,
        codex_timeout_seconds=args.codex_timeout_seconds,
        grok_timeout_seconds=args.grok_timeout_seconds,
        claude_timeout_seconds=args.claude_timeout_seconds,
        claude_max_turns=args.claude_max_turns,
        retry_count=args.retry_count,
        max_passes=args.max_passes,
        max_categories=args.max_categories,
        preflight=not args.skip_preflight,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
