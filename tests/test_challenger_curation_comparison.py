import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('curation_comparison',
    Path(__file__).resolve().parents[1] / 'scripts/curate-challenger-comparison.py')
comparison = importlib.util.module_from_spec(spec)
spec.loader.exec_module(comparison)


class AttributionTests(unittest.TestCase):
    def fixture(self, directory):
        key = {
            'H1': {'provider': 'saved-baseline', 'categoryId': 'housing'},
            'H2': {'provider': 'new-trial', 'categoryId': 'housing'},
            'E1': {'provider': 'new-trial', 'categoryId': 'employment'},
            'E2': {'provider': 'saved-baseline', 'categoryId': 'employment'},
        }
        shared = dict(id='same-program', name='Program', categories=['housing'],
                      candidateIds=['H1', 'H2'])
        extended = {**shared, 'categories': ['housing', 'employment'],
                    'candidateIds': ['H1', 'H2', 'E1']}
        def disposition(candidate, state='curated'):
            return dict(candidateId=candidate, disposition=state,
                        resourceIds=[] if state == 'omitted' else ['same-program'], reason='Evidence')
        job = dict(status='completed', categories=[
            dict(categoryId='housing', status='completed', result=dict(resources=[shared],
                candidateDispositions=[disposition('H1'), disposition('H2', 'merged')])),
            dict(categoryId='employment', status='completed', result=dict(resources=[extended],
                candidateDispositions=[disposition('E1', 'merged'), disposition('E2', 'omitted')])),
        ])
        (directory / 'job.json').write_text(json.dumps(job))
        (directory / 'provider-key.json').write_text(json.dumps(key))
        return job

    def test_aliases_and_cross_category_reuse_do_not_inflate_provider_yield(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            self.fixture(directory)
            with patch.object(comparison, 'OUT', directory), contextlib.redirect_stdout(io.StringIO()):
                comparison.compare()
            result = json.loads((directory / 'comparison-counts.json').read_text())
            self.assertEqual(result['globalCounts'], dict(grok=1, deepseek=1, shared=1,
                grokOnly=0, deepseekOnly=0, union=1))
            employment = result['categories'][1]
            self.assertEqual(employment['providers']['saved-baseline']['distinctResourceIds'], [])
            self.assertEqual(employment['deepseekOnly'], ['same-program'])
            self.assertFalse(result['finalReviewComplete'])
            self.assertFalse(result['humanCurated'])

    def test_missing_original_submission_cannot_disappear_from_comparison(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            job = self.fixture(directory)
            job['categories'][1]['result']['candidateDispositions'].pop()
            (directory / 'job.json').write_text(json.dumps(job))
            with patch.object(comparison, 'OUT', directory), self.assertRaisesRegex(RuntimeError, 'coverage'):
                comparison.compare()

    def test_completed_run_preserves_sealed_job_and_never_relaunches_workers(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            self.fixture(directory)
            before = (directory / 'job.json').read_bytes()
            with patch.object(comparison, 'OUT', directory), \
                    patch.object(comparison, 'complete_batched_category') as worker, \
                    contextlib.redirect_stdout(io.StringIO()):
                comparison.run()
                first_resources = (directory / 'resources.json').read_bytes()
                comparison.run()
            worker.assert_not_called()
            self.assertEqual(before, (directory / 'job.json').read_bytes())
            self.assertEqual(first_resources, (directory / 'resources.json').read_bytes())


if __name__ == '__main__':
    unittest.main()
