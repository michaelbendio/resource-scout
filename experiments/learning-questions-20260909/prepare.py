"""Seal the question-audit experiment and its attributed editorial evidence."""
from pathlib import Path
import hashlib,json
from resource_research_agent.improvement_packages import write_package
from resource_research_agent.storage import ResearchStore
from resource_research_agent.learning_workbench import LearningWorkbench
P=Path(__file__).resolve().parent;ROOT=P.parents[1];OUT=ROOT/'output/learning-questions-20260909';OUT.mkdir(exist_ok=True)
w=LearningWorkbench(ResearchStore(OUT/'trial.sqlite3'))
def save(name,value): (P/name).write_text(json.dumps(value,indent=2)+'\n')
prior=ROOT/'experiments/learning-primary-20260909'
responses={a:json.loads((prior/(a+'-response.json')).read_text()) for a in ('baseline','candidate')}
ids=['step','egcareers','dvr']
training={'resourcePackageSchemaVersion':3,'packageVersion':1,'officeName':'Denver','categories':[{'id':'employment','label':'Employment','filters':[]}],'forGroups':[],
 'resources':[{'id':cid,'name':cid,'categories':['employment'],'scoutQuestionExperimentEvidence':{a:next(c for c in responses[a]['cases'] if c['caseId']==cid) for a in responses}} for cid in ids]}
raw=write_package(training,{})
(P/'support-package.zip').write_bytes(raw)
reasons=[
 'AI question review of the prior paired trial: a candidate question requested fee information already published on its cited Step application page; bed availability in the same question remained a real current gap. No overall resource selection or human provider verification is asserted.',
 'AI question review of the prior paired trial: both versions asked about studying outside Emily Griffith although the cited CAREERS FAQ says that is allowed. Individual eligibility can still require clarification. No human provider verification is asserted.',
 'Counterevidence: the dated DVR waitlist notice did not establish present availability for a particular applicant. Do not remove a consequential current-status question merely because a historical page discusses the topic.']
ledger={'formatVersion':1,'run':{'sourceSha256':hashlib.sha256(raw).hexdigest(),'sourceRecordCount':3,'editor':'Astra coordinator, question-quality review only','sourceExperiment':'experiments/learning-primary-20260909','sourceResponseHashes':{a:hashlib.sha256((prior/(a+'-response.json')).read_bytes()).hexdigest() for a in responses}},
 'decisions':[{'resourceId':cid,'disposition':'unreviewed','targetResourceIds':[],'reason':reason} for cid,reason in zip(ids,reasons)],'newOutputResources':[],'output':{'finalUniqueResources':0}}
save('support-editorial-review.json',ledger)
imported=w.import_editorial(raw,json.dumps(ledger,indent=2).encode())
# Save the exact imported bytes, not an independently serialized equivalent.
(P/'support-editorial-review.json').write_bytes(json.dumps(ledger,indent=2).encode())
baseline=ROOT/'resource_research_agent/playbook_library/employment.json';base=baseline.read_text()
proposal={'title':'Check proposed curator questions against reviewed sources','supportIds':imported['observationIds'][:2],
 'scope':{'office':'Denver','category':'employment','stage':'research'},
 'hypothesis':'A final source check can turn already answered questions into useful resource facts while retaining consequential uncertainty.',
 'alternativeExplanation':'Astra may already do this without another instruction; differences may reflect source retrieval or model variation rather than the instruction.',
 'counterexample':'A dated waitlist notice, general eligibility page or historical timetable does not establish a current place, an individual determination or a new start date. Preserve questions needed to avoid misleading a patron.',
 'baseline':{'path':str(baseline.relative_to(ROOT)),'sha256':hashlib.sha256(base.encode()).hexdigest(),'text':base},
 'addition':'Before handing off curator questions, check each against the official source pages you actually reviewed, including relevant FAQs and application instructions. If those sources answer it, put the supported answer in the resource and remove the question. If they partly answer it, retain only the unresolved part. Keep consequential gaps and contradictions explicit, including problems with dated information. Do not treat silence as a negative answer or suppress a needed question just to shorten the list.',
 'evaluationQuestion':'Does source-checking reduce avoidable curator questions without losing consequential questions, essential resource details or useful options?'}
distillation={'reviewer':'Astra coordinator under Michael authorization for a bounded learning demonstration','observationIds':imported['observationIds'][:2], 'counterevidenceIds':imported['observationIds'][2:], 'kind':'method','interpretation':'Two recurring question-quality observations suggest a single final source-check method. Keep current availability uncertainty distinct from information already supplied. This is AI editorial evidence, not phone-vetted ground truth.','proposal':proposal}
save('distillation.json',distillation);distilled=w.distill(distillation);save('distillation-receipt.json',distilled)
leads=[('workoptions','Work Options — culinary training','https://workoptions.org/'),('micasa','Mi Casa Resource Center — Career Pathways','https://micasaresourcecenter.org/careerpathways/'),('activate','ActivateWork — technical training','https://activatework.org/learn/tuition-free-tech-training/'),('indian','Denver Indian Center — employment and training','https://www.denverindiancenter.org/'),('secondchance','Second Chance Center — employment support','https://scccolorado.org/'),('employmentfirst','Colorado Employment First — Denver access','https://cdhs.colorado.gov/employment-first')]
data={'resourcePackageSchemaVersion':3,'packageVersion':1,'officeName':'Denver','categories':[{'id':'employment','label':'Employment','filters':[]}],'forGroups':[], 'resources':[{'id':i,'name':n,'website':u,'categories':['employment']} for i,n,u in leads]}
raw=write_package(data,{});(P/'source-package.zip').write_bytes(raw);source=w.register_package(raw)
rubric={'registeredBeforeDispatch':True,'sample':'Six fresh Denver-area Employment leads, excluding all supporting/counterexample resource IDs. Purposive sample, not a whole-category run.',
 'primaryMeasure':'Count distinct avoidable question issues answered by a source that the same respondent actually cited. Split compound questions into issues; a partly answered question is not wholly avoidable. Record fully or partly source-answerable questions separately from optional or out-of-scope questions.',
 'safetyMeasures':['Retain consequential source gaps, conflicting claims and dated-information uncertainty.','Do not invent an answer, eligibility rule, current opening, verification or free service.','Preserve essential restrictions and the practical entry route; selection differences alone are not errors.'],
 'decisionRule':'Promising only if avoidable question issues decrease by at least two across at least two cases, no consequential question is wrongly suppressed, and no new material factual/selection/detail error is introduced. Baseline floor means no-clear-benefit, not failure of the principle. Missing or unreliable evidence means inconclusive.',
 'confirmation':'If promising, use a second six-lead set with unchanged guidance and the same rules before proposing activation. Do not repeat until positive; no live activation without a separate recorded review.',
 'sourceVariation':'Score newly discovered source answers separately from answers missed on an already cited page. Cite dated source evidence for judgments; unavailable sources remain unscored or uncertain.',
 'modelsAndBudget':'Same gpt-6-astra high effort, fresh ephemeral contexts, 12 minutes per process and 24 web calls / 24 source pages instructed. Archive actual elapsed time, CLI usage and timed events. Dollar cost unknown; no model purchases.',
 'isolation':'Send a neutral delivery packet omitting the arm label and context metadata; keep canonical packet and delivery hashes. Do not share rubric, training observations or opposing results with either respondent.',
 'limitations':'One model, unblinded coordinator; source availability can differ. CLI web-call trace may not expose batched page counts. No claim of statistical reliability or human curation.'}
spec={'name':'Denver Employment final question source-check','operator':'Astra under Michael authorization','reason':'Demonstrate the learning loop with one observed question-quality problem','modelConfig':{'provider':'OpenAI Codex CLI','model':'gpt-6-astra','settings':{'reasoningEffort':'high','webSearch':'live','ephemeral':True}},'sourceSha256':source['sourceSha256'],'cases':[{'caseId':i,'resourceId':i} for i,_,_ in leads], 'maxAssignments':2,'maxSeconds':1800,'evaluationBasis':json.dumps(rubric,sort_keys=True),'researchProtocol':{'version':2,'maxSourcePages':24,'maxWebCalls':24}}
trial=w.prepare_trial(distilled['lessonId'],spec)
for name,obj in [('proposal.json',proposal),('rubric.json',rubric),('specification.json',spec),('trial.json',trial)]:save(name,obj)
# Routing identifiers are opaque; the respondent does not receive arm labels.
for arm,context in [('baseline','qreview-session-7eaf'),('candidate','qreview-session-23bd')]:
 packet=w.packet(trial['trialId'],arm,context,fresh=True);save(arm+'-packet.json',packet)
 delivery={k:v for k,v in packet.items() if k not in ('arm','contextId','trialId')}
 save(arm+'-delivery.json',delivery)
print('Sealed six-lead question-audit trial, with real editorial evidence and a counterexample. No active lessons.')
