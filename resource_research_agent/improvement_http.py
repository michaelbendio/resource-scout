"""HTTP adapter for the durable existing-resource workflow."""
from __future__ import annotations

import re
from urllib.parse import parse_qs

from .improvement_packages import ImprovementError, read_package
from .scout_review import TEMPLATE_PATH


def handle_improvement(handler, parsed, *, post=False):
    path = parsed.path
    classification = path == '/classifications' or path.startswith('/classifications.') or path.startswith('/api/classifications')
    workflow = handler.server.classification if classification else handler.server.improvement
    if not post and path in ('/classifications', '/classifications.js', '/taxonomy-review', '/taxonomy-review.js'):
        name = path[1:] + '.html' if path in ('/classifications', '/taxonomy-review') else path[1:]
        handler._file(handler.server.web_dir / name, ('text/html' if name.endswith('.html') else 'text/javascript') + '; charset=utf-8')
        return True
    if classification:
        path = path.replace('/api/classifications', '/api/improvements', 1)
    query = parse_qs(parsed.query)
    if not post and path in ('/improvements', '/improvements.js', '/improvements.css', '/comparison.js'):
        name = 'improvements.html' if path == '/improvements' else path[1:]
        mime = 'text/html' if name.endswith('.html') else ('text/css' if name.endswith('.css') else 'text/javascript')
        handler._file(handler.server.web_dir / name, mime + '; charset=utf-8')
        return True
    if not post and path == '/improvements-renderer.js':
        template = TEMPLATE_PATH.read_text(encoding='utf-8')
        start = template.index('function escapeHTML(')
        script = template[start:template.index('\n', start)] + '\n'
        script += template[template.index('const INFORMATION_ADDITIONAL_LABEL'):template.index('function fitTextareaToText')]
        handler._binary(script.encode(), 'text/javascript; charset=utf-8', 'improvements-renderer.js')
        return True
    if not path.startswith('/api/improvements'):
        return False
    if path == '/api/improvements' and not post:
        handler._json({'projects': workflow.list_projects()})
        return True
    if post and path in ('/api/improvements/inspect', '/api/improvements/prepare'):
        payload = handler.rfile.read(handler._content_length())
        if path.endswith('/inspect'):
            package = read_package(payload)
            handler._json({'office': package['data'].get('officeName', ''), 'version': package['data']['packageVersion'],
                           'sha256': package['sha256'], 'resources': [
                               {'id': r['id'], 'name': r.get('name', ''), 'categories': r.get('categories', [])}
                               for r in package['resources'].values()]})
        else:
            handler._json(workflow.prepare(payload, query.get('office', [''])[0], query.get('resourceId', []),
                                          source_name=query.get('source', ['resource-package.zip'])[0],
                                          historical=query.get('historical', ['0'])[0] == '1'))
        return True
    match = re.fullmatch(r'/api/improvements/(\d+)(?:/([a-z-]+)(?:/(\d+))?)?', path)
    if not match:
        raise ImprovementError('Unknown improvement endpoint')
    project_id = int(match[1])
    action, export_id = match[2], int(match[3]) if match[3] else None
    if not post:
        if action is None:
            handler._json(workflow.view(project_id))
        elif action == 'events':
            handler._json({'events': workflow.events(project_id)})
        elif action == 'taxonomy' and classification:
            handler._json(handler.server.taxonomy_review.view(project_id))
        elif action == 'taxonomy-exports' and classification and export_id:
            handler._download(handler.server.taxonomy_review.export_bytes(project_id, export_id), 'application/zip', f'scout-taxonomy-{project_id}-{export_id}.zip')
        elif action == 'exports' and export_id:
            handler._download(workflow.export_bytes(project_id, export_id), 'application/zip', f'scout-reviewed-updates-{project_id}-{export_id}.zip')
        elif action == 'attachment':
            handler._binary(workflow.attachment_bytes(project_id, query.get('path', [''])[0], which=query.get('which', ['base'])[0]),
                            'application/pdf', 'resource-attachment.pdf')
        else:
            raise ImprovementError('Unknown improvement endpoint')
        return True
    if action == 'connect':
        payload = handler.rfile.read(handler._content_length())
        handler._json(workflow.connect_latest(project_id, int(query.get('revision', ['-1'])[0]), payload,
                                              query.get('office', [''])[0], source_name=query.get('source', ['current-package.zip'])[0]))
        return True
    body = handler._read_json()
    taxonomy = handler.server.taxonomy_review
    if classification and action == 'taxonomy-select':
        value = taxonomy.select_resources(project_id, body.get('revision'), body.get('resourceIds'))
    elif classification and action == 'taxonomy-group':
        value = taxonomy.save_group(project_id, body.get('revision'), body.get('group'), body.get('outcome'),
            body.get('practicalUse'), body.get('reason'), body.get('reviewer'), body.get('memberDispositions'), body.get('target', ''), body.get('prominence', ''))
    elif classification and action == 'taxonomy-plan':
        value = taxonomy.create_plan(project_id, body.get('revision'), body.get('categoryIds'), body.get('reason'))
    elif classification and action == 'taxonomy-mapping':
        value = taxonomy.review_mapping(project_id, body.get('revision'), body.get('planId'), body.get('resourceId'),
            body.get('choices'), body.get('reviewer'), body.get('note'), body.get('findingNotes', {}), body.get('typeDispositions', {}))
    elif classification and action == 'taxonomy-approve':
        value = taxonomy.approve_plan(project_id, body.get('revision'), body.get('planId'), body.get('reviewer'), body.get('note'))
    elif classification and action == 'taxonomy-export':
        value = taxonomy.prepare_export(project_id, body.get('revision'), body.get('planId'))
    elif classification and action == 'taxonomy-saved':
        value = taxonomy.acknowledge(project_id, body.get('revision'), body.get('exportId'), body.get('packageSha256'))
    elif action == 'next':
        value = {'assignment': workflow.next_assignment(project_id, researcher=body.get('researcher'), resource_id=body.get('resourceId'))}
    elif action == 'submit':
        value = workflow.submit(project_id, body.get('stage'), body.get('result'))
    elif action == 'guidance' and classification:
        value = workflow.save_guidance(project_id, body.get('revision'), body.get('guidance'), body.get('reviewer'), body.get('approvedKeys'))
    elif action == 'edit' and classification:
        value = workflow.edit(project_id, body.get('revision'), body.get('resourceId'), body.get('proposal'), body.get('reviewer'))
    elif action == 'edit':
        value = workflow.edit(project_id, body.get('revision'), body.get('resourceId'), body.get('description'),
                              body.get('informationSections'), body.get('reviewer'))
    elif action == 'review':
        value = workflow.review(project_id, body.get('revision'), body.get('resourceId'), body.get('decision'),
                                body.get('choices'), body.get('reviewer'), body.get('note', ''), body.get('findingNotes'))
    elif action == 'export':
        value = workflow.prepare_export(project_id, body.get('revision'))
    elif action == 'saved':
        value = workflow.acknowledge_export(project_id, body.get('revision'), body.get('exportId'), body.get('packageSha256'))
    else:
        raise ImprovementError('Unknown improvement action')
    handler._json(value)
    return True
