"""Checkpoint-based full-review forecast; unmeasured stages use explicit allowances."""
from datetime import datetime, timezone, timedelta
from pathlib import Path
import fcntl
import json
import sqlite3
from math import floor, ceil

STAGES = ('content', 'identity', 'taxonomy', 'selection', 'validation')
LABELS = dict(content='Resource and candidate review', identity='Cross-category consolidation',
              taxonomy='Types and groups', selection='Starters and complements', validation='Final validation and supervisor audit')
# Planning allowances relative to the projected whole content pass, NOT measured facts.
ALLOWANCES = dict(identity=(.10, .25), taxonomy=(.10, .25), selection=(.20, .40), validation=(.05, .15))


def parse_time(value):
    date = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    return date.replace(tzinfo=timezone.utc) if date.tzinfo is None else date


def forecast(history, totals, sessions, now=None):
    """Pure calculation. No countdown progress, invented completion or old-run timings."""
    now = now or datetime.now(timezone.utc)
    last = history[-1]
    samples = {stage: [0., 0.] for stage in STAGES}
    def active_seconds(begin, end):
        return sum(max(0, (min(end, stop) - max(begin, start)).total_seconds()) for start, stop in sessions)
    for previous, current in zip(history, history[1:]):
        stage = previous['stage']
        delta = current['done'][stage] - previous['done'][stage]
        # A stage switch checkpoint attributes the preceding interval to that stage.
        seconds = active_seconds(parse_time(previous['at']), parse_time(current['at']))
        changed = [s for s in STAGES if current['done'][s] != previous['done'][s]]
        if changed == [stage] and delta > 0 and seconds > 0:
            samples[stage][0] += seconds
            samples[stage][1] += delta
    content_seconds, content_units = samples['content']
    if not content_units or not content_seconds:
        return dict(status='learning', label='Learning review pace — awaiting a timed decision checkpoint.',
                    basis='The estimate will include content, consolidation, taxonomy, selections and final validation.')
    pace = content_seconds / content_units
    projected_content = pace * totals['content']
    measured_categories = last.get('contentCategories', 0)
    low_factor, high_factor = (.65, 1.8) if measured_categories < 3 else (.8, 1.4)
    stages = []
    for stage in STAGES:
        remaining = max(0, totals[stage] - last['done'][stage])
        seconds, units = samples[stage]
        if not remaining:
            low = high = 0
            basis = 'Saved checks complete'
        elif units and seconds:
            low = remaining * seconds / units * low_factor
            high = remaining * seconds / units * high_factor
            basis = 'Observed checkpoint pace'
        else:
            fraction = remaining / totals[stage]
            a, b = ALLOWANCES[stage]
            low, high = projected_content * a * fraction, projected_content * b * fraction
            if stage == 'validation':
                low, high = max(low, 1800), max(high, 7200)
            basis = f'Planning allowance: {round(a*100)}–{round(b*100)}% of projected content time'
            if stage == 'validation':
                basis += '; minimum 30 minutes–2 hours'
        stages.append(dict(stage=stage, label=LABELS[stage], lowerSeconds=round(low), upperSeconds=round(high), basis=basis))
    lower, upper = sum(s['lowerSeconds'] for s in stages), sum(s['upperSeconds'] for s in stages)
    at = parse_time(last['at'])
    finish_low, finish_high = at + timedelta(seconds=lower), at + timedelta(seconds=upper)
    finish_low = datetime.fromtimestamp(floor(finish_low.timestamp()/1800)*1800, timezone.utc)
    finish_high = datetime.fromtimestamp(ceil(finish_high.timestamp()/1800)*1800, timezone.utc)
    return dict(status='overdue' if now > finish_high and upper else 'estimated',
                confidence='Early estimate' if measured_categories < 3 else 'Developing estimate',
                updatedAt=last['at'], lowerSeconds=lower, upperSeconds=upper,
                earliestCompletion=finish_low.isoformat(), latestCompletion=finish_high.isoformat(),
                stages=stages, completedContentCategories=measured_categories,
                basis=f'Based on {round(content_units)} saved resource/candidate decisions across {measured_categories} completed content categor{"y" if measured_categories == 1 else "ies"}; startup time is included. Unmeasured stages use the listed planning allowances.',
                assumptions='Assumes continued operation. Includes cross-category consolidation, taxonomy, selections, final validation and supervisor audit; excludes import/publication. This is a planning range, not a statistical confidence interval.')


def estimate_review(root, database, job_id, progress, pipeline, now=None):
    root = Path(root)
    now = now or datetime.now(timezone.utc)
    phase = pipeline.get('phase')
    if phase not in {'review', 'ready-review'}:
        label = ('Review is stopped or awaiting supervisor action; no running completion estimate.'
                 if phase in {'paused', 'needs-attention'} else 'Review estimate becomes available during active review.')
        if phase in {'prepared-delivery-ready', 'prepared-delivery-complete'}:
            label = 'Review and export checks finished.'
        return dict(status='inactive', label=label)
    if not progress.get('checkpointAvailable') or progress.get('checkpointError'):
        return dict(status='learning', label='Awaiting a valid saved review checkpoint.')
    try:
        sessions = []
        for path in sorted((root / 'review').glob('session-*/launch.json')):
            launch = json.loads(path.read_text())
            start = parse_time(launch['startedAt'])
            execution = path.parent / 'execution.json'
            stop = start + timedelta(seconds=json.loads(execution.read_text())['elapsedSeconds']) if execution.exists() else now
            sessions.append((start, min(stop, now)))
        if not sessions:
            raise ValueError('No current review timing')
        with sqlite3.connect(Path(database).resolve().as_uri() + '?mode=ro', uri=True) as connection:
            rows = connection.execute('SELECT category_id,candidate_count,resource_count FROM scout_curation_categories WHERE job_id=?', (job_id,)).fetchall()
        workloads = {cid: candidates + resources for cid, candidates, resources in rows}
        workloads.setdefault('miscellaneous', 0)
        ids = {r['categoryId'] for r in progress['categories']}
        if not ids or not ids.issubset(workloads):
            raise ValueError('Review workload is unavailable')
        totals = dict(content=sum(workloads[cid] for cid in ids), identity=1, taxonomy=len(ids), selection=len(ids), validation=1)
        done = dict(content=0, identity=int(progress['identityStatus']=='complete'),
                    taxonomy=progress['taxonomyCompleted'], selection=progress['selectionCompleted'],
                    validation=int(progress['validationStatus']=='complete'))
        completed = {r['categoryId'] for r in progress['categories'] if r['content']=='complete'}
        done['content'] = sum(workloads[cid] for cid in completed)
        records = progress.get('recordProgress')
        if records and records['categoryId'] not in completed:
            done['content'] += min(workloads[records['categoryId']], records['resourcesReviewed'] + records['candidatesReviewed'])
        observed = dict(at=progress['updatedAt'], stage=progress['stage'], done=done, contentCategories=len(completed))
        if parse_time(observed['at']) < sessions[0][0] or parse_time(observed['at']) > now:
            raise ValueError('Checkpoint is outside current review timing')
        key = sessions[0][0].isoformat()
        path = root / 'review-estimate-history.json'
        with (root / 'review-estimate-history.lock').open('a+') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            saved = json.loads(path.read_text()) if path.exists() else {}
            if saved.get('runStart') != key or saved.get('totals') != totals:
                saved = dict(runStart=key, totals=totals, checkpoints=[dict(at=key, stage='content', done={s:0 for s in STAGES}, contentCategories=0)])
            history = saved['checkpoints']
            previous = history[-1]
            newer = parse_time(observed['at']) > parse_time(previous['at'])
            if newer and any(done[s] < previous['done'][s] for s in STAGES):
                # Reopened decisions invalidate old pace. Start learning again.
                history[:] = [observed]
            elif newer and (done != previous['done'] or observed['stage'] != previous['stage']):
                history.append(observed)
            encoded = json.dumps(saved, indent=2) + '\n'
            if not path.exists() or path.read_text() != encoded:
                temporary = path.with_suffix('.tmp'); temporary.write_text(encoded); temporary.replace(path)
        return forecast(history, totals, sessions, now)
    except (OSError, ValueError, KeyError, TypeError, sqlite3.Error) as error:
        return dict(status='learning', label='Learning review pace — not enough valid timing evidence yet.', basis=str(error))
