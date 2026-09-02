from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from copy import deepcopy
from typing import Any

from .storage import ResearchStore
from .taxonomy_study import TaxonomyStudyError
from .taxonomy_types import taxonomy_types_status


GROUP_REVIEW_RULES = {
    "definition": (
        "A For group records a population a resource explicitly targets or "
        "meaningfully accommodates. It does not replace the need Category or "
        "describe the service method."
    ),
    "modes": {
        "target": (
            "The population is part of the resource's stated eligibility, mission, "
            "program identity, or dedicated service track."
        ),
        "accommodate": (
            "The resource is broadly available but provides a concrete language, "
            "accessibility, cultural, safety, or logistical accommodation."
        ),
    },
    "evidence": [
        "Use explicit resource text, an existing For assignment, or a retired population-shaped Category.",
        "Do not infer identity from a provider name, neighborhood, diagnosis, or universal availability alone.",
        "Spanish-language access supports the Spanish group; it does not by itself support Hispanic/Latino.",
        "A referral to another organization does not prove the referring resource targets that population.",
        "When the evidence establishes a need but not a population, use no-group-needed rather than guessing.",
    ],
    "combination": (
        "Selected Groups are ORed. When a Category is open, the selected Types are "
        "ORed and the Type result is ANDed with the Group result."
    ),
}


GROUP_CATALOG: list[dict[str, Any]] = [
    {"id": "seniors", "label": "Seniors", "definition": "Older adults, including programs using a stated age threshold."},
    {"id": "veterans", "label": "Veterans", "definition": "Veterans, service members, and military-connected households when expressly included."},
    {"id": "exiting-corrections", "label": "Re-entry", "definition": "People preparing to leave or returning from jail, prison, probation, or parole."},
    {"id": "pregnant-postpartum", "label": "Pregnant/postpartum", "definition": "People who are pregnant, recently gave birth, or need postpartum support."},
    {"id": "families-with-children", "label": "Families", "definition": "Parents, guardians, or households caring for minor children."},
    {"id": "people-with-disabilities", "label": "Disabled", "definition": "People with physical, sensory, intellectual, developmental, or other disabilities."},
    {"id": "youth-young-adults", "label": "Youth", "definition": "Adolescents and transition-age young adults in a dedicated program."},
    {"id": "women", "label": "Women", "definition": "Programs expressly designed for or limited to women."},
    {"id": "men", "label": "Men", "definition": "Programs expressly designed for or limited to men."},
    {"id": "lgbtq", "label": "LGBTQ+", "definition": "LGBTQ+, transgender, queer, or gender-diverse people."},
    {"id": "spanish-speaking", "label": "Spanish", "definition": "People who can use a documented Spanish-language service or access path."},
    {"id": "immigrants", "label": "Immigrants", "definition": "Immigrants, refugees, asylees, humanitarian parolees, and people seeking or maintaining immigration status."},
    {"id": "native-american", "label": "Native American", "definition": "Native American, American Indian, Alaska Native, or tribal communities."},
    {"id": "experiencing-homelessness", "label": "Homeless", "definition": "People who are unsheltered, in shelter, or otherwise experiencing homelessness."},
    {"id": "domestic-violence-survivors", "label": "Domestic violence survivors", "definition": "People experiencing or surviving domestic, dating, or partner abuse."},
    {"id": "low-income", "label": "Low-income households", "definition": "People whose income or poverty level is an explicit eligibility or service focus."},
    {"id": "uninsured-underinsured", "label": "Uninsured/underinsured", "definition": "People without adequate health coverage who have a documented access pathway."},
    {"id": "people-with-pets", "label": "Pet owners", "definition": "People whose pets are expressly welcomed, sheltered, or accommodated."},
    {"id": "medically-vulnerable", "label": "Medically vulnerable", "definition": "People whose serious health condition creates a documented specialized access need."},
]


_PRIOR_GROUPS = {
    "Exiting corrections": ("exiting-corrections", "target"),
    "Families with children": ("families-with-children", "target"),
    "Medically vulnerable": ("medically-vulnerable", "target"),
    "Seniors": ("seniors", "target"),
    "Spanish speaking": ("spanish-speaking", "accommodate"),
    "Spanish-speaking": ("spanish-speaking", "accommodate"),
    "Veterans": ("veterans", "target"),
    "Women": ("women", "target"),
}


_LEGACY_CATEGORY_GROUPS = {
    "seniors": "seniors",
    "veterans": "veterans",
    "reentry-support": "exiting-corrections",
}


_NEED_CATEGORY_GROUPS = {
    "domestic-violence": "domestic-violence-survivors",
    "homeless-services": "experiencing-homelessness",
    "immigration": "immigrants",
    "parenting-child-development": "families-with-children",
}


_PATTERNS: dict[str, dict[str, tuple[str, ...]]] = {
    "seniors": {
        "target": (r"\bseniors?\b", r"\bolder adults?\b", r"\badults? (?:age|ages) (?:50|55|60|62|65)(?:\+| and older)"),
    },
    "veterans": {"target": (r"\bveterans?\b", r"\bservice members?\b", r"\bmilitary families\b")},
    "exiting-corrections": {"target": (r"\breentry\b", r"\bre-entry\b", r"\breturning from incarceration\b", r"\bpost-release\b", r"\bpre-release\b", r"\bjustice-involved\b", r"\bformerly incarcerated\b")},
    "pregnant-postpartum": {"target": (r"\bpregnan(?:t|cy)\b", r"\bpostpartum\b", r"\bprenatal\b", r"\bmaternity\b", r"\bmaternal\b")},
    "families-with-children": {"target": (r"\bfamilies with (?:minor )?children\b", r"\bparents? and children\b", r"\bparenting families\b", r"\bchildren and families\b", r"\b(?:foster|kinship) (?:families|caregivers)\b")},
    "people-with-disabilities": {"target": (r"\bpeople with disabilities\b", r"\badults? with disabilities\b", r"\bdevelopmental disabilities\b", r"\bintellectual disabilities\b", r"\bdisability-specific\b", r"\bdeafblind\b", r"\bdeaf(?:,| and|/) hard of hearing\b", r"\bhard-of-hearing\b", r"\bdeaf survivors?\b", r"\bblind/low-vision\b", r"\bblind and visually impaired\b", r"\bblind or low vision\b", r"\blow-vision\b", r"\bvision loss\b")},
    "youth-young-adults": {"target": (r"\byouth(?:s)?\b", r"\byoung adults?\b", r"\bteens?\b", r"\badolescents?\b", r"\bages? 1[2-9][–-](?:2[0-5]|19)\b")},
    "women": {"target": (r"\bwomen-only\b", r"\bfor women\b", r"\bwomen's (?:center|program|services|housing|shelter|recovery)\b")},
    "men": {"target": (r"\bmen-only\b", r"\bfor men\b", r"\bmen's (?:center|program|services|housing|shelter|recovery)\b")},
    "lgbtq": {"target": (r"\blgbtq\+?\b", r"\btransgender\b", r"\bgender-diverse\b", r"\bqueer\b", r"\btwo-spirit\b")},
    "spanish-speaking": {"accommodate": (r"\bspanish\b",)},
    "immigrants": {"target": (r"\bimmigrants?\b", r"\bimmigration legal\b", r"\bnaturalization\b", r"\brefugees?\b", r"\basylees?\b", r"\bhumanitarian migrants?\b", r"\bnewly arrived humanitarian\b")},
    "native-american": {"target": (r"\bnative american\b", r"\bamerican indian\b", r"\burban indian\b", r"\btribal communities\b")},
    "experiencing-homelessness": {"target": (r"\bpeople experiencing homelessness\b", r"\bpeople who are homeless\b", r"\bhomeless (?:adults|families|youth|seniors|veterans|people)\b", r"\bunsheltered\b", r"\brunaway youth\b")},
    "domestic-violence-survivors": {"target": (r"\bdomestic violence\b", r"\bpartner abuse\b", r"\bintimate partner violence\b")},
    "low-income": {"target": (r"\blow-income\b", r"\bincome-qualified\b", r"\bat or below \d+% (?:fpl|ami)\b", r"\bpoverty level\b")},
    "uninsured-underinsured": {"accommodate": (r"\buninsured(?: and| or|/) underinsured\b", r"\bfor uninsured patients\b", r"\buninsured people\b", r"\bsliding[- ]fee\b")},
    "people-with-pets": {"accommodate": (r"\bpet-friendly\b", r"\bpets? (?:are )?(?:welcome|welcomed|allowed)\b", r"\bpet companion\b", r"\bboard pets\b")},
    "medically-vulnerable": {"target": (r"\bmedically vulnerable\b", r"\btoo sick or injured to recover on the street\b", r"\bcomplex medical conditions\b")},
}


_HIERARCHY: dict[str, str] = {}


# Every inherited label that the deterministic rules cannot independently
# support is reviewed against the frozen corpus.  These decisions change only
# the proposal: production package labels remain untouched until Michael
# approves the study.
_EXISTING_GROUP_REVIEW: dict[tuple[str, str], tuple[str, str, str]] = {
    # Exiting corrections
    ("automesa-curated:ac64a1ee6e7d4f2563ae162bd0a12e9d", "exiting-corrections"):
        ("remove", "target", "The immigration and refugee programs contain no corrections or reentry pathway."),
    ("automesa-curated:6ce0d0fd810d670dae505e267ea6e01a", "exiting-corrections"):
        ("keep", "target", "Hope Closet is limited to youth involved with Juvenile Probation and their families."),

    # Families with children
    ("automesa-curated:33b8cbd29cf68ac3a07e0fd8d984771b", "families-with-children"):
        ("keep", "target", "The Mesa clinic directly provides pediatrics and WIC services for families with infants and young children."),
    ("automesa-curated:eb94f24384f8e51a2b237d7d8c507948", "families-with-children"):
        ("keep", "target", "The DDD and caregiver pathways directly support children with developmental disabilities and their families."),
    ("automesa-curated:193621d2449346f5eb4f3fe57535ad47", "families-with-children"):
        ("keep", "target", "Arouet expressly serves justice-impacted women and their families even though a direct Parenting service remains unverified."),
    ("automesa-curated:7f314bc451d77d01f553d4527407d06d", "families-with-children"):
        ("remove", "target", "The employment resource serves adult job seekers without a family-with-children pathway."),
    ("automesa-curated:302a889f3d615bd6ab350588df7c39e9", "families-with-children"):
        ("remove", "target", "Childcare is one possible expense, not population eligibility or a family accommodation."),
    ("automesa-curated:a90b957439ba736a20a0eb129322891e", "families-with-children"):
        ("remove", "target", "The reentry resource has no family-with-children service track."),
    ("automesa-curated:855aea5e0d3d3b07f11e7bb81212e4d2", "families-with-children"):
        ("remove", "target", "Pregnancy eligibility supports Pregnant/postpartum, not Families with children by itself."),
    ("automesa-curated:86255417090cba31f14b0d7e9334d157", "families-with-children"):
        ("keep", "target", "Weldon House and related recovery services expressly support parenting women."),
    ("automesa-curated:34dc7c352ceb97ec5831aaa7cb4d3904", "families-with-children"):
        ("remove", "target", "A pregnancy/postpartum support group does not require or specifically serve a family with children."),
    ("automesa-curated:0474f03b486642977ecad2860ffac719", "families-with-children"):
        ("remove", "target", "Maternity and pregnancy-loss services support Pregnant/postpartum without proving a family-with-children track."),
    ("automesa-curated:18462adf6dd0d47ac76fba2161b70dfc", "families-with-children"):
        ("remove", "target", "The clinic's documented population is high-risk pregnancy, not families with children generally."),
    ("automesa-curated:5b3220f8a547f64ec5b3171b0af3217e", "families-with-children"):
        ("keep", "accommodate", "The workforce program documents childcare support for low-income job seekers."),
    ("automesa-curated:6aa599e3a9f6ce52dd0a27bc6e625fd2", "families-with-children"):
        ("keep", "target", "Center for Hope is a dedicated residential pathway for pregnant and parenting women."),
    ("automesa-curated:c8f5de50d9d41ce30ec0b8b6ef45b249", "families-with-children"):
        ("keep", "target", "The legal-aid resource expressly covers parenting time, child support, and related family-law matters."),
    ("automesa-curated:fbd7ac5640a1ad45864261484e2bcbf0", "families-with-children"):
        ("keep", "target", "The resource is purpose-built for foster and kinship children and their caregiving households."),
    ("automesa-curated:8f5bf98773af65b68a2a025cff1b0d59", "families-with-children"):
        ("remove", "target", "Pregnancy/infant-loss support does not establish current family-with-children eligibility."),
    ("automesa-curated:e8ecc3d007c722810d2f5ada79c32e6b", "families-with-children"):
        ("keep", "target", "The named Child and Family Program serves children and families in home and community settings."),
    ("automesa-curated:cce4f2f7537a93ea0f58d524dc2dd818", "families-with-children"):
        ("keep", "accommodate", "Childcare is documented for the in-person education classes."),
    ("automesa-curated:ce0a9cdfa73bbb3fdafb2603d8099f40", "families-with-children"):
        ("remove", "target", "Pregnancy/infant-loss support does not establish current family-with-children eligibility."),
    ("automesa-curated:47ea38f7dcac87504d34a3e7d2866f21", "families-with-children"):
        ("keep", "target", "WIC expressly serves infants and children under five as well as pregnant/postpartum participants."),
    ("automesa-curated:111bbc8293126891b0ecef093e94874c", "families-with-children"):
        ("remove", "target", "The documented referral is prenatal and women's health; pediatrics alone does not make it a family pathway."),
    ("automesa-curated:cfddfe7aec2aa52de1a56c0d3d797d9e", "families-with-children"):
        ("remove", "target", "Pregnant/postpartum recovery programming does not by itself establish a family-with-children pathway."),
    ("automesa-curated:1ed078050fc55c8c0fba211d3b8e8c0e", "families-with-children"):
        ("remove", "target", "Pregnancy-specific addiction treatment supports Pregnant/postpartum, not Families with children by itself."),
    ("automesa-curated:ed0745322850d01341f8baf07c69f0a0", "families-with-children"):
        ("keep", "target", "The shelter expressly serves survivors with children and provides childcare."),
    ("automesa-curated:626aab0a5b4c6dcd7811605470690fc3", "families-with-children"):
        ("keep", "target", "The shelter and transitional-housing programs expressly include children and onsite childcare."),
    ("automesa-curated:697d063e4304130741aed2b8ab5fc48f", "families-with-children"):
        ("keep", "target", "The legal pathway expressly covers parenting time and legal decision-making."),

    # Medically vulnerable
    ("connected-package:6b2d7fcadeec59dea6cd835e732ef55f", "medically-vulnerable"):
        ("remove", "target", "Serious mental illness and integrated treatment do not by themselves establish a specialized medically vulnerable access pathway."),
    ("connected-package:446d7aeaa7a45f7bab5d72f34d1b10e3", "medically-vulnerable"):
        ("remove", "target", "General substance-use treatment and insurance access do not establish medically vulnerable eligibility."),

    # Seniors
    ("automesa-curated:95aabc4180655feea072d1fcba13461c", "seniors"):
        ("remove", "target", "Disability employment services do not establish an older-adult pathway."),
    ("automesa-curated:a121b7ac06dc9b9ef503e462d5cffdd8", "seniors"):
        ("remove", "target", "Disability and youth programs do not establish an older-adult pathway."),
    ("automesa-curated:c98efcff0bd197bbec30e22139820e7a", "seniors"):
        ("remove", "target", "Disability travel training does not establish an older-adult pathway."),
    ("automesa-curated:d6de881b1d1c0d17801cfcc7e6614ffd", "seniors"):
        ("remove", "target", "A disability equipment loan closet does not establish an older-adult pathway."),
    ("automesa-curated:b684b97f8e67ea1cb39778d953a2c4cf", "seniors"):
        ("keep", "accommodate", "The ID-card program documents a free-card pathway for people age 65 or older."),
    ("automesa-curated:e65a5ab33ccf6b355ca9b21969c6617e", "seniors"):
        ("remove", "target", "The utility-assistance description has no older-adult eligibility or accommodation."),
    ("automesa-curated:4a4a619b7b63a00120d7f6c7391caabd", "seniors"):
        ("remove", "target", "Homeless-specific identification help has no older-adult pathway."),
    ("automesa-curated:c9a6d961fc20217b2875637b5fef2cb6", "seniors"):
        ("remove", "target", "General homeless navigation has no older-adult pathway."),
    ("connected-package:6b2d7fcadeec59dea6cd835e732ef55f", "seniors"):
        ("remove", "target", "Medicare acceptance does not establish an older-adult service track."),
    ("automesa-curated:a4e45e62c0b9cb505d5b4874340871fb", "seniors"):
        ("remove", "target", "Reentry and probation services have no older-adult pathway."),
    ("automesa-curated:8f69d21d4d0d04de3adeae58d4890d6c", "seniors"):
        ("remove", "target", "Medicaid NEMT has no older-adult eligibility or accommodation."),
    ("automesa-curated:08a26b747ffe8b1ea284e491a62d39e7", "seniors"):
        ("remove", "target", "General homeless services have no older-adult pathway."),
    ("automesa-curated:9674f1a708712c74c41c9d591821a356", "seniors"):
        ("remove", "target", "General food services have no older-adult pathway."),

    # Spanish
    ("automesa-curated:220a1f02f8cd1658a7e7cd4b8e2906aa", "spanish-speaking"):
        ("remove", "accommodate", "The frozen resource record documents no Spanish-language access path."),

    # Veterans
    ("automesa-curated:db2e8f3b8772791cf254fb9cc04b9838", "veterans"):
        ("remove", "target", "The survivor-housing resource has no veteran-specific pathway."),
    ("automesa-curated:f95aad04c5e72f66f324d9875d7caffd", "veterans"):
        ("remove", "target", "The frozen workforce record does not document veteran priority or a veteran-specific track."),
    ("automesa-curated:51cfce1c2944ef0453c793aba1923e08", "veterans"):
        ("keep", "target", "The housing authority expressly administers HUD-VASH veteran housing assistance."),
    ("automesa-curated:c922c1358349b26864bc1c2f50341b2c", "veterans"):
        ("keep", "target", "The housing authority expressly administers HUD-VASH veteran housing assistance."),

    # Women
    ("automesa-curated:855aea5e0d3d3b07f11e7bb81212e4d2", "women"):
        ("remove", "target", "Pregnancy eligibility supports Pregnant/postpartum without making a general Women group useful."),
    ("automesa-curated:1ed84b657420da445ac082991959b3f8", "women"):
        ("remove", "target", "A pregnancy component does not make the broader family resource a women-specific program."),
    ("connected-package:349f6314644d54f9964a53688887cc47", "women"):
        ("keep", "target", "Crossroads documents a women-specific residential campus."),
    ("automesa-curated:0df6bb236d8c7bf168ce4867dc83360e", "women"):
        ("keep", "target", "Maggie's Place housing is expressly limited to homeless pregnant women."),
    ("automesa-curated:ec74c1192ef14f1debb3a31c912a1bbc", "women"):
        ("remove", "target", "Maternal and family supports are represented by Pregnant/postpartum and Families with children, not Women generally."),
    ("automesa-curated:c44c60fb8e5cd640a4e7725286380d5c", "women"):
        ("remove", "target", "Early-childhood education has no women-specific pathway."),
    ("automesa-curated:220a1f02f8cd1658a7e7cd4b8e2906aa", "women"):
        ("remove", "target", "Pregnancy home visiting is represented by Pregnant/postpartum, not Women generally."),
}


# Focused second-pass decisions for misleading text matches and for concrete
# accommodations whose mode cannot be expressed safely by a broad regex.
_INFERRED_GROUP_REVIEW: dict[tuple[str, str], tuple[str, str, str]] = {
    ("automesa-curated:debb9e4a689060f00162da9ac2f8063b", "people-with-disabilities"):
        ("keep", "target", "The adult-day program expressly serves younger adults with disabilities as well as older adults."),
    ("automesa-curated:df1db0951c8ad7dd0bcc0ec05a41b169", "people-with-disabilities"):
        ("keep", "target", "SAIL expressly serves adults age 18 or older with diagnosed physical disabilities."),
    ("automesa-curated:b41ef2cfadba3f4bedf490af52f17362", "people-with-disabilities"):
        ("keep", "target", "The adult-day program is designed for people with cognitive or physical impairments including dementia, Parkinson's, stroke effects, and traumatic brain injury."),
    ("automesa-curated:6aa599e3a9f6ce52dd0a27bc6e625fd2", "men"):
        ("remove", "target", "The men's-center wording is a warning about a different co-located provider, not a CBI program."),
    ("automesa-curated:c399be50023b7d9bbbd54bbdea6b4b5f", "domestic-violence-survivors"):
        ("remove", "target", "The domestic-violence wording describes another provider and does not establish this resource's eligibility."),
    ("automesa-curated:ebac95249761b88323fc73b4e26259fd", "domestic-violence-survivors"):
        ("remove", "target", "One illustrative survivor story does not establish a survivor-specific access pathway."),
    ("automesa-curated:1e0e0a4f5d91fe1401e3730594313ad7", "seniors"):
        ("remove", "target", "Availability across the lifespan does not establish an older-adult target or accommodation."),
    ("automesa-curated:76659e8b276782e5713d685b43231655", "seniors"):
        ("remove", "target", "A historical statement about diverse clients does not establish a current older-adult pathway."),
    ("automesa-curated:b8974853db6587c88187211e9eb32960", "youth-young-adults"):
        ("remove", "target", "The record speculates that older youth could use the general bicycle program; it is not a youth pathway."),
    ("automesa-curated:1ed84b657420da445ac082991959b3f8", "youth-young-adults"):
        ("remove", "target", "Parenting-teens course content and early-childhood services do not create a youth/young-adult client pathway."),
    ("automesa-curated:b684b97f8e67ea1cb39778d953a2c4cf", "seniors"):
        ("keep", "accommodate", "The general ID-card service has a documented free-card pathway for people age 65 or older."),
    ("automesa-curated:b684b97f8e67ea1cb39778d953a2c4cf", "veterans"):
        ("keep", "accommodate", "The general ID-card service has a documented fee waiver for qualifying homeless veterans."),
    ("automesa-curated:b684b97f8e67ea1cb39778d953a2c4cf", "youth-young-adults"):
        ("keep", "accommodate", "The general ID-card service has a documented free-card pathway for youth in DCS custody."),
    ("automesa-curated:b684b97f8e67ea1cb39778d953a2c4cf", "people-with-disabilities"):
        ("keep", "accommodate", "The general ID-card service has a documented free-card pathway for qualifying SSI recipients."),
    ("automesa-curated:b684b97f8e67ea1cb39778d953a2c4cf", "experiencing-homelessness"):
        ("keep", "accommodate", "The general ID-card service has a documented fee waiver for people experiencing homelessness."),
    ("automesa-curated:d8a0a0095b59cb2e7bceb2cffbd239e5", "seniors"):
        ("keep", "accommodate", "The general transit system documents a discounted fare for riders age 65 or older."),
    ("automesa-curated:d8a0a0095b59cb2e7bceb2cffbd239e5", "people-with-disabilities"):
        ("keep", "accommodate", "The general transit system documents discounted fares and accessibility for riders with disabilities."),
    ("automesa-curated:d8a0a0095b59cb2e7bceb2cffbd239e5", "youth-young-adults"):
        ("keep", "accommodate", "The general transit system documents a discounted fare for riders ages 6-18."),
    ("automesa-curated:78410d1265bcc4f89c056a7d624434f8", "veterans"):
        ("keep", "accommodate", "The general men's shelter documents veteran-resource navigation rather than veteran-only eligibility."),
    ("automesa-curated:b8ca7f8d2eab81113b10c1a8835f0817", "domestic-violence-survivors"):
        ("keep", "accommodate", "The general family-housing program expressly includes households affected by domestic violence."),
    ("automesa-curated:8b0cbd343a20dc0118ec3fa8c9a17d1f", "medically-vulnerable"):
        ("keep", "accommodate", "The general utility provides a specialized medical-equipment and medical-vulnerability access pathway."),
    ("automesa-curated:f76b64043d73b489d7067d9f9d856b42", "lgbtq"):
        ("remove", "accommodate", "LGBTQ+ appears only in a verify-before-referral question; the frozen record does not establish a current LGBTQ+ access path."),
    ("automesa-curated:f76b64043d73b489d7067d9f9d856b42", "men"):
        ("remove", "target", "Men appear only in a verify-before-referral question; the frozen record does not establish a current men's access path."),
    ("automesa-curated:b666b49c655c08750bdf54de800e82af", "women"):
        ("remove", "target", "Chrysalis documents service for women, children, and men rather than a women-specific pathway."),
    ("automesa-curated:b666b49c655c08750bdf54de800e82af", "families-with-children"):
        ("keep", "target", "Chrysalis documents family shelter and child services as a direct service pathway."),
    ("automesa-curated:7edc59ef2bb7bef8e25a7d32fd382159", "native-american"):
        ("keep", "accommodate", "The broader mobile-advocacy program expressly extends service into rural and tribal communities."),
    ("automesa-curated:5add8558737e9cfc392878fce4cca308", "native-american"):
        ("keep", "accommodate", "The broadly available food and WIC services are delivered through a Native and urban Indian health organization."),
    ("automesa-curated:d633e161d87ac6cf94df2a2a6b877ab1", "exiting-corrections"):
        ("keep", "accommodate", "The adult-education program is reentry-aware and probation-connected but expressly open to both probationers and the general public."),
    ("automesa-curated:212ecd27650ff9a74102bc122a331934", "experiencing-homelessness"):
        ("keep", "target", "The immigration legal service explicitly prioritizes people experiencing homelessness as part of its vulnerable-client focus."),
    ("automesa-curated:34603fb44974ece7329a1a2d8ca51f35", "low-income"):
        ("remove", "target", "The low-income wording says the IRC is not a general low-income court-defense clinic; it does not establish low-income eligibility or a dedicated pathway."),
    ("automesa-curated:4b42cc9c9bed01788a1fdbfe29248adf", "domestic-violence-survivors"):
        ("keep", "target", "The dedicated humanitarian docket expressly includes VAWA relief for survivors of domestic abuse."),
    ("automesa-curated:89b9bdda24c8a5abd783f15e99dba056", "domestic-violence-survivors"):
        ("keep", "target", "The immigration legal program expressly offers VAWA relief for survivors of domestic abuse."),
    ("automesa-curated:3695184e8d514e52029ab65c18e53728", "domestic-violence-survivors"):
        ("keep", "target", "The immigration program expressly offers VAWA help for survivors of domestic abuse."),
    ("automesa-curated:4465e68f2478923dfe880de0556150f0", "domestic-violence-survivors"):
        ("keep", "target", "The Mesa immigration clinic expressly offers VAWA help for survivors of domestic abuse."),
    ("automesa-curated:b9950394defba173a07461ac5fa19e67", "domestic-violence-survivors"):
        ("keep", "target", "The immigration program expressly offers VAWA help for survivors of domestic abuse."),
    ("automesa-curated:212ecd27650ff9a74102bc122a331934", "domestic-violence-survivors"):
        ("keep", "target", "The immigration representation program expressly includes VAWA matters for survivors of domestic abuse."),
    ("automesa-curated:370e7f0a4f6a63fedd476ff9cc1bfb32", "youth-young-adults"):
        ("keep", "target", "The dedicated Children's Program serves unaccompanied immigrant children in detention and qualifying children released into Arizona communities."),
    ("automesa-curated:15507c56e359f505d8f574491c7962ac", "experiencing-homelessness"):
        ("remove", "target", "The pantry record confirms service for seniors and veterans but expressly leaves homeless eligibility uncertain."),
    ("automesa-curated:617d4be1951f67468b5ddffdb2f670f5", "experiencing-homelessness"):
        ("remove", "target", "The reentry housing track serves people at risk of homelessness; the record does not establish service while homeless."),
    ("automesa-curated:33560faa0e326f7d9f179cfc8f356488", "seniors"):
        ("keep", "accommodate", "The broader volunteer transportation program expressly serves older adults as well as other community members."),
    ("automesa-curated:fa0719b16ad0843652d8175fb792ca87", "seniors"):
        ("keep", "accommodate", "The general utility provides a documented limited-income senior water-rate discount."),
    ("automesa-curated:bcc694b6232b6b88cd40c57d3052f4ca", "seniors"):
        ("remove", "target", "Senior Services and Community Resilience is the administering division's name; the general assistance program documents no senior eligibility or pathway."),
    ("automesa-curated:138a8c6f2c950488f75f8766e2ef6252", "veterans"):
        ("keep", "accommodate", "The general legal clinic includes veterans' issues among its consultation subjects but has no dedicated veteran clinic or eligibility pathway."),
    ("automesa-curated:f76b64043d73b489d7067d9f9d856b42", "spanish-speaking"):
        ("keep", "target", "The domestic-violence resource expressly offers a named Spanish-language service rather than only a general language-access path."),
    ("automesa-curated:38629d0e712141f7531b4cff4b0bfd53", "spanish-speaking"):
        ("keep", "target", "The caregiver resource offers a dedicated Spanish-language support group rather than only general bilingual access."),
    ("automesa-curated:ce14bd1aa42c212343ff01bdda80381e", "domestic-violence-survivors"):
        ("remove", "target", "The elder-affairs record documents elder abuse and exploitation generally but no domestic- or partner-abuse service."),
    ("automesa-curated:b47b61d084512681adb9c7ccacf2268c", "domestic-violence-survivors"):
        ("remove", "target", "The adult-protective-services record documents abuse and unsafe caregiving generally but no domestic- or partner-abuse service."),
    ("automesa-curated:442b7ced0e864db023bebfb05ecc9870", "domestic-violence-survivors"):
        ("keep", "accommodate", "The general furniture bank accepts agency referrals involving domestic violence among several transition circumstances."),
    ("automesa-curated:ea77fba8e182ba83a7f60438bece546b", "youth-young-adults"):
        ("keep", "accommodate", "The general addiction intensive-outpatient program serves adolescents and adults without documenting a dedicated youth track."),
    ("automesa-curated:7de41696b045cd6fdb9bb5c25cf7c53f", "youth-young-adults"):
        ("keep", "accommodate", "The general reentry program serves previously incarcerated youth and adults without documenting a dedicated youth track."),
    ("automesa-curated:00cca473db91285a4a393f5ba53add8f", "youth-young-adults"):
        ("keep", "accommodate", "The adult developmental-disability resource includes adolescents but does not document a dedicated youth program."),
    ("automesa-curated:9630eddb85bca6d59fb0dc70da0935a8", "youth-young-adults"):
        ("keep", "accommodate", "The general walk-in mental-health service accepts adults and youth without documenting a dedicated youth track."),
    ("automesa-curated:03c08ccec6ec7f669d5594a7c8499d06", "youth-young-adults"):
        ("keep", "accommodate", "The general bicycle program serves adults and youth with age-specific participation terms but no dedicated youth program."),
}


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _resource_text(resource: dict[str, Any]) -> str:
    fields = [
        str(resource.get("name") or ""),
        str(resource.get("description") or ""),
        str(resource.get("informationText") or ""),
    ]
    return "\n".join(fields)


def _snippet(text: str, match: re.Match[str]) -> str:
    start = max(0, match.start() - 75)
    end = min(len(text), match.end() + 100)
    return " ".join(text[start:end].split())


def build_group_review_packet(store: ResearchStore, study_id: int) -> dict[str, Any]:
    study = store.get_taxonomy_study(study_id)
    if not study:
        raise TaxonomyStudyError("Taxonomy study not found")
    type_status = taxonomy_types_status(store, study_id)
    if type_status["designedCategoryCount"] != type_status["categoryCount"]:
        raise TaxonomyStudyError("Finish every Category Type design before For groups")
    proposals = study["categoryRedistributionProposals"]
    if not proposals:
        raise TaxonomyStudyError("Approve the need-Category proposal before For groups")
    latest_proposal = proposals[-1]
    changed_categories = {
        item["corpusKey"]: item["proposedNeedCategories"]
        for item in latest_proposal["proposal"]["assignments"]
    }
    resources: list[dict[str, Any]] = []
    for item in study["corpus"]["resources"]:
        resources.append({
            "corpusKey": item["corpusKey"],
            "origin": item["origin"],
            "resourceId": item["resourceId"],
            "name": item["name"],
            "priorCategoryIds": list(item["categories"]),
            "proposedCategoryIds": list(
                changed_categories.get(item["corpusKey"], item["categories"])
            ),
            "priorForGroups": list(item["resource"].get("forGroups") or []),
            "resource": deepcopy(item["resource"]),
            "requiredDisposition": "groups | no-group-needed | unresolved",
        })
    resources.sort(key=lambda item: (item["name"].casefold(), item["corpusKey"]))
    if len(resources) != 342 or len({item["corpusKey"] for item in resources}) != 342:
        raise TaxonomyStudyError("Expected 342 distinct resources in the frozen corpus")
    packet = {
        "schemaVersion": 1,
        "status": "proposal-only",
        "studyId": int(study_id),
        "corpusSha256": study["corpusSha256"],
        "categoryProposalSha256": latest_proposal["proposalSha256"],
        "typeDesignedCategoryCount": type_status["designedCategoryCount"],
        "rules": deepcopy(GROUP_REVIEW_RULES),
        "catalog": deepcopy(GROUP_CATALOG),
        "resources": resources,
    }
    packet_sha256 = _sha256(packet)
    store.save_taxonomy_group_review_packet(
        study_id,
        packet,
        packet_sha256,
        based_on_corpus_sha256=study["corpusSha256"],
    )
    return {"studyId": int(study_id), "packetSha256": packet_sha256, "packet": packet}


def _add_relation(
    relations: dict[str, dict[str, Any]],
    group_id: str,
    mode: str,
    evidence: dict[str, str],
) -> None:
    relation = relations.setdefault(group_id, {
        "groupId": group_id,
        "mode": mode,
        "evidence": [],
    })
    if mode == "target":
        relation["mode"] = "target"
    key = (evidence["source"], evidence["text"])
    if key not in {(item["source"], item["text"]) for item in relation["evidence"]}:
        relation["evidence"].append(evidence)


def infer_group_proposal(packet_record: dict[str, Any]) -> dict[str, Any]:
    packet = packet_record["packet"]
    catalog_items = deepcopy(GROUP_CATALOG)
    catalog = {item["id"]: item for item in catalog_items}
    assignments: list[dict[str, Any]] = []
    group_counts: Counter[str] = Counter()
    mode_counts: Counter[str] = Counter()
    changed_count = 0
    rejected_legacy_count = 0
    confirmed_legacy_count = 0
    rejected_inferred_count = 0
    confirmed_inferred_count = 0
    for item in packet["resources"]:
        relations: dict[str, dict[str, Any]] = {}
        rejected_prior_groups: list[dict[str, Any]] = []
        rejected_inferred_groups: list[dict[str, Any]] = []
        resource = item["resource"]
        text = _resource_text(resource)
        for prior in item["priorForGroups"]:
            mapped = _PRIOR_GROUPS.get(str(prior))
            if mapped:
                group_id, mode = mapped
                review = _EXISTING_GROUP_REVIEW.get((item["corpusKey"], group_id))
                if review and review[0] == "remove":
                    rejected_prior_groups.append({
                        "label": str(prior),
                        "canonicalGroupId": group_id,
                        "reason": review[2],
                        "evidenceSource": "manual-frozen-corpus-review",
                    })
                    rejected_legacy_count += 1
                    continue
                _add_relation(relations, group_id, mode, {
                    "source": "existing-for-group",
                    "text": str(prior),
                })
                if review and review[0] == "keep":
                    relations[group_id]["mode"] = review[1]
                    _add_relation(relations, group_id, review[1], {
                        "source": "manual-frozen-corpus-review",
                        "text": review[2],
                    })
                    confirmed_legacy_count += 1
        for category_id in item["priorCategoryIds"]:
            group_id = _LEGACY_CATEGORY_GROUPS.get(str(category_id))
            if group_id:
                _add_relation(relations, group_id, "target", {
                    "source": "retired-population-category",
                    "text": str(category_id),
                })
        for category_id in item.get("proposedCategoryIds", []):
            group_id = _NEED_CATEGORY_GROUPS.get(str(category_id))
            if group_id:
                _add_relation(relations, group_id, "target", {
                    "source": "approved-need-category",
                    "text": str(category_id),
                })
        for group_id, by_mode in _PATTERNS.items():
            for mode, patterns in by_mode.items():
                for pattern in patterns:
                    match = re.search(pattern, text, flags=re.IGNORECASE)
                    if match:
                        _add_relation(relations, group_id, mode, {
                            "source": "resource-text",
                            "text": _snippet(text, match),
                        })
                        break
        for (corpus_key, group_id), review in _INFERRED_GROUP_REVIEW.items():
            if corpus_key != item["corpusKey"]:
                continue
            if review[0] == "remove":
                if group_id in relations:
                    relations.pop(group_id)
                    rejected_inferred_groups.append({
                        "groupId": group_id,
                        "label": catalog[group_id]["label"],
                        "reason": review[2],
                        "evidenceSource": "manual-frozen-corpus-review",
                    })
                    rejected_inferred_count += 1
                continue
            _add_relation(relations, group_id, review[1], {
                "source": "manual-frozen-corpus-review",
                "text": review[2],
            })
            relations[group_id]["mode"] = review[1]
            confirmed_inferred_count += 1
        for child, parent in _HIERARCHY.items():
            if child in relations:
                child_relation = relations[child]
                _add_relation(relations, parent, child_relation["mode"], {
                    "source": "group-hierarchy",
                    "text": f"{catalog[child]['label']} is included in {catalog[parent]['label']}",
                })
        ordered = []
        for group_id in sorted(relations, key=lambda value: catalog[value]["label"].casefold()):
            relation = relations[group_id]
            relation["label"] = catalog[group_id]["label"]
            relation["evidence"].sort(key=lambda value: (value["source"], value["text"]))
            relation["evidenceStatus"] = (
                "existing-only"
                if {value["source"] for value in relation["evidence"]}
                == {"existing-for-group"}
                else "supported"
            )
            ordered.append(relation)
            group_counts[group_id] += 1
            mode_counts[relation["mode"]] += 1
        prior_canonical = {
            mapped[0] for value in item["priorForGroups"]
            if (mapped := _PRIOR_GROUPS.get(str(value)))
        }
        if set(relations) != prior_canonical:
            changed_count += 1
        assignments.append({
            "corpusKey": item["corpusKey"],
            "resourceId": item["resourceId"],
            "name": item["name"],
            "disposition": "groups" if ordered else "no-group-needed",
            "groups": ordered,
            "priorForGroups": list(item["priorForGroups"]),
            "rejectedPriorGroups": rejected_prior_groups,
            "rejectedInferredGroups": rejected_inferred_groups,
            "reviewStatus": (
                "review-existing-only"
                if any(value["evidenceStatus"] == "existing-only" for value in ordered)
                else "ready"
            ),
        })
    proposal = {
        "schemaVersion": 1,
        "status": "proposal-only",
        "studyId": int(packet_record["studyId"]),
        "packetSha256": packet_record["packetSha256"],
        "inferenceEngine": {
            "version": "for-groups-v1.19",
            "catalogSha256": _sha256(catalog_items),
            "rulesSha256": _sha256(GROUP_REVIEW_RULES),
            "patternsSha256": _sha256(_PATTERNS),
            "hierarchySha256": _sha256(_HIERARCHY),
            "categoryRulesSha256": _sha256({
                "legacy": _LEGACY_CATEGORY_GROUPS,
                "need": _NEED_CATEGORY_GROUPS,
            }),
            "existingGroupReviewSha256": _sha256([
                {
                    "corpusKey": key[0],
                    "groupId": key[1],
                    "decision": value[0],
                    "mode": value[1],
                    "reason": value[2],
                }
                for key, value in sorted(_EXISTING_GROUP_REVIEW.items())
            ]),
            "inferredGroupReviewSha256": _sha256([
                {
                    "corpusKey": key[0],
                    "groupId": key[1],
                    "decision": value[0],
                    "mode": value[1],
                    "reason": value[2],
                }
                for key, value in sorted(_INFERRED_GROUP_REVIEW.items())
            ]),
        },
        "rules": deepcopy(GROUP_REVIEW_RULES),
        "catalog": catalog_items,
        "assignments": assignments,
        "coverage": {
            "resourceCount": len(assignments),
            "resourcesWithGroups": sum(item["disposition"] == "groups" for item in assignments),
            "noGroupNeededCount": sum(item["disposition"] == "no-group-needed" for item in assignments),
            "unresolvedCount": 0,
            "resourcesNeedingExistingOnlyReview": sum(
                item["reviewStatus"] == "review-existing-only"
                for item in assignments
            ),
            "changedFromPriorCount": changed_count,
            "confirmedLegacyRelationCount": confirmed_legacy_count,
            "rejectedLegacyRelationCount": rejected_legacy_count,
            "confirmedInferredRelationCount": confirmed_inferred_count,
            "rejectedInferredRelationCount": rejected_inferred_count,
            "groupCounts": {
                catalog[group_id]["label"]: count
                for group_id, count in sorted(group_counts.items())
            },
            "modeCounts": dict(sorted(mode_counts.items())),
        },
    }
    return proposal


def matches_type_and_group_filters(
    *,
    resource_types: set[str] | frozenset[str],
    resource_groups: set[str] | frozenset[str],
    selected_types: set[str] | frozenset[str],
    selected_groups: set[str] | frozenset[str],
) -> bool:
    """Apply the approved within-dimension OR, across-dimension AND rule."""
    type_match = not selected_types or bool(resource_types & selected_types)
    group_match = not selected_groups or bool(resource_groups & selected_groups)
    return type_match and group_match


def matches_category_filter(
    *,
    resource_categories: set[str] | frozenset[str],
    selected_categories: set[str] | frozenset[str],
) -> bool:
    """Multiple selected need Categories are alternatives, not requirements."""
    return not selected_categories or bool(resource_categories & selected_categories)


def group_browse_category_rows(
    resources: list[dict[str, Any]],
    *,
    selected_groups: set[str] | frozenset[str],
) -> dict[str, list[str]]:
    """Return one card key per matching need-Category heading.

    A resource matching more than one selected Group is deduplicated within a
    heading.  A multi-Category resource intentionally appears once under each
    applicable need Category.
    """
    rows: dict[str, dict[str, None]] = {}
    for resource in resources:
        resource_groups = set(resource.get("groupIds") or [])
        if selected_groups and not resource_groups.intersection(selected_groups):
            continue
        card_key = str(resource["corpusKey"])
        for category_id in resource.get("categoryIds") or []:
            rows.setdefault(str(category_id), {})[card_key] = None
    return {
        category_id: list(cards)
        for category_id, cards in sorted(rows.items())
    }


def save_group_inference(store: ResearchStore, study_id: int) -> dict[str, Any]:
    packet = store.get_taxonomy_group_review_packet(study_id)
    if not packet:
        packet = build_group_review_packet(store, study_id)
    proposal = infer_group_proposal(packet)
    proposal_sha256 = _sha256(proposal)
    revision = store.save_taxonomy_group_inference_revision(
        study_id,
        proposal,
        proposal_sha256,
        based_on_packet_sha256=packet["packetSha256"],
        source="codex-full-corpus-group-inference",
        note="Initial target-or-accommodate proposal for Michael's review; no package changed.",
    )
    return {
        "studyId": int(study_id),
        "revision": revision,
        "proposalSha256": proposal_sha256,
        "coverage": proposal["coverage"],
    }


def taxonomy_groups_status(store: ResearchStore, study_id: int) -> dict[str, Any]:
    packet = store.get_taxonomy_group_review_packet(study_id)
    revisions = store.list_taxonomy_group_inference_revisions(study_id)
    latest = revisions[-1] if revisions else None
    return {
        "studyId": int(study_id),
        "packetStatus": packet["status"] if packet else "not-prepared",
        "packetSha256": packet["packetSha256"] if packet else None,
        "revision": latest["revision"] if latest else None,
        "proposalSha256": latest["proposalSha256"] if latest else None,
        "coverage": latest["proposal"]["coverage"] if latest else None,
    }
