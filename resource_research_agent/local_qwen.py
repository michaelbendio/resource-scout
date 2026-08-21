from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import signal
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .dsh_configuration import LOCAL_QWEN_CONFIGURATION, resolve_dsh_configuration


MLX_SERVER_ENV = "RESOURCE_SCOUT_MLX_SERVER"
HOMEBREW_MLX_SERVER = Path("/opt/homebrew/opt/mlx-lm/bin/mlx_lm.server")
PROJECT_ROOT = Path(__file__).resolve().parent.parent
HEALTH_STAMP = PROJECT_ROOT / "data" / "local-qwen-health.json"


class LocalQwenError(RuntimeError):
    pass


def find_mlx_server(environment: dict[str, str] | None = None) -> Path | None:
    values = environment if environment is not None else os.environ
    configured = values.get(MLX_SERVER_ENV, "").strip()
    candidates = [Path(configured).expanduser()] if configured else []
    candidates.append(HOMEBREW_MLX_SERVER)
    discovered = shutil.which("mlx_lm.server")
    if discovered:
        candidates.append(Path(discovered))
    for candidate in candidates:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate.resolve()
    return None


def server_command(executable: Path, *, port: int = 8081) -> list[str]:
    configuration = resolve_dsh_configuration(LOCAL_QWEN_CONFIGURATION)
    endpoint = configuration.model_endpoint.removesuffix("/v1")
    if endpoint != "http://127.0.0.1:8080":
        raise LocalQwenError(f"Unsupported Local Qwen endpoint: {configuration.model_endpoint}")
    return [
        str(executable),
        "--model",
        configuration.model,
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "--max-tokens",
        "32768",
        "--chat-template-args",
        json.dumps(
            {"enable_thinking": True, "reasoning_effort": configuration.reasoning},
            separators=(",", ":"),
        ),
    ]


def mlx_compatible_payload(payload: dict[str, Any]) -> dict[str, Any]:
    compatible = dict(payload)
    messages = compatible.get("messages")
    if isinstance(messages, list):
        compatible["messages"] = [
            {**message, "role": "system"}
            if isinstance(message, dict) and message.get("role") == "developer"
            else message
            for message in messages
        ]
    if "max_completion_tokens" in compatible and "max_tokens" not in compatible:
        compatible["max_tokens"] = compatible.pop("max_completion_tokens")
    compatible.pop("store", None)
    return compatible


class _CompatibilityHandler(BaseHTTPRequestHandler):
    backend = "http://127.0.0.1:8081"
    max_request_bytes = 10_000_000

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        self._forward(None)

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self.send_error(400, "Invalid Content-Length")
            return
        if length < 0 or length > self.max_request_bytes:
            self.send_error(413, "Request too large")
            return
        body = self.rfile.read(length)
        if self.path.rstrip("/").endswith("/chat/completions"):
            try:
                payload = json.loads(body)
            except json.JSONDecodeError:
                self.send_error(400, "Invalid JSON")
                return
            if not isinstance(payload, dict):
                self.send_error(400, "JSON request must be an object")
                return
            body = json.dumps(mlx_compatible_payload(payload)).encode("utf-8")
        self._forward(body)

    def _forward(self, body: bytes | None) -> None:
        request = Request(
            f"{self.backend}{self.path}",
            data=body,
            method=self.command,
            headers={
                "Accept": self.headers.get("Accept", "application/json"),
                "Content-Type": self.headers.get("Content-Type", "application/json"),
            },
        )
        try:
            with urlopen(request, timeout=900) as response:
                self.send_response(response.status)
                self.send_header(
                    "Content-Type", response.headers.get("Content-Type", "application/json")
                )
                self.end_headers()
                try:
                    for chunk in iter(lambda: response.read1(16 * 1024), b""):
                        self.wfile.write(chunk)
                        self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    return
        except HTTPError as exc:
            detail = exc.read()
            self.send_response(exc.code)
            self.send_header("Content-Type", exc.headers.get("Content-Type", "application/json"))
            self.send_header("Content-Length", str(len(detail)))
            self.end_headers()
            self.wfile.write(detail)
        except (BrokenPipeError, ConnectionResetError):
            return
        except (OSError, URLError) as exc:
            detail = json.dumps({"error": f"MLX backend unavailable: {exc}"}).encode("utf-8")
            try:
                self.send_response(502)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(detail)))
                self.end_headers()
                self.wfile.write(detail)
            except (BrokenPipeError, ConnectionResetError):
                return

    def log_message(self, format: str, *args: Any) -> None:
        return


def _request_json(
    url: str, *, payload: dict[str, Any] | None = None, timeout: float = 5.0
) -> dict[str, Any]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(url, data=body, method="GET" if body is None else "POST")
    request.add_header("Accept", "application/json")
    if body is not None:
        request.add_header("Content-Type", "application/json")
    try:
        with urlopen(request, timeout=timeout) as response:
            value = json.load(response)
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace").strip()
        raise LocalQwenError(f"Local Qwen returned HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise LocalQwenError(f"Local Qwen is not reachable at {url}: {exc.reason}") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise LocalQwenError(f"Local Qwen returned an unreadable response at {url}: {exc}") from exc
    if not isinstance(value, dict):
        raise LocalQwenError(f"Local Qwen returned a non-object response at {url}")
    return value


def catalog_health(timeout: float = 5.0) -> dict[str, Any]:
    configuration = resolve_dsh_configuration(LOCAL_QWEN_CONFIGURATION)
    value = _request_json(f"{configuration.model_endpoint}/models", timeout=timeout)
    entries = value.get("data")
    if not isinstance(entries, list):
        raise LocalQwenError("Local Qwen model catalog did not contain a data array")
    model_entries = [entry for entry in entries if isinstance(entry, dict)]
    model_ids = [str(entry.get("id")) for entry in model_entries]
    if configuration.model not in model_ids:
        raise LocalQwenError(
            f"The MLX server does not report {configuration.model}. "
            "Download or start the pinned model before continuing."
        )
    return {
        "ready": True,
        "endpoint": configuration.model_endpoint,
        "model": configuration.model,
        "availableModels": model_ids,
    }


def server_identity() -> dict[str, Any]:
    try:
        listener = subprocess.run(
            ["lsof", "-nP", "-iTCP:8080", "-sTCP:LISTEN", "-Fp"],
            capture_output=True, text=True, timeout=5, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise LocalQwenError(f"Could not identify the Local Qwen listener: {exc}") from exc
    pids = {
        line[1:].strip() for line in listener.stdout.splitlines()
        if line.startswith("p") and line[1:].strip().isdigit()
    }
    if listener.returncode != 0 or len(pids) != 1:
        raise LocalQwenError("Could not identify one Local Qwen listener on port 8080")
    pid = next(iter(pids))
    try:
        process = subprocess.run(
            ["ps", "-o", "lstart=", "-p", pid],
            capture_output=True, text=True, timeout=5, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise LocalQwenError(f"Could not inspect the Local Qwen listener: {exc}") from exc
    started = process.stdout.strip()
    if process.returncode != 0 or not started:
        raise LocalQwenError("Could not determine when the Local Qwen listener started")
    return {"serverPid": int(pid), "serverStarted": started}


def completion_health(timeout: float = 300.0) -> dict[str, Any]:
    configuration = resolve_dsh_configuration(LOCAL_QWEN_CONFIGURATION)
    catalog_health(timeout=min(timeout, 5.0))
    value = _request_json(
        f"{configuration.model_endpoint}/chat/completions",
        timeout=timeout,
        payload={
            "model": configuration.model,
            "messages": [
                {"role": "user", "content": "Reply with exactly: LOCAL_QWEN_READY"}
            ],
            # Reasoning tokens count against this allowance. Keep enough room for
            # the model to think and still emit the readiness marker.
            "max_tokens": 256,
            "temperature": 0,
        },
    )
    choices = value.get("choices")
    if not isinstance(choices, list) or not choices:
        raise LocalQwenError("Local Qwen completion response did not contain a choice")
    first = choices[0] if isinstance(choices[0], dict) else {}
    message = first.get("message") if isinstance(first.get("message"), dict) else {}
    content = str(message.get("content") or "").strip()
    if "LOCAL_QWEN_READY" not in content:
        raise LocalQwenError("Local Qwen completion did not return the readiness marker")
    return {
        **catalog_health(timeout=min(timeout, 5.0)),
        **server_identity(),
        "completion": content,
    }


def write_health_stamp(status: dict[str, Any], path: Path = HEALTH_STAMP) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(status, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def validated_health(timeout: float = 2.0, path: Path = HEALTH_STAMP) -> dict[str, Any]:
    catalog = catalog_health(timeout=timeout)
    identity = server_identity()
    try:
        stamp = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LocalQwenError(
            "Local Qwen has not completed its live validation. Run ./local-qwen.sh health first."
        ) from exc
    if (
        stamp.get("model") != catalog["model"]
        or stamp.get("endpoint") != catalog["endpoint"]
        or stamp.get("serverPid") != identity["serverPid"]
        or stamp.get("serverStarted") != identity["serverStarted"]
        or "LOCAL_QWEN_READY" not in str(stamp.get("completion") or "")
    ):
        raise LocalQwenError(
            "The Local Qwen server changed after its last live validation. Run ./local-qwen.sh health again."
        )
    return {**catalog, **identity, "validated": True}


def _serve() -> int:
    executable = find_mlx_server()
    if executable is None:
        raise LocalQwenError(
            "MLX LM is not installed. Install the pinned Homebrew runtime before starting Local Qwen."
        )
    configuration = resolve_dsh_configuration(LOCAL_QWEN_CONFIGURATION)
    try:
        _request_json(f"{configuration.model_endpoint}/models", timeout=1.0)
    except LocalQwenError:
        pass
    else:
        raise LocalQwenError(
            "Port 8080 is already serving an MLX API. Stop that process before starting the pinned Local Qwen server."
        )
    command = server_command(executable, port=8081)
    print(
        f"Starting {configuration.model} behind the local compatibility endpoint "
        f"{configuration.model_endpoint}",
        flush=True,
    )
    backend = subprocess.Popen(command)
    server = ThreadingHTTPServer(("127.0.0.1", 8080), _CompatibilityHandler)

    def stop(_signal: int, _frame: Any) -> None:
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        server.serve_forever()
    finally:
        server.server_close()
        backend.terminate()
        try:
            backend.wait(timeout=15)
        except subprocess.TimeoutExpired:
            backend.kill()
            backend.wait()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Manage the Phase 1 Local Qwen runtime")
    parser.add_argument("action", choices=("serve", "catalog", "health"))
    parser.add_argument("--timeout", type=float, default=None)
    arguments = parser.parse_args(argv)
    try:
        if arguments.action == "serve":
            return _serve()
        if arguments.action == "catalog":
            result = catalog_health(timeout=arguments.timeout or 5.0)
        else:
            result = completion_health(timeout=arguments.timeout or 300.0)
            write_health_stamp(result)
    except LocalQwenError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
