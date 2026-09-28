"""Offline evidence replay; no model calls or production guidance changes."""
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
    prior=P.parent/'learning-pilot-20260909'
    w.import_editorial((prior/'source-package.zip').read_bytes(),(prior/'editorial-decisions.json').read_bytes())
    w.register_package((P/'source-package.zip').read_bytes())
    lesson=w.propose(load('proposal.json'));assert lesson==load('lesson.json')
    trial=w.prepare_trial(lesson['lessonId'],load('specification.json'));assert trial==load('trial.json')
    for arm in ('baseline','candidate'):
        receipt=load(arm+'-receipt.json')
        assert w.packet(trial['trialId'],arm,receipt['contextId'],fresh=True)==load(arm+'-packet.json')
        w.submit(trial['trialId'],arm,(P/(arm+'-response.json')).read_text(),receipt)
    report=w.assess(trial['trialId'],load('assessment.json'))
    assert report['quality']==load('report.json')['quality']
    assert report['assessment']['assessment']['conclusion']=='no-clear-benefit'
    assert w.manifest()['entries']==[]
print('Fresh-primary experiment replay passed; no AI calls or active guidance changes.')
