import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from resource_research_agent.curation_supervisor import load_launch, recovery_decision, supervise, notify_local


class CurationSupervisorTests(unittest.TestCase):
    def test_notification_records_failure_without_claiming_user_saw_it(self):
        for code, expected in ((0, 'requested'), (1, 'failed')):
            with patch('resource_research_agent.curation_supervisor.subprocess.run',
                       return_value=Mock(returncode=code, stderr='permission error' if code else '')):
                outcome = notify_local('Curation stopped: inconsistent links')
            self.assertEqual(expected, outcome['status'])
            self.assertFalse(outcome['displayConfirmed'])
        with patch('resource_research_agent.curation_supervisor.subprocess.run', side_effect=OSError('not available')):
            self.assertEqual('failed', notify_local('Stopped')['status'])

    def decision(self, **kwargs):
        settings = dict(complete=False, exported=False, done=2, limit=21,
                        last_phase='codex-curation-active', last_message='Working',
                        restarts=0, maximum_restarts=2)
        settings.update(kwargs)
        return recovery_decision(**settings)

    def test_finished_and_explicit_category_limit_never_restart(self):
        self.assertEqual('ready-for-codex-review', self.decision(complete=True, exported=True))
        self.assertEqual('category-limit-reached', self.decision(limit=2))
        self.assertEqual('restart-coordinator', self.decision(complete=True, exported=False))

    def test_worker_failures_are_not_mistaken_for_crashed_coordinator(self):
        for message in ('401 unauthorized', 'usage limit reached', 'context window exceeded',
                        'Inconsistent candidate/resource links', 'transport retry exhausted: 503'):
            self.assertEqual('needs-attention', self.decision(
                last_phase='codex-curation-stopped', last_message=message))
        self.assertEqual('restart-coordinator', self.decision(
            last_phase='codex-curation-stopped', last_message='503 temporarily unavailable'))
        self.assertEqual('recovery-budget-exhausted', self.decision(restarts=2))

    def manifest(self, root):
        path = root / 'launch.json'
        path.write_text(json.dumps({'pid': 111, 'command': [
            'caffeinate', '-dimsu', 'python3', '-m', 'resource_research_agent.scout_curation_runner',
            '--database', str(root / 'test.sqlite3'), '--output', str(root),
            '--import-id', '1', '--effort', 'high', '--max-categories', '21']}))
        return path

    def store(self):
        store = Mock()
        store.connect.return_value.__enter__ = Mock(return_value=Mock())
        store.connect.return_value.__exit__ = Mock(return_value=False)
        store.connect.return_value.__enter__.return_value.execute.return_value.fetchone.return_value = [1]
        return store

    def test_live_attachment_monitors_without_starting_duplicate_and_observes_completion(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); manifest = self.manifest(root)
            store = self.store()
            store.get_scout_curation_job.side_effect = [
                {'status': 'in-progress', 'categories': [{'categoryId': 'a', 'status': 'assigned'}]},
                {'status': 'completed', 'categories': [{'categoryId': 'a', 'status': 'completed'}]},
            ]
            store.list_scout_curation_progress.return_value = [{'phase': 'codex-curation-completed', 'message': 'Complete'}]
            review = root / 'autoTest.html'; review.write_text('draft')
            (root / 'curation-summary.json').write_text(json.dumps({
                'status': 'completed', 'jobId': 1, 'reviewFile': str(review)}))
            identity = {'state': 'S', 'identity': 'start python -m resource_research_agent.scout_curation_runner'}
            with patch('resource_research_agent.curation_supervisor.ResearchStore', return_value=store), \
                 patch('resource_research_agent.curation_supervisor.process_identity', side_effect=[identity, identity, None]), \
                 patch('resource_research_agent.curation_supervisor.time.sleep'), \
                 patch('resource_research_agent.curation_supervisor.subprocess.Popen') as launch:
                state = supervise(manifest, attach_pid=111)
            launch.assert_not_called()
            self.assertEqual('ready-for-codex-review', state['status'])
            self.assertEqual(0, state['coordinatorRestarts'])

    def test_spent_coordinator_budget_is_preserved_across_supervisor_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); manifest = self.manifest(root)
            (root / 'supervisor-status.json').write_text(json.dumps({
                'database': str((root / 'test.sqlite3').resolve()), 'jobId': 1, 'coordinatorRestarts': 2}))
            store = self.store()
            store.get_scout_curation_job.return_value = {'status': 'in-progress', 'categories': [{'status': 'pending'}]}
            store.list_scout_curation_progress.return_value = []
            with patch('resource_research_agent.curation_supervisor.ResearchStore', return_value=store), \
                 patch('resource_research_agent.curation_supervisor.subprocess.Popen') as launch:
                state = supervise(manifest, attach_pid=None)
            launch.assert_not_called()
            self.assertEqual('recovery-budget-exhausted', state['status'])
            store.record_scout_curation_progress.assert_called_once()

    def test_coordinator_recovery_is_charged_once_and_followed_to_completion(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); manifest = self.manifest(root)
            store = self.store()
            store.get_scout_curation_job.side_effect = [
                {'status': 'in-progress', 'categories': [{'status': 'pending'}]},
                {'status': 'in-progress', 'categories': [{'categoryId': 'a', 'status': 'assigned'}]},
                {'status': 'completed', 'categories': [{'status': 'completed'}]},
            ]
            store.list_scout_curation_progress.return_value = []
            review = root / 'autoTest.html'; review.write_text('draft')
            (root / 'curation-summary.json').write_text(json.dumps({
                'status': 'completed', 'jobId': 1, 'reviewFile': str(review)}))
            identity = {'state': 'S', 'identity': 'start python -m resource_research_agent.scout_curation_runner'}
            child = Mock(pid=222)
            with patch('resource_research_agent.curation_supervisor.ResearchStore', return_value=store), \
                 patch('resource_research_agent.curation_supervisor.process_identity', side_effect=[identity, identity, identity, None]), \
                 patch('resource_research_agent.curation_supervisor.time.sleep'), \
                 patch('resource_research_agent.curation_supervisor.subprocess.Popen', return_value=child) as launch:
                state = supervise(manifest, attach_pid=None)
            launch.assert_called_once()
            self.assertEqual('ready-for-codex-review', state['status'])
            self.assertEqual(1, state['coordinatorRestarts'])
            self.assertEqual(222, json.loads((root / 'supervisor-launch-1.json').read_text())['pid'])

    def test_other_provider_or_shell_launch_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); manifest = self.manifest(root)
            saved = json.loads(manifest.read_text())
            saved['command'][4] = 'resource_research_agent.pairwise_supervisor'
            manifest.write_text(json.dumps(saved))
            with self.assertRaises(ValueError):
                load_launch(manifest)
            manifest = self.manifest(root)
            saved = json.loads(manifest.read_text()); saved['command'][2] = 'zsh'
            manifest.write_text(json.dumps(saved))
            with self.assertRaises(ValueError):
                load_launch(manifest)


if __name__ == '__main__':
    unittest.main()
