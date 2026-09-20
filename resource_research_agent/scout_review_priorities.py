"""Evidence-backed human review order, proposed by the requested AI reviewer.

Scout validates complete coverage and provenance; it does not decide usefulness.
Priorities never change resource facts, human approval, or research stopping rules.
"""
from copy import deepcopy
from datetime import datetime, timezone
import json
from typing import Any

from .scout_curation import ScoutCurationError, _canonical_json, _sha256, build_scout_review_seed
from .scout_review_handoff import priority_base_fingerprint

TIERS = ("start", "specialized", "additional")


def priority_source_seed(store, job):
    compilation = store.latest_taxonomy_compilation_for_curation_job(job['id'])
    return deepcopy(compilation['seed']) if compilation else build_scout_review_seed(store, job['id'])


def latest_priorities(store, job_id):
    with store.connect() as connection:
        row = connection.execute('SELECT * FROM scout_review_priority_revisions WHERE job_id=? ORDER BY id DESC LIMIT 1', (job_id,)).fetchone()
    if not row:
        return None
    proposal = json.loads(row['proposal_json'])
    if _sha256(proposal) != row['proposal_sha256']:
        raise ScoutCurationError('Review priority content does not match its saved hash')
    return dict(id=row['id'], createdAt=row['created_at'], proposalSha256=row['proposal_sha256'], proposal=proposal)


def validate_priorities(job: dict[str, Any], seed: dict[str, Any], proposal: dict[str, Any]) -> None:
    if job['status'] != 'completed' or any(c['status'] != 'completed' for c in job['categories']):
        raise ScoutCurationError('Finish curation before proposing review priorities')
    if not isinstance(proposal, dict) or proposal.get('schemaVersion') != 1 or proposal.get('baseFingerprint') != priority_base_fingerprint(job):
        raise ScoutCurationError('Review priorities were prepared for different curation or navigation; review them again')
    resources = {r['id']:r for r in seed['resources']}
    expected = {(r['id'], cid) for r in resources.values() for cid in r['categories']}
    assignments = proposal.get('assignments')
    if not isinstance(assignments, list) or any(not isinstance(a, dict) for a in assignments):
        raise ScoutCurationError('Review priority assignments must be a list')
    actual = [(a.get('resourceId'), a.get('categoryId')) for a in assignments]
    if any(not isinstance(x, str) or not isinstance(y, str) for x,y in actual) or len(actual) != len(expected) or set(actual) != expected:
        raise ScoutCurationError('Review priorities must cover every resource in each of its Categories exactly once')
    for a in assignments:
        if a.get('tier') not in TIERS:
            raise ScoutCurationError('Choose start, specialized or additional for each review priority')
        if not isinstance(a.get('reason'), str) or not a['reason'].strip() or len(a['reason']) > 500:
            raise ScoutCurationError('Each review priority needs a short reason (at most 500 characters)')
        if 'question' in a and (not isinstance(a['question'], str) or len(a['question']) > 500):
            raise ScoutCurationError('A review question must be text of at most 500 characters')
        evidence = a.get('evidence')
        if not isinstance(evidence, dict):
            raise ScoutCurationError('Each priority needs supporting evidence from the resource')
        field, text = evidence.get('field'), evidence.get('text')
        if field not in ('name','description','informationText','hours','address') or not isinstance(text,str) or not text.strip() or text not in resources[a['resourceId']].get(field,''):
            raise ScoutCurationError('Priority evidence must occur in the saved resource')


def save_priorities(store, job_id, proposal, *, reason):
    if not isinstance(reason,str) or not reason.strip():
        raise ScoutCurationError('A priority revision requires a review reason')
    with store.connect() as connection:
        connection.execute('BEGIN IMMEDIATE')
        job = store.get_scout_curation_job(job_id)
        if not job:
            raise ScoutCurationError('Curation job not found')
        validate_priorities(job, priority_source_seed(store, job), proposal)
        digest = _sha256(proposal)
        current = latest_priorities(store, job_id)
        if current and current['proposalSha256'] == digest:
            return current
        if connection.execute('SELECT 1 FROM scout_review_priority_revisions WHERE job_id=? AND proposal_sha256=?', (job_id,digest)).fetchone():
            raise ScoutCurationError('This priority proposal is an older revision; create an explicitly revised proposal')
        now = datetime.now(timezone.utc).isoformat()
        connection.execute('INSERT INTO scout_review_priority_revisions (job_id,created_at,base_fingerprint,proposal_sha256,proposal_json,reason) VALUES (?,?,?,?,?,?)',
            (job_id,now,proposal['baseFingerprint'],digest,_canonical_json(proposal),reason.strip()))
        connection.execute('INSERT INTO scout_curation_progress_events (job_id,category_id,created_at,phase,message,details_json) VALUES (?,NULL,?,?,?,?)',
            (job_id,now,'review-priorities-proposed','AI-proposed review order saved for every category entry.',_canonical_json({'proposalSha256':digest,'assignments':len(proposal['assignments']),'humanApproved':False})))
    return latest_priorities(store,job_id)


def apply_priorities(store, job, seed, *, required=False):
    revision = latest_priorities(store, job['id'])
    if not revision:
        if required:
            raise ScoutCurationError('Complete the per-category review priorities, reasons and evidence before handoff')
        return seed
    if revision['proposalSha256'] != job.get('reviewPrioritySha256'):
        raise ScoutCurationError('Review priorities changed while preparing the workbench')
    validate_priorities(job, seed, revision['proposal'])
    result = deepcopy(seed)
    result['scoutReviewPriorities'] = {**revision['proposal'], 'proposalSha256':revision['proposalSha256']}
    return result


def main():
    import argparse
    from pathlib import Path
    from .storage import ResearchStore
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--database',required=True);p.add_argument('--job-id',type=int,required=True)
    p.add_argument('--proposal',type=Path,required=True);p.add_argument('--reason',required=True)
    args=p.parse_args()
    result=save_priorities(ResearchStore(args.database),args.job_id,json.loads(args.proposal.read_text()),reason=args.reason)
    print(json.dumps({k:v for k,v in result.items() if k!='proposal'},indent=2))


if __name__ == '__main__':
    main()
