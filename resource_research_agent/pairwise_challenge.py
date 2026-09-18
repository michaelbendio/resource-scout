from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .codex_first_research import (
    next_codex_first_assignment,
    save_codex_first_external_result,
)
from .storage import ResearchStore


def _copy_to_clipboard(text: str) -> bool:
    pbcopy = shutil.which("pbcopy")
    if not pbcopy:
        return False
    subprocess.run([pbcopy], input=text, text=True, check=True)
    return True


def _read_clipboard() -> str:
    pbpaste = shutil.which("pbpaste")
    if not pbpaste:
        raise RuntimeError("pbpaste is required for clipboard submission")
    completed = subprocess.run(
        [pbpaste],
        text=True,
        capture_output=True,
        check=True,
    )
    return completed.stdout


def _open_app(name: str) -> bool:
    opener = shutil.which("open")
    if not opener:
        return False
    completed = subprocess.run(
        [opener, "-a", name],
        text=True,
        capture_output=True,
        check=False,
    )
    return completed.returncode == 0


def next_challenge(
    store: ResearchStore,
    import_id: int,
    researcher: str,
    *,
    copy: bool = False,
    open_app: bool = False,
    output: Path | None = None,
) -> dict[str, Any] | None:
    assignment = next_codex_first_assignment(store, import_id, researcher)
    if assignment is None:
        return None
    if assignment["kind"] not in {"challenger", "shadow"}:
        raise ValueError(f"{researcher} does not have an external assignment")
    external = assignment["externalAssignment"]
    text = str(external["assignment"])
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
    copied = _copy_to_clipboard(text) if copy else False
    opened = _open_app(researcher) if open_app else False
    return {
        "assignmentId": int(external["id"]),
        "jobId": int(assignment["job"]["id"]),
        "categoryId": str(assignment["job"]["categoryId"]),
        "categoryLabel": str(assignment["job"]["categoryLabel"]),
        "researcher": str(external["researcher"]),
        "role": str(external["role"]),
        "status": str(external["status"]),
        "copiedToClipboard": copied,
        "openedApp": opened,
        "outputFile": str(output) if output is not None else "",
        "assignment": text,
    }


def submit_challenge(
    store: ResearchStore,
    assignment_id: int,
    result_file: Path,
) -> dict[str, Any]:
    raw_text = result_file.read_text(encoding="utf-8")
    saved = save_codex_first_external_result(store, assignment_id, raw_text)
    return {
        "assignmentId": int(saved["id"]),
        "researcher": str(saved["researcher"]),
        "status": str(saved["status"]),
        "leadCount": int(saved["leadCount"]),
        "rawSha256": str(saved["rawSha256"] or ""),
    }


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(
        description="Read or submit one external pairwise Scout challenge"
    )
    value.add_argument("--database", default="data/research-agent.sqlite3")
    value.add_argument("--import-id", type=int)
    sub = value.add_subparsers(dest="command", required=True)

    read = sub.add_parser("next", help="Read the next external challenge")
    read.add_argument("--researcher", default="Grok")
    read.add_argument("--copy", action="store_true")
    read.add_argument("--open-app", action="store_true")
    read.add_argument("--output", type=Path)

    submit = sub.add_parser("submit", help="Submit one external challenge result")
    submit.add_argument("assignment_id", type=int)
    submit.add_argument("result_file", type=Path)

    clipboard = sub.add_parser(
        "submit-clipboard",
        help="Submit one external challenge result from the macOS clipboard",
    )
    clipboard.add_argument("assignment_id", type=int)
    return value


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    store = ResearchStore(args.database)
    import_id = int(args.import_id or store.latest_import_id() or 0)
    if not import_id:
        raise SystemExit("Import a resource package before reading pairwise challenges")

    if args.command == "next":
        value = next_challenge(
            store,
            import_id,
            args.researcher,
            copy=args.copy,
            open_app=args.open_app,
            output=args.output,
        )
        if value is None:
            print(json.dumps({"assignment": None}, ensure_ascii=False))
            return 0
        print(json.dumps(value, indent=2, ensure_ascii=False))
        return 0

    if args.command == "submit":
        value = submit_challenge(store, args.assignment_id, args.result_file)
    else:
        raw_text = _read_clipboard()
        saved = save_codex_first_external_result(store, args.assignment_id, raw_text)
        value = {
            "assignmentId": int(saved["id"]),
            "researcher": str(saved["researcher"]),
            "status": str(saved["status"]),
            "leadCount": int(saved["leadCount"]),
            "rawSha256": str(saved["rawSha256"] or ""),
        }
    print(json.dumps(value, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
