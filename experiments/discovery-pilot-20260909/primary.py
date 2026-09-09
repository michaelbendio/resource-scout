"""Submit the operator's actual September 9 research, preserving sealed inputs."""
from copy import deepcopy
import json
from pathlib import Path
from resource_research_agent.storage import ResearchStore
from resource_research_agent.scout_maintenance import MaintenanceWorkflow
from resource_research_agent.performance import timing_session

P=Path(__file__).parent; O=Path('output/discovery-pilot-20260909')
load=lambda n:json.loads((P/n).read_text())
def save(n,x): (P/n).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
S=[
 ('https://jobs.utah.gov/jobseeker/index.html','Get free help polishing a resume'),
 ('https://jobs.utah.gov/jobseeker/career/apply.html','Submit an application online or in-person'),
 ('https://jobs.utah.gov/ui/employer/public/UINoticePosterSpanish.aspx','Salt Lake Metro'),
 ('https://uteta.org/programs/careers-inside-wire/','Earn While You Learn'),
 ('https://uteta.org/programs/apply-now/','Interviews take place on an as-needed basis'),
 ('https://uteta.org/contact/','Phone: 801-975-1945'),
 ('https://local.churchofjesuschrist.org/en/employment-services/us/ut/salt-lake-city/724-e-2100-s','Appointments are encouraged, but not necessary.'),
 ('https://locations.peopleready.com/us/ut/salt-lake-city','1081 S 300 W'),
 ('https://www.peopleready.com/cities/staffing-agencies-salt-lake-city-ut/','short-term, long-term and permanent employees'),
 ('https://jobs.utah.gov/usor/vr/services/order.html','Currently, the Significant Disability (SD) and Disability (D) priority categories are closed.'),
 ('https://www.rescue.org/united-states/salt-lake-city-ut','adults become self-reliant through employment'),
 ('https://jobs.utah.gov/usor/vr/partners/crpapproved.pdf','Updated September 2026')]
sources=[{'url':u,'accessedOn':'2026-09-09','excerpt':s} for u,s in S]
save('primary-sources.json',sources)

def fields(name,description,phone,address,website,kind,sections,hours=''):
 return dict(name=name,description=description,phone=phone,address=address,website=website,hours=hours,
  categories=['employment'],categoryFilters={'employment':[kind]},forGroups=[],informationSections=dict(zip(
  ['programsAndServices','eligibilityRequirements','howToBestConnect','access','importantInformationToKnow'],sections)))

DWS=fields('Utah Workforce Services · Salt Lake Metro Job Help','Free help with resumes, applications and finding work. Training assistance has separate eligibility rules.',
 '801-526-0950','720 South 200 East, Salt Lake City, UT',S[0][0],'Job Search',[
 'Help with job searches, resumes, applications and interviews. Ask about training assistance if you need new skills.',
 'Training funding requires an eligibility review; being eligible for job-search help does not guarantee funding.',
 'Visit the Salt Lake Metro Employment Center or use the DWS website. Call the DWS service number to confirm office hours before traveling.',
 'Salt Lake City. You can apply for career and education services in person; online applications require a UtahID account.',
 'For career and education assistance, a counselor contacts you to arrange an appointment and explains required documents. Submit required information within 45 days.'])
UTETA=fields('Utah Electrical Training Alliance · Paid Electrician Apprenticeship','Apply for paid electrical work with classroom training. Selection, fees and statewide travel make this a longer-term option.',
 '801-975-1945','7466 South Redwood Road, West Jordan, UT 84084',S[4][0],'Apprenticeships',[
 'Paid electrical work with 8,000 hours of work training and 720 classroom hours. Apprentices pay for books and tuition.',
 'Age 18 or older; diploma or GED; passing algebra; valid driver’s license. Required records include identification, Social Security number, birth certificate and school records.',
 'Apply online and pay the $75 processing fee. Upload required documents within 30 days. Email apply@uteta.org for application help.',
 'Training center in West Jordan. Contractors may assign work anywhere in Utah, so reliable statewide travel is required.',
 'A complete application leads to an aptitude test; passing qualifies you for an interview. Interviews occur as needed. Applying does not promise admission or immediate paid work. Ask about total costs and the current wait before paying.'],
 'Monday–Friday, 8 AM–5 PM')
CHURCH=fields('Employment Services · Sugarhouse Job-Search Help','Work with an adviser on resumes, job leads and interviews. Phone or video coaching is also available.',
 '801-467-6443','724 E 2100 S, Suite A, Salt Lake City, UT 84106',S[6][0],'Job Search',[
 'Individual job-search coaching, resume help, interview practice and networking. Computers and printers are available.',
 'Everyone is welcome; Church membership is not required.',
 'Call the center to check current hours. Walk-ins are welcome; an appointment is encouraged. Request Assistance on the website also connects you with an adviser.',
 'Sugarhouse in Salt Lake City. Phone or video coaching is available if you cannot visit.',
 'Bring a resume or job description if you have one. You can still get help without either.'])
PEOPLE=fields('PeopleReady · Salt Lake City Staffing','Apply for temporary and other local work. Job availability and requirements vary.',
 '801-521-0480','1081 S 300 W, Salt Lake City, UT 84115',S[7][0],'Staffing',[
 'Staffing for short-term, longer-term and permanent jobs in several industries.',
 'Requirements depend on the job. Ask the branch what identification, skills and work authorization documents are needed.',
 'Call the Salt Lake City branch for application help or use JobStack to look for assignments.',
 'Salt Lake City branch; check the actual work site and transportation before accepting a job.',
 'An application does not guarantee a shift. Confirm pay, schedule, equipment needs and any costs before accepting.'])
focus={
 'public-workforce':('DWS offers general job-search help and eligibility-screened training via local centers. Detailed veterans and benefits-linked subprograms were not researched in this pilot.',[0,1,2],['Which additional public pathways add distinct help beyond the Metro center?']),
 'immediate-employment':('PeopleReady has a current Salt Lake City branch and durable staffing intake. Individual job advertisements were not copied as lasting resources.',[7,8],['Confirm current branch intake hours and identification requirements. Other staffing agencies were not compared.']),
 'training-advancement':('UTETA offers paid electrical training but requires application fees, qualifications and statewide travel. Paid-work start timing remains uncertain.',[3,4,5],['What is the current selection delay and total initial expense? College and other trade programs remain outside this limited scan.']),
 'supported-employment':('USOR has closed priority categories with delayed service; existing plans continue. Do not imply immediate placement for every new applicant. Keep this lead for separate follow-up rather than fully write it here.',[9],['Confirm local application route and current priority status before drafting a patron referral.']),
 'population-specific':('IRC Salt Lake describes refugee employment services; narrow eligibility can be valuable. A volunteer recruitment page is not client intake. This limited scan has not established direct intake for new employment clients.',[10],['Can a refugee who is not already an IRC client enroll in employment help? Reentry, youth, senior and other pathways remain unsearched.']),
 'community-embedded':('Church Employment Services Sugarhouse offers adviser help, walk-ins and phone/video support regardless of Church membership. This is an accessible community-based job-search route.',[6],['Confirm current center hours. Shelter and other community programs remain unsearched.']),
 'non-obvious-sources':('September 2026 USOR approved-provider registry identifies additional Salt Lake supported-employment providers. Approval alone does not establish walk-in access or funded availability; entries are leads, not automatically useful independent listings.',[11,9],['Which registered providers offer a reachable intake route for the intended patron? Further contracts and grants were not searched.'])}

m=MaintenanceWorkflow(ResearchStore(O/'pilot.sqlite3'));pid=load('research-project.json')['researchProjectId']
with timing_session(P/'workflow-timings.jsonl'):
 while a:=m.next_assignment(pid,researcher='Codex'):
  if a['stage']=='reconcile': break
  r=deepcopy(a['outputContract']);r['assignmentSha256']=a['assignmentSha256'];r['evidenceSources']=sources
  r['researchNotes']='Actual September 9 official-web research by current Codex operator. Bounded pilot; no provider calls. Shared research time is not measured per task; activeMinutes=0 is unallocated, not a claim of zero effort. See pilot timing report.'
  gaps=['This small pilot does not establish complete Employment coverage.']
  if a['stage'].startswith('pass:'):
   summary,evidence,questions=focus[a['stage'].split(':',1)[1]]
   r['observations']=[dict(summary=summary,evidence=evidence,questions=questions)];gaps=questions
  else:
   if a['scope']=='recheck':
    is_dws='Workforce' in a['target']['name'];f=DWS if is_dws else UTETA
    specs=[(a['target']['id'],'changed',f,[0,1,2] if is_dws else [3,4,5])]
   else: specs=[('welfare-employment-sugarhouse','new',CHURCH,[6]),('welfare-employment-peopleready','new',PEOPLE,[7,8])]
   r['items']=[{'id':rid,'status':status,'program':f['name'],'summary':'Official sources support this proposed referral; practical restrictions are retained.',
    'fields':f,'evidence':ev,'closureEvidence':[],'questions':[],'nextCheckOn':'','lastEvidenceOfOperationOn':''} for rid,status,f,ev in specs]
   if 'resolutions' in r:r['resolutions']=[]
  r['executionReceipt']={'complete':True,'model':None,'contextId':'codex-discovery-pilot-20260909','freshContext':False,
   'isolatedInputs':False,'activeMinutes':0,'waitingMinutes':0,'coverageNotes':'Limited official-source scan; timing unallocated across shared searches. No exhaustive coverage or human confirmation.',
   'remainingGaps':gaps}
  name=a['taskId'].replace(':','_')+'--'+a['stage'].replace(':','_')
  save(name+'-packet.json',a);save(name+'-response.json',r)
  m.submit(pid,a['stage'],r)
save('primary-state-summary.json',m.view(pid))
print('Actual primary research and freeze saved. Claude checks remain pending.')
