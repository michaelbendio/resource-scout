"""Regression checks for the reviewed full Mesa delivery and human-state boundaries."""
from collections import Counter
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from resource_research_agent.prepared_resources import validate_artifact
from resource_research_agent.prepared_preview import preview_groups, render_preview
from resource_research_agent.preparation_contract import information_sections
from resource_research_agent.resource_identity import load_registry, alias_key, fingerprint

ROOT = Path(__file__).resolve().parents[1]
D = ROOT/'deliveries/mesa-complete-20260927-r2'
P = ROOT/'data/mesa-prepared-full-20260926-source-checks/review'
load = lambda p: json.loads(p.read_text())
CATEGORIES = {'addiction', 'children-pregnancy', 'clothing-household', 'disability',
    'domestic-violence', 'education', 'employment', 'financial-assistance', 'reentry-support',
    'food', 'medical-dental-vision', 'homeless-services', 'housing', 'id-recovery',
    'immigration', 'legal', 'mental-health', 'miscellaneous', 'seniors', 'transportation',
    'utilities-phone-internet', 'veterans'}
RELEASED = ['ic_02e7188858ce193a0473e36e', 'ic_3a1f70eac66a9c1ae49d0dfc',
    'ic_450234b124d87dcb2aa90972', 'ic_9deedd57ddd7044c63d425bd',
    'ic_9f54ce89ecf20e9f5b5564df', 'ic_ae32b0dbe508394d5ab980fa',
    'ic_b0258e3fb1df711681431cd8', 'ic_bacd7353bff0de954298ee6b',
    'ic_cfc05cff8b09e6be3a88b943', 'ic_d2016d1e52f51d74472bf283',
    'ic_d36673af1257f52a5e1b93d6', 'ic_e72ff299390247e0ed6de871',
    'ic_f3f1868019a328d1f7a10a20']


class MesaCompleteDeliveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.a = load(D/'prepared-resources.json')
        cls.registry = load_registry(ROOT/'registry/resource-identities.json')
        cls.migration = load(D/'identity-migration.json')
        cls.receipt = load(D/'receipt.json')
        cls.attestation = load(ROOT/'docs/prepared/mesa-complete-review-attestation-20260927-r2.json')
        cls.aliases = {x['legacyId']: x['resourceId'] for x in cls.migration['aliases']}
        cls.resources = {r['id']: r for r in cls.a['resources']}

    def test_full_scope_integrity_and_static_review_binding(self):
        counts = validate_artifact(self.a, self.registry, office_category_ids=CATEGORIES)
        self.assertEqual(dict(resources=1866, usable=1785, needsResolution=81,
            considerations=3947, starterMemberships=218, uniqueStarterResources=195), counts)
        self.assertEqual(counts, self.receipt['counts'])
        self.assertEqual(CATEGORIES, set(self.a['scope']['categoryIds']))
        self.assertTrue(self.a['scope']['completeOffice'] and self.a['scope']['completeScope'])
        raw = (D/'prepared-resources.json').read_bytes()
        self.assertEqual(raw, gzip.decompress((D/'prepared-resources.json.gz').read_bytes()))
        self.assertEqual(hashlib.sha256(raw).hexdigest(), self.receipt['artifactSha256'])
        self.assertEqual(self.attestation['reviewFingerprint'], self.receipt['reviewFingerprint'])
        self.assertEqual(self.attestation['inputHashes'], self.receipt['inputHashes'])
        self.assertEqual(self.attestation['review'], self.receipt['review'])
        self.assertEqual(self.a['snapshot']['contentFingerprint'],
                         load(D/'validation.json')['contentFingerprint'])
        self.assertEqual(hashlib.sha256((D/'final-collection-input-manifest.json').read_bytes()).hexdigest(),
                         self.receipt['inputHashes']['finalCollectionInputManifest'])

    def test_existing_aliases_hides_and_authorized_programme_releases(self):
        previous = load(ROOT/'deliveries/mesa-four-categories-20260925/identity-migration.json')
        for row in previous['aliases']:
            self.assertEqual(row['resourceId'], self.aliases[row['legacyId']])
        for old, canonical in self.aliases.items():
            self.assertEqual(canonical, self.registry['aliases'][alias_key(self.migration['sourceNamespace'], old)])
        hidden = set(self.migration['suppressedResourceIds'])
        self.assertEqual(7, len(hidden))
        self.assertLessEqual(set(previous['suppressedResourceIds']), hidden)
        self.assertFalse(hidden & self.resources.keys())
        for cid in RELEASED:
            self.assertEqual('usable', self.resources[self.aliases[cid]]['state'])

    def test_starters_do_not_promote_held_programmes_or_invent_human_approval(self):
        self.assertEqual({c: 9 if c in {'miscellaneous','reentry-support'} else 10 for c in CATEGORIES},
                         {s['categoryId']:len(s['members']) for s in self.a['starterSets']})
        starters = {m['resourceId'] for s in self.a['starterSets'] for m in s['members']}
        self.assertTrue(all(self.resources[rid]['state']=='usable' for rid in starters))
        for cid in ['ic_ea086268fef3f961841ee2c3', 'ic_cebab02af127e3883ade5c10',
                    'ic_0c8ec49a3049e50da2b1dfef', 'ic_f95cf8ce5e2ae1b4c2d04429']:
            r = self.resources[self.aliases[cid]]
            self.assertEqual('needs-resolution', r['state'])
            self.assertNotIn(r['id'], starters)
            self.assertTrue(r['resolutionReason'])
        for r in self.resources.values():
            information_sections(r['informationText'])
            self.assertFalse({'curated','isCurated','verifiedOn','deleted','pinned','notes'} & r.keys())

    def test_types_narrow_usable_results_and_no_unused_labels(self):
        self.assertEqual(269, len(self.a['taxonomy']['types']))
        self.assertEqual(25, len(self.a['taxonomy']['forGroups']))
        for cat in CATEGORIES:
            rs = [r for r in self.resources.values() if cat in r['categories'] and r['state']=='usable']
            tids = {t['id'] for t in self.a['taxonomy']['types'] if t['categoryId']==cat}
            counts = Counter(t for r in rs for t in set(r['types']) & tids)
            self.assertEqual(tids, set(counts))
            self.assertLess(max(counts.values())/len(rs), .85)
        previous = load(ROOT/'deliveries/mesa-four-categories-20260925/prepared-resources.json')
        rare_ids = {t['id'] for t in previous['taxonomy']['types']
                    if t['label'] in {'Infant Formula','ADA Paratransit','Tribal Credentials','Document Storage'}}
        self.assertEqual(4, len(rare_ids))
        transition = load(D/'taxonomy-transition.json')
        replacements = {x['previousType']['id']:x['proposedType']['id'] for x in transition['broaderReplacements']}
        current_ids = {t['id'] for t in self.a['taxonomy']['types']}
        missing_previous = {t['id'] for t in previous['taxonomy']['types']} - current_ids
        self.assertEqual(missing_previous, set(replacements))
        self.assertEqual(13, len(replacements))
        self.assertTrue(all(x['action']=='preserve-human-classifications' for x in transition['broaderReplacements']))
        self.assertIn('type_mesa_housing_housing-legal', current_ids)
        self.assertNotIn('type_mesa_housing_legal-help', current_ids)
        mapped_rare = {replacements.get(t,t) for t in rare_ids}
        self.assertLessEqual(mapped_rare, current_ids)
        self.assertLessEqual(mapped_rare, {t for r in self.resources.values() if r['state']=='usable' for t in r['types']})

    def test_withdrawal_requests_admin_review_and_scope_expansion_is_not_deletion(self):
        event, = self.a['withdrawnEvents']
        self.assertEqual('sr_18b88e4b94e259b0b7d2989f14a2943c', event['resourceId'])
        self.assertEqual('admin-review', event['action'])
        self.assertTrue(event['sourceIds'])
        self.assertIn('Existing applicants', event['reason'])
        self.assertEqual([], self.a['changeSet']['notObserved'])
        self.assertEqual('different-or-incomplete-no-disappearance-claims', self.a['changeSet']['comparisonScope'])

    def test_readable_preview_keeps_holds_separate_and_orders_by_type_gap(self):
        before = fingerprint(self.a)
        for cat in CATEGORIES:
            _, others, unresolved, covered = preview_groups(self.a, cat)
            tids = {t['id'] for t in self.a['taxonomy']['types'] if t['categoryId']==cat}
            keys = [(not bool(set(x['resource']['types']) & tids - covered),
                     x['resource']['name'].casefold(), x['resource']['id']) for x in others]
            self.assertEqual(sorted(keys), keys)
            self.assertTrue(all(x['resource']['state']=='usable' for x in others))
            self.assertTrue(all(x['resource']['state']=='needs-resolution' for x in unresolved))
        md, html = render_preview(self.a)
        self.assertEqual(md, (D/'starters-and-five-more.md').read_text())
        self.assertEqual(html, (D/'starters-and-five-more.html').read_text())
        self.assertEqual(before, fingerprint(self.a))
        self.assertEqual(hashlib.sha256(html.encode()).hexdigest(), load(D/'prepared-preview-inspection.json')['htmlSha256'])

    @unittest.skipUnless((P/'prepared-review-final-type-continuity.json').exists(), 'Local sealed review archive required')
    def test_static_attestation_and_byte_identical_export_retry(self):
        from resource_research_agent.prepared_export import export_bundle, review_fingerprint
        bundle_path = P/'prepared-review-final-type-continuity.json'
        bundle = load(bundle_path)
        self.assertEqual(hashlib.sha256(bundle_path.read_bytes()).hexdigest(), self.attestation['bundleSha256'])
        self.assertEqual(fingerprint(bundle['payload']), self.attestation['payloadFingerprint'])
        self.assertEqual(review_fingerprint(bundle), self.attestation['reviewFingerprint'])
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            registry = target/'registry.json'
            registry.write_bytes((P/'registry-before-full-mesa.json').read_bytes())
            for _ in range(2):
                export_bundle(bundle_path, registry, target/'out',
                    previous_path=ROOT/'deliveries/mesa-four-categories-20260925/prepared-resources.json')
                for name in ['prepared-resources.json','prepared-resources.json.gz','identity-migration.json','receipt.json']:
                    self.assertEqual((D/name).read_bytes(), (target/'out'/name).read_bytes(), name)

    @unittest.skipUnless(importlib.util.find_spec('jsonschema'), 'Optional independent JSON Schema validator')
    def test_independent_schema_validation_of_complete_delivery(self):
        from jsonschema import Draft202012Validator, FormatChecker
        schema = load(ROOT/'schemas/scout-prepared-resources-v1.schema.json')
        Draft202012Validator(schema, format_checker=FormatChecker()).validate(self.a)


if __name__ == '__main__':
    unittest.main()
