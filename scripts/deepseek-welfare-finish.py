"""Supervised, checkpointed DeepSeek completion of five pending challengers.

Uses the tested trial transport and web relay. Original assignments and database
are preserved; importing results is a separate, audited provider handoff.
"""
import argparse
from decimal import Decimal
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('deepseek_transport', ROOT / 'scripts/deepseek-challenger-trial.py')
transport = importlib.util.module_from_spec(spec)
spec.loader.exec_module(transport)
transport.OUT = ROOT / 'data/welfare-square-deepseek-finish-20260921'
transport.CATEGORIES = ['Mental Health', 'Seniors', 'Transportation', 'Utilities, Phone, Internet', 'Veterans']
transport.CEILING = Decimal('2.00')
# The separate account-balance reserve stays at 25 cents. Authorized inference
# ceiling below includes that reserve, conservatively limiting spend to $1.75.

AUTHORIZATION = 'Michael: Finish the job. Then review without asking me. Replace five unfinished Grok challengers with DeepSeek; preserve completed research.'


def handoff():
    from resource_research_agent.storage import ResearchStore
    store = ResearchStore(transport.DB)
    manifest = transport.read(transport.OUT / 'manifest.json')
    result = []
    for item in manifest['assignments']:
        old = store.get_codex_first_assignment(item['originalAssignmentId'])
        if old['assignmentSha256'] != item['originalAssignmentSha256']:
            raise RuntimeError('Original seal changed')
        new = store.replace_codex_first_assignment(old['id'], 'DeepSeek', reason=AUTHORIZATION)
        if new['assignmentSha256'] != item['replacementAssignmentSha256']:
            raise RuntimeError('Replacement differs from researched assignment')
        result.append({'category': item['category'], 'originalAssignmentId': old['id'], 'replacementAssignmentId': new['id'], 'assignmentSha256': new['assignmentSha256']})
    transport.dump(transport.OUT / 'provider-handoff.json', result)
    print(json.dumps(result))


def save_result(category):
    from resource_research_agent.storage import ResearchStore
    from resource_research_agent.codex_first_research import save_codex_first_external_result
    directory = transport.OUT / category.lower()
    state = transport.read(directory / 'state.json')
    if state['status'] != 'completed':
        raise RuntimeError('Research is incomplete')
    acceptance = transport.read(directory / 'acceptance.json')
    raw = (directory / 'result.json').read_text()
    if acceptance.get('resultSha256') != hashlib.sha256(raw.encode()).hexdigest() or not acceptance.get('accepted'):
        raise RuntimeError('Supervisor must inspect and accept the exact result before import')
    transport.validate_result(json.loads(raw))
    record = next(x for x in transport.read(transport.OUT / 'provider-handoff.json') if x['category'] == category)
    store = ResearchStore(transport.DB)
    saved = save_codex_first_external_result(store, record['replacementAssignmentId'], raw)
    with store.connect() as connection:
        exists = connection.execute('SELECT 1 FROM research_worker_telemetry WHERE external_assignment_id=?', (saved['id'],)).fetchone()
    if not exists:
        turns = [transport.read(p) for p in sorted(directory.glob('turn-*/response.json'))]
        usage = {key: sum(t['usage'].get(key, 0) for t in turns) for key in ['prompt_tokens', 'completion_tokens', 'prompt_cache_hit_tokens', 'prompt_cache_miss_tokens']}
        usage.update(reasoningEffort='max', peakPriceUpperEstimateUsd=state['upperCostUsd'], providerCalls=len(turns), evidenceDirectory=str(directory))
        job = store.get_focused_research_job(saved['jobId'])
        store.record_worker_telemetry(import_id=1, profile='codex-grok-with-explicit-deepseek-handoff', provider='DeepSeek', role='challenger', category_id=job['categoryId'], category_label=category, attempt=1, model='deepseek-flash', outcome='completed', started_at=state['createdAt'], completed_at=state['completedAt'], elapsed_ms=round(sum(t['elapsedSeconds'] for t in turns)*1000), job_id=job['id'], external_assignment_id=saved['id'], lead_count=saved['leadCount'], response_bytes=len(raw.encode()), usage=usage)
    print(json.dumps({'category': category, 'savedAssignmentId': saved['id'], 'leadCount': saved['leadCount']}))


def supplements():
    from resource_research_agent.storage import ResearchStore
    report_path = ROOT / 'docs/challenger-review-20260921.json'
    report = transport.read(report_path)
    comparison = transport.read(ROOT / 'docs/challenger-curation-comparison-20260921.json')
    resources = {r['id']: r for r in report['seed']['resources']}
    original_job = transport.read(ROOT / 'data/challenger-curation-review-20260921/review-job.json')
    original_candidates = {c['id']: c for category in original_job['categories'] for c in category['assignment']['candidates']}
    store = ResearchStore(transport.DB)
    counts = {}
    for category in comparison['categories']:
        candidates = []
        for rid in category['resourceIds']['deepseek']:
            resource = resources[rid]
            original_ids = next(r for r in comparison['resources'] if r['id'] == rid)['candidateIds']
            members = [member for cid in original_ids for member in original_candidates[cid]['candidate']['manualDiscoveryProvenance']['members']]
            candidate_id = 'deepseek-reviewed-20260921-' + rid
            draft = {**resource, 'candidateIds': [candidate_id], 'categoryFilters': {}, 'forGroups': []}
            # Existing proposals are evidence, not a new office taxonomy or approval.
            draft.pop('forGroupReview', None)
            draft.pop('curated', None)
            candidates.append({'id': candidate_id, 'name': resource['name'], 'resourceDraft': draft,
                               'candidate': {'manualDiscoveryProvenance': {'members': members}},
                               'notes': 'Previously reviewed supplemental DeepSeek finding. Preserve corrected eligibility and source evidence; compare with all existing office candidates and reuse stable identities when appropriate. Prior review is not human approval.'})
        payload = {'candidates': candidates, 'sourceReport': str(report_path), 'sourceReportSha256': hashlib.sha256(report_path.read_bytes()).hexdigest(), 'originalCategory': category['categoryId'], 'origin': 'DeepSeek V4.1-Flash trial; Codex curation and requested review; mixed-provider shared records retain original submissions.'}
        store.save_scout_curation_supplement(1, category['categoryId'], 'reviewed-deepseek-trial-20260921', payload, reason=AUTHORIZATION)
        counts[category['categoryId']] = len(candidates)
    transport.dump(transport.OUT / 'supplements.json', counts)
    print(json.dumps(counts))


def verify_preserved():
    old = sqlite3.connect(f'file:{transport.OUT / "before.sqlite3"}?mode=ro', uri=True)
    new = sqlite3.connect(f'file:{transport.DB}?mode=ro', uri=True)
    checked = {}
    for table, condition in [('focused_research_passes', '1'), ('codex_first_research_assignments', '1'), ('focused_research_jobs', "status='completed'"), ('manual_discovery_contributions', '1')]:
        rows = old.execute(f'SELECT * FROM {table} WHERE {condition}').fetchall()
        for row in rows:
            current = new.execute(f'SELECT * FROM {table} WHERE id=?', (row[0],)).fetchone()
            if current != row:
                raise RuntimeError(f'Preserved evidence changed: {table} id={row[0]}')
        checked[table] = len(rows)
    if new.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
        raise RuntimeError('SQLite quick_check failed')
    old.close(); new.close()
    transport.dump(transport.OUT / 'preservation-verification.json', {'at': transport.now(), 'unchangedOriginalRows': checked, 'quickCheck': 'ok'})
    print(json.dumps(checked))


def prepare():
    out = transport.OUT
    if (out / 'manifest.json').exists():
        raise RuntimeError('Already prepared; resume saved steps')
    start = transport.balance()
    out.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(f'file:{transport.DB}?mode=ro', uri=True)
    connection.row_factory = sqlite3.Row
    with sqlite3.connect(out / 'before.sqlite3') as backup:
        connection.backup(backup)
    transport.dump(out / 'before-snapshot.json', transport.snapshot())
    assignments = []
    for category in transport.CATEGORIES:
        row = connection.execute("SELECT a.*,j.category_label,j.category_id FROM codex_first_research_assignments a JOIN focused_research_jobs j ON j.id=a.job_id WHERE j.import_id=1 AND j.category_label=? AND a.researcher='Grok' AND a.status='assigned'", (category,)).fetchone()
        if row is None:
            raise RuntimeError('Missing pending assignment: ' + category)
        row = dict(row)
        original = row['assignment']
        if hashlib.sha256(original.encode()).hexdigest() != row['assignment_sha256']:
            raise RuntimeError('Original assignment hash mismatch')
        directory = out / category.lower()
        transport.dump(directory / 'baseline.json', row)
        (directory / 'original-assignment.txt').write_text(original)
        reassigned = original.replace('Resource Scout adversarial challenger assignment for Grok.', 'Resource Scout adversarial challenger assignment for DeepSeek.', 1)
        prompt = transport._research_prompt(reassigned, 'DeepSeek', 'challenger')
        (directory / 'assignment.txt').write_text(prompt)
        transport.dump(directory / 'state.json', {'category': category, 'status': 'prepared', 'turn': 0, 'createdAt': transport.now(), 'messages': [{'role': 'user', 'content': prompt}], 'upperCostUsd': '0', 'assignmentSha256': hashlib.sha256(prompt.encode()).hexdigest()})
        assignments.append({'category': category, 'originalAssignmentId': row['id'], 'originalAssignmentSha256': row['assignment_sha256'], 'replacementAssignmentSha256': hashlib.sha256(reassigned.encode()).hexdigest()})
    connection.close()
    transport.dump(out / 'manifest.json', {'createdAt': transport.now(), 'database': str(transport.DB), 'categories': transport.CATEGORIES, 'assignments': assignments, 'model': 'deepseek-flash', 'versionExpected': 'DeepSeek-V4.1-Flash', 'reasoningEffort': 'max', 'initialBalanceUsd': str(start), 'authorizedCeilingUsd': str(transport.CEILING), 'reserveUsd': str(transport.RESERVE), 'authorization': 'Michael: Finish the job. Then review without asking me.', 'scope': 'Five pending challengers, then Codex High curation and requested Codex review. Preserve completed research and reviewed supplemental trial findings.', 'searchHarness': 'Supervisor relays model-selected web requests through Codex web tools, preserving unedited responses. No paid search fallback.'})
    print(json.dumps({'status': 'prepared', 'balanceUsd': str(start), 'categories': transport.CATEGORIES}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'step', 'handoff', 'save', 'supplements', 'verify'])
    parser.add_argument('category', nargs='?', choices=transport.CATEGORIES)
    args = parser.parse_args()
    with transport.research_runner_lock(transport.DB):
        if args.action == 'prepare':
            prepare()
        elif args.action == 'step':
            transport.step(args.category)
        elif args.action == 'handoff':
            handoff()
        elif args.action == 'save':
            save_result(args.category)
        elif args.action == 'supplements':
            supplements()
        else:
            verify_preserved()


if __name__ == '__main__':
    main()
