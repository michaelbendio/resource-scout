"""Reviewed learning transitions and immutable, scoped guidance snapshots.

The database is the atomic manifest store. Distillation is an attributed editor
judgment, never an inference that a changed package means a provider was called.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from .improvement_packages import ImprovementError, digest, nonempty
from .performance import measured

ACTIVATION_SCHEMA = '''
CREATE TABLE IF NOT EXISTS scout_guidance_head (
 singleton INTEGER PRIMARY KEY CHECK(singleton=1), manifest_id TEXT NOT NULL
);
'''
ROOT = Path(__file__).resolve().parent.parent


def question_changes(event):
    """Describe administrative transitions, without interpreting answers as facts."""
    if event.get('field') != 'openQuestions':
        return []
    before = {q['id']: q for q in event.get('before') or []}
    after = {q['id']: q for q in event.get('after') or []}
    changes = []
    for ident in sorted(before.keys() | after.keys()):
        old, new = before.get(ident), after.get(ident)
        if old == new:
            continue
        label = ('removed-not-proof-of-resolution' if new is None else
                 'new-question' if old is None else
                 'reopened' if old.get('status') == 'resolved' and new.get('status') != 'resolved' else
                 'resolved' if old.get('status') != 'resolved' and new.get('status') == 'resolved' else
                 'answer-changed-review-for-conflict' if old.get('resolution') != new.get('resolution') else
                 'question-edited')
        changes.append({'questionId': ident, 'transition': label, 'before': old, 'after': new})
    return changes


class ActivationMixin:
    def _init_activation(self):
        with self.store.connect() as c:
            c.executescript(ACTIVATION_SCHEMA)
            c.execute('BEGIN IMMEDIATE')
            initial = self._record(c, 'guidance-manifest', {'version': 1, 'parent': None,
                'entries': [], 'action': 'initial', 'reviewId': None})
            c.execute('INSERT OR IGNORE INTO scout_guidance_head VALUES(1,?)', (initial,))

    def _head(self, c):
        ident = c.execute('SELECT manifest_id FROM scout_guidance_head WHERE singleton=1').fetchone()[0]
        return ident, self._get(c, ident, 'guidance-manifest')

    def manifest(self):
        with self.store.connect() as c:
            ident, doc = self._head(c)
            return {'manifestId': ident, **doc}

    def feedback_queue(self):
        self.collect_comparisons()
        groups = {}
        with self.store.connect() as c, measured('learning.feedback_queue'):
            rows = c.execute("SELECT id FROM scout_learning_records WHERE kind='observation' ORDER BY created_at,id").fetchall()
            reports, offices, editorial = {}, {}, {}
            observations = [(row[0], self._get(c, row[0], 'observation')) for row in rows]
            for ident, obs in observations:
                if obs.get('sourceClass') == 'ai-editorial-judgment' and obs.get('decision', {}).get('disposition') in ('exclude', 'reserve'):
                    source = obs.get('sourceSha256')
                    if source not in offices:
                        from .improvement_packages import read_package
                        offices[source] = read_package(self._bytes(c, source, 'resource-package'))['data'].get('officeName', '').casefold()
                    for rid in obs['resourceIds']:
                        editorial.setdefault((offices[source], rid), []).append(ident)
            for observation_id, obs in observations:
                event = obs.get('event', {})
                if event:
                    sha = obs['comparisonSha256']
                    if sha not in reports:
                        reports[sha] = json.loads(self._bytes(c, sha, 'package-comparison'))
                    report = reports[sha]
                    collection = report['collectionId']
                    office = c.execute('SELECT office FROM scout_evidence_collections WHERE id=?', (collection,)).fetchone()[0]
                    key = digest([collection, event['resourceId'], event['field']])
                    label = event['field']
                    scope = {'collectionId': collection, 'office': office, 'before': report['beforeScope'], 'after': report['afterScope']}
                    evidence_key = event['eventId']
                else:
                    collection = obs.get('sourceSha256') or obs.get('editorProjectId')
                    key = digest([collection, obs['resourceIds'], 'editorial'])
                    label, scope = 'editorial decision', {'source': collection}
                    evidence_key = digest({k: obs.get(k) for k in ('resourceIds', 'decision', 'editorProjectId', 'stage')})
                group = groups.setdefault(key, {'groupId': key, 'topic': label, 'scope': scope,
                    'resourceIds': obs['resourceIds'], 'observations': [], 'distinctEventCount': 0,
                    'independentConfirmations': 'Not inferred from package versions',
                    'cautions': ['Changed information can reflect a later provider change, an earlier miss, or an editor preference. Do not infer the cause.',
                                 'An answered question is potential learning; resolution alone is not proof of a provider call.']})
                group['observations'].append({'observationId': observation_id, 'evidenceKey': evidence_key,
                    'evidence': obs, 'questionChanges': question_changes(event)})
                if event.get('change') == 'absence':
                    group['cautions'] = ['Absence, including from a partial package, is not evidence of rejection or closure.']
                if event.get('change') == 'addition':
                    group['cautions'].append('Check prior editor exclusions by stable identity and lineage; this may be a restored useful resource, not a new provider.')
                    group['possibleEditorialReversals'] = editorial.get((office, event['resourceId']), [])
                    group['editorialReversalRequiresLineageReview'] = True
                if 'question' in label.lower():
                    group['cautions'].append('Compare question IDs, answers and history for resolution, reopening or disagreement; do not count versions as independent confirmations.')
            distilled = []
            for row in c.execute("SELECT id FROM scout_learning_records WHERE kind='distillation'"):
                distilled.append({'recordId': row[0], **self._get(c, row[0], 'distillation')})
        for group in groups.values():
            keys = {o['evidenceKey'] for o in group['observations']}
            group['distinctEventCount'] = len(keys)
            ids = {o['observationId'] for o in group['observations']}
            group['reviews'] = [d for d in distilled if ids.intersection(d['observationIds'])]
        return {'groups': list(groups.values()), 'instructions': [
            'Review related observations and their exact provenance. Several versions of one event are one observation, not several votes.',
            'Distinguish resource-fact updates, policy preferences and reusable research/editorial methods.',
            'Propose a concise method with supporting examples, an alternative explanation and a counterexample. Link contradictory evidence explicitly.',
            'Do not manufacture a rule for every resource. Human curators need no extra learning form.'],
            'providerVerificationInferred': False}

    def distill(self, document):
        from .learning_workbench import exact, texts
        exact(document, ('reviewer', 'observationIds', 'counterevidenceIds', 'kind', 'interpretation', 'proposal'), 'Distillation')
        nonempty(document['reviewer'], 'Distillation reviewer')
        nonempty(document['interpretation'], 'Interpretation')
        ids = texts(document['observationIds'], 'Observed evidence')
        counter = texts(document['counterevidenceIds'], 'Counterevidence', empty=True)
        if document['kind'] not in ('method', 'resource-fact', 'policy', 'unsettled'):
            raise ImprovementError('Distillation kind must distinguish methods, resource facts, policy and uncertainty')
        with self.store.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            for ident in ids + counter:
                self._get(c, ident, 'observation')
            proposal = document['proposal']
            if document['kind'] == 'method':
                if not isinstance(proposal, dict) or set(proposal.get('supportIds', [])) != set(ids):
                    raise ImprovementError('Method proposal must cite the exact observed examples')
                lesson = self.propose(proposal, _connection=c)['lessonId']
            else:
                if proposal is not None:
                    raise ImprovementError('Only method interpretations can propose playbook instructions')
                lesson = None
            ident = self._record(c, 'distillation', {**deepcopy(document), 'lessonId': lesson,
                                                   'providerVerificationInferred': False})
        return {'distillationId': ident, 'lessonId': lesson, 'active': False}

    def lesson_status(self, lesson_id):
        with self.store.connect() as c:
            self._get(c, lesson_id, 'lesson')
            _, manifest = self._head(c)
            if lesson_id in manifest['entries']:
                return 'active'
            reviews = [self._get(c, r[0], 'guidance-review') for r in c.execute(
                "SELECT id FROM scout_learning_records WHERE kind='guidance-review' ORDER BY rowid")]
            matching = [r for r in reviews if r['lessonId'] == lesson_id]
            if matching and matching[-1]['decision'] == 'reject':
                return 'rejected'
            for r in c.execute("SELECT id FROM scout_learning_records WHERE kind='guidance-manifest'"):
                if lesson_id in self._get(c, r[0], 'guidance-manifest')['entries']:
                    return 'superseded'
            trials = [r[0] for r in c.execute("SELECT id FROM scout_learning_records WHERE kind='trial'")
                      if self._get(c, r[0], 'trial')['lessonId'] == lesson_id]
            if any(c.execute('SELECT 1 FROM scout_learning_assessments WHERE trial_id=?', (t,)).fetchone() for t in trials):
                return 'evaluated'
            return 'experiment' if trials else 'proposed'

    def _check_evaluation(self, c, lesson_id, trial_ids):
        from .learning_workbench import texts
        lesson = self._get(c, lesson_id, 'lesson')
        scope = lesson['scope']
        if any(v == '*' for v in scope.values()):
            raise ImprovementError('Initial activation requires an exact office/category/stage scope')
        for ident in texts(trial_ids, 'Applicable trial IDs'):
            trial = self._get(c, ident, 'trial')
            if trial['lessonId'] != lesson_id:
                raise ImprovementError('Evaluation belongs to a different lesson')
            _, manifest = self._head(c)
            active_scope = [key for key in manifest['entries']
                            if {k: v.casefold() for k, v in self._get(c, key, 'lesson')['scope'].items()}
                            == {k: v.casefold() for k, v in scope.items()}]
            if sorted(active_scope) != sorted(trial.get('guidanceContext', {}).get('baselineLessonIds', [])):
                raise ImprovementError('Evaluation did not compare against the currently active amendment')
            row = c.execute('SELECT record_id FROM scout_learning_assessments WHERE trial_id=?', (ident,)).fetchone()
            assessment = self._get(c, row[0], 'assessment')['assessment'] if row else None
            if assessment is None or assessment['conclusion'] != 'promising':
                raise ImprovementError('Activation requires applicable promising evaluated evidence')
            for case in assessment['caseJudgments']:
                if any(case['candidate'][key] and not case['baseline'][key]
                       for key in ('criticalError', 'unsupportedPromise')):
                    raise ImprovementError('Resolve newly introduced critical errors or unsupported promises before activation')
            responses = self._responses(c, ident)
            if len(responses) != 2 or any(r['late'] or not r['result']['complete'] for r in responses.values()):
                raise ImprovementError('Incomplete or over-budget responses cannot authorize activation')
            from .improvement_packages import read_package
            package = read_package(self._bytes(c, trial['specification']['sourceSha256'], 'resource-package'))
            if package['data'].get('officeName', '').casefold() != scope['office'].casefold():
                raise ImprovementError('Evaluation office does not match activation scope')
            if any(scope['category'] not in package['resources'][case['resourceId']].get('categories', []) for case in trial['cases']):
                raise ImprovementError('Evaluation category does not match activation scope')
            if scope['stage'] == 'research' and not trial['specification'].get('researchProtocol'):
                raise ImprovementError('Saved-case interpretation alone cannot authorize research guidance')
        self._check_baseline(lesson)

    @staticmethod
    def _check_baseline(lesson):
        path = Path(lesson['baseline']['path'])
        path = path if path.is_absolute() else ROOT / path
        try:
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError as error:
            raise ImprovementError('Baseline guidance file is unavailable; re-evaluate before activation/use') from error
        if actual != lesson['baseline']['sha256']:
            raise ImprovementError('Baseline guidance changed; re-evaluate before activation/use')

    def review_guidance(self, lesson_id, document):
        from .learning_workbench import exact, texts
        exact(document, ('reviewer', 'decision', 'rationale', 'trialIds', 'supersedes'), 'Guidance review')
        for k in ('reviewer', 'rationale'):
            nonempty(document[k], k)
        if document['decision'] not in ('activate', 'reject', 'defer'):
            raise ImprovementError('Review decision must be activate, reject or defer')
        texts(document['trialIds'], 'Trial IDs', empty=True)
        texts(document['supersedes'], 'Superseded lesson IDs', empty=True)
        with self.store.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            self._get(c, lesson_id, 'lesson')
            head, manifest = self._head(c)
            if document['decision'] == 'activate':
                self._check_evaluation(c, lesson_id, document['trialIds'])
                for ident in document['supersedes']:
                    prior = self._get(c, ident, 'lesson')
                    target = self._get(c, lesson_id, 'lesson')
                    if {k: v.casefold() for k, v in prior['scope'].items()} != {k: v.casefold() for k, v in target['scope'].items()}:
                        raise ImprovementError('Superseded amendment must have the same scope')
                if not set(document['supersedes']) <= set(manifest['entries']):
                    raise ImprovementError('Supersede only currently active guidance')
            elif lesson_id in manifest['entries']:
                raise ImprovementError('Roll back active guidance before rejecting or deferring it')
            doc = {**deepcopy(document), 'lessonId': lesson_id, 'manifestId': head}
            previous = [(r[0], self._get(c, r[0], 'guidance-review')) for r in c.execute(
                "SELECT id FROM scout_learning_records WHERE kind='guidance-review' ORDER BY rowid")
                if self._get(c, r[0], 'guidance-review')['lessonId'] == lesson_id]
            if previous and {k: v for k, v in previous[-1][1].items() if k != 'previousReviewId'} == doc:
                return {'reviewId': previous[-1][0], 'decision': document['decision'],
                        'active': False, 'expectedManifestId': head}
            doc['previousReviewId'] = previous[-1][0] if previous else None
            ident = self._record(c, 'guidance-review', doc)
        return {'reviewId': ident, 'decision': document['decision'], 'active': False, 'expectedManifestId': head}

    def activate(self, review_id, expected_manifest_id):
        with self.store.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            review = self._get(c, review_id, 'guidance-review')
            head, manifest = self._head(c)
            if head != expected_manifest_id or head != review['manifestId']:
                raise ImprovementError('Active manifest changed; review the current manifest before activation')
            if review['decision'] != 'activate':
                raise ImprovementError('An explicit activation review is required')
            latest = [r[0] for r in c.execute("SELECT id FROM scout_learning_records WHERE kind='guidance-review' ORDER BY rowid")
                      if self._get(c, r[0], 'guidance-review')['lessonId'] == review['lessonId']]
            if latest[-1] != review_id:
                raise ImprovementError('This review was superseded by a later decision')
            self._check_evaluation(c, review['lessonId'], review['trialIds'])
            lesson = self._get(c, review['lessonId'], 'lesson')
            remaining = set(manifest['entries']) - set(review['supersedes'])
            scope = {k: v.casefold() for k, v in lesson['scope'].items()}
            for ident in remaining:
                other = self._get(c, ident, 'lesson')
                if {k: v.casefold() for k, v in other['scope'].items()} == scope:
                    raise ImprovementError('Conflicting active scope; explicitly review replacement of the existing amendment')
            entries = sorted(remaining | {review['lessonId']})
            new = self._record(c, 'guidance-manifest', {'version': 1, 'parent': head,
                'entries': entries, 'action': 'activate', 'reviewId': review_id})
            c.execute('UPDATE scout_guidance_head SET manifest_id=? WHERE singleton=1', (new,))
        return self.manifest()

    def rollback(self, target_id, *, expected_manifest_id, reviewer, reason):
        nonempty(reviewer, 'Rollback reviewer'); nonempty(reason, 'Rollback reason')
        with self.store.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            head, _ = self._head(c)
            if head != expected_manifest_id:
                raise ImprovementError('Active manifest changed; reload before rollback')
            ancestor = head
            while ancestor and ancestor != target_id:
                ancestor = self._get(c, ancestor, 'guidance-manifest')['parent']
            if ancestor is None or target_id == head:
                raise ImprovementError('Rollback must select an earlier manifest in this history')
            target = self._get(c, target_id, 'guidance-manifest')
            for ident in target['entries']:
                self._check_baseline(self._get(c, ident, 'lesson'))
                reviews = [self._get(c, r[0], 'guidance-review') for r in c.execute(
                    "SELECT id FROM scout_learning_records WHERE kind='guidance-review' ORDER BY rowid")
                    if self._get(c, r[0], 'guidance-review')['lessonId'] == ident]
                if reviews and reviews[-1]['decision'] != 'activate':
                    raise ImprovementError('Rollback would restore guidance with a later rejection or deferral')
            doc = {'version': 1, 'parent': head, 'entries': target['entries'], 'action': 'rollback',
                   'reviewId': None, 'targetManifestId': target_id, 'reviewer': reviewer, 'reason': reason}
            new = self._record(c, 'guidance-manifest', doc)
            c.execute('UPDATE scout_guidance_head SET manifest_id=? WHERE singleton=1', (new,))
        return self.manifest()

    def resolve_guidance(self, office, category_ids, stage):
        """Call only while preparing a new project; packets read their sealed copy."""
        with self.store.connect() as c:
            head, manifest = self._head(c)
            selected = []
            for ident in manifest['entries']:
                lesson = self._get(c, ident, 'lesson')
                scope = lesson['scope']
                if (scope['office'].casefold() == office.casefold() and scope['category'] in category_ids
                        and scope['stage'] == stage):
                    self._check_baseline(lesson)
                    selected.append({'lessonId': ident, 'scope': scope, 'addition': lesson['addition'],
                                     'baselineSha256': lesson['baseline']['sha256']})
        return {'manifestId': head, 'lessons': selected}
