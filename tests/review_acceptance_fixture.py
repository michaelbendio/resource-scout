"""Explicit supervisor acceptance for synthetic/sealed regression fixtures only."""
import json
from pathlib import Path
import tempfile

from resource_research_agent.review_acceptance import accept, JUDGMENTS
from resource_research_agent.review_decisions import file_sha


def accept_fixture(testcase, bundle_path):
    bundle_path = Path(bundle_path)
    bundle = json.loads(bundle_path.read_text())
    temporary = tempfile.TemporaryDirectory(prefix='scout-test-supervisor-')
    testcase.addCleanup(temporary.cleanup)
    audit = Path(temporary.name)
    report = bundle_path.parent/'report.md'
    if not report.exists():
        report.write_text('Synthetic fixture review; not an acceptance of a production office.\n')
    categories = []
    for cid in bundle['payload']['scope']['categoryIds']:
        available = [r['id'] for r in bundle['payload']['resources'] if cid in r['categories']]
        categories.append(dict(categoryId=cid, sampleResourceIds=available[:1], finding='Explicit synthetic fixture audit.'))
    findings = {key:'Explicit fixture judgment for regression testing only.' for key in JUDGMENTS}
    findings['categoryChecks'] = categories
    (audit/'findings.json').write_text(json.dumps(findings))
    (audit/'adapter.json').write_text(json.dumps(dict(compatibilityReason='Explicit pre-contract regression fixture, never production auto-acceptance.',
        content={k:bundle[k] for k in ('payload','assessments','candidateReview','restoredCandidates') if k in bundle},
        decisionFiles=[dict(path=str(bundle_path.resolve()), sha256=file_sha(bundle_path))])))
    result = audit/'acceptance.json'
    accept(bundle_path, audit/'findings.json', result, reviewer='Synthetic test supervisor', preserved_evidence_path=audit/'adapter.json')
    return result
