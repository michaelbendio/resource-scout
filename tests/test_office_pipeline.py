import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import Mock, patch

from resource_research_agent import office_pipeline as pipeline


class OfficePipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.database = self.root / 'research.sqlite3'
        with sqlite3.connect(self.database) as db:
            db.execute('create table focused_research_jobs(import_id,status)')
            db.executemany('insert into focused_research_jobs values(?,?)', [(1, 'completed'), (1, 'in-progress')])
        self.config = dict(runDirectory=str(self.root), database=str(self.database), repository=str(self.root),
            importId=1, expectedCategories=2, authorization='Michael authorized research -> curation -> xhigh review',
            curationEffort='high', reviewEffort='xhigh', model='gpt-5.5', pythonBinary='/usr/bin/python3',
            codexBinary='/usr/local/bin/codex', maximumReviewSessions=8, reviewTimeoutSeconds=5400)
        self.config_path = self.root / 'pipeline.json'
        pipeline.write(self.config_path, self.config)
        pipeline.write(self.root / 'launch.json', {'pid': 101, 'deepseekPid': 102})

    def test_research_gate_requires_entire_exact_roster(self):
        self.assertFalse(pipeline.all_research_complete(self.database, 1, 2))
        self.assertFalse(pipeline.all_research_complete(self.database, 2, 0))
        with sqlite3.connect(self.database) as db:
            db.execute("update focused_research_jobs set status='completed'")
        self.assertTrue(pipeline.all_research_complete(self.database, 1, 2))
        self.assertFalse(pipeline.all_research_complete(self.database, 1, 21))

    def test_incomplete_research_never_launches_curation_or_review(self):
        with patch.object(pipeline, 'alive', return_value=False), patch.object(pipeline.time, 'sleep', side_effect=StopIteration), patch.object(pipeline.subprocess, 'Popen') as launch:
            with self.assertRaises(StopIteration):
                pipeline.supervise(self.config_path)
        launch.assert_not_called()
        self.assertEqual('waiting-research', pipeline.read(self.root / 'pipeline-status.json')['phase'])

    def test_review_flags_and_completion_require_real_checks(self):
        command = pipeline.review_command(self.config, self.root / 'review/session-001')
        self.assertIn('model_reasoning_effort="xhigh"', command)
        self.assertIn('workspace-write', command)
        self.assertFalse(pipeline.curation_complete({'status': 'completed', 'categories': [{'status':'assigned'}]}, 1))
        review = self.root / 'review'
        review.mkdir()
        checkpoint = review / 'checkpoint.md'
        checkpoint.write_text('Actual evidence and remaining browser checks.')
        result = dict(status='review-complete', checkpointFile=str(checkpoint))
        with self.assertRaisesRegex(ValueError, 'native fingerprint'):
            pipeline.review_outcome(result, review, None, False)
        result['status'] = 'continue'
        _, digest = pipeline.review_outcome(result, review, None, False)
        with self.assertRaisesRegex(ValueError, 'no new'):
            pipeline.review_outcome(result, review, digest, False)
        result['checkpointFile'] = str(self.config_path)
        with self.assertRaisesRegex(ValueError, 'inside'):
            pipeline.review_outcome(result, review, None, False)

    def test_finished_research_starts_supervised_high_curation_then_xhigh_review(self):
        curation = self.root / 'curation'
        curation.mkdir()
        pipeline.write(curation / 'supervisor-status.json', {'status':'ready-for-codex-review'})
        review = self.root / 'review'
        review.mkdir()
        checkpoint = review / 'checkpoint.md'
        checkpoint.write_text('All non-UI checks complete; browser verification remains.')
        pipeline.write(review / 'STATUS.json', dict(status='needs-browser-verification', checkpointFile=str(checkpoint)))
        store = Mock()
        store.get_scout_curation_job.return_value = dict(status='completed', categories=[{'status':'completed'}]*2)
        process = Mock(pid=999, returncode=0)
        process.poll.return_value = 0
        with patch.object(pipeline, 'all_research_complete', return_value=True), patch.object(pipeline, 'alive', return_value=False), patch.object(pipeline, 'ResearchStore', return_value=store), patch.object(pipeline, 'prepare_scout_curation_job', return_value={'id':1}), patch.object(pipeline.subprocess, 'Popen', return_value=process) as launch, patch.object(pipeline.subprocess, 'run'), patch.object(pipeline, 'notify_local', return_value={}), patch.object(pipeline, 'review_handoff', return_value={'status':'awaiting-codex-review'}):
            pipeline.supervise(self.config_path)
        self.assertEqual(2, launch.call_count)
        curation_command = pipeline.read(curation / 'launch.json')['command']
        self.assertEqual(self.config['curationEffort'], curation_command[curation_command.index('--effort') + 1])
        self.assertEqual('30', curation_command[curation_command.index('--batch-candidates') + 1])
        review_command = launch.call_args_list[1].args[0]
        self.assertIn('model_reasoning_effort="xhigh"', review_command)
        self.assertEqual('needs-browser-verification', pipeline.read(self.root / 'pipeline-status.json')['phase'])
        self.assertEqual(1, len(pipeline.read(self.root / 'review-time-sessions.json')))

    def test_xhigh_curation_is_not_silently_lowered(self):
        self.config['curationEffort'] = 'xhigh'
        pipeline.write(self.config_path, self.config)
        self.test_finished_research_starts_supervised_high_curation_then_xhigh_review()

    def test_review_prompt_uses_current_office_scope(self):
        self.config.update(officeName='Cedar City', serviceArea='Cedar City residents, Utah',
                           runDocument='docs/cedar-city-run-20260924.md')
        prompt = pipeline.review_prompt(self.config, 1, 1)
        self.assertIn('Cedar City residents, Utah', prompt)
        self.assertIn('docs/cedar-city-run-20260924.md', prompt)
        self.assertNotIn('Las Vegas', prompt)
        self.assertIn('Read each resource and its category-copy variants', prompt)

    def test_manual_review_handoff_launches_no_reviewer(self):
        self.config.update(automaticReview=False, officeName='Cedar City')
        pipeline.write(self.config_path, self.config)
        pipeline.write(self.root / 'pipeline-status.json', {'phase':'ready-review', 'jobId':1, 'reviewSessions':0})
        store = Mock()
        store.get_scout_curation_job.return_value = dict(status='completed', categories=[{'status':'completed'}]*2)
        with patch.object(pipeline, 'ResearchStore', return_value=store), patch.object(pipeline.subprocess, 'Popen') as launch, patch.object(pipeline.subprocess, 'run'), patch.object(pipeline, 'notify_local', return_value={}) as notice:
            pipeline.supervise(self.config_path)
        launch.assert_not_called()
        self.assertEqual('ready-for-codex-review', pipeline.read(self.root / 'pipeline-status.json')['phase'])
        self.assertFalse((self.root / 'review-time-sessions.json').exists())
        self.assertIn('Cedar City', notice.call_args.args[0])

    def test_manual_review_handoff_still_requires_completed_curation(self):
        self.config['automaticReview'] = False
        pipeline.write(self.config_path, self.config)
        pipeline.write(self.root / 'pipeline-status.json', {'phase':'ready-review', 'jobId':1, 'reviewSessions':0})
        store = Mock()
        store.get_scout_curation_job.return_value = dict(status='in-progress', categories=[])
        with patch.object(pipeline, 'ResearchStore', return_value=store), patch.object(pipeline.subprocess, 'Popen') as launch:
            with self.assertRaisesRegex(RuntimeError, 'Canonical curation'):
                pipeline.supervise(self.config_path)
        launch.assert_not_called()
