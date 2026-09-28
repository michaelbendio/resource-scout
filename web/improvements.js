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
function requireSavedDrafts(){if(dirtyWriting.size||dirtyReview.size||invalidating.size)throw new Error('Save writing edits and finish or clear the changed review before continuing.');}
function url(action){return `/api/improvements/${project.id}/${action}`;}
function evidenceHTML(row){
  let html=`<h3>Original Description</h3><p class="text">${text(row.original.description)}</p><h3>Original Information</h3><div class="information-rendered">${renderInformationHTML(row.original.informationText)}</div>`;
  for(const [stage,result] of Object.entries(row.evidence)){
    const label=stage==='primary'?'Primary research':stage==='reconcile'?'Reconciliation':stage.replace('audit:','Independent check: ');
    html+=`<h3>${text(label)}</h3>`;
    if(result.researchNotes)html+=`<p>${text(result.researchNotes)}</p>`;
    for(const note of [...(result.preservationNotes||[]),...(result.reviewNotes||[])])html+=`<p>${text(note)}</p>`;
    for(const finding of result.findings||[])html+=`<p><strong>${text(finding.severity==='material'?'Important finding':'Writing suggestion')}:</strong> ${text(finding.summary)}</p>`;
    for(const resolution of result.resolutions||[])html+=`<p><strong>${text(resolution.status==='resolved'?'Addressed':'Needs review')}:</strong> ${text(resolution.reason)}</p>`;
    for(const source of result.evidenceSources||[])html+=`<p><a target="_blank" rel="noopener" href="${text(source.url)}">${text(source.url)}</a> · checked ${text(source.accessedOn)}</p><blockquote>${text(source.excerpt)}</blockquote>`;
  }
  return html;
}
async function loadProjects(){
  const result=await api('/api/improvements');
  $('projects').innerHTML='<option value="">Choose a project</option>'+result.projects.map(p=>`<option value="${p.id}">${text(p.office)} · ${p.id}</option>`).join('');
}
async function loadProject(id){requireSavedDrafts();project=await api(`/api/improvements/${id}`);history.replaceState(null,'',`/improvements?project=${id}`);$('projects').value=id;render();}
function render(){
  $('project').hidden=false; $('project-title').textContent=project.office;
  $('historical-banner').hidden=!project.historical;
  let evidence=document.getElementById('intake-evidence');if(!evidence){evidence=document.createElement('p');evidence.id='intake-evidence';$('project-summary').after(evidence);}evidence.textContent=intakeEvidenceMessage(project.intakeEvidence);
  const rows=project.resources.filter(r=>!r.packaged);
  const ready=rows.filter(r=>r.review?.decision==='curated').length;
  $('project-summary').textContent=`${rows.length} ${rows.length===1?'resource':'resources'} in review · ${ready} Curated · original package ${project.baseVersion} · current package ${project.latestVersion ?? 'not connected'}`;
  $('export').disabled=!ready||!project.latestSha256||project.requiresReconnection;
  $('resources').innerHTML=rows.map(row=>{
    const completed=row.research.filter(s=>s.completed).length;
    let html=`<article class="resource" data-id="${text(row.id)}"><h2>${text(row.current?.name||row.original.name)}</h2><p>${completed} of ${row.research.length} research and reconciliation steps complete.</p>`;
    const contact=row.current||row.original;
    html+='<div>'+['phone','address','website','hours'].filter(field=>contact[field]).map(field=>`<div><strong>${text(field[0].toUpperCase()+field.slice(1))}:</strong> ${text(contact[field])}</div>`).join('')+'</div>';
    for(const [which,record,label] of [['base',row.original,'Original attachment'],['latest',project.latestSha256?row.current:null,'Current attachment']]){
      for(const pdf of record?.pdfs||[])html+=`<p><a target="_blank" rel="noopener" href="${text(url('attachment')+'?'+new URLSearchParams({which,path:pdf.path}))}">${label}: ${text(pdf.name||pdf.path)}</a></p>`;
    }
    if(!row.proposal)return html+'<p>Writing is not ready for review yet.</p></article>';
    if(row.blocked)html+=`<p class="blocked">${text(row.blocked)}</p>`;
    for(const [field,label] of [['description','Description'],['informationText','Information']]){
      const f=row.fields[field];if(!f)continue;
      const choice=row.review?.choices?.[field] || (f.changed&&!f.conflict?'proposed':'current');
      const diff=highlightComparison(field==='informationText'?renderInformationHTML(f.current):text(f.current),field==='informationText'?renderInformationHTML(f.proposed):text(f.proposed));
      html+=`<h3>${label}</h3>${f.conflict?'<p class="conflict">The office and Scout both changed this field. Choose which text to keep and explain below.</p>':''}<p>Changes are bold; removed text is crossed out in the current version.</p><div class="comparison"><div><strong>Current office text</strong><div class="${field==='informationText'?'information-rendered':'text'}">${diff.before}</div></div><div><strong>Proposed text</strong><div class="${field==='informationText'?'information-rendered':'text'}">${diff.after}</div></div></div><label><input type="radio" name="${text(row.id+'-'+field)}" data-field="${field}" value="current" ${choice==='current'?'checked':''}> Keep current ${label.toLowerCase()}</label><label><input type="radio" name="${text(row.id+'-'+field)}" data-field="${field}" value="proposed" ${choice==='proposed'?'checked':''}> Use proposed ${label.toLowerCase()}</label>`;
    }
    html+=`<details><summary>Original writing and research evidence</summary>${evidenceHTML(row)}</details><details><summary>Edit proposed writing</summary><label>Description<textarea data-edit="description">${text(row.proposal.description)}</textarea></label>`;
    for(const section of project.sections)html+=`<label>${text(section.heading)}<textarea data-section="${text(section.key)}">${text(row.proposal.informationSections[section.key])}</textarea></label>`;
    html+='<button data-action="edit">Save writing edits</button></details>';
    for(const r of row.evidence.reconcile.resolutions){
      if(r.status==='needs-review'&&row.findings[r.findingId].severity==='material')html+=`<label class="conflict">Resolve: ${text(row.findings[r.findingId].summary)}<textarea data-finding="${text(r.findingId)}">${text(row.review?.findingNotes?.[r.findingId]||'')}</textarea></label>`;
    }
    html+=`<label>Review note<textarea data-note>${text(row.review?.note||'')}</textarea></label><p data-review-state>${row.review?.decision==='curated'?'✓ Curated':row.review?.decision==='declined'?'Declined':'Unmarked'}</p><button data-action="curated" class="primary" ${row.blocked?'disabled':''}>Curated</button><button data-action="declined">Decline changes</button><button data-action="unmarked">Clear mark</button><button data-action="print">Print preview</button></article>`;
    return html;
  }).join('');
}
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
  if(command!=='edit'&&dirtyWriting.has(rid))throw new Error('Save the writing edits before reviewing or printing them.');
  if([...dirtyWriting,...dirtyReview].some(id=>id!==rid))throw new Error('Finish the other resource edits before continuing.');
  if(command==='print'){
    const selected=choices(card),record={...(row.current||row.original)};
    for(const field of ['description','informationText'])if(selected[field]==='proposed')record[field]=row.proposal[field];
    $('print-content').innerHTML=`<h2>${text(record.name)}</h2><p>${text(record.description)}</p>`+['phone','address','website','hours'].filter(f=>record[f]).map(f=>`<div><strong>${text(f[0].toUpperCase()+f.slice(1))}:</strong> ${text(record[f])}</div>`).join('')+`<hr><div class="information-rendered">${renderInformationHTML(record.informationText)}</div>`;
    window.print();return;
  }
  const body={revision:project.revision,resourceId:rid,reviewer:$('reviewer').value};
  if(command==='edit'){
    body.description=card.querySelector('[data-edit]').value;
    body.informationSections=Object.fromEntries([...card.querySelectorAll('[data-section]')].map(e=>[e.dataset.section,e.value]));
    project=await api(url('edit'),body);
  }else{
    Object.assign(body,{decision:command,choices:choices(card),note:card.querySelector('[data-note]').value,
                       findingNotes:Object.fromEntries([...card.querySelectorAll('[data-finding]')].map(e=>[e.dataset.finding,e.value]))});
    project=await api(url('review'),body);
  }
  dirtyWriting.delete(rid);dirtyReview.delete(rid);
  render();message(command==='edit'?'Edits saved. Review the revised text before marking it Curated.':'Review saved.');
}));
$('source').onchange=action(async()=>{
  sourceFile=$('source').files[0];if(!sourceFile)return;
  const result=await api('/api/improvements/inspect',sourceFile,true);
  if(result.office)$('office').value=result.office;
  $('source-summary').textContent=`Package ${result.version} · ${result.resources.length} resources. Select a small pilot or the intended work scope.`;
  $('resource-selection').innerHTML=result.resources.map(r=>`<label><input type="checkbox" value="${text(r.id)}"> ${text(r.name)}</label>`).join('');$('prepare').disabled=false;
});
$('prepare').onclick=action(async()=>{
  requireSavedDrafts();
  const query=new URLSearchParams({office:$('office').value,source:sourceFile.name,historical:$('historical').checked?'1':'0'});
  $('resource-selection').querySelectorAll('input:checked').forEach(e=>query.append('resourceId',e.value));
  project=await api('/api/improvements/prepare?'+query,sourceFile,true);await loadProjects();await loadProject(project.id);$('new-project').open=false;
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
