from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from resource_research_agent.resource_writing import (
    DEFAULT_GUIDANCE_PATH, ResourceWritingError, compose_information,
    load_writing_guidance, normalize_written_resource,
)


class ResourceWritingTests(unittest.TestCase):
    def setUp(self):
        self.bundle = load_writing_guidance()
        self.sections = {s['key']: f"Useful {s['key']} text." for s in self.bundle['sections']}
        self.resource = {
            'id': 'example', 'name': 'Example', 'description': 'Local help.',
            'phone': '480-555-0123', 'address': 'Example address',
            'categories': ['employment'], 'forGroups': ['Veterans'],
            'categoryFilters': {}, 'pdfs': [{'name': 'Guide', 'path': 'assets/guide.pdf'}],
            'candidateIds': ['c1'], 'informationSections': self.sections,
            'writingEvidence': {'candidateIds': ['c1'], 'sources': []},
        }

    def test_bundle_failures_and_hash_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copytree(DEFAULT_GUIDANCE_PATH.parent, root, dirs_exist_ok=True)
            path = root / 'default.json'
            original = path.read_text()
            before = load_writing_guidance(path)
            instructions = root / 'plain_language.md'
            instructions.write_text(instructions.read_text() + '\nNew instruction.\n')
            after = load_writing_guidance(path)
            self.assertEqual(before['version'], after['version'])
            self.assertNotEqual(before['sha256'], after['sha256'])
            for change in (
                {'schemaVersion': 99}, {'schemaVersion': True}, {'sections': []},
                {'sections': [before['sections'][0], before['sections'][0]]},
                {'instructionsFile': '../outside.md'},
                {'sections': [{'key': 'a', 'heading': '**bad**'}]},
            ):
                with self.subTest(change=change):
                    path.write_text(json.dumps({**json.loads(original), **change}))
                    with self.assertRaises(ResourceWritingError):
                        load_writing_guidance(path)
            path.write_text(original)
            instructions.unlink()
            with self.assertRaises(ResourceWritingError):
                load_writing_guidance(path)
            path.write_text('{malformed')
            with self.assertRaises(ResourceWritingError):
                load_writing_guidance(path)

    def test_exact_composition_and_unicode(self):
        self.sections['howToBestConnect'] = 'Call José’s office · Mesa.\r\n\r\n- Email: help@example.org\r\n- https://example.org/apply'
        result = compose_information(self.sections, self.bundle)
        expected = '\n\n'.join(
            '**' + s['heading'] + '**\n' + self.sections[s['key']].replace('\r\n', '\n')
            for s in self.bundle['sections']
        )
        self.assertEqual(expected, result)
        self.assertIn('José’s', result)
        self.assertEqual(5, sum(line.startswith('**') for line in result.splitlines()))

    def test_bad_sections_and_heading_injection(self):
        variants = [None, [], {}, {**self.sections, 'extra': 'text'}]
        for bad in ('', '  ', None, [], '**Scout Findings**\nold text',
                    '### Programs and Services\nrepeated', 'Services Provided: repeated',
                    '**Important Information to Know**: repeated'):
            variants.append({**self.sections, 'access': bad})
        for sections in variants:
            with self.subTest(sections=sections), self.assertRaises(ResourceWritingError):
                compose_information(sections, self.bundle)
        self.sections['access'] = 'Ask which services provided at this location require appointments.'
        compose_information(self.sections, self.bundle)

    def test_forged_guidance_is_rejected(self):
        modified = deepcopy(self.bundle)
        modified['instructionsText'] += 'unsealed modification'
        with self.assertRaisesRegex(ResourceWritingError, 'hash'):
            compose_information(self.sections, modified)

    def test_normalization_preserves_fields_and_separates_evidence(self):
        source = deepcopy(self.resource)
        self.resource['writingEvidence']['sources'] = [{
            'url': 'https://example.org/help', 'accessedOn': '2026-09-05',
            'excerpt': 'Application help is available.',
        }]
        normalized, metadata = normalize_written_resource(self.resource, self.bundle)
        for key in ('id', 'phone', 'address', 'categories', 'forGroups', 'pdfs', 'candidateIds'):
            self.assertEqual(source[key], normalized[key])
        self.assertNotIn('writingEvidence', normalized)
        self.assertNotIn('informationSections', normalized)
        self.assertEqual(self.resource['writingEvidence'], metadata['evidence'])
        self.assertEqual(self.sections, metadata['informationSections'])
        self.assertIsNone(normalized['verifiedOn'])
        self.assertNotIn('informationText', self.resource)

    def test_invalid_fields_and_evidence(self):
        for changes in (
            {'description': ''}, {'description': []}, {'informationText': ''},
            {'verifiedOn': '2026-09-05'}, {'email': 'lost@example.org'},
            {'writingEvidence': None},
            {'writingEvidence': {'candidateIds': [], 'sources': []}},
            {'writingEvidence': {'candidateIds': ['unknown'], 'sources': []}},
            {'writingEvidence': {'candidateIds': ['c1'], 'sources': [{'url': 'bad'}]}},
            {'writingEvidence': {'candidateIds': ['c1'], 'sources': [{
                'url': 'file:///private', 'accessedOn': '2026-09-05', 'excerpt': 'text'}]}},
            {'writingEvidence': {'candidateIds': ['c1'], 'sources': [{
                'url': 'https://example.org', 'accessedOn': 'not-a-date', 'excerpt': 'text'}]}},
        ):
            with self.subTest(changes=changes), self.assertRaises(ResourceWritingError):
                normalize_written_resource({**self.resource, **changes}, self.bundle)
