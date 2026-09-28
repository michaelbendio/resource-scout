"""Isolated Scout evaluation CLI. No command dispatches paid work by default."""
import argparse
import json
from pathlib import Path
from .protocol import init_experiment, seal_protocol, verify_protocol, read, EvaluationError


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    initialize = commands.add_parser('init', help='Freeze a read-only historical baseline and original inputs')
    initialize.add_argument('--config', required=True, type=Path)
    initialize.add_argument('--out', required=True, type=Path)
    for name in ['seal','status']:
        sub = commands.add_parser(name); sub.add_argument('--experiment', required=True, type=Path)
    run = commands.add_parser('run', help='Preview or explicitly execute isolated Housing passes')
    run.add_argument('--experiment',required=True,type=Path)
    run.add_argument('--condition',required=True,choices=['existing-policy'])
    run.add_argument('--category',required=True)
    mode=run.add_mutually_exclusive_group()
    mode.add_argument('--dry-run',action='store_true')
    mode.add_argument('--execute',action='store_true')
    for name in ['audit-packet','record-audit','report']:
        sub=commands.add_parser(name,help='Offline reviewer evidence; never dispatches provider requests')
        sub.add_argument('--experiment',required=True,type=Path)
        if name!='report':sub.add_argument('--category',default='housing')
        if name=='record-audit':sub.add_argument('--judgment',required=True,type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == 'init':
            result = {'experiment':str(init_experiment(read(args.config),args.out)), 'sealed':False}
        elif args.command == 'run':
            from .research import run_category
            result = run_category(args.experiment,args.condition,args.category,execute=args.execute)
            if result.get('dryRun'):
                result = {k:v for k,v in result.items() if k!='nextAssignment'}
                result['assignmentFile'] = str(args.experiment/'results'/args.condition/args.category/'dry-run.json')
        elif args.command == 'seal':
            result = seal_protocol(args.experiment)
        elif args.command == 'audit-packet':
            from .audit import build_audit_packet
            packet=build_audit_packet(args.experiment,args.category)
            result=dict(packetFile=str(args.experiment/'audit'/f'{args.category}-packet.json'),
                leadCounts={label:len(leads) for label,leads in packet['collections'].items()})
        elif args.command == 'record-audit':
            from .audit import record_stage_decision
            result=record_stage_decision(args.experiment,args.category,read(args.judgment))
        elif args.command == 'report':
            from .cost_report import write_actuals
            result=write_actuals(args.experiment)['usage']
        else:
            m = verify_protocol(args.experiment)
            result = dict(experimentId=m['experimentId'], sealed=True, evaluationOnly=True, importable=False)
            if (args.experiment/'ledger.sqlite3').exists():
                from .ledger import Ledger
                result['usage'] = Ledger(args.experiment).summarize_usage()
        print(json.dumps(result, sort_keys=True))
    except (EvaluationError, OSError, KeyError) as error:
        parser.exit(2, f'Evaluation held: {error}\n')


if __name__ == '__main__':
    main()
