"""Record the coordinator's source-checked, non-blind assessment; no activation."""
import json
from pathlib import Path
from resource_research_agent.learning_workbench import LearningWorkbench, METRICS
from resource_research_agent.storage import ResearchStore
P=Path(__file__).parent.resolve();ROOT=P.parents[1]
work=LearningWorkbench(ResearchStore(ROOT/'output/learning-primary-20260909/trial.sqlite3'))
tid=json.loads((P/'trial.json').read_text())['trialId']
notes={
'djatc':('https://djeatc68.com/apply/', 'Both preserve the application sequence, paid training, application fee and selection uncertainty. Neither rejects a four-year program merely for its duration.', 'Same useful option. More explicit separation of course duration and first paid assignment, without a demonstrated changed outcome.'),
'step':('https://stepdenver.org/apply/ ; https://stepdenver.org/our-4-pillars/work/', 'Retains an integrated recovery/employment option and clearly states residency and full-time work conditions. This is not a false promise of public drop-in coaching. Includes published fees and the restriction on outside financial support.', 'Clearer exclusion from stand-alone public Employment, while preserving a possible integrated recovery referral. However that fallback omits the published fee amounts and restriction on outside money/benefits. The added fee question is partly answerable from the application page already cited. Completeness concern applies to the fallback, not proof that its exclusion was wrong.'),
'egcareer':('https://www.emilygriffith.edu/career-services-for-job-seekers/', 'Correctly limits coaching to the stated student/alumni audience, reserves public-access uncertainty and preserves the separate apprenticeship contact.', 'Same practical route and uncertainty; no decisive gain.'),
'dayworks':('https://denver.legistar.com/LegislationDetail.aspx?G=928A1C29-26D7-4A5D-8DD4-947A533B1CC6&GUID=C2549384-7B0D-4074-8F30-B120C114EBEE&ID=7974114&Options=&Search=', 'Current city resolution confirms funding under ServiceSource; exact current intake remains unresolved. Correctly avoids treating the former website as closure. Has a local general contact.', 'Same needs-check outcome. Finds historical intake and week-one support, labels their age, but supplies a national general contact. Neither establishes a current program-specific start.'),
'ceo':('https://www.ceoworks.org/participants', 'Retains a usable parole/probation referral with orientation steps and documents. Does not promise a work slot.', 'Same retained route. More explicitly says CEO can help obtain the referral, consistent with the official intake page; no selection gain.'),
'newheights':('https://www.flydenver.com/business-and-community/ceea/career-pathways/new-heights-pilot-program/', 'Preserves targeted eligibility and referral contacts but reserves the resource and omits career-finding services available while waitlisted. That omitted intermediate help matters to the earliest-useful-help question.', 'Retains the targeted CDOC route and includes career-finding help while waitlisted. Explicitly keeps the unresolved operator, capacity, pay and timing questions. Useful improvement; not proof of current available places.'),
'egcareers':('https://www.emilygriffith.edu/careers-for-refugees-and-immigrants/', 'Retains long-term navigation with English, work authorization and financial-stability restrictions. Does not imply immediate placement. The FAQ already permits training outside this college, though exact eligibility screening may still need clarification.', 'Same useful alternative and principal restrictions. Shares a partly source-answerable question about study outside the college; not an extra independent failure caused by the addition.'),
'dvr':('https://content.govdelivery.com/accounts/CODLE/bulletins/4065f78', 'Preserves disability services and the dated waitlist limitation. Does not extrapolate April counts to September. General contact supplied.', 'Preserves the same limitations and notes interim referrals. A more specific Denver contact is supplied, but the coordinator could not independently fetch the office directory, so no factual credit or error is assigned to that difference.')}
cases=[]
for cid,(source,left,right) in notes.items():
 item={'caseId':cid,'evidence':'Coordinator checked official source on 2026-09-09: '+source,
       'baseline':{**dict.fromkeys(METRICS,False),'reason':left},'candidate':{**dict.fromkeys(METRICS,False),'reason':right}}
 if cid=='newheights':item['baseline']['lostCriticalDetail']=True
 if cid=='step':item['candidate']['lostCriticalDetail']=True
 cases.append(item)
assessment={'reviewer':'Astra coordinator, source-checked AI assessment; not human curation',
'method':'Predeclared rubric, eight fresh leads, both outputs sealed before review. Check case-level usefulness and essential details independently of question count. Selection disagreement is not itself an error. The Step omission flag concerns the recovery alternative still offered, not a requirement to publish a rejected employment entry.',
'caseJudgments':cases,'conclusion':'no-clear-benefit',
'limitations':'Mixed signal: better targeted selection and waitlist-help discovery, offset by omitted details in a fallback and shared avoidable questions. Small purposive sample, one pair, same-model blind spots and unblinded coordinator. Some current contact/source pages could not be independently fetched. Live sources can vary. CLI confirms 13 web calls each but does not expose complete batched source-page counts; compliance with the 24-page ceiling is respondent-reported. Requested model is gpt-6-astra high; backend identity is not separately exposed. No claim of statistically reliable superiority, provider verification or full-category discovery. No confirmation trial or activation because the predeclared no-offsetting-harm condition was not met.'}
(P/'assessment.json').write_text(json.dumps(assessment,indent=2)+'\n')
report=work.assess(tid,assessment)
(P/'report.json').write_text(json.dumps(report,indent=2)+'\n')
measurements={}
for arm in ['baseline','candidate']:
 events=[json.loads(x) for x in (P/(arm+'-events.jsonl')).read_text().splitlines()]
 run=json.loads((P/(arm+'-run.json')).read_text())
 data=json.loads((P/(arm+'-response.json')).read_text())
 usage=next(x['usage'] for x in events if x['type']=='turn.completed')
 measurements[arm]={'processSeconds':run['elapsedSeconds'],'webCalls':sum(e['type']=='item.completed' and e.get('item',{}).get('type')=='web_search' for e in events), 'sourcePages':None,'sourcePageCeilingIndependentlyVerified':False,'cliUsage':usage,'uncachedInputTokens':usage['input_tokens']-usage['cached_input_tokens'], 'openQuestions':sum(len(c['openQuestions']) for c in data['cases']), 'incrementalCostUSD':None}
question_review={
'baseline':{'consequentialUnresolved':19,'mixedPartlySourceAnswerable':1,'sourceAnswerableOrScopeAlreadyStated':1,'optionalLowPriority':1,'notes':'Optional: reconciling two employment success percentages adds little to a referral. New Heights already requires CDOC transitional participation. CAREERS outside-college question is partly answered.'},
'candidate':{'consequentialUnresolved':18,'mixedPartlySourceAnswerable':2,'sourceAnswerableOrScopeAlreadyStated':0,'optionalLowPriority':1,'notes':'Step fee/bed question mixes published fees and current availability. CAREERS outside-college question is partly answered. Nonresident Step investigation is optional once reserving that provider for recovery only.'},
'unit':'One question entry; compound questions classified mixed. Coordinator judgment, not a human-scored outcome. Fewer questions alone is not improvement.'}
(P/'measurements.json').write_text(json.dumps(measurements,indent=2)+'\n')
(P/'question-review.json').write_text(json.dumps(question_review,indent=2)+'\n')
print(json.dumps({'conclusion':assessment['conclusion'],'quality':report['quality'],'active':report['active'],'questions':{k:v['openQuestions'] for k,v in measurements.items()}}))
