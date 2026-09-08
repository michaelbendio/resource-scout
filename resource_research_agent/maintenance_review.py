"""Working Scout curation copies of completed research, without approval records."""
from __future__ import annotations

import base64
import json
import re
from copy import deepcopy
from datetime import datetime

from .improvement_packages import ImprovementError, digest, nonempty
from .open_questions import attach_questions, make_questions
from .scout_maintenance import MaintenanceWorkflow, validate_fields
from .scout_review import ScoutReviewFile, _replace_meta, render_scout_review_seed


def build_maintenance_review_file(
    workflow: MaintenanceWorkflow, project_id: int, revision: int, *,
    location_name: str, created_at: str,
) -> ScoutReviewFile:
    """Build a draft review, never call review/prepare_export or mark Curated.

    Persist created_at with the delivery manifest to reproduce the same artifact.
    Changed contents receive isolated review and PDF storage; rebuilding the same
    artifact preserves the browser's edits and selected curation state.
    """
    try:
        timestamp = datetime.fromisoformat(nonempty(created_at, 'Creation timestamp').replace('Z', '+00:00'))
        if timestamp.tzinfo is None:
            raise ValueError('Timezone required')
    except (TypeError, ValueError) as error:
        raise ImprovementError('Creation timestamp needs a timezone') from error
    with workflow.store.connect() as connection:
        state = workflow._load(connection, project_id)
        if state['revision'] != revision:
            raise ImprovementError('Research revision changed; refresh before building review')
        if state['requiresReconnection']:
            raise ImprovementError('Reconnect the current office package before building a working review')
        if any(stage not in task['results'] for task in state['tasks'].values()
               for stage, _ in workflow._task_stages(state, task)):
            raise ImprovementError('Finish every selected research task before building a working review')
        package = workflow._package(connection, state['latestSha256'] or state['baseSha256'])
        rows = workflow._rows(connection, state, package)
    if not rows:
        raise ImprovementError('No reconciled resources to review')
    resources, assets = [], {}
    for row in rows:
        if row['blocked'] or row['saved']:
            raise ImprovementError('Resolve blocked or already-exported items through the maintenance workflow')
        if row['status'] not in ('new', 'current', 'changed', 'moved', 'renamed'):
            raise ImprovementError('Uncertain service status needs the maintenance decision workflow')
        resource = deepcopy(row['current']) if row['current'] else {
            'id': row['id'], 'categories': [], 'categoryFilters': {}, 'forGroups': [], 'pdfs': [],
        }
        proposed = validate_fields(row['fields'], package['data'], state['writingGuidance'], new=not row['current'])
        if any(change['conflict'] for change in row['comparison'].values()):
            raise ImprovementError('Resolve newer office edits before building a working review')
        resource.update(proposed)
        if resource.get('lastModified'):
            previous = datetime.fromisoformat(resource['lastModified'].replace('Z', '+00:00'))
            if previous.tzinfo is None or timestamp <= previous:
                raise ImprovementError('Review timestamp must follow the resource timestamp')
        resource['lastModified'] = created_at
        provenance = {
            'kind': 'maintenance', 'projectId': project_id, 'taskId': row['taskId'],
            'itemId': row['id'], 'baseSha256': state['baseSha256'],
            'researchRevision': revision,
            'resultSha256': digest(state['tasks'][row['taskId']]['results']['reconcile']),
        }
        urls = list(dict.fromkeys(row['sources'][i]['url'] for i in row['evidence']))
        explanation = row['summary']
        if urls:
            explanation += '\n\nSources checked:\n' + '\n'.join(urls)
        attach_questions(resource, make_questions([
            {'question': question, 'explanation': explanation} for question in row['questions']
        ], provenance))
        resource['scoutResearch'] = {**provenance, 'curationRequired': True, 'sources': urls}
        # Keep exact referenced bytes, including attachments unaffected by writing.
        for pdf in resource.get('pdfs', []):
            assets[pdf['path']] = base64.b64encode(package['assets'][pdf['path']]).decode('ascii')
        resources.append(resource)
    if len({resource['id'] for resource in resources}) != len(resources):
        raise ImprovementError('Multiple proposals target the same resource identity')
    seed = deepcopy(package['data'])
    location_token = ''.join(character for character in location_name if character.isalnum())
    seed.update(resources=resources, officeName='Auto' + location_token,
                packageCreatedAt=created_at, lastModified=created_at)
    rendered = render_scout_review_seed(
        seed, location_name=location_name, source_sha256=state['baseSha256'],
        category_ids=[category['id'] for category in seed['categories']],
    )
    document = rendered.content.decode('utf-8')
    artifact = re.search(r'<meta name="scout-review-artifact-id" content="([^"]+)"', document).group(1)
    document = _replace_meta(document, 'tso-storage-id', artifact)
    # Awaited by asset-dependent operations. Existing browser assets take
    # precedence, so reopening a review never undoes a curator's replacement PDF.
    asset_json = json.dumps(assets, separators=(',', ':')).replace('</', '<\\/')
    bootstrap = '''<script>
window.scoutPreviewAssetsReady=(async()=>{
 const assets=ASSETS;
 for(const [path,encoded] of Object.entries(assets)){
  if(!await getPDF(path)) await savePDF(path,new Blob([
   Uint8Array.from(atob(encoded),c=>c.charCodeAt(0))],{type:'application/pdf'}));
 }
})();
window.scoutPreviewAssetsReady.catch(error=>showAppError('Resource attachments',error.message));
</script>'''.replace('ASSETS', asset_json)
    document = document.replace('</body>', bootstrap + '</body>', 1)
    return ScoutReviewFile(rendered.filename, document.encode('utf-8'), rendered.scout_version, rendered.scout_build)
