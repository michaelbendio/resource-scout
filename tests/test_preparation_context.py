from copy import deepcopy
import unittest
import hashlib
from pathlib import Path
import tempfile

from resource_research_agent.preparation_context import attach_reviewed_context, reviewed_index
from resource_research_agent.scout_curation_runner import compact_assignment


class PreparationContextTests(unittest.TestCase):
    def test_supervisor_requires_current_prepared_draft_hash(self):
        from resource_research_agent.curation_supervisor import completed_export
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'drafts.json'
            path.write_text('{"importable":false}')
            summary=dict(status='completed',jobId=5,handoff='Ready for Codex review',
                         draftFile=str(path),draftSha256=hashlib.sha256(path.read_bytes()).hexdigest())
            self.assertTrue(completed_export(summary,5))
            self.assertFalse(completed_export(summary,6))
            path.write_text('changed')
            self.assertFalse(completed_export(summary,5))

    def setUp(self):
        self.assignment = dict(preparationPolicyVersion='prepared-resources-v1-five-sections',
            location={'name':'Mesa'}, availableCategories=[{'id':'food','label':'Food'}],
            candidates=[dict(id='7',name='Pantry',candidate={})])
        self.context = dict(schemaVersion=1,artifactType='scout-preparation-context',officeSlug='mesa',
            categories=[{'id':'food','label':'Food'},{'id':'miscellaneous','label':'Miscellaneous'}],
            forGroups=['Seniors'],forGroupDefinitions={'Seniors':{'description':'Dedicated older-adult access'}},
            sourceHashes={'seed':'sealed'},instructions='Historical evidence; assess every current candidate.',
            resources=[dict(legacyResourceId='legacy-a',preferredDraftReference='legacy-a',historicalCandidateIds=['7','8'],record={'name':'Reviewed pantry','informationText':'Earlier corrected access.'}),
                       dict(legacyResourceId='legacy-b',preferredDraftReference='legacy-b',historicalCandidateIds=['9'],record={'name':'Other provider'})])

    def test_bounded_index_keeps_full_evidence_out_of_inline_prompt(self):
        original = deepcopy(self.assignment)
        sealed = attach_reviewed_context(self.assignment,self.context)
        self.assertEqual(original,self.assignment)
        self.assertEqual(1,len(sealed['reviewedContext']['resources']))
        index=reviewed_index(sealed)
        self.assertEqual(['7'],index[0]['relatedCandidateIds'])
        view=compact_assignment(sealed)
        self.assertNotIn('reviewedContext',view)
        self.assertEqual(index,view['reviewedResourceIndex'])
        self.assertIn('reviewed-resources.json',view['evidenceFiles'])
        self.assertEqual(['Seniors'],view['availableForGroups'])

    def test_context_change_alters_sealed_fingerprint(self):
        first=attach_reviewed_context(self.assignment,self.context)
        self.context['resources'][0]['record']['informationText']='Changed review finding.'
        second=attach_reviewed_context(self.assignment,self.context)
        self.assertNotEqual(first['reviewedContext']['fingerprint'],second['reviewedContext']['fingerprint'])

    def test_other_office_removed_category_and_legacy_mode_reject(self):
        for mutation in ('office','category','legacy'):
            a,c=deepcopy(self.assignment),deepcopy(self.context)
            if mutation=='office': c['officeSlug']='provo'
            elif mutation=='category': c['categories']=[{'id':'other'}]
            else: a.pop('preparationPolicyVersion')
            with self.assertRaises(ValueError):attach_reviewed_context(a,c)
