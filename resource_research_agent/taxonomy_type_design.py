from __future__ import annotations

import hashlib
import json
from collections import Counter
from copy import deepcopy
from typing import Any

from .storage import ResearchStore
from .taxonomy_study import TaxonomyStudyError


NEW_CATEGORY_TYPE_DESIGNS: dict[str, dict[str, Any]] = {
    "food": {
        "types": [
            {"label": "Food Pantry", "definition": "Food boxes, groceries, commodities, or pantry shopping."},
            {"label": "Prepared Meals", "definition": "Ready-to-eat meals served at a site or program."},
            {"label": "Home Delivery", "definition": "Food or meals delivered to someone unable to reach a site."},
            {"label": "Food Benefits", "definition": "Enrollment or direct access to SNAP, WIC, or similar benefits."},
            {"label": "School Food", "definition": "Meals, pantries, or food programs accessed through school or college."},
        ],
        "assignments": {
            "b818a3a3b765d76ab42f0c78b169eef9": ["Food Pantry"],
            "33b8cbd29cf68ac3a07e0fd8d984771b": ["Food Benefits"],
            "5f72f3c9e07e90867dc016da33c05457": ["Prepared Meals", "Home Delivery"],
            "de9cf94ebcf45f375f7b8f0dba219edc": ["Prepared Meals", "Home Delivery"],
            "cd0fd35209b8684c1b85d3a08afb1f4d": ["Food Benefits"],
            "78ae362f464eb9c81519fc00a43f21ba": ["Prepared Meals", "Home Delivery"],
            "af848390332ec0fb5a3b60ba708457ee": ["Food Pantry"],
            "bd171f3dee49f66941dccb61f68c2dea": ["Food Pantry"],
            "e8989c429a0fd3824db237f9d8a9a4d8": ["Food Pantry"],
            "528e3dad283cd117ea2ff80b3bec333c": "no-type-needed",
            "24ea5cbf96413ae1016d5b8ad6140c2c": ["Food Pantry"],
            "a6043035dfbf51e34bad108416bca340": "no-type-needed",
            "47ea38f7dcac87504d34a3e7d2866f21": ["Food Benefits"],
            "d6f9cf4449c9ba1d947c0bcbf2ead96f": ["School Food"],
            "da047755bc1b7958186bd4dbcea9c8cb": ["Food Pantry", "School Food"],
            "e81c856ded56111fff730cb01a05858c": ["Prepared Meals", "School Food"],
            "61ba95efea2447e1f5b054e5206ef5e1": ["Food Pantry"],
            "5add8558737e9cfc392878fce4cca308": ["Food Pantry"],
            "89a928c6f5bbdc65de87c3fecbbcae79": ["Food Pantry"],
            "f05e5c2c63d27e8c03ce7ed46003ae31": ["Food Pantry", "Prepared Meals"],
            "72ddcda0a55400e3066289181a6795d0": ["Food Pantry"],
            "9674f1a708712c74c41c9d591821a356": ["Food Pantry", "Prepared Meals", "Food Benefits"],
            "15507c56e359f505d8f574491c7962ac": ["Food Pantry"],
            "2bf6edeedd27a167fa3b1ba584d2c7c4": ["Food Pantry", "Food Benefits"],
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
    "clothing-household": {
        "types": [
            {"label": "General Clothing", "definition": "Everyday clothing and shoes."},
            {"label": "Work Clothing", "definition": "Interview attire, uniforms, work shoes, or job equipment."},
            {"label": "School Clothing", "definition": "School uniforms, school clothes, and student shoes."},
            {"label": "Baby Supplies", "definition": "Diapers, infant clothing, cribs, car seats, or baby equipment."},
            {"label": "Furniture", "definition": "Beds, tables, seating, and other major furnishings."},
            {"label": "Household Goods", "definition": "Linens, dishes, appliances, and household necessities."},
            {"label": "Hygiene Supplies", "definition": "Toiletries and personal-care necessities."},
            {"label": "School Supplies", "definition": "Backpacks, books, and classroom supplies."},
            {"label": "Medical Equipment", "definition": "Loaned or donated mobility and durable medical equipment."},
        ],
        "assignments": {
            "2683e222e5f6957b1e5bddb3292334d1": ["Work Clothing", "Furniture"],
            "d6de881b1d1c0d17801cfcc7e6614ffd": ["Medical Equipment"],
            "aeed9f6c57cf87a109315fe1590a12d2": ["General Clothing"],
            "337e91d961e84d96ee124c6c891045eb": ["General Clothing", "Baby Supplies", "Household Goods"],
            "4ea93a335a4945322184f2ce0e01feb5": ["School Clothing", "Hygiene Supplies"],
            "70ea356cba96bcc304b79ca2a5469f9c": ["Work Clothing"],
            "442b7ced0e864db023bebfb05ecc9870": ["Furniture", "Household Goods"],
            "1ed84b657420da445ac082991959b3f8": ["General Clothing", "Baby Supplies", "Hygiene Supplies"],
            "ebac95249761b88323fc73b4e26259fd": ["General Clothing", "Hygiene Supplies", "School Supplies"],
            "ed9cec6557722e44984887fb41637d6e": ["General Clothing", "Baby Supplies"],
            "ea17c3d484efe07c9892521284d54e24": ["Work Clothing"],
            "df171bb522d8c9a10c10b5c20e52cc1b": ["Work Clothing"],
            "528e3dad283cd117ea2ff80b3bec333c": ["General Clothing"],
            "de5e0aa4a6c2164fb8b4a9fcfdcdac9b": ["General Clothing"],
            "7e66c8c912ad9889aa3627405af218f3": ["General Clothing"],
            "fbd7ac5640a1ad45864261484e2bcbf0": ["General Clothing", "Baby Supplies", "Hygiene Supplies"],
            "48635b5d3545aa10e94ee5ef9259b840": ["General Clothing", "Household Goods"],
            "5359125c3611d817c5b9511c96a017fa": ["General Clothing", "Furniture", "Household Goods"],
            "a6043035dfbf51e34bad108416bca340": ["Baby Supplies"],
            "0df6bb236d8c7bf168ce4867dc83360e": ["Baby Supplies"],
            "6ce0d0fd810d670dae505e267ea6e01a": ["General Clothing", "Baby Supplies", "Hygiene Supplies", "School Supplies"],
            "663199b0f4bb6151cde8abc21bceb26c": ["General Clothing"],
            "73dfadc219f93cdde3c2e07d3e1045b4": ["General Clothing", "Work Clothing", "Household Goods"],
            "7bacf0bff58c51dc50d9c02ccd69eac4": ["General Clothing", "Hygiene Supplies"],
            "882badd1df67753d02e23796b2875118": ["General Clothing", "Furniture", "Household Goods"],
            "c399be50023b7d9bbbd54bbdea6b4b5f": ["General Clothing", "Furniture", "Household Goods", "Hygiene Supplies"],
            "08497e5f8c33c372d57430bc722bb639": ["Work Clothing"],
            "c74ea9adad61a6ff3fd9e49ae50d61d2": ["General Clothing", "Work Clothing", "School Clothing", "Hygiene Supplies", "School Supplies"],
            "edacb348adc1480fe0ac0b9b6f1e8580": ["General Clothing", "Baby Supplies", "Furniture", "Household Goods", "Hygiene Supplies", "School Supplies"],
            "669bd738b302f2f17f9caa6163dd35ed": ["Household Goods"],
            "1a240d601f09634fb93383fd76971b5c": ["Furniture", "Household Goods"],
            "3367433d5c6845b44636936a2902a3bb": ["Work Clothing"],
        },
        "boundary": "Who qualifies belongs in For groups; the goods supplied belong in Types.",
    },
    "transportation": {
        "types": [
            {"label": "Travel Training", "definition": "Instruction in using public or fixed-route transportation."},
            {"label": "Medical Rides", "definition": "Transportation to medical or behavioral-health appointments."},
            {"label": "Volunteer Rides", "definition": "Individual trips provided by volunteer drivers."},
            {"label": "Bus Passes", "definition": "Transit passes or fare assistance."},
            {"label": "Ride Vouchers", "definition": "Taxi, rideshare, or other trip vouchers."},
            {"label": "Bicycles", "definition": "Bicycle placement, repair, or cycling transportation."},
            {"label": "Mobility Services", "definition": "Mobility planning or support beyond a single ride method."},
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
            "00cca473db91285a4a393f5ba53add8f": ["Mobility Services"],
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
        ],
        "assignments": {
            "106d516390d810b1989b53d59ae806c9": ["Bill Assistance"],
            "ee67d6c2ce1b1b7f9dbf0b2ef86ef972": ["Communication Equipment"],
            "472c5150aa06dba907ba0bdd1106599e": ["Bill Assistance"],
            "e65a5ab33ccf6b355ca9b21969c6617e": ["Bill Discounts", "Bill Assistance", "Heating/Cooling Repair"],
            "3c04b13381e97f377ba21e3c86d0b12c": ["Heating/Cooling Repair", "Home Utility Repairs"],
            "5b6667d5d6350f7b3c4e9c94b1b17de1": ["Bill Discounts"],
            "fa0719b16ad0843652d8175fb792ca87": ["Payment Plans"],
            "4ff2225ddc559a033efe06a6b6ce3659": ["Low-cost Internet"],
            "8b0cbd343a20dc0118ec3fa8c9a17d1f": ["Bill Discounts"],
            "7d48baeb2cd113386712a5ec693abb8c": ["Bill Discounts"],
            "726f13326a74a1f5d347c70575ea49e7": ["Phone/Internet Discount"],
            "774e5a59b471ceacca5d0fe7cc5e787b": ["Bill Assistance", "Heating/Cooling Repair"],
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
        ],
        "assignments": {
            "2a8159c00294405bdb9123bc13f28b34": ["State ID/License"],
            "a90b957439ba736a20a0eb129322891e": ["Document Navigation"],
            "b684b97f8e67ea1cb39778d953a2c4cf": ["State ID/License"],
            "fb402105bec44e0623b4ccf8d7064802": ["Military Records", "Document Navigation"],
            "8fbf07bdf33a69f83a1afc375c0f66d3": ["State ID/License", "Birth Certificates", "Social Security Card", "Document Navigation"],
            "528e3dad283cd117ea2ff80b3bec333c": ["State ID/License", "Birth Certificates", "Document Navigation"],
            "4a4a619b7b63a00120d7f6c7391caabd": ["State ID/License", "Birth Certificates", "Document Navigation", "Document Storage"],
            "5bfda48463f45755a59145fa7d226906": ["State ID/License", "Birth Certificates", "Social Security Card", "Document Navigation"],
            "a4e45e62c0b9cb505d5b4874340871fb": ["Document Navigation"],
            "1d7914c5fe0d1c96c8583057ac00239f": ["Birth Certificates"],
            "c24a862cda664d0144ec0ae39b3e8f1f": ["Military Records"],
            "fb14c6d3b942c86033ad23bf8b60fb48": ["State ID/License", "Birth Certificates", "Document Navigation"],
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
            {"label": "Deposit Assistance", "definition": "Help with security, utility, or other move-in deposits."},
            {"label": "Community Living", "definition": "Adult foster care, shared living, or disability-supportive community residences."},
        ],
        "assignments": {
            "db2e8f3b8772791cf254fb9cc04b9838": ["Emergency Shelter", "Transitional Housing"],
            "a90b957439ba736a20a0eb129322891e": ["Housing Navigation"],
            "773f0771a3cca46a7a57189d17a58a01": ["Emergency Shelter", "Rental Assistance"],
            "996b322aa685b24c16a5bbea4b68ed0e": ["Transitional Housing", "Housing Navigation"],
            "8d56f8448fc9b780197d3015c051f81c": ["Emergency Shelter", "Rapid Rehousing", "Housing Navigation"],
            "00cca473db91285a4a393f5ba53add8f": ["Community Living"],
            "6f709ac3eafa28d894f99dad814a2430": ["Rental Assistance"],
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
            "36a1aba6efe7a704aa4ca190a4f82467": ["Rental Assistance"],
            "a3782d71fb0f13f124d33c95dadd779c": ["Rapid Rehousing", "Deposit Assistance"],
            "815148d4fe10fdbf28f981c14050256c": ["Treatment Housing"],
            "b8ca7f8d2eab81113b10c1a8835f0817": ["Affordable Housing"],
            "617d4be1951f67468b5ddffdb2f670f5": ["Treatment Housing", "Housing Vouchers"],
            "d0eeddd67746f3a298eaf4969b6e9bd1": ["Emergency Shelter", "Rental Assistance", "Deposit Assistance"],
            "79a54c3aaf0d161f9dbab859bfba7da2": ["Emergency Shelter", "Transitional Housing"],
            "e81a4666fa9fdf3874524e595834798c": ["Housing Vouchers", "Supportive Housing", "Coordinated Entry"],
            "2af79fdd0101ee3a198c732086f9bfc6": ["Transitional Housing", "Rapid Rehousing", "Supportive Housing"],
            "15b833547484fe110411244b99712ca9": ["Emergency Shelter", "Housing Navigation"],
            "eadaaf197b67dc1d520ae55c2dc28a19": ["Coordinated Entry"],
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
            "78410d1265bcc4f89c056a7d624434f8": ["Mail & Storage", "Meals & Basic Needs", "Homeless Navigation"],
            "d54d48c6356e5e983f4bd33e02469bc3": ["Showers & Laundry", "Meals & Basic Needs"],
            "c39b7edce7fd22875fba8558aa17172c": ["Showers & Laundry", "Meals & Basic Needs"],
            "e21ae1b4b21564628d99c417487754a1": ["Day Center", "Showers & Laundry", "Meals & Basic Needs", "Homeless Navigation"],
            "4a4a619b7b63a00120d7f6c7391caabd": ["ID & Documents", "Mail & Storage"],
            "da4f4b5a717ae241f3363cc09eb4298a": ["Day Center", "Showers & Laundry", "ID & Documents", "Meals & Basic Needs", "Homeless Navigation"],
            "c9a6d961fc20217b2875637b5fef2cb6": ["Day Center", "Showers & Laundry", "Mail & Storage", "Homeless Navigation"],
            "3460a40faf90d00f895061b117f1d9cc": ["Day Center", "Showers & Laundry", "Mail & Storage", "ID & Documents", "Homeless Navigation"],
            "0df6bb236d8c7bf168ce4867dc83360e": "no-type-needed",
            "096327d7591511a067b7e9dd29f900b6": ["Overnight Lodging", "Showers & Laundry", "Meals & Basic Needs", "Homeless Navigation"],
            "a3782d71fb0f13f124d33c95dadd779c": ["Homeless Navigation"],
            "08a26b747ffe8b1ea284e491a62d39e7": ["Day Center", "Showers & Laundry", "Mail & Storage", "ID & Documents", "Meals & Basic Needs", "Homeless Navigation"],
            "91d5cdd19b42853fb4bbe8e57f325be0": ["Street Outreach", "Meals & Basic Needs", "Homeless Navigation"],
            "617d4be1951f67468b5ddffdb2f670f5": ["Homeless Navigation"],
            "19a8af5b80be03028603cfa5e8bebb6e": ["Day Center", "Showers & Laundry", "Homeless Navigation", "Overnight Lodging"],
            "2af79fdd0101ee3a198c732086f9bfc6": ["Street Outreach", "Homeless Navigation"],
        },
        "boundary": "These Types describe practical help while someone is homeless; shelter and permanent housing interventions remain visible under Housing too.",
    },
    "financial-assistance": {
        "types": [
            {"label": "Cash Benefits", "definition": "Public cash assistance for basic household needs."},
            {"label": "Disability Income", "definition": "SSI, SSDI, or other disability-based income."},
            {"label": "Veteran Benefits", "definition": "Compensation, pension, survivor, or other veteran benefit claims."},
            {"label": "Benefits Navigation", "definition": "Screening and hands-on application help for public benefits."},
            {"label": "Health Coverage", "definition": "Enrollment in publicly funded medical coverage."},
            {"label": "Rent/Mortgage Aid", "definition": "Financial help paying rent or a mortgage."},
            {"label": "Utility Aid", "definition": "Financial help paying electric, gas, water, phone, or internet bills."},
            {"label": "Deposit Assistance", "definition": "Financial help with rental or utility deposits."},
            {"label": "Emergency Grants", "definition": "Flexible or expense-specific crisis grants not captured by another Type."},
            {"label": "Tax Preparation", "definition": "Free tax filing and help claiming refundable credits."},
            {"label": "Debt/Credit Counseling", "definition": "Counseling for debt, credit, budgeting, and financial decisions."},
            {"label": "Caregiver Vouchers", "definition": "Vouchers that help unpaid caregivers obtain respite or support."},
            {"label": "Funeral Assistance", "definition": "Financial help with funeral or burial expenses."},
        ],
        "assignments": {
            "106d516390d810b1989b53d59ae806c9": ["Rent/Mortgage Aid", "Utility Aid"],
            "33b8cbd29cf68ac3a07e0fd8d984771b": ["Benefits Navigation", "Health Coverage"],
            "5f72f3c9e07e90867dc016da33c05457": ["Benefits Navigation"],
            "b48b75beadedb73dd0606ffb3dcc568d": ["Cash Benefits", "Benefits Navigation"],
            "c11d6b3cdb3f6531bae81d7ec38e1e9e": ["Cash Benefits", "Benefits Navigation"],
            "fb402105bec44e0623b4ccf8d7064802": ["Veteran Benefits", "Emergency Grants"],
            "855ec83aea4c5bc38c85275c8fc38459": ["Emergency Grants"],
            "855aea5e0d3d3b07f11e7bb81212e4d2": ["Health Coverage"],
            "653100ce23fc3523104581629632c77c": ["Utility Aid"],
            "413ff589842e5d267a528fa2221b032a": ["Utility Aid"],
            "193621d2449346f5eb4f3fe57535ad47": "no-type-needed",
            "c6862828db3631873bf2eb1f4ff99bea": ["Benefits Navigation"],
            "343c5cdfd5f0ec79247f90e12f1088d6": ["Tax Preparation"],
            "5a185dff18772905536e3488f7b75129": ["Rent/Mortgage Aid", "Utility Aid", "Benefits Navigation", "Funeral Assistance"],
            "27adbd6da40ba1d0325ed17d523a3e94": ["Rent/Mortgage Aid", "Deposit Assistance"],
            "987a8b8eb5e82e8c0216ef7bb436693f": ["Deposit Assistance"],
            "4d728e518eb341e958f91d67d4cac4cd": ["Rent/Mortgage Aid", "Utility Aid", "Deposit Assistance"],
            "38629d0e712141f7531b4cff4b0bfd53": ["Benefits Navigation", "Caregiver Vouchers"],
            "087b0bd908ca3082b11b8f637137b181": ["Debt/Credit Counseling"],
            "bcc694b6232b6b88cd40c57d3052f4ca": ["Rent/Mortgage Aid", "Utility Aid", "Deposit Assistance"],
            "a3782d71fb0f13f124d33c95dadd779c": ["Rent/Mortgage Aid", "Deposit Assistance"],
            "ff1488daaf584a5c3e58c81b4e22bf10": ["Rent/Mortgage Aid"],
            "8d70eda15ed4d365bd3ffb2577c8653e": ["Disability Income"],
            "5fd29d6c772cabbc8a6abc6614f9d3bd": ["Rent/Mortgage Aid", "Utility Aid"],
            "f3e278c9cf9fd269e07fa88724f2f949": ["Utility Aid"],
            "13cf776353746eb632703023c26e9365": ["Utility Aid", "Emergency Grants"],
            "fcdf7044337d12d9e7bdd3a7a732fd08": ["Rent/Mortgage Aid", "Utility Aid"],
        },
        "boundary": "The funded expense or financial pathway is a Type; urgency, funding availability, and population eligibility belong in access details or For groups.",
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
            "Pregnancy medical care remains Medical; material aid remains Food or "
            "Clothing/Household; population descriptions remain For groups."
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


def save_new_category_type_designs(
    store: ResearchStore,
    study_id: int,
) -> dict[str, Any]:
    saved: list[dict[str, Any]] = []
    for category_id, specification in NEW_CATEGORY_TYPE_DESIGNS.items():
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
