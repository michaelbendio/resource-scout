"""Actual operator reconciliation; never substitutes for the blind reply."""
from copy import deepcopy
import json
from pathlib import Path
from resource_research_agent.storage import ResearchStore
from resource_research_agent.scout_maintenance import MaintenanceWorkflow
from resource_research_agent.frontier_editor import FrontierEditorWorkflow
from resource_research_agent.performance import timing_session

P=Path(__file__).parent;O=Path('output/discovery-pilot-20260909')
load=lambda n:json.loads((P/n).read_text())
def save(n,x): (P/n).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
m=MaintenanceWorkflow(ResearchStore(O/'pilot.sqlite3'));pid=load('research-project.json')['researchProjectId']
sources=load('primary-sources.json')
more=[('https://jobs.utah.gov/usor/vr/apply.html','Contact your local VR office'),
 ('https://utahca.org/workforce-development/','All income levels are accepted.'),
 ('https://uteta.org/programs-overview/','1,000 hours of classroom education'),
 ('https://uteta.org/programs/faqs/','ID cards will not be accepted.'),
 ('https://www.yearup.org/locations/salt-lake-city-ut','young adults aged 18-29')]
sources += [{'url':u,'accessedOn':'2026-09-09','excerpt':e} for u,e in more]

def sections(*values):
 return dict(zip(['programsAndServices','eligibilityRequirements','howToBestConnect','access','importantInformationToKnow'],values))

with timing_session(P/'workflow-timings.jsonl'):
 while a:=m.next_assignment(pid,researcher='Codex'):
  assert a['stage']=='reconcile'
  r=deepcopy(a['outputContract']);r['assignmentSha256']=a['assignmentSha256'];r['evidenceSources']=sources
  r['items']=deepcopy(a['frozenResult']['items'])
  r['researchNotes']='Actual operator reconciliation after frozen primary research and Claude blind completion. Checked the suggested official pages independently. Claude supplied a compact second reply after the operator stopped oversized generation; the original partial capture and transport notes are preserved. No provider calls or new human approval. Zero timing fields below mean unallocated shared operator time; not zero effort.'
  resolutions=[]
  for b in a['blindResults']['Claude']['items']:
   reason=''
   if a['scope']=='recheck':
    item=r['items'][0];f=item['fields']
    if 'uteta.org' in f['website']:
     f['informationSections']=sections(
      'Paid electrical work combined with classroom training. Apprentices pay for books, tuition and required tools.',
      'Age 18 or older; diploma or GED; passing algebra or an accepted alternative. A valid driver’s license is required; Utah residents need a Utah license. Provide birth and school records; foreign transcripts need professional translation and notarization.',
      'Start at Apply Now on the website. Upload required records within 30 days. Call 801-975-1945 or email apply@uteta.org for help before paying.',
      'Training center in West Jordan. Work can be assigned anywhere in Utah, requiring reliable travel.',
      'The current Apply Now page lists a $75 application fee; confirm the amount and other starting costs. Selection includes testing and an interview, with no confirmed start date. Applying does not guarantee paid work.')
     item['evidence']=[3,4,5,14,15]
     item['questions']=['What will an applicant need to pay before paid work starts? The current Apply Now and Inside Wireman pages I read list $75. Claude reported $30 from search snippets and the application portal, but I could not reproduce that portal amount. Ask the office to confirm the application charge, books, tuition and tools before someone spends money.']
     reason='Accepted the license clarification after reading the FAQ. Independently confirmed the 720-versus-1,000 classroom-hour discrepancy, so omitted that nonessential figure. Did not repeat Claude’s claim that the current program page says $30: my current read says $75. Portal amount remains unverified and is explained in the question. Preserve this as a researched option for the final editor, not a promise of immediate work.'
    else:
     f.update(name='Utah Workforce Services · Job Search and Training Help',address='',hours='')
     f['description']='Free job-search help and a way to apply for career or training assistance. Ask DWS which local office to visit.'
     f['informationSections']=sections(
      'Help with resumes, applications, interviews and finding work. Career and education assistance has a separate application and eligibility review.',
      'General job-search help is available to job seekers. Training support depends on your circumstances and the program; a counselor decides eligibility.',
      'Use the website for job-search tools. For career and education assistance, apply online or at an Employment Center. Call the general DWS service number, 801-526-0950, to confirm a local starting point.',
      'Utah, including Salt Lake City. Online career applications need a UtahID account; in-person applications are also offered.',
      'For career assistance, a counselor should contact you within three business days to arrange an appointment. Submit required documents within 45 days. Applying does not guarantee training funding.')
     item['questions']=['Which nearby DWS office should someone visit, and when? Older official listings name Salt Lake Metro at 720 South 200 East. The current office finder did not show readable office details during this check. Confirm a nearby address, hours and whether an appointment is needed; the listed phone is a general DWS number.']
     reason='Agree that cached directory details are not current local verification. Retain the supported statewide job-seeker service with general phone/online entry; remove the unconfirmed office address and clarify its title. This is a prospective lead, not a human-curated office identity. Local in-person routing remains one concrete question. Keep VR separate because its eligibility and application differ.'
    item['summary']='Source-checked draft with consequential access details and explicitly identified uncertainty.'
   elif 'usor' in b['id']:
    item=deepcopy(b);f=item['fields'];f['name']='Utah Vocational Rehabilitation · Disability Job Support'
    f['informationSections']=sections(
     'Work with a counselor on a plan to get or keep a job. Services depend on your needs, eligibility and available funding.',
     'A disability must substantially affect work, and you must need and benefit from rehabilitation services. A counselor decides eligibility, usually within 60 days of your appointment; some cases take longer.',
     'Call 866-454-8397 for your local VR office. Obtain an application and arrange a counselor appointment. Bring identification, your Social Security card and any disability records; staff can arrange an evaluation if records are missing.',
     'Salt Lake area and statewide. Spanish and large-print applications are available. You may bring someone to your appointment.',
     'Some newly eligible applicants must wait for training or job placement; existing employment plans continue. People waiting receive information and referrals. Ask about current availability and any costs before making plans.')
    item.update(evidence=[9,12],questions=[],summary='Distinct disability employment route, independently confirmed; waiting restrictions preserved.')
    r['items'].append(item)
    reason='Confirmed the application phone, eligibility process and order-of-selection exceptions on official pages. Retain as a separate route; no curator decision is needed about ordinary organizational overlap. Preserve waiting restrictions without claiming every applicant must wait or every service is free.'
   else:
    item=deepcopy(b);f=item['fields'];f['name']='Utah Community Action · Job Help, GED and Career Training'
    f['informationSections']=sections(
     'Free job-readiness and money-management help, GED preparation and a child-care credential. Staff also refer people to English classes and other training.',
     'Age 18 or older and living in Salt Lake or Tooele County. All income levels are welcome. The child-care credential has additional qualifications.',
     'Call 801-359-2444 and ask for Workforce Development, or complete the website’s English or Spanish form. Staff follow up to finish the application by phone.',
     'The listed office is at 1307 S 900 W. Ask where your classes or appointments will take place before traveling.',
     'GED preparation is currently in English and includes exam fees. The child-care credential requires 120 class hours plus 480 preschool hours. Services reached through referrals may have different costs and requirements.')
    item.update(evidence=[13],questions=[],summary='Confirmed free local adult support with direct intake; language, course time and referral limits retained.')
    r['items'].append(item)
    reason='Independently confirmed the provider page. Retain the described programs. No need to burden the curator with deciding whether an undescribed form option merits its own listing; leave culinary expansion for future research. Confirm class location by phone before travel.'
   resolutions.append({'findingId':'Claude:'+b['id'],'status':'resolved','reason':reason})
  if a['scope']=='discovery':
   r['researchNotes']+=' Year Up remains an unexpanded lead: the location page supports 18–29 training but this limited scan did not establish full enrollment conditions, schedule or support. Do not describe it as rejected or completed research. Primary Sugarhouse coaching and PeopleReady staffing remain distinct practical options alongside Claude’s two additions.'
  r['resolutions']=resolutions
  r['executionReceipt']={'complete':True,'model':None,'contextId':'codex-discovery-pilot-20260909','freshContext':False,'isolatedInputs':False,
   'activeMinutes':0,'waitingMinutes':0,'coverageNotes':'Actual source-checked reconciliation. Shared operator timing is unallocated; zero values are not measured zero effort.',
   'remainingGaps':['No provider phone verification. The pilot is not exhaustive Employment coverage.','Local DWS in-person routing and apprenticeship initial costs remain questions.']}
  name=a['taskId'].replace(':','_')+'--reconcile';save(name+'-packet.json',a);save(name+'-response.json',r)
  m.submit(pid,a['stage'],r)
save('reconciled-state-summary.json',m.view(pid))
f=FrontierEditorWorkflow(m.store);packet=f.finish_research(load('project.json')['id']);save('final-packet.json',packet)
print('Research reconciled; final editor packet contains',len(packet['package']['resources']),'resources.')
