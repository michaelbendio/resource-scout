"""Sealed earlier review evidence for a new curation pass, not pre-approved output."""
from copy import deepcopy

from .resource_identity import fingerprint


def attach_reviewed_context(assignment, context):
    if context.get('schemaVersion') != 1 or context.get('artifactType') != 'scout-preparation-context':
        raise ValueError('Unknown reviewed preparation context')
    if not assignment.get('preparationPolicyVersion'):
        raise ValueError('Reviewed context requires prepared mode')
    if context['officeSlug'].casefold() != assignment['location']['name'].casefold().replace(' ', '-'):
        raise ValueError('Reviewed context belongs to another office')
    categories = context['categories']
    old_ids = {c['id'] for c in assignment['availableCategories']}
    new_ids = {c['id'] for c in categories}
    if len(new_ids) != len(categories) or not old_ids <= new_ids:
        raise ValueError('Reviewed context cannot silently remove research category IDs')
    candidates = {str(c['id']) for c in assignment['candidates']}
    records = [deepcopy(r) for r in context['resources'] if candidates.intersection(map(str, r['historicalCandidateIds']))]
    assignment = deepcopy(assignment)
    assignment['availableCategories'] = deepcopy(categories)
    assignment['availableForGroups'] = deepcopy(context['forGroups'])
    assignment['reviewedContext'] = dict(fingerprint=fingerprint(context),
        sourceHashes=deepcopy(context['sourceHashes']), resources=records,
        forGroupDefinitions=deepcopy(context['forGroupDefinitions']),
        instructions=context['instructions'])
    return assignment


def reviewed_index(assignment):
    candidates = {str(c['id']) for c in assignment['candidates']}
    return [dict(legacyResourceId=r['legacyResourceId'],
                 preferredDraftReference=r['preferredDraftReference'],
                 name=r['record']['name'],
                 relatedCandidateIds=sorted(candidates.intersection(map(str, r['historicalCandidateIds']))))
            for r in assignment.get('reviewedContext', {}).get('resources', [])
            if candidates.intersection(map(str, r['historicalCandidateIds']))]
