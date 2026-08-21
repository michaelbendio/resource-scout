from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit


LOCAL_QWEN_CONFIGURATION = "local-qwen"
DEEPSEEK_CONFIGURATION = "deepseek"


@dataclass(frozen=True)
class DSHConfiguration:
    key: str
    display_name: str
    model_provider: str
    model: str
    model_endpoint: str
    context_window: int
    reasoning: str
    search_provider: str
    fetch_provider: str
    timeout_seconds: int
    metered: bool
    model_fallbacks: tuple[str, ...] = ()
    search_fallbacks: tuple[str, ...] = ()

    @property
    def uses_only_unmetered_services(self) -> bool:
        return not zero_metered_services_violations(self)

    def as_status(self) -> dict[str, Any]:
        return {
            "configuration": self.key,
            "configurationDisplayName": self.display_name,
            "provider": self.model_provider,
            "model": self.model,
            "endpoint": self.model_endpoint,
            "contextWindow": self.context_window,
            "reasoning": self.reasoning,
            "searchProvider": self.search_provider,
            "fetchProvider": self.fetch_provider,
            "timeoutSeconds": self.timeout_seconds,
            "metered": self.metered,
            "modelFallbacks": list(self.model_fallbacks),
            "searchFallbacks": list(self.search_fallbacks),
            "usesOnlyUnmeteredServices": self.uses_only_unmetered_services,
        }


CONFIGURATIONS: dict[str, DSHConfiguration] = {
    LOCAL_QWEN_CONFIGURATION: DSHConfiguration(
        key=LOCAL_QWEN_CONFIGURATION,
        display_name="Local Qwen - no metered services",
        model_provider="qwen-local",
        model="mlx-community/Qwen3.8-27B-8bit",
        model_endpoint="http://127.0.0.1:8080/v1",
        context_window=65_536,
        reasoning="medium",
        search_provider="ddgs",
        fetch_provider="safe-http",
        timeout_seconds=900,
        metered=False,
    ),
    DEEPSEEK_CONFIGURATION: DSHConfiguration(
        key=DEEPSEEK_CONFIGURATION,
        display_name="DeepSeek - metered",
        model_provider="deepseek-official",
        model="deepseek-v4-flash",
        model_endpoint="https://api.deepseek.com",
        context_window=128_000,
        reasoning="provider-default",
        search_provider="deepseek-official",
        fetch_provider="none",
        timeout_seconds=900,
        metered=True,
    ),
}


def resolve_dsh_configuration(key: str) -> DSHConfiguration:
    normalized = str(key or "").strip().casefold()
    try:
        return CONFIGURATIONS[normalized]
    except KeyError as exc:
        choices = ", ".join(sorted(CONFIGURATIONS))
        raise ValueError(f"Unknown DSH configuration {key!r}; choose one of: {choices}") from exc


def zero_metered_services_violations(configuration: DSHConfiguration) -> list[str]:
    violations: list[str] = []
    endpoint = urlsplit(configuration.model_endpoint)
    if endpoint.scheme != "http" or endpoint.hostname not in {"127.0.0.1", "localhost", "::1"}:
        violations.append("model endpoint is not loopback HTTP")
    if configuration.model_provider != "qwen-local":
        violations.append("model provider is not qwen-local")
    if configuration.search_provider != "ddgs":
        violations.append("search provider is not DDGS")
    if configuration.fetch_provider != "safe-http":
        violations.append("fetch provider is not the safe local fetcher")
    if configuration.model_fallbacks:
        violations.append("a model fallback is configured")
    if configuration.search_fallbacks:
        violations.append("a search fallback is configured")
    if configuration.metered:
        violations.append("configuration is marked metered")
    return violations


def local_model_catalog_error(
    configuration: DSHConfiguration, model_ids: list[str] | tuple[str, ...]
) -> str:
    if not configuration.uses_only_unmetered_services:
        return "The selected DSH configuration is not the Local Qwen configuration."
    if configuration.model not in model_ids:
        return (
            f"Local Qwen is unavailable: {configuration.model} is not reported by "
            f"{configuration.model_endpoint}/models. Start the pinned MLX model server first."
        )
    return ""

