"""Administrative curator questions, separate from printable service information."""
from copy import deepcopy
from datetime import datetime
from .improvement_packages import ImprovementError, digest, nonempty


def make_questions(items, source):
    if not isinstance(items, list):
        raise ImprovementError('Open questions must be an array')
    questions = []
    for item in items:
        if not isinstance(item, dict) or set(item) != {'question', 'explanation'}:
            raise ImprovementError('Each Scout question needs only question and explanation; Scout cannot mark curator questions resolved')
        text = {key: nonempty(item[key], key) for key in ('question', 'explanation')}
        questions.append({'id': 'scout-question:' + digest(text)[:24], **text,
                          'status': 'open', 'resolution': '', 'source': deepcopy(source)})
    return list({q["id"]: q for q in questions}.values())


def attach_questions(resource, questions):
    """Retain curator decisions and unknown question data when Scout revisits."""
    if not questions:
        return
    existing = resource.get('openQuestions', [])
    validate_questions(existing)
    validate_questions(questions)
    by_id = {q['id']: q for q in existing}
    additions = []
    for q in questions:
        old = by_id.get(q['id'])
        if old and any(old[key] != q[key] for key in ('question', 'explanation')):
            raise ImprovementError('An existing question ID has different text; settle its identity before export')
        if old is None:
            additions.append(deepcopy(q)); by_id[q['id']] = q
    resource['openQuestions'] = existing + additions


def validate_questions(questions):
    """Fail visibly on malformed administrative data; preserve unknown extension keys."""
    if not isinstance(questions, list):
        raise ImprovementError('openQuestions must be an array')
    ids = set()
    def decision(value):
        return (isinstance(value, dict) and value.get('status') in ('open', 'resolved')
                and isinstance(value.get('resolution'), str)
                and (value['status'] != 'resolved' or bool(value['resolution'].strip())))
    for q in questions:
        if not isinstance(q, dict):
            raise ImprovementError('Each open question must be an object')
        for key in ('id', 'question', 'explanation'):
            nonempty(q.get(key), 'Question ' + key)
        if q['id'] in ids:
            raise ImprovementError('Duplicate question ID: ' + q['id'])
        ids.add(q['id'])
        if not decision(q):
            raise ImprovementError('Question needs valid status and resolution note')
        if 'history' in q:
            if not isinstance(q['history'], list):
                raise ImprovementError('Question history must be an array')
            for h in q['history']:
                if not decision(h):
                    raise ImprovementError('Invalid question decision history')
                try:
                    datetime.fromisoformat(nonempty(h.get('changedAt'), 'Decision timestamp').replace('Z', '+00:00'))
                except (ValueError, TypeError) as error:
                    raise ImprovementError('Invalid question decision timestamp') from error
        if 'resolutionConflict' in q and not isinstance(q['resolutionConflict'], bool):
            raise ImprovementError('Invalid question conflict flag')
        if 'decisionAlternatives' in q and (not isinstance(q['decisionAlternatives'], list)
                or not all(decision(h) for h in q['decisionAlternatives'])):
            raise ImprovementError('Invalid competing question decisions')
        if q.get('resolutionConflict') and (q['status'] != 'open' or len(q.get('decisionAlternatives', [])) < 2):
            raise ImprovementError('Competing question decisions must remain open for the curator')


def improvement_questions(item, source):
    questions = []
    findings = {stage.split(':', 1)[1] + ':' + finding['id']: finding
                for stage, result in item['results'].items() if stage.startswith('audit:')
                for finding in result['findings']}
    findings.update({stage.split(':', 1)[1] + ':' + finding['id']: finding
                     for stage, result in item['results'].items() if stage.startswith('blind:')
                     for finding in result['items']})
    for resolution in item['results'].get('reconcile', {}).get('resolutions', []):
        if resolution['status'] == 'needs-review':
            finding = findings[resolution['findingId']]
            questions += make_questions([{'question': finding['summary'], 'explanation': resolution['reason']}],
                                        {**source, 'findingId': resolution['findingId']})
    return list({q["id"]: q for q in questions}.values())
