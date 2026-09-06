'use strict';
// Inputs are already escaped/rendered HTML. Only text nodes are changed.
function highlightComparison(beforeHTML, afterHTML) {
  function prepare(source) {
    const root=document.createElement('div');root.innerHTML=source;
    const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT), nodes=[], tokens=[];
    while(walker.nextNode()) {
      const node=walker.currentNode, parts=node.data.match(/\s+|[\p{L}\p{N}_]+|[^\s\p{L}\p{N}_]/gu)||[];
      nodes.push({node,parts,start:tokens.length});tokens.push(...parts);
    }
    return {root,nodes,tokens};
  }
  const a=prepare(beforeHTML),b=prepare(afterHTML), keptA=new Set(),keptB=new Set();
  let start=0,endA=a.tokens.length,endB=b.tokens.length;
  while(start<endA && start<endB && a.tokens[start]===b.tokens[start]) {keptA.add(start);keptB.add(start++);}
  while(endA>start && endB>start && a.tokens[endA-1]===b.tokens[endB-1]) {keptA.add(--endA);keptB.add(--endB);}
  const n=endA-start,m=endB-start;
  // Bound memory for unusually long fields; retain exact text in all cases.
  if(n*m<=2000000) {
    const rows=Array.from({length:n+1},()=>new Uint32Array(m+1));
    for(let i=n-1;i>=0;i--)for(let j=m-1;j>=0;j--)
      rows[i][j]=a.tokens[start+i]===b.tokens[start+j]?1+rows[i+1][j+1]:Math.max(rows[i+1][j],rows[i][j+1]);
    let i=0,j=0;
    while(i<n && j<m) {
      if(a.tokens[start+i]===b.tokens[start+j]) {keptA.add(start+i++);keptB.add(start+j++);}
      else if(rows[i+1][j]>=rows[i][j+1])i++;else j++;
    }
  }
  function render(value,kept,removed) {
    for(const {node,parts,start} of value.nodes) {
      const fragment=document.createDocumentFragment();
      for(let i=0;i<parts.length;) {
        const changed=!kept.has(start+i);let content=parts[i++];
        while(i<parts.length && (!kept.has(start+i))===changed)content+=parts[i++];
        if(changed && content.trim()) {
          const strong=document.createElement('strong');strong.className='comparison-change';
          if(removed){const del=document.createElement('del');del.textContent=content;strong.append(del);}
          else strong.textContent=content;
          fragment.append(strong);
        } else fragment.append(document.createTextNode(content));
      }
      node.replaceWith(fragment);
    }
    return value.root.innerHTML;
  }
  return {before:render(a,keptA,true),after:render(b,keptB,false)};
}

function intakeEvidenceMessage(evidence) {
  if(!evidence)return '';
  return `Package comparison saved: ${evidence.observedChanges} changes; ${evidence.linkedAdoptions} linked to delivered proposals. No provider verification inferred.`;
}
