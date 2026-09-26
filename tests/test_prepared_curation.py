import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tests import test_scout_curation as legacy
from resource_research_agent.preparation_contract import (POLICY_VERSION, INFORMATION_HEADINGS,
    assemble_information, prepared_assignment)
from resource_research_agent.scout_curation import (prepare_scout_curation_job,
    next_scout_curation_assignment, save_scout_curation_result, build_scout_review_seed, ScoutCurationError, _completed_resources)
from resource_research_agent.scout_curation_runner import response_schema, worker_prompt, compact_assignment, run


class PreparedCurationTests(unittest.TestCase):
    def setUp(self):
        self.fixture = legacy.ScoutCurationTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.fixture.completed_run('food', 'Food', ['codex', 'deepseek'])
        self.fixture.completed_run('housing', 'Housing', ['codex', 'deepseek'])

    def result(self, assignment):
        result = self.fixture.result_for(assignment, resource_id='draft-' + assignment['category']['id'])
        result['resources'][0].update(
            informationText=assemble_information({h: 'Supported details for this section.' for h in INFORMATION_HEADINGS}),
            verifiedOn=None, email='help@example.org', researchedAt='2026-09-25', state='usable', resolutionReason='',
            sources=[dict(url='https://example.org/help', title='Official intake')],
            taxonomySuggestions=[dict(kind='type', label='Food benefits', definition='Help applying for benefits', evidence='SNAP application assistance')])
        return result

    def test_new_mode_preserves_legacy_seals_and_evidence_round_trip(self):
        old = prepare_scout_curation_job(self.fixture.store, self.fixture.import_id)
        sealed = json.dumps(old, sort_keys=True)
        new = prepare_scout_curation_job(self.fixture.store, self.fixture.import_id, prepared=True)
        self.assertNotEqual(old['id'], new['id'])
        for _ in range(2):
            assignment = next_scout_curation_assignment(self.fixture.store, new['id'])
            self.assertEqual(POLICY_VERSION, assignment['preparationPolicyVersion'])
            view = compact_assignment(assignment)
            prompt = worker_prompt(view, '')
            self.assertIn('five standalone bold', prompt)
            self.assertNotIn('smallest high-confidence', prompt)
            self.assertNotIn("verifiedOn is today's date", prompt)
            schema = response_schema(assignment)['properties']['resources']['items']['properties']
            self.assertEqual({'type': 'null'}, schema['verifiedOn'])
            self.assertIn('taxonomySuggestions', schema)
            result = self.result(assignment)
            save_scout_curation_result(self.fixture.store, new['id'], assignment['category']['id'], result)
        seed = build_scout_review_seed(self.fixture.store, new['id'])
        self.assertFalse(seed['importable'])
        self.assertEqual('scout-preparation-drafts', seed['artifactType'])
        for resource in seed['resources']:
            self.assertEqual('2026-09-25', resource['researchedAt'])
            self.assertEqual('help@example.org', resource['email'])
            self.assertTrue(resource['sources'])
            self.assertTrue(resource['taxonomySuggestions'])
            self.assertTrue(resource['candidateIds'])
            self.assertIsNone(resource['verifiedOn'])
        self.assertEqual(sealed, json.dumps(self.fixture.store.get_scout_curation_job(old['id']), sort_keys=True))

    def test_no_model_production_identity_or_office_verification(self):
        job = prepare_scout_curation_job(self.fixture.store, self.fixture.import_id, prepared=True)
        assignment = next_scout_curation_assignment(self.fixture.store, job['id'])
        for mutation, message in (({'verifiedOn': '2026-09-25'}, 'verification date'),
                                  ({'id': 'sr_invented'}, 'registry IDs'),
                                  ({'sources': []}, 'source pages')):
            result = self.result(assignment); result['resources'][0].update(mutation)
            with self.assertRaisesRegex(ScoutCurationError, message):
                save_scout_curation_result(self.fixture.store, job['id'], assignment['category']['id'], result)

    def test_cross_category_extension_preserves_sources_and_resolution_flags(self):
        first = dict(id='draft', categories=['food'], categoryFilters={}, forGroups=[], candidateIds=['1'],
            sources=[dict(url='https://example.org/food', title='Food')], taxonomySuggestions=[dict(label='Food applications')],
            state='needs-resolution', resolutionReason='Intake conflict needs review')
        second = dict(first, categories=['housing'], candidateIds=['2'],
            sources=[dict(url='https://example.org/housing', title='Housing')], taxonomySuggestions=[], state='usable', resolutionReason='')
        job = dict(categories=[dict(assignment={'preparationPolicyVersion': POLICY_VERSION}, result=dict(resources=[r])) for r in (first, second)])
        resource, = _completed_resources(job)
        self.assertEqual(2, len(resource['sources']))
        self.assertEqual(first['taxonomySuggestions'], resource['taxonomySuggestions'])
        self.assertEqual('needs-resolution', resource['state'])
        self.assertEqual(first['resolutionReason'], resource['resolutionReason'])

    def test_conversion_does_not_mutate_sealed_original(self):
        job = prepare_scout_curation_job(self.fixture.store, self.fixture.import_id)
        assignment = next_scout_curation_assignment(self.fixture.store, job['id'])
        old = json.dumps(assignment, sort_keys=True)
        converted = prepared_assignment(assignment)
        self.assertNotIn('assignmentSha256', converted)
        self.assertEqual(old, json.dumps(assignment, sort_keys=True))
        self.assertNotIn('sources', response_schema()['properties']['resources']['items']['properties'])

    def test_all_research_keeps_both_collections_and_distinct_checkpoint(self):
        later = self.fixture.completed_run('food', 'Food', ['codex', 'deepseek', 'other'])
        default = prepare_scout_curation_job(self.fixture.store, self.fixture.import_id, prepared=True)
        combined = prepare_scout_curation_job(self.fixture.store, self.fixture.import_id,
                                            prepared=True, all_research_runs=True)
        self.assertNotEqual(default['id'], combined['id'])
        food = next(c for c in combined['categories'] if c['categoryId'] == 'food')
        original = next(c for c in default['categories'] if c['categoryId'] == 'food')
        self.assertGreater(food['candidateCount'], original['candidateCount'])
        self.assertEqual(3, len(food['assignment']['category']['researchRunIds']))
        self.assertEqual(6, food['candidateCount'])
        self.assertEqual(6, len(food['assignment']['sourceResponses']))
        self.assertIn(later, food['assignment']['category']['researchRunIds'])
        self.assertEqual(combined['id'], prepare_scout_curation_job(
            self.fixture.store, self.fixture.import_id, prepared=True, all_research_runs=True)['id'])
        with self.assertRaises(ScoutCurationError):
            prepare_scout_curation_job(self.fixture.store, self.fixture.import_id, all_research_runs=True)

    def test_runner_emits_review_drafts_and_resumes_without_calls(self):
        import contextlib
        import io
        args = SimpleNamespace(database=str(self.fixture.store.path), output=str(self.fixture.root/'prepared'),
            import_id=self.fixture.import_id, source_audit=None, prepared=True, max_categories=None,
            batch_candidates=0, batch_chars=60000, compact_prior_index=False,
            codex_binary='unused', model='test', effort='high', timeout_seconds=60)
        def worker(directory, **kwargs):
            assignment = json.loads((directory/'assignment.json').read_text())
            (directory/'result.json').write_text(json.dumps(self.result(assignment)))
        with contextlib.redirect_stdout(io.StringIO()), patch('resource_research_agent.scout_curation_runner.execute_worker', side_effect=worker) as launch:
            first = run(args)
            draft = Path(first['draftFile']).read_bytes()
            second = run(args)
            self.assertEqual(2, launch.call_count)
        self.assertEqual(first, second)
        self.assertEqual('Ready for Codex review', first['handoff'])
        self.assertEqual(draft, Path(second['draftFile']).read_bytes())
        self.assertNotIn('reviewFile', first)
        Path(first['draftFile']).write_text('changed')
        with self.assertRaisesRegex(ValueError, 'artifact changed'):
            run(args)


if __name__ == '__main__': unittest.main()
