#!/usr/bin/env python3
"""Rebuild a timing snapshot from durable evidence; never alter worker state."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3


def read(path):
    return json.loads(path.read_text())


def seconds(start, end):
    return max(0, (datetime.fromisoformat(end) - datetime.fromisoformat(start)).total_seconds())


def report(run, curation=None):
    launch = read(run / 'launch.json')
    database = Path(launch['database']).resolve()
    out = run / 'deepseek-challenger'
    manifest = read(out / 'manifest.json') if (out / 'manifest.json').exists() else {}
    separate = manifest.get('database') == str(database) and manifest.get('importId') == launch['importId']
    attempts = []
    with sqlite3.connect(f'file:{database}?mode=ro', uri=True) as connection:
        rows = connection.execute('SELECT id,provider,outcome,elapsed_ms,category_label FROM research_worker_telemetry WHERE import_id=?', (launch['importId'],))
        for identifier, provider, outcome, elapsed, category in rows:
            if separate and provider == 'DeepSeek':
                continue  # Imported summaries duplicate the preserved request timings.
            attempts.append(dict(phase='research', provider=provider, outcome=outcome,
                                 seconds=elapsed / 1000, category=category, source=f'telemetry:{identifier}'))
    if separate:
        for path in sorted(out.glob('assignment-*/turn-*')):
            bill, failure = path / 'billing.json', path / 'failure.json'
            if bill.exists():
                duration, method = read(bill)['seconds'], 'monotonic'
            elif failure.exists():
                duration = seconds(read(path / 'reservation.json')['at'], read(failure)['at'])
                method = 'request-to-failure timestamps'
            else:
                continue  # In-flight or unresolved calls are not completed processing.
            attempts.append(dict(phase='research', provider='DeepSeek', outcome='failed' if failure.exists() else 'completed',
                                 seconds=duration, method=method, source=str(path)))
    if curation:
        for path in sorted(curation.rglob('execution.json')):
            if 'audit' in path.relative_to(curation).parts:
                continue
            execution = read(path)
            attempts.append(dict(phase='curation', provider='Codex', outcome='completed' if execution['exitCode'] == 0 else 'failed',
                                 seconds=execution['elapsedSeconds'], source=str(path)))
    review_path = run / 'review-time-sessions.json'
    sessions = read(review_path) if review_path.exists() else []
    review_seconds = sum(seconds(s['startedAt'], s['endedAt']) for s in sessions if s.get('endedAt'))
    now = datetime.now(timezone.utc).isoformat()
    totals = {}
    for attempt in attempts:
        key = f"{attempt['phase']}:{attempt['provider']}:{attempt['outcome']}"
        totals[key] = totals.get(key, 0) + attempt['seconds']
    return dict(asOf=now, elapsedSeconds=seconds(launch['createdAt'], launch.get('deliveredAt') or now),
                workerSeconds=sum(a['seconds'] for a in attempts), byPhaseProviderOutcomeSeconds=totals,
                reviewSessionSeconds=review_seconds, reviewSessionsRecorded=len(sessions),
                openReviewSessions=sum(not s.get('endedAt') for s in sessions),
                curationTimingIncluded=bool(curation), attempts=attempts,
                curationWorkersMissingFinalTiming=[str(p) for p in curation.rglob('worker.json')
                    if 'audit' not in p.relative_to(curation).parts and not p.with_name('execution.json').exists()] if curation else [],
                limits='Worker runtimes include provider/search latency, not GPU compute. Concurrent runtimes add together. '
                       'In-flight/unknown attempts, local tool overhead and unrecorded review sessions are excluded. '
                       'Review sessions measure active-session wall time, not model-only compute. Connectivity probes are excluded.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    parser.add_argument('--curation-dir', type=Path)
    review = parser.add_mutually_exclusive_group()
    review.add_argument('--review-start', metavar='DESCRIPTION')
    review.add_argument('--review-stop', action='store_true')
    args = parser.parse_args()
    if args.review_start or args.review_stop:
        path = args.run / 'review-time-sessions.json'
        sessions = read(path) if path.exists() else []
        active = [s for s in sessions if not s.get('endedAt')]
        stamp = datetime.now(timezone.utc).isoformat()
        if args.review_start:
            if active:
                parser.error('Close the existing review session before starting another')
            sessions.append(dict(description=args.review_start, startedAt=stamp))
        else:
            if len(active) != 1:
                parser.error('Expected exactly one open review session')
            active[0]['endedAt'] = stamp
        path.write_text(json.dumps(sessions, indent=2) + '\n')
    result = report(args.run.resolve(), args.curation_dir)
    target = args.run / 'timing-summary.json'
    target.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k not in {'attempts', 'limits'}}))
