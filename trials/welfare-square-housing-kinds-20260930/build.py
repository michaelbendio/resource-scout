"""Build only a non-importable evaluation artifact from authored trial decisions.

No network, database, production registry or WSRS-TSO access. Rebuilding cannot
turn this evaluation into a production package.
"""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
sys.path.insert(0, str(REPO))
from resource_research_agent.preparation_contract import assemble_information, INFORMATION_HEADINGS, normalize_preparation_fields
from resource_research_agent.prepared_resources import source_catalog, source_id, revision, content_fingerprint, validate_artifact, PreparedResourceError

def read(path):
    return json.loads((ROOT/path).read_text())

def write(path, value):
    (ROOT/path).write_text(json.dumps(value, indent=2, ensure_ascii=False)+'\n')

def draft_id(key):
    return 'trial_' + hashlib.sha256(('welfare-square-housing-kinds-20260930:'+key).encode()).hexdigest()[:24]

def build():
    drafts=read('curation/prepared-drafts.json')
    research=read('research/decisions.json')
    run=read('metrics/run.json')
    # Preserve a reproducible generation timestamp on subsequent rebuilds.
    generated=run.setdefault('artifactGeneratedAt', datetime.now(timezone.utc).isoformat())
    original=json.loads((REPO/'docs/list-seeding-trial-claude-20260930/kinds-checklist-from-provo.json').read_text())['categories']['housing']
    definitions=[
        'Public housing authority applications for subsidized or affordable rental homes.',
        'Financial help with rent, rental deposits or qualifying tenant relocation costs.',
        'Time-limited housing intended to help residents move toward independent housing.',
        'Essential home repairs and accessibility or safety improvements.',
        'Homebuyer education, counseling or purchase financing assistance.',
        'Housing stabilization or housing programs specifically for veterans.',
        'Low-cost shared housing with evidenced suitability for people on fixed incomes.',
        'Rental search tools or directly bookable extended-stay lodging.',
        'Temporary care for pets when a housing crisis prevents an owner from keeping them safely.',
        'Personal rental navigation or landlord–tenant mediation to address tenancy problems.'
    ]
    kinds=[dict(number=i+1,id=f'housing-kind-{i+1:02}',categoryId='housing',label=row[0],definition=definitions[i]) for i,row in enumerate(original)]
    kinds.append(dict(number=10,id='housing-kind-10',categoryId='housing',label='Tenant support and eviction prevention',definition=definitions[9]))
    used={k for d in drafts for k in d['kinds']}
    groups=[dict(id=g,label=l,definition=d) for g,l,d in [
        ('seniors','Seniors','A documented program or property specifically targets older adults.'),
        ('disabilities','People with disabilities','A documented program or property specifically targets people with disabilities.'),
        ('young-adults','Young adults','A housing program specifically serves young adults within stated ages.'),
        ('single-parents','Single parents','Housing specifically for a parent raising children without a partner in the household.'),
        ('veterans','Veterans','A housing pathway specifically for veterans or their households.')]]
    sources=source_catalog([dict(url=u,title=d['name']+' — '+u.split('/')[-1]) for d in drafts for u in d['sources']])
    resources=[]
    ledger=[]
    for d in drafts:
        sid=[source_id(u) for u in d['sources']]
        r=dict(id=draft_id(d['key']), revision='',state='usable',name=d['name'],description=d['sections'][0],
            phone=d['phone'],address=d['address'],locationDescription=d['where'],website=d['website'],email=d['email'],hours=d['hours'],
            informationText=assemble_information(dict(zip(INFORMATION_HEADINGS,d['sections']))),
            categories=['housing'],types=[f'housing-kind-{k:02}' for k in d['kinds']],forGroups=d['groups'],
            sourceIds=sid,researchedAt='2026-09-30',identityStatus='provisional-trial',
            sourceAccessNote=('Program details were available in the public search index; the program page opened with no parsed text. Contact details were also available in the official services page search index.' if d['key']=='lifestart' else 'Public web evidence; no provider contact or live capacity check.'))
        # The existing preparation normalizer verifies actual provisional records.
        normalized=normalize_preparation_fields(dict(r,sources=[s for s in sources if s['id'] in sid],taxonomySuggestions=[],resolutionReason=''))
        r['revision']=revision(r)
        resources.append(r)
        ledger.append(dict(resourceId=r['id'],key=d['key'],decision='retain-usable-trial',
            officeFit=dict(reach=d['where'],mainService=d['sections'][0],directContact=d['sections'][3],agencyDeduplication=d['duplicateDecision']),
            kindNumbers=d['kinds'],typeEvidence=d['sections'][0],
            groupDecisions=[dict(groupId=g['id'],assigned=g['id'] in d['groups'],
                reason=(d['sections'][1]+' '+d['sections'][2] if g['id'] in d['groups'] else 'No dedicated '+g['label'].lower()+' pathway is established in this scoped record; general availability alone is insufficient.')) for g in groups],
            limitations=d['sections'][4],sourceIds=sid,consideration=d['reason']))
    bykey={d['key']:d for d in drafts}
    starters=['housing-connect','uca-rent','homeinn','lifestart','assist','cdcu-homebuyer','ssvf','rental-search','ruff-haven','tenant-center']
    complements=['milestone','haslc','habitat-repair','uca-mediation','slc-repair','woodspring']
    gap=research['gaps'][0]['reason']
    artifact=dict(artifactType='scout-prepared-resources',schemaVersion=1,evaluationOnly=True,importable=False,
        note='TRIAL — NOT FOR IMPORT. Welfare Square Housing kinds-checklist evaluation, with provisional identities. No office approval or agency verification is implied.',
        snapshot=dict(id='trial-welfare-square-housing-kinds-20260930',predecessorId=None,generatedAt=generated),
        office=dict(slug='welfare-square',name='Welfare Square'),
        scope=dict(categoryIds=['housing'],completeScope=False,completeOffice=False),
        taxonomy=dict(categories=[dict(id='housing',label='Housing')],types=[{k:v for k,v in x.items() if k!='number'} for x in kinds if x['number'] in used],forGroups=groups),
        sources=sources,resources=resources,
        starterSets=[dict(categoryId='housing',rationale='Cover eight evidenced original kinds plus tenant support. Two transitional starters are justified by a client-noticeable difference: single-room adult accommodation versus apartments for single-parent families. No emergency-shelter-only starter.',gaps=gap,
            members=[dict(resourceId=draft_id(k),position=i+1,contribution=bykey[k]['reason'],limitation=bykey[k]['sections'][4]) for i,k in enumerate(starters)])],
        considerations=[dict(resourceId=draft_id(d['key']),categoryId='housing',reason=d['reason']) for d in drafts if d['key'] not in starters],
        trialChecklist=dict(originalKindCount=9,coveredOriginalKinds=sorted(used-{10}),gaps=research['gaps'],additions=research['additions']),
        trialComplements=[dict(resourceId=draft_id(k),reason=bykey[k]['reason']) for k in complements])
    artifact['snapshot']['contentFingerprint']=content_fingerprint(artifact)
    artifact['review']=dict(status='reviewed-for-evaluation',reviewer='Codex',scope='All 16 prepared trial records, taxonomy, sources, office fit and selection; human judging pending.',contentFingerprint=artifact['snapshot']['contentFingerprint'])
    filename='scout-welfare-square-prepared-resources-26-09-30.json'
    write('results/'+filename,artifact)
    write('review/decisions.json',ledger)
    # An exact copy is deliberately rejected by the normal production importer.
    try:
        validate_artifact(artifact)
    except PreparedResourceError as e:
        assert str(e)=='Evaluation artifacts cannot be imported'
    else:
        raise AssertionError('Trial unexpectedly passed the production import gate')
    shuffled=sorted(drafts,key=lambda d:d['key'])
    random.Random(20260930).shuffle(shuffled)
    chosen=shuffled[:min(20,len(shuffled))]
    write('results/sample-selection.json',dict(seed=20260930,algorithm='Python random.Random(seed).shuffle over keys sorted lexically; first min(20,N)',population=len(drafts),resourceIds=[draft_id(d['key']) for d in chosen]))
    sample=['# Welfare Square Housing — judging sample','',
        'TRIAL — NOT FOR IMPORT. All 16 usable resources are included because there are fewer than 20; order was shuffled with seed 20260930. No agency verification or office approval is implied.','',
        '| Resource | Where | What it gives |','| --- | --- | --- |']
    sample += [f"| {d['name']} | {d['where']} | {d['sections'][0]} |" for d in chosen]
    sample += ['', 'For each: would you hand it to a client across the desk? Mark Yes / No / Depends and the reason. The JSON contains contact details, eligibility and limitations.','']
    (ROOT/'results/judging-sample.md').write_text('\n'.join(sample))
    run.update(resourceCount=len(resources),starterCount=len(starters),nonStarterCount=len(complements),originalKindsCovered=len(used-{10}),investigatedLeads=len(drafts)+len(research['notSelected']),webToolCalls=len(read('metrics/web-requests.json')),
        directPaidModelApiCalls=0,directPaidModelApiCostUsd=0,codexSessionCount=1,codexInferenceCalls=None,codexUsageCostUsd=None,
        measurementNote='No separate model API or worker was launched. Interactive Codex inference count/token charges are not exposed here; total model cost is unknown, not zero. Web tool requests are counted separately. Recorded clock starts after initial setup/main pull.')
    write('metrics/run.json',run)
    print(json.dumps(dict(resources=len(resources),starters=len(starters),originalKindsCovered=len(used-{10}),webToolCalls=run['webToolCalls'],productionImport='rejected as intended')))

if __name__=='__main__':
    build()
