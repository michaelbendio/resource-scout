#!/usr/bin/env python3
"""Build a working Scout HTML draft from completed, uncurated maintenance research."""
import argparse
import hashlib
import json
from pathlib import Path

from resource_research_agent.improvement_packages import utcnow
from resource_research_agent.maintenance_review import build_maintenance_review_file
from resource_research_agent.scout_maintenance import MaintenanceWorkflow
from resource_research_agent.storage import ResearchStore


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database',type=Path,required=True)
    parser.add_argument('--project',type=int,required=True)
    parser.add_argument('--location',required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    flow=MaintenanceWorkflow(ResearchStore(args.database));view=flow.view(args.project)
    args.output.mkdir(parents=True,exist_ok=True)
    manifest_path=args.output/'review-build.json'
    identity={'projectId':args.project,'revision':view['revision'],'baseSha256':view['baseSha256'],'location':args.location}
    if manifest_path.exists():
        manifest=json.loads(manifest_path.read_text())
        if any(manifest[key]!=value for key,value in identity.items()):
            raise ValueError('This delivery directory belongs to different research; choose a new output directory to preserve curator work')
    else:
        manifest={**identity,'createdAt':utcnow()}
    result=build_maintenance_review_file(flow,args.project,view['revision'],location_name=args.location,created_at=manifest['createdAt'])
    target=args.output/result.filename
    # This is a generated draft; real user answers live in artifact-scoped browser
    # storage and exported packages. An explicit new directory protects versions.
    target.write_bytes(result.content)
    manifest.update(filename=result.filename,sha256=hashlib.sha256(result.content).hexdigest(),
                    byteCount=len(result.content),coverage=view['coverage'],resources=len(view['items']),
                    humanApprovalsCreated=0,sourceDatabase=str(args.database.resolve()))
    manifest_path.write_text(json.dumps(manifest,indent=2)+'\n')


if __name__=='__main__':main()
