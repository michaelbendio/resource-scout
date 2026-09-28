"""Seal a fresh-lead paired research trial. No model calls or activation."""
import json
from pathlib import Path
from resource_research_agent.learning_workbench import LearningWorkbench
from resource_research_agent.storage import ResearchStore
from resource_research_agent.improvement_packages import write_package
ROOT=Path(__file__).resolve().parents[2]
P=Path(__file__).parent
OUT=ROOT/'output/learning-primary-20260909'
OUT.mkdir(parents=True,exist_ok=True)
work=LearningWorkbench(ResearchStore(OUT/'trial.sqlite3'))
prior=ROOT/'experiments/learning-pilot-20260909'
work.import_editorial((prior/'source-package.zip').read_bytes(),(prior/'editorial-decisions.json').read_bytes())
proposal=json.loads((ROOT/'experiments/discovery-pilot-20260909/employment-lesson-proposal.json').read_text())
proposal['scope']={'office':'Denver','category':'employment','stage':'research'}
proposal['title']='First reachable employment help — fresh primary-research transfer test'
proposal['alternativeExplanation']='Existing Employment guidance or model ability may already cover the method. Earlier saved-case instructions contaminated the control. Transfer from Mesa editorial evidence to Denver research is unproven.'
proposal['evaluationQuestion']='Does this addition improve actionable entry routes or prevent a consequential selection/factual error without losing useful alternatives or adding avoidable curator work?'
leads=[
 ('djatc','Denver Joint Electrical Apprenticeship and Training Committee','https://djeatc68.com/'),
 ('step','Step Denver — work and career counseling','https://stepdenver.org/our-4-pillars/work/'),
 ('egcareer','Emily Griffith — Career Services for Job Seekers','https://www.emilygriffith.edu/career-services-for-job-seekers/'),
 ('dayworks','Bayaud Enterprises — Denver DayWorks','https://bayaudenterprises.org/'),
 ('ceo','Center for Employment Opportunities — Denver','https://www.ceoworks.org/locations'),
 ('newheights','Denver International Airport — New Heights','https://www.flydenver.com/business-and-community/ceea/career-pathways/new-heights-pilot-program/'),
 ('egcareers','Emily Griffith — CAREERS for Refugees and Immigrants','https://www.emilygriffith.edu/careers-for-refugees-and-immigrants/'),
 ('dvr','Colorado Division of Vocational Rehabilitation — Denver','https://dvr.colorado.gov/'),
]
data={'resourcePackageSchemaVersion':3,'packageVersion':1,'officeName':'Denver','categories':[{'id':'employment','label':'Employment','filters':[]}],'forGroups':[],'resources':[{'id':i,'name':n,'website':u,'categories':['employment']} for i,n,u in leads]}
payload=write_package(data,{})
(P/'source-package.zip').write_bytes(payload)
source=work.register_package(payload)
lesson=work.propose(proposal)
rubric={
 'registeredBeforeDispatch':True,'purpose':'One paired primary-research trial, then confirmation on a different set only if promising. No repeat-until-positive.',
 'selection':'Eight purposive Denver Employment leads, not previously edited Mesa/Welfare Square resources. Includes potentially public help, training, referrals and program-internal support. Not a representative office sample.',
 'sharedInstructions':'Procedural only; production Employment baseline unchanged. Respondents see names and primary URLs, no prior edited descriptions, answers, or rubric.',
 'quality':['Score against official sources after both results are sealed. A disagreement alone is not an error.','First usable step and actual entry route established or uncertainty explicit.','Useful alternatives preserved, including consequential narrow eligibility.','No unsupported availability, income, referral, public access or cost promises.','Important eligibility, timing, cost and location details preserved.'],
 'curatorWork':'Classify questions as consequential unresolved, source-answerable/redundant, or optional. Raw question count alone does not decide quality.',
 'decisionRule':'Promising requires a source-supported consequential benefit and no offsetting critical harm. Parity is no-clear-benefit. Incomplete research, protocol violations or unreliable evidence may be inconclusive. Do not activate from this trial alone.',
 'timing':'Same gpt-6-astra high config; fresh ephemeral CLI sessions; 24 web calls and 24 source pages each, 1200 seconds each. Stop processes at elapsed ceiling; no retry of a completed arm. Record actual elapsed and emitted token usage; dollars unknown under subscription.',
 'limits':'Same-model blind spots remain. Live retrieval can vary. Parent selects and scores cases; no independent blind assessor. Measures bounded lead research, not full category discovery.'}
spec={'name':'Fresh Denver Employment primary research','operator':'Astra under Michael authorization','reason':'Correct shared-instruction leakage and test research applicability','modelConfig':{'provider':'OpenAI Codex CLI','model':'gpt-6-astra','settings':{'reasoningEffort':'high','webSearch':'live','ephemeral':True}},'sourceSha256':source['sourceSha256'],'cases':[{'caseId':i,'resourceId':i} for i,_,_ in leads],'maxAssignments':2,'maxSeconds':1800,'evaluationBasis':json.dumps(rubric,sort_keys=True),'researchProtocol':{'version':2,'maxSourcePages':24,'maxWebCalls':24}}
trial=work.prepare_trial(lesson['lessonId'],spec)
for name,obj in [('proposal.json',proposal),('lesson.json',lesson),('rubric.json',rubric),('specification.json',spec),('trial.json',trial)]:
 (P/name).write_text(json.dumps(obj,indent=2)+'\n')
for arm in ('baseline','candidate'):
 packet=work.packet(trial['trialId'],arm,'denver-primary-20260909-'+arm,fresh=True)
 (P/(arm+'-packet.json')).write_text(json.dumps(packet,indent=2)+'\n')
print('Sealed eight-lead trial; no activation.')
