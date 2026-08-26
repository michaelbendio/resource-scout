from __future__ import annotations

import argparse
from contextlib import closing
import os
from pathlib import Path
import sqlite3
import threading

from .dsh_configuration import TRACE_QWEN_CONFIGURATION
from .server import serve
from .storage import ResearchStore
from .trace_console import (
    TRACE_HOST,
    TRACE_MODEL_PORT,
    TRACE_UI_PORT,
    TraceHub,
    TraceModelServer,
    TraceUIServer,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE_DATABASE = PROJECT_ROOT / "data" / "research-agent.sqlite3"
DEFAULT_TRACE_DATABASE = PROJECT_ROOT / "data" / "trace-scout.sqlite3"
DEFAULT_TRACE_LOG = PROJECT_ROOT / "data" / "scout-trace.jsonl"


def fresh_database(source: Path, target: Path) -> None:
    source = source.expanduser().resolve()
    target = target.expanduser().resolve()
    if source == target:
        raise ValueError("The temporary Trace Scout database must differ from production")
    if not source.is_file():
        raise ValueError(f"Production Scout database does not exist: {source}")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.unlink(missing_ok=True)
    with closing(sqlite3.connect(source)) as source_connection, closing(
        sqlite3.connect(temporary)
    ) as target_connection:
        source_connection.backup(target_connection)
        target_connection.commit()
    store = ResearchStore(temporary, recover_interrupted=True)
    with store.connect() as connection:
        connection.execute("DELETE FROM research_lessons")
        connection.execute("DELETE FROM discoveries")
        connection.execute("DELETE FROM research_runs")
    store.save_settings(
        {
            "adapter": "dsh",
            "dshConfiguration": TRACE_QWEN_CONFIGURATION,
            "dshModel": "",
            "timeoutSeconds": 7200,
        }
    )
    temporary.replace(target)


def prepare_database(source: Path, target: Path, *, fresh: bool) -> Path:
    target = target.expanduser().resolve()
    if fresh or not target.is_file():
        fresh_database(source, target)
    else:
        ResearchStore(target, recover_interrupted=True).save_settings(
            {
                "adapter": "dsh",
                "dshConfiguration": TRACE_QWEN_CONFIGURATION,
                "dshModel": "",
                "timeoutSeconds": 7200,
            }
        )
    return target


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Run isolated Resource Scout with an approval-gated communication trace"
    )
    result.add_argument("--source-database", type=Path, default=DEFAULT_SOURCE_DATABASE)
    result.add_argument("--database", type=Path, default=DEFAULT_TRACE_DATABASE)
    result.add_argument("--trace-log", type=Path, default=DEFAULT_TRACE_LOG)
    result.add_argument("--scout-port", type=int, default=8766)
    result.add_argument(
        "--fresh",
        action="store_true",
        help="replace the disposable trace database and trace log with a clean snapshot",
    )
    return result


def main(argv: list[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    try:
        database = prepare_database(
            arguments.source_database,
            arguments.database,
            fresh=arguments.fresh,
        )
        trace_path = arguments.trace_log.expanduser().resolve()
        if arguments.fresh:
            trace_path.unlink(missing_ok=True)
    except (OSError, sqlite3.Error, ValueError) as exc:
        raise SystemExit(str(exc)) from exc

    os.environ.pop("RESOURCE_SCOUT_REQUIRE_UNMETERED", None)
    os.environ["RESOURCE_RESEARCH_DSH_HOME"] = str(
        (PROJECT_ROOT / "dsh-runtime" / ".dsh-trace-home").resolve()
    )
    os.environ["RESOURCE_SCOUT_TRACE_ENDPOINT"] = f"http://{TRACE_HOST}:{TRACE_UI_PORT}"

    hub = TraceHub(trace_path)
    ui_server = TraceUIServer((TRACE_HOST, TRACE_UI_PORT), hub)
    model_server = TraceModelServer((TRACE_HOST, TRACE_MODEL_PORT), hub)
    threads = [
        threading.Thread(target=ui_server.serve_forever, name="trace-console", daemon=True),
        threading.Thread(target=model_server.serve_forever, name="trace-qwen-proxy", daemon=True),
    ]
    for thread in threads:
        thread.start()
    print("Temporary Trace Scout is isolated from production.")
    print(f"1. Open Trace Console: http://{TRACE_HOST}:{TRACE_UI_PORT}")
    print(f"2. Open temporary Scout: http://{TRACE_HOST}:{arguments.scout_port}")
    print("Qwen remains the researcher; Trace Console gates each logical handoff.")
    print("Keep this window open. Press Control-C here to stop both temporary apps.")
    try:
        serve(database, TRACE_HOST, arguments.scout_port)
    finally:
        hub.release_all()
        for server in (model_server, ui_server):
            server.shutdown()
            server.server_close()
        for thread in threads:
            thread.join(timeout=5)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
