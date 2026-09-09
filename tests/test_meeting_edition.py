"""Synthetic deadline-delivery tests; no real research or human decisions."""
import json
import re
import tempfile
import unittest
import sqlite3
from copy import deepcopy
from pathlib import Path

from resource_research_agent.improvement_packages import ImprovementError, read_package, write_package
from resource_research_agent.meeting_edition import build_meeting_edition, ReadOnlyMaintenanceWorkflow, render_meeting_overview
from resource_research_agent.open_questions import make_questions
from resource_research_agent.scout_maintenance import MaintenanceWorkflow
from resource_research_agent.storage import ResearchStore
from tests.test_scout_improvement import fixture_package
from tests.test_scout_maintenance import result_for


class MeetingEditionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.flow = MaintenanceWorkflow(ResearchStore(Path(self.temp.name)/'qa.sqlite3'))
        self.data = fixture_package()
        q = make_questions([{'question':'Original question','explanation':'Synthetic original evidence'}], {'kind':'synthetic-QA'})[0]
        q.update(status='resolved',resolution='Synthetic curator answer',history=[{
            'changedAt':'2026-09-02T00:00:00Z','status':'resolved','resolution':'Synthetic curator answer'}])
        self.data['resources'][0]['openQuestions'] = [q]
        self.assets = {'pdfs/guide.pdf':b'%PDF-1.4 synthetic exact attachment'}
        self.payload = write_package(self.data,self.assets)
        self.pid = self.flow.prepare(self.payload,'Test TSO',['r1'],['food'],run_name='Synthetic meeting QA')['id']

    def finish(self, pid=None, task=None, status='moved'):
        pid = pid or self.pid
        while a := self.flow.next_assignment(pid,task_id=task):
            self.flow.submit(pid,a['stage'],result_for(a,status=status))

    def build(self, projects=None, stamp='2026-09-09T00:00:00Z'):
        return build_meeting_edition(self.flow,
            projects or [(self.pid,self.flow.view(self.pid)['revision'])],
            location_name='TestV2',created_at=stamp)

    def test_partial_snapshot_preserves_baseline_answers_assets_and_does_not_approve(self):
        self.finish(task='recheck:r1')
        # A drafted discovery is deliberately not allowed into the delivery.
        a=self.flow.next_assignment(self.pid,task_id='discovery:food')
        self.flow.submit(self.pid,a['stage'],result_for(a))
        before=deepcopy(self.flow.view(self.pid)); first=self.build()
        self.assertEqual(first,self.build())
        self.assertEqual(before,self.flow.view(self.pid))
        data=read_package(first.package)['data']; rows={r['id']:r for r in data['resources']}
        self.assertEqual({'r1','r2'},set(rows))
        self.assertEqual('New address',rows['r1']['address'])
        self.assertEqual(self.data['resources'][1],rows['r2'])
        self.assertEqual(self.data['resources'][0]['openQuestions'],rows['r1']['openQuestions'])
        self.assertEqual('08/26',rows['r1']['verifiedOn'])
        self.assertEqual(self.assets,read_package(first.package)['assets'])
        self.assertEqual(1,first.manifest['counts']['pendingTasks'])
        self.assertEqual(0,first.manifest['humanApprovalsCreated'])
        self.assertTrue(all(r['review'] is None for r in before['items']))
        document=first.review.content.decode()
        seed=json.loads(re.search(r'<script id="seed-data" type="application/json">(.*?)</script>',document,re.S).group(1))
        self.assertEqual(data['resources'],seed['resources'])
        self.assertIn('research tasks remain unfinished',document)
        self.assertIn('if(!await getPDF(path))',document)

    def test_uncertain_closure_is_held_without_deleting_or_rewriting_original(self):
        self.finish(task='recheck:r1',status='possibly-closed')
        self.finish(task='discovery:food')
        edition=self.build(); data=read_package(edition.package)['data']
        original=next(r for r in data['resources'] if r['id']=='r1')
        for key,value in self.data['resources'][0].items():
            if key not in ('lastModified','openQuestions'):self.assertEqual(value,original[key])
        self.assertEqual(self.data['resources'][0]['openQuestions'][0],original['openQuestions'][0])
        self.assertEqual('open',original['openQuestions'][1]['status'])
        self.assertEqual('held',original['scoutResearch']['reviewStatus'])
        self.assertEqual(1,edition.manifest['counts']['heldProposals'])
        self.assertEqual(1,edition.manifest['counts']['newProposals'])
        self.assertEqual(self.data.get('deletionRequests',[]),data.get('deletionRequests',[]))
        self.assertEqual('possibly-closed',edition.manifest['heldProposals'][0]['status'])

    def test_pilot_and_continuation_combine_only_matching_exact_snapshots(self):
        self.finish()
        other=self.flow.prepare(self.payload,'Test TSO',['r2'],[],run_name='Synthetic continuation')['id']
        self.finish(pid=other)
        ids=[(pid,self.flow.view(pid)['revision']) for pid in [self.pid,other]]
        edition=self.build(ids)
        self.assertEqual(2,edition.manifest['counts']['existingWithCompletedProposals'])
        self.assertEqual(1,edition.manifest['counts']['newProposals'])
        self.assertEqual(0,edition.manifest['counts']['pendingTasks'])
        self.assertEqual(2,len(edition.manifest['projects']))
        with self.assertRaisesRegex(ImprovementError,'revision changed'):
            self.build([(self.pid,0)])
        changed=deepcopy(self.data);changed['resources'][1]['name']='New curator name'
        self.flow.connect_latest(other,self.flow.view(other)['revision'],write_package(changed,self.assets),'Test TSO')
        with self.assertRaisesRegex(ImprovementError,'same current office package'):
            self.build([(pid,self.flow.view(pid)['revision']) for pid in [self.pid,other]])

    def test_newer_office_edits_remain_intact_and_conflicting_proposal_is_reported(self):
        self.finish(task='recheck:r1')
        changed=deepcopy(self.data);changed['resources'][0]['address']='Current curator address'
        self.flow.connect_latest(self.pid,self.flow.view(self.pid)['revision'],write_package(changed,self.assets),'Test TSO')
        edition=self.build(); row=read_package(edition.package)['data']['resources'][0]
        self.assertEqual(changed['resources'][0],row)
        self.assertEqual('newer office edits',edition.manifest['heldProposals'][0]['reason'])

    def test_duplicate_completed_identity_is_rejected(self):
        self.finish(task='recheck:r1')
        other=self.flow.prepare(self.payload,'Test TSO',['r1'],[],run_name='Synthetic duplicate scope')['id']
        self.finish(pid=other)
        with self.assertRaisesRegex(ImprovementError,'same resource identity'):
            self.build([(pid,self.flow.view(pid)['revision']) for pid in [self.pid,other]])

    def test_delivery_reader_cannot_write_and_overview_marks_changes(self):
        self.finish(task='recheck:r1')
        reader=ReadOnlyMaintenanceWorkflow(self.flow.store.path)
        view=self.flow.view(self.pid)
        edition=build_meeting_edition(reader,[(self.pid,view['revision'])],
            location_name='TestV2',created_at='2026-09-09T00:00:00Z')
        self.assertEqual(edition,self.build())
        with reader.store.connect() as connection:
            with self.assertRaises(sqlite3.OperationalError):
                connection.execute('DELETE FROM scout_improvement_projects')
        self.assertEqual(view,self.flow.view(self.pid))
        overview=render_meeting_overview(edition,self.data)
        self.assertIn('<strong>New</strong>',overview)
        self.assertIn('Print overview',overview)
        self.assertIn('Print this resource',overview)
        self.assertIn('research-draft ZIP',overview)


if __name__=='__main__':unittest.main()
