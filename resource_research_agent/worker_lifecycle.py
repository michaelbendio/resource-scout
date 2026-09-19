"""Durable worker identity so a restarted coordinator cannot duplicate an orphan."""
from __future__ import annotations

import json
import os
import signal
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


def atomic_json(path: Path, value: Any) -> None:
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, sort_keys=True)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def process_identity(pid: int) -> dict[str, str] | None:
    result = subprocess.run(["ps", "-p", str(pid), "-o", "stat=", "-o", "lstart=", "-o", "command="],
                            text=True, capture_output=True, check=False)
    line = result.stdout.strip()
    if result.returncode or not line:
        return None
    state, _, identity = line.partition(" ")
    return {"state": state, "identity": identity.strip()}


def record_worker(directory: Path, pid: int, command: list[str]) -> None:
    identity = process_identity(pid)
    atomic_json(directory / "worker.json", {
        "pid": pid, "identity": (identity or {}).get("identity"), "command": command,
        "startedAt": datetime.now(timezone.utc).isoformat(),
    })


def await_orphan(directory: Path, timeout_seconds: int, heartbeat: Callable[[float], None],
                 *, pause: Callable[[float], None] = time.sleep) -> None:
    path = directory / "worker.json"
    if not path.exists():
        return
    worker = json.loads(path.read_text())
    started = datetime.fromisoformat(worker["startedAt"])
    while True:
        identity = process_identity(int(worker["pid"]))
        if identity is None or identity["state"].startswith("Z"):
            return
        if not worker.get("identity") or identity["identity"] != worker["identity"]:
            raise RuntimeError("Worker PID identity changed; refusing to signal or duplicate an uncertain process")
        elapsed = (datetime.now(timezone.utc) - started).total_seconds()
        heartbeat(elapsed)
        if elapsed >= timeout_seconds:
            # Only the positively matched worker's dedicated process group.
            os.killpg(int(worker["pid"]), signal.SIGTERM)
            for _ in range(5):
                pause(1)
                current = process_identity(int(worker["pid"]))
                if current is None or current["state"].startswith("Z"):
                    return
                if current["identity"] != worker["identity"]:
                    raise RuntimeError("Worker identity changed during termination")
            os.killpg(int(worker["pid"]), signal.SIGKILL)
            return
        pause(min(30, max(1, timeout_seconds - elapsed)))
