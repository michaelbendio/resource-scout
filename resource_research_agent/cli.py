from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .duplicates import DuplicateIndex
from .importer import ResourcePackageImporter
from .server import serve
from .storage import ResearchStore
from .tailscale import TailscaleAccessError, TailscaleServeManager


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="resource-scout")
    result.add_argument("--database", default="data/research-agent.sqlite3", help="Separate research database path")
    subcommands = result.add_subparsers(dest="command", required=True)
    import_command = subcommands.add_parser("import", help="Read a resource-package.zip into an immutable snapshot")
    import_command.add_argument("package")
    import_command.add_argument("--category", default="Housing")
    import_command.add_argument("--report", help="Write a JSON import report")
    serve_command = subcommands.add_parser("serve", help="Run Resource Scout")
    serve_command.add_argument("--host", default="127.0.0.1")
    serve_command.add_argument("--port", type=int, default=8765)
    tailscale_command = subcommands.add_parser(
        "tailscale", help="Run the app privately for devices on this Tailscale network"
    )
    tailscale_command.add_argument("--port", type=int, default=8765)
    match_command = subcommands.add_parser("match", help="Check candidate JSON against the known-resource index")
    match_command.add_argument("candidate", help="JSON file containing a candidate object")
    match_command.add_argument("--limit", type=int, default=5)
    subcommands.add_parser("summary", help="Show the latest import summary")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.command == "serve":
        serve(args.database, args.host, args.port)
        return 0
    if args.command == "tailscale":
        try:
            access = TailscaleServeManager().configure(args.port)
        except KeyboardInterrupt:
            print("\nPrivate iPad setup stopped.", file=sys.stderr)
            return 130
        except TailscaleAccessError as error:
            print(f"Private iPad access could not start:\n{error}", file=sys.stderr)
            return 1
        print("Private iPad access is ready")
        print(f"Open on an iPad connected to Tailscale: {access.private_url}")
        print("This address is private to your Tailscale network. Public Funnel is not enabled.")
        print("Keep this window open while using the app.")
        serve(args.database, "127.0.0.1", args.port, private_url=access.private_url)
        return 0
    store = ResearchStore(args.database)
    if args.command == "import":
        package = ResourcePackageImporter(args.category).read(args.package)
        import_id = store.save_import(package)
        summary = store.import_summary(import_id)
        output = json.dumps(summary, ensure_ascii=False, indent=2)
        print(output)
        if args.report:
            Path(args.report).write_text(output + "\n", encoding="utf-8")
        return 0
    if args.command == "match":
        candidate = json.loads(Path(args.candidate).read_text(encoding="utf-8"))
        print(json.dumps(DuplicateIndex(store).match(candidate, limit=args.limit), ensure_ascii=False, indent=2))
        return 0
    if args.command == "summary":
        print(json.dumps(store.import_summary(), ensure_ascii=False, indent=2))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
