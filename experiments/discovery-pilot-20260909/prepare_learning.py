"""Prepare a bounded Employment-only interpretation test; do not dispatch it."""
import hashlib
import json
from pathlib import Path
from resource_research_agent.storage import ResearchStore
from resource_research_agent.learning_workbench import LearningWorkbench

P=Path(__file__).parent; OLD=P.parent/'learning-pilot-20260909'
def save(n,x): (P/n).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
load=lambda n:json.loads((OLD/n).read_text())
w=LearningWorkbench(ResearchStore('output/discovery-pilot-20260909/pilot.sqlite3'))
w.import_editorial((OLD/'source-package.zip').read_bytes(),(OLD/'editorial-decisions.json').read_bytes())
proposal=load('lesson-proposal.json')
baseline=Path('resource_research_agent/playbook_library/employment.json').read_text()
proposal.update(title='Employment: useful help after entry versus barriers before entry',
 scope={'office':'Mesa saved-case pilot','category':'employment','stage':'editorial'},
 hypothesis='A short method may prevent discarding useful paid training or named referral routes while avoiding false immediate-work promises.',
 alternativeExplanation='Existing Employment guidance and capable model judgment may already handle these distinctions. This is interpretation of saved records, not evidence of improved discovery recall.',
 counterexample='A four-year paid apprenticeship can be useful even though selection is not immediate; a named disability caseworker referral can be actionable. Costs and access constraints can still justify a reasoned reserve decision.',
 baseline={'path':'resource_research_agent/playbook_library/employment.json','sha256':hashlib.sha256(baseline.encode()).hexdigest(),'text':baseline},
 addition='Assess the first useful help a person can realistically reach. Separate the length of a program after entry from delay before paid work or other help begins. Do not discard paid training solely because it lasts years, or an actionable named referral solely because it requires a referral. Preserve selection uncertainty, consequential fees, travel and eligibility. Work restricted to residents of another program is not a stand-alone public job route; check whether any separate job help is actually available.',
 evaluationQuestion='Within Employment, does the added method reduce critical errors or lost useful options without false promises or loss of consequential access details?')
save('employment-lesson-proposal.json',proposal)
lesson=w.propose(proposal);save('employment-lesson-receipt.json',lesson)
ids=['mesa-employment-pejatc','mesa-employment-scsep','ffb70295ec3f1e3256fc1955ec7ad5c0','mesa-employment-copa-ers','mesa-employment-st-mary-skills','83d02712bba592a7bc59214e02c13b72']
spec={'name':'Employment practical-entry paired test 2026-09-09','operator':'Astra / Codex operator',
 'reason':'Authorized limited follow-up to the inconclusive mixed-category test. All six cases now use Employment guidance. Support comes from prior editorial evidence, not these cases.',
 'modelConfig':{'provider':'Claude web','model':'Opus 5','settings':{'effort':'High','tools':'none requested','context':'separate incognito chat per arm; service isolation not independently audited'}},
 'sourceSha256':hashlib.sha256((OLD/'source-package.zip').read_bytes()).hexdigest(),
 'cases':[{'caseId':f'employment-{i+1}','resourceId':rid} for i,rid in enumerate(ids)],
 'maxAssignments':2,'maxSeconds':3600,
 'evaluationBasis':'Prepared criteria are held outside respondent packets. Score factual interpretation, preserved useful options, consequential details and unsupported promises. Reasoned reserve versus retain is not automatically an error. These are saved facts, not current phone verification. One trial is exploratory and cannot activate guidance.'}
save('employment-trial-specification.json',spec)
save('employment-evaluation-plan.json',{
 'preparedBeforeDispatch':True,'method':'Evaluate against saved public facts, not the previous editor’s label. Different defensible reserve/retain decisions are not accuracy gains. Count an omission as critical only if the response as a whole loses a consequential condition.',
 'criteria':[
 {'caseId':'employment-1','mustPreserve':['Paid work during four-year training is distinct from waiting four years for work.','$40 application fee, $187 monthly training cost, selection uncertainty, qualification and regional travel requirements.'],'notRequired':'Automatically retain despite all practical barriers.'},
 {'caseId':'employment-2','mustPreserve':['Paid temporary training for unemployed low-income adults 55+, eligibility review and roughly 20 hours weekly.','Named grantee entry route, limited places or waitlists, not a permanent job guarantee.'],'notRequired':'Reject age-specific service or demand immediate placement.'},
 {'caseId':'employment-3','mustPreserve':['Free job placement, variable openings and job requirements.','Phone/in-person help; account alone is not a submitted Mesa application.','Benefits and training are conditional, not guaranteed on applying.'],'notRequired':'Enumerate every optional benefit.'},
 {'caseId':'employment-4','mustPreserve':['Disability service with named direct contact and caseworker/VR/DDD referral possibilities.','Funding and possible cost must be confirmed; business payments do not prove participant wages.'],'notRequired':'Treat every referral as unusable.'},
 {'caseId':'employment-5','mustPreserve':['Free nine-week weekday training, daily Phoenix travel, not guaranteed employment.','Age/work eligibility, screening and living-arrangement restrictions; housing not included.'],'notRequired':'Treat nine weeks of training as nine weeks of no useful help.'},
 {'caseId':'employment-6','mustPreserve':['Paid crew jobs restricted to specified housing residents.','Separate nonresident job help remains unconfirmed.','Housing contribution rules conflict; do not promise a free public job route.'],'notRequired':'Exclude all useful housing support because this is an Employment test.'}],
 'decisionRule':'No clear benefit unless at least one consequential error is corrected without an offsetting regression. Even a positive result remains inactive.'})
save('employment-trial-receipt.json',w.prepare_trial(lesson['lessonId'],spec))
print('Six-case Employment trial and assessment criteria saved; no respondent dispatched yet.')
