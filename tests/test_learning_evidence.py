"""Synthetic evidence QA. No fixture is a real human decision or provider fact."""
import json
import hashlib
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from resource_research_agent.storage import ResearchStore
from resource_research_agent.learning_evidence import EvidenceLedger
from resource_research_agent.improvement_packages import ImprovementError, write_package, read_package
from resource_research_agent.scout_maintenance import MaintenanceWorkflow
from tests.test_scout_improvement import fixture_package
from tests.test_scout_maintenance import result_for


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.store=ResearchStore(Path(self.tmp.name)/'qa.sqlite3');self.ledger=EvidenceLedger(self.store)
        self.data=fixture_package();self.assets={'pdfs/guide.pdf':b'%PDF-1.4 synthetic bytes'}
        self.base=self.imp(self.data)
    def imp(self,data,scope='full',collection='test',historical=True):
        return self.ledger.import_package(collection,'Test TSO',write_package(data,self.assets),scope=scope,historical=historical)
    def compare(self,before,after,**kwargs):
        return self.ledger.compare(before['id'],after['id'],reviewer='Synthetic curator',lineage_note='Explicit synthetic predecessor',**kwargs)
    def changed(self,**fields):
        data=deepcopy(self.data);data['resources'][0].update(fields);return data
    def manual(self,fields,config='v1'):
        artifact=Path(self.tmp.name)/(config+'.html');artifact.write_text('Synthetic proposal: '+json.dumps(fields))
        artifact_sha=hashlib.sha256(artifact.read_bytes()).hexdigest()
        return self.ledger.record_manual_proposal('test',self.base['id'],resource_id='r1',fields=fields,
            artifact={'path':str(artifact),'sha256':artifact_sha,'deliveredAt':'2026-09-06T12:00:00Z'},
            configuration={'policy':config,'researcher':'Synthetic QA'})

    def test_routine_connection_captures_unknown_scope_and_missing_office_without_rewriting(self):
        from resource_research_agent.scout_improvement import ImprovementWorkflow
        from resource_research_agent.scout_classification import ClassificationWorkflow
        data=deepcopy(self.data);data.pop('officeName',None)
        baseline=write_package(data,self.assets)
        for flow in (ImprovementWorkflow(self.store), ClassificationWorkflow(self.store), MaintenanceWorkflow(self.store)):
            if isinstance(flow,MaintenanceWorkflow):
                project=flow.prepare(baseline,'Test TSO',['r1'],[],run_name='Intake test',historical=True)
            else:project=flow.prepare(baseline,'Test TSO',['r1'],historical=True)
            changed=deepcopy(data);changed['resources'][0]['name']='Human-edited title'
            payload=write_package(changed,self.assets)
            connected=flow.connect_latest(project['id'],project['revision'],payload,'Test TSO')
            evidence=connected['intakeEvidence']
            self.assertEqual(1,evidence['observedChanges']);self.assertEqual(0,evidence['linkedAdoptions'])
            report=self.ledger.report(evidence['comparisonId'])
            self.assertTrue(report['historical']);self.assertEqual('unknown',report['afterScope'])
            self.assertEqual('observed-change',report['events'][0]['level'])
            with self.store.connect() as c:
                record=self.ledger._get(c,report['afterId'])
                self.assertIn('explicitly selected',record['officeIdentitySource'])
                self.assertEqual(payload,c.execute('SELECT payload FROM scout_evidence_artifacts WHERE id=?',(record['sha256'],)).fetchone()[0])
            again=flow.connect_latest(project['id'],connected['revision'],payload,'Test TSO')
            self.assertEqual(connected,again)

    def test_intake_failure_rolls_back_package_connection_and_evidence(self):
        from unittest.mock import patch
        from resource_research_agent.scout_improvement import ImprovementWorkflow
        flow=ImprovementWorkflow(self.store)
        project=flow.prepare(write_package(self.data,self.assets),'Test TSO',['r1'],historical=True)
        payload=write_package(self.changed(name='Changed'),self.assets)
        with patch.object(EvidenceLedger,'compare',side_effect=ImprovementError('Injected failure')):
            with self.assertRaises(ImprovementError):flow.connect_latest(project['id'],project['revision'],payload,'Test TSO')
        self.assertEqual(project,flow.view(project['id']))
        with self.store.connect() as c:
            self.assertEqual(0,c.execute("SELECT count(*) FROM scout_evidence_collections WHERE id LIKE 'project-intake:%'").fetchone()[0])
            self.assertEqual(0,c.execute('SELECT count(*) FROM scout_improvement_packages WHERE sha256=?',(hashlib.sha256(payload).hexdigest(),)).fetchone()[0])

    def test_legacy_version_is_evidence_only_and_original_bytes_survive(self):
        data=deepcopy(self.data);data['packageVersion']='2'
        payload=write_package(data,self.assets)
        with self.assertRaises(ImprovementError):read_package(payload)
        evidence=self.ledger.import_package('legacy','Test TSO',payload,scope='full',historical=True)
        self.assertEqual('2',evidence['packageVersion'])
        self.assertTrue(evidence['intakeWarnings'])
        with self.store.connect() as c:
            saved=c.execute('SELECT payload FROM scout_evidence_artifacts WHERE id=?',(evidence['sha256'],)).fetchone()[0]
            self.assertEqual(payload,saved)
            self.assertEqual('2',self.ledger._package(c,evidence['sha256'])['data']['packageVersion'])
        later=deepcopy(data);later['packageVersion']=3;later['resources'][0]['name']='Changed'
        after=self.ledger.import_package('legacy','Test TSO',write_package(later,self.assets),scope='full',historical=True)
        self.assertEqual(1,len(self.compare(evidence,after)['events']))
        for invalid in ('-1','2.0','02',' 2','٢',True,None):
            data['packageVersion']=invalid
            with self.assertRaises(ImprovementError):self.imp(data)

    def test_exact_fields_idempotency_and_editorial_adoption_not_vetting(self):
        title='Example · Clothing, furniture and household essentials'
        proposal=self.manual({'name':title});after=self.imp(self.changed(name=title))
        first=self.compare(self.base,after,captures=[proposal['id']]);again=self.compare(self.base,after,captures=[proposal['id']])
        self.assertEqual(first,again);self.assertEqual(self.base,self.imp(self.data))
        self.assertEqual(1,len(first['events']));event=first['events'][0]
        self.assertEqual(self.data['resources'][0]['name'],event['before']);self.assertEqual(title,event['after'])
        self.assertEqual('linked-adoption',event['level'])
        report=self.ledger.report(first['id']);self.assertEqual(0,report['summary']['explicitFieldVerifications'])
        self.assertEqual(0,report['summary']['resourceVettingInferred'])

    def test_metadata_set_order_and_missing_vs_null(self):
        original=deepcopy(self.data);original['resources'][0]['forGroups']=['Seniors','Veterans'];base=self.imp(original)
        changed=deepcopy(original);changed['resources'].reverse();changed['packageVersion']=22
        changed['resources'][1]['forGroups'].reverse();changed['resources'][1]['lastModified']='2026-09-06T12:00:00Z'
        after=self.imp(changed);self.assertFalse(self.compare(base,after)['events'])
        changed['resources'][1]['newField']=None
        e=self.compare(base,self.imp(changed))['events'][0]
        self.assertFalse(e['beforePresent']);self.assertTrue(e['afterPresent']);self.assertIsNone(e['after'])

    def test_partial_absence_addition_and_explicit_deletion_are_distinct(self):
        data=deepcopy(self.data);data['resources']=data['resources'][:1]
        for scope in ('partial','unknown','full'):
            result=self.compare(self.base,self.imp(data,scope))
            self.assertEqual('absence',result['events'][0]['change']);self.assertIn('not establish',result['events'][0]['ambiguity'])
        data['deletions']=[{'kind':'resource','targetId':'r2','label':'Test pantry r2'}]
        result=self.compare(self.base,self.imp(data));self.assertEqual({'absence','explicit-history'},{e['change'] for e in result['events']})
        extra=deepcopy(self.data);extra['resources'].append({**extra['resources'][0],'id':'human-added'})
        event=self.compare(self.base,self.imp(extra))['events'][0]
        self.assertEqual('addition',event['change']);self.assertEqual('observed-change',event['level'])

    def test_collections_historical_and_concurrent_lineage(self):
        production=self.imp(self.data,collection='live',historical=False)
        with self.assertRaises(ImprovementError):self.compare(self.base,production)
        with self.assertRaises(ImprovementError):self.imp(self.data,historical=False)
        a=self.imp(self.changed(name='Branch A'));b=self.imp(self.changed(name='Branch B'))
        self.assertEqual(self.base['id'],self.compare(self.base,a)['beforeId'])
        self.assertEqual(self.base['id'],self.compare(self.base,b)['beforeId'])
        with self.assertRaises(ImprovementError):self.ledger.compare(a['id'],b['id'],reviewer='QA',lineage_note='')

    def test_versions_and_sources_are_not_pooled(self):
        one=self.manual({'name':'New'},'v1');two=self.manual({'name':'New'},'v2');after=self.imp(self.changed(name='New'))
        event=self.compare(self.base,after,captures=[one['id'],two['id']])['events'][0]
        self.assertEqual('observed-change',event['level']);self.assertIn('ambiguity',event)
        event=self.compare(self.base,after,captures=[two['id']])['events'][0];self.assertEqual('linked-adoption',event['level'])
        unrelated=self.imp(self.changed(name='Different baseline'))
        event=self.compare(unrelated,after,captures=[one['id']])['events'][0];self.assertFalse(event['proposalLinks'])

    def test_identity_links_are_explicit_and_do_not_infer_service_verification(self):
        data=deepcopy(self.data);data['resources'][0]['id']='renamed-id';after=self.imp(data)
        plain=self.compare(self.base,after);self.assertEqual(2,len(plain['events']));self.assertFalse(plain['identityLinks'])
        link={'beforeIds':['r1'],'afterIds':['renamed-id'],'reviewer':'Synthetic curator','note':'Explicit identity correction'}
        result=self.compare(self.base,after,identity_links=[link]);self.assertEqual([link],result['identityLinks'])
        self.assertTrue(all(e['level']=='observed-change' for e in result['events']))
        with self.assertRaises(ImprovementError):self.compare(self.base,after,identity_links=[link,link])

    def test_explicit_field_verification_supersession_and_ambiguity(self):
        after=self.imp(self.changed(name='New',phone='555-0199'))
        comp=self.compare(self.base,after);phone=next(e for e in comp['events'] if e['field']=='phone')
        args=dict(reviewer='Synthetic curator',method='phone',note='Synthetic confirmed contact',source='Synthetic call note, not real')
        one=self.ledger.attest(comp['id'],phone['eventId'],**args)
        self.assertEqual(one,self.ledger.attest(comp['id'],phone['eventId'],**args))
        report=self.ledger.report(comp['id']);self.assertEqual(1,report['summary']['explicitFieldVerifications'])
        self.assertEqual('observed-change',next(e for e in report['events'] if e['field']=='name')['level'])
        two=self.ledger.attest(comp['id'],phone['eventId'],**{**args,'note':'Corrected synthetic note'},supersedes=one['id'])
        self.assertEqual(1,self.ledger.report(comp['id'])['summary']['explicitFieldVerifications'])
        self.ledger.attest(comp['id'],phone['eventId'],**{**args,'note':'Unrelated competing note'})
        self.assertEqual(0,self.ledger.report(comp['id'])['summary']['explicitFieldVerifications'])
        with self.assertRaises(ImprovementError):self.ledger.attest(comp['id'],phone['eventId'],**{**args,'method':'title-approved'})
        self.assertTrue(two['historical'])

    def test_attachments_preserved_and_changes_observed(self):
        self.assets['pdfs/guide.pdf']=b'%PDF-1.4 changed synthetic bytes';after=self.imp(self.data)
        event=self.compare(self.base,after)['events'][0];self.assertEqual('attachment-change',event['change'])
        self.assertNotEqual(event['before'],event['after'])
        with self.store.connect() as c:
            self.assertEqual(b'%PDF-1.4 synthetic bytes',self.ledger._package(c,self.base['sha256'])['assets']['pdfs/guide.pdf'])

    def test_workflow_review_export_receipt_then_later_package_adoption(self):
        flow=MaintenanceWorkflow(self.store)
        pid=flow.prepare(write_package(self.data,self.assets),'Test TSO',['r1'],[],run_name='Synthetic evidence QA',historical=True)['id']
        while assignment:=flow.next_assignment(pid):
            result=result_for(assignment,'changed')
            if not assignment['stage'].startswith('audit:'):
                result['items'][0]['fields']={'name':'Example · Food pantry'}
                result['items'][0]['questions']=['Synthetic unresolved access question.']
            flow.submit(pid,assignment['stage'],result)
        flow.connect_latest(pid,flow.view(pid)['revision'],write_package(self.data,self.assets),'Test TSO')
        row=flow.view(pid)['items'][0]
        flow.review(pid,flow.view(pid)['revision'],row['taskId'],'r1','accept',{'name':'proposed'},'Synthetic curator','Title only; access remains unresolved.')
        capture_before=self.ledger.capture_project('test',pid)
        export=flow.prepare_export(pid,flow.view(pid)['revision']);prepared=self.ledger.capture_project('test',pid)
        after=self.ledger.import_package('test','Test TSO',flow.export_bytes(pid,export['exportId']),scope='full',historical=True)
        event=self.compare(self.base,after,captures=[prepared['id']])['events'][0]
        self.assertEqual('observed-change',event['level']);self.assertFalse(event['proposalLinks'][0]['delivered'])
        flow.acknowledge_export(pid,flow.view(pid)['revision'],export['exportId'],export['manifest']['packageSha256'])
        saved=self.ledger.capture_project('test',pid)
        self.assertEqual(saved,self.ledger.capture_project('test',pid))
        comparison=self.compare(self.base,after,captures=[saved['id']]);event=comparison['events'][0]
        self.assertEqual('linked-adoption',event['level']);self.assertEqual('name',event['field'])
        self.assertEqual({'name':'proposed'},event['proposalLinks'][0]['review']['choices'])
        self.assertEqual(0,self.ledger.report(comparison['id'])['summary']['explicitFieldVerifications'])
        connected=flow.connect_latest(pid,flow.view(pid)['revision'],flow.export_bytes(pid,export['exportId']),'Test TSO')
        self.assertEqual(2,connected['intakeEvidence']['linkedAdoptions'])  # Title and administrative question handoff.
        self.assertEqual(0,connected['intakeEvidence']['explicitFieldVerifications'])
        automatic=self.ledger.report(connected['intakeEvidence']['comparisonId'])
        self.assertEqual({'name':'proposed'},automatic['events'][0]['proposalLinks'][0]['review']['choices'])
        self.assertFalse(capture_before['exports'])
        with self.assertRaises(ImprovementError):self.compare(self.base,after,captures=[prepared['id'],saved['id']])
        self.imp(self.data,collection='live',historical=False)
        with self.assertRaises(ImprovementError):self.ledger.capture_project('live',pid)

    def test_catalog_changes_and_metadata_equivalent_confirmation(self):
        changed=self.changed(phone='555-0188');after=self.imp(changed)
        comp=self.compare(self.base,after);event=comp['events'][0]
        args=dict(reviewer='QA',method='phone',note='Synthetic note',source='Synthetic call 1')
        self.ledger.attest(comp['id'],event['eventId'],**args)
        changed['packageVersion']=55;again=self.compare(self.base,self.imp(changed))
        self.assertEqual(event['eventId'],again['events'][0]['eventId'])
        self.ledger.attest(again['id'],event['eventId'],**args)
        self.assertEqual(1,self.ledger.report(again['id'])['summary']['explicitFieldVerifications'])
        changed=deepcopy(self.data);changed['categories'][0]['label']='Food assistance'
        event=self.compare(self.base,self.imp(changed))['events'][0]
        self.assertEqual('catalog-change',event['change'])
        self.assertEqual('Food',event['before'][0]['label'])

    def test_invalid_manual_provenance_and_field_verification(self):
        with self.assertRaises(ImprovementError):self.manual({'verifiedOn':'today'})
        with self.assertRaises(ImprovementError):
            self.ledger.record_manual_proposal('test',self.base['id'],resource_id='r1',fields={'name':'New'},
                artifact={'path':'qa.html','sha256':'a'*64,'deliveredAt':'not a date'},configuration={'policy':'v1'})
        comp=self.compare(self.base,self.imp(self.changed(verifiedOn='09/26')))
        with self.assertRaises(ImprovementError):
            self.ledger.attest(comp['id'],comp['events'][0]['eventId'],reviewer='QA',method='phone',note='QA',source='QA')

    def test_writing_workflow_receipt_is_supported(self):
        from resource_research_agent.scout_improvement import ImprovementWorkflow
        from tests.test_scout_improvement import result_for as writing_result
        flow=ImprovementWorkflow(self.store)
        pid=flow.prepare(write_package(self.data,self.assets),'Test TSO',['r1'],historical=True)['id']
        while a:=flow.next_assignment(pid):flow.submit(pid,a['stage'],writing_result(a))
        flow.connect_latest(pid,flow.view(pid)['revision'],write_package(self.data,self.assets),'Test TSO')
        flow.review(pid,flow.view(pid)['revision'],'r1','curated',{'description':'proposed','informationText':'proposed'},'Synthetic reviewer','Synthetic writing review')
        export=flow.prepare_export(pid,flow.view(pid)['revision'])
        flow.acknowledge_export(pid,flow.view(pid)['revision'],export['exportId'],export['manifest']['packageSha256'])
        capture=self.ledger.capture_project('test',pid)
        later=deepcopy(self.data);exported=read_package(flow.export_bytes(pid,export['exportId']))
        later['resources'][0]=exported['resources']['r1']
        result=self.compare(self.base,self.imp(later),captures=[capture['id']])
        self.assertEqual({'description','informationText'},{e['field'] for e in result['events']})
        self.assertTrue(all(e['level']=='linked-adoption' for e in result['events']))
        self.assertTrue(all(e['proposalLinks'][0]['configuration']['writingGuidance']['sha256'] for e in result['events']))

    def test_cli_import_compare_report(self):
        import io
        from contextlib import redirect_stdout
        from resource_research_agent.cli import main
        def run(*args):
            out=io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(0,main(['--database',str(self.store.path),'evidence',*args]))
            return json.loads(out.getvalue())
        path=Path(self.tmp.name)/'later.zip';path.write_bytes(write_package(self.changed(name='Manual office edit'),self.assets))
        later=run('import',str(path),'--collection','test','--office','Test TSO','--scope','full','--historical')
        result=run('compare',self.base['id'],later['id'],'--reviewer','Synthetic operator','--lineage-note','Explicit synthetic predecessor')
        report=run('report',result['id'])
        self.assertEqual(1,report['summary']['observedChanges']);self.assertEqual(0,report['summary']['linkedAdoptions'])

    def test_reviewed_discovery_adoption_and_explicit_split(self):
        flow=MaintenanceWorkflow(self.store)
        pid=flow.prepare(write_package(self.data,self.assets),'Test TSO',[],['food'],run_name='Synthetic discovery',historical=True)['id']
        while a:=flow.next_assignment(pid):flow.submit(pid,a['stage'],result_for(a))
        flow.connect_latest(pid,flow.view(pid)['revision'],write_package(self.data,self.assets),'Test TSO')
        flow.review(pid,flow.view(pid)['revision'],'discovery:food','new-pantry','accept',{},'Synthetic curator','Synthetic candidate acceptance')
        export=flow.prepare_export(pid,flow.view(pid)['revision'])
        flow.acknowledge_export(pid,flow.view(pid)['revision'],export['exportId'],export['manifest']['packageSha256'])
        capture=self.ledger.capture_project('test',pid)
        after=self.ledger.import_package('test','Test TSO',flow.export_bytes(pid,export['exportId']),scope='full',historical=True)
        event=self.compare(self.base,after,captures=[capture['id']])['events'][0]
        self.assertEqual('addition',event['change']);self.assertEqual('linked-adoption',event['level'])
        self.assertTrue(event['resourceId'].startswith('scout-'))
        split=deepcopy(self.data);split['resources'][0]['id']='split-a';split['resources'].append({**split['resources'][0],'id':'split-b'})
        links=[{'beforeIds':['r1'],'afterIds':['split-a','split-b'],'reviewer':'Synthetic curator','note':'Explicit synthetic split'}]
        result=self.compare(self.base,self.imp(split),identity_links=links)
        self.assertEqual(links,result['identityLinks']);self.assertTrue(all(e['level']=='observed-change' for e in result['events']))

    def test_report_bytes_are_checked_and_preserved(self):
        proposal=self.manual({'name':'New'})
        path=Path(proposal['artifact']['path']);original=path.read_bytes();path.write_text('Changed file')
        with self.assertRaises(ImprovementError):
            self.ledger.record_manual_proposal('test',self.base['id'],resource_id='r1',fields={'name':'New'},
                artifact=proposal['artifact'],configuration={'policy':'v1'})
        with self.store.connect() as c:
            saved=c.execute('SELECT payload FROM scout_evidence_artifacts WHERE id=?',(proposal['artifact']['sha256'],)).fetchone()[0]
        self.assertEqual(original,saved)
