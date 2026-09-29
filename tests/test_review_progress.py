import json
from pathlib import Path
import tempfile
import unittest

from resource_research_agent.review_progress import review_progress


class ReviewProgressTests(unittest.TestCase):
    def test_record_checkpoints_and_native_activity_stay_separate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            review = root / 'review'
            session = review / 'session-001'
            session.mkdir(parents=True)
            checkpoint = review / 'decisions.md'
            checkpoint.write_text('Individual saved decisions for two Food resources.')
            data = dict(updatedAt='2026-09-29T07:00:00Z', stage='content', summary='Checking Food intake.',
                checkpointFile=str(checkpoint), identityStatus='pending', validationStatus='pending',
                categories=[dict(categoryId='food', content='in-progress', taxonomy='pending', selection='pending')],
                recordProgress=dict(categoryId='food', resourcesReviewed=2, resourcesTotal=20,
                                    candidatesReviewed=3, candidatesTotal=30, currentTask='Checking pantry eligibility'),
                recentFindings=['One pantry requires a referral; checking the public front door.'])
            (review / 'progress.json').write_text(json.dumps(data))
            events = session / 'events.jsonl'
            events.write_text(json.dumps(dict(type='item.completed', item=dict(type='agent_message', text='Checking intake.'))) + '\n'
                              + json.dumps(dict(type='item.completed', item=dict(type='command_execution', command='private command'))) + '\n{partial')
            pipeline = dict(phase='review', reviewSessions=1, reviewDirectory=str(session))
            progress = review_progress(root, ['food'], pipeline)
            self.assertEqual(2, progress['recordProgress']['resourcesReviewed'])
            self.assertEqual(0, progress['contentCompleted'])
            self.assertEqual('Checking intake.', progress['activity']['message'])
            self.assertNotIn('private command', json.dumps(progress))
            self.assertEqual('in-progress', progress['categories'][0]['content'])
            data['recordProgress']['resourcesReviewed'] = 21
            (review / 'progress.json').write_text(json.dumps(data))
            self.assertTrue(review_progress(root, ['food'], pipeline)['checkpointError'])
            pipeline['reviewDirectory'] = str(root)
            self.assertIsNone(review_progress(root, ['food'], pipeline)['activity'])

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
