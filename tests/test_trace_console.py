from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
import time
import unittest
from unittest.mock import patch
from urllib.request import Request, urlopen

from resource_research_agent.trace_console import (
    TRACE_HTML,
    TraceHub,
    TraceModelServer,
)


class TraceHubTests(unittest.TestCase):
    def emit_thread(self, hub: TraceHub, **overrides):
        values = {
            "source": "Scout",
            "target": "DSH",
            "kind": "stage-request",
            "summary": "Stage",
            "payload": {"prompt": "research"},
            "trace_id": "trace-one",
        }
        values.update(overrides)
        thread = threading.Thread(target=lambda: hub.emit(**values))
        thread.start()
        return thread

    def wait_pending(self, hub: TraceHub) -> dict:
        for _attempt in range(100):
            pending = hub.state()["pending"]
            if pending:
                return pending
            time.sleep(0.01)
        self.fail("No trace event became pending")

    def test_ok_gates_one_logical_message(self) -> None:
        hub = TraceHub()
        thread = self.emit_thread(hub)
        pending = self.wait_pending(hub)
        self.assertTrue(thread.is_alive())

        hub.approve(pending["id"])
        thread.join(timeout=2)

        self.assertFalse(thread.is_alive())
        event = hub.event(pending["id"])
        self.assertEqual("ok", event["approval"])
        self.assertEqual("trace-one", event["traceId"])

    def test_skip_n_and_run_until_stop_at_the_requested_boundary(self) -> None:
        hub = TraceHub()
        first = self.emit_thread(hub)
        self.wait_pending(hub)
        hub.control("skip", 3)
        first.join(timeout=2)
        hub.emit(source="DSH", target="Qwen", kind="model-request", summary="one", payload={}, trace_id="trace-one")
        hub.emit(source="Qwen", target="DSH", kind="model-response", summary="two", payload={}, trace_id="trace-one")
        fourth = self.emit_thread(
            hub, source="DSH", target="Safe Fetch", kind="fetch-request", summary="four"
        )
        pending = self.wait_pending(hub)
        self.assertEqual(4, pending["sequence"])
        hub.control("run-until", "search")
        fourth.join(timeout=2)
        hub.emit(source="Safe Fetch", target="DSH", kind="fetch-response", summary="five", payload={}, trace_id="trace-one")
        search = self.emit_thread(
            hub, source="DSH", target="DDGS", kind="search-request", summary="six"
        )
        pending = self.wait_pending(hub)
        self.assertEqual("search-request", pending["kind"])
        hub.approve(pending["id"])
        search.join(timeout=2)

    def test_continue_mode_never_blocks_and_pause_restores_gating(self) -> None:
        hub = TraceHub()
        hub.control("continue")
        event = hub.emit(
            source="DSH", target="Qwen", kind="model-request", summary="auto",
            payload={}, trace_id="trace-one",
        )
        self.assertEqual("automatic", event.approval)
        hub.control("pause")
        thread = self.emit_thread(hub)
        pending = self.wait_pending(hub)
        hub.approve(pending["id"])
        thread.join(timeout=2)

    def test_ui_exposes_requested_controls_without_external_assets(self) -> None:
        for phrase in ("OK — next message", "Skip N", "Run to…", "Trace this flow", "Continue without pausing"):
            self.assertIn(phrase, TRACE_HTML)
        self.assertNotIn("https://", TRACE_HTML)


class FakeQwenHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def do_GET(self):
        body = json.dumps({"data": [{"id": "mlx-community/Qwen3.8-27B-8bit"}]}).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0")); self.rfile.read(length)
        body = json.dumps({"choices": [{"message": {"role": "assistant", "content": "answer"}, "finish_reason": "stop"}]}).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)


class TraceModelProxyTests(unittest.TestCase):
    def test_proxy_gates_request_and_response_as_two_logical_messages(self) -> None:
        backend = ThreadingHTTPServer(("127.0.0.1", 0), FakeQwenHandler)
        backend_thread = threading.Thread(target=backend.serve_forever, daemon=True); backend_thread.start()
        hub = TraceHub(); hub.control("continue")
        proxy = TraceModelServer(("127.0.0.1", 0), hub)
        proxy_thread = threading.Thread(target=proxy.serve_forever, daemon=True); proxy_thread.start()
        base = f"http://127.0.0.1:{proxy.server_address[1]}"
        try:
            with patch("resource_research_agent.trace_console.QWEN_BACKEND", f"http://127.0.0.1:{backend.server_address[1]}"):
                request = Request(
                    f"{base}/v1/chat/completions",
                    data=json.dumps({"model": "mlx-community/Qwen3.8-27B-8bit", "messages": []}).encode(),
                    method="POST",
                    headers={"Content-Type": "application/json"},
                )
                with urlopen(request, timeout=5) as response:
                    value = json.load(response)
        finally:
            proxy.shutdown(); proxy.server_close(); proxy_thread.join(timeout=2)
            backend.shutdown(); backend.server_close(); backend_thread.join(timeout=2)

        self.assertEqual("answer", value["choices"][0]["message"]["content"])
        events = hub.state()["events"]
        self.assertEqual(["model-request", "model-response"], [event["kind"] for event in events])
        self.assertEqual(events[0]["id"], events[1]["replyTo"])


if __name__ == "__main__":
    unittest.main()
