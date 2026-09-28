import json
import sqlite3
import zipfile
from pathlib import Path
from resource_research_agent.evaluation.protocol import file_hash


def fixture(root):
    root = Path(root); package = root/'original.zip'; source = root/'source.sqlite3'
    with zipfile.ZipFile(package,'w') as archive:
        archive.writestr('tso-resources.json',json.dumps(dict(resourcePackageSchemaVersion=3,
            packageVersion=1,officeName='Mesa TSO',serviceArea='Mesa, Arizona',
            categories=[dict(id='housing',name='Housing',filters=[])], forGroups=[],
            resources=[dict(id='original-known',name='Original Known Shelter',categories=['housing'],
                            website='https://original.example.org',description='Original known provider',informationText='')])) )
    db=sqlite3.connect(source);db.execute('PRAGMA journal_mode=WAL')
    db.executescript('''CREATE TABLE imports(id INTEGER,source_sha256 TEXT);
      CREATE TABLE focused_research_jobs(id INTEGER,run_id INTEGER,import_id INTEGER,category_id TEXT,status TEXT,experiment_mode TEXT,playbook_version TEXT,plan_json TEXT);
      CREATE TABLE focused_research_passes(id INTEGER,job_id INTEGER,ordinal INTEGER,status TEXT,pass_kind TEXT,contribution_id INTEGER,focus_key TEXT);
      CREATE TABLE manual_discovery_contributions(id INTEGER,raw_text TEXT);''')
    from resource_research_agent.focused_research import build_focused_plan
    from resource_research_agent.playbooks import playbook_for
    plan=build_focused_plan(playbook_for('housing','Housing','Mesa, Arizona'),import_id=7,category_id='housing',category_label='Housing',office_name='Mesa TSO',service_area='Mesa, Arizona',experiment_mode='codex-first-v1')
    db.execute('INSERT INTO imports VALUES (?,?)',(7,file_hash(package)))
    db.execute('INSERT INTO focused_research_jobs VALUES (11,13,7,?,?,?,?,?)',('housing','completed','codex-first-v1',plan['playbookVersion'],json.dumps(plan)))
    keys=[f['key'] for f in plan['focuses']]+['gap']
    for i,key in enumerate(keys,1):
        db.execute('INSERT INTO focused_research_passes VALUES (?,11,?,?,?,?,?)',(i,i,'completed','gap' if key=='gap' else 'focus',i,key))
        db.execute('INSERT INTO manual_discovery_contributions VALUES (?,?)',(i,'SECRET_REVIEWER_CANARY'))
    db.commit()
    config=dict(experimentId='synthetic-housing',codeCommit='synthetic-fixture',condition='existing-policy',categories=['housing'],
        selectionReason='One predetermined primary run, before examining outcome quality.',sampleSeed=927,
        baseline=dict(sourceDb=str(source),originalPackage=str(package),importId=7,jobIds={'housing':11},
            expectedSourceSha256=file_hash(package),experimentMode='codex-first-v1',redactRecoveryTargets=False,
            playbookVersions={'housing':plan['playbookVersion']},historicalModel=None,historicalModelUnknownReason='Fixture has no provider execution.'),
        provider=dict(endpoint='https://api.deepseek.com/anthropic/v1/messages',model='deepseek-flash',acceptedModels=['deepseek-flash'],
            thinking={'type':'enabled'},effort='max',maxOutputTokens=1000,maxInputTokens=100000,maxSearchUses=2,maxFetchesPerTurn=3,timeoutSeconds=10),
        limits=dict(callsPerCategory=60,activeSecondsPerCategory=3600,maxTurns=24,maxRecoveries=2),
        pricing=dict(version='synthetic-v1',verified=False,reference='synthetic fixture, not live pricing',
            inputPerMillion='1',cacheHitPerMillion='0.1',cacheWritePerMillion='1',outputPerMillion='2',searchPerUse='0.01',
            inputAccounting='exclusive',reasoningIncludedInOutput=True,inputBoundCoversToolContext=True),
        criteria=dict(version='synthetic-v1',essentialNeeds=['emergency shelter'],frozenBy='synthetic fixture'))
    return config,db
