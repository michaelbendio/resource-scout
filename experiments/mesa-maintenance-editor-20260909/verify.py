"""Offline integration verification of actual pilot artifacts; never calls a model."""
import hashlib,json,tempfile
from pathlib import Path
from resource_research_agent.improvement_packages import read_package
from resource_research_agent.open_questions import validate_questions
from resource_research_agent.storage import ResearchStore
from resource_research_agent.learning_evidence import EvidenceLedger
from resource_research_agent.learning_workbench import LearningWorkbench
P=Path(__file__).resolve().parent
load=lambda n:json.loads((P/n).read_text())
if (P/'artifact-hashes.json').exists():
 for name,sha in load('artifact-hashes.json').items():
  assert hashlib.sha256((P/name).read_bytes()).hexdigest()==sha,name
assert hashlib.sha256((P/'primary-findings.json').read_bytes()).hexdigest()==load('primary-freeze.json')['sha256']
original=read_package((P/'source-package.zip').read_bytes())
draft=read_package((P/'mesa-maintenance-editor-draft.zip').read_bytes())
assert len(original['resources'])==len(draft['resources'])==12
assert set(original['resources'])==set(draft['resources'])
assert original['assetHashes']==draft['assetHashes']
assert draft['data']['packageVersion']>original['data']['packageVersion']
assert draft['data']['scoutPilotScope']['scope']=='partial'
assert draft['data']['deletions']==original['data']['deletions']
assert draft['data']['deletionRequests']==original['data']['deletionRequests']
changed=[]
for rid,old in original['resources'].items():
 new=draft['resources'][rid]
 for field in ('categories','categoryFilters','forGroups','verifiedOn','pdfs'):
  assert old.get(field)==new.get(field),(rid,field)
 validate_questions(new.get('openQuestions',[]))
 new_questions={q['id']:q for q in new.get('openQuestions',[])}
 for q in old.get('openQuestions',[]):assert new_questions[q['id']]==q
 for q in new_questions.values():assert q['status']=='open'
 if old!=new:
  changed.append(rid)
  assert set(k for k in new if new.get(k)!=old.get(k))<={'informationText','openQuestions','lastModified'}
  assert new['lastModified']>old['lastModified']
  for heading in ('Programs and Services','Eligibility Requirements','How to Best Connect','Access','Important Information to Know'):
   assert new['informationText'].count('**'+heading+'**')==1
assert len(changed)==3
assert sum(len(r.get('openQuestions',[])) for r in draft['resources'].values())==16
with tempfile.TemporaryDirectory() as temp:
 store=ResearchStore(Path(temp)/'replay.sqlite3')
 w=LearningWorkbench(store)
 first=w.import_editorial((P/'source-package.zip').read_bytes(),(P/'editorial-decisions.json').read_bytes())
 assert first==load('editorial-import.json')
 assert w.import_editorial((P/'source-package.zip').read_bytes(),(P/'editorial-decisions.json').read_bytes())==first
 e=EvidenceLedger(store)
 before=e.import_package('mesa-maintenance-editor-20260909','AutoMesa',(P/'source-package.zip').read_bytes(),scope='partial')
 after=e.import_package('mesa-maintenance-editor-20260909','AutoMesa',(P/'mesa-maintenance-editor-draft.zip').read_bytes(),scope='partial')
 saved=load('package-comparison.json')
 comparison=e.compare(before['id'],after['id'],reviewer='Codex operator/editor',lineage_note='Draft derived from the twelve saved records; same IDs. These are AI edits and new unresolved questions, not human curation or provider confirmation.')
 assert comparison['id']==saved['id']
 assert comparison['events']==saved['events']
 assert w.collect_comparisons()['newObservationVersions']==5
 assert w.collect_comparisons()['newObservationVersions']==0
 inbox=w.inbox()
 assert inbox['recordCounts']['observation']==17
 assert inbox['lessons']==[] and not w.manifest()['entries']
 assert not w.feedback_queue()['providerVerificationInferred']
print('Passed: exact question/history and attachment preservation, partial scope, three edits, idempotent editorial/feedback replay, no activation.')
