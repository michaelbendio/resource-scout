from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from resource_research_agent.preparation_contract import assemble_information, INFORMATION_HEADINGS, POLICY_VERSION
from resource_research_agent.resource_identity import new_registry, fingerprint
from resource_research_agent.prepared_resources import (build_snapshot, validate_artifact,
    source_catalog, source_id, revision, compare_snapshots)
from resource_research_agent.prepared_export import finalize, review_fingerprint, export_bundle, encoded


def fixture():
    resource = dict(id='old-a', state='usable', name='Housing and legal intake',
        description='Help for a parent facing eviction; children and housing needs considered.',
        phone='123', address='', website='https://example.org/help', email='', hours='',
        informationText=assemble_information({h: 'Evidence-backed fixture text.' for h in INFORMATION_HEADINGS}),
        categories=['housing'], types=['rent'], forGroups=[], sourceIds=[source_id('https://example.org/help')], researchedAt=None)
    payload = dict(office=dict(slug='mesa', name='Mesa'), scope=dict(categoryIds=['housing'], completeScope=True, completeOffice=False),
        taxonomy=dict(categories=[dict(id='housing', label='Housing')],
                      types=[dict(id='rent', categoryId='housing', label='Rent help', definition='Housing cost help')], forGroups=[]),
        resources=[resource], considerations=[], sources=source_catalog([dict(url='https://example.org/help', title='Program')]),
        starterSets=[dict(categoryId='housing', rationale='Test coverage', gaps='No other supported fixture programs',
            sizeException='Single-record test fixture, not a real office starter set.',
            members=[dict(resourceId='old-a', position=1, contribution='Eviction prevention', limitation='Confirm funding')])])
    bundle = dict(artifactType='scout-reviewed-preparation', policyVersion=POLICY_VERSION,
        sourceNamespace='mesa-legacy-resource', officeCategoryIds=['housing'], inputs=dict(seed='sealed'),
        identityDecisions=[dict(members=['old-a', 'older-a'], label=resource['name'], reason='Reviewed same intake'),
                           dict(members=['hidden'], label='Hidden provider', reason='Separate program')],
        assessments={'old-a': dict(state='usable', reason='Supported'),
                     'older-a': dict(state='merged', target='old-a', reason='Same program'),
                     'hidden': dict(state='suppressed', reason='Existing human deletion')}, payload=payload)
    seal(bundle)
    return bundle


def seal(bundle):
    bundle['review'] = dict(reviewer='Test reviewer', reviewedAt='2026-09-25T12:00:00Z',
        identity='Reviewed program boundaries', content='Reviewed source facts', taxonomy='Reviewed selectivity and support',
        starterSets='Reviewed complementary choices', preservation='Reviewed aliases, facts and human suppression',
        inputFingerprint=review_fingerprint(bundle))


class PreparedResourceTests(unittest.TestCase):
    def setUp(self):
        self.bundle = fixture()
        self.artifact, self.registry, self.migration, self.receipt = finalize(self.bundle, new_registry())

    def test_code_id_alias_migration_and_hidden_preservation(self):
        mapping = {r['legacyId']: r['resourceId'] for r in self.migration['aliases']}
        self.assertEqual(mapping['old-a'], mapping['older-a'])
        self.assertEqual(self.artifact['resources'][0]['id'], mapping['old-a'])
        self.assertEqual([mapping['hidden']], self.migration['suppressedResourceIds'])
        self.assertNotIn(mapping['hidden'], {r['id'] for r in self.artifact['resources']})
        # Snapshot replay cannot allocate new identities or manufacture updates.
        artifact, registry, migration, _ = finalize(self.bundle, self.registry, previous=self.artifact)
        self.assertEqual(self.artifact, artifact)
        self.assertEqual(self.registry, registry)
        self.assertEqual(self.migration, migration)

    def test_rename_url_and_reordered_runs_keep_reviewed_identity(self):
        updated = deepcopy(self.bundle)
        updated['payload']['resources'][0].update(name='Renamed service', website='https://example.org/new')
        updated['identityDecisions'].reverse()
        seal(updated)
        artifact, _, _, _ = finalize(updated, self.registry, previous=self.artifact)
        self.assertEqual(self.artifact['resources'][0]['id'], artifact['resources'][0]['id'])
        self.assertEqual([artifact['resources'][0]['id']], artifact['changeSet']['changed'])
        self.assertEqual(self.artifact['snapshot']['id'], artifact['snapshot']['predecessorId'])

    def test_review_stales_when_facts_taxonomy_selection_or_identity_changes(self):
        mutations = [lambda b: b['payload']['resources'][0].update(phone='456'),
            lambda b: b['payload']['taxonomy']['types'][0].update(definition='Changed meaning'),
            lambda b: b['payload']['starterSets'][0]['members'][0].update(contribution='Changed choice rationale'),
            lambda b: b['identityDecisions'][0].update(reason='Different boundary')]
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                changed = deepcopy(self.bundle); mutate(changed)
                with self.assertRaisesRegex(ValueError, 'Stale'):
                    finalize(changed, self.registry)

    def test_no_lost_reserve_or_incomplete_assessment(self):
        for mutation in (lambda b: b['payload']['resources'].clear(),
                         lambda b: b['assessments'].pop('hidden')):
            bad = deepcopy(self.bundle); mutation(bad); seal(bad)
            with self.assertRaises(ValueError): finalize(bad, self.registry)

    def test_hidden_merge_cannot_resurrect(self):
        bad = deepcopy(self.bundle)
        bad['identityDecisions'] = [dict(members=['old-a', 'older-a', 'hidden'], label='Same', reason='Conflict')]
        seal(bad)
        with self.assertRaisesRegex(ValueError, 'human-hidden'): finalize(bad, new_registry())

    def test_excluded_states_are_never_published(self):
        for state in ('not-offered', 'raw', 'suppressed'):
            bad = deepcopy(self.bundle); bad['assessments']['old-a']['state'] = state; seal(bad)
            with self.assertRaises(ValueError): finalize(bad, self.registry)

    def check_bad_resource(self, change, message):
        bad = deepcopy(self.artifact); change(bad['resources'][0])
        bad['resources'][0]['revision'] = revision(bad['resources'][0])
        with self.assertRaisesRegex(ValueError, message): validate_artifact(bad, self.registry)

    def test_sources_categories_and_types_are_closed_references(self):
        self.check_bad_resource(lambda r: r.update(sourceIds=['absent']), 'source references')
        self.check_bad_resource(lambda r: r.update(categories=['Housing']), 'category scope')
        self.check_bad_resource(lambda r: r.update(types=['absent']), 'taxonomy')
        self.check_bad_resource(lambda r: r.update(types=[]), 'supported Type')
        self.check_bad_resource(lambda r: r.update(forGroups=['invented']), 'taxonomy')

    def test_human_verification_approval_and_notes_never_export(self):
        for key in ('verifiedOn', 'curated', 'deleted', 'clientNote'):
            self.check_bad_resource(lambda r: r.update({key: None}), 'office-owned')
        self.assertIsNone(self.artifact['resources'][0]['researchedAt'])
        self.check_bad_resource(lambda r: r.pop('researchedAt'), 'explicit or null')

    def test_five_sections_and_state(self):
        self.check_bad_resource(lambda r: r.update(informationText='**Access**\nOld layout'), 'ordered standalone')
        self.check_bad_resource(lambda r: r.update(state='needs-resolution'), 'explanation')
        bad = deepcopy(self.bundle)
        bad['payload']['resources'][0].update(state='needs-resolution', resolutionReason='Intake unknown')
        bad['assessments']['old-a']['state'] = 'needs-resolution'; seal(bad)
        with self.assertRaisesRegex(ValueError, 'Starter member'): finalize(bad, self.registry)

    def test_schema_and_office_identity_fail_clearly(self):
        for changed in ({'schemaVersion': 2}, {'schemaVersion': True}, {'evaluationOnly': True}):
            bad = {**self.artifact, **changed}
            with self.assertRaises(ValueError): validate_artifact(bad)
        with self.assertRaisesRegex(ValueError, 'Office category IDs'):
            validate_artifact(self.artifact, office_category_ids=['Housing'])
        # Future optional fields are accepted after the producer recomputes hashes.
        future = build_snapshot({**self.artifact, 'futureOptional': {'a': 1}}, generated_at='2026-09-26T00:00:00Z')
        validate_artifact(future, self.registry)

    def test_narrow_scope_does_not_claim_disappearance(self):
        empty = deepcopy(self.artifact); empty['resources'] = []
        self.assertEqual([self.artifact['resources'][0]['id']], compare_snapshots(self.artifact, empty)['notObserved'])
        empty['scope']['categoryIds'] = ['food']
        self.assertEqual([], compare_snapshots(self.artifact, empty)['notObserved'])
        self.assertNotIn('deleted', compare_snapshots(self.artifact, empty))
        empty['scope'].update(categoryIds=['housing'], completeScope=False)
        self.assertEqual([], compare_snapshots(self.artifact, empty)['notObserved'])

    def test_considerations_cover_each_nonstarter_membership_once(self):
        base = deepcopy(self.artifact)
        base['starterSets'][0]['members'] = []
        base = build_snapshot(base, generated_at='2026-09-26T00:00:00Z')
        with self.assertRaisesRegex(ValueError, 'non-starter membership'): validate_artifact(base, self.registry)
        item = dict(resourceId=base['resources'][0]['id'], categoryId='housing', reason='Adds a local intake route.')
        base['considerations'] = [item]
        base = build_snapshot(base, generated_at='2026-09-26T00:00:00Z')
        validate_artifact(base, self.registry)
        for bad_items in ([item, item], [{**item, 'categoryId': 'food'}], [{**item, 'reason': ''}]):
            bad = build_snapshot({**base, 'considerations': bad_items}, generated_at='2026-09-26T00:00:00Z')
            with self.assertRaises(ValueError): validate_artifact(bad, self.registry)

    def test_withdrawal_requires_evidence_and_admin_action(self):
        event = dict(resourceId=self.artifact['resources'][0]['id'], reason='Evidence says intake closed',
                     sourceIds=[self.artifact['sources'][0]['id']], action='admin-review')
        changed = build_snapshot({**self.artifact, 'withdrawnEvents': [event]}, generated_at='2026-09-26T00:00:00Z')
        validate_artifact(changed, self.registry)
        changed['withdrawnEvents'][0]['action'] = 'delete'
        changed = build_snapshot(changed, generated_at='2026-09-26T00:00:00Z')
        with self.assertRaisesRegex(ValueError, 'automatically remove'): validate_artifact(changed, self.registry)

    def test_transport_export_is_repeatable_and_refuses_replace(self):
        import gzip
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); bundle = root/'bundle.json'; bundle.write_bytes(encoded(self.bundle))
            registry = root/'registry.json'; output = root/'delivery'
            first = export_bundle(bundle, registry, output, initialize_registry=True)
            second = export_bundle(bundle, registry, output)
            self.assertEqual(first, second)
            self.assertEqual((output/'prepared-resources.json').read_bytes(), gzip.decompress((output/'prepared-resources.json.gz').read_bytes()))
            with self.assertRaisesRegex(ValueError, 'already exists'):
                export_bundle(bundle, registry, output, initialize_registry=True)
            (output/'prepared-resources.json').write_text('modified')
            before = registry.read_bytes()
            with self.assertRaisesRegex(ValueError, 'Refusing to replace'): export_bundle(bundle, registry, output)
            self.assertEqual(before, registry.read_bytes())


if __name__ == '__main__': unittest.main()
