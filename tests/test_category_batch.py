from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from run_scout_category_batch import (
    BatchError,
    BatchRunner,
    category_plan,
    initial_state,
    load_state,
    validate_status,
)


def status(*, resources: int = 0) -> dict:
    return {
        "version": "0.30.2",
        "agent": {
            "ready": True,
            "configuration": "local-qwen",
            "metered": False,
            "usesOnlyUnmeteredServices": True,
        },
        "latestImport": {
            "id": 7,
            "sourceName": "mesa-resource-package.zip",
            "sourceSha256": "package-hash",
            "resourceCount": resources,
            "categories": [
                {"id": "food", "label": "Food", "active": True},
                {"id": "housing", "label": "Housing", "active": True},
                {"id": "miscellaneous", "label": "Miscellaneous", "active": True},
            ],
        },
    }


class FakeClient:
    def __init__(self, states: dict[int, list[str]] | None = None) -> None:
        self.states = states or {}
        self.started: list[str] = []
        self.resumed: list[int] = []
        self.next_id = 1

    def list_runs(self) -> list[dict]:
        return []

    def status(self) -> dict:
        return status()

    def start_run(self, category_id: str) -> dict:
        run_id = self.next_id
        self.next_id += 1
        self.started.append(category_id)
        self.states.setdefault(run_id, ["completed"])
        return {"id": run_id, "status": "queued"}

    def get_run(self, run_id: int) -> dict:
        values = self.states[run_id]
        run_status = values.pop(0) if len(values) > 1 else values[0]
        return {
            "id": run_id,
            "status": run_status,
            "progress": {"completed": 4 if run_status == "completed" else 0, "total": 4},
            "error": "interrupted" if run_status == "failed" else "",
        }

    def resume_run(self, run_id: int) -> dict:
        self.resumed.append(run_id)
        return {"id": run_id, "status": "queued"}


class CategoryBatchTests(unittest.TestCase):
    def test_plan_skips_only_the_explicit_category_and_preserves_order(self) -> None:
        plan = category_plan(status(), excluded={"miscellaneous"}, selected=set())

        self.assertEqual(["food", "housing"], [item["id"] for item in plan])
        with self.assertRaisesRegex(BatchError, "Unknown package category"):
            category_plan(status(), excluded={"not-real"}, selected=set())

    def test_status_fails_closed_for_metered_or_nonempty_scout(self) -> None:
        validate_status(status(), require_empty_package=True)
        unsafe = status()
        unsafe["agent"]["metered"] = True
        with self.assertRaisesRegex(BatchError, "not locked"):
            validate_status(unsafe, require_empty_package=True)
        with self.assertRaisesRegex(BatchError, "expected zero"):
            validate_status(status(resources=1), require_empty_package=True)

    def test_new_state_requires_a_clean_scout_and_is_bound_to_package(self) -> None:
        plan = category_plan(status(), excluded={"miscellaneous"}, selected=set())
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            with self.assertRaisesRegex(BatchError, "already has 1 research run"):
                load_state(path, status(), plan, existing_runs=1)
            state = load_state(path, status(), plan, existing_runs=0)
            self.assertEqual(7, state["packageImportId"])

    def test_runner_starts_categories_sequentially_and_persists_completion(self) -> None:
        plan = category_plan(status(), excluded={"miscellaneous"}, selected=set())
        state = initial_state(status(), plan)
        client = FakeClient()
        messages: list[str] = []
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            BatchRunner(
                client,
                path,
                state,
                poll_seconds=0,
                max_resumes=3,
                output=messages.append,
            ).run()

        self.assertEqual(["food", "housing"], client.started)
        self.assertEqual("completed", state["status"])
        self.assertTrue(all(item["status"] == "completed" for item in state["categories"]))
        self.assertIn("Batch complete", messages[-1])

    def test_runner_resumes_an_interrupted_run_without_starting_another(self) -> None:
        plan = [{"id": "food", "label": "Food"}]
        state = initial_state(status(), plan)
        state["categories"][0].update({"runId": 9, "status": "failed"})
        client = FakeClient({9: ["failed", "completed"]})
        with tempfile.TemporaryDirectory() as directory:
            BatchRunner(
                client,
                Path(directory) / "state.json",
                state,
                poll_seconds=0,
                max_resumes=3,
                output=lambda _message: None,
            ).run()

        self.assertEqual([], client.started)
        self.assertEqual([9], client.resumed)
        self.assertEqual(1, state["categories"][0]["resumeCount"])


if __name__ == "__main__":
    unittest.main()
