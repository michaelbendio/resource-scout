#!/usr/bin/env python3
"""Build the read-only Provo pilot report, with small, selectable print handouts."""
import argparse,json,html,re
from pathlib import Path
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('pilot_directory',type=Path)
p=parser.parse_args().pilot_directory
v=json.loads((p/'review-snapshot.json').read_text());m=json.loads((p/'manifest.json').read_text())
esc=lambda x:html.escape(str(x),quote=True)
labels={'informationText':'Information','informationSections':'Information','forGroups':'Groups','categoryFilters':'Types','categories':'Categories','name':'Name','description':'Description','hours':'Hours','address':'Address','phone':'Phone','website':'Website'}
headings={'programsAndServices':'Programs and Services','eligibilityRequirements':'Eligibility Requirements','howToBestConnect':'How to Best Connect','access':'Access','importantInformationToKnow':'Important Information to Know'}
def value(x):
 if x is None or x=='' or x==[] or x=={}:return '<span class="muted">Not recorded</span>'
 if isinstance(x,dict):return ''.join('<h4>'+esc(headings.get(k,labels.get(k,k)))+'</h4>'+value(t) for k,t in x.items())
 if isinstance(x,list):return '<p>'+esc(', '.join('Food' if t=='food' else str(t) for t in x))+'</p>'
 return '<div class="value">'+re.sub(r'\*\*(.*?)\*\*',r'<strong>\1</strong>',esc(x))+'</div>'
parts=[]
for r in v['items']:
 name=r['current']['name'] if r['current'] else r['fields']['name']
 block=f'<section id="{esc(r["id"])}"><h2>{esc(name)}</h2><p class="status">'+('Proposed update' if r['current'] else 'Proposed addition')+' · awaiting your review</p><p>'+esc(r['summary'])+'</p>'
 if r['current']:
  for k,c in r['comparison'].items():
   block+='<h3>'+esc(labels.get(k,k))+'</h3><div class="comparison"><div><h4>In historical office package</h4>'+'<div data-diff-before>'+value(c['current'])+'</div>'+'</div><div><h4>Scout proposes</h4>'+'<div data-diff-after>'+value(c['proposed'])+'</div>'+'</div></div>'
  block+='<details class="original-notes"><summary>Existing Information stays intact</summary><p>These are the original local notes, including dated limits that still need confirmation. This pilot does not rewrite them or claim they are all current.</p>'+value(r['current'].get('informationText'))+'<p>Last human verification: '+esc(r['current'].get('verifiedOn'))+'. Preserved; no new human verification.</p></details>'
 else:
  block+='<div class="new-resource">'
  for k,x in r['fields'].items():
   if k in ['categories','categoryFilters','forGroups']:continue
   if k=='informationSections':block+=value(x)
   elif x:block+='<h3>'+esc(labels.get(k,k))+'</h3>'+value(x)
  block+='</div><p><strong>Classification:</strong> Food. No Type or group proposed. No matching resource found in the historical package; check the current package before adding.</p>'
 block+='<h3>Questions to settle</h3><ul>'+''.join('<li>'+esc(q)+'</li>' for q in r['questions'][:3])+'</ul>'
 if len(r['questions'])>3:block+='<details><summary>Other unresolved local details ('+str(len(r['questions'])-3)+')</summary><ul>'+''.join('<li>'+esc(q)+'</li>' for q in r['questions'][3:])+'</ul></details>'
 block+='<p class="muted">Suggested follow-up by September 13, 2026. This is a recommendation, not an automatic scheduled run.</p><details class="audit-details"><summary>Sources and independent audit decisions</summary><p>Web research: September 6, 2026. No provider was contacted; no form was submitted. Seeing a website does not prove a service was delivered that day.</p>'
 for s in r['sources']:block+='<p><a target="_blank" rel="noopener" href="'+esc(s['url'])+'">'+esc(s['url'])+'</a><br>'+esc(s['excerpt'])+'</p>'
 for who,audit in r['audits'].items():
  block+='<h3>'+esc(who)+'</h3><p>'+esc(audit['researchNotes'])+'</p>'
  for finding in audit['findings']:
   fid=who+':'+finding['id'];resolution=next(x for x in r['resolutions'] if x['findingId']==fid)
   block+='<div class="audit"><p><strong>Auditor finding:</strong> '+esc(finding['summary'])+'</p><p><strong>Scout decision — '+('needs human follow-up' if resolution['status']=='needs-review' else 'addressed in proposal')+':</strong> '+esc(resolution['reason'])+'</p></div>'
 block+='</details></section>';parts.append(block)
body='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Provo Food Maintenance Pilot</title><style>
*{box-sizing:border-box}body{margin:0;font:18px/1.55 system-ui,sans-serif;color:#203647;background:#f2f5f7;overflow-wrap:anywhere}header{background:#103d58;color:#fff;padding:26px 20px}header div,main{max-width:1060px;margin:auto}main{padding:20px}h1{font-size:1.8rem;margin:0}h2{font-size:1.3rem;margin-top:0}h3{font-size:1.08rem}h4{font-size:1rem;margin:.8rem 0}.subtitle{margin:6px 0 0;color:#d9eaf3}section{background:white;border:1px solid #cad7df;border-radius:10px;padding:22px;margin:20px 0}a{color:#075d87;overflow-wrap:anywhere}.notice{background:#fff1ce;border-left:5px solid #a16f13;padding:16px}.status{font-weight:650;color:#745113}.muted{color:#586874}.comparison{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:16px}.comparison>div{background:#f4f7f9;padding:14px;border-radius:6px}.comparison>div+div{background:#edf6f3}.value{white-space:pre-wrap;overflow-wrap:anywhere}summary{cursor:pointer;font-weight:650;padding:14px 0}details{border-top:1px solid #dce4e8;margin-top:18px}li{margin:10px 0}.audit{border-left:3px solid #b5cbd8;padding:1px 14px;margin:20px 0}.new-resource{border-left:4px solid #36846a;padding:0 18px}.counts{display:flex;gap:18px;flex-wrap:wrap}.counts div{background:#edf3f7;padding:12px 18px;border-radius:6px}.counts strong{display:block;font-size:1.5rem}.scope{font-weight:600}:focus-visible{outline:3px solid #1477ac;outline-offset:3px}@media(max-width:640px){body{font-size:17px}main{padding:12px}section{padding:16px}.comparison{grid-template-columns:1fr}.counts{gap:10px}}button{font:inherit;font-weight:650;background:#fff;color:#103d58;border:2px solid #fff;border-radius:6px;padding:10px 18px;cursor:pointer}.print-help{font-size:1rem}.print-only{display:none}dialog{width:min(560px,calc(100% - 24px));max-height:90vh;overflow:auto;border:1px solid #9aadb9;border-radius:10px;padding:24px}dialog::backdrop{background:#17334a88}dialog select{font:inherit;width:100%;padding:10px;margin:8px 0 18px}dialog label{display:block}dialog button{border-color:#103d58}dialog .primary{background:#103d58;color:white}.dialog-actions{display:flex;gap:12px;justify-content:flex-end;margin-top:22px}.audit-option{display:flex;gap:10px;align-items:flex-start}.audit-option input{width:20px;height:20px;flex-shrink:0}dialog [hidden]{display:none}#print-copy{display:none}@page{size:letter;margin:0.65in}@media print{body>header,body>main,body>dialog{display:none!important}#print-copy{display:block!important}#print-copy>header{display:block}#print-copy h1{font-size:16pt}#print-copy h2{font-size:14pt}#print-copy h3{font-size:12pt}body{background:white;color:black;font-size:11pt;line-height:1.3}header{background:white;color:black;padding:0}main{padding:0;max-width:none}.subtitle,.status,.muted{color:black}section{break-inside:auto;border:0;padding:12px 0;margin:12px 0}section[id]{border-top:2px solid #555;padding-top:18px}h1,h2,h3,h4,summary{break-after:avoid}p,li{orphans:3;widows:3}#print-copy p{margin:6px 0}#print-copy li{margin:6px 0}#print-copy h3{margin:12px 0 6px}#print-copy h4{margin:8px 0 4px}details{display:block;border:0;margin-top:12px}details::details-content{display:block;content-visibility:visible}summary{list-style:none;padding:8px 0}summary::-webkit-details-marker{display:none}.audit{break-inside:avoid;margin:14px 0}.comparison{display:block}.comparison>div{background:white;border-left:2px solid #777;margin:4px 0;padding:4px 10px}.counts div{background:white;padding:6px 12px;border:1px solid #777}.counts strong{font-size:1.2rem}a{color:black}.notice{background:white;padding:10px}.print-tools{display:none}.print-only{display:block}.new-resource{border-left:2px solid #777}}
</style></head><body><header><div><h1>Provo Food maintenance pilot</h1><p class="subtitle">Actual research · September 6, 2026 · proposals for your review</p><div class="print-tools"><p><button type="button" id="print-report">Print report</button></p><p class="print-help">Choose an overview or one resource to print. Full audit details are optional; all material stays available here on screen.</p></div></div></header><main><p class="notice"><strong>Historical development pilot.</strong> Research uses the previously approved Provo v41 package. Nothing has been added, updated, retired, or marked human-verified. This read-only page cannot change your office package.</p>
<section id="overview"><h2>What Scout checked</h2><div class="counts"><div><strong>2</strong>known resources rechecked</div><div><strong>1</strong>bounded Food addition search</div><div><strong>9</strong>independent audits completed</div></div><p class="scope">Food-focused checks of two broader service providers, not confirmation of every service they offer.</p><p>The package has 183 resources and 20 categories. The other 181 resources and 19 categories were not rechecked. Codex researched and reconciled; ChatGPT, Grok, and Perplexity each audited all three assignments.</p><p>31 audit findings received explicit decisions. Thirteen still call for human follow-up; some describe the same underlying question. Two updates and one addition are proposed. No closure is proposed.</p><p>Review the proposed wording below. Use Print report to keep it handy while making changes in the office app. The questions identify what still needs a staff call or local judgment.</p></section>'''
body+=''.join(parts)
body+='''<section><h2>Other leads and classification questions</h2><p>These were triaged during the addition search; they are not extra completed maintenance checks.</p><ul><li><strong>Elevate Utah and UVU:</strong> already represented in Food. Do not create duplicates.</li><li><strong>Mountainland Technical College:</strong> its <a href="https://mtec.edu/mtech-pantry/">pantry page</a> confirms food help for current students, faculty and staff, including campus arrangements in Provo. The college already has a resource entry. Review whether to add Food and the pantry details there or create a distinct program entry; resolve the differing campus schedules first.</li><li><strong>MAG meals on wheels:</strong> already mentioned inside MAG Aging and Family Services, currently under Seniors. This is a navigation/classification question, not a new provider. Preserve the pending Seniors migration decisions.</li><li><strong>Lasagna Love:</strong> a <a href="https://lasagnalove.org/request/">meal-request route</a> exists, but current volunteer availability in Provo remains unconfirmed. Kept as a lead, not a proposed addition.</li></ul></section>
<section><h2>What this pilot taught us</h2><p>Official pages can contradict each other. “New to this package” differs from a newly opened service. A valuable resource may already be hidden inside a list or another category. And an application form can contain practical access details that a homepage omits.</p><p>These are observations for discussion, not active learned rules. Our grand plan next calls for increment 5: proposed research-method lessons from attributable human-vetted outcomes. We should discuss this pilot and your decisions before implementing that learning step; adaptive assignment goals and run counts come later.</p></section><details><summary>Research provenance</summary>'''
for who,a in m['externalAudits'].items():body+='<p><a href="'+esc(a['url'])+'">'+esc(who)+' audit conversation</a></p>'
body+='<p>Source package SHA-256: '+esc(m['sourceSha256'])+'</p><p>All original IDs, 93 referenced PDF files, local Information and verification dates remain in the untouched source package. No attachment content was inspected in this Food pilot. No current production package has been connected for export.</p></details></main></body></html>'
print_script = """<script>
(() => {
  const dialog = document.getElementById('print-options');
  const choice = document.getElementById('print-choice');
  const includeAudit = document.getElementById('include-audit');
  const printCopy = document.getElementById('print-copy');
  const printButton = document.getElementById('print-report');
  function describeChoice() {
    const overview = choice.value === 'overview';
    document.getElementById('audit-option').hidden = overview;
    document.getElementById('chosen-resource').textContent = overview ? '' : choice.selectedOptions[0].textContent;
    document.getElementById('print-description').textContent = overview
      ? 'A short overview and a list of proposed changes.'
      : 'Current and proposed wording, Questions to settle, and Scout’s explanation. Original local notes stay in the on-screen report.';
  }
  function buildHandout() {
    printCopy.replaceChildren();
    const header = document.createElement('header');
    const title = document.createElement('h1');
    title.textContent = 'Provo Food maintenance pilot';
    const subtitle = document.createElement('p');
    subtitle.textContent = 'September 6, 2026 · Historical Provo v41 · Proposals, not completed office changes';
    header.append(title, subtitle);
    printCopy.append(header);
    const selected = document.getElementById(choice.value);
    if (!selected) return;
    const copy = selected.cloneNode(true);
    copy.removeAttribute('id');
    copy.querySelectorAll('[id]').forEach(el => el.removeAttribute('id'));
    if (choice.value === 'overview') {
      const paragraphs = copy.querySelectorAll(':scope > p');
      paragraphs[paragraphs.length - 1]?.remove();
      const heading = document.createElement('h3');
      heading.textContent = 'Proposed changes';
      const list = document.createElement('ul');
      document.querySelectorAll('main > section[id]:not(#overview)').forEach(section => {
        const item = document.createElement('li');
        const name = document.createElement('strong');
        name.textContent = section.querySelector('h2').textContent + ': ';
        item.append(name, section.querySelector(':scope > p:not(.status)').textContent);
        list.append(item);
      });
      copy.append(heading, list);
    } else {
      copy.querySelectorAll('.original-notes').forEach(el => el.remove());
      if (!includeAudit.checked) copy.querySelectorAll('.audit-details').forEach(el => el.remove());
      const note = document.createElement('p');
      note.textContent = includeAudit.checked
        ? 'Working copy with full audit details for this resource only.'
        : 'Working copy. Full sources and audit decisions remain in the on-screen report.';
      copy.prepend(note);
    }
    copy.querySelectorAll('details').forEach(el => el.open = true);
    printCopy.append(copy);
  }
  choice.addEventListener('change', describeChoice);
  printButton.addEventListener('click', () => { describeChoice(); dialog.showModal(); });
  document.getElementById('cancel-print').addEventListener('click', () => dialog.close());
  document.getElementById('confirm-print').addEventListener('click', () => {
    dialog.close();
    buildHandout();
    window.print();
  });
  dialog.addEventListener('close', () => printButton.focus());
  // Browser-menu printing uses the chosen handout, initially the overview.
  window.addEventListener('beforeprint', buildHandout);
  window.addEventListener('afterprint', () => printCopy.replaceChildren());
})();
</script>"""
options='<option value="overview">Overview — What Scout checked</option>'+''.join('<option value="'+esc(r['id'])+'">'+esc(r['current']['name'] if r['current'] else r['fields']['name'])+'</option>' for r in v['items'])
dialog='<dialog id="print-options" aria-labelledby="print-title"><h2 id="print-title">What would you like to print?</h2><p>Make a manageable handout to use while updating the office app.</p><label for="print-choice">Choose a handout</label><select id="print-choice">'+options+'</select><p id="chosen-resource"></p><div id="audit-option" hidden><label class="audit-option"><input type="checkbox" id="include-audit"><span>Include this resource’s full audit details<br><small>AI introductions, sources, Auditor findings, and Scout decisions. Adds several pages.</small></span></label></div><p id="print-description">A short overview and a list of proposed changes.</p><div class="dialog-actions"><button type="button" id="cancel-print">Cancel</button><button type="button" id="confirm-print" class="primary">Print handout</button></div></dialog><div id="print-copy" aria-hidden="true"></div>'
body=body.replace('</body>',dialog+print_script+'</body>')
highlighter=(Path(__file__).resolve().parents[1]/'web/comparison.js').read_text()
body=body.replace('</body>', '<script>'+highlighter+"\nfor(const pair of document.querySelectorAll('.comparison')){const a=pair.querySelector('[data-diff-before]'),b=pair.querySelector('[data-diff-after]');if(a&&b){const d=highlightComparison(a.innerHTML,b.innerHTML);a.innerHTML=d.before;b.innerHTML=d.after;}}"+'</script></body>')
body=body.replace('Review the proposed wording below.', 'Changes below are bold; removed wording is crossed out in the historical version.')
(p/'autoProvoMaintenancePilot.html').write_text(body)
print(p/'autoProvoMaintenancePilot.html')
