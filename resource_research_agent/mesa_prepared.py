"""Reviewed, reproducible four-category Mesa migration (no new research calls).

All semantic choices live in docs/prepared/mesa-four-category-review.json and the
accepted starter proposal. Unknown labels or changed inputs stop compilation.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re

from .preparation_contract import (POLICY_VERSION, LEGACY_INFORMATION_HEADINGS,
                                   assemble_information, information_sections)
from .prepared_export import review_fingerprint, encoded
from .prepared_resources import require, source_catalog, source_id
from .resource_identity import fingerprint
from .starter_trial import compile_trial


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def check_attestation(bundle, attestation):
    require(bundle['review']['inputFingerprint'] == attestation.get('reviewFingerprint')
            and fingerprint(bundle['payload']) == attestation.get('payloadFingerprint'),
            'Changed Mesa review/output requires renewed judgment; do not auto-update the attestation')


def compile_mesa(seed_bytes, state_bytes, decisions_bytes, proposal_bytes, config, office_categories):
    inputs = dict(seedSha256=sha(seed_bytes), stateSha256=sha(state_bytes),
                  decisionsSha256=sha(decisions_bytes), proposalSha256=sha(proposal_bytes))
    for key, digest in inputs.items():
        require(config[key] == digest, f"Changed reviewed input: {key}")
    inputs.update(configFingerprint=fingerprint(config), officeCategoryFingerprint=fingerprint(office_categories))
    require({c['id'] for c in office_categories} == set(config['officeCategoryIds']),
            "Mesa office category IDs changed; stop and reconcile, never translate by label")
    trial = compile_trial(seed_bytes, state_bytes, json.loads(proposal_bytes))
    seed, state, decisions = json.loads(seed_bytes), json.loads(state_bytes), json.loads(decisions_bytes)
    require(not state.get('curatedResourceIds'), "Review existing human approvals before this initial Mesa migration")
    by_id = {r['id']: deepcopy(r) for r in seed['resources']}
    for override in state.get('resourceOverrides', []):
        by_id[override['id']].update(deepcopy(override))
    source_decisions = {r['id']: next(d for d in decisions if d['n'] == n)
                        for n, r in enumerate(seed['resources'], 1)}
    require(all(d.get('resourceId', rid) == rid for rid, d in source_decisions.items()),
            'Reviewed decision numbering no longer matches source identities')
    scope = config['scope']
    scoped = {rid: r for rid, r in by_id.items() if set(scope).intersection(r['categories'])}
    hidden = set(state.get('deletedResourceIds', [])) & set(scoped)

    def resolve(prefix):
        matches = [rid for rid in scoped if rid.startswith(prefix)]
        require(len(matches) == 1, f"Unknown/ambiguous reviewed reference: {prefix}")
        return matches[0]

    memberships = {rid: [a for s in trial['starterSets'] for a in s['assessments'] if a['resourceId'] == rid]
                   for rid in scoped}
    audit, identity_groups, merge_target = {}, {}, {}
    for item in config['merges']:
        primary = resolve(item['primary'])
        group = [primary, *(resolve(p) for p in item['members'])]
        require(not hidden.intersection(group), "Cannot merge a hidden record into a visible resource")
        require(not set(group).intersection(merge_target), "Repeated merge member")
        identity_groups[primary] = dict(members=group, label=item['name'], reason=item['reason'])
        merge_target.update({rid: primary for rid in group[1:]})
    not_offered = {resolve(k): v for k, v in config['notOffered'].items()}
    unresolved = {resolve(k): v for k, v in config['needsResolution'].items()}
    removals = {resolve(k): v for k, v in config['removeMemberships'].items()}
    descriptions = {resolve(k): v for k, v in config['descriptionOverrides'].items()}
    populations = {resolve(k): v for k, v in config.get('populationOverrides', {}).items()}
    program_labels = {resolve(k): v for k, v in config.get('programLabels', {}).items()}
    require(not (set(not_offered) & (set(unresolved) | set(merge_target))), "Conflicting reviewed state decisions")

    types, type_map = [], {}
    for cid, entries in config['typeCatalog'].items():
        for stable_key, label, definition, aliases in entries:
            tid = f'type_mesa_{cid}_{stable_key}'
            types.append(dict(id=tid, categoryId=cid, label=label, definition=definition))
            for alias in aliases:
                require((cid, alias) not in type_map, "Ambiguous Type consolidation")
                type_map[cid, alias] = tid
    group_labels = sorted({g for r in scoped.values() for g in r['forGroups']})
    # These initial identifiers are recorded in the delivered catalog. Later
    # label edits must reuse that catalog ID, not rerun this initial allocation.
    group_map = {g: 'group_mesa_' + re.sub(r'[^a-z0-9]+', '-', g.lower()).strip('-') for g in group_labels}
    groups = [dict(id=group_map[g], label=g, definition=seed['forGroupDefinitions'][g]['description']) for g in group_labels]

    sources, resources, identities = [], [], []
    for rid, original in scoped.items():
        assessment = dict(state='usable', reason='Retained as a supported prepared resource from the completed Mesa review.',
                          memberships=memberships[rid], groupEvidence=deepcopy(source_decisions[rid]['groups']),
                          groupReason=source_decisions[rid].get('groupReason') or source_decisions[rid].get('semanticReason', ''),
                          noGroupDecision=not original['forGroups'])
        audit[rid] = assessment
        if rid in merge_target:
            assessment.update(state='merged', target=merge_target[rid], reason=identity_groups[merge_target[rid]]['reason'])
            continue
        identity = identity_groups.get(rid, dict(members=[rid], label=original['name'],
            reason='Retain the reviewed program as a distinct identity; no unsupported same-organization merge.'))
        identities.append(identity)
        if rid in hidden:
            assessment.update(state='suppressed', reason='Preserve the saved human-hidden decision; never resurrect through this export.')
            continue
        if rid in not_offered:
            assessment.update(state='not-offered', reason=not_offered[rid])
            continue
        if rid in unresolved:
            assessment.update(state='needs-resolution', reason=unresolved[rid])
        constituents = [scoped[mid] for mid in identity['members']]
        sections, urls, categories, tids, gids, service_text = {}, [], set(), set(), set(), []
        for constituent in constituents:
            mid = constituent['id']
            old = information_sections(constituent['informationText'], LEGACY_INFORMATION_HEADINGS)
            for heading, body in old.items():
                if len(constituents) > 1:
                    body = f"**{program_labels[mid]}:** {body}"
                sections.setdefault(heading, [])
                if body not in sections[heading]:
                    sections[heading].append(body)
            description = descriptions.get(mid, constituent['description'])
            if description not in service_text:
                service_text.append(description)
            for cid in constituent['categories']:
                if cid in scope and cid not in removals.get(mid, {}):
                    categories.add(cid)
                    for label in constituent['categoryFilters'].get(cid, []):
                        require((cid, label) in type_map, f"Unreviewed Type: {cid}/{label}")
                        tids.add(type_map[cid, label])
            gids.update(group_map[g] for g in constituent['forGroups'])
            urls.extend(source_decisions[mid].get('sources', []))
            # Keep the reviewed source URLs already embedded beside facts too.
            urls.extend(re.findall(r'https?://[^\s<>\[\]"\)]+', constituent['informationText'] + ' ' + constituent['website']))
        limitations = [m['limitation'] for s in trial['starterSets'] for m in s['members'] if m['resourceId'] in identity['members']]
        cautions = [*sections['Important Information to Know'], *limitations]
        if rid in unresolved:
            cautions.insert(0, unresolved[rid])
        clean_urls = sorted({u.rstrip('.,;:') for u in urls})
        sources.extend(dict(url=u, title=identity['label'] + ' — research source') for u in clean_urls)
        join = lambda paragraphs: '\n\n'.join(dict.fromkeys(paragraphs))
        information = assemble_information({
            'Services Offered': join(service_text),
            'Eligibility Requirements': join(sections['Eligibility Requirements']),
            'Population Served': populations.get(rid, join(sections['Eligibility Requirements'])),
            'How to Best Connect': join([*sections['How to Best Connect'], *sections['Access']]),
            'Important Information to Know': join(cautions),
        })
        resource = dict(id=rid, state=assessment['state'], name=identity['label'],
            description=join(service_text), informationText=information,
            categories=[c for c in scope if c in categories], types=sorted(tids), forGroups=sorted(gids),
            sourceIds=[source_id(u) for u in clean_urls], researchedAt='2026-09-24')
        for key in ('phone', 'address', 'website', 'email', 'hours'):
            resource[key] = original.get(key) or ''
        if rid in unresolved:
            resource['resolutionReason'] = unresolved[rid]
        if rid in removals:
            assessment['removedMemberships'] = removals[rid]
        resources.append(resource)

    sets = []
    for starter in trial['starterSets']:
        members = []
        for m in starter['members']:
            members.append(dict(resourceId=merge_target.get(m['resourceId'], m['resourceId']),
                position=m['position'], contribution=m['contribution'], limitation=m['limitation']))
        sets.append(dict(categoryId=starter['categoryId'], rationale=starter['rationale'],
                         gaps=starter['gaps'], members=members))
    selected = {(m['resourceId'], s['categoryId']) for s in sets for m in s['members']}
    expected = {(r['id'], cid) for r in resources for cid in r['categories']} - selected
    considerations = [dict(resourceId=resolve(ref), categoryId=cid, reason=reason)
                      for cid, entries in config['considerations'].items() for ref, reason in entries.items()]
    require({(c['resourceId'], c['categoryId']) for c in considerations} == expected,
            'Authored considerations must cover exactly every non-starter membership')
    bundle = dict(artifactType='scout-reviewed-preparation', policyVersion=POLICY_VERSION,
        sourceNamespace=config['sourceNamespace'], inputs=inputs, officeCategoryIds=config['officeCategoryIds'],
        identityDecisions=identities, assessments=audit,
        payload=dict(office=config['office'], scope=dict(categoryIds=scope, completeScope=True, completeOffice=False,
            note='Only Housing, Food, Transportation and ID Recovery; other Mesa categories are outside this snapshot.'),
            taxonomy=dict(categories=office_categories, types=types, forGroups=groups),
            sources=source_catalog(sources), resources=resources, starterSets=sets, considerations=considerations))
    bundle['review'] = dict(reviewer='Codex, requested Extra High review; starter trial accepted by Michael',
        reviewedAt=config['reviewedAt'], identity='Three explicit same-program consolidations; no organization-wide merging. Other identities retain their reviewed program boundary.',
        content='Migration of completed Mesa content review plus accepted trial cautions. Unsupported memberships excluded and unresolved referrals quarantined. No new whole-collection research or agency verification claimed. ' + config['populationPolicy'],
        taxonomy=config['taxonomyJudgment'], starterSets='Michael accepted the four-category trial. All 37 positions and contribution/limitation explanations retained; shared identities are one resource. Non-starter reasons were written individually for curators and compared with the actual selected set; overlapping services are not described as extra capacity.',
        preservation=config['preservationJudgment'], inputFingerprint=review_fingerprint(bundle))
    return bundle


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-dir', type=Path, default=Path('data/mesa-review-20260924'))
    parser.add_argument('--office-file', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(Path('docs/prepared/mesa-four-category-review.json').read_text())
    config['considerations'] = json.loads(Path('docs/prepared/mesa-considerations-20260925.json').read_text())
    match = re.search(r'<script[^>]+id=["\x27]seed-data["\x27][^>]*>(.*?)</script>', args.office_file.read_text(), re.S)
    require(match is not None, 'Office file has no seed-data; do not infer category IDs')
    office_categories = [{k: c[k] for k in ('id', 'label')} for c in json.loads(match[1])['categories']]
    bundle = compile_mesa((args.source_dir / 'after-seed.json').read_bytes(),
        (args.source_dir / 'browser-state-reconciled-v3.json').read_bytes(),
        (args.source_dir / 'final-decisions.json').read_bytes(),
        Path('docs/trials/mesa-starter-proposal-20260925.json').read_bytes(), config, office_categories)
    check_attestation(bundle, json.loads(Path('docs/prepared/mesa-review-attestation.json').read_text()))
    raw = encoded(bundle)
    require(not args.output.exists() or args.output.read_bytes() == raw, 'Refusing to replace a reviewed bundle')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(raw)
    print(json.dumps(dict(resources=len(bundle['payload']['resources']), assessed=len(bundle['assessments']))))


if __name__ == '__main__':
    main()
