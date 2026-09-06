"""Office-wide group evidence and complete, explicitly reviewed category retirements.

Group outcomes are recommendations. Category retirements use the office reader's
existing categoryMigrations and deletion tombstones, with per-resource mappings.
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from copy import deepcopy
from urllib.parse import urlsplit

from .improvement_packages import ImprovementError, digest, nonempty, next_timestamp, read_package, resource_blocked, utcnow, write_package
from .scout_classification import FIELDS, evidence_snapshot, memberships, term_key, validate_guidance

SCHEMA = '''CREATE TABLE IF NOT EXISTS scout_taxonomy_exports (
 id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL, export_key TEXT NOT NULL UNIQUE,
 manifest_json TEXT NOT NULL, payload BLOB NOT NULL, acknowledged_at TEXT
);'''
OUTCOMES = ('retain', 'clarify', 'change-prominence', 'merge', 'retire')


def _same_provider(record):
    """A candidate cluster only, never an asserted provider identity."""
    site = str(record.get('website', '')).strip().split(';')[0].strip()
    try:
        host = urlsplit(site if '://' in site else 'https://' + site).hostname
    except ValueError:
        host = None
    if host:
        host = host.lower().removeprefix('www.')
    # Do not collapse unrelated providers using directories or shared social sites.
    if host and '.' in host and host not in {'facebook.com', 'instagram.com', 'linktr.ee', '211.org', 'utah211.org'}:
        return 'website:' + host
    phone = re.sub(r'\D', '', str(record.get('phone', '')))
    return 'phone:' + phone if len(phone) in (10, 11) else 'record:' + record['id']


class TaxonomyReview:
    def __init__(self, workflow):
        self.flow = workflow
        self.store = workflow.store
        self._packages = {}
        with self.store.connect() as c:
            c.executescript(SCHEMA)

    def _package(self, c, sha):
        if sha not in self._packages:
            if len(self._packages) >= 2: self._packages.clear()
            self._packages[sha] = self.flow._package(c, sha)
        return self._packages[sha]

    def _inputs(self, c, state):
        package = self._package(c, state['latestSha256'] or state['baseSha256'])
        fingerprint = digest({'package': package['sha256'], 'guidance': state['classificationGuidance'],
                              'research': state['resources'], 'reconnect': state.get('requiresReconnection', False)})
        return package, fingerprint

    def _records(self, package, state):
        records = {}
        # Research proposals carry their comparison baseline; the project source
        # remains the fallback, matching the ordinary classification reviewer.
        for rid, current in package['resources'].items():
            item = state['resources'].get(rid)
            proposal = item and item.get('proposal')
            record = deepcopy(current)
            if proposal and not item['packaged'] and not resource_blocked(package, rid):
                record = self.flow.materialize(proposal.get('comparisonBase', state['researchSnapshots'][rid]['resource']), current, proposal, {f:'proposed' for f in FIELDS})
            records[rid] = record
        return records

    def _report(self, c, state):
        package, fingerprint = self._inputs(c, state)
        proposed = self._records(package, state)
        live = {rid:r for rid,r in package['resources'].items() if not resource_blocked(package, rid)}
        terms = {(t['field'],t['categoryId'],t['value']):t for t in state['classificationGuidance']['terms']}
        names = {cat['id']:cat['label'] for cat in package['data']['categories']}
        cards = []
        for label in package['data']['forGroups']:
            current_ids = {rid for rid,r in live.items() if label in r.get('forGroups', [])}
            proposed_ids = {rid for rid in live if label in proposed[rid].get('forGroups', [])}
            union = current_ids | proposed_ids
            definition = terms.get(('forGroups','',label), {})
            decision = deepcopy(state.get('groupReviews', {}).get(label))
            if decision:
                decision['stale'] = decision['inputSha256'] != fingerprint
            rows = []
            for rid in sorted(union):
                item = state['resources'].get(rid, {})
                classification = next((d for d in (item.get('proposal') or {}).get('decisions', []) if d['field']=='forGroups' and d['value']==label), None)
                unresolved = bool(classification and classification['status']=='unconfirmed') or any(
                    x['status']=='needs-review' for x in item.get('results',{}).get('reconcile',{}).get('resolutions',[]))
                rows.append({'id':rid,'name':live[rid].get('name',rid),'current':rid in current_ids,
                    'proposed':rid in proposed_ids,'categories':proposed[rid].get('categories',[]),
                    'researched':bool(item.get('proposal')),'unresolved':unresolved,
                    'groupEvidence':deepcopy(classification),
                    'reviewed':bool(decision and not decision['stale'] and rid in decision['memberDispositions']),
                    'providerCluster':_same_provider(live[rid])})
            clusters = defaultdict(list)
            for rid in sorted(proposed_ids):clusters[_same_provider(live[rid])].append(rid)
            duplicates = defaultdict(list)
            for rid in sorted(proposed_ids):
                r=live[rid]; key=(str(r.get('name','')).strip().casefold(), str(r.get('address','')).strip().casefold())
                if key[0]:duplicates[key].append(rid)
            overlaps = []
            for other in package['data']['forGroups']:
                if other==label:continue
                common=sorted(rid for rid in proposed_ids if other in proposed[rid].get('forGroups',[]))
                if common:overlaps.append({'group':other,'count':len(common),'resourceIds':common})
            attention=[]
            if not definition.get('approvedBy'):attention.append('Definition pending; do not infer new memberships.')
            if not union:attention.append('No recorded members; incomplete research does not prove this group is unnecessary.')
            if len(proposed_ids)==1:attention.append('One resource: assess its practical use, not a membership minimum.')
            if any(not row['researched'] for row in rows):attention.append('Some member records have no completed classification research.')
            if any(row['unresolved'] for row in rows):attention.append('Unresolved evidence remains visible.')
            if overlaps:attention.append('Shared membership may be useful; overlap alone does not justify merging groups.')
            cards.append({'group':label,'definition':definition.get('definition',''),'aliases':definition.get('aliases',[]),
                'definitionApproved':bool(definition.get('approvedBy')),'currentCount':len(current_ids),'proposedCount':len(proposed_ids),
                'members':rows,'categories':[{'id':cid,'label':names.get(cid,cid),'count':n} for cid,n in sorted(Counter(cid for rid in proposed_ids for cid in set(proposed[rid].get('categories',[]))).items())],
                'coverage':{'members':len(rows),'researched':sum(r['researched'] for r in rows),'reviewed':sum(r['reviewed'] for r in rows),
                            'unreviewed':sum(not r['reviewed'] for r in rows),'unresolved':sum(r['unresolved'] for r in rows)},
                'providerClusters':[{'key':key,'resourceIds':ids,'count':len(ids)} for key,ids in sorted(clusters.items())],
                'providerIdentityNote':'Website/phone clusters are possible shared providers, not verified independent-provider counts. Distinct programs stay separate.',
                'possibleDuplicates':[ids for ids in duplicates.values() if len(ids)>1], 'overlaps':overlaps,'attention':attention,'review':decision})
        population=[{'id':cat['id'],'label':cat['label'],'affectedCount':len(self._affected(package,proposed,[cat['id']]))}
                    for cat in package['data']['categories'] if terms.get(('categories','',cat['id']),{}).get('populationCategory')]
        return {'projectId':state['id'],'revision':state['revision'],'office':state['office'],'historical':state['historical'],
            'packageSha256':package['sha256'],'packageVersion':package['data']['packageVersion'],'inputSha256':fingerprint,
            'officeResourceCount':len(live),'excludedDeletedResources':len(package['resources'])-len(live),
            'researchedResourceCount':sum(bool(state['resources'].get(rid,{}).get('proposal')) for rid in live),
            'coverageNote':'Counts include the entire connected package. Proposed counts overlay only completed research; unresearched records keep their current assignments.',
            'groups':cards,'populationCategories':population,
            'plans':[self._plan_view(c,state,plan) for plan in state.get('taxonomyPlans',[])]}

    def view(self, project_id):
        with self.store.connect() as c:return self._report(c,self.flow._load(c,project_id))

    def select_resources(self, project_id, revision, resource_ids):
        """Extend research coverage without discarding completed assignments."""
        if not isinstance(resource_ids, list) or not resource_ids or any(not isinstance(r, str) for r in resource_ids) or len(set(resource_ids)) != len(resource_ids):
            raise ImprovementError('Select unique resource IDs to research')
        with self.store.connect() as c:
            state = self.flow._checked(c, project_id, revision)
            if state.get('requiresReconnection'):
                raise ImprovementError('Reconnect the current package before extending research')
            package, _ = self._inputs(c, state)
            base = self._package(c, state['baseSha256'])
            for rid in resource_ids:
                if rid not in base['resources']:
                    raise ImprovementError('A resource added after this project began needs a new project from the latest package')
                if rid in state['resources']:
                    raise ImprovementError('Resource is already selected for research')
                if message := resource_blocked(package, rid):
                    raise ImprovementError(message)
            for rid in resource_ids:
                state['resources'][rid] = {'assignments': {}, 'results': {}, 'proposal': None, 'review': None, 'packaged': False}
                state['researchSnapshots'][rid] = evidence_snapshot(package['resources'][rid], package['assetHashes'])
            self.flow._save(c, state, 'classification-coverage-extended', {'resourceIds': resource_ids})
            return self._report(c, state)

    def save_group(self, project_id, revision, label, outcome, practical_use, reason, reviewer, member_dispositions, target='', prominence=''):
        reviewer=nonempty(reviewer,'Reviewer'); practical_use=nonempty(practical_use,'Practical missionary use');reason=nonempty(reason,'Review reason')
        if outcome not in OUTCOMES:raise ImprovementError('Unknown group outcome')
        with self.store.connect() as c:
            state=self.flow._checked(c,project_id,revision);report=self._report(c,state)
            card=next((g for g in report['groups'] if g['group']==label),None)
            if not card:raise ImprovementError('Choose an existing exact office group')
            ids={r['id'] for r in card['members']}
            if not isinstance(member_dispositions,dict) or set(member_dispositions)!=ids:
                raise ImprovementError('Record a disposition for every current or proposed member, including removals')
            for value in member_dispositions.values():nonempty(value,'Member disposition and reason')
            if outcome=='merge' and (target==label or target not in [g['group'] for g in report['groups']]):
                raise ImprovementError('A merge recommendation needs a distinct existing group; missing terms require definition review')
            if outcome!='merge' and target:raise ImprovementError('Only merge recommendations have a target group')
            if outcome=='change-prominence' and prominence not in ('prominent','all-groups'):
                raise ImprovementError('Choose prominent or all-groups')
            if outcome!='change-prominence' and prominence:raise ImprovementError('Only prominence recommendations have a display preference')
            review={'outcome':outcome,'practicalUse':practical_use,'reason':reason,'reviewer':reviewer,'reviewedAt':utcnow(),
                    'inputSha256':report['inputSha256'],'memberDispositions':deepcopy(member_dispositions),'target':target,'prominence':prominence,
                    'recommendationOnly':True,'missingAssignmentsNote':'Unreviewed office resources may contain missing members; this review does not certify complete discovery.'}
            state.setdefault('groupReviews',{})[label]=review
            self.flow._save(c,state,'group-usefulness-reviewed',{'group':label,'review':review})
            return self._report(c,state)

    @staticmethod
    def _affected(package, proposed, ids):
        return sorted(rid for rid,r in package['resources'].items() if any(
            cid in r.get('categories',[]) or cid in r.get('categoryFilters',{}) or
            cid in proposed[rid].get('categories',[]) or cid in proposed[rid].get('categoryFilters',{}) for cid in ids))

    def create_plan(self, project_id, revision, category_ids, reason):
        reason=nonempty(reason,'Migration purpose')
        if not isinstance(category_ids,list) or not category_ids or any(not isinstance(v,str) for v in category_ids) or len(set(category_ids))!=len(category_ids):
            raise ImprovementError('Select unique population categories for one complete change set')
        with self.store.connect() as c:
            state=self.flow._checked(c,project_id,revision);package,fingerprint=self._inputs(c,state)
            validate_guidance(state['classificationGuidance'],package['data'],state['office'])
            terms={t['value']:t for t in state['classificationGuidance']['terms'] if t['field']=='categories'}
            for cid in category_ids:
                if not terms.get(cid,{}).get('populationCategory') or not terms[cid]['approvedBy']:
                    raise ImprovementError('Retirement requires an approved population-category definition')
            # Retire incoming legacy aliases in the same explicitly approved plan.
            # Leaving one pointed at a retired category would resurrect it on merge.
            retired = set(category_ids)
            while True:
                incoming = {m['fromId'] for m in package['data'].get('categoryMigrations', [])
                            if isinstance(m, dict) and m.get('fromId') and m.get('toId') in retired}
                if incoming <= retired: break
                retired.update(incoming)
            legacy_ids = sorted(retired - set(category_ids))
            plans=state.setdefault('taxonomyPlans',[])
            plan={'id':max([x['id'] for x in plans],default=0)+1,'categoryIds':list(category_ids),'reason':reason,
                  'inputSha256':fingerprint,'packageSha256':package['sha256'],'createdAt':utcnow(),
                  'legacyCategoryIds':legacy_ids,'retiredCategoryIds':list(category_ids)+legacy_ids,
                  'affectedIds':self._affected(package,self._records(package,state),retired),'mappings':{},'approval':None,'saved':None}
            plans.append(plan);self.flow._save(c,state,'taxonomy-plan-created',deepcopy(plan));return self._report(c,state)

    @staticmethod
    def _plan(state, plan_id):
        plan=next((p for p in state.get('taxonomyPlans',[]) if p['id']==plan_id),None)
        if not plan:raise ImprovementError('Migration plan not found')
        return plan

    def _mapping(self,c,state,plan,rid,choices,note,finding_notes,type_dispositions):
        package,fingerprint=self._inputs(c,state)
        if plan['inputSha256']!=fingerprint:raise ImprovementError('Migration inputs changed; create and review a new plan')
        if not state['latestSha256'] or state.get('requiresReconnection'):raise ImprovementError('Reconnect the current package before reviewing migration mappings')
        if rid not in plan['affectedIds']:raise ImprovementError('Resource is outside this complete migration')
        if message:=resource_blocked(package,rid):raise ImprovementError(message)
        item=state['resources'].get(rid)
        if not item or item['packaged'] or not item['proposal']:raise ImprovementError('Complete classification research for this resource first')
        if any(stage not in item['results'] for stage,_ in self.flow._stages(state)):
            raise ImprovementError('Every required real research stage must be complete')
        base=self._package(c,state['baseSha256']);current=package['resources'][rid]
        selected=self.flow.materialize(base['resources'][rid],current,item['proposal'],choices)
        self.flow._ready(state,rid,base,package,selected)
        nonempty(note,'Mapping rationale, including group choice or reason no group applies')
        if not isinstance(finding_notes,dict):raise ImprovementError('Finding resolutions must be an object')
        findings=self.flow._findings(item)
        for resolution in item['results']['reconcile']['resolutions']:
            fid=resolution['findingId']
            if resolution['status']=='needs-review' and findings[fid]['severity']=='material':nonempty(finding_notes.get(fid),f'Human resolution for {fid}')
        retired=set(plan['retiredCategoryIds'])
        old_types={term_key(('categoryFilters',cid,t)) for record in (current,selected) for cid,types in record.get('categoryFilters',{}).items() if cid in retired for t in types}
        if not isinstance(type_dispositions,dict) or set(type_dispositions)!=old_types:
            raise ImprovementError('Explain the replacement or deliberate removal of every Type owned by a retiring category')
        for value in type_dispositions.values():nonempty(value,'Retiring Type disposition')
        selected['categories']=[cid for cid in selected.get('categories',[]) if cid not in retired]
        selected['categoryFilters']={cid:ts for cid,ts in selected.get('categoryFilters',{}).items() if cid not in retired}
        definitions={(t['field'],t['categoryId'],t['value']):t for t in state['classificationGuidance']['terms']}
        decisions={(d['field'],d['categoryId'],d['value']):d for d in item['proposal']['decisions']}
        if not any(not definitions.get(('categories','',cid),{}).get('populationCategory') for cid in selected['categories']):
            raise ImprovementError('Every migrated resource needs at least one actual service category')
        for key in memberships(selected):
            d=decisions.get(key)
            if not d or d['status']!='supported' or not definitions.get(key,{}).get('approvedBy'):
                raise ImprovementError('Every remaining membership needs approved definitions and supported research; resolve unconfirmed mappings first')
        return {f:deepcopy(selected[f]) for f in FIELDS}

    def review_mapping(self, project_id, revision, plan_id, rid, choices, reviewer, note, finding_notes, type_dispositions):
        reviewer=nonempty(reviewer,'Reviewer')
        with self.store.connect() as c:
            state=self.flow._checked(c,project_id,revision);plan=self._plan(state,plan_id)
            if plan['saved']:raise ImprovementError('This migration has already been saved')
            fields=self._mapping(c,state,plan,rid,choices,note,finding_notes,type_dispositions)
            plan['mappings'][rid]={'fields':fields,'choices':deepcopy(choices),'reviewer':reviewer,'reviewedAt':utcnow(),
                'note':note,'findingNotes':deepcopy(finding_notes),'typeDispositions':deepcopy(type_dispositions)}
            plan['approval']=None
            self.flow._save(c,state,'taxonomy-mapping-reviewed',{'planId':plan_id,'resourceId':rid,'mapping':deepcopy(plan['mappings'][rid])})
            return self._report(c,state)

    def _plan_view(self,c,state,plan):
        package,fingerprint=self._inputs(c,state);view=deepcopy(plan);blockers=[]
        proposed_records=self._records(package,state)
        compatibility=[]
        if plan['legacyCategoryIds']:
            compatibility.append('Location reader update required: an older package can restore a redirect to a retired category. Migration export remains blocked until that merge behavior is fixed and verified.')
            blockers.extend(compatibility)
        view['stale']=plan['inputSha256']!=fingerprint
        if view['stale']:blockers.append('Source package, definitions, or classification evidence/review changed. Create a new plan.')
        if not state['latestSha256'] or state.get('requiresReconnection'):blockers.append('Reconnect the current office package.')
        current_ids=self._affected(package,proposed_records,plan['retiredCategoryIds'])
        if current_ids!=plan['affectedIds']:blockers.append('Affected resources changed; this plan no longer covers the whole package.')
        rows=[]
        for rid in plan['affectedIds']:
            current=package['resources'].get(rid,{});item=state['resources'].get(rid,{})
            mapping=plan['mappings'].get(rid);problem=''
            if not mapping:problem='Mapping not reviewed.'
            elif not view['stale']:
                try:
                    fields=self._mapping(c,state,plan,rid,mapping['choices'],mapping['note'],mapping['findingNotes'],mapping['typeDispositions'])
                    if fields!=mapping['fields']:problem='Mapping changed.'
                except ImprovementError as error:problem=str(error)
            if problem:blockers.append(rid+': '+problem)
            proposed=proposed_records.get(rid,current)
            proposal=item.get('proposal') or {}
            comparison=self.flow.compare_fields(self._package(c,state['baseSha256'])['resources'].get(rid,current),current,proposal) if proposal else {}
            expected={term_key(('categoryFilters',cid,t)):'' for record in (current,proposed) for cid,ts in record.get('categoryFilters',{}).items() if cid in plan['retiredCategoryIds'] for t in ts}
            rows.append({'id':rid,'name':current.get('name',rid),'original':{f:deepcopy(current.get(f,{} if f=='categoryFilters' else [])) for f in FIELDS},
                'proposed':{f:deepcopy(proposed.get(f,{} if f=='categoryFilters' else [])) for f in FIELDS},
                'researchComplete':bool(item.get('proposal')),'researchSelected':rid in state['resources'],'mapping':mapping,'blocked':problem,
                'membershipDecisions':deepcopy(proposal.get('decisions',[])),
                'conflictingFields':[field for field,details in comparison.items() if details['conflict']],
                'requiredTypeDispositions':expected,'unresolvedFindings':{fid:f for fid,f in self.flow._findings({'results':item.get('results',{})}).items() if fid in {x['findingId'] for x in item.get('results',{}).get('reconcile',{}).get('resolutions',[]) if x['status']=='needs-review'}}})
        view.update(rows=rows,blockers=blockers,compatibilityBlockers=compatibility,ready=not blockers and not plan['saved'],reviewedCount=len(plan['mappings']))
        return view

    def approve_plan(self,project_id,revision,plan_id,reviewer,note):
        reviewer=nonempty(reviewer,'Reviewer');note=nonempty(note,'Whole migration review note')
        with self.store.connect() as c:
            state=self.flow._checked(c,project_id,revision);plan=self._plan(state,plan_id);view=self._plan_view(c,state,plan)
            if not view['ready']:raise ImprovementError('Complete migration is blocked: '+'; '.join(view['blockers'] or ['already saved']))
            plan['approval']={'reviewer':reviewer,'note':note,'reviewedAt':utcnow(),'inputSha256':plan['inputSha256'],'mappingSha256':digest(plan['mappings'])}
            self.flow._save(c,state,'taxonomy-plan-approved',{'planId':plan_id,'approval':deepcopy(plan['approval'])});return self._report(c,state)

    def prepare_export(self,project_id,revision,plan_id):
        with self.store.connect() as c:
            state=self.flow._checked(c,project_id,revision);plan=self._plan(state,plan_id);view=self._plan_view(c,state,plan)
            approval=plan['approval']
            if not view['ready'] or not approval or approval['mappingSha256']!=digest(plan['mappings']) or approval['inputSha256']!=view['inputSha256']:
                raise ImprovementError('Review and approve the complete current migration before export')
            package,_=self._inputs(c,state);exported=deepcopy(package['data']);retired=set(plan['retiredCategoryIds'])
            export_key=digest({'projectId':project_id,'plan':plan})
            old=c.execute('SELECT id,manifest_json FROM scout_taxonomy_exports WHERE export_key=?',(export_key,)).fetchone()
            if old:return {'exportId':old['id'],'manifest':json.loads(old['manifest_json'])}
            records=[*exported['resources'],*exported['categories'],exported]
            for d in exported.get('deletions',[]):records.append({'lastModified':d.get('deletedAt')})
            stamp=next_timestamp(records)
            for r in exported['resources']:
                if r['id'] in plan['mappings']:
                    r.update(deepcopy(plan['mappings'][r['id']]['fields']));r['lastModified']=stamp
                    exported.setdefault('changes', []).append({'id':f"scout-taxonomy:{project_id}:{plan_id}:resource:{r['id']}:{export_key[:16]}",
                        'type':'resource','action':'updated','targetId':r['id'],'targetName':r.get('name',r['id']),
                        'description':'Reviewed category migration: '+plan['mappings'][r['id']]['note'],'timestamp':stamp})
            category_labels={cat['id']:cat['label'] for cat in exported['categories']}
            exported['categories']=[cat for cat in exported['categories'] if cat['id'] not in retired]
            exported['categoryMigrations']=[m for m in exported.get('categoryMigrations',[]) if m.get('fromId') not in retired]+[{'fromId':cid} for cid in plan['retiredCategoryIds']]
            for cid in plan['retiredCategoryIds']:
                exported.setdefault('deletions',[]).append({'key':'category:'+cid,'kind':'category','targetId':cid,'label':category_labels.get(cid,cid),'deletedAt':stamp,'description':plan['reason']})
                exported.setdefault('changes',[]).append({'id':f'scout-taxonomy:{project_id}:{plan_id}:{cid}:{export_key[:16]}','type':'category','action':'deleted','targetId':cid,'targetName':category_labels.get(cid,cid),'description':plan['reason'],'timestamp':stamp})
            exported['deletionRequests']=[d for d in exported.get('deletionRequests',[]) if not(d.get('kind')=='category' and d.get('targetId') in retired)]
            for r in exported['resources']:
                if any(cid in retired for cid in r.get('categories',[])) or any(cid in retired for cid in r.get('categoryFilters',{})):
                    raise ImprovementError('Migration would leave a reference to a retired category')
            prior_versions=[json.loads(row[0])['packageVersion'] for row in c.execute('SELECT manifest_json FROM scout_taxonomy_exports WHERE project_id=?',(project_id,))]
            prior_versions += [json.loads(row[0])['packageVersion'] for row in c.execute('SELECT manifest_json FROM scout_improvement_exports WHERE project_id=?',(project_id,))]
            exported.update(packageVersion=max([exported['packageVersion'],*prior_versions])+1,packageCreatedAt=stamp,lastModified=stamp)
            payload=write_package(exported,package['assets']);out=read_package(payload)
            manifest={'projectId':project_id,'planId':plan_id,'exportKey':export_key,'inputSha256':plan['inputSha256'],
                'planSha256':digest(plan),'packageSha256':out['sha256'],'packageVersion':exported['packageVersion'],
                'latestSha256':package['sha256'],'historicalDevelopmentOnly':state['historical'],'categoryIds':plan['categoryIds'],'retiredCategoryIds':plan['retiredCategoryIds'],
                'affectedResourceIds':plan['affectedIds'],'assetHashes':out['assetHashes'],'approval':deepcopy(approval)}
            cursor=c.execute('INSERT INTO scout_taxonomy_exports(project_id,export_key,manifest_json,payload) VALUES(?,?,?,?)',(project_id,export_key,json.dumps(manifest,ensure_ascii=False),payload))
            self.flow._save(c,state,'taxonomy-export-prepared',{'exportId':cursor.lastrowid,'manifest':manifest})
            return {'exportId':cursor.lastrowid,'manifest':manifest,'revision':state['revision']}

    def export_bytes(self,project_id,export_id):
        with self.store.connect() as c:
            self.flow._load(c,project_id)
            row=c.execute('SELECT payload FROM scout_taxonomy_exports WHERE id=? AND project_id=?',(export_id,project_id)).fetchone()
            if not row:raise ImprovementError('Migration export not found')
            return bytes(row['payload'])

    def acknowledge(self,project_id,revision,export_id,sha):
        with self.store.connect() as c:
            state=self.flow._checked(c,project_id,revision)
            row=c.execute('SELECT manifest_json,acknowledged_at FROM scout_taxonomy_exports WHERE id=? AND project_id=?',(export_id,project_id)).fetchone()
            if not row:raise ImprovementError('Migration export not found')
            manifest=json.loads(row['manifest_json']);plan=self._plan(state,manifest['planId'])
            if sha!=manifest['packageSha256']:raise ImprovementError('Saved bytes do not match this migration export')
            if row['acknowledged_at']:return self._report(c,state)
            _,fingerprint=self._inputs(c,state)
            if fingerprint!=manifest['inputSha256'] or digest(plan)!=manifest['planSha256']:raise ImprovementError('Migration changed after export; retain the new review and discard the stale export')
            c.execute('UPDATE scout_taxonomy_exports SET acknowledged_at=? WHERE id=?',(utcnow(),export_id))
            plan['saved']={'exportId':export_id,'packageSha256':sha,'savedAt':utcnow()}
            for rid in plan['affectedIds']:
                if rid in state['resources']:state['resources'][rid]['packaged']=True
            state['requiresReconnection']=True
            self.flow._save(c,state,'taxonomy-export-saved',{'exportId':export_id,'planId':plan['id']})
            return self._report(c,state)
