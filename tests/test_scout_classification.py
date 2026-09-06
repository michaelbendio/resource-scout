from __future__ import annotations

import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from resource_research_agent.improvement_packages import ImprovementError, read_package, write_package
from resource_research_agent.scout_classification import (ClassificationWorkflow, FIELDS, draft_guidance,
    memberships, term_key, compare_classifications, materialize_classifications)
from resource_research_agent.scout_improvement import ImprovementWorkflow
from resource_research_agent.storage import ResearchStore
from tests.test_scout_improvement import fixture_package


def classification_result(a):
    r = deepcopy(a['outputContract']); r['assignmentSha256'] = a['assignmentSha256']
    r['evidenceSources'] = [{'url': 'https://example.org/qa', 'accessedOn': '2026-09-05',
                            'excerpt': 'Synthetic QA: meals for older adults; Spanish help. Not real research.'}]
    for entry in r['attachmentAccess']:
        entry.update(mode='not-inspected', note='Synthetic QA attachment; no real inspection claimed.')
    if a['stage'].startswith('audit:'):
        r.update(findings=[], researchNotes='Synthetic QA; no independent service run claimed.')
    else:
        r.update({f: deepcopy(a['resource'].get(f, {} if f == 'categoryFilters' else [])) for f in FIELDS})
        r['forGroups'] = list(dict.fromkeys([*r['forGroups'], 'Spanish speaking']))
        definitions = {(t['field'], t['categoryId'], t['value']): t for t in a['classificationGuidance']['terms']}
        r['decisions'] = []
        for f,c,v in sorted(memberships(r) | memberships(a['resource'])):
            t = definitions.get((f,c,v), {})
            r['decisions'].append({'field':f,'categoryId':c,'value':v,
                'status':'supported' if t.get('approvedBy') else 'unconfirmed',
                'relation':'accommodates' if f=='forGroups' and v=='Spanish speaking' else 'targets' if f=='forGroups' else None,
                'program':'QA program','definitionVersion':a['classificationGuidance']['version'],
                'source':'https://example.org/qa','excerpt':r['evidenceSources'][0]['excerpt'],
                'evidenceDate':None,'reason':'Synthetic decision for workflow verification.'})
        r.update(emptyReasons={f:'' for f in FIELDS},taxonomyProposals=[],migrationProposals=[],reviewNotes=[])
        if a['stage']=='reconcile':
            r['resolutions']=[{'findingId':name+':'+f['id'],'status':'resolved','reason':'QA resolution'} for name,audit in a['audits'].items() for f in audit['findings']]
    return r


class ClassificationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.store=ResearchStore(Path(self.temp.name)/'qa.sqlite3'); self.flow=ClassificationWorkflow(self.store)
        self.data=fixture_package();self.data['forGroups']+=['Spanish speaking','Veterans']
        self.data['categories'] += [{'id':'seniors','label':'Seniors','filters':[]},{'id':'employment','label':'Employment','filters':['Placement']}]
        self.data['resources'][0]['categories'].append('seniors')
        self.assets={'pdfs/guide.pdf':b'%PDF-1.4 QA byte-preservation fixture'}
        self.payload=write_package(self.data,self.assets)
        self.view=self.flow.prepare(self.payload,'Test TSO',['r1','r2'],historical=True);self.pid=self.view['id']

    def approve(self, skip=()):
        v=self.flow.view(self.pid);g=deepcopy(v['currentCatalogDraft']);g['version']=v['guidance']['version']+1
        keys=[]
        for t in g['terms']:
            t['definition']='Synthetic QA definition of '+t['label']
            t['populationCategory']=t['field']=='categories' and t['value']=='seniors'
            if t['value'] not in skip: keys.append(term_key((t['field'],t['categoryId'],t['value'])))
        return self.flow.save_guidance(self.pid,v['revision'],g,'QA definition reviewer; not Michael',keys)

    def finish(self):
        while a:=self.flow.next_assignment(self.pid):self.flow.submit(self.pid,a['stage'],classification_result(a))
        return self.flow.view(self.pid)

    def connect(self,data=None,assets=None):
        v=self.flow.view(self.pid)
        return self.flow.connect_latest(self.pid,v['revision'],write_package(data or self.data,assets or self.assets),'Test TSO')

    def curate(self,rid='r1',choices=None,note='',finding_notes=None):
        v=self.flow.view(self.pid)
        return self.flow.review(self.pid,v['revision'],rid,'curated',choices or {f:'proposed' for f in FIELDS},'QA reviewer',note,finding_notes)

    def test_project_kind_isolation_and_no_approval_from_import(self):
        writing=ImprovementWorkflow(self.store);w=writing.prepare(self.payload,'Test TSO',['r1'])
        self.assertNotEqual(self.pid,w['id'])
        self.assertEqual([self.pid],[p['id'] for p in self.flow.list_projects()])
        with self.assertRaisesRegex(ImprovementError,'different workflow'):writing.view(self.pid)
        with self.assertRaisesRegex(ImprovementError,'different workflow'):self.flow.view(w['id'])
        g=deepcopy(self.view['guidance']);g['terms'][0].update(approvedBy='Michael',definition='Claimed approval')
        with self.assertRaisesRegex(ImprovementError,'claiming approval'):self.flow.prepare(self.payload,'Test TSO',['r1'],guidance=g)
        with self.assertRaisesRegex(ImprovementError,'approve office definitions'):self.flow.next_assignment(self.pid)

    def test_two_offices_keep_exact_catalog_and_no_mesa_constants(self):
        other=deepcopy(self.data);other.update(officeName='Other TSO',forGroups=['Older neighbours'])
        other['categories']=[{'id':'nourishment','label':'Nourishment','filters':['Hot lunch']}]
        g=draft_guidance(other,'Other TSO')
        self.assertEqual({'Older neighbours','nourishment','Hot lunch'},{t['value'] for t in g['terms']})
        self.assertTrue(all(t['approvedBy'] is None and t['definition']=='' for t in g['terms']))
        with self.assertRaisesRegex(ImprovementError,'exact office catalog'):self.flow.prepare(self.payload,'Test TSO',['r1'],guidance=g)

    def test_frozen_guidance_exact_contract_all_audits_restart(self):
        self.approve();a=self.flow.next_assignment(self.pid,resource_id='r2')
        self.assertNotIn('writingGuidance',a);self.assertIn('classificationGuidance',a)
        self.assertIn('universal availability',json.dumps(a['instructions']).lower())
        self.assertEqual(a,ClassificationWorkflow(self.store).next_assignment(self.pid,resource_id='r2'))
        response=classification_result(a);bad=deepcopy(response);bad['description']='Do not change writing'
        with self.assertRaisesRegex(ImprovementError,'exactly'):self.flow.submit(self.pid,'primary',bad)
        self.flow.submit(self.pid,'primary',response)
        self.assertIsNone(self.flow.next_assignment(self.pid,researcher='Codex',resource_id='r2'))
        v=self.finish();self.assertTrue(all(len(r['research'])==5 and all(s['completed'] for s in r['research']) for r in v['resources']))
        self.assertTrue(all(r['review'] is None for r in v['resources']))

    def test_pending_definition_can_preserve_but_not_add_membership(self):
        self.approve(skip=('Seniors','seniors','Spanish speaking'))
        a=self.flow.next_assignment(self.pid);r=classification_result(a)
        with self.assertRaisesRegex(ImprovementError,'Unconfirmed human membership'):self.flow.submit(self.pid,'primary',r)
        r['forGroups'].remove('Spanish speaking');r['decisions']=[d for d in r['decisions'] if d['value']!='Spanish speaking']
        self.flow.submit(self.pid,'primary',r)
        self.assertEqual('unconfirmed',next(d for d in r['decisions'] if d['value']=='Seniors')['status'])

    def test_membership_evidence_and_type_ownership_validation(self):
        self.approve();a=self.flow.next_assignment(self.pid);r=classification_result(a)
        cases=[]
        bad=deepcopy(r);bad['forGroups'].append('Invented group');cases.append((bad,'Unknown taxonomy'))
        bad=deepcopy(r);bad['categoryFilters']['employment']=['Placement'];cases.append((bad,'assigned category'))
        bad=deepcopy(r);bad['decisions']=bad['decisions'][1:];cases.append((bad,'every proposed'))
        bad=deepcopy(r);bad['decisions'][0]['source']='https://unsupported.example/';cases.append((bad,'supporting evidence'))
        bad=deepcopy(r);next(d for d in bad['decisions'] if d['value']=='Spanish speaking')['relation']=None;cases.append((bad,'targets or accommodates'))
        bad=deepcopy(r);bad['attachmentAccess']=[];cases.append((bad,'every assigned attachment'))
        bad=deepcopy(r);bad['decisions'][0]['definitionVersion']=999;cases.append((bad,'definition version'))
        for bad,message in cases:
            with self.subTest(message=message),self.assertRaisesRegex(ImprovementError,message):self.flow.submit(self.pid,'primary',bad)
        self.assertFalse(self.flow.view(self.pid)['resources'][0]['research'][0]['completed'])

    def test_population_category_removal_blocked_and_separate_proposal_preserved(self):
        self.approve();a=self.flow.next_assignment(self.pid);r=classification_result(a)
        r['categories'].remove('seniors');next(d for d in r['decisions'] if d['value']=='seniors')['status']='remove'
        with self.assertRaisesRegex(ImprovementError,'complete migration'):self.flow.submit(self.pid,'primary',r)
        r=classification_result(a);r['migrationProposals']=[{'categoryId':'seniors','replacement':'Food plus Seniors group','reason':'Review every affected resource first'}]
        r['taxonomyProposals']=[{'term':'Food boxes','definition':'A defined intervention','examples':'CSFP','overlap':'Compare Pantries','reason':'Needs office review'}]
        self.flow.submit(self.pid,'primary',r)
        self.assertNotIn('Food boxes',r['categoryFilters']['food'])

    def test_empty_groups_are_valid_with_explanation(self):
        self.approve();a=self.flow.next_assignment(self.pid);r=classification_result(a)
        r['forGroups']=[];r['decisions']=[d for d in r['decisions'] if d['value']!='Spanish speaking']
        for d in r['decisions']:
            if d['field']=='forGroups':d['status']='remove'
        with self.assertRaisesRegex(ImprovementError,'Reason no classification'):self.flow.submit(self.pid,'primary',r)
        r['emptyReasons']['forGroups']='QA fixture: no documented targeting or accommodation.'
        self.flow.submit(self.pid,'primary',r)

    def test_later_independent_memberships_contacts_history_and_exact_pdf_survive(self):
        self.approve();self.finish();latest=deepcopy(self.data);latest['packageVersion']+=1
        latest['resources'][0].update(phone='New phone',hours='Friday',verifiedOn='09/26',forGroups=['Seniors','Veterans'])
        self.connect(latest);self.curate();v=self.flow.view(self.pid);e=self.flow.prepare_export(self.pid,v['revision'])
        output=read_package(self.flow.export_bytes(self.pid,e['exportId']));r=output['resources']['r1']
        self.assertEqual(['Seniors','Veterans','Spanish speaking'],r['forGroups'])
        for field,value in latest['resources'][0].items():
            if field not in (*FIELDS,'lastModified'):self.assertEqual(value,r[field],field)
        self.assertEqual(self.assets,output['assets']);self.assertEqual(latest['changes'],output['data']['changes'][:-1])
        self.assertEqual(latest['categories'],output['data']['categories']);self.assertEqual(latest['forGroups'],output['data']['forGroups'])
        self.assertEqual({'r1'},set(output['resources']));self.assertNotIn('decisions',r)

    def test_changed_evidence_clears_research_preserves_history_and_rejects_old_result(self):
        self.approve();self.finish();self.connect();self.curate();old=self.flow.next_assignment(self.pid)
        with self.store.connect() as c:old_result=self.flow._load(c,self.pid)['resources']['r1']['results']['primary']
        latest=deepcopy(self.data);latest['resources'][0]['informationText']='Eligibility changed; review groups again'
        v=self.connect(latest);row=v['resources'][0]
        self.assertIsNone(row['proposal']);self.assertIsNone(row['review']);self.assertEqual(1,row['previousResearchRuns'])
        a=self.flow.next_assignment(self.pid,resource_id='r1');self.assertEqual(latest['resources'][0]['informationText'],a['resource']['informationText'])
        with self.assertRaisesRegex(ImprovementError,'sealed assignment'):self.flow.submit(self.pid,'primary',old_result)
        self.assertIsNotNone(v['resources'][1]['proposal'])

    def test_changed_attachment_bytes_require_research_again(self):
        self.approve();self.finish();v=self.connect(assets={'pdfs/guide.pdf':b'%PDF-1.4 Different bytes'})
        self.assertTrue(all(r['proposal'] is None for r in v['resources']))

    def test_catalog_or_definition_change_invalidates_acceptance_and_assignments(self):
        self.approve();self.finish();self.connect();self.curate();self.approve()
        v=self.flow.view(self.pid);self.assertTrue(all(r['proposal'] is None for r in v['resources']))
        self.finish();latest=deepcopy(self.data);latest['forGroups'].append('New office group')
        v=self.connect(latest);self.assertIsNone(v['resources'][0]['proposal'])
        with self.assertRaisesRegex(ImprovementError,'exact office catalog'):self.flow.next_assignment(self.pid)
        self.approve();self.assertIsNotNone(self.flow.next_assignment(self.pid))

    def test_missing_deleted_or_pending_deletion_cannot_export(self):
        self.approve();self.finish()
        for field in ('deletions','deletionRequests'):
            latest=deepcopy(self.data);latest[field]=[{'kind':'resource','targetId':'r1'}];self.connect(latest)
            with self.assertRaisesRegex(ImprovementError,'deletion'):self.curate()
        latest=deepcopy(self.data);latest['resources']=latest['resources'][1:];self.connect(latest)
        with self.assertRaisesRegex(ImprovementError,'absent'):self.curate()

    def test_material_findings_require_real_review_notes(self):
        self.approve()
        while a:=self.flow.next_assignment(self.pid):
            r=classification_result(a)
            if a['stage']=='audit:ChatGPT':r['findings']=[{'id':'eligibility','field':'forGroups','severity':'material','summary':'QA source conflict'}]
            if a['stage']=='reconcile':
                for resolution in r['resolutions']:resolution['status']='needs-review'
            self.flow.submit(self.pid,a['stage'],r)
        self.connect()
        with self.assertRaisesRegex(ImprovementError,'Human resolution'):self.curate()
        self.curate(finding_notes={'ChatGPT:eligibility':'QA only; retain uncertainty'})

    def test_save_cancel_retry_edit_and_stale_acknowledgement(self):
        self.approve();self.finish();self.connect();v=self.curate()
        e=self.flow.prepare_export(self.pid,v['revision']);v=self.flow.view(self.pid)
        self.assertFalse(v['resources'][0]['packaged'])
        self.assertEqual(e['exportId'],self.flow.prepare_export(self.pid,v['revision'])['exportId'])
        row=v['resources'][0];edit={k:deepcopy(row['proposal'][k]) for k in (*FIELDS,'decisions','emptyReasons','taxonomyProposals','migrationProposals','reviewNotes')}
        edit['evidenceSources']=row['evidence']['reconcile']['evidenceSources'];edit['reviewNotes']=['QA human edit']
        v=self.flow.edit(self.pid,v['revision'],'r1',edit,'QA editor');self.assertIsNone(v['resources'][0]['review'])
        with self.assertRaisesRegex(ImprovementError,'Review changed'):self.flow.acknowledge_export(self.pid,v['revision'],e['exportId'],e['manifest']['packageSha256'])
        v=self.curate();e=self.flow.prepare_export(self.pid,v['revision']);v=self.flow.view(self.pid)
        v=self.flow.acknowledge_export(self.pid,v['revision'],e['exportId'],e['manifest']['packageSha256'])
        self.assertTrue(v['resources'][0]['packaged']);self.assertFalse(v['resources'][1]['packaged'])
        with self.assertRaisesRegex(ImprovementError,'Reconnect'):self.curate('r2')

    def test_category_type_conflict_requires_coherent_final_selection(self):
        self.approve();self.finish();latest=deepcopy(self.data)
        latest['resources'][0]['categories'].remove('food')
        latest['resources'][0]['categoryFilters']={}
        self.connect(latest)
        with self.assertRaisesRegex(ImprovementError,'Explain'):self.curate()
        # Keep the later office removal; do not resurrect a category just to add a group.
        v=self.curate(choices={f:'current' if f!='forGroups' else 'proposed' for f in FIELDS},note='QA retains office removal')
        self.assertEqual('curated',v['resources'][0]['review']['decision'])

    def test_explicit_edit_can_resolve_later_office_membership_with_evidence(self):
        self.approve();self.finish();latest=deepcopy(self.data)
        latest['resources'][0]['forGroups'].append('Veterans');v=self.connect(latest)
        edit=deepcopy(v['resources'][0]['editableProposal'])
        self.assertIn('Veterans',edit['forGroups'])
        self.assertEqual('unconfirmed',next(d for d in edit['decisions'] if d['value']=='Veterans')['status'])
        edit['forGroups'].remove('Veterans')
        d=next(d for d in edit['decisions'] if d['value']=='Veterans')
        d.update(status='remove',program='QA program',source='https://example.org/correction',
                 excerpt='QA evidence explicitly contradicting this classification',reason='QA explicit correction; not silence')
        edit['evidenceSources'].append({'url':d['source'],'accessedOn':'2026-09-05','excerpt':d['excerpt']})
        v=self.flow.edit(self.pid,v['revision'],'r1',edit,'QA editor')
        from resource_research_agent.improvement_packages import digest
        self.assertEqual(digest(v['resources'][0]['evidence']['reconcile']),v['resources'][0]['proposal']['sourceResultSha256'])
        v=self.curate();e=self.flow.prepare_export(self.pid,v['revision'])
        r=read_package(self.flow.export_bytes(self.pid,e['exportId']))['resources']['r1']
        self.assertNotIn('Veterans',r['forGroups']);self.assertIn('Spanish speaking',r['forGroups'])

    def test_pending_group_and_type_deletions_use_office_label_keys(self):
        self.approve();self.finish()
        for deletion in ({'kind':'forGroup','label':'SPANISH SPEAKING'},
                         {'kind':'type','categoryId':'food','label':'pantries'}):
            latest=deepcopy(self.data);latest['deletionRequests']=[deletion];self.connect(latest)
            with self.assertRaisesRegex(ImprovementError,'deletion record or request'):self.curate()

    def test_category_and_new_type_merge_cannot_create_an_orphan(self):
        b={'categories':['food'],'categoryFilters':{},'forGroups':[]}
        c={'categories':[],'categoryFilters':{},'forGroups':[]}
        p={'categories':['food'],'categoryFilters':{'food':['Pantries']},'forGroups':[]}
        merged=materialize_classifications(b,c,p,{f:'proposed' for f in FIELDS})
        self.assertEqual([],merged['categories']);self.assertEqual({'food':['Pantries']},merged['categoryFilters'])
        self.approve();self.finish();self.connect()
        with self.store.connect() as connection:
            state=self.flow._load(connection,self.pid)
            package=read_package(self.payload)
            with self.assertRaisesRegex(ImprovementError,'without their category'):
                self.flow._ready(state,'r1',package,package,merged)

    def test_sealed_linked_evidence_preserves_scope_and_does_not_rewrite_source(self):
        from resource_research_agent.improvement_packages import digest
        content={'informationText':'Accepted earlier wording', 'scope':'Writing only; classification remains unreviewed'}
        linked={'r1':[{'label':'Prior pilot', 'sha256':digest(content),'content':content}]}
        v=self.flow.prepare(self.payload,'Test TSO',['r1'],linked_evidence=linked,historical=True)
        self.pid=v['id'];self.approve();content['informationText']='Caller mutated its copy'
        a=self.flow.next_assignment(self.pid)
        self.assertEqual('Accepted earlier wording',a['linkedEvidence'][0]['content']['informationText'])
        self.assertEqual(self.data['resources'][0]['informationText'],a['resource']['informationText'])
        self.assertEqual('Prior pilot',self.flow.view(self.pid)['resources'][0]['linkedEvidence'][0]['label'])
        with self.assertRaisesRegex(ImprovementError,'exact hash'):
            self.flow.prepare(self.payload,'Test TSO',['r1'],linked_evidence=linked)

    def test_old_writing_state_without_kind_remains_resumable_and_idempotent(self):
        writing=ImprovementWorkflow(self.store);v=writing.prepare(self.payload,'Test TSO',['r1'])
        with self.store.connect() as c:
            state=json.loads(c.execute('SELECT state_json FROM scout_improvement_projects WHERE id=?',(v['id'],)).fetchone()[0])
            state.pop('kind')
            c.execute('UPDATE scout_improvement_projects SET state_json=? WHERE id=?',(json.dumps(state),v['id']))
        self.assertEqual(v['id'],writing.prepare(self.payload,'Test TSO',['r1'])['id'])
        self.assertIn('writingGuidance',writing.next_assignment(v['id']))

    def test_definition_change_invalidates_prepared_export_save_acknowledgement(self):
        self.approve();self.finish();self.connect();v=self.curate()
        e=self.flow.prepare_export(self.pid,v['revision']);v=self.approve()
        with self.assertRaisesRegex(ImprovementError,'Review changed'):
            self.flow.acknowledge_export(self.pid,v['revision'],e['exportId'],e['manifest']['packageSha256'])
        self.assertFalse(self.flow.view(self.pid)['resources'][0]['packaged'])

    def test_set_merge_ignores_order_and_preserves_unaffected_display_order(self):
        b={'categories':['a','b'],'forGroups':['g','h'],'categoryFilters':{'a':['x','y']}}
        c=deepcopy(b);c['forGroups'].append('new-human')
        p=deepcopy(b);p['categories'].reverse();p['forGroups']=['h','g','new-scout'];p['categoryFilters']['a'].reverse()
        comparisons=compare_classifications(b,c,p)
        self.assertFalse(comparisons['categories']['changed']);self.assertFalse(comparisons['categoryFilters']['changed'])
        result=materialize_classifications(b,c,p,{f:'proposed' for f in FIELDS})
        self.assertEqual(['a','b'],result['categories']);self.assertEqual(['g','h','new-human','new-scout'],result['forGroups'])


if __name__=='__main__':unittest.main()
