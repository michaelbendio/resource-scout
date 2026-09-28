from copy import deepcopy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch,Mock

from tests.test_evaluation_preparation import assignment,result,collection
from resource_research_agent.evaluation.prepared_handoff import build_bundle,validate_resolution,reconcile_and_export
from resource_research_agent.evaluation.protocol import EvaluationError,write_once,read
from resource_research_agent.prepared_export import finalize
from resource_research_agent.prepared_resources import validate_artifact
from resource_research_agent.resource_identity import new_registry,register_reviewed


def fixtures():
    registry=new_registry()
    registry,mapping=register_reviewed(registry,source_namespace='existing-mesa',decisions=[
        dict(members=['old-shelter'],match=None,label='Shelter',reason='Existing distinct shelter identity.')])
    previous={'taxonomy':{'categories':[{'id':'housing','label':'Housing'},{'id':'food','label':'Food'}],
        'types':[{'id':'existing-shelter','categoryId':'housing','label':'Emergency Shelter','definition':'Immediate shelter access.'}],
        'forGroups':[]}}
    report={'resources':result(assignment())['resources'],'collection':collection()}
    resolution={'identities':[{'canonicalId':'b01-program','match':mapping['old-shelter'],
                              'reason':'Same distinct shelter and access route.','possibleDuplicateExistingIds':[]}],
                'mergedResources':[], 'mergeFindings':[], 'typeMatches':[{'proposedId':'shelter','existingId':'existing-shelter','reason':'Same service meaning.'}],
                'groupMatches':[], 'preservationJudgment':'Preserved supported facts and sources; no office approval.'}
    return report,resolution,registry,previous


class PreparedHandoffTests(unittest.TestCase):
    def test_full_handoff_and_resume_preserve_registry_and_both_deliveries(self):
        report,resolution,registry,previous=fixtures()
        previous['resources']=[]
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);output=root/'delivery';source=root/'production-registry.json';dest=root/'checkout-registry.json'
            for path,data in [(source,registry),(dest,registry),(root/'previous.json',previous),
                (root/'progress.json',{'status':'completed'}),(root/'inputs/assignment.json',{'candidates':[]}),
                (root/'reports/curated-with-selections.json',report),(root/'reports/reviewed-with-selections.json',report)]:
                write_once(path,data)
            (root/'reports/reviewed-with-selections.html').write_text('<html>Evaluation</html>')
            write_once(root/'results/normalized/reviewed-01.json',{'reviewFindings':[dict(resourceIds=['b01-program'],issue='Checked source',before='Draft facts',after='Supported facts retained',sourceUrls=['https://example.org'],status='no-change')]})
            ledger=Mock();ledger.config={'provider':{'endpoint':'https://api.deepseek.com/anthropic/v1/messages'}}
            ledger.summarize_usage.return_value={'attempts':1}
            with patch('resource_research_agent.evaluation.prepared_handoff.Ledger',return_value=ledger),patch('resource_research_agent.evaluation.prepared_handoff.run_assignment',return_value={'result':resolution}):
                for _ in range(2):
                    reconcile_and_export(root,production_registry=source,previous_artifact=root/'previous.json',destination_registry=dest,output=output)
            self.assertEqual(read(source),read(dest))
            artifact=read(output/'prepared-resources.json')
            self.assertEqual(validate_artifact(artifact,read(source))['resources'],1)
            self.assertTrue(read(output/'evaluation.json')['evaluationOnly'])
            page=(output/'review.html').read_text()
            self.assertIn('Services Offered',page);self.assertIn('Supported facts retained',page)
            self.assertEqual(len(read(source)['resources']),len(registry['resources']))

    def test_import_payload_reuses_registry_and_type_ids_and_limits_scope(self):
        report,resolution,registry,previous=fixtures()
        bundle=build_bundle(report,resolution,registry,previous,source_namespace='housing-trial',
            input_hashes={'review':'hash'},reviewed_at='2026-09-28T06:00:00+00:00')
        artifact,updated,migration,receipt=finalize(bundle,registry)
        self.assertEqual(artifact['resources'][0]['id'],resolution['identities'][0]['match'])
        self.assertEqual(artifact['resources'][0]['types'],['existing-shelter'])
        self.assertEqual(artifact['scope'],{'categoryIds':['housing'],'completeScope':True,'completeOffice':False})
        self.assertNotIn('verifiedOn',artifact['resources'][0])
        self.assertEqual(len(updated['resources']),len(registry['resources']))
        self.assertEqual(validate_artifact(artifact,updated)['resources'],1)
        self.assertIn('DeepSeek',receipt['review']['reviewer'])
        self.assertNotIn('Codex-reviewed',receipt['review']['reviewer'])

    def test_bad_registry_or_taxonomy_matches_are_rejected(self):
        report,resolution,registry,previous=fixtures()
        for path in ['identity','type']:
            broken=deepcopy(resolution)
            if path=='identity':broken['identities'][0]['match']='invented'
            else:broken['typeMatches'][0]['existingId']='invented'
            with self.assertRaises(EvaluationError):validate_resolution(broken,report,registry,previous)
        broken=deepcopy(resolution)
        broken['identities'][0]['possibleDuplicateExistingIds']=[broken['identities'][0]['match']]
        broken['identities'][0]['match']=None
        with self.assertRaises(EvaluationError):validate_resolution(broken,report,registry,previous)

    def test_merge_requires_full_preserved_candidates_and_sources(self):
        report,resolution,registry,previous=fixtures()
        second=deepcopy(report['resources'][0]);second.update(id='b02-alias',candidateIds=['c2'])
        report['resources'].append(second);report['collection']['identities'][0]['memberIds'].append('b02-alias')
        with self.assertRaises(EvaluationError):validate_resolution(resolution,report,registry,previous)
        merged=deepcopy(report['resources'][0]);resolution['mergedResources']=[merged]
        with self.assertRaises(EvaluationError):validate_resolution(resolution,report,registry,previous)
        resolution['mergeFindings']=[dict(canonicalId='b01-program',before='Two aliases of one program.',after='All sources and lead links preserved.',sourceUrls=['https://example.org'])]
        merged['candidateIds'].append('c2')
        validate_resolution(resolution,report,registry,previous)
        merged['sources']=[]
        with self.assertRaises(ValueError):validate_resolution(resolution,report,registry,previous)

    def test_evaluation_envelope_cannot_be_imported(self):
        report,resolution,registry,previous=fixtures()
        b=build_bundle(report,resolution,registry,previous,source_namespace='trial',input_hashes={'review':'hash'},reviewed_at='2026-09-28T06:00:00+00:00')
        artifact,updated,_,_=finalize(b,registry)
        artifact['evaluationOnly']=True
        with self.assertRaises(ValueError):validate_artifact(artifact,updated)


if __name__=='__main__':unittest.main()
