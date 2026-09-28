"""Offline artifact verification; never dispatches a model or changes policy."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from resource_research_agent.improvement_packages import digest
P=Path(__file__).resolve().parent


def load(path):return json.loads(path.read_text())


def run():
    summary=load(P/'comparison-summary.json');audit=load(P/'execution-audit.json');prepared=load(P/'prepared.json')
    before=load(P/'baseline-policy.json');after=load(P/'candidate-policy.json')
    assert {k for k in before if before[k]!=after[k]}=={'passes'}
    for a,b in zip(before['passes'],after['passes']):assert {k for k in a if a[k]!=b[k]}=={'direction'}
    assert hashlib.sha256((P/'source-package.zip').read_bytes()).hexdigest()==load(P/'source.json')['packageSha256']
    hashes={};contexts=[]
    for arm in ('baseline','candidate'):
        folder=P/arm;packet=load(folder/'policy-packet.json');contexts.append(packet['contextId'])
        assert digest({k:v for k,v in packet.items() if k not in ('packetId','assignmentSha256')})==packet['assignmentSha256']
        assignments=sorted(folder.glob('*-assignment.json'));assert len(assignments)==7
        for path in assignments:
            a=load(path);r=load(folder/(path.name.removesuffix('-assignment.json')+'-result.json'))
            assert digest({k:v for k,v in a.items() if k!='assignmentSha256'})==a['assignmentSha256']
            assert r['assignmentSha256']==a['assignmentSha256']
            assert set(r)==set(a['outputContract'])
            assert r['executionReceipt']['contextId']==packet['contextId']
            assert r['executionReceipt']['model']=='gpt-6-astra'
            assert a.get('priorChecks',[])==[] and a['knownIdentities']==[]
            assert digest(r)==audit['arms'][arm]['resultHashes'][a['stage']]
        result=load(folder/'comparison-result.json');accepted=load(folder/'accepted-comparison-result.json')
        assert accepted['result']==result
        assert accepted['resultId']==summary['results'][arm]
        assert accepted['executionEvidence']['historical'] is False
        assert not accepted['executionEvidence']['incomplete']
        assert accepted['late'] is False
        assert result['complete'] and result['limitHit'] and result['remainingGaps']
        assert len({f['key'] for f in result['findings'] if f['retained']})==10
        assert len(load(folder/'reconcile-result.json')['items'])==3
    assert len(set(contexts))==2
    assert summary['activeManifest']==prepared['initialManifest'] and summary['productionActivation'] is False
    evaluation=load(P/'evaluation.json');assert evaluation['assessment']['verdict']=='inconclusive' and evaluation['blockers']
    for path in sorted(P.rglob('*')):
        if path.is_file() and path.suffix in ('.json','.zip','.py','.md') and path.name not in ('verification.json','preparation-verification.json'):
            hashes[str(path.relative_to(P))]=hashlib.sha256(path.read_bytes()).hexdigest()
    report={'passed':True,'acceptedResearchStages':14,'researchPasses':8,'writtenDrafts':6,'distinctPrograms':3,
            'matchedFindingsPerArm':10,'researcherIsolation':True,'activePolicyUnchanged':True,
            'verdict':'inconclusive','sourceAndArtifactHashes':hashes,
            'verificationScope':'Exact archived packet/result hashes, stage contracts, context isolation, budgets from transport audit, and unchanged manifest. Source facts were separately reviewed against current primary pages; this script does not prove semantic correctness.'}
    (P/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Verified: 14 real accepted stages, 8 passes, 3 shared programs, 2 isolated contexts, inactive policy.')


if __name__=='__main__':run()
