from collections import Counter
from copy import deepcopy
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest

from resource_research_agent.prepared_resources import validate_artifact
from resource_research_agent.preparation_contract import information_sections, LEGACY_INFORMATION_HEADINGS
from resource_research_agent.prepared_preview import preview_groups, render_preview
from resource_research_agent.resource_identity import load_registry, fingerprint, alias_key

ROOT = Path(__file__).resolve().parents[1]
DELIVERY = ROOT/'deliveries/mesa-four-categories-20260925'


class MesaDeliveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.artifact = json.loads((DELIVERY/'prepared-resources.json').read_text())
        cls.registry = load_registry(ROOT/'registry/resource-identities.json')
        cls.migration = json.loads((DELIVERY/'identity-migration.json').read_text())
        cls.receipt = json.loads((DELIVERY/'receipt.json').read_text())
        cls.config = json.loads((ROOT/'docs/prepared/mesa-four-category-review.json').read_text())
        cls.aliases = {r['legacyId']: r['resourceId'] for r in cls.migration['aliases']}
        cls.resources = {r['id']: r for r in cls.artifact['resources']}

    def by_prefix(self, prefix):
        old, = [rid for rid in self.aliases if rid.startswith(prefix)]
        return self.resources[self.aliases[old]]

    def test_delivery_integrity_and_exact_scope(self):
        counts = validate_artifact(self.artifact, self.registry, office_category_ids=self.config['officeCategoryIds'])
        self.assertEqual(dict(resources=143, usable=125, needsResolution=18, considerations=118,
                              starterMemberships=37, uniqueStarterResources=34), counts)
        self.assertEqual(counts, self.receipt['counts'])
        raw = (DELIVERY/'prepared-resources.json').read_bytes()
        self.assertEqual(raw, gzip.decompress((DELIVERY/'prepared-resources.json.gz').read_bytes()))
        self.assertEqual(hashlib.sha256(raw).hexdigest(), self.receipt['artifactSha256'])
        # The global registry may legitimately gain later offices after this
        # historical receipt; its namespace and existing bindings must survive.
        self.assertEqual(self.migration['registryNamespace'], self.registry['namespace'])
        for old, canonical in self.aliases.items():
            self.assertEqual(canonical, self.registry['aliases'][alias_key(self.migration['sourceNamespace'], old)])
        self.assertEqual(set(self.config['scope']), set(self.artifact['scope']['categoryIds']))
        self.assertFalse(self.artifact['scope']['completeOffice'])
        self.assertEqual(22, len(self.artifact['taxonomy']['categories']))
        self.assertLess(max(len(json.dumps(r).encode()) for r in self.resources.values()), 20_000)

    def test_starters_and_confirmed_identity_consolidations(self):
        self.assertEqual({'housing': 9, 'food': 10, 'transportation': 9, 'id-recovery': 9},
                         {s['categoryId']: len(s['members']) for s in self.artifact['starterSets']})
        for group in self.config['merges']:
            target = self.by_prefix(group['primary'])['id']
            for old in group['members']:
                self.assertEqual(target, self.by_prefix(old)['id'])
        self.assertEqual(3, len(self.migration['suppressedResourceIds']))
        self.assertFalse(set(self.migration['suppressedResourceIds']) & set(self.resources))

    def test_unresolved_conflicts_and_unsupported_memberships_stay_distinct(self):
        for prefix in self.config['needsResolution']:
            self.assertEqual('needs-resolution', self.by_prefix(prefix)['state'])
        for prefix in self.config['notOffered']:
            old, = [rid for rid in self.aliases if rid.startswith(prefix)]
            self.assertNotIn(self.aliases[old], self.resources)
        self.assertNotIn('housing', self.by_prefix('08a26b74')['categories'])
        self.assertEqual(['id-recovery'], self.by_prefix('fb402105')['categories'])

    def test_each_type_narrows_and_rare_paths_survive(self):
        for cid in self.config['scope']:
            resources = [r for r in self.resources.values() if cid in r['categories'] and r['state']=='usable']
            category_types = {t['id'] for t in self.artifact['taxonomy']['types'] if t['categoryId']==cid}
            counts = Counter(t for r in resources for t in set(r['types']) & category_types)
            self.assertLess(max(counts.values()), len(resources))
        labels = {t['label'] for t in self.artifact['taxonomy']['types']}
        self.assertTrue({'Infant Formula', 'ADA Paratransit', 'Tribal Credentials', 'Document Storage'} <= labels)

    def test_cross_category_need_remains_retrievable(self):
        expected = [('a75559d0','housing','eviction'), ('0e36c87d','housing','children'),
                    ('cd0fd352','food','SNAP'), ('1d65b4ad','transportation','AHCCCS')]
        for prefix, category, fact in expected:
            resource = self.by_prefix(prefix)
            self.assertIn(category, resource['categories'])
            self.assertIn(fact.casefold(), resource['informationText'].casefold())
        for resource in self.resources.values():
            self.assertNotIn('verifiedOn', resource)
            information_sections(resource['informationText'])

    def test_preview_uses_type_gap_then_alphabetic_without_mutation(self):
        before = fingerprint(self.artifact)
        for cid in self.config['scope']:
            _, others, unresolved, covered = preview_groups(self.artifact, cid)
            tids = {t['id'] for t in self.artifact['taxonomy']['types'] if t['categoryId']==cid}
            keys = [(not bool(set(r['resource']['types']) & tids - covered), r['resource']['name'].casefold(), r['resource']['id']) for r in others]
            self.assertEqual(sorted(keys), keys)
            self.assertTrue(all(r['resource']['state']=='needs-resolution' for r in unresolved))
        md, html = render_preview(self.artifact)
        self.assertEqual(before, fingerprint(self.artifact))
        self.assertIn('First five more to consider', md)
        self.assertIn('<details open>', html)
        self.assertNotIn('<script', html)
        self.assertEqual(md, (DELIVERY/'starters-and-five-more.md').read_text())
        self.assertEqual(html, (DELIVERY/'starters-and-five-more.html').read_text())

    @unittest.skipUnless((ROOT/'data/mesa-review-20260924/after-seed.json').exists(), 'Local original review archive required')
    def test_original_reviewed_information_and_source_bytes_preserved(self):
        source = ROOT/'data/mesa-review-20260924'
        seed = json.loads((source/'after-seed.json').read_text())
        state = json.loads((source/'browser-state-reconciled-v3.json').read_text())
        overrides = {r['id']: r for r in state['resourceOverrides']}
        for key, filename in [('seedSha256','after-seed.json'), ('stateSha256','browser-state-reconciled-v3.json'), ('decisionsSha256','final-decisions.json')]:
            self.assertEqual(self.config[key], hashlib.sha256((source/filename).read_bytes()).hexdigest())
        for original in seed['resources']:
            if original['id'] not in self.aliases or self.aliases[original['id']] not in self.resources:
                continue
            original = {**original, **overrides.get(original['id'], {})}
            output = self.resources[self.aliases[original['id']]]
            for body in information_sections(original['informationText'], LEGACY_INFORMATION_HEADINGS).values():
                self.assertIn(body, output['informationText'], original['id'])
        self.assertTrue(all(r['state'] in ('usable','needs-resolution') for r in self.resources.values()))

    @unittest.skipUnless((ROOT/'data/mesa-prepared-four-20260925/review-bundle-final.json').exists(), 'Local reviewed bundle required')
    def test_reproduction_cannot_silently_attest_changed_output(self):
        from resource_research_agent.mesa_prepared import check_attestation
        from resource_research_agent.prepared_export import review_fingerprint
        bundle = json.loads((ROOT/'data/mesa-prepared-four-20260925/review-bundle-final.json').read_text())
        attestation = json.loads((ROOT/'docs/prepared/mesa-review-attestation.json').read_text())
        check_attestation(bundle, attestation)
        bundle['payload']['resources'][0]['description'] += ' Changed compiler output.'
        bundle['review']['inputFingerprint'] = review_fingerprint(bundle)
        with self.assertRaisesRegex(ValueError, 'renewed judgment'): check_attestation(bundle, attestation)

    @unittest.skipUnless(importlib.util.find_spec('jsonschema'), 'Optional independent JSON Schema validator')
    def test_independent_json_schema_validation(self):
        from jsonschema import Draft202012Validator, FormatChecker
        schema = json.loads((ROOT/'schemas/scout-prepared-resources-v1.schema.json').read_text())
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        validator.validate(self.artifact)
        invalid = deepcopy(self.artifact); invalid['schemaVersion'] = 2
        self.assertTrue(list(validator.iter_errors(invalid)))


if __name__ == '__main__': unittest.main()
