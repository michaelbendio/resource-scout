"""Build the bounded draft and import real editorial/package evidence. No AI calls."""
from copy import deepcopy
import hashlib, json, re
from pathlib import Path
from resource_research_agent.improvement_packages import read_package, write_package, utcnow, next_timestamp
from resource_research_agent.open_questions import make_questions, attach_questions
from resource_research_agent.learning_evidence import EvidenceLedger
from resource_research_agent.learning_workbench import LearningWorkbench
from resource_research_agent.storage import ResearchStore
from resource_research_agent.scout_review import render_scout_review_seed

P=Path(__file__).resolve().parent
OUT=P.parents[1]/'output/mesa-maintenance-editor-20260909'
OUT.mkdir(parents=True,exist_ok=True)
save=lambda name,value:(P/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
source=read_package((P/'source-package.zip').read_bytes())
data=deepcopy(source['data'])
stamp_path=P/'draft-timestamp.json'
if not stamp_path.exists():save(stamp_path.name,{'timestamp':next_timestamp([data, *data['resources']])})
stamp=json.loads(stamp_path.read_text())['timestamp']
rows={r['id']:r for r in data['resources']}
worker=rows['08497e5f8c33c372d57430bc722bb639']
old=worker['informationText']
replacements={
 'The separate Workforce Housing program offers 90 days in a private room in shared housing, weekly support and life-skills classes, followed by nine months of follow-up.':
 'The separate Workforce Housing program offers 90 days in shared housing, weekly support, life-skills classes and follow-up after moving out. Ask about room privacy and the length of follow-up; the provider’s pages give different descriptions.',
 'Workforce Housing has separate rules: applicants must work full time in a direct-hire job earning at least $18 an hour. Ask about current openings and any other requirements; qualifying for job-search help does not qualify someone for housing.':
 'Workforce Housing has separate rules. Its housing page requires full-time, direct-hire W-2 work paying at least $18 an hour, plus 30–45 days on the job or at least two pay stubs. Participants commit to saving 80% of take-home pay, weekly meetings and first-month workshops. Some felonies are considered individually. Job-search eligibility does not establish housing eligibility.',
 'For Workforce Housing, ask a housing expert about enrollment, the waiting list, housing location and costs. The Mesa office is not a housing unit.':
 'For Workforce Housing, use the Apply to Workforce Housing link at https://www.theworkeraz.org/get-housing or ask staff for application help. The page advertised a two-to-three-month wait when checked September 9, 2026; confirm today’s estimate. Ask about location and costs. The Mesa office is not a housing unit.'}
for before,after in replacements.items():
 assert old.count(before)==1,before
 old=old.replace(before,after)
worker['informationText']=old
qsource={'kind':'operator-maintenance-pilot','date':'2026-09-09','sourcePackageSha256':source['sha256'],'providerVerificationInferred':False}
attach_questions(worker,make_questions([{
 'question':'What room arrangement and follow-up does Workforce Housing offer now?',
 'explanation':'The overview still describes a private room in a shared unit and nine months of follow-up. The dedicated housing page describes a shared one-bedroom apartment and one year of follow-up. Neither page explains which description applies now. Ask 602-755-5627 about room privacy, the current stay and follow-up, and whether these are different arrangements. Also settle the costs and locations in the existing housing question. The draft now avoids promising a private room or a specific follow-up period.\n\nhttps://www.theworkeraz.org/what-we-do\nhttps://www.theworkeraz.org/get-housing'
}],qsource))
cabin=rows['73dfadc219f93cdde3c2e07d3e1045b4']
needle='For help, call 480-285-4111 or email info@onesmallstepaz.org.'
assert needle in cabin['informationText']
cabin['informationText']=cabin['informationText'].replace(needle,needle+' If you cannot visit because of a crisis or transportation problem, ask your service provider about PINCH pickup. Clothes Cabin accepts requests from local service providers; your helper should confirm they can use it. Work shoes still require a new job.')
attach_questions(cabin,make_questions([{
 'question':'Can TSO missionaries use PINCH to collect items for someone who cannot visit?',
 'explanation':'Clothes Cabin invites local service providers to request small emergency orders for people in crisis, without transportation, or otherwise unable to visit. Providers collect under their agency information; the page does not name TSO or explain whether its missionaries qualify. Call 480-285-4111 to confirm who can request and collect an order, using https://www.onesmallstepaz.org/pages/pinch. Do not promise pickup until that is settled. The ordinary walk-in service remains available without a referral.'
}],qsource))
deposit=rows['987a8b8eb5e82e8c0216ef7bb436693f']
deposit['informationText']=deposit['informationText'].replace('The linked form asks for photo ID','The saved FY25/26 paper form asks for photo ID')
deposit['informationText']=deposit['informationText'].replace('the form lists fax','that paper form lists fax')
deposit['informationText']=deposit['informationText'].replace('The linked form asks for at least 14 days','The saved FY25/26 paper form asks for at least 14 days')
deposit['informationText']=deposit['informationText'].replace('on the linked form.','on that paper form.')
deposit['informationText']=deposit['informationText'].replace('Ask for the current checklist and help obtaining missing documents.','Ask for the current form and checklist, and help obtaining missing documents. The current online application could not be read during this check.')

findings=json.loads((P/'primary-findings.json').read_text())['findings']
targeted=json.loads((P/'targeted-findings.json').read_text())['findings']
decisions=[]
for r in data['resources']:
 original=source['resources'][r['id']]
 changes=[{'field':k,'before':deepcopy(original.get(k)),'after':deepcopy(v),'reason':'Source-supported maintenance draft; existing questions, answers and verification fields preserved.'}
          for k,v in r.items() if original.get(k)!=v]
 if changes:r['lastModified']=stamp
 sources=sorted({u for f in targeted if f['resourceId']==r['id'] for u in f['sources']}) or [r['website']]
 finding=next(f for f in findings if f['resourceId']==r['id'])
 reason='Retain: useful service with a reachable starting point; preserve its specific eligibility and open questions. '+finding['finding']
 decisions.append({'resourceId':r['id'],'originalName':original['name'],'disposition':'retain','targetResourceIds':[r['id']],
  'reason':reason,'evidence':[{'kind':'web-and-saved-research','reference':u,'checkedAt':'2026-09-09','note':'See primary and targeted findings for actual retrieval limits; this is not a provider call.'} for u in sources],
  'fieldChanges':changes,'serviceScopeChanges':[],'questionActions':[{'questionId':q['id'],'action':'preserved','reason':'No human resolution or authoritative settlement established.'} for q in original.get('openQuestions',[])],
  'uncertainties':[q['question'] for q in r.get('openQuestions',[])],'originalRecordReference':'source-resources.json#'+r['id']})
data['lastModified']=stamp
data['packageCreatedAt']=stamp
data['packageVersion']=int(source['data']['packageVersion'])+1
data['scoutPilotScope'].update({'reviewedAt':stamp,'humanApprovalsCreated':0,'scope':'partial','sourcePagesNotCompleteVerification':True,'selectedResources':12,'unreviewedOfficeResources':256})
payload=write_package(data,source['assets'])
draft=P/'mesa-maintenance-editor-draft.zip'
if draft.exists():
 existing=read_package(draft.read_bytes())
 assert existing['data']==data and existing['assetHashes']==source['assetHashes'],'Refuse to replace a different saved draft'
 payload=draft.read_bytes()
else:draft.write_bytes(payload)
save('draft-resources.json',data)
ledger={'formatVersion':1,'run':{'editor':'Codex coordinator','exactModelVersion':None,'date':'2026-09-09','office':'Mesa','trialMode':'Operator-led maintenance and editorial review, same context',
 'sourceFilename':'source-package.zip','sourceSha256':source['sha256'],'sourceRecordCount':12,'researchScope':'Partial twelve-resource recheck; source attempts and unresolved gaps recorded separately','previousResultExposure':'Saw saved editorial decisions and curator questions; not blind; no outside researcher.'},
 'decisions':decisions,'newOutputResources':[],'suggestions':[],
 'output':{'filename':draft.name,'sha256':hashlib.sha256(payload).hexdigest(),'finalUniqueResources':12}}
save('editorial-decisions.json',ledger)
store=ResearchStore(OUT/'pilot.sqlite3')
w=LearningWorkbench(store)
save('editorial-import.json',w.import_editorial((P/'source-package.zip').read_bytes(),(P/'editorial-decisions.json').read_bytes()))
e=EvidenceLedger(store)
before=e.import_package('mesa-maintenance-editor-20260909','AutoMesa',(P/'source-package.zip').read_bytes(),scope='partial')
after=e.import_package('mesa-maintenance-editor-20260909','AutoMesa',payload,scope='partial')
comparison=e.compare(before['id'],after['id'],reviewer='Codex operator/editor',lineage_note='Draft derived from the twelve saved records; same IDs. These are AI edits and new unresolved questions, not human curation or provider confirmation.')
save('package-comparison.json',comparison)
save('collection-receipt.json',w.collect_comparisons())
save('feedback.json',w.feedback_queue())
save('inbox.json',w.inbox())
assert not w.manifest()['entries']
# Use the common resource application with an isolated storage identity. Keep
# the embedded office identity AutoMesa so a later explicit merge remains valid.
rendered=render_scout_review_seed(data,location_name='MesaMaintenancePilot',source_sha256=hashlib.sha256(payload).hexdigest(),category_ids=['housing','employment','clothing'])
document=rendered.content.decode().replace('content="AutoMesaMaintenancePilot"','content="AutoMesa"')
banner='<div style="padding:12px;background:#fff4cf;text-align:center;font:16px system-ui">Partial maintenance draft: 12 Mesa resources. <a href="mesa-maintenance-editor-review.html">What changed and questions to settle</a>. No human verification added.</div>'
document=re.sub(r'(<body\b[^>]*>)',lambda m:m.group(1)+banner,document,count=1)
(OUT/'autoMesaMaintenancePilot.html').write_text(document)
(OUT/draft.name).write_bytes(payload)
print(json.dumps({'retained':12,'editedResources':sum(bool(d['fieldChanges']) for d in decisions),'originalQuestions':sum(len(r.get('openQuestions',[])) for r in source['resources'].values()),'draftQuestions':sum(len(r.get('openQuestions',[])) for r in rows.values()),'newLessons':0,'activeLessons':0}))
