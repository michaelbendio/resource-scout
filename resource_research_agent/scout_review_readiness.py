"""Release checks for the human resource-vetting workbench."""
import re
from typing import Any
from .scout_curation import ScoutCurationError, build_scout_review_seed

INFORMATION_HEADINGS = (
    "Eligibility Requirements", "How to Best Connect", "Access", "Important Information to Know",
)


def validate_ready_seed(seed: dict[str, Any]) -> dict[str, int]:
    categories = {c['id']: set(c.get('filters') or []) for c in seed['categories']}
    missing = [cid for cid, types in categories.items() if not types]
    if missing:
        raise ScoutCurationError('Design Types before handoff for: ' + ', '.join(missing))
    groups = set(seed.get('forGroups') or [])
    assigned = 0
    for r in seed['resources']:
        text = r.get('informationText', '')
        matches = list(re.finditer(r'^\*\*(.+?)\*\*\s*$', text, re.M))
        if tuple(m[1] for m in matches) != INFORMATION_HEADINGS or text[:matches[0].start()].strip():
            raise ScoutCurationError(f"{r['id']}: Information needs the four standalone bold headings")
        if any(not text[m.end():matches[i+1].start() if i<3 else len(text)].strip() for i,m in enumerate(matches)):
            raise ScoutCurationError(f"{r['id']}: Information has an empty section")
        for cid in r['categories']:
            choices = r.get('categoryFilters', {}).get(cid, [])
            if not choices or not set(choices) <= categories.get(cid, set()):
                raise ScoutCurationError(f"{r['id']}: missing or invalid {cid} Types")
        if not set(r.get('forGroups', [])) <= groups:
            raise ScoutCurationError(f"{r['id']}: unknown For group")
        assigned += bool(r.get('forGroups'))
    return {'resources':len(seed['resources']), 'categoriesWithTypes':len(categories),
            'groups':len(groups), 'resourcesWithGroups':assigned,
            'resourcesWithoutGroups':len(seed['resources'])-assigned}


def require_review_ready(store, job: dict[str, Any]) -> dict[str, int]:
    compilation = store.latest_taxonomy_compilation_for_curation_job(job['id'])
    if compilation and job.get('reviewNavigationSha256'):
        raise ScoutCurationError('Resolve competing navigation and taxonomy proposals before handoff')
    if not job.get('reviewNavigationSha256') and not compilation:
        raise ScoutCurationError('Complete the Types and For-group review, including explicit no-group decisions, before handoff')
    seed = compilation['seed'] if compilation else build_scout_review_seed(store, job['id'])
    summary = validate_ready_seed(seed)
    from .scout_review_priorities import apply_priorities
    reviewed = apply_priorities(store, job, seed, required=True)
    summary['priorityAssignments'] = len(reviewed['scoutReviewPriorities']['assignments'])
    return summary
