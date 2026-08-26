from __future__ import annotations

import json
import threading
import time
import unittest
from urllib.request import Request, urlopen

from resource_research_agent.human_model import (
    HUMAN_MODEL_HTML,
    HUMAN_MODEL_ID,
    HumanModelServer,
)


class HumanModelTests(unittest.TestCase):
    def setUp(self) -> None:
        self.server = HumanModelServer(("127.0.0.1", 0))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def request(self, path: str, payload: dict | None = None) -> tuple[int, bytes, str]:
        body = None if payload is None else json.dumps(payload).encode()
        request = Request(
            f"{self.base_url}{path}",
            data=body,
            method="GET" if body is None else "POST",
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )
        with urlopen(request, timeout=5) as response:
            return response.status, response.read(), response.headers.get("Content-Type", "")

    def wait_for_pending(self) -> dict:
        for _attempt in range(100):
            state = self.server.hub.state()
            if state["waiting"]:
                return state["request"]
            time.sleep(0.01)
        self.fail("Human model request did not become pending")

    def test_catalog_and_ui_are_local_human_model_surfaces(self) -> None:
        _status, body, _content_type = self.request("/v1/models")
        self.assertEqual(HUMAN_MODEL_ID, json.loads(body)["data"][0]["id"])
        self.assertIn("Scout pauses here", HUMAN_MODEL_HTML)
        self.assertNotIn("https://", HUMAN_MODEL_HTML)

    def test_nonstreaming_text_answer_unblocks_scout_request(self) -> None:
        result: dict = {}

        def call_model() -> None:
            _status, body, _content_type = self.request(
                "/v1/chat/completions",
                {"model": HUMAN_MODEL_ID, "messages": [{"role": "user", "content": "Research"}]},
            )
            result.update(json.loads(body))

        caller = threading.Thread(target=call_model)
        caller.start()
        pending = self.wait_for_pending()
        self.request(
            "/api/respond",
            {"requestId": pending["id"], "type": "text", "content": '{"summary":"done"}'},
        )
        caller.join(timeout=5)

        self.assertEqual('{"summary":"done"}', result["choices"][0]["message"]["content"])
        self.assertEqual("stop", result["choices"][0]["finish_reason"])

    def test_streaming_tool_call_uses_only_an_offered_tool(self) -> None:
        result: dict[str, object] = {}
        tool = {
            "type": "function",
            "function": {
                "name": "web_search",
                "description": "Search",
                "parameters": {"type": "object", "properties": {"query": {"type": "string"}}},
            },
        }

        def call_model() -> None:
            _status, body, content_type = self.request(
                "/v1/chat/completions",
                {
                    "model": HUMAN_MODEL_ID,
                    "stream": True,
                    "messages": [{"role": "user", "content": "Research"}],
                    "tools": [tool],
                },
            )
            result.update({"body": body.decode(), "contentType": content_type})

        caller = threading.Thread(target=call_model)
        caller.start()
        pending = self.wait_for_pending()
        self.request(
            "/api/respond",
            {
                "requestId": pending["id"],
                "type": "tool",
                "name": "web_search",
                "arguments": {"query": "Mesa food pantry"},
            },
        )
        caller.join(timeout=5)

        self.assertIn("text/event-stream", str(result["contentType"]))
        self.assertIn('"name": "web_search"', str(result["body"]))
        self.assertIn('Mesa food pantry', str(result["body"]))
        self.assertIn('"finish_reason": "tool_calls"', str(result["body"]))
        self.assertTrue(str(result["body"]).endswith("data: [DONE]\n\n"))


if __name__ == "__main__":
    unittest.main()

