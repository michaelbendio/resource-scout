"""Explicit operator commands for isolated learning experiments."""
import json
from pathlib import Path
from .learning_workbench import LearningWorkbench


def add_learning_commands(subcommands):
    group = subcommands.add_parser('learning', help='Preserve evidence and evaluate inactive lesson proposals')
    actions = group.add_subparsers(dest='learning_action', required=True)
    actions.add_parser('collect'); actions.add_parser('inbox')
    p = actions.add_parser('register-package'); p.add_argument('package')
    p = actions.add_parser('import-editorial'); p.add_argument('package'); p.add_argument('ledger')
    p = actions.add_parser('import-comparison'); p.add_argument('comparison_id')
    p = actions.add_parser('propose'); p.add_argument('document')
    p = actions.add_parser('prepare'); p.add_argument('lesson_id'); p.add_argument('document')
    p = actions.add_parser('packet'); p.add_argument('trial_id'); p.add_argument('arm', choices=['baseline', 'candidate'])
    p.add_argument('--context-id', required=True); p.add_argument('--fresh', action='store_true', required=True)
    p = actions.add_parser('submit'); p.add_argument('trial_id'); p.add_argument('arm', choices=['baseline', 'candidate'])
    p.add_argument('response'); p.add_argument('receipt')
    p = actions.add_parser('assess'); p.add_argument('trial_id'); p.add_argument('document')
    p = actions.add_parser('report'); p.add_argument('trial_id')
    p = actions.add_parser('inspect'); p.add_argument('record_id')


def run_learning_command(store, args):
    work = LearningWorkbench(store)
    load = lambda path: json.loads(Path(path).read_text())
    action = args.learning_action
    if action == 'collect': return work.collect_comparisons()
    if action == 'inbox': return work.inbox()
    if action == 'register-package': return work.register_package(Path(args.package).read_bytes())
    if action == 'import-editorial': return work.import_editorial(Path(args.package).read_bytes(), Path(args.ledger).read_bytes())
    if action == 'import-comparison': return work.import_comparison(args.comparison_id)
    if action == 'propose': return work.propose(load(args.document))
    if action == 'prepare': return work.prepare_trial(args.lesson_id, load(args.document))
    if action == 'packet': return work.packet(args.trial_id, args.arm, args.context_id, fresh=args.fresh)
    if action == 'submit': return work.submit(args.trial_id, args.arm, Path(args.response).read_text(), load(args.receipt))
    if action == 'assess': return work.assess(args.trial_id, load(args.document))
    if action == 'report': return work.report(args.trial_id)
    if action == 'inspect': return work.inspect(args.record_id)
    raise ValueError('Unknown learning command')
