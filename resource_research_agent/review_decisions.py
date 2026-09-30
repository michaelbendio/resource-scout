"""Compile explicit, bounded review decisions without generating any judgments."""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from .prepared_resources import require, text
from .resource_identity import fingerprint

CONTENT_FIELDS = ('name', 'description', 'phone', 'address', 'website', 'email', 'hours', 'informationText')
RULES = ('reach', 'mainService', 'directContact', 'agencyBoundary')


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def load_documents(manifest_path):
    path = Path(manifest_path).resolve()
    manifest = read(path)
    require(manifest.get('schemaVersion') == 1, 'Unsupported review decision contract')
    documents, hashes = {}, {}
    for section in ('resourceBatches', 'candidateBatches', 'categories', 'collection'):
        refs = manifest.get(section)
        if section == 'collection':
            refs = [refs]
        require(isinstance(refs, list) and refs, f'Missing decision documents: {section}')
        documents[section] = []
        for ref in refs:
            require(isinstance(ref, dict) and text(ref.get('path')), 'Decision reference needs a path')
            source = (path.parent / ref['path']).resolve()
            require(source.is_relative_to(path.parent) and source != path, 'Decision file must stay inside review workspace')
            digest = file_sha(source)
            require(digest == ref.get('sha256'), f'Stale decision file: {ref["path"]}')
            require(str(source) not in hashes, 'Repeated decision document')
            hashes[str(source)] = digest
            documents[section].append(read(source))
    return manifest, documents, hashes


def assemble(manifest_path, drafts):
    """Return the entire content view, selections and exact decision-file bindings."""
    manifest, docs, hashes = load_documents(manifest_path)
    originals = {r['id']: r for r in drafts['resources']}
    require(len(originals) == len(drafts['resources']), 'Duplicate input draft')
    collection = docs['collection'][0]
    for field in ('taxonomyJudgment', 'identityBoundaryJudgment', 'preservationJudgment'):
        require(text(collection.get(field)), f'Missing collection judgment: {field}')
    base = deepcopy(collection['payloadBase'])
    require(set(base) == {'office', 'scope', 'taxonomy', 'sources'}, 'Collection payloadBase has unexpected/missing fields')
    restored = collection.get('restoredCandidates', {})
    require(isinstance(restored, dict) and not set(restored).intersection(originals), 'Invalid restored candidate IDs')
    resources, assessments = {}, {}
    for batch in docs['resourceBatches']:
        rows = batch.get('decisions')
        require(isinstance(rows, list) and 1 <= len(rows) <= 15, 'Resource batches require 1-15 explicit decisions')
        for row in rows:
            rid = row['resourceId']
            require(rid not in assessments and rid in set(originals) | set(restored), 'Unknown or repeated resource decision')
            original = originals.get(rid)
            require(row.get('inputFingerprint') == (fingerprint(original) if original else None), 'Resource decision input changed')
            assessment = row['assessment']
            require(assessment.get('state') in {'usable', 'needs-resolution', 'merged', 'not-offered', 'suppressed'}
                    and text(assessment.get('reason')), 'Missing authored assessment')
            require(isinstance(row.get('evidence'), list) and row['evidence']
                    and all(text(e.get('reference')) and text(e.get('finding')) for e in row['evidence']),
                    'Resource decision needs specific evidence')
            result = row.get('result')
            retained = assessment['state'] in {'usable', 'needs-resolution'}
            require(isinstance(result, dict) if retained else result is None, 'Disposition/result mismatch')
            categories = set(original.get('categories', [])) if original else set()
            if retained:
                require(result.get('id') == rid and result.get('state') == assessment['state'], 'Resource identity/state disagrees')
                categories.update(result['categories'])
                field_decisions = row.get('fieldDecisions', {})
                require(set(field_decisions) == set(CONTENT_FIELDS), 'Every content field needs a retain/replace decision')
                for field in CONTENT_FIELDS:
                    decision = field_decisions[field]
                    require(decision.get('action') in {'retain', 'replace'} and text(decision.get('reason')), 'Missing field judgment')
                    require(field in result, 'Missing explicit final field value')
                    if decision['action'] == 'retain':
                        require(original is not None and result[field] == original.get(field, ''), 'Retained field changed')
                    else:
                        require('value' in decision and result[field] == decision['value'], 'Reviewed correction not applied')
                require(set(row.get('typeEvidence', {})) == set(result['types'])
                        and all(text(v) for v in row['typeEvidence'].values()), 'Type assignment lacks evidence')
                require(set(row.get('groupEvidence', {})) == set(result['forGroups'])
                        and all(text(v) for v in row['groupEvidence'].values()), 'Group assignment lacks evidence')
                if not result['forGroups']:
                    require(text(row.get('noGroupReason')), 'Missing explicit no-group decision')
                resources[rid] = deepcopy(result)
            findings = row.get('ruleFindings', {})
            require(set(findings) == categories, 'Office-fit review must cover each original/final category membership')
            require(all(all(text(values.get(rule)) for rule in RULES) for values in findings.values()), 'Missing office-fit judgment')
            assessments[rid] = deepcopy(assessment)
    require(set(assessments) == set(originals) | set(restored), 'Resource decision coverage incomplete')
    candidates, seen = [], set()
    for batch in docs['candidateBatches']:
        rows = batch.get('decisions')
        require(isinstance(rows, list) and 1 <= len(rows) <= 30, 'Candidate batches require 1-30 authored decisions')
        for row in rows:
            key = (row['categoryId'], str(row['candidateId']))
            require(key not in seen and text(row.get('reason')), 'Repeated or unsupported candidate decision')
            require(row.get('decision') in {'retain', 'exclude'}
                    and isinstance(row.get('resourceIds'), list)
                    and set(row['resourceIds']) <= set(resources)
                    and bool(row['resourceIds']) == (row['decision'] == 'retain'), 'Candidate disposition or references invalid')
            require(isinstance(row.get('evidence'), list) and row['evidence']
                    and all(text(e.get('reference')) and text(e.get('finding')) for e in row['evidence']),
                    'Candidate decision needs specific evidence')
            seen.add(key)
            candidates.append(deepcopy(row))
    starters, considerations, selections = [], [], []
    scope, visited = set(base['scope']['categoryIds']), set()
    for category in docs['categories']:
        cid = category['categoryId']
        require(cid in scope and cid not in visited, 'Unexpected/repeated category finalization')
        visited.add(cid)
        require(text(category.get('taxonomyJudgment')) and text(category.get('stoppingReason')), 'Missing taxonomy/selection judgment')
        starter = category['starterSet']
        require(starter['categoryId'] == cid, 'Wrong starter category')
        starter_ids = {m['resourceId'] for m in starter['members']}
        require(len(starter_ids) == len(starter['members']) and all(
            rid in resources and cid in resources[rid]['categories'] and resources[rid]['state'] == 'usable'
            for rid in starter_ids), 'Invalid starter selection')
        expected = {rid for rid, r in resources.items() if cid in r['categories']} - starter_ids
        reasons = category['considerations']
        require(len(reasons) == len(expected) and {r['resourceId'] for r in reasons} == expected
                and all(r['categoryId'] == cid and text(r.get('reason')) for r in reasons), 'Non-starter reasons incomplete')
        complements = category['complements']
        require([r['position'] for r in complements] == list(range(1, len(complements)+1)), 'Complements need explicit consecutive order')
        selected = set()
        for member in complements:
            rid = member['resourceId']
            require(rid in expected and rid not in selected and resources[rid]['state'] == 'usable', 'Invalid complementary selection')
            require(all(text(member.get(k)) for k in ('contribution', 'limitation', 'remainingGaps')), 'Complement contribution/limits/gaps missing')
            selected.add(rid)
        starters.append(deepcopy(starter))
        considerations.extend(deepcopy(reasons))
        selections.append(deepcopy(category))
    require(visited == scope, 'Category finalization coverage incomplete')
    for section in ('types', 'forGroups'):
        labels = [(r.get('categoryId') if section == 'types' else '', ' '.join(r['label'].split()).casefold())
                  for r in base['taxonomy'][section]]
        require(len(labels) == len(set(labels)), 'Duplicate normalized taxonomy label')
    base.update(resources=[resources[k] for k in sorted(resources)],
                starterSets=sorted(starters, key=lambda r:r['categoryId']),
                considerations=sorted(considerations, key=lambda r:(r['categoryId'], r['resourceId'])))
    content = dict(payload=base, assessments=assessments,
                   candidateReview=sorted(candidates, key=lambda r:(r['categoryId'], str(r['candidateId']))),
                   restoredCandidates=restored)
    return content, selections, hashes


def verify_bundle(bundle, manifest_path, drafts_path):
    manifest_path, drafts_path = Path(manifest_path), Path(drafts_path)
    require(bundle['inputs'].get('decisionManifestSha256') == file_sha(manifest_path), 'Decision manifest missing or changed')
    require(read(manifest_path).get('draftsSha256') == file_sha(drafts_path), 'Decision inputs changed')
    content, selections, hashes = assemble(manifest_path, read(drafts_path))
    require(content == {k:bundle[k] for k in content}, 'Bundle differs from explicit review decisions')
    return hashes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True, type=Path)
    parser.add_argument('--drafts', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    require(read(args.manifest).get('draftsSha256') == file_sha(args.drafts), 'Decision inputs changed')
    content, selections, _ = assemble(args.manifest, read(args.drafts))
    args.output.write_text(json.dumps(content, indent=2, ensure_ascii=False)+'\n')
    args.output.with_name('reviewed-selections.json').write_text(json.dumps(selections, indent=2, ensure_ascii=False)+'\n')
    print('Compiled explicit decisions; supervisor acceptance is still required.')


if __name__ == '__main__':
    main()
