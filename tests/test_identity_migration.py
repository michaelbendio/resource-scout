from copy import deepcopy
import unittest

from resource_research_agent.resource_identity import (
    IdentityError, new_registry, register_reviewed, migrate_reviewed_identities,
    resolve_identity, validate_registry)
from resource_research_agent.prepared_export import finalize
from tests.test_prepared_resources import fixture


class IdentityMigrationTests(unittest.TestCase):
    def setUp(self):
        self.registry, self.ids = register_reviewed(new_registry(),
            source_namespace='mesa-legacy-resource', decisions=[
                dict(members=[name], label=name, reason='Initially distinct')
                for name in ('old-a', 'older-a', 'hidden')])
        self.decision = dict(fromResourceId=self.ids['older-a'], toResourceId=self.ids['old-a'],
            reason='Reviewed evidence confirms the same program and intake',
            evidence='Preserved source comparison and supervisor decision')

    def apply(self, registry=None, decisions=None, migration_id='reviewed-001'):
        return migrate_reviewed_identities(registry or self.registry,
            migration_id=migration_id, decisions=decisions or [self.decision])

    def test_merge_preserves_history_and_exports_old_canonical_reference(self):
        original = deepcopy(self.registry)
        migrated = self.apply()
        artifact, updated, migration, _ = finalize(fixture(), migrated)
        self.assertEqual(self.registry, original)
        self.assertEqual(original['nextSequence'], migrated['nextSequence'])
        self.assertEqual(set(original['resources']), set(migrated['resources']))
        self.assertEqual(original['events'], migrated['events'][:-1])
        self.assertEqual(self.ids['old-a'], artifact['resources'][0]['id'])
        redirect = dict(legacyId=self.ids['older-a'], resourceId=self.ids['old-a'])
        self.assertIn(redirect, migration['aliases'])
        self.assertEqual([redirect], migration['canonicalMerges'])
        self.assertEqual([self.ids['hidden']], migration['suppressedResourceIds'])
        self.assertEqual('older-a', updated['resources'][self.ids['older-a']]['initialLabel'])

    def test_rediscovery_matching_retired_id_cannot_resurrect_it(self):
        migrated = self.apply()
        updated, mapping = register_reviewed(migrated, source_namespace='next-run',
            decisions=[dict(members=['rediscovered'], match=self.ids['older-a'],
                label='Renamed program', reason='Same reviewed intake')])
        self.assertEqual(self.ids['old-a'], mapping['rediscovered'])
        self.assertEqual(migrated['nextSequence'], updated['nextSequence'])

    def test_duplicate_migration_and_invalid_plans_fail_without_input_changes(self):
        migrated = self.apply()
        with self.assertRaisesRegex(IdentityError, 'already applied'):
            self.apply(migrated)
        original = deepcopy(self.registry)
        for change in ({'toResourceId': 'unknown'}, {'reason': ''}, {'evidence': ''},
                       {'toResourceId': self.ids['older-a']}):
            with self.subTest(change=change), self.assertRaises(IdentityError):
                self.apply(decisions=[dict(self.decision, **change)])
        self.assertEqual(original, self.registry)

    def test_chain_resolves_and_cycles_or_dangling_redirects_are_rejected(self):
        migrated = self.apply()
        chained = self.apply(migrated, migration_id='reviewed-002', decisions=[dict(
            self.decision, fromResourceId=self.ids['old-a'], toResourceId=self.ids['hidden'])])
        self.assertEqual(self.ids['hidden'], resolve_identity(chained, self.ids['older-a']))
        for target in (self.ids['older-a'], 'unknown'):
            bad = deepcopy(chained)
            bad['resources'][self.ids['hidden']]['redirectTo'] = target
            with self.assertRaises(IdentityError):
                validate_registry(bad)


if __name__ == '__main__':
    unittest.main()
