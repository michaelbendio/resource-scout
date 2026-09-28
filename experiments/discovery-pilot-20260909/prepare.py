"""Prepare the isolated live pilot. No remote calls or synthetic research results."""
import json
from pathlib import Path
from resource_research_agent.storage import ResearchStore
from resource_research_agent.frontier_editor import FrontierEditorWorkflow
from resource_research_agent.improvement_packages import write_package

ROOT=Path(__file__).parent
OUT=Path('output/discovery-pilot-20260909')
OUT.mkdir(parents=True,exist_ok=True)
def save(name,value):
    (ROOT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')

baseline={'resourcePackageSchemaVersion':3,'packageVersion':1,'officeName':'Welfare Square Employment Pilot',
 'categories':[{'id':'employment','label':'Employment','filters':['Job Search','Staffing','Apprenticeships']}],
 'forGroups':[], 'categoryMigrations':[],'deletions':[],'deletionRequests':[],'changes':[],'resources':[]}
payload=write_package(baseline,{})
if (ROOT/'baseline.zip').exists(): payload=(ROOT/'baseline.zip').read_bytes()
else: (ROOT/'baseline.zip').write_bytes(payload)
leads={'leads':[
 {'organization':'Utah Department of Workforce Services','program':'Salt Lake Metro Employment Center',
  'website':'https://jobs.utah.gov/jobseeker/index.html','leadType':'access-point',
  'locationOrServiceArea':'Salt Lake City, Utah','whyRelevant':'Public job-search help and a local route to employment services.',
  'uncertainty':'Confirm current local contact and distinguish general job help from eligibility-screened training.'},
 {'organization':'Utah Electrical Training Alliance','program':'Inside Wireman apprenticeship',
  'website':'https://uteta.org/programs/careers-inside-wire/','leadType':'program',
  'locationOrServiceArea':'West Jordan training center; employers throughout Utah',
  'whyRelevant':'Paid work combined with electrical training may offer a career path.',
  'uncertainty':'Check entry costs, qualifications, waiting before paid work and travel requirements.'}]}
save('leads.json',leads)
config={'name':'Bounded Welfare Square Employment discovery pilot','editor':'Astra / Codex operator','model':None,
 'settings':{'context':'current Codex conversation; primary and editor share context'},'sourceScope':'partial',
 'categoryIds':['employment'],'authorityNote':'Authorized small pilot. Web research and AI editing; no human curation or office publication.'}
save('editor-configuration.json',config)
flow=FrontierEditorWorkflow(ResearchStore(OUT/'pilot.sqlite3'))
project=flow.prepare_leads(payload,(ROOT/'leads.json').read_text(),baseline['officeName'],'employment',config)
save('project.json',project)
packet=flow.packet(project['id'],'early');save('early-packet.json',packet)
reasons=[
 'Retain for research: a general public starting point near Welfare Square. Verify local contact and avoid implying that everyone qualifies for funded training.',
 'Retain for research: paid apprenticeship is a distinct option. Its length alone is not disqualifying; entry fees, selection delays and statewide travel may limit practical fit.']
result={'assignmentSha256':packet['assignmentSha256'],'decisions':[
 {'resourceId':r['id'],'disposition':'retain','targetResourceIds':[r['id']],'reason':reason,
  'evidence':[r['website'],'Initial lead, not confirmed access.'],'fields':{},'questions':[]}
 for r,reason in zip(packet['package']['resources'],reasons)]}
receipt={'editor':config['editor'],'model':None,'settings':config['settings'],'contextId':'codex-discovery-pilot-20260909',
 'notes':'Actual operator judgment in current conversation; no independent editor or human verification claimed.'}
save('early-response.json',result);save('editor-receipt.json',receipt)
flow.submit(project['id'],'early',json.dumps(result,ensure_ascii=False),receipt)
execution={'schemaVersion':1,'protocol':'astra-sampled-v1','version':'welfare-square-pilot-20260909',
 'serviceArea':'Welfare Square TSO context: Salt Lake City and reachable Salt Lake Valley services, Utah',
 'sampling':{'seed':'d28f9d7e-welfare-square-20260909','numerator':1,'denominator':3},
 'deliberateCategoryIds':[],'modelIdentities':{'Codex':None,'Claude':'Opus 5','ChatGPT':None,'Grok':None,'Perplexity':None}}
save('execution-configuration.json',execution)
save('research-project.json',flow.start_research(project['id'],execution))
print('Isolated pilot prepared; early decisions and research configuration saved.')
