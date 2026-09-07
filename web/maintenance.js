'use strict';
const $ = id => document.getElementById(id);
const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fieldLabel = key => ({informationText:'Information',informationSections:'Information',categoryFilters:'Types',forGroups:'Groups',categories:'Categories'}[key] || key.charAt(0).toUpperCase()+key.slice(1));
const show = (value, key='') => {
  if(Array.isArray(value))return value.map(v=>key==='categories'?(state?.catalog.categories.find(c=>c.id===v)?.label || v):v).join(', ') || '(none)';
  if(value && typeof value==='object')return Object.entries(value).map(([k,v])=>fieldLabel(k)+': '+show(v)).join('\n');
  return String(value ?? '(not recorded)');
};
let state, source, assignment, pendingExport;
async function api(path, body, raw=false){
  const response = await fetch('/api/maintenance'+path, body === undefined ? {} : {method:'POST', headers:raw ? {} : {'Content-Type':'application/json'}, body:raw ? body : JSON.stringify(body)});
  const value = await response.json();
  if(!response.ok) throw new Error(value.error || JSON.stringify(value));
  return value;
}
function action(fn){return async () => {try{$('message').textContent='';await fn();}catch(e){$('message').textContent=e.message;}};}
async function projects(){const v=await api('');$('projects').innerHTML='<option value="">Choose a maintenance run</option>'+v.projects.map(p=>`<option value="${p.id}">${esc(p.office)} · Run ${p.id}</option>`).join('');if(state)$('projects').value=state.id;}
async function load(id){state=await api('/'+id);render();}
function render(){
  $('run').hidden=false;$('run-title').textContent=state.office+' · '+state.runName;
  const c=state.coverage;
  $('coverage').textContent=`Known resources: ${c.recheck.completed} completed, ${c.recheck.selected} selected, ${c.officeResources} in office. Searches: ${c.discovery.completed} completed, ${c.discovery.selected} selected, ${c.officeCategories} office categories. Unselected or unfinished work has not been checked.`;
  $('historical-banner').textContent=(state.historical?'Historical development sample. ':'')+(!state.latestSha256 || state.requiresReconnection?'Reconnect the current package before accepting or saving changes.':'Current package connected.');
  let evidence=document.getElementById('intake-evidence');if(!evidence){evidence=document.createElement('p');evidence.id='intake-evidence';$('historical-banner').after(evidence);}evidence.textContent=intakeEvidenceMessage(state.intakeEvidence);
  $('task-choice').innerHTML='<option value="">Next available task</option>'+state.tasks.map(t=>`<option value="${esc(t.id)}">${esc(t.id)}</option>`).join('');
  $('tasks').innerHTML=Object.entries(state.stoppedBlindResearch || {}).map(([name,change])=>`<p><strong>${esc(name)}: further blind research stopped.</strong> ${esc(change.reason)} (${esc(change.operator)} · ${esc(change.stoppedAt)}) Existing results remain available.</p>`).join('')+state.tasks.map(t=>`<p><strong>${esc(t.id)}</strong>: ${t.research.map(s=>esc(s.researcher+' '+s.stage)+(s.complete?' ✓':s.required===false?' — stopped, not completed':' pending')).join(' · ')}</p>`).join('');
  $('items').innerHTML=state.items.length?'':'<p>No reconciled findings yet. Research progress is shown above.</p>';
  state.items.forEach((r,index)=>{
    const card=document.createElement('section');card.dataset.itemId=r.id;
    card.innerHTML=`<h3>${esc(r.current?.name || r.program)} · ${esc(r.status)}</h3><p>${esc(r.summary)}</p><p>${r.saved?'Saved in package':esc(r.review?.decision || 'Not reviewed')}${r.blocked?' · '+esc(r.blocked):''}</p><p>Last attempt: ${esc(r.lastAttemptedOn || 'Unknown')} · Last evidence supporting operation: ${esc(r.lastEvidenceOfOperationOn || 'Unknown')} · Last human verification: ${esc(r.current?.verifiedOn || 'Not recorded')} · Suggested next check: ${esc(r.nextCheckOn || 'Not proposed')}</p>
    <ul>${r.questions.map(q=>`<li>${esc(q)}</li>`).join('')}</ul><details><summary>Evidence and independent findings</summary>${r.sources.map(s=>`<p><a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.url)}</a> · ${esc(s.accessedOn)}<br>${esc(s.excerpt)}</p>`).join('')}<pre style="white-space:pre-wrap">${esc(JSON.stringify({findings:r.findings,resolutions:r.resolutions},null,2))}</pre></details>
    ${r.current?`<details><summary>Current office details and local notes</summary>${Object.entries(r.current).filter(([key])=>!['id','pdfs'].includes(key)).map(([key,value])=>`<h4>${esc(fieldLabel(key))}</h4><p style="white-space:pre-wrap">${esc(show(value,key))}</p>`).join('')}</details>`:''}
    <details><summary>Independent research evidence</summary>${[...Object.entries(r.audits),...Object.entries(r.blindResults || {}).map(([name,result])=>[name+' — independent blind research',result])].map(([name,a])=>`<h4>${esc(name)}</h4><p>${esc(a.researchNotes)}</p>${a.evidenceSources.map(source=>`<p><a href="${esc(source.url)}" target="_blank" rel="noopener">${esc(source.url)}</a> · ${esc(source.accessedOn)}<br>${esc(source.excerpt)}</p>`).join('')}`).join('')}</details>
    ${r.matches.length?`<h4>Identity matches to review</h4><ul>${r.matches.map(m=>`<li>${esc(m.name)} · ${esc(m.identityStatus)} · ${esc(m.matchReasons.join(', '))}</li>`).join('')}</ul>`:''}
    <div class="fields"></div><label>Review rationale, classification consequences, and any identity distinction<textarea class="note" rows="3">${esc(r.review?.note || '')}</textarea></label>
    <div class="finding-notes"></div><label>Identity decision <select class="identity"><option value="">No identity distinction selected</option><option value="distinct-program">This is a distinct program; reason recorded above</option></select></label>
    <label>Decision <select class="decision"><option value="keep">Keep as an observation / follow-up</option><option value="accept">Accept selected update or addition</option><option value="retire">Request office retirement review</option><option value="decline">Decline this proposal</option><option value="unmarked">Clear review mark</option></select></label><button class="save">Save review</button>`;
    const fields=card.querySelector('.fields');
    if(r.current){for(const [key,values] of Object.entries(r.comparison)){
      const diff=highlightComparison(esc(show(values.current,key)),esc(show(values.proposed,key)));
      const field=document.createElement('div');field.innerHTML=`<h4>${esc(fieldLabel(key))}${values.conflict?' · Later office edit — choose carefully':''}</h4><p>Changes are bold; removed text is crossed out.</p><p>Current: ${diff.before}</p><p>Proposed: ${diff.after}</p><label>Use <select data-field="${esc(key)}"><option value="current">Current office value</option><option value="proposed">Proposed value</option></select></label>`;fields.append(field);
    }}else{fields.innerHTML=`<h4>Proposed addition</h4>`+Object.entries(r.fields).map(([key,value])=>`<h4>${esc(fieldLabel(key))}</h4><p style="white-space:pre-wrap">${esc(show(value,key))}</p>`).join('');}
    for(const resolution of r.resolutions){if(resolution.status==='needs-review' && r.findings[resolution.findingId].severity==='material'){
      const label=document.createElement('label');label.textContent='Human resolution: '+r.findings[resolution.findingId].summary;
      const input=document.createElement('textarea');input.dataset.finding=resolution.findingId;label.append(input);card.querySelector('.finding-notes').append(label);
    }}
    card.querySelector('.decision').value=r.review?.decision || 'keep';
    card.querySelector('.identity').value=r.review?.identityDecision || '';
    card.querySelectorAll('[data-field]').forEach(e=>e.value=r.review?.choices?.[e.dataset.field] || 'current');
    card.querySelectorAll('[data-finding]').forEach(e=>e.value=r.review?.findingNotes?.[e.dataset.finding] || '');
    card.querySelector('.save').disabled=r.saved;
    card.querySelector('.save').onclick=action(async()=>{
      const choices=Object.fromEntries([...card.querySelectorAll('[data-field]')].map(e=>[e.dataset.field,e.value]));
      const findingNotes=Object.fromEntries([...card.querySelectorAll('[data-finding]')].map(e=>[e.dataset.finding,e.value]));
      state=await api(`/${state.id}/review`,{revision:state.revision,taskId:r.taskId,itemId:r.id,decision:card.querySelector('.decision').value,choices,reviewer:$('reviewer').value,note:card.querySelector('.note').value,identityDecision:card.querySelector('.identity').value,findingNotes});render();
    });
    $('items').append(card);
  });
}
$('source').onchange=action(async()=>{source=$('source').files[0];if(!source)return;const v=await api('/inspect',source,true);$('office').value=v.office;$('package-info').textContent=`Package ${v.packageVersion}: ${v.resources.length} resources.`;for(const [id,items] of [['resources-scope',v.resources],['categories-scope',v.categories]]){$(id).innerHTML=items.map(i=>`<label><input type="checkbox" value="${esc(i.id)}">${esc(i.name || i.label)}${i.name?' · Last human verification: '+esc(i.verifiedOn || 'not recorded'):''}</label>`).join('');}$('prepare').disabled=false;});
$('all-resources').onclick=()=>document.querySelectorAll('#resources-scope input').forEach(e=>e.checked=true);
$('all-categories').onclick=()=>document.querySelectorAll('#categories-scope input').forEach(e=>e.checked=true);
$('prepare').onclick=action(async()=>{const q=new URLSearchParams({office:$('office').value,runName:$('run-name').value,historical:$('historical').checked?'1':'0'});for(const [selector,key] of [['#resources-scope input:checked','resourceId'],['#categories-scope input:checked','categoryId']])document.querySelectorAll(selector).forEach(e=>q.append(key,e.value));state=await api('/prepare?'+q,source,true);await projects();render();});
$('projects').onchange=action(async()=>{if($('projects').value)await load($('projects').value);});
$('refresh').onclick=action(async()=>{await projects();if(state)await load(state.id);});
$('connect').onclick=action(async()=>{const file=$('latest').files[0];if(!file)throw new Error('Choose the current package ZIP.');state=await api(`/${state.id}/connect?`+new URLSearchParams({office:state.office,revision:state.revision}),file,true);render();});
$('next').onclick=action(async()=>{const v=await api(`/${state.id}/next`,{researcher:$('researcher').value || null,taskId:$('task-choice').value || null});assignment=v.assignment;$('assignment').textContent=assignment?JSON.stringify(assignment,null,2):'No assignment available for this selection.';if(assignment)$('stage').value=assignment.stage;await load(state.id);});
$('submit').onclick=action(async()=>{state=await api(`/${state.id}/submit`,{stage:$('stage').value,result:JSON.parse($('result').value)});render();});
$('export').onclick=action(async()=>{
  const handle=window.showSaveFilePicker ? await showSaveFilePicker({suggestedName:`scout-maintenance-${state.id}.zip`,types:[{description:'Resource package ZIP',accept:{'application/zip':['.zip']}}]}) : null;
  const exported=await api(`/${state.id}/export`,{revision:state.revision});
  const response=await fetch(`/api/maintenance/${state.id}/exports/${exported.exportId}`);if(!response.ok)throw new Error('Could not load the prepared package.');
  const bytes=await response.arrayBuffer();
  if(!handle){
    const url=URL.createObjectURL(new Blob([bytes],{type:'application/zip'}));
    const link=document.createElement('a');link.href=url;link.download=`scout-maintenance-${state.id}.zip`;document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),60000);
    pendingExport={...exported,projectId:state.id};$('pending-save').hidden=false;await load(state.id);return;
  }
  const writer=await handle.createWritable();try{await writer.write(bytes);await writer.close();}catch(e){await writer.abort().catch(()=>{});throw e;}
  const saved=await (await handle.getFile()).arrayBuffer();const hash=[...new Uint8Array(await crypto.subtle.digest('SHA-256',saved))].map(n=>n.toString(16).padStart(2,'0')).join('');
  if(hash!==exported.manifest.packageSha256)throw new Error('Saved bytes did not match; review remains available.');
  await load(state.id);state=await api(`/${state.id}/saved`,{revision:state.revision,exportId:exported.exportId,packageSha256:hash});render();$('message').textContent='Reviewed changes saved. Reconnect the current office package before exporting more.';
});
projects().catch(e=>$('message').textContent=e.message);

$('confirm-saved').onclick=action(async()=>{
  if(!pendingExport || pendingExport.projectId!==state.id)throw new Error('Open the run that created this download before confirming it.');
  await load(state.id);state=await api(`/${state.id}/saved`,{revision:state.revision,exportId:pendingExport.exportId,packageSha256:pendingExport.manifest.packageSha256});pendingExport=null;$('pending-save').hidden=true;render();$('message').textContent='Saved export confirmed.';
});
$('cancel-saved').onclick=()=>{pendingExport=null;$('pending-save').hidden=true;$('message').textContent='Review remains available. No export was marked saved.';};
