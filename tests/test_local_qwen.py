from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from resource_research_agent.dsh_configuration import (
    LOCAL_QWEN_CONFIGURATION,
    resolve_dsh_configuration,
)
from resource_research_agent.local_qwen import (
    BACKEND_REQUEST_TIMEOUT_SECONDS,
    LOCAL_QWEN_MAX_COMPLETION_TOKENS,
    LocalQwenError,
    PINNED_MODELS,
    catalog_health,
    completion_health,
    find_mlx_server,
    main,
    mlx_compatible_payload,
    server_command,
    validated_health,
    write_health_stamp,
)
from resource_research_agent.mlx_server_workaround import (
    install_arrays_cache_materialization,
)


class _JSONResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()


class LocalQwenRuntimeTests(unittest.TestCase):
    def test_backend_proxy_allows_the_declared_two_hour_model_request(self) -> None:
        self.assertEqual(7200, BACKEND_REQUEST_TIMEOUT_SECONDS)

    def test_explicit_runtime_wins_over_homebrew_and_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / "mlx_lm.server"
            executable.write_text("#!/bin/sh\n", encoding="utf-8")
            executable.chmod(0o755)

            resolved = find_mlx_server({"RESOURCE_SCOUT_MLX_SERVER": str(executable)})

        self.assertEqual(executable.resolve(), resolved)

    def test_server_command_pins_model_loopback_port_and_thinking(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / "mlx_lm.server"
            executable.write_text("#!/test/mlx-python\n", encoding="utf-8")
            command = server_command(executable)
        configuration = resolve_dsh_configuration(LOCAL_QWEN_CONFIGURATION)

        self.assertEqual("/test/mlx-python", command[0])
        self.assertEqual(
            ["-m", "resource_research_agent.mlx_server_workaround"], command[1:3]
        )
        self.assertEqual(configuration.model, command[command.index("--model") + 1])
        self.assertEqual("127.0.0.1", command[command.index("--host") + 1])
        self.assertEqual("8081", command[command.index("--port") + 1])
        self.assertEqual(
            str(LOCAL_QWEN_MAX_COMPLETION_TOKENS),
            command[command.index("--max-tokens") + 1],
        )
        self.assertEqual(
            {"enable_thinking": True, "reasoning_effort": "medium"},
            json.loads(command[command.index("--chat-template-args") + 1]),
        )

    def test_server_command_can_select_either_pinned_quantization(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / "mlx_lm.server"
            executable.write_text("#!/test/mlx-python\n", encoding="utf-8")
            for quantization, model in PINNED_MODELS.items():
                command = server_command(executable, model=model)
                self.assertEqual(model, command[command.index("--model") + 1], quantization)

    def test_arrays_cache_workaround_materializes_each_advanced_field(self) -> None:
        calls = []

        class Cache:
            def __init__(self) -> None:
                self.lengths = "lengths-0"
                self.left_padding = "padding-0"

            def advance(self, count: int) -> None:
                self.lengths = f"lengths-{count}"
                self.left_padding = f"padding-{count}"

        self.assertTrue(install_arrays_cache_materialization(Cache, lambda *v: calls.append(v)))
        self.assertFalse(install_arrays_cache_materialization(Cache, lambda *_v: None))
        cache = Cache()
        cache.advance(3)

        self.assertEqual([("lengths-3", "padding-3")], calls)

    def test_compatibility_payload_adapts_dsh_without_changing_the_input(self) -> None:
        original = {
            "messages": [
                {"role": "developer", "content": "instructions"},
                {"role": "user", "content": "request"},
            ],
            "max_completion_tokens": 123,
            "store": False,
            "stream": True,
        }
        compatible = mlx_compatible_payload(original)
        self.assertEqual("system", compatible["messages"][0]["role"])
        self.assertEqual("user", compatible["messages"][1]["role"])
        self.assertEqual(123, compatible["max_tokens"])
        self.assertNotIn("max_completion_tokens", compatible)
        self.assertNotIn("store", compatible)
        self.assertEqual("developer", original["messages"][0]["role"])

    def test_catalog_health_requires_the_exact_pinned_model(self) -> None:
        configuration = resolve_dsh_configuration(LOCAL_QWEN_CONFIGURATION)
        payload = {"data": [{"id": configuration.model}]}
        with patch(
            "resource_research_agent.local_qwen.urlopen",
            return_value=_JSONResponse(json.dumps(payload).encode()),
        ):
            status = catalog_health()
        self.assertTrue(status["ready"])
        self.assertEqual(configuration.model, status["model"])

        with patch(
            "resource_research_agent.local_qwen.urlopen",
            return_value=_JSONResponse(b'{"data":[{"id":"another-model"}]}'),
        ):
            with self.assertRaisesRegex(LocalQwenError, "does not report"):
                catalog_health()

    def test_completion_health_requires_a_real_completion_marker(self) -> None:
        configuration = resolve_dsh_configuration(LOCAL_QWEN_CONFIGURATION)
        responses = [
            _JSONResponse(json.dumps({"data": [{"id": configuration.model}]}).encode()),
            _JSONResponse(
                json.dumps(
                    {"choices": [{"message": {"content": "LOCAL_QWEN_READY"}}]}
                ).encode()
            ),
            _JSONResponse(json.dumps({"data": [{"id": configuration.model}]}).encode()),
        ]
        with patch("resource_research_agent.local_qwen.urlopen", side_effect=responses), patch(
            "resource_research_agent.local_qwen.server_identity",
            return_value={"serverPid": 123, "serverStarted": "test start"},
        ):
            status = completion_health()
        self.assertEqual("LOCAL_QWEN_READY", status["completion"])

    def test_validated_health_requires_a_stamp_from_the_current_server(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            stamp = Path(directory) / "health.json"
            catalog = {
                "ready": True,
                "endpoint": "http://127.0.0.1:8080/v1",
                "model": "mlx-community/Qwen3.8-27B-4bit",
                "availableModels": ["mlx-community/Qwen3.8-27B-4bit"],
            }
            identity = {"serverPid": 123, "serverStarted": "test start"}
            with patch(
                "resource_research_agent.local_qwen.catalog_health", return_value=catalog
            ), patch(
                "resource_research_agent.local_qwen.server_identity", return_value=identity
            ):
                with self.assertRaisesRegex(LocalQwenError, "Run ./local-qwen.sh health"):
                    validated_health(path=stamp)
                write_health_stamp(
                    {**catalog, **identity, "completion": "LOCAL_QWEN_READY"}, stamp
                )
                self.assertTrue(validated_health(path=stamp)["validated"])
                with patch(
                    "resource_research_agent.local_qwen.server_identity",
                    return_value={"serverPid": 456, "serverStarted": "later start"},
                ):
                    with self.assertRaisesRegex(LocalQwenError, "server changed"):
                        validated_health(path=stamp)

    def test_health_command_fails_clearly_when_server_is_unavailable(self) -> None:
        with patch(
            "resource_research_agent.local_qwen.completion_health",
            side_effect=LocalQwenError("Local Qwen is not reachable"),
        ):
            with patch("sys.stderr", new_callable=io.StringIO) as stderr:
                result = main(["health"])
        self.assertEqual(1, result)
        self.assertIn("not reachable", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
