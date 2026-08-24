from __future__ import annotations

import json
import unittest
from copy import deepcopy
from pathlib import Path

from resource_research_agent.optimization import build_housing_urgent_query_plan
from resource_research_agent.optimization_playbook_audit import (
    coverage_plan_sha256,
    normalize_optimization_playbook_audit,
    playbook_source_receipt,
)
from resource_research_agent.playbooks import playbook_for
from resource_research_agent.query_expansion import augment_query_plan_with_targeted_branch


ROOT = Path(__file__).resolve().parents[1]
HOUSING_AUDIT = (
    ROOT
    / "resource_research_agent"
    / "optimization_playbook_audits"
    / "mesa-housing-urgent-v1.json"
)
HOUSING_EXPANSION = (
    ROOT
    / "resource_research_agent"
    / "optimization_query_plans"
    / "mesa-housing-coordinated-entry-depth-v1.json"
)


def housing_audited_plan() -> dict:
    plan = build_housing_urgent_query_plan(
        "Mesa",
        "Maricopa County and nearby areas",
        minimum_queries=4,
        maximum_queries=10,
        saturation_queries=3,
    )
    expansion = json.loads(HOUSING_EXPANSION.read_text(encoding="utf-8"))
    plan = augment_query_plan_with_targeted_branch(
        plan,
        branch_key=expansion["branchKey"],
        purpose=expansion["purpose"],
        queries=expansion["queries"],
        parent_corpus_sha256=expansion["parentCorpusSha256"],
        minimum_queries=expansion["saturation"]["minimumQueries"],
        maximum_queries=expansion["saturation"]["maximumQueries"],
        saturation_queries=expansion["saturation"][
            "consecutiveNoNewIdentityQueries"
        ],
    )
    for key in ["candidate-current-status"]:
        plan["branches"].append(
            {
                "key": key,
                "purpose": f"Fixture operational branch {key}.",
                "required": True,
                "saturation": {
                    "minimumQueries": 1,
                    "maximumQueries": 1,
                    "consecutiveNoNewIdentityQueries": 1,
                    "noveltyUnit": "package-eligible identity",
                },
                "queries": [
                    {
                        "key": f"{key}-fixture-1",
                        "position": 1,
                        "purpose": f"Fixture operational branch {key}.",
                        "query": f"Mesa {key} current service intake",
                    }
                ],
            }
        )
    return plan


def fixture_audit(plan: dict, category_id: str) -> dict:
    playbook = playbook_for(category_id)
    required = sorted(set(playbook.factual_fields) - set(playbook.supplementary_fields))
    return {
        "schemaVersion": 1,
        "policyVersion": "optimization-playbook-audit-v1",
        "auditId": f"fixture-{category_id}-audit-v1",
        "categoryId": category_id,
        "stageKey": plan["stageKey"],
        "targetLocation": plan["targetLocation"],
        "regionalScope": plan["regionalScope"],
        "coveragePlanSha256": coverage_plan_sha256(
            plan, [plan["branches"][0]["key"]]
        ),
        "playbook": playbook_source_receipt(playbook),
        "coverageBranchKeys": [plan["branches"][0]["key"]],
        "operationalBranchKeys": [],
        "serviceNeeds": ["Current direct access to the selected category service"],
        "populations": ["People within the configured service area"],
        "barriers": ["Transportation, documentation, eligibility, and hours"],
        "authoritativeSourceFamilies": [
            {
                "key": "direct",
                "authority": "direct-provider",
                "use": "Confirm the exact program and current access path.",
            },
            {
                "key": "government",
                "authority": "government-referral",
                "use": "Find official programs and bounded referrals.",
            },
        ],
        "geographyRules": ["Require current evidence that the program serves Mesa."],
        "candidateRolePolicy": {
            "eligible": ["direct-program", "access-assessment-service"],
            "preservedNoncandidate": [
                "service-location",
                "referral-system",
                "directory",
                "organization-only",
                "unresolved-lead",
            ],
        },
        "requiredFactualFields": required,
        "accessCriticalFields": ["organization", "program", "geography"],
        "supplementaryFields": list(playbook.supplementary_fields),
        "requiredCoverageNeeds": [
            {
                "key": "direct-access",
                "label": "Direct category access",
                "query": f"Mesa current {category_id} direct intake",
            }
        ],
        "gapSearchTerms": ["No current program for one required service need"],
        "currentStatusSignals": ["Current intake or an explicit closure notice"],
        "corpusComponents": {
            "referralGraphSha256": "a" * 64,
            "referralReviewSha256": "b" * 64,
        },
        "reviewDecision": "The fixture planning contract is explicit.",
    }


class OptimizationPlaybookAuditTests(unittest.TestCase):
    def test_live_housing_audit_covers_exact_plan_and_playbook_contract(self) -> None:
        plan = housing_audited_plan()
        audit = json.loads(HOUSING_AUDIT.read_text(encoding="utf-8"))
        normalized = normalize_optimization_playbook_audit(
            audit,
            query_plan=plan,
            playbook=playbook_for("housing"),
            referral_graph_sha256=audit["corpusComponents"]["referralGraphSha256"],
            referral_review_sha256=audit["corpusComponents"]["referralReviewSha256"],
        )
        self.assertEqual("optimization-playbook-audit-v1", normalized["policyVersion"])
        self.assertEqual(64, len(normalized["auditSha256"]))
        self.assertIn("petPolicy", normalized["supplementaryFields"])
        self.assertNotIn("petPolicy", normalized["accessCriticalFields"])
        self.assertEqual(10, len(normalized["requiredCoverageNeeds"]))
        self.assertEqual(
            {branch["key"] for branch in plan["branches"]},
            set(normalized["coverageBranchKeys"])
            | set(normalized["operationalBranchKeys"]),
        )

    def test_audit_rejects_stale_receipt_branch_and_field_contracts(self) -> None:
        plan = housing_audited_plan()
        audit = json.loads(HOUSING_AUDIT.read_text(encoding="utf-8"))
        stale = deepcopy(audit)
        stale["playbook"]["libraryVersion"] = "stale"
        with self.assertRaisesRegex(ValueError, "receipt is stale"):
            normalize_optimization_playbook_audit(
                stale, query_plan=plan, playbook=playbook_for("housing")
            )
        missing_branch = deepcopy(audit)
        missing_branch["coverageBranchKeys"].pop()
        with self.assertRaisesRegex(ValueError, "classify every query branch"):
            normalize_optimization_playbook_audit(
                missing_branch, query_plan=plan, playbook=playbook_for("housing")
            )
        stale_fields = deepcopy(audit)
        stale_fields["supplementaryFields"].remove("petPolicy")
        with self.assertRaisesRegex(ValueError, "supplementary-field contract"):
            normalize_optimization_playbook_audit(
                stale_fields, query_plan=plan, playbook=playbook_for("housing")
            )

    def test_non_housing_audit_uses_food_stage_and_fields(self) -> None:
        plan = {
            "schemaVersion": 4,
            "candidateQualificationPolicyVersion": "candidate-qualification-gates-v2",
            "categoryId": "food",
            "stageKey": "immediate-food",
            "targetLocation": "Mesa",
            "regionalScope": "Maricopa County and nearby areas",
            "branches": [
                {
                    "key": "direct-food",
                    "purpose": "Find current direct food access.",
                    "required": True,
                    "saturation": {
                        "minimumQueries": 1,
                        "maximumQueries": 1,
                        "consecutiveNoNewIdentityQueries": 1,
                        "noveltyUnit": "package-eligible identity",
                    },
                    "queries": [
                        {
                            "key": "direct-food-1",
                            "position": 1,
                            "purpose": "Find current direct food access.",
                            "query": "Mesa current food pantry intake",
                        }
                    ],
                }
            ],
        }
        normalized = normalize_optimization_playbook_audit(
            fixture_audit(plan, "food"),
            query_plan=plan,
            playbook=playbook_for("food"),
            referral_graph_sha256="a" * 64,
            referral_review_sha256="b" * 64,
        )
        self.assertEqual("food", normalized["categoryId"])
        self.assertEqual("immediate-food", normalized["stageKey"])
        self.assertNotIn("petPolicy", normalized["supplementaryFields"])


if __name__ == "__main__":
    unittest.main()
