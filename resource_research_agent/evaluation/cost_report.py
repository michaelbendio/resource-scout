"""Observed evaluation usage with explicit unknowns; no account-wide attribution."""
import csv
import io
import json
from pathlib import Path
from .ledger import Ledger
from .protocol import read, write_once, write_bytes_once, verify_protocol


def write_actuals(root):
    root=Path(root);verify_protocol(root);ledger=Ledger(root)
    usage=ledger.summarize_usage()
    with ledger.connect() as db:
        rows=[dict(r) for r in db.execute('SELECT id,category,stage,pass_key,state,requested_model,returned_model,elapsed,reservation,calculated,billed,usage_json FROM attempts ORDER BY created_at,id')]
    report=dict(usage=usage,attempts=rows,
        limitations=['Calculated charges are not provider-confirmed bills.',
                    'Unknown usage or billing components prevent a complete dollar total.',
                    'Preparation, review and cross-category reconciliation have not been measured in M1.',
                    'Account-wide balance changes are not attributed to this experiment.'])
    write_once(root/'reports/actuals.json',report)
    stream=io.StringIO();writer=csv.DictWriter(stream,fieldnames=list(rows[0]) if rows else ['id'])
    writer.writeheader();writer.writerows(rows)
    write_bytes_once(root/'reports/actuals.csv',stream.getvalue().encode())
    text='# Initial complete-run projection\n\n'
    text+=f"Housing observed calls: {usage['attempts']}; active processing: {usage['activeSeconds']/60:.2f} minutes.\n\n"
    text+='| Work | Evidence at this stage |\n| --- | --- |\n'
    text+='| Housing research | Measured attempt counts and elapsed time in actuals.json; complete cost may remain unknown |\n'
    text+='| Other-category research | Unmeasured; Housing alone does not establish representative complexity |\n'
    text+='| Preparation under existing full-reserve scope | Unmeasured |\n'
    text+='| Resource review and cross-category reconciliation | Unmeasured |\n'
    text+='| Narrower preparation policy | Separate future experiment, not a saving attributed to this model comparison |\n\n'
    text+='No complete measured dollar total or adoption recommendation follows from this table.\n'
    write_bytes_once(root/'reports/initial-projection.md',text.encode())
    return report
