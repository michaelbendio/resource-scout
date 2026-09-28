from copy import deepcopy
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from resource_research_agent.evaluation.preparation import (
    batch_assignment, normalize, collection_contract, preview, run, REVIEW, include_source_only,ordered_batches,collection_research_context,
)
from resource_research_agent.evaluation.ledger import Ledger, BudgetHold
from resource_research_agent.evaluation.protocol import EvaluationError, read, write_once
from resource_research_agent.preparation_contract import INFORMATION_HEADINGS


def assignment():
    base = dict(preparationPolicyVersion='test', instructions=[], availableCategories=[{'id':'housing'}],
                availableForGroups=[], candidates=[], previouslyCuratedResources=[])
    return batch_assignment(base,[{'id':'c1'}],'b01-')


def result(a):
    r = dict(id='b01-program',name='Shelter',phone='555-555-5555',address='',website='https://example.org',
             hours='',description='Emergency shelter for local residents.',
             informationText='\n\n'.join('**'+h+'**\n\nSupported fact or clear uncertainty.' for h in INFORMATION_HEADINGS),
             verifiedOn=None,categories=['housing'],categoryFilters={},forGroups=[],pdfs=[],candidateIds=['c1'],
             email='',researchedAt=None,sources=[{'url':'https://example.org','title':'Provider'}],state='usable',
             resolutionReason='',taxonomySuggestions=[])
    return dict(scoutCurationResultSchemaVersion=1,assignmentSha256=a['assignmentSha256'],categoryId='housing',
                resources=[r],candidateDispositions=[dict(candidateId='c1',disposition='curated',resourceIds=[r['id']],reason='Distinct local shelter.')])


def collection():
    return dict(identities=[dict(canonicalId='b01-program',memberIds=['b01-program'],reason='Distinct shelter program.')],
                types=[dict(id='shelter',label='Emergency Shelter',definition='Immediate shelter access.')],forGroups=[],
                assignments=[dict(resourceId='b01-program',types=['shelter'],forGroups=[],typeEvidence='Emergency shelter.',
                                  groupEvidenceOrNoGroupReason='No restricted population is evidenced.',consideration='Adds immediate shelter access.')],
                starters=[dict(resourceId='b01-program',contribution='Shelter route.',limitation='Call for space.')],
                rationale='Only supported program in this fixture.',gaps=[],sizeException='Only one supported program.',findings=[])


class PreparationEvaluationTests(unittest.TestCase):
    def test_collection_source_index_preserves_original_text_and_member_links(self):
        member={'sourceLabel':'Original','sourceOrdinal':1,'uncertainty':'Do not infer eligibility.'}
        base={'sourceResponses':[{'sourceLabel':'Original','rawText':'Exact original facts.'}],
              'candidates':[{'id':'c1','name':'Program','notes':'Keep this note.',
                             'candidate':{'manualDiscoveryChecks':{'derived':True},
                                          'manualDiscoveryProvenance':{'members':[member]}},
                             'resourceDraft':{'description':'Derived draft'}},
                            {'id':'routing','name':'Navigator','candidate':{'members':[member]}}]}
        original=deepcopy(base);context=collection_research_context(base)
        self.assertEqual(context['sourceResponses'],base['sourceResponses'])
        self.assertEqual([c['originalMembers'] for c in context['candidateIndex']],[[member],[member]])
        self.assertEqual(context['candidateIndex'][0]['notes'],'Keep this note.')
        self.assertNotIn('resourceDraft',context['candidateIndex'][0])
        self.assertEqual(base,original)
        base['sourceResponses']=[]
        with self.assertRaises(EvaluationError):collection_research_context(base)

    def test_parallel_batches_retain_order_and_stop_pending_work_on_failure(self):
        barrier=threading.Barrier(2)
        def worker(n):
            barrier.wait(timeout=2)
            if n==0:time.sleep(.01)
            return n
        self.assertEqual(ordered_batches(worker,[0,1],2),[0,1])
        barrier=threading.Barrier(2);failed=threading.Event();started=[]
        def failing(n):
            started.append(n)
            if n<2:barrier.wait(timeout=2)
            if n==0:
                failed.set();raise ValueError('Diagnosed failure')
            failed.wait(timeout=2);time.sleep(.02)
            return n
        with self.assertRaises(ValueError):ordered_batches(failing,list(range(8)),2)
        self.assertEqual(set(started),{0,1})
        with self.assertRaises(EvaluationError):ordered_batches(worker,[],3)

    def test_routing_sources_receive_explicit_dispositions_too(self):
        a={'candidates':[{'id':1}], 'sourceOnlyRecords':[{'groupKey':'routing', 'displayName':'Referral line','members':[{'original':'lead'}]}]}
        expanded=include_source_only(a)
        self.assertEqual([c['id'] for c in expanded['candidates']],['1','source-only-routing'])
        self.assertEqual(expanded['candidates'][1]['candidate']['members'],[{'original':'lead'}])
        self.assertEqual(len(a['candidates']),1)

    def test_compact_batch_keeps_assigned_original_evidence_and_removes_other_leads(self):
        base=assignment();base.update(sourceResponses=[{'rawText':'Other leads'}],sourceOnlyRecords=[{'unassigned':'source'}])
        candidates=[{'id':'c1','candidate':{'originalSource':'preserved evidence'}}]
        compact=batch_assignment(base,candidates,'b02a-',compact=True)
        self.assertEqual(compact['candidates'],candidates)
        self.assertEqual(compact['sourceResponses'],[])
        self.assertEqual(compact['sourceOnlyRecords'],[])
        self.assertTrue(base['sourceResponses'])

    def test_full_candidate_coverage_and_five_sections(self):
        a=assignment();r=result(a)
        self.assertEqual(len(normalize(a,r)['resources']),1)
        r['candidateDispositions']=[]
        with self.assertRaises(ValueError):normalize(a,r)
        r=result(a);r['resources'][0]['informationText']='Unstructured summary'
        with self.assertRaises(ValueError):normalize(a,r)

    def test_human_verification_unknown_fields_and_links_rejected(self):
        a=assignment()
        for change in ['verified','approved','wrong-link']:
            r=result(a)
            if change=='verified':r['resources'][0]['verifiedOn']='2026-09-28'
            elif change=='approved':r['resources'][0]['curated']=True
            else:r['candidateDispositions'][0]['resourceIds']=[]
            with self.assertRaises((ValueError,EvaluationError)):normalize(a,r)

    def test_collection_requires_partition_and_all_judgments(self):
        resources=result(assignment())['resources'];c=collection()
        collection_contract(c,resources)
        for key in ['identities','assignments']:
            broken=deepcopy(c);broken[key]=[]
            with self.assertRaises(EvaluationError):collection_contract(broken,resources)
        broken=deepcopy(c);broken['identities'][0]['memberIds']*=2
        with self.assertRaises(EvaluationError):collection_contract(broken,resources)

    def test_group_evidence_and_unknown_types_rejected(self):
        resources=result(assignment())['resources']
        for field,value in [('types',['unknown']),('groupEvidenceOrNoGroupReason','')]:
            c=collection();c['assignments'][0][field]=value
            with self.assertRaises(EvaluationError):collection_contract(c,resources)

    def test_held_resource_cannot_be_starter(self):
        resources=result(assignment())['resources'];resources[0]['state']='needs-resolution'
        with self.assertRaises(EvaluationError):collection_contract(collection(),resources)

    def test_scoped_uncapped_stages_do_not_authorize_other_work(self):
        a=dict(dollarCapMode='none-authorized',totalUsd=None,categories=['housing'],approvalText='Explicit user authorization',
               stageCapsUsd={'housing-preparation':None,'housing-review':None,'housing-collection':None})
        self.assertTrue(Ledger.uncapped(a))
        for stages in [{},{'production':None},{'housing-review':1}]:
            b=dict(a,stageCapsUsd=stages)
            with self.assertRaises(BudgetHold):Ledger.uncapped(b)
        with self.assertRaises(BudgetHold):Ledger.uncapped(dict(a,categories=['food']))

    def test_preview_is_escaped_nonimportable_and_preserves_omissions(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);r=result(assignment());r['resources'][0]['name']='<script>bad()</script>'
            preview(root,'curated',[r],collection())
            saved=read(root/'reports/curated.json')
            self.assertTrue(saved['evaluationOnly']);self.assertFalse(saved['importable'])
            content=(root/'reports/curated.html').read_text()
            self.assertNotIn('<script>',content);self.assertIn('&lt;script&gt;',content)
            self.assertEqual(saved['candidateDispositions'],r['candidateDispositions'])

    def test_review_has_current_standards_not_pilot_answer_key(self):
        for text in ['EVERY original lead','fresh context','7–10','five','omissions']:
            self.assertIn(text,REVIEW)
        for answer in ['Autumn House','Covenant House','one·n·ten','Helaman']:
            self.assertNotIn(answer,REVIEW)


if __name__=='__main__':unittest.main()
