from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any


PLAYBOOK_LIBRARY_DIR = Path(__file__).with_name("playbook_library")


@dataclass(frozen=True)
class CategoryPlaybook:
    category_id: str
    label: str
    default_assignment: str
    scope: tuple[str, ...]
    exclusions: tuple[str, ...]
    verification_questions: tuple[str, ...]
    evidence_rules: tuple[str, ...]
    stages: tuple[dict[str, str], ...]
    library_version: str
    source: str


def normalize_supported_category(category_id: str) -> str | None:
    wanted = str(category_id or "").strip().casefold()
    return wanted or None


def _read_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(f"Cannot read playbook file {path.name}: {error}") from error
    if not isinstance(value, dict):
        raise RuntimeError(f"Playbook file {path.name} must contain one JSON object")
    return value


def _text(value: Any, field: str, path: Path) -> str:
    result = str(value or "").strip()
    if not result:
        raise RuntimeError(f"{path.name}: {field} must not be blank")
    return result


def _text_list(value: Any, field: str, path: Path) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise RuntimeError(f"{path.name}: {field} must be a non-empty JSON array")
    result = tuple(_text(item, field, path) for item in value)
    if len(set(result)) != len(result):
        raise RuntimeError(f"{path.name}: {field} contains a duplicate entry")
    return result


def _stages(value: Any, path: Path) -> tuple[dict[str, str], ...]:
    if not isinstance(value, list) or len(value) != 4:
        raise RuntimeError(f"{path.name}: stages must contain exactly four stages")
    stages: list[dict[str, str]] = []
    for position, item in enumerate(value, start=1):
        if not isinstance(item, dict):
            raise RuntimeError(f"{path.name}: stage {position} must be a JSON object")
        stages.append({
            "key": _text(item.get("key"), f"stages[{position}].key", path),
            "title": _text(item.get("title"), f"stages[{position}].title", path),
            "instruction": _text(
                item.get("instruction"), f"stages[{position}].instruction", path
            ),
        })
    keys = [stage["key"] for stage in stages]
    if len(set(keys)) != len(keys):
        raise RuntimeError(f"{path.name}: stage keys must be unique")
    return tuple(stages)


def _load_library() -> tuple[dict[str, CategoryPlaybook], dict[str, str], str, str]:
    base_path = PLAYBOOK_LIBRARY_DIR / "base.json"
    base = _read_object(base_path)
    if base.get("schemaVersion") != 1:
        raise RuntimeError("base.json: only playbook schemaVersion 1 is supported")
    library_version = _text(base.get("libraryVersion"), "libraryVersion", base_path)
    default_service_area = _text(
        base.get("defaultServiceArea"), "defaultServiceArea", base_path
    )
    evidence_rules = _text_list(base.get("evidenceRules"), "evidenceRules", base_path)
    playbooks: dict[str, CategoryPlaybook] = {}
    aliases: dict[str, str] = {}
    for path in sorted(PLAYBOOK_LIBRARY_DIR.glob("*.json")):
        if path == base_path:
            continue
        value = _read_object(path)
        category_id = _text(value.get("categoryId"), "categoryId", path)
        label = _text(value.get("label"), "label", path)
        if path.stem != category_id:
            raise RuntimeError(
                f"{path.name}: filename must match categoryId ({category_id}.json)"
            )
        normalized_id = normalize_supported_category(category_id)
        if not normalized_id or normalized_id in playbooks:
            raise RuntimeError(f"{path.name}: categoryId must be unique")
        assignment_template = _text(value.get("assignment"), "assignment", path)
        if assignment_template.count("{") != assignment_template.count("{service_area}"):
            raise RuntimeError(
                f"{path.name}: assignment may use only the {{service_area}} placeholder"
            )
        assignment = assignment_template.format(service_area=default_service_area)
        playbook = CategoryPlaybook(
            category_id=category_id,
            label=label,
            default_assignment=assignment,
            scope=_text_list(value.get("include"), "include", path),
            exclusions=_text_list(value.get("exclude"), "exclude", path),
            verification_questions=_text_list(
                value.get("verificationQuestions"), "verificationQuestions", path
            ),
            evidence_rules=evidence_rules,
            stages=_stages(value.get("stages"), path),
            library_version=library_version,
            source=path.name,
        )
        playbooks[normalized_id] = playbook
        raw_aliases = value.get("aliases", [])
        if not isinstance(raw_aliases, list):
            raise RuntimeError(f"{path.name}: aliases must be a JSON array")
        for alias in (category_id, label, *raw_aliases):
            normalized_alias = normalize_supported_category(str(alias))
            if normalized_alias:
                owner = aliases.setdefault(normalized_alias, normalized_id)
                if owner != normalized_id:
                    raise RuntimeError(f"{path.name}: alias {alias!r} is already in use")
    if not playbooks:
        raise RuntimeError("The playbook library does not contain any category files")
    return playbooks, aliases, library_version, default_service_area


PLAYBOOKS, PLAYBOOK_ALIASES, PLAYBOOK_LIBRARY_VERSION, DEFAULT_SERVICE_AREA = _load_library()


FOCUSED_RESEARCH_STAGE = ({
    "key": "focused-branch",
    "title": "Focused resource investigation",
    "instruction": (
        "Investigate the selected known resource deeply, follow its useful organization, program, provider, referral, "
        "and access relationships, and return only well-supported new candidates or material clarifications."
    ),
},)


def _generic_playbook(category_id: str, category_label: str) -> CategoryPlaybook:
    label = str(category_label or category_id).strip() or "Resource"
    subject = label.casefold()
    return CategoryPlaybook(
        category_id=str(category_id).strip() or subject,
        label=label,
        default_assignment=(
            f"Discover realistic {subject} resources for people in {DEFAULT_SERVICE_AREA}. Follow useful relationships "
            "from coordinating organizations and broad directories to the specific programs, providers, benefits, "
            "and practical services people can actually access. Verify eligibility, costs, schedules, service areas, "
            "availability, and the real intake or enrollment path."
        ),
        scope=(
            f"Immediate and direct {subject} services",
            f"Ongoing, preventive, and longer-term {subject} support",
            "Public benefits, nonprofit programs, government services, and credible private options",
            "Population-specific access and practical barriers",
            "The actual intake path, eligibility, schedule, service area, availability, and important gaps",
        ),
        exclusions=(
            "Ordinary commercial options that do not materially improve access for people facing hardship",
            "Directories without a verified, specific service behind the listing",
            "Organizations whose relevant service cannot be confirmed",
        ),
        verification_questions=(
            "What exact service can a person receive?",
            "Who qualifies, what does it cost, and how does someone begin?",
            "Is it currently available in the service area?",
        ),
        evidence_rules=next(iter(PLAYBOOKS.values())).evidence_rules,
        stages=(
            {"key": "direct-access", "title": f"Direct {label} access", "instruction": f"Investigate direct {subject} services a person can use now or soon. Verify the actual provider, service, location or service area, eligibility, schedule, cost, and first access step."},
            {"key": "ongoing-support", "title": f"Ongoing {label} support", "instruction": f"Investigate ongoing, preventive, and longer-term {subject} help, including government benefits, nonprofit programs, referrals, case management, education, and other realistic pathways."},
            {"key": "specialized-access", "title": "Specialized access and barriers", "instruction": f"Investigate {subject} resources for people facing population-specific or practical barriers. Check disability access, language, age, family status, documentation, transportation, cost, referral requirements, and other restrictions relevant to this category."},
            {"key": "category-gaps", "title": f"{label} gap review", "instruction": f"Cross-check earlier findings, avoid repeated candidates, verify time-sensitive claims, follow useful provider and referral relationships, and identify geographic, population, schedule, or service gaps in {subject}."},
        ),
        library_version=PLAYBOOK_LIBRARY_VERSION,
        source="generated fallback",
    )


def playbook_for(
    category_id: str,
    category_label: str | None = None,
    service_area: str | None = None,
) -> CategoryPlaybook:
    normalized = normalize_supported_category(category_id)
    if not normalized:
        raise ValueError("A research category is required")
    label_key = normalize_supported_category(category_label or "")
    owner = PLAYBOOK_ALIASES.get(normalized) or PLAYBOOK_ALIASES.get(label_key or "")
    playbook = PLAYBOOKS[owner] if owner else _generic_playbook(category_id, category_label or category_id)
    wanted_area = str(service_area or DEFAULT_SERVICE_AREA).strip() or DEFAULT_SERVICE_AREA
    if wanted_area == DEFAULT_SERVICE_AREA:
        return playbook
    return replace(
        playbook,
        default_assignment=playbook.default_assignment.replace(DEFAULT_SERVICE_AREA, wanted_area),
    )


def output_schema(category_label: str) -> dict[str, Any]:
    return {
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
            "resourceType": f"Concise description of the {category_label.lower()} service",
            "serviceNeed": "What need this can actually solve and for whom",
            "accessTimeline": "How soon someone can benefit, or unknown",
            "description": "Concise factual description",
            "eligibility": ["Eligibility facts"],
            "barriers": ["Costs, referrals, documentation, waits, restrictions, transportation, or other barriers"],
            "availability": {"status": "available, limited, exhausted, suspended, ended, or unknown", "asOf": "YYYY-MM-DD or blank", "evidence": "Source-backed explanation"},
            **({"petPolicy": "Pets, service animals, emotional-support animals, fees, or unknown"} if category_label.casefold() == "housing" else {}),
            "experienceAssessment": {"safety": "Assessment with evidence strength", "conditions": "Practical lived-experience details and limitations"},
            "recommendedTypes": ["Zero or more exact labels chosen only from categoryBrief.availableTypes"],
            "recommendedFor": ["Zero or more exact labels chosen only from categoryBrief.availableForGroups"],
            "classificationRationale": "Why the existing Type and For labels apply; recommend only labels supplied by the package",
            "suggestedNewTypes": ["Concise Type labels worth human consideration, only when the package taxonomy has a clear gap"],
            "evidence": [{"url": "Source URL", "title": "Source title", "sourceType": "official, government, news, firsthand, review, blog, transcript, or other", "accessedAt": "YYYY-MM-DD", "publishedAt": "YYYY-MM-DD or blank", "finding": "Relevant fact or carefully attributed experience", "firsthand": False, "reliability": "high, moderate, low, or lead-only"}],
            "unknowns": ["Questions still requiring research"],
            "followUpBranches": ["Specific next searches or relationships to pursue"],
        }],
        "lessons": [{"scope": "category or general", "text": "Proposed research lesson", "rationale": "What in this run suggests it"}],
    }


def stages_for(
    category_id: str,
    category_label: str | None = None,
    focused: bool = False,
) -> list[dict[str, str]]:
    source = FOCUSED_RESEARCH_STAGE if focused else playbook_for(category_id, category_label).stages
    return [deepcopy(stage) for stage in source]
