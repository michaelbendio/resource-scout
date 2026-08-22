from __future__ import annotations

import io
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from resource_research_agent.optimization_runtime import (
    LOCAL_QWEN_MAX_COMPLETION_TOKENS,
    LocalQwenJSONClient,
    ReviewedIdentityResolver,
    _extract_object,
    html_to_text,
)
from resource_research_agent.optimization_models import OptimizationModelError


class _JSONResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()


class OptimizationRuntimeTests(unittest.TestCase):
    def test_visible_html_text_excludes_script_and_style(self) -> None:
        text = html_to_text("<h1>Housing</h1><script>secret()</script><p>Call first</p>")
        self.assertEqual("Housing\nCall first", text)

    def test_reviewed_identity_resolution_is_url_canonical(self) -> None:
        resolver = ReviewedIdentityResolver(
            {
                "HTTPS://Example.org/program/?utm_source=test": {
                    "organization": "Example",
                    "program": "Housing",
                }
            }
        )
        self.assertEqual(
            "Housing",
            resolver({"url": "https://example.org/program"})["program"],
        )
        self.assertIsNone(resolver({"url": "https://example.org/other"}))

    def test_local_json_client_rejects_nonloopback_and_wrong_model(self) -> None:
        with self.assertRaisesRegex(ValueError, "loopback"):
            LocalQwenJSONClient("4-bit", endpoint="https://api.example/v1")
        with self.assertRaisesRegex(ValueError, "4-bit or 8-bit"):
            LocalQwenJSONClient("16-bit")

    def test_local_json_client_validates_exact_quantization(self) -> None:
        client = LocalQwenJSONClient("8-bit")
        with patch(
            "resource_research_agent.optimization_runtime.catalog_health",
            return_value={"model": client.model},
        ) as health:
            self.assertEqual(client.model, client.validate()["model"])
        health.assert_called_once_with(timeout=5, model=client.model)

    def test_json_extraction_allows_thinking_wrapper_only(self) -> None:
        self.assertEqual(
            {"status": "ok"},
            _extract_object('<think>private reasoning</think>\n{"status":"ok"}'),
        )

    def test_local_client_has_no_metered_or_fallback_configuration(self) -> None:
        client = LocalQwenJSONClient("4-bit")
        self.assertEqual("http://127.0.0.1:8080/v1", client.endpoint)
        self.assertEqual("mlx-community/Qwen3.8-27B-4bit", client.model)
        self.assertEqual(32768, client.max_completion_tokens)

    def test_local_client_rejects_allowance_above_server_limit(self) -> None:
        with self.assertRaisesRegex(ValueError, "between 1 and 32768"):
            LocalQwenJSONClient(
                "4-bit",
                max_completion_tokens=LOCAL_QWEN_MAX_COMPLETION_TOKENS + 1,
            )

    def test_local_client_sends_and_records_declared_completion_allowance(self) -> None:
        client = LocalQwenJSONClient("4-bit")
        captured = {}

        def respond(request, *, timeout):
            captured.update(json.loads(request.data))
            self.assertEqual(client.timeout_seconds, timeout)
            return _JSONResponse(
                json.dumps(
                    {
                        "choices": [
                            {
                                "finish_reason": "stop",
                                "message": {"content": '{"status":"ok"}'},
                            }
                        ],
                        "usage": {"completion_tokens": 7},
                    }
                ).encode()
            )

        with patch.object(client, "validate"), patch(
            "resource_research_agent.optimization_runtime.urlopen",
            side_effect=respond,
        ):
            invocation = client({"operation": "fixture"})

        self.assertEqual(32768, captured["max_tokens"])
        self.assertEqual("stop", invocation.usage["finishReason"])

    def test_local_client_preserves_unparseable_completion_and_usage(self) -> None:
        client = LocalQwenJSONClient("4-bit")
        response = _JSONResponse(
            json.dumps(
                {
                    "choices": [
                        {
                            "finish_reason": "length",
                            "message": {"content": "unfinished JSON {"},
                        }
                    ],
                    "usage": {
                        "completion_tokens": LOCAL_QWEN_MAX_COMPLETION_TOKENS
                    },
                }
            ).encode()
        )
        with patch.object(client, "validate"), patch(
            "resource_research_agent.optimization_runtime.urlopen",
            return_value=response,
        ):
            with self.assertRaisesRegex(
                OptimizationModelError, "32768-token completion limit"
            ) as raised:
                client({"operation": "fixture"})

        self.assertEqual("unfinished JSON {", raised.exception.raw_output)
        self.assertEqual(32768, raised.exception.usage["completion_tokens"])
        self.assertEqual("length", raised.exception.usage["finishReason"])
        self.assertFalse(raised.exception.usage["metered"])


if __name__ == "__main__":
    unittest.main()
