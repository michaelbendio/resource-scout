from __future__ import annotations

import json
import os
import re
import subprocess
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from .local_qwen import catalog_health
from .optimization_models import ModelInvocation, OptimizationModelError
from .optimization_pipeline import canonicalize_discovery_url


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DDGS_PYTHON = PROJECT_ROOT / "dsh-runtime" / ".venv-ddgs" / "bin" / "python"
DDGS_HELPER = PROJECT_ROOT / "dsh-plugins" / "web-search-ddgs" / "search.py"
SAFE_FETCH_HELPER = PROJECT_ROOT / "dsh-plugins" / "web-fetch-safe" / "fetch-cli.js"
PINNED_MODELS = {
    "4-bit": "mlx-community/Qwen3.8-27B-4bit",
    "8-bit": "mlx-community/Qwen3.8-27B-8bit",
}


class OptimizationRuntimeError(RuntimeError):
    pass


class _VisibleText(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.hidden_depth = 0

    def handle_starttag(self, tag: str, _attrs: list[tuple[str, str | None]]) -> None:
        if tag.casefold() in {"script", "style", "noscript", "svg"}:
            self.hidden_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.casefold() in {"script", "style", "noscript", "svg"} and self.hidden_depth:
            self.hidden_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self.hidden_depth:
            text = " ".join(data.split())
            if text:
                self.parts.append(text)


def html_to_text(value: str) -> str:
    parser = _VisibleText()
    parser.feed(value)
    return "\n".join(parser.parts)


class DDGSSearchClient:
    def __init__(self, *, timeout_seconds: int = 60) -> None:
        self.timeout_seconds = timeout_seconds

    def __call__(self, query: str, max_results: int) -> list[dict[str, Any]]:
        if not DDGS_PYTHON.is_file() or not DDGS_HELPER.is_file():
            raise OptimizationRuntimeError("The project-owned DDGS runtime is unavailable")
        try:
            completed = subprocess.run(
                [str(DDGS_PYTHON), str(DDGS_HELPER)],
                input=json.dumps({"query": query, "maxResults": max_results}),
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
                env={**os.environ, "PYTHONUNBUFFERED": "1"},
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise OptimizationRuntimeError(f"DDGS search failed: {error}") from error
        if completed.returncode != 0:
            raise OptimizationRuntimeError(
                f"DDGS search failed: {completed.stderr.strip() or completed.returncode}"
            )
        try:
            value = json.loads(completed.stdout)
        except json.JSONDecodeError as error:
            raise OptimizationRuntimeError("DDGS search returned invalid JSON") from error
        if not isinstance(value, dict) or not isinstance(value.get("sources"), list):
            raise OptimizationRuntimeError("DDGS search returned the wrong response shape")
        return [source for source in value["sources"] if isinstance(source, dict)]


class SafeFetchClient:
    def __init__(self, *, timeout_seconds: int = 35, max_bytes: int = 500_000) -> None:
        self.timeout_seconds = timeout_seconds
        self.max_bytes = max_bytes

    def __call__(self, url: str) -> dict[str, Any]:
        if not SAFE_FETCH_HELPER.is_file():
            raise OptimizationRuntimeError("The project-owned safe fetch helper is unavailable")
        try:
            completed = subprocess.run(
                ["node", str(SAFE_FETCH_HELPER)],
                input=json.dumps(
                    {
                        "url": url,
                        "timeoutMs": self.timeout_seconds * 1000,
                        "maxBytes": self.max_bytes,
                        "maxRedirects": 5,
                    }
                ),
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds + 5,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise OptimizationRuntimeError(f"Safe fetch failed: {error}") from error
        if completed.returncode != 0:
            raise OptimizationRuntimeError(
                f"Safe fetch failed: {completed.stderr.strip() or completed.returncode}"
            )
        try:
            value = json.loads(completed.stdout)
        except json.JSONDecodeError as error:
            raise OptimizationRuntimeError("Safe fetch returned invalid JSON") from error
        body = value.get("body") if isinstance(value, dict) else None
        if not isinstance(body, dict) or body.get("kind") not in {"html", "text"}:
            raise OptimizationRuntimeError("Safe fetch returned the wrong response shape")
        content = str(body.get("content") or "")
        return {
            "text": html_to_text(content) if body["kind"] == "html" else content,
            "finalUrl": value.get("url") or url,
            "statusCode": value.get("statusCode"),
            "contentType": "text/html" if body["kind"] == "html" else "text/plain",
            "truncated": bool(value.get("truncated")),
        }


class ReviewedIdentityResolver:
    def __init__(self, decisions: dict[str, dict[str, Any]]) -> None:
        self.decisions = {
            canonicalize_discovery_url(url): decision
            for url, decision in decisions.items()
            if isinstance(decision, dict)
        }

    @classmethod
    def from_path(cls, path: Path) -> "ReviewedIdentityResolver":
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict) or not isinstance(value.get("decisions"), dict):
            raise OptimizationRuntimeError("Identity review must contain a decisions object")
        return cls(value["decisions"])

    def __call__(self, result: dict[str, Any]) -> dict[str, Any] | None:
        try:
            return self.decisions.get(canonicalize_discovery_url(result.get("url")))
        except ValueError:
            return None


def _extract_object(text: str) -> dict[str, Any]:
    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE).strip()
    candidates = [cleaned]
    first = cleaned.find("{")
    last = cleaned.rfind("}")
    if 0 <= first < last:
        candidates.append(cleaned[first : last + 1])
    for candidate in candidates:
        try:
            value = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    raise OptimizationModelError("Local Qwen did not return one valid JSON object")


class LocalQwenJSONClient:
    def __init__(
        self,
        quantization: str,
        *,
        endpoint: str = "http://127.0.0.1:8080/v1",
        timeout_seconds: int = 900,
    ) -> None:
        if quantization not in PINNED_MODELS:
            raise ValueError("Quantization must be 4-bit or 8-bit")
        parsed = urlsplit(endpoint)
        if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("Local Qwen endpoint must be loopback HTTP")
        self.quantization = quantization
        self.model = PINNED_MODELS[quantization]
        self.endpoint = endpoint.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def validate(self) -> dict[str, Any]:
        return catalog_health(timeout=5, model=self.model)

    def __call__(self, prompt: dict[str, Any]) -> ModelInvocation:
        self.validate()
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a precise evidence extraction component. "
                        "Return only one JSON object matching the requested structure."
                    ),
                },
                {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
            ],
            "temperature": 0,
            "max_tokens": 16384,
        }
        request = Request(
            f"{self.endpoint}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                value = json.load(response)
        except Exception as error:
            raise OptimizationModelError(f"Local Qwen request failed: {error}") from error
        try:
            content = str(value["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError) as error:
            raise OptimizationModelError("Local Qwen response contained no completion") from error
        reported = value.get("usage") if isinstance(value.get("usage"), dict) else {}
        usage = {
            **reported,
            "provider": "qwen-local",
            "model": self.model,
            "quantization": self.quantization,
            "endpoint": self.endpoint,
            "metered": False,
            "fallbacks": [],
        }
        return ModelInvocation(result=_extract_object(content), raw_output=content, usage=usage)
