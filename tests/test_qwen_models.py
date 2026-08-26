from __future__ import annotations

import json
import sqlite3
import subprocess
import tempfile
import unittest
import zipfile
from copy import deepcopy
from pathlib import Path

from resource_research_agent.optimization import (
    EVIDENCE_PREPARATION_POLICY_VERSION,
    optimization_candidate_id,
    optimization_resource_id,
    package_exclusion_state,
)
from resource_research_agent.optimization_models import (
    apply_verification_decisions,
    compact_source_bindings,
    derive_verification_from_response,
    OptimizationModelError,
    OptimizationModelPipeline,
    recompute_model_evaluation_audits,
    recompute_persisted_verifications,
    remediate_invalid_factual_fields,
    restore_frozen_candidate_identity,
    restore_frozen_source_envelopes,
    restore_reviewed_identity_bindings,
    validate_dossier_for_packet,
    verification_status,
)
from resource_research_agent.playbooks import playbook_for
from resource_research_agent.optimization_pipeline import OptimizationDiscoveryPipeline
from resource_research_agent.optimization_outcomes import (
    OptimizationOutcomeError,
    compare_optimization_run_to_package,
)
from resource_research_agent.importer import (
    ResourcePackageImporter,
    resource_program_identity,
)
from resource_research_agent.review_export import build_optimization_review_copy
from resource_research_agent.storage import ResearchStore
from tests.test_qwen_discovery import FixtureProviders


HOUSING_FACTUAL_FIELDS = playbook_for("housing").factual_fields


def model_configuration(providers: FixtureProviders, label: str) -> dict:
    value = providers.configuration(label)
    value.update(
        {
            "modelArtifact": "mlx-community/Qwen3.8-27B-4bit",
            "quantization": "4-bit",
            "modelProvider": "qwen-local",
            "modelEndpoint": "http://127.0.0.1:8080/v1",
            "mlxVersion": "fixture-runtime",
            "dshVersion": "0.1.0-rc.6",
            "promptPolicyVersion": "schema-playbook-dossier-v1-and-verifier-decision-patch-v1",
        }
    )
    return value


def source_records(packet: dict) -> list[dict]:
    result = []
    for source in packet["sources"]:
        result.append(
            {
                "id": str(source["id"]),
                "url": source["canonical_url"],
                "title": source["extract"]["title"],
                "extract": source["extract"]["text"],
                "authority": source["authority"],
                "pageIdentityKey": source["page_identity_key"],
                "pageOrganizationKey": source["page_identity_key"].split("::", 1)[0],
                "supports": [],
                "contradicts": [],
            }
        )
    return result


class SeededFixtureModels:
    def __init__(self) -> None:
        self.extract_prompts: list[dict] = []
        self.verify_prompts: list[dict] = []

    def extract(self, prompt: dict) -> dict:
        self.extract_prompts.append(deepcopy(prompt))
        packet = prompt["evidencePacket"]
        identity = packet["candidateIdentity"]
        identity_key = identity["identityKey"]
        sources = source_records(packet)
        fields = {
            field: {
                "status": "unknown",
                "reason": "Not found in the frozen fixture evidence packet",
            }
            for field in prompt["requiredFields"]
        }
        program = identity["program"]
        components = [identity_key]
        if program == "Rapid Re-Housing":
            sources[0]["pageIdentityKey"] = "a new leaf::mesacan"
            sources[0]["supports"] = [
                {
                    "field": "phone",
                    "value": "480-000-0100",
                    "scope": "program",
                }
            ]
            fields["phone"] = {
                "status": "supported",
                "value": "480-000-0100",
                "evidenceIds": [sources[0]["id"]],
            }
        elif program == "Off the Streets":
            sources[0]["supports"] = [
                {
                    "field": "geography",
                    "value": "Maricopa County outside Mesa",
                    "scope": "program",
                }
            ]
            sources[0]["contradicts"] = [
                {"field": "geography", "value": "Mesa"}
            ]
            fields["geography"] = {
                "status": "supported",
                "value": "Mesa",
                "evidenceIds": [sources[0]["id"]],
            }
        elif program == "Emergency Lodging Program":
            fields["barriers"] = {
                "status": "supported",
                "value": ["Must be sober"],
                "evidenceIds": [],
            }
        return {
            "candidateIdentity": {
                "organization": identity["organization"],
                "program": program,
                "identityKey": identity_key,
                "componentIdentityKeys": components,
            },
            "sources": sources,
            "fields": fields,
        }

    def verify(self, prompt: dict) -> dict:
        self.verify_prompts.append(deepcopy(prompt))
        decisions = {
            field: {"action": "keep"} for field in prompt["requiredFields"]
        }
        for finding in prompt["deterministicFindings"]:
            field = finding.get("field")
            if field in decisions:
                decisions[field] = {
                    "action": "downgrade-to-unknown",
                    "reason": f"Removed by verifier: {finding['code']}",
                }
        return {
            "status": "passed",
            "fieldDecisions": decisions,
            "materialDefects": [],
            "findings": [],
        }


class ModelPipelineTests(unittest.TestCase):
    def test_optimization_linkage_uses_packet_content_and_preserves_legacy_ids(
        self,
    ) -> None:
        configuration_hash = "a" * 64
        packet_sha256 = "b" * 64
        self.assertEqual(
            "dfcf35d767d45e62b4688b2344c24869",
            optimization_resource_id(configuration_hash, 7),
        )
        self.assertEqual(
            optimization_resource_id(configuration_hash, packet_sha256),
            optimization_resource_id(configuration_hash, packet_sha256.upper()),
        )
        self.assertNotEqual(
            optimization_resource_id(configuration_hash, 7),
            optimization_resource_id(configuration_hash, packet_sha256),
        )
        self.assertEqual(
            optimization_candidate_id(configuration_hash, packet_sha256),
            optimization_candidate_id(configuration_hash, packet_sha256.upper()),
        )
        with self.assertRaisesRegex(ValueError, "packet id or packet hash"):
            optimization_resource_id(configuration_hash, "not-a-hash")

    def test_deterministic_remediation_only_downgrades_factual_fields(self) -> None:
        dossier = {
            "fields": {
                "phone": {"status": "supported", "value": "480-555-0100"},
            }
        }
        remediated, findings = remediate_invalid_factual_fields(
            dossier,
            [
                {"code": "missing-evidence", "field": "phone", "message": "bad"},
                {
                    "code": "altered-source",
                    "field": "url",
                    "message": "structural defect",
                },
            ],
            ["phone"],
        )
        self.assertEqual("unknown", remediated["fields"]["phone"]["status"])
        self.assertEqual("deterministic-field-downgrade", findings[0]["code"])
        self.assertEqual("phone", findings[0]["field"])
        self.assertEqual({"status": "supported", "value": "480-555-0100"}, dossier["fields"]["phone"])

    def test_actual_verifier_omissions_preserve_extraction_and_never_fail_candidate(
        self,
    ) -> None:
        cases = json.loads(
            (
                Path(__file__).parent
                / "fixtures"
                / "verification_omission_regressions.json"
            ).read_text(encoding="utf-8")
        )
        for case in cases:
            with self.subTest(program=case["program"], field=case["field"]):
                dossier = {
                    "candidateIdentity": {
                        "organization": case["organization"],
                        "program": case["program"],
                    },
                    "sources": [{"id": "preserved-source"}],
                    "fields": {
                        field: {
                            "status": "unknown",
                            "reason": "Not found in regression fixture",
                        }
                        for field in HOUSING_FACTUAL_FIELDS
                    },
                }
                dossier["fields"][case["field"]] = case["extractedFinding"]
                response = {
                    "status": "passed",
                    "fieldDecisions": {
                        field: {"action": "keep"}
                        for field in HOUSING_FACTUAL_FIELDS
                        if field != case["field"]
                    },
                    "materialDefects": [],
                }

                verified, findings, material_defects = apply_verification_decisions(
                    dossier, response, HOUSING_FACTUAL_FIELDS
                )
                self.assertEqual(
                    case["extractedFinding"], verified["fields"][case["field"]]
                )
                self.assertEqual(dossier["candidateIdentity"], verified["candidateIdentity"])
                self.assertEqual(dossier["sources"], verified["sources"])
                self.assertEqual([], material_defects)
                self.assertEqual(
                    [("verification-incomplete", case["field"])],
                    [
                        (finding["code"], finding.get("field"))
                        for finding in findings
                    ],
                )
                self.assertEqual(
                    "needs-review",
                    verification_status(
                        final_issues=[],
                        material_defects=material_defects,
                        review_findings=findings,
                        requested_status="passed",
                    ),
                )

    def test_pet_policy_cannot_be_promoted_to_candidate_blocking_defect(self) -> None:
        dossier = {
            "candidateIdentity": {"organization": "Example", "program": "Shelter"},
            "sources": [],
            "fields": {
                field: {"status": "unknown", "reason": "Not found"}
                for field in HOUSING_FACTUAL_FIELDS
            },
        }
        verified, findings, defects = apply_verification_decisions(
            dossier,
            {
                "status": "passed",
                "fieldDecisions": {
                    field: {"action": "keep"} for field in HOUSING_FACTUAL_FIELDS
                },
                "materialDefects": [
                    {
                        "code": "unsupported-safety-critical-claim",
                        "field": "petPolicy",
                        "reason": "The pet policy is not known.",
                    }
                ],
            },
            HOUSING_FACTUAL_FIELDS,
            playbook_for("housing").supplementary_fields,
        )
        self.assertEqual(dossier["fields"]["petPolicy"], verified["fields"]["petPolicy"])
        self.assertEqual([], defects)
        self.assertIn(
            "supplementary-field-material-defect",
            {finding["code"] for finding in findings},
        )
        self.assertEqual(
            "needs-review",
            verification_status(
                final_issues=[],
                material_defects=defects,
                review_findings=findings,
                requested_status="passed",
            ),
        )

    def test_additional_phone_number_requires_a_purpose_without_becoming_fatal(
        self,
    ) -> None:
        identity_key = "example housing::senior apartments"
        packet = {
            "candidateIdentity": {
                "organization": "Example Housing",
                "program": "Senior Apartments",
                "identityKey": identity_key,
            },
            "sources": [
                {
                    "id": 7,
                    "canonical_url": "https://example.org/senior-apartments",
                    "authority": "direct-provider",
                    "page_identity_key": identity_key,
                    "extract": {
                        "title": "Senior Apartments",
                        "text": "Phone: 480-555-0100. TTY: 800-855-2880.",
                    },
                }
            ],
        }

        def derive(value: str) -> tuple[str, dict, dict]:
            dossier = {
                "candidateIdentity": {
                    **packet["candidateIdentity"],
                    "componentIdentityKeys": [identity_key],
                },
                "sources": [
                    {
                        "id": "7",
                        "url": "https://example.org/senior-apartments",
                        "title": "Senior Apartments",
                        "extract": "Phone: 480-555-0100. TTY: 800-855-2880.",
                        "authority": "direct-provider",
                        "pageIdentityKey": identity_key,
                        "pageOrganizationKey": "example housing",
                        "supports": [
                            {
                                "field": "additionalPhoneNumbers",
                                "value": [value],
                                "scope": "program",
                            }
                        ],
                        "contradicts": [],
                    }
                ],
                "fields": {
                    "additionalPhoneNumbers": {
                        "status": "supported",
                        "value": [value],
                        "evidenceIds": ["7"],
                    }
                },
            }
            return derive_verification_from_response(
                dossier,
                packet,
                {
                    "status": "passed",
                    "fieldDecisions": {
                        "additionalPhoneNumbers": {"action": "keep"}
                    },
                    "materialDefects": [],
                    "findings": [],
                },
                ("additionalPhoneNumbers",),
            )

        status, verified, findings = derive("800-855-2880")
        self.assertEqual("needs-review", status)
        self.assertEqual(
            ["800-855-2880"],
            verified["fields"]["additionalPhoneNumbers"]["value"],
        )
        self.assertEqual(
            ["additional-phone-purpose-unlabeled"],
            [finding["code"] for finding in findings["fieldContractFindings"]],
        )
        self.assertEqual([], findings["finalDeterministicFindings"])

        labeled_status, _labeled_verified, labeled_findings = derive(
            "TTY: 800-855-2880"
        )
        self.assertEqual("passed", labeled_status)
        self.assertEqual([], labeled_findings["fieldContractFindings"])

    def test_invented_field_cannot_become_safety_critical_blocking_defect(self) -> None:
        dossier = {
            "candidateIdentity": {"organization": "Example", "program": "Shelter"},
            "sources": [],
            "fields": {
                field: {"status": "unknown", "reason": "Not found"}
                for field in HOUSING_FACTUAL_FIELDS
            },
        }
        _verified, findings, defects = apply_verification_decisions(
            dossier,
            {
                "status": "passed",
                "fieldDecisions": {
                    field: {"action": "keep"} for field in HOUSING_FACTUAL_FIELDS
                },
                "materialDefects": [
                    {
                        "code": "unsupported-safety-critical-claim",
                        "field": "petsAllowed",
                        "reason": "The verifier invented an out-of-contract field.",
                    }
                ],
            },
            HOUSING_FACTUAL_FIELDS,
            playbook_for("housing").supplementary_fields,
        )
        self.assertEqual([], defects)
        self.assertIn("invalid-material-defect", {finding["code"] for finding in findings})

    def test_verifier_patch_cannot_mutate_identity_sources_or_unlisted_fields(self) -> None:
        dossier = {
            "candidateIdentity": {"organization": "Example", "program": "Food Box"},
            "sources": [
                {"id": "source-1", "url": "https://example.org", "supports": []},
                {"id": "source-2", "url": "https://example.net", "supports": []},
            ],
            "fields": {
                "phone": {"status": "supported", "value": "480-555-0100"},
                "hours": {"status": "unknown", "reason": "Not published"},
            },
        }
        verified, findings, defects = apply_verification_decisions(
            dossier,
            {
                "fieldDecisions": {
                    "phone": {
                        "action": "downgrade-to-unknown",
                        "reason": "The cited source describes another program.",
                    },
                    "hours": {
                        "action": "mark-conflicting",
                        "reason": "Two current official schedules conflict.",
                        "alternatives": [
                            {"value": "Weekdays", "evidenceIds": ["source-1"]},
                            {"value": "Daily", "evidenceIds": ["source-2"]},
                        ],
                    },
                    "inventedField": {"action": "keep"},
                },
                "candidateIdentity": {"organization": "Mutated"},
                "sources": [],
                "materialDefects": [],
            },
            ["phone", "hours"],
        )
        self.assertEqual(dossier["candidateIdentity"], verified["candidateIdentity"])
        self.assertEqual(
            [source["url"] for source in dossier["sources"]],
            [source["url"] for source in verified["sources"]],
        )
        self.assertTrue(all(not source["supports"] for source in dossier["sources"]))
        self.assertEqual("unknown", verified["fields"]["phone"]["status"])
        self.assertEqual("conflicting", verified["fields"]["hours"]["status"])
        self.assertNotIn("inventedField", verified["fields"])
        self.assertEqual([], defects)
        self.assertIn(
            "invalid-verifier-decision-field",
            {finding["code"] for finding in findings},
        )
        self.assertIn(
            "forbidden-verifier-rewrite",
            {finding["code"] for finding in findings},
        )
        conflict_support = [
            binding
            for source in verified["sources"]
            for binding in source.get("supports", [])
            if binding.get("field") == "hours"
        ]
        self.assertEqual(2, len(conflict_support))

    def test_field_material_defect_is_quarantined_without_failing_candidate(self) -> None:
        dossier = {
            "fields": {
                "hours": {"status": "supported", "value": "Always open"},
            }
        }
        verified, findings, defects = apply_verification_decisions(
            dossier,
            {
                "status": "passed",
                "fieldDecisions": {"hours": {"action": "keep"}},
                "materialDefects": [
                    {
                        "code": "altered-or-invented-source",
                        "field": "hours",
                        "reason": "The retained hours were attributed to the wrong source.",
                    }
                ],
            },
            ["hours"],
        )
        self.assertEqual("unknown", verified["fields"]["hours"]["status"])
        self.assertEqual([], defects)
        self.assertEqual("field-material-defect", findings[0]["code"])
        self.assertEqual(
            "needs-review",
            verification_status(
                final_issues=[],
                material_defects=defects,
                review_findings=findings,
                requested_status="passed",
            ),
        )

    def test_candidate_fatal_defect_still_fails(self) -> None:
        _verified, findings, defects = apply_verification_decisions(
            {"fields": {"geography": {"status": "unknown", "reason": "Not found"}}},
            {
                "status": "needs-review",
                "fieldDecisions": {"geography": {"action": "keep"}},
                "materialDefects": [
                    {
                        "code": "wrong-geography",
                        "candidateViability": "candidate-fatal",
                        "reason": "No credible evidence indicates service in the configured area.",
                    }
                ],
            },
            ["geography"],
        )
        self.assertEqual([], findings)
        self.assertEqual("candidate-fatal", defects[0]["candidateViability"])
        self.assertEqual(
            "failed",
            verification_status(
                final_issues=[],
                material_defects=defects,
                review_findings=[],
                requested_status="needs-review",
            ),
        )

    def test_hosted_referral_attribution_can_be_semantically_resolved(self) -> None:
        identity_key = "candidate org::coordinated entry"
        packet = {
            "candidateIdentity": {
                "organization": "Candidate Org",
                "program": "Coordinated Entry",
                "identityKey": identity_key,
            },
            "sources": [
                {
                    "id": 1,
                    "canonical_url": "https://referrer.example/access-points",
                    "authority": "government-referral",
                    "page_identity_key": "referrer::access point list",
                    "extract": {
                        "title": "Access points",
                        "text": "Candidate Org provides coordinated entry.",
                    },
                }
            ],
        }
        dossier = {
            "candidateIdentity": {
                "organization": "Candidate Org",
                "program": "Coordinated Entry",
                "identityKey": identity_key,
                "componentIdentityKeys": [identity_key],
            },
            "sources": [
                {
                    "id": "1",
                    "url": "https://referrer.example/access-points",
                    "extract": "Candidate Org provides coordinated entry.",
                    "authority": "government-referral",
                    "pageIdentityKey": "referrer::access point list",
                    "pageOrganizationKey": "referrer",
                    "supports": [
                        {
                            "field": "description",
                            "value": "Provides coordinated entry",
                            "scope": "program",
                        }
                    ],
                    "contradicts": [],
                }
            ],
            "fields": {
                "description": {
                    "status": "supported",
                    "value": "Provides coordinated entry",
                    "evidenceIds": ["1"],
                }
            },
        }
        status, verified, findings = derive_verification_from_response(
            dossier,
            packet,
            {
                "status": "passed",
                "fieldDecisions": {"description": {"action": "keep"}},
                "materialDefects": [],
                "findings": [
                    {
                        "code": "cross-program-evidence",
                        "field": "description",
                        "action": "flagged",
                        "reason": "The page hosts a named multi-organization access-point list.",
                    }
                ],
            },
            ["description"],
        )
        self.assertEqual("needs-review", status)
        self.assertEqual("supported", verified["fields"]["description"]["status"])
        self.assertEqual([], findings["finalDeterministicFindings"])
        self.assertEqual(
            "cross-program-evidence",
            findings["semanticResolutionFindings"][0]["deterministicCode"],
        )

    def test_false_semantic_conflict_does_not_delete_supported_field(self) -> None:
        identity_key = "example::program"
        packet_sources = []
        dossier_sources = []
        for source_id, value in ((1, "Short description"), (2, "Longer description")):
            packet_sources.append(
                {
                    "id": source_id,
                    "canonical_url": f"https://example.org/{source_id}",
                    "authority": "direct-provider",
                    "page_identity_key": identity_key,
                    "extract": {"title": "Program", "text": value},
                }
            )
            dossier_sources.append(
                {
                    "id": str(source_id),
                    "url": f"https://example.org/{source_id}",
                    "extract": value,
                    "authority": "direct-provider",
                    "pageIdentityKey": identity_key,
                    "pageOrganizationKey": "example",
                    "supports": [
                        {"field": "description", "value": value, "scope": "program"}
                    ],
                    "contradicts": [],
                }
            )
        packet = {
            "candidateIdentity": {
                "organization": "Example",
                "program": "Program",
                "identityKey": identity_key,
            },
            "sources": packet_sources,
        }
        dossier = {
            "candidateIdentity": {
                **packet["candidateIdentity"],
                "componentIdentityKeys": [identity_key],
            },
            "sources": dossier_sources,
            "fields": {
                "description": {
                    "status": "supported",
                    "value": "Longer description",
                    "evidenceIds": ["2"],
                }
            },
        }
        status, verified, findings = derive_verification_from_response(
            dossier,
            packet,
            {
                "status": "passed",
                "fieldDecisions": {"description": {"action": "keep"}},
                "materialDefects": [],
                "findings": [
                    {
                        "code": "false-positive-conflict",
                        "field": "description",
                        "action": "flagged",
                        "reason": "The two descriptions are complementary, not incompatible.",
                    }
                ],
            },
            ["description"],
        )
        self.assertEqual("needs-review", status)
        self.assertEqual("supported", verified["fields"]["description"]["status"])
        self.assertEqual([], findings["finalDeterministicFindings"])

    def test_frozen_source_envelope_is_restored_without_hiding_invented_ids(self) -> None:
        packet = {
            "sources": [
                {
                    "id": 7,
                    "canonical_url": "https://example.org/program",
                    "authority": "direct-provider",
                    "page_identity_key": "example::program",
                    "extract": {"title": "Program", "text": "Frozen exact text"},
                }
            ]
        }
        dossier = {
            "sources": [
                {"id": "7", "extract": "model summary", "supports": []},
                {"id": "invented", "extract": "made up", "supports": []},
            ]
        }
        restored = restore_frozen_source_envelopes(dossier, packet)
        self.assertEqual("Frozen exact text", restored["sources"][0]["extract"])
        self.assertEqual("made up", restored["sources"][1]["extract"])

    def test_reviewed_identity_receipts_restore_only_identity_bindings(self) -> None:
        identity_key = "newtown community development corporation::community land trust"
        source_text = (
            "Community Land Trust\nNewtown's Community Land Trust provides "
            "permanently affordable housing."
        )
        packet = {
            "candidateIdentity": {
                "organization": "Newtown Community Development Corporation",
                "program": "Community Land Trust",
                "identityKey": identity_key,
            },
            "sources": [
                {
                    "id": 7,
                    "canonical_url": "https://example.org/clt",
                    "authority": "direct-provider",
                    "page_identity_key": identity_key,
                    "extract": {
                        "title": "Community Land Trust",
                        "text": source_text,
                        "selection": {
                            "method": "reviewed-exact-section",
                            "policyVersion": EVIDENCE_PREPARATION_POLICY_VERSION,
                        },
                        "identitySupport": {
                            "organization": {
                                "relationship": "reviewed-alias",
                                "sourceLabel": "Newtown",
                                "evidenceExcerpt": "Newtown's Community Land Trust",
                                "reason": "The reviewed direct-provider page uses its short name.",
                            },
                            "program": {
                                "relationship": "exact-label",
                                "sourceLabel": "Community Land Trust",
                                "evidenceExcerpt": "Community Land Trust",
                            },
                        },
                    },
                }
            ],
        }
        dossier = {
            "candidateIdentity": {
                **packet["candidateIdentity"],
                "componentIdentityKeys": [identity_key],
            },
            "sources": [
                {
                    "id": "7",
                    "url": "https://example.org/clt",
                    "title": "Community Land Trust",
                    "extract": source_text,
                    "authority": "direct-provider",
                    "pageIdentityKey": identity_key,
                    "pageOrganizationKey": "newtown community development corporation",
                    "supports": [],
                    "contradicts": [],
                }
            ],
            "fields": {
                "organization": {
                    "status": "supported",
                    "value": "Newtown Community Development Corporation",
                    "evidenceIds": ["7"],
                },
                "program": {
                    "status": "supported",
                    "value": "Community Land Trust",
                    "evidenceIds": ["7"],
                },
                "phone": {
                    "status": "supported",
                    "value": "602-000-0000",
                    "evidenceIds": ["7"],
                },
            },
        }

        restored = restore_reviewed_identity_bindings(dossier, packet)
        bindings = restored["sources"][0]["supports"]

        self.assertEqual(
            {"organization", "program"},
            {binding["field"] for binding in bindings},
        )
        self.assertNotIn("phone", {binding["field"] for binding in bindings})
        issues = validate_dossier_for_packet(
            dossier, packet, ("organization", "program", "phone")
        )
        self.assertEqual(
            [("phone", "source-does-not-support-field")],
            [(issue.get("field"), issue["code"]) for issue in issues],
        )

    def test_rederivation_accepts_a_reviewed_identity_receipt_resolution(self) -> None:
        identity_key = "house of refuge::transitional housing program"
        source_text = "House of Refuge\nTransitional Housing Program"
        packet = {
            "candidateIdentity": {
                "organization": "House of Refuge",
                "program": "Transitional Housing Program",
                "identityKey": identity_key,
            },
            "sources": [
                {
                    "id": 7,
                    "canonical_url": "https://example.org/housing",
                    "authority": "direct-provider",
                    "page_identity_key": identity_key,
                    "extract": {
                        "title": "Transitional Housing Program",
                        "text": source_text,
                        "selection": {
                            "method": "reviewed-full-page",
                            "policyVersion": EVIDENCE_PREPARATION_POLICY_VERSION,
                        },
                        "identitySupport": {
                            "organization": {
                                "relationship": "exact-label",
                                "sourceLabel": "House of Refuge",
                                "evidenceExcerpt": "House of Refuge",
                            },
                            "program": {
                                "relationship": "exact-label",
                                "sourceLabel": "Transitional Housing Program",
                                "evidenceExcerpt": "Transitional Housing Program",
                            },
                        },
                    },
                }
            ],
        }
        dossier = {
            "candidateIdentity": {
                **packet["candidateIdentity"],
                "componentIdentityKeys": [identity_key],
            },
            "sources": [
                {
                    "id": "7",
                    "url": "https://example.org/housing",
                    "title": "Transitional Housing Program",
                    "extract": source_text,
                    "authority": "direct-provider",
                    "pageIdentityKey": identity_key,
                    "pageOrganizationKey": "house of refuge",
                    "supports": [
                        {
                            "field": "organization",
                            "value": "House of Refuge",
                            "scope": "organization",
                        }
                    ],
                    "contradicts": [],
                }
            ],
            "fields": {
                "organization": {
                    "status": "supported",
                    "value": "House of Refuge",
                    "evidenceIds": ["7"],
                },
                "program": {
                    "status": "supported",
                    "value": "Transitional Housing Program",
                    "evidenceIds": ["7"],
                },
            },
        }
        response = {
            "status": "passed",
            "fieldDecisions": {
                "organization": {"action": "keep"},
                "program": {"action": "keep"},
            },
            "materialDefects": [],
            "findings": [
                {
                    "code": "deterministic-finding-resolved",
                    "field": "program",
                    "action": "flagged",
                    "reason": "The earlier deterministic finding is a false positive.",
                }
            ],
        }

        status, verified, findings = derive_verification_from_response(
            dossier, packet, response, ("organization", "program")
        )

        self.assertEqual("passed", status)
        self.assertEqual("supported", verified["fields"]["program"]["status"])
        self.assertEqual([], findings["finalDeterministicFindings"])
        self.assertTrue(
            any(
                item["code"] == "obsolete-deterministic-finding-resolution"
                for item in findings["semanticResolutionFindings"]
            )
        )

    def test_source_binding_compaction_preserves_only_model_owned_fields(self) -> None:
        dossier = {
            "sources": [
                {
                    "id": 7,
                    "url": "https://example.org/program",
                    "extract": "immutable text",
                    "authority": "direct-provider",
                    "supports": [{"field": "phone", "value": "211"}],
                    "contradicts": [],
                }
            ],
            "fields": {"phone": {"status": "supported", "value": "211"}},
        }
        compacted = compact_source_bindings(dossier)

        self.assertEqual(
            [{"id": 7, "supports": [{"field": "phone", "value": "211"}], "contradicts": []}],
            compacted["sources"],
        )
        self.assertEqual(dossier["fields"], compacted["fields"])
        self.assertIn("url", dossier["sources"][0])

    def test_frozen_candidate_identity_is_restored_without_dropping_review_metadata(self) -> None:
        packet = {
            "candidateIdentity": {
                "organization": "A New Leaf",
                "program": "Community Alliance Against Family Abuse Shelter",
                "identityKey": "a new leaf::community alliance against family abuse shelter",
            }
        }
        dossier = {
            "candidateIdentity": {
                "organization": "A New Leaf",
                "program": "Community Alliance Against Family Abuse (CAAFA)",
                "identityKey": "a new leaf::community alliance against family abuse shelter",
                "boundaryState": "resolved",
                "coverageTags": ["domestic-violence"],
            }
        }
        restored = restore_frozen_candidate_identity(dossier, packet)

        self.assertEqual(
            packet["candidateIdentity"]["program"],
            restored["candidateIdentity"]["program"],
        )
        self.assertEqual(
            [packet["candidateIdentity"]["identityKey"]],
            restored["candidateIdentity"]["componentIdentityKeys"],
        )
        self.assertEqual("resolved", restored["candidateIdentity"]["boundaryState"])
        self.assertEqual(
            ["domestic-violence"], restored["candidateIdentity"]["coverageTags"]
        )

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.store = ResearchStore(Path(self.temporary.name) / "research.sqlite3")
        self.providers = FixtureProviders()
        discovery = OptimizationDiscoveryPipeline(
            self.store,
            self.providers.configuration("model-fixture-discovery"),
            search=self.providers.search,
            fetch=self.providers.fetch,
            resolve_identity=self.providers.resolve,
            existing_resources=self.providers.fixture["existingResources"],
        )
        self.corpus = discovery.run()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def pipeline(
        self,
        models: SeededFixtureModels,
        label: str,
        *,
        progress=None,
        extract=None,
        verify=None,
    ) -> OptimizationModelPipeline:
        return OptimizationModelPipeline(
            self.store,
            model_configuration(self.providers, label),
            self.corpus.corpus_id,
            extract=extract or models.extract,
            verify=verify or models.verify,
            required_coverage_needs=(
                {
                    "key": "emergency-adult",
                    "label": "Adult emergency access",
                    "query": '"Mesa" adult emergency shelter intake',
                },
                {
                    "key": "medical-respite",
                    "label": "Medical respite",
                    "query": '"Mesa" medical respite homeless program',
                },
                {
                    "key": "adult-pathway",
                    "label": "Equivalent adult access tag",
                    "query": '"Mesa" adult access pathway',
                    "satisfiedByAnyTags": ["emergency-adult", "adult-pathway"],
                },
                {
                    "key": "operational-boundary-check",
                    "label": "Completed boundary check",
                    "query": '"Mesa" regional boundary check',
                    "candidateGap": False,
                },
            ),
            progress=progress,
        )

    def test_fresh_verifier_catches_seeded_defects_and_gap_audit_plans_query(self) -> None:
        models = SeededFixtureModels()
        pipeline = self.pipeline(models, "model-fixture-four-bit")
        result = pipeline.run()

        self.assertTrue(result.quality_gate_passed)
        self.assertEqual(7, result.packet_count)
        self.assertEqual(7, result.passed_count)
        self.assertEqual(0, result.needs_review_count)
        self.assertEqual(0, result.failed_count)
        self.assertEqual(1, result.supported_field_count)
        self.assertEqual(7 * len(HOUSING_FACTUAL_FIELDS) - 1, result.unknown_field_count)
        self.assertEqual(1, result.gap_count)
        self.assertEqual(7, len(models.extract_prompts))
        self.assertEqual(7, len(models.verify_prompts))
        self.assertTrue(
            all(prompt["operation"] == "extract-candidate-dossier" for prompt in models.extract_prompts)
        )
        self.assertTrue(all(prompt.get("outputContract") for prompt in models.extract_prompts))
        self.assertTrue(
            all(
                "only id, supports, and contradicts"
                in prompt["outputContract"]["sources"]
                for prompt in models.extract_prompts
            )
        )
        self.assertTrue(
            all(
                "Use only program or organization as an evidence-binding scope."
                in prompt["instructions"]
                for prompt in models.extract_prompts
            )
        )
        self.assertTrue(
            all(
                any(
                    "never fax numbers or email addresses" in instruction
                    for instruction in prompt["instructions"]
                )
                for prompt in models.extract_prompts
            )
        )
        self.assertTrue(
            all(
                any(
                    "never return a bare alternate number" in instruction
                    for instruction in prompt["instructions"]
                )
                for prompt in models.extract_prompts
            )
        )
        self.assertTrue(
            all(
                any(
                    "access points, properties, partners, subprograms"
                    in instruction
                    for instruction in prompt["instructions"]
                )
                for prompt in models.extract_prompts
            )
        )
        self.assertTrue(
            all(
                any(
                    "site footer, headquarters, admin office"
                    in instruction
                    for instruction in prompt["instructions"]
                )
                for prompt in models.extract_prompts
            )
        )
        self.assertTrue(
            all(
                any(
                    "direct-provider source canonical URL"
                    in instruction
                    for instruction in prompt["instructions"]
                )
                for prompt in models.extract_prompts
            )
        )
        self.assertTrue(
            all(
                "access-point, property, partner, subprogram, and system attribution"
                in prompt["checklist"]
                for prompt in models.verify_prompts
            )
        )
        self.assertTrue(
            all(
                "footer, headquarters, admin-office, and service-geography attribution"
                in prompt["checklist"]
                for prompt in models.verify_prompts
            )
        )
        self.assertTrue(
            all(
                "exact-identity direct-provider URL evidence for the website field"
                in prompt["checklist"]
                for prompt in models.verify_prompts
            )
        )
        self.assertTrue(
            all(
                "a source-supported purpose label for every additional phone number"
                in prompt["checklist"]
                for prompt in models.verify_prompts
            )
        )
        self.assertTrue(
            all(
                prompt["operation"]
                == "verify-candidate-dossier-decision-patch-fresh-context"
                for prompt in models.verify_prompts
            )
        )
        self.assertTrue(all(prompt.get("outputContract") for prompt in models.verify_prompts))
        self.assertTrue(
            all(
                all(
                    set(source) <= {"id", "supports", "contradicts"}
                    for source in prompt["dossier"]["sources"]
                )
                for prompt in models.verify_prompts
            )
        )
        detected_codes = {
            finding["code"]
            for prompt in models.verify_prompts
            for finding in prompt["deterministicFindings"]
        }
        self.assertTrue(
            {
                "source-does-not-support-field",
                "contradicted-field",
                "missing-evidence",
            }.issubset(detected_codes)
        )

        with self.store.connect() as connection:
            final_findings = [
                json.loads(row["findings_json"])["finalDeterministicFindings"]
                for row in connection.execute(
                    "SELECT findings_json FROM optimization_verifications"
                ).fetchall()
            ]
            self.assertTrue(all(not findings for findings in final_findings))
            gaps = connection.execute(
                "SELECT need_key, query_text, status FROM optimization_gap_queries"
            ).fetchall()
            self.assertEqual(
                [("medical-respite", '"Mesa" medical respite homeless program', "planned")],
                [(row["need_key"], row["query_text"], row["status"]) for row in gaps],
            )

        candidates = pipeline.verified_candidates(result.run_id)
        self.assertEqual(7, len(candidates))
        self.assertTrue(all(candidate["name"] for candidate in candidates))
        self.assertTrue(all(candidate["evidence"] for candidate in candidates))
        self.assertEqual(
            7 * len(HOUSING_FACTUAL_FIELDS) - 1,
            sum(len(candidate["unknowns"]) for candidate in candidates),
        )
        self.assertTrue(any(candidate.get("phone") == "480-000-0100" for candidate in candidates))

    def test_completed_run_can_be_rederived_without_model_calls_and_with_history(self) -> None:
        models = SeededFixtureModels()
        result = self.pipeline(models, "model-fixture-rederive").run()
        with self.store.connect() as connection:
            verification = connection.execute(
                """SELECT verification.id
                   FROM optimization_verifications AS verification
                   JOIN optimization_candidate_dossiers AS dossier
                     ON dossier.id = verification.dossier_id
                   WHERE dossier.run_id = ? ORDER BY dossier.packet_id LIMIT 1""",
                (result.run_id,),
            ).fetchone()
            connection.execute(
                "UPDATE optimization_verifications SET status = 'failed' WHERE id = ?",
                (verification["id"],),
            )
            attempts_before = [
                tuple(row)
                for row in connection.execute(
                    """SELECT id, operation, status, raw_output, parsed_json
                       FROM optimization_model_attempts WHERE run_id = ? ORDER BY id""",
                    (result.run_id,),
                ).fetchall()
            ]
        recompute_model_evaluation_audits(self.store, result.run_id)

        recomputed = recompute_persisted_verifications(self.store, result.run_id)
        self.assertEqual(1, recomputed.before["statusCounts"]["failed"])
        self.assertEqual(0, recomputed.after["statusCounts"]["failed"])
        self.assertEqual(0, recomputed.model_inference_calls)
        self.assertNotEqual(
            recomputed.source_snapshot_sha256, recomputed.derived_snapshot_sha256
        )

        repeated = recompute_persisted_verifications(self.store, result.run_id)
        self.assertEqual(recomputed.revision_id, repeated.revision_id)
        with self.store.connect() as connection:
            attempts_after = [
                tuple(row)
                for row in connection.execute(
                    """SELECT id, operation, status, raw_output, parsed_json
                       FROM optimization_model_attempts WHERE run_id = ? ORDER BY id""",
                    (result.run_id,),
                ).fetchall()
            ]
            revision_count = connection.execute(
                """SELECT COUNT(*) FROM optimization_verification_revisions
                   WHERE run_id = ?""",
                (result.run_id,),
            ).fetchone()[0]
            with self.assertRaisesRegex(
                sqlite3.IntegrityError, "verification revisions are immutable"
            ):
                connection.execute(
                    """UPDATE optimization_verification_revisions
                       SET policy_version = 'changed' WHERE id = ?""",
                    (recomputed.revision_id,),
                )
        self.assertEqual(attempts_before, attempts_after)
        self.assertEqual(1, revision_count)

    def test_non_housing_pipeline_uses_the_selected_playbook_field_contract(self) -> None:
        store = ResearchStore(Path(self.temporary.name) / "food.sqlite3")
        providers = FixtureProviders()
        source_package_path = Path(self.temporary.name) / "source-food-package.zip"
        with zipfile.ZipFile(source_package_path, "w") as archive:
            archive.writestr(
                "tso-resources.json",
                json.dumps(
                    {
                        "resourcePackageSchemaVersion": 3,
                        "packageVersion": 1,
                        "categories": [
                            {"id": "food", "label": "Food", "filters": ["Pantries"]}
                        ],
                        "resources": [],
                    }
                ),
            )
        source_package = ResourcePackageImporter("food").read(source_package_path)
        store.save_import(source_package)
        discovery_configuration = providers.configuration("food-fixture-discovery")
        discovery_configuration["sourcePackageSha256"] = source_package.sha256
        discovery_configuration["sourcePackageVersion"] = "1"
        discovery_configuration["targetCategoryId"] = "food"
        discovery_configuration["stageKey"] = "immediate-food"
        discovery_configuration["queryPlan"] = deepcopy(
            discovery_configuration["queryPlan"]
        )
        discovery_configuration["queryPlan"]["categoryId"] = "food"
        discovery_configuration["queryPlan"]["stageKey"] = "immediate-food"

        def resolve_food(result: dict) -> dict | list[dict] | None:
            resolved = providers.resolve(result)
            if isinstance(resolved, list):
                retained = [
                    {**item, "stageKey": "immediate-food"}
                    for item in resolved
                    if item.get("stageKey", "urgent-access") == "urgent-access"
                ]
                return retained or None
            if isinstance(resolved, dict):
                if resolved.get("stageKey", "urgent-access") != "urgent-access":
                    return None
                return {**resolved, "stageKey": "immediate-food"}
            return None

        corpus = OptimizationDiscoveryPipeline(
            store,
            discovery_configuration,
            search=providers.search,
            fetch=providers.fetch,
            resolve_identity=resolve_food,
            existing_resources=providers.fixture["existingResources"],
        ).run()
        configuration = model_configuration(providers, "food-fixture-model")
        for field in (
            "sourcePackageSha256",
            "sourcePackageVersion",
            "targetCategoryId",
            "stageKey",
            "queryPlan",
        ):
            configuration[field] = deepcopy(discovery_configuration[field])
        models = SeededFixtureModels()
        result = OptimizationModelPipeline(
            store,
            configuration,
            corpus.corpus_id,
            extract=models.extract,
            verify=models.verify,
        ).run()

        food_fields = playbook_for("food").factual_fields
        self.assertNotIn("petPolicy", food_fields)
        self.assertTrue(
            all(prompt["requiredFields"] == list(food_fields) for prompt in models.extract_prompts)
        )
        self.assertTrue(
            all(prompt["requiredFields"] == list(food_fields) for prompt in models.verify_prompts)
        )
        self.assertTrue(
            all(
                all("housing" not in instruction.casefold() for instruction in prompt["instructions"])
                for prompt in models.extract_prompts
            )
        )
        self.assertEqual(result.packet_count * len(food_fields), result.supported_field_count + result.conflicting_field_count + result.unknown_field_count)
        with store.connect() as connection:
            dossiers = connection.execute(
                "SELECT verified_dossier_json FROM optimization_verifications"
            ).fetchall()
        self.assertTrue(
            all(
                "petPolicy" not in json.loads(row["verified_dossier_json"])["fields"]
                for row in dossiers
            )
        )
        review = build_optimization_review_copy(store, result.run_id)
        self.assertEqual("Food", review.data["run"]["targetCategoryLabel"])
        self.assertEqual(
            "Curate independently verified Food calibration candidates.",
            review.data["run"]["assignment"],
        )
        self.assertNotIn("Housing", review.data["title"])
        accepted = review.data["candidates"][0]
        provenance = accepted["candidate"]["optimizationProvenance"]
        self.assertEqual(
            optimization_resource_id(
                provenance["configurationHash"], provenance["packetSha256"]
            ),
            accepted["resourceDraft"]["id"],
        )
        self.assertEqual(["food"], accepted["resourceDraft"]["categories"])
        self.assertEqual(
            accepted["id"],
            optimization_candidate_id(
                provenance["configurationHash"], provenance["packetSha256"]
            ),
        )
        package_path = Path(self.temporary.name) / "phone-vetted-food-package.zip"
        with zipfile.ZipFile(package_path, "w") as archive:
            archive.writestr(
                "tso-resources.json",
                json.dumps(
                    {
                        "resourcePackageSchemaVersion": 3,
                        "packageVersion": 2,
                        "categories": [{"id": "food", "label": "Food"}],
                        "resources": [
                            {
                                "id": optimization_resource_id(
                                    provenance["configurationHash"],
                                    provenance["packetSha256"],
                                ),
                                "name": accepted["name"],
                                "categories": ["food"],
                            }
                        ],
                    }
                ),
            )
        outcome = compare_optimization_run_to_package(
            store, result.run_id, package_path
        )
        self.assertEqual("food", outcome.report["targetCategoryId"])
        self.assertEqual(1, outcome.accepted_count)

        curator_script = r"""
const fs = require('fs');
(0, eval)(fs.readFileSync('web/review-copy.js', 'utf8'));
const review = JSON.parse(fs.readFileSync(0, 'utf8'));
const state = ReviewAppCore.initialState(review);
const acceptedId = String(review.candidates[0].id);
ReviewAppCore.setCandidateOutcome(
  state.candidates[acceptedId], 'ready-for-package', '2026-08-24T08:00:00Z', 'Vetter'
);
const built = ReviewAppCore.buildResourcePackage(review, state, '2026-08-24T08:05:00Z');
if (built.errors.length) throw new Error(built.errors.join('\n'));
ReviewAppCore.archivePackagedCandidates(review, state, built, '2026-08-24T08:05:00Z');
process.stdout.write(JSON.stringify({ state, package: built.data }));
"""
        curator_result = subprocess.run(
            ["node", "-e", curator_script],
            input=json.dumps(review.data),
            text=True,
            capture_output=True,
        )
        self.assertEqual(0, curator_result.returncode, curator_result.stderr)
        generated_curator = json.loads(curator_result.stdout)
        generated_identity = resource_program_identity(
            generated_curator["package"]["resources"][0]
        )
        self.assertEqual(
            (
                accepted["candidate"]["organization"],
                accepted["candidate"]["program"],
            ),
            generated_identity,
        )
        self.assertEqual(
            "same-program",
            package_exclusion_state(
                accepted["candidate"]["organization"],
                accepted["candidate"]["program"],
                *generated_identity,
            ),
        )
        curator_work_path = Path(self.temporary.name) / "food-curator-work.json"
        curator_work_path.write_text(
            json.dumps(generated_curator["state"]), encoding="utf-8"
        )
        curator_package_path = Path(self.temporary.name) / "food-curator-package.zip"
        with zipfile.ZipFile(curator_package_path, "w") as archive:
            archive.writestr(
                "tso-resources.json", json.dumps(generated_curator["package"])
            )
        curator_outcome = compare_optimization_run_to_package(
            store,
            result.run_id,
            curator_package_path,
            curator_work_path=curator_work_path,
        )
        self.assertEqual(3, curator_outcome.report["schemaVersion"])
        self.assertEqual("food", curator_outcome.report["targetCategoryId"])
        self.assertEqual(1, curator_outcome.accepted_count)
        self.assertEqual(1, curator_outcome.report["terminalHumanOutcomeCount"])
        self.assertEqual(
            {
                "pending": len(review.data["candidates"]) - 1,
                "present-in-vetted-package": 1,
            },
            curator_outcome.report["outcomeCounts"],
        )
        accepted_outcome = next(
            item
            for item in curator_outcome.report["outcomes"]
            if item["outcome"] == "present-in-vetted-package"
        )
        self.assertEqual("entered-package", accepted_outcome["curatorOutcome"])

    def test_inspection_open_does_not_recover_an_active_model_attempt(self) -> None:
        configuration_id = self.store.save_optimization_configuration(
            model_configuration(self.providers, "active-model-inspection")
        )
        with self.store.connect() as connection:
            run_id = int(
                connection.execute(
                    """INSERT INTO optimization_runs (
                           created_at, label, configuration_id, corpus_id, run_kind,
                           status, current_phase
                       ) VALUES ('now', 'active-model-inspection', ?, ?,
                                 'model-evaluation', 'running', 'candidate-extraction')""",
                    (configuration_id, self.corpus.corpus_id),
                ).lastrowid
            )
            packet_id = int(
                connection.execute(
                    """SELECT id FROM optimization_evidence_packets
                       WHERE corpus_id = ? ORDER BY id LIMIT 1""",
                    (self.corpus.corpus_id,),
                ).fetchone()["id"]
            )
            attempt_id = int(
                connection.execute(
                    """INSERT INTO optimization_model_attempts (
                           run_id, packet_id, corpus_id, operation, attempt_number,
                           started_at, status, prompt_sha256
                       ) VALUES (?, ?, ?, 'extract', 1, 'now', 'running', ?)""",
                    (run_id, packet_id, self.corpus.corpus_id, "0" * 64),
                ).lastrowid
            )

        inspected = ResearchStore(self.store.path)
        with inspected.connect() as connection:
            self.assertEqual(
                "running",
                connection.execute(
                    "SELECT status FROM optimization_model_attempts WHERE id = ?",
                    (attempt_id,),
                ).fetchone()["status"],
            )
            self.assertEqual(
                "running",
                connection.execute(
                    "SELECT status FROM optimization_runs WHERE id = ?", (run_id,)
                ).fetchone()["status"],
            )

        recovered = ResearchStore(self.store.path, recover_interrupted=True)
        with recovered.connect() as connection:
            self.assertEqual(
                "failed",
                connection.execute(
                    "SELECT status FROM optimization_model_attempts WHERE id = ?",
                    (attempt_id,),
                ).fetchone()["status"],
            )
            self.assertEqual(
                "partial",
                connection.execute(
                    "SELECT status FROM optimization_runs WHERE id = ?", (run_id,)
                ).fetchone()["status"],
            )

    def test_needs_review_is_reported_separately_and_reaches_candidate_output(self) -> None:
        review_models = SeededFixtureModels()

        def needs_review(prompt: dict) -> dict:
            result = review_models.verify(prompt)
            return {**result, "status": "needs-review"}

        review_pipeline = self.pipeline(
            review_models,
            "model-fixture-needs-review",
            verify=needs_review,
        )
        review_result = review_pipeline.run()
        self.assertTrue(review_result.quality_gate_passed)
        self.assertEqual(0, review_result.passed_count)
        self.assertEqual(7, review_result.needs_review_count)
        self.assertEqual(0, review_result.failed_count)
        review_candidates = review_pipeline.verified_candidates(review_result.run_id)
        self.assertEqual(7, len(review_candidates))
        self.assertTrue(
            all(
                candidate["verificationStatus"] == "needs-review"
                for candidate in review_candidates
            )
        )
        self.assertTrue(
            all(
                "verifierFindings" in candidate["verificationFindings"]
                for candidate in review_candidates
            )
        )

        mixed_models = SeededFixtureModels()

        def mixed_statuses(prompt: dict) -> dict:
            result = mixed_models.verify(prompt)
            program = prompt["candidateIdentity"]["program"]
            if program == "Rapid Re-Housing":
                return {**result, "status": "needs-review"}
            if program == "Brian Garcia Welcome Center":
                result["materialDefects"].append(
                    {
                        "code": "identity-conflation",
                        "reason": "Fixture material identity defect",
                    }
                )
            return result

        mixed_pipeline = self.pipeline(
            mixed_models,
            "model-fixture-mixed-verification-statuses",
            verify=mixed_statuses,
        )
        mixed_result = mixed_pipeline.run()
        self.assertFalse(mixed_result.quality_gate_passed)
        self.assertEqual(5, mixed_result.passed_count)
        self.assertEqual(1, mixed_result.needs_review_count)
        self.assertEqual(1, mixed_result.failed_count)
        self.assertEqual(6, len(mixed_pipeline.verified_candidates(mixed_result.run_id)))
        with self.store.connect() as connection:
            completeness = json.loads(
                connection.execute(
                    """SELECT report_json FROM optimization_audits
                       WHERE run_id = ? AND audit_type = 'candidate-completeness'""",
                    (mixed_result.run_id,),
                ).fetchone()["report_json"]
            )
            quality = json.loads(
                connection.execute(
                    """SELECT report_json FROM optimization_audits
                       WHERE run_id = ? AND audit_type = 'quality-gate'""",
                    (mixed_result.run_id,),
                ).fetchone()["report_json"]
            )
        self.assertEqual(1, completeness["needsReviewCount"])
        self.assertEqual(1, completeness["failedCount"])
        self.assertEqual(1, quality["verificationNeedsReview"])
        self.assertEqual(1, quality["verificationFailures"])
        review = build_optimization_review_copy(
            self.store,
            mixed_result.run_id,
        )
        repeated_review = build_optimization_review_copy(
            self.store,
            mixed_result.run_id,
        )
        self.assertEqual(6, len(review.data["candidates"]))
        self.assertEqual(
            [item["id"] for item in review.data["candidates"]],
            [item["id"] for item in repeated_review.data["candidates"]],
        )
        self.assertEqual(
            {"passed", "needs-review"},
            {
                item["candidate"]["verificationStatus"]
                for item in review.data["candidates"]
            },
        )
        self.assertTrue(
            all(
                item["candidate"]["optimizationProvenance"]["runId"]
                == mixed_result.run_id
                for item in review.data["candidates"]
            )
        )
        self.assertTrue(
            all(
                "verifierFindings" in item["candidate"]["verificationFindings"]
                for item in review.data["candidates"]
            )
        )
        self.assertNotIn("wrong::program", review.html.decode("utf-8"))
        package_path = Path(self.temporary.name) / "phone-vetted-resource-package.zip"
        accepted_candidates = review.data["candidates"][:2]
        resources = []
        for position, item in enumerate(accepted_candidates):
            provenance = item["candidate"]["optimizationProvenance"]
            packet_reference = (
                provenance["packetSha256"]
                if position == 0
                else provenance["packetId"]
            )
            resources.append(
                {
                    "id": optimization_resource_id(
                        provenance["configurationHash"], packet_reference
                    ),
                    "name": item["name"],
                    "phone": "480-555-0100",
                    "categories": ["housing"],
                }
            )
        with zipfile.ZipFile(package_path, "w") as archive:
            archive.writestr(
                "tso-resources.json",
                json.dumps(
                    {
                        "resourcePackageSchemaVersion": 3,
                        "packageVersion": 2,
                        "categories": [{"id": "housing", "label": "Housing"}],
                        "resources": resources,
                    }
                ),
            )
        outcome = compare_optimization_run_to_package(
            self.store, mixed_result.run_id, package_path
        )
        self.assertEqual(6, outcome.candidate_count)
        self.assertEqual(2, outcome.accepted_count)
        self.assertEqual(4, outcome.not_present_count)
        self.assertEqual(
            {
                resources[0]["id"],
                resources[1]["id"],
            },
            {
                item["matchedResourceId"]
                for item in outcome.report["outcomes"]
                if item["matchedResourceId"]
            },
        )
        self.assertEqual(
            outcome.report_sha256,
            compare_optimization_run_to_package(
                self.store, mixed_result.run_id, package_path
            ).report_sha256,
        )
        with self.store.connect() as connection:
            self.assertEqual(
                1,
                connection.execute(
                    "SELECT COUNT(*) FROM optimization_package_outcomes"
                ).fetchone()[0],
            )

        candidate_ids = [str(item["id"]) for item in review.data["candidates"]]
        curator_states = {}
        for position, candidate_id in enumerate(candidate_ids):
            package_status = "packaged" if position < 2 else "pending"
            disposition = {
                2: "duplicate",
                3: "research-further",
                4: "wrong-category",
                5: "worth-pursuing",
            }.get(position, "")
            curator_states[candidate_id] = {
                "packageStatus": package_status,
                "disposition": disposition,
                "outcomeHistory": (
                    [{"outcome": disposition, "at": "later", "reviewerName": "Vetter"}]
                    if disposition
                    else []
                ),
                "packageHistory": (
                    [{"resourceId": resources[position]["id"], "at": "later"}]
                    if position < 2
                    else []
                ),
                "reviewedAt": "later" if disposition or position < 2 else None,
                "updatedAt": "later",
            }
        curator_work = {
            "reviewFeedbackSchemaVersion": 2,
            "reviewCopySchemaVersion": review.data["reviewCopySchemaVersion"],
            "reviewId": review.data["reviewId"],
            "sourceSha256": (
                review.data["sourcePackage"]["sourceSha256"]
                if review.data["sourcePackage"]
                else None
            ),
            "run": {
                "id": mixed_result.run_id,
                "categoryId": "housing",
                "categoryLabel": "Housing",
            },
            "packagedCandidateIds": candidate_ids[:2],
            "candidates": curator_states,
        }
        curator_work_path = Path(self.temporary.name) / "curator-work.json"
        curator_work_path.write_text(json.dumps(curator_work), encoding="utf-8")
        outcome_with_work = compare_optimization_run_to_package(
            self.store,
            mixed_result.run_id,
            package_path,
            curator_work_path=curator_work_path,
        )
        self.assertEqual(3, outcome_with_work.report["schemaVersion"])
        self.assertEqual(64, len(outcome_with_work.report["curatorWorkSha256"]))
        self.assertEqual(4, outcome_with_work.report["terminalHumanOutcomeCount"])
        self.assertEqual(4, outcome_with_work.report["explicitCuratorDispositionCount"])
        self.assertEqual(0.5, outcome_with_work.report["acceptedAmongTerminalOutcomeRate"])
        self.assertEqual(
            {
                "duplicate": 1,
                "present-in-vetted-package": 2,
                "research-further": 1,
                "worth-pursuing": 1,
                "wrong-category": 1,
            },
            outcome_with_work.report["outcomeCounts"],
        )
        self.assertEqual(
            set(candidate_ids),
            {item["candidateId"] for item in outcome_with_work.report["outcomes"]},
        )
        self.assertEqual(
            outcome_with_work.report_sha256,
            compare_optimization_run_to_package(
                self.store,
                mixed_result.run_id,
                package_path,
                curator_work_path=curator_work_path,
            ).report_sha256,
        )
        with self.store.connect() as connection:
            self.assertEqual(
                2,
                connection.execute(
                    "SELECT COUNT(*) FROM optimization_package_outcomes"
                ).fetchone()[0],
            )

        revised_work = deepcopy(curator_work)
        revised_work["candidates"][candidate_ids[-1]]["disposition"] = "rejected"
        revised_work["candidates"][candidate_ids[-1]]["outcomeHistory"] = [
            {"outcome": "rejected", "at": "latest", "reviewerName": "Vetter"}
        ]
        revised_work_path = Path(self.temporary.name) / "revised-curator-work.json"
        revised_work_path.write_text(json.dumps(revised_work), encoding="utf-8")
        revised_outcome = compare_optimization_run_to_package(
            self.store,
            mixed_result.run_id,
            package_path,
            curator_work_path=revised_work_path,
        )
        self.assertNotEqual(outcome_with_work.report_sha256, revised_outcome.report_sha256)
        self.assertEqual(5, revised_outcome.report["terminalHumanOutcomeCount"])
        self.assertEqual(0.4, revised_outcome.report["acceptedAmongTerminalOutcomeRate"])
        with self.store.connect() as connection:
            self.assertEqual(
                3,
                connection.execute(
                    "SELECT COUNT(*) FROM optimization_package_outcomes"
                ).fetchone()[0],
            )

        invalid_work = deepcopy(curator_work)
        invalid_work["candidates"].pop(candidate_ids[-1])
        invalid_work_path = Path(self.temporary.name) / "invalid-curator-work.json"
        invalid_work_path.write_text(json.dumps(invalid_work), encoding="utf-8")
        with self.assertRaisesRegex(
            OptimizationOutcomeError, "candidate set does not match"
        ):
            compare_optimization_run_to_package(
                self.store,
                mixed_result.run_id,
                package_path,
                curator_work_path=invalid_work_path,
            )

        with self.store.connect() as connection:
            legacy_row = connection.execute(
                """SELECT id, run_id, created_at, final_package_sha256,
                          report_json, report_sha256
                   FROM optimization_package_outcomes
                   WHERE curator_work_sha256 = ''"""
            ).fetchone()
            connection.execute("DROP TABLE optimization_package_outcomes")
            connection.execute(
                """CREATE TABLE optimization_package_outcomes (
                       id INTEGER PRIMARY KEY,
                       run_id INTEGER NOT NULL
                           REFERENCES optimization_runs(id) ON DELETE CASCADE,
                       created_at TEXT NOT NULL,
                       final_package_sha256 TEXT NOT NULL
                           CHECK (length(final_package_sha256) = 64),
                       report_json TEXT NOT NULL,
                       report_sha256 TEXT NOT NULL
                           CHECK (length(report_sha256) = 64),
                       UNIQUE (run_id, final_package_sha256)
                   )"""
            )
            connection.execute(
                "INSERT INTO optimization_package_outcomes VALUES (?, ?, ?, ?, ?, ?)",
                tuple(legacy_row),
            )
        migrated_store = ResearchStore(self.store.path)
        with migrated_store.connect() as connection:
            migrated = connection.execute(
                """SELECT curator_work_sha256, report_sha256
                   FROM optimization_package_outcomes"""
            ).fetchone()
            self.assertEqual("", migrated["curator_work_sha256"])
            self.assertEqual(legacy_row["report_sha256"], migrated["report_sha256"])
            connection.execute(
                """INSERT INTO optimization_package_outcomes (
                       run_id, created_at, final_package_sha256,
                       curator_work_sha256, report_json, report_sha256
                   ) VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    legacy_row["run_id"],
                    legacy_row["created_at"],
                    legacy_row["final_package_sha256"],
                    "a" * 64,
                    legacy_row["report_json"],
                    legacy_row["report_sha256"],
                ),
            )
            self.assertEqual(
                2,
                connection.execute(
                    "SELECT COUNT(*) FROM optimization_package_outcomes"
                ).fetchone()[0],
            )

    def test_residual_invalid_field_is_removed_and_requires_review(self) -> None:
        models = SeededFixtureModels()

        def leave_unsupported_phone(prompt: dict) -> dict:
            result = models.verify(prompt)
            if prompt["candidateIdentity"]["program"] == "Rapid Re-Housing":
                result["fieldDecisions"]["phone"] = {
                    "action": "mark-conflicting",
                    "reason": "Fixture returns an invalid one-value conflict",
                    "alternatives": [
                        {"value": "480-555-0199", "evidenceIds": ["1"]}
                    ],
                }
            return result

        pipeline = self.pipeline(
            models,
            "model-fixture-residual-field-remediation",
            verify=leave_unsupported_phone,
        )
        result = pipeline.run()
        self.assertTrue(result.quality_gate_passed)
        self.assertEqual(6, result.passed_count)
        self.assertEqual(1, result.needs_review_count)
        self.assertEqual(0, result.failed_count)
        with self.store.connect() as connection:
            row = connection.execute(
                """SELECT verification.verified_dossier_json, verification.findings_json
                   FROM optimization_verifications AS verification
                   JOIN optimization_candidate_dossiers AS dossier
                     ON dossier.id = verification.dossier_id
                   JOIN optimization_evidence_packets AS packet
                     ON packet.id = dossier.packet_id
                   WHERE dossier.run_id = ?
                     AND packet.identity_key = 'a new leaf::rapid re housing'""",
                (result.run_id,),
            ).fetchone()
        verified = json.loads(row["verified_dossier_json"])
        findings = json.loads(row["findings_json"])
        self.assertEqual("supported", verified["fields"]["phone"]["status"])
        self.assertEqual([], findings["finalDeterministicFindings"])
        self.assertEqual(
            "invalid-verifier-decision",
            findings["verifierDecisionFindings"][0]["code"],
        )

    def test_verifier_failure_resumes_without_repeating_extraction(self) -> None:
        models = SeededFixtureModels()
        failures = 0

        def fail_first_verification(prompt: dict) -> dict:
            nonlocal failures
            if failures == 0:
                failures += 1
                raise RuntimeError("fixture verifier failure")
            return models.verify(prompt)

        with self.assertRaisesRegex(OptimizationModelError, "fixture verifier failure"):
            self.pipeline(
                models,
                "model-fixture-resume",
                verify=fail_first_verification,
            ).run()
        self.assertEqual(1, len(models.extract_prompts))

        result = self.pipeline(models, "model-fixture-resume").run()
        self.assertTrue(result.quality_gate_passed)
        self.assertEqual(7, len(models.extract_prompts))
        with self.store.connect() as connection:
            first_packet_attempts = connection.execute(
                """SELECT operation, status FROM optimization_model_attempts
                   WHERE run_id = ? ORDER BY id LIMIT 3""",
                (result.run_id,),
            ).fetchall()
        self.assertEqual(
            [("extract", "completed"), ("verify", "failed"), ("verify", "completed")],
            [(row["operation"], row["status"]) for row in first_packet_attempts],
        )

    def test_extractor_failure_is_retained_and_retried(self) -> None:
        models = SeededFixtureModels()
        failures = 0

        def fail_first_extraction(prompt: dict) -> dict:
            nonlocal failures
            if failures == 0:
                failures += 1
                raise RuntimeError("fixture extractor failure")
            return models.extract(prompt)

        with self.assertRaisesRegex(OptimizationModelError, "fixture extractor failure"):
            self.pipeline(
                models,
                "model-fixture-extractor-resume",
                extract=fail_first_extraction,
            ).run()
        result = self.pipeline(models, "model-fixture-extractor-resume").run()
        self.assertTrue(result.quality_gate_passed)
        with self.store.connect() as connection:
            attempts = connection.execute(
                """SELECT operation, status FROM optimization_model_attempts
                   WHERE run_id = ? ORDER BY id LIMIT 3""",
                (result.run_id,),
            ).fetchall()
        self.assertEqual(
            [("extract", "failed"), ("extract", "completed"), ("verify", "completed")],
            [(row["operation"], row["status"]) for row in attempts],
        )

    def test_extractor_may_return_sparse_source_bindings_and_scout_restores_envelopes(
        self,
    ) -> None:
        models = SeededFixtureModels()

        def sparse_extract(prompt: dict) -> dict:
            dossier = models.extract(prompt)
            dossier["sources"] = [
                {
                    key: deepcopy(source[key])
                    for key in ("id", "supports", "contradicts")
                }
                for source in dossier["sources"]
            ]
            return dossier

        result = self.pipeline(
            models,
            "model-fixture-sparse-source-bindings",
            extract=sparse_extract,
        ).run()
        self.assertTrue(result.quality_gate_passed)

        with self.store.connect() as connection:
            dossiers = connection.execute(
                """SELECT dossier_json FROM optimization_candidate_dossiers
                   WHERE run_id = ? ORDER BY packet_id""",
                (result.run_id,),
            ).fetchall()
        for row in dossiers:
            for source in json.loads(row["dossier_json"])["sources"]:
                self.assertTrue(source["url"].startswith("https://"))
                self.assertIn("extract", source)
                self.assertIn("authority", source)
                self.assertIn("pageIdentityKey", source)

    def test_failed_model_output_and_usage_are_retained_for_diagnosis(self) -> None:
        models = SeededFixtureModels()

        def fail_with_raw_output(_prompt: dict) -> dict:
            raise OptimizationModelError(
                "fixture parse failure",
                raw_output="unfinished fixture output",
                usage={"completion_tokens": 99, "metered": False},
            )

        with self.assertRaisesRegex(OptimizationModelError, "fixture parse failure"):
            self.pipeline(
                models,
                "model-fixture-raw-failure",
                extract=fail_with_raw_output,
            ).run()

        with self.store.connect() as connection:
            attempt = connection.execute(
                """SELECT status, raw_output, usage_json, error
                   FROM optimization_model_attempts
                   WHERE operation = 'extract' ORDER BY id DESC LIMIT 1"""
            ).fetchone()
        self.assertEqual("failed", attempt["status"])
        self.assertEqual("unfinished fixture output", attempt["raw_output"])
        self.assertEqual(99, json.loads(attempt["usage_json"])["completion_tokens"])
        self.assertEqual("fixture parse failure", attempt["error"])

    def test_gap_audit_resume_does_not_repeat_model_work(self) -> None:
        models = SeededFixtureModels()
        interrupted = False

        def stop_after_gap_audit(event: dict) -> None:
            nonlocal interrupted
            if event["phase"] == "gap-audit" and not interrupted:
                interrupted = True
                raise RuntimeError("fixture gap audit interruption")

        with self.assertRaisesRegex(OptimizationModelError, "gap audit interruption"):
            self.pipeline(
                models,
                "model-fixture-gap-resume",
                progress=stop_after_gap_audit,
            ).run()
        self.assertEqual(7, len(models.extract_prompts))
        self.assertEqual(7, len(models.verify_prompts))

        result = self.pipeline(models, "model-fixture-gap-resume").run()
        self.assertEqual(1, result.gap_count)
        self.assertEqual(7, len(models.extract_prompts))
        self.assertEqual(7, len(models.verify_prompts))


if __name__ == "__main__":
    unittest.main()
