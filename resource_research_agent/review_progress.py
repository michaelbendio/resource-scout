"""Display saved reviewer checkpoints, separately from worker activity or approval."""
import json
from pathlib import Path


STATES = {'pending', 'in-progress', 'complete'}
STAGES = {'content', 'identity', 'taxonomy', 'selection', 'validation'}


def review_progress(root, category_ids, pipeline):
    root = Path(root)
    total = len(set(category_ids))
    result = dict(stage='waiting', summary='Review follows curation.', totalCategories=total,
                  contentCompleted=0, taxonomyCompleted=0, selectionCompleted=0,
                  identityStatus='pending', validationStatus='pending', updatedAt=None,
                  session=pipeline.get('reviewSessions', 0), checkpointAvailable=False)
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
        for key in ('content', 'taxonomy', 'selection'):
            result[key + 'Completed'] = sum(r[key] == 'complete' for r in rows)
        result.update({k: data[k] for k in ('stage', 'summary', 'updatedAt', 'identityStatus', 'validationStatus')})
        result['checkpointAvailable'] = True
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
