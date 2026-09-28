'use strict';
const $ = id => document.getElementById(id);
let project = null, sourceFile = null, assignment = null, pendingExport = null;
const dirtyWriting=new Set(),dirtyReview=new Set(),invalidating=new Set();
const text = (value) => escapeHTML(String(value ?? ''));
async function api(path, body, raw=false) {
  const response = await fetch(path, body === undefined ? {} : {method:'POST', headers:{'Content-Type':raw?'application/zip':'application/json'}, body:raw?body:JSON.stringify(body)});
  const value = await response.json();
  if(!response.ok) throw new Error(value.error || 'Request failed');
  return value;
}
function message(value, error=false){$('message').textContent=value; $('message').className=error?'error':'';}
function action(callback){return async event=>{try{await callback(event);}catch(error){if(error.name!=='AbortError')message(error.message,true);}};}
function requireSavedDrafts(){if(dirtyWriting.size||dirtyReview.size||invalidating.size)throw new Error('Save classification edits and finish or clear the changed review before continuing.');}
function url(action){return `/api/classifications/${project.id}/${action}`;}
async function loadProjects(){
  const result=await api('/api/classifications');
  $('projects').innerHTML='<option value="">Choose a project</option>'+result.projects.map(p=>`<option value="${p.id}">${text(p.office)} · ${p.id}</option>`).join('');
}
async function loadProject(id){requireSavedDrafts();project=await api(`/api/classifications/${id}`);history.replaceState(null,'',`/classifications?project=${id}`);$('projects').value=id;render();}
function classValue(field, value){
  const names=new Map(project.guidance.terms.filter(t=>t.field==='categories').map(t=>[t.value,t.label]));
  if(field==='categoryFilters')return Object.entries(value||{}).map(([id,types])=>`${text(names.get(id)||id)}: ${types.map(text).join(', ')}`).join('<br>')||'None';
  return (value||[]).map(v=>text(field==='categories'?(names.get(v)||v):v)).join(', ')||'None';
}
function render(){
  if(!project)return;
  $('project').hidden=false;
  $('project-title').textContent=`${project.office} · classification project ${project.id}`;
  $('project-summary').textContent=`Package ${project.baseVersion} · ${project.resources.length} selected resources · definitions v${project.guidance.version}`;
  $('historical-banner').hidden=!project.historical;
  let evidence=document.getElementById('intake-evidence');if(!evidence){evidence=document.createElement('p');evidence.id='intake-evidence';$('project-summary').after(evidence);}evidence.textContent=intakeEvidenceMessage(project.intakeEvidence);
  $('export').disabled=project.requiresReconnection||!project.resources.some(r=>!r.packaged&&r.review?.decision==='curated')||dirtyWriting.size>0||dirtyReview.size>0;
  const draft=project.guidance.catalogSha256===project.currentCatalogDraft.catalogSha256?project.guidance:project.currentCatalogDraft;
  $('definition-rows').innerHTML=draft.terms.map((t,i)=>`<div data-term="${i}"><h3>${text(t.label)} <small>${text(t.field==='categoryFilters'?'Type in '+t.categoryId:t.field==='forGroups'?'Group':'Category')}</small></h3><label>Definition<textarea data-definition>${text(t.definition)}</textarea></label><label>Aliases (one per line)<textarea data-aliases>${text(t.aliases.join('\n'))}</textarea></label>${t.field==='categories'?`<label><input type="checkbox" data-population ${t.populationCategory?'checked':''}> Population category: requires a complete migration before removal</label>`:''}<label><input type="checkbox" data-approve ${t.approvedBy?'checked':''}> Approve this definition</label><p>${t.approvedBy?'Reviewed by '+text(t.approvedBy):'Pending definition review'}</p></div>`).join('');
  $('resources').innerHTML=project.resources.filter(r=>!r.packaged).map(row=>{
    let html=`<article class="resource" data-id="${text(row.id)}"><h2>${text(row.original.name)}</h2><p>${row.research.filter(r=>r.completed).length} of ${row.research.length} research steps complete${row.previousResearchRuns?' · Earlier research retained; changed inputs require a recheck':''}</p><details><summary>Resource information and attachments</summary><p>${text((row.current||row.original).description)}</p><div class="information-rendered">${renderInformationHTML((row.current||row.original).informationText||'')}</div>`;
    for(const which of (project.latestSha256?['original','current']:['original']))for(const pdf of row[which]?.pdfs||[])html+=`<p><a target="_blank" rel="noopener" href="${url('attachment')+'?'+new URLSearchParams({which:which==='original'?'base':'latest',path:pdf.path})}">${text(which)}: ${text(pdf.name||pdf.path)}</a></p>`;
    html+='</details>';
    for(const linked of row.linkedEvidence||[]){
      const accepted=linked.content?.acceptedWritingProposal;
      html+=`<details><summary>${text(linked.label)}</summary>${accepted?'<p>'+text(accepted.description)+'</p><div class="information-rendered">'+renderInformationHTML(accepted.informationText||'')+'</div>':'<pre>'+text(JSON.stringify(linked.content,null,2))+'</pre>'}<p>${text((linked.content?.limitations||[]).join(' '))}</p></details>`;
    }
    if(row.blocked)html+=`<p class="blocked">${text(row.blocked)}</p>`;
    if(!row.proposal)return html+'</article>';
    for(const [field,label] of [['categories','Categories'],['categoryFilters','Types'],['forGroups','Groups']]){
      const f=row.fields[field];if(!f)continue;
      const choice=row.review?.choices?.[field]||(f.changed&&!f.conflict?'proposed':'current');
      const diff=highlightComparison(classValue(field,f.current),classValue(field,f.proposed));
      html+=`<h3>${label}</h3>${f.conflict?'<p class="conflict">A later office edit conflicts with an explicit Scout decision. Explain which to keep.</p>':''}<p>Changes are bold; removed text is crossed out in the current version.</p><div class="comparison"><div><strong>Current</strong><p>${diff.before}</p></div><div><strong>Proposed, including independent office edits</strong><p>${diff.after}</p></div></div>${['current','proposed'].map(c=>`<label><input type="radio" name="${text(row.id+'-'+field)}" data-field="${field}" value="${c}" ${choice===c?'checked':''}> Use ${c.toLowerCase()} ${label.toLowerCase()}</label>`).join('')}`;
    }
    html+='<h3>Reasons for these classifications</h3>';
    for(const d of row.proposal.decisions){const term=project.guidance.terms.find(t=>t.field===d.field&&t.categoryId===d.categoryId&&t.value===d.value);html+=`<p><strong>${text(term?.label||d.value)} — ${text(d.status)}</strong>${d.relation?' · '+text(d.relation):''}<br>${text(d.reason)}${d.program?'<br>Program: '+text(d.program):''}${d.excerpt?'<blockquote>'+text(d.excerpt)+'</blockquote>':''}${/^https?:\/\//.test(d.source)?'<a target="_blank" rel="noopener" href="'+text(d.source)+'">Source</a>':text(d.source||'')}</p>`;}
    for(const field of ['taxonomyProposals','migrationProposals'])if(row.proposal[field].length)html+=`<details><summary>${field==='taxonomyProposals'?'Suggested new terms':'Separate migration proposals'} — not applied</summary><pre>${text(JSON.stringify(row.proposal[field],null,2))}</pre></details>`;
    html+=`<details><summary>Original classifications and research evidence</summary><pre>${text(JSON.stringify({original:Object.fromEntries(['categories','categoryFilters','forGroups'].map(f=>[f,row.original[f]])),research:row.evidence},null,2))}</pre></details>`;
    const edit=row.editableProposal;
    html+=`<details><summary>Edit proposed classifications and reasons</summary><p>Changes require matching evidence and another review.</p><textarea data-edit="proposal" rows="12">${text(JSON.stringify(edit,null,2))}</textarea><button data-action="edit">Save classification edits</button></details>`;
    for(const r of row.evidence.reconcile.resolutions)if(r.status==='needs-review'&&row.findings[r.findingId].severity==='material')html+=`<label class="conflict">Resolve: ${text(row.findings[r.findingId].summary)}<textarea data-finding="${text(r.findingId)}">${text(row.review?.findingNotes?.[r.findingId]||'')}</textarea></label>`;
    html+=`<label>Review note<textarea data-note>${text(row.review?.note||'')}</textarea></label><p data-review-state>${row.review?.decision==='curated'?'✓ Curated':row.review?.decision==='declined'?'Declined':'Unmarked'}</p><button data-action="curated" class="primary" ${row.blocked?'disabled':''}>Curated</button><button data-action="declined">Decline changes</button><button data-action="unmarked">Clear mark</button><button data-action="print">Print resource</button></article>`;
    return html;
  }).join('');
}
$('definitions').addEventListener('input',()=>{dirtyReview.add('definitions');$('export').disabled=true;});
$('save-definitions').onclick=action(async()=>{
  if([...dirtyWriting,...dirtyReview].some(id=>id!=='definitions'))throw new Error('Finish resource edits before saving definitions.');
  const source=project.guidance.catalogSha256===project.currentCatalogDraft.catalogSha256?project.guidance:project.currentCatalogDraft;
  const guidance=JSON.parse(JSON.stringify(source));guidance.version=project.guidance.version+1;
  const approvedKeys=[];
  $('definition-rows').querySelectorAll('[data-term]').forEach(row=>{const t=guidance.terms[Number(row.dataset.term)];t.definition=row.querySelector('[data-definition]').value;t.aliases=row.querySelector('[data-aliases]').value.split('\n').map(s=>s.trim()).filter(Boolean);t.populationCategory=!!row.querySelector('[data-population]')?.checked;t.approvedBy=null;if(row.querySelector('[data-approve]').checked)approvedKeys.push(JSON.stringify([t.field,t.categoryId,t.value]));});
  project=await api(url('guidance'),{revision:project.revision,guidance,approvedKeys,reviewer:$('reviewer').value});dirtyReview.delete('definitions');render();message('Definitions saved. Dependent classifications need research under this version.');
});
function choices(card){return Object.fromEntries([...card.querySelectorAll('input[data-field]:checked')].map(e=>[e.dataset.field,e.value]));}
$('resources').addEventListener('input',action(async event=>{
  const card=event.target.closest('.resource');if(!card)return;
  const rid=card.dataset.id,row=project.resources.find(r=>r.id===rid);
  if(event.target.matches('[data-edit],[data-section]'))dirtyWriting.add(rid);else dirtyReview.add(rid);
  $('export').disabled=true;
  card.querySelector('[data-review-state]').textContent='Unmarked — changes need saving or review';
  if(row.review?.decision==='curated'&&!invalidating.has(rid)){
    invalidating.add(rid);
    try{project=await api(url('review'),{revision:project.revision,resourceId:rid,decision:'unmarked',choices:{},reviewer:row.review.reviewer});}
    finally{invalidating.delete(rid);}
  }
}));
window.addEventListener('beforeunload',event=>{if(dirtyWriting.size||dirtyReview.size||invalidating.size){event.preventDefault();event.returnValue='';}});
$('resources').addEventListener('click',action(async event=>{
  const button=event.target.closest('button[data-action]');if(!button)return;
  const card=button.closest('.resource'),rid=card.dataset.id,command=button.dataset.action;
  const row=project.resources.find(r=>r.id===rid);
  if(invalidating.size)throw new Error('Please wait for the Curated mark to clear.');
  if(command!=='edit'&&dirtyWriting.has(rid))throw new Error('Save the classification edits before reviewing or printing them.');
  if([...dirtyWriting,...dirtyReview].some(id=>id!==rid))throw new Error('Finish the other resource edits before continuing.');
  if(command==='print'){
    const selected=choices(card),record={...(row.current||row.original)};

    $('print-content').innerHTML=`<h2>${text(record.name)}</h2><p>${text(record.description)}</p>`+['phone','address','website','hours'].filter(f=>record[f]).map(f=>`<div><strong>${text(f[0].toUpperCase()+f.slice(1))}:</strong> ${text(record[f])}</div>`).join('')+`<hr><div class="information-rendered">${renderInformationHTML(record.informationText)}</div>`;
    window.print();return;
  }
  const body={revision:project.revision,resourceId:rid,reviewer:$('reviewer').value};
  if(command==='edit'){
    body.proposal=JSON.parse(card.querySelector('[data-edit]').value);
    project=await api(url('edit'),body);
  }else{
    Object.assign(body,{decision:command,choices:choices(card),note:card.querySelector('[data-note]').value,
                       findingNotes:Object.fromEntries([...card.querySelectorAll('[data-finding]')].map(e=>[e.dataset.finding,e.value]))});
    project=await api(url('review'),body);
  }
  dirtyWriting.delete(rid);dirtyReview.delete(rid);
  render();message(command==='edit'?'Edits saved. Review the revised classifications before marking it Curated.':'Review saved.');
}));
$('source').onchange=action(async()=>{
  sourceFile=$('source').files[0];if(!sourceFile)return;
  const result=await api('/api/classifications/inspect',sourceFile,true);
  if(result.office)$('office').value=result.office;
  $('source-summary').textContent=`Package ${result.version} · ${result.resources.length} resources. Select a small pilot or the intended work scope.`;
  $('resource-selection').innerHTML=result.resources.map(r=>`<label><input type="checkbox" value="${text(r.id)}"> ${text(r.name)}</label>`).join('');$('prepare').disabled=false;
});
$('prepare').onclick=action(async()=>{
  requireSavedDrafts();
  const query=new URLSearchParams({office:$('office').value,source:sourceFile.name,historical:$('historical').checked?'1':'0'});
  $('resource-selection').querySelectorAll('input:checked').forEach(e=>query.append('resourceId',e.value));
  project=await api('/api/classifications/prepare?'+query,sourceFile,true);await loadProjects();await loadProject(project.id);$('new-project').open=false;
});
$('projects').onchange=action(async()=>{if($('projects').value)await loadProject($('projects').value);});
$('refresh').onclick=action(async()=>{await loadProjects();if(project)await loadProject(project.id);});
$('latest').onchange=action(async()=>{
  requireSavedDrafts();
  const file=$('latest').files[0];if(!file)return;
  const query=new URLSearchParams({office:project.office,revision:project.revision,source:file.name});
  project=await api(url('connect')+'?'+query,file,true);render();message('Current package connected. Review the comparison before marking changes Curated.');
});
$('next-assignment').onclick=action(async()=>{
  requireSavedDrafts();
  assignment=(await api(url('next'),{})).assignment;$('assignment').textContent=JSON.stringify(assignment,null,2);await loadProject(project.id);
});
$('submit-result').onclick=action(async()=>{
  requireSavedDrafts();
  if(!assignment)throw new Error('Get the assigned research step first.');
  project=await api(url('submit'),{stage:assignment.stage,result:JSON.parse($('result').value)});render();message('Research result saved.');
});
async function acknowledge(){
  project=await api(url('saved'),{revision:project.revision,exportId:pendingExport.exportId,packageSha256:pendingExport.manifest.packageSha256});
  pendingExport=null;$('save-confirmation').hidden=true;render();message('Saved package recorded. Those resources are now hidden from this review.');
}
$('export').onclick=action(async()=>{
  requireSavedDrafts();
  // Obtain a destination while this click still has a browser user gesture.
  const handle=window.showSaveFilePicker?await window.showSaveFilePicker({suggestedName:'scout-reviewed-updates.zip',types:[{description:'Resource package',accept:{'application/zip':['.zip']}}]}):null;
  pendingExport=await api(url('export'),{revision:project.revision});await loadProject(project.id);
  const response=await fetch(url('exports')+'/'+pendingExport.exportId);if(!response.ok)throw new Error('Unable to download prepared package');
  const blob=await response.blob();
  if(handle){const writable=await handle.createWritable();try{await writable.write(blob);await writable.close();}catch(error){try{await writable.abort();}catch{}throw error;}await acknowledge();}
  else{const link=document.createElement('a'),objectURL=URL.createObjectURL(blob);link.href=objectURL;link.download='scout-reviewed-updates.zip';link.click();setTimeout(()=>URL.revokeObjectURL(objectURL),30000);$('save-confirmation').hidden=false;}
});
$('confirm-saved').onclick=action(acknowledge);
$('keep-review').onclick=()=>{pendingExport=null;$('save-confirmation').hidden=true;message('Review retained. No resources were hidden.');};
action(async()=>{await loadProjects();const id=new URLSearchParams(location.search).get('project');if(id)await loadProject(id);})();
