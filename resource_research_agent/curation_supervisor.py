"""Persistent curation monitoring with bounded coordinator recovery.

Attach to an existing coordinator without disturbing its worker, or launch the
saved local command. Native workers are managed by scout_curation_runner.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .runner_lock import research_runner_lock
from .storage import ResearchStore
from .worker_failures import classify_worker_failure
from .worker_lifecycle import atomic_json, process_identity


def completed_export(summary: dict[str, Any], job_id: int) -> bool:
    if summary.get('status') != 'completed' or summary.get('jobId') != job_id:
        return False
    if 'draftFile' in summary:
        path = Path(summary['draftFile'])
        return (summary.get('handoff') == 'Ready for Codex review' and path.is_file()
                and hashlib.sha256(path.read_bytes()).hexdigest() == summary.get('draftSha256'))
    return Path(summary.get('reviewFile', '__absent__')).is_file()


def recovery_decision(*, complete: bool, exported: bool, done: int, limit: int,
                      last_phase: str, last_message: str, restarts: int,
                      maximum_restarts: int) -> str:
    if complete and exported:
        return "ready-for-codex-review"
    if done >= limit and not complete:
        return "category-limit-reached"
    if restarts >= maximum_restarts:
        return "recovery-budget-exhausted"
    if last_phase == "codex-curation-stopped":
        # An ordinary worker/validation failure is not a coordinator crash.
        # Retry only a confirmed transport failure. Its per-batch retry budget
        # is independently enforced on disk by curation_recovery.
        if "retry exhausted" in last_message.casefold():
            return "needs-attention"
        if not classify_worker_failure(last_message).retryable:
            return "needs-attention"
    return "restart-coordinator"


def load_launch(path: Path) -> tuple[dict[str, Any], Path, Path, int, int]:
    launch = json.loads(path.read_text())
    command = launch["command"]
    if not isinstance(command, list) or not all(isinstance(s, str) for s in command):
        raise ValueError("Launch command must be a string argument list")
    module = command.index("-m")
    if command[module + 1] != "resource_research_agent.scout_curation_runner":
        raise ValueError("Only the Codex-only curation runner may be supervised")
    # Reject additional interpreter commands before the module or shell wrappers.
    prefix = command[:module]
    if prefix[:2] == ["caffeinate", "-dimsu"]:
        prefix = prefix[2:]
    if len(prefix) != 1 or not Path(prefix[0]).name.lower().startswith("python"):
        raise ValueError("Expected a direct Python module command")
    def value(option: str) -> str:
        if command.count(option) != 1:
            raise ValueError(f"Expected exactly one {option}")
        return command[command.index(option) + 1]
    database = Path(value("--database")).expanduser().resolve()
    output = Path(value("--output")).expanduser().resolve()
    if value("--effort") not in ("high", "xhigh"):
        raise ValueError("Explicit authorized worker effort required")
    return launch, database, output, int(value("--import-id")), int(value("--max-categories"))


def notify_local(message: str) -> dict[str, Any]:
    script = 'on run argv\ndisplay notification (item 1 of argv) with title "Resource Scout"\nend run'
    try:
        result = subprocess.run(["osascript", "-e", script, message], capture_output=True,
                                text=True, timeout=10, check=False)
        return {"status": "requested" if result.returncode == 0 else "failed",
                "exitCode": result.returncode, "error": result.stderr.strip()[:1000],
                "displayConfirmed": False}
    except (OSError, subprocess.TimeoutExpired) as error:
        return {"status": "failed", "error": str(error)[:1000], "displayConfirmed": False}


def supervise(manifest: Path, *, attach_pid: int | None, maximum_restarts: int = 2,
              interval: float = 30, notify: bool = False) -> dict[str, Any]:
    launch, database, output, import_id, limit = load_launch(manifest)
    output.mkdir(parents=True, exist_ok=True)
    status_path = output / "supervisor-status.json"
    lock_base = database.with_name(database.name + ".curation-supervisor")
    with research_runner_lock(lock_base):
        store = ResearchStore(database)
        # Do not create or reset a job from the supervisor.
        with store.connect() as connection:
            row = connection.execute(
                "SELECT id FROM scout_curation_jobs WHERE import_id=? ORDER BY id DESC LIMIT 1",
                (import_id,),
            ).fetchone()
        if row is None:
            raise ValueError("Prepare the curation job before supervising")
        job_id = row[0]
        prior = json.loads(status_path.read_text()) if status_path.exists() else {}
        if prior and (prior.get("database") != str(database) or prior.get("jobId") != job_id):
            raise ValueError("Supervisor state belongs to another job")
        restarts = int(prior.get("coordinatorRestarts", 0))
        pid = attach_pid
        if pid is None and prior.get("coordinatorPid"):
            candidate = process_identity(int(prior["coordinatorPid"]))
            if candidate and candidate["identity"] == prior.get("coordinatorIdentity"):
                pid = int(prior["coordinatorPid"])
        expected = process_identity(pid) if pid else None
        if pid and (not expected or "resource_research_agent.scout_curation_runner" not in expected["identity"]):
            raise ValueError("Attach PID is not a live curation coordinator")
        if attach_pid and str(launch.get("pid")) != str(pid):
            raise ValueError("Attach PID does not match the launch manifest")
        child: subprocess.Popen | None = None
        while True:
            if child is not None:
                child.poll()  # Reap exited children so their PID cannot look live.
            current = process_identity(pid) if pid else None
            alive = bool(current and expected and current["identity"] == expected["identity"]
                         and not current["state"].startswith("Z"))
            job = store.get_scout_curation_job(job_id)
            done = sum(c["status"] == "completed" for c in job["categories"])
            events = store.list_scout_curation_progress(job_id)
            latest = events[-1] if events else {}
            state = {
                "supervisorPid": os.getpid(), "coordinatorPid": pid,
                "coordinatorIdentity": (expected or {}).get("identity"),
                "database": str(database), "jobId": job_id,
                "completedCategories": done, "totalCategories": len(job["categories"]),
                "coordinatorRestarts": restarts, "maximumRestarts": maximum_restarts,
                "updatedAt": datetime.now(timezone.utc).isoformat(),
                "lastPhase": latest.get("phase"), "lastMessage": latest.get("message"),
                "status": "running" if alive else "coordinator-exited",
            }
            active = [c for c in job["categories"] if c["status"] == "assigned"]
            if active:
                paths = list((output / f"job-{job_id}" / active[0]["categoryId"]).rglob("events.jsonl"))
                if paths:
                    native = max(paths, key=lambda p: p.stat().st_mtime)
                    state.update(nativeEvents=str(native), nativeEventBytes=native.stat().st_size,
                                 secondsSinceNativeEvent=round(time.time() - native.stat().st_mtime))
            atomic_json(status_path, state)
            if alive:
                time.sleep(interval)
                continue
            summary_path = output / "curation-summary.json"
            summary = json.loads(summary_path.read_text()) if summary_path.exists() else {}
            exported = completed_export(summary, job_id)
            decision = recovery_decision(
                complete=job["status"] == "completed", exported=exported, done=done,
                limit=limit, last_phase=latest.get("phase", ""), last_message=latest.get("message", ""),
                restarts=restarts, maximum_restarts=maximum_restarts)
            if decision != "restart-coordinator":
                state["status"] = decision
                atomic_json(status_path, state)
                if notify:
                    state["notification"] = notify_local(
                        "Curation complete — ready for your requested Codex review."
                        if decision == "ready-for-codex-review"
                        else f"Curation stopped at {done}/{len(job['categories'])}: {latest.get('message', decision)[:200]}")
                    atomic_json(status_path, state)
                if decision not in ("ready-for-codex-review", "category-limit-reached"):
                    store.record_scout_curation_progress(job_id, "codex-curation-stopped",
                        f"Supervisor stopped: {decision}. {latest.get('message', '')}",
                        category_id=active[0]["categoryId"] if active else latest.get("categoryId"), details=state)
                return state
            # Charge the durable coordinator budget BEFORE launch. A supervisor
            # crash must not reset it or allow unlimited launches.
            restarts += 1
            state.update(coordinatorRestarts=restarts, status="restarting-coordinator")
            atomic_json(status_path, state)
            with (output / "runner.log").open("ab", buffering=0) as log:
                child = subprocess.Popen(launch["command"], stdin=subprocess.DEVNULL,
                                         stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            pid = child.pid
            expected = process_identity(pid)
            state.update(coordinatorPid=pid, coordinatorIdentity=(expected or {}).get("identity"))
            atomic_json(status_path, state)
            # exec(caffeinate -> Python) can change the process identity briefly.
            time.sleep(min(2, interval))
            expected = process_identity(pid)
            if expected is None:
                continue
            resumed = {**launch, "pid": pid, "identity": expected,
                       "startedAt": datetime.now(timezone.utc).isoformat(),
                       "status": "running", "supervisorRestart": restarts,
                       "supervisorPid": os.getpid()}
            atomic_json(output / f"supervisor-launch-{restarts}.json", resumed)
            atomic_json(output / "launch.json", resumed)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--launch-manifest", required=True, type=Path)
    parser.add_argument("--attach-pid", type=int)
    parser.add_argument("--maximum-restarts", type=int, default=2)
    parser.add_argument("--interval", type=float, default=30)
    parser.add_argument("--notify", action="store_true")
    args = parser.parse_args()
    if args.maximum_restarts < 0 or not 1 <= args.interval <= 60:
        parser.error("Nonnegative restart limit and 1–60 second interval required")
    state = supervise(args.launch_manifest, attach_pid=args.attach_pid,
                      maximum_restarts=args.maximum_restarts, interval=args.interval, notify=args.notify)
    print(json.dumps(state, indent=2), flush=True)
    return 0 if state["status"] in ("ready-for-codex-review", "category-limit-reached") else 1


if __name__ == "__main__":
    raise SystemExit(main())
