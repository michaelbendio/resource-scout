from __future__ import annotations

import json
import threading
from datetime import date
from typing import Any, Callable

from .agents import AgentRunError, ResearchAgentAdapter, build_adapter, merged_settings
from .duplicates import DuplicateIndex
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
        )
        thread = threading.Thread(
            target=self._execute, args=(run_id, prompt_object, settings),
            name=f"resource-research-{run_id}", daemon=True,
        )
        thread.start()
        return self.store.get_run(run_id) or {"id": run_id, "status": "queued"}

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
        try:
            adapter = self.adapter_factory(settings)
            response = adapter.run(self._prompt_text(prompt_object))
            duplicate_index = DuplicateIndex(self.store)
            run = self.store.get_run(run_id)
            source_import_id = run.get("sourceImportId") if run else None
            saved_candidates = []
            for candidate in response.result.get("candidates", []):
                matches = duplicate_index.match(candidate, import_id=source_import_id, limit=1) if source_import_id else []
                match = matches[0] if matches else None
                saved_candidates.append(self.store.save_discovery(candidate, match, run_id=run_id))
            for lesson in response.result.get("lessons", []):
                self.store.save_lesson(
                    lesson["text"], scope=lesson.get("scope", "category"),
                    rationale=lesson.get("rationale", ""), status="proposed",
                    source="agent", run_id=run_id,
                    research_mode=run.get("researchMode", "package") if run else "package",
                    target_location=run.get("targetLocation") if run else None,
                )
            stored_result = dict(response.result)
            stored_result["savedCandidates"] = saved_candidates
            self.store.complete_run(run_id, response.output, stored_result, response.usage)
        except AgentRunError as error:
            self.store.fail_run(run_id, str(error), error.output)
        except Exception as error:
            self.store.fail_run(run_id, f"Unexpected research error: {error}")
