from __future__ import annotations

import json
import threading
from datetime import date
from typing import Any, Callable

from .agents import AgentRunError, ResearchAgentAdapter, build_adapter, merged_settings
from .duplicates import DuplicateIndex
from .importer import normalize_index_value
from .playbooks import (
    CategoryPlaybook,
    PLAYBOOKS,
    DEFAULT_SERVICE_AREA,
    output_schema,
    playbook_for,
    stages_for,
)
from .storage import ResearchStore


def standalone_assignment(location: str) -> str:
    return (
        f"Discover realistic ways a person without adequate housing in {location} could obtain safe "
        "temporary or permanent housing. Follow useful relationships rather than stopping at a directory "
        "listing: voucher providers to participating motels, organizations to specific programs, and temporary "
        "options to longer-term pathways. Investigate practical access and lived experience as well as official claims."
    )
class ResearchCoordinator:
    def __init__(
        self,
        store: ResearchStore,
        adapter_factory: Callable[[dict[str, Any]], ResearchAgentAdapter] = build_adapter,
    ) -> None:
        self.store = store
        self.adapter_factory = adapter_factory

    def agent_status(self) -> dict[str, Any]:
        settings = merged_settings(self.store.get_settings())
        status = self.adapter_factory(settings).status()
        status["settings"] = settings
        return status

    def start(
        self,
        assignment: str,
        seed_resource_id: str | None = None,
        *,
        research_mode: str = "package",
        target_location: str | None = None,
        regional_scope: str = "",
        target_category_id: str = "housing",
    ) -> dict[str, Any]:
        if research_mode not in {"package", "standalone-location"}:
            raise ValueError(f"Unsupported research mode: {research_mode}")
        target_location = target_location.strip() if target_location else None
        regional_scope = regional_scope.strip()
        import_summary = None
        import_id = None
        category_id = "housing"
        category_label = "Housing"
        playbook = PLAYBOOKS["housing"]
        if research_mode == "package":
            import_summary = self.store.import_summary()
            if not import_summary:
                raise ValueError("Import a resource package before starting package-backed research")
            import_id = int(import_summary["id"])
            category = self.store.import_category(import_id, target_category_id)
            if not category:
                raise ValueError("The selected category was not found in the current package")
            category_id = str(category["id"])
            category_label = str(category["label"])
            service_area = str(import_summary.get("serviceArea") or DEFAULT_SERVICE_AREA)
            playbook = playbook_for(category_id, category_label, service_area)
            target_location = None
            regional_scope = ""
            assignment = (assignment.strip() or playbook.default_assignment).replace(
                DEFAULT_SERVICE_AREA, service_area
            )
        else:
            if not target_location:
                raise ValueError("Enter a research location for standalone research")
            if seed_resource_id:
                raise ValueError("Standalone location research cannot branch from an imported package seed")
            assignment = assignment.strip() or standalone_assignment(target_location)
        selected_seed = None
        if seed_resource_id:
            selected_seed = next(
                (
                    seed for seed in self.store.list_seeds(import_id, category_id)
                    if seed["resourceId"] == seed_resource_id
                ),
                None,
            )
            if not selected_seed:
                raise ValueError("The selected research seed was not found in the current package")
        prompt_object = self._prompt_object(
            assignment,
            research_mode,
            import_summary,
            selected_seed,
            target_location,
            regional_scope,
            category_id,
            category_label,
            playbook,
        )
        settings = merged_settings(self.store.get_settings())
        adapter = self.adapter_factory(settings)
        status = adapter.status()
        if not status.get("ready"):
            raise ValueError(status.get("message") or "The research agent is not ready")
        run_id = self.store.create_research_run(
            adapter.key, assignment, prompt_object, import_id,
            selected_seed["resourceId"] if selected_seed else None,
            research_mode=research_mode,
            target_location=target_location,
            regional_scope=regional_scope,
            target_category_id=category_id,
            target_category_label=category_label,
            stages=self._research_stages(category_id, category_label, selected_seed),
        )
        thread = threading.Thread(
            target=self._execute, args=(run_id, prompt_object, settings),
            name=f"resource-research-{run_id}", daemon=True,
        )
        thread.start()
        return self.store.get_run(run_id) or {"id": run_id, "status": "queued"}

    @staticmethod
    def _research_stages(
        category_id: str,
        category_label: str,
        selected_seed: dict[str, Any] | None,
    ) -> list[dict[str, str]]:
        return stages_for(category_id, category_label, focused=bool(selected_seed))

    def resume(self, run_id: int) -> dict[str, Any]:
        run = self.store.get_run(run_id)
        if not run:
            raise ValueError("Research run not found")
        if run["status"] not in {"failed", "partial"}:
            raise ValueError("Only failed or partial research runs can be resumed")
        settings = merged_settings(self.store.get_settings())
        adapter = self.adapter_factory(settings)
        status = adapter.status()
        if adapter.key != run["adapter"]:
            raise ValueError(f"Select the {run['adapter']} connection before resuming this run")
        if not status.get("ready"):
            raise ValueError(status.get("message") or "The research agent is not ready")
        if not run.get("stages"):
            self.store.add_run_stages(
                run_id,
                self._research_stages(
                    run.get("targetCategoryId", "housing"),
                    run.get("targetCategoryLabel", "Housing"),
                    run.get("prompt", {}).get("selectedSeed"),
                ),
            )
            run = self.store.get_run(run_id) or run
        resumed = self.store.prepare_run_resume(run_id)
        if not resumed:
            raise ValueError("Research run not found")
        thread = threading.Thread(
            target=self._execute, args=(run_id, run["prompt"], settings),
            name=f"resource-research-{run_id}-resume", daemon=True,
        )
        thread.start()
        return resumed

    def _prompt_object(
        self,
        assignment: str,
        research_mode: str,
        import_summary: dict[str, Any] | None,
        selected_seed: dict[str, Any] | None,
        target_location: str | None,
        regional_scope: str,
        category_id: str,
        category_label: str,
        playbook: CategoryPlaybook,
    ) -> dict[str, Any]:
        seeds = self.store.list_seeds(int(import_summary["id"]), category_id) if import_summary else []
        package_mode = research_mode == "package"
        category = {"id": category_id, "label": category_label}
        taxonomy = self.store.import_taxonomy(int(import_summary["id"])) if import_summary else {
            "categories": [], "forGroups": []
        }
        category_taxonomy = next(
            (item for item in taxonomy["categories"] if item["id"] == category_id),
            {"types": []},
        )
        geographic_focus = (
            f"{import_summary['serviceArea']} first. Follow nearby or regional options only when they "
            f"realistically serve people in {import_summary['serviceArea']}; state service areas and "
            "transportation barriers explicitly."
            if package_mode
            else (
                f"{target_location} first. Also investigate {regional_scope} when those resources realistically serve "
                f"people in {target_location}; state service areas and transportation barriers explicitly."
                if regional_scope
                else f"{target_location} first. Follow nearby county or regional options only when they realistically serve people in {target_location}; state service areas and transportation barriers explicitly."
            )
        )
        active_lessons = self.store.list_lessons(
            active_only=True,
            research_mode=research_mode,
            target_location=target_location,
            target_category_id=category_id,
        )
        rules = [
            "Research the public web only. Do not edit local files or external systems.",
            "Return only one valid JSON object matching outputSchema. Do not wrap it in Markdown.",
            "Prefer a few well-investigated candidates over a large list of shallow directory entries.",
            "Investigate every resourceGatheringRequirement for every candidate. Put verified findings in its designated output fields and put material unanswered questions in unknowns rather than silently omitting them.",
        ]
        if package_mode:
            rules.insert(1, "Do not edit the imported package.")
            rules.insert(2, "Known resources may be researched deeply and used for branching, but must not be presented as new discoveries.")
        else:
            rules.insert(1, "No resource package is connected to this run. Treat every credible finding as a candidate for human review.")
            rules.insert(2, "This is exploratory location research, not an official or comprehensive TSO Resources inventory.")
        return {
            "role": f"{category_label} resource discovery researcher for a human-reviewed social-service directory",
            "today": date.today().isoformat(),
            "assignment": assignment,
            "researchContext": {
                "mode": research_mode,
                "targetLocation": target_location,
                "regionalScope": regional_scope or None,
                "sourcePackage": (
                    {
                        "id": import_summary["id"],
                        "name": import_summary["sourceName"],
                        "officeName": import_summary["officeName"],
                        "serviceArea": import_summary["serviceArea"],
                        "category": category,
                    }
                    if import_summary else None
                ),
            },
            "categoryBrief": {
                "category": category,
                "playbookVersion": playbook.library_version,
                "playbookSource": playbook.source,
                "availableTypes": category_taxonomy.get("types", []),
                "availableForGroups": taxonomy["forGroups"],
                "geographicFocus": geographic_focus,
                "scope": list(playbook.scope),
                "exclude": list(playbook.exclusions),
                "verificationQuestions": list(playbook.verification_questions),
                "evidenceRules": list(playbook.evidence_rules),
            },
            "resourceGatheringRequirements": [
                dict(requirement) for requirement in playbook.resource_gathering_requirements
            ],
            "knownResources": [{"id": seed["resourceId"], "name": seed["name"]} for seed in seeds],
            "selectedSeed": selected_seed,
            "activeLessons": active_lessons,
            "rules": rules,
            "outputSchema": output_schema(category_label),
        }

    @staticmethod
    def _prompt_text(prompt_object: dict[str, Any]) -> str:
        return (
            "Complete this research assignment. Follow every rule and return only the requested JSON object.\n\n"
            + json.dumps(prompt_object, ensure_ascii=False, indent=2)
        )

    def _execute(
        self,
        run_id: int,
        prompt_object: dict[str, Any],
        settings: dict[str, Any],
        *,
        stage_limit: int | None = None,
    ) -> None:
        self.store.mark_run_running(run_id)
        adapter = self.adapter_factory(settings)
        duplicate_index = DuplicateIndex(self.store)
        run = self.store.get_run(run_id)
        if not run:
            return
        source_import_id = run.get("sourceImportId")
        stages = run.get("stages", [])
        if not stages:
            self.store.fail_run(run_id, "This research run has no executable stages")
            return
        existing_names = {
            self._candidate_name_key(discovery.get("candidate", {}))
            for discovery in self.store.list_discoveries(run_id=run_id)
        }
        existing_names.discard("")
        completed_this_execution = 0
        for stage in stages:
            if stage["status"] == "completed":
                continue
            attempt_id = None
            try:
                stage_prompt = self._stage_prompt(run_id, prompt_object, stage, len(stages))
                prompt_text = self._prompt_text(stage_prompt)
                attempt_id = self.store.mark_stage_running(
                    stage["id"], prompt_chars=len(prompt_text)
                )
                response = adapter.run(prompt_text)
                saved_candidates = []
                for candidate in response.result.get("candidates", []):
                    name_key = self._candidate_name_key(candidate)
                    if name_key and name_key in existing_names:
                        continue
                    matches = (
                        duplicate_index.match(candidate, import_id=source_import_id, limit=1)
                        if source_import_id else []
                    )
                    match = matches[0] if matches else None
                    saved = self.store.save_discovery(
                        candidate, match, run_id=run_id, stage_id=stage["id"]
                    )
                    saved_candidates.append(saved)
                    if name_key:
                        existing_names.add(name_key)
                for lesson in response.result.get("lessons", []):
                    self.store.save_lesson(
                        lesson["text"], scope=lesson.get("scope", "category"),
                        rationale=lesson.get("rationale", ""), status="proposed",
                        source="agent", run_id=run_id,
                        research_mode=run.get("researchMode", "package"),
                        target_location=run.get("targetLocation"), stage_id=stage["id"],
                        target_category_id=run.get("targetCategoryId", "housing"),
                        target_category_label=run.get("targetCategoryLabel", "Housing"),
                    )
                stored_stage_result = dict(response.result)
                stored_stage_result["savedCandidates"] = saved_candidates
                self.store.complete_stage(
                    stage["id"], response.output, stored_stage_result, response.usage,
                    attempt_id=attempt_id,
                )
                result, output, usage = self._aggregate_progress(run_id)
                self.store.update_run_progress(run_id, output, result, usage)
                completed_this_execution += 1
                if stage_limit is not None and completed_this_execution >= stage_limit:
                    remaining = [
                        item for item in self.store.list_run_stages(run_id)
                        if item["status"] != "completed"
                    ]
                    if remaining:
                        self.store.partial_run(
                            run_id,
                            f"Benchmark calibration paused after {completed_this_execution} stage.",
                            output, result, usage,
                        )
                        return
            except AgentRunError as error:
                self.store.fail_stage(
                    stage["id"], str(error), error.output, attempt_id=attempt_id
                )
                self._finish_interrupted_run(run_id, str(error))
                return
            except Exception as error:
                message = f"Unexpected research error: {error}"
                self.store.fail_stage(stage["id"], message, attempt_id=attempt_id)
                self._finish_interrupted_run(run_id, message)
                return
        result, output, usage = self._aggregate_progress(run_id)
        self.store.complete_run(run_id, output, result, usage)

    @staticmethod
    def _candidate_name_key(candidate: dict[str, Any]) -> str:
        name = str(candidate.get("name") or candidate.get("title") or "")
        return normalize_index_value("name", name)

    def _stage_prompt(
        self,
        run_id: int,
        prompt_object: dict[str, Any],
        stage: dict[str, Any],
        total_stages: int,
    ) -> dict[str, Any]:
        completed = []
        discoveries = self.store.list_discoveries(run_id=run_id)
        names_by_stage: dict[int, list[str]] = {}
        for discovery in discoveries:
            if discovery.get("stageId"):
                names_by_stage.setdefault(int(discovery["stageId"]), []).append(discovery["name"])
        for prior in self.store.list_run_stages(run_id):
            if prior["status"] != "completed" or not prior.get("result"):
                continue
            completed.append({
                "stage": prior["title"],
                "summary": str(prior["result"].get("summary") or ""),
                "candidateNames": names_by_stage.get(prior["id"], []),
            })
        return {
            **prompt_object,
            "researchStage": {
                "key": stage["key"],
                "title": stage["title"],
                "position": stage["position"],
                "total": total_stages,
                "instruction": stage["instruction"],
            },
            "completedStageFindings": completed,
            "stageRules": [
                "Complete only this bounded research stage.",
                "Do not repeat a candidate named in completedStageFindings unless correcting a material error.",
                "Make summarySections easy for a human to scan: use a short overview and separate array items instead of embedding (1), (2), or (3) in a prose paragraph.",
                "Return a complete valid JSON result for this stage before doing optional follow-up work.",
            ],
        }

    def _aggregate_progress(
        self, run_id: int
    ) -> tuple[dict[str, Any], str, dict[str, Any] | None]:
        stages = self.store.list_run_stages(run_id)
        completed = [stage for stage in stages if stage["status"] == "completed" and stage.get("result")]
        summaries = []
        for stage in completed:
            sections = stage["result"].get("summarySections", {})
            summaries.append({
                "key": stage["key"],
                "title": stage["title"],
                "summary": str(stage["result"].get("summary") or ""),
                "summarySections": sections if isinstance(sections, dict) else {},
            })
        summary_parts = [f"{item['title']}: {item['summary']}" for item in summaries if item["summary"]]
        prefix = f"Completed {len(completed)} of {len(stages)} research stages."
        result = {
            "summary": "\n\n".join([prefix, *summary_parts]),
            "stageSummaries": summaries,
            "savedCandidates": [
                {"id": item["id"], "status": item["status"], "origin": item["origin"]}
                for item in self.store.list_discoveries(run_id=run_id)
            ],
            "isPartial": len(completed) < len(stages),
        }
        output = "\n\n".join(stage["output"] for stage in completed if stage.get("output"))
        stage_usage = [
            {"key": stage["key"], "usage": stage["usage"]}
            for stage in completed if stage.get("usage")
        ]
        usage = {"stages": stage_usage} if stage_usage else None
        return result, output, usage

    def _finish_interrupted_run(self, run_id: int, error: str) -> None:
        result, output, usage = self._aggregate_progress(run_id)
        if any(stage["status"] == "completed" for stage in self.store.list_run_stages(run_id)):
            self.store.partial_run(run_id, error, output, result, usage)
        else:
            self.store.fail_run(run_id, error, output)
