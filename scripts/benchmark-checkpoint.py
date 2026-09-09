#!/usr/bin/env python3
"""Read a saved checkpoint without modifying its database; benchmark in a temporary DB."""
from contextlib import closing
import argparse
import json
from pathlib import Path
import sqlite3
import tempfile
from time import perf_counter
from resource_research_agent.project_state import decode_project_state, encode_project_state
from resource_research_agent.performance import measured, timing_session, summarize_timings
from resource_research_agent.research_execution import validate_execution
p=argparse.ArgumentParser();p.add_argument('database');p.add_argument('--project',type=int,required=True)
p.add_argument('--output',required=True);p.add_argument('--repetitions',type=int,default=2)
p.add_argument('--legacy-write',action='store_true')
a=p.parse_args();out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
path=out/'timings.jsonl'
if path.exists():raise SystemExit('Use a new output directory to preserve prior measurements')
with timing_session(path):
 with closing(sqlite3.connect(Path(a.database).resolve().as_uri()+'?mode=ro',uri=True)) as source:
  with measured('checkpoint.database_read'):
   row=source.execute('SELECT state_json,revision FROM scout_improvement_projects WHERE id=?',(a.project,)).fetchone()
  if row is None:raise SystemExit('No such project')
  original,revision=row
 state=decode_project_state(original)
 with measured('research.execution_validation'):validate_execution(state)
 with tempfile.TemporaryDirectory() as temporary:
  c=sqlite3.connect(Path(temporary)/'checkpoint.db');c.execute('CREATE TABLE state(payload TEXT)');c.execute('INSERT INTO state VALUES(?)',(original,));c.commit()
  for i in range(a.repetitions):
   with measured('benchmark.save_total'):
    encoded=encode_project_state(state, compact=not a.legacy_write)
    with measured('checkpoint.database_write'):c.execute('UPDATE state SET payload=?',(encoded,))
    with measured('database.commit'):c.commit()
  c.close()
 with measured('benchmark.roundtrip_verify'):
  assert decode_project_state(encoded)==state
report={'source':str(Path(a.database).resolve()),'sourceProject':a.project,'sourceRevision':revision,
        'sourceReadOnly':True,'writeCodec':'legacy' if a.legacy_write else 'automatic-sharing','inputStoredCharacters':len(original),'outputStoredCharacters':len(encoded),
        'repetitions':a.repetitions,'roundtripEqual':True,**summarize_timings(path)}
(out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
