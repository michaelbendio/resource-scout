"""Evidence-bound maintenance, with independently resumable rechecks and discovery."""
from __future__ import annotations

import json
from .project_state import decode_project_state, encode_project_state
from .performance import measured
import re
from copy import deepcopy
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

from .codex_first_research import load_researcher_roster
from .improvement_packages import ImprovementError, digest, next_timestamp, nonempty, read_package, resource_blocked, utcnow, write_package
from .resource_writing import compose_information, load_writing_guidance
from .scout_classification import catalog, memberships
from .scout_improvement import ImprovementWorkflow, _notes, _sources
from .research_execution import (ROLES, augment_assignment, build_execution, execution_ready, execution_summary,
                                execution_stages, freeze_receipt, task_plan,
                                validate_execution, validate_receipt)

POLICY = Path(__file__).with_name('maintenance_guidance') / 'default.json'
BLIND_POLICY = POLICY.with_name('blind_comparison.json')
BLIND_ROSTER = Path(__file__).with_name('researcher_roster_v2.json')
STATUSES = ('current', 'changed', 'moved', 'renamed', 'paused', 'possibly-closed', 'reopened', 'inconclusive', 'identity', 'new')
FIELDS = ('name', 'description', 'informationText', 'phone', 'website', 'address', 'hours', 'categories', 'categoryFilters', 'forGroups')


def date_value(value, label, optional=False):
    if optional and value == '':
        return value
    if not isinstance(value, str):
        raise ImprovementError(f'{label} must be a YYYY-MM-DD date')
    try:
        date.fromisoformat(value)
    except ValueError as error:
        raise ImprovementError(f'{label} must be a YYYY-MM-DD date') from error
    return value


def identity_matches(candidate, records):
    def keys(record):
        name = re.sub(r'\W+', '', str(record.get('name', '')).casefold())
        phone = re.sub(r'\D+', '', str(record.get('phone', '')))[-10:]
        url = urlsplit(str(record.get('website', '')))
        host = (url.hostname or '').removeprefix('www.')
        program_url = host + url.path.rstrip('/') if url.path.strip('/') else ''
        return {('name', name), ('phone', phone), ('host', host), ('program-url', program_url)} - {('name', ''), ('phone', ''), ('host', ''), ('program-url', '')}
    wanted = keys(candidate)
    return [{**deepcopy(record), 'matchReasons': sorted(k for k, v in wanted & keys(record))}
            for record in records if wanted & keys(record) or (candidate.get('id') and candidate.get('id') == record.get('id'))]


def validate_fields(fields, data, guidance, *, new=False):
    if not isinstance(fields, dict) or set(fields) - (set(FIELDS) - {'informationText'} | {'informationSections'}):
        raise ImprovementError('Unknown maintenance field; Information changes require the five sections')
    result = deepcopy(fields)
    if 'informationSections' in result:
        result['informationText'] = compose_information(result.pop('informationSections'), guidance)
    for field in set(FIELDS) - {'categories', 'categoryFilters', 'forGroups'}:
        if field in result and not isinstance(result[field], str):
            raise ImprovementError(f'{field} must be text')
    for field in ('name', 'description'):
        if field in result: nonempty(result[field], field)
    if result.get('website'):
        url = urlsplit(result['website'])
        if url.scheme not in ('http', 'https') or not url.netloc: raise ImprovementError('Proposed website must use HTTP(S)')
    if new:
        for field in ('name', 'description', 'informationText'):
            nonempty(result.get(field), field)
        if not result.get('categories'):
            raise ImprovementError('A new resource needs a service category')
    terms = memberships({k: result.get(k, {} if k == 'categoryFilters' else []) for k in ('categories', 'categoryFilters', 'forGroups')})
    if not terms <= set(catalog(data)):
        raise ImprovementError('Use existing exact office categories, Types, and groups')
    if 'categoryFilters' in result and 'categories' in result and any(c not in result['categories'] for c in result['categoryFilters']):
        raise ImprovementError('Types require membership in their category')
    return result


class MaintenanceWorkflow(ImprovementWorkflow):
    kind = 'maintenance'

    def _load(self, connection, project_id):
        state = super()._load(connection, project_id)
        with measured('research.execution_validation'):
            validate_execution(state)
        return state

    def prepare(self, payload, office, resource_ids, category_ids, *, run_name, historical=False, source_name='resource-package.zip', blind_comparison=False, execution_config=None, supersedes=None, operator='', change_reason='', operating_trial_packet_id=None):
        package = read_package(payload)
        office, run_name = nonempty(office, 'Office'), nonempty(run_name, 'Run name')
        self._office(package, office)
        ids = set(package['resources'])
        categories = {c['id'] for c in package['data']['categories']}
        for selected, allowed, label in ((resource_ids, ids, 'resources'), (category_ids, categories, 'categories')):
            if not isinstance(selected, list) or any(not isinstance(i, str) for i in selected) or len(set(selected)) != len(selected) or not set(selected) <= allowed:
                raise ImprovementError(f'Select unique existing {label}')
        if not resource_ids and not category_ids:
            raise ImprovementError('Select resources to recheck or categories to search')
        for rid in resource_ids:
            if message := resource_blocked(package, rid):
                raise ImprovementError(message)
        configuration = {'office': office, 'runName': run_name, 'baseSha256': package['sha256'],
                         'resourceIds': sorted(resource_ids), 'categoryIds': sorted(category_ids), 'historical': bool(historical),
                         'policy': json.loads(POLICY.read_text()), 'writingGuidance': load_writing_guidance(),
                         'researcherRoster': load_researcher_roster()}
        if operating_trial_packet_id and (execution_config is None or supersedes is not None):
            raise ImprovementError('Experimental policy needs a new sampled execution, not an in-place replan')
        predecessor = None
        if supersedes is not None:
            if execution_config is None or type(supersedes) is not int:
                raise ImprovementError('A protocol change needs an existing project and execution configuration')
            with self.store.connect() as c:
                prior = self._load(c, supersedes)
            if prior['office'].casefold() != office.casefold() or prior['historical'] != bool(historical):
                raise ImprovementError('A protocol change must retain the office and historical/operational context')
            predecessor = prior.get('execution')
            configuration['protocolChange'] = {'predecessorId': supersedes,
                'predecessorRevision': prior['revision'], 'predecessorStateSha256': digest(prior),
                'operator': nonempty(operator, 'Protocol-change operator'),
                'reason': nonempty(change_reason, 'Protocol-change reason'),
                'workReuse': 'New assignments; prior outputs remain historical evidence, not fresh results.'}
        if execution_config is not None:
            if blind_comparison:
                raise ImprovementError('Choose the sampled execution protocol or legacy blind comparison, not both')
            from .learning_workbench import LearningWorkbench
            learning_categories = set(category_ids)
            for rid in resource_ids:
                learning_categories.update(package['resources'][rid].get('categories', []))
            learned = LearningWorkbench(self.store).resolve_guidance(office, learning_categories, 'research')
            if learned['lessons']:
                configuration['learnedGuidance'] = learned
            from .operating_policy import OperatingPolicyWorkbench
            scopes = {(cid, 'discovery') for cid in category_ids}
            scopes.update((cid, 'recheck') for rid in resource_ids for cid in package['resources'][rid].get('categories', []))
            policies=OperatingPolicyWorkbench(self.store)
            if operating_trial_packet_id:
                task_ids=['discovery:'+cid for cid in category_ids]+['recheck:'+rid for rid in resource_ids]
                operating=policies.trial_policy_snapshot(operating_trial_packet_id,package['sha256'],office,task_ids,
                    {**{'discovery:'+cid:{(cid,'discovery')} for cid in category_ids},
                     **{'recheck:'+rid:{(cid,'recheck') for cid in package['resources'][rid].get('categories',[])} for rid in resource_ids}})
                configuration['operatingTrialPacketId']=operating_trial_packet_id
            else:
                operating = policies.resolve_policies(office, scopes)
            if not historical and any(p.get('historicalOnly') for p in operating['policies']):
                raise ImprovementError('Synthetic or historical comparisons cannot govern operational research')
            if operating['policies']:
                configuration['operatingPolicies'] = operating
            configuration['execution'] = build_execution(configuration, package, execution_config, predecessor)
            configuration['researcherRoster'] = {'schemaVersion': 2, 'version': 'astra-sampled-v1',
                'researchers': [{'name': name, 'role': role} for name, role in configuration['execution']['manifest']['roles'].items()]}
        if blind_comparison:
            configuration['researcherRoster'] = load_researcher_roster(BLIND_ROSTER)
            configuration['blindComparisonPolicy'] = json.loads(BLIND_POLICY.read_text())
            if not any(r['role'] == 'blind' for r in configuration['researcherRoster']['researchers']):
                raise ImprovementError('Blind comparison requires a blind researcher')
        key = digest({'kind': self.kind, **configuration})
        with self.store.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            old = c.execute('SELECT id FROM scout_improvement_projects WHERE project_key=?', (key,)).fetchone()
            if old:
                pid = old['id']
            else:
                tasks = {f'{kind}:{ident}': {'kind': kind, 'targetId': ident, 'assignments': {}, 'results': {}, 'reviews': {}, 'saved': []}
                         for kind, selected in (('recheck', sorted(resource_ids)), ('discovery', sorted(category_ids))) for ident in selected}
                state = {**configuration, 'kind': self.kind, 'sourceName': source_name, 'createdAt': utcnow(),
                         'latestSha256': None, 'requiresReconnection': False, 'tasks': tasks}
                c.execute('INSERT OR IGNORE INTO scout_improvement_packages VALUES(?,?)', (package['sha256'], payload))
                pid = c.execute('INSERT INTO scout_improvement_projects(project_key,revision,state_json) VALUES(?,0,?)', (key, encode_project_state(state))).lastrowid
                state.update(id=pid, revision=0)
                self._save(c, state, 'maintenance-created', {'scope': {'resourceIds': resource_ids, 'categoryIds': category_ids}, 'baseSha256': package['sha256']})
        return self.view(pid)

    @classmethod
    def _task_stages(cls, state, task, *, include_stopped=False):
        if state.get('execution'):
            return execution_stages(state, task)
        return cls._stages(state, include_stopped=include_stopped)

    def record_provider(self, project_id, revision, researcher, status, operator, reason, context_id=''):
        """Record an actual availability check; unavailable never means completed."""
        operator, reason = nonempty(operator, 'Operator'), nonempty(reason, 'Availability evidence')
        if researcher not in ROLES or researcher == 'Codex' or status not in ('available', 'unavailable'):
            raise ImprovementError('Choose an outside researcher and available or unavailable')
        if status == 'available':
            nonempty(context_id, 'Provider context identity')
        with self.store.connect() as c:
            state = self._checked(c, project_id, revision)
            if not state.get('execution'):
                raise ImprovementError('Availability records require the sampled execution protocol')
            value = {'status': status, 'operator': operator, 'reason': reason, 'contextId': context_id, 'checkedAt': utcnow()}
            state.setdefault('providerAvailability', {})[researcher] = value
            self._save(c, state, 'execution-provider-availability', {'researcher': researcher, **value})
            return self._view(c, state)

    def request_challenge(self, project_id, revision, task_id, researcher, operator, reason):
        operator, reason = nonempty(operator, 'Operator'), nonempty(reason, 'Challenge reason')
        with self.store.connect() as c:
            state = self._checked(c, project_id, revision)
            task = state['tasks'].get(task_id)
            if not state.get('execution') or not task:
                raise ImprovementError('Select an existing sampled execution task')
            if state['execution']['manifest']['roles'].get(researcher) != 'challenger':
                raise ImprovementError('Targeted challenges require a configured challenger, not the primary or blind researcher')
            if researcher in task.get('targetedChecks', {}):
                if task['targetedChecks'][researcher]['reason'] != reason:
                    raise ImprovementError('An existing challenge cannot silently change its purpose')
                return self._view(c, state)
            if 'reconcile' in task['assignments']:
                raise ImprovementError('Reconciliation is sealed; further challenges require a new execution')
            request = {'operator': operator, 'reason': reason, 'requestedAt': utcnow()}
            task.setdefault('targetedChecks', {})[researcher] = request
            self._save(c, state, 'execution-targeted-check-requested', {'taskId': task_id, 'researcher': researcher, **request})
            return self._view(c, state)

    def assess_pass(self, project_id, revision, task_id, stage, document):
        from .operating_runtime import validate_pass_evaluation
        with self.store.connect() as c:
            state = self._checked(c, project_id, revision)
            task = state['tasks'].get(task_id)
            if not state.get('execution') or task is None: raise ImprovementError('Select a sampled execution task')
            validate_pass_evaluation(task, stage, document)
            prior = task.get('passEvaluations', {}).get(stage)
            if prior is not None:
                if prior != document: raise ImprovementError('Pass evaluation is immutable')
                return self._view(c, state)
            if task.get('stoppingDecision'): raise ImprovementError('Stopping decision is already sealed')
            task.setdefault('passEvaluations', {})[stage] = deepcopy(document)
            self._save(c, state, 'execution-pass-assessed', {'taskId': task_id, 'stage': stage, 'evaluationSha256': digest(document)})
            return self._view(c, state)

    def stop_optional_passes(self, project_id, revision, task_id, reviewer, reason):
        from .operating_runtime import stopping_basis
        nonempty(reviewer, 'Stopping reviewer'); nonempty(reason, 'Stopping reason')
        with self.store.connect() as c:
            state = self._checked(c, project_id, revision)
            task = state['tasks'].get(task_id)
            if not state.get('execution') or task is None: raise ImprovementError('Select a sampled execution task')
            if task.get('stoppingDecision'): return self._view(c, state)
            basis = stopping_basis(task_plan(state, task), task)
            task['stoppingDecision'] = {'reviewer': reviewer, 'reason': reason, 'basis': basis}
            self._save(c, state, 'execution-optional-passes-stopped', {'taskId': task_id, **task['stoppingDecision']})
            return self._view(c, state)

    @staticmethod
    def _stages(state, *, include_stopped=False):
        stages = ImprovementWorkflow._stages(state)
        if not state.get('blindComparisonPolicy'):
            return stages
        primary = stages[0][1]
        blind = [('blind:' + r['name'], r['name']) for r in state['researcherRoster']['researchers']
                 if r['role'] == 'blind' and (include_stopped or r['name'] not in state.get('stoppedBlindResearch', {}))]
        return stages[:-1] + [('freeze', primary)] + blind + [('reconcile', primary)]

    def stop_blind_research(self, project_id, revision, researcher, operator, reason):
        """Record an explicit protocol change without inventing or deleting research."""
        operator, reason = nonempty(operator, 'Operator'), nonempty(reason, 'Reason for stopping blind research')
        with self.store.connect() as c:
            state = self._checked(c, project_id, revision)
            if not state.get('blindComparisonPolicy') or researcher not in {
                r['name'] for r in state['researcherRoster']['researchers'] if r['role'] == 'blind'
            }:
                raise ImprovementError('Only a configured blind researcher can be stopped')
            stopped = state.setdefault('stoppedBlindResearch', {})
            if researcher in stopped:
                return self._view(c, state)
            stopped[researcher] = {'operator': operator, 'reason': reason, 'stoppedAt': utcnow()}
            self._save(c, state, 'maintenance-blind-research-stopped', {'researcher': researcher, **stopped[researcher]})
            return self._view(c, state)

    @classmethod
    def _freeze_manifest(cls, state):
        stages = [s for s, _ in cls._stages(state) if s in ('primary', 'freeze') or s.startswith('audit:')]
        return {'baseSha256': state['baseSha256'], 'tasks': {
            tid: {s: {'assignmentSha256': task['assignments'][s]['assignmentSha256'],
                      'resultSha256': digest(task['results'][s])} for s in stages}
            for tid, task in state['tasks'].items()}}

    @classmethod
    def _stage_ready(cls, state, task, stage):
        if state.get('execution'):
            return execution_ready(state, task, stage)
        if stage not in {s for s, _ in cls._stages(state)}:
            return False
        if stage == 'primary':
            return True
        if 'primary' not in task['results']:
            return False
        if stage.startswith('audit:'):
            return True
        if stage == 'freeze':
            return all(s in task['results'] for s, _ in cls._stages(state) if s.startswith('audit:'))
        if stage.startswith('blind:') or (stage == 'reconcile' and state.get('blindComparisonPolicy')):
            frozen = state.get('blindFreeze')
            if not frozen:
                return False
            manifest = cls._freeze_manifest(state)
            if frozen['manifest'] != manifest or frozen['manifestSha256'] != digest(manifest):
                raise ImprovementError('The frozen pre-blind research has changed')
        if stage.startswith('blind:'):
            return True
        return all(s in task['results'] for s, _ in cls._stages(state) if s != 'reconcile')

    @staticmethod
    def _findings(task):
        findings = ImprovementWorkflow._findings(task)
        for stage, result in task['results'].items():
            if stage.startswith('blind:'):
                for item in result['items']:
                    fid = stage.split(':', 1)[1] + ':' + item['id']
                    findings[fid] = {'id': item['id'], 'summary': item['summary'], 'severity': 'material'}
        return findings

    def _identities(self, c, state, package):
        records = [{**r, 'identityStatus': 'current'} for r in package['resources'].values()]
        records += [{'id': d.get('targetId'), 'name': d.get('label', ''), 'identityStatus': 'retired'}
                    for d in package['data'].get('deletions', []) if d.get('kind') == 'resource']
        if state.get('operatingTrialPacketId'):
            return records
        for row in c.execute('SELECT id,state_json FROM scout_improvement_projects ORDER BY id'):
            prior = decode_project_state(row['state_json'])
            if prior.get('operatingTrialPacketId'):
                continue
            if prior.get('kind') != self.kind or prior['office'].casefold() != state['office'].casefold():
                continue
            # Development outcomes must never become production identity evidence.
            if prior['historical'] != state['historical']:
                continue
            for prior_tid, task in prior['tasks'].items():
                for item in task['results'].get('reconcile', {}).get('items', []):
                    review = task['reviews'].get(item['id'])
                    if review and review['decision'] in ('decline', 'accept', 'retire'):
                        original = task['assignments'].get('primary', {}).get('target', {}) if task['kind'] == 'recheck' else {}
                        fields = {**original, **item['fields']}
                        records.append({'id': review['resourceId'], 'name': fields.get('name', item['program']),
                                        'phone': fields.get('phone', ''), 'website': fields.get('website', ''),
                                        'identityStatus': review['decision'], 'priorRunId': row['id'], 'priorTaskId': prior_tid, 'priorItemId': item['id'], 'note': review['note']})
        return records

    def _prior_checks(self, c, state, task):
        observations = []
        if state.get('operatingTrialPacketId'):
            return observations
        for row in c.execute('SELECT id,state_json FROM scout_improvement_projects WHERE id<>? ORDER BY id DESC', (state['id'],)):
            prior = decode_project_state(row['state_json'])
            if prior.get('operatingTrialPacketId'):
                continue
            if prior.get('kind') != self.kind or prior['office'].casefold() != state['office'].casefold() or prior['historical'] != state['historical']:
                continue
            for old in prior['tasks'].values():
                if (old['kind'], old['targetId']) != (task['kind'], task['targetId']): continue
                if 'reconcile' in old['results']:
                    observations.append({'runId': row['id'], 'baseSha256': prior['baseSha256'],
                        'lastAttemptedOn': old.get('lastAttemptedOn'), 'result': old['results']['reconcile'],
                        'humanReviews': old['reviews'], 'savedItems': old['saved']})
        return observations

    @staticmethod
    def _closure_notice(notice, sources, program):
        if not isinstance(notice, dict) or set(notice) != {'sourceIndex', 'kind', 'program', 'statement'} or notice['kind'] != 'official-program-closure' or notice['program'] != program:
            raise ImprovementError('Closure needs an explicit official-program-closure notice naming the program; failed contact is not closure evidence')
        MaintenanceWorkflow._indices([notice['sourceIndex']], sources, 'closure notice')
        statement = nonempty(notice['statement'], 'Exact closure statement')
        if statement not in sources[notice['sourceIndex']]['excerpt']:
            raise ImprovementError('Closure statement must be present in its cited source excerpt')

    def next_assignment(self, project_id, *, researcher=None, task_id=None):
        with self.store.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            state = self._load(c, project_id)
            package = self._package(c, state['baseSha256'])
            if task_id and task_id not in state['tasks']:
                raise ImprovementError('Unknown maintenance task')
            for tid, task in state['tasks'].items():
                if task_id and task_id != tid:
                    continue
                for stage, name in self._task_stages(state, task):
                    if stage in task['results'] or (researcher and researcher != name):
                        continue
                    if not self._stage_ready(state, task, stage):
                        continue
                    if state.get('execution') and name != 'Codex' and state.get('providerAvailability', {}).get(name, {}).get('status') != 'available':
                        continue
                    if stage in task['assignments']:
                        if state.get('execution') and name != 'Codex' and task['assignments'][stage]['dispatchContext']['contextId'] != state['providerAvailability'][name]['contextId']:
                            raise ImprovementError('Resume the sealed provider context or create an explicit new execution; do not silently move a blind assignment')
                        return deepcopy(task['assignments'][stage])
                    contract = {'schemaVersion': 1, 'taskId': tid, 'assignmentSha256': 'copy from assignment',
                                'evidenceSources': [], 'researchNotes': ''}
                    if stage.startswith('audit:'):
                        contract.update(findings=[], closureChecks=[])
                    else:
                        contract['items'] = []
                        if stage in ('freeze', 'reconcile'):
                            contract['resolutions'] = []
                    a = {'projectId': project_id, 'taskId': tid, 'stage': stage, 'researcher': name,
                         'scope': task['kind'], 'office': state['office'], 'runName': state['runName'],
                         'historicalDevelopmentOnly': state['historical'], 'baseSha256': state['baseSha256'],
                         'target': deepcopy(package['resources'][task['targetId']]) if task['kind'] == 'recheck' else next(c for c in package['data']['categories'] if c['id'] == task['targetId']),
                         'attachmentHashes': package['assetHashes'] if task['kind'] == 'recheck' else {},
                         'catalog': {'categories': package['data']['categories'], 'forGroups': package['data']['forGroups']},
                         'knownIdentities': self._identities(c, state, package), 'priorChecks': self._prior_checks(c, state, task),
                         'priorEvidenceWarning': 'Prior observations and the original package are source history, not proof of current facts or human verification.', 'writingGuidance': state['writingGuidance'],
                         'instructions': deepcopy(state['policy'].get(stage.split(':')[0], [])), 'editableFields': [f for f in FIELDS if f != 'informationText']+['informationSections'], 'outputContract': contract,
                         'itemContract': {'id': task['targetId'] if task['kind'] == 'recheck' else 'stable-lead-id', 'status': 'one of: '+', '.join(STATUSES),
                           'program': 'Exact named program', 'summary': 'What changed or remains uncertain', 'fields': {},
                           'evidence': [0], 'closureEvidence': [], 'questions': [], 'nextCheckOn': '', 'lastEvidenceOfOperationOn': ''},
                         'auditFindingContract': {'id': 'finding-id', 'summary': 'Issue or useful correction', 'severity': 'material'},
                         'closureNoticeContract': {'sourceIndex': 0, 'kind': 'official-program-closure', 'program': 'Exact named program', 'statement': 'Exact closure words from the cited excerpt'},
                         'closureCheckContract': {'itemId': 'closed-item-id', 'notice': {'sourceIndex': 0, 'kind': 'official-program-closure', 'program': 'Exact named program', 'statement': 'Exact closure words from the cited excerpt'}},
                         'resolutionContract': {'findingId': 'researcher:finding-id', 'status': 'resolved or needs-review', 'reason': 'Disposition'}}
                    if state.get('blindComparisonPolicy'):
                        policy_stage = stage.split(':')[0]
                        a['instructions'] = list(a['instructions']) + state['blindComparisonPolicy'].get(policy_stage, [])
                        if stage == 'freeze':
                            a['instructions'] = state['policy']['reconcile'] + a['instructions']
                    if stage != 'primary' and not stage.startswith(('blind:', 'pass:')):
                        a['primaryResult'] = task['results']['primary']
                    if stage in ('freeze', 'reconcile'):
                        a['audits'] = {s.split(':')[1]: r for s, r in task['results'].items() if s.startswith('audit:')}
                    if stage.startswith('blind:'):
                        # Only the original package is shared, never this run's proposals or history.
                        a.pop('priorChecks')
                        a['knownIdentities'] = [deepcopy(r) for r in package['resources'].values()]
                    if stage == 'reconcile' and state.get('blindComparisonPolicy'):
                        a['frozenResult'] = deepcopy(task['results']['freeze'])
                        a['blindFreeze'] = deepcopy(state['blindFreeze'])
                        a['blindResults'] = {s.split(':', 1)[1]: deepcopy(r) for s, r in task['results'].items() if s.startswith('blind:')}
                    if stage in ('freeze', 'reconcile') and state.get('stoppedBlindResearch'):
                        a['stoppedBlindResearch'] = deepcopy(state['stoppedBlindResearch'])
                        a['instructions'].append('The recorded protocol change stops further assignments to the named blind researchers. Do not wait for or invent their missing results. Resolve every challenger finding and every blind result already received. State the missing blind coverage explicitly; stopping research is not a completed check or curator approval.')
                    if state.get('execution'):
                        augment_assignment(a, state, task, package)
                    a['assignmentSha256'] = digest(a)
                    task['assignments'][stage] = a
                    self._save(c, state, 'maintenance-assigned', {'taskId': tid, 'stage': stage, 'assignment': a})
                    return deepcopy(a)
        return None

    @staticmethod
    def _indices(indices, sources, label):
        if not isinstance(indices, list) or any(type(i) is not int or i < 0 or i >= len(sources) for i in indices) or len(set(indices)) != len(indices):
            raise ImprovementError(f'Invalid {label} source references')

    def submit(self, project_id, stage, result):
        if not isinstance(result, dict):
            raise ImprovementError('Result must be an object')
        with self.store.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            state = self._load(c, project_id)
            tid = result.get('taskId')
            task = state['tasks'].get(tid)
            assignment = task and task['assignments'].get(stage)
            if not assignment or type(result.get('schemaVersion')) is not int or result['schemaVersion'] != 1 or result.get('assignmentSha256') != assignment['assignmentSha256']:
                raise ImprovementError('Result does not match a sealed assignment')
            if stage in task['results']:
                if task['results'][stage] != result:
                    raise ImprovementError('Completed research cannot be overwritten')
                return self._view(c, state)
            if not self._stage_ready(state, task, stage):
                raise ImprovementError('Complete the required preceding research stages first')
            if set(result) != set(assignment['outputContract']):
                raise ImprovementError('Return exactly the assigned result fields')
            sources = _sources(result['evidenceSources'])
            nonempty(result['researchNotes'], 'Research notes')
            if state.get('execution'):
                validate_receipt(result, assignment)
                if stage.startswith('blind:'):
                    context_id = result['executionReceipt']['contextId']
                    if any(a.get('dispatchContext', {}).get('contextId') == context_id
                           for t in state['tasks'].values() for s, a in t['assignments'].items()
                           if s.startswith('audit:')) or any(
                            r.get('executionReceipt', {}).get('contextId') == context_id
                            for t in state['tasks'].values() for s, r in t['results'].items()
                            if not s.startswith('blind:')):
                        raise ImprovementError('Blind context was already exposed to primary or challenger work')
            if stage.startswith('pass:'):
                observations = result['observations']
                if not isinstance(observations, list):
                    raise ImprovementError('Pass observations must be an array')
                for observation in observations:
                    if not isinstance(observation, dict) or set(observation) != set(assignment['observationContract']):
                        raise ImprovementError('Use the exact pass observation contract')
                    nonempty(observation['summary'], 'Pass observation')
                    self._indices(observation['evidence'], sources, 'pass observation')
                    _notes(observation['questions'], 'Pass questions')
                    if not observation['evidence'] and not observation['questions']:
                        raise ImprovementError('An unsupported pass observation needs a specific follow-up question')
            elif stage.startswith('audit:'):
                if not isinstance(result['findings'], list) or not isinstance(result['closureChecks'], list):
                    raise ImprovementError('Findings and closure checks must be arrays')
                seen = set()
                for finding in result['findings']:
                    if not isinstance(finding, dict) or set(finding) != {'id', 'summary', 'severity'} or finding['severity'] not in ('material', 'editorial'):
                        raise ImprovementError('Invalid audit finding')
                    fid = nonempty(finding['id'], 'Finding ID'); nonempty(finding['summary'], 'Finding summary')
                    if fid in seen: raise ImprovementError('Duplicate finding')
                    seen.add(fid)
                seen = set()
                for check in result['closureChecks']:
                    if not isinstance(check, dict) or set(check) != {'itemId', 'notice'} or check['itemId'] in seen:
                        raise ImprovementError('Invalid closure check')
                    nonempty(check['itemId'], 'Closure item ID')
                    item = next((i for i in assignment['primaryResult']['items'] if i['id'] == check['itemId']), None)
                    if not item: raise ImprovementError('Closure check must name an assigned program')
                    self._closure_notice(check['notice'], sources, item['program']); seen.add(check['itemId'])
            else:
                package = self._package(c, state['baseSha256'])
                if not isinstance(result['items'], list): raise ImprovementError('Items must be an array')
                ids = set()
                for item in result['items']:
                    if not isinstance(item, dict) or set(item) != set(assignment['itemContract']): raise ImprovementError('Use the exact item contract')
                    ident = nonempty(item['id'], 'Item ID')
                    if ident in ids: raise ImprovementError('Duplicate item ID')
                    ids.add(ident)
                    if item['status'] not in STATUSES: raise ImprovementError('Unknown maintenance status')
                    nonempty(item['program'], 'Named program'); nonempty(item['summary'], 'Finding summary')
                    _notes(item['questions'], 'Follow-up questions')
                    date_value(item['nextCheckOn'], 'Next check', True); date_value(item['lastEvidenceOfOperationOn'], 'Operational evidence date', True)
                    self._indices(item['evidence'], sources, 'evidence')
                    if not isinstance(item['closureEvidence'], list): raise ImprovementError('Closure evidence must be an array of explicit notices')
                    for notice in item['closureEvidence']: self._closure_notice(notice, sources, item['program'])
                    if item['status'] not in ('inconclusive', 'identity') and not item['evidence']: raise ImprovementError('Supported status requires evidence')
                    if item['status'] in ('inconclusive', 'identity') and not item['questions']: raise ImprovementError('Unresolved checks need focused follow-up questions')
                    if item['status'] == 'possibly-closed' and not item['closureEvidence']: raise ImprovementError('Closure needs explicit official evidence; failed contact alone is inconclusive')
                    if item['status'] in ('current', 'inconclusive', 'identity', 'possibly-closed') and item['fields']: raise ImprovementError('This status must not silently change resource fields')
                    validate_fields(item['fields'], package['data'], state['writingGuidance'], new=task['kind'] == 'discovery')
                    if task['kind'] == 'recheck' and item['status'] == 'new': raise ImprovementError('Known resources retain their identity')
                    if task['kind'] == 'discovery' and task['targetId'] not in item['fields'].get('categories', []): raise ImprovementError('Addition must belong to the searched category')
                    if task['kind'] == 'discovery' and item['status'] not in ('new', 'reopened'): raise ImprovementError('Discovery returns new or reopened leads; recheck existing resources separately')
                if task['kind'] == 'recheck' and ids != {task['targetId']}: raise ImprovementError('Recheck must report exactly its assigned resource')
                if stage in ('freeze', 'reconcile'):
                    findings = self._findings(task)
                    resolutions = result['resolutions']
                    if not isinstance(resolutions, list) or len(resolutions) != len(findings): raise ImprovementError('Address every audit finding exactly once')
                    seen = set()
                    for resolution in resolutions:
                        if not isinstance(resolution, dict) or set(resolution) != {'findingId', 'status', 'reason'}: raise ImprovementError('Invalid resolution')
                        fid = resolution['findingId']
                        if fid not in findings or fid in seen or resolution['status'] not in ('resolved', 'needs-review'): raise ImprovementError('Invalid or duplicate resolution')
                        nonempty(resolution['reason'], 'Resolution reason'); seen.add(fid)
                    for item in result['items']:
                        if item['status'] == 'possibly-closed' and any(item['id'] not in {v['itemId'] for v in task['results'][s]['closureChecks'] if v['notice']['program'] == item['program']} for s, _ in self._task_stages(state, task) if s.startswith('audit:') and not (state.get('execution') and stage == 'freeze')):
                            raise ImprovementError('Closure requires every independent audit to check the named program evidence')
                        if stage == 'reconcile' and item['status'] == 'possibly-closed':
                            for s, _ in self._task_stages(state, task):
                                if s.startswith('blind:') and not any(b['id'] == item['id'] and b['program'] == item['program'] and b['closureEvidence'] for b in task['results'][s]['items']):
                                    raise ImprovementError('Closure also requires the blind researcher to check the named program evidence')
            task['lastAttemptedOn'] = utcnow()
            task['results'][stage] = deepcopy(result)
            if stage == 'freeze' and state.get('execution'):
                task['primaryFreeze'] = freeze_receipt(state, task)
            elif stage == 'freeze' and all('freeze' in t['results'] for t in state['tasks'].values()):
                state['blindFreeze'] = {'manifest': self._freeze_manifest(state),
                                       'manifestSha256': digest(self._freeze_manifest(state)), 'frozenAt': utcnow()}
            self._save(c, state, 'maintenance-result', {'taskId': tid, 'stage': stage, 'result': result})
            return self._view(c, state)

    def connect_latest(self, project_id, revision, payload, office):
        package = read_package(payload)
        with self.store.connect() as c:
            state = self._checked(c, project_id, revision)
            if nonempty(office, 'Office').casefold() != state['office'].casefold(): raise ImprovementError('Wrong office package')
            self._office(package, office)
            previous = self._package(c, state['latestSha256'] or state['baseSha256'])
            if package['data']['packageVersion'] < previous['data']['packageVersion']: raise ImprovementError('Package is older than the connected baseline')
            if state['latestSha256'] == package['sha256'] and not state['requiresReconnection']: return self._view(c, state)
            c.execute('INSERT OR IGNORE INTO scout_improvement_packages VALUES(?,?)', (package['sha256'], payload))
            self._capture_intake(c, state, payload)
            state.update(latestSha256=package['sha256'], requiresReconnection=False)
            for task in state['tasks'].values():
                task['reviews'] = {k: v for k, v in task['reviews'].items() if v['decision'] in ('decline', 'keep') or k in task['saved']}
            self._save(c, state, 'maintenance-connected', {'sha256': package['sha256']})
            return self._view(c, state)

    def _comparison(self, base, current, item, guidance, data):
        proposed = validate_fields(item['fields'], data, guidance)
        return {field: {'base': base.get(field), 'current': current.get(field), 'proposed': value,
                        'conflict': current.get(field) != base.get(field) and current.get(field) != value}
                for field, value in proposed.items() if value != base.get(field)}

    def _rows(self, c, state, package):
        base = self._package(c, state['baseSha256'])
        identities = self._identities(c, state, package)
        rows = []
        for tid, task in state['tasks'].items():
            for item in task['results'].get('reconcile', {}).get('items', []):
                current = package['resources'].get(item['id']) if task['kind'] == 'recheck' else None
                row = {'lastAttemptedOn': task.get('lastAttemptedOn'), 'taskId': tid, **deepcopy(item), 'current': current, 'saved': item['id'] in task['saved'],
                       'review': task['reviews'].get(item['id']), 'audits': {s.split(':',1)[1]: deepcopy(r) for s,r in task['results'].items() if s.startswith('audit:')}, 'sources': task['results']['reconcile']['evidenceSources'],
                       'findings': self._findings(task), 'resolutions': task['results']['reconcile']['resolutions'],
                       'matches': [], 'comparison': {}, 'blocked': ''}
                if state.get('blindComparisonPolicy'):
                    row['blindResults'] = {s.split(':', 1)[1]: deepcopy(r) for s, r in task['results'].items() if s.startswith('blind:')}
                    row['frozenResult'] = deepcopy(task['results']['freeze'])
                    row['blindFreezeSha256'] = state['blindFreeze']['manifestSha256']
                if state.get('execution'):
                    row['blindResults'] = {s.split(':', 1)[1]: deepcopy(r) for s, r in task['results'].items() if s.startswith('blind:')}
                    row['frozenResult'] = deepcopy(task['results']['freeze'])
                    row['primaryFreeze'] = deepcopy(task['primaryFreeze'])
                if state.get('stoppedBlindResearch'):
                    row['stoppedBlindResearch'] = deepcopy(state['stoppedBlindResearch'])
                if task['kind'] == 'recheck':
                    row['blocked'] = resource_blocked(package, item['id'])
                    if current: row['comparison'] = self._comparison(base['resources'][item['id']], current, item, state['writingGuidance'], base['data'])
                else:
                    row['matches'] = identity_matches(item['fields'], [r for r in identities if (r.get('priorRunId'), r.get('priorTaskId'), r.get('priorItemId')) != (state['id'], tid, item['id'])])
                try:
                    validate_fields(item['fields'], package['data'], state['writingGuidance'], new=task['kind']=='discovery')
                except ImprovementError as error:
                    row['blocked'] = str(error)
                rows.append(row)
        return rows

    def _view(self, c, state):
        package = self._package(c, state['latestSha256'] or state['baseSha256'])
        tasks = [{'id': tid, 'kind': t['kind'], 'targetId': t['targetId'], 'research': [
            {'stage': s, 'researcher': n, 'complete': s in t['results'],
             'required': not (s.startswith('blind:') and n in state.get('stoppedBlindResearch', {}))}
            for s, n in self._task_stages(state, t, include_stopped=True)],
            **({'primaryFreeze': deepcopy(t.get('primaryFreeze')), 'plan': deepcopy(task_plan(state, t)),
                'targetedChecks': deepcopy(t.get('targetedChecks', {}))} if state.get('execution') else {})} for tid, t in state['tasks'].items()]
        return {'intakeEvidence': deepcopy(state.get('intakeEvidence')), **{k: state[k] for k in ('id', 'revision', 'office', 'runName', 'historical', 'createdAt', 'baseSha256', 'latestSha256', 'requiresReconnection')},
                'coverage': {'officeResources': len(package['resources']), 'officeCategories': len(package['data']['categories']),
                             **{kind: {'selected': sum(t['kind'] == kind for t in tasks), 'completed': sum(t['kind'] == kind and all(s['complete'] or not s['required'] for s in t['research']) for t in tasks)} for kind in ('recheck', 'discovery')}},
                'catalog': {'categories': package['data']['categories'], 'forGroups': package['data']['forGroups']},
                'tasks': tasks, 'items': self._rows(c, state, package),
                **({'execution': deepcopy(state['execution']), 'executionSummary': execution_summary(state), 'providerAvailability': deepcopy(state.get('providerAvailability', {}))} if state.get('execution') else {}),
                **({'stoppedBlindResearch': deepcopy(state['stoppedBlindResearch'])} if state.get('stoppedBlindResearch') else {}),
                **({'blindFreeze': deepcopy(state.get('blindFreeze')), 'blindComparisonPolicy': deepcopy(state['blindComparisonPolicy'])} if state.get('blindComparisonPolicy') else {})}

    def review(self, project_id, revision, task_id, item_id, decision, choices, reviewer, note, *, identity_decision='', finding_notes=None):
        reviewer, note = nonempty(reviewer, 'Reviewer'), nonempty(note, 'Review rationale and classification consequences')
        if decision not in ('accept', 'retire', 'keep', 'decline', 'unmarked'): raise ImprovementError('Unknown review decision')
        with self.store.connect() as c:
            state = self._checked(c, project_id, revision)
            package = self._package(c, state['latestSha256'] or state['baseSha256'])
            row = next((r for r in self._rows(c, state, package) if r['taskId'] == task_id and r['id'] == item_id), None)
            if not row or row['saved']: raise ImprovementError('No unsaved reconciled item to review')
            if decision in ('accept', 'retire'):
                if not state['latestSha256'] or state['requiresReconnection']: raise ImprovementError('Reconnect the current office package before accepting changes')
                if row['blocked']: raise ImprovementError(row['blocked'])
                for resolution in row['resolutions']:
                    fid = resolution['findingId']
                    if resolution['status'] == 'needs-review' and row['findings'][fid]['severity'] == 'material': nonempty((finding_notes or {}).get(fid), f'Human resolution for {fid}')
                if decision == 'retire' and row['status'] != 'possibly-closed': raise ImprovementError('Only corroborated closure can request retirement')
                if decision == 'accept' and row['status'] in ('possibly-closed', 'inconclusive', 'identity', 'current'): raise ImprovementError('This finding is an observation or requires follow-up, not an update')
                if row['current'] and decision == 'accept':
                    if not isinstance(choices, dict) or set(choices) != set(row['comparison']) or any(v not in ('current', 'proposed') for v in choices.values()): raise ImprovementError('Choose current or proposed for each changed field')
                    if not any(choices[k] == 'proposed' and v['proposed'] != v['current'] for k, v in row['comparison'].items()): raise ImprovementError('No changes selected')
                if not row['current']:
                    if row['status'] == 'reopened' or any(m['identityStatus'] in ('retired', 'retire') and (m.get('id') == row['id'] or set(m['matchReasons']) & {'name', 'program-url'}) for m in row['matches']): raise ImprovementError('Possible reopening requires office identity/deletion review; do not recreate a retired resource')
                    if row['matches'] and identity_decision != 'distinct-program': raise ImprovementError('Resolve identity matches: decline duplicates or explicitly identify a distinct program')
            rid = item_id if row['current'] else 'scout-' + digest({'office': state['office'].casefold(), 'identity': row['fields']})[:24]
            review = {'decision': decision, 'choices': deepcopy(choices), 'reviewer': reviewer, 'note': note,
                      'identityDecision': identity_decision, 'findingNotes': deepcopy(finding_notes or {}), 'reviewedAt': utcnow(), 'resourceId': rid,
                      'latestSha256': state['latestSha256'], 'identityMatchesSha256': digest(row['matches']), 'itemSha256': digest({k: row[k] for k in state['tasks'][task_id]['results']['reconcile']['items'][0]})}
            task = state['tasks'][task_id]
            if decision == 'unmarked': task['reviews'].pop(item_id, None)
            else: task['reviews'][item_id] = review
            self._save(c, state, 'maintenance-reviewed', {'taskId': task_id, 'itemId': item_id, 'review': review})
            return self._view(c, state)

    def prepare_export(self, project_id, revision):
        with self.store.connect() as c:
            state = self._checked(c, project_id, revision)
            if not state['latestSha256'] or state['requiresReconnection']: raise ImprovementError('Reconnect the current office package before export')
            package = self._package(c, state['latestSha256'])
            rows = [r for r in self._rows(c, state, package) if not r['saved'] and r['review'] and r['review']['decision'] in ('accept', 'retire')]
            if not rows: raise ImprovementError('No reviewed maintenance changes to export')
            key = digest({'projectId': project_id, 'latest': state['latestSha256'], 'rows': rows})
            prior = c.execute('SELECT id,manifest_json FROM scout_improvement_exports WHERE export_key=?', (key,)).fetchone()
            if prior: return {'exportId': prior['id'], 'manifest': json.loads(prior['manifest_json'])}
            exported = deepcopy(package['data'])
            stamp = next_timestamp([exported, *exported['resources'], *exported['categories']])
            records = []
            for row in rows:
                review = row['review']
                if review['latestSha256'] != state['latestSha256'] or row['blocked']: raise ImprovementError('Review is stale or resource is blocked')
                rid = review['resourceId']
                if review['decision'] == 'retire':
                    exported.setdefault('deletionRequests', []).append({'key': 'resource:'+rid, 'kind': 'resource', 'targetId': rid, 'label': row['current']['name'], 'requestedAt': stamp, 'description': review['note']})
                    action = 'updated'
                elif row['current']:
                    target = next(r for r in exported['resources'] if r['id'] == rid)
                    for field, choice in review['choices'].items():
                        if choice == 'proposed': target[field] = deepcopy(row['comparison'][field]['proposed'])
                    target['lastModified'] = stamp; action = 'updated'
                    if not memberships(target) <= set(catalog(exported)) or any(cid not in target.get('categories', []) for cid in target.get('categoryFilters', {})): raise ImprovementError('Review category/Type consequences together')
                else:
                    if digest(row['matches']) != review['identityMatchesSha256']: raise ImprovementError('Identity evidence changed; review the new matches again')
                    if any(r['id'] == rid for r in exported['resources']): raise ImprovementError('Duplicate new identity in this export')
                    target = {'id': rid, 'categories': [], 'categoryFilters': {}, 'forGroups': [], 'pdfs': [], **validate_fields(row['fields'], exported, state['writingGuidance'], new=True), 'lastModified': stamp}
                    exported['resources'].append(target); action = 'added'
                if review['decision'] != 'retire':
                    from .open_questions import attach_questions, make_questions
                    attach_questions(target, make_questions([{'question':q, 'explanation':row['summary']} for q in row['questions']],
                        {'kind':'maintenance', 'projectId':project_id, 'taskId':row['taskId'], 'itemId':row['id']}))
                exported.setdefault('changes', []).append({'id': f'maintenance:{project_id}:{rid}:{key[:16]}', 'type': 'resource', 'action': action, 'targetId': rid,
                    'targetName': row['program'], 'timestamp': stamp, 'description': ('Maintenance retirement request for office review. ' if review['decision'] == 'retire' else 'Reviewed maintenance change. ') + review['note']})
                records.append({'taskId': row['taskId'], 'itemId': row['id'], 'review': review})
            versions = [json.loads(r[0])['packageVersion'] for r in c.execute('SELECT manifest_json FROM scout_improvement_exports WHERE project_id=?', (project_id,))]
            exported.update(packageVersion=max([exported['packageVersion'], *versions])+1, packageCreatedAt=stamp, lastModified=stamp)
            payload = write_package(exported, package['assets']); out = read_package(payload)
            manifest = {'projectId': project_id, 'latestSha256': state['latestSha256'], 'baseSha256': state['baseSha256'], 'packageVersion': exported['packageVersion'],
                        'packageSha256': out['sha256'], 'assetHashes': out['assetHashes'], 'records': records, 'historicalDevelopmentOnly': state['historical'], 'coverage': self._view(c, state)['coverage']}
            eid = c.execute('INSERT INTO scout_improvement_exports(project_id,export_key,manifest_json,payload) VALUES(?,?,?,?)', (project_id, key, json.dumps(manifest), payload)).lastrowid
            self._save(c, state, 'maintenance-export-prepared', {'exportId': eid, 'manifest': manifest})
            return {'exportId': eid, 'manifest': manifest}

    def acknowledge_export(self, project_id, revision, export_id, package_sha256):
        with self.store.connect() as c:
            state = self._checked(c, project_id, revision)
            export = c.execute('SELECT * FROM scout_improvement_exports WHERE id=? AND project_id=?', (export_id, project_id)).fetchone()
            if not export: raise ImprovementError('Export not found')
            manifest = json.loads(export['manifest_json'])
            if package_sha256 != manifest['packageSha256'] or manifest['latestSha256'] != state['latestSha256']: raise ImprovementError('Saved export does not match the connected package')
            if export['acknowledged_at']: return self._view(c, state)
            if manifest.get('questionHandoffOnly'):
                from .question_handoff import acknowledge_question_export
                return acknowledge_question_export(self, c, state, manifest, export_id)
            for record in manifest['records']:
                if state['tasks'][record['taskId']]['reviews'].get(record['itemId']) != record['review']: raise ImprovementError('Review changed after export; do not acknowledge stale bytes')
            for record in manifest['records']: state['tasks'][record['taskId']]['saved'].append(record['itemId'])
            state['requiresReconnection'] = True
            c.execute('UPDATE scout_improvement_exports SET acknowledged_at=? WHERE id=?', (utcnow(), export_id))
            self._save(c, state, 'maintenance-export-saved', {'exportId': export_id, 'sha256': package_sha256})
            return self._view(c, state)
