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
    save_codex_first_primary_result,
)
from .storage import ResearchStore


SCHEMA_PATH = Path(__file__).with_name("codex_replay_response.schema.json")
DEFAULT_MODEL = "gpt-5.6-codex"


def _worker_prompt(assignment: dict[str, Any]) -> str:
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
            input=_worker_prompt(assignment),
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


def _slug(value: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "-" for ch in value).strip("-")


def export_pending_challenges(
    store: ResearchStore,
    import_id: int,
    output_dir: Path,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    view = codex_first_view(store, import_id)
    exported: list[dict[str, Any]] = []
    for category in view.get("categories") or []:
        job = store.get_focused_research_job(int(category["jobId"]))
        if not job:
            continue
        for item in store.list_codex_first_assignments(int(category["jobId"])):
            if item["role"] != "challenger" or item["status"] == "completed":
                continue
            filename = (
                f"{int(item['id']):04d}-"
                f"{_slug(str(category['categoryLabel']))}-"
                f"{_slug(str(item['researcher']))}.txt"
            )
            path = output_dir / filename
            path.write_text(str(item["assignment"]), encoding="utf-8")
            exported.append({
                "assignmentId": int(item["id"]),
                "jobId": int(category["jobId"]),
                "categoryId": str(category["categoryId"]),
                "categoryLabel": str(category["categoryLabel"]),
                "researcher": str(item["researcher"]),
                "assignmentFile": filename,
            })
    manifest = {
        "schemaVersion": 1,
        "importId": int(import_id),
        "pendingChallenges": exported,
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return manifest


def run_primary(
    store: ResearchStore,
    import_id: int,
    *,
    profile: str,
    codex_binary: str,
    model: str,
    timeout_seconds: int,
    retry_count: int,
    max_passes: int | None,
    challenge_dir: Path,
) -> dict[str, Any]:
    roster = load_researcher_profile(profile)
    primary = next(
        item["name"]
        for item in roster["researchers"]
        if item["role"] == "primary"
    )
    if primary != "Codex":
        raise ValueError(
            f"Profile {profile} uses {primary} as primary. "
            "This runner currently automates Codex-primary profiles only."
        )

    prepare_codex_first_plan(store, import_id, roster=roster)
    completed = 0
    while max_passes is None or completed < max_passes:
        assignment = next_codex_first_assignment(store, import_id, "Codex")
        if assignment is None:
            break
        if assignment["kind"] != "primary":
            break

        research_pass = assignment["researchPass"]
        error: Exception | None = None
        for attempt in range(1, retry_count + 2):
            try:
                raw = _run_codex_worker(
                    assignment,
                    codex_binary=codex_binary,
                    model=model,
                    timeout_seconds=timeout_seconds,
                )
                save_codex_first_primary_result(
                    store,
                    int(assignment["job"]["id"]),
                    str(research_pass["focusKey"]),
                    raw,
                )
                error = None
                break
            except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as caught:
                error = caught
                print(json.dumps({
                    "event": "worker-retry",
                    "category": assignment["job"]["categoryLabel"],
                    "focusKey": research_pass["focusKey"],
                    "attempt": attempt,
                    "error": str(caught),
                }, ensure_ascii=False), flush=True)
        if error is not None:
            raise error

        completed += 1
        view = codex_first_view(store, import_id)
        print(json.dumps({
            "event": "primary-pass-completed",
            "category": assignment["job"]["categoryLabel"],
            "focusKey": research_pass["focusKey"],
            "completedPassesThisRun": completed,
            "completedCategories": view["completedCategories"],
            "totalCategories": view["totalCategories"],
        }, ensure_ascii=False), flush=True)

    manifest = export_pending_challenges(store, import_id, challenge_dir)
    view = codex_first_view(store, import_id)
    print(json.dumps({
        "event": "primary-run-stopped",
        "profile": profile,
        "status": view["status"],
        "completedCategories": view["completedCategories"],
        "totalCategories": view["totalCategories"],
        "pendingChallenges": len(manifest["pendingChallenges"]),
        "challengeDirectory": str(challenge_dir),
    }, ensure_ascii=False), flush=True)
    return view


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(
        description="Run Codex primary passes for a Resource Scout pairwise experiment"
    )
    value.add_argument("--database", default="data/research-agent.sqlite3")
    value.add_argument("--import-id", type=int)
    value.add_argument(
        "--profile",
        default="codex-grok",
        choices=("codex-grok", "codex-claude"),
    )
    value.add_argument("--codex-binary", default=shutil.which("codex") or "codex")
    value.add_argument("--model", default=DEFAULT_MODEL)
    value.add_argument("--timeout-seconds", type=int, default=1800)
    value.add_argument("--retry-count", type=int, default=2)
    value.add_argument("--max-passes", type=int)
    value.add_argument(
        "--challenge-dir",
        default="data/pairwise-challenges",
        type=Path,
    )
    return value


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    store = ResearchStore(args.database)
    import_id = int(args.import_id or store.latest_import_id() or 0)
    if not import_id:
        raise SystemExit("Import a resource package before running pairwise research")
    run_primary(
        store,
        import_id,
        profile=args.profile,
        codex_binary=args.codex_binary,
        model=args.model,
        timeout_seconds=args.timeout_seconds,
        retry_count=args.retry_count,
        max_passes=args.max_passes,
        challenge_dir=args.challenge_dir,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
