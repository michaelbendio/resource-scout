#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from resource_research_agent.local_qwen import completion_health
from resource_research_agent.optimization_comparison import (
    create_model_neutral_comparison,
    reveal_timing_and_decide,
)
from resource_research_agent.optimization_runtime import PINNED_MODELS
from resource_research_agent.storage import ResearchStore


def unmetered_environment() -> dict[str, str]:
    environment = dict(os.environ)
    environment.pop("DEEPSEEK_API_KEY", None)
    return environment


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


parser = argparse.ArgumentParser(description="Run the fair local Qwen quantization comparison")
parser.add_argument("--database", type=Path, required=True)
parser.add_argument("--corpus-id", type=int, required=True)
parser.add_argument("--artifacts", type=Path, required=True)
arguments = parser.parse_args()

arguments.artifacts.mkdir(parents=True, exist_ok=True)
status_path = arguments.artifacts / "comparison-status.json"
environment = unmetered_environment()


def status(**values) -> None:
    write_json(
        status_path,
        {
            "updatedAt": datetime.now(timezone.utc).isoformat(),
            "deepSeekKeyPresent": "DEEPSEEK_API_KEY" in environment,
            **values,
        },
    )


def run_quantization(quantization: str) -> None:
    server_log_path = arguments.artifacts / f"{quantization}-server.log"
    runner_log_path = arguments.artifacts / f"{quantization}-evaluation.log"
    status(phase="starting-model", quantization=quantization)
    with server_log_path.open("a", encoding="utf-8") as server_log:
        server = subprocess.Popen(
            ["./local-qwen.sh", "serve", "--quantization", quantization],
            stdout=server_log,
            stderr=subprocess.STDOUT,
            env=environment,
            start_new_session=True,
        )
        try:
            deadline = time.monotonic() + 600
            while True:
                if server.poll() is not None:
                    raise RuntimeError(f"{quantization} model server exited during startup")
                try:
                    health = completion_health(timeout=300, model=PINNED_MODELS[quantization])
                    break
                except Exception:
                    if time.monotonic() >= deadline:
                        raise
                    time.sleep(2)
            status(
                phase="model-evaluation",
                quantization=quantization,
                model=health["model"],
                serverPid=health["serverPid"],
            )
            with runner_log_path.open("a", encoding="utf-8") as runner_log:
                completed = subprocess.run(
                    [
                        sys.executable,
                        "run-qwen-housing-model.py",
                        "--database",
                        str(arguments.database),
                        "--corpus-id",
                        str(arguments.corpus_id),
                        "--quantization",
                        quantization,
                    ],
                    stdout=runner_log,
                    stderr=subprocess.STDOUT,
                    env=environment,
                    check=False,
                )
            if completed.returncode != 0:
                raise RuntimeError(
                    f"{quantization} evaluation failed; resume by rerunning this command"
                )
        finally:
            server.terminate()
            try:
                server.wait(timeout=30)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait()


try:
    for quantization in ("4-bit", "8-bit"):
        run_quantization(quantization)
    store = ResearchStore(arguments.database)
    with store.connect() as connection:
        corpus = connection.execute(
            "SELECT corpus_sha256 FROM optimization_corpora WHERE id = ?",
            (arguments.corpus_id,),
        ).fetchone()
        if not corpus:
            raise RuntimeError("Frozen corpus disappeared before comparison")
        suffix = str(corpus["corpus_sha256"])[:12]
        run_ids = {}
        for quantization in ("4-bit", "8-bit"):
            label = f"mesa-housing-urgent-{quantization}-reviewed-corpus-v5-{suffix}"
            row = connection.execute(
                "SELECT id FROM optimization_runs WHERE label = ? AND status = 'completed'",
                (label,),
            ).fetchone()
            if not row:
                raise RuntimeError(f"Completed {quantization} run was not found")
            run_ids[quantization] = int(row["id"])
    status(phase="quality-comparison", quantization=None)
    comparison = create_model_neutral_comparison(
        store,
        label=f"mesa-housing-urgent-quantization-v5-{suffix}",
        four_bit_run_id=run_ids["4-bit"],
        eight_bit_run_id=run_ids["8-bit"],
    )
    write_json(arguments.artifacts / "model-neutral-quality-report.json", comparison.report)
    revealed = reveal_timing_and_decide(store, comparison.comparison_id)
    write_json(arguments.artifacts / "quantization-decision.json", revealed)
    status(phase="completed", comparisonId=comparison.comparison_id, decision=revealed["decision"])
except BaseException as error:
    status(phase="failed", error=str(error))
    raise
