from copy import deepcopy
import unittest

from tests.test_evaluation_preparation import assignment,result,collection
from resource_research_agent.evaluation.prepared_handoff import build_bundle,validate_resolution
from resource_research_agent.evaluation.protocol import EvaluationError
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
                'mergedResources':[], 'typeMatches':[{'proposedId':'shelter','existingId':'existing-shelter','reason':'Same service meaning.'}],
                'groupMatches':[], 'preservationJudgment':'Preserved supported facts and sources; no office approval.'}
    return report,resolution,registry,previous


class PreparedHandoffTests(unittest.TestCase):
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

    def test_merge_requires_full_preserved_candidates_and_sources(self):
        report,resolution,registry,previous=fixtures()
        second=deepcopy(report['resources'][0]);second.update(id='b02-alias',candidateIds=['c2'])
        report['resources'].append(second);report['collection']['identities'][0]['memberIds'].append('b02-alias')
        with self.assertRaises(EvaluationError):validate_resolution(resolution,report,registry,previous)
        merged=deepcopy(report['resources'][0]);resolution['mergedResources']=[merged]
        with self.assertRaises(EvaluationError):validate_resolution(resolution,report,registry,previous)
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
