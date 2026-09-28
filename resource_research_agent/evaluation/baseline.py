"""Export a coherent historical primary baseline through SQLite read-only backup."""
from __future__ import annotations
import json
from pathlib import Path
import shutil
import sqlite3
from urllib.parse import quote
from .protocol import EvaluationError, file_hash, write_once, now


def readonly(path):
    return sqlite3.connect('file:' + quote(str(Path(path).resolve())) + '?mode=ro', uri=True)


def export_baseline(source_db, config, destination):
    root = Path(destination).resolve(); source_db = Path(source_db).resolve()
    selected = config['baseline']
    package = Path(selected['originalPackage']).resolve()
    if not source_db.is_file() or not package.is_file():
        raise EvaluationError('Original database/package evidence missing; do not substitute current office data')
    snapshot = root/'reference/source.sqlite3'
    if snapshot.exists() or root in source_db.parents:
        raise EvaluationError('Source and fresh experiment evidence must remain separate')
    # Backup reads a consistent committed view including WAL; no ResearchStore on either DB.
    with readonly(source_db) as source, sqlite3.connect(snapshot) as target:
        source.backup(target)
    with readonly(snapshot) as db:
        db.row_factory = sqlite3.Row
        record = db.execute('SELECT * FROM imports WHERE id=?', (selected['importId'],)).fetchone()
        expected = selected['expectedSourceSha256']
        if not record or record['source_sha256'] != expected or file_hash(package) != expected:
            raise EvaluationError('Original package does not match the selected historical import')
        categories = {}; policies = set()
        for category in config['categories']:
            job_id = selected['jobIds'][category]
            job = db.execute('SELECT * FROM focused_research_jobs WHERE id=?', (job_id,)).fetchone()
            if not job or job['import_id'] != record['id'] or job['category_id'] != category or job['status'] != 'completed':
                raise EvaluationError('Baseline must be a completed, explicitly selected primary category run')
            job = dict(job); plan = json.loads(job['plan_json'])
            mode = job['experiment_mode']; policies.add(mode)
            # Current assignment builder derives redaction from this exact mode on later passes.
            if selected['redactRecoveryTargets'] != (mode == 'employment-retrospective-v1'):
                raise EvaluationError('Historical redaction is incompatible with focused assignment semantics')
            if mode != selected['experimentMode'] or plan['playbookVersion'] != selected['playbookVersions'][category]:
                raise EvaluationError('Historical policy/playbook does not match frozen selection')
            passes = [dict(r) for r in db.execute('SELECT * FROM focused_research_passes WHERE job_id=? ORDER BY ordinal',(job_id,))]
            if not passes or any(p['status'] != 'completed' for p in passes) or sum(p['pass_kind']=='gap' for p in passes) != 1:
                raise EvaluationError('Historical baseline needs every fixed pass and exactly one completed gap pass')
            fixed = [p for p in passes if p['pass_kind'] == 'focus']
            if [p['focus_key'] for p in fixed] != [f['key'] for f in plan['focuses']]:
                raise EvaluationError('Historical fixed passes differ from the saved research plan')
            answers = []
            for item in passes:
                row = db.execute('SELECT * FROM manual_discovery_contributions WHERE id=?', (item['contribution_id'],)).fetchone()
                if row is None:
                    raise EvaluationError('Historical primary response is missing')
                answers.append(dict(row))
            categories[category] = dict(job=job, passes=passes, answers=answers,
                model=selected.get('historicalModel'), modelUnknownReason=selected.get('historicalModelUnknownReason'),
                selectedBecause=config['selectionReason'])
        if len(policies) != 1:
            raise EvaluationError('Do not pool incompatible primary research policies')
    shutil.copyfile(package, root/'inputs/office-package.zip')
    write_once(root/'reference/baseline.json', dict(categories=categories, originalImport=dict(record)))
    # No resource names or later-pass answers are copied into a model-visible summary.
    summary = dict(exportedAt=now(), sourceDb=str(source_db), sourceSnapshotSha256=file_hash(snapshot),
        originalPackageSha256=expected, originalImportId=selected['importId'],
        categories={cat:dict(jobId=data['job']['id'],runId=data['job']['run_id'],
            playbookVersion=data['job']['playbook_version'],experimentMode=data['job']['experiment_mode']) for cat,data in categories.items()},
        historicalModel=selected.get('historicalModel'),
        historicalModelUnknownReason=selected.get('historicalModelUnknownReason'))
    if not summary['historicalModel'] and not summary['historicalModelUnknownReason']:
        raise EvaluationError('Unknown historical model/settings require an explicit reason')
    return summary
