"""Display saved reviewer checkpoints, separately from worker activity or approval."""
import json
import time
from datetime import datetime, timezone
from pathlib import Path


STATES = {'pending', 'in-progress', 'complete'}
STAGES = {'content', 'identity', 'taxonomy', 'selection', 'validation'}


def reviewer_activity(root, pipeline):
    """Bounded native activity, explicitly separate from authored progress."""
    directory = pipeline.get('reviewDirectory')
    if not directory:
        return None
    path = (Path(directory) / 'events.jsonl').resolve()
    if not path.is_relative_to((root / 'review').resolve()):
        return None
    try:
        stat = path.stat()
        with path.open('rb') as source:
            source.seek(max(0, stat.st_size - 256_000))
            lines = source.read().decode('utf-8', errors='replace').splitlines()
        message = ''
        for line in reversed(lines):
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if not isinstance(event, dict):
                continue
            item = event.get('item', {})
            if event.get('type') == 'item.completed' and isinstance(item, dict) and item.get('type') == 'agent_message':
                message = str(item.get('text', ''))[:1600]
                break
        return dict(message=message, lastEventAt=datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                    eventAgeSeconds=max(0, round(time.time() - stat.st_mtime)))
    except OSError:
        return None


def review_progress(root, category_ids, pipeline):
    root = Path(root)
    total = len(set(category_ids))
    result = dict(stage='waiting', summary='Review follows curation.', totalCategories=total,
                  contentCompleted=0, taxonomyCompleted=0, selectionCompleted=0,
                  identityStatus='pending', validationStatus='pending', updatedAt=None,
                  session=pipeline.get('reviewSessions', 0), checkpointAvailable=False,
                  activity=reviewer_activity(root, pipeline), categories=[], recentFindings=[])
    if pipeline.get('phase') == 'paused':
        result['summary'] = 'Review is paused.'
    elif pipeline.get('phase') in {'review', 'ready-review'}:
        result['summary'] = 'Review is starting; awaiting its first saved checkpoint.'
    path = root / 'review/progress.json'
    if not path.exists():
        return result
    try:
        if path.stat().st_size > 200_000:
            raise ValueError('Oversized review progress checkpoint')
        data = json.loads(path.read_text())
        if data['stage'] not in STAGES or not isinstance(data['summary'], str) or not data['updatedAt']:
            raise ValueError('Invalid review stage or timestamp')
        checkpoint = Path(data['checkpointFile']).resolve()
        if not checkpoint.is_relative_to((root / 'review').resolve()) or not checkpoint.is_file() or not checkpoint.stat().st_size:
            raise ValueError('Review progress needs a saved decision checkpoint')
        rows = data['categories']
        ids = [r['categoryId'] for r in rows]
        if len(ids) != len(set(ids)) or set(ids) != set(category_ids):
            raise ValueError('Review progress category scope differs from the run')
        for key in ('content', 'taxonomy', 'selection'):
            if any(r[key] not in STATES for r in rows):
                raise ValueError('Invalid category review status')
        if data['identityStatus'] not in STATES or data['validationStatus'] not in STATES:
            raise ValueError('Invalid collection review status')
        records = data.get('recordProgress')
        if records is not None:
            if records['categoryId'] not in category_ids:
                raise ValueError('Record progress category is outside review scope')
            for unit in ('resources', 'candidates'):
                done, total_records = records[unit + 'Reviewed'], records[unit + 'Total']
                if type(done) is not int or type(total_records) is not int or not 0 <= done <= total_records:
                    raise ValueError('Invalid reviewed record counts')
            if not isinstance(records.get('currentTask', ''), str):
                raise ValueError('Invalid current review task')
        findings = data.get('recentFindings', [])
        if not isinstance(findings, list) or any(not isinstance(f, str) for f in findings):
            raise ValueError('Invalid review findings')
        for key in ('content', 'taxonomy', 'selection'):
            result[key + 'Completed'] = sum(r[key] == 'complete' for r in rows)
        result.update({k: data[k] for k in ('stage', 'summary', 'updatedAt', 'identityStatus', 'validationStatus')})
        result['checkpointAvailable'] = True
        result['categories'] = [{k: r[k] for k in ('categoryId', 'content', 'taxonomy', 'selection')} for r in rows]
        result['recordProgress'] = records
        result['recentFindings'] = [f[:1200] for f in findings[:5]]
    except (ValueError, KeyError, TypeError, OSError) as error:
        result.update(summary='Saved review progress is unavailable: ' + str(error), checkpointError=True)
        return result
    # These counts describe authored checkpoints, never final artifact acceptance.
    if pipeline.get('phase') == 'needs-attention':
        result['runStatus'] = 'needs-attention'
    elif pipeline.get('phase') == 'paused':
        result['runStatus'] = 'paused'
    else:
        result['runStatus'] = pipeline.get('phase')
    return result
