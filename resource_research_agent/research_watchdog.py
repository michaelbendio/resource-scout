"""Persistent research health checks and bounded, evidence-preserving recovery.

This is deterministic supervision, not an autonomous code-editing AI. Unknown
requests, invalid findings, budget/auth failures and primary crashes need diagnosis.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import time

from . import deepseek_challenger_runner as challenger
from .curation_supervisor import notify_local
from .worker_lifecycle import process_identity

read, write, now = challenger.read, challenger.write, challenger.now


def recover_saved_response(directory: Path) -> str | None:
    """Offline fixes only, with originals retained and at most one per turn."""
    state_path = directory / 'state.json'
    state = read(state_path)
    if state['status'] != 'failed':
        return None
    turn = directory / f"turn-{state['turn']:03}"
    if not (turn / 'response.json').exists() or not (turn / 'billing.json').exists():
        return None
    body = read(turn / 'response.json')
    if (body.get('model') != challenger.MODEL or not state['successfulSearchResults']
            or not state['messages'] or state['messages'][-1].get('content') != body.get('content')):
        return None
    result = None
    if body['stop_reason'] == 'end_turn':
        try:
            result = challenger.final_response_result(body)
        except (ValueError, KeyError, TypeError):
            return None
        state.update(status='completed', completedAt=now(), leadCount=len(result['leads']))
        kind = 'saved-final-answer'
    elif challenger.checkpoint_search_limit(body, state):
        kind = 'saved-search-limit'
    else:
        return None
    audit = directory / f"watchdog-recovery-turn-{state['turn']:03}"
    if audit.exists():
        return None
    audit.mkdir()
    original = state_path.read_bytes()
    (audit / 'original-failed-state.json').write_bytes(original)
    write(audit / 'recovery.json', dict(at=now(), kind=kind, newInferenceCalls=0,
          originalStateSha256=hashlib.sha256(original).hexdigest(),
          responseSha256=hashlib.sha256((turn / 'response.json').read_bytes()).hexdigest()))
    if result is not None:
        write(directory / 'result.json', result)
    write(state_path, state)
    return kind


def validated_command(launch, root):
    command = launch['deepseekCommand']
    if not isinstance(command, list) or not all(isinstance(x, str) for x in command):
        raise ValueError('Invalid challenger command')
    prefix = command[:command.index('-m')]
    if prefix[:2] == ['/usr/bin/caffeinate', '-dimsu']:
        prefix = prefix[2:]
    if len(prefix) == 2 and prefix[1] == '-u':
        prefix = prefix[:1]
    if len(prefix) != 1 or not Path(prefix[0]).name.lower().startswith('python'):
        raise ValueError('Expected direct Python module command')
    if command[command.index('-m') + 1] != 'resource_research_agent.deepseek_challenger_runner':
        raise ValueError('Unexpected challenger module')
    for flag, expected in [('--database', launch['database']), ('--import-id', str(launch['importId'])),
                           ('--output-dir', str(root / 'deepseek-challenger')),
                           ('--budget-usd', str(launch['deepseekBudgetUsd']))]:
        if command.count(flag) != 1 or command[command.index(flag) + 1] != expected:
            raise ValueError('Challenger command changed: ' + flag)
    return command


def restart_allowed(states, last_status, restarts, maximum):
    return (restarts < maximum and bool(states)
            and not any(s['status'] not in {'prepared', 'awaiting-tools', 'completed'} for s in states)
            and last_status != 'needs-attention')


def supervise(root: Path, *, interval=30, maximum_restarts=3, notify=False):
    root = root.resolve()
    out = root / 'deepseek-challenger'
    status_path = root / 'research-watchdog-status.json'
    journal = root / 'research-issues.jsonl'
    prior = read(status_path) if status_path.exists() else {}
    restarts = int(prior.get('challengerRestarts', 0))
    identities = prior.get('identities', {})
    previous_issues = prior.get('issues', [])
    child = None
    with (root / 'research-watchdog.lock').open('a+') as lease:
        fcntl.flock(lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
        while True:
            if child is not None:
                child.poll()
            launch = read(root / 'launch.json')
            manifest = read(out / 'manifest.json')
            if (manifest.get('database') != launch['database']
                    or manifest.get('importId') != launch['importId']
                    or manifest.get('model') != challenger.MODEL):
                raise ValueError('Challenger manifest does not match the supervised run')
            live = {}
            for key, module in [('pid', 'pairwise_runner'), ('deepseekPid', 'deepseek_challenger_runner')]:
                pid = launch[key]
                identity = process_identity(pid)
                valid = bool(identity and not identity['state'].startswith('Z')
                             and f'-m resource_research_agent.{module} ' in identity['identity']
                             and launch['database'] in identity['identity'])
                token = f'{key}:{pid}'
                if valid and token not in identities:
                    identities[token] = identity['identity']
                live[key] = bool(valid and identities.get(token) == identity['identity'])
            with sqlite3.connect(f"file:{launch['database']}?mode=ro", uri=True) as db:
                total, done = db.execute('SELECT count(*),sum(status=?) FROM focused_research_jobs WHERE import_id=?',
                                        ('completed', launch['importId'])).fetchone()
                primary_done = db.execute("SELECT count(*) FROM focused_research_jobs j WHERE import_id=? AND EXISTS(SELECT 1 FROM focused_research_passes p WHERE p.job_id=j.id AND p.pass_kind='gap' AND p.status='completed') AND NOT EXISTS(SELECT 1 FROM focused_research_passes p WHERE p.job_id=j.id AND p.status!='completed')", (launch['importId'],)).fetchone()[0]
            complete = bool(total and done == total)
            paths = sorted(out.glob('assignment-*/state.json'))
            states = [read(p) for p in paths]
            last_status = read(out / 'supervisor-status.json').get('status')
            issues, recoveries = [], []
            if not live['pid'] and primary_done != total:
                issues.append('Primary coordinator stopped before research finished; preserve in-flight evidence for diagnosis.')
            if not live['deepseekPid'] and not complete:
                # Same lock as the actual challenger: no recovery while it is active.
                try:
                    with (out / 'challenger.lock').open('a+') as lock:
                        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        if restarts < maximum_restarts:
                            for path in paths:
                                kind = recover_saved_response(path.parent)
                                if kind:
                                    recoveries.append(dict(category=read(path)['category'], kind=kind))
                        states = [read(p) for p in paths]
                        decision_status = 'recovered' if recoveries else last_status
                        if restart_allowed(states, decision_status, restarts, maximum_restarts):
                            command = validated_command(launch, root)
                            restarts += 1
                            # Persist the budget before starting any new process.
                            write(status_path, dict(challengerRestarts=restarts, identities=identities,
                                                    issues=previous_issues, at=now(), status='restarting'))
                            # Release challenger lock before it starts its own loop.
                            fcntl.flock(lock, fcntl.LOCK_UN)
                            with (root / 'deepseek-runner.log').open('a') as log:
                                child = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
                            launch.update(deepseekPid=child.pid, updatedAt=now(), watchdogRestart=restarts)
                            write(root / 'launch.json', launch)
                            recoveries.append(dict(kind='coordinator-restarted', pid=child.pid))
                        else:
                            issues.append('DeepSeek stopped; unknown/in-flight request, invalid findings, auth/budget failure or recovery limit requires diagnosis.')
                except BlockingIOError:
                    issues.append('DeepSeek process identity unavailable but its lock is held; no duplicate launched.')
            primary_age = round(time.time() - (root / 'runner.log').stat().st_mtime)
            if live['pid'] and primary_done != total and primary_age > 2100:
                issues.append('Primary has no new checkpoint for over35 minutes; inspect worker activity before retrying.')
            for path, state in zip(paths, states):
                if live['deepseekPid'] and state['status'] == 'requesting' and time.time() - path.stat().st_mtime > 1020:
                    issues.append(f"DeepSeek request in {state['category']} has exceeded17 minutes; do not replay blindly.")
            status = dict(at=now(), supervisorPid=os.getpid(), status='research-complete-ready-to-curate' if complete else 'needs-attention' if issues else 'monitoring',
                          database=launch['database'], importId=launch['importId'],
                          primaryAlive=live['pid'], challengerAlive=live['deepseekPid'], completedCategories=done,
                          totalCategories=total, primaryCompletedCategories=primary_done, primaryEventAgeSeconds=primary_age,
                          challengerRestarts=restarts, maximumRestarts=maximum_restarts, identities=identities, issues=issues)
            write(status_path, status)
            if issues != previous_issues or recoveries or complete:
                event = dict(at=now(), issues=issues, recoveries=recoveries, completedCategories=done, status=status['status'])
                if notify and (issues or recoveries or complete):
                    event['notification'] = notify_local('Las Vegas Scout: ' + ('research complete, ready to curate' if complete else '; '.join(issues) if issues else 'saved work recovered; challenger resumed'))
                with journal.open('a') as stream:
                    stream.write(json.dumps(event) + '\n')
                previous_issues = issues
            if complete:
                return
            time.sleep(interval)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_directory', type=Path)
    parser.add_argument('--interval', type=float, default=30)
    parser.add_argument('--maximum-restarts', type=int, default=3)
    parser.add_argument('--notify', action='store_true')
    args = parser.parse_args()
    if not 1 <= args.interval <= 60 or args.maximum_restarts < 0:
        parser.error('Interval must be1–60 seconds; restart budget must be nonnegative')
    try:
        supervise(args.run_directory, interval=args.interval, maximum_restarts=args.maximum_restarts, notify=args.notify)
    except Exception as error:
        if not isinstance(error, BlockingIOError):
            path = args.run_directory / 'research-watchdog-status.json'
            status = read(path) if path.exists() else {}
            status.update(at=now(), status='supervisor-needs-attention', error=str(error)[:500])
            write(path, status)
            if args.notify:
                notify_local('Las Vegas research supervisor stopped: inspect research-watchdog-status.json')
        raise


if __name__ == '__main__':
    main()
