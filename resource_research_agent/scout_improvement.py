"""Durable, reviewed writing proposals for existing office package resources."""
from __future__ import annotations

import json
from .project_state import decode_project_state, encode_project_state
from copy import deepcopy
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

from .codex_first_research import load_researcher_roster
from .improvement_packages import (
    EDITABLE_FIELDS, ImprovementError, compare_fields, digest, materialize,
    next_timestamp, nonempty, read_package, resource_blocked, utcnow, write_package,
)
from .resource_writing import compose_information, load_writing_guidance
from .storage import ResearchStore
from .performance import measured

POLICY_PATH = Path(__file__).with_name('writing_guidance') / 'existing_resources.json'
SCHEMA = """
CREATE TABLE IF NOT EXISTS scout_improvement_packages (
 sha256 TEXT PRIMARY KEY, payload BLOB NOT NULL
);
CREATE TABLE IF NOT EXISTS scout_improvement_projects (
 id INTEGER PRIMARY KEY, project_key TEXT NOT NULL UNIQUE,
 revision INTEGER NOT NULL, state_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS scout_improvement_events (
 id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL REFERENCES scout_improvement_projects(id),
 created_at TEXT NOT NULL, action TEXT NOT NULL, detail_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS scout_improvement_exports (
 id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL REFERENCES scout_improvement_projects(id),
 export_key TEXT NOT NULL UNIQUE, manifest_json TEXT NOT NULL, payload BLOB NOT NULL,
 acknowledged_at TEXT
);
"""


def _sources(value):
    if not isinstance(value, list):
        raise ImprovementError('evidenceSources must be an array')
    for source in value:
        if not isinstance(source, dict) or set(source) != {'url', 'accessedOn', 'excerpt'}:
            raise ImprovementError('Sources need url, accessedOn, and excerpt')
        for key in source:
            nonempty(source[key], key)
        parsed = urlsplit(source['url'])
        if parsed.scheme not in ('http', 'https') or not parsed.netloc:
            raise ImprovementError('Evidence URL must use HTTP(S)')
        try:
            date.fromisoformat(source['accessedOn'])
        except ValueError as error:
            raise ImprovementError('Evidence access date must be YYYY-MM-DD') from error
    return deepcopy(value)


def _notes(value, label):
    if not isinstance(value, list) or any(not isinstance(n, str) or not n.strip() for n in value):
        raise ImprovementError(f'{label} must be an array of nonempty notes')
    return deepcopy(value)


class ImprovementWorkflow:
    kind = 'writing'
    editable_fields = EDITABLE_FIELDS
    result_schema_key = 'scoutImprovementResultSchemaVersion'
    change_description = 'Reviewed Description and Information improvements'
    compare_fields = staticmethod(compare_fields)
    materialize = staticmethod(materialize)

    def _assignment(self, state, rid, assignment):
        return assignment

    def _connected(self, state, latest):
        pass

    def _ready(self, state, rid, base, latest, selected=None):
        pass

    def _proposal(self, state, result, assignment):
        nonempty(result['description'], 'Description')
        information = compose_information(result['informationSections'], state['writingGuidance'])
        _notes(result['preservationNotes'], 'preservationNotes')
        _notes(result['reviewNotes'], 'reviewNotes')
        return {'description': result['description'], 'informationText': information,
                'informationSections': deepcopy(result['informationSections']),
                'humanEdited': False, 'sourceResultSha256': digest(result)}

    def __init__(self, store: ResearchStore):
        self.store = store
        with store.connect() as connection:
            connection.executescript(SCHEMA)

    def _load(self, connection, project_id):
        with measured('checkpoint.database_read'):
            row = connection.execute('SELECT * FROM scout_improvement_projects WHERE id=?', (project_id,)).fetchone()
        if row is None:
            raise ImprovementError('Improvement project not found')
        state = decode_project_state(row['state_json'])
        if state.get('kind', 'writing') != self.kind:
            raise ImprovementError('Project belongs to a different workflow')
        state.update(id=row['id'], revision=row['revision'])
        return state

    def _package(self, connection, sha):
        row = connection.execute('SELECT payload FROM scout_improvement_packages WHERE sha256=?', (sha,)).fetchone()
        if row is None:
            raise ImprovementError('Package snapshot is missing')
        return read_package(row['payload'])

    def _save(self, connection, state, action, details):
        revision = state.pop('revision')
        project_id = state.pop('id')
        encoded = encode_project_state(state)
        with measured('checkpoint.database_write') as metrics:
            connection.execute('UPDATE scout_improvement_projects SET revision=?, state_json=? WHERE id=?',
                               (revision + 1, encoded, project_id))
            metrics['characters'] = len(encoded)
        connection.execute('INSERT INTO scout_improvement_events(project_id,created_at,action,detail_json) VALUES(?,?,?,?)',
                           (project_id, utcnow(), action, json.dumps(details, ensure_ascii=False)))
        state.update(id=project_id, revision=revision + 1)

    def _checked(self, connection, project_id, revision):
        connection.execute('BEGIN IMMEDIATE')
        state = self._load(connection, project_id)
        if type(revision) is not int or state['revision'] != revision:
            raise ImprovementError('This review changed in another window. Reload before continuing.')
        return state

    @staticmethod
    def _office(package, office):
        embedded = package['data'].get('officeName')
        if embedded and str(embedded).strip().casefold() != office.casefold():
            raise ImprovementError('Package office does not match the selected office')

    def prepare(self, payload: bytes, office: str, resource_ids: list[str], *, source_name='resource-package.zip', historical=False):
        return self._prepare(payload, office, resource_ids, source_name=source_name, historical=historical)

    def _prepare(self, payload, office, resource_ids, *, source_name, historical, configuration=None):
        office = nonempty(office, 'Office identity')
        package = read_package(payload)
        self._office(package, office)
        if (not isinstance(resource_ids, list) or not resource_ids
                or any(not isinstance(rid, str) or rid not in package['resources'] for rid in resource_ids)
                or len(resource_ids) != len(set(resource_ids))):
            raise ImprovementError('Select unique existing resource IDs from the package')
        configuration = configuration or {}
        guidance = configuration.get('writingGuidance', {}) if configuration else load_writing_guidance()
        roster = load_researcher_roster()
        policy = configuration.get('policy') or json.loads(POLICY_PATH.read_text(encoding='utf-8'))
        if policy.get('schemaVersion') != 1 or any(not policy.get(k) for k in ('primary', 'audit', 'reconcile')):
            raise ImprovementError('Invalid existing-resource policy')
        for rid in resource_ids:
            if message := resource_blocked(package, rid):
                raise ImprovementError(message)
        identity = {'office': office, 'source': package['sha256'], 'ids': resource_ids,
                    'guidance': guidance, 'roster': roster, 'policy': policy, 'historical': bool(historical)}
        if self.kind != 'writing':
            identity.update(kind=self.kind, configuration=configuration)
        key = digest(identity)
        with self.store.connect() as connection:
            connection.execute('BEGIN IMMEDIATE')
            old = connection.execute('SELECT id FROM scout_improvement_projects WHERE project_key=?', (key,)).fetchone()
            if old:
                project_id = old['id']
            else:
                state = {**deepcopy(configuration), 'kind': self.kind, 'office': office, 'createdAt': utcnow(), 'baseSha256': package['sha256'],
                         'sourceName': source_name, 'historical': bool(historical), 'latestSha256': None,
                         'writingGuidance': guidance, 'researcherRoster': roster, 'policy': policy,
                         'resources': {rid: {'assignments': {}, 'results': {}, 'proposal': None,
                                            'review': None, 'packaged': False} for rid in resource_ids}}
                connection.execute('INSERT OR IGNORE INTO scout_improvement_packages VALUES(?,?)', (package['sha256'], payload))
                cursor = connection.execute('INSERT INTO scout_improvement_projects(project_key, revision, state_json) VALUES(?,0,?)',
                                            (key, encode_project_state(state)))
                project_id = cursor.lastrowid
                connection.execute('INSERT INTO scout_improvement_events(project_id,created_at,action,detail_json) VALUES(?,?,?,?)',
                                   (project_id, utcnow(), 'created', json.dumps({'baseSha256': package['sha256'], 'resourceIds': resource_ids, 'historical': bool(historical)})))
        return self.view(project_id)

    def list_projects(self):
        with self.store.connect() as connection:
            projects = []
            for row in connection.execute('SELECT id,state_json FROM scout_improvement_projects ORDER BY id DESC'):
                state = decode_project_state(row['state_json'])
                if state.get('kind', 'writing') == self.kind:
                    projects.append({'id': row['id'], 'office': state['office']})
            return projects

    @staticmethod
    def _stages(state):
        roster = state['researcherRoster']['researchers']
        primary = next(r['name'] for r in roster if r['role'] == 'primary')
        return [('primary', primary)] + [('audit:' + r['name'], r['name']) for r in roster if r['role'] == 'challenger'] + [('reconcile', primary)]

    def next_assignment(self, project_id, *, researcher=None, resource_id=None):
        with self.store.connect() as connection:
            connection.execute('BEGIN IMMEDIATE')
            state = self._load(connection, project_id)
            base = self._package(connection, state['baseSha256'])
            stages = self._stages(state)
            if resource_id is not None and resource_id not in state['resources']:
                raise ImprovementError('Resource is not selected for this project')
            for rid, item in state['resources'].items():
                if resource_id is not None and rid != resource_id:
                    continue
                for stage, name in stages:
                    if stage in item['results']:
                        continue
                    if stage != 'primary' and 'primary' not in item['results']:
                        continue
                    if stage == 'reconcile' and any(s not in item['results'] for s, _ in stages[:-1]):
                        continue
                    if researcher and researcher != name:
                        continue
                    if stage in item['assignments']:
                        return deepcopy(item['assignments'][stage])
                    kind = stage.split(':')[0]
                    result_contract = {
                        'scoutImprovementResultSchemaVersion': 1, 'resourceId': rid,
                        'assignmentSha256': 'copy from assignment',
                        'evidenceSources': [{'url': 'https://official-source.example/', 'accessedOn': 'YYYY-MM-DD', 'excerpt': 'source text'}],
                    }
                    if kind == 'audit':
                        result_contract.update(findings=[{'id': 'finding-1', 'field': 'informationText', 'severity': 'material', 'summary': 'Issue and useful correction'}], researchNotes='What was independently checked')
                    else:
                        result_contract.update(description='Proposed Description', informationSections={s['key']: 'Section body' for s in state['writingGuidance'].get('sections', [])}, preservationNotes=['Consequential details retained or qualified'], reviewNotes=[])
                        if kind == 'reconcile':
                            result_contract['resolutions'] = [{'findingId': 'researcher:finding-1', 'status': 'resolved', 'reason': 'How it was addressed'}]
                    original = deepcopy(base['resources'][rid])
                    assignment = {'assignmentVersion': state['policy']['version'], 'projectId': project_id,
                                  'resourceId': rid, 'stage': stage, 'researcher': name, 'office': state['office'],
                                  'historicalDevelopmentOnly': state['historical'], 'baseSha256': state['baseSha256'],
                                  'resource': original, 'categories': deepcopy(base['data']['categories']),
                                  'attachmentHashes': {p['path']: base['assetHashes'][p['path']] for p in original.get('pdfs', [])},
                                  'writingGuidance': deepcopy(state['writingGuidance']),
                                  'instructions': deepcopy(state['policy'][kind]), 'outputContract': result_contract}
                    if kind != 'primary':
                        assignment['primaryResult'] = deepcopy(item['results']['primary'])
                    if kind == 'reconcile':
                        assignment['audits'] = {s.split(':', 1)[1]: deepcopy(item['results'][s]) for s, _ in stages if s.startswith('audit:')}
                    assignment = self._assignment(state, rid, assignment)
                    assignment['assignmentSha256'] = digest(assignment)
                    item['assignments'][stage] = assignment
                    self._save(connection, state, 'assigned', {'resourceId': rid, 'stage': stage, 'assignment': assignment})
                    return deepcopy(assignment)
        return None

    def submit(self, project_id, stage, result):
        if not isinstance(result, dict):
            raise ImprovementError('Result must be an object')
        rid = nonempty(result.get('resourceId'), 'Result resource ID')
        stage = nonempty(stage, 'Research stage')
        with self.store.connect() as connection:
            connection.execute('BEGIN IMMEDIATE')
            state = self._load(connection, project_id)
            item = state['resources'].get(rid)
            if item is None or stage not in item['assignments']:
                raise ImprovementError('Assign this research stage before submitting its result')
            assignment = item['assignments'][stage]
            if (type(result.get(self.result_schema_key)) is not int
                    or result[self.result_schema_key] != 1
                    or result.get('assignmentSha256') != assignment['assignmentSha256']):
                raise ImprovementError('Result does not match its sealed assignment')
            if stage in item['results']:
                if item['results'][stage] != result:
                    raise ImprovementError('This stage is already sealed; its earlier result cannot be overwritten')
                return self._view(connection, state)
            if set(result) != set(assignment['outputContract']):
                raise ImprovementError('Return exactly the fields in the assigned output contract')
            _sources(result['evidenceSources'])
            if stage.startswith('audit:'):
                nonempty(result['researchNotes'], 'Independent research notes')
                findings = result['findings']
                if not isinstance(findings, list):
                    raise ImprovementError('Audit findings must be an array')
                seen = set()
                for finding in findings:
                    if not isinstance(finding, dict) or set(finding) != {'id', 'field', 'severity', 'summary'}:
                        raise ImprovementError('Malformed audit finding')
                    fid = nonempty(finding['id'], 'Finding ID')
                    nonempty(finding['summary'], 'Finding summary')
                    if fid in seen or finding['field'] not in self.editable_fields or finding['severity'] not in ('material', 'editorial'):
                        raise ImprovementError('Invalid or duplicate audit finding')
                    seen.add(fid)
            else:
                proposal = self._proposal(state, result, assignment)
                if stage == 'reconcile':
                    findings = self._findings(item)
                    resolutions = result['resolutions']
                    if not isinstance(resolutions, list) or len(resolutions) != len(findings):
                        raise ImprovementError('Reconciliation must address every finding exactly once')
                    seen = set()
                    for resolution in resolutions:
                        if not isinstance(resolution, dict) or set(resolution) != {'findingId', 'status', 'reason'}:
                            raise ImprovementError('Malformed finding resolution')
                        fid = nonempty(resolution['findingId'], 'Resolution finding ID')
                        if fid not in findings or fid in seen or resolution['status'] not in ('resolved', 'needs-review'):
                            raise ImprovementError('Invalid or duplicate finding resolution')
                        nonempty(resolution['reason'], 'Resolution reason')
                        seen.add(fid)
                    item['proposal'] = proposal
            item['results'][stage] = deepcopy(result)
            self._save(connection, state, 'result-sealed', {'resourceId': rid, 'stage': stage, 'result': result})
            return self._view(connection, state)

    @staticmethod
    def _findings(item):
        return {stage.split(':', 1)[1] + ':' + finding['id']: finding
                for stage, result in item['results'].items() if stage.startswith('audit:')
                for finding in result['findings']}

    def _capture_intake(self, connection, state, payload):
        """Record the user's project connection atomically, before reviews reset."""
        from .learning_evidence import EvidenceLedger
        ledger = EvidenceLedger(self.store, connection=connection)
        collection = 'project-intake:' + str(state['id'])
        previous_sha = state['latestSha256'] or state['baseSha256']
        previous = connection.execute('SELECT payload FROM scout_improvement_packages WHERE sha256=?',
                                      (previous_sha,)).fetchone()[0]
        kwargs = dict(scope='unknown', historical=bool(state['historical']),
                      office_confirmation='Office explicitly selected and confirmed in project ' + str(state['id']))
        before = ledger.import_package(collection, state['office'], previous, **kwargs)
        after = ledger.import_package(collection, state['office'], payload, **kwargs)
        capture = ledger.capture_project(collection, state['id'])
        comparison = ledger.compare(before['id'], after['id'], reviewer='Project package connection',
            lineage_note='User connected this package to this project. Previous connected package, or project baseline, supplies the comparison. Completeness and provider verification are not inferred.',
            captures=[capture['id']])
        report = ledger.report(comparison['id'])
        state['intakeEvidence'] = {'comparisonId': comparison['id'], **report['summary']}

    def connect_latest(self, project_id, revision, payload, office, *, source_name='current-package.zip'):
        latest = read_package(payload)
        office = nonempty(office, 'Confirmed office')
        with self.store.connect() as connection:
            state = self._checked(connection, project_id, revision)
            if state['office'].casefold() != office.casefold():
                raise ImprovementError('Latest package is for another office')
            self._office(latest, office)
            previous = self._package(connection, state['latestSha256'] or state['baseSha256'])
            if latest['data']['packageVersion'] < previous['data']['packageVersion']:
                raise ImprovementError('This package version is older than the connected baseline')
            if state['latestSha256'] == latest['sha256'] and not state.get('requiresReconnection'):
                return self._view(connection, state)
            connection.execute('INSERT OR IGNORE INTO scout_improvement_packages VALUES(?,?)', (latest['sha256'], payload))
            self._capture_intake(connection, state, payload)
            self._connected(state, latest)
            state['latestSha256'] = latest['sha256']
            state['requiresReconnection'] = False
            state['latestSourceName'] = source_name
            for item in state['resources'].values():
                if item['review'] and item['review']['decision'] == 'curated':
                    item['review'] = None
            self._save(connection, state, 'latest-connected', {'sha256': latest['sha256'], 'office': office, 'sourceName': source_name,
                                                              'previousSha256': previous['sha256']})
            return self._view(connection, state)

    def edit(self, project_id, revision, rid, description, sections, reviewer):
        reviewer = nonempty(reviewer, 'Reviewer name')
        rid = nonempty(rid, 'Resource ID')
        with self.store.connect() as connection:
            state = self._checked(connection, project_id, revision)
            item = state['resources'].get(rid)
            if not item or not item['proposal'] or item['packaged']:
                raise ImprovementError('No editable reconciled proposal')
            previous = deepcopy(item['proposal'])
            item['proposal'].update(description=nonempty(description, 'Description'),
                                    informationSections=deepcopy(sections),
                                    informationText=compose_information(sections, state['writingGuidance']), humanEdited=True)
            item['review'] = None
            self._save(connection, state, 'proposal-edited', {'resourceId': rid, 'reviewer': reviewer,
                                                             'before': previous, 'after': item['proposal']})
            return self._view(connection, state)

    def review(self, project_id, revision, rid, decision, choices, reviewer, note='', finding_notes=None):
        reviewer = nonempty(reviewer, 'Reviewer name')
        rid = nonempty(rid, 'Resource ID')
        if decision not in ('curated', 'declined', 'unmarked'):
            raise ImprovementError('Unknown review decision')
        with self.store.connect() as connection:
            state = self._checked(connection, project_id, revision)
            item = state['resources'].get(rid)
            if not item or not item['proposal'] or item['packaged']:
                raise ImprovementError('No reviewable reconciled proposal')
            if not isinstance(note, str):
                raise ImprovementError('Review note must be text')
            finding_notes = finding_notes or {}
            if not isinstance(finding_notes, dict):
                raise ImprovementError('Finding notes must be an object')
            if decision == 'curated':
                if not state['latestSha256'] or state.get('requiresReconnection'):
                    raise ImprovementError('Reconnect the current office package before curating updates')
                latest = self._package(connection, state['latestSha256'])
                if message := resource_blocked(latest, rid):
                    raise ImprovementError(message)
                base = self._package(connection, state['baseSha256'])
                comparison = self.compare_fields(base['resources'][rid], latest['resources'][rid], item['proposal'])
                selected = self.materialize(base['resources'][rid], latest['resources'][rid], item['proposal'], choices)
                self._ready(state, rid, base, latest, selected)
                if selected == latest['resources'][rid]:
                    raise ImprovementError('No changes selected. Decline changes or clear the mark instead.')
                if any(f['conflict'] for f in comparison.values()) and not note.strip():
                    raise ImprovementError('Explain your choice for the conflicting office edits')
                findings = self._findings(item)
                for resolution in item['results']['reconcile']['resolutions']:
                    fid = resolution['findingId']
                    if resolution['status'] == 'needs-review' and findings[fid]['severity'] == 'material':
                        nonempty(finding_notes.get(fid), f'Human resolution for {fid}')
            item['review'] = None if decision == 'unmarked' else {
                'decision': decision, 'choices': deepcopy(choices), 'reviewer': reviewer,
                'note': note, 'findingNotes': deepcopy(finding_notes), 'reviewedAt': utcnow(),
                'latestSha256': state['latestSha256'], 'proposalSha256': digest(item['proposal'])}
            self._save(connection, state, 'reviewed', {'resourceId': rid, 'review': item['review'], 'reviewer': reviewer})
            return self._view(connection, state)

    def _view(self, connection, state):
        base = self._package(connection, state['baseSha256'])
        latest = self._package(connection, state['latestSha256']) if state['latestSha256'] else None
        result = {k: deepcopy(state[k]) for k in ('id', 'revision', 'office', 'createdAt', 'baseSha256', 'latestSha256', 'sourceName', 'historical')}
        result['intakeEvidence'] = deepcopy(state.get('intakeEvidence'))
        result.update(baseVersion=base['data']['packageVersion'], latestVersion=latest['data']['packageVersion'] if latest else None,
                      requiresReconnection=bool(state.get('requiresReconnection')),
                      sections=deepcopy(state['writingGuidance'].get('sections', [])), resources=[])
        stages = self._stages(state)
        for rid, item in state['resources'].items():
            current = (latest or base)['resources'].get(rid)
            row = {'id': rid, 'original': deepcopy(base['resources'][rid]), 'current': deepcopy(current),
                   'proposal': deepcopy(item['proposal']), 'review': deepcopy(item['review']), 'packaged': item['packaged'],
                   'research': [{'stage': s, 'researcher': n, 'completed': s in item['results'], 'assigned': s in item['assignments']} for s, n in stages],
                   'findings': self._findings(item), 'evidence': deepcopy(item['results']),
                   'blocked': resource_blocked(latest, rid) if latest and not state.get('requiresReconnection') else 'Reconnect the current office package before curating or exporting updates.'}
            row['fields'] = self.compare_fields(base['resources'][rid], current, item['proposal']) if current and item['proposal'] else {}
            try:
                self._ready(state, rid, base, latest or base)
            except ImprovementError as error:
                row['blocked'] = str(error)
            result['resources'].append(row)
        return result

    def view(self, project_id):
        with self.store.connect() as connection:
            return self._view(connection, self._load(connection, project_id))

    def prepare_question_export(self, project_id, revision):
        from .question_handoff import prepare_question_export
        return prepare_question_export(self, project_id, revision)

    def prepare_export(self, project_id, revision):
        with self.store.connect() as connection:
            state = self._checked(connection, project_id, revision)
            if not state['latestSha256'] or state.get('requiresReconnection'):
                raise ImprovementError('Reconnect the latest office package before export')
            latest = self._package(connection, state['latestSha256'])
            base = self._package(connection, state['baseSha256'])
            selected = {rid: item for rid, item in state['resources'].items()
                        if not item['packaged'] and item['review'] and item['review']['decision'] == 'curated'}
            if not selected:
                raise ImprovementError('No curated updates to export')
            manifest = {'projectId': project_id, 'baseSha256': state['baseSha256'], 'latestSha256': state['latestSha256'],
                        'historicalDevelopmentOnly': state['historical'], 'resources': {}}
            resources = []
            for rid, item in selected.items():
                review = item['review']
                if review['latestSha256'] != state['latestSha256'] or review['proposalSha256'] != digest(item['proposal']):
                    raise ImprovementError('Review is stale; review the current proposal again')
                if message := resource_blocked(latest, rid):
                    raise ImprovementError(message)
                current = latest['resources'][rid]
                updated = self.materialize(base['resources'][rid], current, item['proposal'], review['choices'])
                self._ready(state, rid, base, latest, updated)
                if updated == current:
                    continue
                from .open_questions import attach_questions, improvement_questions
                attach_questions(updated, improvement_questions(item, {"kind":self.kind, "projectId":project_id, "resourceId":rid}))
                resources.append(updated)
                manifest['resources'][rid] = {'baseResourceSha256': digest(base['resources'][rid]),
                                             'latestResourceSha256': digest(current), 'proposal': deepcopy(item['proposal']),
                                             'review': deepcopy(review), 'assignmentHashes': {s: a['assignmentSha256'] for s, a in item['assignments'].items()}}
            if not resources:
                raise ImprovementError('The curated selection has no remaining changes to export')
            export_key = digest(manifest)
            previous = connection.execute('SELECT id,manifest_json FROM scout_improvement_exports WHERE export_key=?', (export_key,)).fetchone()
            if previous:
                return {'exportId': previous['id'], 'manifest': json.loads(previous['manifest_json'])}
            timestamp = next_timestamp(resources)
            exported = deepcopy(latest['data'])
            versions = [json.loads(row['manifest_json'])['packageVersion'] for row in connection.execute(
                'SELECT manifest_json FROM scout_improvement_exports WHERE project_id=?', (project_id,))]
            version = max([exported['packageVersion'], base['data']['packageVersion'], *versions]) + 1
            exported.update(resources=resources, packageVersion=version, packageCreatedAt=timestamp, lastModified=timestamp)
            changes = exported.setdefault('changes', [])
            assets = {}
            for resource in resources:
                rid = resource['id']
                resource['lastModified'] = timestamp
                changes.append({'id': f'scout-{"improvement" if self.kind == "writing" else self.kind}:{project_id}:{rid}:{export_key[:16]}', 'type': 'resource',
                                'action': 'updated', 'targetId': rid, 'targetName': resource.get('name', ''),
                                'description': self.change_description, 'timestamp': timestamp,
                                'categoryIds': deepcopy(resource.get('categories', []))})
                for pdf in resource.get('pdfs', []):
                    assets[pdf['path']] = latest['assets'][pdf['path']]
                manifest['resources'][rid]['exportedResourceSha256'] = digest(resource)
            payload = write_package(exported, assets)
            package = read_package(payload)
            manifest.update(exportKey=export_key, packageVersion=version, createdAt=timestamp,
                            packageSha256=package['sha256'], assetHashes=package['assetHashes'])
            cursor = connection.execute('INSERT INTO scout_improvement_exports(project_id,export_key,manifest_json,payload) VALUES(?,?,?,?)',
                                        (project_id, export_key, json.dumps(manifest, ensure_ascii=False), payload))
            export_id = cursor.lastrowid
            self._save(connection, state, 'export-prepared', {'exportId': export_id, 'manifest': manifest})
            return {'exportId': export_id, 'manifest': manifest, 'revision': state['revision']}

    def export_bytes(self, project_id, export_id):
        with self.store.connect() as connection:
            self._load(connection, project_id)
            row = connection.execute('SELECT payload FROM scout_improvement_exports WHERE id=? AND project_id=?', (export_id, project_id)).fetchone()
            if not row:
                raise ImprovementError('Export not found')
            return bytes(row['payload'])

    def attachment_bytes(self, project_id, path, *, which='base'):
        if which not in ('base', 'latest'):
            raise ImprovementError('Choose the original or latest package attachment')
        with self.store.connect() as connection:
            state = self._load(connection, project_id)
            sha = state['baseSha256'] if which == 'base' else state['latestSha256']
            if not sha:
                raise ImprovementError('No latest package connected')
            package = self._package(connection, sha)
            if path not in package['assets']:
                raise ImprovementError('Attachment not found in this package snapshot')
            return package['assets'][path]

    def acknowledge_export(self, project_id, revision, export_id, package_sha256):
        with self.store.connect() as connection:
            state = self._checked(connection, project_id, revision)
            row = connection.execute('SELECT * FROM scout_improvement_exports WHERE id=? AND project_id=?', (export_id, project_id)).fetchone()
            if not row:
                raise ImprovementError('Export not found')
            manifest = json.loads(row['manifest_json'])
            if manifest['packageSha256'] != package_sha256 or manifest['latestSha256'] != state['latestSha256']:
                raise ImprovementError('Saved export does not match the connected package')
            if row['acknowledged_at']:
                return self._view(connection, state)
            if manifest.get('questionHandoffOnly'):
                from .question_handoff import acknowledge_question_export
                return acknowledge_question_export(self, connection, state, manifest, export_id)
            for rid, record in manifest['resources'].items():
                item = state['resources'][rid]
                if item['review'] != record['review'] or item['proposal'] != record['proposal']:
                    raise ImprovementError('Review changed after export. Keep the revised review and discard the stale export.')
            for rid in manifest['resources']:
                state['resources'][rid]['packaged'] = True
            state['requiresReconnection'] = True
            connection.execute('UPDATE scout_improvement_exports SET acknowledged_at=? WHERE id=?', (utcnow(), export_id))
            self._save(connection, state, 'export-saved', {'exportId': export_id, 'packageSha256': package_sha256})
            return self._view(connection, state)

    def events(self, project_id):
        with self.store.connect() as connection:
            self._load(connection, project_id)
            return [{'id': row['id'], 'createdAt': row['created_at'], 'action': row['action'], 'details': json.loads(row['detail_json'])}
                    for row in connection.execute('SELECT * FROM scout_improvement_events WHERE project_id=? ORDER BY id', (project_id,))]
