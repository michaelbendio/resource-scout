from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CategoryPlaybook:
    category_id: str
    label: str
    default_assignment: str
    scope: tuple[str, ...]
    evidence_rules: tuple[str, ...]
    stages: tuple[dict[str, str], ...]


COMMON_EVIDENCE_RULES = (
    "Use official or authoritative sources for program facts; retain source URLs and dates.",
    "Use firsthand accounts, reporting, reviews, blogs, and transcripts carefully for lived experience.",
    "Attribute anecdotal claims and never turn a single account into an unqualified fact.",
    "Treat funding, capacity, schedules, eligibility, and availability as time-varying and record an as-of date.",
    "Turn important unknowns into explicit research questions rather than filling gaps by inference.",
)


PLAYBOOKS: dict[str, CategoryPlaybook] = {
    "housing": CategoryPlaybook(
        category_id="housing",
        label="Housing",
        default_assignment=(
            "Discover realistic ways a person without adequate housing in Utah County could obtain safe "
            "temporary or permanent housing. Follow useful relationships rather than stopping at a directory "
            "listing: voucher providers to participating motels, organizations to specific programs, and temporary "
            "options to longer-term pathways. Investigate practical access and lived experience as well as official claims."
        ),
        scope=(
            "Emergency shelter and safe temporary lodging",
            "Motel or hotel vouchers and the particular lodging providers that accept them",
            "Transitional, supportive, sober, reentry, treatment-linked, and medically appropriate housing",
            "Rent, deposit, utility, rapid-rehousing, subsidized, and permanent-housing pathways",
            "Pet-friendly options and temporary animal care when pet rules block access",
        ),
        evidence_rules=COMMON_EVIDENCE_RULES,
        stages=(
            {
                "key": "urgent-access",
                "title": "Immediate safety and emergency access",
                "instruction": (
                    "Investigate options that can help tonight or within days: emergency and seasonal shelter, "
                    "domestic-violence and family or youth shelter, safe temporary lodging, motel vouchers, "
                    "coordinated entry, crisis access, transportation, pet barriers, and the real intake path."
                ),
            },
            {
                "key": "stabilization",
                "title": "Homelessness prevention and stabilization",
                "instruction": (
                    "Investigate eviction prevention, rent and deposit help, utility help, diversion, rapid rehousing, "
                    "flexible funds, case management, benefits, and practical pathways that can prevent or shorten homelessness."
                ),
            },
            {
                "key": "specialized-housing",
                "title": "Transitional and specialized housing",
                "instruction": (
                    "Investigate transitional, supportive, recovery, reentry, treatment-linked, medically appropriate, "
                    "veteran, family, youth, disability, and other population-specific housing that realistically serves the area."
                ),
            },
            {
                "key": "long-term-and-gaps",
                "title": "Permanent pathways and gap review",
                "instruction": (
                    "Investigate affordable and subsidized housing, housing authorities, waitlists, permanent supportive "
                    "housing, landlord or rental pathways, and important gaps. Cross-check earlier findings and pursue "
                    "missing relationships or access details needed for a useful review."
                ),
            },
        ),
    ),
    "food": CategoryPlaybook(
        category_id="food",
        label="Food",
        default_assignment=(
            "Discover realistic ways a person facing food insecurity in Utah County can obtain meals and groceries. "
            "Follow useful relationships from coordinating organizations to the specific meal sites, pantries, benefit "
            "programs, delivery services, and specialized providers people can actually access. Verify schedules, boundaries, "
            "eligibility, and the practical intake path."
        ),
        scope=(
            "Meals available today, including community meals and emergency food",
            "Food pantries, recurring groceries, mobile distribution, and delivery",
            "SNAP, WIC, school, senior, and other benefit or nutrition pathways",
            "Dietary, disability, transportation, documentation, and service-area barriers",
            "The actual schedule, intake path, limits, and availability",
        ),
        evidence_rules=COMMON_EVIDENCE_RULES,
        stages=(
            {
                "key": "immediate-food",
                "title": "Meals and emergency food",
                "instruction": "Investigate dependable meals and emergency food available today or within days, including the actual locations, schedules, eligibility, and access steps.",
            },
            {
                "key": "pantries-groceries",
                "title": "Pantries and recurring groceries",
                "instruction": "Investigate food pantries, mobile distributions, recurring groceries, delivery, frequency limits, geographic boundaries, identification requirements, and transportation barriers.",
            },
            {
                "key": "benefits-specialized",
                "title": "Benefits and specialized access",
                "instruction": "Investigate benefit enrollment and food resources for children, families, seniors, medically vulnerable people, veterans, people leaving corrections, Spanish speakers, and others with specialized access needs.",
            },
            {
                "key": "food-gaps",
                "title": "Availability and gap review",
                "instruction": "Cross-check schedules and availability, identify geographic or time-of-day gaps, avoid repeated candidates, and pursue missing referral relationships needed for a useful review.",
            },
        ),
    ),
    "employment": CategoryPlaybook(
        category_id="employment",
        label="Employment",
        default_assignment=(
            "Discover realistic employment resources for people in Utah County who need work, better work, training, "
            "or help overcoming barriers to employment. Follow useful relationships from workforce organizations to "
            "specific placement programs, employers, training, credentials, apprenticeships, and supported-employment "
            "services. Verify costs, eligibility, schedules, and the practical enrollment path."
        ),
        scope=(
            "Immediate job search, placement, staffing, and hiring pathways",
            "Training, credentials, apprenticeships, education, and career advancement",
            "Supported employment and help with disability, reentry, language, transportation, or documentation barriers",
            "Work clothing, tools, childcare, transportation, and other employment supports",
            "The actual enrollment path, costs, schedules, placement claims, and availability",
        ),
        evidence_rules=COMMON_EVIDENCE_RULES,
        stages=(
            {
                "key": "job-access",
                "title": "Immediate job access and placement",
                "instruction": "Investigate job-search help, workforce centers, staffing and placement, current hiring pathways, and the practical steps a person can take now.",
            },
            {
                "key": "training-credentials",
                "title": "Training and credentials",
                "instruction": "Investigate short-term training, credentials, apprenticeships, education, scholarships, and career pathways, including cost, schedule, prerequisites, and likely time to benefit.",
            },
            {
                "key": "barrier-aware-employment",
                "title": "Barrier-aware and supported employment",
                "instruction": "Investigate supported employment and services addressing disability, reentry, language, age, transportation, childcare, clothing, tools, identification, and other barriers.",
            },
            {
                "key": "employment-gaps",
                "title": "Opportunity and gap review",
                "instruction": "Cross-check earlier findings, verify service boundaries and outcome claims, avoid repeated candidates, and identify important population or access gaps.",
            },
        ),
    ),
}


FOCUSED_RESEARCH_STAGE = ({
    "key": "focused-branch",
    "title": "Focused resource investigation",
    "instruction": (
        "Investigate the selected known resource deeply, follow its useful organization, program, provider, referral, "
        "and access relationships, and return only well-supported new candidates or material clarifications."
    ),
},)


def normalize_supported_category(category_id: str) -> str | None:
    wanted = str(category_id or "").strip().casefold()
    return wanted or None


def _generic_playbook(category_id: str, category_label: str) -> CategoryPlaybook:
    label = str(category_label or category_id).strip() or "Resource"
    subject = label.casefold()
    return CategoryPlaybook(
        category_id=str(category_id).strip() or subject,
        label=label,
        default_assignment=(
            f"Discover realistic {subject} resources for people in Utah County. Follow useful relationships "
            "from coordinating organizations and broad directories to the specific programs, providers, benefits, "
            "and practical services people can actually access. Verify eligibility, costs, schedules, service areas, "
            "availability, and the real intake or enrollment path."
        ),
        scope=(
            f"Immediate and direct {subject} services",
            f"Ongoing, preventive, and longer-term {subject} support",
            "Public benefits, nonprofit programs, government services, and credible private options",
            "Population-specific access and barriers involving disability, language, age, family status, documentation, transportation, cost, or referrals",
            "The actual intake path, eligibility, schedule, service area, availability, and important gaps",
        ),
        evidence_rules=COMMON_EVIDENCE_RULES,
        stages=(
            {
                "key": "direct-access",
                "title": f"Direct {label} access",
                "instruction": (
                    f"Investigate direct {subject} services a person can use now or soon. Verify the actual provider, "
                    "service, location or service area, eligibility, schedule, cost, and first access step."
                ),
            },
            {
                "key": "ongoing-support",
                "title": f"Ongoing {label} support",
                "instruction": (
                    f"Investigate ongoing, preventive, and longer-term {subject} help, including government benefits, "
                    "nonprofit programs, referrals, case management, education, and other realistic pathways."
                ),
            },
            {
                "key": "specialized-access",
                "title": "Specialized access and barriers",
                "instruction": (
                    f"Investigate {subject} resources for people facing population-specific or practical barriers. "
                    "Check disability access, language, age, family status, documentation, transportation, cost, "
                    "referral requirements, and other restrictions relevant to this category."
                ),
            },
            {
                "key": "category-gaps",
                "title": f"{label} gap review",
                "instruction": (
                    "Cross-check earlier findings, avoid repeated candidates, verify time-sensitive claims, follow useful "
                    f"provider and referral relationships, and identify geographic, population, schedule, or service gaps in {subject}."
                ),
            },
        ),
    )


def playbook_for(category_id: str, category_label: str | None = None) -> CategoryPlaybook:
    normalized = normalize_supported_category(category_id)
    if not normalized:
        raise ValueError("A research category is required")
    label_key = normalize_supported_category(category_label or "")
    if normalized in PLAYBOOKS:
        return PLAYBOOKS[normalized]
    if label_key in PLAYBOOKS:
        return PLAYBOOKS[label_key]
    return _generic_playbook(category_id, category_label or category_id)


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
            **(
                {"petPolicy": "Pets, service animals, emotional-support animals, fees, or unknown"}
                if category_label.casefold() == "housing" else {}
            ),
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
