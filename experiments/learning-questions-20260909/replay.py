"""Validate and replay saved experiment evidence in a temporary database; no AI calls."""
import hashlib,json,tempfile
from pathlib import Path
from resource_research_agent.storage import ResearchStore
from resource_research_agent.learning_workbench import LearningWorkbench
P=Path(__file__).parent
load=lambda name:json.loads((P/name).read_text())
for name,sha in load('artifact-hashes.json').items():
 assert hashlib.sha256((P/name).read_bytes()).hexdigest()==sha,name
with tempfile.TemporaryDirectory() as temp:
 w=LearningWorkbench(ResearchStore(Path(temp)/'replay.sqlite3'))
 w.import_editorial((P/'support-package.zip').read_bytes(),(P/'support-editorial-review.json').read_bytes())
 distilled=w.distill(load('distillation.json'));assert distilled==load('distillation-receipt.json')
 w.register_package((P/'source-package.zip').read_bytes())
 trial=w.prepare_trial(distilled['lessonId'],load('specification.json'));assert trial==load('trial.json')
 packets={}
 for arm in ('baseline','candidate'):
  receipt=load(arm+'-receipt.json')
  packet=w.packet(trial['trialId'],arm,receipt['contextId'],fresh=True)
  assert packet==load(arm+'-packet.json')
  delivery=load(arm+'-delivery.json')
  assert delivery=={k:v for k,v in packet.items() if k not in ('arm','contextId','trialId')}
  assert load(arm+'-run.json')['deliverySha256']==hashlib.sha256((P/(arm+'-delivery.json')).read_bytes()).hexdigest()
  assert not {'arm','contextId','trialId'}&delivery.keys()
  w.submit(trial['trialId'],arm,(P/(arm+'-response.json')).read_text(),receipt)
  packets[arm]=packet
 assert packets['baseline']['cases']==packets['candidate']['cases']
 assert packets['baseline']['instructions']==packets['candidate']['instructions']
 assert packets['baseline']['modelConfig']==packets['candidate']['modelConfig']
 assert packets['candidate']['guidance']==packets['baseline']['guidance']+'\n\n'+load('proposal.json')['addition']
 assert not {c['resourceId'] for c in packets['baseline']['cases']} & {'step','egcareers','dvr'}
 report=w.assess(trial['trialId'],load('assessment.json'))
 assert report['quality']==load('report.json')['quality']
 assert report['assessment']['assessment']['conclusion']==load('report.json')['assessment']['assessment']['conclusion']
 assert not w.manifest()['entries']
print('Question-audit experiment evidence replay passed. No model calls or production activation.')
