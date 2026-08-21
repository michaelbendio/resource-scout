from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class BenchmarkPreparationError(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _decoded(value: Any) -> Any:
    if value in (None, ""):
        return None
    return json.loads(value)


def _rows(connection: sqlite3.Connection, query: str, parameters: tuple[Any, ...] = ()):
    return [dict(row) for row in connection.execute(query, parameters).fetchall()]


def prepare_mesa_benchmark(
    source_database: Path,
    mesa_package: Path,
    output_directory: Path,
    *,
    created_at: str | None = None,
) -> dict[str, Any]:
    source_database = source_database.expanduser().resolve()
    mesa_package = mesa_package.expanduser().resolve()
    output_directory = output_directory.expanduser().resolve()
    if not source_database.is_file():
        raise BenchmarkPreparationError(f"Source database not found: {source_database}")
    if not mesa_package.is_file():
        raise BenchmarkPreparationError(f"Mesa package not found: {mesa_package}")
    output_directory.mkdir(parents=True, exist_ok=True)
    benchmark_database = output_directory / "mesa-qwen-benchmark.sqlite3"
    manifest_path = output_directory / "mesa-deepseek-baseline.json"
    if benchmark_database.exists() or manifest_path.exists():
        raise BenchmarkPreparationError(
            f"Benchmark output already exists in {output_directory}; choose a new dated directory"
        )

    source = sqlite3.connect(source_database)
    source.row_factory = sqlite3.Row
    try:
        imports = _rows(
            source,
            """SELECT * FROM imports
               WHERE office_name = 'Mesa TSO'
               ORDER BY id""",
        )
        if not imports:
            raise BenchmarkPreparationError("The database contains no Mesa TSO imports")
        package_hash = _sha256(mesa_package)
        import_hashes = {str(row["source_sha256"]) for row in imports}
        if import_hashes != {package_hash}:
            raise BenchmarkPreparationError(
                "The selected Mesa package hash does not match every Mesa import in the database"
            )
        runs = _rows(
            source,
            """SELECT research_runs.*
               FROM research_runs
               JOIN imports ON imports.id = research_runs.source_import_id
               WHERE imports.office_name = 'Mesa TSO'
                 AND research_runs.adapter = 'dsh'
                 AND research_runs.status = 'completed'
               ORDER BY research_runs.id""",
        )
        if len(runs) != 20:
            raise BenchmarkPreparationError(
                f"Expected 20 completed Mesa DSH runs, found {len(runs)}"
            )
        labels = [str(run["target_category_label"]) for run in runs]
        if len(set(labels)) != 20:
            raise BenchmarkPreparationError("The 20 Mesa baseline runs are not unique by category")

        manifest_runs = []
        for run in runs:
            run_id = int(run["id"])
            stages = _rows(
                source,
                "SELECT * FROM research_run_stages WHERE run_id = ? ORDER BY position",
                (run_id,),
            )
            if len(stages) != 4 or any(stage["status"] != "completed" for stage in stages):
                raise BenchmarkPreparationError(
                    f"Mesa run {run_id} does not contain four completed stages"
                )
            discoveries = _rows(
                source,
                "SELECT * FROM discoveries WHERE run_id = ? ORDER BY id",
                (run_id,),
            )
            run_record = dict(run)
            run_record["prompt"] = _decoded(run_record.pop("prompt_json"))
            run_record["result"] = _decoded(run_record.pop("result_json"))
            run_record["usage"] = _decoded(run_record.pop("usage_json"))
            run_record["stages"] = []
            for stage in stages:
                stage_record = dict(stage)
                stage_record["result"] = _decoded(stage_record.pop("result_json"))
                stage_record["usage"] = _decoded(stage_record.pop("usage_json"))
                run_record["stages"].append(stage_record)
            run_record["discoveries"] = []
            for discovery in discoveries:
                discovery_record = dict(discovery)
                discovery_record["candidate"] = _decoded(
                    discovery_record.pop("candidate_json")
                )
                run_record["discoveries"].append(discovery_record)
            manifest_runs.append(run_record)

        destination = sqlite3.connect(benchmark_database)
        try:
            source.backup(destination)
        finally:
            destination.close()
    finally:
        source.close()

    created = created_at or datetime.now(timezone.utc).isoformat()
    manifest = {
        "schemaVersion": 1,
        "createdAt": created,
        "purpose": "Mesa DeepSeek baseline for the Local Qwen comparison",
        "sourceDatabase": {
            "path": str(source_database),
            "sha256": _sha256(source_database),
        },
        "benchmarkDatabase": {
            "path": str(benchmark_database),
            "sha256AtCreation": _sha256(benchmark_database),
        },
        "mesaPackage": {
            "path": str(mesa_package),
            "sha256": package_hash,
        },
        "baseline": {
            "configuration": "DSH with DeepSeek and DeepSeek server-side search",
            "runIds": [int(run["id"]) for run in manifest_runs],
            "stageIds": [
                int(stage["id"]) for run in manifest_runs for stage in run["stages"]
            ],
            "categories": labels,
            "runCount": len(manifest_runs),
            "stageCount": sum(len(run["stages"]) for run in manifest_runs),
            "candidateCount": sum(len(run["discoveries"]) for run in manifest_runs),
            "runs": manifest_runs,
        },
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Freeze the 20-run Mesa DeepSeek baseline")
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--mesa-package", type=Path, required=True)
    parser.add_argument("--output-directory", type=Path, required=True)
    arguments = parser.parse_args(argv)
    try:
        manifest = prepare_mesa_benchmark(
            arguments.database, arguments.mesa_package, arguments.output_directory
        )
    except BenchmarkPreparationError as exc:
        parser.error(str(exc))
    baseline = manifest["baseline"]
    print(
        f"Frozen {baseline['runCount']} Mesa runs, {baseline['stageCount']} stages, "
        f"and {baseline['candidateCount']} candidates."
    )
    print(manifest["benchmarkDatabase"]["path"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
