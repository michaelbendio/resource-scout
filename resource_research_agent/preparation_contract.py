"""Shared five-section preparation contract for AI assignments and exports."""
from __future__ import annotations

import re
from copy import deepcopy


POLICY_VERSION = "prepared-resources-v1-five-sections"
ASSIGNMENT_VERSION = "codex-preparation-v3-reserve"
INFORMATION_HEADINGS = (
    "Services Offered", "Eligibility Requirements", "Population Served",
    "How to Best Connect", "Important Information to Know",
)
LEGACY_INFORMATION_HEADINGS = (
    "Eligibility Requirements", "How to Best Connect", "Access", "Important Information to Know",
)


def information_sections(text, headings=INFORMATION_HEADINGS):
    matches = list(re.finditer(r"^\*\*(.+?)\*\*[ \t]*$", text, re.M))
    if tuple(m[1] for m in matches) != headings or not matches or text[:matches[0].start()].strip():
        raise ValueError("Information needs the ordered standalone bold headings: " + ", ".join(headings))
    sections = {m[1]: text[m.end():matches[i+1].start() if i+1 < len(matches) else len(text)].strip()
                for i, m in enumerate(matches)}
    if any(not value for value in sections.values()):
        raise ValueError("Information has an empty section")
    return sections


def assemble_information(sections):
    result = "\n\n".join(f"**{heading}**\n\n{sections[heading].strip()}" for heading in INFORMATION_HEADINGS)
    information_sections(result)
    return result


def migrate_reviewed_information(resource, *, services, population):
    """Reformat existing reviewed facts using explicitly supplied service/population text.

    No keyword classification, eligibility inference, date invention or fact deletion.
    The caller must review services/population; old Access text is retained in full.
    """
    old = information_sections(resource["informationText"], LEGACY_INFORMATION_HEADINGS)
    return assemble_information({
        "Services Offered": services,
        "Eligibility Requirements": old["Eligibility Requirements"],
        "Population Served": population,
        "How to Best Connect": old["How to Best Connect"] + "\n\n" + old["Access"],
        "Important Information to Know": old["Important Information to Know"],
    })


def preparation_instructions():
    return [
        "Retain each distinct, supported, actionable resource, including useful reserve options. Do not minimize the collection or fill a numerical quota.",
        "Assess every candidate; explain omissions and unresolved facts. Distinguish a generic directory from a service that directly assists people with navigation or intake.",
        "Preserve specific services, eligibility, costs, hours, service area, remote access and source URLs. Broader labels must not erase search-relevant details.",
        "Write five standalone bold Information headings in this exact order: " + ", ".join(f"**{h}**" for h in INFORMATION_HEADINGS) + ". Each must have relevant text beneath it.",
        "Services Offered describes the actual help; Eligibility Requirements states qualification rules; Population Served states evidenced populations without inferring identity. Put hours, appointments, location and access limits in How to Best Connect. Important Information to Know preserves costs, conflicts and uncertainties.",
        "Reuse existing Type/group meanings where supported. Record any new population/service concept and its evidence for whole-collection review, rather than inventing a final catalog in a batch.",
        "Keep source URLs with claims. researchedAt is research timing only. verifiedOn must be null: only the office records its verification date.",
        "The output's local resource references identify draft proposals only. Code resolves final consolidated IDs through the registry before any production delivery. Never invent a production sr_ identity.",
        "AI preparation and starter selection never imply human Curated approval, agency confirmation, present capacity or guaranteed eligibility.",
    ]


def prepared_assignment(assignment):
    """New policy for a NEW assignment, never a mutation of sealed evidence."""
    result = deepcopy(assignment)
    result.pop("assignmentSha256", None)
    result["assignmentVersion"] = ASSIGNMENT_VERSION
    result["preparationPolicyVersion"] = POLICY_VERSION
    result["curationPolicy"] = {
        "objective": "Prepare every distinct supported resource for starter selection and reserve search.",
        "humanApproval": "Separate office action; no AI approval or verification date.",
    }
    result["instructions"] = preparation_instructions()
    resource = result["outputContract"]["resources"][0]
    resource.update(id="provisional proposal reference; reuse a prior draft reference only for the same program",
                    email="", researchedAt=None, sources=[], state="usable", resolutionReason="",
                    taxonomySuggestions=[])
    return result


def normalize_preparation_fields(resource):
    """Keep new evidence through the existing storage path, rejecting silent loss."""
    from .prepared_resources import valid_url
    if str(resource["id"]).startswith("sr_"):
        raise ValueError("Workers cannot allocate registry IDs")
    if resource.get("verifiedOn") is not None:
        raise ValueError("Scout cannot supply an office verification date")
    information_sections(resource.get("informationText", ""))
    if resource.get("state") not in ("usable", "needs-resolution"):
        raise ValueError("Prepared proposals need an importable state")
    if resource["state"] == "needs-resolution" and (
        not isinstance(resource.get('resolutionReason'), str) or not resource['resolutionReason'].strip()
    ):
        raise ValueError("Unresolved proposals need an explanation")
    sources = resource.get("sources")
    if not isinstance(sources, list) or not sources or any(
        not isinstance(s, dict) or not valid_url(s.get("url")) or not str(s.get("title", "")).strip()
        for s in sources
    ):
        raise ValueError("Prepared proposals need supporting source pages")
    from datetime import datetime
    if "researchedAt" not in resource:
        raise ValueError("Research date must be explicit, or null when unknown")
    if resource["researchedAt"] is not None:
        if not isinstance(resource['researchedAt'], str):
            raise ValueError('Research date must be an ISO date/time string or null')
        datetime.fromisoformat(resource["researchedAt"].replace("Z", "+00:00"))
    suggestions = resource.get("taxonomySuggestions")
    if not isinstance(suggestions, list) or any(
        not isinstance(s, dict) or s.get("kind") not in ("type", "group") or
        any(not isinstance(s.get(k), str) or not s[k].strip() for k in ("label", "definition", "evidence"))
        for s in suggestions
    ):
        raise ValueError("Taxonomy suggestions need meaning and evidence for collection review")
    if not isinstance(resource.get("email"), str):
        raise ValueError("Email must be a string, empty when unknown")
    return {key: deepcopy(resource[key]) for key in (
        "email", "researchedAt", "sources", "state", "resolutionReason", "taxonomySuggestions")}
