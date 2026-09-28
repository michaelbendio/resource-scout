#!/usr/bin/env python3
"""Optional real-browser QA. Requires playwright, pypdf, and an installed Chrome browser."""
from __future__ import annotations
import argparse
import json
import zipfile
from pathlib import Path
from playwright.sync_api import sync_playwright
from pypdf import PdfReader


def check(directory: Path, chrome: str):
    directory = directory.resolve()
    pdf_dir = directory.parents[0] / 'pdf'
    pdf_dir.mkdir(exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=chrome, headless=True)
        context = browser.new_context(viewport={'width':1100, 'height':1000}, accept_downloads=True)
        page = context.new_page()
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto((directory / 'autoWritingPilot.html').as_uri())
        initial = page.evaluate('data.resources')
        assert len(initial) == 6
        assert page.evaluate('getScoutReviewCuratedResourceIds().size') == 0
        # Inspect the ordinary expanded resource card, then the actual Admin editor.
        page.evaluate('''() => {
            appView.innerHTML = '';
            appView.appendChild(buildResourceCard(data.resources[0], {expanded:true, showDescription:true}));
        }''')
        assert 'jobs.mesaaz@expresspros.com' in page.locator('#appView').inner_text()
        page.screenshot(path=str(directory / 'resource-view.png'), full_page=True)
        page.evaluate('''() => {
            isAdminVisible=true; view='admin'; adminTab='resources';
            selectedResourceId=data.resources[0].id; adminResourceEditMode=true; safeRender();
        }''')
        assert page.locator('#res_description').input_value() == initial[0]['description']
        page.locator('#res_information_preview_btn').click()
        assert 'Important Information to Know' in page.locator('#res_information_preview').inner_text()
        page.screenshot(path=str(directory / 'admin-preview.png'), full_page=True)
        # Print actual single-resource and selection workflows, without changing CSS.
        page.evaluate('PrintWorkflow.previewSingleResource(data.resources[0])')
        page.screenshot(path=str(directory / 'print-preview.png'), full_page=True)
        page.pdf(path=str(pdf_dir / 'scout-writing-express.pdf'), format='Letter', print_background=True, prefer_css_page_size=True)
        page.evaluate('''() => {
            PrintWorkflow.close();
            printSelection=data.resources.map(r=>r.id); PrintWorkflow.startPrintSelection();
        }''')
        packet = page.locator('#printContent').inner_text()
        for resource in initial:
            assert resource['name'] in packet
        assert packet.count('Programs and Services') == 6
        page.pdf(path=str(pdf_dir / 'scout-writing-six-samples.pdf'), format='Letter', print_background=True, prefer_css_page_size=True)
        # A section heading must not be the last visible line on a printed page.
        headings = {'Programs and Services', 'Eligibility Requirements', 'How to Best Connect', 'Access', 'Important Information to Know'}
        for name in ('scout-writing-express.pdf', 'scout-writing-six-samples.pdf'):
            for printed in PdfReader(pdf_dir / name).pages:
                lines = [line.strip() for line in printed.extract_text().splitlines() if line.strip()]
                assert lines and lines[-1] not in headings, (name, lines[-1:])
        page.evaluate('PrintWorkflow.close()')
        # Curated marking and edit invalidation through the real editor.
        page.locator('#res_curated_btn').click()
        assert page.evaluate('getScoutReviewCuratedResourceIds().size') == 1
        edited = initial[0]['description'] + ' Pilot editor check.'
        page.locator('#res_description').fill(edited)
        page.locator('#res_update_description').fill('Isolated pilot editor check')
        assert page.evaluate('commitPendingEditsIfChanged()')
        assert page.evaluate('getScoutReviewCuratedResourceIds().size') == 0
        # Restore the original text before export; reviewer approval is simulated
        # for this isolated QA copy only, not attributed to Michael.
        page.locator('#res_description').fill(initial[0]['description'])
        assert page.evaluate('commitPendingEditsIfChanged()')
        page.evaluate('setScoutReviewResourceCurated(data.resources[0].id, true)')
        # A failed/canceled file save must retain the resource, mark, and version.
        before_version = page.evaluate('data.packageVersion')
        page.evaluate('''async () => {
            try {
                await saveCurrentResourcePackage({kind:'file-handle', handle:{
                    createWritable: async()=>{throw new DOMException('Canceled QA save', 'AbortError')}
                }}, {showSuccessToast:false});
                throw new Error('Expected cancellation');
            } catch(error) { if(error.name !== 'AbortError') throw error; }
        }''')
        assert page.evaluate('data.packageVersion') == before_version
        assert page.evaluate('data.resources.length') == 6
        assert page.evaluate('getScoutReviewCuratedResourceIds().size') == 1
        with page.expect_download() as download:
            page.evaluate("saveCurrentResourcePackage({kind:'download',suggestedName:'writing-pilot-selection.zip'}, {showSuccessToast:false}).then(()=>null)")
        archive = directory / 'writing-pilot-selection.zip'
        download.value.save_as(archive)
        with zipfile.ZipFile(archive) as zipped:
            package = json.loads(zipped.read('tso-resources.json'))
        assert len(package['resources']) == 1
        exported = package['resources'][0]
        for field in ('id','name','description','informationText','phone','address','website','hours'):
            assert exported[field] == initial[0][field], field
        assert not any(field in exported for field in ('writing', 'writingEvidence', 'informationSections', 'candidateIds'))
        assert page.evaluate('data.resources.length') == 5
        page.reload()
        assert page.evaluate('data.resources.length') == 5
        # Reopen the actual exported ZIP data using the app's package reader.
        reopened = page.evaluate('(value)=>processResourcePackageData(value,{sourceName:"QA exported package"}).data', package)
        assert reopened['resources'][0]['informationText'] == initial[0]['informationText']
        assert reopened['resources'][0]['description'] == initial[0]['description']
        assert not errors, errors
        browser.close()
    report = {'status':'passed','resources':6,'browser':'Chrome / Playwright',
              'checks':['resource view','Admin preview','single and multi-resource print','print headings stay with following text','Curated defaults','edit invalidation','canceled save','selected ZIP export','reload','package reopen'],
              'jsErrors':errors,'humanPilotReview':'pending','pdfDirectory':str(pdf_dir)}
    (directory/'browser-checks.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory',type=Path)
    parser.add_argument('--chrome',default='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
    args=parser.parse_args()
    check(args.directory,args.chrome)
