"""Synthetic end-to-end editor/research integration, not a live discovery run."""
import json
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from resource_research_agent.frontier_editor import FrontierEditorWorkflow
from resource_research_agent.improvement_packages import ImprovementError, read_package, write_package
from resource_research_agent.scout_maintenance import MaintenanceWorkflow
from resource_research_agent.storage import ResearchStore
from tests.test_scout_improvement import fixture_package
from tests.test_scout_maintenance import result_for
from tests.test_research_execution import settings, response


class FrontierEditorTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.store=ResearchStore(Path(self.tmp.name)/'qa.db');self.flow=FrontierEditorWorkflow(self.store)
        data=fixture_package();data['resources'][1]['openQuestions']=[{'id':'q','question':'Which office?',
          'explanation':'Synthetic question','status':'resolved','resolution':'Original exact answer','history':[]}]
        self.original=write_package(data,{'pdfs/guide.pdf':b'%PDF original bytes'})
        self.config={'name':'Synthetic discovery','editor':'Synthetic frontier editor','model':None,'settings':{},
                     'sourceScope':'full','categoryIds':['food'],'authorityNote':'Synthetic contract QA, no human verification'}
        self.project=self.flow.prepare(self.original,'Test TSO',self.config)['id']
        self.receipt={'editor':self.config['editor'],'model':None,'settings':{},'contextId':'synthetic-editor', 'notes':'Synthetic fixture only'}

    def result(self,stage):
        packet=self.flow.packet(self.project,stage)
        return {'assignmentSha256':packet['assignmentSha256'],'decisions':[
            {'resourceId':r['id'],'disposition':'retain','targetResourceIds':[r['id']],
             'reason':'Synthetic useful route','evidence':['Saved fixture fields'],'fields':{},'questions':[]}
            for r in packet['package']['resources']]}

    def test_finished_package_enters_final_editing_and_survives_restart(self):
        early_project=self.project
        self.project=self.flow.prepare_final(self.original,'Test TSO',self.config)['id']
        self.assertNotEqual(early_project,self.project)
        self.assertEqual('early-editor',self.flow.status(early_project)['stage'])
        self.flow=FrontierEditorWorkflow(ResearchStore(self.store.path))
        status=self.flow.prepare_final(self.original,'Test TSO',self.config)
        self.assertEqual(self.project,status['id'])
        self.assertEqual('final-editor',status['stage'])
        self.assertIsNone(status['researchProjectId'])
        packet=self.flow.packet(self.project,'final')
        with self.store.connect() as c:
            self.assertEqual(self.original,self.flow.learning._bytes(c,packet['sourceSha256'],'resource-package'))
            row,_=self.flow._row(c,self.project)
            self.assertIsNone(row['early_reply'])
        with self.assertRaisesRegex(ImprovementError,'no early review'):
            self.flow.packet(self.project,'early')
        with self.assertRaisesRegex(ImprovementError,'separate research'):
            self.flow.start_research(self.project,settings())
        with self.assertRaises(ImprovementError):self.flow.export(self.project)
        result=self.result('final')
        result['decisions'][0]['fields']={'name':'Useful combined program'}
        result['decisions'][1].update(disposition='combine',targetResourceIds=['r1'])
        self.flow.submit(self.project,'final',json.dumps(result),self.receipt)
        exported=self.flow.export(self.project)
        p=read_package(exported['package'])
        self.assertEqual(['r1'],list(p['resources']))
        self.assertEqual('Useful combined program',p['resources']['r1']['name'])
        self.assertEqual('Original exact answer',p['resources']['r1']['openQuestions'][0]['resolution'])
        self.assertEqual(b'%PDF original bytes',p['assets']['pdfs/guide.pdf'])
        self.assertEqual([],p['data']['deletions'])
        self.assertEqual(0,exported['manifest']['humanApprovalsCreated'])
        self.assertIsNone(exported['manifest']['researchCoverage'])
        self.assertEqual('complete',self.flow.prepare_final(self.original,'Test TSO',self.config)['stage'])
        self.assertEqual(packet,self.flow.packet(self.project,'final'))
        with self.store.connect() as c:
            self.assertEqual(2,c.execute("SELECT count(*) FROM scout_learning_records WHERE kind='observation'").fetchone()[0])

    def test_finished_package_keeps_declared_partial_coverage(self):
        data=read_package(self.original)['data']
        coverage={'sourceScope':'partial','remainingGaps':['Only one category was checked']}
        data['scoutDiscoveryCoverage']=coverage
        source=write_package(data,{'pdfs/guide.pdf':b'%PDF original bytes'})
        self.project=self.flow.prepare_final(source,'Test TSO',{**self.config,'sourceScope':'partial'})['id']
        self.flow.submit(self.project,'final',json.dumps(self.result('final')),self.receipt)
        exported=self.flow.export(self.project)
        self.assertEqual('partial',exported['manifest']['sourceScope'])
        self.assertEqual(coverage,exported['manifest']['researchCoverage'])
        self.assertEqual(coverage,read_package(exported['package'])['data']['scoutDiscoveryCoverage'])

    def test_finished_package_rejects_wrong_office_and_unknown_categories(self):
        with self.assertRaisesRegex(ImprovementError,'office mismatch'):
            self.flow.prepare_final(self.original,'Another TSO',self.config)
        with self.assertRaisesRegex(ImprovementError,'Unknown research category'):
            self.flow.prepare_final(self.original,'Test TSO',{**self.config,'categoryIds':['unknown']})

    def test_cli_starts_finished_package_at_final_stage(self):
        from resource_research_agent.cli import parser
        from resource_research_agent.editor_cli import run_editor_command
        package=Path(self.tmp.name)/'draft.zip';package.write_bytes(self.original)
        config=Path(self.tmp.name)/'editor.json';config.write_text(json.dumps(self.config))
        args=parser().parse_args(['editor','prepare-final',str(package),str(config),'--office','Test TSO'])
        status=run_editor_command(self.store,args)
        self.assertEqual('final-editor',status['stage'])
        self.assertIsNone(status['researchProjectId'])

    def test_full_sequence_reuses_research_and_preserves_answers_assets(self):
        with self.assertRaises(ImprovementError):self.flow.start_research(self.project)
        early=self.result('early');early['decisions'][1].update(disposition='combine',targetResourceIds=['r1'])
        saved=self.flow.submit(self.project,'early',json.dumps(early),self.receipt)
        self.assertEqual(saved,self.flow.submit(self.project,'early',json.dumps(early),self.receipt))
        early_export=self.flow.export(self.project,'early')
        p=read_package(early_export['package']);self.assertEqual(['r1'],list(p['resources']))
        self.assertEqual('Original exact answer',p['resources']['r1']['openQuestions'][0]['resolution'])
        self.assertEqual([],p['data']['deletions']);self.assertEqual([],p['data']['deletionRequests'])
        research=self.flow.start_research(self.project,settings())
        self.assertEqual(research,self.flow.start_research(self.project))
        with self.assertRaises(ImprovementError):self.flow.finish_research(self.project)
        m=MaintenanceWorkflow(self.store)
        while a:=m.next_assignment(research['researchProjectId']):m.submit(research['researchProjectId'],a['stage'],response(a))
        self.flow=FrontierEditorWorkflow(ResearchStore(self.store.path))
        packet=self.flow.finish_research(self.project);self.assertEqual(packet,self.flow.finish_research(self.project))
        result=self.result('final')
        self.flow.submit(self.project,'final',json.dumps(result),self.receipt)
        export=self.flow.export(self.project);p=read_package(export['package'])
        self.assertEqual('complete',self.flow.status(self.project)['stage'])
        self.assertEqual(b'%PDF original bytes',p['assets']['pdfs/guide.pdf'])
        self.assertEqual('Original exact answer',p['resources']['r1']['openQuestions'][0]['resolution'])
        self.assertIn(b'scoutPreviewAssetsReady',export['html']);self.assertIn(b'Original exact answer',export['html'])
        self.assertEqual(0,export['manifest']['humanApprovalsCreated'])
        with self.store.connect() as c:
            self.assertGreater(c.execute("SELECT count(*) FROM scout_learning_records WHERE kind='observation'").fetchone()[0],0)
            self.assertEqual(self.original,self.flow.learning._bytes(c,self.flow.learning.inspect(self.project)['sourceSha256'],'resource-package'))

    def test_invalid_edits_identity_and_receipts_do_not_advance(self):
        original=self.result('early')
        for mutate in (lambda x:x['decisions'].pop(),lambda x:x['decisions'][0].update(fields={'verifiedOn':'09/26'}),
                       lambda x:x['decisions'][0].update(targetResourceIds=['missing']),lambda x:x.update(assignmentSha256='bad')):
            bad=deepcopy(original);mutate(bad)
            with self.assertRaises(ImprovementError):self.flow.submit(self.project,'early',json.dumps(bad),self.receipt)
        with self.assertRaises(ImprovementError):self.flow.submit(self.project,'early',json.dumps(original),{**self.receipt,'editor':'Other'})
        self.assertEqual('early-editor',self.flow.status(self.project)['stage'])

    def test_conflicting_question_histories_cannot_be_silently_combined(self):
        from resource_research_agent.improvement_packages import read_package
        data=read_package(self.original)['data'];data['resources'][0]['openQuestions']=deepcopy(data['resources'][1]['openQuestions'])
        data['resources'][0]['openQuestions'][0]['resolution']='Different exact answer'
        self.project=self.flow.prepare(write_package(data,{'pdfs/guide.pdf':b'%PDF original bytes'}),'Test TSO',self.config)['id']
        result=self.result('early');result['decisions'][1].update(disposition='combine',targetResourceIds=['r1'])
        with self.assertRaisesRegex(ImprovementError,'conflicting question'):self.flow.submit(self.project,'early',json.dumps(result),self.receipt)

    def test_restart_after_research_creation_does_not_duplicate_the_run(self):
        from unittest.mock import patch
        early=self.result('early');self.flow.submit(self.project,'early',json.dumps(early),self.receipt)
        prepare=MaintenanceWorkflow.prepare
        def interrupted(flow,*args,**kwargs):
            prepare(flow,*args,**kwargs)
            raise RuntimeError('Interrupted after durable research preparation')
        with patch.object(MaintenanceWorkflow,'prepare',interrupted):
            with self.assertRaises(RuntimeError):self.flow.start_research(self.project,settings())
        with patch('resource_research_agent.frontier_editor.write_package',side_effect=AssertionError('Must reuse sealed bytes')):
            saved=self.flow.start_research(self.project)
        with self.store.connect() as c:self.assertEqual(1,c.execute('SELECT count(*) FROM scout_improvement_projects').fetchone()[0])
        with self.assertRaises(ImprovementError):self.flow.start_research(self.project,settings(rate=1))
        self.assertEqual(saved,self.flow.start_research(self.project))

    def test_final_fields_are_validated_without_invented_curation(self):
        from resource_research_agent.improvement_packages import next_timestamp
        packet=self.flow.packet(self.project,'early');packet['stage']='final'
        result=self.result('early');project=self.flow.learning.inspect(self.project)
        stamp=next_timestamp(packet['package']['resources'])
        for changes in ({'verifiedOn':'09/26'},{'categories':['invented']},{'forGroups':['invented']},
                        {'informationSections':{'programsAndServices':'Missing four sections'}}):
            bad=deepcopy(result);bad['decisions'][0]['fields']=changes
            with self.assertRaises(ValueError):self.flow._apply(project,packet,bad,stamp)
        result['decisions'][0]['fields']={'name':'Short useful title','forGroups':[]}
        result['decisions'][1].update(disposition='reserve',targetResourceIds=[])
        data=self.flow._apply(project,packet,result,stamp)
        self.assertEqual([],data['forGroups']);self.assertEqual('Short useful title',data['resources'][0]['name'])
        self.assertEqual(packet['package']['resources'][0]['verifiedOn'],data['resources'][0]['verifiedOn'])
        self.assertEqual(packet['package']['changes'],data['changes'])
        self.assertFalse(data['scoutFrontierEditorial']['omissionsAreOfficeDeletions'])

    def test_real_discovery_contract_can_feed_early_editor_before_research(self):
        empty=fixture_package();empty['resources']=[]
        baseline=write_package(empty,{})
        raw=json.dumps({'leads':[{'organization':'Synthetic pantry','program':'Food boxes','website':'https://example.org/',
                                 'leadType':'program','locationOrServiceArea':'Test TSO','whyRelevant':'Possible free food',
                                 'uncertainty':'Eligibility and hours unknown'}]})
        a=self.flow.prepare_leads(baseline,raw,'Test TSO','food',self.config)
        self.assertEqual(a,self.flow.prepare_leads(baseline,raw,'Test TSO','food',self.config))
        packet=self.flow.packet(a['id'],'early');resource=packet['package']['resources'][0]
        self.assertTrue(resource['id'].startswith('scout-lead:'));self.assertNotIn('verifiedOn',resource)
        self.assertEqual('Eligibility and hours unknown',resource['scoutLeadEvidence']['lead']['uncertainty'])
        self.assertIsNone(a['researchProjectId'])

    def test_finished_bounded_research_keeps_coverage_gaps_in_export(self):
        self.flow.submit(self.project,'early',json.dumps(self.result('early')),self.receipt)
        pid=self.flow.start_research(self.project,settings())['researchProjectId']
        m=MaintenanceWorkflow(self.store)
        while a:=m.next_assignment(pid):
            r=response(a)
            r['executionReceipt']['coverageNotes']='One limited source scan; not exhaustive.'
            r['executionReceipt']['remainingGaps']=['Other local providers have not been searched.']
            m.submit(pid,a['stage'],r)
        packet=self.flow.finish_research(self.project)
        coverage=packet['package']['scoutDiscoveryCoverage']
        self.assertEqual(pid,coverage['researchProjectId'])
        self.assertTrue(coverage['assignments'])
        self.assertTrue(all(x['remainingGaps'] for x in coverage['assignments']))
        self.flow.submit(self.project,'final',json.dumps(self.result('final')),self.receipt)
        self.flow=FrontierEditorWorkflow(ResearchStore(self.store.path))
        exported=self.flow.export(self.project)
        self.assertEqual(coverage,exported['manifest']['researchCoverage'])
        self.assertEqual(coverage,read_package(exported['package'])['data']['scoutDiscoveryCoverage'])
        self.assertEqual(packet,self.flow.finish_research(self.project))
