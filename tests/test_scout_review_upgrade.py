from __future__ import annotations

import json
import re
import unittest

from resource_research_agent import __version__, __build__
from resource_research_agent.scout_curation import ScoutCurationError
from resource_research_agent.scout_review import upgrade_scout_review_document


class ScoutReviewUpgradeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.seed = json.dumps({
            'resources': [{'id': 'original-id', 'name': 'Reviewed name',
                           'informationText': 'Exact original text', 'categories': ['old-category'],
                           'pdfs': [{'id': 'pdf-1', 'path': 'attachment.pdf'}]}],
            'categories': [{'id': 'old-category', 'label': 'Original category'}],
            'forGroups': ['Original group'], 'packageVersion': 17,
            'changes': [{'description': 'Reviewer correction'}],
            'deletions': [{'id': 'deleted-id'}],
        }, ensure_ascii=False, indent=3)
        self.old = f'''<!DOCTYPE html><html><head>
<meta name="tso-storage-id" content="scout-review-mesa">
<meta name="tso-office-name" content="AutoMesa">
<meta name="scout-review-location-name" content="Mesa">
<meta name="scout-review-artifact-id" content="original-artifact-id">
<meta name="scout-review-taxonomy-study-id" content="20">
<title>AutoMesa TSO Resources</title></head><body>
<script id="seed-data" type="application/json">{self.seed}</script>
<script id="app-release-data" type="application/json">{{"version":"0.47.0"}}</script>
<p>obsolete interface</p></body></html>'''

    def test_upgrade_preserves_exact_seed_identity_and_provenance(self) -> None:
        updated = upgrade_scout_review_document(self.old).decode()
        seed_block = f'<script id="seed-data" type="application/json">{self.seed}</script>'
        self.assertIn(seed_block, updated)
        for tag in re.findall(r'<meta[^>]+>', self.old):
            self.assertIn(tag, updated)
        self.assertIn('<title>AutoMesa TSO Resources</title>', updated)
        self.assertIn('function toggleCurrentResourceCurated()', updated)
        self.assertIn('function requireResourceEditorForGroupReview(draft)', updated)
        self.assertNotIn('obsolete interface', updated)
        release = json.loads(re.search(
            r'<script id="app-release-data" type="application/json">([\s\S]*?)</script>', updated
        )[1])
        self.assertEqual((release['version'], release['build']), (__version__, __build__))
        self.assertEqual(upgrade_scout_review_document(updated).decode(), updated)

    def test_refuses_ambiguous_or_unidentified_input(self) -> None:
        for old in (
            self.old.replace('content="original-artifact-id"', 'content=""'),
            self.old.replace('</head>', '<meta name="tso-storage-id" content="other"></head>'),
            self.old.replace('</head>', '<meta name="unknown-provenance" content="keep"></head>'),
            self.old.replace('"resources": [', '"wrong-key": ['),
            self.old.replace('</body>', f'<script id="seed-data" type="application/json">{self.seed}</script></body>'),
        ):
            with self.subTest(old=old[:80]), self.assertRaises(ScoutCurationError):
                upgrade_scout_review_document(old)
