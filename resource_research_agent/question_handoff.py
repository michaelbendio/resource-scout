"""Deliver questions without accepting service changes or claiming resource curation."""
import json
from copy import deepcopy
from .improvement_packages import ImprovementError, digest, next_timestamp, read_package, resource_blocked, utcnow, write_package
from .open_questions import attach_questions, improvement_questions, make_questions


def research_state_hash(state):
    return digest(state['tasks'] if state['kind'] == 'maintenance' else state['resources'])


def prepare_question_export(flow, project_id, revision):
    with flow.store.connect() as c:
        state = flow._checked(c, project_id, revision)
        if not state['latestSha256'] or state.get('requiresReconnection'):
            raise ImprovementError('Reconnect the current office package before exporting questions')
        package = flow._package(c, state['latestSha256'])
        targets = {}
        if state['kind'] == 'maintenance':
            for tid, task in state['tasks'].items():
                # Discovery leads do not establish an existing resource identity.
                if task['kind'] != 'recheck':
                    continue
                for item in task['results'].get('reconcile', {}).get('items', []):
                    questions = make_questions([{'question': q, 'explanation': item['summary']} for q in item['questions']],
                        {'kind': 'maintenance', 'projectId': project_id, 'taskId': tid, 'itemId': item['id']})
                    questions += improvement_questions(task, {'kind':'maintenance', 'projectId':project_id, 'taskId':tid, 'resourceId':item['id']})
                    targets.setdefault(item['id'], []).extend(questions)
        else:
            for rid, item in state['resources'].items():
                targets[rid] = improvement_questions(item, {'kind': state['kind'], 'projectId': project_id, 'resourceId': rid})
        for rid, questions in targets.items():
            if questions and (message := resource_blocked(package, rid)):
                raise ImprovementError(message)
            targets[rid] = list({q['id']:q for q in questions}.values())
        exported = deepcopy(package['data'])
        changed = {}
        for resource in exported['resources']:
            rid = resource['id']
            questions = targets.get(rid, [])
            if not questions:
                continue
            if message := resource_blocked(package, rid):
                raise ImprovementError(message)
            before = deepcopy(resource)
            attach_questions(resource, questions)
            if resource != before:
                changed[rid] = {'questionIds': [q['id'] for q in questions], 'beforeResourceSha256': digest(before)}
        if not changed:
            raise ImprovementError('No new questions for existing resources to export')
        manifest = {'questionHandoffOnly': True, 'projectId': project_id, 'baseSha256': state['baseSha256'],
            'latestSha256': state['latestSha256'], 'researchStateSha256': research_state_hash(state),
            'historicalDevelopmentOnly': state['historical'], 'questionResources': changed, 'resources': {}, 'records': []}
        key = digest(manifest)
        prior = c.execute('SELECT id,manifest_json FROM scout_improvement_exports WHERE export_key=?', (key,)).fetchone()
        if prior:
            return {'exportId': prior['id'], 'manifest': json.loads(prior['manifest_json'])}
        stamp = next_timestamp([exported, *exported['resources'], *exported['categories']])
        for rid in changed:
            exported.setdefault('changes', []).append({'id': f'scout-questions:{project_id}:{rid}:{key[:16]}',
                'type': 'resource', 'action': 'updated', 'targetId': rid, 'targetName': package['resources'][rid].get('name', ''),
                'timestamp': stamp, 'description': 'Scout questions for the office curator; service fields unchanged.'})
        # Leave resource clocks unchanged: an administrative handoff must not make
        # an old service snapshot defeat a newer office edit during a merge.
        versions = [json.loads(r[0])['packageVersion'] for r in c.execute('SELECT manifest_json FROM scout_improvement_exports WHERE project_id=?', (project_id,))]
        exported.update(packageVersion=max([exported['packageVersion'], *versions])+1, packageCreatedAt=stamp, lastModified=stamp)
        payload = write_package(exported, package['assets'])
        out = read_package(payload)
        manifest.update(exportKey=key, packageVersion=exported['packageVersion'], createdAt=stamp,
                        packageSha256=out['sha256'], assetHashes=out['assetHashes'])
        eid = c.execute('INSERT INTO scout_improvement_exports(project_id,export_key,manifest_json,payload) VALUES(?,?,?,?)',
                        (project_id, key, json.dumps(manifest, ensure_ascii=False), payload)).lastrowid
        flow._save(c, state, 'questions-export-prepared', {'exportId': eid, 'manifest': manifest})
        return {'exportId': eid, 'manifest': manifest}


def acknowledge_question_export(flow, c, state, manifest, export_id):
    if manifest['researchStateSha256'] != research_state_hash(state):
        raise ImprovementError('Research or review changed after question export; discard the stale export')
    # No resource becomes curated, packaged or provider-verified through this path.
    state['requiresReconnection'] = True
    c.execute('UPDATE scout_improvement_exports SET acknowledged_at=? WHERE id=?', (utcnow(), export_id))
    flow._save(c, state, 'questions-export-saved', {'exportId': export_id, 'packageSha256': manifest['packageSha256']})
    return flow._view(c, state)
