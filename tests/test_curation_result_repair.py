import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from resource_research_agent.curation_result_repair import enforce_structural_changes, repair_once
from resource_research_agent.scout_curation_runner import validate_links, write_once


class CurationResultRepairTests(unittest.TestCase):
    def results(self):
        real = {"id": "real", "candidateIds": ["1"], "name": "University online tutoring",
                "description": "K-12 tutoring", "informationText": "Utah students; online access",
                "phone": "435-555-0100", "hours": "Confirm hours", "address": "Online",
                "categories": ["education"], "website": "https://example.org/tutoring",
                "forGroups": [], "categoryFilters": {}, "pdfs": []}
        dummy = {**real, "id": "stray", "name": "Duplicate placeholder remove",
                 "description": "Duplicate placeholder", "informationText": "Duplicate placeholder remove",
                 "phone": "", "hours": "", "address": "Campus address"}
        original = {"assignmentSha256": "sealed", "categoryId": "education", "scoutCurationResultSchemaVersion": 1,
                    "resources": [real, dummy], "candidateDispositions": [
                        {"candidateId": "1", "disposition": "curated", "resourceIds": ["real"], "reason": ""}]}
        corrected = copy.deepcopy(original); corrected["resources"].pop()
        return original, corrected

    def test_known_placeholder_defect_can_be_corrected_without_losing_candidate_or_facts(self):
        original, corrected = self.results()
        with self.assertRaises(ValueError):
            validate_links({}, original)
        enforce_structural_changes(original, corrected, {})
        validate_links({}, corrected)
        self.assertEqual(original['resources'][0], corrected['resources'][0])
        self.assertEqual(original['candidateDispositions'], corrected['candidateDispositions'])

    def test_fact_edits_decision_changes_real_deletions_and_new_resources_rejected(self):
        original, good = self.results()
        mutations = [
            lambda r: r['resources'][0].update(informationText='Different eligibility'),
            lambda r: r['candidateDispositions'][0].update(disposition='omitted', reason='Remove difficult case'),
            lambda r: r.update(resources=[]),
            lambda r: r['resources'].append({**r['resources'][0], 'id': 'new'}),
            lambda r: r.update(assignmentSha256='different'),
        ]
        for mutate in mutations:
            changed = copy.deepcopy(good); mutate(changed)
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                enforce_structural_changes(original, changed, {})

    def test_making_links_consistent_by_keeping_placeholder_is_rejected(self):
        original, _ = self.results()
        changed = copy.deepcopy(original)
        changed['candidateDispositions'][0]['resourceIds'].append('stray')
        with self.assertRaisesRegex(ValueError, 'placeholder'):
            enforce_structural_changes(original, changed, {})

    def test_candidate_cannot_be_moved_to_previously_unrelated_program(self):
        original, corrected = self.results()
        other = {**original['resources'][0], 'id': 'other', 'candidateIds': ['2']}
        original['resources'].append(other); corrected['resources'].append(copy.deepcopy(other))
        original['candidateDispositions'].append({'candidateId':'2', 'disposition':'curated', 'reason':'', 'resourceIds':['other']})
        corrected['candidateDispositions'] = copy.deepcopy(original['candidateDispositions'])
        corrected['resources'][1]['candidateIds'].append('1')
        corrected['candidateDispositions'][0]['resourceIds'].append('other')
        with self.assertRaisesRegex(ValueError, 'invented'):
            enforce_structural_changes(original, corrected, {})

    def test_placeholder_with_distinct_evidence_or_identity_is_not_silently_dropped(self):
        for changes in ({'website': 'https://example.org/different'}, {'phone': '555'},
                        {'informationText': 'Children must be accompanied by an adult'},
                        {'categories': ['education', 'housing']}, {'candidateIds': ['2']}):
            original, corrected = self.results(); original['resources'][1].update(changes)
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                enforce_structural_changes(original, corrected, {})
        original, corrected = self.results()
        with self.assertRaises(ValueError):
            enforce_structural_changes(original, corrected, {'previouslyCuratedResources': [{'id': 'stray'}]})
        original['candidateDispositions'][0]['resourceIds'].append('stray')
        with self.assertRaises(ValueError):
            enforce_structural_changes(original, corrected, {})

    def inputs(self, root, original):
        for name in ('assignment.json', 'view.json', 'prior-resources.json', 'schema.json'):
            (root / name).write_text('{}')
        (root / 'result.json').write_text(json.dumps(original))

    def invoke(self, root, original, execute):
        def validate(value):
            validate_links({}, value)
            return value
        return repair_once(root, original, {}, ValueError('Inconsistent candidate/resource links: 1'),
                           execute=execute, validate=validate, seal=write_once, heartbeat=lambda _: None,
                           binary='never-call', model='test', effort='high', timeout=3600)

    def test_single_attempt_no_search_and_result_reused_across_restart(self):
        original, corrected = self.results()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); self.inputs(root, original); raw = (root / 'result.json').read_bytes()
            def execute(folder, **options):
                self.assertFalse(options['search'])
                self.assertEqual('high', options['effort'])
                self.assertEqual(600, options['timeout'])
                (folder / 'result.json').write_text(json.dumps(corrected))
            worker = Mock(side_effect=execute)
            self.assertEqual(corrected, self.invoke(root, original, worker))
            self.assertEqual(corrected, self.invoke(root, original, worker))
            worker.assert_called_once()
            self.assertEqual(raw, (root / 'result.json').read_bytes())
            self.assertTrue((root / 'structural-repair-1/accepted-repair.json').exists())

    def test_failed_correction_never_gets_another_paid_attempt_after_restart(self):
        original, _ = self.results()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); self.inputs(root, original)
            def execute(folder, **_):
                (folder / 'result.json').write_text(json.dumps(original))
            worker = Mock(side_effect=execute)
            for _ in range(2):
                with self.assertRaises(ValueError):
                    self.invoke(root, original, worker)
            worker.assert_called_once()
            self.assertFalse((root / 'structural-repair-1/accepted-repair.json').exists())

    def test_interrupted_unsuccessful_correction_does_not_repeat(self):
        original, _ = self.results()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); self.inputs(root, original)
            folder = root / 'structural-repair-1'; folder.mkdir()
            (folder / 'events.jsonl').write_text('{"type":"turn.failed"}')
            (folder / 'execution.json').write_text('{"exitCode":1}')
            worker = Mock()
            with self.assertRaisesRegex(ValueError, 'exhausted'):
                self.invoke(root, original, worker)
            worker.assert_not_called()


if __name__ == '__main__':
    unittest.main()
