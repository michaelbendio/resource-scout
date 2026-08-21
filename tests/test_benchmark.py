from __future__ import annotations

import hashlib
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from resource_research_agent.benchmark import BenchmarkPreparationError, prepare_mesa_benchmark


class MesaBenchmarkPreparationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.database = self.root / "source.sqlite3"
        self.package = self.root / "mesa-resource-package.zip"
        self.package.write_bytes(b"mesa package")
        package_hash = hashlib.sha256(self.package.read_bytes()).hexdigest()
        connection = sqlite3.connect(self.database)
        connection.executescript(
            """
            CREATE TABLE imports (
                id INTEGER PRIMARY KEY, source_name TEXT, source_sha256 TEXT,
                imported_at TEXT, json_member TEXT, resource_path TEXT, category_path TEXT,
                schema_version TEXT, package_version TEXT, target_category_id TEXT,
                target_category_label TEXT, resource_count INTEGER,
                target_resource_count INTEGER, multicategory_target_count INTEGER,
                metadata_json TEXT, manifest_json TEXT, for_groups_json TEXT,
                office_name TEXT, service_area TEXT, identity_source TEXT
            );
            CREATE TABLE research_runs (
                id INTEGER PRIMARY KEY, created_at TEXT, started_at TEXT, completed_at TEXT,
                status TEXT, adapter TEXT, assignment TEXT, seed_import_id INTEGER,
                seed_resource_id TEXT, prompt_json TEXT, output_text TEXT, result_json TEXT,
                usage_json TEXT, error TEXT, source_import_id INTEGER, research_mode TEXT,
                target_location TEXT, regional_scope TEXT, target_category_id TEXT,
                target_category_label TEXT
            );
            CREATE TABLE research_run_stages (
                id INTEGER PRIMARY KEY, run_id INTEGER, stage_key TEXT, title TEXT,
                instruction TEXT, position INTEGER, status TEXT, created_at TEXT,
                started_at TEXT, completed_at TEXT, output_text TEXT, result_json TEXT,
                usage_json TEXT, error TEXT
            );
            CREATE TABLE discoveries (
                id INTEGER PRIMARY KEY, created_at TEXT, updated_at TEXT, status TEXT,
                origin TEXT, name TEXT, candidate_json TEXT, matched_import_id INTEGER,
                matched_resource_id TEXT, duplicate_score REAL, notes TEXT, run_id INTEGER,
                reviewed_at TEXT, review_feedback TEXT, match_assessment TEXT,
                match_assessed_at TEXT, stage_id INTEGER
            );
            """
        )
        connection.execute(
            "INSERT INTO imports VALUES (1, ?, ?, '', '', '', NULL, '', '', '', '', 0, 0, 0, '{}', '{}', '[]', 'Mesa TSO', 'Mesa', '')",
            (self.package.name, package_hash),
        )
        stage_id = 1
        discovery_id = 1
        for run_id in range(1, 21):
            connection.execute(
                "INSERT INTO research_runs VALUES (?, '', '', '', 'completed', 'dsh', 'assignment', NULL, NULL, ?, '', ?, ?, '', 1, 'package', NULL, '', ?, ?)",
                (
                    run_id,
                    json.dumps({"run": run_id}),
                    json.dumps({"summary": "done"}),
                    json.dumps({"provider": "deepseek"}),
                    f"category-{run_id}",
                    f"Category {run_id}",
                ),
            )
            for position in range(4):
                connection.execute(
                    "INSERT INTO research_run_stages VALUES (?, ?, ?, ?, ?, ?, 'completed', '', '', '', '', ?, ?, '')",
                    (
                        stage_id,
                        run_id,
                        f"stage-{position}",
                        f"Stage {position}",
                        "instruction",
                        position,
                        json.dumps({"candidates": []}),
                        json.dumps({"provider": "deepseek"}),
                    ),
                )
                stage_id += 1
            connection.execute(
                "INSERT INTO discoveries VALUES (?, '', '', 'pending', 'agent', 'Candidate', ?, NULL, NULL, NULL, '', ?, NULL, '', NULL, NULL, NULL)",
                (discovery_id, json.dumps({"name": f"Candidate {run_id}"}), run_id),
            )
            discovery_id += 1
        connection.commit()
        connection.close()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_freezes_copy_and_machine_readable_manifest(self) -> None:
        output = self.root / "benchmark"
        manifest = prepare_mesa_benchmark(
            self.database, self.package, output, created_at="2026-08-21T00:00:00+00:00"
        )

        self.assertEqual(20, manifest["baseline"]["runCount"])
        self.assertEqual(80, manifest["baseline"]["stageCount"])
        self.assertEqual(20, manifest["baseline"]["candidateCount"])
        self.assertEqual(list(range(1, 21)), manifest["baseline"]["runIds"])
        self.assertEqual({"run": 1}, manifest["baseline"]["runs"][0]["prompt"])
        self.assertTrue((output / "mesa-qwen-benchmark.sqlite3").is_file())
        loaded = json.loads((output / "mesa-deepseek-baseline.json").read_text())
        self.assertEqual(80, len(loaded["baseline"]["stageIds"]))

    def test_refuses_wrong_package_and_existing_output(self) -> None:
        wrong = self.root / "wrong.zip"
        wrong.write_bytes(b"wrong")
        with self.assertRaisesRegex(BenchmarkPreparationError, "hash"):
            prepare_mesa_benchmark(self.database, wrong, self.root / "wrong-output")

        output = self.root / "existing"
        prepare_mesa_benchmark(self.database, self.package, output)
        with self.assertRaisesRegex(BenchmarkPreparationError, "already exists"):
            prepare_mesa_benchmark(self.database, self.package, output)


if __name__ == "__main__":
    unittest.main()
