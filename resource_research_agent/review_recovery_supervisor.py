"""Bounded recovery for authorized office reviews, without replacing live workers."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
from pathlib import Path
import subprocess
import time

from .curation_supervisor import notify_local
from .worker_failures import classify_worker_failure, native_error
from .worker_lifecycle import atomic_json, process_identity


def read(path):
    return json.loads(Path(path).read_text())


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def live(pid):
    identity = process_identity(pid) if pid else None
    return bool(identity and not identity['state'].startswith('Z'))


def saved_checkpoint(review, state, receipts):
    """Require a real saved decision file, never a heartbeat or native session log."""
    used = {state.get('reviewCheckpointSha256')}
    used.update(row.get('checkpointSha256') for row in receipts)
    for name in ('progress.json', 'STATUS.json'):
        try:
            doc = read(review / name)
            path = Path(doc.get('checkpointFile', '')).resolve()
            relative = path.relative_to(review.resolve())
            if (not relative.parts or relative.parts[0].startswith('session-')
                    or path.name in {'STATUS.json', 'progress.json'}
                    or not path.is_file() or not path.stat().st_size):
                continue
            fingerprint = digest(path)
            if fingerprint not in used:
                return path, fingerprint
        except (OSError, ValueError, TypeError):
            continue
    return None, None


def prepare_recovery(root, config, state):
    """Preserve the failed attempt and prepare only a demonstrably safe continuation."""
    review = root / 'review'
    directory = Path(state.get('reviewDirectory', '')).resolve()
    if directory.parent != review.resolve() or not directory.name.startswith('session-'):
        return False, 'Missing or invalid failed review session'
    if live(state.get('reviewPid')):
        return False, 'Review worker is still alive; refusing a duplicate'
    if state.get('reviewSessions', 0) >= config['maximumReviewSessions']:
        return False, 'Review session budget exhausted'
    try:
        execution = read(directory / 'execution.json')
    except (OSError, ValueError):
        return False, 'No confirmed worker exit record'
    if execution.get('timedOut'):
        return False, 'Review timed out; inspect liveness and saved work before retrying'
    if not execution.get('exitCode'):
        return False, 'Reviewer requested attention; not a failed worker'
    failure = classify_worker_failure(native_error(directory), timed_out=execution.get('timedOut', False))
    recovery_root = root / 'review-recovery'
    receipts = [read(p) for p in sorted(recovery_root.glob('attempt-*/receipt.json'))]
    if any(row['failedSession'] == directory.name for row in receipts):
        return False, 'This failed session already has a recovery attempt'
    if len(receipts) >= 6:
        return False, 'Automatic review recovery budget exhausted'
    checkpoint, fingerprint = saved_checkpoint(review, state, receipts)
    if failure.kind == 'context':
        if not checkpoint:
            return False, 'Context exhaustion without new saved decisions'
        if sum(row['failureKind'] == 'context' for row in receipts) >= 3:
            return False, 'Context recovery budget exhausted'
    elif failure.retryable:
        if sum(row['failureKind'] == 'transport' for row in receipts) >= 3:
            return False, 'Transport recovery budget exhausted'
        if not checkpoint and any(row.get('withoutNewProgress') for row in receipts):
            return False, 'Repeated transport failure without new saved progress'
    else:
        return False, f'{failure.kind}: {failure.message}'
    attempt = recovery_root / f'attempt-{len(receipts)+1:03}'
    attempt.mkdir(parents=True, exist_ok=False)
    for source in (root / 'pipeline-status.json', review / 'STATUS.json', review / 'progress.json'):
        if source.exists():
            (attempt / source.name).write_bytes(source.read_bytes())
    receipt = dict(at=datetime.now(timezone.utc).isoformat(), failedSession=directory.name,
                   failureKind=failure.kind, error=failure.message,
                   checkpointFile=str(checkpoint) if checkpoint else None,
                   checkpointSha256=fingerprint, withoutNewProgress=not bool(checkpoint),
                   eventsSha256=digest(directory / 'events.jsonl'),
                   priorReviewSessions=state['reviewSessions'])
    # Charge the durable retry allowance before any new worker can start.
    atomic_json(attempt / 'receipt.json', receipt)
    (review / 'AUTOMATIC_RECOVERY.md').write_text(
        'Resume the saved authored decisions; do not repeat completed groups.\n'
        'The last failed session is preserved at ' + str(directory) + '.\n'
        'Failure: ' + failure.kind + '. Keep the requested effort and full review depth.\n'
        'For content review, complete at most TWO groups of at most 15 resources per '
        'fresh session, fewer if evidence is large. Save progress.json and STATUS.json '
        'with continue, then END the session. Separate taxonomy/selection from content '
        'when needed. Use bounded reads and targeted source excerpts. For collection '
        'work, checkpoint one bounded reconciliation task per session.\n'
        'All original office rules, evidence requirements and supervisor acceptance '
        'gates remain mandatory. This recovery is not review completion.\n')
    if checkpoint:
        atomic_json(review / 'STATUS.json', dict(status='continue', checkpointFile=str(checkpoint),
                    summary='Automatic recovery from ' + failure.kind + '; resume saved decisions and read AUTOMATIC_RECOVERY.md.'))
    state.update(phase='ready-review', reason='Automatic recovery: ' + failure.kind,
                 reviewRecoveryAttempt=str(attempt), at=receipt['at'])
    state.pop('reviewPid', None)
    atomic_json(root / 'pipeline-status.json', state)
    return True, str(attempt)


def supervise(launch_path, interval=30):
    launch = read(launch_path)
    config_path = Path(launch['config']).resolve()
    config = read(config_path)
    root = Path(config['runDirectory']).resolve()
    config_hash = digest(config_path)
    command = launch['pipelineCommand']
    if (not config.get('automaticReview') or not config.get('authorization')
            or config.get('reviewEffort') != 'xhigh'
            or (config.get('preparedMode') and not config.get('preparedReviewAuthorized'))):
        raise ValueError('Existing automatic review authorization is required')
    if not isinstance(command, list) or '--config' not in command or command[-1] != str(config_path):
        raise ValueError('Expected the exact existing pipeline command and config')
    with (root / 'review-recovery-supervisor.lock').open('a+') as lease:
        fcntl.flock(lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
        child = None
        while True:
            if child is not None:
                child.poll()
            state = read(root / 'pipeline-status.json')
            status = dict(at=datetime.now(timezone.utc).isoformat(), phase=state['phase'],
                          status='monitoring', pipelinePid=state.get('supervisorPid'))
            if digest(config_path) != config_hash:
                status.update(status='needs-attention', reason='Pipeline config changed; reconcile authorization')
            elif state['phase'] in {'paused', 'prepared-delivery-ready', 'prepared-delivery-complete',
                                     'needs-browser-verification', 'ready-for-codex-review', 'review-complete'}:
                status['status'] = 'handoff'
            elif not live(state.get('supervisorPid')):
                if state['phase'] == 'needs-attention':
                    recovered, reason = prepare_recovery(root, config, state)
                    if recovered:
                        with (root / 'pipeline.log').open('ab') as log:
                            child = subprocess.Popen(command, cwd=config['repository'], stdin=subprocess.DEVNULL,
                                                     stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
                        status.update(status='restarted', pipelinePid=child.pid, recovery=reason)
                        atomic_json(Path(reason) / 'launch.json', dict(pid=child.pid, command=command))
                        notify_local(f"{config.get('officeName', 'Office')} review recovered automatically; saved work preserved.")
                    else:
                        status.update(status='needs-attention', reason=reason)
                else:
                    status.update(status='needs-attention', reason='Pipeline exited outside a confirmed recoverable worker failure')
            atomic_json(root / 'review-recovery-status.json', status)
            if status['status'] in {'needs-attention', 'handoff'}:
                if status['status'] == 'needs-attention':
                    notify_local(f"{config.get('officeName', 'Office')} review needs diagnosis: {status.get('reason', '')[:200]}")
                return
            time.sleep(interval)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--launch', required=True, type=Path)
    args = parser.parse_args()
    try:
        supervise(args.launch)
    except BlockingIOError:
        raise  # Another monitor owns this run; do not overwrite its status.
    except Exception as error:
        config = read(read(args.launch)['config'])
        atomic_json(Path(config['runDirectory']) / 'review-recovery-status.json',
                    dict(status='needs-attention', at=datetime.now(timezone.utc).isoformat(),
                         reason=f'Recovery monitor error: {error}'))
        notify_local(f"{config.get('officeName', 'Office')} recovery monitor needs diagnosis: {str(error)[:200]}")
        raise


if __name__ == '__main__':
    main()
