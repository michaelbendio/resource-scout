"""Trial checks: the production validator must reject this file, not import it."""
import json
from pathlib import Path
import random
import sys
import unittest

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parents[1]))
from resource_research_agent.preparation_contract import information_sections, normalize_preparation_fields
from resource_research_agent.prepared_resources import validate_artifact, PreparedResourceError, source_id, revision, content_fingerprint

def read(p): return json.loads((ROOT/p).read_text())

class TrialChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.artifact=read('results/scout-welfare-square-prepared-resources-26-09-30.json')
        cls.resources={r['id']:r for r in cls.artifact['resources']}

    def test_import_rejected_with_and_without_trial_marker(self):
        with self.assertRaisesRegex(PreparedResourceError,'Evaluation artifacts cannot be imported'):
            validate_artifact(self.artifact)
        copy=dict(self.artifact,evaluationOnly=False)
        with self.assertRaisesRegex(PreparedResourceError,'registry-assigned identities'):
            validate_artifact(copy)
        self.assertFalse(self.artifact['importable'])
        self.assertTrue(all(r.startswith('trial_') for r in self.resources))

    def test_sources_sections_and_human_state(self):
        catalog={s['id']:s for s in self.artifact['sources']}
        self.assertEqual(len(catalog),len(self.artifact['sources']))
        for s in catalog.values(): self.assertEqual(s['id'],source_id(s['url']))
        for r in self.resources.values():
            self.assertEqual(r['revision'],revision(r))
            self.assertEqual(len(information_sections(r['informationText'])),5)
            self.assertFalse(set(r)&{'verifiedOn','verifiedAt','curated','deleted','pinned'})
            self.assertTrue(r['sourceIds'] and set(r['sourceIds'])<=set(catalog))
            normalize_preparation_fields(dict(r,sources=[catalog[s] for s in r['sourceIds']],resolutionReason='',taxonomySuggestions=[]))
        bad=dict(next(iter(self.resources.values())),informationText='No valid headings')
        with self.assertRaises(ValueError): information_sections(bad['informationText'])

    def test_selection_and_kind_coverage(self):
        a=self.artifact
        members=a['starterSets'][0]['members']
        picks=[m['resourceId'] for m in members]
        self.assertEqual(len(set(picks)),10)
        self.assertEqual([m['position'] for m in members],list(range(1,11)))
        self.assertTrue(all(m['contribution'] and m['limitation'] for m in members))
        covered={t for rid in picks for t in self.resources[rid]['types']}
        self.assertEqual(covered,{f'housing-kind-{k:02}' for k in [1,2,3,4,5,6,8,9,10]})
        self.assertEqual(a['trialChecklist']['coveredOriginalKinds'],[1,2,3,4,5,6,8,9])
        remaining=set(self.resources)-set(picks)
        self.assertEqual(remaining,{c['resourceId'] for c in a['considerations']})
        self.assertEqual(len(a['considerations']),len(remaining))
        self.assertEqual(remaining,{c['resourceId'] for c in a['trialComplements']})

    def test_taxonomy_scope_and_complete_review(self):
        a=self.artifact
        types={t['id']:t for t in a['taxonomy']['types']}
        groups={g['id']:g for g in a['taxonomy']['forGroups']}
        self.assertFalse(a['scope']['completeOffice'])
        self.assertFalse(a['scope']['completeScope'])
        self.assertEqual(a['scope']['categoryIds'],['housing'])
        self.assertEqual({t for r in self.resources.values() for t in r['types']},set(types))
        self.assertEqual({g for r in self.resources.values() for g in r['forGroups']},set(groups))
        for r in self.resources.values():
            self.assertEqual(r['categories'],['housing'])
            self.assertTrue(r['types'] and set(r['types'])<=set(types))
            self.assertTrue(set(r['forGroups'])<=set(groups))
        review=read('review/decisions.json')
        self.assertEqual({r['resourceId'] for r in review},set(self.resources))
        for r in review:
            self.assertEqual({g['groupId'] for g in r['groupDecisions']},set(groups))
            self.assertTrue(all(g['reason'] for g in r['groupDecisions']))
            self.assertTrue(all(r['officeFit'].values()))
        fp=content_fingerprint(a)
        self.assertEqual(a['review']['contentFingerprint'],fp)
        self.assertEqual(a['snapshot']['contentFingerprint'],fp)

    def test_judging_sample_reproducible_and_exhaustive(self):
        from build import draft_id
        keys=sorted(d['key'] for d in read('curation/prepared-drafts.json'))
        random.Random(20260930).shuffle(keys)
        sample=read('results/sample-selection.json')
        self.assertEqual(sample['resourceIds'],[draft_id(k) for k in keys[:20]])
        self.assertEqual(set(sample['resourceIds']),set(self.resources))

    def test_decisions_and_metrics_reconcile(self):
        run=read('metrics/run.json')
        research=read('research/decisions.json')
        self.assertEqual(run['investigatedLeads'],len(self.resources)+len(research['notSelected']))
        self.assertEqual(run['webToolCalls'],len(read('metrics/web-requests.json')))
        self.assertEqual(run['resourceCount'],16)
        self.assertEqual(run['claudeCalls'],0)
        self.assertEqual(run['imports'],0)
        self.assertEqual(run['productionRegistryWrites'],0)
        self.assertIsNone(run['codexUsageCostUsd'])
        self.assertEqual([g['kind'] for g in research['gaps']],[7])

if __name__=='__main__': unittest.main()
