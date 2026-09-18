from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .codex_first_research import codex_first_view
from .pairwise_runner import (
    DEFAULT_CODEX_MODEL,
    _binary_available,
    _claude_preflight,
    _grok_preflight,
)
from .storage import ResearchStore


PROFILES = ("codex-grok", "codex-claude", "claude-grok")
IMPORT_TABLES = (
    "imports",
    "categories",
    "imported_resources",
    "known_terms",
    "research_seeds",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def clone_import_baseline(
    seed_database: Path,
    seed_import_id: int,
    destination: Path,
) -> int:
    if destination.exists():
        raise FileExistsError(f"Refusing to overwrite experiment database: {destination}")
    ResearchStore(destination)
    with sqlite3.connect(destination) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("ATTACH DATABASE ? AS seed", (str(seed_database.resolve()),))
        try:
            row = connection.execute(
                "SELECT id FROM seed.imports WHERE id = ?",
                (seed_import_id,),
            ).fetchone()
            if not row:
                raise ValueError(
                    f"Import {seed_import_id} not found in {seed_database}"
                )
            connection.execute(
                "INSERT INTO imports SELECT * FROM seed.imports WHERE id = ?",
                (seed_import_id,),
            )
            for table in IMPORT_TABLES[1:]:
                connection.execute(
                    f"INSERT INTO {table} "
                    f"SELECT * FROM seed.{table} WHERE import_id = ? ORDER BY rowid",
                    (seed_import_id,),
                )
            connection.commit()
        finally:
            connection.execute("DETACH DATABASE seed")
    return seed_import_id


def _condition_summary(
    profile: str,
    database: Path,
    *,
    returncode: int,
    started_at: str,
    completed_at: str,
    elapsed_seconds: float,
    log_file: Path,
) -> dict[str, Any]:
    store = ResearchStore(database)
    import_id = int(store.latest_import_id() or 0)
    view = codex_first_view(store, import_id) if import_id else {
        "status": "not-started",
        "completedCategories": 0,
        "totalCategories": 0,
        "categories": [],
    }
    primary_leads = sum(
        int(category["primary"]["leadCount"])
        for category in view.get("categories") or []
    )
    challenger_leads = sum(
        int(researcher.get("leadCount") or 0)
        for category in view.get("categories") or []
        for researcher in category.get("researchers") or []
        if researcher.get("role") == "challenger"
    )
    return {
        "profile": profile,
        "returnCode": returncode,
        "processStatus": "success" if returncode == 0 else "failed",
        "researchStatus": view.get("status"),
        "completedCategories": int(view.get("completedCategories") or 0),
        "totalCategories": int(view.get("totalCategories") or 0),
        "primaryLeadCount": primary_leads,
        "challengerLeadCount": challenger_leads,
        "totalLeadCount": primary_leads + challenger_leads,
        "startedAt": started_at,
        "completedAt": completed_at,
        "elapsedSeconds": round(elapsed_seconds, 3),
        "database": str(database),
        "logFile": str(log_file),
    }


def run_supervisor(
    *,
    seed_database: Path,
    seed_import_id: int,
    output_dir: Path,
    max_categories: int,
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
    stagger_seconds: int,
) -> dict[str, Any]:
    if not seed_database.exists():
        raise FileNotFoundError(f"Seed database not found: {seed_database}")
    for name, binary in (
        ("Codex", codex_binary),
        ("Grok", grok_binary),
        ("Claude", claude_binary),
    ):
        if not _binary_available(binary):
            raise RuntimeError(f"{name} CLI not found: {binary}")

    print(json.dumps({"event": "supervisor-preflight", "provider": "Grok"}), flush=True)
    _grok_preflight(
        grok_binary=grok_binary,
        model=grok_model,
        timeout_seconds=grok_timeout_seconds,
    )
    print(json.dumps({"event": "supervisor-preflight-completed", "provider": "Grok"}), flush=True)

    print(json.dumps({"event": "supervisor-preflight", "provider": "Claude"}), flush=True)
    _claude_preflight(
        claude_binary=claude_binary,
        model=claude_model,
        timeout_seconds=claude_timeout_seconds,
        max_turns=claude_max_turns,
    )
    print(json.dumps({"event": "supervisor-preflight-completed", "provider": "Claude"}), flush=True)

    output_dir.mkdir(parents=True, exist_ok=False)
    databases: dict[str, Path] = {}
    logs: dict[str, Path] = {}
    for profile in PROFILES:
        database = output_dir / f"{profile}.sqlite3"
        clone_import_baseline(seed_database, seed_import_id, database)
        databases[profile] = database
        logs[profile] = output_dir / f"{profile}.log"

    manifest = {
        "schemaVersion": 1,
        "createdAt": _utc_now(),
        "seedDatabase": str(seed_database.resolve()),
        "seedImportId": seed_import_id,
        "profiles": list(PROFILES),
        "maxCategories": max_categories,
        "codexModel": codex_model,
        "grokModel": grok_model or "cli-default",
        "claudeModel": claude_model or "cli-default",
        "databases": {profile: str(path) for profile, path in databases.items()},
        "logs": {profile: str(path) for profile, path in logs.items()},
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    processes: dict[str, subprocess.Popen[str]] = {}
    handles: dict[str, Any] = {}
    started: dict[str, tuple[str, float]] = {}

    for index, profile in enumerate(PROFILES):
        if index and stagger_seconds:
            time.sleep(stagger_seconds)
        handle = logs[profile].open("w", encoding="utf-8")
        handles[profile] = handle
        command = [
            sys.executable,
            "-m", "resource_research_agent.pairwise_runner",
            "--database", str(databases[profile]),
            "--import-id", str(seed_import_id),
            "--profile", profile,
            "--max-categories", str(max_categories),
            "--codex-binary", codex_binary,
            "--codex-model", codex_model,
            "--grok-binary", grok_binary,
            "--claude-binary", claude_binary,
            "--codex-timeout-seconds", str(codex_timeout_seconds),
            "--grok-timeout-seconds", str(grok_timeout_seconds),
            "--claude-timeout-seconds", str(claude_timeout_seconds),
            "--claude-max-turns", str(claude_max_turns),
            "--retry-count", str(retry_count),
            "--skip-preflight",
        ]
        if grok_model:
            command.extend(["--grok-model", grok_model])
        if claude_model:
            command.extend(["--claude-model", claude_model])
        started_at = _utc_now()
        started[profile] = (started_at, time.monotonic())
        process = subprocess.Popen(
            command,
            stdout=handle,
            stderr=subprocess.STDOUT,
            text=True,
        )
        processes[profile] = process
        print(json.dumps({
            "event": "condition-started",
            "profile": profile,
            "pid": process.pid,
            "database": str(databases[profile]),
            "logFile": str(logs[profile]),
        }), flush=True)

    summaries: list[dict[str, Any]] = []
    remaining = set(PROFILES)
    while remaining:
        for profile in list(remaining):
            process = processes[profile]
            returncode = process.poll()
            if returncode is None:
                continue
            handles[profile].flush()
            handles[profile].close()
            completed_at = _utc_now()
            started_at, monotonic_start = started[profile]
            summary = _condition_summary(
                profile,
                databases[profile],
                returncode=returncode,
                started_at=started_at,
                completed_at=completed_at,
                elapsed_seconds=time.monotonic() - monotonic_start,
                log_file=logs[profile],
            )
            summaries.append(summary)
            remaining.remove(profile)
            print(json.dumps({
                "event": "condition-completed",
                **summary,
            }, ensure_ascii=False), flush=True)
        if remaining:
            time.sleep(5)

    summary_document = {
        "schemaVersion": 1,
        "completedAt": _utc_now(),
        "seedDatabase": str(seed_database.resolve()),
        "seedImportId": seed_import_id,
        "maxCategories": max_categories,
        "conditions": sorted(summaries, key=lambda item: PROFILES.index(item["profile"])),
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary_document, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "event": "supervisor-completed",
        "outputDirectory": str(output_dir),
        "summaryFile": str(output_dir / "summary.json"),
    }), flush=True)
    return summary_document


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(
        description="Run all three Resource Scout pairwise conditions concurrently"
    )
    value.add_argument("--seed-database", type=Path, required=True)
    value.add_argument("--seed-import-id", type=int, default=1)
    value.add_argument("--output-dir", type=Path)
    value.add_argument("--max-categories", type=int, default=6)
    value.add_argument("--codex-binary", default=shutil.which("codex") or "codex")
    value.add_argument("--codex-model", default=DEFAULT_CODEX_MODEL)
    value.add_argument("--grok-binary", default=shutil.which("grok") or "grok")
    value.add_argument("--grok-model", default="")
    value.add_argument("--claude-binary", default=shutil.which("claude") or "claude")
    value.add_argument("--claude-model", default="")
    value.add_argument("--codex-timeout-seconds", type=int, default=1800)
    value.add_argument("--grok-timeout-seconds", type=int, default=1800)
    value.add_argument("--claude-timeout-seconds", type=int, default=1800)
    value.add_argument("--claude-max-turns", type=int, default=24)
    value.add_argument("--retry-count", type=int, default=3)
    value.add_argument("--stagger-seconds", type=int, default=10)
    return value


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    output_dir = args.output_dir or Path("data") / f"pairwise-overnight-{timestamp}"
    summary = run_supervisor(
        seed_database=args.seed_database,
        seed_import_id=args.seed_import_id,
        output_dir=output_dir,
        max_categories=args.max_categories,
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
        stagger_seconds=args.stagger_seconds,
    )
    return 0 if all(item["returnCode"] == 0 for item in summary["conditions"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
