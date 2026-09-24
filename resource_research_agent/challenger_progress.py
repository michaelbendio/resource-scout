"""Read-only monitor projection of independently checkpointed challenger work."""
from __future__ import annotations

import json
from pathlib import Path


def _read(path):
    try:
        value = json.loads(path.read_text())
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def apply_challenger_progress(categories, database: Path, import_id: int):
    directory = database.parent / 'deepseek-challenger'
    manifest = _read(directory / 'manifest.json')
    # Never project another run's provider onto this database/import.
    if (manifest.get('database') != str(database.resolve())
            or manifest.get('importId') != import_id
            or manifest.get('model') != 'deepseek-flash'
            or not manifest.get('authorization')):
        return
    states = {}
    for path in directory.glob('assignment-*/state.json'):
        baseline = _read(path.parent / 'baseline.json')
        state = _read(path)
        if baseline.get('category_id') and baseline.get('job_id'):
            states[(baseline['category_id'], baseline['job_id'])] = state
    status_labels = {
        'prepared': 'pending', 'requesting': 'in-progress',
        'awaiting-tools': 'in-progress', 'completed': 'awaiting-import',
        'failed': 'failed', 'budget-stop': 'failed',
    }
    for category in categories:
        state = states.get((category['categoryId'], category['jobId']), {})
        for researcher in category['researchers']:
            if researcher['role'] != 'challenger':
                continue
            if researcher['name'] not in {'Grok', 'DeepSeek'}:
                continue
            researcher['modelLabel'] = manifest.get('versionExpected', 'DeepSeek V4.1-Flash')
            if researcher['name'] == 'DeepSeek':
                continue  # An imported result's database status is authoritative.
            researcher.update(
                name='DeepSeek',
                status=status_labels.get(state.get('status'), 'pending'),
                leadCount=int(state.get('leadCount') or 0),
            )
            researcher['progressSource'] = 'independent-challenger-checkpoint'
            researcher['note'] = 'Saved results enter Scout at the next configured coordinator import checkpoint.'
