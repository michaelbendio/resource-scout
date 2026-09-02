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
from .taxonomy_category_proposal import (
    save_mesa_category_redistribution_proposal,
)
from .taxonomy_study import (
    prepare_taxonomy_study,
    record_mesa_category_directions,
    taxonomy_study_summary,
)
from .taxonomy_types import (
    approve_categories_and_prepare_type_review,
    taxonomy_types_status,
)
from .taxonomy_type_design import save_category_type_designs
from .taxonomy_groups import (
    build_group_review_packet,
    save_group_inference,
    taxonomy_groups_status,
)
from .taxonomy_compile import compile_taxonomy_study
from .scout_review import build_scout_review_file
from .scout_enrichment import (
    build_scout_enriched_html,
    default_enriched_filename,
    ensure_scout_enrichment_audits,
    enrichment_project_summary,
    next_scout_enrichment_assignment,
    next_scout_enrichment_audit,
    next_scout_enrichment_reconciliation,
    prepare_scout_enrichment_project,
    save_scout_enrichment_audit_result,
    save_scout_enrichment_reconciliation_result,
    save_scout_enrichment_result,
)
from .scout_enrichment_checkpoint import (
    export_scout_enrichment_checkpoint,
    import_scout_enrichment_checkpoint,
)


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
    taxonomy_approve_directions = subcommands.add_parser(
        "taxonomy-record-mesa-directions",
        help="Record Michael's approved Mesa need-Category directions",
    )
    taxonomy_approve_directions.add_argument("study_id", type=int)
    taxonomy_propose_categories = subcommands.add_parser(
        "taxonomy-propose-mesa-categories",
        help="Create the resource-level Mesa need-Category proposal",
    )
    taxonomy_propose_categories.add_argument("study_id", type=int)
    taxonomy_category_proposal = subcommands.add_parser(
        "taxonomy-category-proposal",
        help="Show the latest resource-level need-Category proposal",
    )
    taxonomy_category_proposal.add_argument("study_id", type=int)
    taxonomy_approve_categories = subcommands.add_parser(
        "taxonomy-approve-mesa-categories",
        help="Approve the Mesa need Categories and prepare Type review packets",
    )
    taxonomy_approve_categories.add_argument("study_id", type=int)
    taxonomy_type_packet = subcommands.add_parser(
        "taxonomy-type-packet",
        help="Show one exact category-by-category Type review packet",
    )
    taxonomy_type_packet.add_argument("study_id", type=int)
    taxonomy_type_packet.add_argument("category_id")
    taxonomy_design_types = subcommands.add_parser(
        "taxonomy-design-category-types",
        help="Save the complete category-by-category Type design",
    )
    taxonomy_design_types.add_argument("study_id", type=int)
    taxonomy_design_new_types = subcommands.add_parser(
        "taxonomy-design-new-category-types",
        help="Legacy alias for taxonomy-design-category-types",
    )
    taxonomy_design_new_types.add_argument("study_id", type=int)
    taxonomy_type_design = subcommands.add_parser(
        "taxonomy-type-design",
        help="Show the latest Type design for one Category",
    )
    taxonomy_type_design.add_argument("study_id", type=int)
    taxonomy_type_design.add_argument("category_id")
    taxonomy_types_status_command = subcommands.add_parser(
        "taxonomy-types-status",
        help="Show category-by-category Types design progress",
    )
    taxonomy_types_status_command.add_argument("study_id", type=int)
    taxonomy_groups_prepare = subcommands.add_parser(
        "taxonomy-groups-prepare",
        help="Freeze the full-corpus For-group review packet",
    )
    taxonomy_groups_prepare.add_argument("study_id", type=int)
    taxonomy_groups_infer = subcommands.add_parser(
        "taxonomy-groups-infer",
        help="Infer target and accommodation For groups for every resource",
    )
    taxonomy_groups_infer.add_argument("study_id", type=int)
    taxonomy_groups_status_command = subcommands.add_parser(
        "taxonomy-groups-status",
        help="Show full-corpus For-group inference progress",
    )
    taxonomy_groups_status_command.add_argument("study_id", type=int)
    taxonomy_groups_proposal = subcommands.add_parser(
        "taxonomy-groups-proposal",
        help="Show the latest full-corpus For-group proposal for review",
    )
    taxonomy_groups_proposal.add_argument("study_id", type=int)
    taxonomy_compile = subcommands.add_parser(
        "taxonomy-compile",
        help="Compile an approved taxonomy study into auto[Location].html",
    )
    taxonomy_compile.add_argument("study_id", type=int)
    taxonomy_compile.add_argument(
        "--output",
        help="Output HTML path; defaults to the generated auto[Location].html name",
    )
    enrichment_prepare = subcommands.add_parser(
        "enrichment-prepare",
        help="Freeze an auto[Location].html into Stephanie-template assignments",
    )
    enrichment_prepare.add_argument("source_html")
    enrichment_status = subcommands.add_parser(
        "enrichment-status", help="Show concise enrichment project progress"
    )
    enrichment_status.add_argument("project_id", type=int)
    enrichment_next = subcommands.add_parser(
        "enrichment-next", help="Read or resume the next resource assignment"
    )
    enrichment_next.add_argument("project_id", type=int)
    enrichment_submit = subcommands.add_parser(
        "enrichment-submit", help="Validate and seal one resource result"
    )
    enrichment_submit.add_argument("project_id", type=int)
    enrichment_submit.add_argument("result_file")
    enrichment_audit_next = subcommands.add_parser(
        "enrichment-audit-next", help="Read or resume the next targeted external audit"
    )
    enrichment_audit_next.add_argument("project_id", type=int)
    enrichment_audit_next.add_argument("--researcher")
    enrichment_audit_submit = subcommands.add_parser(
        "enrichment-audit-submit", help="Validate and seal one external AI audit"
    )
    enrichment_audit_submit.add_argument("project_id", type=int)
    enrichment_audit_submit.add_argument("result_file")
    enrichment_reconcile_next = subcommands.add_parser(
        "enrichment-reconcile-next", help="Read or resume the next Codex reconciliation"
    )
    enrichment_reconcile_next.add_argument("project_id", type=int)
    enrichment_reconcile_submit = subcommands.add_parser(
        "enrichment-reconcile-submit", help="Validate and seal one Codex reconciliation"
    )
    enrichment_reconcile_submit.add_argument("project_id", type=int)
    enrichment_reconcile_submit.add_argument("result_file")
    enrichment_build = subcommands.add_parser(
        "enrichment-build", help="Build the completed non-destructive enriched HTML"
    )
    enrichment_build.add_argument("project_id", type=int)
    enrichment_build.add_argument("--output")
    enrichment_checkpoint_export = subcommands.add_parser(
        "enrichment-checkpoint-export",
        help="Export a verified cross-device enrichment checkpoint",
    )
    enrichment_checkpoint_export.add_argument("project_id", type=int)
    enrichment_checkpoint_export.add_argument("output")
    enrichment_checkpoint_import = subcommands.add_parser(
        "enrichment-checkpoint-import",
        help="Import a checkpoint into a new Scout database",
    )
    enrichment_checkpoint_import.add_argument("checkpoint")
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
    if args.command == "enrichment-checkpoint-import":
        value = import_scout_enrichment_checkpoint(args.checkpoint, args.database)
        print(json.dumps(value, ensure_ascii=False, indent=2))
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
    if args.command == "enrichment-prepare":
        value = prepare_scout_enrichment_project(store, args.source_html)
        print(json.dumps(value, ensure_ascii=False, indent=2))
        return 0
    if args.command == "enrichment-status":
        value = ensure_scout_enrichment_audits(store, args.project_id)
        print(json.dumps(enrichment_project_summary(value), ensure_ascii=False, indent=2))
        return 0
    if args.command == "enrichment-next":
        value = next_scout_enrichment_assignment(store, args.project_id)
        print(json.dumps({"assignment": value}, ensure_ascii=False, indent=2))
        return 0
    if args.command == "enrichment-submit":
        raw_text = Path(args.result_file).read_text(encoding="utf-8")
        value = save_scout_enrichment_result(store, args.project_id, raw_text)
        print(json.dumps(value, ensure_ascii=False, indent=2))
        return 0
    if args.command == "enrichment-audit-next":
        value = next_scout_enrichment_audit(
            store, args.project_id, researcher=args.researcher
        )
        print(json.dumps({"assignment": value}, ensure_ascii=False, indent=2))
        return 0
    if args.command == "enrichment-audit-submit":
        raw_text = Path(args.result_file).read_text(encoding="utf-8")
        value = save_scout_enrichment_audit_result(store, args.project_id, raw_text)
        print(json.dumps(value, ensure_ascii=False, indent=2))
        return 0
    if args.command == "enrichment-reconcile-next":
        value = next_scout_enrichment_reconciliation(store, args.project_id)
        print(json.dumps({"assignment": value}, ensure_ascii=False, indent=2))
        return 0
    if args.command == "enrichment-reconcile-submit":
        raw_text = Path(args.result_file).read_text(encoding="utf-8")
        value = save_scout_enrichment_reconciliation_result(
            store, args.project_id, raw_text
        )
        print(json.dumps(value, ensure_ascii=False, indent=2))
        return 0
    if args.command == "enrichment-build":
        project = store.get_scout_enrichment_project(args.project_id)
        if project is None:
            raise ValueError("Scout enrichment project not found")
        content = build_scout_enriched_html(store, args.project_id)
        output_path = Path(
            args.output or default_enriched_filename(project)
        ).expanduser().resolve()
        if output_path == Path(project["sourcePath"]).expanduser().resolve():
            raise ValueError("Enrichment output cannot overwrite the source artifact")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(content)
        print(json.dumps({
            **enrichment_project_summary(project),
            "outputPath": str(output_path), "byteCount": len(content),
        }, ensure_ascii=False, indent=2))
        return 0
    if args.command == "enrichment-checkpoint-export":
        value = export_scout_enrichment_checkpoint(
            store, args.project_id, args.output
        )
        print(json.dumps(value, ensure_ascii=False, indent=2))
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
    if args.command == "taxonomy-record-mesa-directions":
        value = record_mesa_category_directions(store, args.study_id)
        print(json.dumps(taxonomy_study_summary(value), ensure_ascii=False, indent=2))
        return 0
    if args.command == "taxonomy-propose-mesa-categories":
        value = save_mesa_category_redistribution_proposal(store, args.study_id)
        print(json.dumps(value, ensure_ascii=False, indent=2))
        return 0
    if args.command == "taxonomy-category-proposal":
        value = store.get_taxonomy_study(args.study_id)
        if value is None:
            raise ValueError("Taxonomy study not found")
        proposals = value.get("categoryRedistributionProposals") or []
        if not proposals:
            raise ValueError("The taxonomy study has no Category proposal")
        print(json.dumps(proposals[-1], ensure_ascii=False, indent=2))
        return 0
    if args.command == "taxonomy-approve-mesa-categories":
        value = approve_categories_and_prepare_type_review(store, args.study_id)
        print(json.dumps(value, ensure_ascii=False, indent=2))
        return 0
    if args.command == "taxonomy-type-packet":
        packets = store.list_taxonomy_type_review_packets(
            args.study_id, args.category_id
        )
        if not packets:
            raise ValueError("Type review packet not found")
        print(json.dumps(packets[0], ensure_ascii=False, indent=2))
        return 0
    if args.command in (
        "taxonomy-design-category-types",
        "taxonomy-design-new-category-types",
    ):
        value = save_category_type_designs(store, args.study_id)
        print(json.dumps(value, ensure_ascii=False, indent=2))
        return 0
    if args.command == "taxonomy-type-design":
        values = store.list_taxonomy_type_design_revisions(
            args.study_id, args.category_id
        )
        if not values:
            raise ValueError("Type design not found")
        print(json.dumps(values[-1], ensure_ascii=False, indent=2))
        return 0
    if args.command == "taxonomy-types-status":
        value = taxonomy_types_status(store, args.study_id)
        print(json.dumps(value, ensure_ascii=False, indent=2))
        return 0
    if args.command == "taxonomy-groups-prepare":
        value = build_group_review_packet(store, args.study_id)
        print(json.dumps(value, ensure_ascii=False, indent=2))
        return 0
    if args.command == "taxonomy-groups-infer":
        value = save_group_inference(store, args.study_id)
        print(json.dumps(value, ensure_ascii=False, indent=2))
        return 0
    if args.command == "taxonomy-groups-status":
        value = taxonomy_groups_status(store, args.study_id)
        print(json.dumps(value, ensure_ascii=False, indent=2))
        return 0
    if args.command == "taxonomy-groups-proposal":
        values = store.list_taxonomy_group_inference_revisions(args.study_id)
        if not values:
            raise ValueError("For-group proposal not found")
        print(json.dumps(values[-1], ensure_ascii=False, indent=2))
        return 0
    if args.command == "taxonomy-compile":
        value = compile_taxonomy_study(store, args.study_id)
        study = store.get_taxonomy_study(args.study_id)
        if study is None:
            raise ValueError("Taxonomy study not found")
        review_file = build_scout_review_file(
            store, int(study["curationJobId"])
        )
        output_path = Path(args.output or review_file.filename).expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(review_file.content)
        print(json.dumps({
            "studyId": value["studyId"],
            "status": "compiled",
            "seedSha256": value["seedSha256"],
            "categoryCount": value["categoryCount"],
            "resourceCount": value["resourceCount"],
            "forGroupCount": len(value["seed"]["forGroups"]),
            "filename": review_file.filename,
            "outputPath": str(output_path),
            "byteCount": len(review_file.content),
        }, ensure_ascii=False, indent=2))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
