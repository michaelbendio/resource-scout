"""Replay the existing focused/gap policy only in an owned scratch store."""
from __future__ import annotations
from contextlib import contextmanager
import copy
import fcntl
import json
from pathlib import Path
import time
from .protocol import (EvaluationError, verify_protocol, read, write_once, checkpoint, file_hash,
                       digest, identifier, inside, now)
from .baseline import readonly
from .ledger import Ledger, BudgetHold
from .deepseek import LiveTransport, run_assignment
from .providers import make_transport, provider_label
from ..storage import ResearchStore
from ..importer import ResourcePackageImporter
from ..focused_research import (prepare_focused_research_job,next_focused_research_assignment,
    save_focused_research_result,prepare_focused_gap_pass,close_focused_research_job,build_candidate_manifest)
from ..deepseek_challenger_runner import validate_result


@contextmanager
def evaluation_lock(root):
    with inside(root,'evaluation.lock').open('a') as handle:
        try:fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise EvaluationError('Another evaluation invocation owns this experiment') from None
        try:yield
        finally:fcntl.flock(handle,fcntl.LOCK_UN)


def initialize_scratch(root, condition):
    root=Path(root).resolve();manifest=verify_protocol(root);identifier(condition)
    if condition!=manifest['condition']:raise EvaluationError('Condition is not sealed')
    config=read(root/'config.json');path=inside(root,'scratch/'+condition+'.sqlite3')
    for forbidden in [Path(config['baseline']['sourceDb']).resolve(),root/'reference/source.sqlite3']:
        if path==forbidden or (path.exists() and forbidden.exists() and path.samefile(forbidden)):
            raise EvaluationError('Scratch database aliases protected source evidence')
    ownership_path=inside(root,'scratch/'+condition+'-ownership.json')
    ownership=dict(protocolSha256=file_hash(root/'manifest.json'),originalPackageSha256=file_hash(root/'inputs/office-package.zip'))
    if path.exists() and not ownership_path.exists():raise EvaluationError('Existing database is not owned by this experiment')
    write_once(ownership_path,ownership)
    store=ResearchStore(path)
    # Recover an import committed just before a crash without importing a second copy.
    with readonly(path) as db:
        rows=db.execute('SELECT id,source_sha256 FROM imports').fetchall()
    if len(rows)>1 or any(r[1]!=ownership['originalPackageSha256'] for r in rows):
        raise EvaluationError('Scratch store contains unexpected imports')
    if rows:
        import_id=rows[0][0]
    else:
        imported=ResourcePackageImporter(config['categories'][0]).read(root/'inputs/office-package.zip')
        imported.source_name=read(root/'baseline.json')['sourceName']
        reconstruction=read(root/'baseline.json').get('inputReconstruction')
        if reconstruction and imported.content_sha256!=reconstruction['canonicalContentSha256']:
            raise EvaluationError('Repacked import changes the original resource content')
        import_id=store.save_import(imported)
    write_once(root/'scratch'/f'{condition}-ids.json',dict(originalImportId=config['baseline']['importId'],scratchImportId=import_id,
        categoryIds={c:c for c in config['categories']},note='Resource source IDs come unchanged from the exact original package. SQLite run/pass/lead IDs are scratch-local.'))
    return store,import_id


def policy_semantics(plan):
    # Only documented bookkeeping/provider identity differences are excluded.
    return {k:v for k,v in plan.items() if k not in ['importId','researcherRoster']}


def stage_eligibility(root,category,execute):
    if not execute or category=='housing':return
    raise EvaluationError('M0/M1 permits Housing only; expansion requires the later audited advancement ticket')


def _run_category(root,condition,category,*,execute=False,transport=None,fetcher=None):
    root=Path(root).resolve();manifest=verify_protocol(root);identifier(category)
    if category not in manifest['categories']:raise EvaluationError('Category outside sealed scope')
    stage_eligibility(root,category,execute)
    with evaluation_lock(root):
        config=read(root/'config.json')
        store,import_id=initialize_scratch(root,condition)
        historical=read(root/'reference/baseline.json')['categories'][category]['job']
        original_plan=json.loads(historical['plan_json'])
        roster=copy.deepcopy(original_plan.get('researcherRoster'))
        if roster:
            # Label the actual provider while leaving source policy untouched.
            for worker in roster.get('researchers',[]):
                if worker.get('role')=='primary':worker['name']=provider_label(config['provider']['endpoint'])
        else:roster={'researchers':[{'name':provider_label(config['provider']['endpoint']),'role':'primary'}]}
        job=prepare_focused_research_job(store,import_id,category_id=category,
            experiment_mode=config['baseline']['experimentMode'],redact_recovery_targets=config['baseline']['redactRecoveryTargets'],
            researcher_roster=roster)
        original_known_hash=historical.get('baseline_manifest_sha256')
        if read(root/'baseline.json').get('inputReconstruction') and not original_known_hash:
            raise EvaluationError('Reconstructed inputs need the original known-resource manifest hash')
        if original_known_hash and job['baselineManifestSha256']!=original_known_hash:
            raise EvaluationError('Scratch known resources differ from the original primary assignment baseline')
        if policy_semantics(job['plan'])!=policy_semantics(original_plan):
            raise EvaluationError('Current focused policy differs from the frozen historical plan; do not run a confounded comparison')
        directory=inside(root,'results/'+condition+'/'+category)
        write_once(directory/'scratch-job-map.json',dict(originalJobId=historical['id'],scratchJobId=job['id'],
            originalRunId=historical['run_id'],scratchRunId=job['runId'],policyComparison='equal except local import ID and provider roster label'))
        if not execute:
            assignment=next_focused_research_assignment(store,job['id'])
            report=dict(evaluationOnly=True,importable=False,dryRun=True,providerRequests=0,
                category=category,focusCount=len(original_plan['focuses']),gapPolicy='one existing gap pass after fixed passes',
                nextAssignment=assignment,notice='Later assignments depend on this condition’s own findings; they are not fabricated during dry-run.')
            checkpoint(directory/'dry-run.json',report)
            return report
        ledger=Ledger(root,simulation=transport is not None and getattr(transport,'is_live',True) is False)
        ledger.authorization()  # No paid call or result import before the explicit gate.
        if transport is None:transport=make_transport(config['provider']['endpoint'])
        while True:
            job=store.get_focused_research_job(job['id'])
            if job['status']=='completed':break
            assignment=next_focused_research_assignment(store,job['id'])
            if assignment is None:
                if not any(p['passKind']=='gap' for p in job['passes']):
                    prepare_focused_gap_pass(store,job['id']);continue
                close_focused_research_job(store,job['id']);break
            packet=dict(assignmentId=category+'-'+assignment['focusKey'],condition=condition,category=category,
                stage=category+'-research',passKey=assignment['focusKey'],task=assignment['assignment'],requiresLiveSearch=True)
            options={'fetcher':fetcher} if fetcher else {}
            result=run_assignment(packet,ledger,transport,validate_result,**options)
            write_once(directory/(assignment['focusKey']+'-original.json'),result)
            # Only scratch IDs/stores are passed to the existing importer.
            save_focused_research_result(store,job['id'],assignment['focusKey'],json.dumps(result['result'],ensure_ascii=False))
            checkpoint(directory/'progress.json',dict(at=now(),lastCompletedPass=assignment['focusKey'],usage=ledger.summarize_usage()))
        job=store.get_focused_research_job(job['id'])
        summary=dict(evaluationOnly=True,importable=False,status='completed-research-awaiting-source-audit',condition=condition,
            category=category,passes=[dict(key=p['focusKey'],kind=p['passKind'],leadCount=p['leadCount']) for p in job['passes']],
            candidates=build_candidate_manifest(store,job['runId']),usage=ledger.summarize_usage(),
            qualityJudgment=None,notice='Completed scratch research is not an approved office collection or an advancement decision.')
        write_once(directory/'summary.json',summary)
        held=directory/'held-outcome.json'
        if held.exists():
            record=read(held)
            write_once(directory/'resolved-holds'/(digest(record)+'.json'),record)
            held.unlink()
        return summary


def run_category(root,condition,category,*,execute=False,transport=None,fetcher=None):
    identifier(condition);identifier(category)
    try:
        return _run_category(root,condition,category,execute=execute,transport=transport,fetcher=fetcher)
    except (EvaluationError, ValueError) as error:
        if execute:
            directory=inside(root,'results/'+condition+'/'+category)
            checkpoint(directory/'held-outcome.json',dict(evaluationOnly=True,importable=False,
                status='held',at=now(),reason=str(error),errorType=type(error).__name__,
                notice='This is not a completed comparison or a quality judgment; partial evidence and charges remain retained.'))
        raise
