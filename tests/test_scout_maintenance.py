"""Synthetic maintenance QA: fixtures are not real research or human approvals."""
import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from resource_research_agent.improvement_packages import ImprovementError, read_package, write_package
from resource_research_agent.scout_maintenance import MaintenanceWorkflow
from resource_research_agent.storage import ResearchStore
from tests.test_scout_improvement import fixture_package


def result_for(a, status='moved', *, discovery=True):
    r=deepcopy(a['outputContract']); r['assignmentSha256']=a['assignmentSha256']
    r['evidenceSources']=[{'url':'https://official.example/program-notice','accessedOn':'2026-09-06','excerpt':'Synthetic QA provider notice, not real research: This named program has permanently closed.'}]
    r['researchNotes']='Synthetic QA check of this program and category; not actual external research.'
    if a['stage'].startswith('audit:'):
        r['closureChecks']=[{'itemId':i['id'],'notice':{'sourceIndex':0,'kind':'official-program-closure','program':i['program'],'statement':'This named program has permanently closed.'}} for i in a['primaryResult']['items'] if i['status']=='possibly-closed']
    else:
        known=a['scope']=='recheck'
        item={'id':a['target']['id'] if known else 'new-pantry', 'program':a['target']['name'] if known else 'New pantry',
              'status':status if known else 'new', 'summary':'Synthetic QA finding.',
              'fields':{'address':'New address'} if known and status not in ('current','inconclusive','identity','possibly-closed') else {},
              'evidence':[0], 'closureEvidence':[{'sourceIndex':0,'kind':'official-program-closure','program':a['target']['name'],'statement':'This named program has permanently closed.'}] if status=='possibly-closed' else [],
              'questions':['Call to resolve the named program status.'] if status in ('inconclusive','identity') else [],
              'nextCheckOn':'2026-10-06','lastEvidenceOfOperationOn':'' if status=='possibly-closed' else '2026-09-06'}
        if not known:
            item['fields']={'name':'New pantry','description':'Free groceries in Test County.','website':'https://new-pantry.example/',
              'categories':[a['target']['id']], 'forGroups':[], 'categoryFilters':{},
              'informationSections':{'programsAndServices':'Groceries.','eligibilityRequirements':'Call for eligibility.','howToBestConnect':'Call before visiting.','access':'Test County.','importantInformationToKnow':'Food varies.'}}
        r['items']=[item] if known or discovery else []
    return r


class MaintenanceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.store=ResearchStore(Path(self.temp.name)/'test.sqlite3'); self.flow=MaintenanceWorkflow(self.store)
        self.data=fixture_package(); self.assets={'pdfs/guide.pdf':b'%PDF-1.4 Synthetic exact bytes'}
        self.payload=write_package(self.data,self.assets)
        self.pid=self.flow.prepare(self.payload,'Test TSO',['r1'],['food'],run_name='Synthetic QA',historical=True)['id']
    def view(self): return self.flow.view(self.pid)
    def connect(self,data=None): return self.flow.connect_latest(self.pid,self.view()['revision'],write_package(data or self.data,self.assets),'Test TSO')
    def finish(self,status='moved',task=None,transform=None):
        while a:=self.flow.next_assignment(self.pid,task_id=task):
            r=result_for(a,status)
            if transform: transform(a,r)
            self.flow.submit(self.pid,a['stage'],r)
        return self.view()
    def review(self,ident='r1',decision='accept',**kwargs):
        row=next(r for r in self.view()['items'] if r['id']==ident)
        return self.flow.review(self.pid,self.view()['revision'],row['taskId'],ident,decision,
            kwargs.pop('choices',{k:'proposed' for k in row['comparison']}),'QA reviewer; not Michael',
            kwargs.pop('note','Synthetic QA rationale: service scope and classifications remain appropriate.'),**kwargs)
    def export(self): return self.flow.prepare_export(self.pid,self.view()['revision'])
    def package(self,e): return read_package(self.flow.export_bytes(self.pid,e['exportId']))

    def test_sealed_assignments_restart_scope_and_separate_coverage(self):
        a=self.flow.next_assignment(self.pid)
        self.assertEqual(a,MaintenanceWorkflow(self.store).next_assignment(self.pid))
        self.assertIsNone(self.flow.next_assignment(self.pid,researcher='ChatGPT'))
        r=result_for(a); self.flow.submit(self.pid,'primary',r)
        self.assertEqual('audit:ChatGPT',self.flow.next_assignment(self.pid)['stage'])
        with self.assertRaises(ImprovementError): self.flow.submit(self.pid,'primary',{**r,'researchNotes':'changed'})
        self.finish(task='recheck:r1')
        self.assertEqual({'selected':1,'completed':1},self.view()['coverage']['recheck'])
        self.assertEqual({'selected':1,'completed':0},self.view()['coverage']['discovery'])
        self.assertEqual(2,self.view()['coverage']['officeResources'])
        self.assertEqual(self.view(),MaintenanceWorkflow(self.store).view(self.pid))

    def test_moved_update_preserves_ids_pdfs_local_notes_human_verification_and_other_resource(self):
        self.finish(task='recheck:r1'); self.connect(); self.review(); e=self.export(); out=self.package(e)
        r=out['resources']['r1']; self.assertEqual('New address',r['address'])
        for key,value in self.data['resources'][0].items():
            if key not in ('address','lastModified'): self.assertEqual(value,r[key],key)
        self.assertEqual(self.data['resources'][1],out['resources']['r2'])
        self.assertEqual(self.assets,out['assets']); self.assertEqual(self.data['futureField'],out['data']['futureField'])
        self.assertEqual(11,out['data']['packageVersion']); self.assertEqual(0,e['manifest']['coverage']['discovery']['completed'])

    def test_partial_export_repeat_cancellation_and_acknowledgment(self):
        self.finish(task='recheck:r1'); self.connect(); self.review(); e=self.export()
        self.assertEqual(e['exportId'],self.export()['exportId']); self.assertFalse(self.view()['items'][0]['saved'])
        with self.assertRaises(ImprovementError): self.flow.acknowledge_export(self.pid,self.view()['revision'],e['exportId'],'wrong')
        self.flow.acknowledge_export(self.pid,self.view()['revision'],e['exportId'],e['manifest']['packageSha256'])
        self.assertTrue(self.view()['requiresReconnection']); self.assertTrue(self.view()['items'][0]['saved'])
        with self.assertRaises(ImprovementError): self.export()
        self.flow.acknowledge_export(self.pid,self.view()['revision'],e['exportId'],e['manifest']['packageSha256'])
        self.assertIsNotNone(self.flow.next_assignment(self.pid,task_id='discovery:food'))

    def test_current_inconclusive_and_identity_are_observations_not_deletions(self):
        for status in ('current','inconclusive','identity'):
            with self.subTest(status=status):
                self.pid=self.flow.prepare(self.payload,'Test TSO',['r1'],[],run_name=status,historical=True)['id']
                self.finish(status);self.connect()
                with self.assertRaises(ImprovementError):self.review(decision='retire')
                with self.assertRaises(ImprovementError):self.review()
                self.review(decision='keep')
                with self.assertRaises(ImprovementError):self.export()

    def test_paused_renamed_reopened_known_records_keep_identity(self):
        for status in ('paused','renamed','reopened'):
            self.pid=self.flow.prepare(self.payload,'Test TSO',['r1'],[],run_name=status,historical=True)['id']
            self.finish(status);self.connect();self.review();out=self.package(self.export())
            self.assertEqual({'r1','r2'},set(out['resources']));self.assertFalse(out['data']['deletions'])

    def test_closure_needs_evidence_and_all_independent_checks(self):
        a=self.flow.next_assignment(self.pid);r=result_for(a,'possibly-closed');r['items'][0]['closureEvidence']=[]
        with self.assertRaisesRegex(ImprovementError,'explicit official evidence'):self.flow.submit(self.pid,'primary',r)
        r=result_for(a,'possibly-closed');self.flow.submit(self.pid,'primary',r)
        for name in ('ChatGPT','Grok','Perplexity'):
            a=self.flow.next_assignment(self.pid,researcher=name,task_id='recheck:r1');r=result_for(a,'possibly-closed');r['closureChecks']=[]
            self.flow.submit(self.pid,a['stage'],r)
        a=self.flow.next_assignment(self.pid,task_id='recheck:r1')
        with self.assertRaisesRegex(ImprovementError,'every independent audit'):self.flow.submit(self.pid,'reconcile',result_for(a,'possibly-closed'))

    def test_corroborated_closure_exports_only_pending_deletion_request(self):
        self.finish('possibly-closed',task='recheck:r1');self.connect();self.review(decision='retire');out=self.package(self.export())
        self.assertEqual(self.data['resources'],out['data']['resources'])
        self.assertFalse(out['data']['deletions']);self.assertEqual('r1',out['data']['deletionRequests'][0]['targetId'])

    def test_later_human_edits_conflict_and_unrelated_fields_survive(self):
        self.finish(task='recheck:r1');changed=deepcopy(self.data);changed['packageVersion']+=1
        changed['resources'][0].update(address='Human address',phone='555-0999',localKnowledge={'contact':'Ana'})
        self.connect(changed);row=self.view()['items'][0];self.assertTrue(row['comparison']['address']['conflict'])
        with self.assertRaises(ImprovementError):self.review(note='')
        self.review(note='QA: compared the later local address with the dated official move notice. Keep current classifications.')
        out=self.package(self.export());self.assertEqual('555-0999',out['resources']['r1']['phone']);self.assertEqual({'contact':'Ana'},out['resources']['r1']['localKnowledge'])

    def test_new_connection_invalidates_acceptance_and_old_ack(self):
        self.finish(task='recheck:r1');self.connect();self.review();e=self.export()
        changed=deepcopy(self.data);changed['packageVersion']+=1;changed['resources'][0]['address']='Later edit'
        self.connect(changed);self.assertIsNone(self.view()['items'][0]['review'])
        with self.assertRaises(ImprovementError):self.export()
        with self.assertRaises(ImprovementError):self.flow.acknowledge_export(self.pid,self.view()['revision'],e['exportId'],e['manifest']['packageSha256'])

    def test_deleted_resource_cannot_be_restored(self):
        self.finish(task='recheck:r1');changed=deepcopy(self.data);changed['packageVersion']+=1
        changed['resources']=changed['resources'][1:];changed['deletions']=[{'kind':'resource','targetId':'r1','label':'Test pantry r1'}]
        self.connect(changed)
        with self.assertRaises(ImprovementError):self.review()

    def test_new_addition_has_five_sections_no_invented_verification_and_roundtrip(self):
        self.finish(task='discovery:food');self.connect();self.review('new-pantry');out=self.package(self.export())
        added=next(r for rid,r in out['resources'].items() if rid not in ('r1','r2'))
        self.assertEqual(3,len(out['resources']));self.assertNotIn('verifiedOn',added)
        self.assertIn('Programs and Services',added['informationText']);self.assertEqual(['food'],added['categories'])

    def test_current_and_declined_identity_matches_require_review(self):
        def transform(a,r):
            if not a['stage'].startswith('audit:'):r['items'][0]['fields']['name']='Test pantry r1'
        self.finish(task='discovery:food',transform=transform);self.connect()
        self.assertTrue(self.view()['items'][0]['matches'])
        with self.assertRaises(ImprovementError):self.review('new-pantry')
        self.review('new-pantry',decision='decline')
        self.pid=self.flow.prepare(self.payload,'Test TSO',[],['food'],run_name='Again',historical=True)['id']
        self.finish(transform=transform);self.assertTrue(any(m['identityStatus']=='decline' for m in self.view()['items'][0]['matches']))

    def test_reopening_retired_identity_is_not_exported_as_new(self):
        changed=deepcopy(self.data);changed['deletions']=[{'kind':'resource','targetId':'retired-pantry','label':'New pantry'}]
        self.pid=self.flow.prepare(write_package(changed,self.assets),'Test TSO',[],['food'],run_name='Reopen',historical=True)['id']
        self.finish();self.connect(changed)
        with self.assertRaisesRegex(ImprovementError,'reopening'):self.review('new-pantry',identity_decision='distinct-program')

    def test_empty_discovery_is_completed_search_not_a_checked_office(self):
        def transform(a,r):
            if 'items' in r:r['items']=[]
        self.finish(task='discovery:food',transform=transform)
        self.assertEqual(1,self.view()['coverage']['discovery']['completed']);self.assertEqual(0,self.view()['coverage']['recheck']['completed'])

    def test_review_changed_after_prepare_rejects_ack(self):
        self.finish(task='recheck:r1');self.connect();self.review();e=self.export();self.review(decision='decline')
        with self.assertRaisesRegex(ImprovementError,'Review changed'):self.flow.acknowledge_export(self.pid,self.view()['revision'],e['exportId'],e['manifest']['packageSha256'])

    def test_invalid_scope_wrong_office_old_package_revision_and_protected_fields(self):
        with self.assertRaises(ImprovementError):self.flow.prepare(self.payload,'Test TSO',['missing'],[],run_name='bad')
        with self.assertRaises(ImprovementError):self.flow.connect_latest(self.pid,self.view()['revision'],self.payload,'Wrong office')
        with self.assertRaises(ImprovementError):self.flow.connect_latest(self.pid,-1,self.payload,'Test TSO')
        self.connect();older=deepcopy(self.data);older['packageVersion']-=1
        with self.assertRaises(ImprovementError):self.connect(older)
        a=self.flow.next_assignment(self.pid);r=result_for(a);r['items'][0]['fields']['verifiedOn']='09/26'
        with self.assertRaises(ImprovementError):self.flow.submit(self.pid,'primary',r)
        r=result_for(a);r['items'][0]['fields']['forGroups']=['Invented']
        with self.assertRaises(ImprovementError):self.flow.submit(self.pid,'primary',r)

    def test_findings_reconciliation_and_human_resolution(self):
        def transform(a,r):
            if a['stage'].startswith('audit:'):r['findings']=[{'id':'f1','summary':'Eligibility may change group targeting.','severity':'material'}]
            if a['stage']=='reconcile':r['resolutions']=[{'findingId':n+':f1','status':'needs-review','reason':'Office should confirm targeting.'} for n in ('ChatGPT','Grok','Perplexity')]
        self.finish(task='recheck:r1',transform=transform);self.connect()
        with self.assertRaises(ImprovementError):self.review()
        self.review(finding_notes={n+':f1':'QA human confirmed unchanged targeting.' for n in ('ChatGPT','Grok','Perplexity')})
        self.assertTrue(self.export())

    def test_failed_contact_is_not_an_explicit_closure_notice(self):
        a=self.flow.next_assignment(self.pid);r=result_for(a,'possibly-closed')
        r['items'][0]['closureEvidence'][0]['kind']='failed-contact'
        with self.assertRaisesRegex(ImprovementError,'failed contact'):self.flow.submit(self.pid,'primary',r)
        r=result_for(a,'possibly-closed');r['items'][0]['closureEvidence'][0]['statement']='Invented closure words'
        with self.assertRaisesRegex(ImprovementError,'cited source excerpt'):self.flow.submit(self.pid,'primary',r)

    def test_prior_checks_are_history_not_a_new_baseline_or_human_verification(self):
        self.finish('inconclusive',task='recheck:r1');old=self.pid
        self.pid=self.flow.prepare(self.payload,'Test TSO',['r1'],[],run_name='Follow-up',historical=True)['id']
        a=self.flow.next_assignment(self.pid)
        self.assertEqual(old,a['priorChecks'][0]['runId'])
        self.assertEqual('inconclusive',a['priorChecks'][0]['result']['items'][0]['status'])
        self.assertEqual(self.data['resources'][0],a['target'])

    def test_new_match_after_review_invalidates_export(self):
        self.finish(task='discovery:food');self.connect();self.review('new-pantry');original=self.pid
        self.pid=self.flow.prepare(self.payload,'Test TSO',[],['food'],run_name='Another run',historical=True)['id']
        self.finish();self.connect();self.review('new-pantry',decision='decline');self.pid=original
        with self.assertRaisesRegex(ImprovementError,'Identity evidence changed'):self.export()

    def test_http_inspect_prepare_assignment_and_errors(self):
        import threading
        import urllib.request
        from urllib.error import HTTPError
        from resource_research_agent.server import ResearchHTTPServer
        server=ResearchHTTPServer(('127.0.0.1',0),self.store,Path(__file__).resolve().parents[1]/'web')
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        def call(path,body=None):
            req=urllib.request.Request(f'http://127.0.0.1:{server.server_port}'+path,data=body)
            with urllib.request.urlopen(req) as response:return response.read()
        try:
            self.assertIn(b'Maintain the collection',call('/maintenance'))
            self.assertIn(b'confirm-saved',call('/maintenance.js'))
            inspected=json.loads(call('/api/maintenance/inspect',self.payload));self.assertEqual(2,len(inspected['resources']))
            v=json.loads(call('/api/maintenance/prepare?office=Test%20TSO&runName=HTTP&historical=1&resourceId=r1',self.payload))
            a=json.loads(call(f'/api/maintenance/{v["id"]}/next',b'{}'))['assignment'];self.assertEqual('recheck:r1',a['taskId'])
            with self.assertRaises(HTTPError) as caught:call('/api/maintenance/9999')
            caught.exception.close()
        finally:server.shutdown();server.server_close();thread.join()

    def test_cli_prepare_resume_and_export_saved_bytes(self):
        import contextlib,io
        from resource_research_agent.cli import main
        source=Path(self.temp.name)/'source.zip';source.write_bytes(self.payload)
        database=str(Path(self.temp.name)/'test.sqlite3')
        def cli(*args):
            output=io.StringIO()
            with contextlib.redirect_stdout(output):self.assertEqual(0,main(['--database',database,'maintain',*args]))
            return json.loads(output.getvalue())
        project=cli('prepare',str(source),'--office','Test TSO','--run-name','CLI','--resource-id','r1','--historical')
        self.pid=project['id'];a=cli('next',str(self.pid));self.assertEqual(a,cli('next',str(self.pid)))
        self.finish();self.connect();self.review();output=Path(self.temp.name)/'reviewed.zip'
        result=cli('export',str(self.pid),'--revision',str(self.view()['revision']),str(output))
        self.assertEqual(result['manifest']['packageSha256'],read_package(output.read_bytes())['sha256'])
        self.assertTrue(self.view()['items'][0]['saved'])

    def test_closure_reconciliation_cannot_switch_to_a_different_program(self):
        while True:
            a=self.flow.next_assignment(self.pid,task_id='recheck:r1')
            if a['stage']=='reconcile':break
            self.flow.submit(self.pid,a['stage'],result_for(a,'possibly-closed'))
        r=result_for(a,'possibly-closed');r['items'][0]['program']='A different program'
        r['items'][0]['closureEvidence'][0]['program']='A different program'
        with self.assertRaisesRegex(ImprovementError,'every independent audit'):self.flow.submit(self.pid,'reconcile',r)

    def test_removed_catalog_term_blocks_old_proposal_without_hiding_the_review(self):
        def transform(a,r):
            if 'items' in r:r['items'][0]['fields']['forGroups']=['Seniors']
        self.finish(task='recheck:r1',transform=transform)
        changed=deepcopy(self.data);changed['packageVersion']+=1;changed['forGroups']=[]
        for resource in changed['resources']:resource['forGroups']=[]
        self.connect(changed);self.assertIn('existing exact',self.view()['items'][0]['blocked'])
        with self.assertRaises(ImprovementError):self.review()
        self.review(decision='decline')

    def test_closing_one_program_does_not_block_a_distinct_program_at_same_provider(self):
        self.finish('possibly-closed',task='recheck:r1');self.connect();self.review(decision='retire')
        self.pid=self.flow.prepare(self.payload,'Test TSO',[],['food'],run_name='Distinct sibling program',historical=True)['id']
        def transform(a,r):
            if 'items' in r:r['items'][0]['fields']['website']='https://example.org/'
        self.finish(transform=transform);self.connect()
        self.assertTrue(any(m['identityStatus']=='retire' for m in self.view()['items'][0]['matches']))
        with self.assertRaises(ImprovementError):self.review('new-pantry')
        self.review('new-pantry',identity_decision='distinct-program',note='QA verified this is a distinct program at the same provider, not the closed program.')
        self.assertTrue(self.export())
