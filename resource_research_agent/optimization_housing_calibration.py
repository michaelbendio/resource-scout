from __future__ import annotations

"""Frozen Mesa Housing query-plan fixture used only by calibration tooling."""

from copy import deepcopy
from typing import Any

from .optimization import (
    CANDIDATE_QUALIFICATION_POLICY_VERSION,
    branch_stop_state,
    validate_query_plan,
)


def build_housing_urgent_query_plan(
    target_location: str,
    regional_scope: str,
    *,
    minimum_queries: int = 2,
    maximum_queries: int = 6,
    saturation_queries: int = 2,
) -> dict[str, Any]:
    location = " ".join(str(target_location or "").split())
    region = " ".join(str(regional_scope or "").split())
    if not location or not region:
        raise ValueError("Housing query planning requires a target location and regional scope")
    policy = {
        "minimumQueries": minimum_queries,
        "maximumQueries": maximum_queries,
        "consecutiveNoNewIdentityQueries": saturation_queries,
        "noveltyUnit": "package-eligible normalized organization-plus-program identity",
    }
    branch_stop_state(
        [],
        minimum_queries=minimum_queries,
        maximum_queries=maximum_queries,
        saturation_queries=saturation_queries,
    )
    if maximum_queries > 10:
        raise ValueError("Housing urgent query plans support at most ten queries per branch")
    specifications = (
        (
            "official-city",
            "Find city-run access points, programs, funding, jurisdiction rules, and official referrals.",
            (
                f'site:mesaaz.gov "{location}" emergency shelter homeless',
                f'site:mesaaz.gov "{location}" housing crisis assistance',
                f'site:mesaaz.gov "{location}" motel voucher temporary lodging',
                f'site:mesaaz.gov "{location}" coordinated entry homeless',
                f'site:mesaaz.gov "{location}" family youth shelter',
                f'site:mesaaz.gov "{location}" pets shelter transportation homeless',
                f'site:mesaaz.gov "{location}" homeless resource line outreach services',
                f'site:mesaaz.gov "{location}" emergency shelter program intake phone',
                f'site:mesaaz.gov "{location}" homeless services provider partnership',
                f'site:mesaaz.gov "{location}" emergency housing referral program',
            ),
        ),
        (
            "official-county",
            "Find county programs and record whether their jurisdiction includes the target city.",
            (
                f'site:maricopa.gov "{location}" emergency housing',
                f'site:maricopa.gov "{location}" homeless shelter',
                f'site:maricopa.gov "{location}" coordinated entry',
                f'site:maricopa.gov "{location}" motel voucher',
                f'site:maricopa.gov "{location}" family shelter',
                f'site:maricopa.gov "{location}" housing authority service area',
                f'site:maricopa.gov "{location}" homeless services named program',
                f'site:maricopa.gov "{location}" coordinated entry provider',
                f'site:maricopa.gov "East Valley" emergency shelter program',
                f'site:maricopa.gov "{location}" homeless navigation access',
            ),
        ),
        (
            "official-state",
            "Find state-administered programs and authoritative statewide referral paths serving the target.",
            (
                f'site:az.gov "{location}" emergency housing homeless',
                f'site:az.gov "{location}" shelter services',
                f'site:az.gov "{location}" domestic violence shelter housing',
                f'site:az.gov "{location}" youth shelter',
                f'site:az.gov "{location}" veteran emergency housing',
                f'site:az.gov "{location}" temporary lodging assistance',
                f'site:az.gov "{location}" homeless services provider program',
                f'site:az.gov "{location}" coordinated entry provider',
                f'site:az.gov "East Valley" emergency shelter program',
                f'site:az.gov "{location}" family housing hub',
            ),
        ),
        (
            "coordinated-entry-and-211",
            "Trace coordinated entry and authoritative referral results to specific named programs.",
            (
                f'211 Arizona "{location}" emergency shelter',
                f'"{location}" coordinated entry homeless access point',
                f'211 Arizona "{location}" family shelter',
                f'211 Arizona "{location}" domestic violence shelter',
                f'211 Arizona "{location}" youth shelter',
                f'211 Arizona "{location}" motel voucher',
                f'"{location}" "Family Housing Hub" shelter',
                f'"{location}" "Keys to Change" coordinated entry',
                f'"{location}" CASS shelter intake',
                f'Maricopa Regional Continuum of Care "{location}" coordinated entry get help',
            ),
        ),
        (
            "direct-providers",
            "Find direct providers and specific emergency programs with an actionable intake path.",
            (
                f'"{location}" emergency shelter intake',
                f'"{location}" homeless shelter program apply',
                f'"{location}" temporary housing direct provider',
                f'"{location}" emergency lodging homeless program',
                f'"{location}" shelter hotline intake hours',
                f'"{location}" crisis housing nonprofit',
                f'"{location}" "East Valley" shelter provider intake',
                f'"{location}" named homeless outreach program phone',
                f'"{location}" family housing hub intake provider',
                f'"{location}" emergency shelter access point nonprofit',
            ),
        ),
        (
            "specialized-safety",
            "Cover domestic-violence, family, youth, medically vulnerable, and other specialized safety paths.",
            (
                f'"{location}" domestic violence emergency shelter',
                f'"{location}" family emergency shelter children',
                f'"{location}" youth emergency shelter',
                f'"{location}" senior older adults medically vulnerable homeless day center shelter',
                f'"{location}" veteran emergency shelter',
                f'"{location}" disability accessible emergency housing',
                f'"{location}" pregnant women emergency shelter',
                f'"{location}" reentry emergency housing program',
                f'"{location}" recovery housing immediate placement',
                f'"{location}" medical respite homeless housing',
            ),
        ),
        (
            "temporary-lodging",
            "Identify voucher issuers and the specific temporary lodging or bridge programs they use.",
            (
                f'"{location}" motel voucher homeless',
                f'"{location}" hotel voucher emergency housing',
                f'"{location}" emergency lodging voucher program',
                f'"{location}" Salvation Army Phoenix emergency family shelter intake',
                f'"{location}" family motel assistance',
                f'"{location}" shelter overflow hotel program',
                f'"{location}" I-HELP emergency lodging',
                f'"{location}" hotel shelter placement program',
                f'"{location}" bridge housing temporary lodging',
                f'"{location}" Catholic Charities emergency housing',
            ),
        ),
        (
            "regional-serving-target",
            "Find adjacent regional programs only when a source explicitly states that they serve the target.",
            (
                f'"serves {location}" emergency shelter',
                f'"{location} residents" homeless housing program',
                f'"{location}" "{region}" emergency housing',
                f'"{location}" regional shelter intake',
                f'"{location}" Phoenix shelter transportation',
                f'"{location}" East Valley emergency shelter',
                f'"{location}" UMOM shelter intake',
                f'"{location}" A New Leaf shelter placement',
                f'"{location}" CASS emergency shelter eligibility',
                f'"{location}" East Valley family shelter intake',
            ),
        ),
        (
            "access-barriers",
            "Verify transportation, pet, documentation, family-composition, sobriety, and referral barriers.",
            (
                f'"{location}" homeless shelter pets',
                f'"{location}" shelter transportation intake',
                f'"{location}" low barrier shelter identification',
                f'"{location}" family shelter eligibility referral',
                f'"{location}" shelter sobriety requirements',
                f'"{location}" service animals emergency shelter',
                f'"{location}" shelter couples together',
                f'"{location}" shelter no identification required',
                f'"{location}" wheelchair accessible homeless shelter',
                f'"{location}" Lost Our Home temporary care shelter barrier',
            ),
        ),
    )
    branches = []
    for branch_key, purpose, query_texts in specifications:
        branches.append(
            {
                "key": branch_key,
                "purpose": purpose,
                "required": True,
                "saturation": deepcopy(policy),
                "queries": [
                    {
                        "key": f"{branch_key}-{position}",
                        "position": position,
                        "purpose": purpose,
                        "query": query,
                    }
                    for position, query in enumerate(
                        query_texts[:maximum_queries], start=1
                    )
                ],
            }
        )
    plan = {
        "schemaVersion": 4,
        "candidateQualificationPolicyVersion": CANDIDATE_QUALIFICATION_POLICY_VERSION,
        "categoryId": "housing",
        "stageKey": "urgent-access",
        "targetLocation": location,
        "regionalScope": region,
        "branches": branches,
    }
    validate_query_plan(plan)
    return plan
