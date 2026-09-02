from __future__ import annotations

import hashlib
import json
from collections import Counter
from copy import deepcopy
from typing import Any

from .storage import ResearchStore
from .taxonomy_study import TaxonomyStudyError


TAXONOMY_APPLICATION_CLEANUP_FLAGS = [
    {
        "kind": "duplicate-candidate",
        "resourceIds": [
            "0e36c87d7889979a6cf7f4debff3bed7",
            "eadaaf197b67dc1d520ae55c2dc28a19",
        ],
        "proposedIdentity": "Family Housing Hub — operated by UMOM New Day Centers",
        "status": "apply-after-taxonomy-review",
        "preserve": [
            "MesaCAN satellite access details",
            "coordinated entry prioritizes need but does not guarantee shelter",
        ],
    },
    {
        "kind": "duplicate-candidate",
        "resourceIds": [
            "bd8d70a1ed5b94634c74d90a66d1ea64",
            "ea694e1df9c5ce31796e579520312da9",
        ],
        "proposedIdentity": (
            "My Sister's Place — operated by Catholic Charities Community Services Arizona"
        ),
        "status": "apply-after-taxonomy-review",
        "preserve": [
            "confidential emergency-shelter access",
            "Pathways counseling, mobile advocacy, and transitional-housing verification",
        ],
    },
    {
        "kind": "separate-resource-required",
        "sourceResourceIds": ["5359125c3611d817c5b9511c96a017fa"],
        "proposedIdentity": "House of Refuge — Transitional Housing",
        "proposedCategories": ["housing"],
        "proposedTypes": ["Transitional Housing"],
        "status": "apply-after-taxonomy-review",
        "reason": (
            "The existing card describes resident-only material assistance, not how a "
            "family enters the housing program."
        ),
    },
    {
        "kind": "separate-resource-required",
        "sourceResourceIds": ["6f857637fa2be0cd00ed6fc1671bded3"],
        "proposedIdentity": "The Mesa House — Sober and Transitional Housing",
        "proposedCategories": ["housing", "addiction"],
        "proposedTypes": ["Recovery Housing", "Transitional Housing"],
        "status": "apply-after-taxonomy-review",
        "reason": (
            "The existing card describes resident-only bus passes, not housing intake "
            "or placement."
        ),
    },
    {
        "kind": "consolidation-candidate",
        "resourceIds": [
            "c9a6d961fc20217b2875637b5fef2cb6",
            "3460a40faf90d00f895061b117f1d9cc",
            "8c7a5e3631418ce97d934b37a67fbd61",
        ],
        "proposedIdentity": "Keys to Change — Key Campus Welcome Center",
        "proposedCategories": ["homeless-services", "housing"],
        "proposedHomelessTypes": [
            "Day Center", "Street Outreach", "Showers & Laundry",
            "Mail & Storage", "ID & Documents", "Homeless Navigation",
        ],
        "proposedHousingTypes": ["Coordinated Entry", "Housing Navigation"],
        "status": "apply-after-taxonomy-review",
        "preserve": [
            "practical day-center services and street outreach",
            "Welcome Center and Lodestar access details",
            "coordinated-entry assessment and housing navigation",
        ],
    },
    {
        "kind": "consolidation-candidate",
        "resourceIds": [
            "577e54a943c0cb1d97e003e0e6ba6623",
            "5bfda48463f45755a59145fa7d226906",
        ],
        "proposedIdentity": "La Mesa Ministries — Resource Center",
        "proposedCategories": [
            "transportation", "id-recovery", "homeless-services",
        ],
        "proposedHomelessTypes": [
            "Meals & Basic Needs", "ID & Documents", "Mail & Storage",
        ],
        "status": "apply-after-taxonomy-review",
        "preserve": [
            "bus-pass access details",
            "document assistance",
            "mail, storage, and basic-needs services",
        ],
    },
    {
        "kind": "content-transfer-required",
        "sourceResourceIds": ["948dd967fb329f7e5f04c0814a113889"],
        "destinationResourceId": "e81a4666fa9fdf3874524e595834798c",
        "proposedIdentity": "VA Community Resource and Referral Center / HUD-VASH",
        "status": "apply-after-taxonomy-review",
        "reason": (
            "The broad VA card repeats CRRC housing content; keep that card in Medical "
            "and Caregiving and preserve the useful CRRC details on the dedicated card."
        ),
    },
    {
        "kind": "consolidation-candidate",
        "resourceIds": [
            "b48b75beadedb73dd0606ffb3dcc568d",
            "90ef7bed032bcd935b0f82e65f664917",
            "eb94f24384f8e51a2b237d7d8c507948",
        ],
        "proposedIdentity": "Arizona Early Intervention Program (AzEIP)",
        "proposedCategories": [
            "education", "parenting-child-development",
        ],
        "proposedEducationTypes": [
            "Early Intervention", "Education Navigation",
        ],
        "status": "apply-after-taxonomy-review",
        "preserve": [
            "the dedicated central-referral access path",
            "Child Care Assistance content on the broader DES card",
            "DDD, AZ ABLE, and caregiver-support content on the disability card",
        ],
    },
    {
        "kind": "consolidation-candidate",
        "resourceIds": [
            "61a8d9d4eafa58537df9904250187968",
            "d633e161d87ac6cf94df2a2a6b877ab1",
        ],
        "proposedIdentity": "Frank X. Gordon Adult Education Center",
        "proposedCategories": ["education"],
        "status": "apply-after-taxonomy-review",
        "preserve": [
            "public community access and Mesa location details",
            "reentry-aware Adult Probation partnership details",
            "virtual, digital-literacy, ABE, GED, and ESOL pathways",
        ],
    },
    {
        "kind": "consolidation-candidate",
        "resourceIds": [
            "9c6c63b5207dc97a65b6d8ca95c544e9",
            "e0bfbea73949f1e8965c6c1ad4eeb1ff",
        ],
        "proposedIdentity": "East Valley Institute of Technology (EVIT)",
        "proposedCategories": ["education", "financial-assistance"],
        "status": "apply-after-taxonomy-review",
        "preserve": [
            "adult basic education and GED/HSE access",
            "postsecondary career programs and concurrent enrollment",
            "financial-aid, scholarship, VA-benefit, and advising details",
        ],
    },
    {
        "kind": "consolidation-candidate",
        "resourceIds": [
            "7f314bc451d77d01f553d4527407d06d",
            "c3ab0f1578b4ec24df452d8eee4c9ce6",
            "f95aad04c5e72f66f324d9875d7caffd",
        ],
        "proposedIdentity": "Workforce Center @ Mesa",
        "proposedCategories": ["employment", "education"],
        "status": "apply-after-taxonomy-review",
        "preserve": [
            "the City of Mesa education-class and financial-literacy details",
            "A New Leaf walk-in and professional-clothing access details",
            "ARIZONA@WORK training, apprenticeship, and Smart Justice pathways",
        ],
    },
    {
        "kind": "consolidation-candidate",
        "resourceIds": [
            "193621d2449346f5eb4f3fe57535ad47",
            "a9d82c588239bf51cb761861ce2ef062",
        ],
        "proposedIdentity": "Arouet Foundation — Women's Reentry and Employment Support",
        "proposedCategories": [
            "employment", "parenting-child-development",
        ],
        "status": "apply-after-taxonomy-review",
        "preserve": [
            "current pre-release and post-release intake pathways",
            "the Center for Employment Opportunities partnership",
            "job placement, coaching, family support, and transportation details",
        ],
    },
    {
        "kind": "content-transfer-required",
        "sourceResourceIds": ["08a7877a32a11b9f8531fa95f2a64ade"],
        "destinationResourceId": "6be73b6539fd16b3a6c84ffad77aace8",
        "proposedIdentity": (
            "Arizona Rehabilitation Services Administration — Vocational Rehabilitation"
        ),
        "status": "apply-after-taxonomy-review",
        "reason": (
            "Move duplicated Vocational Rehabilitation details to the dedicated RSA "
            "card while preserving DES reentry-employment services on the broader card."
        ),
    },
    {
        "kind": "consolidation-candidate",
        "resourceIds": [
            "6b2d7fcadeec59dea6cd835e732ef55f",
            "446d7aeaa7a45f7bab5d72f34d1b10e3",
            "9b72f8059923e0a5e6d1dca60a9dd708",
        ],
        "proposedIdentity": "Terros Health — Substance Use Treatment",
        "proposedCategories": ["addiction", "mental-health"],
        "status": "apply-after-taxonomy-review",
        "preserve": [
            "Mesa-area outpatient intake and insurance-access details",
            "residential, medication, counseling, and co-occurring treatment details",
            "harm-reduction, overdose-prevention, and Spanish-accommodation details",
            "the Adult Probation partnership and accountable reentry pathway",
        ],
        "reason": (
            "The Lifewell Behavioral Wellness / Terros card appears to duplicate or "
            "misstate the Terros identity and should be reconciled before packaging."
        ),
    },
    {
        "kind": "consolidation-candidate",
        "resourceIds": [
            "33b8cbd29cf68ac3a07e0fd8d984771b",
            "bd13f813cdf1a52f4297b41d93bea46b",
        ],
        "proposedIdentity": "Adelante Healthcare — Mesa",
        "proposedCategories": [
            "medical-dental-vision", "food", "parenting-child-development",
            "financial-assistance",
        ],
        "status": "apply-after-taxonomy-review",
        "preserve": [
            "primary, dental, pediatric, prenatal, postpartum, and reproductive care",
            "same-day care, pharmacy, telehealth, WIC, and behavioral-health details",
            "sliding-fee, uninsured, enrollment, and language-access information",
        ],
    },
    {
        "kind": "consolidation-candidate",
        "resourceIds": [
            "10c59c16ac8288d92ae7a7626edf06ab",
            "2a530b4a56b21439a952af2ac753f12f",
        ],
        "proposedIdentity": "Health-e-Arizona Plus — Benefits Enrollment Portal",
        "proposedCategories": [
            "medical-dental-vision", "financial-assistance", "food",
        ],
        "status": "apply-after-taxonomy-review",
        "preserve": [
            "AHCCCS, KidsCare, SNAP, and TANF enrollment and renewal details",
            "limited adult dental and vision benefit cautions",
            "in-person enrollment-help pathways",
        ],
    },
    {
        "kind": "consolidation-candidate",
        "resourceIds": [
            "af6fce2b1b9927a1669f390313d56ae6",
            "111bbc8293126891b0ecef093e94874c",
        ],
        "proposedIdentity": "Mountain Park Health Center",
        "proposedCategories": ["medical-dental-vision"],
        "status": "apply-after-taxonomy-review",
        "preserve": [
            "primary, pediatric, prenatal, reproductive, dental, and pharmacy care",
            "sliding-fee access for uninsured patients",
            "location-specific service and Mesa-access cautions",
        ],
    },
    {
        "kind": "consolidation-candidate",
        "resourceIds": [
            "4ae8876a9b82a7f0a606939254d87bb8",
            "aee416211643d092d52e82a4470df12b",
        ],
        "proposedIdentity": "Valleywise Health — Mesa and Countywide Care",
        "proposedCategories": [
            "medical-dental-vision", "parenting-child-development",
            "financial-assistance",
        ],
        "status": "apply-after-taxonomy-review",
        "preserve": [
            "Mesa primary, prenatal, postpartum, pediatric, and pharmacy access",
            "hospital, specialty, dental, and reproductive-health pathways",
            "teen maternity, sliding-fee, charity-care, and uninsured-discount details",
        ],
    },
    {
        "kind": "availability-verification-required",
        "resourceIds": ["363ba896bb14a4dc850081cd818533c7"],
        "proposedIdentity": "St. Vincent de Paul — East Valley Medical Clinic",
        "status": "apply-after-taxonomy-review",
        "requirement": (
            "Do not offer the planned Mesa clinic until its opening, current services, "
            "and intake pathway are confirmed from an official source."
        ),
    },
    {
        "kind": "consolidation-candidate",
        "resourceIds": [
            "5b415ee3078420f7b8081b605d1d087a",
            "20cf2620b396a3fc5a0d270ade9af911",
        ],
        "proposedIdentity": "Community Bridges, Inc. — Integrated Care",
        "proposedCategories": ["addiction", "mental-health"],
        "status": "apply-after-taxonomy-review",
        "preserve": [
            "CPEC, EVARC, Center for Hope, and Mesa Heritage Clinic pathways",
            "crisis, withdrawal, residential, outpatient, peer, and case-management care",
            "co-occurring treatment, AHCCCS, sliding-scale, and site-selection details",
        ],
        "reason": (
            "The two broad CBI cards describe the same integrated provider identity; "
            "the specialized Center for Hope reentry card remains separate."
        ),
    },
    {
        "kind": "content-transfer-required",
        "sourceResourceIds": ["0474f03b486642977ecad2860ffac719"],
        "destinationResourceId": "34dc7c352ceb97ec5831aaa7cb4d3904",
        "proposedIdentity": (
            "Banner Desert — Pregnancy, Postpartum & Infant Loss Support"
        ),
        "status": "apply-after-taxonomy-review",
        "reason": (
            "Move the maternity card's mental-health support-group details to the "
            "dedicated support resource while keeping hospital maternity care medical."
        ),
    },
    {
        "kind": "identity-correction-required",
        "resourceIds": ["1191caa6a627cab7f478d5fe36466e0a"],
        "proposedIdentity": "Maricopa County Court Self-Service Center",
        "proposedCategories": ["legal"],
        "status": "apply-after-taxonomy-review",
        "preserve": [
            "set-aside, record-sealing, marijuana-expungement, and rights-restoration help",
            "family and civil forms, workshops, clinics, and brief form review",
            "the distinction between legal information and legal advice",
        ],
        "reason": (
            "The current record-relief name is narrower than the documented family, "
            "civil, and criminal-record self-help pathways."
        ),
    },
    {
        "kind": "service-area-verification-required",
        "resourceIds": ["1c01cd6b13aaf41619e7cdc09b4c6725"],
        "proposedIdentity": (
            "University of Arizona Veterans' Advocacy Law Clinic"
        ),
        "status": "apply-after-taxonomy-review",
        "requirement": (
            "Do not offer this Tucson-centered clinic as a Mesa referral until a "
            "current Maricopa County intake or statewide mobile-clinic pathway is confirmed."
        ),
    },
]


CATEGORY_TYPE_DESIGNS: dict[str, dict[str, Any]] = {
    "food": {
        "types": [
            {"label": "Food Pantry", "definition": "Food boxes, groceries, commodities, or pantry shopping."},
            {"label": "Prepared Meals", "definition": "Ready-to-eat meals served at a site or program."},
            {"label": "Home Delivery", "definition": "Food or meals delivered to someone unable to reach a site."},
            {"label": "Gov't Benefits", "definition": "SNAP, WIC, or similar government food benefits and help applying for them."},
            {"label": "School Food", "definition": "Meals, pantries, or food programs accessed through school or college."},
            {"label": "Infant Formula", "definition": "Infant formula supplied directly to a household."},
        ],
        "assignments": {
            "b818a3a3b765d76ab42f0c78b169eef9": ["Food Pantry"],
            "33b8cbd29cf68ac3a07e0fd8d984771b": ["Gov't Benefits"],
            "5f72f3c9e07e90867dc016da33c05457": ["Prepared Meals", "Home Delivery"],
            "de9cf94ebcf45f375f7b8f0dba219edc": ["Prepared Meals", "Home Delivery"],
            "cd0fd35209b8684c1b85d3a08afb1f4d": ["Gov't Benefits"],
            "78ae362f464eb9c81519fc00a43f21ba": ["Prepared Meals", "Home Delivery"],
            "af848390332ec0fb5a3b60ba708457ee": ["Food Pantry"],
            "bd171f3dee49f66941dccb61f68c2dea": ["Food Pantry"],
            "e8989c429a0fd3824db237f9d8a9a4d8": ["Food Pantry"],
            "528e3dad283cd117ea2ff80b3bec333c": "no-type-needed",
            "24ea5cbf96413ae1016d5b8ad6140c2c": ["Food Pantry"],
            "a6043035dfbf51e34bad108416bca340": ["Infant Formula"],
            "47ea38f7dcac87504d34a3e7d2866f21": ["Gov't Benefits"],
            "d6f9cf4449c9ba1d947c0bcbf2ead96f": ["School Food"],
            "da047755bc1b7958186bd4dbcea9c8cb": ["Food Pantry", "School Food"],
            "e81c856ded56111fff730cb01a05858c": ["Prepared Meals", "School Food"],
            "61ba95efea2447e1f5b054e5206ef5e1": ["Food Pantry"],
            "5add8558737e9cfc392878fce4cca308": ["Food Pantry"],
            "89a928c6f5bbdc65de87c3fecbbcae79": ["Food Pantry"],
            "f05e5c2c63d27e8c03ce7ed46003ae31": ["Food Pantry", "Prepared Meals"],
            "72ddcda0a55400e3066289181a6795d0": ["Food Pantry"],
            "9674f1a708712c74c41c9d591821a356": ["Food Pantry", "Prepared Meals", "Gov't Benefits"],
            "15507c56e359f505d8f574491c7962ac": ["Food Pantry"],
            "2bf6edeedd27a167fa3b1ba584d2c7c4": ["Food Pantry", "Gov't Benefits"],
            "1d66d1be0ba923ab021628030571f488": ["Prepared Meals"],
            "198981e1dc00de23338ff11916b8b4f4": ["Food Pantry"],
            "81a717d8c41a9cf35a86be0cdb1e5de3": ["Food Pantry", "Home Delivery"],
            "b99546482569a1341c2d1bee2c229b84": ["Food Pantry"],
            "d0c9ac481879ff5e0a5b9e11b1eb3d9a": ["Food Pantry"],
            "cdfb3f0865d219ddb377d180c8b354d8": ["Food Pantry"],
            "6e7d458a612213f8327cade4ebd7b7fd": "no-type-needed",
            "7dd0c1074a53e4e1aa41c662ca9e6455": ["Food Pantry"],
        },
        "boundary": "Population eligibility belongs in For groups; food delivery method belongs in Types.",
    },
    "clothing": {
        "types": [
            {"label": "General Clothing", "definition": "Everyday clothing and shoes."},
            {"label": "Dress Clothing", "definition": "Professional or formal clothing suitable for interviews, work, church, or other dress occasions."},
            {"label": "Work Clothing", "definition": "Uniforms, work boots, and other job-required clothing."},
            {"label": "School Clothing", "definition": "School uniforms, school clothes, and student shoes."},
        ],
        "assignments": {
            "2683e222e5f6957b1e5bddb3292334d1": ["Work Clothing"],
            "aeed9f6c57cf87a109315fe1590a12d2": ["General Clothing"],
            "337e91d961e84d96ee124c6c891045eb": ["General Clothing"],
            "4ea93a335a4945322184f2ce0e01feb5": ["School Clothing"],
            "70ea356cba96bcc304b79ca2a5469f9c": ["Work Clothing"],
            "1ed84b657420da445ac082991959b3f8": ["General Clothing"],
            "ebac95249761b88323fc73b4e26259fd": ["General Clothing"],
            "ed9cec6557722e44984887fb41637d6e": ["General Clothing"],
            "ea17c3d484efe07c9892521284d54e24": ["Dress Clothing"],
            "df171bb522d8c9a10c10b5c20e52cc1b": ["Dress Clothing"],
            "528e3dad283cd117ea2ff80b3bec333c": ["General Clothing"],
            "de5e0aa4a6c2164fb8b4a9fcfdcdac9b": ["General Clothing"],
            "7e66c8c912ad9889aa3627405af218f3": ["General Clothing"],
            "fbd7ac5640a1ad45864261484e2bcbf0": ["General Clothing"],
            "48635b5d3545aa10e94ee5ef9259b840": ["General Clothing"],
            "5359125c3611d817c5b9511c96a017fa": ["General Clothing"],
            "6ce0d0fd810d670dae505e267ea6e01a": ["General Clothing"],
            "663199b0f4bb6151cde8abc21bceb26c": ["General Clothing"],
            "73dfadc219f93cdde3c2e07d3e1045b4": ["General Clothing", "Dress Clothing", "Work Clothing"],
            "7bacf0bff58c51dc50d9c02ccd69eac4": ["General Clothing"],
            "882badd1df67753d02e23796b2875118": ["General Clothing"],
            "c399be50023b7d9bbbd54bbdea6b4b5f": ["General Clothing"],
            "08497e5f8c33c372d57430bc722bb639": ["Dress Clothing", "Work Clothing"],
            "c74ea9adad61a6ff3fd9e49ae50d61d2": ["General Clothing", "Work Clothing", "School Clothing"],
            "edacb348adc1480fe0ac0b9b6f1e8580": ["General Clothing"],
            "3367433d5c6845b44636936a2902a3bb": ["Dress Clothing"],
        },
        "boundary": "Who qualifies belongs in For groups; the clothing supplied belongs in Types.",
    },
    "household-essentials": {
        "types": [
            {"label": "Furniture", "definition": "Beds, tables, seating, and other major furnishings."},
            {"label": "Household Goods", "definition": "Linens, dishes, appliances, and household necessities."},
            {"label": "Hygiene Supplies", "definition": "Toiletries and personal-care necessities."},
            {"label": "Baby Supplies", "definition": "Diapers, cribs, car seats, infant clothing, and other baby equipment."},
        ],
        "assignments": {
            "2683e222e5f6957b1e5bddb3292334d1": ["Furniture"],
            "337e91d961e84d96ee124c6c891045eb": ["Baby Supplies"],
            "4ea93a335a4945322184f2ce0e01feb5": ["Hygiene Supplies"],
            "442b7ced0e864db023bebfb05ecc9870": ["Furniture", "Household Goods"],
            "1ed84b657420da445ac082991959b3f8": ["Baby Supplies", "Hygiene Supplies"],
            "ebac95249761b88323fc73b4e26259fd": ["Hygiene Supplies"],
            "ed9cec6557722e44984887fb41637d6e": ["Baby Supplies"],
            "fbd7ac5640a1ad45864261484e2bcbf0": ["Baby Supplies", "Hygiene Supplies"],
            "48635b5d3545aa10e94ee5ef9259b840": ["Household Goods"],
            "5359125c3611d817c5b9511c96a017fa": ["Furniture", "Household Goods"],
            "a6043035dfbf51e34bad108416bca340": ["Baby Supplies"],
            "0df6bb236d8c7bf168ce4867dc83360e": ["Baby Supplies"],
            "6ce0d0fd810d670dae505e267ea6e01a": ["Baby Supplies", "Hygiene Supplies"],
            "73dfadc219f93cdde3c2e07d3e1045b4": ["Household Goods"],
            "7bacf0bff58c51dc50d9c02ccd69eac4": ["Baby Supplies"],
            "882badd1df67753d02e23796b2875118": ["Furniture", "Household Goods"],
            "c399be50023b7d9bbbd54bbdea6b4b5f": ["Furniture", "Household Goods", "Hygiene Supplies"],
            "c74ea9adad61a6ff3fd9e49ae50d61d2": ["Hygiene Supplies"],
            "edacb348adc1480fe0ac0b9b6f1e8580": ["Baby Supplies", "Furniture", "Household Goods", "Hygiene Supplies"],
            "669bd738b302f2f17f9caa6163dd35ed": "no-type-needed",
            "1a240d601f09634fb93383fd76971b5c": ["Furniture", "Household Goods"],
        },
        "boundary": "Who qualifies belongs in For groups; the household goods supplied belong in Types.",
    },
    "transportation": {
        "types": [
            {"label": "Travel Training", "definition": "Instruction in using public or fixed-route transportation."},
            {"label": "Medical Rides", "definition": "Transportation to medical or behavioral-health appointments."},
            {"label": "Volunteer Rides", "definition": "Individual trips provided by volunteer drivers."},
            {"label": "Bus Passes", "definition": "Transit passes or fare assistance."},
            {"label": "Ride Vouchers", "definition": "Taxi, rideshare, or other trip vouchers."},
            {"label": "Bicycles", "definition": "Bicycle placement, repair, or cycling transportation."},
        ],
        "assignments": {
            "c98efcff0bd197bbec30e22139820e7a": ["Travel Training"],
            "1d65b4adbe723072ef2992d60f99bdf2": ["Medical Rides"],
            "33560faa0e326f7d9f179cfc8f356488": ["Volunteer Rides"],
            "206aace5d5722f95e596d3369baa90cc": ["Volunteer Rides", "Medical Rides"],
            "7d5ab5422e4e7754622adfaf76789c63": ["Medical Rides", "Bus Passes"],
            "855aea5e0d3d3b07f11e7bb81212e4d2": ["Medical Rides"],
            "40894eb45a7350552e6e0df4621e8eb3": ["Volunteer Rides"],
            "b8974853db6587c88187211e9eb32960": ["Bicycles"],
            "60e4d8ec2611999a357a1283fd451295": ["Medical Rides"],
            "df171bb522d8c9a10c10b5c20e52cc1b": "no-type-needed",
            "2504ccabf901d68e7682a299c2151b21": ["Volunteer Rides", "Medical Rides"],
            "528e3dad283cd117ea2ff80b3bec333c": ["Bus Passes"],
            "f5956fe09395d25458ca9fda67d737c9": ["Ride Vouchers"],
            "577e54a943c0cb1d97e003e0e6ba6623": ["Bus Passes"],
            "8f69d21d4d0d04de3adeae58d4890d6c": ["Medical Rides", "Bus Passes"],
            "e1f846bba51958551be6dde95f68a852": ["Bus Passes"],
            "2aeb697bd9f8e4d9ce206105d197e6a2": ["Bicycles"],
            "6f857637fa2be0cd00ed6fc1671bded3": ["Bus Passes"],
            "9458ee851891add0159701b3c62bcca4": ["Medical Rides"],
            "d8a0a0095b59cb2e7bceb2cffbd239e5": ["Ride Vouchers"],
            "03c08ccec6ec7f669d5594a7c8499d06": ["Bicycles"],
        },
        "boundary": "Destination or eligible population belongs in For groups unless it changes the transportation method itself.",
    },
    "utilities-phone-internet": {
        "types": [
            {"label": "Bill Assistance", "definition": "One-time or crisis help paying utility bills."},
            {"label": "Bill Discounts", "definition": "Ongoing reduced utility rates or seasonal discounts."},
            {"label": "Payment Plans", "definition": "Extensions, arrangements, or disconnection prevention."},
            {"label": "Heating/Cooling Repair", "definition": "Repair or replacement of heating and cooling equipment."},
            {"label": "Home Utility Repairs", "definition": "Electrical, plumbing, water-heater, or related home repairs."},
            {"label": "Low-cost Internet", "definition": "Reduced-cost internet service or hotspot access."},
            {"label": "Phone/Internet Discount", "definition": "Monthly phone or internet service discount."},
            {"label": "Communication Equipment", "definition": "Accessible telephone or signaling equipment."},
            {"label": "Relay Service", "definition": "Telephone relay connecting people with hearing or speech disabilities."},
        ],
        "assignments": {
            "106d516390d810b1989b53d59ae806c9": ["Bill Assistance"],
            "ee67d6c2ce1b1b7f9dbf0b2ef86ef972": ["Communication Equipment", "Relay Service"],
            "472c5150aa06dba907ba0bdd1106599e": ["Bill Assistance"],
            "e65a5ab33ccf6b355ca9b21969c6617e": ["Bill Discounts", "Bill Assistance", "Heating/Cooling Repair"],
            "3c04b13381e97f377ba21e3c86d0b12c": ["Heating/Cooling Repair", "Home Utility Repairs"],
            "5b6667d5d6350f7b3c4e9c94b1b17de1": ["Bill Discounts"],
            "fa0719b16ad0843652d8175fb792ca87": ["Payment Plans"],
            "4ff2225ddc559a033efe06a6b6ce3659": ["Low-cost Internet"],
            "8b0cbd343a20dc0118ec3fa8c9a17d1f": ["Bill Discounts"],
            "7d48baeb2cd113386712a5ec693abb8c": ["Bill Discounts"],
            "726f13326a74a1f5d347c70575ea49e7": ["Phone/Internet Discount"],
            "774e5a59b471ceacca5d0fe7cc5e787b": ["Heating/Cooling Repair"],
        },
        "boundary": "The utility or communication method is a Type; income, disability, and household eligibility belong in For groups or access details.",
    },
    "id-recovery": {
        "types": [
            {"label": "State ID/License", "definition": "State identification cards and driver licenses."},
            {"label": "Birth Certificates", "definition": "Certified birth records and replacement certificates."},
            {"label": "Social Security Card", "definition": "Replacement Social Security cards."},
            {"label": "Military Records", "definition": "DD214 and other military-service records."},
            {"label": "Tribal ID", "definition": "Tribal enrollment and identification credentials."},
            {"label": "Immigration Documents", "definition": "Replacement immigration-status and citizenship documents."},
            {"label": "Document Navigation", "definition": "Hands-on help reconstructing or applying for documents."},
            {"label": "Document Storage", "definition": "Secure retention of recovered identity documents."},
            {"label": "Mail Service", "definition": "A reliable mailing address for receiving identity documents."},
        ],
        "assignments": {
            "2a8159c00294405bdb9123bc13f28b34": ["State ID/License"],
            "a90b957439ba736a20a0eb129322891e": ["Document Navigation"],
            "b684b97f8e67ea1cb39778d953a2c4cf": ["State ID/License"],
            "fb402105bec44e0623b4ccf8d7064802": ["Military Records", "Document Navigation"],
            "8fbf07bdf33a69f83a1afc375c0f66d3": ["State ID/License", "Birth Certificates", "Social Security Card", "Document Navigation"],
            "528e3dad283cd117ea2ff80b3bec333c": ["State ID/License", "Birth Certificates", "Document Navigation"],
            "4a4a619b7b63a00120d7f6c7391caabd": ["State ID/License", "Birth Certificates", "Document Navigation", "Document Storage"],
            "5bfda48463f45755a59145fa7d226906": ["State ID/License", "Birth Certificates", "Social Security Card", "Document Navigation", "Mail Service"],
            "a4e45e62c0b9cb505d5b4874340871fb": ["Document Navigation"],
            "1d7914c5fe0d1c96c8583057ac00239f": ["Birth Certificates"],
            "c24a862cda664d0144ec0ae39b3e8f1f": ["Military Records"],
            "fb14c6d3b942c86033ad23bf8b60fb48": ["State ID/License", "Birth Certificates", "Document Navigation", "Mail Service"],
            "7605d7bd12f1c558ab092d52ceaa6aa0": ["Tribal ID"],
            "2f439f11fb6027227582190274a7e325": ["Social Security Card"],
            "3a1860ddbd26130bf05da552b564c12a": ["Immigration Documents"],
        },
        "boundary": "The document being recovered is a Type; the person's population or circumstance belongs in For groups.",
    },
    "housing": {
        "types": [
            {"label": "Emergency Shelter", "definition": "Immediate temporary lodging, including shelter beds and emergency hotel rooms."},
            {"label": "Transitional Housing", "definition": "Time-limited housing that bridges toward a permanent home."},
            {"label": "Rapid Rehousing", "definition": "Short-term placement and financial support to move quickly into permanent housing."},
            {"label": "Rental Assistance", "definition": "Rent or mortgage help intended to prevent displacement or preserve housing."},
            {"label": "Housing Vouchers", "definition": "Tenant- or project-based rental subsidies, including Section 8 and HUD-VASH."},
            {"label": "Affordable Housing", "definition": "Income-restricted rental homes or affordable properties."},
            {"label": "Supportive Housing", "definition": "Permanent housing paired with ongoing case, health, or recovery supports."},
            {"label": "Coordinated Entry", "definition": "A formal assessment and placement gateway for shelter and housing programs."},
            {"label": "Housing Navigation", "definition": "Hands-on help finding, applying for, or transitioning to housing."},
            {"label": "Treatment Housing", "definition": "Residential housing integrated with behavioral-health or substance-use treatment."},
            {"label": "Recovery Housing", "definition": "Substance-free living after detox or during ongoing recovery, where housing and peer accountability rather than onsite clinical treatment are the primary service."},
            {"label": "Deposit Assistance", "definition": "Help with security, utility, or other move-in deposits."},
            {"label": "Eviction Prevention", "definition": "Financial or case-management intervention intended to keep someone housed before displacement."},
            {"label": "Eviction Legal Help", "definition": "Legal advice, negotiation, or representation concerning an eviction notice, court case, or related tenant problem."},
            {"label": "Community Living", "definition": "Adult foster care, shared living, or disability-supportive community residences."},
        ],
        "assignments": {
            "db2e8f3b8772791cf254fb9cc04b9838": ["Emergency Shelter", "Transitional Housing"],
            "a90b957439ba736a20a0eb129322891e": ["Housing Navigation"],
            "773f0771a3cca46a7a57189d17a58a01": ["Emergency Shelter", "Rental Assistance", "Eviction Prevention"],
            "996b322aa685b24c16a5bbea4b68ed0e": ["Transitional Housing", "Housing Navigation"],
            "8d56f8448fc9b780197d3015c051f81c": ["Emergency Shelter", "Rapid Rehousing", "Housing Navigation"],
            "00cca473db91285a4a393f5ba53add8f": ["Community Living"],
            "6f709ac3eafa28d894f99dad814a2430": ["Rental Assistance", "Eviction Prevention"],
            "d9955a94238970f4a2e3c2e93c554835": ["Emergency Shelter", "Housing Navigation"],
            "51cfce1c2944ef0453c793aba1923e08": ["Housing Vouchers", "Deposit Assistance"],
            "6aa599e3a9f6ce52dd0a27bc6e625fd2": ["Rapid Rehousing", "Supportive Housing", "Treatment Housing", "Coordinated Entry"],
            "f2e69a8b2402313065411a32eaa02190": ["Treatment Housing"],
            "df171bb522d8c9a10c10b5c20e52cc1b": ["Housing Navigation"],
            "0e36c87d7889979a6cf7f4debff3bed7": ["Coordinated Entry"],
            "ba6cab830d60bb25c2039ae996392523": ["Transitional Housing"],
            "1bd2fb5b4587feef40252e0630c6c94c": ["Community Living", "Housing Navigation"],
            "8228b3327c959acccf53469fa50397a9": "no-type-needed",
            "c922c1358349b26864bc1c2f50341b2c": ["Housing Vouchers", "Affordable Housing"],
            "8c7a5e3631418ce97d934b37a67fbd61": ["Coordinated Entry"],
            "f762833ab9433719331a7c11e58f71c4": ["Emergency Shelter", "Transitional Housing"],
            "5c289896c8e36191fd9beb5704951340": ["Emergency Shelter"],
            "0df6bb236d8c7bf168ce4867dc83360e": ["Transitional Housing"],
            "a4e45e62c0b9cb505d5b4874340871fb": ["Housing Navigation"],
            "6e7170ded0655c5a4c98f215acb7ac4d": ["Emergency Shelter", "Transitional Housing"],
            "36a1aba6efe7a704aa4ca190a4f82467": ["Rental Assistance", "Eviction Prevention"],
            "a3782d71fb0f13f124d33c95dadd779c": ["Rapid Rehousing", "Deposit Assistance"],
            "815148d4fe10fdbf28f981c14050256c": ["Treatment Housing"],
            "b8ca7f8d2eab81113b10c1a8835f0817": ["Affordable Housing"],
            "617d4be1951f67468b5ddffdb2f670f5": ["Treatment Housing", "Housing Vouchers"],
            "d0eeddd67746f3a298eaf4969b6e9bd1": ["Emergency Shelter", "Transitional Housing", "Rental Assistance"],
            "79a54c3aaf0d161f9dbab859bfba7da2": ["Emergency Shelter", "Transitional Housing"],
            "e81a4666fa9fdf3874524e595834798c": ["Housing Vouchers", "Supportive Housing", "Coordinated Entry"],
            "2af79fdd0101ee3a198c732086f9bfc6": ["Transitional Housing", "Rapid Rehousing", "Supportive Housing"],
            "15b833547484fe110411244b99712ca9": ["Emergency Shelter", "Rapid Rehousing", "Housing Navigation"],
            "eadaaf197b67dc1d520ae55c2dc28a19": ["Coordinated Entry"],
            "cfddfe7aec2aa52de1a56c0d3d797d9e": ["Recovery Housing", "Treatment Housing"],
            "a21c310d2a515339bb648af71577d74d": ["Recovery Housing"],
            "5f7fa3abe7c319ad1bd03122a3caae11": ["Recovery Housing", "Treatment Housing"],
            "86255417090cba31f14b0d7e9334d157": ["Recovery Housing", "Supportive Housing"],
            "349f6314644d54f9964a53688887cc47": ["Treatment Housing"],
            "db242d7df7b5e913727adc08e1ab4029": ["Treatment Housing"],
            "25eba00c6cbab9b8fd1950d2938172b3": ["Treatment Housing"],
            "14d40b4e4bdd71c67e009326f3716119": ["Treatment Housing"],
            "0be7372bda5d130e905a555ea663b1aa": ["Treatment Housing"],
            "5494e7153548657ba7384d98b5d24247": ["Recovery Housing", "Transitional Housing"],
            "096327d7591511a067b7e9dd29f900b6": ["Emergency Shelter"],
            "ed0745322850d01341f8baf07c69f0a0": ["Emergency Shelter"],
            "19a8af5b80be03028603cfa5e8bebb6e": ["Emergency Shelter"],
            "78410d1265bcc4f89c056a7d624434f8": ["Emergency Shelter", "Rapid Rehousing", "Affordable Housing", "Housing Navigation"],
            "bd8d70a1ed5b94634c74d90a66d1ea64": ["Emergency Shelter", "Transitional Housing"],
            "626aab0a5b4c6dcd7811605470690fc3": ["Emergency Shelter", "Transitional Housing"],
            "177117c4ee2b5824559a13d70c603148": ["Emergency Shelter", "Transitional Housing"],
            "b666b49c655c08750bdf54de800e82af": ["Emergency Shelter", "Transitional Housing"],
            "f76b64043d73b489d7067d9f9d856b42": ["Emergency Shelter"],
            "ea694e1df9c5ce31796e579520312da9": ["Emergency Shelter"],
            "106d516390d810b1989b53d59ae806c9": ["Rental Assistance", "Eviction Prevention"],
            "5a185dff18772905536e3488f7b75129": ["Rental Assistance"],
            "27adbd6da40ba1d0325ed17d523a3e94": ["Rental Assistance", "Deposit Assistance"],
            "987a8b8eb5e82e8c0216ef7bb436693f": ["Deposit Assistance"],
            "4d728e518eb341e958f91d67d4cac4cd": ["Rental Assistance", "Deposit Assistance", "Housing Navigation"],
            "bcc694b6232b6b88cd40c57d3052f4ca": ["Rental Assistance", "Deposit Assistance"],
            "ff1488daaf584a5c3e58c81b4e22bf10": ["Rental Assistance", "Eviction Prevention"],
            "5fd29d6c772cabbc8a6abc6614f9d3bd": ["Rental Assistance", "Eviction Prevention"],
            "fcdf7044337d12d9e7bdd3a7a732fd08": ["Rental Assistance"],
            "da4f4b5a717ae241f3363cc09eb4298a": ["Housing Navigation"],
            "08a26b747ffe8b1ea284e491a62d39e7": ["Coordinated Entry", "Housing Navigation"],
            "3460a40faf90d00f895061b117f1d9cc": ["Coordinated Entry", "Housing Navigation"],
            "138a8c6f2c950488f75f8766e2ef6252": ["Eviction Legal Help"],
            "c8f5de50d9d41ce30ec0b8b6ef45b249": ["Eviction Legal Help"],
            "a75559d019132060ea10e3390d9106ab": ["Eviction Legal Help"],
            "6d4803e545580ed7abc3cd8bb87b1314": ["Eviction Legal Help"],
            "fb402105bec44e0623b4ccf8d7064802": ["Rental Assistance", "Community Living"],
        },
        "boundary": "Housing Types describe the housing intervention; urgency, wait time, eligibility, and population belong in access details or For groups.",
    },
    "homeless-services": {
        "types": [
            {"label": "Day Center", "definition": "A daytime place for respite and multiple practical services."},
            {"label": "Street Outreach", "definition": "Mobile engagement and supplies for people living outside."},
            {"label": "Showers & Laundry", "definition": "Access to showers, laundry, haircuts, or hygiene facilities."},
            {"label": "Mail & Storage", "definition": "Mail service or secure storage for property and documents."},
            {"label": "ID & Documents", "definition": "Help obtaining, replacing, or safeguarding identity documents."},
            {"label": "Meals & Basic Needs", "definition": "Meals, water, clothing, hygiene kits, and survival supplies."},
            {"label": "Homeless Navigation", "definition": "Case management, assessment, and accountable connections to shelter or housing."},
            {"label": "Overnight Lodging", "definition": "Temporary overnight accommodation offered as part of homeless services."},
        ],
        "assignments": {
            "78410d1265bcc4f89c056a7d624434f8": ["Mail & Storage", "Meals & Basic Needs", "Homeless Navigation", "Overnight Lodging"],
            "d54d48c6356e5e983f4bd33e02469bc3": ["Showers & Laundry", "Meals & Basic Needs"],
            "c39b7edce7fd22875fba8558aa17172c": ["Showers & Laundry", "Meals & Basic Needs"],
            "e21ae1b4b21564628d99c417487754a1": ["Day Center", "Showers & Laundry", "Meals & Basic Needs", "Homeless Navigation"],
            "4a4a619b7b63a00120d7f6c7391caabd": ["ID & Documents", "Mail & Storage"],
            "da4f4b5a717ae241f3363cc09eb4298a": ["Day Center", "Showers & Laundry", "ID & Documents", "Meals & Basic Needs", "Homeless Navigation"],
            "c9a6d961fc20217b2875637b5fef2cb6": ["Day Center", "Street Outreach", "Showers & Laundry", "Mail & Storage", "Homeless Navigation"],
            "3460a40faf90d00f895061b117f1d9cc": ["Day Center", "Showers & Laundry", "Mail & Storage", "ID & Documents", "Homeless Navigation"],
            "096327d7591511a067b7e9dd29f900b6": ["Overnight Lodging", "Showers & Laundry", "Meals & Basic Needs", "Homeless Navigation"],
            "08a26b747ffe8b1ea284e491a62d39e7": ["Day Center", "Showers & Laundry", "Mail & Storage", "ID & Documents", "Meals & Basic Needs", "Homeless Navigation"],
            "91d5cdd19b42853fb4bbe8e57f325be0": ["Street Outreach", "Meals & Basic Needs", "Homeless Navigation"],
            "19a8af5b80be03028603cfa5e8bebb6e": ["Day Center", "Showers & Laundry", "Homeless Navigation", "Overnight Lodging"],
            "2af79fdd0101ee3a198c732086f9bfc6": ["Street Outreach", "Homeless Navigation"],
            "773f0771a3cca46a7a57189d17a58a01": ["Overnight Lodging", "Homeless Navigation"],
            "8d56f8448fc9b780197d3015c051f81c": ["Overnight Lodging", "Homeless Navigation"],
            "d9955a94238970f4a2e3c2e93c554835": ["Overnight Lodging", "Homeless Navigation"],
            "15b833547484fe110411244b99712ca9": ["Overnight Lodging", "Homeless Navigation"],
            "d0eeddd67746f3a298eaf4969b6e9bd1": ["Overnight Lodging", "Homeless Navigation"],
            "6aa599e3a9f6ce52dd0a27bc6e625fd2": ["Street Outreach", "Homeless Navigation"],
            "577e54a943c0cb1d97e003e0e6ba6623": ["Meals & Basic Needs"],
            "5bfda48463f45755a59145fa7d226906": ["ID & Documents", "Mail & Storage"],
            "669bd738b302f2f17f9caa6163dd35ed": ["Meals & Basic Needs"],
            "e81a4666fa9fdf3874524e595834798c": ["Homeless Navigation"],
            "8c7a5e3631418ce97d934b37a67fbd61": ["Homeless Navigation"],
        },
        "boundary": "These Types describe practical help while someone is homeless; shelter and permanent housing interventions remain visible under Housing too.",
    },
    "financial-assistance": {
        "types": [
            {"label": "Cash Assistance", "definition": "Public cash assistance for basic household needs."},
            {"label": "Disability Income", "definition": "SSI, SSDI, or other disability-based income."},
            {"label": "Veteran Benefits", "definition": "Compensation, pension, survivor, or other veteran benefit claims."},
            {"label": "Benefits Navigation", "definition": "Screening and hands-on application help for public benefits."},
            {"label": "Health Coverage", "definition": "Enrollment in publicly funded medical coverage."},
            {"label": "Rent/Mortgage Aid", "definition": "Financial help paying rent or a mortgage."},
            {"label": "Housing Subsidies", "definition": "Ongoing tenant- or project-based help reducing housing costs."},
            {"label": "Deposit Assistance", "definition": "Financial help with rental or utility deposits."},
            {"label": "Utility Aid", "definition": "Financial help paying electric, gas, water, phone, or internet bills."},
            {"label": "Child Care Aid", "definition": "Subsidies or payments that help a household obtain child care."},
            {"label": "Education Aid", "definition": "Scholarships, tuition aid, or other direct help paying education costs."},
            {"label": "Medical Cost Aid", "definition": "Charity care or other direct help with medical costs."},
            {"label": "Emergency Grants", "definition": "Flexible or expense-specific crisis grants not captured by another Type."},
            {"label": "Tax Preparation", "definition": "Free tax filing and help claiming refundable credits."},
            {"label": "Debt/Credit Counseling", "definition": "Counseling for debt, credit, budgeting, and financial decisions."},
            {"label": "Caregiver Aid", "definition": "Financial help that enables unpaid caregivers to obtain respite or support."},
            {"label": "Funeral Assistance", "definition": "Financial help with funeral or burial expenses."},
        ],
        "assignments": {
            "106d516390d810b1989b53d59ae806c9": ["Rent/Mortgage Aid", "Utility Aid", "Tax Preparation"],
            "5f72f3c9e07e90867dc016da33c05457": ["Benefits Navigation"],
            "b48b75beadedb73dd0606ffb3dcc568d": ["Child Care Aid", "Benefits Navigation"],
            "c11d6b3cdb3f6531bae81d7ec38e1e9e": ["Cash Assistance", "Benefits Navigation"],
            "fb402105bec44e0623b4ccf8d7064802": ["Veteran Benefits", "Emergency Grants"],
            "855ec83aea4c5bc38c85275c8fc38459": ["Emergency Grants"],
            "855aea5e0d3d3b07f11e7bb81212e4d2": ["Health Coverage"],
            "653100ce23fc3523104581629632c77c": ["Utility Aid"],
            "413ff589842e5d267a528fa2221b032a": ["Utility Aid"],
            "c6862828db3631873bf2eb1f4ff99bea": ["Benefits Navigation"],
            "343c5cdfd5f0ec79247f90e12f1088d6": ["Tax Preparation"],
            "5a185dff18772905536e3488f7b75129": ["Rent/Mortgage Aid", "Utility Aid", "Benefits Navigation", "Funeral Assistance"],
            "27adbd6da40ba1d0325ed17d523a3e94": ["Rent/Mortgage Aid", "Deposit Assistance"],
            "987a8b8eb5e82e8c0216ef7bb436693f": ["Deposit Assistance"],
            "4d728e518eb341e958f91d67d4cac4cd": ["Rent/Mortgage Aid", "Utility Aid", "Deposit Assistance"],
            "38629d0e712141f7531b4cff4b0bfd53": ["Benefits Navigation", "Caregiver Aid"],
            "087b0bd908ca3082b11b8f637137b181": ["Debt/Credit Counseling"],
            "bcc694b6232b6b88cd40c57d3052f4ca": ["Rent/Mortgage Aid", "Utility Aid", "Deposit Assistance"],
            "a3782d71fb0f13f124d33c95dadd779c": ["Rent/Mortgage Aid", "Deposit Assistance"],
            "ff1488daaf584a5c3e58c81b4e22bf10": ["Rent/Mortgage Aid"],
            "8d70eda15ed4d365bd3ffb2577c8653e": ["Disability Income"],
            "5fd29d6c772cabbc8a6abc6614f9d3bd": ["Rent/Mortgage Aid", "Utility Aid"],
            "f3e278c9cf9fd269e07fa88724f2f949": ["Utility Aid"],
            "13cf776353746eb632703023c26e9365": ["Utility Aid", "Emergency Grants"],
            "fcdf7044337d12d9e7bdd3a7a732fd08": ["Rent/Mortgage Aid", "Utility Aid"],
            "b21220ad00416ac580741d14ba3a1e7d": ["Caregiver Aid"],
            "b47b61d084512681adb9c7ccacf2268c": ["Caregiver Aid"],
            "617d4be1951f67468b5ddffdb2f670f5": ["Housing Subsidies"],
            "bd13f813cdf1a52f4297b41d93bea46b": ["Benefits Navigation", "Health Coverage"],
            "10c59c16ac8288d92ae7a7626edf06ab": ["Benefits Navigation", "Health Coverage"],
            "2a530b4a56b21439a952af2ac753f12f": ["Benefits Navigation", "Health Coverage"],
            "95aabc4180655feea072d1fcba13461c": ["Benefits Navigation"],
            "9674f1a708712c74c41c9d591821a356": ["Benefits Navigation"],
            "2bf6edeedd27a167fa3b1ba584d2c7c4": ["Benefits Navigation"],
            "da4f4b5a717ae241f3363cc09eb4298a": ["Benefits Navigation"],
            "996b322aa685b24c16a5bbea4b68ed0e": ["Benefits Navigation"],
            "8fbf07bdf33a69f83a1afc375c0f66d3": ["Benefits Navigation"],
            "9630eddb85bca6d59fb0dc70da0935a8": ["Benefits Navigation", "Health Coverage"],
            "9b72f8059923e0a5e6d1dca60a9dd708": ["Benefits Navigation", "Health Coverage"],
            "e0bfbea73949f1e8965c6c1ad4eeb1ff": ["Education Aid"],
            "84f48c34515e9e8aa0bce9ff7796631c": ["Education Aid"],
            "86ea9f4c3e5c68d6ad0bcabf51e500c6": ["Education Aid"],
            "4ae8876a9b82a7f0a606939254d87bb8": ["Medical Cost Aid"],
            "773f0771a3cca46a7a57189d17a58a01": ["Rent/Mortgage Aid", "Utility Aid"],
            "6f709ac3eafa28d894f99dad814a2430": ["Rent/Mortgage Aid", "Utility Aid"],
            "51cfce1c2944ef0453c793aba1923e08": ["Housing Subsidies", "Deposit Assistance"],
            "c922c1358349b26864bc1c2f50341b2c": ["Housing Subsidies"],
            "36a1aba6efe7a704aa4ca190a4f82467": ["Rent/Mortgage Aid"],
            "e81a4666fa9fdf3874524e595834798c": ["Housing Subsidies"],
            "d0eeddd67746f3a298eaf4969b6e9bd1": ["Rent/Mortgage Aid", "Utility Aid"],
            "472c5150aa06dba907ba0bdd1106599e": ["Utility Aid"],
            "e65a5ab33ccf6b355ca9b21969c6617e": ["Utility Aid"],
            "5b6667d5d6350f7b3c4e9c94b1b17de1": ["Utility Aid"],
            "8b0cbd343a20dc0118ec3fa8c9a17d1f": ["Utility Aid"],
            "7d48baeb2cd113386712a5ec693abb8c": ["Utility Aid"],
            "726f13326a74a1f5d347c70575ea49e7": ["Utility Aid"],
            "774e5a59b471ceacca5d0fe7cc5e787b": ["Utility Aid", "Emergency Grants"],
            "3c04b13381e97f377ba21e3c86d0b12c": ["Emergency Grants"],
        },
        "boundary": (
            "Include direct money, payment, credit, subsidy, coverage, or hands-on "
            "financial-benefit assistance. Free or sliding-fee service and ordinary "
            "referral mentions do not qualify. The funded expense or financial pathway "
            "is a Type; urgency, availability, and population eligibility belong in "
            "access details or For groups."
        ),
    },
    "education": {
        "types": [
            {"label": "Early Learning", "definition": "Education and school-readiness services before kindergarten."},
            {"label": "Early Intervention", "definition": "Developmental education and intervention for infants and toddlers."},
            {"label": "Adult Basic Education", "definition": "Foundational reading, writing, math, and adult academic skills."},
            {"label": "GED/HSE", "definition": "Preparation, testing support, or pathways to a high-school equivalency credential."},
            {"label": "English Learning", "definition": "English-language learning for adult speakers of other languages."},
            {"label": "Digital Literacy", "definition": "Foundational computer, internet, and digital participation skills."},
            {"label": "Career Training", "definition": "Occupational, trade, or integrated education and training."},
            {"label": "Apprenticeships", "definition": "Paid learn-and-work pathways combining instruction with supervised employment."},
            {"label": "Postsecondary Education", "definition": "College-level study, advising, scholarships, or transition into college credit."},
            {"label": "High School Education", "definition": "Instruction leading to a standard high-school diploma."},
            {"label": "Online Education", "definition": "A program designed for remote, virtual, or hybrid participation."},
            {"label": "Financial Literacy", "definition": "Education in money management and household financial skills."},
            {"label": "Assistive Technology", "definition": "Devices or software used to make education accessible."},
            {"label": "Education Navigation", "definition": "Hands-on help selecting, funding, or entering an education pathway."},
            {"label": "School Supplies", "definition": "Backpacks, books, and classroom supplies."},
        ],
        "assignments": {
            "067d28b529da7122c5d8c50ff1874faf": ["Early Learning", "Early Intervention"],
            "4ac8a5df1279284d2d5e64df54b5c1dd": ["Assistive Technology"],
            "70ea356cba96bcc304b79ca2a5469f9c": ["Education Navigation"],
            "1ed84b657420da445ac082991959b3f8": ["Early Learning"],
            "c3ab0f1578b4ec24df452d8eee4c9ce6": ["GED/HSE", "English Learning", "Financial Literacy", "Education Navigation"],
            "9c6c63b5207dc97a65b6d8ca95c544e9": ["Adult Basic Education", "GED/HSE", "Career Training"],
            "e0bfbea73949f1e8965c6c1ad4eeb1ff": ["GED/HSE", "Career Training", "Postsecondary Education", "Education Navigation"],
            "ba6cab830d60bb25c2039ae996392523": ["Early Learning", "High School Education"],
            "0904081bbb9ee06085267ef392cd071f": ["Early Learning", "Education Navigation"],
            "61a8d9d4eafa58537df9904250187968": ["Adult Basic Education", "GED/HSE", "English Learning", "Digital Literacy", "Online Education"],
            "14ff82acb2568edc7c0375a29e9c9adc": ["GED/HSE", "English Learning", "Career Training", "Online Education"],
            "14e70b482d501a8d8f0552785827462e": ["Adult Basic Education", "GED/HSE", "English Learning"],
            "cce4f2f7537a93ea0f58d524dc2dd818": ["GED/HSE", "English Learning", "Online Education", "Financial Literacy"],
            "01a9e5b0c362df7fad3f6577a423f91a": ["Postsecondary Education", "Education Navigation"],
            "84f48c34515e9e8aa0bce9ff7796631c": ["GED/HSE", "English Learning", "Postsecondary Education"],
            "d633e161d87ac6cf94df2a2a6b877ab1": ["Adult Basic Education", "GED/HSE", "English Learning", "Digital Literacy", "Online Education"],
            "c44c60fb8e5cd640a4e7725286380d5c": ["Early Learning"],
            "ac9f801d1000fcddb2531ecbf84d8b12": ["Adult Basic Education", "GED/HSE", "English Learning", "Digital Literacy", "Career Training", "Online Education"],
            "86ea9f4c3e5c68d6ad0bcabf51e500c6": ["Adult Basic Education", "GED/HSE", "English Learning", "Career Training", "Postsecondary Education", "Online Education", "Education Navigation"],
            "83267695e503b95086c083b44a8befde": ["GED/HSE", "Career Training"],
            "ebac95249761b88323fc73b4e26259fd": ["School Supplies"],
            "6ce0d0fd810d670dae505e267ea6e01a": ["School Supplies"],
            "c74ea9adad61a6ff3fd9e49ae50d61d2": ["School Supplies"],
            "edacb348adc1480fe0ac0b9b6f1e8580": ["School Supplies"],
            "b48b75beadedb73dd0606ffb3dcc568d": [
                "Early Intervention", "Education Navigation",
            ],
            "90ef7bed032bcd935b0f82e65f664917": [
                "Early Intervention", "Education Navigation",
            ],
            "eb94f24384f8e51a2b237d7d8c507948": [
                "Early Intervention", "Education Navigation",
            ],
            "f95aad04c5e72f66f324d9875d7caffd": [
                "Career Training", "Apprenticeships", "Education Navigation",
            ],
            "7f314bc451d77d01f553d4527407d06d": ["Education Navigation"],
            "6ea1c2067f6e451532d3bd346cc56276": [
                "Career Training", "Postsecondary Education", "Education Navigation",
            ],
            "d72b099aea9d25b5ed7f4eafa274da78": [
                "Digital Literacy", "Career Training",
            ],
            "31c5097bb2e3cc1075a6851e27fb88ec": [
                "Career Training", "Apprenticeships", "Education Navigation",
            ],
            "61f0dba0328b11a9ae6db84f7e5e5f81": [
                "Career Training", "Apprenticeships", "Education Navigation",
            ],
            "f5956fe09395d25458ca9fda67d737c9": ["Career Training"],
        },
        "boundary": (
            "Include actual academic, literacy, credential, career-training, early-"
            "learning, or early-intervention pathways and hands-on help entering them. "
            "Job coaching, ordinary referrals, parenting classes, health education, "
            "and recovery education remain with the need they primarily address. "
            "Disability, language community, justice history, age, and parent status "
            "belong in For groups except when they name the instruction itself."
        ),
    },
    "employment": {
        "types": [
            {"label": "Career Planning", "definition": "Assessment, goal setting, and one-to-one career navigation."},
            {"label": "Job Readiness", "definition": "Resume, interview, workplace, and job-search preparation."},
            {"label": "Job Search & Placement", "definition": "Job matching, employer connections, placement, and hiring events."},
            {"label": "Skills Training", "definition": "Occupational or employability training tied to work."},
            {"label": "Credentials", "definition": "Industry certificates or recognized workforce credentials."},
            {"label": "Apprenticeships", "definition": "Paid learn-and-work apprenticeship pathways."},
            {"label": "Staffing/Temp Work", "definition": "Direct access to temporary, part-time, or staffing placements."},
            {"label": "Supported Employment", "definition": "Individualized employment support for workers needing ongoing assistance."},
            {"label": "Job Coaching", "definition": "Coaching before placement, on the job, or during adjustment."},
            {"label": "Benefits Counseling", "definition": "Work-incentive guidance for people receiving SSI or SSDI."},
            {"label": "Transitional Work", "definition": "Paid, low-barrier work used as a bridge to regular employment."},
            {"label": "Entrepreneurship", "definition": "Training or support for starting and operating a small business."},
            {"label": "Retention Support", "definition": "Follow-up help intended to sustain employment after placement."},
        ],
        "assignments": {
            "7f314bc451d77d01f553d4527407d06d": ["Career Planning", "Job Readiness", "Job Search & Placement"],
            "95aabc4180655feea072d1fcba13461c": ["Career Planning", "Job Search & Placement", "Benefits Counseling"],
            "a121b7ac06dc9b9ef503e462d5cffdd8": ["Career Planning", "Job Readiness"],
            "8db24b98270f7864dadcb0f97b901a53": ["Skills Training", "Job Coaching"],
            "7de41696b045cd6fdb9bb5c25cf7c53f": ["Career Planning", "Job Readiness"],
            "a90b957439ba736a20a0eb129322891e": [
                "Career Planning", "Job Readiness",
            ],
            "08a7877a32a11b9f8531fa95f2a64ade": ["Career Planning", "Skills Training", "Job Search & Placement", "Job Coaching"],
            "6be73b6539fd16b3a6c84ffad77aace8": ["Career Planning", "Skills Training", "Job Search & Placement", "Supported Employment", "Job Coaching"],
            "f95aad04c5e72f66f324d9875d7caffd": ["Career Planning", "Job Readiness", "Job Search & Placement", "Skills Training", "Apprenticeships"],
            "193621d2449346f5eb4f3fe57535ad47": [
                "Career Planning", "Job Readiness", "Job Search & Placement",
            ],
            "a9d82c588239bf51cb761861ce2ef062": ["Job Readiness", "Job Search & Placement", "Job Coaching"],
            "70ea356cba96bcc304b79ca2a5469f9c": ["Career Planning", "Job Readiness"],
            "00cca473db91285a4a393f5ba53add8f": ["Supported Employment", "Job Coaching"],
            "5b3220f8a547f64ec5b3171b0af3217e": ["Career Planning", "Skills Training", "Credentials", "Job Search & Placement"],
            "6ea1c2067f6e451532d3bd346cc56276": ["Career Planning", "Job Readiness", "Skills Training", "Credentials"],
            "df171bb522d8c9a10c10b5c20e52cc1b": ["Career Planning", "Job Readiness", "Job Coaching"],
            "ffb70295ec3f1e3256fc1955ec7ad5c0": ["Staffing/Temp Work", "Job Search & Placement"],
            "f5956fe09395d25458ca9fda67d737c9": ["Career Planning", "Skills Training", "Job Coaching"],
            "d72b099aea9d25b5ed7f4eafa274da78": ["Career Planning", "Job Readiness", "Skills Training", "Credentials", "Job Search & Placement"],
            "8228b3327c959acccf53469fa50397a9": ["Skills Training", "Entrepreneurship"],
            "39c84c2f6b4b921b9749108467c670c8": ["Job Readiness", "Job Search & Placement", "Job Coaching"],
            "9dfa946fc15127053ce6832817955b2d": ["Career Planning", "Job Search & Placement", "Retention Support"],
            "133e5f492400dff139f2cafa0b8f67c2": ["Job Readiness", "Supported Employment", "Job Coaching"],
            "38458692f5f4f52d5927866563f7f622": ["Job Search & Placement", "Job Coaching"],
            "61f0dba0328b11a9ae6db84f7e5e5f81": ["Apprenticeships", "Credentials"],
            "a4e45e62c0b9cb505d5b4874340871fb": ["Career Planning"],
            "31c5097bb2e3cc1075a6851e27fb88ec": ["Career Planning", "Skills Training", "Apprenticeships"],
            "6db9a956ed478b1134399954d600ab53": ["Career Planning", "Job Search & Placement", "Supported Employment"],
            "9f520ac58c4f06d5efdcd58cffb47a01": ["Job Readiness", "Job Search & Placement", "Supported Employment", "Job Coaching"],
            "83d02712bba592a7bc59214e02c13b72": ["Job Readiness", "Job Search & Placement", "Transitional Work"],
            "eac51d2e41cab50d1711a49e1f926ff0": ["Job Readiness", "Job Search & Placement", "Supported Employment", "Job Coaching", "Retention Support"],
            "2af79fdd0101ee3a198c732086f9bfc6": [
                "Career Planning", "Job Readiness", "Job Search & Placement",
            ],
            "b8c4699661c4d07b777efdab9ccb9d68": ["Career Planning", "Job Search & Placement"],
            "c3ab0f1578b4ec24df452d8eee4c9ce6": [
                "Career Planning", "Job Readiness",
            ],
            "9c6c63b5207dc97a65b6d8ca95c544e9": [
                "Skills Training", "Credentials",
            ],
            "e0bfbea73949f1e8965c6c1ad4eeb1ff": [
                "Skills Training", "Credentials",
            ],
            "14ff82acb2568edc7c0375a29e9c9adc": [
                "Skills Training", "Credentials",
            ],
            "61a8d9d4eafa58537df9904250187968": ["Skills Training"],
            "d633e161d87ac6cf94df2a2a6b877ab1": ["Job Readiness"],
            "ac9f801d1000fcddb2531ecbf84d8b12": [
                "Job Readiness", "Skills Training",
            ],
            "86ea9f4c3e5c68d6ad0bcabf51e500c6": [
                "Skills Training", "Credentials",
            ],
            "83267695e503b95086c083b44a8befde": [
                "Skills Training", "Credentials",
            ],
        },
        "boundary": (
            "Include an identifiable employment pathway that can be accessed as an "
            "employment service. Incidental employment assistance bundled into shelter, "
            "healthcare, or another program does not qualify without a named workforce "
            "or career pathway. Occupational education can also appear in Education; "
            "work clothing and transportation remain separate needs, while disability, "
            "veteran status, and justice history belong in For groups."
        ),
    },
    "addiction": {
        "types": [
            {"label": "Overdose/Crisis Line", "definition": "Immediate phone triage for overdose, poisoning, withdrawal, or addiction crisis."},
            {"label": "Detox/Withdrawal", "definition": "Medical or clinically supervised withdrawal management and stabilization."},
            {"label": "Residential Treatment", "definition": "Live-in substance-use treatment with structured clinical programming."},
            {"label": "Residential Recovery", "definition": "Structured live-in recovery programming that is not represented as clinical residential treatment."},
            {"label": "Outpatient Treatment", "definition": "Scheduled addiction treatment while the participant lives in the community."},
            {"label": "Intensive Outpatient", "definition": "A higher-frequency structured outpatient treatment program."},
            {"label": "Medication Treatment", "definition": "Methadone, buprenorphine, naltrexone, or other medication for addiction treatment."},
            {"label": "Recovery Housing", "definition": "Substance-free housing organized to support continuing recovery."},
            {"label": "Harm Reduction", "definition": "Naloxone, safer-use supplies, and practical overdose-risk reduction."},
            {"label": "Peer Support", "definition": "Recovery mentoring, peer accountability, or other recovery support delivered by peers."},
            {"label": "Support Groups", "definition": "Organized mutual-support groups such as AA, NA, or SMART Recovery; no matching resource is present in the frozen Mesa corpus."},
            {"label": "Co-occurring Treatment", "definition": "Integrated treatment for substance use and mental-health conditions."},
            {"label": "Treatment Court", "definition": "Court-supervised treatment and recovery planning as an alternative pathway."},
            {"label": "Counseling", "definition": "Individual or group substance-use counseling."},
        ],
        "assignments": {
            "ea77fba8e182ba83a7f60438bece546b": ["Detox/Withdrawal", "Intensive Outpatient", "Co-occurring Treatment"],
            "d35297757ca15962989aba2961f35f7c": ["Overdose/Crisis Line"],
            "86255417090cba31f14b0d7e9334d157": ["Outpatient Treatment", "Recovery Housing", "Peer Support"],
            "a3f2ae86957032ff2779178a2891f1aa": ["Outpatient Treatment", "Medication Treatment"],
            "3c1ab6d4b53e590caf1c3f0cf433a714": ["Overdose/Crisis Line"],
            "18462adf6dd0d47ac76fba2161b70dfc": ["Outpatient Treatment"],
            "f3014f72c63050649dc92f5e52e88e1b": ["Detox/Withdrawal", "Residential Treatment", "Intensive Outpatient"],
            "b9affc7e4a6b284ed2bdae319aaa486a": "no-type-needed",
            "5b415ee3078420f7b8081b605d1d087a": ["Detox/Withdrawal", "Residential Treatment", "Outpatient Treatment", "Co-occurring Treatment"],
            "f2e69a8b2402313065411a32eaa02190": ["Detox/Withdrawal", "Residential Treatment", "Outpatient Treatment", "Co-occurring Treatment"],
            "7018bb19aca15772a0b8d95cca1f3e50": ["Outpatient Treatment", "Medication Treatment"],
            "349f6314644d54f9964a53688887cc47": ["Residential Treatment", "Outpatient Treatment"],
            "02a5844cdf8b81c34ec1931a9f2fc033": ["Detox/Withdrawal", "Residential Treatment", "Outpatient Treatment", "Medication Treatment"],
            "db242d7df7b5e913727adc08e1ab4029": ["Detox/Withdrawal", "Outpatient Treatment"],
            "25eba00c6cbab9b8fd1950d2938172b3": ["Residential Treatment"],
            "6b2d7fcadeec59dea6cd835e732ef55f": ["Outpatient Treatment", "Co-occurring Treatment"],
            "aa9a90d7f959067cb0447b4e06a5cb13": ["Treatment Court"],
            "87c3e010d39aad60d9640f059b834c21": "no-type-needed",
            "cfddfe7aec2aa52de1a56c0d3d797d9e": ["Residential Treatment", "Intensive Outpatient", "Recovery Housing", "Peer Support", "Counseling"],
            "815148d4fe10fdbf28f981c14050256c": ["Residential Treatment", "Peer Support", "Co-occurring Treatment"],
            "1ed078050fc55c8c0fba211d3b8e8c0e": ["Outpatient Treatment", "Medication Treatment", "Counseling", "Harm Reduction"],
            "4ad64cc79738db00fc4c12cac4481fd5": ["Detox/Withdrawal"],
            "a21c310d2a515339bb648af71577d74d": ["Recovery Housing", "Peer Support"],
            "edc5a63f8239da2c402f528da2718669": ["Residential Recovery"],
            "a307aa54e93fa408dcb6fe7de0251cd2": ["Outpatient Treatment", "Intensive Outpatient"],
            "34bce41d6bcc0b3799d9636d6e0dff8b": ["Residential Recovery"],
            "617d4be1951f67468b5ddffdb2f670f5": ["Residential Treatment"],
            "726cf5766a37f0365d98aa314e95df52": ["Detox/Withdrawal", "Residential Treatment", "Medication Treatment", "Co-occurring Treatment"],
            "18e8c38632cddf6bfd6e57ae47b1f436": ["Outpatient Treatment", "Medication Treatment", "Counseling"],
            "5f7fa3abe7c319ad1bd03122a3caae11": ["Detox/Withdrawal", "Residential Treatment", "Outpatient Treatment", "Recovery Housing"],
            "14d40b4e4bdd71c67e009326f3716119": ["Residential Treatment", "Co-occurring Treatment"],
            "56082a4920ef5e52ae645088882ab65d": ["Harm Reduction"],
            "446d7aeaa7a45f7bab5d72f34d1b10e3": ["Residential Treatment", "Outpatient Treatment", "Medication Treatment", "Harm Reduction", "Counseling", "Co-occurring Treatment"],
            "5494e7153548657ba7384d98b5d24247": ["Residential Treatment", "Recovery Housing", "Peer Support"],
            "2af79fdd0101ee3a198c732086f9bfc6": ["Counseling"],
            "0be7372bda5d130e905a555ea663b1aa": ["Detox/Withdrawal", "Residential Treatment", "Outpatient Treatment", "Medication Treatment"],
        },
        "boundary": (
            "Types describe treatment and recovery methods. Clinical residential "
            "treatment, structured nonclinical residential recovery programs, and "
            "recovery housing are distinct. Substance, gender, age, pregnancy, veteran "
            "status, and justice history belong in For groups or clinical access details."
        ),
    },
    "medical-dental-vision": {
        "types": [
            {"label": "Primary Care", "definition": "General preventive, diagnostic, and ongoing medical care."},
            {"label": "Dental Care", "definition": "Preventive, restorative, emergency, or specialty oral healthcare."},
            {"label": "Vision Care", "definition": "Eye exams, treatment, low-vision care, or corrective lenses."},
            {"label": "Prenatal/Postpartum", "definition": "Medical care during pregnancy, birth, and the postpartum period."},
            {"label": "Pediatrics", "definition": "Medical care for infants, children, and adolescents."},
            {"label": "Reproductive Health", "definition": "Family planning, gynecological, and other non-pregnancy reproductive healthcare."},
            {"label": "Same-day Care", "definition": "Walk-in or same-day care for an immediate non-emergency need."},
            {"label": "Specialty Care", "definition": "Specialist evaluation or treatment beyond primary care."},
            {"label": "Hospital Care", "definition": "Hospital-based inpatient, maternity, or advanced medical care."},
            {"label": "Medical Respite", "definition": "Short-term recuperative care for someone unable to recover safely at home."},
            {"label": "Adult Day Health", "definition": "Daytime care with nursing, health monitoring, and personal assistance."},
            {"label": "Health Coverage", "definition": "Enrollment in or access to publicly funded medical coverage."},
            {"label": "Pharmacy/Medication", "definition": "Prescription medication or on-site pharmacy access."},
            {"label": "Telehealth", "definition": "Medical care designed for remote participation."},
            {"label": "Home Visiting", "definition": "Health and developmental support delivered through planned home visits."},
            {"label": "Doula Support", "definition": "Labor, delivery, and postpartum support from a doula."},
            {"label": "Physical Rehabilitation", "definition": "Physical therapy and rehabilitation for injury, illness, or functional recovery."},
            {"label": "Vision Rehabilitation", "definition": "Independent-living, assistive-technology, and functional support for vision loss."},
            {"label": "Medical Equipment", "definition": "Wheelchairs, walkers, hospital beds, oxygen, or other durable medical equipment; no matching resource is present in the frozen Mesa corpus."},
            {"label": "Pregnancy Testing", "definition": "Clinical or community pregnancy testing."},
        ],
        "assignments": {
            "215c9744b5c85f565edf132c428bb77c": ["Dental Care", "Specialty Care"],
            "33b8cbd29cf68ac3a07e0fd8d984771b": ["Primary Care", "Dental Care", "Prenatal/Postpartum", "Pediatrics", "Reproductive Health", "Health Coverage"],
            "bd13f813cdf1a52f4297b41d93bea46b": ["Primary Care", "Dental Care", "Prenatal/Postpartum", "Pediatrics", "Reproductive Health", "Same-day Care", "Pharmacy/Medication", "Telehealth", "Health Coverage"],
            "debb9e4a689060f00162da9ac2f8063b": ["Adult Day Health"],
            "8db24b98270f7864dadcb0f97b901a53": ["Vision Care", "Vision Rehabilitation"],
            "a90b957439ba736a20a0eb129322891e": ["Health Coverage"],
            "855aea5e0d3d3b07f11e7bb81212e4d2": ["Health Coverage"],
            "a246f47cd18fc8d7b1bfa520a0451300": ["Health Coverage"],
            "10c59c16ac8288d92ae7a7626edf06ab": ["Health Coverage"],
            "0474f03b486642977ecad2860ffac719": ["Prenatal/Postpartum", "Hospital Care"],
            "18462adf6dd0d47ac76fba2161b70dfc": ["Prenatal/Postpartum", "Specialty Care"],
            "ed9cec6557722e44984887fb41637d6e": ["Pregnancy Testing"],
            "69bc2e9938b04722b0c8cdc1d67dadc8": ["Primary Care", "Medical Respite", "Physical Rehabilitation"],
            "0904081bbb9ee06085267ef392cd071f": ["Vision Care", "Vision Rehabilitation"],
            "2a530b4a56b21439a952af2ac753f12f": ["Health Coverage"],
            "ec74c1192ef14f1debb3a31c912a1bbc": ["Prenatal/Postpartum", "Home Visiting", "Doula Support"],
            "9440dc735d5b0aada418ed90bf5c3ad5": ["Dental Care"],
            "3f0d047be9ce5a319562cf127b3b4af1": ["Vision Care", "Specialty Care", "Vision Rehabilitation"],
            "1d201eebb46032309abebb86f3d470ad": ["Primary Care", "Vision Care", "Specialty Care", "Pharmacy/Medication"],
            "af6fce2b1b9927a1669f390313d56ae6": ["Primary Care", "Dental Care", "Prenatal/Postpartum", "Pediatrics", "Reproductive Health", "Pharmacy/Medication"],
            "111bbc8293126891b0ecef093e94874c": ["Primary Care", "Prenatal/Postpartum", "Pediatrics", "Reproductive Health"],
            "edd25249cae3302c71dfdf01ed68fd86": ["Primary Care", "Dental Care", "Same-day Care", "Pharmacy/Medication", "Telehealth"],
            "0aa8df276d838df3292303f1e1e5fb1f": ["Vision Care"],
            "363ba896bb14a4dc850081cd818533c7": ["Primary Care", "Specialty Care", "Reproductive Health", "Physical Rehabilitation"],
            "029031368b1b87b942199b97cb2ac47f": ["Prenatal/Postpartum", "Home Visiting"],
            "948dd967fb329f7e5f04c0814a113889": ["Primary Care", "Specialty Care", "Telehealth"],
            "c7a3916ed96ea82d06f37910ddf70670": ["Primary Care", "Prenatal/Postpartum", "Pediatrics", "Reproductive Health", "Pharmacy/Medication"],
            "4ae8876a9b82a7f0a606939254d87bb8": ["Primary Care", "Dental Care", "Specialty Care", "Hospital Care", "Reproductive Health", "Pharmacy/Medication"],
            "aee416211643d092d52e82a4470df12b": ["Prenatal/Postpartum", "Pediatrics"],
            "1d36ae0a82e6d1f6c264334db09e578c": ["Primary Care", "Prenatal/Postpartum", "Pediatrics", "Reproductive Health", "Health Coverage"],
        },
        "boundary": (
            "Types describe a healthcare service line or a direct access pathway. "
            "Pediatrics and Prenatal/Postpartum describe care actually delivered; Youth "
            "and Pregnant/postpartum separately describe whom a resource targets or "
            "accommodates. Health Coverage requires a direct application, enrollment, "
            "or accountable eligibility-help pathway rather than a vague referral. "
            "Other population traits remain For groups or access details."
        ),
    },
    "mental-health": {
        "types": [
            {"label": "Crisis Line", "definition": "Immediate phone or text counseling, triage, and crisis connection."},
            {"label": "Crisis Center", "definition": "Walk-in assessment and short-term psychiatric crisis stabilization."},
            {"label": "Inpatient Psychiatry", "definition": "Hospital-based inpatient psychiatric treatment."},
            {"label": "Intensive Outpatient", "definition": "Higher-frequency outpatient mental-health treatment; no confirmed matching program is present in the frozen Mesa corpus."},
            {"label": "Partial Hospitalization", "definition": "Structured daytime psychiatric treatment without an overnight hospital stay; no confirmed matching program is present in the frozen Mesa corpus."},
            {"label": "Outpatient Counseling", "definition": "Individual, family, or group therapy while living in the community."},
            {"label": "Psychiatry/Medication", "definition": "Psychiatric evaluation, prescribing, and medication management."},
            {"label": "Support Groups", "definition": "Facilitated mutual support around a shared experience or loss."},
            {"label": "Peer Support", "definition": "Support delivered by trained peers with relevant lived experience."},
            {"label": "Case Management", "definition": "Ongoing coordination across behavioral-health and practical supports."},
            {"label": "School-based Counseling", "definition": "Behavioral-health care delivered through a school setting."},
            {"label": "Home/Community Therapy", "definition": "Therapy delivered in the home or other community setting."},
            {"label": "Telehealth", "definition": "Behavioral-health care designed for remote participation."},
            {"label": "TMS", "definition": "Transcranial magnetic stimulation for treatment-resistant depression."},
            {"label": "Care Navigation", "definition": "Assessment, referral, and accountable connection to continuing mental-health care."},
            {"label": "Residential Treatment", "definition": "Live-in behavioral-health treatment outside an inpatient hospital."},
            {"label": "Post-discharge Support", "definition": "Proactive contact and support following psychiatric discharge."},
        ],
        "assignments": {
            "d35297757ca15962989aba2961f35f7c": ["Crisis Line", "Care Navigation"],
            "a90b957439ba736a20a0eb129322891e": ["Care Navigation"],
            "9b2e1d3d132d014c286fb5c927bad782": ["Inpatient Psychiatry", "Outpatient Counseling"],
            "34dc7c352ceb97ec5831aaa7cb4d3904": ["Support Groups"],
            "18462adf6dd0d47ac76fba2161b70dfc": ["Outpatient Counseling"],
            "20cf2620b396a3fc5a0d270ade9af911": ["Crisis Center", "Residential Treatment", "Outpatient Counseling", "Peer Support", "Case Management"],
            "f2e69a8b2402313065411a32eaa02190": ["Residential Treatment", "Outpatient Counseling"],
            "00248a03e5cb559202ed1b50d6c982cd": ["Crisis Center"],
            "1e0e0a4f5d91fe1401e3730594313ad7": ["Outpatient Counseling", "Psychiatry/Medication", "Case Management", "Telehealth"],
            "f0e0dca057e2ec54e46f72a3bdadd85e": ["Outpatient Counseling", "Care Navigation"],
            "178f4c9a2aad9917c8c4045cf229a5f6": ["Outpatient Counseling", "Psychiatry/Medication", "TMS"],
            "f0f7981734b5bec0944a973258177571": ["School-based Counseling", "Outpatient Counseling"],
            "8f5bf98773af65b68a2a025cff1b0d59": ["Support Groups"],
            "76659e8b276782e5713d685b43231655": ["Outpatient Counseling"],
            "e8ecc3d007c722810d2f5ada79c32e6b": ["Outpatient Counseling", "Psychiatry/Medication", "Support Groups", "Peer Support", "Case Management", "Home/Community Therapy"],
            "ce0a9cdfa73bbb3fdafb2603d8099f40": ["Support Groups"],
            "ec74c1192ef14f1debb3a31c912a1bbc": ["Care Navigation"],
            "aa9a90d7f959067cb0447b4e06a5cb13": ["Care Navigation"],
            "9630eddb85bca6d59fb0dc70da0935a8": ["Crisis Center", "Psychiatry/Medication", "Care Navigation"],
            "815148d4fe10fdbf28f981c14050256c": ["Outpatient Counseling", "Peer Support", "Case Management"],
            "5065a00c9613e2e388a9dce511778b9d": ["Outpatient Counseling"],
            "f6b55e24c78fb7889c9767c7527512ea": ["Crisis Line", "Peer Support", "Post-discharge Support"],
            "9b72f8059923e0a5e6d1dca60a9dd708": ["Outpatient Counseling", "Psychiatry/Medication", "Case Management", "Telehealth"],
            "2888d7f802c66d6db7f0cdfc3d5f1b36": ["Outpatient Counseling", "Peer Support", "Care Navigation"],
            "237f5067019044739acab5aab0d38cd1": ["Outpatient Counseling", "School-based Counseling", "Home/Community Therapy", "Telehealth"],
            "2af79fdd0101ee3a198c732086f9bfc6": ["Outpatient Counseling"],
            "b0d2eba21896a98631e48b8982248936": ["Outpatient Counseling", "Psychiatry/Medication", "Case Management", "Telehealth", "Care Navigation"],
            "ee05bdb730c5b3f705057f47a59a2df9": ["Inpatient Psychiatry", "Outpatient Counseling", "Psychiatry/Medication", "Telehealth"],
            "1d36ae0a82e6d1f6c264334db09e578c": ["Outpatient Counseling"],
        },
        "boundary": (
            "Include direct mental-health treatment or an accountable assessment, "
            "referral, and continuing-care pathway. An incidental or vague referral "
            "does not qualify. Types describe the care setting and method; diagnosis, "
            "age, pregnancy, veteran status, justice history, and language belong in "
            "For groups or clinical details."
        ),
    },
    "legal": {
        "types": [
            {"label": "General Civil Legal Help", "definition": "Free or affordable advice or representation across civil legal problems."},
            {"label": "Protective Orders", "definition": "Orders of protection and injunctions against harassment."},
            {"label": "Family Law", "definition": "Divorce, custody, parenting time, child support, and related family matters."},
            {"label": "Guardianship", "definition": "Help establishing or changing legal guardianship, including kinship-care situations."},
            {"label": "Housing/Eviction Law", "definition": "Tenant, eviction, rental, and housing-related legal help."},
            {"label": "Immigration Law", "definition": "Legal help with immigration filings, status, or humanitarian relief."},
            {"label": "Criminal Record Relief", "definition": "Set-asides, sealing, expungement, and restoration of rights."},
            {"label": "Criminal Defense", "definition": "Advice or representation for criminal charges, including misdemeanors."},
            {"label": "Disability Rights", "definition": "Advocacy involving disability access, discrimination, education, or institutional rights."},
            {"label": "Consumer/Fraud", "definition": "Consumer protection, scams, fraud, and financial exploitation."},
            {"label": "Debt/Bankruptcy", "definition": "Debt collection, bankruptcy, and related financial legal help; no matching resource is present in the frozen Mesa corpus."},
            {"label": "Benefits Appeals", "definition": "Legal help challenging denial or termination of public benefits; no matching resource is present in the frozen Mesa corpus."},
            {"label": "Employment Law", "definition": "Wage, workplace-rights, and employment-discrimination help; no matching resource is present in the frozen Mesa corpus."},
            {"label": "Abuse/Exploitation", "definition": "Protective or legal action involving abuse, neglect, or exploitation."},
            {"label": "Wills/Probate", "definition": "Wills, trusts, probate, and related estate-planning matters."},
            {"label": "Veteran Claims/Appeals", "definition": "VA benefit claims, administrative appeals, and related veteran matters."},
            {"label": "Discharge Upgrades", "definition": "Legal representation or advocacy to change military discharge status."},
            {"label": "Court Self-help", "definition": "Court forms, legal information, workshops, and brief form review."},
            {"label": "Document Preparation", "definition": "Help completing and filing legal documents without full representation."},
            {"label": "Problem-solving Court", "definition": "Specialized court coordination addressing underlying needs."},
        ],
        "assignments": {
            "ce14bd1aa42c212343ff01bdda80381e": ["Consumer/Fraud", "Abuse/Exploitation"],
            "b47b61d084512681adb9c7ccacf2268c": ["Abuse/Exploitation"],
            "fb402105bec44e0623b4ccf8d7064802": ["Veteran Claims/Appeals", "Discharge Upgrades"],
            "138a8c6f2c950488f75f8766e2ef6252": ["General Civil Legal Help"],
            "ace0c97e80c85b18e515be9d6b44dd3e": ["Family Law", "Immigration Law", "Criminal Record Relief"],
            "c8f5de50d9d41ce30ec0b8b6ef45b249": ["Protective Orders", "Family Law"],
            "59a9c46dfd4d1314edea363898ada9bc": ["Disability Rights"],
            "38629d0e712141f7531b4cff4b0bfd53": ["Family Law", "Guardianship"],
            "528e3dad283cd117ea2ff80b3bec333c": ["Family Law"],
            "4465e68f2478923dfe880de0556150f0": ["Immigration Law"],
            "f6dcb4c45715df15ef11f764c6a40e50": ["Protective Orders", "Family Law", "Document Preparation"],
            "a75559d019132060ea10e3390d9106ab": ["Housing/Eviction Law"],
            "aa9a90d7f959067cb0447b4e06a5cb13": ["Problem-solving Court"],
            "1191caa6a627cab7f478d5fe36466e0a": ["Family Law", "Criminal Record Relief", "Court Self-help"],
            "617d4be1951f67468b5ddffdb2f670f5": ["Criminal Record Relief"],
            "697d063e4304130741aed2b8ab5fc48f": ["Protective Orders", "Family Law", "Document Preparation"],
            "6d4803e545580ed7abc3cd8bb87b1314": ["General Civil Legal Help", "Family Law", "Housing/Eviction Law", "Immigration Law", "Criminal Defense", "Consumer/Fraud", "Wills/Probate"],
            "63094d56f92faa642ec6143be4d44d60": ["Discharge Upgrades"],
            "1c01cd6b13aaf41619e7cdc09b4c6725": ["Veteran Claims/Appeals", "Discharge Upgrades", "Problem-solving Court"],
        },
        "boundary": (
            "Types identify the legal matter or a concrete legal pathway. A resource "
            "must provide legal information, document help, advocacy, representation, "
            "or an accountable protective process; population eligibility alone does "
            "not establish a legal service. Age, disability, survivor status, veteran "
            "status, and justice history belong in For groups."
        ),
    },
    "immigration": {
        "types": [
            {"label": "Citizenship", "definition": "Naturalization applications and citizenship-related filings."},
            {"label": "Family Petitions", "definition": "Petitions and consular processes for qualifying relatives."},
            {"label": "Green Card/Adjustment", "definition": "Permanent-residence applications, adjustment of status, and card renewal."},
            {"label": "Work Authorization", "definition": "Employment authorization applications and renewals."},
            {"label": "DACA", "definition": "Deferred Action for Childhood Arrivals renewals and related filings."},
            {"label": "Humanitarian Relief", "definition": "U visas, T visas, VAWA, SIJS, TPS, and related protections."},
            {"label": "Asylum", "definition": "Affirmative or defensive asylum applications."},
            {"label": "Removal Defense", "definition": "Representation in deportation or removal proceedings."},
            {"label": "Detention Representation", "definition": "Legal representation for people held in immigration detention."},
            {"label": "Document Replacement", "definition": "Replacement of immigration documents and status records."},
            {"label": "Refugee/Asylee Filings", "definition": "Status, family, and integration filings for refugees and asylees."},
            {"label": "Appeals", "definition": "Administrative or court appeals in immigration matters."},
            {"label": "Case Status/Biometrics", "definition": "Official case-status, appointment, interview, and biometrics services."},
        ],
        "assignments": {
            "ac64a1ee6e7d4f2563ae162bd0a12e9d": ["Citizenship", "Family Petitions", "Green Card/Adjustment", "Humanitarian Relief", "Document Replacement", "Refugee/Asylee Filings"],
            "4b42cc9c9bed01788a1fdbfe29248adf": ["Citizenship", "Green Card/Adjustment", "Work Authorization", "Humanitarian Relief"],
            "511ba569ec22349728cb875494668f20": ["Citizenship", "Family Petitions", "Work Authorization", "DACA", "Refugee/Asylee Filings"],
            "89b9bdda24c8a5abd783f15e99dba056": ["Family Petitions", "Green Card/Adjustment", "Work Authorization", "DACA", "Humanitarian Relief", "Asylum", "Removal Defense"],
            "3695184e8d514e52029ab65c18e53728": ["Citizenship", "Family Petitions", "Green Card/Adjustment", "DACA", "Humanitarian Relief"],
            "370e7f0a4f6a63fedd476ff9cc1bfb32": ["Removal Defense", "Detention Representation", "Humanitarian Relief"],
            "4465e68f2478923dfe880de0556150f0": ["Citizenship", "Family Petitions", "Green Card/Adjustment", "DACA", "Humanitarian Relief"],
            "b9950394defba173a07461ac5fa19e67": ["Citizenship", "Family Petitions", "Green Card/Adjustment", "Work Authorization", "Humanitarian Relief"],
            "34603fb44974ece7329a1a2d8ca51f35": ["Citizenship", "Family Petitions", "Document Replacement", "Refugee/Asylee Filings"],
            "8b325c40eea9d85f2dd5afccb96f5993": ["Family Petitions", "Green Card/Adjustment", "Work Authorization", "Refugee/Asylee Filings"],
            "212ecd27650ff9a74102bc122a331934": ["Green Card/Adjustment", "Asylum", "Removal Defense", "Appeals"],
            "dca1d74f147af392005268006630b3ce": ["Case Status/Biometrics"],
        },
        "boundary": "Types identify the immigration matter; language, nationality, culture, refugee identity, age, and survivor status remain For groups when the resource targets or accommodates them.",
    },
    "domestic-violence": {
        "types": [
            {"label": "Crisis Hotline", "definition": "Immediate phone, chat, or text support and safety connection."},
            {"label": "Emergency Shelter", "definition": "Confidential immediate shelter for a survivor fleeing danger."},
            {"label": "Transitional Housing", "definition": "Time-limited survivor housing after immediate crisis shelter."},
            {"label": "Mobile Advocacy", "definition": "Advocacy delivered where the survivor is rather than at a shelter."},
            {"label": "Safety Planning", "definition": "Individual planning to reduce danger and prepare safe next steps."},
            {"label": "Protective Orders", "definition": "Help preparing, filing, or navigating an order of protection."},
            {"label": "Legal Advocacy", "definition": "Legal information, accompaniment, referrals, or representation."},
            {"label": "Counseling & Support", "definition": "Individual counseling, support groups, or trauma support."},
            {"label": "Emergency Financial Aid", "definition": "Flexible funds for immediate survivor safety and stability."},
            {"label": "Address Confidentiality", "definition": "Substitute address and protected mail-forwarding services."},
            {"label": "Forensic Exams", "definition": "Trauma-informed medical forensic examination and evidence services."},
            {"label": "Court Advocacy", "definition": "Court-process explanation, accompaniment, and hearing support."},
            {"label": "Relocation Assistance", "definition": "Help moving or establishing safety in another location."},
            {"label": "Case Management", "definition": "Ongoing coordination of safety, housing, health, and practical services."},
            {"label": "Peer Support", "definition": "Survivor-led or lived-experience support."},
            {"label": "Protective Services", "definition": "Investigation and protective response to abuse, neglect, or exploitation."},
        ],
        "assignments": {
            "db2e8f3b8772791cf254fb9cc04b9838": ["Emergency Shelter", "Transitional Housing", "Safety Planning", "Legal Advocacy", "Counseling & Support", "Case Management"],
            "b60a98183555e1d70e0381cd56c8e16c": ["Crisis Hotline", "Safety Planning"],
            "177117c4ee2b5824559a13d70c603148": ["Crisis Hotline", "Transitional Housing", "Legal Advocacy", "Counseling & Support", "Case Management"],
            "302a889f3d615bd6ab350588df7c39e9": ["Emergency Financial Aid", "Relocation Assistance"],
            "1f4670d227a649fee7dd6451e9624fe2": ["Protective Orders"],
            "18b310b424be337cab93090af8d2d5fd": ["Protective Orders", "Legal Advocacy"],
            "85a5b070658ea4afa6c89b604340e53e": ["Address Confidentiality"],
            "bd8d70a1ed5b94634c74d90a66d1ea64": ["Emergency Shelter", "Mobile Advocacy", "Safety Planning"],
            "b666b49c655c08750bdf54de800e82af": ["Emergency Shelter", "Transitional Housing", "Legal Advocacy", "Counseling & Support", "Case Management"],
            "c8f5de50d9d41ce30ec0b8b6ef45b249": ["Protective Orders", "Legal Advocacy"],
            "f76b64043d73b489d7067d9f9d856b42": ["Emergency Shelter"],
            "7edc59ef2bb7bef8e25a7d32fd382159": ["Mobile Advocacy", "Safety Planning", "Legal Advocacy", "Relocation Assistance"],
            "70b9fd4e146bba9123d1e4e6bb9540d1": ["Forensic Exams"],
            "9b5f0efdd5d35daa147a150ce13c5f6d": ["Mobile Advocacy", "Safety Planning", "Protective Orders", "Court Advocacy", "Counseling & Support", "Case Management"],
            "962a15177e75cb7770115e0b18c9cfa8": ["Safety Planning", "Protective Orders", "Court Advocacy"],
            "0f7c45b87848334794e5e2f98a15f2fc": ["Safety Planning", "Protective Orders", "Court Advocacy"],
            "426b0bcb1722f916832484d3cbb141fd": ["Safety Planning", "Protective Orders", "Legal Advocacy", "Counseling & Support", "Forensic Exams", "Case Management"],
            "ea694e1df9c5ce31796e579520312da9": ["Emergency Shelter"],
            "36fd485bb7ad2ff81df256dbae24025d": ["Crisis Hotline", "Safety Planning"],
            "141b0ffaf944535bcc958d1d62ff4adc": ["Safety Planning", "Legal Advocacy"],
            "ed0745322850d01341f8baf07c69f0a0": ["Emergency Shelter"],
            "626aab0a5b4c6dcd7811605470690fc3": ["Mobile Advocacy", "Safety Planning", "Legal Advocacy", "Counseling & Support"],
            "5c4f74d54fc3bf4246ee0eec1edc078a": ["Crisis Hotline", "Safety Planning", "Peer Support"],
        },
        "boundary": "Types describe survivor interventions; gender, age, disability, language, culture, and relationship identity belong in For groups when targeted or accommodated.",
    },
    "parenting-child-development": {
        "types": [
            {
                "label": "Parenting Education",
                "definition": "Classes, coaching, or practical education for parents and caregivers.",
            },
            {
                "label": "Home Visiting",
                "definition": "Family support delivered through planned visits in the home.",
            },
            {
                "label": "Early Intervention",
                "definition": "Developmental evaluation or intervention for infants and young children.",
            },
            {
                "label": "Child Care",
                "definition": "Supervised care that enables work, school, safety, or family stability.",
            },
            {
                "label": "Early Learning",
                "definition": "Early-childhood learning and school-readiness programming.",
            },
            {
                "label": "Family Resource Center",
                "definition": "A multi-service family hub with activities, education, and navigation.",
            },
            {
                "label": "Family Reunification",
                "definition": "Support for restoring or strengthening parent-child relationships.",
            },
        ],
        "assignments": {
            "33b8cbd29cf68ac3a07e0fd8d984771b": ["Parenting Education"],
            "b48b75beadedb73dd0606ffb3dcc568d": ["Child Care", "Early Intervention"],
            "90ef7bed032bcd935b0f82e65f664917": ["Early Intervention"],
            "eb94f24384f8e51a2b237d7d8c507948": ["Early Intervention"],
            "067d28b529da7122c5d8c50ff1874faf": ["Early Intervention"],
            "193621d2449346f5eb4f3fe57535ad47": ["Family Reunification"],
            "1ed84b657420da445ac082991959b3f8": [
                "Parenting Education", "Early Learning", "Family Resource Center",
            ],
            "ed9cec6557722e44984887fb41637d6e": ["Parenting Education"],
            "2822ad624344c1ae4686dbbb665c3700": [
                "Parenting Education", "Early Learning", "Family Resource Center",
            ],
            "313775a628d6ace7912cbbd7fe30a8a3": [
                "Parenting Education", "Early Learning", "Family Resource Center",
            ],
            "38629d0e712141f7531b4cff4b0bfd53": "no-type-needed",
            "528e3dad283cd117ea2ff80b3bec333c": [
                "Parenting Education", "Family Reunification",
            ],
            "ba6cab830d60bb25c2039ae996392523": [
                "Parenting Education", "Child Care", "Early Learning",
            ],
            "a6043035dfbf51e34bad108416bca340": [
                "Parenting Education", "Early Learning", "Family Resource Center",
            ],
            "0df6bb236d8c7bf168ce4867dc83360e": ["Parenting Education"],
            "ec74c1192ef14f1debb3a31c912a1bbc": [
                "Parenting Education", "Home Visiting", "Early Intervention",
            ],
            "c44c60fb8e5cd640a4e7725286380d5c": ["Child Care", "Early Learning"],
            "220a1f02f8cd1658a7e7cd4b8e2906aa": [
                "Parenting Education", "Home Visiting", "Early Intervention",
            ],
            "029031368b1b87b942199b97cb2ac47f": [
                "Parenting Education", "Home Visiting",
            ],
            "aee416211643d092d52e82a4470df12b": ["Parenting Education"],
        },
        "boundary": (
            "Pregnancy medical care remains Medical; material aid remains Food, Clothing, "
            "or Household Essentials; population descriptions remain For groups."
        ),
    },
    "independent-living": {
        "types": [
            {
                "label": "In-home Support",
                "definition": "Personal, homemaking, habilitation, or other support in the home.",
            },
            {
                "label": "Adult Day",
                "definition": "Structured daytime care, health, skill, or activity programs.",
            },
            {
                "label": "Assistive Technology",
                "definition": "Devices, software, evaluation, loans, or training that improve access.",
            },
            {
                "label": "Communication Access",
                "definition": "Tools or services enabling accessible communication.",
            },
            {
                "label": "Living Skills",
                "definition": "Training and support for managing daily life more independently.",
            },
            {
                "label": "Case Management",
                "definition": "Assessment, planning, coordination, and follow-through across supports.",
            },
            {
                "label": "Adaptive Recreation",
                "definition": "Sports, recreation, clubs, or activities adapted for participation.",
            },
            {
                "label": "Self-Advocacy",
                "definition": "Peer or professional support for expressing choices and protecting access.",
            },
            {
                "label": "Vision Rehabilitation",
                "definition": "Specialized rehabilitation and skills for blindness or low vision.",
            },
            {
                "label": "Long-Term Care",
                "definition": "Eligibility or service pathways for sustained home or community-based care.",
            },
        ],
        "assignments": {
            "a121b7ac06dc9b9ef503e462d5cffdd8": [
                "Living Skills", "Adaptive Recreation", "Self-Advocacy",
            ],
            "debb9e4a689060f00162da9ac2f8063b": ["Adult Day"],
            "5f72f3c9e07e90867dc016da33c05457": [
                "In-home Support", "Adult Day", "Case Management",
            ],
            "8db24b98270f7864dadcb0f97b901a53": [
                "Vision Rehabilitation", "Assistive Technology", "Living Skills",
            ],
            "ee67d6c2ce1b1b7f9dbf0b2ef86ef972": [
                "Communication Access", "Assistive Technology", "Self-Advocacy",
            ],
            "c30d34b41e5260bdd10a194738ec8df2": ["Adaptive Recreation"],
            "a246f47cd18fc8d7b1bfa520a0451300": ["Long-Term Care"],
            "6be73b6539fd16b3a6c84ffad77aace8": [
                "Assistive Technology", "Living Skills",
            ],
            "4ac8a5df1279284d2d5e64df54b5c1dd": ["Assistive Technology"],
            "d6de881b1d1c0d17801cfcc7e6614ffd": ["Assistive Technology"],
            "00cca473db91285a4a393f5ba53add8f": [
                "Adult Day", "Living Skills", "Case Management",
            ],
            "f4bd5e83655dc1a2a573dc362204a505": ["Adaptive Recreation"],
            "0904081bbb9ee06085267ef392cd071f": [
                "Vision Rehabilitation", "Living Skills",
            ],
            "1bd2fb5b4587feef40252e0630c6c94c": [
                "In-home Support", "Case Management",
            ],
            "133e5f492400dff139f2cafa0b8f67c2": [
                "In-home Support", "Adult Day", "Living Skills",
            ],
            "df1db0951c8ad7dd0bcc0ec05a41b169": [
                "In-home Support", "Adult Day", "Case Management",
            ],
            "b41ef2cfadba3f4bedf490af52f17362": ["Adult Day"],
            "1a4c80c30adcb0f1df1846f7f84c3489": ["Self-Advocacy"],
            "b8c4699661c4d07b777efdab9ccb9d68": [
                "Communication Access", "Case Management", "Self-Advocacy",
            ],
        },
        "boundary": (
            "Employment, Housing, Transportation, Education, and Medical remain separate "
            "needs even when the same resource also supports independent living."
        ),
    },
    "caregiving": {
        "types": [
            {
                "label": "Respite",
                "definition": "Temporary relief or substitute care for an unpaid caregiver.",
            },
            {
                "label": "Support Groups",
                "definition": "Peer or facilitated emotional and practical caregiver support.",
            },
            {
                "label": "Caregiver Training",
                "definition": "Education and skills specifically for caregivers.",
            },
            {
                "label": "Care Coordination",
                "definition": "Assessment and arrangement of services supporting caregiver and recipient.",
            },
            {
                "label": "Adult Day",
                "definition": "Daytime programs that also provide caregiver relief.",
            },
            {
                "label": "In-home Support",
                "definition": "Care delivered in the home that reduces caregiver burden.",
            },
        ],
        "assignments": {
            "debb9e4a689060f00162da9ac2f8063b": ["Adult Day", "Respite"],
            "5f72f3c9e07e90867dc016da33c05457": [
                "Respite", "Adult Day", "In-home Support", "Care Coordination",
            ],
            "b21220ad00416ac580741d14ba3a1e7d": ["Respite"],
            "eb94f24384f8e51a2b237d7d8c507948": [
                "Respite", "Care Coordination",
            ],
            "b47b61d084512681adb9c7ccacf2268c": ["Respite", "Support Groups"],
            "38629d0e712141f7531b4cff4b0bfd53": [
                "Respite", "Support Groups", "Care Coordination",
            ],
            "1bd2fb5b4587feef40252e0630c6c94c": [
                "In-home Support", "Care Coordination",
            ],
            "133e5f492400dff139f2cafa0b8f67c2": ["Adult Day", "In-home Support"],
            "df1db0951c8ad7dd0bcc0ec05a41b169": [
                "Adult Day", "In-home Support", "Care Coordination",
            ],
            "b41ef2cfadba3f4bedf490af52f17362": ["Adult Day", "Respite"],
            "948dd967fb329f7e5f04c0814a113889": [
                "Respite", "Support Groups", "Caregiver Training", "Care Coordination",
            ],
        },
        "boundary": (
            "The care recipient may also appear in Independent Living or Medical; this "
            "Category describes the unpaid caregiver's distinct need."
        ),
    },
}


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def build_type_design(
    packet_record: dict[str, Any],
    specification: dict[str, Any],
) -> dict[str, Any]:
    packet = packet_record["packet"]
    category_id = str(packet_record["categoryId"])
    type_labels = [str(item["label"]) for item in specification["types"]]
    if len(type_labels) != len(set(type_labels)):
        raise TaxonomyStudyError(f"{category_id} has duplicate Type labels")
    expected_ids = {str(item["resourceId"]) for item in packet["resources"]}
    assignments = specification["assignments"]
    if expected_ids != set(assignments):
        raise TaxonomyStudyError(
            f"{category_id} Type coverage mismatch; "
            f"missing={sorted(expected_ids - set(assignments))}, "
            f"extra={sorted(set(assignments) - expected_ids)}"
        )
    resource_by_id = {
        str(item["resourceId"]): item for item in packet["resources"]
    }
    rows: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    disposition_counts: Counter[str] = Counter()
    for resource_id, selected in assignments.items():
        resource = resource_by_id[resource_id]
        if selected in ("no-type-needed", "unresolved"):
            disposition = str(selected)
            selected_types: list[str] = []
            disposition_counts.update([disposition])
            rows.append({
                "resourceId": resource_id,
                "name": resource["name"],
                "disposition": disposition,
                "types": [],
            })
            continue
        if not isinstance(selected, list) or not selected or len(selected) != len(set(selected)):
            raise TaxonomyStudyError(
                f"{category_id}/{resource_id} needs Types, no-type-needed, or unresolved"
            )
        selected_types = selected
        unknown = sorted(set(selected_types) - set(type_labels))
        if unknown:
            raise TaxonomyStudyError(
                f"{category_id}/{resource_id} has unknown Types: {unknown}"
            )
        counts.update(selected_types)
        disposition_counts.update(["assigned-types"])
        rows.append({
            "resourceId": resource_id,
            "name": resource["name"],
            "disposition": "assigned-types",
            "types": list(selected_types),
        })
    rows.sort(key=lambda item: (item["name"].casefold(), item["resourceId"]))
    design = {
        "schemaVersion": 1,
        "status": "proposal-only",
        "studyId": int(packet_record["studyId"]),
        "categoryId": category_id,
        "categoryLabel": packet_record["categoryLabel"],
        "packetSha256": packet_record["packetSha256"],
        "definition": packet["typeReviewRules"]["definition"],
        "types": deepcopy(specification["types"]),
        "boundary": str(specification["boundary"]),
        "assignments": rows,
        "coverage": {
            "resourceCount": len(expected_ids),
            "assignedTypesCount": disposition_counts["assigned-types"],
            "noTypeNeededCount": disposition_counts["no-type-needed"],
            "unresolvedCount": disposition_counts["unresolved"],
            "typeCounts": dict(sorted(counts.items())),
        },
    }
    return design


def save_category_type_designs(
    store: ResearchStore,
    study_id: int,
) -> dict[str, Any]:
    saved: list[dict[str, Any]] = []
    for category_id, specification in CATEGORY_TYPE_DESIGNS.items():
        packets = store.list_taxonomy_type_review_packets(study_id, category_id)
        if not packets:
            raise TaxonomyStudyError(f"Type review packet not found: {category_id}")
        packet = packets[0]
        design = build_type_design(packet, specification)
        design_sha256 = _sha256(design)
        revision = store.save_taxonomy_type_design_revision(
            study_id,
            category_id,
            design,
            design_sha256,
            based_on_packet_sha256=packet["packetSha256"],
            source="codex-category-by-category-type-design",
            note="Initial Type design for Michael's review; no resource package changed.",
        )
        saved.append({
            "categoryId": category_id,
            "categoryLabel": packet["categoryLabel"],
            "revision": revision,
            "designSha256": design_sha256,
            "typeCount": len(design["types"]),
            "resourceCount": design["coverage"]["resourceCount"],
            "unresolvedCount": design["coverage"]["unresolvedCount"],
            "types": [item["label"] for item in design["types"]],
        })
    return {
        "studyId": int(study_id),
        "designedCategoryCount": len(saved),
        "categories": saved,
    }


# Backward-compatible names for the initial three-Category checkpoint command.
NEW_CATEGORY_TYPE_DESIGNS = CATEGORY_TYPE_DESIGNS


def save_new_category_type_designs(
    store: ResearchStore,
    study_id: int,
) -> dict[str, Any]:
    return save_category_type_designs(store, study_id)
