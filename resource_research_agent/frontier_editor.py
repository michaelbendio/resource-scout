"""Opt-in discovery: early frontier selection, existing research, final editing.

Model work is an explicit external assignment, not a hard-coded suitability
classifier. Original packages, replies and transitions remain attributable.
"""
import base64
from copy import deepcopy
import json
import re
from pathlib import Path
from .improvement_packages import ImprovementError, digest, nonempty, read_package, write_package, utcnow, next_timestamp
from .learning_workbench import LearningWorkbench, exact, texts
from .open_questions import attach_questions, make_questions
from .resource_writing import load_writing_guidance
from .scout_maintenance import MaintenanceWorkflow, validate_fields
from .scout_review import render_scout_review_seed, _replace_meta
from .meeting_edition import build_meeting_edition

SCHEMA='''CREATE TABLE IF NOT EXISTS scout_editor_projects (
 id TEXT PRIMARY KEY, early_reply TEXT, research_id INTEGER,
 final_source TEXT, final_reply TEXT, final_created_at TEXT, research_source TEXT, research_config TEXT
);'''
GUIDANCE_PATH = Path(__file__).with_name('editor_guidance') / 'default.json'


class FrontierEditorWorkflow:
    def __init__(self, store):
        self.store=store;self.learning=LearningWorkbench(store)
        with store.connect() as c:c.executescript(SCHEMA)

    def prepare(self, payload, office, configuration):
        exact(configuration,('name','editor','model','settings','sourceScope','categoryIds','authorityNote'),'Editor configuration')
        for k in ('name','editor','authorityNote'):nonempty(configuration[k],k)
        if configuration['model'] is not None:nonempty(configuration['model'],'Model')
        if not isinstance(configuration['settings'],dict):raise ImprovementError('Editor settings must be an object')
        if configuration['sourceScope'] not in ('full','partial','unknown'):raise ImprovementError('Declare source scope')
        categories=texts(configuration['categoryIds'],'Research categories')
        package=read_package(payload);office=nonempty(office,'Office')
        token=''.join(c for c in office if c.isalnum())
        if package['data'].get('officeName') not in (None,'',office,'Auto'+token):raise ImprovementError('Source office mismatch')
        if not set(categories)<={x['id'] for x in package['data']['categories']}:raise ImprovementError('Unknown research category')
        learned = self.learning.resolve_guidance(office, categories, 'editorial')
        with self.store.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            source=self.learning._artifact(c,'resource-package',payload)
            project={'sourceSha256':source,'office':office,'configuration':deepcopy(configuration),
                     'instructions':json.loads(GUIDANCE_PATH.read_text())['instructions'],'writingGuidance':load_writing_guidance()}
            if learned['lessons']:
                project['learnedGuidance'] = learned
            ident=self.learning._record(c,'editor-project',project)
            c.execute('INSERT OR IGNORE INTO scout_editor_projects(id) VALUES(?)',(ident,))
        return self.status(ident)

    def prepare_leads(self, baseline, raw, office, category_id, configuration):
        """Bridge Scout's existing manual-discovery contract into early editing."""
        from .manual_discovery import parse_manual_contribution
        package=read_package(baseline)
        if category_id not in configuration['categoryIds']:
            raise ImprovementError('Lead category must be selected for research')
        with self.store.connect() as c:
            base=self.learning._artifact(c,'resource-package',baseline)
            source=self.learning._artifact(c,'discovery-leads',raw.encode('utf-8'))
        parsed=parse_manual_contribution(raw)
        if parsed['status']!='parsed' or len(parsed['leads'])!=len(parsed['parsed']['leads']):
            raise ImprovementError('Use the complete manual-discovery leads contract; raw input was preserved')
        data=deepcopy(package['data'])
        for lead in parsed['leads']:
            name=nonempty(lead['organization'],'Lead organization')
            if lead['program']:name+=' · '+lead['program']
            rid='scout-lead:'+digest({'sourceSha256':source,'ordinal':lead['ordinal']})[:24]
            if any(r['id']==rid for r in data['resources']):
                raise ImprovementError('This lead is already represented in the supplied baseline')
            data['resources'].append({'id':rid,'name':name,'description':lead['whyRelevant'],
                'informationText':'Research lead; eligibility and entry route still need investigation.',
                'phone':lead['phone'],'address':lead['address'],'website':lead['website'],'hours':'',
                'categories':[category_id],'categoryFilters':{},'forGroups':[],'pdfs':[],
                'scoutLeadEvidence':{'sourceSha256':source,'baselineSha256':base,'lead':deepcopy(lead),
                                     'providerVerificationInferred':False}})
        data['scoutLeadIntake']={'baselineSha256':base,'leadsSha256':source,'warnings':parsed['warnings']}
        # ZIP timestamps are fixed for reproducible preparation/restart.
        import io, zipfile
        stream=io.BytesIO()
        with zipfile.ZipFile(stream,'w',compression=zipfile.ZIP_DEFLATED) as archive:
            entries={'tso-resources.json':json.dumps(data,ensure_ascii=False,allow_nan=False).encode(),**package['assets']}
            for name,content in sorted(entries.items()):
                info=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
                archive.writestr(info,content)
        return self.prepare(stream.getvalue(),office,configuration)

    def _row(self,c,ident):
        row=c.execute('SELECT * FROM scout_editor_projects WHERE id=?',(ident,)).fetchone()
        if row is None:raise ImprovementError('Editor project not found')
        return row,self.learning._get(c,ident,'editor-project')

    def status(self,ident):
        with self.store.connect() as c:
            row,project=self._row(c,ident)
            return {'id':ident,'office':project['office'],
                    'stage':'complete' if row['final_reply'] else 'final-editor' if row['final_source'] else 'research' if row['early_reply'] else 'early-editor',
                    'researchProjectId':row['research_id'],'humanApprovalsCreated':0,'activeLessons':0}

    def _packet(self,c,ident,stage):
        if stage not in ('early','final'):raise ImprovementError('Select early or final editor')
        row,project=self._row(c,ident)
        if stage=='final' and not row['final_source']:raise ImprovementError('Finish the selected research before final editing')
        source=project['sourceSha256'] if stage=='early' else row['final_source']
        package=read_package(self.learning._bytes(c,source,'resource-package'))
        packet={'schemaVersion':1,'editorProjectId':ident,'stage':stage,'sourceSha256':source,
                'office':project['office'],'configuration':project['configuration'],'instructions':project['instructions'],
                'writingGuidance':project['writingGuidance'],'package':package['data'],
                'outputContract':{'assignmentSha256':'copy from assignment','decisions':[{
                    'resourceId':'source ID','disposition':'retain|combine|reserve|exclude',
                    'targetResourceIds':['retained ID'], 'reason':'specific practical judgment',
                    'evidence':['saved field or checked source supporting this decision'],
                    'fields':{},'questions':[]} ]}}
        if project.get('learnedGuidance'):
            packet['learnedGuidance'] = deepcopy(project['learnedGuidance'])
            packet['instructions'] = [*packet['instructions'], 'Apply the sealed learnedGuidance methods only within their declared scope; they do not verify provider facts.']
        packet['assignmentSha256']=digest(packet)
        return packet

    def packet(self,ident,stage):
        with self.store.connect() as c:return self._packet(c,ident,stage)

    def _apply(self,project,packet,result,stamp):
        exact(result,('assignmentSha256','decisions'),'Editorial result')
        if result['assignmentSha256']!=packet['assignmentSha256']:raise ImprovementError('Editorial assignment changed')
        data=deepcopy(packet['package']);original={r['id']:r for r in data['resources']}
        decisions=result['decisions']
        if not isinstance(decisions,list):raise ImprovementError('Editorial decisions need an array')
        ids=[]
        for d in decisions:
            exact(d,('resourceId','disposition','targetResourceIds','reason','evidence','fields','questions'),'Editorial decision')
            ids.append(nonempty(d['resourceId'],'Source ID'));nonempty(d['reason'],'Reason');texts(d['evidence'],'Evidence')
            if d['disposition'] not in ('retain','combine','reserve','exclude'):raise ImprovementError('Unknown editorial disposition')
        if len(ids)!=len(set(ids)) or set(ids)!=set(original):raise ImprovementError('Account for every original exactly once')
        retained={d['resourceId'] for d in decisions if d['disposition']=='retain'}
        output={rid:deepcopy(original[rid]) for rid in original if rid in retained}
        for d in decisions:
            rid=d['resourceId'];targets=texts(d['targetResourceIds'],'Targets',empty=True)
            if not set(targets)<=retained:raise ImprovementError('Every combination must target a retained identity')
            if d['disposition']=='retain' and targets!=[rid]:raise ImprovementError('Retained resources keep their identity')
            if d['disposition']=='combine' and len(targets)!=1:raise ImprovementError('Initial editor integration supports one combination destination; splits require a separate reviewed identity plan')
            if d['disposition'] in ('reserve','exclude') and targets:raise ImprovementError('Omitted resources cannot have output targets')
            if not isinstance(d['fields'],dict):raise ImprovementError('Fields must be an object')
            if packet['stage']=='early' and d['fields']:raise ImprovementError('Early review selects leads; writing changes belong to final editing')
            if d['disposition']!='retain' and (d['fields'] or d['questions']):raise ImprovementError('Write changes/questions on a retained destination')
            additions=make_questions(d['questions'],{'kind':'frontier-editor','projectId':packet['editorProjectId'],'stage':packet['stage']})
            if d['disposition']=='retain':
                output[rid].update(validate_fields(d['fields'],data,project['writingGuidance']))
                attach_questions(output[rid],additions)
        for d in decisions:
            for target in d['targetResourceIds']:
                dest=output[target];source=original[d['resourceId']]
                if target!=d['resourceId']:
                    existing={q['id']:q for q in dest.get('openQuestions',[])}
                    for q in source.get('openQuestions',[]):
                        if q['id'] in existing and q!=existing[q['id']]:
                            raise ImprovementError('Combination has conflicting question histories; settle the conflict before combining')
                    attach_questions(dest,source.get('openQuestions',[]))
                    paths={p['path'] for p in dest.get('pdfs',[])}
                    dest.setdefault('pdfs',[]).extend(deepcopy(p) for p in source.get('pdfs',[]) if p['path'] not in paths)
                dest.setdefault('scoutEditorHistory',[]).append({'projectId':packet['editorProjectId'],'stage':packet['stage'],
                    'sourceSha256':packet['sourceSha256'],'originalRecord':deepcopy(source),'decision':deepcopy(d),
                    'providerVerificationInferred':False})
        for rid,r in output.items():
            validate_fields({k:r.get(k,{} if k=='categoryFilters' else []) for k in ('categories','categoryFilters','forGroups')},data,project['writingGuidance'])
            r['lastModified']=stamp
        # Prune unused navigation terms; retain office category definitions for gap research.
        label=lambda x:x.get('label',x.get('name','')) if isinstance(x,dict) else x
        if packet['stage']=='final':
            used_groups={g for r in output.values() for g in r.get('forGroups',[])}
            data['forGroups']=[g for g in data['forGroups'] if label(g) in used_groups]
            for cat in data['categories']:
                used={t for r in output.values() for t in r.get('categoryFilters',{}).get(cat['id'],[])}
                cat['filters']=[t for t in cat.get('filters',[]) if label(t) in used]
        data['resources']=list(output.values());data['packageCreatedAt']=stamp
        data['scoutFrontierEditorial']={'projectId':packet['editorProjectId'],'stage':packet['stage'],
            'sourceSha256':packet['sourceSha256'],'originalCount':len(original),'retainedCount':len(output),
            'omissionsAreOfficeDeletions':False,'humanApprovalsCreated':0}
        return data

    def submit(self,ident,stage,raw,receipt):
        exact(receipt,('editor','model','settings','contextId','notes'),'Editor receipt')
        for k in ('editor','contextId','notes'):nonempty(receipt[k],k)
        with self.store.connect() as c:
            row,project=self._row(c,ident);packet=self._packet(c,ident,stage)
            self.learning._record(c,'editor-submission',{'projectId':ident,'stage':stage,'raw':raw,'receipt':receipt})
        try:result=json.loads(raw)
        except json.JSONDecodeError as error:raise ImprovementError('Invalid editorial JSON; raw delivery preserved') from error
        with self.store.connect() as c:
            c.execute('BEGIN IMMEDIATE');row,project=self._row(c,ident);packet=self._packet(c,ident,stage)
            for k in ('editor','model','settings'):
                if receipt[k]!=project['configuration'][k]:raise ImprovementError('Editor receipt does not match sealed configuration')
            prior=row[stage+'_reply']
            if prior:
                saved=self.learning._get(c,prior,'editor-result')
                if saved['raw']!=raw or saved['receipt']!=receipt:raise ImprovementError('Editorial result is immutable')
                return {'resultId':prior,'outputSha256':saved['outputSha256']}
            stamp=next_timestamp([packet['package'],*packet['package']['resources']]);data=self._apply(project,packet,result,stamp)
            source=read_package(self.learning._bytes(c,packet['sourceSha256'],'resource-package'))
            payload=write_package(data,source['assets']);read_package(payload)
            output=self.learning._artifact(c,'resource-package',payload)
            doc={'projectId':ident,'stage':stage,'raw':raw,'receipt':deepcopy(receipt),'result':result,
                 'sourceSha256':packet['sourceSha256'],'outputSha256':output,'createdAt':stamp}
            result_id=self.learning._record(c,'editor-result',doc)
            for d in result['decisions']:
                self.learning._record(c,'observation',{'sourceClass':'ai-editorial-judgment','resourceIds':[d['resourceId']],
                    'sourceSha256':packet['sourceSha256'],'editorResultId':result_id,'stage':stage,
                    'decision':deepcopy(d),'providerVerificationInferred':False})
            column='early_reply' if stage=='early' else 'final_reply'
            c.execute(f'UPDATE scout_editor_projects SET {column}=? WHERE id=?',(result_id,ident))
        return {'resultId':result_id,'outputSha256':output}

    def start_research(self,ident,execution_config=None):
        with self.store.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            row,project=self._row(c,ident)
            if not row['early_reply']:raise ImprovementError('Complete early editorial selection first')
            if execution_config is None:
                if row['research_source']:
                    execution_config=json.loads(row['research_config'])
                else:
                    raise ImprovementError('Choose an explicit sampled execution configuration before starting research')
            if row['research_source'] and json.loads(row['research_config'])!=execution_config:
                raise ImprovementError('Research configuration is already sealed for this editor project')
            if row['research_id']:return {'researchProjectId':row['research_id']}
            if row['research_source']:
                payload=self.learning._bytes(c,row['research_source'],'resource-package')
            else:
                result=self.learning._get(c,row['early_reply'],'editor-result')
                package=read_package(self.learning._bytes(c,result['outputSha256'],'resource-package'))
                data=deepcopy(package['data']);data['officeName']=project['office']
                payload=write_package(data,package['assets'])
                source=self.learning._artifact(c,'resource-package',payload)
                c.execute('UPDATE scout_editor_projects SET research_source=?,research_config=? WHERE id=?',
                          (source,json.dumps(execution_config,sort_keys=True),ident))
        package=read_package(payload)
        # Persisted bytes/config make a retry after interruption reuse the run.
        research=MaintenanceWorkflow(self.store).prepare(payload,project['office'],
            list(package['resources']),project['configuration']['categoryIds'],
            run_name='Frontier discovery '+ident[:16],execution_config=execution_config)
        with self.store.connect() as c:
            c.execute('UPDATE scout_editor_projects SET research_id=? WHERE id=? AND research_id IS NULL',(research['id'],ident))
            saved=c.execute('SELECT research_id FROM scout_editor_projects WHERE id=?',(ident,)).fetchone()[0]
        return {'researchProjectId':saved}

    def finish_research(self,ident):
        with self.store.connect() as c:
            row,project=self._row(c,ident)
            if row['final_source']:return self._packet(c,ident,'final')
            if not row['research_id']:raise ImprovementError('Research has not started')
        flow=MaintenanceWorkflow(self.store)
        with self.store.connect() as c:
            state=flow._load(c,row['research_id'])
            if any(stage not in task['results'] for task in state['tasks'].values() for stage,_ in flow._task_stages(state,task)):
                raise ImprovementError('Finish every selected research/check/reconciliation task first')
        stamp=utcnow()
        edition=build_meeting_edition(flow,[(state['id'],state['revision'])],location_name=project['office'],created_at=stamp)
        # No partial or held findings are silently labelled ready for final editing.
        if edition.manifest['pendingTasks'] or edition.manifest['heldProposals']:
            raise ImprovementError('Research has held findings; settle them explicitly before the final editorial stage')
        # A completed assignment can still report bounded coverage and gaps.
        # Seal those qualifications with the exact research revision; exports
        # must not turn transport completion into a claim of exhaustive search.
        package=read_package(edition.package)
        coverage={'sourceScope':project['configuration']['sourceScope'],
                  'researchProjectId':state['id'],'researchRevision':state['revision'],
                  'categoryIds':deepcopy(project['configuration']['categoryIds']),
                  'meaning':'Selected assignments completed; remaining gaps are not demonstrated coverage.',
                  'assignments':[]}
        for task_id,task in state['tasks'].items():
            for stage,researcher in flow._task_stages(state,task):
                receipt=task['results'][stage].get('executionReceipt',{})
                coverage['assignments'].append({'taskId':task_id,'stage':stage,'researcher':researcher,
                    'coverageNotes':receipt.get('coverageNotes',''),
                    'remainingGaps':deepcopy(receipt.get('remainingGaps',[]))})
        package['data']['scoutDiscoveryCoverage']=coverage
        final_payload=write_package(package['data'],package['assets'])
        with self.store.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            source=self.learning._artifact(c,'resource-package',final_payload)
            c.execute('UPDATE scout_editor_projects SET final_source=?,final_created_at=? WHERE id=? AND final_source IS NULL',(source,stamp,ident))
            return self._packet(c,ident,'final')

    def export(self,ident,stage='final'):
        with self.store.connect() as c:
            row,project=self._row(c,ident)
            if stage not in ('early','final') or not row[stage+'_reply']:raise ImprovementError('Selected editorial stage is incomplete')
            saved=self.learning._get(c,row[stage+'_reply'],'editor-result')
            payload=self.learning._bytes(c,saved['outputSha256'],'resource-package')
        package=read_package(payload)
        rendered=render_scout_review_seed(package['data'],location_name=project['office'],source_sha256=saved['outputSha256'],
                                          category_ids=[c['id'] for c in package['data']['categories']])
        document=rendered.content.decode();artifact=re.search(r'<meta name="scout-review-artifact-id" content="([^"]+)"',document).group(1)
        document=_replace_meta(document,'tso-storage-id',artifact)
        assets=json.dumps({p:base64.b64encode(b).decode() for p,b in package['assets'].items()}).replace('</','<\\/')
        script='''<script>window.scoutPreviewAssetsReady=(async()=>{for(const [path,encoded] of Object.entries(ASSETS)){if(!await getPDF(path))await savePDF(path,new Blob([Uint8Array.from(atob(encoded),c=>c.charCodeAt(0))],{type:'application/pdf'}));}})();window.scoutPreviewAssetsReady.catch(e=>showAppError('Resource attachments',e.message));</script>'''.replace('ASSETS',assets)
        return {'package':payload,'html':document.replace('</body>',script+'</body>',1).encode(),'filename':rendered.filename,
                'manifest':{'projectId':ident,'stage':stage,'sourceSha256':saved['sourceSha256'],'outputSha256':saved['outputSha256'],
                            'sourceScope':project['configuration']['sourceScope'],
                            'researchCoverage':deepcopy(package['data'].get('scoutDiscoveryCoverage')),
                            'humanApprovalsCreated':0,'resources':len(package['resources'])}}
