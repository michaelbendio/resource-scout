#!/usr/bin/env python3
"""Create the authorized isolated Mesa re-curation input; do not launch workers."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import sqlite3
import sys
from datetime import datetime, timezone

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from resource_research_agent.scout_curation import prepare_scout_curation_job
from resource_research_agent.scout_curation_runner import write_evidence_once
from resource_research_agent.storage import ResearchStore


def main():
    root=Path(__file__).resolve().parents[1]
    run=root/'data/mesa-prepared-full-20260926-source-checks'
    run.mkdir(parents=True,exist_ok=True)
    source=root/'data/mesa-review-20260924'
    database=run/'research.sqlite3'
    original=source/'original-mesa.sqlite3'
    files={name:source/name for name in ('after-seed.json','browser-state-reconciled-v3.json','final-decisions.json')}
    files['original-mesa.sqlite3']=original
    office_file=Path.home()/'resource-assistant/mesa.html'
    published_root=root/'deliveries/mesa-four-categories-20260925'
    audit_source=root/'docs/prepared/mesa-full-recuration-source-audit-20260926.md'
    files.update({'office-mesa.html':office_file,'source-audit.md':audit_source,
        'prior-prepared-resources.json':published_root/'prepared-resources.json',
        'prior-identity-migration.json':published_root/'identity-migration.json',
        'prior-reviewed-merges.json':root/'docs/prepared/mesa-four-category-review.json'})
    prior_attempt=root/'data/mesa-prepared-full-20260926-all-research/curation'
    earlier_drafts=[]
    for worker in sorted(prior_attempt.rglob('worker.json')):
        result=worker.with_name('result.json')
        if not result.exists():
            raise RuntimeError('Let the earlier active worker finish before sealing its supporting draft evidence')
        files['earlier-attempt-'+worker.parent.name+'.json']=result
        earlier_drafts.extend(json.loads(result.read_text())['resources'])
    hashes={name:hashlib.sha256(path.read_bytes()).hexdigest() for name,path in files.items()}
    if not database.exists():
        with sqlite3.connect(original.as_uri()+'?mode=ro',uri=True) as src, sqlite3.connect(database) as dest:
            src.backup(dest)
    seed=json.loads(files['after-seed.json'].read_text())
    state=json.loads(files['browser-state-reconciled-v3.json'].read_text())
    records={r['id']:dict(r) for r in seed['resources']}
    for overlay in state['resourceOverrides']:records[overlay['id']].update(overlay)
    match=re.search(r'<script[^>]+id=["\x27]seed-data["\x27][^>]*>(.*?)</script>',office_file.read_text(),re.S)
    categories=[{k:c[k] for k in ('id','label')} for c in json.loads(match[1])['categories']]
    published=json.loads((published_root/'prepared-resources.json').read_text())
    oldmap=json.loads((published_root/'identity-migration.json').read_text())
    canonical={a['legacyId']:a['resourceId'] for a in oldmap['aliases']}
    current={r['id']:r for r in published['resources']}
    choices=json.loads((root/'docs/prepared/mesa-four-category-review.json').read_text())
    prefer={rid:rid for rid in records}
    for group in choices['merges']:
        primary,=[rid for rid in records if rid.startswith(group['primary'])]
        for prefix in group['members']:
            member,=[rid for rid in records if rid.startswith(prefix)]
            prefer[member]=primary
    historical=[]
    for rid,record in records.items():
        refs=record.pop('candidateIds')
        updated=current.get(canonical.get(rid))
        if updated:
            for key in ('description','informationText','phone','address','website','hours','email'):
                record[key]=updated[key]
        historical.append(dict(legacyResourceId=rid,preferredDraftReference=prefer[rid],
            canonicalIdentityForFinalReview=canonical.get(rid),historicalCandidateIds=refs,
            officeHidden=rid in state['deletedResourceIds'],
            previousPreparationState=updated.get('state') if updated else None,
            previousResolutionReason=updated.get('resolutionReason','') if updated else '',
            record=record))
    by_reference={r['legacyResourceId']:r for r in historical}
    for draft in earlier_drafts:
        rid=draft['id']
        if rid not in by_reference:
            item=dict(legacyResourceId=rid,preferredDraftReference=rid,
                historicalCandidateIds=draft['candidateIds'],officeHidden=False,
                evidenceStatus='unreviewed-preparation-draft',record=draft)
            historical.append(item)
            by_reference[rid]=item
        by_reference[rid].setdefault('earlierPreparationDrafts',[]).append(draft)
        by_reference[rid]['historicalCandidateIds']=sorted(set(map(str,
            by_reference[rid]['historicalCandidateIds']+draft['candidateIds'])))
    context=dict(schemaVersion=1,artifactType='scout-preparation-context',officeSlug='mesa',
        sourceHashes=hashes,categories=categories,forGroups=seed['forGroups'],
        forGroupDefinitions=seed['forGroupDefinitions'],resources=historical,
        instructions='Re-curate all saved research candidates under the new policy. Earlier September 24 review and September 25 prepared facts are supporting evidence, not pre-approved output. Read matching records, retain supported corrections and investigate material conflicts. Map services to the supplied current office category IDs, not the historical taxonomy in records. Reuse preferredDraftReference only for the same program; canonicalIdentityForFinalReview is not an allowed worker output ID. Do not copy unrelated historicalCandidateIds into current dispositions. Human-hidden choices and unresolved human identity/name conflicts remain for final review; AI preparation must not approve or resurrect them. Use current source checks for stale or uncertain claims. Keep useful reserve options, including niche programs. Record new Type/group concepts with evidence for whole-collection review.')
    context_path=run/'reviewed-context.json'
    context['instructions'] += ' EarlierPreparationDrafts and records marked unreviewed-preparation-draft are saved work from the initial attempt, which did too few live source checks. Reuse supported drafting work, not its state judgments or unverified claims; perform the targeted official-source checks required by this sealed assignment. Never treat these drafts as reviewed or office-approved.'
    write_evidence_once(context_path,context)
    audit_path=run/'source-audit.md'
    audit_text=audit_source.read_text()
    from resource_research_agent.scout_curation_runner import write_once
    write_once(audit_path,audit_text)
    store=ResearchStore(database)
    job=prepare_scout_curation_job(store,4,prepared=True,reviewed_context=context,all_research_runs=True)
    connected=set()
    for category in job['categories']:
        assignment=category['assignment']
        connected.update(r['legacyResourceId'] for r in assignment['reviewedContext']['resources'])
    if connected != {r['legacyResourceId'] for r in historical}:
        raise ValueError('The new assignments must retain evidence links to every reviewed resource')
    command=[sys.executable,'-m','resource_research_agent.scout_curation_runner',
        '--database',str(database),'--import-id','4','--output',str(run/'curation'),
        '--prepared','--all-research-runs','--reviewed-context',str(context_path),'--source-audit',str(run/'source-audit.md'),
        '--codex-binary',shutil.which('codex'),'--model','gpt-5.5','--effort','high',
        '--batch-candidates','30','--batch-chars','60000','--compact-prior-index','--max-categories','21']
    manifest=dict(schemaVersion=1,kind='mesa-prepared-recuration',database=str(database),importId=4,
        jobId=job['id'],command=command,cwd=str(root),sourceHashes=hashes,
        workerEffort='high',requestedReviewEffort='xhigh',reviewOwner='current supervising Codex session; one reviewer',
        authorization='Michael: have Scout re-curate the Mesa research results; when finished review them and create the complete prepared-resources. This supersedes the four-category-only limit for Mesa, not Cedar City\'s hold.',
        sourceCandidateCount=sum(c['candidateCount'] for c in job['categories']),
        preservedReviewedResources=len(records),humanHiddenCount=len(state['deletedResourceIds']))
    write_evidence_once(run/'launch.json',manifest)
    write_evidence_once(run/'input-manifest.json',dict(sourceHashes=hashes,jobId=job['id'],sourceStudyId=20,sourceCurationJobId=4,
        authoritativeCategories=categories,preparedCategoryCount=len(job['categories']),
        coverageNote='21 researched service categories; Miscellaneous is the office catch-all, to assess explicitly during complete-office review.'))
    print(json.dumps(dict(jobId=job['id'],categories=len(job['categories']),candidates=manifest['sourceCandidateCount'],
                         historicalResources=len(records),workerEffort='high',reviewEffort='xhigh')))


if __name__=='__main__':main()
