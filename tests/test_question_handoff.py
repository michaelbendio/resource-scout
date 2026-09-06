import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from resource_research_agent.storage import ResearchStore
from resource_research_agent.scout_improvement import ImprovementWorkflow
from resource_research_agent.scout_maintenance import MaintenanceWorkflow
from resource_research_agent.improvement_packages import ImprovementError, read_package, write_package
from resource_research_agent.improvement_cli import run_improvement_command
from resource_research_agent.cli import parser
from tests.test_scout_improvement import fixture_package, result_for
from tests.test_scout_maintenance import result_for as maintenance_result


class QuestionHandoffTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.store=ResearchStore(Path(self.temp.name)/'scout.sqlite3')
        self.data=fixture_package();self.assets={'pdfs/guide.pdf':b'%PDF-1.4 synthetic QA'}
        self.payload=write_package(self.data,self.assets)

    def prepare(self, maintenance=False):
        flow=MaintenanceWorkflow(self.store) if maintenance else ImprovementWorkflow(self.store)
        state=flow.prepare(self.payload,'Test TSO',['r1'],[],run_name='QA',historical=True) if maintenance else flow.prepare(self.payload,'Test TSO',['r1'],historical=True)
        pid=state['id']
        while assignment:=flow.next_assignment(pid):
            result=maintenance_result(assignment,'inconclusive') if maintenance else result_for(assignment)
            if not maintenance and assignment['stage'].startswith('audit:'):
                result['findings']=[{'id':'rule','field':'informationText','severity':'material','summary':'Which intake rule applies?'}]
            if not maintenance and assignment['stage']=='reconcile':
                for resolution in result['resolutions']:
                    resolution.update(status='needs-review',reason='Official pages disagree.')
            flow.submit(pid,assignment['stage'],result)
        return flow,pid

    def connect(self,flow,pid,payload=None):
        return flow.connect_latest(pid,flow.view(pid)['revision'],payload or self.payload,'Test TSO')

    def assert_service_unchanged(self,package):
        self.assertEqual(self.assets,package['assets'])
        self.assertEqual(len(self.data['resources']),len(package['data']['resources']))
        for before in self.data['resources']:
            after=deepcopy(package['resources'][before['id']]);after.pop('openQuestions',None)
            self.assertEqual(before,after)  # Includes Verified, resource clocks and unknown extension data.

    def test_unreviewed_writing_questions_export_without_curating_proposals(self):
        flow,pid=self.prepare()
        with self.assertRaisesRegex(ImprovementError,'Reconnect'):flow.prepare_question_export(pid,flow.view(pid)['revision'])
        self.connect(flow,pid)
        with self.assertRaisesRegex(ImprovementError,'No curated'):flow.prepare_export(pid,flow.view(pid)['revision'])
        export=flow.prepare_question_export(pid,flow.view(pid)['revision'])
        again=flow.prepare_question_export(pid,flow.view(pid)['revision']);self.assertEqual(export['exportId'],again['exportId'])
        payload=flow.export_bytes(pid,export['exportId']);package=read_package(payload)
        self.assert_service_unchanged(package)
        self.assertEqual(1,len(package['resources']['r1']['openQuestions'])) # Same question from three auditors.
        with self.assertRaises(ImprovementError):flow.acknowledge_export(pid,flow.view(pid)['revision'],export['exportId'],'wrong hash')
        view=flow.acknowledge_export(pid,flow.view(pid)['revision'],export['exportId'],export['manifest']['packageSha256'])
        self.assertTrue(view['requiresReconnection']);self.assertFalse(view['resources'][0]['packaged']);self.assertIsNone(view['resources'][0]['review'])
        self.connect(flow,pid,payload)
        with self.assertRaisesRegex(ImprovementError,'No new questions'):flow.prepare_question_export(pid,flow.view(pid)['revision'])

    def test_maintenance_keep_and_inconclusive_questions_survive(self):
        flow,pid=self.prepare(maintenance=True);self.connect(flow,pid)
        row=flow.view(pid)['items'][0]
        flow.review(pid,flow.view(pid)['revision'],row['taskId'],row['id'],'keep',{},'QA','Keep the existing fields; let office curator answer the question.')
        export=flow.prepare_question_export(pid,flow.view(pid)['revision'])
        package=read_package(flow.export_bytes(pid,export['exportId']));self.assert_service_unchanged(package)
        self.assertTrue(package['resources']['r1']['openQuestions'])
        view=flow.acknowledge_export(pid,flow.view(pid)['revision'],export['exportId'],export['manifest']['packageSha256'])
        self.assertFalse(view['items'][0]['saved']);self.assertEqual('keep',view['items'][0]['review']['decision'])

    def test_stale_review_and_removed_resource_block_handoff(self):
        flow,pid=self.prepare();self.connect(flow,pid)
        export=flow.prepare_question_export(pid,flow.view(pid)['revision'])
        flow.review(pid,flow.view(pid)['revision'],'r1','declined',{},'QA','Changed review')
        with self.assertRaisesRegex(ImprovementError,'changed after question export'):
            flow.acknowledge_export(pid,flow.view(pid)['revision'],export['exportId'],export['manifest']['packageSha256'])
        removed=deepcopy(self.data);removed['resources']=removed['resources'][1:];removed['packageVersion']+=1
        self.connect(flow,pid,write_package(removed,self.assets))
        with self.assertRaisesRegex(ImprovementError,'absent'):flow.prepare_question_export(pid,flow.view(pid)['revision'])

    def test_operator_command_writes_verified_bytes_and_retains_review(self):
        flow,pid=self.prepare();self.connect(flow,pid)
        output=Path(self.temp.name)/'questions.zip'
        args=parser().parse_args(['improve','export',str(pid),'--revision',str(flow.view(pid)['revision']),'--output',str(output),'--questions-only'])
        export=run_improvement_command(self.store,args)
        self.assertEqual(export['manifest']['packageSha256'],read_package(output.read_bytes())['sha256'])
        self.assertFalse(flow.view(pid)['resources'][0]['packaged'])
        with self.assertRaisesRegex(ValueError,'existing package'):run_improvement_command(self.store,args)
