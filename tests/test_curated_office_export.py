"""Exercise the generated workbench's real ZIP boundary in an isolated browser."""
from __future__ import annotations

import base64
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
import zipfile

from resource_research_agent.scout_review import render_scout_review_seed

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None


class CuratedOfficeExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if sync_playwright is None:
            raise unittest.SkipTest('Playwright is required for generated-workbench ZIP checks')
        chrome = Path('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
        executable = str(chrome) if chrome.exists() else shutil.which('chromium') or shutil.which('google-chrome')
        if not executable:
            raise unittest.SkipTest('Chrome or Chromium is required')
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch(executable_path=executable, headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='scout-office-export-')
        self.addCleanup(self.temp.cleanup)
        internal = {'privateNote': 'INTERNAL_ONLY', 'futureExtension': {'score': 42}}
        resource = {
            'id': 'curated', 'name': 'Local help', 'phone': '555-0100',
            'address': '12 Main St', 'website': 'https://example.org', 'hours': '',
            'description': 'Public description', 'informationText': '**Services**\nPublic details',
            'verifiedOn': '09/26', 'lastModified': '2026-09-14T10:00:00Z',
            'categories': ['housing', 'food'],
            'categoryFilters': {'housing': ['Rent'], 'food': ['Pantry']},
            'forGroups': ['Veterans'],
            'pdfs': [{'id': 'flyer', 'name': 'Flyer.pdf', 'path': 'assets/flyer.pdf', **internal}],
            'openQuestions': [{'id': 'q', 'question': 'INTERNAL_ONLY question',
                               'explanation': 'INTERNAL_ONLY evidence', 'status': 'open',
                               'resolution': '', 'history': []},
                              {'id': 'still-open', 'question': 'INTERNAL_ONLY unresolved',
                               'explanation': 'INTERNAL_ONLY uncertainty', 'status': 'open', 'resolution': ''}],
            'informationSections': {'research': 'INTERNAL_ONLY'}, **internal,
        }
        seed = {
            'resourcePackageSchemaVersion': 3, 'packageVersion': 7,
            'lastModified': '2026-09-14T10:00:00Z',
            'categories': [{'id': 'housing', 'label': 'Housing', 'active': True, 'filters': ['Rent'], **internal},
                           {'id': 'food', 'label': 'Food', 'active': False, 'filters': ['Pantry'], **internal},
                           {'id': 'unused', 'label': 'Unused'}],
            'forGroups': ['Veterans', 'Unused'],
            'resources': [resource, {**resource, 'id': 'uncurated', 'pdfs': [], 'pdf': ''}],
            'changes': [{'id': 'edit', 'type': 'resource', 'action': 'updated', 'targetId': 'curated',
                         'targetName': 'Local help', 'description': 'Updated public hours',
                         'timestamp': '2026-09-14T10:00:00Z', 'categoryIds': ['housing'], **internal}],
            'categoryMigrations': [], 'deletionRequests': [], 'deletions': [],
            'astraEditorialReview': internal, 'futureResearchMetadata': internal,
        }
        artifact = render_scout_review_seed(seed, location_name='QA', source_sha256='a' * 64,
                                            category_ids=['housing', 'food', 'unused'])
        path = Path(self.temp.name) / artifact.filename
        path.write_bytes(artifact.content)
        self.context = self.browser.new_context()
        self.addCleanup(self.context.close)
        self.page = self.context.new_page()
        self.errors = []
        self.page.on('pageerror', lambda error: self.errors.append(str(error)))
        self.page.goto(path.as_uri())
        self.page.wait_for_function('typeof buildScoutReviewSelectionPackageData === "function"')
        self.page.evaluate('''async () => {
          const r = data.resources.find(r => r.id === 'curated');
          r.openQuestions[0].status = 'resolved';
          r.openQuestions[0].resolution = 'INTERNAL_ONLY answer';
          r.openQuestions[0].history = [{status:'resolved', resolution:'INTERNAL_ONLY answer', changedAt:'2026-09-14T11:00:00Z'}];
          r.description = 'Human-approved public wording';
          persist();
          setScoutReviewResourceCurated('curated', true);
          await savePDF('assets/flyer.pdf', new Blob(['%PDF-1.4 synthetic unchanged bytes'], {type:'application/pdf'}));
        }''')

    def test_curated_zip_is_clean_and_workbench_retains_records_after_reload(self):
        before = self.page.evaluate('structuredClone(data)')
        output = self.page.evaluate('''async () => {
          let blob;
          await saveCurrentResourcePackage({kind:'file-handle', suggestedName:'qa-resource-package.zip',
            handle:{createWritable:async()=>({write:async value=>{blob=value}, close:async()=>{}, abort:async()=>{}})}},
            {showSuccessToast:false});
          return btoa(String.fromCharCode(...new Uint8Array(await blob.arrayBuffer())));
        }''')
        with zipfile.ZipFile(io.BytesIO(base64.b64decode(output))) as archive:
            self.assertEqual(set(archive.namelist()), {'tso-resources.json', 'assets/', 'assets/flyer.pdf'})
            self.assertEqual(archive.read('assets/flyer.pdf'), b'%PDF-1.4 synthetic unchanged bytes')
            packet = json.loads(archive.read('tso-resources.json'))
        self.assertNotIn('INTERNAL_ONLY', json.dumps(packet))
        self.assertEqual(set(packet), {'resourcePackageSchemaVersion', 'packageVersion', 'packageCreatedAt',
                                      'lastModified', 'categories', 'categoryMigrations', 'forGroups',
                                      'resources', 'changes', 'deletionRequests', 'deletions'})
        self.assertEqual(packet['packageVersion'], 8)
        self.assertEqual([r['id'] for r in packet['resources']], ['curated'])
        original = next(r for r in before['resources'] if r['id'] == 'curated')
        resource = packet['resources'][0]
        for key in ('id', 'name', 'phone', 'address', 'website', 'hours', 'description', 'informationText',
                    'verifiedOn', 'lastModified', 'categories', 'categoryFilters', 'forGroups'):
            self.assertEqual(resource[key], original[key], key)
        self.assertEqual(resource['pdfs'], [{'id': 'flyer', 'name': 'Flyer.pdf', 'path': 'assets/flyer.pdf'}])
        self.assertEqual({c['id'] for c in packet['categories']}, {'housing', 'food'})
        self.assertFalse(next(c for c in packet['categories'] if c['id'] == 'food')['active'])
        self.assertEqual(packet['forGroups'], ['Veterans'])
        self.assertEqual(packet['changes'][0]['description'], 'Updated public hours')
        self.assertEqual(packet['categoryMigrations'], [])
        self.assertEqual(packet['deletionRequests'], [])
        self.assertEqual(packet['deletions'], [])
        self.assertTrue(self.page.evaluate('(p) => validateResourcePackageData(p).ok', packet))
        # Successful packaging archives the selection; its full edited record stays in the overlay.
        self.page.reload()
        self.page.wait_for_function('typeof scoutReviewState === "object"')
        saved = self.page.evaluate("scoutReviewState.resourceOverrides.find(r => r.id === 'curated')")
        self.assertEqual(saved, original)
        self.assertEqual(self.page.evaluate('data.astraEditorialReview'), before['astraEditorialReview'])
        self.assertEqual(self.page.evaluate("data.resources.map(r => r.id)"), ['uncurated'])
        self.assertEqual(self.errors, [])

    def test_export_projection_does_not_mutate_source_or_strip_full_draft(self):
        results = self.page.evaluate('''() => {
          const before = JSON.stringify(data);
          const empty = buildScoutReviewSelectionPackageData(data, []);
          const office = buildScoutReviewSelectionPackageData(data, ['curated']);
          const draft = buildResourcePackageData(data);
          return {unchanged:before === JSON.stringify(data), empty, office, draft};
        }''')
        self.assertTrue(results['unchanged'])
        self.assertEqual(results['empty']['resources'], [])
        self.assertEqual(results['empty']['categories'], [])
        self.assertNotIn('INTERNAL_ONLY', json.dumps(results['office']))
        self.assertIn('INTERNAL_ONLY', json.dumps(results['draft']))
        self.assertEqual(self.errors, [])

    def test_failed_save_does_not_archive_curated_records(self):
        result = self.page.evaluate('''async () => {
          const before = JSON.stringify(data);
          let failed = false;
          try { await saveCurrentResourcePackage({kind:'file-handle', handle:{createWritable:async()=>{
            throw Error('Synthetic disk failure');
          }}}, {showSuccessToast:false}); } catch(error) { failed = true; }
          return {failed, unchanged:before === JSON.stringify(data),
            ids:[...getScoutReviewCuratedResourceIds()], batches:scoutReviewState.packagedBatches};
        }''')
        self.assertTrue(result['failed'])
        self.assertTrue(result['unchanged'])
        self.assertEqual(result['ids'], ['curated'])
        self.assertEqual(result['batches'], [])


if __name__ == '__main__':
    unittest.main()
