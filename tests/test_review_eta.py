import json
import sqlite3
import tempfile
import unittest
from copy import deepcopy
from datetime import datetime, timezone, timedelta
from pathlib import Path
from resource_research_agent.review_eta import estimate_review, forecast


class ReviewEstimateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        session = self.root / 'review/session-001'
        session.mkdir(parents=True)
        self.start = datetime(2026, 9, 29, 12, tzinfo=timezone.utc)
        (session / 'launch.json').write_text(json.dumps({'startedAt':self.start.isoformat()}))
        self.db = self.root / 'research.sqlite3'
        with sqlite3.connect(self.db) as c:
            c.execute('create table scout_curation_categories(job_id,category_id,candidate_count,resource_count)')
            c.executemany('insert into scout_curation_categories values(1,?,?,?)', [('food',50,50),('housing',100,100)])
        self.progress = dict(checkpointAvailable=True, updatedAt=(self.start+timedelta(hours=1)).isoformat(),stage='taxonomy',
            categories=[dict(categoryId='food',content='complete'),dict(categoryId='housing',content='pending')],
            identityStatus='pending',validationStatus='pending',taxonomyCompleted=0,selectionCompleted=0)
        self.pipeline = dict(phase='review')

    def estimate(self, hours=1):
        return estimate_review(self.root, self.db, 1, self.progress, self.pipeline, self.start+timedelta(hours=hours))

    def test_all_stages_included_and_poll_does_not_advance(self):
        first = self.estimate()
        self.assertEqual('estimated', first['status'])
        self.assertEqual(5, len(first['stages']))
        stages = {s['stage']:s for s in first['stages']}
        self.assertEqual('Observed checkpoint pace', stages['content']['basis'])
        for stage in ['identity','taxonomy','selection','validation']:
            self.assertGreater(stages[stage]['upperSeconds'], 0)
            self.assertIn('Planning allowance', stages[stage]['basis'])
        self.assertEqual(sum(s['upperSeconds'] for s in first['stages']), first['upperSeconds'])
        saved = (self.root/'review-estimate-history.json').read_bytes()
        again = self.estimate(1.5)
        self.assertEqual(first['latestCompletion'], again['latestCompletion'])
        self.assertEqual(saved,(self.root/'review-estimate-history.json').read_bytes())
        self.assertEqual('overdue', self.estimate(30)['status'])

    def test_measured_taxonomy_replaces_allowance(self):
        self.estimate()
        self.progress.update(updatedAt=(self.start+timedelta(hours=1.5)).isoformat(),stage='selection',taxonomyCompleted=1)
        result = self.estimate(1.5)
        taxonomy = next(s for s in result['stages'] if s['stage']=='taxonomy')
        self.assertEqual('Observed checkpoint pace',taxonomy['basis'])
        self.assertAlmostEqual(1800*1.8,taxonomy['upperSeconds'])

    def test_reopen_reset_and_paused_suppression(self):
        self.estimate()
        self.progress['categories'][0]['content']='in-progress'
        self.progress['updatedAt']=(self.start+timedelta(hours=2)).isoformat()
        self.assertEqual('learning',self.estimate(2)['status'])
        self.pipeline['phase']='needs-attention'
        self.assertNotIn('latestCompletion',self.estimate(3))
        self.assertEqual('inactive',self.estimate(3)['status'])

    def test_new_review_does_not_reuse_old_pace(self):
        self.estimate()
        start2=self.start+timedelta(days=1)
        (self.root/'review/session-001/launch.json').write_text(json.dumps({'startedAt':start2.isoformat()}))
        self.assertEqual('learning',self.estimate(25)['status'])

    def test_partial_counts_and_session_gaps(self):
        self.progress['categories'][0]['content']='in-progress'
        self.progress['stage']='content'
        self.progress['recordProgress']=dict(categoryId='food',resourcesReviewed=10,candidatesReviewed=10)
        result=self.estimate()
        self.assertIn('20 saved',result['basis'])
        history=json.loads((self.root/'review-estimate-history.json').read_text())
        # Only half of this wall-clock interval was spent in an active session.
        result=forecast(history['checkpoints'],history['totals'],[(self.start,self.start+timedelta(minutes=30))],self.start+timedelta(hours=1))
        content=next(s for s in result['stages'] if s['stage']=='content')
        self.assertEqual(round(280*90*.65),content['lowerSeconds'])
