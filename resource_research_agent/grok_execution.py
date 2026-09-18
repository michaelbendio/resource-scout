"""Run the isolated Grok CLI without hiding authentication stalls as timeouts."""
from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path


class GrokAuthenticationError(RuntimeError):
    """A worker cannot authenticate; retrying research will not repair sign-in."""


class _AuthLog:
    def __init__(self, path: Path):
        self.path = path
        self.identity = None
        self.offset = 0
        self.partial = b""
        try:
            stat = path.stat()
            self.identity = (stat.st_dev, stat.st_ino)
            self.offset = stat.st_size
        except OSError:
            pass

    def failed(self, pid: int) -> bool:
        # Only inspect new structured events belonging to this exact child.
        # Never copy credential-bearing log contents into exceptions or telemetry.
        try:
            with self.path.open("rb") as stream:
                stat = self.path.stat()
                identity = (stat.st_dev, stat.st_ino)
                if identity != self.identity or stat.st_size < self.offset:
                    self.offset = 0
                    self.partial = b""
                self.identity = identity
                stream.seek(self.offset)
                data = self.partial + stream.read()
                self.offset = stream.tell()
        except OSError:
            return False
        lines = data.split(b"\n")
        self.partial = lines.pop()
        for line in lines:
            try:
                event = json.loads(line)
            except (ValueError, UnicodeDecodeError):
                continue
            if not isinstance(event, dict) or event.get("pid") != pid:
                continue
            context = event.get("ctx")
            if (event.get("msg") == "shell.turn.inference_failed"
                    and isinstance(context, dict) and context.get("kind") == "auth"):
                return True
        return False


def run_grok_process(
    command: list[str], *, timeout_seconds: int,
    log_path: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    log = _AuthLog(log_path or Path.home() / ".grok/logs/unified.jsonl")
    deadline = time.monotonic() + timeout_seconds
    with subprocess.Popen(
        command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    ) as process:
        try:
            while True:
                if log.failed(process.pid):
                    raise GrokAuthenticationError(
                        "Grok authentication failed. Research stopped; saved work is intact. "
                        "Run `grok login`, then resume with preflight enabled."
                    )
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise subprocess.TimeoutExpired(command, timeout_seconds)
                try:
                    stdout, stderr = process.communicate(timeout=min(2, remaining))
                except subprocess.TimeoutExpired:
                    continue
                if log.failed(process.pid):
                    raise GrokAuthenticationError(
                        "Grok authentication failed. Run `grok login`, then resume "
                        "with preflight enabled."
                    )
                return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)
        except BaseException:
            process.kill()
            process.communicate()
            raise
