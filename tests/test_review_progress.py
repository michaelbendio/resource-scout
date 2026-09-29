import json
from pathlib import Path
import tempfile
import unittest

from resource_research_agent.review_progress import review_progress


class ReviewProgressTests(unittest.TestCase):
    def test_saved_decisions_drive_counts_and_activity_does_not(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'review').mkdir()
            pipeline = dict(phase='review', reviewSessions=2, lastReviewEventAgeSeconds=0)
            self.assertFalse(review_progress(root, ['housing', 'food'], pipeline)['checkpointAvailable'])
            checkpoint = root / 'review/decisions.md'
            checkpoint.write_text('Reviewed Housing dispositions and facts; Food review remains.')
            data = dict(updatedAt='2026-09-29T07:00:00Z', stage='content', summary='Housing complete; checking Food.',
                checkpointFile=str(checkpoint), identityStatus='pending', validationStatus='pending',
                categories=[dict(categoryId='housing', content='complete', taxonomy='pending', selection='pending'),
                            dict(categoryId='food', content='in-progress', taxonomy='pending', selection='pending')])
            path = root / 'review/progress.json'
            path.write_text(json.dumps(data))
            progress = review_progress(root, ['housing', 'food'], pipeline)
            self.assertEqual((1, 0, 0), tuple(progress[k] for k in ['contentCompleted', 'taxonomyCompleted', 'selectionCompleted']))
            self.assertEqual(2, progress['totalCategories'])
            pipeline['lastReviewEventAgeSeconds'] = 400
            self.assertEqual(progress, review_progress(root, ['housing', 'food'], pipeline))
            data['categories'][0]['content'] = 'in-progress'
            path.write_text(json.dumps(data))
            self.assertEqual(0, review_progress(root, ['housing', 'food'], pipeline)['contentCompleted'])
            data['categories'].pop()
            path.write_text(json.dumps(data))
            self.assertTrue(review_progress(root, ['housing', 'food'], pipeline)['checkpointError'])
            path.write_text('{')
            self.assertTrue(review_progress(root, ['housing', 'food'], pipeline)['checkpointError'])

    def test_progress_cannot_use_an_external_or_missing_checkpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'review').mkdir()
            other = root / 'outside.md'
            other.write_text('Not a review checkpoint')
            data = dict(updatedAt='2026-09-29T07:00:00Z', stage='validation', summary='Claimed done',
                checkpointFile=str(other), identityStatus='complete', validationStatus='complete',
                categories=[dict(categoryId='food', content='complete', taxonomy='complete', selection='complete')])
            (root / 'review/progress.json').write_text(json.dumps(data))
            progress = review_progress(root, ['food'], {'phase':'review'})
            self.assertTrue(progress['checkpointError'])
            self.assertFalse(progress['checkpointAvailable'])
