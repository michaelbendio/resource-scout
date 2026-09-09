"""Opt-in, content-free operational timings; never part of research state/hashes."""
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
import json
from pathlib import Path
from time import perf_counter
import warnings

_sink = ContextVar('scout_timing_sink', default=None)


@contextmanager
def measured(phase):
    sink = _sink.get()
    counters = {}
    if sink is None:
        yield counters
        return
    start = perf_counter()
    status = 'ok'
    try:
        yield counters
    except BaseException:
        status = 'error'
        raise
    finally:
        # Only numeric counters are permitted. Never serialize errors or payloads.
        event = {'schemaVersion': 1, 'phase': phase, 'status': status,
                 'seconds': max(0.0, perf_counter() - start),
                 'recordedAt': datetime.now(timezone.utc).isoformat(),
                 'counters': {k: v for k, v in counters.items()
                              if k in {'inputBytes', 'outputBytes', 'characters', 'records'}
                              and type(v) in (int, float)}}
        sink(event)


@contextmanager
def capture_timings():
    events = []
    token = _sink.set(events.append)
    try:
        yield events
    finally:
        _sink.reset(token)


@contextmanager
def timing_session(path=None):
    if path is None:
        yield
        return
    try:
        destination = Path(path).expanduser()
        destination.parent.mkdir(parents=True, exist_ok=True)
        handle = destination.open('a', encoding='utf-8')
    except OSError:
        warnings.warn('Scout timing output could not be opened; work will continue.', RuntimeWarning)
        yield
        return
    failed = False

    def emit(event):
        nonlocal failed
        if failed:
            return
        try:
            handle.write(json.dumps(event, allow_nan=False) + '\n')
            handle.flush()
        except (OSError, ValueError):
            failed = True
            warnings.warn('Scout timing output failed; work will continue.', RuntimeWarning)

    token = _sink.set(emit)
    try:
        yield
    finally:
        _sink.reset(token)
        try:
            handle.close()
        except OSError:
            warnings.warn('Scout timing output could not be closed.', RuntimeWarning)


def summarize_timings(path):
    phases = {}
    for line in Path(path).read_text().splitlines():
        event = json.loads(line)
        if event.get('schemaVersion') != 1 or not isinstance(event.get('phase'), str):
            raise ValueError('Unsupported Scout timing record')
        bucket = phases.setdefault(event['phase'], {'count': 0, 'seconds': 0.0, 'errors': 0})
        bucket['count'] += 1
        bucket['seconds'] += event['seconds']
        bucket['errors'] += event['status'] == 'error'
    return {'phases': phases,
            'note': 'Phases can be nested; do not add their durations as total wall time. No provider time or cost is inferred.'}
