"""Synthetic workflow QA. These fixtures are not independent AI research."""
from copy import deepcopy
import tempfile
import unittest
from pathlib import Path

from resource_research_agent.storage import ResearchStore
from resource_research_agent.scout_classification import ClassificationWorkflow, FIELDS, term_key
from resource_research_agent.scout_improvement import ImprovementWorkflow
from resource_research_agent.improvement_packages import ImprovementError, read_package, write_package
from resource_research_agent.taxonomy_review import TaxonomyReview, _same_provider
from tests.test_scout_classification import classification_result
from tests.test_scout_improvement import fixture_package


class TaxonomyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.store = ResearchStore(Path(self.temp.name)/'test.sqlite3')
        self.flow = ClassificationWorkflow(self.store); self.review = TaxonomyReview(self.flow)
        self.data = fixture_package()
        self.data['forGroups'] += ['Spanish speaking', 'Veterans', 'Rare group']
        self.data['categories'] += [{'id':'seniors','label':'Seniors','filters':['Legacy Type']}]
        for r in self.data['resources']:
            r['categories'].append('seniors');r['categoryFilters']['seniors']=['Legacy Type']
        self.data['resources'][0]['forGroups'].append('Rare group')
        third=deepcopy(self.data['resources'][1]);third.update(id='r3',name='Separate provider',website='https://different.example/')
        self.data['resources'].append(third)
        self.assets={'pdfs/guide.pdf':b'%PDF-1.4 Synthetic QA preservation fixture'}
        self.payload=write_package(self.data,self.assets)
        self.pid=self.flow.prepare(self.payload,'Test TSO',['r1','r2'],historical=True)['id']
        v=self.flow.view(self.pid);g=deepcopy(v['currentCatalogDraft']);g['version']+=1
        for t in g['terms']:
            t['definition']='Synthetic QA definition of '+t['label']
            t['populationCategory']=t['field']=='categories' and t['value']=='seniors'
        self.flow.save_guidance(self.pid,v['revision'],g,'QA reviewer; not Michael',[term_key((t['field'],t['categoryId'],t['value'])) for t in g['terms']])
        self.connect()

    def rev(self):return self.flow.view(self.pid)['revision']
    def connect(self,data=None):return self.flow.connect_latest(self.pid,self.rev(),write_package(data or self.data,self.assets),'Test TSO')
    def finish(self, transform=None):
        while a:=self.flow.next_assignment(self.pid):
            r=classification_result(a)
            if transform:transform(a,r)
            self.flow.submit(self.pid,a['stage'],r)
    def select_all(self):return self.review.select_resources(self.pid,self.rev(),['r3'])
    def plan(self):return self.review.create_plan(self.pid,self.rev(),['seniors'],'QA complete population-category retirement')['plans'][-1]
    def mapping(self,plan,rid='r1',**kwargs):
        return self.review.review_mapping(self.pid,self.rev(),plan['id'],rid,kwargs.get('choices',{f:'proposed' for f in FIELDS}),
            'QA reviewer; not Michael',kwargs.get('note','QA service category and supported groups reviewed.'),
            kwargs.get('finding_notes',{}),kwargs.get('types',{term_key(('categoryFilters','seniors','Legacy Type')):'Retire redundant legacy Type; Food / Pantries remains.'}))
    def ready(self):
        self.select_all();self.finish();p=self.plan()
        for rid in p['affectedIds']:self.mapping(p,rid)
        return p
    def approve(self,p):return self.review.approve_plan(self.pid,self.rev(),p['id'],'QA reviewer; not Michael','QA all mappings inspected.')
    def export(self,p):return self.review.prepare_export(self.pid,self.rev(),p['id'])

    def test_office_counts_partial_coverage_provider_clusters_and_overlap(self):
        self.finish();v=self.review.view(self.pid);g={x['group']:x for x in v['groups']}
        self.assertEqual(3,v['officeResourceCount']);self.assertEqual(2,v['researchedResourceCount'])
        self.assertEqual((3,3),(g['Seniors']['currentCount'],g['Seniors']['proposedCount']))
        self.assertEqual(2,g['Seniors']['coverage']['researched']);self.assertEqual(3,g['Seniors']['coverage']['unreviewed'])
        self.assertEqual([2,1],sorted([c['count'] for c in g['Seniors']['providerClusters']],reverse=True))
        self.assertEqual(3,next(c['count'] for c in g['Seniors']['categories'] if c['id']=='food'))
        self.assertEqual(2,next(x['count'] for x in g['Seniors']['overlaps'] if x['group']=='Spanish speaking'))
        self.assertEqual(0,g['Veterans']['proposedCount']);self.assertIn('incomplete research',g['Veterans']['attention'][0])
        self.assertEqual(1,g['Rare group']['proposedCount']);self.assertIn('not a membership minimum',g['Rare group']['attention'][0])

    def test_useful_one_member_group_retention_is_allowed_and_recommendation_only(self):
        v=self.review.save_group(self.pid,self.rev(),'Rare group','retain','Find this essential specialist.','Useful even with one member.',
            'QA reviewer',{'r1':'Retain documented membership.'})
        g=next(g for g in v['groups'] if g['group']=='Rare group')
        self.assertEqual(1,g['coverage']['reviewed']);self.assertTrue(g['review']['recommendationOnly'])
        self.assertFalse(g['review']['stale'])
        
        with self.store.connect() as c:
            state=self.flow._load(c,self.pid)
            self.assertEqual(self.data['forGroups'],self.flow._package(c,state['latestSha256'])['data']['forGroups'])
        restarted=TaxonomyReview(ClassificationWorkflow(self.store)).view(self.pid)
        self.assertEqual(v,restarted)
        self.select_all();self.assertTrue(next(g for g in self.review.view(self.pid)['groups'] if g['group']=='Rare group')['review']['stale'])

    def test_group_dispositions_must_include_every_member_and_merge_target_existing(self):
        with self.assertRaisesRegex(ImprovementError,'every current or proposed'):
            self.review.save_group(self.pid,self.rev(),'Seniors','retire','QA','QA','QA',{'r1':'Remove'})
        with self.assertRaisesRegex(ImprovementError,'distinct existing'):
            self.review.save_group(self.pid,self.rev(),'Rare group','merge','QA','QA','QA',{'r1':'Replace'},'Invented')
        self.review.save_group(self.pid,self.rev(),'Veterans','clarify','Future targeted help','No members is not proof of no need','QA',{})
        self.review.save_group(self.pid,self.rev(),'Rare group','change-prominence','Find specialist','Keep accessible','QA',{'r1':'Retain'},prominence='all-groups')

    def test_unselected_affected_resource_blocks_partial_pilot_retirement(self):
        self.finish();p=self.plan();self.assertEqual(['r1','r2','r3'],p['affectedIds'])
        self.mapping(p,'r1');self.mapping(p,'r2')
        with self.assertRaisesRegex(ImprovementError,'research'):self.mapping(p,'r3')
        with self.assertRaisesRegex(ImprovementError,'r3'):self.approve(p)
        with self.assertRaisesRegex(ImprovementError,'complete current'):self.export(p)

    def test_extend_selection_preserves_completed_research_and_invalidates_plan(self):
        self.finish();before=self.flow.view(self.pid)['resources'][0]['proposal'];p=self.plan()
        v=self.select_all();self.assertTrue(v['plans'][0]['stale'])
        self.assertEqual(before,self.flow.view(self.pid)['resources'][0]['proposal'])
        self.assertEqual('r3',self.flow.next_assignment(self.pid)['resourceId'])
        with self.assertRaisesRegex(ImprovementError,'inputs changed'):self.mapping(p)
        with self.assertRaisesRegex(ImprovementError,'already selected'):self.select_all()

    def test_full_migration_requires_type_dispositions_and_whole_approval(self):
        self.select_all();self.finish();p=self.plan()
        with self.assertRaisesRegex(ImprovementError,'every Type'):self.mapping(p,types={})
        with self.assertRaisesRegex(ImprovementError,'Mapping rationale'):self.mapping(p,note='')
        for rid in p['affectedIds']:self.mapping(p,rid)
        with self.assertRaisesRegex(ImprovementError,'approve'):self.export(p)
        self.approve(p);self.assertTrue(self.review.view(self.pid)['plans'][0]['ready'])
        self.mapping(p);self.assertIsNone(self.review.view(self.pid)['plans'][0]['approval'])

    def test_complete_export_preserves_full_package_assets_fields_and_history(self):
        p=self.ready();self.approve(p);e=self.export(p);raw=self.review.export_bytes(self.pid,e['exportId']);out=read_package(raw)
        self.assertEqual(self.assets,out['assets']);self.assertEqual({'r1','r2','r3'},set(out['resources']))
        self.assertEqual(self.data['futureField'],out['data']['futureField'])
        self.assertEqual(self.data['changes'],out['data']['changes'][:1]);self.assertEqual(5,len(out['data']['changes']))
        self.assertEqual(self.data['forGroups'],out['data']['forGroups'])
        self.assertEqual([{'fromId':'seniors'}],out['data']['categoryMigrations'])
        self.assertEqual('category:seniors',out['data']['deletions'][0]['key'])
        self.assertEqual(11,out['data']['packageVersion']);self.assertNotIn('seniors',[c['id'] for c in out['data']['categories']])
        for original in self.data['resources']:
            r=out['resources'][original['id']]
            self.assertEqual(['food'],r['categories']);self.assertEqual({'food':['Pantries']},r['categoryFilters'])
            self.assertIn('Spanish speaking',r['forGroups']);self.assertGreater(r['lastModified'],original['lastModified'])
            for k,v in original.items():
                if k not in (*FIELDS,'lastModified'):self.assertEqual(v,r[k],k)
        retry=self.export(p);self.assertEqual(e['exportId'],retry['exportId'])
        self.assertTrue(all(not r['packaged'] for r in self.flow.view(self.pid)['resources']))
        with self.assertRaisesRegex(ImprovementError,'bytes'):self.review.acknowledge(self.pid,self.rev(),e['exportId'],'wrong')
        self.review.acknowledge(self.pid,self.rev(),e['exportId'],e['manifest']['packageSha256'])
        self.assertTrue(all(r['packaged'] for r in self.flow.view(self.pid)['resources']))
        self.review.acknowledge(self.pid,self.rev(),e['exportId'],e['manifest']['packageSha256'])
        with self.assertRaisesRegex(ImprovementError,'complete current'):self.export(p)

    def test_changed_package_blocks_old_export_and_saved_acknowledgement(self):
        p=self.ready();self.approve(p);e=self.export(p)
        changed=deepcopy(self.data);r=deepcopy(changed['resources'][0]);r.update(id='r4',name='Later human addition');changed['resources'].append(r)
        changed['packageVersion']+=1;self.connect(changed)
        v=self.review.view(self.pid)['plans'][0];self.assertTrue(v['stale']);self.assertIn('Affected resources changed',str(v['blockers']))
        with self.assertRaisesRegex(ImprovementError,'approve'):self.export(p)
        with self.assertRaisesRegex(ImprovementError,'changed after export'):self.review.acknowledge(self.pid,self.rev(),e['exportId'],e['manifest']['packageSha256'])
        self.assertEqual(4,len(self.plan()['affectedIds']))
        with self.assertRaisesRegex(ImprovementError,'new project'):self.review.select_resources(self.pid,self.rev(),['r4'])

    def test_pending_definitions_or_unconfirmed_memberships_block_final_mapping(self):
        def transform(a,r):
            if not a['stage'].startswith('audit:'):
                next(d for d in r['decisions'] if d['value']=='Pantries')['status']='unconfirmed'
        self.finish(transform);p=self.plan()
        with self.assertRaisesRegex(ImprovementError,'supported research'):self.mapping(p)

    def test_no_service_category_blocks_retirement_without_inventing_groups(self):
        def transform(a,r):
            if not a['stage'].startswith('audit:'):
                r['categories'].remove('food');r['categoryFilters'].pop('food')
                for d in r['decisions']:
                    if d['value']=='food' or d['categoryId']=='food':d['status']='remove'
        self.finish(transform);p=self.plan()
        with self.assertRaisesRegex(ImprovementError,'actual service category'):self.mapping(p)

    def test_material_findings_need_explicit_human_resolution(self):
        def transform(a,r):
            if a['stage']=='audit:ChatGPT':r['findings']=[{'id':'uncertain','field':'forGroups','severity':'material','summary':'QA unresolved access'}]
            if a['stage']=='reconcile':r['resolutions'][0]['status']='needs-review'
        self.finish(transform);p=self.plan()
        with self.assertRaisesRegex(ImprovementError,'Human resolution'):self.mapping(p)
        self.mapping(p,finding_notes={'ChatGPT:uncertain':'QA fixture resolved explicitly, not a provider claim.'})

    def test_deleted_resource_and_existing_migration_dependency_block_retirement(self):
        self.finish();changed=deepcopy(self.data)
        changed['deletionRequests']=[{'kind':'resource','targetId':'r3','requestedAt':'2026-09-06T00:00:00Z'}]
        self.connect(changed);p=self.plan()
        self.assertIn('r3',p['affectedIds'])
        with self.assertRaises(ImprovementError):self.mapping(p,'r3')
        changed=deepcopy(self.data);changed['categoryMigrations']=[{'fromId':'older','toId':'seniors'}];self.connect(changed)
        self.assertEqual(['older'],self.plan()['legacyCategoryIds'])

    def test_legacy_alias_plan_is_reviewable_but_reader_compatibility_blocks_export(self):
        self.data['categoryMigrations']=[{'fromId':'older','toId':'seniors'}]
        self.connect();p=self.ready()
        self.assertEqual(['older'],p['legacyCategoryIds'])
        with self.assertRaisesRegex(ImprovementError,'Location reader update required'):self.approve(p)
        with self.assertRaisesRegex(ImprovementError,'complete current'):self.export(p)

    def test_definition_change_invalidates_mapping_and_preserves_prior_research(self):
        p=self.ready();self.approve(p);v=self.flow.view(self.pid);g=deepcopy(v['guidance']);g['version']+=1
        self.flow.save_guidance(self.pid,v['revision'],g,'QA revised definitions',[term_key((t['field'],t['categoryId'],t['value'])) for t in g['terms']])
        self.assertTrue(self.review.view(self.pid)['plans'][0]['stale'])
        self.assertEqual(1,self.flow.view(self.pid)['resources'][0]['previousResearchRuns'])
        with self.assertRaisesRegex(ImprovementError,'complete current'):self.export(p)

    def test_group_review_includes_proposed_removals_and_does_not_require_new_groups(self):
        def transform(a,r):
            if not a['stage'].startswith('audit:'):
                r['forGroups']=[]
                r['decisions']=[d for d in r['decisions'] if d['value']!='Spanish speaking']
                for d in r['decisions']:
                    if d['field']=='forGroups':d['status']='remove'
                r['emptyReasons']['forGroups']='Synthetic QA: no targeting or accommodation.'
        self.finish(transform);g=next(g for g in self.review.view(self.pid)['groups'] if g['group']=='Rare group')
        self.assertEqual((1,0),(g['currentCount'],g['proposedCount']));self.assertEqual(['r1'],[r['id'] for r in g['members']])
        with self.assertRaisesRegex(ImprovementError,'every current or proposed'):
            self.review.save_group(self.pid,self.rev(),'Rare group','retire','QA','QA','QA',{})
        p=self.plan();v=self.mapping(p);self.assertEqual([],v['plans'][0]['mappings']['r1']['fields']['forGroups'])

    def test_exact_duplicate_candidates_remain_distinct_resource_records(self):
        changed=deepcopy(self.data);changed['resources'][1]['name']=changed['resources'][0]['name'];self.connect(changed)
        g=next(g for g in self.review.view(self.pid)['groups'] if g['group']=='Seniors')
        self.assertEqual([['r1','r2']],g['possibleDuplicates']);self.assertEqual(3,g['currentCount'])

    def test_stale_revision_and_writing_project_cannot_review_taxonomy(self):
        revision=self.rev();self.plan()
        with self.assertRaisesRegex(ImprovementError,'another window'):self.review.create_plan(self.pid,revision,['seniors'],'QA')
        w=ImprovementWorkflow(self.store).prepare(self.payload,'Test TSO',['r1'])
        with self.assertRaisesRegex(ImprovementError,'different workflow'):self.review.view(w['id'])

    def test_provider_candidates_do_not_collapse_shared_directories_or_bad_urls(self):
        self.assertEqual('record:x',_same_provider({'id':'x','website':'https://facebook.com/example'}))
        self.assertEqual('record:x',_same_provider({'id':'x','website':'https://[bad'}))
        self.assertEqual('phone:4808203700',_same_provider({'id':'x','phone':'480-820-3700'}))

if __name__=='__main__':unittest.main()
