from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from resource_research_agent.review_decisions import assemble, verify_bundle, file_sha, CONTENT_FIELDS, RULES
from resource_research_agent.review_acceptance import accept, verify_acceptance, JUDGMENTS
from resource_research_agent.resource_identity import fingerprint
from resource_research_agent.prepared_export import export_bundle
from tests.test_prepared_resources import fixture, seal


class ReviewDecisionTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = Path(temp.name); self.review = self.root/'review'; self.review.mkdir()
        self.bundle = fixture()
        draft = deepcopy(self.bundle['payload']['resources'][0])
        self.drafts = dict(resources=[draft, dict(id='older-a', categories=['housing']), dict(id='hidden', categories=['housing'])])
        self.write('drafts.json', self.drafts)
        rows = []
        for original in self.drafts['resources']:
            rid = original['id']
            row = dict(resourceId=rid, inputFingerprint=fingerprint(original),
                assessment=self.bundle['assessments'][rid], evidence=[dict(reference='https://example.org/help', finding='Individual source finding.')],
                ruleFindings=dict(housing={r:'Explicit rule finding from this program evidence.' for r in RULES}), result=None)
            if rid == 'old-a':
                row.update(result=deepcopy(draft), fieldDecisions={f:dict(action='retain', reason='Source supports this field.') for f in CONTENT_FIELDS},
                    typeEvidence={'rent':'Program helps with housing costs.'}, groupEvidence={}, noGroupReason='No evidenced population restriction.')
                row['fieldDecisions']['phone'] = dict(action='replace', value='456', reason='Corrected official intake number.')
                row['result']['phone'] = '456'
            rows.append(row)
        self.documents = dict(resources=dict(decisions=rows), candidates=dict(decisions=[dict(categoryId='housing', candidateId='c1', decision='retain',
            reason='Reviewed direct front door.', resourceIds=['old-a'], evidence=[dict(reference='candidate:c1', finding='Supports this intake.')])]),
            housing=dict(categoryId='housing', taxonomyJudgment='Rent means cost help, distinct from shelter.',
                stoppingReason='No additional supported fixture programs.', starterSet=self.bundle['payload']['starterSets'][0], considerations=[], complements=[]),
            collection=dict(taxonomyJudgment='Compared all labels and definitions.', identityBoundaryJudgment='Same intake merged; distinct hidden agency preserved.',
                preservationJudgment='Original suppression remains.', restoredCandidates={},
                payloadBase={k:self.bundle['payload'][k] for k in ('office','scope','taxonomy','sources')}))
        self.refresh()

    def write(self, name, value):
        path = self.review/name; path.write_text(json.dumps(value)); return path

    def refresh(self):
        for name, doc in self.documents.items(): self.write(name+'.json', doc)
        def ref(name): return dict(path=name+'.json', sha256=file_sha(self.review/(name+'.json')))
        manifest = dict(schemaVersion=1, draftsSha256=file_sha(self.review/'drafts.json'),
            resourceBatches=[ref('resources')], candidateBatches=[ref('candidates')], categories=[ref('housing')], collection=ref('collection'))
        self.manifest = self.write('decision-manifest.json', manifest)
        return manifest

    def compile(self): return assemble(self.manifest, self.drafts)[0]

    def bundle_path(self):
        self.bundle.update(self.compile())
        self.bundle['inputs']['decisionManifestSha256'] = file_sha(self.manifest)
        seal(self.bundle)
        (self.review/'report.md').write_text('Authored fixture report.')
        return self.write('reviewed-bundle.json', self.bundle)

    def findings(self):
        findings = {key:'Explicit supervisor fixture audit judgment.' for key in JUDGMENTS}
        findings['categoryChecks'] = [dict(categoryId='housing', sampleResourceIds=['old-a'], finding='Checked corrected intake and starter contribution.')]
        path = self.root/'findings.json'; path.write_text(json.dumps(findings)); return path

    def test_compiler_applies_exact_correction_and_exclusions(self):
        content = self.compile()
        self.assertEqual(content['payload']['resources'][0]['phone'], '456')
        self.assertEqual(len(content['payload']['resources']), 1)
        self.assertEqual(content['assessments']['hidden']['state'], 'suppressed')

    def test_missing_decisions_and_unapplied_correction_fail_closed(self):
        for mutation in (lambda d: d['resources']['decisions'].pop(),
            lambda d: d['resources']['decisions'][0]['result'].update(phone='123'),
            lambda d: d['resources']['decisions'][0]['fieldDecisions'].pop('hours'),
            lambda d: d['resources']['decisions'][0].update(noGroupReason=''),
            lambda d: d['resources']['decisions'][0].update(groupEvidence={'invented':'Keyword inference'}),
            lambda d: d['candidates']['decisions'][0].update(evidence=[])):
            before=deepcopy(self.documents)
            mutation(self.documents); self.refresh()
            with self.assertRaises(ValueError): self.compile()
            self.documents=before

    def test_bounded_batches_and_case_variant_taxonomy_rejected(self):
        self.documents['resources']['decisions'] *= 6; self.refresh()
        with self.assertRaisesRegex(ValueError, '1-15'): self.compile()
        self.setUp()
        types=self.documents['collection']['payloadBase']['taxonomy']['types']
        types.append({**types[0], 'id':'rent2', 'label':'RENT HELP'}); self.refresh()
        with self.assertRaisesRegex(ValueError, 'Duplicate normalized'): self.compile()

    def test_changed_decision_and_changed_assembly_cannot_match_seal(self):
        self.bundle_path()
        verify_bundle(self.bundle, self.manifest, self.review/'drafts.json')
        self.bundle['payload']['resources'][0]['phone']='123'
        with self.assertRaisesRegex(ValueError, 'differs'): verify_bundle(self.bundle, self.manifest, self.review/'drafts.json')
        self.documents['resources']['decisions'][0]['evidence'][0]['finding']='Changed'
        self.write('resources.json', self.documents['resources'])
        with self.assertRaisesRegex(ValueError, 'Stale decision'): self.compile()

    def test_manifest_cannot_read_outside_review_workspace(self):
        manifest=self.refresh(); manifest['resourceBatches'][0]['path']='../external.json'
        self.write('decision-manifest.json',manifest)
        with self.assertRaisesRegex(ValueError, 'stay inside'): self.compile()

    def test_acceptance_required_before_any_registry_or_delivery_write(self):
        bundle=self.bundle_path(); registry=self.root/'registry.json'; output=self.root/'delivery'
        with self.assertRaisesRegex(ValueError, 'Supervisor acceptance required'):
            export_bundle(bundle, registry, output, initialize_registry=True)
        self.assertFalse(registry.exists()); self.assertFalse(output.exists())

    def test_structured_acceptance_binds_output_and_every_authored_file(self):
        bundle=self.bundle_path(); receipt=self.root/'acceptance.json'
        accepted=accept(bundle,self.findings(),receipt,reviewer='Supervisor',manifest_path=self.manifest,drafts_path=self.review/'drafts.json')
        self.assertEqual(accepted['mode'],'structured-decisions-v1')
        verify_acceptance(bundle,receipt)
        export_bundle(bundle,self.root/'registry.json',self.root/'delivery',initialize_registry=True,acceptance_path=receipt)
        with self.assertRaisesRegex(ValueError,'Preserve the earlier'):
            accept(bundle,self.findings(),receipt,reviewer='Supervisor',manifest_path=self.manifest,drafts_path=self.review/'drafts.json')
        (self.review/'housing.json').write_text('{}')
        with self.assertRaisesRegex(ValueError,'evidence changed'): verify_acceptance(bundle,receipt)

    def test_worker_receipt_or_incomplete_supervisor_audit_rejected(self):
        bundle=self.bundle_path(); findings=self.findings()
        with self.assertRaisesRegex(ValueError,'outside'):
            accept(bundle,findings,self.review/'acceptance.json',reviewer='Worker')
        data=json.loads(findings.read_text()); data['categoryChecks']=[]; findings.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError,'every category'):
            accept(bundle,findings,self.root/'acceptance.json',reviewer='Supervisor')

    def test_stale_receipt_blocks_registry_mutation(self):
        bundle=self.bundle_path(); receipt=self.root/'acceptance.json'
        accept(bundle,self.findings(),receipt,reviewer='Supervisor',manifest_path=self.manifest,drafts_path=self.review/'drafts.json')
        before=bundle.read_bytes(); bundle.write_bytes(before+b'\n')
        with self.assertRaisesRegex(ValueError,'stale'):
            export_bundle(bundle,self.root/'registry.json',self.root/'delivery',initialize_registry=True,acceptance_path=receipt)
        self.assertFalse((self.root/'registry.json').exists())
