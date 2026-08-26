from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
import time
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen
from uuid import uuid4


HUMAN_MODEL_ID = "resource-scout-human"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8082
MAX_REQUEST_BYTES = 10 * 1024 * 1024
MAX_RESPONSE_BYTES = 5 * 1024 * 1024
REQUEST_TIMEOUT_SECONDS = 7200


class HumanModelError(RuntimeError):
    pass


@dataclass
class PendingRequest:
    id: str
    payload: dict[str, Any]
    created_at: str
    response: dict[str, Any] | None = None
    event: threading.Event = field(default_factory=threading.Event)

    def public_value(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "createdAt": self.created_at,
            "model": self.payload.get("model"),
            "messages": self.payload.get("messages", []),
            "tools": self.payload.get("tools", []),
            "responded": self.response is not None,
        }


class HumanModelHub:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._pending: PendingRequest | None = None
        self._last_completed: dict[str, Any] | None = None

    def create(self, payload: dict[str, Any]) -> PendingRequest:
        with self._lock:
            if self._pending is not None and not self._pending.event.is_set():
                raise HumanModelError(
                    "The human researcher is already answering another Scout request"
                )
            request = PendingRequest(
                id=f"human-{uuid4().hex}",
                payload=payload,
                created_at=datetime.now(timezone.utc).isoformat(),
            )
            self._pending = request
            return request

    def state(self) -> dict[str, Any]:
        with self._lock:
            pending = self._pending
            return {
                "waiting": pending is not None and not pending.event.is_set(),
                "request": pending.public_value() if pending is not None else None,
                "lastCompleted": self._last_completed,
            }

    def respond(self, request_id: str, response: dict[str, Any]) -> None:
        with self._lock:
            request = self._pending
            if request is None or request.id != request_id:
                raise HumanModelError("That Scout request is no longer waiting")
            if request.event.is_set():
                raise HumanModelError("That Scout request already has an answer")
            response_type = response.get("type")
            if response_type == "text":
                content = str(response.get("content") or "")
                if not content.strip():
                    raise HumanModelError("An answer cannot be empty")
                normalized = {"type": "text", "content": content}
            elif response_type == "tool":
                name = str(response.get("name") or "").strip()
                arguments = response.get("arguments")
                tool_names = {
                    str(tool.get("function", {}).get("name") or "")
                    for tool in request.payload.get("tools", [])
                    if isinstance(tool, dict) and isinstance(tool.get("function"), dict)
                }
                if not name or name not in tool_names:
                    raise HumanModelError("Choose one of the tools Scout offered")
                if not isinstance(arguments, dict):
                    raise HumanModelError("Tool inputs must be one JSON object")
                normalized = {"type": "tool", "name": name, "arguments": arguments}
            else:
                raise HumanModelError("Response type must be text or tool")
            request.response = normalized
            self._last_completed = {
                "id": request.id,
                "completedAt": datetime.now(timezone.utc).isoformat(),
                "responseType": normalized["type"],
                "toolName": normalized.get("name"),
            }
            request.event.set()

    def finish(self, request: PendingRequest) -> None:
        with self._lock:
            if self._pending is request:
                self._pending = None


class HumanModelServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address: tuple[str, int], hub: HumanModelHub | None = None) -> None:
        super().__init__(address, HumanModelHandler)
        self.hub = hub or HumanModelHub()


class HumanModelHandler(BaseHTTPRequestHandler):
    server: HumanModelServer
    protocol_version = "HTTP/1.1"

    def log_message(self, format: str, *args: Any) -> None:
        return

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        if self.path.rstrip("/") in {"", "/"}:
            self._bytes(HUMAN_MODEL_HTML.encode("utf-8"), "text/html; charset=utf-8")
        elif self.path.rstrip("/") == "/api/state":
            self._json(self.server.hub.state())
        elif self.path.rstrip("/") == "/v1/models":
            self._json(
                {
                    "object": "list",
                    "data": [
                        {
                            "id": HUMAN_MODEL_ID,
                            "object": "model",
                            "created": 0,
                            "owned_by": "resource-scout-human",
                        }
                    ],
                }
            )
        else:
            self._json({"error": "Not found"}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        try:
            if self.path.rstrip("/") == "/api/respond":
                value = self._read_json(MAX_RESPONSE_BYTES)
                self.server.hub.respond(str(value.get("requestId") or ""), value)
                self._json({"ok": True})
            elif self.path.rstrip("/") == "/v1/chat/completions":
                self._completion(self._read_json(MAX_REQUEST_BYTES))
            else:
                self._json({"error": "Not found"}, HTTPStatus.NOT_FOUND)
        except HumanModelError as exc:
            self._json({"error": str(exc)}, HTTPStatus.CONFLICT)
        except ValueError as exc:
            self._json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)

    def _completion(self, payload: dict[str, Any]) -> None:
        if payload.get("model") != HUMAN_MODEL_ID:
            raise ValueError(f"model must be {HUMAN_MODEL_ID}")
        messages = payload.get("messages")
        if not isinstance(messages, list):
            raise ValueError("messages must be an array")
        request = self.server.hub.create(payload)
        try:
            if not request.event.wait(REQUEST_TIMEOUT_SECONDS):
                self._json(
                    {"error": "The human researcher did not answer before Scout's time limit"},
                    HTTPStatus.GATEWAY_TIMEOUT,
                )
                return
            response = request.response
            if response is None:
                self._json({"error": "The human response was lost"}, HTTPStatus.INTERNAL_SERVER_ERROR)
                return
            if payload.get("stream") is True:
                self._stream_completion(request.id, response)
            else:
                self._json(self._completion_value(request.id, response))
        finally:
            self.server.hub.finish(request)

    @staticmethod
    def _message(response: dict[str, Any]) -> tuple[dict[str, Any], str]:
        if response["type"] == "tool":
            call_id = f"call_{uuid4().hex}"
            return (
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": call_id,
                            "type": "function",
                            "function": {
                                "name": response["name"],
                                "arguments": json.dumps(
                                    response["arguments"], ensure_ascii=False, separators=(",", ":")
                                ),
                            },
                        }
                    ],
                },
                "tool_calls",
            )
        return ({"role": "assistant", "content": response["content"]}, "stop")

    def _completion_value(self, request_id: str, response: dict[str, Any]) -> dict[str, Any]:
        message, finish_reason = self._message(response)
        return {
            "id": request_id,
            "object": "chat.completion",
            "created": int(time.time()),
            "model": HUMAN_MODEL_ID,
            "choices": [{"index": 0, "message": message, "finish_reason": finish_reason}],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        }

    def _stream_completion(self, request_id: str, response: dict[str, Any]) -> None:
        message, finish_reason = self._message(response)
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()

        def send(value: dict[str, Any]) -> None:
            self.wfile.write(
                b"data: " + json.dumps(value, ensure_ascii=False).encode("utf-8") + b"\n\n"
            )
            self.wfile.flush()

        base = {
            "id": request_id,
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": HUMAN_MODEL_ID,
        }
        if response["type"] == "tool":
            delta = {"role": "assistant", "content": None, "tool_calls": message["tool_calls"]}
        else:
            delta = {"role": "assistant", "content": message["content"]}
        send({**base, "choices": [{"index": 0, "delta": delta, "finish_reason": None}]})
        send(
            {
                **base,
                "choices": [{"index": 0, "delta": {}, "finish_reason": finish_reason}],
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            }
        )
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()
        self.close_connection = True

    def _read_json(self, maximum: int) -> dict[str, Any]:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise ValueError("Invalid Content-Length") from exc
        if length <= 0 or length > maximum:
            raise ValueError("Request body has an invalid size")
        try:
            value = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"Invalid JSON: {exc}") from exc
        if not isinstance(value, dict):
            raise ValueError("Request body must be one JSON object")
        return value

    def _json(self, value: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
        self._bytes(
            json.dumps(value, ensure_ascii=False).encode("utf-8"),
            "application/json; charset=utf-8",
            status,
        )

    def _bytes(
        self,
        data: bytes,
        content_type: str,
        status: HTTPStatus = HTTPStatus.OK,
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(data)


def catalog_health(port: int = DEFAULT_PORT, timeout: float = 2.0) -> dict[str, Any]:
    url = f"http://127.0.0.1:{port}/v1/models"
    try:
        with urlopen(url, timeout=timeout) as response:
            value = json.load(response)
    except (OSError, URLError, json.JSONDecodeError) as exc:
        raise HumanModelError(f"Human Model is not available at {url}: {exc}") from exc
    entries = value.get("data") if isinstance(value, dict) else None
    ids = [entry.get("id") for entry in entries or [] if isinstance(entry, dict)]
    if HUMAN_MODEL_ID not in ids:
        raise HumanModelError("Human Model did not report the expected local model identity")
    return {"ready": True, "model": HUMAN_MODEL_ID, "endpoint": url.removesuffix("/models")}


HUMAN_MODEL_HTML = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Human Model for Resource Scout</title><style>
:root{font-family:ui-sans-serif,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:#17211d;background:#eef3ef}*{box-sizing:border-box}body{margin:0}.top{padding:22px 28px;background:#173f35;color:white}.top h1{margin:0 0 6px;font-size:24px}.top p{margin:0;color:#d7e8e1}.layout{display:grid;grid-template-columns:minmax(0,1.25fr) minmax(340px,.75fr);gap:18px;padding:18px;max-width:1500px;margin:auto}.card{background:white;border:1px solid #cfdbd4;border-radius:14px;box-shadow:0 3px 14px #173f3512;padding:18px}.status{font-weight:700;color:#27614f}.waiting{color:#9a4d00}.messages{display:grid;gap:12px;max-height:68vh;overflow:auto}.message{border:1px solid #dce5df;border-radius:10px;padding:12px}.role{font-weight:700;text-transform:capitalize;margin-bottom:7px}.message pre,.schema{white-space:pre-wrap;overflow-wrap:anywhere;margin:0;font:13px/1.45 ui-monospace,SFMono-Regular,Menlo,monospace}textarea,select{width:100%;border:1px solid #aebfb5;border-radius:8px;padding:10px;font:14px/1.45 inherit;margin:6px 0 12px}textarea{min-height:180px;font-family:ui-monospace,SFMono-Regular,Menlo,monospace}button{border:0;border-radius:8px;background:#176a52;color:#fff;padding:10px 14px;font-weight:700;cursor:pointer}button:disabled{opacity:.45;cursor:default}.secondary{background:#596b64}.tabs{display:flex;gap:8px;margin:12px 0}.tabs button.active{background:#173f35}.muted{color:#65736d;font-size:13px}.error{color:#a12622;font-weight:700}.hidden{display:none}@media(max-width:850px){.layout{grid-template-columns:1fr}.messages{max-height:none}}
</style></head><body><header class="top"><h1>Human Model for Resource Scout</h1><p>Scout pauses here whenever it would normally ask Qwen. Nothing is sent to a paid model.</p></header>
<main class="layout"><section class="card"><h2>What Scout can see</h2><p id="status" class="status">Waiting for Scout…</p><div id="messages" class="messages"></div></section>
<section class="card"><h2>Your turn</h2><p class="muted">Answer as the model, or ask Scout to run one of the bounded search/fetch tools it offered.</p><div id="empty">Start a research stage in the temporary Scout window. Its request will appear here.</div><div id="response" class="hidden"><div class="tabs"><button id="answer-tab" class="active" type="button">Answer Scout</button><button id="tool-tab" class="secondary" type="button">Use a tool</button></div><div id="answer-panel"><label>Answer<textarea id="answer" placeholder="Type or paste the complete response Scout requested."></textarea></label><button id="send-answer" type="button">Send answer to Scout</button></div><div id="tool-panel" class="hidden"><label>Tool<select id="tool"></select></label><pre id="schema" class="schema"></pre><label>Tool inputs as JSON<textarea id="arguments">{}</textarea></label><button id="send-tool" type="button">Ask Scout to run this tool</button></div><p id="error" class="error"></p></div></section></main>
<script>
let currentId=null,currentTools=[];const q=s=>document.querySelector(s);function text(value){if(typeof value==='string')return value;return JSON.stringify(value,null,2)}
function renderMessages(messages){const root=q('#messages');root.replaceChildren();for(const message of messages||[]){const box=document.createElement('article');box.className='message';const role=document.createElement('div');role.className='role';role.textContent=message.role||'message';const pre=document.createElement('pre');pre.textContent=text(message.content??message);box.append(role,pre);root.append(box)}}
function toolFunction(tool){return tool&&tool.function&&typeof tool.function==='object'?tool.function:null}function renderTools(){const select=q('#tool');select.replaceChildren();for(const tool of currentTools){const fn=toolFunction(tool);if(!fn)continue;const option=document.createElement('option');option.value=fn.name;option.textContent=fn.name;select.append(option)}renderSchema()}
function renderSchema(){const fn=currentTools.map(toolFunction).find(item=>item&&item.name===q('#tool').value);q('#schema').textContent=fn?`${fn.description||''}\n\nInputs:\n${JSON.stringify(fn.parameters||{},null,2)}`:''}
function setMode(mode){q('#answer-panel').classList.toggle('hidden',mode!=='answer');q('#tool-panel').classList.toggle('hidden',mode!=='tool');q('#answer-tab').className=mode==='answer'?'active':'secondary';q('#tool-tab').className=mode==='tool'?'active':'secondary'}
async function refresh(){try{const state=await fetch('/api/state',{cache:'no-store'}).then(r=>r.json());const request=state.request;if(state.waiting&&request){q('#status').textContent='Scout is waiting for you.';q('#status').className='status waiting';q('#empty').classList.add('hidden');q('#response').classList.remove('hidden');if(currentId!==request.id){currentId=request.id;currentTools=request.tools||[];renderMessages(request.messages);renderTools();q('#answer').value='';q('#arguments').value='{}';q('#error').textContent='';setMode('answer')}}else{q('#status').textContent='Waiting for Scout…';q('#status').className='status';q('#empty').classList.remove('hidden');q('#response').classList.add('hidden');currentId=null}}catch(error){q('#status').textContent='Human Model app is reconnecting…'}}
async function respond(value){q('#error').textContent='';try{const response=await fetch('/api/respond',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({requestId:currentId,...value})});const result=await response.json();if(!response.ok)throw new Error(result.error||'Scout did not accept the response');await refresh()}catch(error){q('#error').textContent=error.message}}
q('#answer-tab').onclick=()=>setMode('answer');q('#tool-tab').onclick=()=>setMode('tool');q('#tool').onchange=renderSchema;q('#send-answer').onclick=()=>respond({type:'text',content:q('#answer').value});q('#send-tool').onclick=()=>{try{respond({type:'tool',name:q('#tool').value,arguments:JSON.parse(q('#arguments').value)})}catch(error){q('#error').textContent='Tool inputs are not valid JSON.'}};refresh();setInterval(refresh,1000);
</script></body></html>"""

