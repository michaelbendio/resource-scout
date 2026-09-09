#!/usr/bin/env python3
"""Build an explicit, uncurated research checkpoint from exact saved revisions."""
import argparse
import hashlib
import json
from pathlib import Path

from resource_research_agent.improvement_packages import utcnow
from resource_research_agent.meeting_edition import (
    ReadOnlyMaintenanceWorkflow, build_meeting_edition, render_meeting_overview,
)


def project_snapshot(value):
    try:
        pid,revision=map(int,value.split(':'))
        if pid < 1 or revision < 0:raise ValueError()
        return pid,revision
    except ValueError as error:
        raise argparse.ArgumentTypeError('Use PROJECT_ID:REVISION') from error


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database',type=Path,required=True)
    parser.add_argument('--project',type=project_snapshot,action='append',required=True)
    parser.add_argument('--location',required=True)
    parser.add_argument('--created-at',default=None)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists() and any(args.output.iterdir()):
        raise ValueError('Choose an empty delivery directory to preserve earlier files and curator work')
    flow=ReadOnlyMaintenanceWorkflow(args.database)
    edition=build_meeting_edition(flow,args.project,location_name=args.location,created_at=args.created_at or utcnow())
    with flow.store.connect() as connection:
        baseline=flow._package(connection,edition.manifest['sourcePackageSha256'])['data']
    overview=render_meeting_overview(edition,baseline).encode('utf-8')
    stem=Path(edition.review.filename).stem
    artifacts={edition.review.filename:edition.review.content,
               stem+'-review.html':overview,stem+'-research-draft.zip':edition.package}
    manifest={**edition.manifest,'sourceDatabase':str(args.database.resolve()),
              'artifacts':{name:{'sha256':hashlib.sha256(payload).hexdigest(),'bytes':len(payload)}
                           for name,payload in artifacts.items()}}
    args.output.mkdir(parents=True,exist_ok=True)
    for name,payload in artifacts.items():(args.output/name).write_bytes(payload)
    (args.output/'meeting-edition.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n')


if __name__=='__main__':main()
