"""Read-only starter and five-more evaluation, not a curation application."""
from __future__ import annotations

import argparse
from html import escape
import json
from pathlib import Path

from .prepared_resources import validate_artifact


def preview_groups(artifact, category_id):
    resources = {r['id']: r for r in artifact['resources']}
    starter = next(s for s in artifact['starterSets'] if s['categoryId'] == category_id)
    category_types = {t['id'] for t in artifact['taxonomy']['types'] if t['categoryId'] == category_id}
    covered = {tid for m in starter['members'] for tid in resources[m['resourceId']]['types']} & category_types
    others = [dict(resource=resources[c['resourceId']], reason=c['reason']) for c in artifact['considerations'] if c['categoryId'] == category_id]
    usable = [r for r in others if r['resource']['state'] == 'usable']
    usable.sort(key=lambda r: (not bool((set(r['resource']['types']) & category_types) - covered),
                               r['resource']['name'].casefold(), r['resource']['id']))
    unresolved = sorted((r for r in others if r['resource']['state'] != 'usable'), key=lambda r: r['resource']['name'].casefold())
    return starter, usable, unresolved, covered


def render_preview(artifact):
    validate_artifact(artifact)
    resources = {r['id']: r for r in artifact['resources']}
    labels = {c['id']: c['label'] for c in artifact['taxonomy']['categories']}
    title = artifact['office']['name'] + ' — starters and five more'
    introduction = ('Read-only evaluation. The first five alternatives add a Type absent from the starter set first, '
        'then sort alphabetically; this is a preview, not a stored rank. WSRS-TSO will use actual curated Type coverage. '
        'No resource is marked Curated here. Items needing resolution stay in the administrator list.')
    md = ['# ' + title, '', introduction, '']
    html = ['<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
        '<title>' + escape(title) + '</title><style>body{font:17px/1.5 system-ui;margin:2rem auto;max-width:950px;padding:0 1rem;color:#253443;background:#f7f8fa}h1,h2{color:#173c54}section{margin:2rem 0}article,details{background:white;border:1px solid #dce1e5;border-radius:8px;padding:1rem;margin:.7rem 0}h3{margin:0 0 .4rem}p{margin:.4rem 0}.muted{color:#546270}summary{cursor:pointer;font-weight:600}.warning{border-left:5px solid #a66b1a}a{color:#175f8f}</style>',
        '<h1>' + escape(title) + '</h1><p>' + escape(introduction) + '</p>']
    def card(resource, reason, limitation=None):
        name = escape(resource['name'])
        result = '<article><h3>' + name + '</h3><p>' + escape(reason) + '</p>'
        if limitation:
            result += '<p class="muted">' + escape(limitation) + '</p>'
        return result + '</article>'
    for cid in artifact['scope']['categoryIds']:
        starter, others, unresolved, covered = preview_groups(artifact, cid)
        name = labels[cid]
        md.extend(['## ' + name, '', starter['rationale'], '', '### Starter set', ''])
        html.extend(['<section><h2>' + escape(name) + '</h2><p>' + escape(starter['rationale']) + '</p><h3>Starter set</h3>'])
        for m in starter['members']:
            r = resources[m['resourceId']]
            md.extend([f"- **{r['name']}** — {m['contribution']} Limitation: {m['limitation']}", ''])
            html.append(card(r, m['contribution'], m['limitation']))
        html.append('<p class="muted">Gaps: ' + escape(starter['gaps']) + '</p>')
        md.extend(['Gaps: ' + starter['gaps'], ''])
        for offset in range(0, len(others), 5):
            heading = 'First five more to consider' if offset == 0 else f'More to consider ({offset+1}–{min(offset+5, len(others))})'
            md.extend(['### ' + heading, ''])
            html.append('<details' + (' open' if offset == 0 else '') + '><summary>' + escape(heading) + '</summary>')
            for item in others[offset:offset+5]:
                md.extend([f"- **{item['resource']['name']}** — {item['reason']}", ''])
                html.append(card(item['resource'], item['reason']))
            html.append('</details>')
        if unresolved:
            md.extend(['### Administrator resolution needed', ''])
            html.append('<details class="warning"><summary>Administrator resolution needed (' + str(len(unresolved)) + ')</summary>')
            for item in unresolved:
                md.extend([f"- **{item['resource']['name']}** — {item['reason']}", ''])
                html.append(card(item['resource'], item['reason'], item['resource'].get('resolutionReason')))
            html.append('</details>')
        html.append('</section>')
    html.append('</html>')
    return '\n'.join(md), '\n'.join(html)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('artifact', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    markdown, html = render_preview(json.loads(args.artifact.read_text()))
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output/'starters-and-five-more.md').write_text(markdown)
    (args.output/'starters-and-five-more.html').write_text(html)


if __name__ == '__main__': main()
