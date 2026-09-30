"""Supervisor-owned acceptance, separate from a review worker's completion claim."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from .prepared_resources import require, text
from .review_decisions import file_sha, read, verify_bundle

JUDGMENTS = ('content', 'taxonomy', 'selections', 'assembly', 'identity', 'preservation')


def accept(bundle_path, findings_path, output_path, *, reviewer, drafts_path=None,
           manifest_path=None, preserved_evidence_path=None):
    """Called by the supervising assistant AFTER substantive inspection.

    This is an operational role boundary, not a cryptographic sandbox. The worker
    is instructed to write only in review/, never the supervisor's audit/receipt.
    """
    bundle_path, findings_path, output_path = map(lambda p:Path(p).resolve(),
                                                  (bundle_path, findings_path, output_path))
    require(not output_path.is_relative_to(bundle_path.parent)
            and not findings_path.is_relative_to(bundle_path.parent),
            'Supervisor findings and acceptance must be outside the worker review workspace')
    require(text(reviewer), 'Supervisor identity missing')
    bundle, findings = read(bundle_path), read(findings_path)
    require(all(text(findings.get(k)) for k in JUDGMENTS), 'Substantive supervisor findings are required')
    scope = set(bundle['payload']['scope']['categoryIds'])
    categories = findings.get('categoryChecks', [])
    require(len(categories) == len(scope) and {r['categoryId'] for r in categories} == scope,
            'Supervisor audit must cover every category')
    by_id = {r['id']:r for r in bundle['payload']['resources']}
    for row in categories:
        cid, samples = row['categoryId'], row.get('sampleResourceIds')
        available = {rid for rid,r in by_id.items() if cid in r['categories']}
        require(text(row.get('finding')) and isinstance(samples, list)
                and len(samples) == len(set(samples)) and set(samples) <= available
                and (bool(samples) or not available), 'Category audit needs actual resource samples or an empty-category finding')
    evidence = {str(findings_path):file_sha(findings_path)}
    if 'decisionManifestSha256' in bundle['inputs']:
        require(manifest_path is not None and drafts_path is not None, 'Acceptance requires the bound decisions and draft inputs')
        evidence.update(verify_bundle(bundle, manifest_path, drafts_path))
        evidence[str(Path(manifest_path).resolve())] = file_sha(manifest_path)
        evidence[str(Path(drafts_path).resolve())] = file_sha(drafts_path)
        mode = 'structured-decisions-v1'
    else:
        # Existing sealed reviews may be adapted without repeating their work.
        # The supervisor must explicitly bind their authored files and verify
        # the complete resulting content, rather than silently grandfather them.
        require(preserved_evidence_path is not None, 'Structured decisions required; existing reviews need an explicit supervisor adapter')
        path = Path(preserved_evidence_path).resolve()
        adapter = read(path)
        require(text(adapter.get('compatibilityReason')) and adapter.get('content') ==
                {k:bundle[k] for k in ('payload','assessments','candidateReview','restoredCandidates') if k in bundle},
                'Preserved review adapter does not describe the reviewed output')
        require(adapter.get('decisionFiles'), 'Preserved review requires its original authored decisions')
        for ref in adapter['decisionFiles']:
            source = (path.parent / ref['path']).resolve()
            require(file_sha(source) == ref['sha256'], 'Preserved decision changed')
            evidence[str(source)] = ref['sha256']
        evidence[str(path)] = file_sha(path)
        mode = 'explicit-preserved-review-adapter'
    report = bundle_path.parent/'report.md'
    require(report.is_file() and text(report.read_text()), 'Acceptance requires a readable review report')
    evidence[str(report)] = file_sha(report)
    receipt = dict(artifactType='scout-supervisor-acceptance', schemaVersion=1,
        acceptedAt=datetime.now(timezone.utc).isoformat(), reviewer=reviewer,
        bundleSha256=file_sha(bundle_path), reviewFingerprint=bundle['review']['inputFingerprint'],
        mode=mode, evidenceFiles=evidence,
        rule='Supervisor accepted this exact reviewed submission; no office approval or agency verification is implied.')
    require(not output_path.exists(), 'Preserve the earlier acceptance receipt; use a new path')
    output_path.write_text(json.dumps(receipt, indent=2)+'\n')
    return receipt


def verify_acceptance(bundle_path, acceptance_path):
    require(acceptance_path is not None, 'Supervisor acceptance required before export or registry allocation')
    path, bundle_path = Path(acceptance_path).resolve(), Path(bundle_path).resolve()
    require(not path.is_relative_to(bundle_path.parent), 'Worker workspace cannot supply supervisor acceptance')
    receipt, bundle = read(path), read(bundle_path)
    require(receipt.get('artifactType') == 'scout-supervisor-acceptance' and receipt.get('schemaVersion') == 1
            and text(receipt.get('reviewer')) and text(receipt.get('acceptedAt'))
            and receipt.get('mode') in {'structured-decisions-v1', 'explicit-preserved-review-adapter'},
            'Invalid supervisor acceptance')
    require(receipt.get('bundleSha256') == file_sha(bundle_path)
            and receipt.get('reviewFingerprint') == bundle['review']['inputFingerprint'], 'Supervisor acceptance is stale')
    evidence = receipt.get('evidenceFiles')
    require(isinstance(evidence, dict) and evidence, 'Acceptance evidence missing')
    for source, digest in evidence.items():
        require(file_sha(source) == digest, 'Accepted review evidence changed')
    return receipt


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for key in ('bundle', 'findings', 'output'):
        p.add_argument('--'+key, required=True, type=Path)
    p.add_argument('--reviewer', required=True)
    p.add_argument('--drafts', type=Path)
    p.add_argument('--manifest', type=Path)
    p.add_argument('--preserved-evidence', type=Path)
    a=p.parse_args()
    accept(a.bundle, a.findings, a.output, reviewer=a.reviewer, drafts_path=a.drafts,
           manifest_path=a.manifest, preserved_evidence_path=a.preserved_evidence)
    print('Exact submission accepted by supervisor; export remains a separate operation.')


if __name__ == '__main__':
    main()
