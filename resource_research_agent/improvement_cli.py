"""Operator commands for existing-resource research and review."""
import json
from pathlib import Path

from .scout_improvement import ImprovementWorkflow


def add_improvement_commands(subcommands):
    group = subcommands.add_parser('improve', help='Research and review writing updates to existing resources')
    actions = group.add_subparsers(dest='improvement_action', required=True)
    prepare = actions.add_parser('prepare')
    prepare.add_argument('package')
    prepare.add_argument('--office', required=True)
    prepare.add_argument('--resource-id', action='append', required=True)
    prepare.add_argument('--historical', action='store_true')
    for action in ('status', 'next', 'submit', 'connect', 'events', 'export'):
        command = actions.add_parser(action)
        command.add_argument('project_id', type=int)
        if action == 'next':
            command.add_argument('--researcher')
            command.add_argument('--resource-id')
        if action == 'submit':
            command.add_argument('stage')
            command.add_argument('result_file')
        if action == 'connect':
            command.add_argument('package')
            command.add_argument('--office', required=True)
        if action in ('connect', 'export'):
            command.add_argument('--revision', type=int, required=True)
        if action == 'export':
            command.add_argument('--output', required=True)


def run_improvement_command(store, args):
    workflow = ImprovementWorkflow(store)
    action = args.improvement_action
    if action == 'prepare':
        path = Path(args.package).expanduser()
        return workflow.prepare(path.read_bytes(), args.office, args.resource_id,
                                source_name=path.name, historical=args.historical)
    if action == 'status':
        return workflow.view(args.project_id)
    if action == 'next':
        return workflow.next_assignment(args.project_id, researcher=args.researcher, resource_id=args.resource_id)
    if action == 'submit':
        return workflow.submit(args.project_id, args.stage, json.loads(Path(args.result_file).read_text(encoding='utf-8')))
    if action == 'connect':
        path = Path(args.package).expanduser()
        return workflow.connect_latest(args.project_id, args.revision, path.read_bytes(), args.office, source_name=path.name)
    if action == 'events':
        return workflow.events(args.project_id)
    if action == 'export':
        output = Path(args.output).expanduser()
        if output.exists():
            raise ValueError('Choose a new output filename; an existing package will not be overwritten')
        exported = workflow.prepare_export(args.project_id, args.revision)
        payload = workflow.export_bytes(args.project_id, exported['exportId'])
        with output.open('xb') as destination:
            destination.write(payload)
        # Record success only after the file was closed and its bytes verified.
        if output.read_bytes() != payload:
            raise ValueError('Saved package verification failed; review remains available')
        current = workflow.view(args.project_id)
        workflow.acknowledge_export(args.project_id, current['revision'], exported['exportId'], exported['manifest']['packageSha256'])
        return {'output': str(output), **exported}
    raise ValueError('Unknown improvement command')
