import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from resource_research_agent import research_watchdog as watchdog


class ResearchWatchdogTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.directory = self.root / 'deepseek-challenger/assignment-1'
        self.body = {'model': 'deepseek-flash', 'stop_reason': 'end_turn', 'content': [
            {'type': 'text', 'text': 'Checking official sources.'},
            {'type': 'web_search_tool_result', 'content': [{'url': 'https://example.org'}]},
            {'type': 'text', 'text': '{"leads": []}'}]}
        self.state = dict(status='failed', turn=1, category='Food', successfulSearchResults=1,
                          messages=[{'role': 'assistant', 'content': self.body['content']}])
        self.save()

    def save(self):
        watchdog.write(self.directory / 'state.json', self.state)
        watchdog.write(self.directory / 'turn-001/response.json', self.body)
        watchdog.write(self.directory / 'turn-001/billing.json', {'seconds': 3})

    def test_offline_recovery_preserves_original_and_cannot_repeat(self):
        original = (self.directory / 'state.json').read_bytes()
        with patch.object(watchdog.subprocess, 'Popen') as process:
            self.assertEqual('saved-final-answer', watchdog.recover_saved_response(self.directory))
        process.assert_not_called()
        self.assertEqual(original, (self.directory / 'watchdog-recovery-turn-001/original-failed-state.json').read_bytes())
        self.assertEqual(self.body, watchdog.read(self.directory / 'turn-001/response.json'))
        self.assertEqual('completed', watchdog.read(self.directory / 'state.json')['status'])
        self.assertIsNone(watchdog.recover_saved_response(self.directory))

    def test_unknown_output_and_inflight_requests_are_not_replayed(self):
        self.body['content'][-1]['text'] = 'I could not finish the research.'
        self.save()
        self.assertIsNone(watchdog.recover_saved_response(self.directory))
        self.assertEqual('failed', watchdog.read(self.directory / 'state.json')['status'])
        self.state['status'] = 'requesting'
        self.save()
        self.assertIsNone(watchdog.recover_saved_response(self.directory))
        for status in ['requesting', 'failed', 'budget-stop']:
            self.assertFalse(watchdog.restart_allowed([{'status': status}], 'recovered', 0, 3))
        self.assertFalse(watchdog.restart_allowed([{'status': 'completed'}], 'needs-attention', 0, 3))
        self.assertFalse(watchdog.restart_allowed([{'status': 'prepared'}], 'recovered', 3, 3))
        self.assertTrue(watchdog.restart_allowed([{'status': 'awaiting-tools'}], 'recovered', 1, 3))

    def test_command_binding_rejects_changed_budget(self):
        launch = dict(database=str(self.root / 'research.sqlite3'), importId=1, deepseekBudgetUsd='5.00')
        command = ['/usr/bin/caffeinate', '-dimsu', '/usr/bin/python3', '-u', '-m',
                   'resource_research_agent.deepseek_challenger_runner', '--database', launch['database'],
                   '--import-id', '1', '--output-dir', str(self.root / 'deepseek-challenger'), '--budget-usd', '5.00']
        launch['deepseekCommand'] = command
        self.assertEqual(command, watchdog.validated_command(launch, self.root))
        command[-1] = '50.00'
        with self.assertRaisesRegex(ValueError, 'budget'):
            watchdog.validated_command(launch, self.root)

    def test_live_coordinators_and_offline_recovery_restart(self):
        database = self.root / 'research.sqlite3'
        with sqlite3.connect(database) as db:
            db.execute('create table focused_research_jobs(id,import_id,status)')
            db.execute("insert into focused_research_jobs values(1,1,'in-progress')")
            db.execute('create table focused_research_passes(job_id,pass_kind,status)')
            db.execute("insert into focused_research_passes values(1,'focus','assigned')")
        watchdog.write(self.root / 'launch.json', dict(database=str(database), importId=1, pid=101, deepseekPid=102))
        watchdog.write(self.root / 'deepseek-challenger/manifest.json', dict(database=str(database), importId=1, model='deepseek-flash'))
        watchdog.write(self.root / 'deepseek-challenger/supervisor-status.json', {'status': 'running'})
        (self.root / 'runner.log').write_text('primary-pass-started')
        self.state['status'] = 'requesting'
        self.save()
        def identity(pid):
            module = 'pairwise_runner' if pid == 101 else 'deepseek_challenger_runner'
            return {'state': 'S', 'identity': f'timestamp python -m resource_research_agent.{module} --database {database}'}
        with patch.object(watchdog, 'process_identity', side_effect=identity), patch.object(watchdog.time, 'sleep', side_effect=StopIteration), patch.object(watchdog.subprocess, 'Popen') as process:
            with self.assertRaises(StopIteration):
                watchdog.supervise(self.root)
        process.assert_not_called()
        status = watchdog.read(self.root / 'research-watchdog-status.json')
        self.assertEqual('monitoring', status['status'])
        self.assertTrue(status['primaryAlive'] and status['challengerAlive'])
        self.assertEqual(0, status['challengerRestarts'])
        # A diagnosed saved response can be recovered, with a single persisted restart.
        self.state['status'] = 'failed'
        self.save()
        launch = watchdog.read(self.root / 'launch.json')
        launch.update(deepseekBudgetUsd='5.00', deepseekCommand=[
            '/usr/bin/python3', '-u', '-m', 'resource_research_agent.deepseek_challenger_runner',
            '--database', str(database), '--import-id', '1', '--output-dir',
            str(self.root / 'deepseek-challenger'), '--budget-usd', '5.00'])
        watchdog.write(self.root / 'launch.json', launch)
        watchdog.write(self.root / 'deepseek-challenger/supervisor-status.json', {'status': 'needs-attention'})
        with patch.object(watchdog, 'process_identity', side_effect=lambda pid: identity(pid) if pid == 101 else None), patch.object(watchdog.time, 'sleep', side_effect=StopIteration), patch.object(watchdog.subprocess, 'Popen') as process:
            process.return_value.pid = 103
            with self.assertRaises(StopIteration):
                watchdog.supervise(self.root)
        process.assert_called_once()
        self.assertEqual(103, watchdog.read(self.root / 'launch.json')['deepseekPid'])
        self.assertEqual(1, watchdog.read(self.root / 'research-watchdog-status.json')['challengerRestarts'])
        self.assertEqual('completed', watchdog.read(self.directory / 'state.json')['status'])
        self.assertIn('saved-final-answer', (self.root / 'research-issues.jsonl').read_text())


if __name__ == '__main__':
    unittest.main()
