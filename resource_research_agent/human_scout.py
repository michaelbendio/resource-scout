from __future__ import annotations

import argparse
from contextlib import closing
import os
from pathlib import Path
import sqlite3
import threading

from .dsh_configuration import HUMAN_CONFIGURATION
from .human_model import DEFAULT_HOST, DEFAULT_PORT, HumanModelServer
from .server import serve
from .storage import ResearchStore


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE_DATABASE = PROJECT_ROOT / "data" / "research-agent.sqlite3"
DEFAULT_HUMAN_DATABASE = PROJECT_ROOT / "data" / "human-scout.sqlite3"


def fresh_database(source: Path, target: Path) -> None:
    source = source.expanduser().resolve()
    target = target.expanduser().resolve()
    if source == target:
        raise ValueError("The temporary Human Scout database must differ from production")
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
            "dshConfiguration": HUMAN_CONFIGURATION,
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
                "dshConfiguration": HUMAN_CONFIGURATION,
                "dshModel": "",
                "timeoutSeconds": 7200,
            }
        )
    return target


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Run an isolated temporary Scout whose model decisions come from you"
    )
    result.add_argument("--source-database", type=Path, default=DEFAULT_SOURCE_DATABASE)
    result.add_argument("--database", type=Path, default=DEFAULT_HUMAN_DATABASE)
    result.add_argument("--scout-port", type=int, default=8766)
    result.add_argument("--human-port", type=int, default=DEFAULT_PORT)
    result.add_argument(
        "--fresh",
        action="store_true",
        help="replace the disposable Human Scout database with a clean production snapshot",
    )
    return result


def main(argv: list[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    if arguments.human_port != DEFAULT_PORT:
        raise SystemExit(f"--human-port must remain {DEFAULT_PORT}; the locked DSH route uses it")
    try:
        database = prepare_database(
            arguments.source_database,
            arguments.database,
            fresh=arguments.fresh,
        )
    except (OSError, sqlite3.Error, ValueError) as exc:
        raise SystemExit(str(exc)) from exc

    # The production launcher deliberately locks its instance to Qwen. This
    # separate process is still unmetered, but explicitly selects Human Model.
    os.environ.pop("RESOURCE_SCOUT_REQUIRE_UNMETERED", None)
    os.environ["RESOURCE_RESEARCH_DSH_HOME"] = str(
        (PROJECT_ROOT / "dsh-runtime" / ".dsh-human-home").resolve()
    )
    human_server = HumanModelServer((DEFAULT_HOST, arguments.human_port))
    human_thread = threading.Thread(
        target=human_server.serve_forever,
        name="resource-scout-human-model",
        daemon=True,
    )
    human_thread.start()
    print("Temporary Human Scout is isolated from production.")
    print(f"1. Open Human Model: http://{DEFAULT_HOST}:{arguments.human_port}")
    print(f"2. Open temporary Scout: http://{DEFAULT_HOST}:{arguments.scout_port}")
    print("Keep this window open. Press Control-C here to stop both temporary apps.")
    try:
        serve(database, DEFAULT_HOST, arguments.scout_port)
    finally:
        human_server.shutdown()
        human_server.server_close()
        human_thread.join(timeout=5)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
