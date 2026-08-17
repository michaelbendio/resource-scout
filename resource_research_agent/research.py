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

    def start(self, assignment: str, seed_resource_id: str | None = None) -> dict[str, Any]:
        assignment = assignment.strip() or DEFAULT_ASSIGNMENT
        import_summary = self.store.import_summary()
        if not import_summary:
            raise ValueError("Import a resource package before starting research")
        import_id = int(import_summary["id"])
        selected_seed = None
        if seed_resource_id:
            selected_seed = next(
                (seed for seed in self.store.list_seeds(import_id) if seed["resourceId"] == seed_resource_id),
                None,
            )
            if not selected_seed:
                raise ValueError("The selected research seed was not found in the current package")
        prompt_object = self._prompt_object(assignment, import_summary, selected_seed)
        settings = merged_settings(self.store.get_settings())
        adapter = self.adapter_factory(settings)
        status = adapter.status()
        if not status.get("ready"):
            raise ValueError(status.get("message") or "The research agent is not ready")
        run_id = self.store.create_research_run(
            adapter.key, assignment, prompt_object, import_id,
            selected_seed["resourceId"] if selected_seed else None,
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
        import_summary: dict[str, Any],
        selected_seed: dict[str, Any] | None,
    ) -> dict[str, Any]:
        seeds = self.store.list_seeds(int(import_summary["id"]))
        return {
            "role": "Housing resource discovery researcher for a human-reviewed social-service directory",
            "today": date.today().isoformat(),
            "assignment": assignment,
            "categoryBrief": {
                "category": import_summary["category"],
                "geographicFocus": "Utah County first; follow viable Salt Lake, Weber, and other Utah options when appropriate.",
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
            "activeLessons": self.store.list_lessons(active_only=True),
            "rules": [
                "Research the public web only. Do not edit local files, the imported package, or external systems.",
                "Known resources may be researched deeply and used for branching, but must not be presented as new discoveries.",
                "Return only one valid JSON object matching outputSchema. Do not wrap it in Markdown.",
                "Prefer a few well-investigated candidates over a large list of shallow directory entries.",
            ],
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
            saved_candidates = []
            for candidate in response.result.get("candidates", []):
                matches = duplicate_index.match(candidate, limit=1)
                match = matches[0] if matches else None
                saved_candidates.append(self.store.save_discovery(candidate, match, run_id=run_id))
            for lesson in response.result.get("lessons", []):
                self.store.save_lesson(
                    lesson["text"], scope=lesson.get("scope", "category"),
                    rationale=lesson.get("rationale", ""), status="proposed",
                    source="agent", run_id=run_id,
                )
            stored_result = dict(response.result)
            stored_result["savedCandidates"] = saved_candidates
            self.store.complete_run(run_id, response.output, stored_result, response.usage)
        except AgentRunError as error:
            self.store.fail_run(run_id, str(error), error.output)
        except Exception as error:
            self.store.fail_run(run_id, f"Unexpected research error: {error}")
