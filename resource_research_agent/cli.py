from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .duplicates import DuplicateIndex
from .codex_replay import (
    codex_replay_view,
    next_codex_replay_assignment,
    prepare_codex_replay_study,
    reveal_and_complete_codex_replay,
    save_codex_replay_result,
)
from .importer import ResourcePackageImporter
from .server import serve
from .storage import ResearchStore
from .tailscale import TailscaleAccessError, TailscaleServeManager
from .taxonomy_study import prepare_taxonomy_study, taxonomy_study_summary


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
    replay_prepare = subcommands.add_parser(
        "replay-prepare", help="Seal a source-hidden Codex-first v1/v2 replay"
    )
    replay_prepare.add_argument("--import-id", type=int)
    replay_status = subcommands.add_parser("replay-status", help="Show a Codex replay")
    replay_status.add_argument("study_id", type=int)
    replay_next = subcommands.add_parser("replay-next", help="Read the next v2 assignment")
    replay_next.add_argument("study_id", type=int)
    replay_submit = subcommands.add_parser("replay-submit", help="Submit one v2 pass result")
    replay_submit.add_argument("study_id", type=int)
    replay_submit.add_argument("job_id", type=int)
    replay_submit.add_argument("focus_key")
    replay_submit.add_argument("result_file")
    replay_reveal = subcommands.add_parser(
        "replay-reveal", help="Reveal holdouts and calculate the final comparison"
    )
    replay_reveal.add_argument("study_id", type=int)
    taxonomy_prepare = subcommands.add_parser(
        "taxonomy-prepare", help="Freeze a full-corpus taxonomy review study"
    )
    taxonomy_prepare.add_argument("--import-id", type=int, required=True)
    taxonomy_prepare.add_argument("--curation-job-id", type=int, required=True)
    taxonomy_prepare.add_argument("--replay-study-id", type=int, required=True)
    taxonomy_status = subcommands.add_parser(
        "taxonomy-status", help="Show a concise taxonomy study status"
    )
    taxonomy_status.add_argument("study_id", type=int)
    taxonomy_review = subcommands.add_parser(
        "taxonomy-category-review", help="Show the need-Category review worksheet"
    )
    taxonomy_review.add_argument("study_id", type=int)
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
    if args.command == "replay-prepare":
        value = prepare_codex_replay_study(store, args.import_id)
        print(json.dumps(value, ensure_ascii=False, indent=2))
        return 0
    if args.command == "replay-status":
        print(json.dumps(codex_replay_view(store, args.study_id), ensure_ascii=False, indent=2))
        return 0
    if args.command == "replay-next":
        value = next_codex_replay_assignment(store, args.study_id)
        print(json.dumps({"assignment": value}, ensure_ascii=False, indent=2))
        return 0
    if args.command == "replay-submit":
        raw_text = Path(args.result_file).read_text(encoding="utf-8")
        value = save_codex_replay_result(
            store, args.study_id, args.job_id, args.focus_key, raw_text
        )
        print(json.dumps(value, ensure_ascii=False, indent=2))
        return 0
    if args.command == "replay-reveal":
        value = reveal_and_complete_codex_replay(store, args.study_id)
        print(json.dumps(value, ensure_ascii=False, indent=2))
        return 0
    if args.command == "taxonomy-prepare":
        value = prepare_taxonomy_study(
            store,
            args.import_id,
            curation_job_id=args.curation_job_id,
            replay_study_id=args.replay_study_id,
        )
        print(json.dumps(taxonomy_study_summary(value), ensure_ascii=False, indent=2))
        return 0
    if args.command == "taxonomy-status":
        value = store.get_taxonomy_study(args.study_id)
        if value is None:
            raise ValueError("Taxonomy study not found")
        print(json.dumps(taxonomy_study_summary(value), ensure_ascii=False, indent=2))
        return 0
    if args.command == "taxonomy-category-review":
        value = store.get_taxonomy_study(args.study_id)
        if value is None:
            raise ValueError("Taxonomy study not found")
        print(json.dumps(value["categoryReview"], ensure_ascii=False, indent=2))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
