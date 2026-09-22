import importlib.util
import json
import hashlib
from decimal import Decimal
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, MagicMock

spec = importlib.util.spec_from_file_location('deepseek_finish', Path(__file__).resolve().parents[1] / 'scripts/deepseek-welfare-finish.py')
finish = importlib.util.module_from_spec(spec)
spec.loader.exec_module(finish)


class LengthRecoveryTests(unittest.TestCase):
    def test_recovered_result_telemetry_does_not_double_count_failed_usage(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(finish.transport, 'OUT', Path(folder)):
            directory = Path(folder) / 'utilities, phone, internet'
            raw = json.dumps({'leads': []})
            directory.mkdir()
            (directory / 'result.json').write_text(raw)
            finish.transport.dump(directory / 'acceptance.json', {'accepted': True, 'resultSha256': hashlib.sha256(raw.encode()).hexdigest()})
            finish.transport.dump(Path(folder) / 'provider-handoff.json', [{'category': 'Utilities, Phone, Internet', 'replacementAssignmentId': 25}])
            usages = [{'prompt_tokens': 1000, 'completion_tokens': 32768}, {'prompt_tokens': 2000, 'completion_tokens': 100}]
            total = sum((finish.transport.usage_cost(u) for u in usages), Decimal(0))
            finish.transport.dump(directory / 'state.json', {'status': 'completed', 'createdAt': 'start', 'completedAt': 'end', 'upperCostUsd': str(total)})
            for i, usage in enumerate(usages, 1):
                finish.transport.dump(directory / f'turn-{i:03d}/response.json', {'usage': usage, 'elapsedSeconds': i})
            finish.transport.dump(directory / 'turn-001/failure.json', {'at': 'failure', 'message': 'Incomplete or unexpected finish: length'})
            finish.transport.dump(directory / 'turn-001/reservation.json', {'startedAt': 'start'})
            store = MagicMock()
            store.connect.return_value.__enter__.return_value.execute.return_value.fetchone.return_value = None
            store.get_focused_research_job.return_value = {'id': 20, 'categoryId': 'utilities-phone-internet'}
            with patch('resource_research_agent.storage.ResearchStore', return_value=store), patch('resource_research_agent.codex_first_research.save_codex_first_external_result', return_value={'id': 25, 'jobId': 20, 'leadCount': 0}):
                finish.save_result('Utilities, Phone, Internet')
            calls = [c.kwargs for c in store.record_worker_telemetry.call_args_list]
            self.assertEqual(['failed', 'completed'], [c['outcome'] for c in calls])
            self.assertEqual([1, 2], [c['attempt'] for c in calls])
            self.assertEqual(total, sum(Decimal(c['usage']['peakPriceUpperEstimateUsd']) for c in calls))
            self.assertEqual(100, calls[1]['usage']['completion_tokens'])

    def test_preserves_truncated_attempt_and_bounds_changed_continuation(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(finish.transport, 'OUT', Path(folder)):
            directory = Path(folder) / 'utilities, phone, internet'
            state = {'status': 'failed', 'turn': 1, 'upperCostUsd': '0.04',
                     'messages': [{'role': 'user', 'content': 'sealed assignment'},
                                  {'role': 'assistant', 'content': '', 'reasoning_content': 'saved planning'}]}
            response = {'finishReason': 'length', 'message': {'role': 'assistant', 'content': ''}}
            finish.transport.dump(directory / 'state.json', state)
            finish.transport.dump(directory / 'turn-001/response.json', response)
            finish.resume_length('Utilities, Phone, Internet')
            saved = finish.transport.read(directory / 'state.json')
            self.assertEqual(state, finish.transport.read(directory / 'failed-state-before-output-limit-recovery.json'))
            self.assertEqual(response, finish.transport.read(directory / 'turn-001/response.json'))
            self.assertEqual(state['messages'], saved['messages'][:-1])
            self.assertIn('Make a web tool call now', saved['messages'][-1]['content'])
            self.assertEqual('prepared', saved['status'])
            self.assertEqual(1, saved['turn'])
            self.assertEqual('0.04', saved['upperCostUsd'])
            saved['status'] = 'failed'
            finish.transport.dump(directory / 'state.json', saved)
            with self.assertRaisesRegex(RuntimeError, 'budget exhausted'):
                finish.resume_length('Utilities, Phone, Internet')


if __name__ == '__main__':
    unittest.main()
