"""Operator commands for evidence capture, without a new curator editor."""
import json
from pathlib import Path
from .learning_evidence import EvidenceLedger


def add_evidence_commands(subcommands):
    group = subcommands.add_parser('evidence', help='Capture curator/package evidence without inferring lessons')
    actions = group.add_subparsers(dest='evidence_action', required=True)
    p = actions.add_parser('import'); p.add_argument('package'); p.add_argument('--collection', required=True)
    p.add_argument('--office', required=True); p.add_argument('--scope', choices=['full','partial','unknown'], required=True)
    p.add_argument('--historical', action='store_true')
    p = actions.add_parser('capture-project'); p.add_argument('project_id', type=int); p.add_argument('--collection', required=True)
    p = actions.add_parser('manual-proposal'); p.add_argument('proposal_file')
    p = actions.add_parser('compare'); p.add_argument('before_id'); p.add_argument('after_id')
    p.add_argument('--reviewer', required=True); p.add_argument('--lineage-note', required=True)
    p.add_argument('--capture', action='append', default=[]); p.add_argument('--identity-links')
    p = actions.add_parser('attest'); p.add_argument('verification_file')
    p = actions.add_parser('report'); p.add_argument('comparison_id')


def run_evidence_command(store, args):
    ledger = EvidenceLedger(store)
    load = lambda path: json.loads(Path(path).read_text())
    if args.evidence_action == 'import':
        return ledger.import_package(args.collection, args.office, Path(args.package).read_bytes(),
                                     scope=args.scope, historical=args.historical)
    if args.evidence_action == 'capture-project': return ledger.capture_project(args.collection, args.project_id)
    if args.evidence_action == 'manual-proposal': return ledger.record_manual_proposal(**load(args.proposal_file))
    if args.evidence_action == 'compare': return ledger.compare(args.before_id, args.after_id, reviewer=args.reviewer,
        lineage_note=args.lineage_note, captures=args.capture, identity_links=load(args.identity_links) if args.identity_links else [])
    if args.evidence_action == 'attest': return ledger.attest(**load(args.verification_file))
    if args.evidence_action == 'report': return ledger.report(args.comparison_id)
