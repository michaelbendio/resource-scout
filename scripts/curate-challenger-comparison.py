"""Curate the sealed Grok/DeepSeek trial union without touching production data.

Reuses Scout's ordinary High curator, batching, recovery and validation. All
checkpoints are files in the isolated experiment, not production curation jobs.
Provider labels and the earlier audit scores are withheld from workers.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from resource_research_agent.runner_lock import research_runner_lock
from resource_research_agent.scout_curation import (
    _assignment, _assignment_sha256, _completed_resources,
    validate_scout_curation_result,
)
from resource_research_agent.scout_curation_runner import (
    complete_batched_category, encode, validate_links, write_evidence_once,
)
from resource_research_agent.worker_lifecycle import atomic_json

SOURCE = ROOT / 'data/deepseek-challenger-trial-20260921'
OUT = ROOT / 'data/challenger-curation-comparison-20260921'
DB = ROOT / 'data/welfare-square-production-20260921-codex-grok/research.sqlite3'
NAMES = ['Housing', 'Employment', 'Disability']


def now():
    return datetime.now(timezone.utc).isoformat()


def read(path):
    return json.loads(path.read_text())


def snapshot():
    with sqlite3.connect(f'file:{DB}?mode=ro', uri=True) as connection:
        tables = [r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        result = {}
        for name in tables:
            rows = connection.execute('SELECT * FROM "' + name + '"').fetchall()
            content = json.dumps(sorted(rows, key=repr), ensure_ascii=False, default=str).encode()
            result[name] = {'rows': len(rows), 'sha256': hashlib.sha256(content).hexdigest()}
        return result


def event(phase, message, category_id=None, **details):
    value = dict(at=now(), phase=phase, message=message, categoryId=category_id, **details)
    with (OUT / 'progress.jsonl').open('a') as handle:
        handle.write(encode(value) + '\n')
    atomic_json(OUT / 'live-status.json', value)
    print(encode(value), flush=True)


def prepare():
    if (OUT / 'job.json').exists():
        raise RuntimeError('Existing experiment retained; use run to resume')
    with zipfile.ZipFile(DB.parent / 'welfare-square-resource-package.zip') as archive:
        package = json.loads(archive.read('resource-package.json'))
    with sqlite3.connect(f'file:{DB}?mode=ro', uri=True) as connection:
        connection.row_factory = sqlite3.Row
        original = dict(connection.execute('SELECT * FROM imports WHERE id=1').fetchone())
    selected = [c for c in package['categories'] if c['label'] in NAMES]
    selected.sort(key=lambda c: NAMES.index(c['label']))
    if len(selected) != 3:
        raise RuntimeError('Expected the three sealed comparison categories')
    source_package = dict(sourceSha256=original['source_sha256'],
                          contentSha256=original['content_sha256'], packageVersion=original['package_version'])
    common = dict(location=dict(name='Welfare Square challenger comparison',
                               officeName=original['office_name'], serviceArea=original['service_area']),
                  sourcePackage=source_package, categories=selected,
                  forGroups=json.loads(original['for_groups_json']))
    job = dict(id=1, importId=1, status='prepared', categories=[], createdAt=now(),
               locationName=common['location']['name'], officeName=original['office_name'],
               serviceArea=original['service_area'], sourcePackage=source_package,
               summary=dict(categories=selected, forGroups=common['forGroups'],
                            schema=dict(packageVersion=original['package_version'])))
    mapping = {}
    for category in selected:
        folder = SOURCE / category['label'].lower()
        packet = read(folder / 'blind-review.json')
        key = read(folder / 'blind-key.json')
        candidates = []
        for row in packet:
            lead = {k: v for k, v in row.items() if k != 'id'}
            candidates.append(dict(id=row['id'], name=lead['organization'] + ' — ' + lead['program'],
                                   candidate=dict(manualDiscoveryProvenance=dict(members=[lead]))))
            mapping[row['id']] = dict(categoryId=category['id'], **key[row['id']], originalSubmission=lead)
        assignment = _assignment(common, category, dict(run=dict(id=len(job['categories']) + 1),
            candidates=candidates, sourceOnlyRecords=read(folder / 'primary-leads.json')))
        assignment['comparisonScope'] = (
            'Curate ALL supplied original submissions under identical ordinary direct-service standards. '
            'Provider names and earlier scores are deliberately hidden. Do not infer or rank providers. '
            'The source-only records are prior research leads, not approved or curated resources. '
            'Do not copy their unverified claims as facts. Do not omit an otherwise valid submitted service '
            'merely because prior research names it: retain/merge it normally and mention prior coverage in '
            'the disposition reason. Incremental discovery credit is evaluated separately afterward. '
            'Keep legitimate distinct specialized services; no output quota or pressure to favor volume. '
            'For each disposition, briefly identify material corrections, remaining uncertainty and evidence '
            'as well as the retain/merge/omit reason. Do not read outside this assignment directory.'
        )
        job['categories'].append(dict(categoryId=category['id'], categoryLabel=category['label'],
                                      status='pending', candidateCount=len(candidates), assignment=assignment))
    job['candidatePackageSha256'] = hashlib.sha256(encode(mapping).encode()).hexdigest()
    write_evidence_once(OUT / 'provider-key.json', mapping)
    write_evidence_once(OUT / 'before-production.json', snapshot())
    write_evidence_once(OUT / 'job.json', job)
    write_evidence_once(OUT / 'plan.json', dict(createdAt=now(), model='gpt-5.5', effort='high',
        batchCandidates=30, batchChars=60000, candidateCount=len(mapping),
        approach='One common provider-label-hidden curation of the full 140-submission union; assign credit afterward.',
        comparison=['retained distinct direct-service resources per provider',
                    'shared and provider-unique resources', 'incremental contribution beyond sealed primary research',
                    'substantive corrections and unresolved access questions', 'service importance and limits'],
        limits=['Common curator, not a comparison of providers as curators.',
                'Shared curation can use evidence from either submission; credit concerns discovery, not original writing quality.',
                'Provider styles may be recognizable; supervisor knows earlier results.',
                'No new Grok/DeepSeek research, no production changes, no human Curated approval or final Codex review.']))
    event('prepared', 'Sealed all 140 submissions for common High curation')


def run():
    args = argparse.Namespace(batch_candidates=30, batch_chars=60000,
        codex_binary=shutil.which('codex') or 'codex', model='gpt-5.5', effort='high', timeout_seconds=3600)
    job = read(OUT / 'job.json')
    if job['status'] == 'completed':
        resources = _completed_resources(job)
        write_evidence_once(OUT / 'resources.json', resources)
        event('completed', 'Saved curation already complete; no workers launched', resources=len(resources))
        return
    for category in job['categories']:
        if category['status'] == 'completed':
            continue
        assignment = category['assignment']
        if category['status'] == 'pending':
            assignment['previouslyCuratedResources'] = _completed_resources(job)
            assignment['assignmentSha256'] = _assignment_sha256(assignment)
            category.update(status='assigned', assignmentSha256=assignment['assignmentSha256'])
            job['status'] = 'running'
            atomic_json(OUT / 'job.json', job)
        directory = OUT / category['categoryId'] / assignment['assignmentSha256'][:16]
        directory.mkdir(parents=True, exist_ok=True)
        write_evidence_once(directory / 'assignment.json', assignment)
        result = complete_batched_category(job, assignment, directory, args,
            'No prior judgments supplied. Independently verify all original submissions.', event)
        validate_links(assignment, result)
        result = validate_scout_curation_result(job, category['categoryId'], result)
        category.update(status='completed', result=result, resourceCount=len(result['resources']), completedAt=now())
        atomic_json(OUT / 'job.json', job)
        event('category-completed', 'Completed ' + category['categoryLabel'], category['categoryId'],
              resources=len(result['resources']), candidates=len(result['candidateDispositions']))
    job.update(status='completed', completedAt=now())
    atomic_json(OUT / 'job.json', job)
    write_evidence_once(OUT / 'resources.json', _completed_resources(job))
    event('completed', 'Curation complete; ready for comparison and a separately requested Codex review',
          resources=len(_completed_resources(job)))


def verify():
    unchanged = snapshot() == read(OUT / 'before-production.json')
    value = dict(at=now(), allProductionTablesUnchanged=unchanged)
    atomic_json(OUT / 'production-verification.json', value)
    print(encode(value))
    if not unchanged:
        raise RuntimeError('Production data changed')


def render():
    """Build ordinary, unapproved Scout drafts from the completed file job.

    The renderer reads an empty in-memory priority table because this experiment
    has no requested final review or priority proposal. No review is fabricated.
    """
    from resource_research_agent.scout_review import _build_scout_review_file_from_seed
    job = read(OUT / 'job.json')
    if job['status'] != 'completed':
        raise RuntimeError('Finish all curation before rendering')
    resources = _completed_resources(job)
    classification_path = OUT / 'comparison-classifications.json'
    classifications = read(classification_path) if classification_path.exists() else {}
    navigation_ids = {r['resourceId'] for r in classifications.get('excludedFromDirectServiceCounts', [])}
    if not navigation_ids <= {r['id'] for r in resources}:
        raise RuntimeError('Comparison classification names an unknown resource')
    navigation = [r for r in resources if r['id'] in navigation_ids]
    write_evidence_once(OUT / 'navigation-resources.json', navigation)
    resources = [r for r in resources if r['id'] not in navigation_ids]
    mapping = read(OUT / 'provider-key.json')

    class DraftRenderContext:
        @contextmanager
        def connect(self):
            connection = sqlite3.connect(':memory:')
            connection.execute('CREATE TABLE scout_review_priority_revisions (id INTEGER, job_id INTEGER)')
            try:
                yield connection
            finally:
                connection.close()

        def record_scout_curation_progress(self, job_id, phase, message, **details):
            event(phase, message, **details)

    manifest = []
    for label, provider in [('Combined', None), ('Grok', 'saved-baseline'), ('DeepSeek', 'new-trial')]:
        selected = [deepcopy(r) for r in resources if provider is None or any(
            mapping[c]['provider'] == provider for c in r['candidateIds'])]
        for resource in selected:
            resource.pop('candidateIds', None)
        name = 'Welfare Square ' + label + ' Comparison'
        render_job = {**job, 'locationName': name}
        seed = dict(resourcePackageSchemaVersion=3, packageVersion='1',
            officeName='Auto' + name.replace(' ', ''), serviceArea=job['serviceArea'],
            categories=job['summary']['categories'], forGroups=job['summary']['forGroups'],
            resources=selected, categoryMigrations=[], changes=[], deletionRequests=[], deletions=[],
            packageCreatedAt=job['completedAt'], lastModified=job['completedAt'])
        artifact = _build_scout_review_file_from_seed(DraftRenderContext(), render_job, seed)
        destination = OUT / artifact.filename
        if destination.exists() and destination.read_bytes() != artifact.content:
            raise RuntimeError('Refusing to replace a changed draft: ' + str(destination))
        destination.write_bytes(artifact.content)
        write_evidence_once(OUT / (label.lower() + '-seed.json'), seed)
        manifest.append(dict(provider=provider or 'combined', file=str(destination),
                             resourceCount=len(selected), sha256=hashlib.sha256(artifact.content).hexdigest()))
    write_evidence_once(OUT / 'drafts.json', dict(status='Ready for Codex review',
        finalReviewComplete=False, humanCurated=False, drafts=manifest,
        navigationRetainedSeparately=[r['id'] for r in navigation],
        classificationSha256=hashlib.sha256(classification_path.read_bytes()).hexdigest()
            if classification_path.exists() else None))
    print(json.dumps(manifest, indent=2))


def compare():
    """Compute attribution only; usefulness and primary overlap need judgment."""
    job = read(OUT / 'job.json')
    if job['status'] != 'completed':
        raise RuntimeError('Finish all curation before comparing')
    mapping = read(OUT / 'provider-key.json')
    resources = _completed_resources(job)
    by_id = {r['id']: r for r in resources}
    dispositions = [d for c in job['categories'] for d in c['result']['candidateDispositions']]
    if {d['candidateId'] for d in dispositions} != set(mapping) or len(dispositions) != len(mapping):
        raise RuntimeError('Incomplete original-submission coverage')
    rows = []
    for category in job['categories']:
        counts = {}
        for provider in ['saved-baseline', 'new-trial']:
            own = [d for d in category['result']['candidateDispositions'] if mapping[d['candidateId']]['provider'] == provider]
            retained = {rid for d in own for rid in d['resourceIds']}
            counts[provider] = dict(submissions=len(own),
                retainedSubmissions=sum(d['disposition'] != 'omitted' for d in own),
                omittedSubmissions=sum(d['disposition'] == 'omitted' for d in own),
                distinctResourceIds=sorted(retained))
        a, b = [set(counts[p]['distinctResourceIds']) for p in counts]
        rows.append(dict(categoryId=category['categoryId'], providers=counts,
                         shared=sorted(a & b), grokOnly=sorted(a-b), deepseekOnly=sorted(b-a)))
    global_sets = {p: {rid for d in dispositions if mapping[d['candidateId']]['provider'] == p
                       for rid in d['resourceIds']} for p in ['saved-baseline', 'new-trial']}
    for p, ids in global_sets.items():
        expected = {r['id'] for r in resources if any(mapping[c]['provider'] == p for c in r['candidateIds'])}
        if ids != expected:
            raise RuntimeError('Final merged resource attribution differs from dispositions')
    a, b = global_sets.values()
    result = dict(status='AI curation complete; Ready for Codex review', createdAt=now(),
        finalReviewComplete=False, humanCurated=False, categories=rows,
        globalCounts=dict(grok=len(a), deepseek=len(b), shared=len(a & b),
                          grokOnly=len(a-b), deepseekOnly=len(b-a), union=len(a | b)),
        globalResourceIds={p: sorted(ids) for p, ids in global_sets.items()},
        resources=resources,
        decisions=[dict(**d, source=mapping[d['candidateId']]) for d in dispositions],
        pendingJudgment='Incremental primary coverage, consequential services, original corrections and unresolved access questions.',
        sourceJobSha256=hashlib.sha256((OUT / 'job.json').read_bytes()).hexdigest())
    if set(by_id) != a | b:
        raise RuntimeError('Unattributed resource in final union')
    atomic_json(OUT / 'comparison-counts.json', result)
    print(json.dumps(dict(globalCounts=result['globalCounts'], categories=rows), indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'run', 'verify', 'render', 'compare'])
    options = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    with research_runner_lock(OUT / 'curation-files'), research_runner_lock(DB):
        try:
            {'prepare': prepare, 'run': run, 'verify': verify, 'render': render, 'compare': compare}[options.action]()
        except Exception as error:
            if options.action == 'run':
                event('stopped', f'{type(error).__name__}: {error}')
            raise
