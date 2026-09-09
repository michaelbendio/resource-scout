"""Deadline snapshots of completed Scout proposals, never curation approvals.

The strict completed-project builder remains unchanged. This explicit delivery
path keeps unfinished or unsafe-to-apply office records and reports every hold.
"""
from __future__ import annotations

import base64
import html
import json
import re
import sqlite3
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path

from .improvement_packages import ImprovementError, digest, write_package
from .open_questions import attach_questions, make_questions
from .scout_maintenance import MaintenanceWorkflow, validate_fields
from .scout_review import ScoutReviewFile, _replace_meta, render_scout_review_seed


@dataclass(frozen=True)
class MeetingEdition:
    review: ScoutReviewFile
    package: bytes
    manifest: dict


class ReadOnlyMaintenanceWorkflow(MaintenanceWorkflow):
    """A delivery reader; even inherited mutation methods cannot write."""
    def __init__(self, path):
        self.store = _ReadOnlyStore(path)


class _ReadOnlyStore:
    def __init__(self, path):
        self.path = Path(path).expanduser().resolve(strict=True)

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.path.as_uri() + '?mode=ro', uri=True)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
        finally:
            connection.close()


def build_meeting_edition(workflow, projects, *, location_name, created_at):
    """Read exact (project ID, revision) snapshots without modifying the run.

    Multiple projects must share the same current office package, as with a pilot
    and its continuation. No partially researched proposal enters the snapshot.
    """
    try:
        timestamp = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        if timestamp.tzinfo is None:
            raise ValueError('Timezone required')
    except (AttributeError, TypeError, ValueError) as error:
        raise ImprovementError('Creation timestamp needs a timezone') from error
    projects = list(projects)
    if not projects or len({pid for pid, _ in projects}) != len(projects):
        raise ImprovementError('Select unique project snapshots')
    loaded = []
    package = None
    with workflow.store.connect() as connection:
        connection.execute('BEGIN')
        for pid, revision in projects:
            state = workflow._load(connection, pid)
            if state['revision'] != revision:
                raise ImprovementError('Research revision changed; refresh before delivery')
            if state['requiresReconnection']:
                raise ImprovementError('Reconnect the current office package before delivery')
            candidate = workflow._package(connection, state['latestSha256'] or state['baseSha256'])
            if package and candidate['sha256'] != package['sha256']:
                raise ImprovementError('Project snapshots must share the same current office package')
            package = candidate
            loaded.append((state, workflow._rows(connection, state, candidate)))

    seed = deepcopy(package['data'])
    originals = {r['id']: r for r in seed['resources']}
    resources = deepcopy(originals)
    manifest = {'createdAt': created_at, 'sourcePackageSha256': package['sha256'],
                'projects': [], 'appliedProposals': [], 'heldProposals': [],
                'pendingTasks': [], 'humanApprovalsCreated': 0,
                'kind': 'uncurated-research-checkpoint'}
    seen = set()
    for state, rows in loaded:
        pid = state['id']
        manifest['projects'].append({'projectId': pid, 'revision': state['revision']})
        complete = set()
        for tid, task in state['tasks'].items():
            if all(stage in task['results'] for stage, _ in workflow._task_stages(state, task)):
                complete.add(tid)
            else:
                manifest['pendingTasks'].append({'projectId': pid, 'taskId': tid})
        for row in rows:
            if row['taskId'] not in complete:
                continue
            rid = row['id']
            if rid in seen:
                raise ImprovementError('Multiple completed proposals target the same resource identity')
            seen.add(rid)
            provenance = {'kind': 'maintenance', 'projectId': pid, 'taskId': row['taskId'],
                          'itemId': rid, 'baseSha256': state['baseSha256'],
                          'researchRevision': state['revision'],
                          'resultSha256': digest(state['tasks'][row['taskId']]['results']['reconcile'])}
            hold = ('blocked office record' if row['blocked'] else
                    'already exported' if row['saved'] else
                    'newer office edits' if any(c['conflict'] for c in row['comparison'].values()) else
                    'uncertain service status' if row['status'] not in ('new', 'current', 'changed', 'moved', 'renamed') else '')
            if hold:
                manifest['heldProposals'].append({**provenance, 'name': row['program'],
                    'status': row['status'], 'reason': hold, 'questions': deepcopy(row['questions']),
                    'summary': row['summary'],
                    'sources': list(dict.fromkeys(row['sources'][i]['url'] for i in row['evidence']))})
                # Uncertain status needs a visible curator question, not a
                # silent retirement or an unannounced change to patron text.
                if hold == 'uncertain service status' and row['current']:
                    resource = deepcopy(row['current'])
                    if resource.get('lastModified'):
                        previous = datetime.fromisoformat(resource['lastModified'].replace('Z', '+00:00'))
                        if previous.tzinfo is None or timestamp <= previous:
                            raise ImprovementError('Delivery timestamp must follow the resource timestamp')
                    questions = row['questions'] or [{
                        'possibly-closed':'Should this resource be retired after confirming the closure?',
                        'identity':'Which program should this resource describe?',
                    }.get(row['status'],'Is this program currently available, and where should someone start?')]
                    urls = manifest['heldProposals'][-1]['sources']
                    explanation = row['summary'] + ('\n\nSources checked:\n' + '\n'.join(urls) if urls else '')
                    attach_questions(resource, make_questions([
                        {'question': q, 'explanation': explanation} for q in questions], provenance))
                    resource['lastModified'] = created_at
                    resource['scoutResearch'] = {**provenance, 'curationRequired': True,
                        'reviewStatus': 'held', 'sources': urls}
                    resources[rid] = resource
                    manifest['heldProposals'][-1]['questions'] = list(questions)
                continue
            resource = deepcopy(row['current']) if row['current'] else {
                'id': rid, 'categories': [], 'categoryFilters': {}, 'forGroups': [], 'pdfs': []}
            proposed = validate_fields(row['fields'], seed, state['writingGuidance'], new=not row['current'])
            resource.update(proposed)
            if resource.get('lastModified'):
                previous = datetime.fromisoformat(resource['lastModified'].replace('Z', '+00:00'))
                if previous.tzinfo is None or timestamp <= previous:
                    raise ImprovementError('Delivery timestamp must follow the resource timestamp')
            resource['lastModified'] = created_at
            urls = list(dict.fromkeys(row['sources'][i]['url'] for i in row['evidence']))
            explanation = row['summary'] + ('\n\nSources checked:\n' + '\n'.join(urls) if urls else '')
            attach_questions(resource, make_questions([
                {'question': q, 'explanation': explanation} for q in row['questions']], provenance))
            resource['scoutResearch'] = {**provenance, 'curationRequired': True, 'sources': urls}
            resources[rid] = resource
            manifest['appliedProposals'].append({**provenance, 'name': row['program'],
                'isNew': not bool(row['current']), 'status': row['status']})

    updated = {r['itemId'] for r in manifest['appliedProposals'] if not r['isNew']}
    manifest['retainedExistingIds'] = sorted(set(originals) - updated)
    manifest['counts'] = {'existing': len(originals), 'existingWithCompletedProposals': len(updated),
        'existingRetained': len(originals) - len(updated),
        'newProposals': sum(r['isNew'] for r in manifest['appliedProposals']),
        'heldProposals': len(manifest['heldProposals']), 'pendingTasks': len(manifest['pendingTasks'])}
    token = ''.join(c for c in location_name if c.isalnum())
    if not token:
        raise ImprovementError('Location needs a usable name')
    seed.update(resources=list(resources.values()), officeName='Auto' + token,
                packageCreatedAt=created_at, lastModified=created_at,
                scoutMeetingEdition=deepcopy(manifest))
    # Retain the source version: this is a draft, not a published office update.
    payload = write_package(seed, package['assets'])
    rendered = render_scout_review_seed(seed, location_name=location_name,
        source_sha256=package['sha256'], category_ids=[c['id'] for c in seed['categories']])
    document = rendered.content.decode('utf-8')
    artifact = re.search(r'<meta name="scout-review-artifact-id" content="([^"]+)"', document).group(1)
    document = _replace_meta(document, 'tso-storage-id', artifact)
    assets = {p: base64.b64encode(b).decode('ascii') for p, b in package['assets'].items()}
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
    counts = manifest['counts']
    notice = ('<aside id="scout-meeting-status" role="note" style="margin:12px;padding:12px;border:1px solid #aaa">'
        '<strong>Scout research checkpoint</strong> · Proposals for curation.<br>'
        f'{counts["existingWithCompletedProposals"]} existing resources have completed proposals; '
        f'{counts["newProposals"]} new resources are proposed. '
        f'{counts["existingRetained"]} existing resources retain their previous text. '
        f'{counts["pendingTasks"]} research tasks remain unfinished; '
        f'{counts["heldProposals"]} findings require separate follow-up. '
        'See the companion research overview for the unfinished work and questions.</aside>'
        '<style>@media print{#scout-meeting-status{display:none!important}}</style>')
    document = re.sub(r'(<body\b[^>]*>)', lambda m: m.group(1) + notice, document, count=1)
    document = document.replace('</body>', bootstrap + '</body>', 1)
    review = ScoutReviewFile(rendered.filename, document.encode('utf-8'), rendered.scout_version, rendered.scout_build)
    return MeetingEdition(review, payload, manifest)


def render_meeting_overview(edition, baseline):
    """Full details on screen; print only the overview or one chosen resource."""
    from .improvement_packages import read_package
    data = read_package(edition.package)['data']
    current = {r['id']: r for r in baseline['resources']}
    records = {r['id']: r for r in data['resources']}
    m = edition.manifest; c = m['counts']; esc = html.escape
    display_time = datetime.fromisoformat(m['createdAt'].replace('Z','+00:00')).strftime('%B %d, %Y at %H:%M %Z')
    labels = {'name':'Title','description':'Description','phone':'Phone','address':'Address',
              'hours':'Hours','website':'Website','informationText':'Information',
              'categories':'Categories','categoryFilters':'Types','forGroups':'Groups'}

    def text(value):
        return value if isinstance(value,str) else json.dumps(value,ensure_ascii=False,indent=2)

    def pair(before, after):
        a=re.findall(r'\s+|\S+',text(before)); b=re.findall(r'\s+|\S+',text(after)); left=[]; right=[]
        for op,i,j,k,l in SequenceMatcher(None,a,b,autojunk=False).get_opcodes():
            old=esc(''.join(a[i:j])); new=esc(''.join(b[k:l]))
            left.append(old if op=='equal' else '<strong>'+old+'</strong>')
            right.append(new if op=='equal' else '<strong>'+new+'</strong>')
        return '<div class="pair"><div><h4>Before</h4><pre>'+''.join(left)+'</pre></div><div><h4>Scout proposal</h4><pre>'+''.join(right)+'</pre></div></div>'

    cards=[]
    for entry in m['appliedProposals']:
        rid=entry['itemId']; r=records[rid]; prior=current.get(rid,{})
        body=''
        questions=[q for q in r.get('openQuestions',[]) if q.get('status')=='open']
        if questions:
            body+='<h3>Questions for the curator</h3>'
            for q in questions:
                body+='<p><strong>'+esc(q['question'])+'</strong></p><details><summary>Research details</summary><pre>'+esc(q.get('explanation',''))+'</pre></details>'
        for field,label in labels.items():
            if r.get(field,'') != prior.get(field,''):
                body+='<h3>'+label+'</h3>'+pair(prior.get(field,''),r.get(field,''))
        cards.append((r['name'],body or '<p>No patron-facing field changes.</p>'))
    for held in m['heldProposals']:
        body='<p><strong>Original resource retained: '+esc(held['reason'])+'.</strong></p>'
        for question in held['questions']:body+='<p>'+esc(question)+'</p>'
        body+='<pre>'+esc(held['summary'])+'</pre><h3>Sources checked</h3><ul>'
        body+=''.join('<li><a href="'+esc(u,quote=True)+'">'+esc(u)+'</a></li>' for u in held['sources'])+'</ul>'
        cards.append((held['name'],body))
    details=''
    for index,(name,body) in enumerate(cards):
        details+=f'<details class="resource" id="resource-{index}"><summary>{esc(name)}</summary><h2>{esc(name)}</h2><button type="button" onclick="printResource({index})">Print this resource</button>{body}</details>'
    names={c['id']:c['label'] for c in baseline['categories']}
    pending=[]
    for task in m['pendingTasks']:
        kind,rid=task['taskId'].split(':',1)
        name=current.get(rid,{}).get('name',names.get(rid,rid))
        pending.append('<li>'+esc(name)+(' — category discovery' if kind=='discovery' else '')+'</li>')
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Scout research checkpoint</title>
<style>body{{font:17px/1.45 system-ui,sans-serif;max-width:1100px;margin:24px auto;padding:0 16px;color:#182330}}button{{padding:9px 14px;cursor:pointer}}summary{{cursor:pointer;font-weight:650;padding:12px}}details{{border:1px solid #ccd3da;border-radius:6px;margin:12px 0;padding:8px}}.pair{{display:grid;grid-template-columns:1fr 1fr;gap:20px}}pre{{font:inherit;white-space:pre-wrap;overflow-wrap:anywhere}}strong{{font-weight:800}}@media(max-width:700px){{.pair{{grid-template-columns:1fr}}}}@media print{{button,.resource,.pending{{display:none!important}}body{{font-size:11pt;max-width:none;margin:0}}body.print-resource #overview{{display:none}}body.print-resource .resource.print-selected{{display:block!important;border:0}}body.print-resource .print-selected>summary{{display:none}}.pair{{grid-template-columns:1fr 1fr}}details details{{display:none}}}}</style></head><body>
<section id="overview"><h1>Scout research checkpoint</h1><p>Working proposals for curation · {esc(display_time)}</p><button type="button" onclick="window.print()">Print overview</button>
<h2>What Scout checked</h2><p>This edition includes only proposals that completed their assigned research and reconciliation. Research checks provider information, access, costs and service classifications. Independent checks follow the run’s selected assignments.</p>
<ul><li><strong>{c['existingWithCompletedProposals']}</strong> existing resources have completed proposals.</li><li><strong>{c['newProposals']}</strong> new resources are proposed.</li><li><strong>{c['existingRetained']}</strong> existing resources retain their previous text.</li><li><strong>{c['pendingTasks']}</strong> research tasks remain unfinished; <strong>{c['heldProposals']}</strong> findings are held for follow-up.</li></ul>
<h2>Questions to settle</h2><p>Open a resource below for its questions and comparisons. Changed wording is <strong>bold</strong>. Held findings leave the previous resource intact. Resolved curator answers and existing attachments are preserved. This checkpoint does not mark resources curated or retire them.</p>
<p>The companion HTML is the working resource editor. The research-draft ZIP contains these same proposals and retained resources; it is not a curated office release.</p></section>
<details class="pending"><summary>Unfinished research ({c['pendingTasks']} tasks)</summary><ul>{''.join(pending)}</ul></details>
{details}<script>function printResource(n){{document.body.classList.add('print-resource');const target=document.getElementById('resource-'+n);target.open=true;target.classList.add('print-selected');window.print();}}window.addEventListener('afterprint',()=>{{document.body.classList.remove('print-resource');document.querySelectorAll('.print-selected').forEach(e=>e.classList.remove('print-selected'));}});</script></body></html>'''
