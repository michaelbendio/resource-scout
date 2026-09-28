"""Reviewer packets and explicit advancement decisions; never provider dispatch."""
import json
import random
from pathlib import Path
from .providers import experiment_label
from .protocol import EvaluationError, verify_protocol, read, write_once, file_hash, digest, identifier


def build_audit_packet(root, category='housing'):
    root=Path(root); identifier(category); manifest=verify_protocol(root)
    if category not in manifest['categories']:raise EvaluationError('Category outside protocol')
    summary_path=root/'results'/manifest['condition']/category/'summary.json'
    if not summary_path.exists():raise EvaluationError('Completed research required for a scored comparison')
    summary=read(summary_path)
    if summary.get('status')!='completed-research-awaiting-source-audit':raise EvaluationError('Research incomplete')
    history=read(root/'reference/baseline.json')['categories'][category]
    original=[]
    for answer in history['answers']:
        if answer.get('parse_error'):raise EvaluationError('Historical parsing error requires reviewer resolution')
        parsed=json.loads(answer['parsed_json'])
        original.extend(parsed['leads'])
    fresh=[]
    evidence=[]
    for path in sorted(summary_path.parent.glob('*-original.json')):
        value=read(path);fresh.extend(value['result']['leads'])
        evidence.append(dict(path=str(path.relative_to(root)),sha256=file_hash(path)))
    labels=['A','B'];random.Random(read(root/'config.json')['sampleSeed']).shuffle(labels)
    from ..importer import ResourcePackageImporter
    baseline=ResourcePackageImporter(category).read(root/'inputs/office-package.zip')
    packet=dict(category=category,evaluationOnly=True,importable=False,
        criteria=read(root/'audit/criteria.json'),
        commonKnownResources=baseline.target_resources,
        collections={labels[0]:original,labels[1]:fresh},
        limitations=['Labels conceal explicit provider attribution only; a reviewer may recognize historical examples.',
                    'Raw lead counts are not unique useful routes or quality scores.'],
        protocolSha256=file_hash(root/'manifest.json'),resultSha256=file_hash(summary_path))
    write_once(root/'audit'/f'{category}-packet.json',packet)
    write_once(root/'reference'/f'{category}-audit-reveal.json',dict(labels={labels[0]:'historical-primary',labels[1]:experiment_label(root).lower()+'-existing-policy'},newEvidence=evidence))
    return packet


def record_stage_decision(root, category, judgment):
    root=Path(root);identifier(category);verify_protocol(root)
    packet=read(root/'audit'/f'{category}-packet.json')
    if judgment.get('packetSha256')!=digest(packet):raise EvaluationError('Judgment does not match audit packet')
    if judgment.get('decision') not in ['advance','targeted-retest','stop']:raise EvaluationError('Invalid decision')
    for key in ['reviewer','reviewedAt','reasons','recognitionDisclosure']:
        if not isinstance(judgment.get(key),str) or not judgment[key].strip():raise EvaluationError('Missing reviewer judgment: '+key)
    assessments=judgment.get('essentialAssessments',[])
    needs=packet['criteria']['essentialNeeds']
    if sorted(a.get('need','') for a in assessments)!=sorted(needs):raise EvaluationError('Assess every frozen essential need exactly once')
    allowed={'supported','evidenced-limitation','miss','unsupported','unresolved'}
    for assessment in assessments:
        if assessment.get('outcome') not in allowed or not assessment.get('reason'):
            raise EvaluationError('Missing substantive essential assessment')
        if assessment['outcome'] in ['supported','evidenced-limitation'] and not assessment.get('evidence'):
            raise EvaluationError('Supported route or limitation needs dated source evidence')
        for evidence in assessment.get('evidence',[]):
            if not all(evidence.get(k) for k in ['url','checkedAt','finding']):raise EvaluationError('Incomplete dated evidence')
    if judgment['decision']=='advance':
        if any(a['outcome'] not in ['supported','evidenced-limitation'] for a in assessments):raise EvaluationError('Unresolved essential coverage prevents advancement')
        if judgment.get('consequentialErrorsResolved') is not True or judgment.get('remainingCodexWorkReduced') is not True:
            raise EvaluationError('Resolve consequential errors and assess useful reduction in Codex work')
        if judgment.get('repeatedConsequentialErrors') is not False:raise EvaluationError('Repeated consequential errors require targeted retest')
        if judgment.get('uniqueAdditionsAuditComplete') is not True:raise EvaluationError('Audit every claimed unique useful addition')
    write_once(root/'audit'/f'{category}-judgment.json',judgment)
    return judgment
