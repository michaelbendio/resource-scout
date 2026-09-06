from __future__ import annotations

import io
import json
import tempfile
import unittest
import zipfile
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from resource_research_agent.improvement_packages import ImprovementError, read_package, write_package
from resource_research_agent.scout_improvement import ImprovementWorkflow
from resource_research_agent.storage import ResearchStore


def fixture_package():
    return {
        'resourcePackageSchemaVersion': 3, 'packageVersion': 10, 'officeName': 'Test TSO',
        'categories': [{'id': 'food', 'label': 'Food', 'filters': ['Pantries']}],
        'forGroups': ['Seniors'], 'categoryMigrations': [], 'deletions': [], 'deletionRequests': [],
        'changes': [{'id': 'old-history', 'type': 'resource', 'action': 'updated', 'targetId': 'r1',
                     'timestamp': '2026-09-01T12:00:00Z', 'description': 'Local contact confirmed'}],
        'resources': [
            {'id': rid, 'name': 'Test pantry ' + rid, 'description': 'Food in Test County.',
             'informationText': 'Bring photo ID. Maria can help in Spanish. Call before visiting.',
             'phone': '555-0100', 'website': 'https://example.org/', 'address': 'Original address',
             'hours': 'Tuesday', 'verifiedOn': '08/26', 'categories': ['food'], 'categoryFilters': {'food': ['Pantries']},
             'forGroups': ['Seniors'], 'pdfs': [{'id': 'pdf1', 'name': 'Local guide', 'path': 'pdfs/guide.pdf'}],
             'lastModified': '2026-09-01T12:00:00.000Z', 'localKnowledge': {'contact': 'Maria'}}
            for rid in ('r1', 'r2')], 'futureField': {'preserve': True},
    }


def result_for(assignment):
    result = deepcopy(assignment['outputContract'])
    result['assignmentSha256'] = assignment['assignmentSha256']
    result['evidenceSources'] = [{'url': 'https://example.org/help', 'accessedOn': '2026-09-05', 'excerpt': 'Synthetic QA source, not real research.'}]
    if assignment['stage'].startswith('audit:'):
        result.update(findings=[], researchNotes='Synthetic QA independent-check fixture.')
    else:
        result.update(description='Free groceries in Test County.',
                      informationSections={
                          'programsAndServices': 'Food boxes and fresh produce.',
                          'eligibilityRequirements': 'Bring photo ID.',
                          'howToBestConnect': 'Call before visiting. Ask for Maria.',
                          'access': 'Test County. Maria can help in Spanish.',
                          'importantInformationToKnow': 'Food varies by day.'},
                      preservationNotes=['Preserved the ID rule, local contact, language help, and call-ahead instruction.'],
                      reviewNotes=[])
        if assignment['stage'] == 'reconcile':
            result['resolutions'] = [{'findingId': name + ':' + f['id'], 'status': 'resolved', 'reason': 'Addressed in the proposed text.'}
                                     for name, audit in assignment['audits'].items() for f in audit['findings']]
    return result


class ScoutImprovementTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'scout.sqlite3'
        self.store = ResearchStore(self.path)
        self.flow = ImprovementWorkflow(self.store)
        self.data = fixture_package()
        self.assets = {'pdfs/guide.pdf': b'%PDF-1.4\nSynthetic attachment integrity fixture\n%%EOF'}
        self.payload = write_package(self.data, self.assets)
        self.project = self.flow.prepare(self.payload, 'Test TSO', ['r1', 'r2'], historical=True)
        self.pid = self.project['id']

    def tearDown(self):
        self.temp.cleanup()

    def finish(self):
        while assignment := self.flow.next_assignment(self.pid):
            self.flow.submit(self.pid, assignment['stage'], result_for(assignment))
        return self.flow.view(self.pid)

    def connect(self, data=None, assets=None):
        view = self.flow.view(self.pid)
        return self.flow.connect_latest(self.pid, view['revision'], write_package(data or self.data, assets or self.assets), 'Test TSO')

    def review(self, rid='r1', **kwargs):
        view = self.flow.view(self.pid)
        return self.flow.review(self.pid, view['revision'], rid, kwargs.pop('decision', 'curated'),
                                kwargs.pop('choices', {'description': 'proposed', 'informationText': 'proposed'}),
                                'QA reviewer; not human approval', **kwargs)

    def test_frozen_inputs_restart_and_idempotent_assignments(self):
        again = self.flow.prepare(self.payload, 'Test TSO', ['r1', 'r2'], historical=True)
        self.assertEqual(self.pid, again['id'])
        assignment = self.flow.next_assignment(self.pid)
        with patch('resource_research_agent.scout_improvement.load_writing_guidance', side_effect=AssertionError('No live guidance on resume')):
            restarted = ImprovementWorkflow(ResearchStore(self.path))
            self.assertEqual(assignment, restarted.next_assignment(self.pid))
            response = result_for(assignment)
            restarted.submit(self.pid, assignment['stage'], response)
            before = restarted.view(self.pid)['revision']
            restarted.submit(self.pid, assignment['stage'], response)
            self.assertEqual(before, restarted.view(self.pid)['revision'])
            changed = deepcopy(response); changed['description'] = 'Overwritten'
            with self.assertRaisesRegex(ImprovementError, 'sealed'):
                restarted.submit(self.pid, assignment['stage'], changed)
        with self.store.connect() as connection:
            saved = connection.execute('SELECT payload FROM scout_improvement_packages WHERE sha256=?', (self.project['baseSha256'],)).fetchone()
        self.assertEqual(self.payload, bytes(saved['payload']))

    def test_invalid_results_do_not_complete_research(self):
        assignment = self.flow.next_assignment(self.pid)
        for field, value in [('assignmentSha256', 'wrong'), ('description', ''), ('verifiedOn', '09/26'),
                             ('scoutImprovementResultSchemaVersion', True), ('informationSections', {}), ('resourceId', [])]:
            result = result_for(assignment); result[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.flow.submit(self.pid, assignment['stage'], result)
            self.assertFalse(self.flow.view(self.pid)['resources'][0]['research'][0]['completed'])

    def test_all_independent_checks_and_reconciliation_required(self):
        primary = self.flow.next_assignment(self.pid)
        self.flow.submit(self.pid, 'primary', result_for(primary))
        audit = self.flow.next_assignment(self.pid)
        self.assertEqual('ChatGPT', audit['researcher'])
        self.assertFalse(self.flow.view(self.pid)['resources'][0]['proposal'])
        with self.assertRaises(ImprovementError):
            self.review()
        self.finish()
        view = self.flow.view(self.pid)
        self.assertTrue(all(len(r['research']) == 5 and all(s['completed'] for s in r['research']) for r in view['resources']))
        self.assertTrue(all(r['review'] is None for r in view['resources']))

    def test_every_finding_requires_reconciliation_and_material_human_resolution(self):
        primary = self.flow.next_assignment(self.pid); self.flow.submit(self.pid, 'primary', result_for(primary))
        audit = self.flow.next_assignment(self.pid)
        response = result_for(audit)
        response['findings'] = [{'id': 'local-rule', 'field': 'informationText', 'severity': 'material', 'summary': 'Source and local instructions conflict.'}]
        self.flow.submit(self.pid, audit['stage'], response)
        for _ in range(2):
            a = self.flow.next_assignment(self.pid); self.flow.submit(self.pid, a['stage'], result_for(a))
        a = self.flow.next_assignment(self.pid); self.assertEqual('reconcile', a['stage'])
        response = result_for(a); response['resolutions'] = []
        with self.assertRaises(ImprovementError): self.flow.submit(self.pid, 'reconcile', response)
        response = result_for(a); response['resolutions'][0]['status'] = 'needs-review'
        self.flow.submit(self.pid, 'reconcile', response)
        self.connect()
        with self.assertRaisesRegex(ImprovementError, 'Human resolution'): self.review()
        view = self.review(finding_notes={'ChatGPT:local-rule': 'QA resolution: preserve local instructions and flag uncertainty.'})
        self.assertEqual('curated', view['resources'][0]['review']['decision'])

    def test_latest_package_required_wrong_office_older_and_missing_resource(self):
        self.finish()
        with self.assertRaisesRegex(ImprovementError, 'Reconnect'): self.review()
        for office, version in [('Other TSO', 10), ('Test TSO', 9)]:
            data = deepcopy(self.data); data['officeName'] = office; data['packageVersion'] = version
            with self.assertRaises(ImprovementError): self.connect(data)
        data = deepcopy(self.data); data['resources'] = data['resources'][1:]
        self.connect(data)
        with self.assertRaisesRegex(ImprovementError, 'absent'): self.review()

    def test_deletion_and_pending_deletion_never_resurrect_records(self):
        self.finish()
        for field in ('deletions', 'deletionRequests'):
            data = deepcopy(self.data); data[field] = [{'kind': 'resource', 'targetId': 'r1', 'requestedAt': '2026-09-05T00:00:00Z'}]
            self.connect(data)
            with self.assertRaisesRegex(ImprovementError, 'deletion'): self.review()

    def test_three_way_merge_keeps_new_contacts_assets_unknown_fields_and_history(self):
        self.finish()
        current = deepcopy(self.data); current['packageVersion'] = 11
        current['resources'][0].update(phone='555-0200', address='New office', hours='Friday', localKnowledge={'contact': 'Maria', 'extension': 42})
        assets = {'pdfs/guide.pdf': b'%PDF-1.4\nRevised office attachment\n%%EOF'}
        self.connect(current, assets); self.review()
        view = self.flow.view(self.pid)
        export = self.flow.prepare_export(self.pid, view['revision'])
        payload = self.flow.export_bytes(self.pid, export['exportId'])
        package = read_package(payload); updated = package['resources']['r1']
        for field, value in current['resources'][0].items():
            if field not in ('description', 'informationText', 'lastModified'):
                self.assertEqual(value, updated[field], field)
        self.assertEqual(assets, package['assets'])
        self.assertEqual(assets['pdfs/guide.pdf'], self.flow.attachment_bytes(self.pid, 'pdfs/guide.pdf', which='latest'))
        self.assertEqual(self.assets['pdfs/guide.pdf'], self.flow.attachment_bytes(self.pid, 'pdfs/guide.pdf'))
        self.assertEqual(current['categories'], package['data']['categories'])
        self.assertEqual(current['futureField'], package['data']['futureField'])
        self.assertEqual(current['changes'], package['data']['changes'][:-1])
        self.assertEqual(12, package['data']['packageVersion'])
        self.assertEqual({'r1'}, set(package['resources']))
        self.assertEqual('08/26', updated['verifiedOn'])
        self.assertNotIn('writingGuidance', json.dumps(package['data']))
        self.assertNotIn('proposal', updated)
        self.assertIn('Maria', updated['informationText'])
        original = self.flow.view(self.pid)['resources'][0]['original']
        self.assertEqual(self.data['resources'][0], original)

    def test_same_field_conflict_needs_explicit_choice_and_note(self):
        self.finish()
        current = deepcopy(self.data); current['resources'][0]['description'] = 'Later office wording'
        view = self.connect(current)
        self.assertTrue(view['resources'][0]['fields']['description']['conflict'])
        with self.assertRaisesRegex(ImprovementError, 'Explain'): self.review()
        self.review(choices={'description': 'current', 'informationText': 'proposed'}, note='Keep the newer office description.')
        view = self.flow.view(self.pid); export = self.flow.prepare_export(self.pid, view['revision'])
        updated = read_package(self.flow.export_bytes(self.pid, export['exportId']))['resources']['r1']
        self.assertEqual('Later office wording', updated['description'])

    def test_edit_reconnect_decline_and_stale_revisions(self):
        self.finish(); self.connect(); view = self.review()
        old = view['revision']; row = view['resources'][0]
        edited = self.flow.edit(self.pid, old, 'r1', 'Edited locally', row['proposal']['informationSections'], 'QA')
        self.assertIsNone(edited['resources'][0]['review'])
        with self.assertRaisesRegex(ImprovementError, 'another window'):
            self.flow.review(self.pid, old, 'r1', 'curated', {}, 'QA')
        self.review(); data = deepcopy(self.data); data['resources'][0]['phone'] = '555-0300'
        self.assertIsNone(self.connect(data)['resources'][0]['review'])
        view = self.review(decision='declined')
        self.assertFalse(view['resources'][0]['packaged'])
        with self.assertRaisesRegex(ImprovementError, 'No curated'):
            self.flow.prepare_export(self.pid, view['revision'])

    def test_cancelled_save_idempotent_export_and_acknowledgement(self):
        self.finish(); self.connect(); self.review()
        view = self.flow.view(self.pid); first = self.flow.prepare_export(self.pid, view['revision'])
        view = self.flow.view(self.pid)
        self.assertFalse(view['resources'][0]['packaged'])
        second = self.flow.prepare_export(self.pid, view['revision'])
        self.assertEqual(first['exportId'], second['exportId'])
        self.assertEqual(self.flow.export_bytes(self.pid, first['exportId']), self.flow.export_bytes(self.pid, second['exportId']))
        with self.assertRaisesRegex(ImprovementError, 'does not match'):
            self.flow.acknowledge_export(self.pid, view['revision'], first['exportId'], 'bad-sha')
        saved = self.flow.acknowledge_export(self.pid, view['revision'], first['exportId'], first['manifest']['packageSha256'])
        self.assertTrue(saved['resources'][0]['packaged']); self.assertFalse(saved['resources'][1]['packaged'])
        restarted = ImprovementWorkflow(ResearchStore(self.path))
        self.assertTrue(restarted.view(self.pid)['resources'][0]['packaged'])
        self.assertEqual('export-saved', restarted.events(self.pid)[-1]['action'])

    def test_changed_review_invalidates_pending_save_acknowledgement(self):
        self.finish(); self.connect(); self.review()
        view = self.flow.view(self.pid); export = self.flow.prepare_export(self.pid, view['revision'])
        view = self.review(decision='declined')
        with self.assertRaisesRegex(ImprovementError, 'Review changed'):
            self.flow.acknowledge_export(self.pid, view['revision'], export['exportId'], export['manifest']['packageSha256'])
        self.assertFalse(self.flow.view(self.pid)['resources'][0]['packaged'])

    def test_next_batch_requires_a_fresh_current_package_connection(self):
        self.finish(); self.connect(); self.review()
        view = self.flow.view(self.pid); export = self.flow.prepare_export(self.pid, view['revision'])
        view = self.flow.view(self.pid)
        self.flow.acknowledge_export(self.pid, view['revision'], export['exportId'], export['manifest']['packageSha256'])
        with self.assertRaisesRegex(ImprovementError, 'Reconnect'): self.review('r2')
        self.connect()
        view = self.review('r2')
        self.assertEqual('curated', view['resources'][1]['review']['decision'])

    def test_archive_validation_and_required_assets(self):
        with self.assertRaisesRegex(ImprovementError, 'Missing PDF'): read_package(write_package(self.data, {}))
        data = deepcopy(self.data); data['resources'].append(deepcopy(data['resources'][0]))
        with self.assertRaisesRegex(ImprovementError, 'Duplicate'): read_package(write_package(data, self.assets))
        for name in ('../escape.pdf', '/escape.pdf', 'folder\\escape.pdf'):
            stream = io.BytesIO()
            with zipfile.ZipFile(stream, 'w') as archive:
                archive.writestr('tso-resources.json', json.dumps(self.data)); archive.writestr(name, b'bad')
            with self.assertRaisesRegex(ImprovementError, 'Unsafe'): read_package(stream.getvalue())


if __name__ == '__main__':
    unittest.main()
