from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from resource_research_agent import office_pipeline as pipeline
from resource_research_agent.prepared_pipeline import (
    content_view, sha, validate_submission, export_reviewed_submission, prepared_review_prompt)
from resource_research_agent.resource_identity import new_registry
from resource_research_agent.scout_review_handoff import curation_fingerprint
from resource_research_agent.scout_progress import prepared_delivery_context
from tests.test_prepared_resources import fixture, seal


class PreparedPipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'review').mkdir()
        (self.root / 'curation').mkdir()
        self.config = dict(runDirectory=str(self.root), officeName='Welfare Square', officeSlug='welfare-square',
            repository=str(self.root), database=str(self.root / 'db'), importId=1, expectedCategories=1,
            authorization='Complete fresh research, curation, review and prepared work product',
            serviceArea='Salt Lake County', sourceNamespace='fresh-test', preparedMode=True,
            preparedReviewAuthorized=True, automaticReview=True, curationEffort='high', reviewEffort='xhigh',
            registryPath=str(self.root / 'registry.json'), sourceSeedPath=str(self.root / 'seed.json'),
            preparedOutputDirectory=str(self.root / 'delivery'), shortDeliveryDate=True,
            codexBinary='codex', pythonBinary='python3', model='gpt-5.5', maximumReviewSessions=2,
            reviewTimeoutSeconds=5400)
        self.job = dict(id=1, status='completed', categories=[dict(categoryId='housing', status='completed',
            assignmentSha256='a', resultSha256='b', assignment=dict(candidates=[dict(id='c1'), dict(id='c2')]))])
        self.bundle = fixture()
        self.bundle['sourceNamespace'] = 'fresh-test'
        self.bundle['payload']['office'] = dict(slug='welfare-square', name='Welfare Square')
        self.bundle['payload']['scope']['completeOffice'] = True
        self.bundle['candidateReview'] = [dict(categoryId='housing', candidateId='c1', decision='retain',
            reason='Reviewed direct housing intake', resourceIds=['old-a']),
            dict(categoryId='housing', candidateId='c2', decision='exclude', reason='No direct intake', resourceIds=[])]
        self.bundle['restoredCandidates'] = {}
        self.write('seed.json', dict(categories=[dict(id='housing', label='Housing')]))
        self.config['sourceSeedSha256'] = sha(self.config['sourceSeedPath'])
        self.write('registry.json', new_registry())
        self.write('curation/prepared-drafts.json', dict(artifactType='scout-preparation-drafts', importable=False,
            resources=[dict(id=rid) for rid in self.bundle['assessments']]))
        self.write('curation/curation-summary.json', dict(draftFile=str(self.root / 'curation/prepared-drafts.json'),
            draftSha256=sha(self.root / 'curation/prepared-drafts.json')))
        (self.root / 'review/report.md').write_text('Reviewed every candidate; no supported additional starters.')
        self.save_bundle()

    def write(self, relative, value):
        (self.root / relative).write_text(json.dumps(value))

    def save_bundle(self):
        self.write('review/content-reviewed.json', content_view(self.bundle))
        self.bundle['inputs'] = dict(draftsSha256=sha(self.root / 'curation/prepared-drafts.json'),
            curationFingerprint=curation_fingerprint(self.job), sourceSeedSha256=sha(self.root / 'seed.json'),
            contentReviewSha256=sha(self.root / 'review/content-reviewed.json'))
        seal(self.bundle)
        self.write('review/reviewed-bundle.json', self.bundle)

    def test_real_export_readback_and_short_date(self):
        result = export_reviewed_submission(self.config, self.job)
        artifact = Path(result['artifactFile'])
        self.assertEqual(artifact.name, 'scout-welfare-square-prepared-resources-26-09-25.json')
        self.assertEqual(sha(artifact), result['artifactSha256'])
        self.assertTrue(result['registryCommitRequired'])
        self.assertTrue((artifact.parent / 'preview.html').is_file())
        self.assertEqual(result, export_reviewed_submission(self.config, self.job))

    def test_cannot_drop_candidate_or_draft_even_with_new_review_fingerprint(self):
        self.bundle['candidateReview'].pop()
        self.save_bundle()
        with self.assertRaisesRegex(ValueError, 'Candidate review coverage'):
            validate_submission(self.config, self.job)
        self.setUp_candidate_rows()
        del self.bundle['assessments']['hidden']
        self.save_bundle()
        with self.assertRaisesRegex(ValueError, 'Draft assessment coverage'):
            validate_submission(self.config, self.job)

    def setUp_candidate_rows(self):
        self.bundle['candidateReview'].append(dict(categoryId='housing', candidateId='c2', decision='exclude',
            reason='No direct intake', resourceIds=[]))

    def test_stale_raw_drafts_or_curation_rejected_before_registry_write(self):
        before = sha(self.config['registryPath'])
        changed = deepcopy(self.job)
        changed['categories'][0]['resultSha256'] = 'new'
        with self.assertRaisesRegex(ValueError, 'Curation changed'):
            export_reviewed_submission(self.config, changed)
        with (self.root / 'curation/prepared-drafts.json').open('a') as handle:
            handle.write(' ')
        with self.assertRaisesRegex(ValueError, 'Drafts differ'):
            export_reviewed_submission(self.config, self.job)
        self.assertEqual(before, sha(self.config['registryPath']))

    def test_identity_stage_cannot_silently_change_frozen_content(self):
        self.bundle['payload']['resources'][0]['phone'] = 'new'
        seal(self.bundle)
        self.write('review/reviewed-bundle.json', self.bundle)
        with self.assertRaisesRegex(ValueError, 'altered reviewed content'):
            validate_submission(self.config, self.job)

    def test_cross_category_coverage_and_unaccounted_additions_rejected(self):
        self.bundle['candidateReview'][0]['categoryId'] = 'food'
        self.save_bundle()
        with self.assertRaisesRegex(ValueError, 'Candidate review coverage'):
            validate_submission(self.config, self.job)
        self.bundle['candidateReview'][0]['categoryId'] = 'housing'
        self.bundle['assessments']['extra'] = dict(state='not-offered', reason='Unknown record')
        self.save_bundle()
        with self.assertRaisesRegex(ValueError, 'Draft assessment coverage'):
            validate_submission(self.config, self.job)

    def test_authorized_pipeline_exports_without_legacy_review_completion(self):
        self.write('pipeline.json', self.config)
        self.write('pipeline-status.json', dict(phase='ready-review', jobId=1, reviewSessions=0))
        checkpoint = self.root / 'review/checkpoint.md'
        checkpoint.write_text('All category and draft judgments complete; final bundle sealed.')
        self.write('review/STATUS.json', dict(status='review-complete', checkpointFile=str(checkpoint)))
        store = Mock()
        store.get_scout_curation_job.return_value = self.job
        process = Mock(pid=123, returncode=0)
        process.poll.return_value = 0
        with patch.object(pipeline, 'ResearchStore', return_value=store), \
                patch.object(pipeline.subprocess, 'Popen', return_value=process), \
                patch.object(pipeline.subprocess, 'run'), patch.object(pipeline, 'notify_local', return_value={}), \
                patch.object(pipeline, 'review_handoff') as legacy:
            pipeline.supervise(self.root / 'pipeline.json')
        legacy.assert_not_called()
        state = json.loads((self.root / 'pipeline-status.json').read_text())
        self.assertEqual(state['phase'], 'prepared-delivery-ready')
        self.assertTrue(Path(state['delivery']['artifactFile']).exists())

    def test_prompt_is_fresh_and_prepared_not_legacy(self):
        prompt = prepared_review_prompt(self.config, 1, 1)
        self.assertIn('BLANK-SHEET', prompt)
        self.assertIn('FIVE ordered Information headings', prompt)
        self.assertIn('One sequential Codex reviewer', prompt)
        self.assertNotIn('Do not use review-complete unless the native handoff reports reviewed', prompt)

    def test_preserved_research_review_keeps_human_suppression(self):
        result = export_reviewed_submission(self.config, self.job)
        artifact = json.loads(Path(result['artifactFile']).read_text())
        (self.root / 'source-snapshot').mkdir()
        self.write('source-snapshot/research-manifest.json', {'source': 'frozen research'})
        self.write('source-snapshot/preservation.json', {'suppressedResourceIds': [artifact['resources'][0]['id']]})
        self.config.update(researchOrigin='preserved',
            researchManifestSha256=sha(self.root / 'source-snapshot/research-manifest.json'),
            preservationSha256=sha(self.root / 'source-snapshot/preservation.json'))
        self.bundle['inputs'].update({k:self.config[k] for k in ['researchManifestSha256', 'preservationSha256']})
        seal(self.bundle)
        self.write('review/reviewed-bundle.json', self.bundle)
        with self.assertRaisesRegex(ValueError, 'human-suppressed'):
            validate_submission(self.config, self.job)
        prompt = prepared_review_prompt(self.config, 1, 1)
        self.assertIn('REUSES PRESERVED RESEARCH', prompt)
        self.assertNotIn('This is a BLANK-SHEET run', prompt)
        self.assertIn('No new broad discovery', prompt)

    def test_dashboard_names_json_before_curation_and_never_borrows_another_import(self):
        self.write('pipeline.json', self.config)
        store = Mock(path=Path(self.config['database']))
        context = prepared_delivery_context(store, 1)
        self.assertEqual(context['filename'], 'scout-welfare-square-prepared-resources-<YY-MM-DD>.json')
        self.assertFalse(context['readyForSave'])
        self.assertIsNone(prepared_delivery_context(store, 2))
        self.write('pipeline-status.json', dict(phase='prepared-delivery-ready', delivery=dict(
            artifactFile='/delivery/scout-welfare-square-prepared-resources-26-09-29.json')))
        self.assertFalse(prepared_delivery_context(store, 1)['readyForSave'])
        self.assertEqual(prepared_delivery_context(store, 1)['filename'], 'scout-welfare-square-prepared-resources-26-09-29.json')
