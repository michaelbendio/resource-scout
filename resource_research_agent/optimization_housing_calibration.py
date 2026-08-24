from __future__ import annotations

"""Mesa Housing query-plan fixtures used only by calibration tooling."""

from copy import deepcopy
from typing import Any

from .optimization import (
    CANDIDATE_QUALIFICATION_POLICY_VERSION,
    branch_stop_state,
    validate_query_plan,
)


HOUSING_STAGE_KEYS = (
    "urgent-access",
    "stabilization",
    "specialized-housing",
    "long-term-and-gaps",
)


def _later_stage_specifications(
    stage_key: str, location: str, region: str
) -> tuple[tuple[str, str, tuple[str, ...]], ...]:
    if stage_key == "stabilization":
        return (
            (
                "official-local-prevention",
                "Find current city and county homelessness-prevention programs and jurisdiction rules.",
                (
                    f'site:mesaaz.gov "{location}" eviction prevention rent assistance',
                    f'site:mesaaz.gov "{location}" utility deposit housing assistance',
                    f'site:maricopa.gov "{location}" homelessness prevention program',
                    f'site:maricopa.gov "{location}" rental assistance current intake',
                    f'site:az.gov "{location}" eviction prevention housing assistance',
                    f'"{location}" government rapid rehousing diversion program',
                ),
            ),
            (
                "rent-deposit-and-utilities",
                "Find actionable rent, deposit, and utility assistance that can prevent displacement.",
                (
                    f'"{location}" current rent assistance application',
                    f'"{location}" security deposit assistance program',
                    f'"{location}" utility assistance prevent eviction',
                    f'"{location}" emergency rental assistance nonprofit intake',
                    f'"{location}" flexible funds housing stability',
                    f'"{location}" move in deposit help program',
                ),
            ),
            (
                "diversion-and-rapid-rehousing",
                "Find distinct diversion and rapid-rehousing programs with a current access path.",
                (
                    f'"{location}" homeless diversion program intake',
                    f'"{location}" rapid rehousing program current',
                    f'"{location}" homelessness prevention case management housing',
                    f'"{location}" coordinated entry rapid rehousing provider',
                    f'"{location}" family rapid rehousing program',
                    f'"{location}" veteran rapid rehousing SSVF',
                ),
            ),
            (
                "direct-stabilization-providers",
                "Find direct providers with named prevention or stabilization programs.",
                (
                    f'"{location}" nonprofit homelessness prevention intake',
                    f'"{location}" housing stability program apply',
                    f'"{location}" eviction legal assistance housing stability',
                    f'"{location}" tenant assistance program case management',
                    f'"{location}" family housing stabilization provider',
                    f'"{location}" reentry housing stabilization assistance',
                ),
            ),
            (
                "regional-serving-stabilization",
                "Find regional stabilization programs only with evidence that they serve the target.",
                (
                    f'"serves {location}" rent assistance program',
                    f'"{location} residents" eviction prevention',
                    f'"{location}" "{region}" rapid rehousing',
                    f'"{location}" East Valley housing stabilization',
                    f'"{location}" regional utility assistance intake',
                    f'"{location}" Maricopa housing prevention provider',
                ),
            ),
        )
    if stage_key == "specialized-housing":
        return (
            (
                "official-specialized-systems",
                "Find official specialized-housing programs and authoritative referral pathways.",
                (
                    f'site:mesaaz.gov "{location}" transitional supportive housing',
                    f'site:maricopa.gov "{location}" supportive housing program',
                    f'site:az.gov "{location}" specialized housing program',
                    f'211 Arizona "{location}" transitional housing',
                    f'"{location}" coordinated entry supportive housing',
                    f'"{location}" Continuum of Care specialized housing provider',
                ),
            ),
            (
                "transitional-housing",
                "Find named transitional-housing programs with current intake and population rules.",
                (
                    f'"{location}" transitional housing program intake',
                    f'"{location}" family transitional housing',
                    f'"{location}" women transitional housing program',
                    f'"{location}" men transitional housing program',
                    f'"{location}" youth transitional living program',
                    f'"{location}" bridge housing program application',
                ),
            ),
            (
                "recovery-treatment-and-medical",
                "Find recovery, treatment-linked, and medically appropriate housing without inferring restrictions.",
                (
                    f'"{location}" recovery housing program intake',
                    f'"{location}" sober living financial assistance program',
                    f'"{location}" treatment linked transitional housing',
                    f'"{location}" medical respite homeless program',
                    f'"{location}" behavioral health supportive housing intake',
                    f'"{location}" pregnant women residential housing program',
                ),
            ),
            (
                "reentry-veteran-and-disability",
                "Find population-specific programs for reentry, veterans, and people with disabilities.",
                (
                    f'"{location}" reentry transitional housing program',
                    f'"{location}" veteran transitional housing program',
                    f'"{location}" disability supportive housing program',
                    f'"{location}" accessible transitional housing',
                    f'"{location}" serious mental illness supportive housing',
                    f'"{location}" formerly incarcerated housing intake',
                ),
            ),
            (
                "safety-family-and-youth",
                "Find specialized domestic-violence, family, parenting, and youth housing beyond emergency shelter.",
                (
                    f'"{location}" domestic violence transitional housing',
                    f'"{location}" family supportive housing program',
                    f'"{location}" parenting youth housing program',
                    f'"{location}" young adult transitional living',
                    f'"{location}" trafficking survivor housing program',
                    f'"{location}" single parent transitional housing',
                ),
            ),
            (
                "regional-serving-specialized",
                "Find adjacent specialized programs only with evidence that they serve the target.",
                (
                    f'"serves {location}" transitional housing',
                    f'"{location} residents" supportive housing program',
                    f'"{location}" "{region}" recovery housing program',
                    f'"{location}" East Valley specialized housing',
                    f'"{location}" regional veteran housing program',
                    f'"{location}" regional disability housing intake',
                ),
            ),
        )
    if stage_key == "long-term-and-gaps":
        return (
            (
                "housing-authorities-and-vouchers",
                "Find housing-authority programs, exact service boundaries, vouchers, and current waitlist paths.",
                (
                    f'site:mesaaz.gov "{location}" housing authority waitlist voucher',
                    f'"{location}" Housing Choice Voucher current waitlist',
                    f'"{location}" project based voucher program',
                    f'"{location}" public housing application waitlist',
                    f'"{location}" housing authority jurisdiction service area',
                    f'"{location}" Section 8 application official',
                ),
            ),
            (
                "affordable-and-subsidized-programs",
                "Find named affordable or subsidized programs with an actual application pathway.",
                (
                    f'"{location}" affordable housing program apply',
                    f'"{location}" subsidized apartment program waitlist',
                    f'"{location}" income restricted housing application',
                    f'"{location}" low income housing tax credit property application',
                    f'"{location}" nonprofit affordable housing program',
                    f'"{location}" senior affordable housing waitlist',
                ),
            ),
            (
                "permanent-supportive-housing",
                "Find distinct permanent-supportive-housing programs and their referral requirements.",
                (
                    f'"{location}" permanent supportive housing program',
                    f'"{location}" supportive housing coordinated entry referral',
                    f'"{location}" disability permanent supportive housing',
                    f'"{location}" veteran permanent housing program',
                    f'"{location}" behavioral health permanent housing',
                    f'"{location}" chronically homeless supportive housing provider',
                ),
            ),
            (
                "rental-and-landlord-pathways",
                "Find credible landlord, unit-location, and rental-access programs rather than ordinary listings.",
                (
                    f'"{location}" housing locator program low income',
                    f'"{location}" landlord liaison housing program',
                    f'"{location}" rental access program voucher holders',
                    f'"{location}" tenant based rental assistance program',
                    f'"{location}" affordable rental referral program',
                    f'"{location}" community land trust housing program',
                ),
            ),
            (
                "permanent-pathway-gaps",
                "Cross-check missing populations, access barriers, and transitions from temporary housing.",
                (
                    f'"{location}" family permanent housing program gap',
                    f'"{location}" youth permanent housing program',
                    f'"{location}" accessible affordable housing assistance',
                    f'"{location}" Spanish housing application assistance',
                    f'"{location}" homeless pets permanent housing barrier',
                    f'"{location}" shelter to permanent housing pathway program',
                ),
            ),
            (
                "regional-serving-permanent",
                "Find regional permanent pathways only with evidence that they serve the target.",
                (
                    f'"serves {location}" permanent supportive housing',
                    f'"{location} residents" affordable housing program',
                    f'"{location}" "{region}" subsidized housing',
                    f'"{location}" East Valley permanent housing program',
                    f'"{location}" regional housing locator program',
                    f'"{location}" Maricopa permanent housing provider',
                ),
            ),
        )
    raise ValueError(f"Unsupported Housing calibration stage: {stage_key}")


def build_housing_stage_query_plan(
    target_location: str,
    regional_scope: str,
    *,
    stage_key: str,
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
    if stage_key not in HOUSING_STAGE_KEYS:
        raise ValueError(f"Unsupported Housing calibration stage: {stage_key}")
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
    ) if stage_key == "urgent-access" else _later_stage_specifications(
        stage_key, location, region
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
        "stageKey": stage_key,
        "targetLocation": location,
        "regionalScope": region,
        "branches": branches,
    }
    validate_query_plan(plan)
    return plan


def build_housing_urgent_query_plan(
    target_location: str,
    regional_scope: str,
    *,
    minimum_queries: int = 2,
    maximum_queries: int = 6,
    saturation_queries: int = 2,
) -> dict[str, Any]:
    """Compatibility wrapper preserving the frozen urgent-stage plan exactly."""

    return build_housing_stage_query_plan(
        target_location,
        regional_scope,
        stage_key="urgent-access",
        minimum_queries=minimum_queries,
        maximum_queries=maximum_queries,
        saturation_queries=saturation_queries,
    )
