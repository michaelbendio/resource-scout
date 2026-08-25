#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


SCHEMA_VERSION = 1


class BatchError(RuntimeError):
    pass


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ScoutClient:
    def __init__(self, base_url: str, timeout_seconds: float = 15.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def request(self, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        request = Request(
            f"{self.base_url}{path}",
            data=body,
            method="GET" if body is None else "POST",
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                value = json.load(response)
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace").strip()
            raise BatchError(f"Scout returned HTTP {exc.code} for {path}: {detail}") from exc
        except (URLError, OSError) as exc:
            raise ConnectionError(f"Scout is unavailable at {self.base_url}: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise BatchError(f"Scout returned unreadable JSON for {path}") from exc
        if not isinstance(value, dict):
            raise BatchError(f"Scout returned a non-object response for {path}")
        return value

    def status(self) -> dict[str, Any]:
        return self.request("/api/status")

    def list_runs(self) -> list[dict[str, Any]]:
        value = self.request("/api/research-runs").get("runs", [])
        return value if isinstance(value, list) else []

    def get_run(self, run_id: int) -> dict[str, Any]:
        return self.request(f"/api/research-runs/{run_id}")

    def start_run(self, category_id: str) -> dict[str, Any]:
        return self.request(
            "/api/research-runs",
            {"assignment": "", "researchMode": "package", "categoryId": category_id},
        )

    def resume_run(self, run_id: int) -> dict[str, Any]:
        return self.request(f"/api/research-runs/{run_id}/resume", {})


def validate_status(status: dict[str, Any], *, require_empty_package: bool) -> None:
    try:
        version = tuple(int(part) for part in str(status.get("version") or "").split("."))
    except ValueError:
        version = ()
    if version < (0, 30, 2):
        raise BatchError(
            f"Scout 0.30.2 or later is required; running version is {status.get('version')!r}"
        )
    agent = status.get("agent") if isinstance(status.get("agent"), dict) else {}
    if (
        agent.get("configuration") != "local-qwen"
        or agent.get("metered") is not False
        or agent.get("usesOnlyUnmeteredServices") is not True
    ):
        raise BatchError("Scout is not locked to the unmetered Local Qwen configuration")
    latest = status.get("latestImport")
    if not isinstance(latest, dict):
        raise BatchError("Scout has no connected resource package")
    if require_empty_package and int(latest.get("resourceCount", -1)) != 0:
        raise BatchError(
            f"The connected package contains {latest.get('resourceCount')} resources; expected zero"
        )


def category_plan(
    status: dict[str, Any], *, excluded: set[str], selected: set[str]
) -> list[dict[str, str]]:
    latest = status.get("latestImport") if isinstance(status.get("latestImport"), dict) else {}
    categories = latest.get("categories") if isinstance(latest.get("categories"), list) else []
    plan: list[dict[str, str]] = []
    available: set[str] = set()
    for category in categories:
        if not isinstance(category, dict) or category.get("active") is False:
            continue
        category_id = str(category.get("id") or "").strip()
        if not category_id:
            continue
        available.add(category_id)
        if category_id in excluded or (selected and category_id not in selected):
            continue
        plan.append({"id": category_id, "label": str(category.get("label") or category_id)})
    unknown = (excluded | selected) - available
    if unknown:
        raise BatchError(f"Unknown package category IDs: {', '.join(sorted(unknown))}")
    if not plan:
        raise BatchError("The selected category plan is empty")
    return plan


def write_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def initial_state(status: dict[str, Any], plan: list[dict[str, str]]) -> dict[str, Any]:
    latest = status["latestImport"]
    return {
        "schemaVersion": SCHEMA_VERSION,
        "createdAt": now(),
        "updatedAt": now(),
        "status": "running",
        "scoutVersion": status["version"],
        "packageImportId": latest["id"],
        "packageSha256": latest["sourceSha256"],
        "categories": [
            {
                **category,
                "status": "pending",
                "runId": None,
                "resumeCount": 0,
                "lastError": "",
            }
            for category in plan
        ],
    }


def load_state(
    path: Path, status: dict[str, Any], plan: list[dict[str, str]], *, existing_runs: int
) -> dict[str, Any]:
    if not path.exists():
        if existing_runs:
            raise BatchError(
                f"Scout already has {existing_runs} research run(s). Reset Recent runs or use the existing batch state."
            )
        return initial_state(status, plan)
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BatchError(f"Could not read batch state {path}: {exc}") from exc
    if not isinstance(state, dict) or state.get("schemaVersion") != SCHEMA_VERSION:
        raise BatchError("The batch state uses an unsupported schema")
    latest = status["latestImport"]
    if (
        state.get("packageImportId") != latest.get("id")
        or state.get("packageSha256") != latest.get("sourceSha256")
    ):
        raise BatchError("The connected package changed after this batch was created")
    expected = [category["id"] for category in plan]
    actual = [category.get("id") for category in state.get("categories", [])]
    if actual != expected:
        raise BatchError("The requested category plan differs from the saved batch state")
    return state


class BatchRunner:
    def __init__(
        self,
        client: ScoutClient,
        state_path: Path,
        state: dict[str, Any],
        *,
        poll_seconds: float,
        max_resumes: int,
        output: Callable[[str], None] = print,
    ) -> None:
        self.client = client
        self.state_path = state_path
        self.state = state
        self.poll_seconds = poll_seconds
        self.max_resumes = max_resumes
        self.output = output

    def save(self) -> None:
        self.state["updatedAt"] = now()
        write_state(self.state_path, self.state)

    def run(self) -> None:
        self.save()
        total = len(self.state["categories"])
        for index, category in enumerate(self.state["categories"], start=1):
            if category["status"] == "completed":
                continue
            self._run_category(index, total, category)
        self.state["status"] = "completed"
        self.state["completedAt"] = now()
        self.save()
        self.output(f"Batch complete: all {total} categories finished.")

    def _run_category(self, index: int, total: int, category: dict[str, Any]) -> None:
        prefix = f"[{index}/{total}] {category['label']}"
        if category.get("runId") is None:
            matching = [
                run
                for run in self.client.list_runs()
                if run.get("targetCategoryId") == category["id"]
            ]
            if len(matching) > 1:
                raise BatchError(f"{prefix} has multiple untracked Scout runs")
            if matching:
                run = matching[0]
                self.output(f"{prefix}: adopted existing run {run['id']} after interruption.")
            else:
                self._wait_until_ready()
                run = self.client.start_run(category["id"])
            category["runId"] = int(run["id"])
            category["status"] = str(run.get("status") or "queued")
            self.save()
            self.output(f"{prefix}: started as run {category['runId']}.")
        last_progress = None
        while True:
            try:
                run = self.client.get_run(int(category["runId"]))
            except ConnectionError as exc:
                self.output(f"{prefix}: {exc}; waiting for Scout to return.")
                time.sleep(self.poll_seconds)
                continue
            run_status = str(run.get("status") or "")
            progress = run.get("progress") if isinstance(run.get("progress"), dict) else {}
            progress_key = (
                run_status,
                int(progress.get("completed", 0)),
                int(progress.get("total", 0)),
                str(run.get("error") or ""),
            )
            if progress_key != last_progress:
                self.output(
                    f"{prefix}: {run_status}; stages {progress_key[1]}/{progress_key[2]}."
                )
                last_progress = progress_key
            category["status"] = run_status
            category["lastError"] = str(run.get("error") or "")
            self.save()
            if run_status == "completed":
                category["completedAt"] = run.get("completedAt") or now()
                self.save()
                return
            if run_status in {"failed", "partial"}:
                if int(category.get("resumeCount", 0)) >= self.max_resumes:
                    self.state["status"] = "attention-required"
                    self.save()
                    raise BatchError(
                        f"{prefix} needs attention after {self.max_resumes} automatic resumes: "
                        f"{category['lastError']}"
                    )
                self._wait_until_ready()
                self.client.resume_run(int(category["runId"]))
                category["resumeCount"] = int(category.get("resumeCount", 0)) + 1
                category["status"] = "queued"
                self.save()
                self.output(
                    f"{prefix}: resumed run {category['runId']} "
                    f"({category['resumeCount']}/{self.max_resumes})."
                )
            time.sleep(self.poll_seconds)

    def _wait_until_ready(self) -> None:
        while True:
            try:
                status = self.client.status()
                validate_status(status, require_empty_package=False)
                agent = status.get("agent", {})
                if agent.get("ready") is True:
                    return
                self.output(f"Local Qwen is not ready yet: {agent.get('message', '')}")
            except ConnectionError as exc:
                self.output(f"{exc}; waiting for Scout to return.")
            time.sleep(self.poll_seconds)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Run Resource Scout categories sequentially through unmetered Local Qwen"
    )
    result.add_argument("--base-url", default="http://127.0.0.1:8765")
    result.add_argument("--exclude", action="append", default=[], metavar="CATEGORY_ID")
    result.add_argument(
        "--include-miscellaneous",
        action="store_true",
        help="include Miscellaneous, which is skipped by default",
    )
    result.add_argument("--category", action="append", default=[], metavar="CATEGORY_ID")
    result.add_argument("--state", type=Path, default=Path("data/scout-category-batch.json"))
    result.add_argument("--poll-seconds", type=float, default=30.0)
    result.add_argument("--max-resumes", type=int, default=3)
    result.add_argument("--require-empty-package", action="store_true")
    result.add_argument("--dry-run", action="store_true")
    return result


def main(argv: list[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    if arguments.poll_seconds < 1:
        raise SystemExit("--poll-seconds must be at least 1")
    if arguments.max_resumes < 0:
        raise SystemExit("--max-resumes cannot be negative")
    client = ScoutClient(arguments.base_url)
    try:
        status = client.status()
        validate_status(status, require_empty_package=arguments.require_empty_package)
        excluded = set(arguments.exclude)
        if not arguments.include_miscellaneous:
            excluded.add("miscellaneous")
        plan = category_plan(
            status,
            excluded=excluded,
            selected=set(arguments.category),
        )
        print(f"Connected package: {status['latestImport']['sourceName']}")
        print(f"Planned categories ({len(plan)}): {', '.join(item['label'] for item in plan)}")
        if arguments.dry_run:
            return 0
        state = load_state(
            arguments.state,
            status,
            plan,
            existing_runs=len(client.list_runs()),
        )
        BatchRunner(
            client,
            arguments.state,
            state,
            poll_seconds=arguments.poll_seconds,
            max_resumes=arguments.max_resumes,
        ).run()
    except (BatchError, ConnectionError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nBatch stopped. Run the same command to continue from the saved state.")
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
