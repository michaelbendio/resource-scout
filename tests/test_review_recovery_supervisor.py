import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from resource_research_agent import review_recovery_supervisor as recovery
from resource_research_agent import office_pipeline


class ReviewRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.review = self.root / 'review'
        self.session = self.review / 'session-011'
        self.session.mkdir(parents=True)
        self.checkpoint = self.review / 'food-decisions.json'
        self.checkpoint.write_text('{"authoredDecisions": ["retained original evidence"]}')
        self.config = dict(maximumReviewSessions=64, automaticReview=True, authorization='Resume both office reviews',
                           reviewEffort='xhigh', preparedMode=True, preparedReviewAuthorized=True,
                           runDirectory=str(self.root), repository=str(self.root))
        self.state = dict(phase='needs-attention', reviewSessions=11, reviewDirectory=str(self.session),
                          supervisorPid=None, reviewPid=None, reviewCheckpointSha256='prior-completed-category')
        self.write(self.review / 'progress.json', dict(checkpointFile=str(self.checkpoint)))
        self.write(self.review / 'STATUS.json', dict(status='continue', checkpointFile=str(self.checkpoint)))
        self.write(self.root / 'pipeline-status.json', self.state)
        self.failure('Codex ran out of room in the model context window.')

    def write(self, path, value):
        recovery.atomic_json(path, value)

    def failure(self, text, exit_code=1):
        self.write(self.session / 'execution.json', dict(exitCode=exit_code, timedOut=False))
        self.write(self.session / 'events.jsonl', dict(type='turn.failed', error=dict(message=text)))

    def prepare(self):
        return recovery.prepare_recovery(self.root, self.config, dict(self.state))

    def test_context_preserves_attempt_and_resumes_only_saved_work(self):
        native = (self.session / 'events.jsonl').read_bytes()
        evidence = self.checkpoint.read_bytes()
        ok, attempt = self.prepare()
        self.assertTrue(ok)
        self.assertEqual(native, (self.session / 'events.jsonl').read_bytes())
        self.assertEqual(evidence, self.checkpoint.read_bytes())
        self.assertEqual('ready-review', recovery.read(self.root / 'pipeline-status.json')['phase'])
        self.assertEqual(11, recovery.read(self.root / 'pipeline-status.json')['reviewSessions'])
        self.assertEqual('continue', recovery.read(self.review / 'STATUS.json')['status'])
        self.assertTrue((Path(attempt) / 'STATUS.json').is_file())
        self.assertIn('TWO groups', (self.review / 'AUTOMATIC_RECOVERY.md').read_text())
        self.assertFalse(self.prepare()[0])

    def test_context_without_new_checkpoint_never_retries(self):
        self.state['reviewCheckpointSha256'] = recovery.digest(self.checkpoint)
        ok, reason = self.prepare()
        self.assertFalse(ok)
        self.assertIn('without new saved', reason)

    def test_checkpoint_outside_review_or_in_native_session_is_rejected(self):
        for path in [self.root / 'outside.json', self.session / 'prompt.txt']:
            path.write_text('not saved review decisions')
            self.write(self.review / 'progress.json', dict(checkpointFile=str(path)))
            self.write(self.review / 'STATUS.json', dict(checkpointFile=str(path)))
            self.assertFalse(self.prepare()[0])

    def test_transport_without_progress_retries_once_only(self):
        self.state['reviewCheckpointSha256'] = recovery.digest(self.checkpoint)
        self.failure('stream disconnected: connection reset')
        self.assertTrue(self.prepare()[0])
        self.session = self.review / 'session-012'
        self.session.mkdir()
        self.state.update(reviewDirectory=str(self.session), reviewSessions=12)
        self.failure('stream disconnected: connection reset')
        ok, reason = self.prepare()
        self.assertFalse(ok)
        self.assertIn('without new saved progress', reason)

    def test_budgets_and_account_errors_do_not_loop(self):
        for text in ['usage limit reached', 'authentication failed', 'unexpected validation failure']:
            self.failure(text)
            self.assertFalse(self.prepare()[0])
        self.failure('context window exceeded')
        self.state['reviewSessions'] = 64
        self.assertFalse(self.prepare()[0])

    def test_intentional_acceptance_stop_and_live_worker_are_preserved(self):
        self.failure('context window exceeded', exit_code=0)
        self.assertFalse(self.prepare()[0])
        self.failure('context window exceeded')
        with patch.object(recovery, 'live', return_value=True):
            self.assertFalse(self.prepare()[0])

    def test_timeout_does_not_replay_even_with_a_context_error(self):
        self.write(self.session / 'execution.json', dict(exitCode=-15, timedOut=True))
        self.assertIn('timed out', self.prepare()[1])

    def test_context_recovery_budget_persists_across_sessions(self):
        for i in range(3):
            self.session = self.review / f'session-{i+11:03}'
            self.session.mkdir(exist_ok=True)
            self.state.update(reviewDirectory=str(self.session), reviewSessions=i+11)
            self.checkpoint.write_text(f'New authored decisions group {i}')
            self.failure('context window exceeded')
            self.assertTrue(self.prepare()[0])
        self.session = self.review / 'session-014'
        self.session.mkdir()
        self.state.update(reviewDirectory=str(self.session), reviewSessions=14)
        self.checkpoint.write_text('New authored decisions group 4')
        self.failure('context window exceeded')
        self.assertIn('budget exhausted', self.prepare()[1])

    def test_future_prompt_contains_bounded_recovery_and_original_acceptance(self):
        self.assertTrue(self.prepare()[0])
        with patch.object(office_pipeline, '_base_review_prompt', return_value='Original supervisor acceptance gate'):
            prompt = office_pipeline.review_prompt(self.config, 1, 12)
        self.assertIn('Original supervisor acceptance gate', prompt)
        self.assertIn('TWO groups', prompt)
        self.assertIn('not review completion', prompt)

    def test_monitor_restarts_exact_acceptance_wrapper_and_honors_pause(self):
        config = self.root / 'pipeline.json'
        self.write(config, self.config)
        command = ['python3', 'supervise_thorough_review.py', '--config', str(config)]
        launch = self.root / 'recovery-launch.json'
        self.write(launch, dict(config=str(config), pipelineCommand=command))
        def pause(_):
            state = recovery.read(self.root / 'pipeline-status.json')
            state['phase'] = 'paused'
            self.write(self.root / 'pipeline-status.json', state)
        with patch.object(recovery, 'live', return_value=False), patch.object(recovery, 'notify_local'), \
             patch.object(recovery.subprocess, 'Popen', return_value=Mock(pid=999)) as spawn, \
             patch.object(recovery.time, 'sleep', side_effect=pause):
            recovery.supervise(launch)
        spawn.assert_called_once()
        self.assertEqual(command, spawn.call_args.args[0])
        self.assertEqual('handoff', recovery.read(self.root / 'review-recovery-status.json')['status'])
