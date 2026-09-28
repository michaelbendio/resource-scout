"""Explicitly authorized import handoff AFTER the independent Housing trial.

The evaluation evidence stays immutable. Production identity/taxonomy context is
introduced only here, after the fresh DeepSeek review has been frozen.
"""
from copy import deepcopy
import fcntl
import html
import json
from pathlib import Path

from .protocol import EvaluationError, read, write_once, write_bytes_once, file_hash, digest, now
from .deepseek import run_assignment, LiveTransport
from .ledger import Ledger
from .preparation import collection_contract, validate_schema
from ..scout_curation_runner import response_schema
from ..preparation_contract import POLICY_VERSION, normalize_preparation_fields, information_sections
from ..prepared_resources import source_catalog, source_id, validate_artifact
from ..prepared_export import finalize, review_fingerprint, export_bundle
from ..resource_identity import load_registry, fingerprint


SHAPE = {
    'identities':[{'canonicalId':'reviewed canonical ID','match':None,
                   'reason':'program-specific identity evidence; null match only for a distinct new program',
                   'possibleDuplicateExistingIds':[]}],
    'mergedResources':[],
    'mergeFindings':[{'canonicalId':'each merged identity','before':'original differences or duplicate facts',
                       'after':'how supported facts were preserved or conflicts resolved','sourceUrls':[]}],
    'typeMatches':[{'proposedId':'trial type ID','existingId':None,'reason':'same meaning or why a new meaning is needed'}],
    'groupMatches':[{'proposedId':'trial group ID','existingId':None,'reason':'same evidenced population meaning or why new'}],
    'preservationJudgment':'Explain supported fact preservation, program boundaries, unresolved conflicts and no human approval.',
}


def validate_resolution(resolution, report, registry, previous):
    collection_contract(report['collection'],report['resources'])
    groups = report['collection']['identities']
    canonical = {g['canonicalId'] for g in groups}
    decisions = resolution['identities']
    if len(decisions)!=len(canonical) or {d['canonicalId'] for d in decisions}!=canonical:
        raise EvaluationError('Every reviewed identity requires a registry decision')
    matches = [d['match'] for d in decisions if d['match'] is not None]
    if len(matches)!=len(set(matches)):
        raise EvaluationError('Separate trial identities matched one existing program; reconcile first')
    for d in decisions:
        if not d['reason'].strip() or d['match'] is not None and d['match'] not in registry['resources']:
            raise EvaluationError('Unknown registry match or missing identity judgment')
        if set(d['possibleDuplicateExistingIds'])-set(registry['resources']):
            raise EvaluationError('Unknown possible duplicate identity')
        if d['match'] is None and d['possibleDuplicateExistingIds']:
            raise EvaluationError('Resolve the possible existing identity before allocating another ID')
    merged = resolution['mergedResources']
    required = {g['canonicalId'] for g in groups if len(g['memberIds'])>1}
    if len(merged)!=len(required) or {r['id'] for r in merged}!=required:
        raise EvaluationError('Each multi-proposal identity needs one complete consolidated resource')
    findings=resolution['mergeFindings']
    if len(findings)!=len(required) or {f['canonicalId'] for f in findings}!=required:
        raise EvaluationError('Each consolidation needs a before/after finding')
    for f in findings:
        if not f['before'].strip() or not f['after'].strip() or not f['sourceUrls']:
            raise EvaluationError('Consolidation finding needs evidence and before/after text')
    by_id={r['id']:r for r in report['resources']}
    schema=response_schema({'preparationPolicyVersion':POLICY_VERSION})['properties']['resources']['items']
    for r in merged:
        validate_schema(r,schema);normalize_preparation_fields(r)
        group=next(g for g in groups if g['canonicalId']==r['id'])
        expected={c for m in group['memberIds'] for c in by_id[m]['candidateIds']}
        if set(r['candidateIds'])!=expected or r['categories']!=['housing']:
            raise EvaluationError('A consolidation lost candidate provenance or changed scope')
        expected_sources={s['url'] for m in group['memberIds'] for s in by_id[m]['sources']}
        if expected_sources-{s['url'] for s in r['sources']}:
            raise EvaluationError('A consolidation lost source evidence')
    for kind,key in [('types','typeMatches'),('forGroups','groupMatches')]:
        proposed={t['id'] for t in report['collection'][kind]}
        mappings=resolution[key]
        old={t['id']:t for t in previous['taxonomy'][kind]}
        if len(mappings)!=len(proposed) or {m['proposedId'] for m in mappings}!=proposed:
            raise EvaluationError('Taxonomy mappings must cover each reviewed meaning once')
        used=[m['existingId'] for m in mappings if m['existingId'] is not None]
        if len(used)!=len(set(used)):
            raise EvaluationError('Multiple trial meanings map to one office meaning; reconcile first')
        for m in mappings:
            if not m['reason'].strip() or m['existingId'] is not None and m['existingId'] not in old:
                raise EvaluationError('Unknown taxonomy match or missing explanation')
            if kind=='types' and m['existingId'] is not None and old[m['existingId']]['categoryId']!='housing':
                raise EvaluationError('Type belongs to another category')
    if not resolution['preservationJudgment'].strip():
        raise EvaluationError('Final preservation judgment missing')


def build_bundle(report, resolution, registry, previous, *, source_namespace, input_hashes, reviewed_at):
    validate_resolution(resolution,report,registry,previous)
    collection=report['collection']
    by_id={r['id']:deepcopy(r) for r in report['resources']}
    by_id.update({r['id']:deepcopy(r) for r in resolution['mergedResources']})
    taxonomy={'categories':deepcopy(previous['taxonomy']['categories'])}
    maps={}
    for kind,key in [('types','typeMatches'),('forGroups','groupMatches')]:
        old={t['id']:t for t in previous['taxonomy'][kind]}
        decisions={m['proposedId']:m for m in resolution[key]}
        taxonomy[kind]=[];maps[kind]={}
        for proposed in collection[kind]:
            match=decisions[proposed['id']]['existingId']
            if match:
                entry=deepcopy(old[match])
            else:
                entry=deepcopy(proposed)
                entry['id']=('type_mesa_housing_' if kind=='types' else 'group_mesa_')+digest(proposed)[:14]
                if kind=='types':entry['categoryId']='housing'
            taxonomy[kind].append(entry);maps[kind][proposed['id']]=entry['id']
    identities=[];assessments={};resources=[]
    decisions={d['canonicalId']:d for d in resolution['identities']}
    assignments={a['resourceId']:a for a in collection['assignments']}
    for group in collection['identities']:
        rid=group['canonicalId'];resource=by_id[rid];decision=decisions[rid]
        identities.append(dict(members=group['memberIds'],match=decision['match'],label=resource['name'],
                               reason=group['reason']+' Registry reconciliation: '+decision['reason']))
        for member in group['memberIds']:
            assessments[member]=dict(state=resource['state'] if member==rid else 'merged',
                reason=group['reason']+' '+decision['reason'],**({'target':rid} if member!=rid else {}))
        row={k:resource.get(k,'') for k in ['id','name','description','phone','address','website','email','hours','informationText','state']}
        row.update(researchedAt=resource.get('researchedAt'),categories=['housing'],
            types=[maps['types'][t] for t in assignments[rid]['types']],
            forGroups=[maps['forGroups'][g] for g in assignments[rid]['forGroups']],
            sourceIds=list(dict.fromkeys(source_id(s['url'].strip()) for s in resource['sources'])))
        if resource['state']=='needs-resolution':row['resolutionReason']=resource['resolutionReason']
        resources.append(row)
    starters=[dict(resourceId=s['resourceId'],position=i,contribution=s['contribution'],limitation=s['limitation'])
              for i,s in enumerate(collection['starters'],1)]
    selected={s['resourceId'] for s in starters}
    catalog=source_catalog([s for g in collection['identities'] for s in by_id[g['canonicalId']]['sources']])
    payload=dict(office={'slug':'mesa','name':'Mesa'},scope={'categoryIds':['housing'],'completeScope':True,'completeOffice':False},
        taxonomy=taxonomy,resources=resources,sources=catalog,
        starterSets=[dict(categoryId='housing',rationale=collection['rationale'],gaps='; '.join(collection['gaps']),
                          sizeException=collection.get('sizeException',''),members=starters)],
        considerations=[dict(resourceId=rid,categoryId='housing',reason=a['consideration']) for rid,a in assignments.items() if rid not in selected])
    bundle=dict(artifactType='scout-reviewed-preparation',policyVersion=POLICY_VERSION,
        sourceNamespace=source_namespace,officeCategoryIds=[c['id'] for c in taxonomy['categories']],
        inputs=input_hashes,identityDecisions=identities,assessments=assessments,payload=payload)
    bundle['review']=dict(reviewer='DeepSeek V4.1-Flash (max), fresh review plus explicit import reconciliation',
        reviewedAt=reviewed_at,identity=json.dumps(resolution['identities'],ensure_ascii=False),
        content='Full original-lead dispositions and fresh reviewed batch findings are retained in the hashed evaluation report. '+resolution['preservationJudgment'],
        taxonomy=json.dumps({'typeMatches':resolution['typeMatches'],'groupMatches':resolution['groupMatches'],'assignments':collection['assignments']},ensure_ascii=False),
        starterSets=collection['rationale']+' Gaps: '+'; '.join(collection['gaps']),preservation=resolution['preservationJudgment'])
    bundle['review']['inputFingerprint']=review_fingerprint(bundle)
    return bundle


def render_review(artifact, evaluation):
    from ..prepared_preview import render_preview
    markdown,page=render_preview(artifact)
    esc=lambda value:html.escape(str(value))
    sources={s['id']:s for s in artifact['sources']}
    types={t['id']:t['label'] for t in artifact['taxonomy']['types']}
    groups={g['id']:g['label'] for g in artifact['taxonomy']['forGroups']}
    sections=['<section><h2>All resource details</h2><p>DeepSeek-reviewed Housing proposals. Office approval and agency verification remain separate.</p>']
    for r in sorted(artifact['resources'],key=lambda r:r['name'].casefold()):
        sections.append('<details id="'+esc(r['id'])+'"><summary>'+esc(r['name'])+' — '+esc(r['state'])+'</summary>')
        sections.append('<p>'+esc(r['description'])+'</p><p class="muted">Kinds of help: '+esc(', '.join(types[t] for t in r['types']))+'; Groups: '+esc(', '.join(groups[g] for g in r['forGroups']) or 'No group assigned')+'</p>')
        for key in ['phone','address','website','email','hours','resolutionReason']:
            if r.get(key):sections.append('<p><strong>'+esc(key)+':</strong> '+esc(r[key])+'</p>')
        for heading,text in information_sections(r['informationText']).items():
            sections.append('<h4>'+esc(heading)+'</h4><p>'+esc(text).replace('\n','<br>')+'</p>')
        sections.append('<p>Sources: '+' · '.join('<a href="'+esc(sources[s]['url'])+'">'+esc(sources[s]['title'])+'</a>' for s in r['sourceIds'])+'</p></details>')
    sections.append('</section><section><h2>DeepSeek review findings</h2>')
    for n,findings in enumerate(evaluation['batchReviews'],1):
        for f in findings:
            sections.append('<article><h3>'+esc(f['issue'])+'</h3><p class="muted">Batch '+str(n)+' · '+esc(f['status'])+'</p><p><strong>Before:</strong> '+esc(f['before'])+'</p><p><strong>After:</strong> '+esc(f['after'])+'</p>')
            sections.append('<p>'+' · '.join('<a href="'+esc(url)+'">'+esc(url)+'</a>' for url in f['sourceUrls'] if url.startswith(('https://','http://')))+'</p></article>')
    sections.append('<h3>Import reconciliation</h3><p>'+esc(evaluation['importReconciliation']['preservationJudgment'])+'</p>')
    for f in evaluation['importReconciliation']['mergeFindings']:
        sections.append('<p><strong>'+esc(f['canonicalId'])+':</strong> '+esc(f['before'])+' → '+esc(f['after'])+'</p>')
    sections.append('</section>')
    return markdown,page.replace('</html>','\n'.join(sections)+'</html>')


def reconcile_and_export(root, **kwargs):
    with (Path(root)/'runner.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        return _reconcile_and_export(root,**kwargs)


def _reconcile_and_export(root, *, production_registry, previous_artifact, destination_registry, output):
    """Call only after user explicitly requests an importable Housing handoff."""
    root=Path(root).resolve();handoff=root/'handoff';output=Path(output)
    report_path=root/'reports/reviewed-with-selections.json'
    if read(root/'progress.json').get('status')!='completed':
        raise EvaluationError('Freeze the independent preparation/review trial first')
    report=read(report_path)
    # Immutable copies prevent changing office context during identity reconciliation.
    for name,path in [('registry.json',production_registry),('previous-artifact.json',previous_artifact)]:
        if not (handoff/name).exists():write_bytes_once(handoff/name,Path(path).read_bytes())
    registry=load_registry(handoff/'registry.json');previous=read(handoff/'previous-artifact.json')
    write_once(handoff/'authorization.json',dict(approvedBy='Michael',scope='Importable Mesa Housing prepared-resources.json plus separate evaluation JSON and readable review',
        approvalText='"I’d like WSRS-TSO to import it." "Both formats, please--evaluation file as weell as prepared-resources."',
        evaluationReportSha256=file_hash(report_path),registrySha256=file_hash(handoff/'registry.json'),
        previousArtifactSha256=file_hash(handoff/'previous-artifact.json')))
    existing=[{k:r.get(k,'') for k in ['id','name','website','address','phone']} for r in previous['resources']]
    prompt=('You are DeepSeek completing the explicitly requested import reconciliation AFTER your independent Housing review is frozen. '
        'The legacy Mesa records below are identity/taxonomy context only, not an answer key or authority for resource facts. '
        'Match each reviewed distinct program to an existing registry ID only when program-specific evidence supports it. '
        'Never merge different programs merely because they share an agency/domain/contact. Record ambiguous legacy duplicates explicitly; do not delete or suppress them. '
        'For each multi-proposal identity group, return ONE full merged resource in mergedResources, preserving all candidateIds, source URLs and supported details, with the canonical provisional ID. '
        'Do not return unchanged singleton resources. Resolve material factual conflicts with targeted primary sources or keep needs-resolution. '
        'Do not rewrite facts from the historical reviewed package. Preserve five Information sections and null verifiedOn. '
        'Reuse established office Type and For-group IDs when their meaning is the same; explain genuinely different meanings. '
        'Check the final starter explanations still fit these identities. Return only JSON with this exact shape:\n'+json.dumps(SHAPE)+
        '\nMerged-resource schema:\n'+json.dumps(response_schema({'preparationPolicyVersion':POLICY_VERSION})['properties']['resources']['items'])+
        '\nFrozen independently reviewed proposals and collection judgments:\n'+json.dumps(report,ensure_ascii=False)+
        '\nExisting identity context:\n'+json.dumps(existing,ensure_ascii=False)+
        '\nExisting office taxonomy:\n'+json.dumps(previous['taxonomy'],ensure_ascii=False))
    packet=dict(assignmentId='import-reconciliation',condition='existing-policy',category='housing',stage='housing-collection',
                passKey='import-reconciliation',task=prompt,requiresLiveSearch=False)
    ledger=Ledger(root)
    resolution=run_assignment(packet,ledger,LiveTransport(ledger.config['provider']['endpoint']),
                              lambda value:validate_resolution(value,report,registry,previous))['result']
    bundle_path=handoff/'reviewed-bundle.json'
    if not bundle_path.exists():
        bundle=build_bundle(report,resolution,registry,previous,source_namespace='mesa-housing-deepseek-20260928',
            input_hashes={'evaluationReport':file_hash(report_path),'candidateAssignment':file_hash(root/'inputs/assignment.json'),
                         'registry':file_hash(handoff/'registry.json'),'legacyIdentityContext':file_hash(handoff/'previous-artifact.json'),
                         'reconciliation':digest(resolution)},reviewed_at=now())
        # Complete all structural/identity checks before touching the production registry.
        finalize(bundle,registry)
        write_once(bundle_path,bundle)
    _,expected_registry,_,_=finalize(read(bundle_path),registry)
    source_now=load_registry(Path(production_registry))
    if fingerprint(source_now) not in {fingerprint(registry),fingerprint(expected_registry)}:
        raise EvaluationError('Production registry advanced; reconcile against its current version before export')
    destination_registry=Path(destination_registry)
    current=load_registry(destination_registry)
    already_exported=fingerprint(current)==fingerprint(expected_registry)
    if not already_exported and (current['namespace']!=registry['namespace'] or not set(current['resources'])<=set(registry['resources'])):
        raise EvaluationError('Destination registry is not an ancestor of the frozen production registry')
    if not already_exported and any(registry['aliases'].get(k)!=v for k,v in current['aliases'].items()):
        raise EvaluationError('Destination and production registry aliases disagree')
    if not already_exported and fingerprint(current)!=fingerprint(registry):
        # Explicitly preserve the full current registry from the production checkout.
        from ..resource_identity import save_registry
        save_registry(destination_registry,registry,expected_fingerprint=fingerprint(current))
    export_bundle(bundle_path,destination_registry,output)
    if Path(production_registry).resolve()!=destination_registry.resolve():
        from ..resource_identity import save_registry
        save_registry(Path(production_registry),load_registry(destination_registry),expected_fingerprint=fingerprint(source_now))
    validate_artifact(read(output/'prepared-resources.json'),load_registry(destination_registry),
                      office_category_ids=[c['id'] for c in previous['taxonomy']['categories']])
    evaluation=dict(artifactType='scout-housing-evaluation',evaluationOnly=True,importable=False,
        originalAssignment=read(root/'inputs/assignment.json'),curated=read(root/'reports/curated-with-selections.json'),
        reviewed=report,importReconciliation=resolution,independentReviewInputWarning='Legacy office identity context was introduced only AFTER the fresh DeepSeek review was frozen.')
    evaluation['batchReviews']=[read(p).get('reviewFindings',[]) for p in sorted((root/'results/normalized').glob('reviewed-*.json'))]
    evaluation['execution']={name:read(root/path) for name,path in {
        'executionPlan':'execution-plan.json','executionControl':'execution-control.json',
        'executionLimitAmendment':'execution-limit-amendment.json'}.items() if (root/path).exists()}
    evaluation['execution']['outputAllowanceAmendments']=[read(p) for p in sorted((root/'execution-amendments').glob('*-output.json'))]
    evaluation['execution']['collectionAssemblies']=[
        {'assignmentId':p.parent.name,'evidence':value['assemblyEvidence']}
        for p in sorted((root/'results/existing-policy/housing').glob('*collection*/result.json'))
        if 'assemblyEvidence' in (value:=read(p))]
    evaluation['execution']['note']='Recorded recovery and scheduling changes are part of this trial; all prior usage is retained. Raw native responses remain in the Scout audit.'
    write_once(output/'evaluation.json',evaluation)
    markdown,page=render_review(read(output/'prepared-resources.json'),evaluation)
    write_bytes_once(output/'review.html',page.encode())
    write_bytes_once(output/'starter-summary.md',markdown.encode())
    write_bytes_once(output/'evaluation-review.html',(root/'reports/reviewed-with-selections.html').read_bytes())
    write_once(output/'usage.json',ledger.summarize_usage())
    return read(output/'receipt.json')
