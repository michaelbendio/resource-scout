"""Resumable maintenance operator commands."""
import json
from pathlib import Path
from .scout_maintenance import MaintenanceWorkflow


def add_maintenance_commands(subcommands):
    group = subcommands.add_parser('maintain', help='Recheck resources and search for additions')
    actions = group.add_subparsers(dest='maintenance_action', required=True)
    p = actions.add_parser('prepare'); p.add_argument('package'); p.add_argument('--office', required=True); p.add_argument('--run-name', required=True)
    p.add_argument('--resource-id', action='append', default=[]); p.add_argument('--category-id', action='append', default=[]); p.add_argument('--historical', action='store_true')
    p.add_argument('--blind-comparison', action='store_true', help='Require a batch freeze and independent Claude research before final reconciliation')
    p.add_argument('--execution-config', help='Opt into the versioned Astra-led protocol using a JSON configuration')
    p.add_argument('--supersedes', type=int, help='Create a separate execution with an explicit protocol/scope-change record')
    p.add_argument('--operator', default=''); p.add_argument('--change-reason', default='')
    p = actions.add_parser('provider', help='Record an actual outside-provider availability check')
    p.add_argument('project_id', type=int); p.add_argument('--revision', type=int, required=True)
    p.add_argument('--researcher', required=True); p.add_argument('--status', choices=['available', 'unavailable'], required=True)
    p.add_argument('--operator', required=True); p.add_argument('--reason', required=True); p.add_argument('--context-id', default='')
    p = actions.add_parser('challenge', help='Request a targeted check before final reconciliation is sealed')
    p.add_argument('project_id', type=int); p.add_argument('--revision', type=int, required=True)
    p.add_argument('--task-id', required=True); p.add_argument('--researcher', required=True)
    p.add_argument('--operator', required=True); p.add_argument('--reason', required=True)
    p = actions.add_parser('stop-blind', help='Record an explicit decision to stop further blind research in an existing run')
    p.add_argument('project_id', type=int); p.add_argument('--revision', type=int, required=True)
    p.add_argument('--researcher', required=True); p.add_argument('--operator', required=True); p.add_argument('--reason', required=True)
    for name in ('status', 'events', 'next', 'submit', 'connect', 'review', 'export'):
        p = actions.add_parser(name); p.add_argument('project_id', type=int)
        if name == 'next': p.add_argument('--researcher'); p.add_argument('--task-id')
        if name == 'submit': p.add_argument('stage'); p.add_argument('result_file')
        if name in ('connect', 'review', 'export'): p.add_argument('--revision', type=int, required=True)
        if name == 'connect': p.add_argument('package'); p.add_argument('--office', required=True)
        if name == 'review': p.add_argument('review_file')
        if name == 'export':
            p.add_argument('output')
            p.add_argument('--questions-only', action='store_true', help='Hand off questions on existing resources without accepting service changes')


def run_maintenance_command(store, args):
    flow = MaintenanceWorkflow(store); action = args.maintenance_action
    if action == 'prepare': return flow.prepare(Path(args.package).read_bytes(), args.office, args.resource_id, args.category_id, run_name=args.run_name, historical=args.historical, blind_comparison=getattr(args, 'blind_comparison', False), execution_config=json.loads(Path(args.execution_config).read_text()) if getattr(args, 'execution_config', None) else None, supersedes=getattr(args, 'supersedes', None), operator=getattr(args, 'operator', ''), change_reason=getattr(args, 'change_reason', ''))
    if action == 'provider': return flow.record_provider(args.project_id, args.revision, args.researcher, args.status, args.operator, args.reason, args.context_id)
    if action == 'challenge': return flow.request_challenge(args.project_id, args.revision, args.task_id, args.researcher, args.operator, args.reason)
    if action == 'status': return flow.view(args.project_id)
    if action == 'events': return flow.events(args.project_id)
    if action == 'stop-blind': return flow.stop_blind_research(args.project_id, args.revision, args.researcher, args.operator, args.reason)
    if action == 'next': return flow.next_assignment(args.project_id, researcher=args.researcher, task_id=args.task_id)
    if action == 'submit': return flow.submit(args.project_id, args.stage, json.loads(Path(args.result_file).read_text()))
    if action == 'connect': return flow.connect_latest(args.project_id, args.revision, Path(args.package).read_bytes(), args.office)
    if action == 'review':
        b = json.loads(Path(args.review_file).read_text())
        return flow.review(args.project_id, args.revision, b['taskId'], b['itemId'], b['decision'], b.get('choices', {}), b['reviewer'], b['note'], identity_decision=b.get('identityDecision', ''), finding_notes=b.get('findingNotes', {}))
    if action == 'export':
        path = Path(args.output)
        if path.exists(): raise ValueError('Choose a new export filename')
        export = (flow.prepare_question_export if getattr(args, 'questions_only', False) else flow.prepare_export)(args.project_id, args.revision)
        payload = flow.export_bytes(args.project_id, export['exportId'])
        with path.open('xb') as target: target.write(payload)
        if path.read_bytes() != payload: raise ValueError('Saved file verification failed')
        flow.acknowledge_export(args.project_id, flow.view(args.project_id)['revision'], export['exportId'], export['manifest']['packageSha256'])
        return {'output': str(path), **export}
