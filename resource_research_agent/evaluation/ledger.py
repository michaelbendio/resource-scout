"""Transactional reservations and conservative native-usage accounting."""
from __future__ import annotations
from contextlib import contextmanager
from decimal import Decimal, InvalidOperation
import json
import hashlib
from pathlib import Path
import sqlite3
import time
from .protocol import EvaluationError, read, write_once, file_hash, digest, identifier, verify_protocol, now, inside


class BudgetHold(EvaluationError):
    pass


def money(value):
    try:
        amount = Decimal(str(value))
    except InvalidOperation as exc:
        raise EvaluationError('Invalid decimal amount') from exc
    if not amount.is_finite() or amount < 0:
        raise EvaluationError('Money must be finite and nonnegative')
    return amount


def maximum_charge(provider, pricing):
    """Bound every possible native-search generation, not an assumed average turn."""
    if pricing.get('inputBoundCoversToolContext') is not True:
        raise BudgetHold('No verified bound for native tool-generated context')
    if pricing.get('reasoningIncludedInOutput') is not True or pricing.get('inputAccounting') not in ['exclusive','totalIncludesCached']:
        raise BudgetHold('Token/cache/reasoning billing is not defined')
    keys = ['inputPerMillion','cacheHitPerMillion','cacheWritePerMillion','outputPerMillion','searchPerUse']
    if any(pricing.get(k) is None for k in keys):
        raise BudgetHold('A token or native-tool charge is unknown')
    rate = max(money(pricing[k]) for k in keys[:3])
    generations = provider['maxSearchUses'] + 1
    return (rate * provider['maxInputTokens'] + money(pricing['outputPerMillion']) * provider['maxOutputTokens']) * generations / 1_000_000 + money(pricing['searchPerUse']) * provider['maxSearchUses']


def normalize_usage(usage, pricing):
    """Missing native counters remain unknown. Components are mutually exclusive."""
    def counter(key):
        value = usage.get(key)
        return value if type(value) is int and value >= 0 else None
    values = dict(input=counter('input_tokens'), cacheHit=counter('cache_read_input_tokens'),
                  cacheWrite=counter('cache_creation_input_tokens'), output=counter('output_tokens'))
    # A documented absent-means-zero rule must be frozen, not inferred from absence.
    for key, field in [('cacheHit','cache_read_input_tokens'),('cacheWrite','cache_creation_input_tokens')]:
        if values[key] is None and field in pricing.get('absentMeansZero', []):
            values[key] = 0
    if pricing.get('inputAccounting') == 'totalIncludesCached':
        if any(values[k] is None for k in ['input','cacheHit','cacheWrite']):
            values['input'] = None
        else:
            values['input'] -= values['cacheHit'] + values['cacheWrite']
            if values['input'] < 0:
                raise EvaluationError('Cache counters exceed total input')
    elif pricing.get('inputAccounting') != 'exclusive':
        raise EvaluationError('Unknown input/cache accounting convention')
    tool = usage.get('server_tool_use')
    searches = tool.get('web_search_requests') if isinstance(tool,dict) else None
    if searches is None and 'web_search_requests' in pricing.get('absentMeansZero',[]):
        searches = 0
    values['searches'] = searches if type(searches) is int and searches >= 0 else None
    values['reasoning'] = counter('reasoning_tokens')
    if pricing.get('reasoningIncludedInOutput') is not True:
        raise BudgetHold('Reasoning billing must be explicitly defined before dispatch')
    # Reasoning is diagnostic only when already included in output.
    if any(values[k] is None for k in ['input','cacheHit','cacheWrite','output','searches']):
        return values, None
    cost = sum(money(pricing[p]) * values[v] / 1_000_000 for v,p in [
        ('input','inputPerMillion'),('cacheHit','cacheHitPerMillion'),('cacheWrite','cacheWritePerMillion'),('output','outputPerMillion')])
    cost += money(pricing['searchPerUse']) * values['searches']
    return values, cost


class Ledger:
    def __init__(self, root, *, simulation=False):
        self.root = Path(root).resolve(); self.simulation = simulation
        self.manifest = verify_protocol(self.root)
        self.manifest_sha = file_hash(self.root/'manifest.json')
        self.config = read(self.root/'config.json'); self.pricing = read(self.root/'inputs/pricing.json')
        self.path = inside(self.root,'ledger.sqlite3')
        with self.connect() as db:
            db.executescript('''CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
              CREATE TABLE IF NOT EXISTS attempts(
                id TEXT PRIMARY KEY, condition TEXT, category TEXT, stage TEXT, pass_key TEXT,
                request_sha TEXT, requested_model TEXT, returned_model TEXT, state TEXT,
                reservation TEXT, calculated TEXT, billed TEXT, pricing_sha TEXT, authorization_sha TEXT,
                created_at TEXT, sent_at REAL, timeout_seconds REAL, elapsed REAL NOT NULL DEFAULT 0,
                response_sha TEXT, usage_json TEXT, diagnosis TEXT, recovery_of TEXT);
              CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,attempt_id TEXT,event TEXT,at TEXT,details TEXT);''')
            row=db.execute("SELECT value FROM meta WHERE key='protocol'").fetchone()
            if row and row[0]!=self.manifest_sha:raise EvaluationError('Ledger belongs to another protocol')
            db.execute("INSERT OR IGNORE INTO meta VALUES ('protocol',?)",(self.manifest_sha,))

    def connect(self):
        db=sqlite3.connect(self.path,timeout=30);db.row_factory=sqlite3.Row;return db

    @contextmanager
    def transaction(self):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            yield db

    def authorization(self):
        if (self.root/'accounting-hold.json').exists():raise BudgetHold('Accounting discrepancy needs explicit reconciliation')
        path=self.root/'authorization.json'
        if not path.exists():raise BudgetHold('A concrete spending authorization is required')
        raw=path.read_bytes(); a=json.loads(raw); auth_sha=hashlib.sha256(raw).hexdigest()
        if a.get('protocolSha256')!=self.manifest_sha or a.get('experimentId')!=self.manifest['experimentId']:
            raise BudgetHold('Authorization does not match this sealed experiment')
        for key in ['approvedBy','approvedAt','approvalText','billingOwner','billingAccount']:
            if not isinstance(a.get(key),str) or not a[key].strip():raise BudgetHold(f'Authorization needs {key}')
        if a.get('provider')!='deepseek':raise BudgetHold('Wrong authorized billing provider')
        if not self.simulation:
            if a.get('simulationOnly') is not False or self.pricing.get('verified') is not True:
                raise BudgetHold('Simulation authorization or unverified pricing cannot dispatch live work')
            if self.config['provider']['maxInputTokens'] < self.pricing.get('providerContextLimitTokens',float('inf')):
                raise BudgetHold('Input reservation must cover the provider context limit, including native tools')
        if file_hash(self.root/'manifest.json')!=self.manifest_sha or digest(self.pricing)!=digest(read(self.root/'inputs/pricing.json')):
            raise BudgetHold('Protocol or pricing changed')
        write_once(self.root/'authorizations'/(auth_sha+'.json'),a)
        return a,auth_sha

    @staticmethod
    def exposure(rows):
        return sum((money(r['billed'] if r['billed'] is not None else r['calculated'] if r['calculated'] is not None else r['reservation'])
                    for r in rows if r['state']!='failed-not-sent'),Decimal(0))

    def reserve_attempt(self, attempt_id, *, condition, category, stage, pass_key, request,
                        timeout_seconds, recovery_of=None, diagnosis=None):
        identifier(attempt_id);identifier(category)
        a,auth_sha=self.authorization()
        if category not in a['categories'] or stage not in a['stageCapsUsd']:
            raise BudgetHold('Category/stage outside the authorized envelope')
        if condition!=self.config['condition']:raise BudgetHold('Unsealed experimental condition')
        amount=maximum_charge(self.config['provider'],self.pricing)
        request_sha=digest(request)
        with self.transaction() as db:
            prior=db.execute('SELECT * FROM attempts WHERE id=?',(attempt_id,)).fetchone()
            if prior:
                if (prior['request_sha'],prior['category'],prior['stage'],prior['pass_key'])!=(request_sha,category,stage,pass_key):
                    raise EvaluationError('Attempt ID reused for different work')
                return dict(prior)
            rows=list(db.execute('SELECT * FROM attempts'));cat=[r for r in rows if r['category']==category]
            if any(r['state'] in ['sent','unknown-outcome'] for r in rows):
                raise BudgetHold('Uncertain paid outcome requires saved-response reconciliation before new dispatch')
            if any(r['state']=='reserved' for r in rows):
                raise BudgetHold('One evaluation worker/reservation at a time')
            if recovery_of:
                source=db.execute('SELECT * FROM attempts WHERE id=?',(recovery_of,)).fetchone()
                if not source or source['state']!='failed-not-sent' or not diagnosis:
                    raise BudgetHold('Recovery needs diagnosed evidence of a request not sent')
                if sum(r['recovery_of'] is not None for r in cat)>=self.config['limits']['maxRecoveries']:
                    raise BudgetHold('Diagnosed transport recovery limit reached')
            if sum(r['state']!='failed-not-sent' for r in cat)>=self.config['limits']['callsPerCategory']:
                raise BudgetHold('Category call cap reached')
            if sum(r['elapsed'] for r in cat)+timeout_seconds>self.config['limits']['activeSecondsPerCategory']:
                raise BudgetHold('Category active-time cap reached')
            if timeout_seconds<=0 or timeout_seconds>self.config['provider']['timeoutSeconds']:
                raise BudgetHold('Request timeout exceeds sealed bound')
            if self.exposure(rows)+amount>money(a['totalUsd']):raise BudgetHold('Experiment dollar cap reached')
            if self.exposure([r for r in rows if r['stage']==stage])+amount>money(a['stageCapsUsd'][stage]):
                raise BudgetHold('Stage dollar cap reached')
            db.execute('''INSERT INTO attempts(id,condition,category,stage,pass_key,request_sha,requested_model,state,
                reservation,pricing_sha,authorization_sha,created_at,timeout_seconds,recovery_of,diagnosis)
                VALUES (?,?,?,?,?,?,?,'reserved',?,?,?,?,?,?,?)''',
                (attempt_id,condition,category,stage,pass_key,request_sha,request['model'],str(amount),digest(self.pricing),auth_sha,now(),timeout_seconds,recovery_of,diagnosis))
            self.event(db,attempt_id,'reserved',{'maximumUsd':str(amount)})
        return self.attempt(attempt_id)

    @staticmethod
    def event(db,attempt_id,event,details):
        db.execute('INSERT INTO events(attempt_id,event,at,details) VALUES (?,?,?,?)',(attempt_id,event,now(),json.dumps(details)))

    def attempt(self,attempt_id):
        with self.connect() as db:
            row=db.execute('SELECT * FROM attempts WHERE id=?',(attempt_id,)).fetchone()
            return dict(row) if row else None

    def mark_sent(self,attempt_id):
        with self.transaction() as db:
            updated=db.execute("UPDATE attempts SET state='sent',sent_at=? WHERE id=? AND state='reserved'",(time.time(),attempt_id))
            if updated.rowcount!=1:raise BudgetHold('Attempt was already sent; do not replay it')
            self.event(db,attempt_id,'sent',{})

    def record_failure(self,attempt_id,*,not_sent=False,diagnosis):
        with self.transaction() as db:
            row=db.execute('SELECT * FROM attempts WHERE id=?',(attempt_id,)).fetchone()
            if not row or row['state'] not in ['reserved','sent','unknown-outcome']:
                raise EvaluationError('Failure does not match an outstanding attempt')
            if not_sent and row['state']!='reserved':raise BudgetHold('A sent request cannot be declared unused without provider reconciliation')
            state='failed-not-sent' if not_sent else 'unknown-outcome'
            elapsed=max(0,time.time()-row['sent_at']) if row['sent_at'] else 0
            db.execute('UPDATE attempts SET state=?,diagnosis=?,elapsed=? WHERE id=?',(state,diagnosis,elapsed,attempt_id))
            self.event(db,attempt_id,state,{'diagnosis':diagnosis})

    def record_response(self,attempt_id,body):
        # Save evidence before parsing counters or changing the paid outcome.
        path=self.root/'attempts'/identifier(attempt_id)/'response.json'
        write_once(path,body)
        with self.transaction() as db:
            row=db.execute('SELECT * FROM attempts WHERE id=?',(attempt_id,)).fetchone()
            if not row or row['state'] not in ['sent','unknown-outcome','responded']:
                raise EvaluationError('Response without a matching dispatched attempt')
            if row['state']=='responded':
                if row['response_sha']!=file_hash(path):raise EvaluationError('Changed saved response')
                return
            usage,cost=normalize_usage(body.get('usage',{}),self.pricing)
            elapsed=max(0,time.time()-row['sent_at'])
            db.execute("UPDATE attempts SET state='responded',returned_model=?,calculated=?,response_sha=?,usage_json=?,elapsed=? WHERE id=?",
                (body.get('model'),str(cost) if cost is not None else None,file_hash(path),json.dumps(usage),elapsed,attempt_id))
            self.event(db,attempt_id,'responded',{'usageComplete':cost is not None,'chargeIsCalculated':True})
        if cost is not None and cost>money(row['reservation']):
            write_once(self.root/'accounting-hold.json',{'attemptId':attempt_id,'reason':'Observed charge exceeded the sealed upper bound; review billing before any further dispatch.'})
            raise BudgetHold('Provider usage exceeded the reserved bound; all further dispatch held')

    def summarize_usage(self):
        with self.connect() as db:rows=[dict(r) for r in db.execute('SELECT * FROM attempts')]
        return dict(attempts=len(rows),states={s:sum(r['state']==s for r in rows) for s in ['reserved','sent','responded','failed-not-sent','unknown-outcome']},
            exposureUsd=str(self.exposure(rows)),calculatedUsd=str(sum((money(r['calculated']) for r in rows if r['calculated'] is not None),Decimal(0))),
            knownBilledUsd=None,unknownUsageAttempts=sum(r['state']=='responded' and r['calculated'] is None for r in rows),
            outstandingReservedUsd=str(sum((money(r['reservation']) for r in rows if r['state'] in ['reserved','sent','unknown-outcome'] or (r['state']=='responded' and r['calculated'] is None)),Decimal(0))),
            activeSeconds=sum(r['elapsed'] for r in rows),accountBalanceAttribution='Not used; other account activity cannot be attributed to this experiment.')
