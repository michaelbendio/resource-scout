"""Replay preserved evidence only; no AI calls, new research or lesson activation."""
import hashlib
import json
from pathlib import Path
import tempfile
from resource_research_agent.storage import ResearchStore
from resource_research_agent.learning_workbench import LearningWorkbench
p=Path(__file__).parent
load=lambda n:json.loads((p/n).read_text())
for name,expected in load('artifact-hashes.json').items():
    assert hashlib.sha256((p/name).read_bytes()).hexdigest()==expected, name
with tempfile.TemporaryDirectory() as temp:
    work=LearningWorkbench(ResearchStore(Path(temp)/'replay.sqlite3'))
    work.import_editorial((p/'source-package.zip').read_bytes(),(p/'editorial-decisions.json').read_bytes())
    lesson=work.propose(load('lesson-proposal.json'))
    assert lesson==load('lesson-receipt.json')
    trial=work.prepare_trial(lesson['lessonId'],load('trial-specification.json'))
    assert trial==load('trial-receipt.json')
    for arm in ('baseline','candidate'):
        receipt=load(arm+'-receipt.json')
        packet=work.packet(trial['trialId'],arm,receipt['contextId'],fresh=True)
        assert packet==load(arm+'-packet.json')
        work.submit(trial['trialId'],arm,(p/(arm+'-response.json')).read_text(),receipt)
    report=work.assess(trial['trialId'],load('assessment.json'))
    assert report['quality']==load('report.json')['quality']
    assert report['assessment']['assessment']['conclusion']=='no-clear-benefit'
    assert report['active'] is False
print('Historical evidence replay passed. No model calls or active guidance changes.')
