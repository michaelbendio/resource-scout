from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path


TEMPLATE = (
    Path(__file__).resolve().parents[1]
    / "resource_research_agent"
    / "scout_review_template.html"
)


class ScoutReviewTaxonomyUITests(unittest.TestCase):
    @staticmethod
    def _function(source: str, name: str) -> str:
        start = source.index(f"function {name}(")
        brace = source.index("{", start)
        depth = 0
        for index in range(brace, len(source)):
            if source[index] == "{":
                depth += 1
            elif source[index] == "}":
                depth -= 1
                if depth == 0:
                    return source[start:index + 1]
        raise AssertionError(f"Could not extract {name}")

    def test_offers_need_and_group_browsing(self) -> None:
        source = TEMPLATE.read_text(encoding="utf-8")
        self.assertIn('label:"Browse by need"', source)
        self.assertIn('label:"Find resources for"', source)
        self.assertIn("Choose one or more groups", source)
        self.assertIn("organized below by the needs they address", source)
        self.assertIn("openCategoryFromGroupBrowse", source)
        self.assertIn('typeof container.appendChild === "function"', source)

    def test_types_or_groups_or_and_dimensions_and(self) -> None:
        source = TEMPLATE.read_text(encoding="utf-8")
        functions = "\n".join(
            self._function(source, name)
            for name in (
                "canonicalizeTaxonomyLabel",
                "normalizeTaxonomyLabels",
                "normalizeCategoryFilters",
                "makeCategorySpecificFilterKey",
                "makeForGroupFilterKey",
                "getResourceCategoryFilterKeys",
                "getResourceForGroupFilterKeys",
                "selectedCategoryFilterDimensions",
                "resourceMatchesSelectedCategoryFilters",
            )
        )
        cases = [
            {
                "name": "type and group both match",
                "selected": ["filter:ged", "for:veterans"],
                "expected": True,
            },
            {
                "name": "type matches but group does not",
                "selected": ["filter:ged", "for:spanish"],
                "expected": False,
            },
            {
                "name": "types are ORed",
                "selected": ["filter:ged", "filter:online education", "for:veterans"],
                "expected": True,
            },
            {
                "name": "groups are ORed",
                "selected": ["filter:ged", "for:spanish", "for:veterans"],
                "expected": True,
            },
        ]
        script = f"""
{functions}
const resource = {{
  categoryFilters: {{ education: ["GED"] }},
  forGroups: ["Veterans"]
}};
const cases = {json.dumps(cases)};
for (const item of cases) {{
  const actual = resourceMatchesSelectedCategoryFilters(
    resource, "education", item.selected
  );
  if (actual !== item.expected) {{
    throw new Error(`${{item.name}}: expected ${{item.expected}}, received ${{actual}}`);
  }}
}}
"""
        completed = subprocess.run(
            ["node", "-e", script],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(0, completed.returncode, completed.stderr)


if __name__ == "__main__":
    unittest.main()
