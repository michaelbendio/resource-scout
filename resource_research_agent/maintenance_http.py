"""Maintenance routes; package uploads use the same bounded HTTP reader as Scout."""
import re
from urllib.parse import parse_qs
from .improvement_packages import ImprovementError, read_package


def handle_maintenance(handler, parsed, *, post=False):
    path, query = parsed.path, parse_qs(parsed.query)
    if not post and path in ('/maintenance', '/maintenance.js'):
        handler._file(handler.server.web_dir / ('maintenance.html' if path == '/maintenance' else 'maintenance.js'), ('text/html' if path == '/maintenance' else 'text/javascript')+'; charset=utf-8')
        return True
    if not path.startswith('/api/maintenance'): return False
    flow = handler.server.maintenance
    if path == '/api/maintenance' and not post:
        handler._json({'projects': flow.list_projects()}); return True
    if post and path in ('/api/maintenance/inspect', '/api/maintenance/prepare'):
        payload = handler.rfile.read(handler._content_length())
        if path.endswith('/inspect'):
            package = read_package(payload)
            value = {'office': package['data'].get('officeName', ''), 'packageVersion': package['data']['packageVersion'],
                     'resources': [{'id': r['id'], 'name': r.get('name', ''), 'verifiedOn': r.get('verifiedOn', '')} for r in package['resources'].values()], 'categories': package['data']['categories']}
        else:
            value = flow.prepare(payload, query.get('office', [''])[0], query.get('resourceId', []), query.get('categoryId', []), run_name=query.get('runName', [''])[0], historical=query.get('historical', ['0'])[0] == '1')
        handler._json(value); return True
    match = re.fullmatch(r'/api/maintenance/(\d+)(?:/([a-z-]+)(?:/(\d+))?)?', path)
    if not match: raise ImprovementError('Unknown maintenance endpoint')
    pid, action = int(match[1]), match[2]
    if not post:
        if action is None: handler._json(flow.view(pid))
        elif action == 'events': handler._json({'events': flow.events(pid)})
        elif action == 'exports' and match[3]: handler._download(flow.export_bytes(pid, int(match[3])), 'application/zip', f'scout-maintenance-{pid}-{match[3]}.zip')
        elif action == 'attachment': handler._binary(flow.attachment_bytes(pid, query.get('path', [''])[0]), 'application/pdf', 'maintenance-source.pdf')
        else: raise ImprovementError('Unknown maintenance endpoint')
        return True
    if action == 'connect':
        value = flow.connect_latest(pid, int(query.get('revision', ['-1'])[0]), handler.rfile.read(handler._content_length()), query.get('office', [''])[0])
    else:
        b = handler._read_json()
        if action == 'next': value = {'assignment': flow.next_assignment(pid, researcher=b.get('researcher'), task_id=b.get('taskId'))}
        elif action == 'submit': value = flow.submit(pid, b.get('stage'), b.get('result'))
        elif action == 'review': value = flow.review(pid, b.get('revision'), b.get('taskId'), b.get('itemId'), b.get('decision'), b.get('choices'), b.get('reviewer'), b.get('note'), identity_decision=b.get('identityDecision', ''), finding_notes=b.get('findingNotes'))
        elif action == 'export': value = flow.prepare_export(pid, b.get('revision'))
        elif action == 'saved': value = flow.acknowledge_export(pid, b.get('revision'), b.get('exportId'), b.get('packageSha256'))
        else: raise ImprovementError('Unknown maintenance action')
    handler._json(value); return True
