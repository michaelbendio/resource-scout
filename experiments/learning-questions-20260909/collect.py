"""Collect actual paired replies and instrumentation; no scoring or activation."""
import hashlib,json
from pathlib import Path
from resource_research_agent.storage import ResearchStore
from resource_research_agent.learning_workbench import LearningWorkbench
P=Path(__file__).resolve().parent;ROOT=P.parents[1];OUT=ROOT/'output/learning-questions-20260909'
w=LearningWorkbench(ResearchStore(OUT/'trial.sqlite3'))
load=lambda p:json.loads(p.read_text())
trial=load(P/'trial.json');measurements={}
for arm in ('baseline','candidate'):
 out=OUT/arm;run=load(out/'run.json')
 if run['status']!='finished' or run['returncode']!=0:raise RuntimeError('Incomplete model execution; preserve its files and report the blocker')
 packet=load(P/(arm+'-packet.json'))
 receipt={'contextId':packet['contextId'],'fresh':True,'modelConfig':packet['modelConfig'],'incrementalCostUSD':None,'interventions':0,
 'notes':'Actual ephemeral CLI response; requested Astra high with no fallback. Neutral archived delivery omits only routing metadata. Exact raw response, delivery hash, prompt hash, event trace and event timing retained. No human verification. CLI does not independently expose backend model identity or all batched page counts.'}
 raw=(out/'response.txt').read_text();saved=w.submit(trial['trialId'],arm,raw,receipt)
 (P/(arm+'-response.json')).write_text(raw)
 (P/(arm+'-receipt.json')).write_text(json.dumps(receipt,indent=2)+'\n')
 for name in ('run.json','events.jsonl','timed-events.jsonl'):(P/(arm+'-'+name)).write_bytes((out/name).read_bytes())
 events=[json.loads(l) for l in (out/'events.jsonl').read_text().splitlines()]
 typed=[e.get('item',{}).get('type') for e in events if e.get('type')=='item.completed']
 usage=next(e['usage'] for e in events if e['type']=='turn.completed')
 timings=[json.loads(l) for l in (out/'timed-events.jsonl').read_text().splitlines()]
 starts={};web_durations=[]
 for entry in timings:
  event=entry['event'];item=event.get('item',{})
  if item.get('type')!='web_search':continue
  if event['type']=='item.started':starts[item['id']]=entry['elapsedSeconds']
  elif item['id'] in starts:web_durations.append(entry['elapsedSeconds']-starts[item['id']])
 result=json.loads(raw.strip().removeprefix('```json').removesuffix('```').strip())
 measurements[arm]={'processSeconds':run['elapsedSeconds'],'webCalls':typed.count('web_search'),'observedWebCallSeconds':sum(web_durations),'timedWebCalls':len(web_durations),'sourcePages':None,'unexpectedCompletedItemTypes':sorted(set(typed)-{'web_search','agent_message','reasoning'}),
 'cliUsage':usage,'uncachedInputTokens':usage['input_tokens']-usage['cached_input_tokens'],'questionEntries':sum(len(c['openQuestions']) for c in result['cases']), 'responseWords':len(raw.split()),'incrementalCostUSD':None,'complete':saved['complete'],'late':saved['late'],'deliverySha256':hashlib.sha256((P/(arm+'-delivery.json')).read_bytes()).hexdigest()}
(P/'measurements.json').write_text(json.dumps(measurements,indent=2)+'\n')
print(json.dumps({arm:{k:m[k] for k in ('processSeconds','webCalls','questionEntries','complete','late')} for arm,m in measurements.items()}))
