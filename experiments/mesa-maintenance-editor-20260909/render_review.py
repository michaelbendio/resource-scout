"""Render concise operator review; long comparisons expand on screen only."""
import difflib,html,json
from pathlib import Path
import markdown
P=Path(__file__).resolve().parent
ROOT=P.parents[1];OUT=ROOT/'output/mesa-maintenance-editor-20260909'
load=lambda n:json.loads((P/n).read_text())
ledger=load('editorial-decisions.json')
escape=html.escape
def difference(old,new):
 a=old.split();b=new.split();parts=[]
 for tag,i,j,k,l in difflib.SequenceMatcher(a=a,b=b).get_opcodes():
  if tag=='equal':parts.append(escape(' '.join(b[k:l])))
  else:
   if i!=j:parts.append('<del>'+escape(' '.join(a[i:j]))+'</del>')
   if k!=l:parts.append('<strong>'+escape(' '.join(b[k:l]))+'</strong>')
 return ' '.join(parts)
def changed_paragraphs(old,new):
 a=old.split('\n\n');b=new.split('\n\n');parts=[]
 for tag,i,j,k,l in difflib.SequenceMatcher(a=a,b=b).get_opcodes():
  if tag=='equal':continue
  parts.append('<p>'+difference('\n\n'.join(a[i:j]),'\n\n'.join(b[k:l]))+'</p>')
 return ''.join(parts)
intro='''# Mesa maintenance pilot: what changed

**12 resources retained · 3 text updates · 2 new open questions**

This is a partial draft for review. The original autoMesa and active playbooks are unchanged. Current web checks are not human phone verification.

| Resource | Proposed change |
|---|---|
| Clothes Cabin | **Add conditional PINCH pickup** for a person who cannot visit. A service provider must confirm it can use the program. Ordinary walk-in access remains. |
| The Worker | **Add housing participation requirements and the dated wait estimate.** Remove the promise of a private room and a fixed follow-up period because two provider pages disagree. Keep free job-search help separate from housing rules. |
| Mesa deposit help | **Label the checklist as the saved FY25/26 paper form.** Ask for current instructions; the online application could not be read. Keep the conflicting eligibility and timing questions. |

## Two new questions to settle

- **Clothes Cabin:** Can TSO missionaries request and collect PINCH orders? The provider welcomes local service organizations, but does not name TSO.
- **The Worker:** What room arrangement and follow-up apply now? Its overview says private room and nine months; its housing page describes a shared one-bedroom apartment and one year. Ask about costs and current locations at the same time as the existing housing question.

## Existing questions remain useful

All **14 original questions and histories remain intact**. Mesa's 80% versus 60% income conflict, Smart Justice's photo-ID versus driver's-license wording, and the Family Housing Hub check-in question were not settled by the second pass. Two overlapping Mesa deposit eligibility questions can be covered by one inquiry; their original records remain separate.

The voucher office and deposit program stay separate because their services and application routes differ. No extra exclusions or combinations were forced.

## What we learned

The targeted pass corroborated or reconciled four useful findings across two resources and reconfirmed several existing uncertainties. It did not justify a new lesson test. Scout saved twelve editorial decisions and five package-change observations; these are evidence records, not seventeen independent examples.

**Increment 5 remains next:** adaptive passes and model sampling, guided by further measured work. No model comparison or scheduling change occurred here.
'''
body=markdown.markdown(intro,extensions=['tables'])
body+='<nav class="screen-only"><button onclick="window.print()">Print this short review</button> · <a href="autoMesaMaintenancePilot.html">Open the 12-resource draft</a> · <a href="mesa-maintenance-editor-draft.zip">Partial resource package</a> · <a href="scout-mesa-maintenance-editor-results.md">Detailed results</a></nav>'
body+='<section class="screen-only"><h2>Exact changes</h2><p>Expand a resource to compare changed paragraphs. <strong>Added wording is bold</strong>; removed wording is crossed out. Unchanged paragraphs are omitted here. Existing questions are preserved in the resource app.</p>'
for d in ledger['decisions']:
 if not d['fieldChanges']:continue
 body+='<details><summary>'+escape(d['originalName'])+'</summary>'
 for change in d['fieldChanges']:
  if change['field']=='informationText':body+=changed_paragraphs(change['before'],change['after'])
 body+='<p>Sources: '+' · '.join('<a href="'+escape(e['reference'],quote=True)+'">'+escape(e['reference'].split('/')[2])+'</a>' for e in d['evidence'])+'</p></details>'
body+='</section>'
doc='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Mesa maintenance pilot review</title><style>
body{font:17px/1.5 system-ui,sans-serif;color:#20303c;max-width:900px;margin:28px auto;padding:0 20px}h1{font-size:1.7em;line-height:1.2}h2{font-size:1.25em;margin-top:1.5em}table{border-collapse:collapse;width:100%;font-size:.95em}th,td{text-align:left;vertical-align:top;border-bottom:1px solid #ccd4dd;padding:9px}th{background:#edf3f6}a{color:#175881;overflow-wrap:anywhere}details{border:1px solid #cbd6df;border-radius:5px;margin:12px 0;padding:12px}summary{cursor:pointer;font-weight:700}del{color:#735353}strong{font-weight:750}nav{padding:18px 0;line-height:2}button{font:inherit;padding:8px 12px}@media print{.screen-only{display:none!important}body{font-size:10.5pt;line-height:1.3;margin:0;padding:0}h1{font-size:18pt}h2{font-size:12pt;break-after:avoid;margin-top:12px}tr,li{break-inside:avoid}th,td{padding:6px}@page{margin:16mm}}
</style><body>'''+body+'</body></html>'
(OUT/'mesa-maintenance-editor-review.html').write_text(doc)
(OUT/'scout-mesa-maintenance-editor-results.md').write_bytes((ROOT/'docs/scout-mesa-maintenance-editor-results.md').read_bytes())
print('Rendered concise review with expandable exact changes and compact print layout.')
