#!/usr/bin/env python3
"""Real-browser QA with synthetic data only; requires Playwright and Chrome."""
from __future__ import annotations

import argparse
import json
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))
from playwright.sync_api import sync_playwright
from test_scout_improvement import fixture_package, result_for
from resource_research_agent.improvement_packages import read_package, write_package
from resource_research_agent.scout_improvement import ImprovementWorkflow
from resource_research_agent.server import ResearchHTTPServer
from resource_research_agent.storage import ResearchStore


def check(output, chrome, office_html):
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    database = output / 'qa.sqlite3'
    if database.exists():
        raise SystemExit('Use a fresh QA output directory')
    store = ResearchStore(database)
    flow = ImprovementWorkflow(store)
    source = fixture_package()
    assets = {'pdfs/guide.pdf': b'%PDF-1.4\nSynthetic byte-preservation QA fixture\n%%EOF'}
    source_path = output / 'qa-original.zip'
    source_path.write_bytes(write_package(source, assets))
    current = fixture_package()
    current['packageVersion'] = 11
    current['resources'][0].update(phone='555-0200', description='Later office description. Keep this local wording.')
    current_path = output / 'qa-current.zip'
    current_path.write_bytes(write_package(current, assets))
    server = ResearchHTTPServer(('127.0.0.1', 0), store, ROOT / 'web')
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    errors = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=chrome, headless=True)
            context = browser.new_context(viewport={'width': 1200, 'height': 950}, accept_downloads=True)
            page = context.new_page(); page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto(f'http://127.0.0.1:{server.server_port}/improvements')
            page.locator('#new-project summary').click()
            page.locator('#source').set_input_files(str(source_path))
            page.locator('#resource-selection input').first.wait_for()
            page.locator('#resource-selection input').first.check()
            page.locator('#historical').check()
            page.locator('#prepare').click()
            page.locator('#project-title').wait_for(state='visible')
            pid = int(page.url.split('project=')[1])
            assert flow.view(pid)['historical']
            assert page.locator('[data-action=curated]').count() == 0
            # Explicitly synthetic, in-process responses. Never label these as AI research.
            while assignment := flow.next_assignment(pid):
                flow.submit(pid, assignment['stage'], result_for(assignment))
            page.locator('#refresh').click()
            page.locator('[data-action=curated]').wait_for()
            assert page.locator('[data-action=curated]').is_disabled()
            page.locator('#latest').set_input_files(str(current_path))
            page.locator('#reviewer').fill('Synthetic browser QA; not Michael approval')
            page.wait_for_function("document.querySelector('[data-action=curated]') && !document.querySelector('[data-action=curated]').disabled")
            for link in page.locator('a', has_text='attachment:').all():
                response = context.request.get(f'http://127.0.0.1:{server.server_port}' + link.get_attribute('href'))
                assert response.ok and response.body() == assets['pdfs/guide.pdf']
            assert 'both changed' in page.locator('.conflict').inner_text()
            assert page.locator('input[data-field=description]:checked').input_value() == 'current'
            page.locator('[data-note]').fill('QA: keep the later office description and improve Information.')
            page.locator('[data-action=curated]').click()
            page.wait_for_function("document.querySelector('[data-review-state]').textContent.includes('✓ Curated')")
            page.screenshot(path=str(output / 'comparison.png'), full_page=True)
            # Starting an edit clears acceptance durably, before Save is clicked.
            page.locator('summary', has_text='Edit proposed writing').click()
            page.locator('[data-edit]').fill('Edited proposal for QA only.')
            page.wait_for_function("document.querySelector('[data-review-state]').textContent.includes('Unmarked')")
            page.wait_for_function('invalidating.size === 0')
            assert flow.view(pid)['resources'][0]['review'] is None
            assert page.locator('#export').is_disabled()
            page.locator('[data-action=edit]').click()
            page.wait_for_function("document.getElementById('message').textContent.startsWith('Edits saved')")
            page.locator('[data-note]').fill('QA: keep the latest description after reviewing edited proposal.')
            page.locator('[data-action=curated]').click()
            page.wait_for_function("document.querySelector('[data-review-state]').textContent.includes('✓ Curated')")
            # A canceled native picker does not prepare or hide an export.
            page.evaluate("()=>{window.showSaveFilePicker=async()=>{throw new DOMException('QA cancel','AbortError')}}")
            page.locator('#export').click()
            assert not flow.view(pid)['resources'][0]['packaged']
            # Browser-download fallback preserves review until explicit save acknowledgment.
            page.evaluate('window.showSaveFilePicker=undefined')
            with page.expect_download() as download:
                page.locator('#export').click()
            saved_path = output / 'qa-reviewed-updates.zip'; download.value.save_as(saved_path)
            page.locator('#confirm-saved').wait_for(state='visible')
            assert not flow.view(pid)['resources'][0]['packaged']
            page.locator('#keep-review').click()
            assert not flow.view(pid)['resources'][0]['packaged']
            # Printing uses the selected field choices and the actual shared Information renderer.
            page.evaluate('()=>{window.print=()=>{}}')
            page.locator('[data-action=print]').click()
            assert 'Later office description' in page.locator('#print-content').inner_text()
            assert 'Maria' in page.locator('#print-content').inner_text()
            page.emulate_media(media='print')
            page.screenshot(path=str(output / 'print.png'), full_page=True)
            page.emulate_media(media='screen')
            with page.expect_download() as download:
                page.locator('#export').click()
            second = output / 'qa-reviewed-updates-again.zip'; download.value.save_as(second)
            assert saved_path.read_bytes() == second.read_bytes()
            page.locator('#confirm-saved').click()
            page.wait_for_function("document.querySelectorAll('.resource').length===0")
            page.reload(); page.wait_for_function("document.getElementById('project-summary').textContent.includes('0 resources')")
            assert flow.view(pid)['resources'][0]['packaged']
            package = read_package(saved_path.read_bytes())
            assert package['resources']['r1']['phone'] == '555-0200'
            assert package['resources']['r1']['description'] == current['resources'][0]['description']
            assert package['assets'] == assets
            # Exercise the office application's actual package reader and merge in a disposable browser context.
            office = context.new_page(); office.on('pageerror', lambda error: errors.append(str(error)))
            office.goto(office_html.resolve().as_uri())
            merged = office.evaluate('''([current,incoming])=>{
                const old=processResourcePackageData(current,{sourceName:'Synthetic current office'}).data;
                const next=processResourcePackageData(incoming,{sourceName:'Synthetic reviewed update'}).data;
                return mergeResourcePackages(old,next);
            }''', [current, package['data']])
            (output / 'office-merge.json').write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding='utf-8')
            # The merge API returns its materialized data and a separate summary.
            data = merged['mergedData']
            resources = {r['id']: r for r in data['resources']}
            assert len(resources) == 2
            for field in ('description', 'informationText', 'phone', 'verifiedOn', 'pdfs'):
                assert resources['r1'][field] == package['resources']['r1'][field], field
            assert resources['r2']['informationText'] == current['resources'][1]['informationText']
            assert not errors, errors
            browser.close()
        report = {'status': 'passed', 'syntheticOnly': True, 'realResearchPerformed': False,
                  'checks': ['UI package intake and scope', 'research completion gate', 'latest package connection',
                             'same-field conflict choice', 'durable acceptance invalidation on edit', 'canceled picker',
                             'download cancellation retention', 'byte-identical retry', 'save acknowledgment', 'reload',
                             'selected writing print', 'original and latest PDF access', 'PDF byte preservation', 'actual office reader and merge'],
                  'jsErrors': errors, 'officeHtml': str(office_html)}
        (output / 'browser-checks.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        print(json.dumps(report, indent=2))
    finally:
        server.shutdown(); server.server_close(); thread.join()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--chrome', default='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
    parser.add_argument('--office-html', type=Path, default=ROOT / 'resource_research_agent/scout_review_template.html')
    args = parser.parse_args(); check(args.output, args.chrome, args.office_html)
