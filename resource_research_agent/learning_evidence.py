"""Immutable evidence capture; never edits office data or infers active lessons."""
from __future__ import annotations

import json
import hashlib
from pathlib import Path
from copy import deepcopy
from datetime import datetime

from .improvement_packages import ImprovementError, digest, nonempty, read_package, utcnow
from .scout_improvement import ImprovementWorkflow

SCHEMA = '''
CREATE TABLE IF NOT EXISTS scout_evidence_collections (
 id TEXT PRIMARY KEY, office TEXT NOT NULL, historical INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS scout_evidence_artifacts (
 id TEXT PRIMARY KEY, payload BLOB NOT NULL
);
CREATE TABLE IF NOT EXISTS scout_evidence_records (
 id TEXT PRIMARY KEY, collection_id TEXT NOT NULL REFERENCES scout_evidence_collections(id),
 kind TEXT NOT NULL, created_at TEXT NOT NULL, document TEXT NOT NULL
);
'''
METADATA = {'lastModified', 'packageVersion', 'packageCreatedAt'}


def comparable(value, field=''):
    """Normalize only known set-valued fields, never prose or unknown lists."""
    if field in ('categories', 'forGroups') and isinstance(value, list):
        return sorted({digest(v): v for v in value}.values(), key=digest)
    if field == 'categoryFilters' and isinstance(value, dict):
        return {k: comparable(v, 'forGroups') for k, v in value.items()}
    return value


def catalog_value(data, field):
    value = data.get(field, [])
    if not isinstance(value, list):
        return value
    if field == 'categories':
        value = [{k: (sorted(v, key=digest) if k == 'filters' and isinstance(v, list) else v)
                  for k, v in item.items() if k not in METADATA} if isinstance(item, dict) else item
                 for item in value]
    return sorted(value, key=digest)


def semantic(package):
    return {'resources': {rid: {k: comparable(v, k) for k, v in r.items() if k not in METADATA}
                          for rid, r in package['resources'].items()},
            'catalog': {k: catalog_value(package['data'], k) for k in ('categories', 'forGroups', 'categoryMigrations')},
            'assets': package['assetHashes'],
            'deletions': sorted(package['data'].get('deletions', []), key=digest),
            'deletionRequests': sorted(package['data'].get('deletionRequests', []), key=digest)}


class EvidenceLedger:
    def __init__(self, store):
        self.store = store
        ImprovementWorkflow(store)  # Reuse existing storage, never its mutation methods.
        with store.connect() as c:
            c.executescript(SCHEMA)

    @staticmethod
    def _collection(c, ident):
        row = c.execute('SELECT * FROM scout_evidence_collections WHERE id=?', (ident,)).fetchone()
        if not row:
            raise ImprovementError('Unknown evidence collection')
        return dict(row)

    @staticmethod
    def _get(c, ident, kind=None):
        row = c.execute('SELECT * FROM scout_evidence_records WHERE id=?', (ident,)).fetchone()
        if not row or (kind and row['kind'] != kind):
            raise ImprovementError('Evidence record not found or wrong kind')
        return {'id': row['id'], 'collectionId': row['collection_id'], 'kind': row['kind'], 'recordedAt': row['created_at'],
                **json.loads(row['document'])}

    @staticmethod
    def _save(c, collection, kind, document):
        key = digest({'collection': collection, 'kind': kind, 'document': document})
        c.execute('INSERT OR IGNORE INTO scout_evidence_records VALUES(?,?,?,?,?)',
                  (key, collection, kind, utcnow(), json.dumps(document, ensure_ascii=False)))
        return key

    @staticmethod
    def _artifact(c, payload):
        package = read_package(payload, evidence_legacy_version=True)
        c.execute('INSERT OR IGNORE INTO scout_evidence_artifacts VALUES(?,?)', (package['sha256'], payload))
        return package

    @staticmethod
    def _package(c, sha):
        row = c.execute('SELECT payload FROM scout_evidence_artifacts WHERE id=?', (sha,)).fetchone()
        if not row:
            raise ImprovementError('Evidence package bytes are missing')
        return read_package(row[0], evidence_legacy_version=True)

    def import_package(self, collection, office, payload, *, scope, historical=False):
        collection, office = nonempty(collection, 'Collection'), nonempty(office, 'Office')
        if scope not in ('full', 'partial', 'unknown') or type(historical) is not bool:
            raise ImprovementError('Declare package scope and development status')
        package = read_package(payload, evidence_legacy_version=True)
        if package['data'].get('officeName', '').casefold() != office.casefold():
            raise ImprovementError('Package office does not match collection office')
        with self.store.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            c.execute('INSERT OR IGNORE INTO scout_evidence_collections VALUES(?,?,?)',
                      (collection, office.casefold(), historical))
            config = self._collection(c, collection)
            if config['office'] != office.casefold() or bool(config['historical']) != historical:
                raise ImprovementError('Collection office/development status cannot change')
            self._artifact(c, payload)
            ident = self._save(c, collection, 'package', {'sha256': package['sha256'],
                'semanticSha256': digest(semantic(package)), 'scope': scope,
                'packageVersion': package['data'].get('packageVersion'), 'historical': historical,
                'intakeWarnings': (['Legacy packageVersion is text; original value and ZIP bytes retained.']
                                   if isinstance(package['data'].get('packageVersion'), str) else [])})
            return self._get(c, ident)

    def capture_project(self, collection, project_id):
        """Copy raw history and receipts, retaining policy versions and source bytes."""
        with self.store.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            config = self._collection(c, collection)
            row = c.execute('SELECT * FROM scout_improvement_projects WHERE id=?', (project_id,)).fetchone()
            if not row:
                raise ImprovementError('Research project not found')
            state = json.loads(row['state_json'])
            if state['office'].casefold() != config['office'] or bool(state['historical']) != bool(config['historical']):
                raise ImprovementError('Project office/development status does not match collection')
            events = [dict(r) for r in c.execute('SELECT * FROM scout_improvement_events WHERE project_id=? ORDER BY id', (project_id,))]
            exports = []
            for exported in c.execute('SELECT * FROM scout_improvement_exports WHERE project_id=? ORDER BY id', (project_id,)).fetchall():
                manifest = json.loads(exported['manifest_json'])
                self._artifact(c, exported['payload'])
                exports.append({'id': exported['id'], 'manifest': manifest, 'acknowledgedAt': exported['acknowledged_at']})
            for sha in {state['baseSha256'], state.get('latestSha256')} - {None}:
                payload = c.execute('SELECT payload FROM scout_improvement_packages WHERE sha256=?', (sha,)).fetchone()
                if not payload:
                    raise ImprovementError('Research baseline bytes are missing')
                self._artifact(c, payload[0])
            ident = self._save(c, collection, 'project', {'projectId': project_id, 'revision': row['revision'],
                'state': state, 'events': events, 'exports': exports})
            return self._get(c, ident)

    def record_manual_proposal(self, collection, baseline_id, *, resource_id, fields, artifact, configuration):
        """Link a delivered read-only report, without fabricating review or vetting."""
        if not isinstance(fields, dict) or not fields or any(k in METADATA or k in ('id', 'verifiedOn') for k in fields):
            raise ImprovementError('Provide proposed resource fields, not identity or verification metadata')
        if not isinstance(configuration, dict) or not configuration:
            raise ImprovementError('Record the research/guidance configuration')
        if not isinstance(artifact, dict) or set(artifact) != {'path', 'sha256', 'deliveredAt'}:
            raise ImprovementError('Record delivered report path, hash and delivery time')
        for key in artifact:
            nonempty(artifact[key], key)
        try:
            timestamp = datetime.fromisoformat(artifact['deliveredAt'].replace('Z', '+00:00'))
            if timestamp.tzinfo is None:
                raise ValueError('Timezone required')
        except ValueError as error:
            raise ImprovementError('Delivery time must be an ISO timestamp with timezone') from error
        if len(artifact['sha256']) != 64 or any(ch not in '0123456789abcdef' for ch in artifact['sha256']):
            raise ImprovementError('Report hash must be SHA-256')
        artifact_bytes = Path(artifact['path']).read_bytes()
        if hashlib.sha256(artifact_bytes).hexdigest() != artifact['sha256']:
            raise ImprovementError('Delivered report bytes do not match the recorded hash')
        with self.store.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            base = self._get(c, baseline_id, 'package')
            if base['collectionId'] != collection:
                raise ImprovementError('Proposal baseline belongs to another collection')
            if resource_id not in self._package(c, base['sha256'])['resources']:
                raise ImprovementError('Manual proposal needs an existing stable resource ID')
            c.execute('INSERT OR IGNORE INTO scout_evidence_artifacts VALUES(?,?)', (artifact['sha256'], artifact_bytes))
            ident = self._save(c, collection, 'manual-proposal', {'baselineId': baseline_id,
                'resourceId': resource_id, 'fields': fields, 'artifact': artifact, 'configuration': configuration})
            return self._get(c, ident)

    def _candidates(self, c, collection, capture_ids):
        result = []
        selected = [self._get(c, ident) for ident in sorted(set(capture_ids))]
        projects = [r['projectId'] for r in selected if r['kind'] == 'project']
        if len(set(projects)) != len(projects):
            raise ImprovementError('Choose one applicable capture per project, not superseded captures together')
        for record in selected:
            if record['collectionId'] != collection:
                raise ImprovementError('Evidence source belongs to another collection')
            if record['kind'] == 'manual-proposal':
                base = self._get(c, record['baselineId'], 'package')
                result.append({'captureId': record['id'], 'resourceId': record['resourceId'],
                    'fields': record['fields'], 'baselineSha256': base['sha256'], 'delivered': True,
                    'review': None, 'configuration': record['configuration'], 'source': record['artifact']})
                continue
            if record['kind'] != 'project':
                raise ImprovementError('Select project captures or delivered manual proposals')
            state = record['state']
            # Project history includes superseded reviews; only an export receipt selects
            # a concrete proposal/review revision for adoption, never the newest timestamp.
            for export in record['exports']:
                m = export['manifest']
                out = self._package(c, m['packageSha256'])
                reviews = {r['review']['resourceId']: r['review'] for r in m.get('records', [])}
                reviews.update({rid: r['review'] for rid, r in m.get('resources', {}).items()})
                base = self._package(c, m['latestSha256'])
                for rid, review in reviews.items():
                    if review['decision'] not in ('accept', 'curated') or rid not in out['resources']:
                        continue
                    target = out['resources'][rid]
                    fields = {k: v for k, v in target.items() if k not in METADATA | {'id', 'verifiedOn'}
                              and (rid not in base['resources'] or base['resources'][rid].get(k) != v)}
                    result.append({'captureId': record['id'], 'exportId': export['id'], 'resourceId': rid,
                        'fields': fields, 'baselineSha256': m['latestSha256'], 'delivered': bool(export['acknowledgedAt']),
                        'review': review, 'reviewApplicability': 'At export time; not blanket or continuing approval', 'configuration': {k: state.get(k) for k in ('kind', 'policy', 'writingGuidance', 'researcherRoster')},
                        'source': {'projectId': record['projectId'], 'exportId': export['id']}})
        return result

    def compare(self, before_id, after_id, *, reviewer, lineage_note, captures=(), identity_links=()):
        reviewer, lineage_note = nonempty(reviewer, 'Lineage reviewer'), nonempty(lineage_note, 'Lineage explanation')
        with self.store.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            before, after = self._get(c, before_id, 'package'), self._get(c, after_id, 'package')
            if before['collectionId'] != after['collectionId']:
                raise ImprovementError('Compare packages in the same collection')
            collection = before['collectionId']
            old, new = self._package(c, before['sha256']), self._package(c, after['sha256'])
            left, right = old['resources'], new['resources']
            candidates = self._candidates(c, collection, captures)
            links = []
            used_old, used_new = set(), set()
            for link in identity_links:
                if set(link) != {'beforeIds', 'afterIds', 'reviewer', 'note'}:
                    raise ImprovementError('Identity links need IDs, reviewer and explanation')
                nonempty(link['reviewer'], 'Identity reviewer'); nonempty(link['note'], 'Identity explanation')
                a, b = link['beforeIds'], link['afterIds']
                if (not isinstance(a, list) or not isinstance(b, list) or not a or not b
                    or any(not isinstance(x, str) for x in a+b) or len(set(a)) != len(a) or len(set(b)) != len(b)
                    or not set(a) <= left.keys() or not set(b) <= right.keys()
                    or set(a) & used_old or set(b) & used_new):
                    raise ImprovementError('Identity links require existing, unambiguous IDs')
                used_old.update(a); used_new.update(b); links.append(deepcopy(link))
            events = []
            def add(rid, field, kind, old_present, new_present, old_value, new_value):
                event = {'resourceId': rid, 'field': field, 'change': kind,
                    'beforePresent': old_present, 'afterPresent': new_present,
                    'before': old_value, 'after': new_value, 'level': 'observed-change', 'proposalLinks': []}
                event['eventId'] = digest({'collection': collection, 'before': before['semanticSha256'],
                    'after': after['semanticSha256'], 'resourceId': rid, 'field': field, 'change': kind})
                if kind in ('field-change', 'addition') and new_present:
                    for candidate in candidates:
                        if candidate['resourceId'] != rid:
                            continue
                        baseline_records = self._package(c, candidate['baselineSha256'])['resources']
                        baseline = baseline_records.get(rid, {})
                        if kind == 'addition':
                            matches = (rid not in baseline_records and bool(candidate['fields'])
                                and all(k in new_value and comparable(v, k) == comparable(new_value[k], k)
                                        for k, v in candidate['fields'].items()))
                        else:
                            matches = (field in candidate['fields']
                                and comparable(candidate['fields'][field], field) == comparable(new_value, field)
                                and (field in baseline) == old_present
                                and comparable(baseline.get(field), field) == comparable(old_value, field))
                        if matches:
                            event['proposalLinks'].append(candidate)
                    delivered = [r for r in event['proposalLinks'] if r['delivered']]
                    # Retried exports of the same approved value are one proposal; distinct
                    # reviews/configurations remain ambiguous rather than pooled evidence.
                    distinct = {digest({k: r[k] for k in ('resourceId','fields','baselineSha256','review','configuration')}) for r in delivered}
                    if len(distinct) == 1:
                        event['level'] = 'linked-adoption'
                    elif len(distinct) > 1:
                        event['ambiguity'] = 'Multiple attributable proposals; select the applicable source.'
                if kind in ('absence', 'addition') and event['level'] == 'observed-change':
                    event['ambiguity'] = ('Absence does not establish deletion or closure.' if kind == 'absence'
                                          else 'Newly observed resource; author, timing and Scout omission are not inferred.')
                events.append(event)
            for rid in sorted(left.keys() | right.keys()):
                if rid not in left or rid not in right:
                    add(rid, '*', 'addition' if rid not in left else 'absence', rid in left, rid in right, left.get(rid), right.get(rid))
                    continue
                for field in sorted((left[rid].keys() | right[rid].keys()) - METADATA - {'id'}):
                    op, np = field in left[rid], field in right[rid]
                    ov, nv = left[rid].get(field), right[rid].get(field)
                    if op != np or comparable(ov, field) != comparable(nv, field):
                        add(rid, field, 'field-change', op, np, ov, nv)
            for field in ('categories', 'forGroups', 'categoryMigrations'):
                if catalog_value(old['data'], field) != catalog_value(new['data'], field):
                    add('@catalog', field, 'catalog-change', field in old['data'], field in new['data'], old['data'].get(field), new['data'].get(field))
            for field in ('deletions', 'deletionRequests'):
                for value in new['data'].get(field, []):
                    if value not in old['data'].get(field, []):
                        add(value.get('targetId', ''), field+':'+digest(value), 'explicit-history', False, True, None, value)
            for asset in sorted(old['assetHashes'].keys() | new['assetHashes'].keys()):
                ov, nv = old['assetHashes'].get(asset), new['assetHashes'].get(asset)
                if ov != nv:
                    add('@attachments', asset, 'attachment-change', ov is not None, nv is not None, ov, nv)
            document = {'beforeId': before_id, 'afterId': after_id, 'beforeScope': before['scope'],
                'afterScope': after['scope'], 'lineage': {'reviewer': reviewer, 'note': lineage_note},
                'captures': sorted(set(captures)), 'identityLinks': links, 'events': events,
                'historical': after['historical'], 'activeLessons': 0}
            ident = self._save(c, collection, 'comparison', document)
            return self._get(c, ident)

    def attest(self, comparison_id, event_id, *, reviewer, method, note, source, supersedes=None):
        """Explicit field-specific verification evidence; no inference from review text."""
        for key, value in [('Reviewer',reviewer),('Method',method),('Note',note),('Source',source)]:
            nonempty(value, key)
        if method not in ('phone', 'in-person', 'provider-written-confirmation'):
            raise ImprovementError('Record an explicit verification method, not editorial acceptance')
        with self.store.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            comp = self._get(c, comparison_id, 'comparison')
            event = next((e for e in comp['events'] if e['eventId'] == event_id), None)
            if not event or event['change'] != 'field-change' or not event['afterPresent'] or event['field'] == 'verifiedOn':
                raise ImprovementError('Verification must identify a particular present resource field')
            if supersedes:
                previous = self._get(c, supersedes, 'verification')
                if previous['collectionId'] != comp['collectionId'] or previous['eventId'] != event_id:
                    raise ImprovementError('Superseded verification must cover the same event')
            ident = self._save(c, comp['collectionId'], 'verification', {'comparisonId': comparison_id,
                'eventId': event_id, 'reviewer': reviewer, 'method': method, 'note': note, 'source': source,
                'supersedes': supersedes, 'historical': comp['historical'], 'field': event['field'],
                'resourceId': event['resourceId'], 'valueSha256': digest(event['after'])})
            return self._get(c, ident)

    def report(self, comparison_id):
        with self.store.connect() as c:
            comp = self._get(c, comparison_id, 'comparison')
            rows = [self._get(c, r[0]) for r in c.execute(
                "SELECT id FROM scout_evidence_records WHERE collection_id=? AND kind='verification'", (comp['collectionId'],))]
            superseded = {r['supersedes'] for r in rows if r['supersedes']}
            for event in comp['events']:
                evidence = [r for r in rows if r['eventId'] == event['eventId'] and r['id'] not in superseded]
                # Repeating the same sourced confirmation against an equivalent
                # metadata-only import is one confirmation, with all raw records retained.
                evidence = list({digest({k: r[k] for k in ('eventId','reviewer','method','note','source','valueSha256','supersedes')}): r for r in evidence}.values())
                event['verifications'] = evidence
                if len(evidence) == 1:
                    event['level'] = 'explicit-vetted-outcome'
                elif len(evidence) > 1:
                    event['verificationAmbiguity'] = 'Multiple verification records; resolve supersession explicitly.'
            comp['summary'] = {'observedChanges': len(comp['events']),
                'linkedAdoptions': sum(e['level'] == 'linked-adoption' for e in comp['events']),
                'explicitFieldVerifications': sum(e['level'] == 'explicit-vetted-outcome' for e in comp['events']),
                'resourceVettingInferred': 0, 'activeLessons': 0,
                'learningReadiness': 'Not evaluated; field evidence is not a terminal resource-vetting count.'}
            return comp
