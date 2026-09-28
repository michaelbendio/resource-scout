"""Pure helpers for sealed operating policies and auditable pass stopping."""
from copy import deepcopy
from .improvement_packages import ImprovementError, digest, nonempty


def apply_policies(manifest, snapshot):
    from .operating_policy import validate_policy
    from .research_execution import sample_categories
    policies = {}
    for entry in snapshot['policies']:
        policy = validate_policy(entry['policy']); scope = policy['scope']
        category = scope['category']
        current = digest({'playbook':manifest['playbooks'][category], 'learnedGuidance':manifest.get('learnedGuidance')})
        if current != entry['guidanceSha256']:
            raise ImprovementError('Operating policy guidance changed; compare and review it again')
        policies[(category,scope['kind'])] = entry
    manifest['operatingPolicies'] = deepcopy(snapshot)
    for tid, plan in manifest['taskPlans'].items():
        kind = tid.split(':',1)[0]
        chosen = [policies[(cid,kind)] for cid in plan['categoryIds'] if (cid,kind) in policies]
        if not chosen: continue
        models = [p['policy']['models'] for p in chosen]
        if any(m != models[0] for m in models):
            raise ImprovementError('Conflicting model profiles on an overlapping resource; settle scope explicitly')
        if manifest['settings']['schemaVersion'] == 2:
            requested = manifest['settings']['modelIdentities']
            if any(model is not None and models[0][name] != model for name, model in requested.items()):
                raise ImprovementError('Operating policy conflicts with an explicitly requested model; review the policy or execution configuration')
        plan['models'] = deepcopy(models[0])
        plan['operatingPolicyIds'] = [p['proposalId'] for p in chosen]
        for entry in chosen:
            p=entry['policy']; cid=p['scope']['category']
            if kind == 'discovery':
                plan['passes']=[{**deepcopy(f),'reason':f['direction']} for f in p['passes']]
                plan['stopping']=deepcopy(p['stopping']); plan['requiredNeeds']=deepcopy(p['requiredNeeds'])
            # Preserve mandatory deliberate checks. Targeted requests are separate
            # task events and are never changed by category sampling.
            if plan['comparisonReasons'].get(cid)=='deliberate': continue
            rate=p['sampling']
            selected=set()
            for cohort in manifest['sampling']['cohorts']:
                selected.update(sample_categories(cohort['categoryIds'],cohort['seed'],rate['numerator'],rate['denominator']))
            plan['comparisonReasons'].pop(cid,None)
            if cid in selected:
                plan['comparisonReasons'][cid]='policy-random'


def validate_pass_evaluation(task, stage, document):
    from .learning_workbench import exact, texts
    exact(document,('reviewer','resultSha256','retainedFindingKeys','coveredNeeds','unresolvedNeeds','limitHit','reason'),'Pass evaluation')
    for k in ('reviewer','reason'): nonempty(document[k],k)
    for k in ('retainedFindingKeys','coveredNeeds','unresolvedNeeds'): texts(document[k],k,empty=True)
    if type(document['limitHit']) is not bool: raise ImprovementError('Limit status must be explicit')
    if not stage.startswith('pass:') or stage not in task['results']:
        raise ImprovementError('Assess a completed discovery pass')
    if digest(task['results'][stage]) != document['resultSha256']:
        raise ImprovementError('Pass evaluation refers to a different result')


def stopping_basis(plan, task):
    if 'stopping' not in plan: raise ImprovementError('No approved stopping rule for this task')
    stages=['pass:'+p['key'] for p in plan['passes']]
    completed=[]
    for stage in stages:
        if stage not in task['results']:break
        completed.append(stage)
    skipped=stages[len(completed):]
    rule=plan['stopping']
    if not skipped or len(completed)<rule['minPasses']:
        raise ImprovementError('Minimum passes not met or no remaining tail')
    if any(s in task['assignments'] for s in skipped) or 'primary' in task['assignments']:
        raise ImprovementError('Cannot omit an already dispatched pass or change sealed synthesis')
    covered=set();seen=set();gains=[];reviews={}
    for stage in completed:
        review=task.get('passEvaluations',{}).get(stage)
        if review is None:raise ImprovementError('Every completed pass needs a value assessment')
        validate_pass_evaluation(task,stage,review)
        receipt=task['results'][stage]['executionReceipt']
        if not receipt['complete'] or receipt['remainingGaps'] or review['limitHit'] or review['unresolvedNeeds']:
            raise ImprovementError('Limits or unresolved work cannot count as coverage')
        covered.update(review['coveredNeeds'])
        value=set(review['retainedFindingKeys']);gains.append(len(value-seen));seen.update(value)
        reviews[stage]=digest(review)
    if not set(plan['requiredNeeds'])<=covered:
        raise ImprovementError('An important or sparse required need is still unexamined')
    n=rule['consecutiveNoGain']
    if len(gains)<n or any(gains[-n:]):raise ImprovementError('Consecutive zero-new-value criterion not met')
    return {'skippedStages':skipped,'evaluationHashes':reviews,'coveredNeeds':sorted(covered),
            'distinctRetainedFindings':len(seen),'rule':deepcopy(rule)}


def validate_stopping(plan, task):
    for stage,review in task.get('passEvaluations',{}).items():validate_pass_evaluation(task,stage,review)
    decision=task.get('stoppingDecision')
    if decision:
        nonempty(decision.get('reviewer'),'Stopping reviewer');nonempty(decision.get('reason'),'Stopping reason')
        # Later primary/freeze assignments are legitimate after the stop. Check
        # eligibility as it stood at stopping, while still validating all results.
        original=deepcopy(task)
        original['assignments']={s:a for s,a in original['assignments'].items() if s.startswith('pass:')}
        if decision['basis'] != stopping_basis(plan,original):raise ImprovementError('Stopping evidence changed')
