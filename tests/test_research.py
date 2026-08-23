from __future__ import annotations

import json
import os
import tempfile
import time
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from resource_research_agent.agents import (
    AgentRunError,
    AgentRunResult,
    DSHCLIAdapter,
    HermesCLIAdapter,
    ResearchAgentAdapter,
    _extract_json_object,
    build_adapter,
)
from resource_research_agent.importer import ResourcePackageImporter
from resource_research_agent.research import ResearchCoordinator
from resource_research_agent.storage import ResearchStore


class ResearchWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.store = ResearchStore(self.root / "research.sqlite3")
        package_path = self.root / "resources.zip"
        package = {
            "schemaVersion": 3,
            "categories": [
                {"id": "housing", "name": "Housing"},
                {"id": "food", "name": "Food", "filters": ["Meals", "Pantries"]},
                {"id": "employment", "name": "Employment", "filters": ["Temp Agencies"]},
                {"id": "legal", "name": "Legal"},
            ],
            "forGroups": ["Families with children", "Veterans"],
            "resources": [{
                "id": "known-home", "name": "Known Home", "categories": ["housing"],
                "website": "https://known.example.org", "address": "1 Main St, Provo, UT",
            }, {"id": "known-pantry", "name": "Known Pantry", "categories": ["food"]}],
        }
        with zipfile.ZipFile(package_path, "w") as archive:
            archive.writestr("tso-resources.json", json.dumps(package))
        self.store.save_import(ResourcePackageImporter().read(package_path))

    def tearDown(self) -> None:
        self.directory.cleanup()

    def test_json_extraction_repairs_only_a_missing_top_level_closing_brace(self) -> None:
        repaired = _extract_json_object(
            '{"candidates":[{"name":"Mesa Housing"}],"lessons":[]'
        )
        self.assertEqual("Mesa Housing", repaired["candidates"][0]["name"])

        malformed_values = (
            '{"candidates":[{"name":"Mesa Housing"}],"lessons":',
            '{"candidates":[{"name":"Mesa Housing}],"lessons":[]',
            '{"candidates":[],"lessons":[],}',
        )
        for malformed in malformed_values:
            with self.subTest(malformed=malformed):
                with self.assertRaises(AgentRunError):
                    _extract_json_object(malformed)

    def test_demo_research_run_creates_separate_candidate_and_review_lesson(self) -> None:
        self.store.save_settings({"adapter": "demo"})
        coordinator = ResearchCoordinator(self.store)
        run = coordinator.start("Find a transitional housing option", "known-home")
        for _ in range(200):
            current = self.store.get_run(run["id"])
            if current and current["status"] in {"completed", "failed"}:
                break
            time.sleep(0.01)
        self.assertEqual("completed", current["status"])
        discoveries = self.store.list_discoveries()
        self.assertEqual(1, len(discoveries))
        self.assertEqual("candidate", discoveries[0]["status"])
        self.assertEqual(run["id"], discoveries[0]["runId"])
        reviewed = self.store.review_discovery(discoveries[0]["id"], "research-further", "Verify pet policy")
        self.assertEqual("research-further", reviewed["status"])
        lesson = self.store.save_lesson(
            "Verify pet policy", source="human-feedback", discovery_id=discoveries[0]["id"]
        )
        self.assertEqual("active", lesson["status"])
        self.assertEqual(1, len(self.store.list_lessons(active_only=True)))
        self.assertIsNotNone(self.store.full_resource(1, "known-home"))

    def test_standalone_location_is_explicit_and_isolated_from_imported_context(self) -> None:
        class CapturingAdapter(ResearchAgentAdapter):
            key = "capture"

            def __init__(self) -> None:
                self.prompt = ""

            def status(self) -> dict[str, object]:
                return {"adapter": self.key, "ready": True}

            def run(self, prompt: str) -> AgentRunResult:
                self.prompt = prompt
                return AgentRunResult(
                    output="captured",
                    result={
                        "summary": "Mesa research complete",
                        "candidates": [{"name": "Known Home", "geography": "Mesa, Arizona"}],
                        "lessons": [{"scope": "category", "text": "Confirm Mesa service boundaries"}],
                    },
                )

        self.store.save_lesson("Package-only lesson", research_mode="package")
        self.store.save_lesson(
            "Mesa lesson", research_mode="standalone-location", target_location="Mesa, Arizona"
        )
        self.store.save_lesson(
            "Tempe lesson", research_mode="standalone-location", target_location="Tempe, Arizona"
        )
        adapter = CapturingAdapter()
        coordinator = ResearchCoordinator(self.store, adapter_factory=lambda settings: adapter)
        run = coordinator.start(
            "",
            research_mode="standalone-location",
            target_location="Mesa, Arizona",
            regional_scope="Maricopa County",
        )
        for _ in range(200):
            current = self.store.get_run(run["id"])
            if current and current["status"] in {"completed", "failed"}:
                break
            time.sleep(0.01)

        self.assertEqual("completed", current["status"])
        self.assertEqual("standalone-location", current["researchMode"])
        self.assertEqual("Mesa, Arizona", current["targetLocation"])
        self.assertEqual("Maricopa County", current["regionalScope"])
        self.assertIsNone(current["sourceImportId"])
        prompt = current["prompt"]
        self.assertEqual([], prompt["knownResources"])
        self.assertIsNone(prompt["researchContext"]["sourcePackage"])
        self.assertIn("Mesa, Arizona first", prompt["categoryBrief"]["geographicFocus"])
        self.assertEqual(["Mesa lesson"], [lesson["text"] for lesson in prompt["activeLessons"]])
        self.assertIn("without adequate housing in Mesa, Arizona", current["assignment"])
        discovery = self.store.list_discoveries(run_id=run["id"])[0]
        self.assertEqual("candidate", discovery["status"])
        self.assertIsNone(discovery["match"])
        run_lesson = next(lesson for lesson in self.store.list_lessons() if lesson["runId"] == run["id"])
        self.assertEqual("standalone-location", run_lesson["researchMode"])
        self.assertEqual("Mesa, Arizona", run_lesson["targetLocation"])

        with self.assertRaisesRegex(ValueError, "cannot branch"):
            coordinator.start(
                "Research Mesa",
                "known-home",
                research_mode="standalone-location",
                target_location="Mesa, Arizona",
            )

    def test_package_research_remains_the_default(self) -> None:
        self.store.save_settings({"adapter": "demo"})
        run = ResearchCoordinator(self.store).start("Find Housing broadly")
        self.assertEqual("package", run["researchMode"])
        self.assertEqual(1, run["sourceImportId"])
        self.assertIsNone(run["targetLocation"])
        self.assertEqual([{"id": "known-home", "name": "Known Home"}], run["prompt"]["knownResources"])
        for _ in range(200):
            if self.store.get_run(run["id"])["status"] in {"completed", "failed"}:
                break
            time.sleep(0.01)

    def test_food_run_uses_package_taxonomy_food_seeds_and_food_stages(self) -> None:
        class CapturingAdapter(ResearchAgentAdapter):
            key = "capture-food"

            def status(self) -> dict[str, object]:
                return {"adapter": self.key, "ready": True}

            def run(self, prompt: str) -> AgentRunResult:
                return AgentRunResult(output="done", result={"summary": "done", "candidates": [], "lessons": []})

        coordinator = ResearchCoordinator(self.store, adapter_factory=lambda settings: CapturingAdapter())
        run = coordinator.start("", target_category_id="food")
        current = self.store.get_run(run["id"])
        self.assertEqual("food", current["targetCategoryId"])
        self.assertEqual("Food", current["targetCategoryLabel"])
        self.assertEqual([{"id": "known-pantry", "name": "Known Pantry"}], current["prompt"]["knownResources"])
        self.assertEqual(["Meals", "Pantries"], current["prompt"]["categoryBrief"]["availableTypes"])
        self.assertEqual(["Families with children", "Veterans"], current["prompt"]["categoryBrief"]["availableForGroups"])
        self.assertEqual("immediate-food", current["stages"][0]["key"])
        self.assertIn("food insecurity", current["assignment"])
        legal_run = coordinator.start("", target_category_id="legal")
        legal = self.store.get_run(legal_run["id"])
        self.assertEqual("legal", legal["targetCategoryId"])
        self.assertEqual("Legal", legal["targetCategoryLabel"])
        self.assertEqual("legal-urgent", legal["stages"][0]["key"])
        self.assertIn("civil legal help", legal["assignment"])
        self.assertEqual("1.2.0", legal["prompt"]["categoryBrief"]["playbookVersion"])
        self.assertEqual("legal.json", legal["prompt"]["categoryBrief"]["playbookSource"])
        self.assertTrue(legal["prompt"]["categoryBrief"]["exclude"])
        self.assertTrue(legal["prompt"]["categoryBrief"]["verificationQuestions"])
        requirements = legal["prompt"]["resourceGatheringRequirements"]
        self.assertEqual("identity-and-contact", requirements[0]["key"])
        self.assertIn("whatToExpect", requirements[3]["outputFields"])
        self.assertIn("every resourceGatheringRequirement", " ".join(legal["prompt"]["rules"]))
        candidate_schema = legal["prompt"]["outputSchema"]["candidates"][0]
        self.assertIn("servicesProvided", candidate_schema)
        self.assertIn("howToBestConnect", candidate_schema)
        self.assertIn("keyFindings", legal["prompt"]["outputSchema"]["summarySections"])
        for _ in range(200):
            legal = self.store.get_run(legal_run["id"])
            if legal and legal["status"] in {"completed", "failed"}:
                break
            time.sleep(0.01)
        self.assertEqual("completed", legal["status"])

    def test_mesa_package_localizes_assignment_prompt_and_run_identity(self) -> None:
        mesa_path = self.root / "mesa-resource-package.zip"
        with zipfile.ZipFile(mesa_path, "w") as archive:
            archive.writestr("tso-resources.json", json.dumps({
                "schemaVersion": 3,
                "categories": [{"id": "food", "name": "Food", "filters": ["Meals"]}],
                "resources": [],
            }))
        import_id = self.store.save_import(ResourcePackageImporter("food").read(mesa_path))

        class CapturingAdapter(ResearchAgentAdapter):
            key = "capture-mesa"

            def status(self) -> dict[str, object]:
                return {"adapter": self.key, "ready": True}

            def run(self, prompt: str) -> AgentRunResult:
                return AgentRunResult(
                    output="done",
                    result={"summary": "done", "candidates": [], "lessons": []},
                )

        coordinator = ResearchCoordinator(
            self.store, adapter_factory=lambda settings: CapturingAdapter()
        )
        run = coordinator.start(
            "Discover realistic ways a person facing food insecurity in Utah County can obtain meals and groceries.",
            target_category_id="food",
        )
        current = self.store.get_run(run["id"])
        self.assertEqual(import_id, current["sourceImportId"])
        self.assertEqual("Mesa TSO", current["sourceOfficeName"])
        self.assertEqual(
            "Mesa and Maricopa County, Arizona", current["sourceServiceArea"]
        )
        self.assertIn("Mesa and Maricopa County, Arizona", current["assignment"])
        self.assertNotIn("Utah County", current["assignment"])
        self.assertIn(
            "Mesa and Maricopa County, Arizona first",
            current["prompt"]["categoryBrief"]["geographicFocus"],
        )
        history = next(item for item in self.store.list_runs() if item["id"] == run["id"])
        self.assertEqual("Mesa TSO", history["sourceOfficeName"])
        for _ in range(200):
            current = self.store.get_run(run["id"])
            if current and current["status"] in {"completed", "failed", "partial"}:
                break
            time.sleep(0.01)
        self.assertEqual("completed", current["status"])

    def test_staged_run_keeps_partial_candidates_and_resumes_without_repeating_work(self) -> None:
        class FlakyStagedAdapter(ResearchAgentAdapter):
            key = "staged-test"

            def __init__(self) -> None:
                self.calls: dict[str, int] = {}
                self.failed_once = False

            def status(self) -> dict[str, object]:
                return {"adapter": self.key, "ready": True}

            def run(self, prompt: str) -> AgentRunResult:
                payload = json.loads(prompt.split("\n\n", 1)[1])
                key = payload["researchStage"]["key"]
                self.calls[key] = self.calls.get(key, 0) + 1
                if key == "stabilization" and not self.failed_once:
                    self.failed_once = True
                    raise AgentRunError("Hermes research exceeded the 900-second limit", "partial output")
                return AgentRunResult(
                    output=f"output for {key}",
                    result={
                        "summary": f"summary for {key}",
                        "summarySections": {
                            "overview": f"Overview for {key}",
                            "keyFindings": [f"Finding for {key}"],
                            "cautions": [],
                            "accessSteps": [f"Call about {key}"],
                            "gaps": [],
                        },
                        "candidates": [{"name": f"{key} candidate", "geography": "Mesa, Arizona"}],
                        "lessons": [],
                    },
                    usage={"stage": key},
                )

        adapter = FlakyStagedAdapter()
        coordinator = ResearchCoordinator(self.store, adapter_factory=lambda settings: adapter)
        run = coordinator.start(
            "Research Mesa Housing",
            research_mode="standalone-location",
            target_location="Mesa, Arizona",
        )
        for _ in range(300):
            partial = self.store.get_run(run["id"])
            if partial and partial["status"] in {"partial", "failed", "completed"}:
                break
            time.sleep(0.01)

        self.assertEqual("partial", partial["status"])
        self.assertEqual({"total": 4, "completed": 1, "failed": 1}, partial["progress"])
        self.assertEqual(
            ["completed", "failed", "queued", "queued"],
            [stage["status"] for stage in partial["stages"]],
        )
        first_candidates = self.store.list_discoveries(run_id=run["id"])
        self.assertEqual(["urgent-access candidate"], [item["name"] for item in first_candidates])
        self.assertTrue(partial["result"]["isPartial"])
        self.assertIn("Completed 1 of 4", partial["result"]["summary"])

        coordinator.resume(run["id"])
        for _ in range(500):
            completed = self.store.get_run(run["id"])
            if completed and completed["status"] == "completed":
                break
            time.sleep(0.01)

        self.assertEqual("completed", completed["status"])
        self.assertEqual({"total": 4, "completed": 4, "failed": 0}, completed["progress"])
        self.assertEqual(1, adapter.calls["urgent-access"])
        self.assertEqual(2, adapter.calls["stabilization"])
        self.assertEqual(1, adapter.calls["specialized-housing"])
        self.assertEqual(1, adapter.calls["long-term-and-gaps"])
        self.assertEqual(4, len(self.store.list_discoveries(run_id=run["id"])))
        self.assertFalse(completed["result"]["isPartial"])
        self.assertEqual(
            "Overview for urgent-access",
            completed["result"]["stageSummaries"][0]["summarySections"]["overview"],
        )
        history = next(item for item in self.store.list_runs() if item["id"] == run["id"])
        self.assertEqual(
            ["Finding for urgent-access"],
            history["result"]["stageSummaries"][0]["summarySections"]["keyFindings"],
        )

    def test_legacy_failed_run_is_upgraded_to_stages_when_resumed(self) -> None:
        class LegacyResumeAdapter(ResearchAgentAdapter):
            key = "legacy-test"

            def status(self) -> dict[str, object]:
                return {"adapter": self.key, "ready": True}

            def run(self, prompt: str) -> AgentRunResult:
                payload = json.loads(prompt.split("\n\n", 1)[1])
                key = payload["researchStage"]["key"]
                return AgentRunResult(
                    output=key,
                    result={"summary": key, "candidates": [{"name": f"{key} lead"}], "lessons": []},
                )

        prompt = {
            "assignment": "Research Mesa Housing",
            "researchContext": {
                "mode": "standalone-location",
                "targetLocation": "Mesa, Arizona",
                "regionalScope": None,
                "sourcePackage": None,
            },
            "selectedSeed": None,
            "knownResources": [],
            "activeLessons": [],
            "rules": [],
            "outputSchema": {},
        }
        run_id = self.store.create_research_run(
            "legacy-test",
            "Research Mesa Housing",
            prompt,
            research_mode="standalone-location",
            target_location="Mesa, Arizona",
        )
        self.store.fail_run(run_id, "Hermes research exceeded the 900-second limit")
        coordinator = ResearchCoordinator(
            self.store, adapter_factory=lambda settings: LegacyResumeAdapter()
        )
        resumed = coordinator.resume(run_id)
        self.assertEqual(4, resumed["progress"]["total"])
        for _ in range(500):
            completed = self.store.get_run(run_id)
            if completed and completed["status"] == "completed":
                break
            time.sleep(0.01)
        self.assertEqual("completed", completed["status"])
        self.assertEqual(4, completed["progress"]["completed"])

    def test_restart_converts_an_interrupted_staged_run_to_resumable_partial(self) -> None:
        run_id = self.store.create_research_run(
            "demo",
            "Research Mesa",
            {"selectedSeed": None},
            research_mode="standalone-location",
            target_location="Mesa, Arizona",
            stages=[
                {"key": "one", "title": "First", "instruction": "First stage"},
                {"key": "two", "title": "Second", "instruction": "Second stage"},
            ],
        )
        self.store.mark_run_running(run_id)
        stages = self.store.list_run_stages(run_id)
        self.store.mark_stage_running(stages[0]["id"])
        self.store.complete_stage(stages[0]["id"], "done", {"summary": "done"}, None)
        self.store.mark_stage_running(stages[1]["id"])

        reopened = ResearchStore(self.store.path, recover_interrupted=True)
        recovered = reopened.get_run(run_id)
        self.assertEqual("partial", recovered["status"])
        self.assertEqual(["completed", "failed"], [stage["status"] for stage in recovered["stages"]])
        self.assertIn("app stopped", recovered["error"].lower())
        interrupted = reopened.list_stage_attempts(stages[1]["id"])
        self.assertEqual("failed", interrupted[0]["status"])
        self.assertIn("app stopped", interrupted[0]["error"].lower())

    def test_stage_attempts_preserve_success_and_retry_provenance(self) -> None:
        run_id = self.store.create_research_run(
            "dsh", "Research Mesa", {"selectedSeed": None},
            research_mode="standalone-location", target_location="Mesa, Arizona",
            stages=[{"key": "one", "title": "First", "instruction": "Research"}],
        )
        stage_id = self.store.list_run_stages(run_id)[0]["id"]
        failed_attempt = self.store.mark_stage_running(stage_id, prompt_chars=321)
        self.store.fail_stage(stage_id, "temporary failure", "partial", attempt_id=failed_attempt)
        completed_attempt = self.store.mark_stage_running(stage_id, prompt_chars=654)
        self.store.complete_stage(
            stage_id, "finished", {"summary": "done"}, {"model": "local"},
            attempt_id=completed_attempt,
        )

        attempts = self.store.list_stage_attempts(stage_id)
        self.assertEqual([1, 2], [item["attemptNumber"] for item in attempts])
        self.assertEqual(["failed", "completed"], [item["status"] for item in attempts])
        self.assertEqual(321, attempts[0]["promptChars"])
        self.assertEqual("temporary failure", attempts[0]["error"])
        self.assertEqual(8, attempts[1]["outputChars"])
        self.assertEqual("local", attempts[1]["usage"]["model"])

    def test_hermes_cli_adapter_uses_oneshot_and_parses_json(self) -> None:
        fake = self.root / "fake_hermes.py"
        fake.write_text(
            "import json, pathlib, sys\n"
            "if '--version' in sys.argv:\n"
            "    print('Hermes 0.test')\n"
            "    raise SystemExit(0)\n"
            "usage = pathlib.Path(sys.argv[sys.argv.index('--usage-file') + 1])\n"
            "usage.write_text(json.dumps({'provider': 'fake', 'completed': True}))\n"
            "print(json.dumps({'summary':'done','summarySections':{'overview':' concise overview ','keyFindings':[' one finding ',7],'cautions':'not a list','accessSteps':[' call first '],'gaps':[]},'candidates':[{'name':'New Place'}],'lessons':['Prefer direct services']}))\n",
            encoding="utf-8",
        )
        hermes_home = self.root / "hermes-home"
        hermes_home.mkdir()
        (hermes_home / "config.yaml").write_text("model:\n  default: fake\n", encoding="utf-8")
        (hermes_home / ".env").write_text("FAKE_API_KEY=present\n", encoding="utf-8")
        settings = {
            "hermesCommand": f"{os.sys.executable} {fake}",
            "dshCommand": "/not/the/hermes/command", "timeoutSeconds": 30,
        }
        with patch.dict(os.environ, {"HERMES_HOME": str(hermes_home)}):
            adapter = HermesCLIAdapter(settings)
            self.assertTrue(adapter.status()["ready"])
            result = adapter.run("Research Housing")
        self.assertEqual("New Place", result.result["candidates"][0]["name"])
        self.assertEqual("Prefer direct services", result.result["lessons"][0]["text"])
        self.assertEqual("concise overview", result.result["summarySections"]["overview"])
        self.assertEqual(["one finding"], result.result["summarySections"]["keyFindings"])
        self.assertEqual([], result.result["summarySections"]["cautions"])
        self.assertEqual(["call first"], result.result["summarySections"]["accessSteps"])
        self.assertEqual("fake", result.usage["provider"])

    def test_dsh_adapter_uses_headless_research_overlay_and_parses_json(self) -> None:
        fake = self.root / "fake_dsh.py"
        invocation = self.root / "dsh-invocation.json"
        fake.write_text(
            "import json, os, pathlib, sys\n"
            "if '--version' in sys.argv:\n"
            "    print('dsh 0.test')\n"
            "    raise SystemExit(0)\n"
            "patches = [pathlib.Path(sys.argv[i + 1]).read_text() for i, value in enumerate(sys.argv) if value == '--patch']\n"
            f"pathlib.Path({str(invocation)!r}).write_text(json.dumps({{'argv': sys.argv, 'cwd': os.getcwd(), 'dshHome': os.environ.get('DSH_HOME'), 'patches': patches}}))\n"
            "print(json.dumps({'summary':'dsh done','candidates':[{'name':'DeepSeek Place'}],'lessons':['Keep the adapter boundary']}))\n",
            encoding="utf-8",
        )
        settings = {
            "adapter": "dsh", "dshCommand": f"{os.sys.executable} {fake}",
            "dshModel": "deepseek-v4-flash", "command": "/legacy/hermes/command",
            "timeoutSeconds": 30,
        }
        environment = {
            "DEEPSEEK_API_KEY": "test-key-not-sent-anywhere",
            "RESOURCE_RESEARCH_DSH_HOME": str(self.root / "dsh-home"),
        }
        with patch.dict(os.environ, environment):
            adapter = DSHCLIAdapter(settings)
            self.assertTrue(adapter.status()["ready"])
            result = adapter.run("Research Housing")
        call = json.loads(invocation.read_text(encoding="utf-8"))
        self.assertIn("headless", call["argv"])
        self.assertEqual(2, call["argv"].count("--patch"))
        self.assertIn("tool-bash\n  disabled: true", call["patches"][0])
        self.assertIn("deepseek-v4-flash", call["patches"][1])
        self.assertNotEqual(str(Path.cwd()), call["cwd"])
        self.assertEqual(str((self.root / "dsh-home").resolve()), call["dshHome"])
        self.assertEqual("DeepSeek Place", result.result["candidates"][0]["name"])
        self.assertEqual("Keep the adapter boundary", result.result["lessons"][0]["text"])
        self.assertEqual("dsh", result.usage["adapter"])

    def test_dsh_adapter_reports_missing_key_without_storing_it(self) -> None:
        fake = self.root / "fake_dsh.py"
        fake.write_text("print('dsh 0.test')\n", encoding="utf-8")
        settings = {"adapter": "dsh", "dshCommand": f"{os.sys.executable} {fake}"}
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": ""}):
            status = DSHCLIAdapter(settings).status()
        self.assertTrue(status["installed"])
        self.assertFalse(status["configured"])
        self.assertFalse(status["ready"])
        self.assertIsInstance(build_adapter(settings), DSHCLIAdapter)

    def test_dsh_adapter_routes_local_qwen_without_a_deepseek_key(self) -> None:
        fake = self.root / "fake_local_dsh.py"
        invocation = self.root / "local-dsh-invocation.json"
        fake.write_text(
            "import json, os, pathlib, sys\n"
            "if '--version' in sys.argv:\n"
            "    print('dsh 0.test')\n"
            "    raise SystemExit(0)\n"
            "patches = [pathlib.Path(sys.argv[i + 1]).read_text() for i, value in enumerate(sys.argv) if value == '--patch']\n"
            f"pathlib.Path({str(invocation)!r}).write_text(json.dumps({{'argv': sys.argv, 'hasDeepSeekKey': 'DEEPSEEK_API_KEY' in os.environ, 'patches': patches}}))\n"
            "print(json.dumps({'summary':'local done','candidates':[{'name':'Qwen Place'}],'lessons':[]}))\n",
            encoding="utf-8",
        )
        settings = {
            "adapter": "dsh",
            "dshConfiguration": "local-qwen",
            "dshCommand": f"{os.sys.executable} {fake}",
            "dshModel": "deepseek-v4-flash",
            "timeoutSeconds": 30,
        }
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "must-not-be-forwarded"}):
            with patch("resource_research_agent.agents.validated_health", return_value={"ready": True}):
                adapter = DSHCLIAdapter(settings)
                status = adapter.status()
                result = adapter.run("Research Housing")

        call = json.loads(invocation.read_text(encoding="utf-8"))
        self.assertTrue(status["ready"])
        self.assertEqual("Local Qwen - no metered services", status["configurationDisplayName"])
        self.assertEqual(3, call["argv"].count("--patch"))
        self.assertFalse(call["hasDeepSeekKey"])
        self.assertIn("provider: qwen-local", call["patches"][1])
        self.assertIn("disabled: true", call["patches"][1])
        self.assertIn("provider: qwen-local", call["patches"][2])
        self.assertNotIn("deepseek-v4-flash", call["patches"][2])
        self.assertEqual("Qwen Place", result.result["candidates"][0]["name"])
        self.assertEqual("local-qwen", result.usage["configuration"])
        self.assertEqual("qwen-local", result.usage["provider"])
        self.assertEqual("mlx-lm", result.usage["runtime"])
        self.assertEqual("4-bit", result.usage["quantization"])
        self.assertEqual("ddgs", result.usage["searchProvider"])
        self.assertEqual("safe-http", result.usage["fetchProvider"])
        self.assertFalse(result.usage["metered"])

    def test_dsh_configuration_selection_round_trips_through_settings(self) -> None:
        saved = self.store.save_settings({
            "adapter": "dsh",
            "dshConfiguration": "local-qwen",
            "dshModel": "must-not-override-local-qwen",
        })

        self.assertEqual("dsh", saved["adapter"])
        self.assertEqual("local-qwen", saved["dshConfiguration"])
        self.assertEqual("must-not-override-local-qwen", saved["dshModel"])
        adapter = build_adapter(saved)
        self.assertIsInstance(adapter, DSHCLIAdapter)
        self.assertEqual("local-qwen", adapter._configuration().key)


if __name__ == "__main__":
    unittest.main()
