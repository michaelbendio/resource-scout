from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
import tempfile
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_SETTINGS: dict[str, Any] = {
    "adapter": "hermes",
    "hermesCommand": "",
    "hermesProfile": "",
    "hermesProvider": "",
    "hermesModel": "",
    "dshCommand": "",
    "dshModel": "",
    # Legacy shared keys remain readable so existing databases keep working.
    "command": "",
    "profile": "",
    "provider": "",
    "model": "",
    "timeoutSeconds": 900,
    "maxTurns": 80,
}


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DSH_DEFAULT_MODEL = "deepseek-v4-flash"


@dataclass(frozen=True)
class AgentRunResult:
    output: str
    result: dict[str, Any]
    usage: dict[str, Any] | None = None


class AgentRunError(RuntimeError):
    def __init__(self, message: str, output: str = "") -> None:
        super().__init__(message)
        self.output = output


class ResearchAgentAdapter(ABC):
    key = "unknown"

    @abstractmethod
    def status(self) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def run(self, prompt: str) -> AgentRunResult:
        raise NotImplementedError


def merged_settings(saved: dict[str, Any] | None = None) -> dict[str, Any]:
    result = dict(DEFAULT_SETTINGS)
    result.update(saved or {})
    return result


def _command_candidates(configured: str = "") -> list[list[str]]:
    candidates: list[list[str]] = []
    override = configured.strip() or os.environ.get("HERMES_COMMAND", "").strip()
    if override:
        candidates.append(shlex.split(override))
    found = shutil.which("hermes")
    if found:
        candidates.append([found])
    home = Path.home()
    for path in (home / ".local/bin/hermes", home / ".hermes/bin/hermes"):
        if path.is_file():
            candidates.append([str(path)])
    unique: list[list[str]] = []
    for candidate in candidates:
        if candidate and candidate not in unique:
            unique.append(candidate)
    return unique


def _extract_json_object(output: str, agent_name: str = "Research agent") -> dict[str, Any]:
    text = output.strip()
    if not text:
        raise AgentRunError(f"{agent_name} returned an empty response", output)
    candidates = [text]
    fenced = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL | re.IGNORECASE)
    candidates.extend(fenced)
    first = text.find("{")
    last = text.rfind("}")
    if 0 <= first < last:
        candidates.append(text[first : last + 1])
    for candidate in candidates:
        try:
            value = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    raise AgentRunError(f"{agent_name} did not return the required JSON research object", output)


def _validate_result(value: dict[str, Any], agent_name: str = "Research agent") -> dict[str, Any]:
    candidates = value.get("candidates", [])
    lessons = value.get("lessons", [])
    if not isinstance(candidates, list):
        raise AgentRunError(f"{agent_name} result field 'candidates' must be an array")
    if not isinstance(lessons, list):
        raise AgentRunError(f"{agent_name} result field 'lessons' must be an array")
    clean_candidates = [candidate for candidate in candidates if isinstance(candidate, dict)]
    for candidate in clean_candidates:
        if not str(candidate.get("name") or candidate.get("title") or "").strip():
            candidate["name"] = "Unnamed candidate"
    clean_lessons = []
    for lesson in lessons:
        if isinstance(lesson, str) and lesson.strip():
            clean_lessons.append({"scope": "category", "text": lesson.strip(), "rationale": ""})
        elif isinstance(lesson, dict) and str(lesson.get("text", "")).strip():
            clean_lessons.append({
                "scope": lesson.get("scope") if lesson.get("scope") in {"category", "general"} else "category",
                "text": str(lesson["text"]).strip(),
                "rationale": str(lesson.get("rationale", "")).strip(),
            })
    value["candidates"] = clean_candidates
    value["lessons"] = clean_lessons
    value["summary"] = str(value.get("summary", "")).strip()
    return value


class HermesCLIAdapter(ResearchAgentAdapter):
    key = "hermes"

    def __init__(self, settings: dict[str, Any] | None = None) -> None:
        self.settings = merged_settings(settings)

    def _command(self) -> list[str] | None:
        configured = str(self.settings.get("hermesCommand", "")).strip()
        if not configured and self.settings.get("adapter") == "hermes":
            configured = str(self.settings.get("command", "")).strip()
        for candidate in _command_candidates(configured):
            executable = candidate[0]
            if Path(executable).is_file() or shutil.which(executable):
                return candidate
        return None

    def status(self) -> dict[str, Any]:
        command = self._command()
        if not command:
            return {
                "adapter": self.key, "displayName": "Hermes", "installed": False, "configured": False,
                "ready": False, "version": "", "command": "",
                "message": "Hermes is not installed.",
            }
        version = "installed"
        error = ""
        try:
            completed = subprocess.run(
                [*command, "--version"], capture_output=True, text=True, timeout=15, check=False
            )
            version = (completed.stdout or completed.stderr).strip().splitlines()[0] or version
            if completed.returncode != 0:
                error = (completed.stderr or completed.stdout).strip()
        except (OSError, subprocess.TimeoutExpired) as exc:
            error = str(exc)
        hermes_home = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes"))).expanduser()
        configured: bool | None = None
        try:
            dump_command = list(command)
            profile = str(self.settings.get("hermesProfile", "")).strip()
            if not profile:
                profile = str(self.settings.get("profile", "")).strip()
            if profile:
                dump_command.extend(["--profile", profile])
            dump_command.append("dump")
            dump = subprocess.run(
                dump_command, capture_output=True, text=True, timeout=15, check=False
            )
            model_match = re.search(r"(?m)^model:\s*(.+?)\s*$", dump.stdout)
            if dump.returncode == 0 and model_match:
                model_value = model_match.group(1).strip().lower()
                configured = model_value not in {"", "(not set)", "none", "null"}
        except (OSError, subprocess.TimeoutExpired):
            pass
        if configured is None:
            config = hermes_home / "config.yaml"
            secret_file = hermes_home / ".env"
            configured = bool(
                config.is_file() and config.stat().st_size > 0
                and secret_file.is_file() and secret_file.stat().st_size > 0
            )
        ready = not error and configured
        message = (
            "Hermes is installed and appears configured."
            if ready else
            "Hermes is installed. Run 'hermes setup' once to choose an account and model."
        )
        if error:
            message = f"Hermes was found but its version check failed: {error}"
        return {
            "adapter": self.key, "displayName": "Hermes", "installed": True,
            "configured": configured, "ready": ready,
            "version": version, "command": " ".join(shlex.quote(part) for part in command),
            "profile": self.settings.get("hermesProfile") or self.settings.get("profile", ""),
            "provider": self.settings.get("hermesProvider") or self.settings.get("provider", ""),
            "model": self.settings.get("hermesModel") or self.settings.get("model", ""),
            "message": message,
            "setupCommand": f"{shlex.quote(command[0])} setup",
        }

    def run(self, prompt: str) -> AgentRunResult:
        command = self._command()
        if not command:
            raise AgentRunError("Hermes is not installed or its command cannot be found")
        status = self.status()
        if not status["configured"]:
            raise AgentRunError("Hermes needs account and model setup before research can run")
        timeout = max(30, min(int(self.settings.get("timeoutSeconds", 900)), 7200))
        with tempfile.TemporaryDirectory(prefix="resource-research-hermes-") as directory:
            usage_path = Path(directory) / "usage.json"
            arguments = list(command)
            profile = str(self.settings.get("hermesProfile", "")).strip()
            if not profile:
                profile = str(self.settings.get("profile", "")).strip()
            if profile:
                arguments.extend(["--profile", profile])
            arguments.extend(["--toolsets", "web,browser", "--ignore-rules"])
            arguments.extend(["-z", prompt, "--usage-file", str(usage_path)])
            provider = str(self.settings.get("hermesProvider", "")).strip()
            model = str(self.settings.get("hermesModel", "")).strip()
            if not provider:
                provider = str(self.settings.get("provider", "")).strip()
            if not model:
                model = str(self.settings.get("model", "")).strip()
            if provider:
                arguments.extend(["--provider", provider])
            if model:
                arguments.extend(["--model", model])
            try:
                completed = subprocess.run(
                    arguments, capture_output=True, text=True, timeout=timeout, check=False,
                    env={**os.environ, "NO_COLOR": "1"},
                )
            except subprocess.TimeoutExpired as exc:
                output = (exc.stdout or "") + (exc.stderr or "")
                raise AgentRunError(f"Hermes research exceeded the {timeout}-second limit", output) from exc
            except OSError as exc:
                raise AgentRunError(f"Could not start Hermes: {exc}") from exc
            output = completed.stdout.strip()
            if completed.returncode != 0:
                detail = completed.stderr.strip() or output or f"exit code {completed.returncode}"
                raise AgentRunError(f"Hermes research failed: {detail}", output)
            usage = None
            if usage_path.is_file():
                try:
                    usage_value = json.loads(usage_path.read_text(encoding="utf-8"))
                    usage = usage_value if isinstance(usage_value, dict) else None
                except (OSError, json.JSONDecodeError):
                    usage = None
            result = _validate_result(_extract_json_object(output, "Hermes"), "Hermes")
            return AgentRunResult(output=output, result=result, usage=usage)


def _dsh_command_candidates(configured: str = "") -> list[list[str]]:
    candidates: list[list[str]] = []
    override = configured.strip() or os.environ.get("DSH_COMMAND", "").strip()
    if override:
        candidates.append(shlex.split(override))
    local = PROJECT_ROOT / "dsh-runtime" / "node_modules" / ".bin" / "dsh"
    if local.is_file():
        candidates.append([str(local)])
    found = shutil.which("dsh")
    if found:
        candidates.append([found])
    unique: list[list[str]] = []
    for candidate in candidates:
        if candidate and candidate not in unique:
            unique.append(candidate)
    return unique


class DSHCLIAdapter(ResearchAgentAdapter):
    """Experimental DeepSeek Harness adapter using its supported headless profile."""

    key = "dsh"

    def __init__(self, settings: dict[str, Any] | None = None) -> None:
        self.settings = merged_settings(settings)

    def _command(self) -> list[str] | None:
        configured = str(self.settings.get("dshCommand", "")).strip()
        for candidate in _dsh_command_candidates(configured):
            executable = candidate[0]
            if Path(executable).is_file() or shutil.which(executable):
                return candidate
        return None

    def status(self) -> dict[str, Any]:
        command = self._command()
        configured = bool(os.environ.get("DEEPSEEK_API_KEY", "").strip())
        model = str(self.settings.get("dshModel", "")).strip()
        model = model or DSH_DEFAULT_MODEL
        if not command:
            return {
                "adapter": self.key, "displayName": "DeepSeek Harness", "installed": False,
                "configured": configured, "ready": False, "version": "", "command": "",
                "model": model,
                "message": "DeepSeek Harness is not installed. Run ./install-dsh.sh once.",
                "setupCommand": "./install-dsh.sh",
            }
        version = "installed"
        error = ""
        try:
            completed = subprocess.run(
                [*command, "--version"], capture_output=True, text=True, timeout=30, check=False,
                env={**os.environ, "NO_COLOR": "1"},
            )
            version = (completed.stdout or completed.stderr).strip().splitlines()[0] or version
            if completed.returncode != 0:
                error = (completed.stderr or completed.stdout).strip()
        except (OSError, subprocess.TimeoutExpired) as exc:
            error = str(exc)
        ready = not error and configured
        if error:
            message = f"DeepSeek Harness was found but its version check failed: {error}"
        elif not configured:
            message = "DeepSeek Harness is installed. Start this app with DEEPSEEK_API_KEY available."
        else:
            message = "DeepSeek Harness is installed and the API key is available."
        return {
            "adapter": self.key, "displayName": "DeepSeek Harness", "installed": True,
            "configured": configured, "ready": ready, "version": version,
            "command": " ".join(shlex.quote(part) for part in command),
            "model": model, "message": message,
            "setupCommand": "./run-dsh.sh",
            "experimental": True,
        }

    def run(self, prompt: str) -> AgentRunResult:
        command = self._command()
        if not command:
            raise AgentRunError("DeepSeek Harness is not installed or its command cannot be found")
        if not os.environ.get("DEEPSEEK_API_KEY", "").strip():
            raise AgentRunError("DEEPSEEK_API_KEY must be available when the app starts")
        timeout = max(30, min(int(self.settings.get("timeoutSeconds", 900)), 7200))
        model = str(self.settings.get("dshModel", "")).strip()
        model = model or DSH_DEFAULT_MODEL
        if not re.fullmatch(r"[A-Za-z0-9._:/-]+", model):
            raise AgentRunError("The DeepSeek model name contains unsupported characters")
        base_patch = PROJECT_ROOT / "dsh-research.patch.yml"
        if not base_patch.is_file():
            raise AgentRunError(f"DeepSeek research configuration is missing: {base_patch}")
        dsh_home = Path(
            os.environ.get("RESOURCE_RESEARCH_DSH_HOME", str(PROJECT_ROOT / "data" / "dsh-home"))
        ).expanduser().resolve()
        dsh_home.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="resource-research-dsh-") as directory:
            workspace = Path(directory)
            model_patch = workspace / "model.patch.yml"
            model_patch.write_text(
                "- id: agent-default-model\n"
                "  config:\n"
                "    provider: deepseek-official\n"
                f"    model: {json.dumps(model)}\n",
                encoding="utf-8",
            )
            arguments = [
                *command, "--profile", "headless",
                "--patch", str(base_patch), "--patch", str(model_patch), prompt,
            ]
            environment = {
                **os.environ,
                "DSH_HOME": str(dsh_home),
                "DSH_TOOLS_MODE": "native",
                "NO_COLOR": "1",
            }
            try:
                completed = subprocess.run(
                    arguments, capture_output=True, text=True, timeout=timeout, check=False,
                    cwd=workspace, env=environment,
                )
            except subprocess.TimeoutExpired as exc:
                output = (exc.stdout or "") + (exc.stderr or "")
                raise AgentRunError(
                    f"DeepSeek Harness research exceeded the {timeout}-second limit", output
                ) from exc
            except OSError as exc:
                raise AgentRunError(f"Could not start DeepSeek Harness: {exc}") from exc
            output = completed.stdout.strip()
            if completed.returncode != 0:
                detail = completed.stderr.strip() or output or f"exit code {completed.returncode}"
                raise AgentRunError(f"DeepSeek Harness research failed: {detail}", output)
            result = _validate_result(
                _extract_json_object(output, "DeepSeek Harness"), "DeepSeek Harness"
            )
            usage = {
                "adapter": self.key,
                "provider": "deepseek-official",
                "model": model,
                "reportedTokenUsage": False,
            }
            return AgentRunResult(output=output, result=result, usage=usage)


class DemoAgentAdapter(ResearchAgentAdapter):
    """Deterministic adapter used for tests and an explicit local demo mode."""

    key = "demo"

    def status(self) -> dict[str, Any]:
        return {
            "adapter": self.key, "displayName": "Built-in demo", "installed": True,
            "configured": True, "ready": True,
            "version": "built-in", "command": "", "message": "Built-in demo adapter is ready.",
        }

    def run(self, prompt: str) -> AgentRunResult:
        result = {
            "summary": "Demo research completed without contacting an external agent.",
            "candidates": [{
                "name": "Demonstration Housing Program",
                "organization": "Demonstration Organization",
                "website": "https://example.org/housing",
                "geography": "Utah County, Utah",
                "resourceType": "transitional housing",
                "housingNeed": "Short-term housing while a permanent placement is arranged",
                "accessTimeline": "Unknown — verify before referral",
                "description": "A sample candidate used to exercise the review workflow.",
                "eligibility": ["Eligibility not yet verified"],
                "barriers": ["Availability unknown"],
                "availability": {"status": "unknown", "asOf": "", "evidence": ""},
                "petPolicy": "Unknown",
                "evidence": [],
                "unknowns": ["Confirm that the program exists before accepting this demo record"],
                "followUpBranches": [],
            }],
            "lessons": [],
        }
        return AgentRunResult(output=json.dumps(result), result=result, usage={"provider": "demo"})


def build_adapter(settings: dict[str, Any] | None = None) -> ResearchAgentAdapter:
    values = merged_settings(settings)
    if values.get("adapter") == "dsh":
        return DSHCLIAdapter(values)
    if values.get("adapter") == "demo":
        return DemoAgentAdapter()
    return HermesCLIAdapter(values)
