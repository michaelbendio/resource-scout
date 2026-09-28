"""Compatibility boundaries between the merged writing and prepared workflows."""
from copy import deepcopy
import unittest

from resource_research_agent.curation_result_repair import is_explicit_placeholder
from resource_research_agent.preparation_contract import prepared_assignment
from resource_research_agent.resource_writing import load_writing_guidance
from resource_research_agent.scout_curation_runner import response_schema, worker_prompt
from resource_research_agent.scout_review_readiness import validate_ready_seed
from resource_research_agent.scout_curation import ScoutCurationError


class MergedCurationContractTests(unittest.TestCase):
    def assignment(self):
        return {
            'writingGuidance': load_writing_guidance(),
            'curationContractVersion': 'codex-curation-v3-writing',
            'instructions': ['Follow the sealed evidence.'],
            'outputContract': {'scoutCurationResultSchemaVersion': 2,
                'resources': [{'informationSections': {}, 'writingEvidence': {}, 'openQuestions': []}]},
        }

    def test_structured_worker_schema_and_prompt_follow_sealed_sections(self):
        assignment = self.assignment()
        schema = response_schema(assignment)
        resource = schema['properties']['resources']['items']['properties']
        self.assertEqual(schema['properties']['scoutCurationResultSchemaVersion']['enum'], [2])
        self.assertEqual(set(resource['informationSections']['properties']),
                         {s['key'] for s in assignment['writingGuidance']['sections']})
        self.assertNotIn('informationText', resource)
        self.assertEqual(resource['verifiedOn'], {'type': 'null'})
        prompt = worker_prompt(assignment, 'Source checks required')
        self.assertIn('Follow the sealed evidence.', prompt)
        self.assertNotIn('these four bold', prompt)
        self.assertIn('verifiedOn must be null', prompt)

    def test_prepared_conversion_preserves_input_and_its_schema_one_boundary(self):
        original = self.assignment()
        before = deepcopy(original)
        prepared = prepared_assignment(original)
        self.assertEqual(original, before)
        self.assertEqual(prepared['outputContract']['scoutCurationResultSchemaVersion'], 1)
        self.assertNotIn('writingGuidance', prepared)
        resource = prepared['outputContract']['resources'][0]
        self.assertIn('informationText', resource)
        self.assertNotIn('informationSections', resource)
        self.assertNotIn('writingEvidence', resource)
        self.assertEqual(response_schema(prepared)['properties']['scoutCurationResultSchemaVersion']['enum'], [1])

    def test_legacy_response_contract_stays_schema_one(self):
        schema = response_schema()
        self.assertEqual(schema['properties']['scoutCurationResultSchemaVersion']['enum'], [1])
        self.assertIn('informationText', schema['properties']['resources']['items']['properties'])

    def test_structured_placeholder_cannot_hide_substantive_information(self):
        row = {'name': 'Duplicate placeholder', 'description': 'Duplicate placeholder',
               'informationSections': {'one': 'Placeholder', 'two': 'Placeholder remove'},
               'writingEvidence': {'sources': []}}
        self.assertTrue(is_explicit_placeholder(row))
        row['informationSections']['two'] = 'Bring proof of county residence.'
        self.assertFalse(is_explicit_placeholder(row))
        row['informationSections']['two'] = 'Placeholder'
        row['writingEvidence']['sources'] = [{'url': 'https://example.org/eligibility'}]
        self.assertFalse(is_explicit_placeholder(row))

    def test_readiness_checks_every_section_of_the_assigned_contract(self):
        headings = tuple(s['heading'] for s in load_writing_guidance()['sections'])
        seed = {'categories': [{'id': 'food', 'filters': ['Pantries']}], 'forGroups': [],
                'resources': [{'id': 'r', 'categories': ['food'], 'categoryFilters': {'food': ['Pantries']},
                               'informationText': '\n\n'.join(f'**{h}**\n\nSupported detail.' for h in headings)}]}
        self.assertEqual(validate_ready_seed(seed, information_headings=headings)['resources'], 1)
        seed['resources'][0]['informationText'] = seed['resources'][0]['informationText'].rsplit('Supported detail.', 1)[0]
        with self.assertRaisesRegex(ScoutCurationError, 'empty section'):
            validate_ready_seed(seed, information_headings=headings)
        with self.assertRaisesRegex(ScoutCurationError, 'assigned standalone'):
            validate_ready_seed(seed)

    def test_package_bytes_do_not_depend_on_export_clock(self):
        import io
        import zipfile
        from unittest.mock import patch
        from resource_research_agent.improvement_packages import write_package
        data = {'name': 'Same package'}
        assets = {'pdfs/source.pdf': b'Preserved original bytes'}
        with patch('zipfile.time.localtime', return_value=(2026, 9, 28, 12, 0, 0, 0, 0, 0)):
            first = write_package(data, assets)
        with patch('zipfile.time.localtime', return_value=(2026, 9, 29, 12, 0, 0, 0, 0, 0)):
            second = write_package(data, assets)
        self.assertEqual(first, second)
        with zipfile.ZipFile(io.BytesIO(first)) as archive:
            self.assertEqual(archive.read('pdfs/source.pdf'), assets['pdfs/source.pdf'])
            self.assertEqual(archive.getinfo('tso-resources.json').date_time, (1980, 1, 1, 0, 0, 0))
