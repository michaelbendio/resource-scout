from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "dsh-plugins" / "web-search-ddgs" / "search.py"
SPEC = importlib.util.spec_from_file_location("resource_scout_ddgs_search", HELPER)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class DDGSSearchNormalizationTests(unittest.TestCase):
    def test_explicit_no_results_condition_is_an_empty_success(self) -> None:
        class EmptyDDGS:
            def __init__(self, **_kwargs):
                pass

            def text(self, *_args, **_kwargs):
                raise RuntimeError("No results found.")

        self.assertEqual([], MODULE.search_rows("empty query", 8, EmptyDDGS))

    def test_other_provider_errors_remain_failures(self) -> None:
        class BrokenDDGS:
            def __init__(self, **_kwargs):
                pass

            def text(self, *_args, **_kwargs):
                raise RuntimeError("network unavailable")

        with self.assertRaisesRegex(RuntimeError, "network unavailable"):
            MODULE.search_rows("broken query", 8, BrokenDDGS)

    def test_normalizes_deduplicates_and_limits_results(self) -> None:
        result = MODULE.normalize_results(
            [
                {"href": "HTTPS://Example.org:443/help#hours", "title": " Help ", "body": " Details "},
                {"url": "https://example.org/help", "title": "Duplicate"},
                {"href": "https://second.example/path", "title": "Second", "date": "2026-08-01"},
                {"href": "https://third.example/path", "title": "Over limit"},
            ],
            2,
        )

        self.assertTrue(result["truncated"])
        self.assertEqual(2, len(result["sources"]))
        self.assertEqual("https://example.org/help", result["sources"][0]["url"])
        self.assertEqual("Help", result["sources"][0]["title"])
        self.assertEqual("Details", result["sources"][0]["snippet"])
        self.assertEqual("2026-08-01", result["sources"][1]["publishedAt"])

    def test_rejects_unsupported_malformed_and_credential_urls(self) -> None:
        result = MODULE.normalize_results(
            [
                {"href": "javascript:alert(1)"},
                {"href": "https://user:secret@example.org/private"},
                {"href": "http://[invalid"},
                None,
                {"href": "http://valid.example"},
            ],
            8,
        )

        self.assertTrue(result["truncated"])
        self.assertEqual([{"url": "http://valid.example/"}], result["sources"])

    def test_empty_results_are_valid(self) -> None:
        self.assertEqual({"sources": [], "truncated": False}, MODULE.normalize_results([], 8))


if __name__ == "__main__":
    unittest.main()
