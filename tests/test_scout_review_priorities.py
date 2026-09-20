import copy
import json
import unittest

import test_scout_curation as fixtures
from resource_research_agent.scout_curation import ScoutCurationError, build_scout_review_seed
from resource_research_agent.scout_navigation import latest_navigation, save_navigation
from resource_research_agent.scout_review_handoff import review_fingerprint, review_handoff
from resource_research_agent.scout_review_priorities import latest_priorities, save_priorities, validate_priorities, priority_source_seed
from resource_research_agent.scout_review_readiness import require_review_ready
from resource_research_agent.scout_review import build_scout_review_file


class ScoutReviewPriorityTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.ScoutCurationTests()
        self.fixture.setUp()
        self.store = self.fixture.store
        self.job = self.fixture.completed_review_fixture()
        self.fixture.complete_test_review(self.job['id'])
        self.job = self.store.get_scout_curation_job(self.job['id'])
        self.proposal = latest_priorities(self.store,self.job['id'])['proposal']

    def tearDown(self):
        self.fixture.tearDown()

    def test_requires_complete_evidenced_category_membership_decisions(self):
        seed=priority_source_seed(self.store,self.job)
        for mutate, message in [
            (lambda p:p['assignments'].pop(), 'every resource'),
            (lambda p:p['assignments'].append(p['assignments'][0]), 'every resource'),
            (lambda p:p['assignments'][0].update(categoryId='invented'), 'every resource'),
            (lambda p:p['assignments'][0].update(reason=' '), 'short reason'),
            (lambda p:p['assignments'][0].update(tier='best provider'), 'Choose start'),
            (lambda p:p['assignments'][0].update(evidence={'field':'description','text':'invented fact'}), 'evidence'),
            (lambda p:p.update(baseFingerprint='0'*64), 'different curation'),
        ]:
            broken=copy.deepcopy(self.proposal);mutate(broken)
            with self.assertRaisesRegex(ScoutCurationError,message):validate_priorities(self.job,seed,broken)
        # A resource with a second category needs another independently chosen priority.
        seed=copy.deepcopy(seed);seed['resources'][0]['categories'].append('new-category')
        with self.assertRaisesRegex(ScoutCurationError,'every resource'):validate_priorities(self.job,seed,self.proposal)

    def test_immutable_revisions_change_approval_without_changing_resources(self):
        before=build_scout_review_seed(self.store,self.job['id'])
        old=latest_priorities(self.store,self.job['id'])
        same=save_priorities(self.store,self.job['id'],self.proposal,reason='Idempotent review')
        self.assertEqual(old['id'],same['id'])
        self.proposal['assignments'][0]['tier']='specialized'
        self.proposal['assignments'][0]['reason']='Review for this narrower program after the general intake.'
        revised=save_priorities(self.store,self.job['id'],self.proposal,reason='Reviewer changed assessment')
        current=self.store.get_scout_curation_job(self.job['id'])
        self.assertNotEqual(review_fingerprint(self.job),review_fingerprint(current))
        self.assertFalse(review_handoff(current,self.store.list_scout_curation_progress(self.job['id']))['readyForSave'])
        after=build_scout_review_seed(self.store,self.job['id'])
        self.assertEqual(before['resources'],after['resources'])
        with self.store.connect() as c:
            saved=json.loads(c.execute('SELECT proposal_json FROM scout_review_priority_revisions WHERE id=?',(old['id'],)).fetchone()[0])
        self.assertEqual('start',saved['assignments'][0]['tier'])
        with self.assertRaisesRegex(ScoutCurationError,'older revision'):save_priorities(self.store,self.job['id'],saved,reason='Cannot silently roll back')
        self.assertIn(revised['proposalSha256'],build_scout_review_file(self.store,self.job['id']).content.decode())

    def test_missing_or_stale_priorities_block_review_completion(self):
        with self.store.connect() as c:c.execute('DELETE FROM scout_review_priority_revisions WHERE job_id=?',(self.job['id'],))
        current=self.store.get_scout_curation_job(self.job['id'])
        with self.assertRaisesRegex(ScoutCurationError,'per-category review priorities'):require_review_ready(self.store,current)
        self.fixture.save_test_priorities(self.job['id'])
        nav=latest_navigation(self.store,self.job['id'])['proposal']
        nav['groups'][0]['definition']+=' Explicit eligibility applies.'
        save_navigation(self.store,self.job['id'],nav,reason='Clarify definition')
        with self.assertRaisesRegex(ScoutCurationError,'different curation or navigation'):
            require_review_ready(self.store,self.store.get_scout_curation_job(self.job['id']))


if __name__=='__main__':unittest.main()
