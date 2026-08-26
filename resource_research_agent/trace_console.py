from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlsplit
from urllib.request import Request, urlopen
from uuid import uuid4


TRACE_HOST = "127.0.0.1"
TRACE_UI_PORT = 8082
TRACE_MODEL_PORT = 8083
QWEN_BACKEND = "http://127.0.0.1:8080"
MAX_EVENT_BYTES = 2 * 1024 * 1024
MAX_MODEL_REQUEST_BYTES = 10 * 1024 * 1024
MAX_HISTORY = 5000
WAIT_SECONDS = 7200


class TraceError(RuntimeError):
    pass


def catalog_health(timeout: float = 2.0) -> dict[str, Any]:
    url = f"http://{TRACE_HOST}:{TRACE_MODEL_PORT}/v1/models"
    try:
        with urlopen(url, timeout=timeout) as response:
            value = json.load(response)
    except (OSError, URLError, json.JSONDecodeError) as exc:
        raise TraceError(f"Trace Console model proxy is unavailable at {url}: {exc}") from exc
    entries = value.get("data") if isinstance(value, dict) else None
    model_ids = [str(item.get("id") or "") for item in entries or [] if isinstance(item, dict)]
    if "mlx-community/Qwen3.8-27B-8bit" not in model_ids:
        raise TraceError("Trace Console did not report the locked local Qwen model")
    return {"ready": True, "model": model_ids[0], "endpoint": url.removesuffix("/models")}


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def bounded_payload(value: Any) -> tuple[Any, bool]:
    rendered = json.dumps(value, ensure_ascii=False, default=str)
    if len(rendered.encode("utf-8")) <= MAX_EVENT_BYTES:
        return value, False
    preview = rendered.encode("utf-8")[:MAX_EVENT_BYTES].decode("utf-8", "ignore")
    return {"truncated": True, "originalBytes": len(rendered.encode("utf-8")), "preview": preview}, True


@dataclass
class TraceEvent:
    sequence: int
    source: str
    target: str
    kind: str
    summary: str
    payload: Any
    trace_id: str
    reply_to: str | None = None
    id: str = field(default_factory=lambda: f"event-{uuid4().hex}")
    created_at: str = field(default_factory=timestamp)
    approved_at: str | None = None
    approval: str = "waiting"
    payload_truncated: bool = False
    gate: threading.Event = field(default_factory=threading.Event, repr=False)

    def summary_value(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "sequence": self.sequence,
            "source": self.source,
            "target": self.target,
            "kind": self.kind,
            "summary": self.summary,
            "traceId": self.trace_id,
            "replyTo": self.reply_to,
            "createdAt": self.created_at,
            "approvedAt": self.approved_at,
            "approval": self.approval,
            "payloadTruncated": self.payload_truncated,
        }

    def detail_value(self) -> dict[str, Any]:
        return {**self.summary_value(), "payload": self.payload}


class TraceHub:
    def __init__(self, trace_path: Path | None = None) -> None:
        self._condition = threading.Condition()
        self._events: list[TraceEvent] = []
        self._pending: TraceEvent | None = None
        self._sequence = 0
        self._skip_remaining = 0
        self._run_until: str | None = None
        self._continue = False
        self._active_trace_id = ""
        self.trace_path = trace_path

    @property
    def active_trace_id(self) -> str:
        with self._condition:
            return self._active_trace_id or f"trace-{uuid4().hex}"

    def emit(
        self,
        *,
        source: str,
        target: str,
        kind: str,
        summary: str,
        payload: Any,
        trace_id: str = "",
        reply_to: str | None = None,
    ) -> TraceEvent:
        payload, truncated = bounded_payload(payload)
        with self._condition:
            while self._pending is not None:
                self._condition.wait()
            self._sequence += 1
            effective_trace = trace_id or self._active_trace_id or f"trace-{uuid4().hex}"
            if kind == "stage-request" and source == "Scout":
                self._active_trace_id = effective_trace
            event = TraceEvent(
                sequence=self._sequence,
                source=source,
                target=target,
                kind=kind,
                summary=summary,
                payload=payload,
                trace_id=effective_trace,
                reply_to=reply_to,
                payload_truncated=truncated,
            )
            self._events.append(event)
            if len(self._events) > MAX_HISTORY:
                self._events = self._events[-MAX_HISTORY:]
            self._append_record({"recordType": "event", **event.detail_value()})
            if self._should_auto_approve(event):
                self._approve_locked(event, "automatic")
            else:
                self._pending = event
                self._condition.notify_all()
        if not event.gate.wait(WAIT_SECONDS):
            with self._condition:
                if not event.gate.is_set():
                    self._approve_locked(event, "timeout")
                    if self._pending is event:
                        self._pending = None
                        self._condition.notify_all()
            raise TraceError("Trace approval timed out after two hours")
        if kind in {"stage-response", "stage-error"} and source == "DSH":
            with self._condition:
                if self._active_trace_id == effective_trace:
                    self._active_trace_id = ""
        return event

    def _should_auto_approve(self, event: TraceEvent) -> bool:
        if self._continue:
            return True
        if self._skip_remaining > 0:
            self._skip_remaining -= 1
            return True
        if self._run_until:
            if self._matches_run_until(event, self._run_until):
                self._run_until = None
                return False
            return True
        return False

    @staticmethod
    def _matches_run_until(event: TraceEvent, boundary: str) -> bool:
        if boundary == "qwen":
            return event.target == "Qwen" or event.source == "Qwen"
        if boundary == "search":
            return event.kind.startswith("search-")
        if boundary == "fetch":
            return event.kind.startswith("fetch-")
        if boundary == "error":
            return event.kind.endswith("error")
        if boundary == "stage":
            return event.kind in {"stage-request", "stage-response", "stage-error"}
        return True

    def approve(self, event_id: str, approval: str = "ok") -> None:
        with self._condition:
            if self._pending is None or self._pending.id != event_id:
                raise TraceError("That message is no longer waiting")
            self._approve_locked(self._pending, approval)
            self._pending = None
            self._condition.notify_all()

    def control(self, action: str, value: Any = None) -> None:
        with self._condition:
            if action == "skip":
                count = int(value)
                if count < 1 or count > 10000:
                    raise TraceError("Skip count must be between 1 and 10,000")
                self._skip_remaining = count
                if self._pending is not None:
                    self._skip_remaining -= 1
                    self._approve_locked(self._pending, "skipped")
                    self._pending = None
                    self._condition.notify_all()
            elif action == "run-until":
                boundary = str(value or "")
                if boundary not in {"qwen", "search", "fetch", "error", "stage"}:
                    raise TraceError("Unknown run-until boundary")
                self._run_until = boundary
                if self._pending is not None:
                    self._approve_locked(self._pending, f"run-until-{boundary}")
                    self._pending = None
                    self._condition.notify_all()
            elif action == "continue":
                self._continue = True
                self._skip_remaining = 0
                self._run_until = None
                if self._pending is not None:
                    self._approve_locked(self._pending, "continue")
                    self._pending = None
                    self._condition.notify_all()
            elif action == "pause":
                self._continue = False
                self._skip_remaining = 0
                self._run_until = None
            else:
                raise TraceError("Unknown trace control")

    def _approve_locked(self, event: TraceEvent, approval: str) -> None:
        if event.gate.is_set():
            return
        event.approval = approval
        event.approved_at = timestamp()
        self._append_record(
            {
                "recordType": "approval",
                "eventId": event.id,
                "approvedAt": event.approved_at,
                "approval": approval,
            }
        )
        event.gate.set()

    def state(self, after: int = 0) -> dict[str, Any]:
        with self._condition:
            events = [event.summary_value() for event in self._events if event.sequence > after]
            return {
                "events": events,
                "pending": self._pending.summary_value() if self._pending else None,
                "controls": {
                    "skipRemaining": self._skip_remaining,
                    "runUntil": self._run_until,
                    "continueWithoutPausing": self._continue,
                },
                "latestSequence": self._sequence,
            }

    def event(self, event_id: str) -> dict[str, Any] | None:
        with self._condition:
            event = next((item for item in self._events if item.id == event_id), None)
            return event.detail_value() if event else None

    def export(self) -> bytes:
        with self._condition:
            return (
                "\n".join(
                    json.dumps(event.detail_value(), ensure_ascii=False, default=str)
                    for event in self._events
                )
                + ("\n" if self._events else "")
            ).encode("utf-8")

    def release_all(self) -> None:
        with self._condition:
            self._continue = True
            if self._pending is not None:
                self._approve_locked(self._pending, "shutdown")
                self._pending = None
            self._condition.notify_all()

    def _append_record(self, value: dict[str, Any]) -> None:
        if self.trace_path is None:
            return
        self.trace_path.parent.mkdir(parents=True, exist_ok=True)
        with self.trace_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(value, ensure_ascii=False, default=str) + "\n")


class TraceUIServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address: tuple[str, int], hub: TraceHub) -> None:
        super().__init__(address, TraceUIHandler)
        self.hub = hub


class TraceUIHandler(BaseHTTPRequestHandler):
    server: TraceUIServer
    protocol_version = "HTTP/1.1"

    def log_message(self, format: str, *args: Any) -> None:
        return

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlsplit(self.path)
        if parsed.path in {"/", "/index.html"}:
            self._bytes(TRACE_HTML.encode(), "text/html; charset=utf-8")
        elif parsed.path == "/api/state":
            query = parse_qs(parsed.query)
            self._json(self.server.hub.state(int(query.get("after", ["0"])[0])))
        elif parsed.path.startswith("/api/events/"):
            value = self.server.hub.event(parsed.path.rsplit("/", 1)[-1])
            self._json(value or {"error": "Not found"}, HTTPStatus.OK if value else HTTPStatus.NOT_FOUND)
        elif parsed.path == "/api/export":
            self._bytes(
                self.server.hub.export(),
                "application/x-ndjson; charset=utf-8",
                headers={"Content-Disposition": 'attachment; filename="resource-scout-trace.jsonl"'},
            )
        else:
            self._json({"error": "Not found"}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        try:
            value = self._read_json()
            if self.path == "/api/events":
                event = self.server.hub.emit(
                    source=str(value.get("source") or "Unknown"),
                    target=str(value.get("target") or "Unknown"),
                    kind=str(value.get("kind") or "message"),
                    summary=str(value.get("summary") or "Message"),
                    payload=value.get("payload"),
                    trace_id=str(value.get("traceId") or ""),
                    reply_to=str(value.get("replyTo") or "") or None,
                )
                self._json({"ok": True, "event": event.summary_value()})
            elif self.path == "/api/approve":
                self.server.hub.approve(str(value.get("eventId") or ""))
                self._json({"ok": True})
            elif self.path == "/api/control":
                self.server.hub.control(str(value.get("action") or ""), value.get("value"))
                self._json({"ok": True})
            else:
                self._json({"error": "Not found"}, HTTPStatus.NOT_FOUND)
        except (TraceError, ValueError) as exc:
            self._json({"error": str(exc)}, HTTPStatus.CONFLICT)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > MAX_EVENT_BYTES:
            raise ValueError("Invalid request size")
        value = json.loads(self.rfile.read(length))
        if not isinstance(value, dict):
            raise ValueError("Request must be one JSON object")
        return value

    def _json(self, value: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
        self._bytes(json.dumps(value, ensure_ascii=False).encode(), "application/json; charset=utf-8", status)

    def _bytes(
        self,
        data: bytes,
        content_type: str,
        status: HTTPStatus = HTTPStatus.OK,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(data)


class TraceModelServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address: tuple[str, int], hub: TraceHub) -> None:
        super().__init__(address, TraceModelHandler)
        self.hub = hub


class TraceModelHandler(BaseHTTPRequestHandler):
    server: TraceModelServer
    protocol_version = "HTTP/1.1"

    def log_message(self, format: str, *args: Any) -> None:
        return

    def do_GET(self) -> None:  # noqa: N802
        self._forward(None, trace=False)

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > MAX_MODEL_REQUEST_BYTES:
            self.send_error(HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
            return
        body = self.rfile.read(length)
        is_completion = self.path.rstrip("/").endswith("/chat/completions")
        trace_id = self.server.hub.active_trace_id
        request_event = None
        if is_completion:
            try:
                payload = json.loads(body)
            except json.JSONDecodeError:
                payload = {"unreadableBody": body.decode("utf-8", "replace")}
            request_event = self.server.hub.emit(
                source="DSH",
                target="Qwen",
                kind="model-request",
                summary=_model_request_summary(payload),
                payload=payload,
                trace_id=trace_id,
            )
        self._forward(body, trace=is_completion, trace_id=trace_id, reply_to=request_event.id if request_event else None)

    def _forward(
        self,
        body: bytes | None,
        *,
        trace: bool,
        trace_id: str = "",
        reply_to: str | None = None,
    ) -> None:
        request = Request(
            f"{QWEN_BACKEND}{self.path}",
            data=body,
            method=self.command,
            headers={"Accept": self.headers.get("Accept", "application/json"), "Content-Type": "application/json"},
        )
        try:
            with urlopen(request, timeout=WAIT_SECONDS) as response:
                data = response.read()
                content_type = response.headers.get("Content-Type", "application/json")
                status = response.status
        except HTTPError as exc:
            data = exc.read()
            content_type = exc.headers.get("Content-Type", "application/json")
            status = exc.code
        except (OSError, URLError) as exc:
            data = json.dumps({"error": f"Qwen unavailable: {exc}"}).encode()
            content_type = "application/json"
            status = HTTPStatus.BAD_GATEWAY
        if trace:
            decoded = data.decode("utf-8", "replace")
            self.server.hub.emit(
                source="Qwen",
                target="DSH",
                kind="model-response" if status < 400 else "model-error",
                summary=_model_response_summary(decoded, content_type, status),
                payload={"status": int(status), "contentType": content_type, "body": decoded},
                trace_id=trace_id,
                reply_to=reply_to,
            )
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)


def _model_request_summary(payload: Any) -> str:
    if not isinstance(payload, dict):
        return "Model request"
    messages = payload.get("messages") if isinstance(payload.get("messages"), list) else []
    tools = payload.get("tools") if isinstance(payload.get("tools"), list) else []
    return f"{len(messages)} conversation messages; {len(tools)} tools offered"


def _model_response_summary(body: str, content_type: str, status: int) -> str:
    if status >= 400:
        return f"Qwen error HTTP {status}"
    tool_names: list[str] = []
    content_chars = 0
    try:
        if "text/event-stream" in content_type:
            values = []
            for line in body.splitlines():
                if line.startswith("data: ") and line[6:] != "[DONE]":
                    values.append(json.loads(line[6:]))
        else:
            values = [json.loads(body)]
        for value in values:
            for choice in value.get("choices", []):
                message = choice.get("delta") or choice.get("message") or {}
                content_chars += len(str(message.get("content") or ""))
                for call in message.get("tool_calls") or []:
                    name = str(call.get("function", {}).get("name") or "")
                    if name and name not in tool_names:
                        tool_names.append(name)
    except (AttributeError, json.JSONDecodeError, TypeError):
        return f"Qwen response; {len(body)} characters"
    suffix = f"; tools: {', '.join(tool_names)}" if tool_names else ""
    return f"Qwen response; {content_chars} content characters{suffix}"


TRACE_HTML = r"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Resource Scout Trace Console</title><style>
:root{font-family:ui-sans-serif,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:#16211c;background:#edf2ef}*{box-sizing:border-box}body{margin:0}.top{display:flex;justify-content:space-between;gap:20px;padding:18px 24px;background:#183f35;color:white}.top h1{margin:0 0 4px;font-size:23px}.top p{margin:0;color:#d6e8e0}.top a{color:white}.controls{position:sticky;top:0;z-index:2;display:flex;flex-wrap:wrap;gap:9px;align-items:center;padding:12px 18px;background:#dce8e2;border-bottom:1px solid #bdcec5}.controls button,.controls select,.controls input{height:38px;border:1px solid #9eb3a8;border-radius:8px;padding:0 11px;background:white}.controls button{background:#176a52;color:white;border:0;font-weight:700;cursor:pointer}.controls .danger{background:#8d3b31}.controls .quiet{background:#52675e}.controls input{width:76px}.status{margin-left:auto;font-weight:700}.layout{display:grid;grid-template-columns:minmax(430px,.9fr) minmax(0,1.1fr);gap:15px;padding:15px;max-width:1700px;margin:auto}.panel{background:white;border:1px solid #cfdbd4;border-radius:12px;min-height:70vh;overflow:hidden}.panel h2{font-size:17px;margin:0;padding:14px 16px;border-bottom:1px solid #dce5df}.events{max-height:76vh;overflow:auto}.event{display:grid;grid-template-columns:50px 115px 1fr;gap:8px;padding:11px 13px;border:0;border-bottom:1px solid #e3e9e5;width:100%;background:white;text-align:left;cursor:pointer}.event:hover,.event.selected{background:#f0f7f3}.event.waiting{border-left:5px solid #c56a16;background:#fff8ed}.seq{color:#687770}.route{font-weight:700}.kind{font-size:12px;color:#557067}.summary{grid-column:2/4;color:#293a33}.detail{padding:16px}.detail dl{display:grid;grid-template-columns:100px 1fr;gap:6px;margin:0 0 15px}.detail dt{font-weight:700}.detail dd{margin:0}.detail pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f4f7f5;border:1px solid #d8e2dc;border-radius:8px;padding:12px;max-height:58vh;overflow:auto;font:12px/1.45 ui-monospace,SFMono-Regular,Menlo,monospace}.detail-actions{display:flex;gap:8px;margin-bottom:12px}.hidden{display:none}.notice{padding:18px;color:#63716b}.flow{background:#e8f1ec;padding:7px 10px;border-radius:7px;font-size:13px}@media(max-width:900px){.layout{grid-template-columns:1fr}.panel{min-height:auto}.events{max-height:48vh}.status{width:100%;margin:0}}
</style></head><body><header class="top"><div><h1>Resource Scout Trace Console</h1><p>Qwen is doing the research. You approve each logical handoff.</p></div><a href="/api/export">Download trace</a></header><section class="controls"><button id="ok">OK — next message</button><input id="skip-count" type="number" min="1" max="10000" value="10"><button id="skip" class="quiet">Skip N</button><select id="until"><option value="qwen">next Qwen message</option><option value="search">next search</option><option value="fetch">next page fetch</option><option value="error">next error</option><option value="stage">next stage boundary</option></select><button id="run-until" class="quiet">Run to…</button><button id="continue" class="danger">Continue without pausing</button><button id="pause" class="quiet">Pause again</button><span id="status" class="status">Waiting for Scout…</span></section><main class="layout"><section class="panel"><h2>Communication timeline</h2><div id="flow-banner" class="notice hidden"></div><div id="events" class="events"><p class="notice">Start or resume a run in temporary Scout. The first handoff will appear here.</p></div></section><section class="panel"><h2>Selected message</h2><div id="detail" class="detail"><p class="notice">Select a message to inspect its complete payload.</p></div></section></main><script>
let events=[],pending=null,selectedId=null,flowFilter='';const q=s=>document.querySelector(s);const escape=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function visibleEvents(){return flowFilter?events.filter(e=>e.traceId===flowFilter):events}function render(){pending=events.find(e=>e.approval==='waiting')||pending;const root=q('#events');const shown=visibleEvents();root.innerHTML=shown.length?'':'<p class="notice">No messages in this view yet.</p>';for(const e of shown){const button=document.createElement('button');button.className=`event ${e.id===selectedId?'selected':''} ${e.approval==='waiting'?'waiting':''}`;button.innerHTML=`<span class="seq">#${e.sequence}</span><span class="route">${escape(e.source)} → ${escape(e.target)}</span><span class="kind">${escape(e.kind)}</span><span class="summary">${escape(e.summary)}</span>`;button.onclick=()=>selectEvent(e.id);root.append(button)}const controls=window.traceControls||{};q('#status').textContent=pending?`Paused at message #${pending.sequence}`:controls.continueWithoutPausing?'Running without pauses':controls.runUntil?`Running to next ${controls.runUntil}`:controls.skipRemaining?`Skipping ${controls.skipRemaining} more`: 'Waiting for the next message…';q('#ok').disabled=!pending;q('#flow-banner').classList.toggle('hidden',!flowFilter);q('#flow-banner').innerHTML=flowFilter?`Showing one stage flow: <strong>${escape(flowFilter)}</strong> <button onclick="clearFlow()">Show all</button>`:''}
function prettyValue(value,depth=0){if(depth>12)return value;if(Array.isArray(value))return value.map(item=>prettyValue(item,depth+1));if(value&&typeof value==='object')return Object.fromEntries(Object.entries(value).map(([key,item])=>[key,prettyValue(item,depth+1)]));if(typeof value!=='string')return value;const trimmed=value.trim();if((trimmed.startsWith('{')&&trimmed.endsWith('}'))||(trimmed.startsWith('[')&&trimmed.endsWith(']'))){try{return prettyValue(JSON.parse(trimmed),depth+1)}catch{}}const dataLines=trimmed.split(/\r?\n/).filter(line=>line.startsWith('data:'));if(dataLines.length){return{format:'server-sent events',events:dataLines.map(line=>{const data=line.slice(5).trim();if(data==='[DONE]')return'[DONE]';try{return prettyValue(JSON.parse(data),depth+1)}catch{return data}})}}return value}
function prettyJSON(value){return JSON.stringify(prettyValue(value),null,2)}
async function selectEvent(id){selectedId=id;render();const e=await fetch(`/api/events/${id}`,{cache:'no-store'}).then(r=>r.json());const payload=prettyJSON(e.payload);q('#detail').innerHTML=`<div class="detail-actions"><button id="trace-flow">Trace this flow</button></div><dl><dt>Number</dt><dd>#${e.sequence}</dd><dt>Route</dt><dd>${escape(e.source)} → ${escape(e.target)}</dd><dt>Kind</dt><dd>${escape(e.kind)}</dd><dt>Time</dt><dd>${escape(e.createdAt)}</dd><dt>Trace</dt><dd class="flow">${escape(e.traceId)}</dd><dt>Approval</dt><dd>${escape(e.approval)}</dd>${e.replyTo?`<dt>Replies to</dt><dd>${escape(e.replyTo)}</dd>`:''}</dl><pre>${escape(payload)}</pre>`;q('#trace-flow').onclick=()=>{flowFilter=e.traceId;render()}}
function clearFlow(){flowFilter='';render()}window.clearFlow=clearFlow;async function post(path,value){const response=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(value)});const result=await response.json();if(!response.ok)throw new Error(result.error||'Control failed');return result}
q('#ok').onclick=async()=>{if(pending)await post('/api/approve',{eventId:pending.id});pending=null;await refresh()};q('#skip').onclick=async()=>{await post('/api/control',{action:'skip',value:Number(q('#skip-count').value)});pending=null;await refresh()};q('#run-until').onclick=async()=>{await post('/api/control',{action:'run-until',value:q('#until').value});pending=null;await refresh()};q('#continue').onclick=async()=>{await post('/api/control',{action:'continue'});pending=null;await refresh()};q('#pause').onclick=async()=>{await post('/api/control',{action:'pause'});await refresh()};
async function refresh(){try{const state=await fetch('/api/state',{cache:'no-store'}).then(r=>r.json());window.traceControls=state.controls;for(const e of state.events){const index=events.findIndex(old=>old.id===e.id);if(index>=0)events[index]=e;else events.push(e)}pending=state.pending;if(pending){const index=events.findIndex(e=>e.id===pending.id);if(index>=0)events[index]=pending;else events.push(pending);if(!selectedId)selectEvent(pending.id)}render()}catch(error){q('#status').textContent='Trace Console is reconnecting…'}}refresh();setInterval(refresh,700);
</script></body></html>"""
