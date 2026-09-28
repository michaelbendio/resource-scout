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
    args = parser.parse_args(argv)
    try:
        if args.command == 'init':
            result = {'experiment':str(init_experiment(read(args.config),args.out)), 'sealed':False}
        elif args.command == 'seal':
            result = seal_protocol(args.experiment)
        else:
            m = verify_protocol(args.experiment)
            result = dict(experimentId=m['experimentId'], sealed=True, evaluationOnly=True, importable=False)
        print(json.dumps(result, sort_keys=True))
    except (EvaluationError, OSError, KeyError) as error:
        parser.exit(2, f'Evaluation held: {error}\n')


if __name__ == '__main__':
    main()
