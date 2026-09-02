from __future__ import annotations

import hashlib
import json
import re
import unicodedata
import unittest
from collections import Counter
from pathlib import Path


FIXTURES = Path(__file__).parent / "fixtures" / "manual_discovery"


def first_json_object(text: str) -> tuple[dict[str, object], str]:
    stripped = text.lstrip()
    value, end = json.JSONDecoder().raw_decode(stripped)
    if not isinstance(value, dict):
        raise AssertionError("fixture must start with a JSON object")
    return value, stripped[end:]


def normalized_identity(value: dict[str, object]) -> tuple[str, str]:
    def normalize(text: object) -> str:
        without_parenthetical = re.sub(r"\([^)]*\)", "", str(text or ""))
        ascii_text = (
            unicodedata.normalize("NFKD", without_parenthetical)
            .encode("ascii", "ignore")
            .decode("ascii")
            .casefold()
            .replace("&", " and ")
        )
        ascii_text = re.sub(
            r"\b(incorporated|inc|llc|pllc|corp|corporation)\b", "", ascii_text
        )
        return re.sub(r"[^a-z0-9]+", " ", ascii_text).strip()

    return normalize(value.get("organization")), normalize(value.get("program"))


class ManualDiscoveryFixtureTests(unittest.TestCase):
    def test_reduced_pilot_accounting_is_stable(self) -> None:
        expected = json.loads((FIXTURES / "expected.json").read_text(encoding="utf-8"))
        leads: list[dict[str, object]] = []
        trailing_sources: list[str] = []
        for source in expected["sourceOrder"]:
            payload = (FIXTURES / expected["files"][source]).read_bytes()
            self.assertEqual(expected["sha256"][source], hashlib.sha256(payload).hexdigest())
            text = payload.decode("utf-8")
            value, trailing = first_json_object(text)
            source_leads = value.get("leads")
            self.assertIsInstance(source_leads, list)
            leads.extend(source_leads)
            if trailing.strip():
                trailing_sources.append(source)

        self.assertEqual(expected["submittedRows"], len(leads))
        self.assertEqual(
            expected["declaredLeadTypes"],
            dict(Counter(str(item["leadType"]) for item in leads)),
        )
        self.assertEqual(
            expected["blankWebsites"],
            sum(not str(item["website"]).strip() for item in leads),
        )
        self.assertEqual(
            expected["markdownWebsites"],
            sum(bool(re.match(r"^\[[^]]+\]\(https?://", str(item["website"]))) for item in leads),
        )
        self.assertEqual(expected["sourcesWithTrailingText"], trailing_sources)
        self.assertEqual(
            expected["exactNormalizedIdentityGroups"],
            len({normalized_identity(item) for item in leads}),
        )

    def test_every_fixture_row_preserves_the_discovery_contract(self) -> None:
        expected = json.loads((FIXTURES / "expected.json").read_text(encoding="utf-8"))
        required = {
            "organization",
            "program",
            "website",
            "leadType",
            "locationOrServiceArea",
            "whyRelevant",
            "uncertainty",
        }
        for source, filename in expected["files"].items():
            value, _trailing = first_json_object(
                (FIXTURES / filename).read_text(encoding="utf-8")
            )
            for position, lead in enumerate(value["leads"], start=1):
                with self.subTest(source=source, position=position):
                    self.assertEqual(required, set(lead))
                    self.assertTrue(all(isinstance(lead[key], str) for key in required))
                    self.assertTrue(lead["organization"].strip())
                    self.assertIn(
                        lead["leadType"],
                        {"program", "provider-organization", "access-point", "routing-source", "directory"},
                    )


if __name__ == "__main__":
    unittest.main()
