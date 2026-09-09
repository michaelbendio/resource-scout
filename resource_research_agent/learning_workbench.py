"""Attributable lesson proposals and bounded paired trials.

Exact source artifacts and records are immutable. Task receipts are small rows;
the existing research project's growing checkpoint is never rewritten here.
"""
from copy import deepcopy
from contextlib import nullcontext
import hashlib
import json
import math
import time

from .improvement_packages import ImprovementError, digest, nonempty, read_package, utcnow
from .learning_evidence import EvidenceLedger
from .performance import measured
from .learning_activation import ActivationMixin

SCHEMA = '''
CREATE TABLE IF NOT EXISTS scout_learning_artifacts (
 sha256 TEXT PRIMARY KEY, kind TEXT NOT NULL, payload BLOB NOT NULL
);
CREATE TABLE IF NOT EXISTS scout_learning_records (
 id TEXT PRIMARY KEY, kind TEXT NOT NULL, created_at TEXT NOT NULL, document TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS scout_learning_trials (
 id TEXT PRIMARY KEY REFERENCES scout_learning_records(id), started_at REAL
);
CREATE TABLE IF NOT EXISTS scout_learning_runs (
 trial_id TEXT NOT NULL REFERENCES scout_learning_trials(id), arm TEXT NOT NULL,
 context_id TEXT NOT NULL UNIQUE, dispatched_at REAL NOT NULL,
 packet TEXT NOT NULL, reply_id TEXT REFERENCES scout_learning_records(id),
 PRIMARY KEY(trial_id,arm)
);
CREATE TABLE IF NOT EXISTS scout_learning_assessments (
 trial_id TEXT PRIMARY KEY REFERENCES scout_learning_trials(id),
 record_id TEXT NOT NULL REFERENCES scout_learning_records(id)
);
'''
ARMS = ('baseline', 'candidate')
DECISIONS = ('retain', 'reserve', 'exclude', 'needs-check')
METRICS = ('criticalError', 'missedUsefulResource', 'lostCriticalDetail', 'unsupportedPromise')


def exact(value, keys, label):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise ImprovementError(f'{label} requires exactly: {", ".join(keys)}')


def texts(value, label, *, empty=False):
    if not isinstance(value, list) or (not value and not empty):
        raise ImprovementError(f'{label} needs an array of text values')
    result = [nonempty(x, label) for x in value]
    if len(set(result)) != len(result):
        raise ImprovementError(f'{label} contains duplicate values')
    return result


class LearningWorkbench(ActivationMixin):
    def __init__(self, store, *, clock=None):
        self.store = store
        self.clock = clock or time.time
        with store.connect() as c:
            c.executescript(SCHEMA)
        self._init_activation()

    @staticmethod
    def _record(c, kind, document):
        ident = digest({'kind': kind, 'document': document})
        c.execute('INSERT OR IGNORE INTO scout_learning_records VALUES(?,?,?,?)',
                  (ident, kind, utcnow(), json.dumps(document, ensure_ascii=False, allow_nan=False)))
        return ident

    @staticmethod
    def _get(c, ident, kind=None):
        row = c.execute('SELECT * FROM scout_learning_records WHERE id=?', (ident,)).fetchone()
        if row is None or (kind and row['kind'] != kind):
            raise ImprovementError('Learning record is missing or has the wrong kind')
        document = json.loads(row['document'])
        if digest({'kind': row['kind'], 'document': document}) != ident:
            raise ImprovementError('Learning record hash mismatch')
        return document

    @staticmethod
    def _artifact(c, kind, payload):
        ident = hashlib.sha256(payload).hexdigest()
        prior = c.execute('SELECT kind,payload FROM scout_learning_artifacts WHERE sha256=?', (ident,)).fetchone()
        if prior and (prior['kind'] != kind or prior['payload'] != payload):
            raise ImprovementError('Conflicting learning artifact')
        c.execute('INSERT OR IGNORE INTO scout_learning_artifacts VALUES(?,?,?)', (ident, kind, payload))
        return ident

    @staticmethod
    def _bytes(c, ident, kind):
        row = c.execute('SELECT kind,payload FROM scout_learning_artifacts WHERE sha256=?', (ident,)).fetchone()
        if row is None or row['kind'] != kind or hashlib.sha256(row['payload']).hexdigest() != ident:
            raise ImprovementError('Learning source artifact is missing or changed')
        return row['payload']

    def register_package(self, payload):
        package = read_package(payload)
        with self.store.connect() as c:
            ident = self._artifact(c, 'resource-package', payload)
        return {'sourceSha256': ident, 'resources': len(package['resources']),
                'office': package['data'].get('officeName'), 'scope': 'unknown'}

    def import_editorial(self, package_bytes, ledger_bytes):
        package = read_package(package_bytes)
        ledger = json.loads(ledger_bytes)
        if ledger.get('formatVersion') != 1 or not isinstance(ledger.get('run'), dict):
            raise ImprovementError('Use editorial decision interchange format 1')
        run = ledger['run']
        if run.get('sourceSha256') != package['sha256']:
            raise ImprovementError('Editorial source package hash mismatch')
        decisions = ledger.get('decisions')
        if not isinstance(decisions, list):
            raise ImprovementError('Editorial decisions must be an array')
        ids = [d.get('resourceId') for d in decisions if isinstance(d, dict)]
        if len(ids) != len(decisions) or len(set(ids)) != len(ids) or set(ids) != set(package['resources']):
            raise ImprovementError('Account for every original resource exactly once')
        if run.get('sourceRecordCount') != len(ids):
            raise ImprovementError('Editorial source count mismatch')
        # First trial contract supports retained identities; additions/splits need
        # their own independently validated identity path, not silent inference.
        if ledger.get('newOutputResources') != []:
            raise ImprovementError('This editorial evidence importer requires no new/split output identities')
        retained = {d['resourceId'] for d in decisions if d.get('disposition') == 'retain'}
        for d in decisions:
            if d.get('disposition') not in ('retain', 'combine', 'reserve', 'exclude', 'unreviewed'):
                raise ImprovementError('Unknown editorial disposition')
            nonempty(d.get('reason'), 'Editorial reason')
            targets = texts(d.get('targetResourceIds'), 'Editorial targets', empty=True)
            if not set(targets) <= retained:
                raise ImprovementError('Combination target must be a retained output identity')
            if d['disposition'] == 'retain' and targets != [d['resourceId']]:
                raise ImprovementError('Retained identity must target itself')
            if d['disposition'] == 'combine' and not targets:
                raise ImprovementError('A combination needs a retained destination')
            if d['disposition'] in ('reserve', 'exclude', 'unreviewed') and targets:
                raise ImprovementError('Omitted resources cannot claim retained destinations')
        if ledger.get('output') and ledger['output'].get('finalUniqueResources') != len(retained):
            raise ImprovementError('Final editorial count mismatch')
        with self.store.connect() as c, measured('learning.editorial_import'):
            c.execute('BEGIN IMMEDIATE')
            source = self._artifact(c, 'resource-package', package_bytes)
            evidence = self._artifact(c, 'editorial-ledger', ledger_bytes)
            observations = []
            for d in decisions:
                observation = {'sourceClass': 'ai-editorial-judgment', 'sourceSha256': source,
                               'editorialSha256': evidence, 'resourceIds': [d['resourceId']],
                               'editor': run.get('editor'), 'configuration': deepcopy(run),
                               'decision': deepcopy(d), 'providerVerificationInferred': False}
                observations.append(self._record(c, 'observation', observation))
        return {'sourceSha256': source, 'editorialSha256': evidence,
                'observationIds': observations, 'count': len(observations), 'activeLessons': 0}

    def import_comparison(self, comparison_id):
        report = EvidenceLedger(self.store).report(comparison_id)
        with self.store.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            artifact = self._artifact(c, 'package-comparison', json.dumps(report, ensure_ascii=False, sort_keys=True).encode())
            ids = []
            for event in report['events']:
                # Keep the ledger's exact distinctions; never turn an observed
                # edit or answered question into an inferred provider call.
                obs = {'sourceClass': 'package-observation', 'comparisonId': comparison_id,
                       'comparisonSha256': artifact, 'resourceIds': [event['resourceId']] if event.get('resourceId') else [],
                       'event': deepcopy(event), 'providerVerificationInferred': False}
                ids.append(self._record(c, 'observation', obs))
        return {'observationIds': ids, 'count': len(ids), 'activeLessons': 0}

    def propose(self, document, *, _connection=None):
        exact(document, ('title', 'supportIds', 'scope', 'hypothesis', 'alternativeExplanation',
                         'counterexample', 'baseline', 'addition', 'evaluationQuestion'), 'Lesson proposal')
        proposal = deepcopy(document)
        proposal['supportIds'] = texts(proposal['supportIds'], 'Lesson support')
        for field in ('title', 'hypothesis', 'alternativeExplanation', 'counterexample', 'addition', 'evaluationQuestion'):
            nonempty(proposal[field], field)
        exact(proposal['scope'], ('office', 'category', 'stage'), 'Lesson scope')
        for value in proposal['scope'].values():
            nonempty(value, 'Scope value')
        if proposal['scope']['stage'] not in ('research', 'editorial'):
            raise ImprovementError('Lesson stage must be research or editorial')
        exact(proposal['baseline'], ('path', 'sha256', 'text'), 'Baseline guidance')
        nonempty(proposal['baseline']['path'], 'Guidance path')
        nonempty(proposal['baseline']['text'], 'Guidance text')
        if hashlib.sha256(proposal['baseline']['text'].encode()).hexdigest() != proposal['baseline']['sha256']:
            raise ImprovementError('Baseline guidance hash mismatch')
        with (nullcontext(_connection) if _connection is not None else self.store.connect()) as c:
            if _connection is None:
                c.execute('BEGIN IMMEDIATE')
            for support in proposal['supportIds']:
                self._get(c, support, 'observation')
            ident = self._record(c, 'lesson', proposal)
        return {'lessonId': ident, 'status': 'proposed', 'active': False}

    def prepare_trial(self, lesson_id, specification):
        protocol = specification.get('researchProtocol')
        if protocol is not None:
            exact(protocol, ('version', 'maxSourcePages', 'maxWebCalls'), 'Research protocol')
            if type(protocol['version']) is not int or protocol['version'] != 2 or any(type(protocol[k]) is not int or not 1 <= protocol[k] <= 80
                                              for k in ('maxSourcePages', 'maxWebCalls')):
                raise ImprovementError('Research protocol 2 needs bounded source and web allowances')
        exact(specification, ('name', 'operator', 'reason', 'modelConfig', 'sourceSha256',
                              'cases', 'maxAssignments', 'maxSeconds', 'evaluationBasis',
                              *(('researchProtocol',) if protocol is not None else ())), 'Trial specification')
        spec = deepcopy(specification)
        for k in ('name', 'operator', 'reason', 'evaluationBasis'):
            nonempty(spec[k], k)
        exact(spec['modelConfig'], ('provider', 'model', 'settings'), 'Model configuration')
        nonempty(spec['modelConfig']['provider'], 'Provider')
        if spec['modelConfig']['model'] is not None:
            nonempty(spec['modelConfig']['model'], 'Model')
        if not isinstance(spec['modelConfig']['settings'], dict):
            raise ImprovementError('Model settings must be an object')
        if type(spec['maxAssignments']) is not int or spec['maxAssignments'] != 2:
            raise ImprovementError('A paired trial permits exactly two original assignments; retries need a new named trial')
        if type(spec['maxSeconds']) is not int or not 1 <= spec['maxSeconds'] <= 3600:
            raise ImprovementError('Limited trial allowance must be 1–3600 seconds')
        if not isinstance(spec['cases'], list) or not 2 <= len(spec['cases']) <= 20:
            raise ImprovementError('A limited trial needs 2–20 cases')
        with self.store.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            lesson = self._get(c, lesson_id, 'lesson')
            if protocol and lesson['scope']['stage'] != 'research':
                raise ImprovementError('Live research trials require a research-stage proposal')
            package = read_package(self._bytes(c, spec['sourceSha256'], 'resource-package'))
            training = set()
            for support in lesson['supportIds']:
                training.update(self._get(c, support, 'observation')['resourceIds'])
            for row in c.execute("SELECT id FROM scout_learning_records WHERE kind='distillation'"):
                distillation = self._get(c, row[0], 'distillation')
                if distillation['lessonId'] == lesson_id:
                    for counter in distillation['counterevidenceIds']:
                        training.update(self._get(c, counter, 'observation')['resourceIds'])
            seen, resources, cases = set(), set(), []
            for case in spec['cases']:
                exact(case, ('caseId', 'resourceId'), 'Trial case')
                cid = nonempty(case['caseId'], 'Case ID')
                rid = nonempty(case['resourceId'], 'Resource ID')
                if cid in seen or rid in resources or rid not in package['resources'] or rid in training:
                    raise ImprovementError('Test cases must be unique existing resources, separate from lesson examples')
                seen.add(cid); resources.add(rid)
                original = package['resources'][rid]
                # Administrative questions/research/editor answers never enter
                # the respondent's packet. Exact public fields are preserved.
                cases.append({'caseId': cid, 'resourceId': rid, 'resource': {
                    k: deepcopy(original.get(k, '')) for k in
                    ('name', 'description', 'informationText', 'phone', 'address', 'website', 'hours')}})
                if protocol:
                    cases[-1]['resource'] = {k: deepcopy(original.get(k, '')) for k in ('name', 'website')}
            trial = {'lessonId': lesson_id, 'specification': spec, 'cases': cases,
                     'baselineGuidance': lesson['baseline']['text'],
                     'candidateGuidance': lesson['baseline']['text'] + '\n\n' + lesson['addition'],
                     'purpose': 'Saved-case interpretation experiment; not new discovery or human verification.'}
            head, active = self._head(c)
            scope = {k: v.casefold() for k, v in lesson['scope'].items()}
            current = [(ident, self._get(c, ident, 'lesson')) for ident in active['entries']]
            current = [(ident, item) for ident, item in current
                       if {k: v.casefold() for k, v in item['scope'].items()} == scope]
            if current:
                for _, item in current:
                    self._check_baseline(item)
                    if item['baseline']['sha256'] != lesson['baseline']['sha256']:
                        raise ImprovementError('Trial baseline differs from the active guidance baseline')
                trial['baselineGuidance'] += '\n\n' + '\n\n'.join(item['addition'] for _, item in current)
                trial['guidanceContext'] = {'manifestId': head, 'baselineLessonIds': [ident for ident, _ in current]}
            if protocol:
                trial['purpose'] = 'Bounded primary research from fresh leads; not human verification.'
            ident = self._record(c, 'trial', trial)
            c.execute('INSERT OR IGNORE INTO scout_learning_trials VALUES(?,NULL)', (ident,))
        return {'trialId': ident, 'status': 'approved-for-experiment', 'active': False,
                'caseCount': len(cases), 'maxAssignments': 2, 'maxSeconds': spec['maxSeconds']}

    def packet(self, trial_id, arm, context_id, *, fresh):
        if arm not in ARMS or fresh is not True:
            raise ImprovementError('Select a valid arm and attest a fresh isolated context')
        nonempty(context_id, 'Context identity')
        with self.store.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            trial = self._get(c, trial_id, 'trial')
            prior = c.execute('SELECT * FROM scout_learning_runs WHERE trial_id=? AND arm=?', (trial_id, arm)).fetchone()
            if prior:
                if prior['context_id'] != context_id:
                    raise ImprovementError('Assignment already belongs to a different context')
                return json.loads(prior['packet'])
            if c.execute('SELECT 1 FROM scout_learning_runs WHERE context_id=?', (context_id,)).fetchone():
                raise ImprovementError('Experiment arms require separate unused contexts')
            start = c.execute('SELECT started_at FROM scout_learning_trials WHERE id=?', (trial_id,)).fetchone()[0]
            now = self.clock()
            if start is not None and now - start > trial['specification']['maxSeconds']:
                raise ImprovementError('Trial time allowance exhausted; preserve work and prepare a new explicitly bounded trial')
            if start is None:
                c.execute('UPDATE scout_learning_trials SET started_at=? WHERE id=?', (now, trial_id))
            packet = {'schemaVersion': 1, 'trialId': trial_id, 'arm': arm,
                      'contextId': context_id, 'modelConfig': trial['specification']['modelConfig'],
                      'instructions': 'Assess each supplied resource for practical TSO usefulness using the supplied guidance. '
                      'Use only these saved facts; do not browse, use tools, contact anyone or read other chats. '
                      'Return JSON only with assignmentSha256, complete (boolean), and cases. Each case needs caseId, '
                      'decision (retain/reserve/exclude/needs-check), reason, criticalDetails (array of strings), '
                      'and openQuestions (array of strings). Account for every case. Preserve usable named referrals '
                      'and consequential eligibility, cost and timing details. Do not invent provider facts or human approval.',
                      'guidance': trial[arm + 'Guidance'], 'cases': trial['cases']}
            if trial['specification'].get('researchProtocol'):
                packet['schemaVersion'] = 2
                packet['researchProtocol'] = trial['specification']['researchProtocol']
                packet['scope'] = self._get(c, trial['lessonId'], 'lesson')['scope']
                packet['instructions'] = (
                    'Research each lead for practical TSO usefulness using the supplied guidance and public primary sources. '
                    'TSO service missionaries help people in need find practical services. '
                    'Use fresh source evidence; do not read other chats, local project files, or prior assessments. '
                    'Do not contact providers. Respect the supplied source-page and web-call ceilings across this assignment. '
                    'Return JSON only with assignmentSha256, complete (boolean), and cases. Each case needs caseId, '
                    'decision (retain/reserve/exclude/needs-check), reason, criticalDetails (array of strings), '
                    'and openQuestions (array of strings). Include supporting source URLs with the factual details. '
                    'Account for every case. Distinguish source facts from uncertainty; do not invent facts or human approval. '
                    'If evidence or time runs out, explain gaps in the affected cases.')
            packet['assignmentSha256'] = digest(packet)
            c.execute('INSERT INTO scout_learning_runs VALUES(?,?,?,?,?,NULL)',
                      (trial_id, arm, context_id, now, json.dumps(packet, ensure_ascii=False)))
        return packet

    def submit(self, trial_id, arm, raw, receipt):
        # Preserve the delivered bytes before parsing, including malformed or
        # rejected deliveries. This is evidence, not a completed response.
        if not isinstance(raw, str):
            raise ImprovementError('Response must be raw text')
        with self.store.connect() as c:
            self._get(c, trial_id, 'trial')
            if not c.execute('SELECT 1 FROM scout_learning_runs WHERE trial_id=? AND arm=?', (trial_id, arm)).fetchone():
                raise ImprovementError('Assignment has not been dispatched')
            self._record(c, 'trial-submission', {'trialId': trial_id, 'arm': arm, 'raw': raw, 'receiptText': json.dumps(receipt, ensure_ascii=False)})
        exact(receipt, ('contextId', 'fresh', 'modelConfig', 'incrementalCostUSD', 'interventions', 'notes'), 'Response receipt')
        if receipt['fresh'] is not True:
            raise ImprovementError('Response needs a fresh-context attestation')
        cost = receipt['incrementalCostUSD']
        if cost is not None and (type(cost) not in (int, float) or not math.isfinite(cost) or cost < 0):
            raise ImprovementError('Cost must be a nonnegative measured amount or null')
        if type(receipt['interventions']) is not int or receipt['interventions'] < 0:
            raise ImprovementError('Intervention count must be nonnegative')
        nonempty(receipt['notes'], 'Receipt notes')
        cleaned = raw.strip()
        if cleaned.startswith('```json\n') and cleaned.endswith('```'):
            cleaned = cleaned[8:-3].strip()
        try:
            result = json.loads(cleaned)
        except json.JSONDecodeError as error:
            raise ImprovementError('Response is not valid JSON; raw delivery was preserved') from error
        exact(result, ('assignmentSha256', 'complete', 'cases'), 'Trial response')
        if type(result['complete']) is not bool or not isinstance(result['cases'], list):
            raise ImprovementError('Response completeness and cases are required')
        with self.store.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            trial = self._get(c, trial_id, 'trial')
            row = c.execute('SELECT * FROM scout_learning_runs WHERE trial_id=? AND arm=?', (trial_id, arm)).fetchone()
            if row is None:
                raise ImprovementError('Assignment has not been dispatched')
            packet = json.loads(row['packet'])
            if digest({k: v for k, v in packet.items() if k != 'assignmentSha256'}) != packet['assignmentSha256']:
                raise ImprovementError('Stored assignment hash mismatch')
            if result['assignmentSha256'] != packet['assignmentSha256']:
                raise ImprovementError('Response assignment hash mismatch')
            if receipt['contextId'] != row['context_id'] or receipt['modelConfig'] != packet['modelConfig']:
                raise ImprovementError('Response context/model does not match sealed assignment')
            expected = {x['caseId'] for x in packet['cases']}
            seen = set()
            for item in result['cases']:
                exact(item, ('caseId', 'decision', 'reason', 'criticalDetails', 'openQuestions'), 'Case response')
                if item['caseId'] not in expected or item['caseId'] in seen or item['decision'] not in DECISIONS:
                    raise ImprovementError('Unknown/duplicate case or disposition')
                seen.add(item['caseId'])
                nonempty(item['reason'], 'Case reason')
                texts(item['criticalDetails'], 'Critical details', empty=True)
                texts(item['openQuestions'], 'Open questions', empty=True)
            if result['complete'] and seen != expected:
                raise ImprovementError('Complete response must account for every case')
            if row['reply_id']:
                prior = self._get(c, row['reply_id'], 'trial-response')
                if prior['raw'] == raw and prior['receipt'] == receipt:
                    return {'responseId': row['reply_id'], 'complete': result['complete'], 'late': prior['late']}
                raise ImprovementError('A saved response is immutable; use a new named trial for another attempt')
            now = self.clock()
            started = c.execute('SELECT started_at FROM scout_learning_trials WHERE id=?', (trial_id,)).fetchone()[0]
            record = {'trialId': trial_id, 'arm': arm, 'raw': raw, 'result': result,
                      'receipt': deepcopy(receipt), 'elapsedSeconds': max(0, now - row['dispatched_at']),
                      'trialElapsedSeconds': max(0, now - started),
                      'late': now - started > trial['specification']['maxSeconds']}
            ident = self._record(c, 'trial-response', record)
            c.execute('UPDATE scout_learning_runs SET reply_id=? WHERE trial_id=? AND arm=?', (ident, trial_id, arm))
        return {'responseId': ident, 'complete': result['complete'], 'late': record['late']}

    def assess(self, trial_id, assessment):
        exact(assessment, ('reviewer', 'method', 'caseJudgments', 'conclusion', 'limitations'), 'Assessment')
        for k in ('reviewer', 'method', 'limitations'):
            nonempty(assessment[k], k)
        if assessment['conclusion'] not in ('promising', 'no-clear-benefit', 'worse', 'inconclusive'):
            raise ImprovementError('Unknown assessment conclusion')
        with self.store.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            trial = self._get(c, trial_id, 'trial')
            responses = self._responses(c, trial_id)
            if set(responses) != set(ARMS) or any(not r['result']['complete'] for r in responses.values()):
                raise ImprovementError('Assess only after both complete responses are preserved')
            judgments = assessment['caseJudgments']
            if not isinstance(judgments, list):
                raise ImprovementError('Assessment needs case judgments')
            expected = {x['caseId'] for x in trial['cases']}
            seen = set()
            for case in judgments:
                exact(case, ('caseId', 'baseline', 'candidate', 'evidence'), 'Case assessment')
                if case['caseId'] in seen or case['caseId'] not in expected:
                    raise ImprovementError('Unknown or duplicate assessment case')
                seen.add(case['caseId']); nonempty(case['evidence'], 'Assessment evidence')
                for arm in ARMS:
                    exact(case[arm], (*METRICS, 'reason'), 'Arm assessment')
                    if any(type(case[arm][k]) is not bool for k in METRICS):
                        raise ImprovementError('Assessment metrics must be explicit booleans')
                    nonempty(case[arm]['reason'], 'Assessment reason')
            if seen != expected:
                raise ImprovementError('Assess every case, including favorable counterexamples')
            doc = {'trialId': trial_id, 'assessment': deepcopy(assessment),
                   'responseIds': {arm: digest({'kind': 'trial-response', 'document': r}) for arm, r in responses.items()},
                   'status': 'evaluated', 'active': False, 'providerVerificationInferred': False}
            ident = self._record(c, 'assessment', doc)
            prior = c.execute('SELECT record_id FROM scout_learning_assessments WHERE trial_id=?', (trial_id,)).fetchone()
            if prior and prior[0] != ident:
                raise ImprovementError('Assessment is immutable; preserve a new trial/evaluation rather than replacing history')
            c.execute('INSERT OR IGNORE INTO scout_learning_assessments VALUES(?,?)', (trial_id, ident))
        return self.report(trial_id)

    def _responses(self, c, trial_id):
        return {row['arm']: self._get(c, row['reply_id'], 'trial-response') for row in c.execute(
            'SELECT arm,reply_id FROM scout_learning_runs WHERE trial_id=? AND reply_id IS NOT NULL', (trial_id,))}

    def report(self, trial_id):
        with self.store.connect() as c:
            trial = self._get(c, trial_id, 'trial')
            responses = self._responses(c, trial_id)
            assessment_row = c.execute('SELECT record_id FROM scout_learning_assessments WHERE trial_id=?', (trial_id,)).fetchone()
            assessment = self._get(c, assessment_row[0], 'assessment') if assessment_row else None
            dispatches = c.execute('SELECT count(*) FROM scout_learning_runs WHERE trial_id=?', (trial_id,)).fetchone()[0]
        result = {'trialId': trial_id, 'lessonId': trial['lessonId'], 'name': trial['specification']['name'],
                  'status': 'evaluated' if assessment else 'awaiting-assessment' if len(responses) == 2 and all(x['result']['complete'] for x in responses.values()) else 'incomplete',
                  'active': self.lesson_status(trial['lessonId']) == 'active',
                  'lessonStatus': self.lesson_status(trial['lessonId']),
                  'caseCount': len(trial['cases']), 'dispatches': dispatches,
                  'modelConfig': trial['specification']['modelConfig'],
                  'responses': {arm: {'complete': r['result']['complete'], 'elapsedSeconds': r['elapsedSeconds'],
                                     'late': r['late'], 'incrementalCostUSD': r['receipt']['incrementalCostUSD'],
                                     'interventions': r['receipt']['interventions']} for arm, r in responses.items()},
                  'assessment': assessment, 'quality': {},
                  'limits': trial['purpose'] + ' Timing includes operator handoff. Evaluation alone does not activate guidance.'}
        if assessment:
            cases = assessment['assessment']['caseJudgments']
            result['quality'] = {arm: {**{key: sum(case[arm][key] for case in cases) for key in METRICS},
                                      'casesWithAnyFlag': sum(any(case[arm][key] for key in METRICS) for case in cases)} for arm in ARMS}
        return result

    def inspect(self, ident):
        with self.store.connect() as c:
            return self._get(c, ident)

    def collect_comparisons(self):
        """Collect ordinary intake/question feedback; never distill or activate it."""
        EvidenceLedger(self.store)
        with self.store.connect() as c:
            ids=[r[0] for r in c.execute("SELECT id FROM scout_evidence_records WHERE kind='comparison' ORDER BY created_at,id")]
            before=c.execute("SELECT count(*) FROM scout_learning_records WHERE kind='observation'").fetchone()[0]
        for ident in ids:
            self.import_comparison(ident)
        with self.store.connect() as c:
            after=c.execute("SELECT count(*) FROM scout_learning_records WHERE kind='observation'").fetchone()[0]
        return {'comparisonsExamined':len(ids),'newObservationVersions':after-before,'activeLessons':len(self.manifest()['entries']),
                'note':'Versions of the same event are not independent confirmations. No automatic lesson inference.'}

    def inbox(self):
        feedback = self.feedback_queue()
        with self.store.connect() as c:
            counts={row[0]:row[1] for row in c.execute('SELECT kind,count(*) FROM scout_learning_records GROUP BY kind')}
            lessons=[{'lessonId':row[0], 'title':self._get(c,row[0],'lesson')['title'],
                      'status': self.lesson_status(row[0]), 'active':self.lesson_status(row[0]) == 'active'}
                     for row in c.execute("SELECT id FROM scout_learning_records WHERE kind='lesson' ORDER BY created_at,id")]
        return {'recordCounts':counts,'lessons':lessons,'activeLessons':sum(x['active'] for x in lessons),
                'feedbackGroups': len(feedback['groups']),
                'note':'Observations are candidates for intelligent review, not verified facts or independent outcome counts.'}
