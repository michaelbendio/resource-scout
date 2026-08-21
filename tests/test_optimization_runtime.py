from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from resource_research_agent.optimization_runtime import (
    LocalQwenJSONClient,
    ReviewedIdentityResolver,
    _extract_object,
    html_to_text,
)


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


if __name__ == "__main__":
    unittest.main()
