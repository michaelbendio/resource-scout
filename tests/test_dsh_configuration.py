from __future__ import annotations

import unittest
from dataclasses import replace

from resource_research_agent.dsh_configuration import (
    DEEPSEEK_CONFIGURATION,
    LOCAL_QWEN_CONFIGURATION,
    TRACE_QWEN_CONFIGURATION,
    local_model_catalog_error,
    resolve_dsh_configuration,
    zero_metered_services_violations,
)


class DSHConfigurationTests(unittest.TestCase):
    def test_local_qwen_contract_names_every_execution_provider(self) -> None:
        configuration = resolve_dsh_configuration(LOCAL_QWEN_CONFIGURATION)

        self.assertEqual("qwen-local", configuration.model_provider)
        self.assertEqual("mlx-community/Qwen3.8-27B-8bit", configuration.model)
        self.assertEqual("http://127.0.0.1:8080/v1", configuration.model_endpoint)
        self.assertEqual(65_536, configuration.context_window)
        self.assertEqual("medium", configuration.reasoning)
        self.assertEqual("ddgs", configuration.search_provider)
        self.assertEqual("safe-http", configuration.fetch_provider)
        self.assertEqual(7200, configuration.timeout_seconds)
        self.assertEqual("8-bit", configuration.quantization)

    def test_local_qwen_contract_has_no_metered_route_or_fallback(self) -> None:
        configuration = resolve_dsh_configuration(LOCAL_QWEN_CONFIGURATION)

        self.assertTrue(configuration.uses_only_unmetered_services)
        self.assertFalse(configuration.metered)
        self.assertNotEqual("deepseek-official", configuration.model_provider)
        self.assertNotEqual("deepseek-official", configuration.search_provider)
        self.assertEqual((), configuration.model_fallbacks)
        self.assertEqual((), configuration.search_fallbacks)
        self.assertEqual([], zero_metered_services_violations(configuration))

    def test_zero_metered_invariant_fails_closed_for_cloud_or_fallbacks(self) -> None:
        configuration = resolve_dsh_configuration(LOCAL_QWEN_CONFIGURATION)
        unsafe = replace(
            configuration,
            model_endpoint="https://api.example.test/v1",
            model_provider="deepseek-official",
            search_provider="deepseek-official",
            model_fallbacks=("deepseek-official/deepseek-v4-flash",),
            search_fallbacks=("deepseek-official",),
            metered=True,
        )

        violations = zero_metered_services_violations(unsafe)
        self.assertIn("model endpoint is not loopback HTTP", violations)
        self.assertIn("model provider is not an approved local provider", violations)
        self.assertIn("search provider is not DDGS", violations)
        self.assertIn("a model fallback is configured", violations)
        self.assertIn("a search fallback is configured", violations)
        self.assertIn("configuration is marked metered", violations)
        self.assertFalse(unsafe.uses_only_unmetered_services)

    def test_missing_local_model_has_an_actionable_failure(self) -> None:
        configuration = resolve_dsh_configuration(LOCAL_QWEN_CONFIGURATION)

        message = local_model_catalog_error(configuration, ["some-other-model"])
        self.assertIn(configuration.model, message)
        self.assertIn(configuration.model_endpoint, message)
        self.assertIn("Start the pinned MLX model server", message)
        self.assertEqual("", local_model_catalog_error(configuration, [configuration.model]))

    def test_deepseek_remains_an_explicit_metered_comparison_configuration(self) -> None:
        configuration = resolve_dsh_configuration(DEEPSEEK_CONFIGURATION)

        self.assertTrue(configuration.metered)
        self.assertEqual("deepseek-official", configuration.model_provider)
        self.assertEqual("deepseek-official", configuration.search_provider)
        self.assertFalse(configuration.uses_only_unmetered_services)

    def test_trace_configuration_is_loopback_only_and_unmetered(self) -> None:
        configuration = resolve_dsh_configuration(TRACE_QWEN_CONFIGURATION)

        self.assertEqual("qwen-trace-local", configuration.model_provider)
        self.assertEqual("mlx-community/Qwen3.8-27B-8bit", configuration.model)
        self.assertEqual("http://127.0.0.1:8083/v1", configuration.model_endpoint)
        self.assertEqual("ddgs", configuration.search_provider)
        self.assertEqual("safe-http", configuration.fetch_provider)
        self.assertFalse(configuration.metered)
        self.assertTrue(configuration.uses_only_unmetered_services)
        self.assertEqual([], zero_metered_services_violations(configuration))

    def test_unknown_configuration_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown DSH configuration"):
            resolve_dsh_configuration("automatic")


if __name__ == "__main__":
    unittest.main()
