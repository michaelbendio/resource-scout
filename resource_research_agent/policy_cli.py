"""Explicit operator commands for measured operating policies."""
import json
from pathlib import Path
from .operating_policy import OperatingPolicyWorkbench


def add_policy_commands(subcommands):
    group=subcommands.add_parser('policy',help='Evaluate research scheduling policies without changing defaults')
    actions=group.add_subparsers(dest='policy_action',required=True)
    actions.add_parser('manifest'); actions.add_parser('report')
    p=actions.add_parser('import-measurement');p.add_argument('source');p.add_argument('metadata')
    for action in ('baseline','capture'):
        p=actions.add_parser(action);p.add_argument('project_id',type=int);p.add_argument('category');p.add_argument('kind',choices=['discovery','recheck'])
        if action=='capture':p.add_argument('--reviewer',required=True)
    p=actions.add_parser('propose');p.add_argument('document')
    p=actions.add_parser('prepare');p.add_argument('proposal_id');p.add_argument('source');p.add_argument('design')
    p=actions.add_parser('packet');p.add_argument('trial_id');p.add_argument('arm',choices=['baseline','candidate']);p.add_argument('--context-id',required=True)
    p=actions.add_parser('submit');p.add_argument('packet_id');p.add_argument('response')
    p=actions.add_parser('evaluate');p.add_argument('trial_id');p.add_argument('assessment')
    p=actions.add_parser('approve');p.add_argument('evaluation_id');p.add_argument('--reviewer',required=True);p.add_argument('--rationale',required=True)
    p=actions.add_parser('activate');p.add_argument('approval_id');p.add_argument('--expected-manifest',required=True)
    p=actions.add_parser('rollback');p.add_argument('manifest_id');p.add_argument('--expected-manifest',required=True);p.add_argument('--reviewer',required=True);p.add_argument('--reason',required=True)


def run_policy_command(store,args):
    w=OperatingPolicyWorkbench(store);load=lambda path:json.loads(Path(path).read_text());a=args.policy_action
    if a=='manifest':return w.policy_manifest()
    if a=='report':return w.policy_report()
    if a=='import-measurement':return w.import_measurement(Path(args.source).read_bytes(),load(args.metadata))
    if a=='baseline':return w.baseline(args.project_id,args.category,args.kind)
    if a=='capture':return w.capture_execution(args.project_id,args.category,args.kind,args.reviewer)
    if a=='propose':return w.propose_policy(load(args.document))
    if a=='prepare':return w.prepare_comparison(args.proposal_id,Path(args.source).read_bytes(),load(args.design))
    if a=='packet':return w.policy_packet(args.trial_id,args.arm,args.context_id)
    if a=='submit':return w.submit_policy_result(args.packet_id,Path(args.response).read_text())
    if a=='evaluate':return w.evaluate_policy(args.trial_id,load(args.assessment))
    if a=='approve':return w.approve_policy(args.evaluation_id,args.reviewer,args.rationale)
    if a=='activate':return w.activate_policy(args.approval_id,args.expected_manifest)
    if a=='rollback':return w.rollback_policy(args.manifest_id,args.expected_manifest,args.reviewer,args.reason)
    raise ValueError('Unknown operating policy command')
