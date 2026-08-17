from __future__ import annotations

import json
import threading
from datetime import date
from typing import Any, Callable

from .agents import AgentRunError, ResearchAgentAdapter, build_adapter, merged_settings
from .duplicates import DuplicateIndex
from .importer import normalize_index_value
from .storage import ResearchStore


DEFAULT_ASSIGNMENT = (
    "Discover realistic ways a person without adequate housing in Utah County could obtain safe "
    "temporary or permanent housing. Follow useful relationships rather than stopping at a directory "
    "listing: voucher providers to participating motels, organizations to specific programs, and temporary "
    "options to longer-term pathways. Investigate practical access and lived experience as well as official claims."
)


def standalone_assignment(location: str) -> str:
    return (
        f"Discover realistic ways a person without adequate housing in {location} could obtain safe "
        "temporary or permanent housing. Follow useful relationships rather than stopping at a directory "
        "listing: voucher providers to participating motels, organizations to specific programs, and temporary "
        "options to longer-term pathways. Investigate practical access and lived experience as well as official claims."
    )


OUTPUT_SCHEMA = {
    "summary": "Brief account of the research performed and the most important findings.",
    "candidates": [{
        "name": "Resource or program name",
        "organization": "Parent organization, if distinct",
        "program": "Program name, if distinct",
        "website": "Best direct URL",
        "address": "Physical or service address",
        "phone": "Contact phone",
        "hours": "Published service, office, intake, or access hours, or blank if unknown",
        "geography": "Area served",
        "resourceType": "shelter, voucher, motel, transitional housing, etc.",
        "housingNeed": "What need this can actually solve and for whom",
        "accessTimeline": "tonight, days, weeks, months, long-term, or unknown",
        "description": "Concise factual description",
        "eligibility": ["Eligibility facts"],
        "barriers": ["Costs, referrals, documentation, sobriety, waits, restrictions, transportation"],
        "availability": {"status": "available, limited, exhausted, suspended, ended, or unknown", "asOf": "YYYY-MM-DD or blank", "evidence": "Source-backed explanation"},
        "petPolicy": "Pets, service animals, emotional-support animals, fees, or unknown",
        "experienceAssessment": {"safety": "Assessment with evidence strength", "conditions": "Cleanliness, theft, drugs, rules, staff, belongings, and limitations"},
        "evidence": [{"url": "Source URL", "title": "Source title", "sourceType": "official, government, news, firsthand, review, blog, transcript, or other", "accessedAt": "YYYY-MM-DD", "publishedAt": "YYYY-MM-DD or blank", "finding": "Relevant fact or carefully attributed experience", "firsthand": False, "reliability": "high, moderate, low, or lead-only"}],
        "unknowns": ["Questions still requiring research"],
        "followUpBranches": ["Specific next searches or relationships to pursue"],
    }],
    "lessons": [{"scope": "category or general", "text": "Proposed research lesson", "rationale": "What in this run suggests it"}],
}


BROAD_RESEARCH_STAGES = [
    {
        "key": "urgent-access",
        "title": "Immediate safety and emergency access",
        "instruction": (
            "Investigate options that can help tonight or within days: emergency and seasonal shelter, domestic-violence "
            "and family or youth shelter, safe temporary lodging, motel vouchers, coordinated entry, crisis access, "
            "transportation, pet barriers, and the real intake path."
        ),
    },
    {
        "key": "stabilization",
        "title": "Homelessness prevention and stabilization",
        "instruction": (
            "Investigate eviction prevention, rent and deposit help, utility help, diversion, rapid rehousing, flexible "
            "funds, case management, benefits, and other practical pathways that can prevent or shorten homelessness."
        ),
    },
    {
        "key": "specialized-housing",
        "title": "Transitional and specialized housing",
        "instruction": (
            "Investigate transitional, supportive, recovery, reentry, treatment-linked, medically appropriate, veteran, "
            "family, youth, LGBTQ+, disability, and other population-specific housing that realistically serves the area."
        ),
    },
    {
        "key": "long-term-and-gaps",
        "title": "Permanent pathways and gap review",
        "instruction": (
            "Investigate affordable and subsidized housing, housing authorities, waitlists, permanent supportive housing, "
            "landlord or rental pathways, and important gaps. Cross-check earlier findings, avoid repeating candidates, "
            "and pursue missing relationships or access details needed for a useful review."
        ),
    },
]


FOCUSED_RESEARCH_STAGE = [{
    "key": "focused-branch",
    "title": "Focused resource investigation",
    "instruction": (
        "Investigate the selected known resource deeply, follow its useful organization, program, provider, referral, "
        "and access relationships, and return only well-supported new candidates or material clarifications."
    ),
}]


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
    ) -> dict[str, Any]:
        if research_mode not in {"package", "standalone-location"}:
            raise ValueError(f"Unsupported research mode: {research_mode}")
        target_location = target_location.strip() if target_location else None
        regional_scope = regional_scope.strip()
        import_summary = None
        import_id = None
        if research_mode == "package":
            import_summary = self.store.import_summary()
            if not import_summary:
                raise ValueError("Import a resource package before starting package-backed research")
            import_id = int(import_summary["id"])
            target_location = None
            regional_scope = ""
            assignment = assignment.strip() or DEFAULT_ASSIGNMENT
        else:
            if not target_location:
                raise ValueError("Enter a research location for standalone research")
            if seed_resource_id:
                raise ValueError("Standalone location research cannot branch from an imported package seed")
            assignment = assignment.strip() or standalone_assignment(target_location)
        selected_seed = None
        if seed_resource_id:
            selected_seed = next(
                (seed for seed in self.store.list_seeds(import_id) if seed["resourceId"] == seed_resource_id),
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
            stages=self._research_stages(selected_seed),
        )
        thread = threading.Thread(
            target=self._execute, args=(run_id, prompt_object, settings),
            name=f"resource-research-{run_id}", daemon=True,
        )
        thread.start()
        return self.store.get_run(run_id) or {"id": run_id, "status": "queued"}

    @staticmethod
    def _research_stages(selected_seed: dict[str, Any] | None) -> list[dict[str, str]]:
        return [dict(stage) for stage in (FOCUSED_RESEARCH_STAGE if selected_seed else BROAD_RESEARCH_STAGES)]

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
                self._research_stages(run.get("prompt", {}).get("selectedSeed")),
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
    ) -> dict[str, Any]:
        seeds = self.store.list_seeds(int(import_summary["id"])) if import_summary else []
        package_mode = research_mode == "package"
        category = import_summary["category"] if import_summary else {"id": None, "label": "Housing"}
        geographic_focus = (
            "Utah County first; follow viable Salt Lake, Weber, and other Utah options when appropriate."
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
        )
        rules = [
            "Research the public web only. Do not edit local files or external systems.",
            "Return only one valid JSON object matching outputSchema. Do not wrap it in Markdown.",
            "Prefer a few well-investigated candidates over a large list of shallow directory entries.",
        ]
        if package_mode:
            rules.insert(1, "Do not edit the imported package.")
            rules.insert(2, "Known resources may be researched deeply and used for branching, but must not be presented as new discoveries.")
        else:
            rules.insert(1, "No resource package is connected to this run. Treat every credible finding as a candidate for human review.")
            rules.insert(2, "This is exploratory location research, not an official or comprehensive TSO Resources inventory.")
        return {
            "role": "Housing resource discovery researcher for a human-reviewed social-service directory",
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
                        "category": import_summary["category"],
                    }
                    if import_summary else None
                ),
            },
            "categoryBrief": {
                "category": category,
                "geographicFocus": geographic_focus,
                "scope": [
                    "Emergency shelter and safe temporary lodging",
                    "Motel or hotel vouchers and the particular lodging providers that accept them",
                    "Transitional, supportive, sober, reentry, treatment-linked, and medically appropriate housing",
                    "Rent, deposit, utility, rapid-rehousing, subsidized, and permanent-housing pathways",
                    "Pet-friendly options and temporary animal care when pet rules block access",
                ],
                "evidenceRules": [
                    "Use official or authoritative sources for program facts; retain source URLs and dates.",
                    "Use firsthand accounts, reporting, reviews, blogs, and transcripts carefully for lived experience.",
                    "Attribute anecdotal claims and never turn a single account into an unqualified fact.",
                    "Treat funding, capacity, wait lists, and voucher availability as time-varying and record an as-of date.",
                    "Unknown pet policy, availability, eligibility, or conditions should become an explicit research question.",
                ],
            },
            "knownResources": [{"id": seed["resourceId"], "name": seed["name"]} for seed in seeds],
            "selectedSeed": selected_seed,
            "activeLessons": active_lessons,
            "rules": rules,
            "outputSchema": OUTPUT_SCHEMA,
        }

    @staticmethod
    def _prompt_text(prompt_object: dict[str, Any]) -> str:
        return (
            "Complete this research assignment. Follow every rule and return only the requested JSON object.\n\n"
            + json.dumps(prompt_object, ensure_ascii=False, indent=2)
        )

    def _execute(self, run_id: int, prompt_object: dict[str, Any], settings: dict[str, Any]) -> None:
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
        for stage in stages:
            if stage["status"] == "completed":
                continue
            self.store.mark_stage_running(stage["id"])
            try:
                stage_prompt = self._stage_prompt(run_id, prompt_object, stage, len(stages))
                response = adapter.run(self._prompt_text(stage_prompt))
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
                    )
                stored_stage_result = dict(response.result)
                stored_stage_result["savedCandidates"] = saved_candidates
                self.store.complete_stage(stage["id"], response.output, stored_stage_result, response.usage)
                result, output, usage = self._aggregate_progress(run_id)
                self.store.update_run_progress(run_id, output, result, usage)
            except AgentRunError as error:
                self.store.fail_stage(stage["id"], str(error), error.output)
                self._finish_interrupted_run(run_id, str(error))
                return
            except Exception as error:
                message = f"Unexpected research error: {error}"
                self.store.fail_stage(stage["id"], message)
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
                "Return a complete valid JSON result for this stage before doing optional follow-up work.",
            ],
        }

    def _aggregate_progress(
        self, run_id: int
    ) -> tuple[dict[str, Any], str, dict[str, Any] | None]:
        stages = self.store.list_run_stages(run_id)
        completed = [stage for stage in stages if stage["status"] == "completed" and stage.get("result")]
        summaries = [
            {"key": stage["key"], "title": stage["title"], "summary": str(stage["result"].get("summary") or "")}
            for stage in completed
        ]
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
