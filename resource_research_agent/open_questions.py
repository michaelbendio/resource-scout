"""Administrative curator questions, separate from printable service information."""
from copy import deepcopy
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
    return questions


def attach_questions(resource, questions):
    """Retain curator decisions and unknown question data when Scout revisits."""
    if not questions:
        return
    existing = resource.setdefault('openQuestions', [])
    if not isinstance(existing, list):
        raise ImprovementError('Existing openQuestions must be an array; retain and resolve malformed data before export')
    ids = {q.get('id') for q in existing if isinstance(q, dict)}
    for q in questions:
        if q['id'] not in ids:
            existing.append(deepcopy(q)); ids.add(q['id'])


def improvement_questions(item, source):
    questions = []
    findings = {stage.split(':', 1)[1] + ':' + finding['id']: finding
                for stage, result in item['results'].items() if stage.startswith('audit:')
                for finding in result['findings']}
    for resolution in item['results'].get('reconcile', {}).get('resolutions', []):
        if resolution['status'] == 'needs-review':
            finding = findings[resolution['findingId']]
            questions += make_questions([{'question': finding['summary'], 'explanation': resolution['reason']}],
                                        {**source, 'findingId': resolution['findingId']})
    return questions
