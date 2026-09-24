"""One local research runner per canonical SQLite path (macOS/Linux)."""
from __future__ import annotations

import fcntl
import json
import os
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import Iterator

_held_databases = ContextVar('research_runner_databases', default=frozenset())


def assert_runner_lock_held(database: Path) -> None:
    if Path(database).expanduser().resolve() not in _held_databases.get():
        raise RuntimeError('This coordinator must hold the database runner lock')


@contextmanager
def research_runner_lock(database: Path) -> Iterator[None]:
    database = database.expanduser().resolve()
    lock_path = database.with_name(database.name + ".runner.lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+") as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError(f"A research runner already holds {lock_path}") from error
        try:
            handle.seek(0)
            handle.truncate()
            json.dump({"pid": os.getpid(), "database": str(database)}, handle)
            handle.flush()
            token = _held_databases.set(_held_databases.get() | {database})
            try:
                yield
            finally:
                _held_databases.reset(token)
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    # Keep the inode: unlinking it would let another process lock a different
    # file while a waiter still holds the original. A stale file is harmless.
