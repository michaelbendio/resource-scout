"""Operator interface to the opt-in frontier discovery workflow."""
import json
from pathlib import Path
from .frontier_editor import FrontierEditorWorkflow


def add_editor_commands(subcommands):
    group=subcommands.add_parser('editor',help='Opt-in early selection, research and final frontier editing')
    actions=group.add_subparsers(dest='editor_action',required=True)
    p=actions.add_parser('prepare');p.add_argument('package');p.add_argument('configuration');p.add_argument('--office',required=True)
    p=actions.add_parser('prepare-final',help='Start final editing from an existing Scout draft package');p.add_argument('package');p.add_argument('configuration');p.add_argument('--office',required=True)
    p=actions.add_parser('prepare-leads');p.add_argument('package');p.add_argument('leads');p.add_argument('configuration');p.add_argument('--office',required=True);p.add_argument('--category',required=True)
    p=actions.add_parser('status');p.add_argument('project_id')
    p=actions.add_parser('packet');p.add_argument('project_id');p.add_argument('stage',choices=['early','final'])
    p=actions.add_parser('submit');p.add_argument('project_id');p.add_argument('stage',choices=['early','final']);p.add_argument('response');p.add_argument('receipt')
    p=actions.add_parser('start-research');p.add_argument('project_id');p.add_argument('--execution-config')
    p=actions.add_parser('finish-research');p.add_argument('project_id')
    p=actions.add_parser('export');p.add_argument('project_id');p.add_argument('destination');p.add_argument('--stage',choices=['early','final'],default='final')


def run_editor_command(store,args):
    flow=FrontierEditorWorkflow(store);load=lambda p:json.loads(Path(p).read_text())
    if args.editor_action=='prepare':return flow.prepare(Path(args.package).read_bytes(),args.office,load(args.configuration))
    if args.editor_action=='prepare-final':return flow.prepare_final(Path(args.package).read_bytes(),args.office,load(args.configuration))
    if args.editor_action=='prepare-leads':return flow.prepare_leads(Path(args.package).read_bytes(),Path(args.leads).read_text(),args.office,args.category,load(args.configuration))
    if args.editor_action=='status':return flow.status(args.project_id)
    if args.editor_action=='packet':return flow.packet(args.project_id,args.stage)
    if args.editor_action=='submit':return flow.submit(args.project_id,args.stage,Path(args.response).read_text(),load(args.receipt))
    if args.editor_action=='start-research':return flow.start_research(args.project_id,load(args.execution_config) if args.execution_config else None)
    if args.editor_action=='finish-research':return flow.finish_research(args.project_id)
    if args.editor_action=='export':
        exported=flow.export(args.project_id,args.stage);destination=Path(args.destination)
        destination.mkdir(parents=True,exist_ok=False)
        (destination/exported['filename']).write_bytes(exported['html'])
        (destination/'research-draft.zip').write_bytes(exported['package'])
        (destination/'manifest.json').write_text(json.dumps(exported['manifest'],indent=2)+'\n')
        return {'destination':str(destination.resolve()),**exported['manifest']}
    raise ValueError('Unknown editor action')
