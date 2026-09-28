#!/usr/bin/env python3
"""Build the source-only editorial pilot through Scout's normal curation path.

All research completion here is explicitly scoped fixture setup, not live research.
"""
from __future__ import annotations

import argparse
import json
import sys
import zipfile
from copy import deepcopy
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from resource_research_agent.importer import ResourcePackageImporter
from resource_research_agent.storage import ResearchStore
from resource_research_agent.manual_consolidation import consolidate_manual_discovery, finish_manual_discovery
from resource_research_agent.scout_curation import prepare_scout_curation_job, next_scout_curation_assignment, save_scout_curation_result, build_scout_review_seed
from resource_research_agent.scout_review import build_scout_review_file


def build(output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    database = output / 'pilot.sqlite3'
    if database.exists():
        raise SystemExit('Use a fresh pilot directory; an existing pilot is preserved.')
    fixture = Path(__file__).resolve().parents[1] / 'tests/fixtures/resource_writing/pilot_cases.json'
    data = json.loads(fixture.read_text())
    cases = data['cases']
    source_package = output / 'pilot-source.zip'
    with zipfile.ZipFile(source_package, 'w') as archive:
        archive.writestr('tso-resources.json', json.dumps({
            'resourcePackageSchemaVersion': 3, 'packageVersion': 1,
            'officeName': 'Writing Pilot', 'serviceArea': 'Mesa and relevant Arizona service areas; historical writing samples',
            'categories': [{'id': 'writing-pilot', 'name': 'Writing samples', 'filters': []}],
            'forGroups': [], 'resources': [],
        }))
    store = ResearchStore(database)
    import_id = store.save_import(ResourcePackageImporter('Writing samples').read(source_package))
    run_id = store.create_manual_discovery_run(
        'OFFLINE WRITING PILOT: reuse saved sources; not fresh or completed provider research.',
        {'researchContext': {'mode': 'package'}, 'pilotOnly': True}, import_id,
        target_category_id='writing-pilot', target_category_label='Writing samples',
    )
    leads = []
    for case in cases:
        source = case['source']
        leads.append({
            'organization': source['name'], 'program': source['name'],
            'website': source['website'], 'phone': source.get('phone', ''),
            'address': source.get('address', ''), 'leadType': 'program',
            'locationOrServiceArea': 'Mesa / Arizona as described in the saved source',
            'whyRelevant': source['description'],
            'uncertainty': 'Historical text for writing evaluation; no new verification.',
            'savedWritingSource': source, 'sourceProvenance': case['sourceProvenance'],
        })
    store.save_manual_contribution(run_id, 'Archived source-only writing fixture', json.dumps({'leads': leads}, ensure_ascii=False))
    consolidate_manual_discovery(store, run_id)
    finish_manual_discovery(store, run_id)
    job = prepare_scout_curation_job(store, import_id)
    assignment = next_scout_curation_assignment(store, job['id'])
    (output / 'assignment.json').write_text(json.dumps(assignment, ensure_ascii=False, indent=2) + '\n')
    resources, dispositions = [], []
    for case in cases:
        source = case['source']
        matches = [candidate for candidate in assignment['candidates'] if source['website'] in json.dumps(candidate)]
        if len(matches) != 1:
            raise SystemExit(f"Expected one candidate for {source['name']}, found {len(matches)}")
        candidate_id = str(matches[0]['id'])
        resource = {key: deepcopy(source.get(key, '')) for key in ('id', 'name', 'phone', 'address', 'website', 'hours')}
        resource.update(
            description=case['description'], informationSections=case['sections'],
            candidateIds=[candidate_id], writingEvidence={'candidateIds': [candidate_id], 'sources': []},
            verifiedOn=None, categories=['writing-pilot'], categoryFilters={}, forGroups=[], pdfs=[],
        )
        resources.append(resource)
        dispositions.append({'candidateId': candidate_id, 'disposition': 'curated', 'resourceIds': [resource['id']], 'reason': ''})
    response = {
        'scoutCurationResultSchemaVersion': assignment['outputContract']['scoutCurationResultSchemaVersion'],
        'assignmentSha256': assignment['assignmentSha256'], 'categoryId': 'writing-pilot',
        'resources': resources, 'candidateDispositions': dispositions,
    }
    (output / 'source-cases.json').write_text(fixture.read_text())
    (output / 'response.json').write_text(json.dumps(response, ensure_ascii=False, indent=2) + '\n')
    save_scout_curation_result(store, job['id'], 'writing-pilot', response)
    seed = build_scout_review_seed(store, job['id'])
    (output / 'seed.json').write_text(json.dumps(seed, ensure_ascii=False, indent=2) + '\n')
    review = build_scout_review_file(store, job['id'])
    (output / review.filename).write_bytes(review.content)
    notes = ['# Writing pilot: six source-only examples', '',
             'These are historical editorial samples, not newly verified resources or an office release.',
             'The pilot uses a synthetic Writing samples category. Source classifications remain in source-cases.json; no new taxonomy decisions are claimed.',
             'The response was written by Codex from the recorded source text and the saved writing guidance, then passed through normal curation validation and HTML generation.',
             'Human review of content and print experience is pending.', '']
    for case in cases:
        notes += ['## ' + case['source']['name'], '', ' '.join(case['reviewNotes']), '',
                  'Review for: ' + '; '.join(case['mustPreserve']), '']
    (output / 'README.md').write_text('\n'.join(notes))
    return {'output': str(output), 'html': review.filename, 'resourceCount': len(seed['resources']), 'assignmentSha256': assignment['assignmentSha256']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path, help='Fresh isolated pilot directory')
    print(json.dumps(build(parser.parse_args().output), indent=2))
