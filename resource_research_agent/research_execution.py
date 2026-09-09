"""Opt-in Astra execution contracts. Legacy maintenance stages are unchanged.

The manifest seals guidance and sampling; task freezes seal primary-only work.
Provider availability and targeted-check requests are separate, audited events.
These contracts record operator attestations, not proof of browser isolation.
"""
from copy import deepcopy
from dataclasses import asdict
from hashlib import sha256
import json
import math
from pathlib import Path

from .improvement_packages import ImprovementError, digest, nonempty
from .playbooks import playbook_for

PROTOCOL = 'astra-sampled-v1'
ROLES = {'Codex': 'primary', 'Claude': 'blind', 'ChatGPT': 'challenger',
         'Grok': 'challenger', 'Perplexity': 'challenger'}
ALGORITHM = 'sha256-rank-v1'
PROTOCOL_GUIDANCE = Path(__file__).with_name('maintenance_guidance') / 'astra_protocol.json'


def sample_categories(ids, seed, numerator, denominator):
    """Stable sampling without replacement; callers preserve the seed and scope."""
    if (type(numerator) is not int or type(denominator) is not int
            or denominator < 1 or not 0 <= numerator <= denominator):
        raise ImprovementError('Sampling needs integer 0 <= numerator <= denominator')
    nonempty(seed, 'Sampling seed')
    ids = sorted(ids)
    ranked = sorted(ids, key=lambda cid: (sha256((seed + '\0' + cid).encode()).hexdigest(), cid))
    return sorted(ranked[:(len(ids) * numerator + denominator - 1) // denominator])


def build_execution(configuration, package, settings, predecessor=None):
    settings = deepcopy(settings)
    required = {'schemaVersion', 'protocol', 'version', 'serviceArea', 'sampling',
                'deliberateCategoryIds', 'modelIdentities'}
    if not isinstance(settings, dict) or set(settings) != required:
        raise ImprovementError('Use the exact versioned execution configuration fields')
    if type(settings['schemaVersion']) is not int or settings['schemaVersion'] != 1 or settings['protocol'] != PROTOCOL:
        raise ImprovementError('Unsupported research execution protocol')
    nonempty(settings['version'], 'Execution settings version')
    nonempty(settings['serviceArea'], 'Service area')
    sampling = settings['sampling']
    if not isinstance(sampling, dict) or set(sampling) != {'seed', 'numerator', 'denominator'}:
        raise ImprovementError('Sampling needs seed, numerator and denominator')
    if sampling.get('seed') == 'REPLACE-ONCE-WITH-A-RANDOM-SEED-BEFORE-PREPARING-THE-RUN':
        raise ImprovementError('Replace the example sampling seed once before preparing the execution')
    models = settings['modelIdentities']
    if not isinstance(models, dict) or set(models) != set(ROLES):
        raise ImprovementError('Record every researcher model identity, using null when unknown')
    if any(v is not None and (not isinstance(v, str) or not v.strip()) for v in models.values()):
        raise ImprovementError('Model identities must be nonblank text or null')
    categories = {c['id']: c for c in package['data']['categories']}
    task_categories = {f'discovery:{cid}': [cid] for cid in configuration['categoryIds']}
    for rid in configuration['resourceIds']:
        task_categories[f'recheck:{rid}'] = sorted(set(package['resources'][rid].get('categories', [])))
    eligible = sorted({cid for ids in task_categories.values() for cid in ids})
    if not set(eligible) <= set(categories):
        raise ImprovementError('Execution scope contains an unknown category')
    deliberate = settings['deliberateCategoryIds']
    if (not isinstance(deliberate, list) or any(not isinstance(cid, str) for cid in deliberate)
            or len(set(deliberate)) != len(deliberate) or not set(deliberate) <= set(eligible)):
        raise ImprovementError('Deliberate comparisons must name unique in-scope categories')
    settings['deliberateCategoryIds'] = sorted(deliberate)
    random_scope = sorted(set(eligible) - set(deliberate))
    sample = sample_categories(random_scope, **sampling)
    cohorts = [{'categoryIds': random_scope, 'selectedCategoryIds': sample, **sampling}]
    if predecessor:
        prior = predecessor['manifest']['sampling']
        if not set(prior['eligibleCategoryIds']) <= set(random_scope) or prior['deliberateCategoryIds'] != sorted(deliberate):
            raise ImprovementError('A scope amendment must retain prior random and deliberate comparisons')
        if any(prior[k] != sampling[k] for k in ('seed', 'numerator', 'denominator')):
            raise ImprovementError('Scope amendments retain the original sampling policy and seed')
        added = sorted(set(random_scope) - set(prior['eligibleCategoryIds']))
        cohorts = deepcopy(prior['cohorts'])
        if added:
            seed = digest({'seed': sampling['seed'], 'predecessor': predecessor['manifestSha256'], 'added': added})
            selected = sample_categories(added, seed, sampling['numerator'], sampling['denominator'])
            cohorts.append({'categoryIds': added, 'selectedCategoryIds': selected, **sampling, 'seed': seed})
        sample = sorted({cid for cohort in cohorts for cid in cohort['selectedCategoryIds']})
    playbooks = {cid: asdict(playbook_for(cid, categories[cid].get('label') or categories[cid].get('name'),
                                         settings['serviceArea'])) for cid in eligible}
    plans = {}
    for tid, ids in task_categories.items():
        # Discovery passes are individually resumable. Rechecks use the same
        # category guidance, but examine one named resource as a whole.
        passes = []
        if tid.startswith('discovery:'):
            focused = playbooks[ids[0]]['focused_research']
            passes = [{'key': f['key'], 'reason': f['direction'], **deepcopy(f)} for f in focused['focuses']]
        plans[tid] = {'categoryIds': ids, 'passes': passes,
                      'comparisonReasons': {cid: ('deliberate' if cid in deliberate else 'random')
                                            for cid in ids if cid in deliberate or cid in sample}}
    manifest = {'protocol': PROTOCOL, 'settings': settings, 'roles': ROLES,
                'baseSha256': configuration['baseSha256'], 'office': configuration['office'],
                'runName': configuration['runName'], 'historical': configuration['historical'],
                'resourceIds': configuration['resourceIds'], 'categoryIds': configuration['categoryIds'],
                'sampling': {'algorithm': ALGORITHM, **sampling, 'eligibleCategoryIds': random_scope,
                             'selectedCategoryIds': sample, 'deliberateCategoryIds': sorted(deliberate), 'cohorts': cohorts},
                'policy': configuration['policy'], 'writingGuidance': configuration['writingGuidance'],
                'playbooks': playbooks, 'taskPlans': plans}
    if configuration.get('protocolChange'):
        manifest['protocolChange'] = deepcopy(configuration['protocolChange'])
    guidance = json.loads(PROTOCOL_GUIDANCE.read_text())
    if type(guidance.get('schemaVersion')) is not int or guidance['schemaVersion'] != 1:
        raise ImprovementError('Unsupported protocol guidance schema')
    nonempty(guidance.get('version'), 'Protocol guidance version')
    for stage in ('receipt', 'pass', 'freeze', 'blind', 'audit', 'reconcile'):
        if not isinstance(guidance.get(stage), list) or not guidance[stage]:
            raise ImprovementError('Protocol guidance requires every stage instruction')
        for instruction in guidance[stage]:
            nonempty(instruction, 'Protocol instruction')
    manifest['protocolGuidance'] = guidance
    if configuration.get('learnedGuidance'):
        manifest['learnedGuidance'] = deepcopy(configuration['learnedGuidance'])
    # JSON normalization means tuples from dataclasses cannot drift after resume.
    manifest = json.loads(json.dumps(manifest))
    return {'manifest': manifest, 'manifestSha256': digest(manifest)}


def validate_execution(state):
    execution = state.get('execution')
    if not execution:
        return
    m = execution['manifest']
    if digest(m) != execution['manifestSha256']:
        raise ImprovementError('Execution guidance or sampling manifest has changed')
    for key in ('baseSha256', 'office', 'runName', 'historical', 'policy', 'writingGuidance', 'resourceIds', 'categoryIds'):
        if state[key] != m[key]:
            raise ImprovementError('Execution configuration no longer matches the sealed manifest')
    if state.get('protocolChange') != m.get('protocolChange'):
        raise ImprovementError('Execution protocol-change record has changed')
    if set(state['tasks']) != set(m['taskPlans']):
        raise ImprovementError('Scope changes require a new execution, not an in-place sampling reroll')
    for tid, task in state['tasks'].items():
        if tid != task['kind'] + ':' + task['targetId']:
            raise ImprovementError('Execution task identity has changed')
        for stage, a in task['assignments'].items():
            if a['assignmentSha256'] != digest({k: v for k, v in a.items() if k != 'assignmentSha256'}):
                raise ImprovementError('Sealed execution assignment has changed')
        frozen = task.get('primaryFreeze')
        if frozen and frozen != freeze_receipt(state, task):
            raise ImprovementError('Frozen primary-only research has changed')


def task_plan(state, task):
    return state['execution']['manifest']['taskPlans'][task['kind'] + ':' + task['targetId']]


def execution_stages(state, task):
    plan = task_plan(state, task)
    return ([(f'pass:{p["key"]}', 'Codex') for p in plan['passes']]
            + [('primary', 'Codex'), ('freeze', 'Codex')]
            + [('audit:' + name, name) for name in sorted(task.get('targetedChecks', {}))]
            + ([('blind:Claude', 'Claude')] if plan['comparisonReasons'] else [])
            + [('reconcile', 'Codex')])


def freeze_receipt(state, task):
    stages = [s for s, _ in execution_stages(state, task) if s.startswith('pass:') or s in ('primary', 'freeze')]
    return {'manifestSha256': state['execution']['manifestSha256'],
            'research': {s: {'assignmentSha256': task['assignments'][s]['assignmentSha256'],
                             'resultSha256': digest(task['results'][s])} for s in stages}}


def execution_ready(state, task, stage):
    stages = [s for s, _ in execution_stages(state, task)]
    if stage not in stages:
        return False
    if stage.startswith('pass:') or stage in ('primary', 'freeze'):
        return all(s in task['results'] for s in stages[:stages.index(stage)])
    if not task.get('primaryFreeze'):
        return False
    # Freeze all primary work for a category before revealing any outside work
    # for that category. Other categories can keep moving during an outage.
    ids = set(task_plan(state, task)['categoryIds'])
    if any(ids & set(task_plan(state, t)['categoryIds']) and not t.get('primaryFreeze')
           for t in state['tasks'].values()):
        return False
    if stage == 'reconcile':
        return all(s in task['results'] for s in stages if s != 'reconcile')
    # Availability gates dispatch, not submission of an already received reply.
    return True


def augment_assignment(a, state, task, package):
    """Build provider inputs from sealed snapshots, never live guidance files."""
    stage = a['stage']
    m = state['execution']['manifest']
    guidance = m['protocolGuidance']
    plan = task_plan(state, task)
    a['protocol'] = PROTOCOL
    a['serviceArea'] = m['settings']['serviceArea']
    a['configuredModel'] = m['settings']['modelIdentities'][a['researcher']]
    a['fieldFormats'] = {
        'categories': {'type': 'array of category IDs', 'values': 'Use catalog.categories IDs.'},
        'categoryFilters': {'type': 'object',
            'example': {'category-id': ['Exact Type label']},
            'rule': 'Keys are category IDs in this resource; each value is an array of that category’s exact catalog filters. Never return a flat array.'},
        'forGroups': {'type': 'array of strings', 'values': 'Use exact catalog.forGroups labels.'},
        'informationSections': {section['key']: 'text' for section in a['writingGuidance']['sections']},
        'otherEditableFields': 'Text strings; omit fields you are not proposing to change.'}
    a['statusFieldRules'] = {
        'current, inconclusive, identity, possibly-closed': 'fields must be the empty object {}.',
        'changed': 'Use for updates to an existing resource; fields contains the proposed replacements.',
        'new, reopened': 'Discovery additions require name, description, all five informationSections and categories including the assigned category.'}
    a['outputContract']['executionReceipt'] = {
        'complete': True, 'model': None, 'contextId': '', 'freshContext': False,
        'isolatedInputs': False, 'activeMinutes': 0, 'waitingMinutes': 0,
        'coverageNotes': '', 'remainingGaps': []}
    a['receiptInstructions'] = deepcopy(guidance['receipt'])
    a['priorEvidenceWarning'] = 'The original package and dated observations are history, not proof of current facts.'
    if stage.startswith('blind:'):
        # Explicit original-data allowlists exclude administrative research hints.
        a.pop('priorChecks', None)
        a['knownIdentities'] = [{k: deepcopy(r[k]) for k in ('id', 'name', 'website') if k in r}
                                for r in package['resources'].values()]
        a['categoryScope'] = {cid: {'include': deepcopy(m['playbooks'][cid]['scope']),
                                   'exclude': deepcopy(m['playbooks'][cid]['exclusions'])}
                              for cid in plan['categoryIds']}
        if task['kind'] == 'recheck':
            a['target'] = {k: deepcopy(v) for k, v in a['target'].items()
                           if k in {'id', 'pdfs', 'verifiedOn', *a['editableFields'], 'informationText'}}
        a['instructions'] = deepcopy(guidance['blind'])
    else:
        a['playbooks'] = {cid: deepcopy(m['playbooks'][cid]) for cid in plan['categoryIds']}
        if m.get('learnedGuidance'):
            learned = m['learnedGuidance']
            selected = [deepcopy(x) for x in learned['lessons'] if x['scope']['category'] in plan['categoryIds']]
            if selected:
                a['learnedGuidance'] = {'manifestId': learned['manifestId'], 'lessons': selected}
        a['passPlan'] = deepcopy(plan['passes'])
        if stage.startswith('pass:'):
            focus = next(p for p in plan['passes'] if stage == 'pass:' + p['key'])
            a['focus'] = deepcopy(focus)
            a['instructions'] = state['policy']['primary'] + [focus['direction']] + guidance['pass']
            a['outputContract'].pop('items')
            a['outputContract']['observations'] = []
            a['observationContract'] = {'summary': 'Supported finding or specific gap', 'evidence': [0], 'questions': []}
        if stage.startswith('pass:') or stage == 'primary':
            a['passResults'] = {s: deepcopy(r) for s, r in task['results'].items() if s.startswith('pass:')}
        if stage == 'freeze':
            a['instructions'] = state['policy']['reconcile'][1:] + guidance['freeze']
        if stage.startswith('audit:'):
            a['primaryResult'] = deepcopy(task['results']['freeze'])
            a['challengeReason'] = task['targetedChecks'][a['researcher']]['reason']
            a['instructions'] += guidance['audit']
        if stage == 'reconcile':
            a['frozenResult'] = deepcopy(task['results']['freeze'])
            a['primaryFreeze'] = deepcopy(task['primaryFreeze'])
            a['blindResults'] = {s.split(':', 1)[1]: deepcopy(r) for s, r in task['results'].items() if s.startswith('blind:')}
            a['instructions'] += guidance['reconcile']
    if a.get('learnedGuidance'):
        a['instructions'] = [*a['instructions'], 'Apply the sealed learnedGuidance methods within their declared scope. They are method instructions, not evidence of provider facts.']
    if a['researcher'] != 'Codex':
        availability = state['providerAvailability'][a['researcher']]
        # Operator availability notes can mention draft-derived issues; keep
        # those in the coordinator ledger rather than the researcher packet.
        a['dispatchContext'] = {key: availability[key] for key in ('status', 'contextId', 'checkedAt')}


def validate_receipt(result, assignment):
    r = result['executionReceipt']
    if not isinstance(r, dict) or set(r) != set(assignment['outputContract']['executionReceipt']):
        raise ImprovementError('Use the exact execution receipt contract')
    if r['complete'] is not True:
        raise ImprovementError('Incomplete transport packets cannot complete an assignment')
    if r['model'] is not None:
        nonempty(r['model'], 'Actual model')
    nonempty(r['contextId'], 'Research context')
    nonempty(r['coverageNotes'], 'Coverage notes')
    if not isinstance(r['remainingGaps'], list) or any(not isinstance(g, str) or not g.strip() for g in r['remainingGaps']):
        raise ImprovementError('Remaining gaps must be nonblank text entries')
    for key in ('activeMinutes', 'waitingMinutes'):
        if type(r[key]) not in (int, float) or not math.isfinite(r[key]) or r[key] < 0:
            raise ImprovementError('Research timing must be finite nonnegative minutes')
    if type(r['freshContext']) is not bool or type(r['isolatedInputs']) is not bool:
        raise ImprovementError('Context attestations must be booleans')
    if assignment['stage'].startswith('blind:') and not (r['freshContext'] and r['isolatedInputs']):
        raise ImprovementError('A blind result requires a fresh isolated context; preserve contaminated output as external evidence, not a completed blind check')
    if assignment.get('dispatchContext') and r['contextId'] != assignment['dispatchContext']['contextId']:
        raise ImprovementError('Result context does not match the recorded provider dispatch')


def execution_summary(state):
    pending = []
    timings = {name: {'activeMinutes': 0, 'waitingMinutes': 0, 'completedAssignments': 0} for name in ROLES}
    for tid, task in state['tasks'].items():
        for stage, name in execution_stages(state, task):
            if stage in task['results']:
                receipt = task['results'][stage]['executionReceipt']
                for key in ('activeMinutes', 'waitingMinutes'):
                    timings[name][key] += receipt[key]
                timings[name]['completedAssignments'] += 1
            elif name != 'Codex':
                availability = state.get('providerAvailability', {}).get(name, {})
                pending.append({'taskId': tid, 'researcher': name, 'stage': stage,
                                'availability': availability.get('status', 'not-checked'),
                                'reason': availability.get('reason', 'Provider access has not been checked.')})
    return {'pendingOutsideChecks': pending, 'researcherTiming': timings,
            'timingMeaning': 'Reported effort and waiting per assignment; sums are not elapsed run time when work overlaps.'}
