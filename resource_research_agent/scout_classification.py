"""Office-defined, evidence-bound classification using the reviewed update lifecycle."""
from __future__ import annotations

import json
from copy import deepcopy
from datetime import date
from pathlib import Path

from .improvement_packages import ImprovementError, digest, nonempty, read_package
from .scout_improvement import ImprovementWorkflow, _notes

FIELDS = ('categories', 'categoryFilters', 'forGroups')
POLICY = Path(__file__).with_name('classification_guidance') / 'default.json'


def labels(value, label):
    if not isinstance(value, list) or any(not isinstance(v, str) or not v.strip() or v != v.strip() for v in value):
        raise ImprovementError(f'{label} must be an array of exact nonempty labels')
    if len(value) != len(set(value)):
        raise ImprovementError(f'{label} contains duplicate values')
    return value


def memberships(record):
    result = {('categories', '', c) for c in labels(record.get('categories', []), 'categories')}
    result |= {('forGroups', '', g) for g in labels(record.get('forGroups', []), 'groups')}
    types = record.get('categoryFilters', {})
    if not isinstance(types, dict):
        raise ImprovementError('categoryFilters must be an object')
    for cid, values in types.items():
        if not isinstance(cid, str):
            raise ImprovementError('Type category must be text')
        result |= {('categoryFilters', cid, t) for t in labels(values, 'Types')}
    return result


def term_key(term):
    return json.dumps(list(term), ensure_ascii=False, separators=(',', ':'))


def catalog(data):
    terms = {}
    categories = set()
    for c in data['categories']:
        if not isinstance(c, dict):
            raise ImprovementError('Category must have an ID and label')
        cid = nonempty(c.get('id'), 'Category ID')
        if cid in categories or cid != c['id']:
            raise ImprovementError('Duplicate or unnormalized category ID')
        categories.add(cid)
        terms[('categories', '', cid)] = nonempty(c.get('label'), 'Category label')
        for t in labels(c.get('filters', []), 'Catalog Types'):
            terms[('categoryFilters', cid, t)] = t
    for g in labels(data['forGroups'], 'Catalog groups'):
        terms[('forGroups', '', g)] = g
    return terms


def draft_guidance(data, office):
    return {'schemaVersion': 1, 'office': office, 'version': 1,
            'catalogSha256': digest([data['categories'], data['forGroups']]),
            'terms': [{'field': f, 'categoryId': c, 'value': v, 'label': label,
                       'definition': '', 'aliases': [], 'populationCategory': False,
                       'approvedBy': None} for (f, c, v), label in catalog(data).items()]}


def validate_guidance(guidance, data, office, *, draft=False):
    if not isinstance(guidance, dict) or type(guidance.get('schemaVersion')) is not int or guidance.get('schemaVersion') != 1 or type(guidance.get('version')) is not int or guidance['version'] < 1:
        raise ImprovementError('Invalid classification guidance version')
    if guidance.get('office') != office or guidance.get('catalogSha256') != digest([data['categories'], data['forGroups']]):
        raise ImprovementError('Guidance must match the exact office catalog')
    if not isinstance(guidance.get('terms'), list):
        raise ImprovementError('Guidance needs terms')
    terms = catalog(data)
    seen = set()
    for item in guidance['terms']:
        if not isinstance(item, dict) or set(item) != {'field', 'categoryId', 'value', 'label', 'definition', 'aliases', 'populationCategory', 'approvedBy'}:
            raise ImprovementError('Malformed taxonomy definition')
        key = (item['field'], item['categoryId'], item['value'])
        if any(not isinstance(k, str) for k in key) or key not in terms or key in seen or item['label'] != terms[key]:
            raise ImprovementError('Definitions must use each exact office term once')
        seen.add(key)
        if not isinstance(item['definition'], str) or type(item['populationCategory']) is not bool:
            raise ImprovementError('Definition must be text and populationCategory must be boolean')
        if item['populationCategory'] and item['field'] != 'categories':
            raise ImprovementError('Only categories can be population categories')
        labels(item['aliases'], 'Aliases')
        if draft and item['approvedBy'] is not None:
            raise ImprovementError('Import draft definitions without claiming approval; use the review action')
        if item['approvedBy'] is not None:
            nonempty(item['approvedBy'], 'Definition reviewer')
            nonempty(item['definition'], 'Approved definition')
    if seen != set(terms):
        raise ImprovementError('Guidance must cover the office catalog, including pending definitions')
    return deepcopy(guidance)


def evidence_snapshot(resource, asset_hashes):
    # Writing, attached source bytes, identity and local notes can alter eligibility/access.
    return {'resource': deepcopy(resource), 'attachmentHashes': {p['path']: asset_hashes[p['path']] for p in resource.get('pdfs', [])}}


def dependency(snapshot):
    r = snapshot['resource']
    return digest({'evidence': {k: v for k, v in r.items() if k not in (*FIELDS, 'lastModified', 'verifiedOn', 'phone', 'website', 'address', 'hours')},
                   'attachments': snapshot['attachmentHashes']})


def merged_record(base, current, proposal):
    base = proposal.get('comparisonBase', base)
    b, c, p = memberships(base), memberships(current), memberships(proposal)
    reaffirmed = {(d['field'], d['categoryId'], d['value']) for d in proposal.get('decisions', []) if d['status'] == 'supported'}
    merged = (c - (b - p)) | (p - b) | ((b - c) & p & reaffirmed)
    result = deepcopy(current)
    for field in FIELDS:
        if {t for t in merged if t[0] == field} == {t for t in c if t[0] == field}:
            continue
        if field == 'categoryFilters':
            result[field] = {}
            # Preserve current display order, then append genuinely new memberships.
            for source in (current, proposal):
                for cid, values in source.get(field, {}).items():
                    for value in values:
                        if (field, cid, value) in merged and value not in result[field].setdefault(cid, []):
                            result[field][cid].append(value)
        else:
            result[field] = list(dict.fromkeys(v for source in (current, proposal) for v in source.get(field, []) if (field, '', v) in merged))
    return result


def compare_classifications(base, current, proposal):
    base = proposal.get('comparisonBase', base)
    merged = merged_record(base, current, proposal)
    b, c, p = memberships(base), memberships(current), memberships(proposal)
    result = {}
    for field in FIELDS:
        subset = lambda values: {t for t in values if t[0] == field}
        # An explicit reaffirmation opposed by a later human removal needs review.
        reaffirmed = {(d['field'], d['categoryId'], d['value']) for d in proposal.get('decisions', []) if d['status'] == 'supported'}
        conflict = bool((b - c) & p & reaffirmed & subset(b))
        result[field] = {'base': deepcopy(base.get(field, {} if field == 'categoryFilters' else [])),
                         'current': deepcopy(current.get(field, {} if field == 'categoryFilters' else [])),
                         'proposed': deepcopy(merged.get(field, {} if field == 'categoryFilters' else [])),
                         'changed': subset(memberships(merged)) != subset(c), 'conflict': conflict,
                         'alreadyApplied': subset(p) != subset(b) and subset(p) == subset(c)}
    return result


def materialize_classifications(base, current, proposal, choices):
    if not isinstance(choices, dict) or set(choices) != set(FIELDS) or any(v not in ('current', 'proposed') for v in choices.values()):
        raise ImprovementError('Choose current or proposed for all three classification fields')
    result = deepcopy(current)
    for field, comparison in compare_classifications(base, current, proposal).items():
        if choices[field] == 'proposed' and comparison['changed']:
            result[field] = deepcopy(comparison['proposed'])
    return result


class ClassificationWorkflow(ImprovementWorkflow):
    kind = 'classification'
    editable_fields = FIELDS
    result_schema_key = 'scoutClassificationResultSchemaVersion'
    change_description = 'Reviewed categories, Types and groups'
    compare_fields = staticmethod(compare_classifications)
    materialize = staticmethod(materialize_classifications)

    def prepare(self, payload, office, resource_ids, *, source_name='resource-package.zip', historical=False, guidance=None, linked_evidence=None):
        package = read_package(payload)
        office = nonempty(office, 'Office identity')
        if not isinstance(resource_ids, list) or any(not isinstance(rid, str) for rid in resource_ids):
            raise ImprovementError('Select existing resource IDs')
        guidance = validate_guidance(guidance or draft_guidance(package['data'], office), package['data'], office, draft=True)
        for resource in package['resources'].values():
            memberships(resource)
        linked_evidence = linked_evidence or {}
        if not isinstance(linked_evidence, dict) or any(rid not in resource_ids for rid in linked_evidence):
            raise ImprovementError('Linked evidence must be scoped to selected resources')
        for rid, entries in linked_evidence.items():
            if not isinstance(entries, list):
                raise ImprovementError('Linked evidence entries must be an array')
            for entry in entries:
                if not isinstance(entry, dict) or set(entry) != {'label', 'sha256', 'content'} or entry['sha256'] != digest(entry['content']):
                    raise ImprovementError('Linked evidence must include content with its exact hash')
                nonempty(entry['label'], 'Linked evidence provenance label')
        return self._prepare(payload, office, resource_ids, source_name=source_name, historical=historical,
            configuration={'classificationGuidance': guidance, 'linkedEvidence': deepcopy(linked_evidence), 'writingGuidance': {},
                           'policy': json.loads(POLICY.read_text()),
                           'researchSnapshots': {rid: evidence_snapshot(package['resources'][rid], package['assetHashes']) for rid in resource_ids if rid in package['resources']}})

    def save_guidance(self, project_id, revision, guidance, reviewer, approved_keys):
        reviewer = nonempty(reviewer, 'Definition reviewer')
        labels(approved_keys, 'Approved definition keys')
        with self.store.connect() as connection:
            state = self._checked(connection, project_id, revision)
            package = self._package(connection, state['latestSha256'] or state['baseSha256'])
            candidate = deepcopy(guidance)
            if not isinstance(candidate, dict):
                raise ImprovementError('Guidance must be an object')
            # Approval comes only from this explicit review action, never imported JSON.
            if not isinstance(candidate.get('terms'), list):
                raise ImprovementError('Guidance needs terms')
            for term in candidate['terms']:
                if isinstance(term, dict):
                    term['approvedBy'] = None
            candidate = validate_guidance(candidate, package['data'], state['office'], draft=True)
            if candidate['version'] <= state['classificationGuidance']['version']:
                raise ImprovementError('Use a newer guidance version')
            remaining = set(approved_keys)
            for term in candidate['terms']:
                key = term_key((term['field'], term['categoryId'], term['value']))
                if key in remaining:
                    nonempty(term['definition'], 'Approved definition')
                    term['approvedBy'] = reviewer
                    remaining.remove(key)
            if remaining:
                raise ImprovementError('Unknown approved definition key')
            previous = deepcopy(state['classificationGuidance'])
            state['classificationGuidance'] = candidate
            self._reset(state, list(state['resources']))
            self._save(connection, state, 'definitions-reviewed', {'reviewer': reviewer, 'before': previous, 'after': candidate, 'approvedKeys': approved_keys})
            return self._view(connection, state)

    @staticmethod
    def _reset(state, resource_ids):
        for rid in resource_ids:
            item = state['resources'][rid]
            if item['packaged']:
                continue
            if item['assignments'] or item['results']:
                item.setdefault('previousResearch', []).append({k: deepcopy(item[k]) for k in ('assignments', 'results', 'proposal', 'review')})
            item.update(assignments={}, results={}, proposal=None, review=None)

    def _connected(self, state, latest):
        catalog(latest['data'])
        for resource in latest['resources'].values():
            memberships(resource)
        changed = []
        for rid, item in state['resources'].items():
            if rid in latest['resources'] and not item['packaged']:
                new = evidence_snapshot(latest['resources'][rid], latest['assetHashes'])
                if dependency(new) != dependency(state['researchSnapshots'][rid]):
                    changed.append(rid)
                state['researchSnapshots'][rid] = new
        if state['classificationGuidance']['catalogSha256'] != digest([latest['data']['categories'], latest['data']['forGroups']]):
            changed = list(state['resources'])
        self._reset(state, changed)

    def _assignment(self, state, rid, assignment):
        guidance = state['classificationGuidance']
        if not any(t['approvedBy'] for t in guidance['terms']):
            raise ImprovementError('Review and approve office definitions before assigning classification research')
        snapshot = state['researchSnapshots'][rid]
        if state.get('latestSha256'):
            with self.store.connect() as connection:
                latest = self._package(connection, state['latestSha256'])
            validate_guidance(guidance, latest['data'], state['office'])
            assignment['categories'] = deepcopy(latest['data']['categories'])
        assignment['researchPackageSha256'] = state['latestSha256'] or state['baseSha256']
        kind = assignment['stage'].split(':')[0]
        contract = {self.result_schema_key: 1, 'resourceId': rid, 'assignmentSha256': 'copy from assignment',
                    'evidenceSources': [{'url': 'https://official-source.example/', 'accessedOn': 'YYYY-MM-DD', 'excerpt': 'exact supporting source text'}],
                    'attachmentAccess': [{'path': p, 'sha256': sha, 'mode': 'not-inspected', 'note': 'Describe actual access; bytes-inspected, supplied-observation, or not-inspected'} for p, sha in snapshot['attachmentHashes'].items()]}
        if kind == 'audit':
            contract.update(findings=[{'id': 'finding-1', 'field': 'forGroups', 'severity': 'material',
                                      'summary': 'Issue and useful correction; return an empty findings array if none'}],
                            researchNotes='What was independently checked')
        else:
            contract.update(categories=[], categoryFilters={}, forGroups=[],
                decisions=[{'field': 'categories', 'categoryId': '', 'value': 'exact catalog ID or label',
                            'status': 'supported', 'relation': None, 'program': 'Specific service',
                            'definitionVersion': guidance['version'], 'source': 'https://source.example/ or original-package',
                            'excerpt': 'Supporting text', 'evidenceDate': None, 'reason': 'Why the definition applies'}],
                emptyReasons={f: 'Explain if this field is empty; otherwise empty string' for f in FIELDS},
                taxonomyProposals=[], migrationProposals=[], reviewNotes=[])
            if kind == 'reconcile':
                contract['resolutions'] = [{'findingId': 'researcher:finding-1', 'status': 'resolved',
                                            'reason': 'How addressed; use needs-review for unresolved findings'}]
        assignment['optionalProposalFormats'] = {
            'taxonomyProposals': {'term': 'Suggested term', 'definition': 'Proposed meaning',
                                 'examples': 'Concrete examples', 'overlap': 'Compare existing terms', 'reason': 'Practical need'},
            'migrationProposals': {'categoryId': 'Existing category ID', 'replacement': 'Proposed service categories and groups',
                                   'reason': 'Why a separate complete migration review is needed'},
        }
        assignment.pop('writingGuidance', None)
        assignment.update(resource=deepcopy(snapshot['resource']), attachmentHashes=deepcopy(snapshot['attachmentHashes']),
                          classificationGuidance=deepcopy(guidance), evidenceSha256=dependency(snapshot),
                          linkedEvidence=deepcopy(state.get('linkedEvidence', {}).get(rid, [])),
                          outputContract=contract)
        return assignment

    def submit(self, project_id, stage, result):
        # Validate PDF access for every stage, including audits, before the shared seal.
        if not isinstance(result, dict):
            raise ImprovementError('Result must be an object')
        with self.store.connect() as connection:
            state = self._load(connection, project_id)
            item = state['resources'].get(result.get('resourceId')) if isinstance(result.get('resourceId'), str) else None
            assignment = item and item['assignments'].get(stage)
            if not assignment:
                raise ImprovementError('Assign this research stage before submitting its result')
            access = result.get('attachmentAccess')
            if not isinstance(access, list):
                raise ImprovementError('attachmentAccess must be an array')
            seen = set()
            for a in access:
                if not isinstance(a, dict) or set(a) != {'path', 'sha256', 'mode', 'note'} or not isinstance(a['path'], str):
                    raise ImprovementError('Malformed attachment access')
                if a['path'] in seen or assignment['attachmentHashes'].get(a['path']) != a['sha256'] or a['mode'] not in ('bytes-inspected', 'supplied-observation', 'not-inspected'):
                    raise ImprovementError('Attachment access does not match assigned bytes')
                seen.add(a['path']); nonempty(a['note'], 'Attachment access note')
            if seen != set(assignment['attachmentHashes']):
                raise ImprovementError('Report access to every assigned attachment')
        return super().submit(project_id, stage, result)

    def _proposal(self, state, result, assignment):
        proposal = {f: deepcopy(result[f]) for f in FIELDS}
        proposed = memberships(proposal)
        original = memberships(assignment['resource'])
        terms = {(t['field'], t['categoryId'], t['value']): t for t in state['classificationGuidance']['terms']}
        if proposed - set(terms) - original:
            raise ImprovementError('Unknown taxonomy term; propose it separately')
        for field, cid, _ in proposed:
            if field == 'categoryFilters' and ('categories', '', cid) not in proposed:
                raise ImprovementError('Types must belong to an assigned category')
        decisions = result['decisions']
        if not isinstance(decisions, list):
            raise ImprovementError('decisions must be an array')
        seen = set()
        for d in decisions:
            if not isinstance(d, dict) or set(d) != {'field', 'categoryId', 'value', 'status', 'relation', 'program', 'definitionVersion', 'source', 'excerpt', 'evidenceDate', 'reason'}:
                raise ImprovementError('Malformed classification decision')
            key = (d['field'], d['categoryId'], d['value'])
            if any(not isinstance(k, str) for k in key) or key in seen or key not in (original | proposed):
                raise ImprovementError('Duplicate or unrelated classification decision')
            seen.add(key)
            if d['status'] not in ('supported', 'unconfirmed', 'remove') or type(d['definitionVersion']) is not int or d['definitionVersion'] != state['classificationGuidance']['version']:
                raise ImprovementError('Invalid decision status or definition version')
            nonempty(d['reason'], 'Decision reason')
            if any(not isinstance(d[key], str) for key in ('program', 'source', 'excerpt')):
                raise ImprovementError('Program, source and excerpt must be text')
            if d['status'] == 'unconfirmed':
                if key not in original or key not in proposed:
                    raise ImprovementError('Unconfirmed human membership must be retained')
            elif not terms.get(key, {}).get('approvedBy'):
                raise ImprovementError('Dependent assignment needs an approved definition')
            if d['status'] == 'remove':
                if key not in original or key in proposed:
                    raise ImprovementError('Removal must explicitly remove an existing membership')
                if terms[key]['populationCategory']:
                    raise ImprovementError('Population category removal requires the complete migration review')
            elif key not in proposed:
                raise ImprovementError('Retained decision must appear in classifications')
            if d['status'] != 'unconfirmed':
                nonempty(d['program'], 'Specific program'); nonempty(d['excerpt'], 'Supporting text')
                if d['source'] == 'original-package':
                    if d['excerpt'] not in json.dumps(assignment['resource'], ensure_ascii=False):
                        raise ImprovementError('Original-package excerpt must occur in the source record')
                elif isinstance(d['source'], str) and d['source'].startswith('linked-evidence:'):
                    sha = d['source'][len('linked-evidence:'):]
                    if not any(e['sha256'] == sha and d['excerpt'] in json.dumps(e['content'], ensure_ascii=False) for e in assignment['linkedEvidence']):
                        raise ImprovementError('Linked evidence excerpt must occur in the sealed input')
                elif isinstance(d['source'], str) and d['source'].startswith('attachment:'):
                    path = d['source'][len('attachment:'):]
                    if not any(a['path'] == path and a['mode'] == 'bytes-inspected' for a in result['attachmentAccess']):
                        raise ImprovementError('Attachment evidence requires actual inspection of assigned bytes')
                elif not any(s['url'] == d['source'] and d['excerpt'] in s['excerpt'] for s in result['evidenceSources']):
                    raise ImprovementError('Decision must reference supporting evidenceSources text')
                if d['field'] == 'forGroups' and d['status'] == 'supported' and d['relation'] not in ('targets', 'accommodates'):
                    raise ImprovementError('Supported group needs targets or accommodates')
            if d['field'] != 'forGroups' and d['relation'] is not None:
                raise ImprovementError('Only groups have a targeting or accommodation relation')
            if d['evidenceDate'] is not None:
                try: date.fromisoformat(d['evidenceDate'])
                except (ValueError, TypeError): raise ImprovementError('Evidence date must be YYYY-MM-DD or null')
        if seen != original | proposed:
            raise ImprovementError('Explain every proposed and prior membership exactly once')
        if not isinstance(result['emptyReasons'], dict) or set(result['emptyReasons']) != set(FIELDS):
            raise ImprovementError('Give emptyReasons for all classification fields')
        for field in FIELDS:
            if not isinstance(result['emptyReasons'][field], str):
                raise ImprovementError('Empty reasons must be text')
            if not any(t[0] == field for t in proposed):
                nonempty(result['emptyReasons'][field], 'Reason no classification is needed')
        for name in ('taxonomyProposals', 'migrationProposals'):
            if not isinstance(result[name], list):
                raise ImprovementError(f'{name} must be an array')
            for suggestion in result[name]:
                keys = {'term', 'definition', 'examples', 'overlap', 'reason'} if name == 'taxonomyProposals' else {'categoryId', 'replacement', 'reason'}
                if not isinstance(suggestion, dict) or set(suggestion) != keys:
                    raise ImprovementError(f'Malformed {name} entry')
                for value in suggestion.values(): nonempty(value, 'Proposal explanation')
        _notes(result['reviewNotes'], 'reviewNotes')
        proposal.update({k: deepcopy(result[k]) for k in ('decisions', 'emptyReasons', 'taxonomyProposals', 'migrationProposals', 'reviewNotes')})
        proposal.update(comparisonBase={f: deepcopy(assignment['resource'].get(f, {} if f == 'categoryFilters' else [])) for f in FIELDS},
                        humanEdited=False, sourceResultSha256=digest(result),
                        guidanceSha256=digest(state['classificationGuidance']), evidenceSha256=assignment['evidenceSha256'])
        return proposal

    def _ready(self, state, rid, base, latest, selected=None):
        guidance = state['classificationGuidance']
        validate_guidance(guidance, latest['data'], state['office'])
        item = state['resources'][rid]
        if not item['proposal']:
            raise ImprovementError('Complete classification research and reconciliation before review')
        if item['proposal']['guidanceSha256'] != digest(guidance) or item['proposal']['evidenceSha256'] != dependency(state['researchSnapshots'][rid]):
            raise ImprovementError('Classification evidence or definitions changed; research again')
        if selected is not None:
            proposed = memberships(selected)
            current = memberships(latest['resources'][rid])
            terms = catalog(latest['data'])
            if proposed - set(terms) - current:
                raise ImprovementError('Unknown term in merged classification')
            inactive = {c['id'] for c in latest['data']['categories'] if c.get('active') is False}
            if any((field == 'categories' and value in inactive) or (field == 'categoryFilters' and cid in inactive) for field, cid, value in proposed - current):
                raise ImprovementError('Do not add classifications to inactive categories')
            for field, cid, value in proposed:
                if field == 'categoryFilters' and ('categories', '', cid) not in proposed:
                    raise ImprovementError('Merged classification has Types without their category; resolve the category/Type conflict')
            for term in guidance['terms']:
                key = (term['field'], term['categoryId'], term['value'])
                if term['populationCategory'] and key in current and key not in proposed:
                    raise ImprovementError('Population category removal requires the complete migration review')
            # Pending taxonomy deletion requests cannot be undone by a classification update.
            for deletion in latest['data'].get('deletions', []) + latest['data'].get('deletionRequests', []):
                if not isinstance(deletion, dict): continue
                if deletion.get('kind') == 'category' and ('categories', '', deletion.get('targetId')) in proposed:
                    raise ImprovementError('Classification references a category with a deletion record or request')
                if deletion.get('kind') == 'forGroup' and any(t[0] == 'forGroups' and t[2].casefold() == str(deletion.get('label', '')).casefold() for t in proposed):
                    raise ImprovementError('Classification references a group with a deletion record or request')
                if deletion.get('kind') == 'type' and any(t[0] == 'categoryFilters' and t[1] == deletion.get('categoryId') and t[2].casefold() == str(deletion.get('label', '')).casefold() for t in proposed):
                    raise ImprovementError('Classification references a Type with a deletion record or request')

    def edit(self, project_id, revision, rid, proposal, reviewer):
        reviewer = nonempty(reviewer, 'Reviewer')
        with self.store.connect() as connection:
            state = self._checked(connection, project_id, revision)
            item = state['resources'].get(rid)
            if not item or not item['proposal'] or item['packaged']:
                raise ImprovementError('No editable reconciled proposal')
            result = deepcopy(item['results']['reconcile'])
            allowed = set(FIELDS) | {'decisions', 'emptyReasons', 'taxonomyProposals', 'migrationProposals', 'reviewNotes', 'evidenceSources'}
            if not isinstance(proposal, dict) or set(proposal) != allowed:
                raise ImprovementError('Edit exactly the classification proposal and evidence fields')
            result.update(proposal)
            from .scout_improvement import _sources
            _sources(result['evidenceSources'])
            before = deepcopy(item['proposal'])
            assignment = deepcopy(item['assignments']['reconcile'])
            assignment['resource'] = deepcopy(state['researchSnapshots'][rid]['resource'])
            item['proposal'] = self._proposal(state, result, assignment)
            item['proposal'].update(humanEdited=True, sourceResultSha256=digest(item['results']['reconcile']),
                                    humanEditSha256=digest(result), evidenceSources=deepcopy(result['evidenceSources']))
            item['review'] = None
            self._save(connection, state, 'classification-edited', {'resourceId': rid, 'reviewer': reviewer, 'before': before, 'after': item['proposal']})
            return self._view(connection, state)

    def _view(self, connection, state):
        view = super()._view(connection, state)
        latest = self._package(connection, state['latestSha256'] or state['baseSha256'])
        view.update(kind=self.kind, guidance=deepcopy(state['classificationGuidance']),
                    currentCatalogDraft=draft_guidance(latest['data'], state['office']),
                    guidanceSha256=digest(state['classificationGuidance']))
        for row in view['resources']:
            if row['proposal'] and row['current']:
                proposed = row['proposal']
                editable = {k: deepcopy(proposed[k]) for k in ('emptyReasons', 'taxonomyProposals', 'migrationProposals', 'reviewNotes')}
                editable.update({f: deepcopy(row['fields'][f]['proposed']) for f in FIELDS})
                editable['evidenceSources'] = deepcopy(proposed.get('evidenceSources', row['evidence']['reconcile']['evidenceSources']))
                old_decisions = {(d['field'], d['categoryId'], d['value']): d for d in proposed['decisions']}
                editable['decisions'] = []
                for key in sorted(memberships(row['current']) | memberships(editable)):
                    decision = old_decisions.get(key)
                    if decision is None:
                        field, category_id, value = key
                        decision = {'field': field, 'categoryId': category_id, 'value': value, 'status': 'unconfirmed',
                                    'relation': None, 'program': '', 'definitionVersion': state['classificationGuidance']['version'],
                                    'source': 'original-package', 'excerpt': '', 'evidenceDate': None,
                                    'reason': 'Later office assignment retained without independent confirmation.'}
                    editable['decisions'].append(deepcopy(decision))
                row['editableProposal'] = editable
            row['linkedEvidence'] = deepcopy(state.get('linkedEvidence', {}).get(row['id'], []))
            row['previousResearchRuns'] = len(state['resources'][row['id']].get('previousResearch', []))
        return view
