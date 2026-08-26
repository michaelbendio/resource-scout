from __future__ import annotations

import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


TRACE_ENDPOINT_ENV = "RESOURCE_SCOUT_TRACE_ENDPOINT"
TRACE_ID_ENV = "RESOURCE_SCOUT_TRACE_ID"


class TraceClientError(RuntimeError):
    pass


def trace_endpoint() -> str:
    return os.environ.get(TRACE_ENDPOINT_ENV, "").strip().rstrip("/")


def emit_trace_event(
    *,
    source: str,
    target: str,
    kind: str,
    summary: str,
    payload: Any,
    trace_id: str,
    reply_to: str | None = None,
    timeout: float = 7200,
) -> dict[str, Any] | None:
    endpoint = trace_endpoint()
    if not endpoint:
        return None
    value = {
        "source": source,
        "target": target,
        "kind": kind,
        "summary": summary,
        "payload": payload,
        "traceId": trace_id,
        "replyTo": reply_to,
    }
    request = Request(
        f"{endpoint}/api/events",
        data=json.dumps(value, ensure_ascii=False).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            result = json.load(response)
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        raise TraceClientError(f"Trace Console returned HTTP {exc.code}: {detail}") from exc
    except (OSError, URLError, json.JSONDecodeError) as exc:
        raise TraceClientError(f"Trace Console is unavailable: {exc}") from exc
    if not isinstance(result, dict) or result.get("ok") is not True:
        raise TraceClientError("Trace Console returned an invalid approval")
    return result.get("event") if isinstance(result.get("event"), dict) else None
