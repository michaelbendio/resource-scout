"""Synthetic review-delivery checks; no actual provider or curator approvals."""
import json
import re
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from resource_research_agent.improvement_packages import ImprovementError, write_package
from resource_research_agent.maintenance_review import build_maintenance_review_file
from resource_research_agent.open_questions import make_questions
from resource_research_agent.scout_maintenance import MaintenanceWorkflow
from resource_research_agent.storage import ResearchStore
from tests.test_scout_improvement import fixture_package
from tests.test_scout_maintenance import result_for


class MaintenanceReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.flow = MaintenanceWorkflow(ResearchStore(Path(self.temp.name) / 'qa.sqlite3'))
        self.data = fixture_package()
        old = make_questions([{'question':'Original question', 'explanation':'Original evidence'}], {'kind':'synthetic-QA'})[0]
        old.update(status='resolved',resolution='Synthetic curator answer',history=[{
            'changedAt':'2026-09-02T00:00:00Z','status':'resolved','resolution':'Synthetic curator answer'}])
        self.data['resources'][0]['openQuestions'] = [old]
        self.assets = {'pdfs/guide.pdf':b'%PDF-1.4 synthetic exact attachment'}
        self.payload = write_package(self.data,self.assets)
        self.pid = self.flow.prepare(self.payload,'Test TSO',['r1'],['food'],run_name='Synthetic delivery QA')['id']

    def finish(self):
        while assignment := self.flow.next_assignment(self.pid):
            result = result_for(assignment)
            if not assignment['stage'].startswith('audit:'):
                result['items'][0]['questions']=['How does the new intake work?']
            self.flow.submit(self.pid,assignment['stage'],result)

    def build(self, revision=None):
        return build_maintenance_review_file(self.flow,self.pid,
            self.flow.view(self.pid)['revision'] if revision is None else revision,
            location_name='TestV2',created_at='2026-09-08T05:20:00Z')

    def test_draft_preserves_questions_assets_and_identity_without_approvals(self):
        self.finish(); before=deepcopy(self.flow.view(self.pid))
        first=self.build();self.assertEqual(first,self.build())
        document=first.content.decode();seed=json.loads(re.search(
            r'<script id="seed-data" type="application/json">(.*?)</script>',document,re.S).group(1))
        self.assertEqual({'r1','new-pantry'},{r['id'] for r in seed['resources']})
        known=next(r for r in seed['resources'] if r['id']=='r1')
        self.assertEqual(self.data['resources'][0]['openQuestions'][0],known['openQuestions'][0])
        self.assertEqual('open',known['openQuestions'][1]['status'])
        self.assertEqual('New address',known['address'])
        self.assertEqual(self.data['resources'][0]['pdfs'],known['pdfs'])
        self.assertEqual('08/26',known['verifiedOn'])
        self.assertTrue(known['scoutResearch']['curationRequired'])
        self.assertEqual(before,self.flow.view(self.pid))
        self.assertTrue(all(row['review'] is None for row in before['items']))
        self.assertIn('if(!await getPDF(path))',document)
        self.assertIn('window.scoutPreviewAssetsReady',document)
        storage=re.search(r'<meta name="tso-storage-id" content="([^"]+)"',document).group(1)
        artifact=re.search(r'<meta name="scout-review-artifact-id" content="([^"]+)"',document).group(1)
        self.assertEqual(storage,artifact)
        self.assertIn('What did you find out?',document)

    def test_incomplete_and_stale_research_cannot_produce_working_copy(self):
        with self.assertRaisesRegex(ImprovementError,'Finish every'):self.build()
        old=self.flow.view(self.pid)['revision'];self.finish()
        with self.assertRaisesRegex(ImprovementError,'revision changed'):self.build(old)

    def test_newer_office_edits_are_not_silently_replaced(self):
        self.finish(); changed=deepcopy(self.data)
        changed['resources'][0]['address']='New curator address'
        self.flow.connect_latest(self.pid,self.flow.view(self.pid)['revision'],write_package(changed,self.assets),'Test TSO')
        with self.assertRaisesRegex(ImprovementError,'newer office edits'):self.build()

    def test_uncertain_closure_stays_in_decision_workflow(self):
        while assignment := self.flow.next_assignment(self.pid):
            result=result_for(assignment,status='possibly-closed' if assignment['scope']=='recheck' else 'new')
            self.flow.submit(self.pid,assignment['stage'],result)
        with self.assertRaisesRegex(ImprovementError,'Uncertain service status'):self.build()


if __name__=='__main__':unittest.main()
