import copy
from pathlib import Path
import tempfile
import unittest

from resource_research_agent.resource_identity import (
    IdentityError, fingerprint, load_registry, new_registry, register_reviewed, save_registry,
)


class IdentityTests(unittest.TestCase):
    def decision(self, members, match=None, label="Program"):
        return dict(members=members, match=match, label=label, reason="Reviewed same program and intake.")

    def register(self, registry, decisions, namespace="legacy-mesa"):
        return register_reviewed(registry, source_namespace=namespace, decisions=decisions)

    def test_replay_and_rename_preserve_code_allocated_identity(self):
        original = new_registry()
        before = copy.deepcopy(original)
        first, ids = self.register(original, [self.decision(["old-a", "old-b"])])
        second, again = self.register(first, [self.decision(["old-a", "old-b"], label="Renamed")])
        self.assertEqual(first, second)
        self.assertEqual(ids, again)
        self.assertEqual(original, before)
        self.assertEqual(ids["old-a"], ids["old-b"])
        self.assertTrue(ids["old-a"].startswith("sr_"))

    def test_new_run_reuses_identity_only_with_reviewed_match(self):
        registry, ids = self.register(new_registry(), [self.decision(["old"])])
        updated, new_ids = self.register(registry, [self.decision(["new-row"], ids["old"])], "new-run")
        self.assertEqual(ids["old"], new_ids["new-row"])
        self.assertEqual(len(updated["resources"]), 1)

    def test_model_cannot_supply_new_canonical_id(self):
        with self.assertRaisesRegex(IdentityError, "Unknown proposed match"):
            self.register(new_registry(), [self.decision(["x"], "sr_model-invented")])

    def test_conflicting_existing_identities_are_not_silently_merged(self):
        registry, _ = self.register(new_registry(), [self.decision(["a"]), self.decision(["b"])])
        with self.assertRaisesRegex(IdentityError, "Conflicting existing"):
            self.register(registry, [self.decision(["a", "b"])])

    def test_duplicate_members_block_batch_without_mutating_registry(self):
        registry = new_registry()
        with self.assertRaisesRegex(IdentityError, "Repeated"):
            self.register(registry, [self.decision(["a"]), self.decision(["a"])])
        self.assertEqual(registry["resources"], {})

    def test_restore_continuity_and_reject_stale_write_or_missing_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "registry.json"
            with self.assertRaisesRegex(IdentityError, "Registry missing"):
                load_registry(path)
            registry = new_registry()
            save_registry(path, registry, expected_fingerprint=None)
            updated, ids = self.register(registry, [self.decision(["a"])])
            save_registry(path, updated, expected_fingerprint=fingerprint(registry))
            restored = load_registry(path)
            _, again = self.register(restored, [self.decision(["a"])])
            self.assertEqual(ids, again)
            with self.assertRaisesRegex(IdentityError, "changed since"):
                save_registry(path, registry, expected_fingerprint=fingerprint(registry))


if __name__ == "__main__":
    unittest.main()
